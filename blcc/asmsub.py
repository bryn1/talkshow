# LINES reason: the §3.5 TEMPLATE half of inline asm — how an operand's
# VALUE/ADDRESS/NAME is spelled (constant folding, static memory forms,
# modifier substitution) — is one concern; the emission machine that OWNS
# the frame/pool lives in blcc/asmgen.py (its AsmGenMixin derives from
# this mixin).
"""M3 inline-asm substitution & folding (contract plan-m3-asm.md v3.1 §3.5/
L4/L5 + the §2 address-vocabulary static folds).

  * _asm_fold/_asm_sym: the imm operand closure {int, symbol, symbol+off};
  * _asm_static/_asm_addr_base: the L3 static memory forms (locals
    -N(%rbp), globals sym+off(%rip), folded .field/[const] chains over the
    §2 address vocab `*p, a[i], s.f, &x, arr[i]`), everything else None →
    the computed base-reg route;
  * _asm_sub: %% / %= / %N / %[name] / %b/%w/%q/%h/%k size names,
    %c/%P/%s const forms and %l<label> — resolved through the M2-C1
    fn_labels map with the M2-C4 `asm:` diagnostic; unknown escapes LOUD
    naming the escape (L3).
"""
from __future__ import annotations

import re
from typing import Optional

from blcc import ast
from blcc.asmstmt import reg_name
from blcc.lexer import DiagError

_DIGRUN = re.compile(r"\d+")


class AsmSubMixin:

    def _asm_fold(self, e, node):
        """CONSTANT closure {int, symbol, symbol+off} (S5/L4) — parse-time
        `folded` first, then _fold_const, then static symbol refs."""
        for v in (getattr(node, "folded", None),):
            if v is not None:
                return v
        sym = self._asm_sym(e)
        if sym is not None:
            return sym
        try:
            return self._fold_const(e, node)     # enums, sizeof, unary/binary
        except DiagError:
            return None

    def _asm_sym(self, e):
        """&global / global (decayed array|fn) / sym+off → ('sym', name, off)
        or None."""
        node = e
        while isinstance(node, ast.Cast):
            node = node.operand
        if isinstance(node, ast.Unary) and node.op == "&":
            node = node.operand
        if isinstance(node, ast.Binary) and node.op in ("+", "-"):
            a, b = self._asm_sym(node.left), self._asm_const(node.right)
            if a is not None and b is not None:
                return ("sym", a[1], a[2] + (b if node.op == "+" else -b))
            a, b = self._asm_sym(node.right), self._asm_const(node.left)
            if a is not None and b is not None and node.op == "+":
                return ("sym", a[1], a[2] + b)
            return None
        if isinstance(node, ast.Ident):
            nm = node.name
            if nm in self.globals or nm in self.sigs:
                return ("sym", nm, 0)
            if nm in self.fn.statics:
                return ("sym", self.fn.statics[nm][0], 0)
        return None

    def _asm_const(self, e):
        for fn in (lambda: self._fold_const(e, e),):
            try:
                return fn()
            except DiagError:
                return None

    # ------------------------------------------------ static mem forms --
    def _asm_static(self, e) -> Optional[str]:
        """The ADDRESS of the lvalue as a static memory text, or None →
        the computed base-reg route (L3). Locals ride -N(%rbp), globals
        and statics sym+off(%rip) (the §2 address vocab: *p, a[i], s.f,
        &x, arr[i] close under folding)."""
        node = e
        while isinstance(node, ast.Cast):
            node = node.operand
        base = self._asm_addr_base(node)
        if base[0] is None:
            return None
        kind, val, off = base
        if kind == "frame":
            return "{}(%rbp)".format(val + off)
        return "{}{}(%rip)".format(val, _plus(off))

    def _asm_static_value(self, e) -> Optional[str]:
        """A plain-scalar ident's VALUE already lives in its slot → return
        that memory text (binds are handled by the §3.10 law)."""
        node = e
        while isinstance(node, ast.Cast):
            node = node.operand
        if not isinstance(node, ast.Ident):
            return None
        nm = node.name
        if nm in self.fn.regasms or nm in self.regasm_global:
            return None
        if nm in self.fn.statics:
            sym, sty = self.fn.statics[nm]
            if isinstance(self._untype(sty), ast.ArrayType):
                return None
            return "{}(%rip)".format(sym)
        if nm in self.fn.locals:
            off, lty = self.fn.locals[nm]
            if isinstance(self._untype(lty), ast.ArrayType):
                return None
            return "{}(%rbp)".format(off)
        if nm in self.globals:
            if isinstance(self._untype(self.globals[nm].type),
                          ast.ArrayType):
                return None
            return "{}(%rip)".format(nm)
        return None

    def _asm_addr_base(self, node):
        """Fold IDENT / .field / [const] chains: ((kind, base, delta) |
        None). kind "frame" → negative rbp int; "sym" → symbol text."""
        off = 0
        cur = node
        while True:
            if isinstance(cur, ast.Unary) and cur.op == "&":
                cur = cur.operand
                continue
            if isinstance(cur, ast.Ident):
                nm = cur.name
                if nm in self.fn.locals:
                    return ("frame", self.fn.locals[nm][0], off)
                if nm in self.fn.statics:
                    return ("sym", self.fn.statics[nm][0], -off)
                if nm in self.globals:
                    return ("sym", nm, -off)
                return (None, None, None)
            if isinstance(cur, ast.Select) and not cur.arrow:
                bty = self._asm_obj_base_ty(cur.base)
                if bty is None:
                    return (None, None, None)
                mo = self._asm_member_off(bty, cur.field, cur)
                if mo is None:
                    return (None, None, None)
                off += mo
                cur = cur.base
                continue
            if isinstance(cur, ast.Index):
                k = self._asm_const(cur.index)
                ety = self._asm_elem_ty(cur.base)
                if k is None or ety is None:
                    return (None, None, None)
                try:
                    off += k * self._size(ety, cur)
                except DiagError:
                    return (None, None, None)
                cur = cur.base
                continue
            return (None, None, None)

    def _asm_obj_base_ty(self, e):
        try:
            ty = self._decay(self._ty(e))
        except DiagError:
            return None
        return ty if isinstance(ty, ast.StructType) else None

    def _asm_member_off(self, sty, field, at):
        try:
            slots = self._struct_layout(sty, at)[2]
        except DiagError:
            return None
        for s in slots:
            if s[0] == field:
                return s[2]
        return None

    def _asm_elem_ty(self, e):
        try:
            ty = self._untype(self._decay(self._ty(e)))
        except DiagError:
            return None
        if isinstance(ty, ast.ArrayType):
            return self._decay(ty.inner)
        if isinstance(ty, ast.PtrType):
            return self._decay(ty.pointee)
        return None

    # ---------------------------------------------------- substitution --
    def _asm_sub(self, tmpl, ops, n) -> str:
        out: List[str] = []
        i = 0
        nops = len(ops)
        t = tmpl
        by_name = {o.node.name: o for o in ops if o.node.name}
        while i < len(t):
            c = t[i]
            if c != "%":
                out.append(c)
                i += 1
                continue
            nx = t[i + 1] if i + 1 < len(t) else ""
            if nx == "%":                # §3.5: %% → % (0 $-escapes needed)
                out.append("%")
                i += 2
                continue
            if nx == "=":                # %= unique id via existing counter
                self._label_n += 1
                out.append(".LL{}".format(self._label_n))
                i += 2
                continue
            j = i + 1
            mod = None
            if nx in "bwqhkclPs":
                mod = nx
                j += 1
            if j >= len(t):
                self._err(n, "dangling '%' at the end of the template "
                          "(§3 L3: '%%' is the escape)", "%", "asm")
            if t[j] == "[":
                k = t.find("]", j)
                if k < 0:
                    self._err(n, "unterminated '[name]' operand reference "
                              "(§3 L3)", "%[", "asm")
                ref: tuple = ("name", t[j + 1:k])
                j = k + 1
            elif t[j].isdigit():
                m = _DIGRUN.match(t, j)
                ref = ("num", int(m.group()))
                j = m.end()
            else:
                self._err(n, "template escape '%{}' is not in the §3.5 "
                          "modifier table (L3: unknown modifier LOUD names "
                          "it)".format(t[i + 1:j + 1]), t[i:j + 1], "asm")
            if mod == "l":               # %l LABELS only, never a reg (L5)
                if ref[0] == "num":
                    li = ref[1] - nops
                    if li < 0 or li >= len(n.labels):
                        self._err(n, "%l{} references no label — labels "
                                  "number AFTER the {} operands (§3 L5)"
                                  .format(ref[1], nops), "%l", "asm")
                    lab = n.labels[li]
                else:
                    lab = ref[1]
                out.append(self._asm_label(n, lab))
                i = j
                continue
            if ref[0] == "num":
                if ref[1] >= nops:
                    self._err(n, "%{} numbers past the operand list (§3 L0: "
                              "outputs then inputs)".format(ref[1]),
                              "%{}".format(ref[1]), "asm")
                o = ops[ref[1]]
            else:
                o = by_name.get(ref[1])
                if o is None:
                    self._err(n, "template names operand [{}] which the "
                              "statement does not declare (§3 L3)".format(
                                  ref[1]), ref[1], "asm")
            out.append(self._asm_print(o, mod, n))
            i = j
        return "".join(out)

    def _asm_label(self, at, name: str) -> str:
        """M2-C4: every asm-embedded label resolves through fn_labels; the
        diagnostic rides the `asm:` phase naming the label."""
        try:
            return self._label_ref(at, name)
        except DiagError as e:
            raise DiagError("asm", e.file, e.line, e.col,
                            "asm label '{}' not usable here: {}".format(
                                name, e.message), name) from None

    def _asm_print(self, o, mod, n) -> str:
        while o.form == "match":
            o = o.match
        if o.form == "mem":
            if mod is not None:
                self._err(n, "size/const modifier '%{}' on a MEMORY operand "
                          "(§3 L3 silent-size guard)"
                          .format(mod), "%{}".format(mod), "asm")
            if o.mem is not None:
                return o.mem
            return "(%{})".format(o.reg)
        if o.form == "imm":
            if mod in ("b", "w", "q", "h", "k"):
                self._err(n, "register size modifier '%{}' on an immediate "
                          "operand (§3.5)".format(mod), "%{}".format(mod),
                          "asm")
            if mod == "l":
                self._err(n, "%l on an immediate — labels only (§3 L5)",
                          "%l", "asm")
            v = o.imm
            if isinstance(v, tuple):     # {symbol, symbol+off} (L4)
                txt = "{}{}".format(v[1], _plus(v[2]))
                if mod in ("c", "P", "s"):
                    return txt
                return "$" + txt         # L4: plain `$sym` as lone i
            if mod == "s":
                self._err(n, "%s needs a SYMBOL operand (0 sites; §3.5)",
                          "%s", "asm")
            if mod in ("c", "P"):        # %c raw; %P call-int form
                return str(v)
            return "${}".format(v)
        # reg / bind operand:
        if mod in ("c", "P", "s", "l"):
            self._err(n, "'%{}' needs a constant/symbol/label operand, not "
                      "a register (§3.5)".format(mod), "%{}".format(mod),
                      "asm")
        return reg_name(o.reg, o.w, mod, at=o.node)


def _plus(off: int) -> str:
    if off == 0:
        return ""
    return "+{}".format(off) if off > 0 else "-{}".format(-off)
