"""A small, strict reader of this project's ES modules, for tests/cache_mix.py (not a suite of its own).

tokenize(src) splits JavaScript into tokens (names, strings, template literals with their ${...} parts, numbers, regular
expressions, punctuation), skipping comments. modinfo(src) reads, at the top level of a module, every import and export
it recognises, and lists anything that looks like one but is not a form it knows, so a caller can fail on it instead of
missing it. Forms known: import 'x'; import {a, b as c} from 'x'; import * as ns from 'x'; import d from 'x' (with ,{..}
or , * as ns); export const|let|var a=.., b=..; export [async] function[*] f; export class C; export {a, b as c};
export {a} from 'x'; and import('x') anywhere (with the name its .then(m=>..) gives the module, and plain aliases X=m).
Not known, so reported: export default, export *, destructuring in an export, import.meta, anything else after
import/export."""
import re

PUNCT = sorted(['>>>=', '...', '===', '!==', '**=', '<<=', '>>=', '>>>', '&&=', '||=', '??=', '=>', '==', '!=', '<=', '>=', '&&', '||', '??', '?.', '++', '--',
                '+=', '-=', '*=', '/=', '%=', '&=', '|=', '^=', '**', '<<', '>>', '{', '}', '(', ')', '[', ']', ';', ',', '<', '>', '+', '-', '*', '/', '%',
                '&', '|', '^', '!', '~', '?', ':', '=', '.', '@', '#'], key=len, reverse=True)
REGEX_BEFORE_WORDS = {'return', 'typeof', 'case', 'do', 'else', 'in', 'of', 'new', 'delete', 'void', 'throw', 'instanceof', 'yield', 'await'}
IDENT = re.compile(r'[A-Za-z_$ -￿][\w$ -￿]*')
NUM = re.compile(r'0[xXoObB][\da-fA-F_]+n?|(?:\d[\d_]*\.?[\d_]*|\.\d[\d_]*)(?:[eE][+-]?\d+)?n?')


class Tok:
    __slots__ = ('t', 'v', 'pos', 'line')

    def __init__(self, t, v, pos, line):
        self.t, self.v, self.pos, self.line = t, v, pos, line

    def __repr__(self):
        return f'{self.t}:{self.v!r}'


def tokenize(src, base=0):
    out, i, n = [], 0, len(src)

    def line_of(p):
        return src.count('\n', 0, p) + 1
    while i < n:
        c = src[i]
        if c in ' \t\r\n ﻿':
            i += 1; continue
        if src.startswith('//', i):
            j = src.find('\n', i); i = n if j < 0 else j; continue
        if src.startswith('/*', i):
            j = src.find('*/', i + 2)
            if j < 0: raise SyntaxError(f'unclosed comment at {base + i}')
            i = j + 2; continue
        if c in '"\'':
            j = i + 1
            while j < n and src[j] != c:
                if src[j] == '\\': j += 1
                elif src[j] == '\n': raise SyntaxError(f'line break in a string at {base + i}')
                j += 1
            if j >= n: raise SyntaxError(f'unclosed string at {base + i}')
            out.append(Tok('str', src[i + 1:j], base + i, line_of(i))); i = j + 1; continue
        if c == '`':
            j, parts = i + 1, []
            while True:
                if j >= n: raise SyntaxError(f'unclosed template at {base + i}')
                if src[j] == '\\': j += 2; continue
                if src[j] == '`': break
                if src.startswith('${', j):
                    depth, k = 1, j + 2
                    # find the matching }, minding strings, templates and comments inside
                    inner_start = k
                    while depth:
                        if k >= n: raise SyntaxError(f'unclosed ${{ in a template at {base + j}')
                        ch = src[k]
                        if ch in '"\'`':
                            k += _literal_len(src, k)   # a string or template inside: skipped whole
                            continue
                        if src.startswith('//', k):
                            e = src.find('\n', k); k = n if e < 0 else e; continue
                        if src.startswith('/*', k):
                            e = src.find('*/', k + 2); k = e + 2; continue
                        if ch == '{': depth += 1
                        elif ch == '}': depth -= 1
                        k += 1
                    parts.extend(tokenize(src[inner_start:k - 1], base + inner_start))
                    j = k; continue
                j += 1
            t = Tok('tmpl', src[i + 1:j], base + i, line_of(i)); out.append(t); out.extend(parts); i = j + 1; continue
        if c == '/':
            prev = out[-1] if out else None
            if prev is None or (prev.t == 'punct' and prev.v not in (')', ']', '}', '++', '--')) or (prev.t == 'id' and prev.v in REGEX_BEFORE_WORDS):
                j, cls = i + 1, False
                while j < n:
                    ch = src[j]
                    if ch == '\\': j += 2; continue
                    if ch == '\n': raise SyntaxError(f'line break in a regular expression at {base + i}')
                    if ch == '[': cls = True
                    elif ch == ']': cls = False
                    elif ch == '/' and not cls: break
                    j += 1
                j += 1
                while j < n and (src[j].isalnum() or src[j] == '_'): j += 1
                out.append(Tok('regex', src[i:j], base + i, line_of(i))); i = j; continue
        m = IDENT.match(src, i)
        if m:
            out.append(Tok('id', m.group(), base + i, line_of(i))); i = m.end(); continue
        m = NUM.match(src, i)
        if m and m.group():
            out.append(Tok('num', m.group(), base + i, line_of(i))); i = m.end(); continue
        for p in PUNCT:
            if src.startswith(p, i):
                out.append(Tok('punct', p, base + i, line_of(i))); i += len(p); break
        else:
            raise SyntaxError(f'unexpected character {c!r} at {base + i}')
    return out


def _literal_len(src, k):
    """the length of the string or template literal that starts at src[k]"""
    q, j = src[k], k + 1
    if q == '`':
        depth = 0
        while j < len(src):
            if src[j] == '\\': j += 2; continue
            if src.startswith('${', j): depth += 1; j += 2; continue
            if src[j] == '}' and depth: depth -= 1; j += 1; continue
            if src[j] == '`' and not depth: return j + 1 - k
            j += 1
        raise SyntaxError('unclosed template')
    while j < len(src):
        if src[j] == '\\': j += 2; continue
        if src[j] == q: return j + 1 - k
        j += 1
    raise SyntaxError('unclosed string')


def _is(t, v, typ='punct'):
    return t is not None and t.t == typ and t.v == v


def modinfo(src):
    """{'exports': {name}, 'imports': [(source, [(imported, local)])], 'namespaces': [(source, local)],
        'defaults': [(source, local)], 'dynamic': [(source, binding or None, token index)], 'reexports': [(source, [names])],
        'unknown': [text], 'tokens': [...]}"""
    T = tokenize(src)
    info = {'exports': set(), 'imports': [], 'namespaces': [], 'defaults': [], 'dynamic': [], 'reexports': [], 'unknown': [], 'tokens': T}
    at = lambda k: T[k] if 0 <= k < len(T) else None
    depth = 0

    def specs(k):
        """{ a, b as c } from k at '{': the pairs and the index after '}'"""
        pairs, k = [], k + 1
        while not _is(at(k), '}'):
            a = at(k)
            if a is None or a.t not in ('id', 'str'): raise ValueError('a list it does not know')
            b = a.v; k += 1
            if at(k) is not None and at(k).t == 'id' and at(k).v == 'as':
                if at(k + 1) is None or at(k + 1).t not in ('id', 'str'): raise ValueError('as without a name')
                b = at(k + 1).v; k += 2
            pairs.append((a.v, b))
            if _is(at(k), ','): k += 1
            elif not _is(at(k), '}'): raise ValueError('a list it does not know')
        return pairs, k + 1

    k = 0
    while k < len(T):
        t = T[k]
        if t.t == 'punct' and t.v in '([{': depth += 1
        elif t.t == 'punct' and t.v in ')]}': depth -= 1
        prev = at(k - 1)
        member = _is(prev, '.') or _is(prev, '?.')
        if t.t == 'id' and t.v == 'import' and not member:
            nx = at(k + 1)
            if _is(nx, '('):
                s = at(k + 2)
                if s is None or s.t != 'str' or not _is(at(k + 3), ')'):
                    info['unknown'].append(f'line {t.line}: import( with something other than one plain string')
                else:
                    info['dynamic'].append((s.v, _then_binding(T, k + 4), k))
                k += 1; continue
            if _is(nx, '.'):
                info['unknown'].append(f'line {t.line}: import.meta'); k += 1; continue
            if depth != 0:
                info['unknown'].append(f'line {t.line}: import inside a block'); k += 1; continue
            try:
                if nx is not None and nx.t == 'str':
                    info['imports'].append((nx.v, [])); k += 2; continue
                pairs, ns, dflt, j = [], None, None, k + 1
                if at(j) is not None and at(j).t == 'id' and at(j).v not in ('from',):
                    dflt = at(j).v; j += 1
                    if _is(at(j), ','): j += 1
                if _is(at(j), '{'):
                    pairs, j = specs(j)
                elif _is(at(j), '*') and at(j + 1) is not None and at(j + 1).v == 'as' and at(j + 2) is not None and at(j + 2).t == 'id':
                    ns = at(j + 2).v; j += 3
                if not (at(j) is not None and at(j).t == 'id' and at(j).v == 'from' and at(j + 1) is not None and at(j + 1).t == 'str'):
                    raise ValueError('no from')
                src_ = at(j + 1).v
                info['imports'].append((src_, pairs))
                if ns: info['namespaces'].append((src_, ns))
                if dflt: info['defaults'].append((src_, dflt))
                k = j + 2; continue
            except ValueError as e:
                info['unknown'].append(f'line {t.line}: an import it does not know ({e})'); k += 1; continue
        if t.t == 'id' and t.v == 'export' and not member:
            if depth != 0:
                info['unknown'].append(f'line {t.line}: export inside a block'); k += 1; continue
            nx = at(k + 1)
            try:
                if nx is not None and nx.t == 'id' and nx.v in ('const', 'let', 'var'):
                    j = k + 2
                    while True:
                        nm = at(j)
                        if nm is None or nm.t != 'id': raise ValueError('destructuring or no name after ' + nx.v)
                        info['exports'].add(nm.v); j += 1
                        d = 0   # skip the initializer to the next declarator or the end of the statement
                        while at(j) is not None:
                            x = at(j)
                            if x.t == 'punct' and x.v in '([{': d += 1
                            elif x.t == 'punct' and x.v in ')]}': d -= 1
                            elif d == 0 and x.t == 'punct' and x.v in (',', ';'): break
                            elif d == 0 and x.t == 'id' and x.v in ('export', 'import') and not _is(at(j - 1), '.'): break
                            j += 1
                        if _is(at(j), ','): j += 1; continue
                        break
                    k = j; continue
                if nx is not None and nx.t == 'id' and nx.v in ('function', 'async', 'class'):
                    j = k + 1
                    if at(j).v == 'async': j += 1
                    if at(j) is None or at(j).v not in ('function', 'class'): raise ValueError('async without function')
                    j += 1
                    if _is(at(j), '*'): j += 1
                    if at(j) is None or at(j).t != 'id': raise ValueError('no name')
                    info['exports'].add(at(j).v); k = j + 1; continue
                if _is(nx, '{'):
                    pairs, j = specs(k + 1)
                    names = [b for a, b in pairs]
                    if at(j) is not None and at(j).t == 'id' and at(j).v == 'from':
                        if at(j + 1) is None or at(j + 1).t != 'str': raise ValueError('from without a string')
                        info['reexports'].append((at(j + 1).v, [a for a, b in pairs])); j += 2
                    info['exports'].update(names); k = j; continue
                raise ValueError('export ' + (nx.v if nx else 'at the end'))
            except ValueError as e:
                info['unknown'].append(f'line {t.line}: an export it does not know ({e})'); k += 1; continue
        k += 1
    return info


def _then_binding(T, k):
    """after import('x'): the parameter of .then(p=>..) or .then((p)=>..), or of .then(({a,b})=>..) as a list"""
    at = lambda i: T[i] if 0 <= i < len(T) else None
    if not (_is(at(k), '.') and at(k + 1) is not None and at(k + 1).v == 'then' and _is(at(k + 2), '(')):
        return None
    j = k + 3
    if at(j) is not None and at(j).t == 'id' and _is(at(j + 1), '=>'): return at(j).v
    if _is(at(j), '(') and at(j + 1) is not None and at(j + 1).t == 'id' and _is(at(j + 2), ')'): return at(j + 1).v
    if _is(at(j), '(') and _is(at(j + 1), '{'):
        names, i = [], j + 2
        while at(i) is not None and not _is(at(i), '}'):
            if at(i).t == 'id': names.append(at(i).v)
            i += 1
        return names
    return None
