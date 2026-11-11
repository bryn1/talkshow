"""Global data emission for blcc (ARCHITECTURE.md §4): constant evaluation of
file-scope initializers (integer/char constants, address-of-global, brace
lists; a string literal is a §5-style diagnostic naming the construct) and
their .data/.bss assembly lines — all-zero objects go to .bss, the rest to
.data. Mixin of blcc.codegen.Codegen, which provides
globals/enums/structs/strings tables plus _size/_decay/_struct_layout/_err/
_str_label (strings interning stays on Codegen with the rodata pool)."""
from __future__ import annotations

from typing import List, Tuple

from blcc import ast


class DataEmitter:
    def _const(self, n: ast.Node):
        """-> int | ('lab', label) for address-of-global constants."""
        if isinstance(n, ast.IntLit):
            return n.value
        if isinstance(n, ast.CharLit):
            return n.value - 256 if n.value > 127 else n.value
        if isinstance(n, ast.Ident) and n.name in self.enums:
            return self.enums[n.name]
        if isinstance(n, ast.Unary) and n.op == "-":
            v = self._const(n.operand)
            if isinstance(v, int):
                return -v
        if isinstance(n, ast.Unary) and n.op == "&":
            if isinstance(n.operand, ast.Ident) and n.operand.name in self.globals:
                return ("lab", n.operand.name)
        if isinstance(n, ast.StrLit):
            self._err(n, "'string literal in global initializer' is not in the "
                      "§4 set (integer/char constant or address-of-global; "
                      "string bytes belong in a char array initializer)",
                      "string literal")
        self._err(n, "global initializer must be an integer/char constant or "
                  "address-of-global (§4)", type(n).__name__)

    def _bytes_of(self, ty: ast.Node, init, at) -> List[Tuple[str, int]]:
        """-> list of ('b', byte) | ('q', label) covering size(ty) bytes."""
        if isinstance(ty, (ast.BuiltinType, ast.PtrType)):
            sz = self._size(ty, at)
            if init is None:
                return [("b", 0)] * sz
            if isinstance(init, ast.InitList):
                self._err(init, "brace initializer for a scalar (§4)", "{")
            v = self._const(init)
            if isinstance(v, int):
                return [("b", (v >> 8 * i) & 255) for i in range(sz)]
            if sz != 8:
                self._err(init, "address initializer needs an 8-byte pointer "
                          "type (§4)", "initializer")
            return [("q", v[1])]
        if isinstance(ty, ast.ArrayType):
            esz = self._size(ty.inner, at)
            n = 0 if ty.size is None else self._arrlen(ty, at)
            if isinstance(init, ast.StrLit):
                raw = init.value.encode("utf-8", "surrogateescape") + b"\0"
                if ty.size is not None and len(raw) > n:
                    self._err(init, "string initializer longer than char[{}] (§4)"
                              .format(n), "initializer")
                return ([("b", b) for b in raw]
                        + [("b", 0)] * (n - len(raw)))
            items = init.items if isinstance(init, ast.InitList) else \
                ([] if init is None else None)
            if items is None:
                self._err(init, "array initializer must be a brace list or "
                          "string literal (§4)", type(init).__name__)
            if len(items) > n:
                self._err(init, "too many initializers for {} elements (§4)"
                          .format(n), "initializer")
            out: List[Tuple[str, int]] = []
            for it in items:
                out.extend(self._bytes_of(ty.inner, it, at))
            return out + [("b", 0)] * max(0, n * esz - len(out))
        if isinstance(ty, ast.StructType):
            offsets, total = self._struct_layout(ty, at)
            members = self.structs[ty.tag]
            items = init.items if isinstance(init, ast.InitList) else \
                ([] if init is None else None)
            if items is None or len(items) > len(members):
                self._err(init, "struct initializer must be a brace list of "
                          "member constants (§4)", "initializer")
            out = []
            for i, m in enumerate(members):
                out.extend([("b", 0)] * (offsets[m.name] - len(out)))
                if i < len(items):
                    out.extend(self._bytes_of(m.type, items[i], at))
            return out + [("b", 0)] * (total - len(out))
        self._err(at or self.tu, "cannot initialize this type", type(ty).__name__)

    def _emit_global(self, vd: ast.VarDecl):
        items = self._bytes_of(vd.type, vd.init, vd)
        # .align precedes the label (.data AND .bss): a label written before
        # its padding binds to the pre-padding address, not to the bytes.
        if all(k == "b" and v == 0 for k, v in items):
            return "bss", ["    .align 8", "{}:".format(vd.name),
                           "    .zero {}".format(len(items))]
        lines = ["    .align 8", "{}:".format(vd.name)]
        acc: List[int] = []

        def flush():
            if acc:
                lines.append("    .byte {}".format(
                    ",".join(str(b) for b in acc)))
                acc.clear()

        for kind, val in items:
            if kind == "b":
                acc.append(val)
            else:
                flush()
                lines.append("    .quad {}".format(val))
        flush()
        return "data", lines


