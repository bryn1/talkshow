"""Tokenizer for blcc (ARCHITECTURE.md §3/§8) plus the shared diagnostic type.

Concerns: SourceLine, Token, DiagError (§8 format), the Lexer, TokenStream.
Every token carries file:line:col (1-based). Unclassifiable input is a lex
diagnostic naming the offending text.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import List, Optional

KEYWORDS = frozenset({
    "char", "short", "int", "long", "void", "const", "struct", "typedef",
    "enum", "static", "extern", "if", "else", "while", "do", "for", "switch",
    "case", "default", "break", "continue", "return", "sizeof",
    # §5 constructs kept as keywords so diagnostics can name them exactly:
    "goto", "float", "double", "union", "unsigned",
})

DIGITS = set("0123456789")
HEX_DIGITS = set("0123456789abcdefABCDEF")
OCT_DIGITS = set("01234567")
ID_START = set("abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ_")
ID_CHARS = ID_START | DIGITS

# Pinned escape set (§3): \n \t \\ \" \0ddd \xHH. \' is accepted inside char
# literals only. Anything else — including \u — is an unknown escape.
_SIMPLE_ESCAPES = {"n": "\n", "t": "\t", "\\": "\\", '"': '"'}


def _esc_byte(v: int) -> str:
    """An escape's byte value 0-255 as one character. Values >= 0x80 stay a
    SINGLE byte: they are carried as their surrogate-escape code point so
    encode("utf-8", "surrogateescape") in the emitters yields one byte — the
    C rule (gcc: \\x80 is byte 0x80, never re-encoded as UTF-8)."""
    return chr(v) if v < 0x80 else chr(0xDC00 + v)


def char_value(s: str) -> int:
    """Char-literal int value; maps an escape byte carried as a surrogate
    (see _esc_byte) back to its 0-255 value."""
    o = ord(s)
    return o - 0xDC00 if 0xDC80 <= o <= 0xDCFF else o

_PUNCT = [
    "<<=", ">>=", "...",
    "->", "++", "--", "<<", ">>", "&&", "||", "==", "!=", "<=", ">=",
    "+=", "-=", "*=", "/=", "%=", "&=", "|=", "^=",
    "(", ")", "{", "}", "[", "]", ";", ",", ".", "+", "-", "*", "/", "%",
    "=", "!", "<", ">", "&", "|", "^", "~", "?", ":",
]


@dataclass(frozen=True)
class SourceLine:
    """One physical source line with its origin, so tokens keep true positions."""

    file: str
    line: int
    text: str


@dataclass(frozen=True)
class Token:
    """kind: id | kw | int | char | str | punct | eof; value = decoded literal."""

    kind: str
    text: str
    file: str
    line: int
    col: int
    value: object = None


class DiagError(Exception):
    """§8: file:line:col: <phase>: <message>, found '<token-or-construct>'."""

    def __init__(self, phase: str, file: str, line: int, col: int,
                 message: str, found: str):
        super().__init__(
            "{}:{}:{}: {}: {}, found '{}'".format(file, line, col, phase, message, found))
        self.phase = phase
        self.file = file
        self.line = line
        self.col = col
        self.message = message
        self.found = found


class Lexer:
    """Turns a list of SourceLine into a token list; block comments may span lines."""

    def __init__(self, lines):
        self.lines = list(lines)

    def tokenize(self) -> List[Token]:
        toks: List[Token] = []
        last = self.lines[-1] if self.lines else SourceLine("<input>", 1, "")
        in_block = False
        block_open = (last.file, 1, 1)
        for src in self.lines:
            i = 0
            text = src.text.rstrip("\r")
            n = len(text)
            while i < n:
                c = text[i]
                if in_block:
                    j = text.find("*/", i)
                    if j < 0:
                        i = n
                    else:
                        in_block = False
                        i = j + 2
                    continue
                if c in " \t\r\f\v":
                    i += 1
                    continue
                if text.startswith("//", i):
                    break
                if text.startswith("/*", i):
                    in_block = True
                    block_open = (src.file, src.line, i + 1)
                    i += 2
                    continue
                if c == "#":
                    raise DiagError("lex", src.file, src.line, i + 1,
                                    "stray '#' outside a preprocessor directive", c)
                if c in ID_START:
                    j = i
                    while j < n and text[j] in ID_CHARS:
                        j += 1
                    word = text[i:j]
                    kind = "kw" if word in KEYWORDS else "id"
                    toks.append(Token(kind, word, src.file, src.line, i + 1))
                    i = j
                    continue
                if c in DIGITS:
                    tok, i = self._number(src, text, i)
                    toks.append(tok)
                    continue
                if c in "\"'":
                    i = self._literal(src, text, i, toks)
                    # L1 (M1 R9, phase-6 parity): the pp leaves `"a" "b"`
                    # juxtaposed; merge immediately-adjacent string literals.
                    while i < n and text[i] == '"' and toks \
                            and toks[-1].kind == "str":
                        i = self._literal(src, text, i, toks)
                        nxt = toks.pop()
                        prev = toks.pop()
                        toks.append(Token("str", prev.text + nxt.text,
                                          prev.file, prev.line, prev.col,
                                          prev.value + nxt.value))
                    continue
                matched = None
                for p in _PUNCT:
                    if text.startswith(p, i):
                        matched = p
                        break
                if matched is None:
                    raise DiagError("lex", src.file, src.line, i + 1,
                                    "unclassifiable input", c)
                toks.append(Token("punct", matched, src.file, src.line, i + 1))
                i += len(matched)
        if in_block:
            raise DiagError("lex", block_open[0], block_open[1], block_open[2],
                            "unterminated block comment", "/*")
        toks.append(Token("eof", "<eof>", last.file, last.line, 1))
        return toks

    def _number(self, src: SourceLine, text: str, i: int):
        start = i
        n = len(text)
        if text[i] == "0" and i + 1 < n and text[i + 1] in "xX":
            i += 2
            j = i
            while j < n and text[j] in HEX_DIGITS:
                j += 1
            if j == i:
                raise DiagError("lex", src.file, src.line, start + 1,
                                "malformed hex integer literal", text[start:j + 1])
            i = j
        else:
            while i < n and text[i] in DIGITS:
                i += 1
            if i < n and text[i] == ".":
                i += 1
                while i < n and text[i] in DIGITS:
                    i += 1
                if i < n and text[i] in "eE":
                    i += 1
                    if i < n and text[i] in "+-":
                        i += 1
                    while i < n and text[i] in DIGITS:
                        i += 1
                raise DiagError("lex", src.file, src.line, start + 1,
                                "'float' is not in the subset (§4: int types only)",
                                text[start:i])
            if i < n and text[i] in "eE":
                j = i + 1
                if j < n and text[j] in "+-":
                    j += 1
                k = j
                while k < n and text[k] in DIGITS:
                    k += 1
                if k > j:
                    raise DiagError("lex", src.file, src.line, start + 1,
                                    "'float' is not in the subset (§4: int types only)",
                                    text[start:k])
        if i < n and (text[i] in ID_CHARS):
            j = i
            while j < n and text[j] in ID_CHARS:
                j += 1
            raise DiagError("lex", src.file, src.line, start + 1,
                            "malformed number literal", text[start:j])
        raw = text[start:i]
        value = int(raw, 16) if raw[:2].lower() == "0x" else int(raw, 10)
        return Token("int", raw, src.file, src.line, start + 1, value), i

    def _literal(self, src: SourceLine, text: str, i: int, toks: List[Token]) -> int:
        quote = text[i]
        col = i + 1
        n = len(text)
        i += 1
        buf: List[str] = []
        while True:
            if i >= n:
                raise DiagError("lex", src.file, src.line, col,
                                "unterminated {} literal".format(
                                    "string" if quote == '"' else "char"),
                                text[col - 1:i])
            c = text[i]
            if c == quote:
                i += 1
                break
            if c == "\\":
                if i + 1 >= n:
                    raise DiagError("lex", src.file, src.line, col,
                                    "unterminated escape in literal", text[col - 1:i])
                e = text[i + 1]
                if e == "x":
                    j = i + 2
                    k = j
                    while k < n and text[k] in HEX_DIGITS and k - j < 2:
                        k += 1
                    if k == j:
                        raise DiagError("lex", src.file, src.line, i + 1,
                                        "'\\x' escape needs at least one hex digit",
                                        text[i:k + 1])
                    buf.append(_esc_byte(int(text[j:k], 16)))
                    i = k
                    continue
                if e == "0":                   # \0ddd: leading \0 + up to 3
                    j = i + 2                  # octal digits (C rule, §3)
                    k = j
                    while k < n and text[k] in OCT_DIGITS and k - j < 3:
                        k += 1
                    buf.append(_esc_byte(int("0" + text[j:k], 8) & 0xFF))
                    i = k
                    continue
                if quote == "'" and e == "'":
                    buf.append("'")
                    i += 2
                    continue
                if e in _SIMPLE_ESCAPES:
                    buf.append(_SIMPLE_ESCAPES[e])
                    i += 2
                    continue
                raise DiagError("lex", src.file, src.line, i + 1,
                                "unknown escape '\\{}' is not in the pinned "
                                "escape set (§3)".format(e), "\\{}".format(e))
            buf.append(c)
            i += 1
        raw = text[col - 1:i]
        s = "".join(buf)
        if quote == '"':
            toks.append(Token("str", raw, src.file, src.line, col, s))
        else:
            if len(s) == 0:
                raise DiagError("lex", src.file, src.line, col,
                                "empty char literal", raw)
            if len(s) > 1:
                raise DiagError("lex", src.file, src.line, col,
                                "char literal too long", raw)
            toks.append(Token("char", raw, src.file, src.line, col, char_value(s)))
        return i


class TokenStream:
    """Peekable cursor over a token list with expect/accept helpers."""

    def __init__(self, toks: List[Token]):
        self.toks = toks
        self.i = 0

    def peek(self, k: int = 0) -> Token:
        j = self.i + k
        if j >= len(self.toks):
            j = len(self.toks) - 1
        return self.toks[j]

    def next(self) -> Token:
        t = self.peek()
        if t.kind != "eof":
            self.i += 1
        return t

    def at_punct(self, text: str, k: int = 0) -> bool:
        t = self.peek(k)
        return t.kind == "punct" and t.text == text

    def accept_punct(self, text: str) -> Optional[Token]:
        if self.at_punct(text):
            return self.next()
        return None

    def expect_punct(self, text: str, phase: str = "parse") -> Token:
        if not self.at_punct(text):
            t = self.peek()
            raise DiagError(phase, t.file, t.line, t.col,
                            "expected '{}'".format(text), t.text)
        return self.next()

    def expect_id(self, phase: str = "parse") -> Token:
        t = self.peek()
        if t.kind != "id":
            raise DiagError(phase, t.file, t.line, t.col,
                            "expected an identifier", t.text)
        return self.next()
