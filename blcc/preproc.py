"""Subset preprocessor per ARCHITECTURE.md §3.

Supports EXACTLY: #include "quoted.h" (input-relative, cycle guard),
object-like and function-like #define, #ifdef/#ifndef/#else/#endif, #undef.
#include <...> is a pp diagnostic naming the construct (§5); so is every
other directive. Output is a list of SourceLine so every token keeps its
true origin file/line. stdlib-only.
"""
from __future__ import annotations

import os
import re
from typing import Dict, List, Optional, Tuple

from blcc.lexer import DiagError, SourceLine

# One chunk = string literal | char literal | line comment | block comment |
# identifier | run of whitespace | single other char. Literals and comments
# are opaque, so macro names inside them are never expanded.
_CHUNK_RE = re.compile(
    r'"(?:\\.|[^"\\])*"?|\'(?:\\.|[^\\\'])*\'?|//[^\n]*|/\*.*?(?:\*/|$)'
    r'|[A-Za-z_][A-Za-z0-9_]*|\s+|.', re.S)

_MAX_EXPANSION_ROUNDS = 64


class _Macro:
    def __init__(self, name: str, body: str,
                 params: Optional[List[str]]):  # None = object-like
        self.name = name
        self.body = body
        self.params = params


class Preprocessor:
    def __init__(self):
        self.defs: Dict[str, _Macro] = {}
        self.out: List[SourceLine] = []
        self._stack: List[str] = []

    # -- entry points ------------------------------------------------------

    def preprocess_text(self, path: str, text: str) -> List[SourceLine]:
        return self._run(path, text)

    def preprocess_file(self, path: str) -> List[SourceLine]:
        return self._run(path, self._read(path))

    # -- file level (include stack + cycle guard) ---------------------------

    def _run(self, path: str, text: str) -> List[SourceLine]:
        resolved = os.path.abspath(path)
        if resolved in self._stack:
            raise DiagError("pp", path, 1, 1,
                            "include cycle detected for '{}'".format(path),
                            "#include")
        self._stack.append(resolved)
        try:
            self._process_lines(path, text.splitlines())
        finally:
            self._stack.pop()
        return self.out

    def _read(self, path: str) -> str:
        try:
            with open(path, "r", encoding="utf-8") as fh:
                return fh.read()
        except OSError as exc:
            raise DiagError("pp", path, 1, 1,
                            "cannot read input file ({})".format(exc.strerror),
                            path) from exc

    # -- line level (directives + conditionals + expansion) ------------------

    def _process_lines(self, path: str, lines: List[str]) -> None:
        # cond stack entries: (parent_active, active_now, any_branch_taken)
        conds: List[List[bool]] = []
        for lineno, raw in enumerate(lines, 1):
            active = all(e[1] for e in conds)
            stripped = raw.strip()
            if stripped.startswith("#"):
                self._directive(path, lineno, stripped, conds)
            elif active:
                self.out.append(SourceLine(path, lineno,
                                           self.expand(raw, path, lineno)))

    def _directive(self, path: str, lineno: int, s: str,
                   conds: List[List[bool]]) -> None:
        m = re.match(r"#\s*([A-Za-z_][A-Za-z0-9_]*)\s*(.*)", s, re.S)
        if m is None:
            raise DiagError("pp", path, lineno, 1,
                            "malformed preprocessor directive", s)
        word, rest = m.group(1), m.group(2).strip()
        parent = conds[-1][1] if conds else True
        if word in ("ifdef", "ifndef"):
            taken = parent and self._defined(rest) if word == "ifdef" \
                else parent and not self._defined(rest)
            conds.append([parent, taken, taken])
            return
        if word == "else":
            if not conds:
                raise DiagError("pp", path, lineno, 1,
                                "#else without #ifdef/#ifndef", "#else")
            entry = conds.pop()
            taken = entry[0] and not entry[2]
            conds.append([entry[0], taken, entry[2] or taken])
            return
        if word == "endif":
            if not conds:
                raise DiagError("pp", path, lineno, 1,
                                "#endif without #ifdef/#ifndef", "#endif")
            conds.pop()
            return
        if conds and not conds[-1][1]:
            return  # inactive region: only if/else/endif bookkeeping above
        if word == "include":
            self._include(path, lineno, rest)
        elif word == "define":
            self._define(path, lineno, rest)
        elif word == "undef":
            name = self._directive_name(path, lineno, rest, "#undef")
            self.defs.pop(name, None)
        else:
            raise DiagError("pp", path, lineno, 1,
                            "unsupported preprocessor directive (the subset "
                            "has #include \"...\", #define, #ifdef, #ifndef, "
                            "#else, #endif, #undef)", "#" + word)

    def _defined(self, expr: str) -> bool:
        name = expr.split()[0] if expr.split() else ""
        return name in self.defs

    def _directive_name(self, path: str, lineno: int, rest: str,
                        directive: str) -> str:
        words = rest.split()
        if len(words) != 1 or not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*",
                                               words[0]):
            raise DiagError("pp", path, lineno, 1,
                            "{} needs one macro name".format(directive), rest)
        return words[0]

    # -- #include ------------------------------------------------------------

    def _include(self, path: str, lineno: int, rest: str) -> None:
        if rest.startswith("<"):
            raise DiagError("pp", path, lineno, 1,
                            "'#include <...>' (system headers) is not in the "
                            "subset — only quoted, input-relative includes "
                            "are supported", "#include " + rest)
        m = re.match(r'"([^"]*)"\s*(.*)', rest, re.S)
        if m is None:
            raise DiagError("pp", path, lineno, 1,
                            "malformed #include: expected \"quoted.h\"", rest)
        target, trailing = m.group(1), m.group(2).strip()
        if trailing:
            raise DiagError("pp", path, lineno, 1,
                            "trailing text after #include", trailing)
        if not target:
            raise DiagError("pp", path, lineno, 1, "empty #include path", rest)
        # Input-relative: resolve against the directory of the including file.
        full = os.path.normpath(os.path.join(os.path.dirname(path) or ".",
                                             target))
        if not os.path.isfile(full):
            raise DiagError("pp", path, lineno, 1,
                            "no such file for #include", '"%s"' % target)
        self._run(full, self._read(full))

    # -- #define ---------------------------------------------------------------

    def _define(self, path: str, lineno: int, rest: str) -> None:
        m = re.match(r"([A-Za-z_][A-Za-z0-9_]*)(\()?(\s*)", rest)
        if m is None:
            raise DiagError("pp", path, lineno, 1,
                            "#define needs a macro name", rest)
        name = m.group(1)
        if m.group(2) == "(":  # function-like: '(' glued to the name, no space
            close = rest.find(")")
            if close < 0:
                raise DiagError("pp", path, lineno, 1,
                                "unterminated parameter list in #define", rest)
            raw_params = rest[m.end():close]
            body = rest[close + 1:].strip()
            params: List[str] = []
            if raw_params.strip():
                for p in raw_params.split(","):
                    p = p.strip()
                    if p == "...":
                        raise DiagError("pp", path, lineno, 1,
                                        "variadic macro is not in the subset",
                                        "#define " + rest)
                    if not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", p):
                        raise DiagError("pp", path, lineno, 1,
                                        "bad macro parameter", p)
                    params.append(p)
            self.defs[name] = _Macro(name, body, params)
        else:
            self.defs[name] = _Macro(name, rest[m.end(1) + len(m.group(3)):].strip(),
                                     None)

    # -- expansion -----------------------------------------------------------

    def expand(self, text: str, path: str = "<macro>", lineno: int = 1) -> str:
        for round_no in range(_MAX_EXPANSION_ROUNDS):
            chunks = _CHUNK_RE.findall(text)
            out: List[str] = []
            changed = False
            i = 0
            while i < len(chunks):
                ch = chunks[i]
                macro = self.defs.get(ch) if re.fullmatch(
                    r"[A-Za-z_][A-Za-z0-9_]*", ch) else None
                if macro is None:
                    out.append(ch)
                    i += 1
                    continue
                if macro.params is None:
                    out.append(macro.body)
                    changed = True
                    i += 1
                    continue
                j = self._invocation(chunks, i)
                if j is None:
                    out.append(ch)
                    i += 1
                    continue
                args, close = self._arguments(chunks, i, j, path, lineno, macro)
                out.append(self._substitute(macro, args))
                changed = True
                i = close + 1
            text = "".join(out)
            if not changed:
                return text
        raise DiagError("pp", path, lineno, 1,
                        "macro expansion limit exceeded (self-referential "
                        "or runaway '#define')", "macro expansion")

    @staticmethod
    def _invocation(chunks: List[str], i: int) -> Optional[int]:
        """Index of the '(' chunk if chunks[i] id is immediately followed by
        '(' (only whitespace between), else None."""
        k = i + 1
        while k < len(chunks) and not chunks[k].strip():
            k += 1
        return k if k < len(chunks) and chunks[k] == "(" else None

    def _arguments(self, chunks: List[str], i: int, j: int, path: str,
                   lineno: int, macro: _Macro
                   ) -> Tuple[Tuple[str, ...], int]:
        depth = 0
        group: List[str] = []
        groups: List[str] = []
        close = j
        for k in range(j, len(chunks)):
            ch = chunks[k]
            if ch in "([{":
                depth += 1
                if depth == 1:
                    continue
            elif ch in ")]}":
                depth -= 1
                if depth == 0:
                    if "".join(group).strip():
                        groups.append("".join(group))
                    close = k
                    break
            elif ch == "," and depth == 1:
                groups.append("".join(group))
                group = []
                continue
            group.append(ch)
        else:
            raise DiagError("pp", path, lineno, i + 1,
                            "unterminated argument list for macro '{}'".format(
                                macro.name), macro.name)
        if len(groups) != len(macro.params):
            raise DiagError("pp", path, lineno, i + 1,
                            "macro '{}' takes {} argument(s)".format(
                                macro.name, len(macro.params)), macro.name)
        args = tuple(self.expand(g.strip(), path, lineno) for g in groups)
        return args, close

    def _substitute(self, macro: _Macro, args: List[str]) -> str:
        mapping = dict(zip(macro.params, args))
        parts: List[str] = []
        for ch in _CHUNK_RE.findall(macro.body):
            parts.append(mapping[ch] if ch in mapping else ch)
        return "".join(parts)


def preprocess(path: str, text: str) -> List[SourceLine]:
    """Preprocess in-memory source; path only labels outputs and resolves
    quoted includes relative to its directory."""
    return Preprocessor().preprocess_text(path, text)


def preprocess_file(path: str) -> List[SourceLine]:
    return Preprocessor().preprocess_file(path)
