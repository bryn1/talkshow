"""Token-stream macro expansion for the M1 preprocessor (plan R7–R9, R14,
R15, R18, R19).

LINES (510 > 400): the expansion recursion, argument collection, prescan,
substitution and paste pass tokens through ONE cursor chain; splitting
would thread the same cursor through two files.

Concern: given pre-tokenized tokens + the macro table,
produce the fully expanded token list — `##` paste (result rescanned), `#`
stringify (prescan-exempt operand, whitespace runs collapse), GNU variadic
`...` spellings with `, ## __VA_ARGS__` comma-swallow, blue-paint self-
reference hiding, and the __LINE__/__FILE__/__COUNTER__/_Pragma/__has_attribute
builtin hooks fired at the USE SITE inside the rescan. No directives, no
files, no expression grammar. stdlib-only.

Oracle posture (gcc 11.4, probed this card): arguments of a plain parameter
are prescanned with a FRESH hidden set (F(F(1)) → 1+1+1); rescanning the
replacement list carries the hidden set (mutual cycles stop silently, the
identifier survives, exit 0 — test_paste/ga rows pin it); a paste operand is
used RAW (no prescan). A runaway (non-cyclic, doubling) expansion still
raises the §8 pp diagnostic.
"""
from __future__ import annotations

import re
from typing import Callable, Dict, List, Optional, Set

from blcc.lexer import DiagError

# One chunk: string | char | identifier | pp-number-ish | multi-char operator
# | whitespace | other. Multi-char operators stay ONE token so pp_eval sees
# '=='/'<<'/'&&' whole. Comments never reach here (pp strips them in pass 1,
# R21).
_CHUNK_RE = re.compile(
    r'"(?:\\.|[^"\\])*"?|\'(?:\\.|[^\'\\])*\'?'
    r"|[A-Za-z_][A-Za-z0-9_]*|[0-9][0-9A-Za-z_.]*|\s+"
    r"|<<=|>>=|\.\.\.|->|\+\+|--|<<|>>|&&|\|\||==|!=|<=|>=|\+=|-=|\*=|/="
    r"|%=|&=|\^=|\|=|##|.", re.S)

_ID_RE = re.compile(r"[A-Za-z_][A-Za-z0-9_]*$")
_MAX_EXPANSIONS = 4000000      # runaway (doubling) guard, not a depth cap
_IDENTISH = re.compile(r"^[A-Za-z0-9_.']")
_PASTE_SPLIT = re.compile(r"[A-Za-z_][A-Za-z0-9_]*|[0-9][0-9A-Za-z_.]*|.?$")


def tokenize(text: str) -> List[str]:
    return _CHUNK_RE.findall(text) or []


def is_ws(tok: str) -> bool:
    return tok.strip() == ""


def is_id(tok: str) -> bool:
    return bool(_ID_RE.match(tok))


class Macro:
    """One macro. kind: std | line | file | base | counter | date | time |
    hasattr | pragma. params None = object-like; variadic = tail exists;
    var_name = the name the tail tokens answer to (R15: `x...` names it,
    `...` spells it __VA_ARGS__)."""

    def __init__(self, name: str, body: List[str],
                 params: Optional[List[str]], variadic: bool = False,
                 kind: str = "std", builtin: bool = False,
                 var_name: str = "__VA_ARGS__"):
        self.name = name
        self.body = body
        self.params = params
        self.variadic = variadic
        self.var_name = var_name
        self.kind = kind
        self.builtin = builtin


def canon_attr(name: str) -> str:
    """gcc normalizes __x__, _x_, x to the same attribute name."""
    n = name
    while n.startswith("_") and n.endswith("_") and len(n) > 2:
        n = n[1:-1]
    return n


def escape_string(s: str) -> str:
    return '"' + s.replace("\\", "\\\\").replace('"', '\\"') + '"'


def decode_string(tok: str) -> str:
    """Decoded content of a str token: only \" \\ escapes decoded (the
    pragma text is re-emitted as bytes, not as C string values)."""
    body = tok[1:-1] if tok.startswith('"') and tok.endswith('"') else tok
    out: List[str] = []
    i = 0
    while i < len(body):
        c = body[i]
        if c == "\\" and i + 1 < len(body):
            e = body[i + 1]
            out.append({"n": "\n", "t": "\t", "\\": "\\", '"': '"'}.get(e,
                                                                  "\\" + e))
            i += 2
            continue
        out.append(c)
        i += 1
    return "".join(out)


class Expander:
    """Stateless per call except the shared __COUNTER__; one instance owns
    one translation unit's counter."""

    def __init__(self, macros: Dict[str, Macro], warn: Callable[[int, int, str], None],
                 counter: List[int], main_file: str, date: str, time: str,
                 emit_pragmas: bool):
        self.macros = macros
        self.warn = warn            # warn(line, col, message)
        self.counter = counter
        self.main_file = main_file
        self.date = date
        self.time = time
        self.emit_pragmas = emit_pragmas
        self._budget = [_MAX_EXPANSIONS]

    # -- public ---------------------------------------------------------------

    def expand(self, toks: List[str], path: str, line: int,
               more: Optional[Callable[[], bool]] = None,
               protect: bool = False) -> List[str]:
        self._budget[0] = _MAX_EXPANSIONS
        return self._expand(toks, set(), path, line, more, protect)

    # -- core recursion --------------------------------------------------------

    def _expand(self, toks: List[str], hidden: Set[str], path: str,
                line: int, more, protect: bool = False) -> List[str]:
        out: List[str] = []
        i, n = 0, len(toks)
        while i < n:
            t = toks[i]
            if protect and t == "defined" and not self.macros.get("defined"):
                out.append(t)
                i += 1
                j = i
                while j < n and is_ws(toks[j]):
                    out.append(toks[j])
                    j += 1
                if j < n and toks[j] == "(":
                    depth = 0
                    while j < n:
                        out.append(toks[j])
                        depth += toks[j] in "([{["
                        depth -= toks[j] in ")]}"
                        j += 1
                        if depth == 0:
                            break
                elif j < n:
                    out.append(toks[j])
                    j += 1
                i = j
                continue
            macro = self.macros.get(t) if is_id(t) else None
            if macro is None or t in hidden:
                out.append(t)
                i += 1
                continue
            self._budget[0] -= 1
            if self._budget[0] <= 0:
                raise DiagError("pp", path, line, 1,
                                "macro expansion limit exceeded (runaway "
                                "'#define')", "macro expansion")
            if macro.kind != "std":
                repl = self._builtin(macro, toks, i, path, line, more, hidden)
                if repl is None:            # not expandable right here
                    out.append(t)
                    i += 1
                    continue
                out.extend(repl)
                i = self._last_consumed
                continue
            if macro.params is None:        # object-like
                sub = self._expand(list(macro.body), hidden | {t}, path,
                                   line, more, protect)
                out.extend(sub)
                i += 1
                continue
            k = i + 1
            while k < n and is_ws(toks[k]):
                k += 1
            if not (k < n and toks[k] == "("):
                out.append(t)               # function-like name not invoked
                i += 1
                continue
            args, close = self._collect_args(toks, k, path, line, macro, more)
            args = self._check_args(args, macro, path, line)
            sub_raw = self._prescan_args(args, macro, path, line, more,
                                         protect)
            subst = self._substitute(macro, sub_raw, path, line)
            out.extend(self._expand(subst, hidden | {t}, path, line,
                             more, protect))
            i = close + 1
            n = len(toks)
        return out

    # -- builtin hooks (fire at the USE SITE, once per occurrence) -------------

    def _builtin(self, macro: Macro, toks: List[str], i: int, path: str,
                 line: int, more, hidden) -> Optional[List[str]]:
        kind = macro.kind
        if kind == "line":
            self._last_consumed = i + 1
            return [str(line)]
        if kind == "file":
            self._last_consumed = i + 1
            return [escape_string(path)]
        if kind == "base":
            self._last_consumed = i + 1
            return [escape_string(self.main_file)]
        if kind == "counter":
            self._last_consumed = i + 1
            tok = str(self.counter[0])
            self.counter[0] += 1
            return [tok]
        if kind == "date":
            self._last_consumed = i + 1
            return [escape_string(self.date)]
        if kind == "time":
            self._last_consumed = i + 1
            return [escape_string(self.time)]
        if kind == "hasattr":
            args, close = self._need_one_arg(toks, i, path, line, macro, more)
            self._last_consumed = close + 1
            if args is None:
                return None
            name = next((t for t in args if not is_ws(t)), None)
            if name is None or not is_id(name):
                self._last_consumed = i + 1
                return ["0"]
            from blcc.pp_predefines import HAS_ATTRIBUTE   # table lives there
            return ["1" if HAS_ATTRIBUTE.get(canon_attr(name)) == 1 else "0"]
        if kind == "pragma":
            args, close = self._need_one_arg(toks, i, path, line, macro, more)
            self._last_consumed = close + 1
            if args is None:
                return None
            args = self._expand(args, set(), path, line, more)  # R14: the
            # argument is FULLY EXPANDED, not stringified; the result must
            # be exactly one string-literal token.
            toks_a = [t for t in args if not is_ws(t)]
            if len(toks_a) != 1 or not toks_a[0].startswith('"'):
                self.warn(line, 1, "_Pragma requires a single string literal")
                return [""]              # consumed, emits nothing
            text = decode_string(toks_a[0])
            if not self.emit_pragmas:
                return [""]
            return tokenize("#pragma " + text)
        return None

    def _need_one_arg(self, toks, i, path, line, macro, more):
        k = i + 1
        n = len(toks)
        while k < n and is_ws(toks[k]):
            k += 1
        if not (k < n and toks[k] == "("):
            return None, i
        args_list, close = self._collect_args(toks, k, path, line, macro, more)
        if len(args_list) != 1:
            raise DiagError("pp", path, line, 1,
                            "macro '%s' takes 1 argument" % macro.name,
                            macro.name)
        return args_list[0], close

    # -- argument collection ----------------------------------------------------

    def _collect_args(self, toks: List[str], open_i: int, path: str,
                      line: int, macro: Macro, more):
        """Returns (list-of-arg-token-lists, index of the ')' token)."""
        groups: List[List[str]] = []
        group: List[str] = []
        depth = 0
        k = open_i
        n = len(toks)
        while True:
            if k >= n:
                if more and more():
                    n = len(toks)           # multi-line invocation (R2 spliced
                    continue                # logical line may still continue)
                raise DiagError("pp", path, line, 1,
                                "unterminated argument list for macro "
                                "'%s'" % macro.name, macro.name)
            t = toks[k]
            if t in "([{":
                depth += 1
                if depth == 1:
                    k += 1
                    continue
            elif t in ")]}":
                depth -= 1
                if depth == 0:
                    groups.append(group)
                    return groups, k
            elif t == "," and depth == 1:
                groups.append(group)
                group = []
                k += 1
                continue
            if depth >= 1:
                group.append(t)
            k += 1

    def _check_args(self, groups: List[List[str]], macro: Macro, path: str,
                    line: int) -> List[List[str]]:
        named = macro.params or []
        # F2 (GNU spelling `name(p..., x...)`): the NAMED variadic param
        # answers to the tail, so it is NOT a required argument — the call
        # needs only the non-variadic named params (mipi_dbi_command(dbi,
        # cmd, seq...) accepts mipi_dbi_command(dbi, 0x01); oracle).
        required = len(named) - (1 if (macro.variadic and
                                       macro.var_name in named) else 0)
        fixed = []
        for idx, g in enumerate(groups):
            # P2a (oracle stringify matrix): a variadic parameter answers to
            # ONE contiguous token range — the tail groups stay RAW here and
            # are flattened-with-commas + range-end trimmed in _substitute
            # (gcc keeps the source whitespace around the joining commas:
            # Q(a , b) -> "a , b", Q(a,b) -> "a,b", Q( ,) -> ","). Named
            # params keep their per-argument trim (S( a ) -> "a").
            tail = macro.variadic and idx >= required
            if not tail:
                while g and is_ws(g[0]):
                    g = g[1:]
                while g and is_ws(g[-1]):
                    g = g[:-1]
            fixed.append(g)
        if len(named) == 0 and len(fixed) == 1 and not fixed[0]:
            return []                      # zero-argument invocation() form
        if len(fixed) < required or (not macro.variadic and
                                       len(fixed) > required):
            raise DiagError("pp", path, line, 1,
                            "macro '%s' takes %s argument(s)" % (
                                macro.name, required if not macro.variadic
                                else "at least %d" % required), macro.name)
        return fixed

    # -- prescan (plain parameters only, fresh hidden set — oracle F(F(1))) ----

    def _prescan_args(self, args: List[List[str]], macro: Macro, path: str,
                      line: int, more, protect: bool = False) -> List[List[str]]:
        plain = self._param_usage(macro)
        out = []
        for idx, arg in enumerate(args):
            name = self._param_at(macro, idx)
            if name is not None and plain.get(name) == "plain":
                out.append(self._expand(arg, set(), path, line, more,
                                        protect))
            else:
                out.append(arg)
        return out

    @staticmethod
    def _param_at(macro: Macro, idx: int) -> Optional[str]:
        if macro.params is None:
            return None
        start = len(macro.params) - (1 if (macro.variadic and
                                           macro.var_name in macro.params)
                                      else 0)
        if idx < start:
            return macro.params[idx]
        if macro.variadic and idx >= start:
            return macro.var_name
        return None

    @staticmethod
    def _param_usage(macro: Macro) -> Dict[str, str]:
        """param -> 'plain' | 'raw' (a #/## operand is raw: never prescanned)."""
        names = set(macro.params or [])
        if macro.variadic:
            names.add(macro.var_name)
        usage: Dict[str, str] = {}
        body = macro.body
        for j, t in enumerate(body):
            if t == "#":
                nxt = next((b for b in body[j + 1:] if not is_ws(b)), None)
                if nxt in names:
                    usage[nxt] = "raw"
            elif t == "##":
                for side in (reversed(body[:j]), body[j + 1:]):
                    nxt = next((b for b in side if not is_ws(b)), None)
                    if nxt in names:
                        usage[nxt] = "raw"
            elif t in names:
                usage.setdefault(t, "plain")
        return usage

    # -- substitution + paste ----------------------------------------------------

    def _substitute(self, macro: Macro, args: List[List[str]], path: str,
                    line: int) -> List[str]:
        mapping: Dict[str, List[str]] = {}
        named = macro.params or []
        start = len(named) - (1 if (macro.variadic and
                                    macro.var_name in named) else 0)
        for idx, arg in enumerate(args[:start]):
            mapping[named[idx]] = arg
        if macro.variadic:                        # the tail ALWAYS answers,
            tail = args[start:]                   # even when the call is
            rest: List[str] = list(tail[0]) if tail else []
            for arg in tail[1:]:                  # ONE contiguous range:
                rest.append(",")                  # groups rejoined by index,
                rest.extend(arg)                  # ws trimmed at the ENDS
            while rest and is_ws(rest[0]):        # only (oracle, P2a)
                rest = rest[1:]
            while rest and is_ws(rest[-1]):
                rest = rest[:-1]
            mapping[macro.var_name] = rest
        raw_names = {n for n, u in self._param_usage(macro).items()
                     if u == "raw"}
        out: List[str] = []
        body = list(macro.body)        # local copy: paste splices back into it
        i, n = 0, len(body)
        while i < n:
            t = body[i]
            if t == "#" and i + 1 < n:
                j = i + 1
                while j < n and is_ws(body[j]):
                    j += 1
                if j < n and body[j] in mapping and body[j] in raw_names:
                    out.append(_stringify(mapping[body[j]]))
                    i = j + 1
                    continue
            if t == "##":
                i = self._paste(out, body, i, mapping, path, line)
                n = len(body)
                continue
            if t in mapping:
                out.extend(mapping[t])
                i += 1
                continue
            out.append(t)
            i += 1
        return [t for t in out if t != ""]

    def _paste(self, out: List[str], body: List[str], i: int,
                mapping: Dict[str, List[str]], path: str, line: int) -> int:
        while out and is_ws(out[-1]):
            out.pop()
        left = out.pop() if out else None
        j = i + 1
        while j < len(body) and is_ws(body[j]):
            j += 1
        # collapse a duplicated '## ##' (gcc joins the operands instead)
        if j < len(body) and body[j] == "##":
            return self._paste(out, body, j, mapping, path, line)
        right: Optional[str] = None
        if j < len(body):
            if body[j] in mapping and mapping[body[j]] and not is_ws(
                    mapping[body[j]][0]):
                right = mapping[body[j]][0]
                tail = mapping[body[j]][1:]
                # NO mapping shrink here: the parameter's FULL argument must
                # survive for every later occurrence/paste of the same
                # parameter in this body (verdict-c2 F-2, MC 12436 — the old
                # `mapping[p] = tail` silently turned asm("rsp") into
                # asm("r") and killed the __ATTR_RW chain). The operand's
                # REMAINING tokens stay in the stream via the body splice
                # (R8: `## __VA_ARGS__` pastes only the first, tail follows)
                body[j:j + 1] = tail
            elif body[j] in mapping:       # empty operand for this paste
                j += 1
            else:
                right = body[j]
                j += 1
        if left == "," and right is None:
            return j                       # GNU comma-swallow (R8)
        if left is not None and right is not None:
            joined = left + right
            if _IDENTISH.match(left) and _IDENTISH.match(right) \
                    and not _PASTE_SPLIT.match(joined):
                self.warn(line, 1,
                          "pasting '%s' and '%s' does not give a valid "
                          "preprocessing token" % (left, right))
            out.append(joined)
        elif right is not None:
            out.append(right)              # empty left operand: paste no-op
        elif left is not None:
            out.append(left)
        return j


def _stringify(arg: List[str]) -> str:
    parts: List[str] = []
    ws = False
    for t in arg:
        if is_ws(t):
            ws = parts
            continue
        if parts and ws:
            parts.append(" ")
        if t.startswith('"'):
            parts.append(decode_string_raw(t))   # quotes escaped, not re-wrapped
        else:
            parts.append(t)
        ws = False
    return '"' + "".join(parts) + '"'


def decode_string_raw(tok: str) -> str:
    """Stringify keeps the operand's bytes but escapes quote/backslash — the
    WHOLE token including its own quotes (gcc: `"a"` stringifies to `"\"a\""`)."""
    out: List[str] = []
    for c in tok:
        if c in '"\\':
            out.append("\\")
        out.append(c)
    return "".join(out)
