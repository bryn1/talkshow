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


class _AIDeferred:
    """M4 W-AI (MC 12404.2.153 / card 12846): the THIRD imm-context
    sentinel — the fold was asked in a context that NEVER exists: the
    never-expanded standalone copy of a zero-site `static inline`. Not a
    value, not None: an `'i'`-class operand here was NEVER decided by a
    caller, so it DEFERS to materialization instead of refusing (the
    expansion-time door the walk owes, cpufeature.h:187)."""
    pass


_AI_DEFERRED = _AIDeferred()


def _ai_uses_param(e, names):
    """True when the operand expression mentions one of the copy's param
    names — the SAME name-keyed lookup the shipped imm-map already rides
    (`self._inl_imm.get(e.name)` in `_asm_fold`), widened to the composed
    fold route. OPERAND-anchored, never body-anchored: a LOCAL under
    `'i'` inside a dead copy keeps its refusal (r3 plant measures the
    alternative)."""
    import dataclasses
    stack = [e]
    while stack:
        x = stack.pop()
        if not dataclasses.is_dataclass(x):
            continue
        if isinstance(x, ast.Ident) and x.name in names:
            return True
        for f in dataclasses.fields(x):
            v = getattr(x, f.name, None)
            for y in (v if isinstance(v, (tuple, list)) else (v,)):
                if dataclasses.is_dataclass(y):
                    stack.append(y)
    return False


class AsmSubMixin:

    def _asm_fold(self, e, node):
        """CONSTANT closure {int, symbol, symbol+off} (S5/L4) — parse-time
        `folded` first, then _fold_const, then static symbol refs."""
        for v in (getattr(node, "folded", None),):
            if v is not None:
                return v
        if self._inl_imm and isinstance(e, ast.Ident):
            # M4 W-P (MC 12705): a spliced-body param whose caller arg
            # folded — the imm answer the ARGUMENT gives at the call
            # (gcc's post-inline literal; row i03: `.word 245`). The
            # closure itself is UNTOUCHED: only this IDENT resolution
            # gained a source.
            v = self._inl_imm.get(e.name)
            if v is not None:
                return v
        sym = self._asm_sym(e)
        if sym is not None:
            return sym
        try:
            return self._fold_const(e, node)     # enums, sizeof, unary/binary
        except DiagError:
            dfd = getattr(self, "_inl_defer_fd", None)
            if dfd and _ai_uses_param(e, dfd):
                return _AI_DEFERRED              # M4 W-AI: no ctx ever
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
            # W-U COMMIT-3 (MC 12739): a spliced callee LOCAL of this
            # name means the caller's static is NOT this operand; the
            # frame answer below (or the plain local path) owns it.
            stc = self.fn.statics.get(nm) if (
                self.fn is not None and nm not in self.fn.locals) else None
            if addr:
                # address-of ANY object/function with a symbol answers
                # the symbol — scalar or not (`&gi` -> `$gi`, `&c` -> `$c`).
                # M4 W-O S27 (MC 12690): a FUNCTION folds as an address
                # ONLY when DEFINED in this TU — gcc on a declared-only
                # `&f` answers LOUD 'impossible constraint' (measured
                # s27c); the tip answered `$f` silently through
                # `nm in self.sigs`. The ADDRESS fold of an OBJECT
                # (global/static) stays qualifier-blind (S19: `&vc` is
                # $vc rc0, measured s19d).
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
                # M4 W-O S19 (MC 12690): the VALUE fold reads the
                # QUALIFIER — a VOLATILE-qualified const is gcc LOUD
                # 'impossible constraint' (gate rp19 + bare volatile,
                # measured) and the tip printed `$42` silently.
                if ("const" in qt and "volatile" not in qt
                        and g.init is not None
                        and isinstance(spine, ast.BuiltinType)
                        and spine.name not in ("void", "float", "double")):
                    v = self._asm_const(g.init)  # F-3 VALUE arm (bare spelling)
                    if v is not None:
                        return v
                return None                      # non-const scalar: gcc LOUD
            if nm in self.sigs:
                # M4 W-O S27 DISCOVERY (MC 12690, own hands): at the
                # KERNEL recipe (-fno-pic in) gcc folds $fn under "i"
                # for DEFINED and declared-only functions alike, both
                # spellings (`f` and `&f` — probes u2/u3/s27c rc0);
                # 'impossible constraint' is the PIE-posture answer
                # (same probes, -fPIE/default-pie). blcc is static
                # non-PIE by the §6 link law — the W-N fold stays the
                # REC-pair answer; the gate's S27 LOUD capture was
                # measured in a PIE context (its leg1 harness carries
                # no kernel REC flags — grep-verified), named in the
                # verdict as the claim-repair exception.
                return ("sym", nm, 0)            # function address
            if stc is not None:
                # M4 W-O S18 (MC 12690): the BARE fn-static spelling
                # folds by the SAME ONE type law as the global arm —
                # const, non-volatile, scalar spine, constant
                # initializer answers the VALUE (gcc `movl $7`,
                # measured; the tip printed the symbol `$sc.0` — a
                # silent wrong value, gate rp18: gcc exit 42, blcc
                # exit garbage). Arrays keep the DECAYED-SYMBOL arm
                # ($nm.N / the `__func__` leg); a non-const bare
                # static now REFUSES (the `gi` law made symmetric —
                # gcc folds it only by dataflow propagation, which
                # the parse-time fold cannot re-derive: named
                # LOUD-DIV twin, volume 0 in the 706). The W-N
                # "no init in the statics table" note is DEAD — the
                # table carries the init expression since this card.
                spine2 = self._untype(stc[1])    # layout type: sized, bare
                qt3 = self._split_q(stc[3])[0] if len(stc) > 3 else ()
                if isinstance(spine2, ast.ArrayType):
                    return ("sym", stc[0], 0)    # decayed array address
                if (len(stc) > 2 and stc[2] is not None
                        and "const" in qt3 and "volatile" not in qt3
                        and isinstance(spine2, ast.BuiltinType)
                        and spine2.name not in ("void", "float", "double")):
                    v = self._asm_const(stc[2])  # S18 VALUE fold
                    if v is not None:
                        return v
                return None
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

    def _asm_p_text_ok(self, e) -> bool:
        """May a `'p'` operand's VALUE be printed as a STATIC text at all?
        'p' takes the VALUE of the expression; that value is printable
        only where it IS a static address — an `&object` expression or a
        DECAYED ARRAY (slot and object coincide, the W-N `p`-text legs).
        A bare POINTER variable answers a RUNTIME value: the slot's text
        is the pointer's OWN address (`&pp`), and answering it for `pp`
        is the F-N-1 slot/value confusion under `'p'` — measured gcc
        P5c at REC: the value rides a reg and `%P` prints the bare
        `%rdi` (MC 12690). Everything else takes the computed route."""
        node = e
        while isinstance(node, ast.Cast):
            node = node.operand
        if isinstance(node, ast.Unary) and node.op == "&":
            return True
        try:
            ty = self._untype(self._ty(node))
        except DiagError:
            return False
        return isinstance(ty, ast.ArrayType)

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
        if self._static_visible(nm):
            # W-U COMMIT-3 (MC 12739): ONE predicate, locals-first law
            # (the spliced callee scope owns the name).
            sym, sty = self.fn.statics[nm][0], self.fn.statics[nm][1]
            if isinstance(self._untype(sty), ast.ArrayType):
                return None
            return "{}(%rip)".format(sym)
        if nm in self.fn.locals:
            off, lty = self.fn.locals[nm][:2]     # W-AB: raw slot rides
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
        """Element type of an ARRAY-typed subscriptable base for the
        static-address walk. M4 W-O (MC 12690, gate F-N-1): the walk
        folds a `[k]` ONLY over an ARRAY base — an array's slot IS the
        object, so sym/frame + k·esz is a STATIC address. A POINTER-
        typed base answers None: `p[i]` lives where p POINTS — a
        runtime value — and folding the pointer's OWN frame/sym slot
        is the F-N-1 silent miscompile (gate rp5f 7→207, rp5l 42→7,
        rp5p write-through the frame slot; the tip died LOUD with an
        AttributeError before W-N legitimated this arm). The computed
        L3 route (address → aslot → base reg) carries the pointer
        shape with the right VALUE. W-N read the DECAYED type here —
        arrays and pointers were one arm; the W-O law reads the
        UNDECAYED type, which is exactly the array/pointer distinction
        the fold needs (the ICE-dead legs stay green: `gs[3]` is an
        array under either read)."""
        try:
            ty = self._untype(self._ty(e))
        except DiagError:
            return None
        if isinstance(ty, ast.ArrayType):
            # M4 W-P (MC 12705, gate F-1): the element is the UNDECAYED
            # inner object. A row of a 2-D array IS a row-sized object
            # (`int mm[2][3]`: the row step is sizeof(int[3]) = 12);
            # decaying to the row pointer gave esz 8 — `mm[1][2]` folded
            # to mm+16 (row 1 landed at byte 12*1 + 2*4 = 20, gcc
            # measured). W-O's decay at THIS tail was right for scalars
            # (decay of a scalar is identity) and wrong for array
            # elements; the walk's array/pointer gate at the top of this
            # function is the W-O F-N-1 law and stays.
            return ty.inner
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
            elif not ops:
                # M4 W-AO {A2} (MC 12404.2.162 / card 12889): a not-in-table
                # '%'+letter prints VERBATIM iff the statement has NO
                # OPERANDS. W-AN sims measured gcc's scan scope (a13
                # verbatim): with operands present "%eax" is gcc's `operand
                # number missing after %-letter` rc1, while the zero-operand
                # templates a01/a02/a03/a12/a16/a17 print RAW and reach gas
                # rc0. So a zero-operand '%a' is not a modifier demand at
                # all — it is a register mnemonic under a scanner that never
                # ran (io_delay.c:43 `outb %al, $0x80`). This is the SHIPPED
                # `%%` arm above extended to the not-in-table case (print
                # `%`+char, consume no operand) — NOT a new table letter and
                # not a new mechanism; gas still decides the fate of the
                # text (a11 `nop %al`, a18 `%ae` stay BOTH-REFUSE, so the
                # arm adds no acceptance beyond gcc's own). WITH OPERANDS
                # the shipped §3.5 L3 LOUD below stands UNCHANGED: the GATE
                # is the finding, and its absence measured LOOSE at
                # a13/a19 (plant_a_ungate).
                out.append(t[i])
                out.append(t[i + 1])
                i += 2
                continue
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
                # constant).
                if o.mem is None:
                    # M4 W-O MATERIALIZATION (MC 12690, gate-confirmed
                    # walk wall special_insns.h:217): a COMPUTED operand
                    # answers the same plain text from its base register
                    # (stage (4) moved the aslot address into %o.reg
                    # before the template). Measured at REC, 12 shapes
                    # (.tmp/m4-wo/out/measure-pct-computed.txt): the
                    # computed MEMORY operand's text is the parenthesized
                    # base reg — `clflush (%rdi)`; the computed `'p'`
                    # operand CARRIES the value in its base reg and
                    # prints the bare name — `movq %rdi, %rdx` (P5c; the
                    # tip's "computed = unprintable rc1" reading was
                    # measured FALSE — rc1 is the FRAME-under-'p'
                    # posture, which stays LOUD below, P12 re-confirmed
                    # at REC). Same L3 equivalence law as the static
                    # texts: gcc folds disp(base,index,scale) into the
                    # text, blcc's computed route carries the FULL
                    # address in the base reg — value-paired, the
                    # `(%reg)` text already pinned by the plain path
                    # (line 548), never a new printer.
                    if o.ci.cls == "p":
                        return "%{}".format(o.reg)
                    return "(%{})".format(o.reg)
                if not (o.ci.cls == "p" and "%rbp" in o.mem):
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
            # M4 W-O (MC 12690): the SAME measured value law as `%P` —
            # a computed `'p'` operand CARRIES its value in the base
            # reg (plain `%N` prints the bare reg; `(reg)` would LOAD
            # through it — a silent value split, measured gcc exit 1
            # vs blcc 0 on `movq %1, %0`/"p"(pp) before this arm); a
            # computed `"m"` operand's text is the parenthesized base
            # reg (the pre-existing plain path, byte-equal to gcc for
            # the `(%reg)` shapes).
            if o.ci.cls == "p":
                return "%{}".format(o.reg)
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
