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
            return esz * int(ty.size.value)
        self._err(at or self.tu, "cannot size this type", type(ty).__name__)

    def _decay(self, ty: ast.Node) -> ast.Node:
        if isinstance(ty, ast.ArrayType):
            return ast.PtrType(ty.file, ty.line, ty.col, ty.inner)
        return ty

    def _struct_layout(self, ty: ast.StructType, at) -> Tuple[Dict[str, int], int]:
        members = self.structs.get(ty.tag)
        if not members:
            self._err(at or ty, "undefined struct '{}' — only fully defined "
                      "structs are in the subset (§4)".format(ty.tag), ty.tag)
        off = 0
        offsets: Dict[str, int] = {}
        for m in members:
            msz = self._size(m.type, at or ty)
            align = min(max(msz, 1), 8)
            off = (off + align - 1) // align * align
            offsets[m.name] = off
            off += msz
        return offsets, _roundup8(off)

    # -- type-of-expression (only what addressing widths need) --------------------

    def _int(self, n) -> ast.BuiltinType:
        return ast.BuiltinType(n.file, n.line, n.col, "int")

    def _ty(self, n: ast.Node) -> ast.Node:
        if isinstance(n, (ast.IntLit, ast.CharLit)):
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
