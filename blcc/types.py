"""Type answers for codegen (ARCHITECTURE.md §4): sizes, the decay rule,
struct layout (§4 natural alignment), type-of-expression, and the §6 builtin
result kinds. This is the shared base of blcc.codegen.Codegen: every method
reads tables Codegen collects (structs/enums/globals/sigs/fn.locals/tu)."""
from __future__ import annotations

from typing import Dict, List, Tuple

from blcc import ast
from blcc.lexer import DiagError
from blcc.runtime import BUILTINS

TYPE_SIZE = {
    # M2 §1 row 2 (gcc 11.4 LP64 measured): the full scalar family. Names are
    # the PARSER-NORMALIZED spellings (`signed int` → `int`, bare `signed`
    # → `int`; `signed char` keeps its distinct identity).
    "char": 1, "signed char": 1, "unsigned char": 1,
    "short": 2, "unsigned short": 2,
    "int": 4, "unsigned int": 4,
    "long": 8, "unsigned long": 8,
    "long long": 8, "unsigned long long": 8,
    "float": 4, "double": 8,          # STORAGE only (§1 row 14): arith LOUD
    "void": 0,
}
UNSIGNED_NAMES = frozenset({"unsigned char", "unsigned short", "unsigned int",
                            "unsigned long", "unsigned long long"})
_RANK = {"int": 1, "unsigned int": 1, "long": 2, "unsigned long": 2,
         "long long": 3, "unsigned long long": 3}
_UNSIGNED_OF = {"int": "unsigned int", "long": "unsigned long",
                "long long": "unsigned long long"}


def is_unsigned(ty) -> bool:
    return isinstance(ty, ast.BuiltinType) and ty.name in UNSIGNED_NAMES


def _roundup8(n: int) -> int:
    return (n + 7) & ~7


def what(n) -> str:
    """§8 literal-naming: the offending CONSTRUCT as found '...' — never a
    Python node class name (DA-c3 P1-1). Identifiers render as their own
    source token; the fallback never echoes a class name. Shared by the
    parser, sema and both codegens (module function: the mixins stay
    independent)."""
    if isinstance(n, ast.Ident):
        return n.name
    if isinstance(n, ast.IntLit):
        return "integer literal"
    if isinstance(n, ast.CharLit):
        return "char literal"
    if isinstance(n, ast.FloatLit):
        return "floating literal"
    if isinstance(n, ast.StrLit):
        return "string literal"
    if isinstance(n, ast.LabelAddr):
        return "&&label"
    if isinstance(n, ast.Call):
        return "call expression"
    if isinstance(n, ast.Cast):
        return "cast expression"
    if isinstance(n, ast.Sizeof):
        return "sizeof expression"
    if isinstance(n, ast.Binary):
        return "{} expression".format(n.op)
    if isinstance(n, ast.Unary):
        return "{} expression".format(n.op)
    if isinstance(n, ast.BuiltinType):
        return n.name
    if isinstance(n, ast.PtrType):
        return "pointer"
    if isinstance(n, ast.ArrayType):
        return "array"
    if isinstance(n, ast.StructType):
        return "struct {}".format(n.tag)
    if isinstance(n, ast.InitList):
        return "{"
    return "construct"


class TypeMap:

    # -- diagnostics ---------------------------------------------------------

    def _err(self, at, message: str, found: str, phase: str = "sema"):
        raise DiagError(phase, at.file, at.line, at.col, message, found)

    def _what(self, n) -> str:
        """§8 literal-naming — see module-level what()."""
        return what(n)

    # -- type sizing (§4 table lives HERE, never in ast.py) ---------------------

    def _size(self, ty: ast.Node, at=None) -> int:
        if isinstance(ty, ast.BuiltinType):
            if ty.name == "void":
                self._err(ty, "'sizeof(void)' is not in the subset (§4)", "void")
            return TYPE_SIZE[ty.name]
        if isinstance(ty, ast.PtrType):
            return 8
        if isinstance(ty, ast.StructType):
            return self._struct_layout(ty, at or ty)[1]
        if isinstance(ty, ast.ArrayType):
            esz = self._size(ty.inner, at)
            if ty.size is None:        # parameter: decays to pointer (§4)
                return 8
            return esz * self._arrlen(ty, at)
        self._err(at or self.tu, "cannot size this type", self._what(ty))

    # -- constant-folded array sizes (P1-2: §4 sizes are expressions) ------------

    def _fold_const(self, n, at) -> int:
        """Constant-fold an array-size expression (§4: integer literals, enum
        constants, + - * / % and parentheses; gcc's C rules)."""
        if isinstance(n, ast.IntLit):
            return n.value
        if isinstance(n, ast.CharLit):
            return n.value - 256 if n.value > 127 else n.value
        if isinstance(n, ast.Ident) and n.name in self.enums:
            return self.enums[n.name]
        if isinstance(n, ast.Unary) and n.op in ("-", "+"):
            v = self._fold_const(n.operand, at)
            return -v if n.op == "-" else v
        if isinstance(n, ast.Binary) and n.op in ("+", "-", "*", "/", "%"):
            a = self._fold_const(n.left, at)
            b = self._fold_const(n.right, at)
            if n.op == "+":
                return a + b
            if n.op == "-":
                return a - b
            if n.op == "*":
                return a * b
            if b == 0:
                self._err(at or n, "array size expression divides by zero (§4)",
                          n.op)
            q = abs(a) // abs(b)                 # C: truncate toward zero
            if (a < 0) != (b < 0):
                q = -q
            return q if n.op == "/" else a - b * q
        self._err(at or n, "array size must be a compile-time constant "
                  "expression (§4: literals, enum constants, + - * /)",
                  self._what(n))

    def _arrlen(self, ty: ast.ArrayType, at) -> int:
        n = self._fold_const(ty.size, at)
        if n < 0:
            self._err(at or ty.size, "array size must be positive (§4)", str(n))
        esz = self._size(ty.inner, at)
        if n > 2 ** 28 or esz * n > 2 ** 31:
            self._err(at or ty.size, "array size exceeds the implementation "
                      "limit of 2^28 elements / 2^31 bytes (§4)", str(n))
        return n

    def _sized_array_decl(self, ty: ast.Node, init, at) -> ast.Node:
        """§4 admits `T a[]` only with an initializer — the DECLARATION then
        takes its size FROM THE INITIALIZER (count x elem; a string array is
        strlen+1 bytes). The `size is None` proxy is legal only for array
        PARAMETERS; leaving an unsized array with storage made _slot emit an
        8-byte frame hole and _ex_ident load array content as a pointer."""
        if not isinstance(ty, ast.ArrayType) or ty.size is not None or init is None:
            return ty
        n = None
        if isinstance(init, ast.InitList):
            inner = ty.inner
            if isinstance(inner, ast.ArrayType) and init.items and \
                    not all(self._whole_elem(inner, it) for it in init.items):
                cap = self._leaf_cap(inner, at)      # brace-elided flat rows
                n = -(-self._leaf_count(init.items) // cap) if cap \
                    else len(init.items)
            else:
                n = len(init.items)
        elif isinstance(init, ast.StrLit) and isinstance(ty.inner, ast.BuiltinType) \
                and TYPE_SIZE[ty.inner.name] == 1:
            n = len(init.value.encode("utf-8", "surrogateescape")) + 1
        if n is None:
            return ty                       # scalar init: the loud §4 reject owns
        return ast.ArrayType(ty.file, ty.line, ty.col, ty.inner,
                             ast.IntLit(ty.file, ty.line, ty.col, n))

    # -- array initializer descent (§6.7.9 brace elision, DA-c3 P0-2) ----------

    def _whole_elem(self, inner, it) -> bool:
        """True when item `it` initializes ONE element of type `inner`
        wholesale: a brace list, or a string literal for a char array row."""
        if isinstance(it, ast.InitList):
            return True
        return isinstance(it, ast.StrLit) and isinstance(inner, ast.ArrayType) \
            and isinstance(inner.inner, ast.BuiltinType) \
            and TYPE_SIZE[inner.inner.name] == 1

    def _leaf_cap(self, ty, at) -> int:
        """Scalar slots one value of `ty` holds (0 = opaque aggregate)."""
        if isinstance(ty, ast.ArrayType):
            return self._arrlen(ty, at) * self._leaf_cap(ty.inner, at)
        return 0 if isinstance(ty, ast.StructType) else 1

    def _leaf_count(self, items) -> int:
        """Scalar values a (possibly nested) initializer stream carries."""
        tot = 0
        for it in items:
            if isinstance(it, ast.InitList):
                tot += self._leaf_count(it.items)
            elif isinstance(it, ast.StrLit):
                tot += len(it.value.encode("utf-8", "surrogateescape")) + 1
            else:
                tot += 1
        return tot

    def _fill_plan(self, ty: ast.ArrayType, items, at):
        """Walk an array's element stream in memory order honoring C brace
        elision (§6.7.9): an element consumes one item (brace list, char-row
        string, scalar) — or, when the element is itself an array and the
        item is not a whole-element init, draws items straight into its
        slots. When items run out the tail is ZERO-filled: partial init is
        legal C and must not inherit frame garbage (local) or exceed the
        object size (global). ty must be SIZED (_sized_array_decl owns that
        upstream). Returns (plan, items_consumed); plan entries are
        ('init', byte_off, elem_ty, item) | ('zero', byte_off, nbytes, None).
        Both blcc.data (byte runs) and blcc.codegen (frame stores) consume
        this — one elision rule, two writers (DA-c3 P0-2)."""
        plan: List[Tuple] = []
        pos = [0]

        def fill_arr(a_ty, base):
            n = self._arrlen(a_ty, at)
            esz = self._size(a_ty.inner, at)
            i = 0
            while i < n:
                off = base + i * esz
                if pos[0] >= len(items):
                    plan.append(("zero", off, esz * (n - i), None))
                    return
                it = items[pos[0]]
                inner = a_ty.inner
                if isinstance(inner, ast.ArrayType) \
                        and not self._whole_elem(inner, it):
                    mark = len(plan)
                    fill_arr(inner, off)      # elide: fill this row's slots
                    if len(plan) == mark:
                        return                # stream dry mid-row
                    i += 1
                    continue
                pos[0] += 1
                plan.append(("init", off, inner, it))
                i += 1

        fill_arr(ty, 0)
        return plan, pos[0]

    # -- alignments (P2-2: natural C layout, never a flat 8) ----------------------

    def _align(self, ty: ast.Node, at=None) -> int:
        """alignof: scalars/pointers by size, arrays by element, structs by
        their widest member (recursive)."""
        if isinstance(ty, ast.BuiltinType):
            return max(TYPE_SIZE[ty.name], 1)
        if isinstance(ty, ast.PtrType):
            return 8
        if isinstance(ty, ast.ArrayType):
            return self._align(ty.inner, at)
        if isinstance(ty, ast.StructType):
            members = self.structs.get(ty.tag)
            if not members:
                self._err(at or ty, "undefined struct '{}' — only fully defined "
                          "structs are in the subset (§4)".format(ty.tag), ty.tag)
            return max([self._align(m.type, at) for m in members] + [1])
        return 8

    def _decay(self, ty: ast.Node) -> ast.Node:
        if isinstance(ty, ast.ArrayType):
            return ast.PtrType(ty.file, ty.line, ty.col, ty.inner)
        return ty

    def _struct_layout(self, ty: ast.StructType, at) -> Tuple[Dict[str, int], int]:
        members = self.structs.get(ty.tag)
        if not members:
            self._err(at or ty, "undefined struct '{}' — only fully defined "
                      "structs are in the subset (§4)".format(ty.tag), ty.tag)
        # Natural C layout (P2-2): each member aligns to its own alignment;
        # the struct's align is the widest member's; size rounds to that.
        off = 0
        align = 1
        offsets: Dict[str, int] = {}
        for m in members:
            msz = self._size(m.type, at or ty)
            mal = self._align(m.type, at or ty)
            align = max(align, mal)
            off = (off + mal - 1) // mal * mal
            offsets[m.name] = off
            off += msz
        return offsets, (off + align - 1) // align * align

    # -- type-of-expression (only what addressing widths need) --------------------

    def _int(self, n) -> ast.BuiltinType:
        return ast.BuiltinType(n.file, n.line, n.col, "int")

    def _bt(self, n, name: str) -> ast.BuiltinType:
        return ast.BuiltinType(n.file, n.line, n.col, name)

    def _promote(self, ty: ast.Node) -> ast.Node:
        """Integer promotion (§2.2): the narrow types → int (unsigned short
        fits in int on LP64)."""
        if isinstance(ty, ast.BuiltinType) and ty.name in (
                "char", "signed char", "unsigned char", "short",
                "unsigned short"):
            return ast.BuiltinType(ty.file, ty.line, ty.col, "int")
        return ty

    def _uac(self, lt: ast.Node, rt: ast.Node, n) -> ast.BuiltinType:
        """Usual arithmetic conversions (§2.2, gcc 11.4 measured): after
        promotion — same sign: wider rank wins; unsigned rank >= signed
        rank: unsigned of the max rank; else the signed type (on LP64 a
        strictly-higher signed rank represents every value of the lower
        unsigned rank: long ⊇ uint, long long ⊇ ulong)."""
        lt, rt = self._promote(lt), self._promote(rt)
        ln = lt.name if isinstance(lt, ast.BuiltinType) else None
        rn = rt.name if isinstance(rt, ast.BuiltinType) else None
        if ln is None or rn is None:
            self._err(n, "arithmetic on a non-numeric type is not in the "
                      "subset (§4)", self._what(n))
        if ln in ("float", "double") or rn in ("float", "double"):
            self._err(n, "'float' arithmetic is DEFERRED — storage only "
                      "(§1 row 14)", self._what(n))
        if ln == rn:
            return self._bt(n, ln)
        lu, ru = ln in UNSIGNED_NAMES, rn in UNSIGNED_NAMES
        lr, rr = _RANK[ln], _RANK[rn]
        if lu == ru:
            return self._bt(n, ln if lr >= rr else rn)
        un, ur = (ln, lr) if lu else (rn, rr)
        sn, sr = (rn, rr) if lu else (ln, lr)
        return self._bt(n, un if ur >= sr else sn)

    def _ty(self, n: ast.Node) -> ast.Node:
        if isinstance(n, ast.IntLit):
            # §2.1 (M2): the literal's TYPE is the lexer's typed suffix/range
            # answer (hex may take unsigned early; decimal signed-first).
            return self._bt(n, n.itype)
        if isinstance(n, ast.CharLit):
            return self._int(n)
        if isinstance(n, ast.FloatLit):
            return self._bt(n, "float" if n.fsize == 4 else "double")
        if isinstance(n, ast.StrLit):
            return ast.PtrType(n.file, n.line, n.col,
                               ast.BuiltinType(n.file, n.line, n.col, "char"))
        if isinstance(n, ast.LabelAddr):
            # §2.6: `&&label` is void* (code address; _THIS_IP_ casts it to
            # unsigned long through the ordinary ptr->int path).
            return ast.PtrType(n.file, n.line, n.col,
                               ast.BuiltinType(n.file, n.line, n.col, "void"))
        if isinstance(n, ast.Sizeof):
            return ast.BuiltinType(n.file, n.line, n.col, "long")
        if isinstance(n, ast.Ident):
            return self._ident_ty(n)
        if isinstance(n, ast.Cast):
            return n.type
        if isinstance(n, ast.Unary):
            if n.op == "&":
                return ast.PtrType(n.file, n.line, n.col,
                                   self._decay(self._ty(n.operand)))
            if n.op == "*":
                base = self._decay(self._ty(n.operand))
                if not isinstance(base, ast.PtrType):
                    self._err(n, "'*' applied to a non-pointer (§4)", n.op)
                return base.inner
            if n.op == "!":
                return self._int(n)
            return self._ty(n.operand)
        if isinstance(n, ast.Binary):
            return self._binary_ty(n)
        if isinstance(n, ast.Call):
            name = n.callee.name
            if name in BUILTINS:
                kind = BUILTINS[name][1]
                return ast.BuiltinType(n.file, n.line, n.col,
                                       "long" if kind == "void" else kind)
            return self.sigs[name][1]
        if isinstance(n, (ast.Assign, ast.AssignOp)):
            return self._ty(n.target)
        if isinstance(n, ast.IncDec):
            return self._ty(n.operand)
        if isinstance(n, ast.Select):
            return self._member_ty(n)
        if isinstance(n, ast.Index):
            base = self._decay(self._ty(n.base))
            if not isinstance(base, ast.PtrType):
                self._err(n, "'[]' applied to a non-pointer/array (§4)", "[]")
            return base.inner
        self._err(n, "cannot type this expression", self._what(n))

    def _binary_ty(self, n: ast.Binary) -> ast.Node:
        if n.op in ("==", "!=", "<", "<=", ">", ">=", "&&", "||"):
            return self._int(n)
        lt = self._decay(self._ty(n.left))
        rt = self._decay(self._ty(n.right))
        lp = isinstance(lt, ast.PtrType)
        rp = isinstance(rt, ast.PtrType)
        if n.op in ("+", "-") and (lp or rp):
            if n.op == "-" and lp and rp:
                return self._bt(n, "long")
            return lt if lp else rt
        if n.op not in ("+", "-") and (lp or rp):
            self._err(n, "'{}' with a pointer operand is not in the subset (§4)"
                      .format(n.op), n.op)
        if n.op in ("<<", ">>"):
            # C: a shift's result type is its promoted LEFT operand alone.
            return self._promote(lt)
        return self._uac(lt, rt, n)

    def _ident_ty(self, n: ast.Ident) -> ast.Node:
        loc = self.fn.locals.get(n.name)
        if loc is not None:
            return loc[1]
        if n.name in self.enums:
            return self._int(n)
        gd = self.globals.get(n.name)
        if gd is not None:
            return gd.type
        if n.name in self.sigs:
            # §5: a function name used as a VALUE is a function pointer
            # (M4 DEFER). This is the ONE wall — _ty and _ex_ident share it
            # so any context (assign, call arg, return) names it identically.
            self._err(n, "'{}' is a function name used as a value — 'function "
                      "pointer' is not in the subset (§5)".format(n.name),
                      n.name)
        self._err(n, "'{}' undeclared — not a local, parameter, global or "
                     "enum constant".format(n.name), n.name)

    def _member_ty(self, n: ast.Select) -> ast.Node:
        base = self._struct_of(n)
        offsets, _ = self._struct_layout(base, n)
        if n.field not in offsets:
            self._err(n, "no member '{}' in struct '{}'".format(n.field, base.tag),
                      n.field)
        for m in self.structs[base.tag]:
            if m.name == n.field:
                return m.type
        self._err(n, "no member '{}' in struct '{}'".format(n.field, base.tag),
                  n.field)

    def _struct_of(self, n: ast.Select) -> ast.StructType:
        base = self._ty(n.base)
        if n.arrow:
            base = self._decay(base)
            if not isinstance(base, ast.PtrType):
                self._err(n, "'->' applied to a non-pointer (§4)", "->")
            base = base.inner
        if not isinstance(base, ast.StructType):
            self._err(n, "'.'/'->' applied to a non-struct value (§4)", n.field)
        return base

    def _member_off(self, n: ast.Select) -> int:
        base = self._struct_of(n)
        offsets, _ = self._struct_layout(base, n)
        if n.field not in offsets:
            self._err(n, "no member '{}' in struct '{}'".format(n.field, base.tag),
                      n.field)
        return offsets[n.field]
