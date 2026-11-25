-- Test only. The smallest stand-in for what a Supabase project provides before our migrations run, so the migrations
-- and their policies are exercised exactly as written on a plain local PostgreSQL (no Docker, no project).
-- Run as the cluster superuser; the migrations then run as `postgres`, which is not a superuser here either.
create role anon nologin noinherit;
create role authenticated nologin noinherit;
create role service_role nologin noinherit bypassrls;
create role postgres login createrole bypassrls;      -- as on Supabase: owner of our objects, not a superuser
grant anon, authenticated, service_role to postgres;  -- so tests can "set role"

create schema auth;
create table auth.users (
  id uuid primary key default gen_random_uuid(),
  email text unique,
  encrypted_password text,
  phone text,
  is_anonymous boolean not null default false,
  created_at timestamptz not null default now()
);
create table auth.sessions (
  id uuid primary key default gen_random_uuid(),
  user_id uuid not null references auth.users (id) on delete cascade,
  created_at timestamptz not null default now()
);
create table auth.mfa_factors (id uuid primary key default gen_random_uuid(), user_id uuid not null references auth.users (id) on delete cascade, factor_type text);
create table auth.identities (id uuid primary key default gen_random_uuid(), user_id uuid not null references auth.users (id) on delete cascade, provider text not null, provider_id text not null default '', identity_data jsonb not null default '{}');
create table auth.audit_log_entries (id uuid primary key default gen_random_uuid(), payload json, ip_address text, created_at timestamptz default now());
-- the same definitions Supabase ships: the API sets request.jwt.claims for every request
create function auth.uid() returns uuid language sql stable as $$
  select coalesce(nullif(current_setting('request.jwt.claim.sub', true), ''),
                  (nullif(current_setting('request.jwt.claims', true), '')::jsonb ->> 'sub'))::uuid $$;
create function auth.role() returns text language sql stable as $$
  select coalesce(nullif(current_setting('request.jwt.claim.role', true), ''),
                  (nullif(current_setting('request.jwt.claims', true), '')::jsonb ->> 'role'))::text $$;
create function auth.jwt() returns jsonb language sql stable as $$
  select coalesce(nullif(current_setting('request.jwt.claims', true), ''), '{}')::jsonb $$;
grant usage on schema auth to anon, authenticated, service_role, postgres;
grant execute on all functions in schema auth to anon, authenticated, service_role, postgres;
grant select, insert, delete, references on auth.users, auth.sessions to postgres;
grant select, insert, delete on auth.audit_log_entries to postgres;
-- on Supabase the owner may add triggers to auth tables (the documented way to react to a new user)
grant trigger on auth.users, auth.mfa_factors, auth.identities to postgres;
grant select on auth.mfa_factors, auth.identities to postgres;
grant all on auth.mfa_factors, auth.identities to service_role;
grant all on auth.users, auth.sessions to service_role;

-- Supabase's defaults: every new object in public is open to the API roles and RLS is the only guard.
-- The migrations must not rely on that being absent, so the stand-in keeps it.
alter schema public owner to postgres;
grant usage on schema public to anon, authenticated, service_role;
alter default privileges for role postgres in schema public grant all on tables    to anon, authenticated, service_role;
alter default privileges for role postgres in schema public grant all on sequences to anon, authenticated, service_role;
alter default privileges for role postgres in schema public grant all on functions to anon, authenticated, service_role;
grant create on database :"DBNAME" to postgres;
