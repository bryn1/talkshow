"""Type answers for codegen (ARCHITECTURE.md §4): sizes, the decay rule,
struct layout (§4 natural alignment), type-of-expression, and the §6 builtin
result kinds. This is the shared base of blcc.codegen.Codegen: every method
reads tables Codegen collects (structs/enums/globals/sigs/fn.locals/tu)."""
from __future__ import annotations

from typing import Dict, Tuple

from blcc import ast
from blcc.lexer import DiagError
from blcc.runtime import BUILTINS

TYPE_SIZE = {"char": 1, "short": 2, "int": 4, "long": 8, "void": 0}


def _roundup8(n: int) -> int:
    return (n + 7) & ~7


class TypeMap:

    # -- diagnostics ---------------------------------------------------------

    def _err(self, at, message: str, found: str, phase: str = "sema"):
        raise DiagError(phase, at.file, at.line, at.col, message, found)

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
        self._err(at or self.tu, "cannot size this type", type(ty).__name__)

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
                  type(n).__name__)

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
            n = len(init.items)
        elif isinstance(init, ast.StrLit) and isinstance(ty.inner, ast.BuiltinType) \
                and TYPE_SIZE[ty.inner.name] == 1:
            n = len(init.value.encode("utf-8", "surrogateescape")) + 1
        if n is None:
            return ty                       # scalar init: the loud §4 reject owns
        return ast.ArrayType(ty.file, ty.line, ty.col, ty.inner,
                             ast.IntLit(ty.file, ty.line, ty.col, n))

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

    def _ty(self, n: ast.Node) -> ast.Node:
        if isinstance(n, ast.IntLit):
            # §4: an unsuffixed decimal literal is int when it fits, else
            # long — the type sizeof and the usual conversions must see.
            if -2 ** 31 <= n.value < 2 ** 31:
                return self._int(n)
            return ast.BuiltinType(n.file, n.line, n.col, "long")
        if isinstance(n, ast.CharLit):
            return self._int(n)
        if isinstance(n, ast.StrLit):
            return ast.PtrType(n.file, n.line, n.col,
                               ast.BuiltinType(n.file, n.line, n.col, "char"))
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
        self._err(n, "cannot type this expression", type(n).__name__)

    def _binary_ty(self, n: ast.Binary) -> ast.Node:
        if n.op in ("==", "!=", "<", "<=", ">", ">=", "&&", "||"):
            return self._int(n)
        lt = self._decay(self._ty(n.left))
        rt = self._decay(self._ty(n.right))
        lp = isinstance(lt, ast.PtrType)
        rp = isinstance(rt, ast.PtrType)
        if n.op in ("+", "-") and (lp or rp):
            if n.op == "-" and lp and rp:
                return ast.BuiltinType(n.file, n.line, n.col, "long")
            return lt if lp else rt
        if n.op not in ("+", "-") and (lp or rp):
            self._err(n, "'{}' with a pointer operand is not in the subset (§4)"
                      .format(n.op), n.op)
        if n.op in ("<<", ">>"):
            # C: a shift's result type is its promoted LEFT operand alone.
            if isinstance(lt, ast.BuiltinType) and lt.name == "long":
                return lt
            return self._int(n)
        if isinstance(lt, ast.BuiltinType) and isinstance(rt, ast.BuiltinType) \
                and TYPE_SIZE[lt.name] < 8 and TYPE_SIZE[rt.name] < 8:
            return self._int(n)      # int (or narrower) op int -> int (§4)
        return ast.BuiltinType(n.file, n.line, n.col, "long")

    def _ident_ty(self, n: ast.Ident) -> ast.Node:
        loc = self.fn.locals.get(n.name)
        if loc is not None:
            return loc[1]
        if n.name in self.enums:
            return self._int(n)
        gd = self.globals.get(n.name)
        if gd is not None:
            return gd.type
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
