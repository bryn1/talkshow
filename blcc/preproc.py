"""M1 GCC-compatible preprocessor: directive dispatch & source bookkeeping
(plan R1, R2, R4, R10–R14, R17, R20, R21).

LINES reason (562 > 400): directive dispatch is ONE concern — the #if-conditional
stack, #line origin state and include search must share the per-file state
machine; splitting would duplicate that state across files. The M4 W4
depfile writer (plan §4.4) rides THIS machine on purpose: the include
event list (self.deps) is recorded inside _include/_process, where the
resolver already spells and opens the file — no second include walk (the
rendering half lives in blcc/depfile.py, its own module). MC 12775
split the pass-0/1 text mechanics out to blcc/pp_text.py and the
include-search law to blcc/pp_include.py (IncludeMixin) — both
MOVED VERBATIM; the per-file state machine below stays one home.

Pass order per plan §2: pass-0 line splice (backslash-newline, keeping a
(file,line) origin map) BEFORE comment strip; directive dispatch on logical
lines; conditionals as a stack driven by pp_eval; include search order with
guarded REOPEN semantics (R20 + verdict-c2 F-1, MC 12436: a file already on
the ACTIVE include stack is re-opened exactly once — gcc does the same and
the guard skips the body, so guarded re-entrant chains are NORMAL; a SECOND
re-entry is a true cycle and stays loud; the recursion depth cap bounds
runaways); #line
origin renumber; #pragma record-and-ignore (passed through ONLY in -E mode,
where gcc passes them through too); #error is a §8 pp diagnostic, #warning
the §8 warning tier (stderr, exit code unaffected). Expansion itself is
delegated to pp_expand; this file knows no expression grammar. Output is
List[SourceLine] so parser/lexer are untouched. stdlib-only.
"""
from __future__ import annotations

import os
import re
import time
from typing import Dict, List, Optional, Tuple

from blcc.lexer import DiagError, SourceLine
from blcc.pp_expand import (Expander, Macro, is_id, is_ws, tokenize)
from blcc.pp_include import IncludeMixin
from blcc.pp_text import (_NAME_RE, _emit_join,
                            _merge_id_runs, _spell,
                            _splice, _strip_comments)
from blcc.pp_predefines import builtins
from blcc import pp_eval



class PpOpts:
    """Parsed CLI preprocessing surface (R17) — built by driver._parse_args."""

    def __init__(self):
        self.includes_dir: List[str] = []      # -I, argv order
        self.isystem: List[str] = []           # -isystem, searched after -I
        self.preinclude: List[str] = []        # -include, in order
        self.du: List[Tuple[str, str, Optional[str]]] = []   # -D/-U ordered
        self.std = "gnu17"
        self.emit_pragmas = False              # True only in -E mode


class Preprocessor(IncludeMixin):
    def __init__(self, opts: Optional[PpOpts] = None,
                 warn_out=None):
        self.opts = opts or PpOpts()
        self.defs: Dict[str, Macro] = builtins(self.opts.std)
        self.out: List[SourceLine] = []
        self.warnings: List[str] = []
        self.warn_out = warn_out               # callable(str) e.g. stderr.write
        self.pragmas: Dict[str, int] = {}      # R11 recorded allow-set
        self.counter = [0]
        now = time.localtime()
        self.expander = Expander(
            self.defs, lambda ln, col, msg: self._warn(self._cur_file, ln,
                                                       col, msg),
            self.counter, "<input>",
            time.strftime("%b %e %Y", now), time.strftime("%H:%M:%S", now),
            self.opts.emit_pragmas)
        self.stack: List[str] = []
        # M4 W4 depfile events (plan §4.4): one entry per EMITTED include
        # event — (spelled candidate path, resolved abspath, is_system) —
        # in resolution order; the renderer never re-walks (depfile.py).
        self.deps: List[Tuple[str, bool]] = []
        self._dep_objs: set = set()   # the .d OBJECT keys (see _include)
        self._cond_base: List[int] = []
        self._cur_file = "<input>"
        self._conds: List[List[bool]] = []
        self._cond_open: List[Tuple[str, int]] = []

    # -- entry points ---------------------------------------------------------

    def preprocess_text(self, path: str, text: str) -> List[SourceLine]:
        self.expander.main_file = path
        self._apply_cli()
        for name in self.opts.preinclude:
            self._include(path, 1, '"%s"' % name, preinclude=True)
        self._process(path, text)
        # gcc's -E stream ENDS at the last content line + one \n — no
        # trailing blank lines at EOF, measured (even `V FOO\n\n\n`
        # collapses to zero); blcc's per-line output carried one empty
        # trailing SourceLine in EVERY run. Invisible to norm() as plain
        # whitespace, VISIBLE when the final token is an unterminated
        # string, which swallows to end-of-stream (F-X12 token diff, MC
        # 12469). Drop the trailing blank run; INTERNAL blanks stay
        # (measured mid-file: 2 blank lines survive on both sides).
        while self.out and self.out[-1].text == "":
            self.out.pop()
        return self.out

    def preprocess_file(self, path: str) -> List[SourceLine]:
        return self.preprocess_text(path, self._read(path))

    # -- -D / -U (order: builtins -> argv left-to-right, R17) ------------------

    def _apply_cli(self) -> None:
        for kind, arg, _ in self.opts.du:
            # libcpp parses a CLI -D/-U OPERAND by pushing it behind a
            # synthetic `#define`/`#undef` line — the operand rides the
            # SAME directive reader as the in-source spelling (skip ws,
            # longest identifier, tolerate the tail; F-c5-A/F-c5-B, MC
            # 12458). The FIRST '=' separates the body (measured
            # `-DFOO==1` -> body `= 1`); with NO '=' the tail is still
            # read and followed by `1`: `-DFOO BAR` -> body `BAR 1`,
            # bare `-DFOO` -> `1` exactly (F-c4-A, MC 12456) while the
            # explicit `-Dname=` keeps its EMPTY body (oracle `int x = ;`
            # rc 0 — the c6 fix-boundary row).
            # A directive is a LINE: the synthetic one ends at the first
            # newline of the operand, and a lone \r ends it too (F-c6-A
            # S07/S18/S54/S55 + the c8 \r rows, MC 12465). The implicit
            # ` 1` of a bare -D is appended AFTER the whole operand, so
            # any clip puts it past the line end: a clipped bare name is
            # EMPTY (S54 `V V`), while a same-line tail still reads `1`
            # only with no clip (`-DFOO BAR` -> `BAR 1`, S44 stands). A
            # '=' past the clip sits on the dead line: it neither
            # separates (S55/N01 clip the body) nor suppresses. The tail
            # past the EOL never reaches either reader (N11: no
            # extra-tokens warning from `-UFOO\nBAR`).
            if any("\ud800" <= c <= "\udfff" for c in arg):
                # An argv byte that is not valid UTF-8 arrives through
                # Python's surrogateescape and CANNOT reach the text-mode
                # -E stream at all (it used to ICE the write with rc 1 —
                # §8 violation). Unrepresentable -> LOUD naming the
                # operand (F-X05 family, §5; gcc emits raw bytes rc 0,
                # the disclosed loud-divergence row).
                raise DiagError("pp", "<command-line>", 1, 1,
                                "-%s operand is not valid UTF-8" % kind,
                                "-%s %s" % (kind, arg.encode(
                                    "utf-8", "backslashreplace").decode(
                                        "ascii")))
            eol = min((i for i in (arg.find("\n"), arg.find("\r"))
                       if i >= 0), default=-1)
            head = arg if eol < 0 else arg[:eol]
            if kind == "U":
                self._undef("<command-line>", 1,
                            _merge_id_runs(tokenize(head), "<command-line>",
                                           1),
                            "-U needs an identifier", arg)
                continue
            name_part, sep, tail = head.partition("=")
            if sep:
                text = name_part + " " + tail
            elif eol >= 0:
                text = name_part + " "
            else:
                text = name_part + " 1"
            toks = _merge_id_runs(tokenize(text), "<command-line>", 1)
            for tok in toks:
                # the operand's unterminated literal tier (F-X12): gcc
                # warns `missing terminating " character` on the operand
                # parse itself (rc stays 0, the clipped body still
                # defines); blcc had no such warning.
                if tok[:1] in ("'", '"') and not re.fullmatch(
                        tok[0] + r"(?:\\.|[^" + tok[0] + r"\\])*" + tok[0],
                        tok):
                    self._warn("<command-line>", 1, 1,
                               "missing terminating %s character" % tok[0])
            # A backslash glued after the NAME (the UCN spellings that did
            # not merge into one run, e.g. the incomplete `-DA\u00e=5`
            # that gcc takes as name `A` + warn + body `5`) half-parses
            # exactly like X05 — the M1 subset cannot represent it, so it
            # is refused LOUD before the shared reader. `-DFOO-x` (dash
            # tail) is NOT a libcpp name char and stays tail-tolerated
            # (fairness rows c7/X-measured, def `-x 1` both sides).
            tk = self._skip_ws(toks)
            if tk[1:2] == ["\\"]:
                raise DiagError("pp", "<command-line>", 1, 1,
                                "-D needs an identifier", "-D " + arg)
            self._define("<command-line>", 1, toks,
                         warn_ctx="-D " + arg,
                         name_msg="-D needs an identifier")

    # -- directives -------------------------------------------------------------

    def _process(self, path: str, text: str) -> None:
        lines = _strip_comments(_splice(text))
        # Diagnostic label: gcc drops a LEADING "./" component only
        # (mid-path segments ride raw) — normpath is never applied.
        st = {"label": _spell(path), "forced": None}   # R10 origin-map state
        self.stack.append(os.path.abspath(path))
        self._cond_base.append(len(self._conds))   # this file's floor
        # The quote-head identity is the includer's dir as its RAW PATH
        # PREFIX (gcc dir_name_of_file: ends in '/' when non-empty, ""
        # when the path has no slash — make_cpp_dir hashes the STRING,
        # so "" != "./" != "d1/"; the W4-fix F-1 law).
        base_dir = path[:len(path) - len(os.path.basename(path))]
        i = 0
        try:
            while i < len(lines):
                phys, joined = lines[i]
                ln = phys if st["forced"] is None else st["forced"]
                if st["forced"] is not None:
                    st["forced"] += 1
                self._cur_file = st["label"]
                active = all(c[1] for c in self._conds)
                toks = tokenize(joined)
                head = next((t for t in toks if not is_ws(t)), None)
                if head == "#":
                    # a directive starts at the first '#' TOKEN, not the
                    # first character: `/* c */ #define` is a directive too
                    # (verdict-c1 F5, oracle rc 0).
                    self._directive(st, base_dir, ln, toks[toks.index("#"):])
                    i += 1
                    continue
                if not active:
                    i += 1
                    continue
                # active code line: expand, consuming further logical lines
                # when a function-like invocation is unterminated (R2).
                buf = {"i": i}
                stream = list(toks)

                def more(dst):
                    # appends to the STREAM THE EXPANDER IS CURRENTLY
                    # SCANNING (it splices replacements into that list and
                    # re-binds it — F-3/MC 12436), not to the fixed buffer.
                    # While an open argument list spans lines, gcc KEEPS
                    # preprocessing line by line: a directive there is
                    # EXECUTED, contributes nothing to the argument, and
                    # its #if/#else decide which following lines are in the
                    # argument at all (mm/page_alloc.c:1095, ipc/shm.c:157
                    # — silent + loud residuals of the MC 12436 sweep).
                    while True:
                        if buf["i"] + 1 >= len(lines):
                            return False
                        buf["i"] += 1
                        phys2, joined2 = lines[buf["i"]]
                        tk = tokenize(joined2)
                        if next((t for t in tk if not is_ws(t)), None) == "#":
                            self._directive(st, base_dir, phys2,
                                            tk[tk.index("#"):])
                            continue
                        if all(c[1] for c in self._conds):
                            dst.extend(tk)
                            return True

                exp = self.expander.expand(stream, st["label"], ln, more)
                self.out.append(SourceLine(st["label"], ln,
                                           _emit_join(exp)))
                i = buf["i"] + 1
                continue
            if len(self._conds) > self._cond_base[-1]:
                f, cl = self._cond_open[-1]
                raise DiagError("pp", f, cl, 1,
                                "unterminated #if at end of file (M1 drops "
                                "the GA lenient-EOF posture)", "#if")
        finally:
            self.stack.pop()
            self._cond_base.pop()

    def _directive(self, st, base_dir, ln, toks):
        label = st["label"]
        word_t = next((t for t in toks[1:] if not is_ws(t)), None)
        if word_t is None:
            return                             # null directive: ignore
        word = word_t.lstrip("#")
        rest = toks[toks.index(word_t) + 1:] if word_t in toks else []
        rest = self._skip_ws(rest)
        parent = self._conds[-1][1] if self._conds else True
        if word in ("ifdef", "ifndef"):
            name = rest[0] if rest else ""
            if not _NAME_RE.match(name):
                raise DiagError("pp", label, ln, 1,
                                "#%s needs one macro name" % word,
                                self._text(rest))
            taken = parent and (name in self.defs)
            if word == "ifndef":
                taken = parent and (name not in self.defs)
            self._conds.append([parent, taken, taken])
            self._cond_open.append((label, ln))
            return
        if word == "if":
            taken = parent and bool(self._eval(label, ln, rest))
            self._conds.append([parent, taken, taken])
            self._cond_open.append((label, ln))
            return
        if word == "elif":
            if len(self._conds) <= self._cond_base[-1]:
                raise DiagError("pp", label, ln, 1, "#elif without #if",
                                "#elif")
            e = self._conds[-1]
            taken = (e[0] and not e[2] and bool(self._eval(label, ln, rest))) \
                if e[0] else False
            e[1] = taken
            e[2] = e[2] or taken
            return
        if word == "else":
            if len(self._conds) <= self._cond_base[-1]:
                raise DiagError("pp", label, ln, 1,
                                "#else without #ifdef/#ifndef/#if", "#else")
            e = self._conds.pop()
            taken = e[0] and not e[2]
            self._conds.append([e[0], taken, e[2] or taken])
            return
        if word == "endif":
            if len(self._conds) <= self._cond_base[-1]:
                raise DiagError("pp", label, ln, 1,
                                "#endif without #ifdef/#ifndef/#if", "#endif")
            self._conds.pop()
            self._cond_open.pop()
            return
        if self._conds and not self._conds[-1][1]:
            return                             # inactive region: silence
        if word == "include":
            self._include_line(label, ln, rest, base_dir)
        elif word == "define":
            self._define(label, ln, rest, warn_ctx="#define " + self._text(rest))
        elif word == "undef":
            self._undef(label, ln, rest, "#undef needs one macro name",
                        self._text(rest))
        elif word == "error":
            msg = self._text(rest).strip()
            raise DiagError("pp", label, ln, 1, "#error %s" % msg, msg)
        elif word == "warning":
            self._warn(label, ln, 1, self._text(rest).strip())
        elif word == "line":
            self._line(st, ln, rest)
        elif word == "pragma":
            text = self._text(rest).strip()
            word0 = text.split()[0] if text.split() else ""
            self.pragmas[word0] = self.pragmas.get(word0, 0) + 1
            if self.opts.emit_pragmas:
                self.out.append(SourceLine(label, ln, "#pragma " + text))
        else:
            raise DiagError("pp", label, ln, 1,
                            "unsupported preprocessor directive (M1 supports "
                            "#include, #define, #undef, #if/#ifdef/#ifndef/"
                            "#elif/#else/#endif, #line, #error, #warning, "
                            "#pragma; #include_next is deferred)", "#" + word)

    @staticmethod
    def _skip_ws(toks):
        j = 0
        while j < len(toks) and is_ws(toks[j]):
            j += 1
        return toks[j:]

    @staticmethod
    def _text(toks) -> str:
        return "".join(toks)

    def _line(self, st, ln, rest):
        toks = [t for t in rest if not is_ws(t)]
        if not toks or not toks[0].isdigit():
            raise DiagError("pp", st["label"], ln, 1,
                            "#line needs a line number", self._text(rest))
        st["forced"] = int(toks[0])
        if len(toks) > 1:
            if not (toks[1].startswith('"') and toks[1].endswith('"')):
                raise DiagError("pp", st["label"], ln, 1,
                                "#line file name must be a string literal",
                                toks[1])
            st["label"] = toks[1][1:-1]

    # -- #if evaluation (defined both spellings, expand, evaluate) ---------------

    def _eval(self, path: str, ln: int, toks) -> bool:
        toks = self._defined_pass(path, ln, list(toks))
        toks = self.expander.expand(toks, path, ln, protect=True)
        toks = self._defined_pass(path, ln, toks)
        return bool(pp_eval.eval_tokens(toks, path, ln))

    def _defined_pass(self, path: str, ln: int, toks) -> List[str]:
        out: List[str] = []
        i, n = 0, len(toks)
        while i < n:
            t = toks[i]
            if t == "defined":
                j = self._skip_idx(toks, i + 1)
                if j < n and toks[j] == "(":
                    k = self._skip_idx(toks, j + 1)
                    if k < n and is_id(toks[k]) and \
                            self._skip_idx(toks, k + 1) < n and \
                            toks[self._skip_idx(toks, k + 1)] == ")":
                        out.append("1" if toks[k] in self.defs else "0")
                        i = self._skip_idx(toks, k + 1) + 1
                        continue
                    i += 1
                    continue
                if j < n and is_id(toks[j]):
                    out.append("1" if toks[j] in self.defs else "0")
                    i = j + 1
                    continue
                raise DiagError("pp", path, ln, 1,
                                "'defined' with no macro name after it",
                                "defined")
            out.append(t)
            i += 1
        return out

    @staticmethod
    def _skip_idx(toks, i):
        while i < len(toks) and is_ws(toks[i]):
            i += 1
        return i

    # -- #include (search order + reopen, R1/R20) --------------------------------


    # -- #define ------------------------------------------------------------------

    def _undef(self, path: str, ln: int, toks, msg: str, ctx: str) -> None:
        """THE macro-name reader, shared by the in-source `#undef` and the
        CLI `-U` operand (verdict-c5 F-c5-A, MC 12458): skip whitespace,
        take the longest identifier token, tolerate the tail — the exact
        shape libcpp parses BOTH spellings through (it pushes a -U operand
        behind a synthetic `#undef` line), so the CLI branch uses THIS
        reader, not a parallel string pop. Missing/invalid name = the §8
        diagnostic naming the construct; a NON-WHITESPACE tail = gcc's
        measured rc-0 warning tier; undefining a BUILT-IN warns
        `undefining \"NAME\"` (c5 matrix U21) and still undefines."""
        rest = self._skip_ws(toks)
        if not rest or not _NAME_RE.match(rest[0]):
            raise DiagError("pp", path, ln, 1, msg, ctx)
        if self._skip_ws(rest[1:]):
            self._warn(path, ln, 1, "extra tokens at end of #undef directive")
        old = self.defs.pop(rest[0], None)
        if old is not None and old.builtin:
            self._warn(path, ln, 1, "undefining '%s'" % rest[0])

    def _define(self, path: str, ln: int, toks, warn_ctx: str,
                name_msg: Optional[str] = None) -> None:
        toks = self._skip_ws(toks)
        if not toks or not _NAME_RE.match(toks[0]):
            raise DiagError("pp", path, ln, 1,
                            name_msg or "#define needs a macro name",
                            warn_ctx)
        name = toks[0]
        body = toks[1:]
        params: Optional[List[str]] = None
        variadic = False
        var_name = "__VA_ARGS__"
        if body and body[0] == "(":
            params = []
            j = 1
            group: List[str] = []
            groups: List[List[str]] = []
            while j < len(body) and body[j] != ")":
                if body[j] == ",":
                    groups.append(group)
                    group = []
                else:
                    group.append(body[j])
                j += 1
            if j >= len(body):
                raise DiagError("pp", path, ln, 1,
                                "unterminated parameter list in #define",
                                warn_ctx)
            groups.append(group)
            body = body[j + 1:]
            if not (len(groups) == 1 and not self._skip_ws(groups[0])):
                for g in groups:
                    g = self._skip_ws(g)
                    txt = "".join(self._text(g).split())
                    if txt == "...":
                        variadic = True
                        continue
                    if txt.endswith("...") and _NAME_RE.match(txt[:-3]):
                        # GNU named variadic (x..., kconfig.h shape): the
                        # name itself captures the whole argument tail.
                        params.append(txt[:-3])
                        variadic = True
                        var_name = txt[:-3]
                        continue
                    if not _NAME_RE.match(txt):
                        raise DiagError("pp", path, ln, 1,
                                        "bad macro parameter", self._text(g))
                    if txt in params:
                        raise DiagError("pp", path, ln, 1,
                                        "duplicate macro parameter", txt)
                    params.append(txt)
            else:
                params = []
        first = self._skip_ws(body)
        while first and is_ws(first[-1]):
            first = first[:-1]        # gcc stores NO edge whitespace in a
            # macro body: `#define F (x) /* c */` ends at `)`, and an
            # expansion that leaks a trailing space corrupts every
            # __stringify of it (alternative.h .word, MC 12436 sweep).
        if first and (first[0] == "##" or first[-1] == "##"):
            if params is None:
                # OBJECT-LIKE edge paste: gcc 11.4 makes this a DEFINE-TIME
                # ERROR, rc != 0 (MC 12454 e6/e7 measured pair: `#define E
                # ##b` dies with "'##' cannot appear at either end of a
                # macro expansion").
                raise DiagError("pp", path, ln, 1,
                                "'##' cannot appear at either end of a macro "
                                "expansion", warn_ctx)
            self._warn(path, ln, 1, "'##' cannot appear at either end of a "
                                    "macro expansion")
            # The function-like spelling keeps the documented M1 leniency
            # (warn + macro NOT defined, rc 0, stream equal — pinned by
            # test_pp_differential_m1.test_paste_no_yield_warns; the oracle
            # is rc 1 here, a KNOWN residual outside F-A's object-like
            # scope, MC 12454 readings).
            return
        new = Macro(name, list(first), params, variadic, var_name=var_name)
        old = self.defs.get(name)
        if old is not None and (old.builtin
                                or not self._same_macro(old, new)):
            # gcc 11.4 measured (c5 F-c5-C, B18–B23): redefining a BUILT-IN
            # warns `redefined` EVEN for an identical body (the builtin is
            # not "the same macro" as far as the oracle is concerned); the
            # user-vs-user rule is untouched — identical SILENT, differing
            # warns, last wins (c6 rows).
            self._warn(path, ln, 1, "macro '%s' redefined" % name)
        self.defs[name] = new

    @staticmethod
    def _same_macro(a: Macro, b: Macro) -> bool:
        if a.kind != "std" or b.kind != "std":
            return False
        return (a.params == b.params and a.variadic == b.variadic
                and [t for t in a.body if not is_ws(t)]
                == [t for t in b.body if not is_ws(t)])

    # -- file IO + warnings -------------------------------------------------------

    def _read(self, path: str) -> str:
        try:
            with open(path, "rb") as fh:
                data = fh.read()
        except OSError as exc:
            raise DiagError("pp", path, 1, 1,
                            "cannot read input file (%s)" % exc.strerror,
                            path) from exc
        try:
            return data.decode("utf-8")
        except UnicodeDecodeError:
            return data.decode("latin-1")

    def _warn(self, path: str, ln: int, col: int, msg: str) -> None:
        line = "%s:%d:%d: pp: warning: %s" % (path, ln, col, msg)
        self.warnings.append(line)
        if self.warn_out:
            self.warn_out(line + "\n")


def preprocess(path: str, text: str) -> List[SourceLine]:
    """Preprocess in-memory source; path labels outputs and anchors quoted
    includes (GA-compatible signature; M1 options default)."""
    return Preprocessor().preprocess_text(path, text)


def preprocess_file(path: str, opts: Optional[PpOpts] = None) -> List[SourceLine]:
    return Preprocessor(opts).preprocess_file(path)
