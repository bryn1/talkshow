"""Token-stream macro expansion for the M1 preprocessor (plan R7–R9, R14,
R15, R18, R19).

LINES (621 > 400): the expansion recursion, argument collection, prescan,
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
are prescanned with a FRESH hidden set (F(F(1)) → 1+1+1); the replacement
list is spliced into the stream and rescanned IN PLACE, blue paint carried
PER TOKEN (mutual cycles stop silently, the identifier survives, exit 0 —
test_paste/ga rows pin it; a name PRODUCED by an expansion is a fresh token
with the producing chain's extras, never painted by them — F-3/MC 12436);
a paste operand is used RAW (no prescan). A runaway (non-cyclic, doubling)
expansion still raises the §8 pp diagnostic.
"""
from __future__ import annotations

import re
from typing import Callable, Dict, FrozenSet, List, Optional, Set, Tuple, Union

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
_PASTE_ONE = re.compile(r"[A-Za-z_][A-Za-z0-9_]*|[0-9][0-9A-Za-z_.]*")
# A paste join that is ONE valid token without being an identifier/pp-number:
# the multi-char operators and the leading-dot pp-number. gcc 11.4 joins
# `&`+`&` to `&&`, `.`+`4` to `.4`, and ERRORS on every join that is not a
# single token (`+`+`-`, `%`+`-`, `.`+`.`, `e`+`+`, `x`+string) — matrix
# measured this card, MC 12454.
_PASTE_JOIN = re.compile(
    r"<<=|>>=|\.\.\.|->|\+\+|--|<<|>>|&&|\|\||==|!=|<=|>=|\+=|-=|\*=|/="
    r"|\.[0-9][0-9A-Za-z_.]*", re.S)


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


_EMPTY = frozenset()

Item = Union[str, Tuple[str, frozenset]]


def plain(item: Item) -> str:
    """The token text of a stream item (items carry per-token hidden extras
    as (tok, extras) tuples — see Expander._expand, F-3/MC 12436)."""
    return item if isinstance(item, str) else item[0]


def item_ws(item: Item) -> bool:
    return is_ws(plain(item))


def _wrap(items: List[Item], extras: Set[str]) -> List[Item]:
    """Blue-paint the produced tokens: every token of a replacement list
    becomes (token, extras), hidden ONLY against those macro names — the
    macro being expanded plus everything already hidden at its use site.
    The OUTER continuation is never wrapped (F-3/MC 12436: the old
    set-scoped hiding is exactly what made the hide-then-emit boundary
    swallow invocations of expansion-produced names)."""
    ex = frozenset(extras)
    return [(plain(it), (it[1] if isinstance(it, tuple) else _EMPTY) | ex)
            for it in items]


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
               more: Optional[Callable[[List], bool]] = None,
               protect: bool = False) -> List[str]:
        self._budget[0] = _MAX_EXPANSIONS
        return [plain(it) for it in
                self._expand_items(toks, set(), path, line, more, protect)]

    # -- core recursion --------------------------------------------------------

    def _expand_items(self, toks: List[Item], hidden: Set[str], path: str,
                      line: int, more, protect: bool = False) -> List[Item]:
        """Scan `toks` to exhaustion. A stream item is a plain token (blue
        against the region `hidden` set) or a (token, extras) tuple —
        extras are the macro names THIS token may never answer to. An
        expansion SPLICES its replacement list into the stream and keeps
        scanning from the replacement head (C's re-scan model): a macro
        name PRODUCED by an expansion — the object-like alias
        `#define cpu_to_le16 __cpu_to_le16` whose call must then expand,
        or a paste-built invocation head CAT(ID, 4) -> ID4(...) — sees the
        following '(' on the next step (verdict-c2 F-3, MC 12436: the old
        emit-then-advance boundary emitted those calls UN-expanded,
        silently). Blue paint hides only the macros named in a token's
        extras, never a name merely produced by their bodies, so the
        oracle's termination posture (identifier survives, rc 0) holds. The
        result keeps its ITEMS: the argument-prescan boundary must carry the
        produced tokens' extras into the substituted argument, or a
        self-referential macro (`#define inline inline __gnu_inline
        __inline_maybe_unused notrace`, compiler_types.h:144) re-expands the
        keyword it produced at EVERY substitution site and SILENTLY doubles
        its tail — the mm/interval_tree.c 72-token divergence (MC 12438).
        The public expand() is the flattening boundary."""
        out: List[Item] = []
        i, n = 0, len(toks)
        while i < n:
            item = toks[i]
            if isinstance(item, str):
                t, hid = item, hidden
            else:
                t, hid = item[0], hidden | item[1]
            if protect and t == "defined" and not self.macros.get("defined"):
                out.append(item)
                i += 1
                j = i
                while j < n and is_ws(plain(toks[j])):
                    out.append(toks[j])
                    j += 1
                if j < n and plain(toks[j]) == "(":
                    depth = 0
                    while j < n:
                        out.append(toks[j])
                        pt = plain(toks[j])
                        depth += pt in "([{"
                        depth -= pt in ")]}"
                        j += 1
                        if depth == 0:
                            break
                elif j < n:
                    out.append(toks[j])
                    j += 1
                i = j
                continue
            macro = self.macros.get(t) if is_id(t) else None
            if macro is None or t in hid:
                out.append(item)            # ITEM survives, not just the
                i += 1                      # text (MC 12438: flattening here
                continue                    # dropped the blue paint emitted
            self._budget[0] -= 1            # by every splice)
            if self._budget[0] <= 0:
                raise DiagError("pp", path, line, 1,
                                "macro expansion limit exceeded (runaway "
                                "'#define')", "macro expansion")
            if macro.kind != "std":
                repl = self._builtin(macro, toks, i, path, line, more, hid)
                if repl is None:            # not expandable right here
                    out.append(item)
                    i += 1
                    continue
                out.extend(repl)
                i = self._last_consumed
                continue
            if macro.params is None:        # object-like: ONE substitution
                subst = self._substitute(macro, [], path, line)
                # (and paste) pass with an EMPTY mapping, then splice + rescan
                # (C11 6.10.3.4: `##` in an object-like body joins the RAW
                # body tokens BEFORE the rescan — the old bare splice left
                # `X ## Y` for the rescan, which then prescanned the operands
                # and never joined them: verdict-c3 F-A, MC 12454).
                toks = _wrap(subst, hid | {t}) + toks[i + 1:]
                i, n = 0, len(toks)
                continue
            k = i + 1
            while k < n and is_ws(plain(toks[k])):
                k += 1
            if not (k < n and plain(toks[k]) == "("):
                out.append(item)            # function-like name not invoked
                i += 1
                continue
            args, close = self._collect_args(toks, k, path, line, macro, more)
            args = self._check_args(args, macro, path, line)
            sub_raw = self._prescan_args(args, macro, path, line, more,
                                         protect)
            subst = self._substitute(macro, sub_raw, path, line)
            toks = _wrap(subst, hid | {t}) + toks[close + 1:]
            i, n = 0, len(toks)
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
            name = next((plain(t) for t in args if not is_ws(plain(t))),
                        None)
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
            args = [plain(it) for it in
                    self._expand_items(args, set(), path, line, more)
                    ]                               # R14: the
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
        while k < n and is_ws(plain(toks[k])):
            k += 1
        if not (k < n and plain(toks[k]) == "("):
            return None, i
        args_list, close = self._collect_args(toks, k, path, line, macro, more)
        if len(args_list) != 1:
            raise DiagError("pp", path, line, 1,
                            "macro '%s' takes 1 argument" % macro.name,
                            macro.name)
        return args_list[0], close

    # -- argument collection ----------------------------------------------------

    def _collect_args(self, toks: List[Item], open_i: int, path: str,
                      line: int, macro: Macro, more):
        """Returns (list-of-arg-item-lists, index of the ')' token). Items
        (with their blue-paint extras) flow into the argument lists; the
        continuation callback appends further logical lines to THIS stream
        (`more(dst)`), so a splice that re-bound the list keeps working."""
        groups: List[List[Item]] = []
        group: List[Item] = []
        depth = 0
        k = open_i
        n = len(toks)
        while True:
            if k >= n:
                if more and more(toks):
                    n = len(toks)           # multi-line invocation (R2 spliced
                    continue                # logical line may still continue)
                raise DiagError("pp", path, line, 1,
                                "unterminated argument list for macro "
                                "'%s'" % macro.name, macro.name)
            t = plain(toks[k])
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
                group.append(toks[k])
            k += 1

    def _check_args(self, groups: List[List[Item]], macro: Macro, path: str,
                    line: int) -> List[List[Item]]:
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
                while g and is_ws(plain(g[0])):
                    g = g[1:]
                while g and is_ws(plain(g[-1])):
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

    def _prescan_args(self, args: List[List[Item]], macro: Macro, path: str,
                      line: int, more, protect: bool = False
                      ) -> List[List[Item]]:
        usage = self._param_usage(macro)
        out = []
        for idx, arg in enumerate(args):
            name = self._param_at(macro, idx)
            if name is not None and usage.get(name) == "plain":
                # ITEMS SURVIVE the prescan boundary (MC 12438): the
                # blue-paint extras of produced tokens must reach the
                # substitution-site rescan.
                out.append(self._expand_items(arg, set(), path, line, more,
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

    def _substitute(self, macro: Macro, args: List[List[Item]], path: str,
                    line: int) -> List[Item]:
        mapping: Dict[str, List[Item]] = {}
        named = macro.params or []
        start = len(named) - (1 if (macro.variadic and
                                    macro.var_name in named) else 0)
        for idx, arg in enumerate(args[:start]):
            mapping[named[idx]] = arg
        if macro.variadic:                        # the tail ALWAYS answers,
            tail = args[start:]                   # even when the call is
            rest: List[Item] = list(tail[0]) if tail else []
            for arg in tail[1:]:                  # ONE contiguous range:
                rest.append(",")                  # groups rejoined by index,
                rest.extend(arg)                  # ws trimmed at the ENDS
            while rest and is_ws(plain(rest[0])):  # only (oracle, P2a)
                rest = rest[1:]
            while rest and is_ws(plain(rest[-1])):
                rest = rest[:-1]
            mapping[macro.var_name] = rest
        raw_names = {n for n, u in self._param_usage(macro).items()
                     if u == "raw"}
        out: List[Item] = []
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
                i = self._paste(out, body, i, mapping, macro, path, line)
                n = len(body)
                continue
            if t in mapping:
                out.extend(mapping[t])
                i += 1
                continue
            out.append(t)
            i += 1
        return [t for t in out if t != ""]

    def _paste(self, out: List[Item], body: List[Item], i: int,
                mapping: Dict[str, List[Item]], macro: Macro, path: str,
                line: int) -> int:
        while out and is_ws(plain(out[-1])):
            out.pop()
        left = out.pop() if out else None          # Item | None
        j = i + 1
        while j < len(body) and is_ws(plain(body[j])):
            j += 1
        # collapse a duplicated '## ##' (gcc joins the operands instead): the
        # popped left goes BACK so the collapsed cursor pastes against the
        # SAME left operand (`X## ##Y` -> XY, oracle-measured, MC 12454).
        if j < len(body) and plain(body[j]) == "##":
            if left is not None:
                out.append(left)
            return self._paste(out, body, j, mapping, macro, path, line)
        right: Optional[str] = None
        tail: List[Item] = []
        variadic_operand = False
        if j < len(body):
            if body[j] in mapping and mapping[body[j]] and not is_ws(
                    plain(mapping[body[j]][0])):
                right = plain(mapping[body[j]][0])
                tail = mapping[body[j]][1:]
                variadic_operand = (macro.variadic and
                                    body[j] == macro.var_name)
                # NO mapping shrink here: the parameter's FULL argument must
                # survive for every later occurrence/paste of the same
                # parameter in this body (verdict-c2 F-2, MC 12436 — the old
                # `mapping[p] = tail` silently turned asm("rsp") into
                # asm("r") and killed the __ATTR_RW chain). The operand's
                # REMAINING tokens are emitted RAW right here (below) — they
                # are ARGUMENT text, and gcc never re-substitutes parameter
                # names inside it: `#define e(f, a...) p(f, ##a)` called as
                # e(fmt, ..., f->num) must keep the caller's `f`, not expand
                # it to the fmt argument again (block/partitions/ldm.c,
                # silent, MC 12436 sweep).
                j += 1                           # continue PAST the param
            elif body[j] in mapping:       # empty operand for this paste
                j += 1
            else:
                right = plain(body[j])
                j += 1
        if left is not None and plain(left) == "," and right is None:
            return j                       # GNU comma-swallow (R8)
        if left is not None and right is not None:
            joined = plain(left) + right
            if _PASTE_ONE.fullmatch(joined) or _PASTE_JOIN.fullmatch(joined):
                out.append(joined)
            elif plain(left) == "," and variadic_operand:
                # GNU `, ## __VA_ARGS__` with a NON-empty tail: the comma
                # swallower suppresses the paste and gcc emits the TWO
                # tokens with no diagnostic (rmwcc.h COUNT_LAST shape, 1309
                # sites in linux-5.10, rc 0; the same `,`+token paste
                # through a PLAIN parameter IS an error — measured pair,
                # MC 12454).
                out.append(left)
                out.append(right)
            else:
                # C11 6.10.3.4p4: a paste that yields no valid preprocessing
                # token is UB, and gcc 11.4's posture is LOUD: an ERROR
                # (rc != 0) naming the operands. Matrix measured this card:
                # `%`+`-`, `+`+`-`, `%`+`%`, `1`+`+`, `e`+`+`, `.`+`.`,
                # ident+string, string+ident, plain `,`+token, token+`,`
                # ALL error; every single-token join stays quiet.
                raise DiagError(
                    "pp", path, line, 1,
                    "pasting '%s' and '%s' does not give a valid "
                    "preprocessing token" % (plain(left), right),
                    "macro paste")
        elif right is not None:
            out.append(right)              # empty left operand: paste no-op
        elif left is not None:
            out.append(left)
        if tail:
            out.extend(tail)               # raw argument remainder (above)
        return j


def _stringify(arg: List[Item]) -> str:
    parts: List[str] = []
    ws = False
    for item in arg:
        t = plain(item)
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
