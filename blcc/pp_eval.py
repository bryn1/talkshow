"""`#if` constant-expression evaluation (plan R5/R6 evaluation half).

Concern: an ALREADY-EXPANDED token list -> int. Precedence-climbing over the
R5 operator set; integer constants with suffixes (hex/oct/bin incl. gnu89
`0b`), char literals (gcc 11.4 answer: a byte >= 0x80 signs to negative,
multichar packs bytes into int), undefined identifiers -> 0, and the C
integer ladder (int -> long -> long long, unsigned wrap) evaluated in a
64-bit two's-complement model. Division by zero raises the §8 pp diagnostic
(gcc errors the same). Pure: no file IO, no macro table — `defined` handling
and macro expansion live in preproc/pp_expand; a `defined` surviving to here
is honored (operand -> 0/1 by the caller's pre-pass). stdlib-only.
"""
from __future__ import annotations

from typing import List, Optional

from blcc.lexer import DiagError

# (signedness, rank) → width; rank order for the C ladder. gcc cpp computes
# EVERY rank at 64-bit precision (see _number), so all widths are 64.
_INT, _LONG, _LL = 0, 1, 2
_WIDTH = {_INT: 64, _LONG: 64, _LL: 64}
_HEX = set("0123456789abcdefABCDEF")
_OCT = set("01234567")
_DIG = set("0123456789")
_ID = set("abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ_")
_IDC = _ID | _DIG
_ESC = {"n": 10, "t": 9, "r": 13, "a": 7, "b": 8, "f": 12, "v": 11,
        "\\": 92, "'": 39, '"': 34, "?": 63}


class _V:
    __slots__ = ("v", "u", "r")

    def __init__(self, v: int, u: bool, r: int):
        self.v, self.u, self.r = v, u, r

    def conv(self) -> "_V":
        bits = _WIDTH[self.r]
        m = (1 << bits) - 1
        if self.u:
            self.v &= m
        else:
            self.v &= m
            if self.v >= 1 << (bits - 1):
                self.v -= 1 << bits
        return self


def _wrap(v: int, u: bool, r: int) -> _V:
    return _V(v, u, r).conv()


def _ladder(au, ar, bu, br):
    """Usual arithmetic conversions in gcc's cpp model: all ranks are 64-bit
    wide, so mixed sign always takes the unsigned type."""
    return (au or bu), max(ar, br)


class _Parser:
    def __init__(self, toks: List[str], path: str, line: int):
        self.toks = [t for t in toks if t.strip()]
        self.i = 0
        self.path = path
        self.line = line

    def parse(self) -> int:
        if not self.toks:
            raise self._err("the #if expression has no tokens", "")
        v = self._expr(0)
        if self.i != len(self.toks):
            raise self._err("missing binary operator before token",
                            self.toks[self.i])
        return _wrap(v.v, v.u, v.r).v

    def _err(self, msg, found) -> DiagError:
        return DiagError("pp", self.path, self.line, 1,
                         "invalid constant-expression in #if: %s" % msg,
                         str(found))

    def _peek(self) -> Optional[str]:
        return self.toks[self.i] if self.i < len(self.toks) else None

    def _accept(self, *words) -> Optional[str]:
        t = self._peek()
        if t in words:
            self.i += 1
            return t
        return None

    def _expr(self, min_prec: int) -> _V:
        left = self._unary()
        while True:
            t = self._peek()
            prec = _PREC.get(t if t else "")
            if t is None or prec is None or prec < min_prec:
                return left
            self.i += 1
            if t in ("&&", "||"):          # both operands evaluated (gcc
                right = self._expr(prec + 1)   # cpp does not short-circuit
                if t == "&&":              # parse errors and computes ints)
                    left = _wrap(1 if (left.v and right.v) else 0, False, _INT)
                else:
                    left = _wrap(1 if (left.v or right.v) else 0, False, _INT)
                continue
            right = self._expr(prec + 1)
            left = self._binop(t, left, right)

    def _unary(self) -> _V:
        t = self._accept("+", "-", "~", "!")
        if t is None:
            return self._primary()
        v = self._unary()
        if t == "+":
            return v
        if t == "-":
            return _wrap(-v.v, v.u, v.r)
        if t == "~":
            return _wrap(~v.v, v.u, v.r)
        return _wrap(1 if v.v == 0 else 0, False, _INT)

    def _binop(self, op: str, a: _V, b: _V) -> _V:
        if op in ("<<", ">>"):
            u, r = a.u, a.r
            av, bv = _wrap(a.v, a.u, a.r), _wrap(b.v, b.u, b.r)
            cnt = bv.v % 256               # count >= width is UB territory;
            val = (av.v << cnt) if op == "<<" else (av.v >> cnt)
            return _wrap(val, u, r)
        u, r = _ladder(a.u, a.r, b.u, b.r)
        av = _wrap(a.v, u, r)
        bv = _wrap(b.v, u, r)
        if op in ("==", "!=", "<", "<=", ">", ">="):
            res = {"==": av.v == bv.v, "!=": av.v != bv.v, "<": av.v < bv.v,
                   "<=": av.v <= bv.v, ">": av.v > bv.v,
                   ">=": av.v >= bv.v}[op]
            return _wrap(1 if res else 0, False, _INT)
        if op == "+":
            return _wrap(av.v + bv.v, u, r)
        if op == "-":
            return _wrap(av.v - bv.v, u, r)
        if op == "*":
            return _wrap(av.v * bv.v, u, r)
        if op in ("/", "%"):
            if bv.v == 0:
                raise self._err("division by zero in #if",
                                " ".join(self.toks))
            q = abs(av.v) // abs(bv.v)
            if (av.v < 0) != (bv.v < 0):
                q = -q
            rem = av.v - q * bv.v
            return _wrap(q if op == "/" else rem, u, r)
        if op == "&":
            return _wrap(_twos(a) & _twos(b), u, r)
        if op == "|":
            return _wrap(_twos(a) | _twos(b), u, r)
        if op == "^":
            return _wrap(_twos(a) ^ _twos(b), u, r)
        raise self._err("unknown operator", op)

    def _primary(self) -> _V:
        t = self._peek()
        if t is None:
            raise self._err("the #if expression ends after a binary operator",
                            "")
        if t == "(":
            self.i += 1
            v = self._expr(0)
            if self._accept(")") is None:
                raise self._err("unbalanced parentheses", "(")
            return v
        self.i += 1
        if t[0] in _DIG:
            return _number(t, self)
        if t[0] == "'":
            return _char(t, self)
        if t[0] == '"':
            raise self._err("string literal is not valid in a #if expression",
                            t)
        if t[0] in _ID:
            return _wrap(0, False, _INT)   # undefined identifier -> 0 (R6)
        raise self._err("missing binary operator before token", t)


_PREC = {"||": 1, "&&": 2, "|": 3, "^": 4, "&": 5,
         "==": 6, "!=": 6, "<": 7, ">": 7, "<=": 7, ">=": 7,
         "<<": 8, ">>": 8, "+": 9, "-": 9, "*": 10, "/": 10, "%": 10}


def _twos(v: _V) -> int:
    bits = _WIDTH[v.r]
    return v.v & ((1 << bits) - 1)


def _number(raw: str, p: _Parser) -> _V:
    s = raw
    u = False
    lcount = 0
    j = len(s)
    while j > 0 and s[j - 1] in "uUlL":
        c = s[j - 1]
        if c in "uU":
            if u:
                raise p._err("bad integer suffix", raw)
            u = True
        else:
            lcount += 1
            if lcount > 2:
                raise p._err("bad integer suffix", raw)
        j -= 1
    body = s[:j]
    low = body.lower()
    try:
        if low.startswith("0x"):
            v = int(body, 16)
            assert body[2:] and all(c in _HEX for c in body[2:])
        elif low.startswith("0b"):
            v = int(body, 2)
            assert all(c in "01" for c in body[2:])
        elif body[0] == "0" and len(body) > 1:
            v = int(body, 8)
            assert all(c in _OCT for c in body)
        else:
            v = int(body, 10)
    except (ValueError, AssertionError):
        raise p._err("invalid pp-number", raw)
    # gcc cpp arithmetic model (probed, gcc 11.4): EVERY integer is 64-bit —
    # int does NOT wrap at 32 (`0x7fffffff + 1 < 0` is FALSE in cpp, TRUE in
    # the compiler); unsigned constants wrap at 2^64, signed at 2^63. A
    # literal too big for signed 64 silently becomes unsigned.
    if v > (1 << 64) - 1:
        if low.startswith("0x") or low.startswith("0b") or body[0] == "0":
            v &= (1 << 64) - 1
        else:
            raise p._err("integer constant is too large for its type", raw)
    if not u and v > (1 << 63) - 1:
        u = True
    return _wrap(v, u, _LL)


def _char(raw: str, p: _Parser) -> _V:
    body = raw[1:-1] if raw.endswith("'") and len(raw) >= 2 else raw[1:]
    if not body:
        raise p._err("empty character constant", raw)
    bytes_: List[int] = []
    i = 0
    while i < len(body):
        c = body[i]
        if c != "\\":
            bytes_.append(ord(c) & 0xFF if ord(c) < 0x8000 else ord(c))
            i += 1
            continue
        i += 1
        if i >= len(body):
            raise p._err("unterminated escape in character constant", raw)
        e = body[i]
        if e in _ESC:
            bytes_.append(_ESC[e])
            i += 1
        elif e == "x":
            j = i + 1
            while j < len(body) and body[j] in _HEX:
                j += 1
            if j == i + 1:
                raise p._err("\\x needs a hex digit", raw)
            bytes_.append(int(body[i + 1:j], 16) & 0xFF)
            i = j
        elif e in _OCT:
            j = i
            while j < len(body) and body[j] in _OCT and j - i < 3:
                j += 1
            bytes_.append(int(body[i:j], 8) & 0xFF)
            i = j
        else:
            raise p._err("unknown escape", "\\" + e)
    if len(bytes_) == 1:
        return _wrap(bytes_[0], False, _INT) if bytes_[0] < 0x80 else \
            _wrap(bytes_[0] - 0x100, False, _INT)     # gcc: \\xff == -1
    v = 0
    for b in bytes_:
        v = v << 8 | b & 0xFF
    return _wrap(v, False, _INT)


def eval_tokens(toks: List[str], path: str, line: int) -> int:
    """Evaluate an expanded #if token list to its truth value (1/0)."""
    v = _Parser(toks, path, line).parse()
    return 0 if v == 0 else 1
