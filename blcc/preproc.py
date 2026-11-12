"""M1 GCC-compatible preprocessor: directive dispatch & source bookkeeping
(plan R1, R2, R4, R10–R14, R17, R20, R21).

LINES (508 > 400): directive dispatch is ONE concern — the #if-conditional
stack, #line origin state and include search must share the per-file state
machine; splitting would duplicate that state across files.

Pass order per plan §2: pass-0 line splice (backslash-newline, keeping a
(file,line) origin map) BEFORE comment strip; directive dispatch on logical
lines; conditionals as a stack driven by pp_eval; include search order with
guarded REOPEN semantics (R20: a guarded header re-reads, the guard skips
the body — recursion depth cap + same-file-re-entered stay loud); #line
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
from blcc.pp_predefines import builtins
from blcc import pp_eval

_MAX_INCLUDE_DEPTH = 200         # mirrors gcc's default -fmax-include-depth
_NAME_RE = re.compile(r"[A-Za-z_][A-Za-z0-9_]*$")


def _splice(text: str) -> List[Tuple[int, List[Tuple[int, str]]]]:
    """Pass 0: join backslash-newline physical lines into logical lines
    (trailing splicing backslash removed, R2); each keeps its physical-line
    origin in the segment map."""
    raw = text.split("\n")
    logicals: List[Tuple[int, List[Tuple[int, str]]]] = []
    i = 0
    while i < len(raw):
        segs = [(i + 1, raw[i][:-1] if raw[i].endswith("\\") else raw[i])]
        while raw[i].endswith("\\"):
            i += 1
            nxt = raw[i]
            segs.append((i + 1, nxt[:-1] if nxt.endswith("\\") else nxt))
        logicals.append((segs[0][0], segs))
        i += 1
    return logicals


def _strip_comments(logicals):
    """R21 pass 1: every comment becomes one space; strings stay opaque.
    Operates across logical lines (a block comment may span them)."""
    out = []
    in_block = False
    for line, segs in logicals:
        text = "".join(s[1] for s in segs)
        buf: List[str] = []
        i, n = 0, len(text)
        while i < n:
            if in_block:
                j = text.find("*/", i)
                if j < 0:
                    i = n
                else:
                    in_block = False
                    i = j + 2
                    buf.append(" ")
                continue
            c = text[i]
            if text.startswith("/*", i):
                in_block = True
                i += 2
                buf.append(" ")
                continue
            if text.startswith("//", i):
                break
            if c in "\"'":
                j = i + 1
                while j < n and text[j] != c:
                    j += 2 if text[j] == "\\" and j + 1 < n else 1
                buf.append(text[i:min(j + 1, n)])
                i = j + 1
                continue
            buf.append(c)
            i += 1
        out.append((line, "".join(buf)))
    return out


class PpOpts:
    """Parsed CLI preprocessing surface (R17) — built by driver._parse_args."""

    def __init__(self):
        self.includes_dir: List[str] = []      # -I, argv order
        self.isystem: List[str] = []           # -isystem, searched after -I
        self.preinclude: List[str] = []        # -include, in order
        self.du: List[Tuple[str, str, Optional[str]]] = []   # -D/-U ordered
        self.std = "gnu17"
        self.emit_pragmas = False              # True only in -E mode


class Preprocessor:
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
        self._cond_base: List[int] = []
        self._cur_file = "<input>"
        self._conds: List[List[bool]] = []
        self._cond_open: List[Tuple[str, int]] = []

    # -- entry points ---------------------------------------------------------

    def preprocess_text(self, path: str, text: str) -> List[SourceLine]:
        self.expander.main_file = path
        self._apply_cli()
        for name in self.opts.preinclude:
            self._include(path, 1, '"%s"' % name,
                          base_dir=os.path.dirname(path) or ".")
        self._process(path, text)
        return self.out

    def preprocess_file(self, path: str) -> List[SourceLine]:
        return self.preprocess_text(path, self._read(path))

    # -- -D / -U (order: builtins -> argv left-to-right, R17) ------------------

    def _apply_cli(self) -> None:
        for kind, arg, _ in self.opts.du:
            if kind == "U":
                self.defs.pop(arg, None)
                continue
            name, _, body = arg.partition("=")
            m = re.match(r"[A-Za-z_][A-Za-z0-9_]*", name)
            # -D may spell a function-like macro: SQ(x)=((x)*(x)) (R17).
            if not m or (m.end() != len(name) and name[m.end()] != "("):
                raise DiagError("pp", "<command-line>", 1, 1,
                                "-D needs an identifier", arg)
            text = ("%s %s" % (name, body)) if body else name
            self._define("<command-line>", 1, tokenize(text),
                         warn_ctx="#define " + arg)

    # -- directives -------------------------------------------------------------

    def _process(self, path: str, text: str) -> None:
        lines = _strip_comments(_splice(text))
        st = {"label": path, "forced": None}   # R10 origin-map state
        self.stack.append(os.path.abspath(path))
        self._cond_base.append(len(self._conds))   # this file's floor
        base_dir = os.path.dirname(path) or "."
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
                    self._directive(st, base_dir, ln, toks)
                    i += 1
                    continue
                if not active:
                    i += 1
                    continue
                # active code line: expand, consuming further logical lines
                # when a function-like invocation is unterminated (R2).
                buf = {"i": i}
                stream = list(toks)

                def more():
                    if buf["i"] + 1 >= len(lines):
                        return False
                    buf["i"] += 1
                    stream.extend(tokenize(lines[buf["i"]][1]))
                    return True

                exp = self.expander.expand(stream, st["label"], ln, more)
                self.out.append(SourceLine(st["label"], ln, "".join(exp)))
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
            self._include(label, ln, self._text(rest).strip(),
                          base_dir=base_dir)
        elif word == "define":
            self._define(label, ln, rest, warn_ctx="#define " + self._text(rest))
        elif word == "undef":
            if not rest or not _NAME_RE.match(rest[0]):
                raise DiagError("pp", label, ln, 1,
                                "#undef needs one macro name",
                                self._text(rest))
            self.defs.pop(rest[0], None)
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

    def _include(self, path: str, ln: int, operand: str,
                 base_dir=".") -> None:
        if not operand:
            raise DiagError("pp", path, ln, 1, "empty #include",
                            "#include")
        if operand[0] == "<":
            end = operand.find(">")
            if end < 0:
                raise DiagError("pp", path, ln, 1, "malformed #include",
                                "#include " + operand)
            target = operand[1:end]
            angle = True
        elif operand[0] == '"':
            end = operand.find('"', 1)
            if end < 0:
                raise DiagError("pp", path, ln, 1,
                                "malformed #include: expected \"quoted.h\"",
                                "#include " + operand)
            target = operand[1:end]
            angle = False
        else:
            raise DiagError("pp", path, ln, 1,
                            "macro-operand #include is not evaluated in M1 "
                            "(deferred §5)", "#include " + operand)
        if not target:
            raise DiagError("pp", path, ln, 1, "empty #include path",
                            "#include " + operand)
        cand: List[str] = []
        if not angle:
            cand.append(os.path.normpath(os.path.join(base_dir, target)))
        cand += [os.path.normpath(os.path.join(d, target))
                 for d in self.opts.includes_dir + self.opts.isystem]
        full = next((c for c in cand if os.path.isfile(c)), None)
        shown = "#include %s" % operand
        if full is None:
            raise DiagError("pp", path, ln, 1, "no such file or directory",
                            shown)
        resolved = os.path.abspath(full)
        if resolved in self.stack:
            raise DiagError("pp", path, ln, 1,
                            "include cycle detected for '%s'" % full, shown)
        if len(self.stack) >= _MAX_INCLUDE_DEPTH:
            raise DiagError("pp", path, ln, 1,
                            "#include nested depth %d exceeds maximum of %d "
                            "(use -fmax-include-depth=DEPTH to increase the "
                            "maximum)" % (_MAX_INCLUDE_DEPTH,
                                          _MAX_INCLUDE_DEPTH), shown)
        self._process(full, self._read(full))

    # -- #define ------------------------------------------------------------------

    def _define(self, path: str, ln: int, toks, warn_ctx: str) -> None:
        toks = self._skip_ws(toks)
        if not toks or not _NAME_RE.match(toks[0]):
            raise DiagError("pp", path, ln, 1, "#define needs a macro name",
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
        if first and (first[0] == "##" or first[-1] == "##"):
            self._warn(path, ln, 1, "'##' cannot appear at either end of a "
                                    "macro expansion")
            return                               # macro NOT defined (oracle)
        new = Macro(name, list(first), params, variadic, var_name=var_name)
        old = self.defs.get(name)
        if old is not None and not self._same_macro(old, new):
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
