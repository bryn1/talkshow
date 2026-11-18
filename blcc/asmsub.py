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

    def _asm_ctype(self, e):
        """C type of the expression, unqualified and DECAYED, or None when
        the typer refuses (the caller's wall answers). M4 W-N (MC 12687):
        the fold's ONE type check — called once per recursion at the fold
        ENTRY, never re-peeked from the shape."""
        try:
            return self._untype(self._decay(self._ty(e)))
        except DiagError:
            return None

    def _asm_esz(self, ty, at):
        """Element size a pointer-typed fold scales by. `void*` arithmetic
        is the GNU esz-1 extension (measured `(void*)&g+4 -> $g+4`);
        anything unsizable refuses (None)."""
        if isinstance(ty, ast.PtrType):
            inner = self._untype(ty.inner)
            if isinstance(inner, ast.BuiltinType) and inner.name == "void":
                return 1
            try:
                n = self._size(inner, at)
            except DiagError:
                return None
            return n if n else None
        return None

    def _asm_sym(self, e, narrow=False):
        """CONSTANT closure {int, symbol, symbol+off} (S5/L4) read through
        the C TYPE of every arm — M4 W-N (MC 12687) replaced the W-M
        shape-reading. One type check per recursion at the ENTRY decides
        which arms are OPEN: an ADDRESS-typed spelling (or the `&` form)
        opens the symbol/Index arms and Scales pointer arithmetic by the
        element size; an integer-typed spelling opens the VALUE arm for a
        const global and closes the address rvalue in; a TRUNCATING
        (<8-byte) integer cast of an address refuses (gcc LOUD). Returns
        ('sym', name, off) | int | None — None is the honest 'i' wall.
        THE LAW (measured, .tmp/m4-wn/out/measure-wn*.txt):
          F-1  bare pointer difference = ELEMENT count (esz divides);
               (long)-cast difference = BYTES; the compound difference
               COMPOSES as int arithmetic (no ICE);
          F-2  a bare element rvalue `gs[3]` is NOT a constant (the
               Index arm is an ADDRESS arm — it needs the address);
          F-3  `&c` answers the ADDRESS ($c), the value arm never fires
               through the `&`; bare `c` keeps the VALUE ($5);
          F-4  `&gs[3]+1` adds ONE ELEMENT; casts scale by THEIR pointee;
          +    a non-const scalar global under "i" refuses — the folder
               may not answer `$sym` (the address) where gcc is LOUD."""
        ty = self._asm_ctype(e)
        addr = isinstance(ty, ast.PtrType)       # this expression IS an address
        node = e
        while isinstance(node, ast.Cast):
            cty = self._asm_ctype(node)
            if isinstance(cty, ast.BuiltinType):
                try:
                    if self._size(cty, node) < 8 and not narrow:
                        # truncating cast: gcc LOUD — EXCEPT as one side
                        # of a same-symbol difference, the only place
                        # gcc tolerates it (measured; the '-' arm asks
                        # for `narrow` explicitly).
                        return None
                except DiagError:
                    return None
            node = node.operand
        if isinstance(node, ast.Unary) and node.op == "&":
            node = node.operand
            addr = True
        if isinstance(node, ast.Binary) and node.op in ("+", "-"):
            return self._asm_sym_bin(node)
        if isinstance(node, ast.Index):
            # ARRAY-ELEMENT addresses of a global/static array fold at
            # `sym + k*esz` (W-M family arm 1, now type-gated). The
            # element size is the pointee's OWN _size law; a non-constant
            # index or a non-address spelling refuses (F-2; the 2-D
            # `&mm[1][2]` honest wall rides the nested spelling).
            if not addr:
                return None
            k = self._asm_const(node.index)
            if k is None:
                return None
            bsym = self._asm_sym(node.base)
            if not (isinstance(bsym, tuple) and bsym[0] == "sym"):
                return None
            bty = self._asm_ctype(node.base)
            esz = self._asm_esz(bty, node)
            if esz is None:
                return None
            return ("sym", bsym[1], bsym[2] + k * esz)
        if isinstance(node, ast.Ident):
            # Ident arms read the DECLARED type, not the name table alone.
            nm = node.name
            g = self.globals.get(nm)
            stc = self.fn.statics.get(nm) if self.fn else None
            if addr:
                # address-of ANY object/function with a symbol answers
                # the symbol — scalar or not (`&gi` -> `$gi`, `&c` -> `$c`).
                if g is not None or nm in self.sigs:
                    return ("sym", nm, 0)
                if stc is not None:
                    return ("sym", stc[0], 0)
                return None
            if g is not None:
                qt, spine = self._split_q(g.type)
                spine = self._untype(spine)
                if isinstance(spine, ast.ArrayType):
                    return ("sym", nm, 0)        # decayed array address
                if ("const" in qt and g.init is not None
                        and isinstance(spine, ast.BuiltinType)
                        and spine.name not in ("void", "float", "double")):
                    v = self._asm_const(g.init)  # F-3 VALUE arm (bare spelling)
                    if v is not None:
                        return v
                return None                      # non-const scalar: gcc LOUD
            if nm in self.sigs:
                return ("sym", nm, 0)            # function address
            if stc is not None:
                # file- or fn-scope static: the value fold has no init in
                # the statics table — the address still folds (the `&`
                # arm answered it above); a bare fn-static const int
                # answers the symbol (honest wall, named in the card).
                return ("sym", stc[0], 0)
            return None
        return None

    def _asm_sym_bin(self, node):
        """`+`/`-` arms of the fold closure, type-read (M4 W-N): a
        pointer-typed side SCALES the constant by its element size; a
        same-symbol difference divides by it when the difference is
        pointer-typed (ELEMENTS, F-1) and keeps the byte answer when an
        integer cast rode it; folded ints COMPOSE (no ICE on
        `&gs[4]-&gs[0]-1`); a difference ACROSS objects stays gcc's own
        LOUD (`impossible constraint in \'asm\'`, rc1 — the twin pin in
        tests/test_core_m4wm1.py)."""
        op = node.op
        lt = self._asm_ctype(node.left)
        rt = self._asm_ctype(node.right)
        lptr = isinstance(lt, ast.PtrType)
        rptr = isinstance(rt, ast.PtrType)
        lv = self._asm_sym(node.left)
        if lv is None:
            lv = self._asm_const(node.left)      # pure-int trees fold
        rv = self._asm_sym(node.right)
        if rv is None:
            rv = self._asm_const(node.right)
        lsym = isinstance(lv, tuple) and lv[0] == "sym"
        rsym = isinstance(rv, tuple) and rv[0] == "sym"
        lint = isinstance(lv, int)
        rint = isinstance(rv, int)
        if op == "-":
            if lsym and rsym:
                if lv[1] != rv[1]:
                    return None                  # cross-symbol: gcc LOUD
                d = lv[2] - rv[2]
                if lptr:
                    esz = self._asm_esz(lt, node)
                    return d // esz if esz else None
                return d                         # cast form: BYTES
            if lsym and rint:
                if lptr:
                    esz = self._asm_esz(lt, node)
                    if esz is None:
                        return None
                    return ("sym", lv[1], lv[2] - rv * esz)
                return ("sym", lv[1], lv[2] - rv)
            if lint and rint:
                return lv - rv                   # COMPOSES (was an ICE)
            if not (lsym or rsym or lint or rint):
                # The truncating-cast PAIR — `(int)&gs[4] - (int)&gs[0]`
                # is the ONE placement gcc folds (measured $16; every
                # other narrow spelling is LOUD, pinned by the pair legs).
                a = self._asm_sym(node.left, narrow=True)
                b = self._asm_sym(node.right, narrow=True)
                if (isinstance(a, tuple) and isinstance(b, tuple)
                        and a[0] == "sym" and b[0] == "sym"
                        and a[1] == b[1]):
                    return a[2] - b[2]
            return None
        # '+'
        if lsym and rint:
            if lptr:
                esz = self._asm_esz(lt, node)
                if esz is None:
                    return None
                return ("sym", lv[1], lv[2] + rv * esz)
            return ("sym", lv[1], lv[2] + rv)
        if rsym and lint:
            if rptr:
                esz = self._asm_esz(rt, node)
                if esz is None:
                    return None
                return ("sym", rv[1], rv[2] + lv * esz)
            return ("sym", rv[1], rv[2] + lv)
        if lint and rint:
            return lv + rv
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
                    # M4 W-N (MC 12687): the delta sign was FLIPPED here
                    # (M3-A seed): `gs[3]` materialized `gs-12` — a SILENT
                    # wrong address the %P table flushed out. The chain
                    # accumulates `off` positively for .field and [k];
                    # sym and frame answer the SAME sign.
                    return ("sym", self.fn.statics[nm][0], off)
                if nm in self.globals:
                    return ("sym", nm, off)
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
            return self._decay(ty.inner)
        return None

    # ---------------------------------------------------- substitution --
    def _asm_sub(self, tmpl, ops, n) -> str:
        out: List[str] = []
        i = 0
        nops = len(ops)
        t = tmpl
        by_name = {o.node.name: o for o in ops if o.node.name}
        pct_id = None                    # %=: ONE id per asm STATEMENT
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
            if nx == "=":                # §3.5 %= — gcc-11.4 law, measured
                # MC 12499 (3 occurrences in ONE statement print the SAME
                # id; ids differ per statement, byte-stable across
                # recompiles). A label DEFINED by one %= and BACK-REFERENCED
                # by another in the same template must agree — mint once.
                if pct_id is None:
                    self._label_n += 1
                    pct_id = ".LL{}".format(self._label_n)
                out.append(pct_id)
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
        if o.ci.cls == "cc":             # §cc: gcc law (measured MC 12499):
            self._err(n, "invalid use of asm flag output — a '=@cc…' "
                      "operand never appears in the template (oracle rc1: "
                      "invalid 'asm': invalid use of asm flag output)",
                      "@cc", "asm")
        if o.form == "mem":
            if mod == "P":
                # M4 W-N (MC 12687): `%P` PRINTS THE ADDRESS — the text
                # the plain operand already prints, with no `$` (measured
                # gcc law: `g`, `12+gs`, the frame `-8(%rsp)`; the SAME
                # answer the §3 L3 materializer owns — one printer, one
                # text). Guarded by gcc's OWN refusals: a `"p"` operand
                # whose text is a FRAME address (gcc rc1 'invalid
                # expression as operand' — a runtime address is not a
                # constant) and any COMPUTED operand (no text exists;
                # the named honest wall for computed "m", volume 0).
                if o.mem is not None and \
                        not (o.ci.cls == "p" and "%rbp" in o.mem):
                    return o.mem
                self._err(n, "'%P' needs a CONSTANT address operand — no"
                          " address text here (gcc law MC 12687: frame/"
                          "computed addresses are rc1 or unprintable)",
                          "%P", "asm")
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
        if mod == "P":
            # M4 W-N: `%P` on a REGISTER operand prints the register —
            # measured gcc (`"r"(x)` under %P → `%rax`), NOT loud.
            return reg_name(o.reg, o.w, None, at=o.node)
        if mod in ("c", "s", "l"):
            self._err(n, "'%{}' needs a constant/symbol/label operand, not "
                      "a register (§3.5)".format(mod), "%{}".format(mod),
                      "asm")
        return reg_name(o.reg, o.w, mod, at=o.node)


def _plus(off: int) -> str:
    if off == 0:
        return ""
    return "+{}".format(off) if off > 0 else "-{}".format(-off)
