"""blcc/pp_text.py — pass-0/pass-1 source-text mechanics for the M1
preprocessor (MC 12775 clean-code split of preproc.py, functions MOVED
VERBATIM — zero behavior change): backslash-newline splice with the
(file,line) origin map, comment strip (R21), the glued identifier/UCN run
merger (F-X05) and the -E token serializer with its space_needed/UCN rules
(F-X20). Pure text: no macro table, no files, no directives.
"""
from __future__ import annotations

import re
from typing import List, Optional, Tuple

from blcc.lexer import DiagError
from blcc.pp_expand import is_ws


def _spell(path: str) -> str:
    """A dep/diagnostic PATH as gcc spells it (M4 W4-fix F-2 + M4 W-B
    COMMIT-0): a LEADING `.` component is dropped and eats EVERY slash
    that follows it (measured, gate m4-w4-fixgate LEG2 rep: -I. -> n.h,
    -I./inc -> inc/n.h, -include ./n.h -> n.h, `-I.//inc` -> inc/n.h,
    `././/dd/a.h` -> dd/a.h); every OTHER segment rides raw — mid-path
    './', '../', a leading '/' and '//' survive exactly as gcc emits
    them (inc/./z.h, inc/sub/../z.h, inc/sub//z.h). Object IDENTITY is
    untouched: the drop happens at SPELL time only, so two raw
    spellings of one file stay TWO libcpp objects (g3.d emits both).
    normpath is never applied: its collapse was the 37/705-recipe
    universe divergence."""
    while path.startswith("./"):
        path = path[2:]
        while path.startswith("/"):   # the dot eats its whole slash run
            path = path[1:]
    return path
_NAME_RE = re.compile(r"[A-Za-z_][A-Za-z0-9_]*$")
_IDENTC_RE = re.compile(r"[A-Za-z0-9_.']")
# Two spliced tokens must never re-lex as one: `pri`+`ntf` may not print as
# `printf` (e14, MC 12454) and `<`+`<` may not print as `<<`, exactly like
# the space_needed rule in cpp (gcc emits `pri ntf`, `< < <`, `/ *x`).
_MERGE2_OPS = ("<<=", ">>=", "...", "->", "++", "--", "<<", ">>", "&&",
               "||", "==", "!=", "<=", ">=", "+=", "-=", "*=", "/=", "%=",
               "&=", "^=", "|=")

# --- CLI-operand identifier charclass (F-X05, MC 12469). MEASURED libcpp
# rule, locale-INDEPENDENT (re-ran this session under LC_ALL=C, C.UTF-8,
# ISO-8859-1 and GB18030 — identical): raw chars >= 0xAA and `$` are
# identifier-constituent, and a glued `\uXXXX`/`\UXXXXXXXX` UCN continues
# the identifier (bytes 0x80..0xA9 — C1 controls, NBSP — are NOT name
# chars: gcc emits those RAW, never UCN-ized). blcc's token model is
# ASCII (the expander's is_id gate; UCN fold is not implemented), so the
# c7/c8 operand reader EXTENDS its charclass to take the libcpp run as
# ONE token: the name gate (`_NAME_RE`, the M1 ASCII C-identifier subset)
# then LOUD-refuses any run it cannot represent — a half-name def at
# rc 0 is IMPOSSIBLE (ARCHITECTURE §5). An INCOMPLETE `\u` escape is no
# UCN (gcc emits it as written, rc 0) and glues nothing; a syntactically
# complete UCN whose code point is below U+00A0 (`\u0041`) is not a valid
# identifier UCN and is loud both sides.
_IDRUN_TOK = re.compile(r"[A-Za-z0-9_$\u00aa-\U0010ffff]+$")
_UCN_SHAPE = re.compile(r"([uU])([0-9a-fA-F]{8}|[0-9a-fA-F]{4,})")


def _ucn_cp(tok: str) -> Optional[int]:
    """Code point of the UCN payload when `tok` is the token glued after a
    backslash, or None when it does not spell a COMPLETE UCN."""
    m = _UCN_SHAPE.match(tok)
    if not m:
        return None
    want = 8 if m[1] == "U" else 4
    if len(m[2]) < want:
        return None
    return int(m[2][:want], 16)


def _merge_id_runs(toks, path: str, ln: int) -> List[str]:
    r"""Reader charclass extension (NOT a second reader): merge the glued
    pieces of one libcpp identifier run — ASCII ident chunks, `$`, raw
    chars >= 0xAA and `\u`/`\U` UCNs — into a single token, keeping the
    spelled text. Names outside what M1 can represent (anything the
    `_NAME_RE` gate rejects) reach the shared name reader as ONE whole
    name and go LOUD there; the split-halves silent wrong-def (X05) is
    gone by construction.
    """
    out: List[str] = []
    i, n = 0, len(toks)

    def glued_ucn(j: int) -> Optional[int]:
        v = _ucn_cp(toks[j])
        if v is not None and v < 0xA0:
            raise DiagError("pp", path, ln, 1,
                            "\\U%08x is not a valid universal character" % v,
                            "\\" + toks[j])
        return v

    while i < n:
        t = toks[i]
        if is_ws(t) or (t != "\\" and not _IDRUN_TOK.match(t)):
            out.append(t)
            i += 1
            continue
        if t == "\\":
            if glued_ucn(i + 1) if i + 1 < n else None:
                run = "\\" + toks[i + 1]
                i += 2
            else:
                out.append(t)
                i += 1
                continue
        else:
            run = t
            i += 1
        while i < n and not is_ws(toks[i]):
            if toks[i] == "\\":
                if i + 1 >= n or glued_ucn(i + 1) is None:
                    break
                run += "\\" + toks[i + 1]
                i += 2
                continue
            if _IDRUN_TOK.match(toks[i]):
                run += toks[i]
                i += 1
                continue
            break
        out.append(run)
    return out


# --- -E token serialization (F-X20, MC 12469). Measured gcc 11.4: an
# identifier token carrying non-ASCII prints as lowercase UCNs per char
# (`ó` -> `\U000000f3`, 漢 -> `\U00006f22`, U+1F600 -> `\U0001f600`); the
# `\uXXXX` spelling normalizes to the 8-digit `\U` form; STRING/CHAR-
# LITERAL contents stay RAW BYTES; non-name bytes (< 0xAA, e.g. NBSP)
# print raw.
_U_LOWER_RE = re.compile(r"\\u([0-9a-fA-F]{4})")
_U_UPPER_RE = re.compile(r"\\U([0-9a-fA-F]{8})")


def _ucn_spell(tok: str) -> str:
    if tok and tok[0] in "\"'":
        return tok
    if (not any(ord(c) >= 0x80 for c in tok)
            and "\\u" not in tok and "\\U" not in tok):
        return tok
    t = _U_LOWER_RE.sub(lambda m: "\\U0000" + m.group(1).lower(), tok)
    t = _U_UPPER_RE.sub(lambda m: "\\U" + m.group(1).lower(), t)
    return "".join(c if ord(c) < 0xAA else "\\U%08x" % ord(c) for c in t)


def _emit_join(toks: List[str]) -> str:
    """Serialize an expanded token list, separating two tokens whose bare
    concatenation would lex back as something else (ident/pp-number runs,
    multi-char-operator prefixes, comment starts). Source whitespace
    between tokens survives untouched."""
    out: List[str] = []
    spelled: List[str] = []
    for t in toks:
        if out:
            a, b = spelled[-1], t
            if a and b and not is_ws(a[-1]) and not is_ws(b[0]):
                j = a[-1] + b[0]
                if ((_IDENTC_RE.match(j[0]) and _IDENTC_RE.match(j[1]))
                        or any(op.startswith(j) for op in _MERGE2_OPS)
                        or j in ("/*", "*/", "//")):
                    out.append(" ")
                    spelled.append(" ")
        out.append(_ucn_spell(t))
        spelled.append(t)
    return "".join(out)



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
