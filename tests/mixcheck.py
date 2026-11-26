"""The check without a browser behind tests/cache_mix.py: can this checkout's modules run next to the previous ship's?

static_check(now, prev) takes {'ui.js': source} for this checkout and for the previous ship and returns (bad, added,
unknown). It is strict: what it cannot follow is a failure, never a pass.

Both directions:
  - new code, old module: an export added since the previous ship may not be bound by name (import {a}, import d from
    for a new default, export {a} from, import('x').then(({a})=>..), const {a}=NS); every read of it through a module
    object (import * as NS, the parameter of import('x').then(m=>..), an alias Y=NS) must be guarded at that read:
      - inside the true branch of typeof NS.a==='function'?..:.., or after typeof NS.a==='function'&&.., or in the body
        of if(typeof NS.a==='function'){..} (the condition may add more terms with &&, never || or ??);
      - or, for a data export (not a function), NS.a??fallback where NS.a is a whole operand of ?? (not 'x'+NS.a??..);
    a module object used any other way (passed on, returned, m=>m, NS[k]) cannot be followed and fails.
  - old code, new module: every name the previous ship's modules import by name must still be exported here, and
    every module they import must still exist.
"""
import jsmods

_is = jsmods._is
START = {'(', '[', '{', ',', ';', '=', '=>', ':', '?', '...', '+=', '-=', '&&=', '||=', '??='}   # an operand starts after these
ENDS = {'||', '??', '?', ':', ',', ';'}


def _tok(T, i):
    return T[i] if 0 <= i < len(T) else None


def _starts_operand(t):
    return t is None or (t.t == 'punct' and t.v in START) or (t.t == 'id' and t.v in ('return', 'case', 'throw'))


def _match(T, i):
    """the index of the bracket that closes the one at i"""
    d = 0
    for j in range(i, len(T)):
        if T[j].t == 'punct' and T[j].v in '([{': d += 1
        elif T[j].t == 'punct' and T[j].v in ')]}':
            d -= 1
            if d == 0: return j
    return len(T) - 1


def _expr_end(T, i, stop):
    """from i, the last index of the expression before a token in `stop` at depth 0 or an unmatched closing bracket"""
    d = 0
    for j in range(i, len(T)):
        t = T[j]
        if t.t == 'punct' and t.v in '([{': d += 1
        elif t.t == 'punct' and t.v in ')]}':
            if d == 0: return j - 1
            d -= 1
        elif d == 0 and t.t == 'punct' and t.v in stop: return j - 1
    return len(T) - 1


def _arrow_body(T, a):
    """a: index of '=>'; the range of the arrow's body"""
    if _is(_tok(T, a + 1), '{'): return a + 1, _match(T, a + 1)
    return a + 1, _expr_end(T, a + 1, {',', ';'})


def _kinds(info):
    """{exported name: 'function' | 'data'}: function when its declaration is a function, a class or an arrow"""
    T = info['tokens']
    local = {}
    for k in range(len(T)):
        if T[k].t == 'id' and T[k].v == 'export' and _is(_tok(T, k + 1), '{'):
            j = k + 2
            while j < len(T) and not _is(T[j], '}'):
                if T[j].t == 'id' and _tok(T, j + 1) is not None and _tok(T, j + 1).v == 'as':
                    local[T[j + 2].v] = T[j].v; j += 3
                elif T[j].t == 'id':
                    local[T[j].v] = T[j].v; j += 1
                else:
                    j += 1
    out = {}
    for name in info['exports']:
        decl = local.get(name, name)
        kind = None
        for i in range(len(T)):
            if not (T[i].t == 'id' and T[i].v == decl and not _is(_tok(T, i - 1), '.')): continue
            p = _tok(T, i - 1)
            if p is not None and p.v in ('function', 'class', '*'):
                kind = 'function'; break
            if p is not None and (p.v in ('const', 'let', 'var') or _is(p, ',')) and _is(_tok(T, i + 1), '='):
                x = _tok(T, i + 2)
                if x is None: break
                if x.v in ('function', 'async', 'class') or (x.t == 'id' and _is(_tok(T, i + 3), '=>')) \
                        or (_is(x, '(') and _is(_tok(T, _match(T, i + 2) + 1), '=>')):
                    kind = 'function'
                else:
                    kind = kind or 'data'
                if kind == 'function': break
        out[name] = kind or 'function'   # not found: the stricter reading
    return out


def _guards(T):
    """[(obj, name, first, last)]: the token ranges each typeof obj.name==='function' protects"""
    out = []
    for g in range(len(T) - 5):
        if not (T[g].t == 'id' and T[g].v == 'typeof' and T[g + 1].t == 'id' and T[g + 2].t == 'punct' and T[g + 2].v in ('.', '?.')
                and T[g + 3].t == 'id' and T[g + 4].t == 'punct' and T[g + 4].v in ('===', '==') and T[g + 5].t == 'str' and T[g + 5].v == 'function'):
            continue
        obj, name, nx = T[g + 1].v, T[g + 3].v, _tok(T, g + 6)
        if _is(nx, '&&'):
            out.append((obj, name, g + 7, _expr_end(T, g + 7, ENDS)))
        if _is(nx, '?'):
            # the condition must be the guard, or the guard joined by && only: (a||guard)?x:y runs x without it
            j, ok, d = g - 1, True, 0
            while j >= 0:
                t = T[j]
                if t.t == 'punct' and t.v in ')]}': d += 1
                elif t.t == 'punct' and t.v in '([{':
                    if d == 0: break
                    d -= 1
                elif d == 0 and (_starts_operand(t) and not _is(t, '&&')): break
                elif d == 0 and t.t == 'punct' and t.v in ('||', '??'): ok = False; break
                j -= 1
            if ok:
                d, q = 0, 0
                for e in range(g + 7, len(T)):
                    t = T[e]
                    if t.t == 'punct' and t.v in '([{': d += 1
                    elif t.t == 'punct' and t.v in ')]}':
                        if d == 0: break
                        d -= 1
                    elif d == 0 and _is(t, '?'): q += 1
                    elif d == 0 and _is(t, ':'):
                        if q == 0: break
                        q -= 1
                out.append((obj, name, g + 7, e - 1))
        # if(..guard..){body}: the guard directly in the if's parentheses, joined to the rest by && only
        d, j = 0, g - 1
        while j >= 0:
            t = T[j]
            if t.t == 'punct' and t.v in ')]}': d += 1
            elif t.t == 'punct' and t.v in '([{':
                if d == 0: break
                d -= 1
            j -= 1
        if j >= 1 and _is(T[j], '(') and T[j - 1].t == 'id' and T[j - 1].v == 'if':
            c = _match(T, j)
            d, ok = 0, True
            for i in range(j + 1, c):
                t = T[i]
                if t.t == 'punct' and t.v in '([{': d += 1
                elif t.t == 'punct' and t.v in ')]}': d -= 1
                elif d == 0 and t.t == 'punct' and t.v in ('||', '??', '?', ','): ok = False
            if ok:
                b = c + 1
                last = _match(T, b) if _is(_tok(T, b), '{') else _expr_end(T, b, {';'})
                out.append((obj, name, b, last))
    return out


def static_check(now, prev):
    mod = lambda s: s[2:] if s.startswith('./') else s
    info = {f: jsmods.modinfo(s) for f, s in now.items()}
    old = {f: jsmods.modinfo(s) for f, s in prev.items()}
    unknown = [f'js/{f} {u}' for f, i in info.items() for u in i['unknown']] + [f'(previous ship) js/{f} {u}' for f, i in old.items() for u in i['unknown']]
    added = {f: {n: [] for n in sorted(info[f]['exports'] - old[f]['exports'])} for f in now if f in old and info[f]['exports'] - old[f]['exports']}
    kinds = {f: _kinds(info[f]) for f in added}
    bad = []

    def use(m, n, where, ok):
        added[m][n].append(where + ('' if ok else ' (BREAKS)'))
        if not ok: bad.append(where)

    # ---- old code, new module ----
    local = lambda s: s.startswith('./') and '/' not in s[2:]   # a module in js/ (not three, not ../vendor/..)
    for f, i in old.items():
        for s, pairs in i['imports']:
            if not local(s): continue
            m = mod(s)
            if m not in info:
                bad.append(f'the previous ship\'s js/{f} imports {s}, which is gone'); continue
            for a, _ in pairs:
                if a not in info[m]['exports']: bad.append(f'the previous ship\'s js/{f} imports {{{a}}} from {s}, which this checkout no longer exports')
        for s, _ in i['defaults']:
            if mod(s) in info and 'default' not in info[mod(s)]['exports']: bad.append(f'the previous ship\'s js/{f} imports a default from {s}, which has none now')
        for s, names in i['reexports']:
            for a in names:
                if mod(s) in info and a not in info[mod(s)]['exports']: bad.append(f'the previous ship\'s js/{f} re-exports {{{a}}} from {s}, gone now')

    # ---- new code, old module: the bindings ----
    loose = set()
    for f, i in info.items():
        T = i['tokens']
        for s, pairs in i['imports']:
            for a, _ in pairs:
                if a in added.get(mod(s), {}): use(mod(s), a, f'js/{f} imports {{{a}}} from {s}', False)
        for s, _ in i['defaults']:
            if 'default' in added.get(mod(s), {}): use(mod(s), 'default', f'js/{f} imports the new default of {s}', False)
        for s, names in i['reexports']:
            for a in names:
                if a in added.get(mod(s), {}): use(mod(s), a, f'js/{f} re-exports {{{a}}} from {s}', False)
        binds = []   # (name, module, first, last, declared at)
        for s, ns in i['namespaces']:
            at = next(k for k in range(len(T)) if T[k].t == 'id' and T[k].v == ns)
            binds.append((ns, mod(s), 0, len(T) - 1, {at}))
        for s, b, k in i['dynamic']:
            m = mod(s)
            if isinstance(b, list):
                for a in b:
                    if a in added.get(m, {}): use(m, a, f'js/{f} line {T[k].line}: destructures {a} from import({s})', False)
                continue
            if not b:
                # import('x') whose module is passed on: x's new exports are checked by name wherever they are read
                loose.add(m); continue
            j = k + 7   # import ( 'x' ) . then ( <param> =>
            decl = j if T[j].t == 'id' else j + 1
            a = decl + 1 if _is(_tok(T, decl + 1), '=>') else decl + 2
            first, last = _arrow_body(T, a)
            binds.append((b, m, first, last, {decl}))
        # aliases: Y=B where B holds a module at that point, the whole of Y's file from then on (to a fixed point)
        grew = True
        while grew:
            grew = False
            for k in range(2, len(T) - 1):
                if not (T[k].t == 'id' and _is(T[k - 1], '=') and T[k - 2].t == 'id' and not _is(_tok(T, k - 3), '.') and not _is(_tok(T, k + 1), '.')
                        and not _is(_tok(T, k + 1), '?.') and T[k + 1].t == 'punct' and T[k + 1].v in (',', ';', ')', '}')):
                    continue
                src = next((x for x in binds if x[0] == T[k].v and x[2] <= k <= x[3]), None)
                if src and not any(x[0] == T[k - 2].v and x[4] == {k - 2} for x in binds):
                    binds.append((T[k - 2].v, src[1], 0, len(T) - 1, {k - 2})); grew = True
        guards = _guards(T)
        alias_at = {d for x in binds for d in x[4]}
        for k in range(len(T)):
            t = T[k]
            if t.t != 'id' or _is(_tok(T, k - 1), '.') or _is(_tok(T, k - 1), '?.'): continue
            hits = [x for x in binds if x[0] == t.v and x[2] <= k <= x[3]]
            if not hits and k not in alias_at:
                # a read of a new export of a loose import(): by name
                if (_is(_tok(T, k + 1), '.') or _is(_tok(T, k + 1), '?.')) and _tok(T, k + 2) is not None:
                    n = T[k + 2].v
                    m = next((x for x in loose if n in added.get(x, {}) and x != f), None)
                    if m: hits = [(t.v, m, 0, 0, set())]
                if not hits: continue
            if k in alias_at or (hits and k in hits[0][4]): continue
            m = hits[0][1]
            nx = _tok(T, k + 1)
            if (_is(nx, '.') or _is(nx, '?.')) and _tok(T, k + 2) is not None and T[k + 2].t == 'id':
                n = T[k + 2].v
                if n not in added.get(m, {}): continue
                if T[k - 1].t == 'id' and T[k - 1].v == 'typeof': continue   # the guard itself
                g = any(o == t.v and nm == n and a <= k <= z for o, nm, a, z in guards)
                data = kinds[m].get(n) == 'data' and _is(_tok(T, k + 3), '??') and _starts_operand(_tok(T, k - 1))
                why = ' guarded' if g else ' with a ?? fallback' if data else ''
                use(m, n, f'js/{f} line {t.line}: {t.v}.{n}' + (why or ' read with no typeof guard around it'
                                                               + (' and no ?? fallback' if kinds[m].get(n) == 'data' else '')), bool(why))
                continue
            if _is(nx, '=') and not _is(_tok(T, k + 2), '='): continue          # Y=... gives the alias a new value
            if T[k - 1].t == 'id' and T[k - 1].v in ('let', 'var', 'const'): continue
            if (_is(nx, '&&') or _is(nx, '?')) or (_is(nx, ')') and _is(_tok(T, k - 1), '(') and _tok(T, k - 2) is not None and _tok(T, k - 2).v == 'if') \
                    or _is(_tok(T, k - 1), '!'):
                continue   # tested for being there: AV&&AV.x(), if(AV), !AV
            if _is(_tok(T, k - 1), '=') and _tok(T, k - 2) is not None and T[k - 2].t == 'id' and nx is not None and nx.t == 'punct' and nx.v in (',', ';', ')', '}'):
                continue   # Y=NS: an alias, followed above
            # const {a}=NS
            if _is(_tok(T, k - 1), '=') and _is(_tok(T, k - 2), '}'):
                o = k - 2; d = 0
                while o >= 0:
                    if _is(T[o], '}'): d += 1
                    elif _is(T[o], '{'):
                        d -= 1
                        if d == 0: break
                    o -= 1
                for q in range(o + 1, k - 2):
                    if T[q].t == 'id' and T[q].v in added.get(m, {}) and (_is(T[q - 1], '{') or _is(T[q - 1], ',')):
                        use(m, T[q].v, f'js/{f} line {T[q].line}: destructures {T[q].v} from {t.v}', False)
                continue
            if not added.get(m): continue   # nothing new in it: whatever is read through it, the previous ship's copy has too
            bad.append(f'js/{f} line {t.line}: the module object {t.v} is used another way ({t.v}{nx.v if nx else ""}...), so its reads cannot be followed')
    return bad, added, unknown
