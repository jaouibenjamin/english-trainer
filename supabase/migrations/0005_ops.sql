-- Operations (docs/BACKEND.md sections 6 and 8): the encrypted backup export and the import from the Sheet.

-- ---------------------------------------------------------------- backup export
-- Supabase ships pgcrypto in the schema "extensions"; the local test database gets the same.
create schema if not exists extensions;
create extension if not exists pgcrypto with schema extensions;

alter table private.settings
  add column backup_pubkey     text,           -- the owner's RSA 4096 public key, ASCII armour (checklist step 14)
  add column backup_token_hash text check (backup_token_hash is null or backup_token_hash ~ '^[0-9a-f]{64}$'),
  add column backup_opened_at  timestamptz,    -- an export runs for 30 minutes, and starts at most once in 6 hours
  add column backup_every_h    int not null default 6,
  add column backup_chunk      int not null default 2000 check (backup_chunk between 1 and 20000);

-- every table that is backed up, in the order a restore needs them (tools/restore.py)
create function private.backup_tables() returns text[] language sql immutable set search_path = '' as $$
  select array['public.classes', 'public.roster', 'public.teachers', 'public.pupils', 'public.items', 'public.levels',
    'public.answers', 'public.points', 'public.pupil_totals', 'public.progress', 'public.flags', 'public.level_best',
    'public.answer_daily', 'private.class_codes', 'private.pupil_secrets', 'private.reset_codes',
    'private.pupil_devices', 'private.answer_batches', 'private.pupil_days', 'private.deletions', 'private.maintenance_log',
    'private.settings'] $$;
-- and every table that is NOT, on purpose (review S-d). tests/ops.py checks that the two lists cover every table.
--   ip_salts, auth_buckets, class_misses: with the day's salt, address hashes could be reversed for every address
--   auth_attempts, auth_lock_events: names typed at sign-in, kept 30 days in the database and never longer in a backup
--   legacy_import: the Sheet's bare fast hashes, for minutes during the migration
--   teacher_resets: a counter for the teacher's daily cap of new codes, 2 days long
-- A restore therefore starts with every lock open and every counter at zero; a picture recovery that was closed
-- after 3 wrong tries is open again (the teacher's screen shows nothing locked).
create function private.backup_excluded() returns text[] language sql immutable set search_path = '' as $$
  select array['private.ip_salts', 'private.auth_buckets', 'private.class_misses', 'private.auth_attempts',
    'private.auth_lock_events', 'private.legacy_import', 'private.teacher_resets'] $$;
revoke all on function private.backup_excluded() from public, anon, authenticated;

/* Callable with the public key, so the twice-weekly workflow needs no server key. The caller proves it holds the
   export token (only its sha256 is stored here). What comes back is ciphertext for the owner's key only.
     backup_export(token)                     opens an export (at most once in backup_every_h hours): the table list
     backup_export(token, table, offset)      one chunk of that table, encrypted; `next` is the next offset or null
   Chunks keep every statement short (the public role has a short statement timeout). A table that changes between
   two chunks may be a few rows off; the restore's totals check says so. */
create function public.backup_export(p_token text, p_table text default null, p_offset int default 0) returns jsonb
language plpgsql security definer set search_path = '' as $$
declare s private.settings; v_now timestamptz := clock_timestamp(); v_rows jsonb; v_n int; v_order text;
begin
  select * into s from private.settings;
  if s.backup_pubkey is null or s.backup_token_hash is null then return jsonb_build_object('ok', false, 'e', 'setup'); end if;
  if p_token is null or char_length(p_token) > 200
     or encode(extensions.digest(convert_to(p_token, 'UTF8'), 'sha256'), 'hex') <> s.backup_token_hash then
    return jsonb_build_object('ok', false, 'e', 'token');
  end if;
  if p_table is null then
    if s.backup_opened_at is not null and s.backup_opened_at > v_now - make_interval(hours => s.backup_every_h) then
      return jsonb_build_object('ok', false, 'e', 'wait',
        'wait', ceil(extract(epoch from s.backup_opened_at + make_interval(hours => s.backup_every_h) - v_now))::int);
    end if;
    update private.settings set backup_opened_at = v_now;
    return jsonb_build_object('ok', true, 'tables', to_jsonb(private.backup_tables()), 'at', v_now);
  end if;
  if s.backup_opened_at is null or s.backup_opened_at < v_now - interval '30 minutes' then
    return jsonb_build_object('ok', false, 'e', 'closed');
  end if;
  if not (p_table = any (private.backup_tables())) or p_offset is null or p_offset < 0 then
    return jsonb_build_object('ok', false, 'e', 'input');
  end if;
  -- the table name comes from the fixed list above, never from the caller as text in SQL
  select coalesce(string_agg(format('%I', a.attname), ', ' order by array_position(i.indkey, a.attnum)), 'x::text')
    into v_order
    from pg_index i join pg_attribute a on a.attrelid = i.indrelid and a.attnum = any (i.indkey)
   where i.indrelid = p_table::regclass and i.indisprimary;
  execute format('select coalesce(jsonb_agg(to_jsonb(x)), ''[]''::jsonb), count(*)::int from (select * from %s x order by %s offset %s limit %s) x',
                 p_table::regclass, v_order, p_offset, s.backup_chunk) into v_rows, v_n;
  return jsonb_build_object('ok', true, 'table', p_table, 'offset', p_offset, 'rows', v_n,
    'next', case when v_n = s.backup_chunk then p_offset + v_n end,
    'data', extensions.armor(extensions.pgp_pub_encrypt(v_rows::text, extensions.dearmor(s.backup_pubkey))));
end $$;
revoke all on function public.backup_export(text, text, int) from public, authenticated;
grant execute on function public.backup_export(text, text, int) to anon, service_role;
revoke all on function private.backup_tables() from public, anon, authenticated;

-- ---------------------------------------------------------------- import from the Sheet (tools/migrate_sheet.py)
/* One class's pupils from the Sheet, as JSON rows {name, salt, hash, state, points}. Run by the owner with the
   database password (never with the pepper: the hashes are wrapped afterwards by admin-wrap-legacy). Idempotent, so
   the nightly re-sync of the copy phase is the same call:
   - a name not here yet: a pupil, its fast hash staged in legacy_import, its blob, its points as one 'migrated' row
     (capped at settings.migrated_cap);
   - a name already here: its blob is replaced by the Sheet's (the Sheet is the truth until the switch); a code
     already set or wrapped is never touched; points are never given twice.
   Returns counts and the names above three times the class median of points (the tool prints their CSV rows). */
create function private.sheet_import(p_class uuid, p_rows jsonb) returns jsonb
language plpgsql security definer set search_path = '' as $$
declare s private.settings; r jsonb; v_id uuid; v_name text; v_pts int; v_state jsonb;
  n_new int := 0; n_seen int := 0; n_blob int := 0; n_hash int := 0; n_bad int := 0; n_err int := 0; v_med numeric; v_out jsonb;
  d_new int; d_blob int; d_hash int;
begin
  if not exists (select 1 from public.classes where id = p_class) then raise exception 'no such class'; end if;
  if jsonb_typeof(p_rows) <> 'array' then raise exception 'rows must be an array'; end if;
  select * into s from private.settings;
  for r in select * from jsonb_array_elements(p_rows) loop
    v_name := btrim(regexp_replace(normalize(coalesce(r ->> 'name', ''), NFC), '\s+', ' ', 'g'));
    if not app.name_ok(v_name) then n_bad := n_bad + 1; continue; end if;
    v_state := case when jsonb_typeof(r -> 'state') = 'object' and char_length((r -> 'state')::text) <= 40000 then r -> 'state' else '{}'::jsonb end;
    v_pts := least(app.safe_int(r -> 'points', 1000000), s.migrated_cap);
    d_new := 0; d_blob := 0; d_hash := 0;
    -- one row at a time: a row the database refuses is counted and skipped. Caught here, its error and the
    -- "Failing row contains (...)" detail never reach the server's log (review of #27, B3-bis)
    begin
      select id into v_id from public.pupils where class_id = p_class and name_key = app.name_key(v_name);
      if v_id is null then
        d_new := 1;
        insert into public.pupils (class_id, display_name) values (p_class, v_name) returning id into v_id;
        if v_pts > 0 then
          insert into public.points (pupil_id, delta, reason, ref) values (v_id, v_pts, 'migrated', 'sheet');
          update public.pupil_totals set points = points + v_pts where pupil_id = v_id;
        end if;
      end if;
      insert into public.progress (pupil_id, state, updated_at) values (v_id, v_state, now())
        on conflict (pupil_id) do update set state = excluded.state, updated_at = excluded.updated_at
        where public.progress.state is distinct from excluded.state;
      get diagnostics d_blob = row_count;
      if coalesce(r ->> 'hash', '') ~ '^[0-9a-f]{64}$' and coalesce(r ->> 'salt', '') <> ''
         and not exists (select 1 from private.pupil_secrets where pupil_id = v_id and code_hash is not null) then
        insert into private.legacy_import (pupil_id, salt, hash) values (v_id, r ->> 'salt', r ->> 'hash')
          on conflict (pupil_id) do update set salt = excluded.salt, hash = excluded.hash;
        d_hash := 1;
      end if;
      n_new := n_new + d_new; n_seen := n_seen + (1 - d_new); n_blob := n_blob + d_blob; n_hash := n_hash + d_hash;
    exception when others then
      n_err := n_err + 1;
    end;
  end loop;
  select percentile_cont(0.5) within group (order by t.points) into v_med
    from public.pupil_totals t join public.pupils p on p.id = t.pupil_id where p.class_id = p_class;
  select jsonb_build_object('new', n_new, 'existing', n_seen, 'blobs', n_blob, 'hashes_staged', n_hash, 'refused_names', n_bad,
           'refused_rows', n_err, 'median', coalesce(v_med, 0),
           'look_at', coalesce((select jsonb_agg(p.display_name order by t.points desc) from public.pupil_totals t
                                join public.pupils p on p.id = t.pupil_id
                               where p.class_id = p_class and v_med > 0 and t.points > 3 * v_med), '[]'::jsonb))
    into v_out;
  -- a dry run is the caller's ROLLBACK (tools/migrate_sheet.py)
  return v_out;
end $$;
revoke all on function private.sheet_import(uuid, jsonb) from public, anon, authenticated;
grant execute on function private.sheet_import(uuid, jsonb) to service_role;
