# LINES reason: the inline-asm BACK half (§3.2 pool rule + §3.5 substitution
# + §3.6-T timing + L10 bind placement) is ONE emission pipeline — splitting
# it would separate the allocation from the placement law that makes the
# magic-call shapes sound (plan-m3-asm v3.1 §3.10's worked trace pins the
# instruction ORDER across these steps); tables/constraints live in
# blcc/asmstmt.py.
"""M3 inline-asm codegen (contract plan-m3-asm.md v3.1 §3).

AsmGenMixin (a blcc.codegen.Codegen base) emits ONE asm statement per pass:

  1. outputs' addresses materialized once (L1) and inputs evaluated
     exactly like _ex_call args into 8-byte slots;
  2. THE POOL RULE (§3.2/F-1): A(stmt) = POOL − clobber-named − implicit-use
     − fixed-class − §3.10 binds; greedy order fixed → matching → outputs →
     inputs; EVERY conflict (a)-(e) LOUD (S8), exhaustion LOUD — never a
     silent wrong color;
  3. §3.6-T callee-saved bracket: save BEFORE input placement, restore
     AFTER output write-back (A02 pins the timing);
  4. placement moves; §3.10 bind law: SCRATCH binds materialize from their
     shadow slot LAST (bind-last — the %rax-protecting order of the
     do_put_user_call trace), STABLE binds need no move;
  5. the template, substituted (§3.5): %%, %=, %N, %[name], %b/%w/%q/%h/%k
     size names, %c/%P/%s const forms, %l<label> resolved through the
     M2-C1 fn_labels map (M2-C4: undefined = `asm:` loud), labels never
     picked like colors;
  6. output write-back (reg outputs: movX → temp → _load → _store; SCRATCH
     binds: the C-type-width value INTO the shadow; %rsp/%rbp skip);
  7. the L9 section belt: `    .text` + `    .align 16` after EVERY asm
     statement (the ALTERNATIVE .pushsection shape never strands code).
"""
from __future__ import annotations

from typing import List

from blcc import ast
from blcc.asmsub import AsmSubMixin
from blcc.asmstmt import (POOL, CALLEE_SAVED, STABLE_BIND, _IMMO,
                          norm_clobber, implicit_regs, parse_constraint,
                          reg_name)

_QREACH = frozenset(("rax", "rbx", "rcx", "rdx", "r8", "r9", "r10", "r11",
                     "r12", "r13", "r14", "r15"))
_SCRATCH = ("rdx", "rcx", "rsi", "rdi", "r8", "r9", "r10", "r11")
_MOVOP = {1: "movb", 2: "movw", 4: "movl", 8: "movq"}


class _Op:
    """One operand's codegen record (built per statement, never shared)."""
    __slots__ = ("idx", "sec", "ci", "expr", "ty", "w", "form", "reg",
                 "mem", "imm", "vslot", "aslot", "bind", "stable", "shadow",
                 "match", "node")

    def __init__(self, idx, sec, node):
        self.idx = idx
        self.sec = sec                   # "out" | "in"
        self.node = node                 # the AsmOperand parse node
        self.ci = None
        self.expr = None
        self.ty = None
        self.w = 8
        self.form = ""                   # reg | mem | imm | bind | match
        self.reg = None                  # assigned color / bound reg / base
        self.mem = None                  # static memory text (or target)
        self.imm = None                  # int | ("sym", name, off)
        self.vslot = None                # value-slot MEM text (input)
        self.aslot = None                # address-slot rbp offset (int)
        self.bind = None
        self.stable = False
        self.shadow = None               # bind shadow rbp offset (int)
        self.match = None                # matched target _Op


class AsmGenMixin(AsmSubMixin):

    # ------------------------------------------------------ entry point --
    def _stmt_asm(self, n) -> None:
        if self.fn.name == "<none>":     # belt: file scope never emits code
            self._err(n, "inline asm inside a file-scope initializer is not "
                      "in the subset (§3 L4 — the .S path is M4+)", "asm",
                      "asm")
        if n.labels and not n.goto_:
            self._err(n, "an asm LABELS section without 'goto' is not in the "
                      "grammar (§3 L0/S15)", ":", "asm")
        ops: List[_Op] = []
        for i, o in enumerate(n.outs):
            ops.append(self._asm_opnd(i, "out", o, n))
        nin = len(n.outs)
        for j, o in enumerate(n.ins):
            ops.append(self._asm_opnd(nin + j, "in", o, n))
        for o in ops:
            if o.form == "match":
                self._asm_link_match(o, ops, nin)
        # -- clobbers (§3.2-N: normalize; UNKNOWN = LOUD naming it) --------
        clo: List[str] = []
        for raw in n.clobbers:
            try:
                toks = norm_clobber(raw)
            except ValueError:
                self._err(n, "unknown clobber name '{}' — §3.2-N resolves "
                          "every clobber to a register/memory/cc or LOUDs "
                          "naming the clobber; never silently dropped"
                          .format(raw), raw, "asm")
            for tk in toks:
                if tk in ("memory", "cc"):
                    continue             # value no-ops (blcc emits in-order)
                if tk in ("rsp", "rbp"):
                    self._err(n, "clobber of '%{}' (N2): blcc pins every "
                              "frame address to %rbp and never allocates "
                              "%rsp/%rbp — supporting it needs a frame- "
                              "realign pass (0 active sites, §3.7-L6)"
                              .format(tk), raw, "asm")
                if tk not in clo:
                    clo.append(tk)
        iuse, idef = implicit_regs(n.tmpl)
        # -- N3: asm-goto with a TIED ('+' output) is LOUD ------------------
        if n.goto_ and any(o.ci.readwrite for o in ops if o.sec == "out"):
            self._err(n, "asm-goto with a '+' (TIED output) operand is N3 "
                      "LOUD: no tiny asm-goto site uses it (census: only "
                      "__try_cmpxchg_user_asm, ZERO live call sites) and "
                      "the taken-path materialization would silently read a "
                      "stale slot (§3.7-N3)", "+", "asm")
        for lab in n.labels:             # §2A-M2-C4: resolve, never mint
            self._asm_label(n, lab)
        # -- S8 conflicts + §3.2 pool assignment -----------------------------
        self._asm_alloc(ops, clo, iuse, n)
        # -- §3.6-T bracket members (never rsp/rbp) --------------------------
        T = sorted(r for r in (set(clo) | {o.reg for o in ops if o.reg}
                               | set(idef)) if r in CALLEE_SAVED)
        # ---- emission ------------------------------------------------------
        for o in ops:                    # (1) output/computed addresses
            if (o.form == "mem" and o.mem is None) or \
               (o.sec == "out" and o.form == "reg" and o.mem is None):
                o.aslot = self._slot(self._longty(n), n)
                self._asm_addr_emit(o, n)
                self._e("movq %rax, {}(%rbp)".format(o.aslot))
        for o in ops:                    # (2) input evaluation (numeric ord)
            if o.form not in ("reg", "match") or o.bind is not None:
                continue
            if o.sec == "out" and not o.ci.readwrite:
                continue                 # pure output: no input value
            o.vslot = self._asm_eval_in(o, n)
        for r in T:                      # (3) T save — BEFORE placement
            ts = self.fn.asm_t.get(r)
            if ts is None:
                ts = self._slot(self._longty(n), n)
                self.fn.asm_t[r] = ts
            self._e("movq %{}, {}(%rbp)".format(r, ts))
        # (4) placement — SCRATCH binds materialize LAST (bind-last §3.10c)
        late: List[_Op] = []
        for o in ops:                    # (numeric order = template order)
            if o.form == "bind":
                if not o.stable and (o.sec == "in" or o.ci.readwrite):
                    late.append(o)       # materialize from shadow LAST;
                continue                 # pure outputs get write-back only
            if o.form in ("reg", "match") and o.vslot is not None and (
                    o.sec == "in" or o.ci.readwrite):
                self._e("{} {}, %{}".format(
                    _MOVOP[o.w], o.vslot, reg_name(o.reg, o.w)[1:]))
            if o.aslot is not None and o.form == "mem":
                # computed-mem base reg (L3): object addr → own base,
                # ALWAYS before the template (the template addresses the
                # object THROUGH this base; reg-out aslot rides the
                # write-back instead)
                self._e("movq {}(%rbp), %{}".format(o.aslot, o.reg))
        for o in late:                   # bind-last: shadow → color at C
            self._e("{} {}, %{}".format(_MOVOP[o.w],
                                        "{}(%rbp)".format(o.shadow),
                                        reg_name(o.reg, o.w)[1:]))
        # (5) the template (§3.5 substitution)
        for line in self._asm_sub(n.tmpl, ops, n).split("\n"):
            line = line.rstrip()
            if line:
                self._e(line)
        # (6) output write-back (reg + bind; mem outputs landed directly)
        outs = [o for o in ops if o.sec == "out" and o.form in ("reg",
                                                                 "bind")]
        live = {o.reg for o in outs if o.reg}
        for o in outs:
            live.discard(o.reg)
            if o.form == "bind":
                if o.stable or o.shadow is None:
                    continue             # STABLE + %rsp/%rbp skip writeback
                # (d) C-type-width value INTO the shadow (store target =
                # the shadow; _reintern law = the same movX width)
                self._e("{} %{}, {}(%rbp)".format(
                    _MOVOP[o.w], reg_name(o.reg, o.w)[1:], o.shadow))
                continue
            t = self._t()
            self._e("{} %{}, {}".format(_MOVOP[o.w],
                                        reg_name(o.reg, o.w)[1:], t))
            self._load(o.ty, t, at=o.node)         # width+sign re-intern
            if o.mem is not None:
                self._store(o.ty, o.mem, at=o.node)
            else:
                sc = self._asm_scratch(live, n)
                self._e("movq {}(%rbp), %{}".format(o.aslot, sc))
                self._store(o.ty, "(%{})".format(sc), at=o.node)
            self._unt()
        for r in T:                      # (7) T restore — AFTER write-back
            self._e("movq {}(%rbp), %{}".format(self.fn.asm_t[r], r))
        self._e(".text")                 # (8) L9 section belt
        self._e(".align 16")

    # ------------------------------------------------ operand building --
    def _longty(self, at):
        return ast.BuiltinType(at.file, at.line, at.col, "long")

    def _asm_opnd(self, idx, sec, node, n) -> _Op:
        o = _Op(idx, sec, node)
        o.ci = parse_constraint(node.constraint, node)
        o.expr = node.expr
        o.ty = self._decay(self._ty(node.expr))
        o.w = self._size(o.ty, node)
        if isinstance(o.expr, ast.Ident):
            ra = self._asm_regasm(node.expr.name)
            if ra is not None:
                if o.ci.cls in ("m", "p", "i", "I", "N", "n", "g"):
                    self._err(node, "register-bound variable with constraint "
                              "'{}' — a §3.10 bind is a REGISTER operand "
                              "(S17)".format(o.ci.raw), o.ci.raw, "asm")
                shadow, reg, stable = ra[0], ra[1], ra[2]
                o.form = "bind"
                o.bind = reg
                o.reg = reg
                o.stable = stable
                o.shadow = shadow
                return o
        ci = o.ci
        if ci.cls == "match":
            o.form = "match"
            return o
        if ci.cls in ("i", "I", "N", "n"):
            val = self._asm_fold(o.expr, node)
            if val is None and ci.alt:
                o.ci = parse_constraint(ci.alt, node)   # iq/Ir fallback S2
            elif val is None:
                self._err(node, "constraint '{}' operand is not a "
                          "compile-time constant (S5/L4: the closure is "
                          "{{int, symbol, symbol+off}})".format(ci.raw),
                          ci.raw, "asm")
            else:
                lo, hi = _IMMO[ci.cls]
                if isinstance(val, int) and not (lo <= val <= hi):
                    self._err(node, "immediate {} out of range for "
                              "constraint '{}' (§3 L4 names the value)"
                              .format(val, ci.raw), ci.raw, "asm")
                o.form = "imm"
                o.imm = val
                if ci.readwrite:
                    self._err(node, "read-write '+' on an immediate "
                              "constraint '{}' (S3: never silent)".format(
                                  ci.raw), "+", "asm")
                return o
        if ci.cls == "g":                # m, then i, then r (S4)
            st = self._asm_static(o.expr)
            if st is not None:
                o.form = "mem"
                o.mem = st
                return o
            val = self._asm_fold(o.expr, node)
            if val is not None:
                o.form = "imm"
                o.imm = val
                return o
            o.form = "reg"
            return o
        if ci.cls in ("m", "p"):
            o.form = "mem"
            o.mem = self._asm_static(o.expr)   # None → computed base reg
            return o
        o.form = "reg"                   # fixed / r / q / e
        if ci.cls == "fixed":
            o.reg = ci.fixed
            if ci.readwrite and o.reg == "rsp":
                pass                     # unreachable: 'b' etc. never rsp
        if o.form == "reg" and sec == "out":
            o.mem = self._asm_static(o.expr)   # write-back target text
        return o

    def _asm_link_match(self, o, ops, nin) -> None:
        ci = o.ci
        tgt = None
        if ci.match is not None:
            if ci.match >= nin:
                self._err(o.node, "matching constraint '{}' names no output "
                          "(outputs are operands 0..{})".format(
                              ci.raw, nin - 1), ci.raw, "asm")
            tgt = ops[ci.match]
        else:
            for p in ops[:nin]:
                if p.node.name == ci.sym:
                    tgt = p
                    break
            if tgt is None:
                self._err(o.node, "symbolic match '{}' names no operand "
                          "(§3 S9 — usercopy_64.c's [size8]/[dst] law)"
                          .format(ci.raw), ci.raw, "asm")
        if tgt.sec != "out":
            self._err(o.node, "matching constraint references a non-output "
                      "operand '{}' (§3 S9)".format(ci.raw), ci.raw, "asm")
        o.match = tgt

    # ------------------------------------------------------ allocation --
    def _asm_alloc(self, ops, clo, iuse, n) -> None:
        excl = set(clo) | set(iuse)
        for o in ops:
            if o.form == "bind":
                if o.reg in clo:
                    self._err(n, "register-bound operand %{} is CLOBBERED by "
                              "the same statement (S8: never silent)".format(
                                  o.reg), "bind", "asm")
                excl.add(o.reg)
            elif o.form == "reg" and o.ci.cls == "fixed":
                if o.reg in clo:
                    self._err(n, "constraint '{}' pins %{} which the same "
                              "statement CLOBBERS (S8)".format(o.ci.raw,
                                                               o.reg),
                              o.ci.raw, "asm")
                excl.add(o.reg)
        avail = [r for r in POOL if r not in excl]
        taken = set()

        def take(o):
            pool = avail if o.ci.cls != "q" else [
                r for r in avail if r in _QREACH]
            free = [r for r in pool if r not in taken]
            if not free:
                self._err(n, "inline asm register pressure: no pool colour "
                          "left for '{}' (the §3.2 pool minus clobbers, "
                          "implicit uses, fixed classes and binds holds {} "
                          "colours — re-run under a PERMUTED pool order "
                          "must not change this answer, A16)".format(
                              o.node.constraint or "output", len(avail)),
                          o.node.constraint, "asm")
            o.reg = free[0]
            taken.add(o.reg)

        for o in ops:                    # greedy: outputs then inputs
            if o.sec == "out" and (o.form == "reg" and o.reg is None
                                   or o.form == "mem" and o.mem is None):
                take(o)
        for o in ops:
            if o.sec == "in" and (o.form == "reg" and o.reg is None
                                  or o.form == "mem" and o.mem is None):
                take(o)
        for o in ops:                    # matching rides its target's color
            if o.form == "match":
                if o.match.form not in ("reg", "bind"):
                    self._err(o.node, "matching constraint onto a "
                              "non-register operand '{}' (S9)".format(
                                  o.ci.raw), o.ci.raw, "asm")
                o.reg = o.match.reg
        # -- post-coloring invariant checks (a)-(e), all LOUD (S8) ----------
        seen = {}
        for o in ops:
            if o.sec == "out" and o.form in ("reg", "bind") and o.reg:
                prev = seen.get(o.reg)
                if prev is not None:
                    self._err(n, "two outputs share %{} (S8(e): distinct "
                              "colors, never silent)".format(o.reg),
                              o.node.constraint, "asm")
                seen[o.reg] = o
        for o in ops:                    # S8(b) early-clobber disjointness
            if o.ci.early and o.sec == "out":
                for p in ops:
                    if p is o or p.reg != o.reg:
                        continue
                    if p.sec == "in" and p.match is not o:
                        self._err(n, "early-clobber '&' output shares %{} "
                                  "with input '{}' (S8(b))".format(
                                      o.reg, p.node.constraint), "&", "asm")
                    if p.sec == "out":
                        self._err(n, "early-clobber '&' output shares %{} "
                                  "with another output (S8(b))".format(
                                      o.reg), "&", "asm")
        for o in ops:
            if o.form == "match" and o.reg in clo:
                self._err(n, "matching operand sits on clobbered %{} (S8)"
                          .format(o.reg), o.node.constraint, "asm")

    # -------------------------------------------------- eval / folding --
    def _asm_eval_in(self, o, n):
        """Input value → an 8-byte slot MEM text; plain locals/statics/
        globals ride their OWN slot (no extra load — L3)."""
        st = self._asm_static_value(o.expr)
        if st is not None:
            return st
        self._emit_expr(o.expr)
        off = self._slot(self._longty(n), n)
        self._e("movq %rax, {}(%rbp)".format(off))
        return "{}(%rbp)".format(off)

    def _asm_addr_emit(self, o, n) -> None:
        """Address of the operand's lvalue (or the pointer VALUE for p) →
        %rax (the L3 computed-memory route)."""
        e = o.expr
        while isinstance(e, ast.Cast):
            e = e.operand
        if o.ci.cls == "p" and not (isinstance(e, ast.Unary)
                                    and e.op == "&"):
            self._emit_expr(o.expr)      # the VALUE is the address (S2 p)
        else:
            self._emit_addr(o.expr)      # address of the lvalue

    def _asm_scratch(self, live, at) -> str:
        for r in _SCRATCH:
            if r not in live:
                return r
        self._err(at, "inline asm: no caller-saved scratch left for output "
                  "write-back (§3.2)", "write-back", "asm")

    # --------------------------------------------------- §3.10 binds ----
    def _asm_bind_reg(self, raw: str, at) -> str:
        try:
            toks = norm_clobber(raw)
        except ValueError:
            self._err(at, "declaration-suffix asm(\"{}\") must name a "
                      "register — the ALIAS form is L4 LOUD (0 active "
                      "sites; §3 L4/L10)".format(raw), raw, "asm")
        if len(toks) != 1 or toks[0] in ("memory", "cc"):
            self._err(at, "register-bind asm(\"{}\") must name exactly one "
                      "register (§3.10)".format(raw), raw, "asm")
        return toks[0]

    def _asm_file_bind(self, d) -> None:
        """File-scope `register T name asm("reg");` — NEVER .bss/.data
        storage (v2 posture upheld); SCRATCH-class binds LOUD (0 sites)."""
        reg = self._asm_bind_reg(d.asm_bind, d)
        if reg not in STABLE_BIND:
            self._err(d, "file-scope register-asm variable bound to '%{}' "
                      "(SCRATCH class): a PERSISTENT C value cannot live in "
                      "a call-clobbered register — 0 sites, never silent "
                      "(§3.10 file-scope law)".format(reg), d.asm_bind,
                      "asm")
        ty = self._decay(d.type)
        self.regasm_global[d.name] = (reg, ty)

    def _asm_local_bind(self, vd) -> None:
        """Function/statement-expr scope: shadow slot (hidden local, never
        .bss) + the §3.10 read/write law downstream."""
        reg = self._asm_bind_reg(vd.asm_bind, vd)
        ty = self._decay(vd.type)
        off = self._slot(self._longty(vd), vd)
        self.fn.regasms[vd.name] = (off, reg, reg in STABLE_BIND, ty)
        if vd.init is not None:          # C-write law at the declaration
            if reg in ("rsp", "rbp"):
                self._err(vd, "initializing a variable bound to '%{}' (N2 "
                          "loud: a C write to the frame register)".format(
                              reg), vd.asm_bind, "asm")
            self._fp_guard(self._ty(vd.init), ty, vd)
            self._emit_expr(vd.init)
            self._store(ty, "{}(%rbp)".format(off), at=vd)
            self._reintern_stored(ty)
            if reg in STABLE_BIND:
                self._e("movq %rax, %{}".format(reg))

    def _asm_regasm(self, name):
        if name in self.fn.regasms:
            return self.fn.regasms[name]
        if name in self.regasm_global:
            return (None, self.regasm_global[name][0], True,
                    self.regasm_global[name][1], True)
        return None

    # C-side hooks (called from ExprEmitter): read/write of bound vars ----
    def _asm_c_read(self, n, ra) -> None:
        off, reg, stable, ty = ra[0], ra[1], ra[2], ra[3]
        if stable:
            self._e("movq %{}, %rax".format(reg))   # value persistently in
        else:
            self._load(ty, "{}(%rbp)".format(off), at=n)  # from the shadow

    def _asm_c_write(self, n, ra) -> None:
        """(c) C-write law: evaluate, %rax, store the shadow; STABLE binds
        additionally move into the register; rsp/rbp binds LOUD (N2)."""
        off, reg, stable, ty = ra[0], ra[1], ra[2], ra[3]
        if ra[4:]:
            self._err(n, "C write to file-scope register-asm variable bound "
                      "to '%{}': writing a callee/frame register persistently "
                      "across a call breaks the §6 ABI law — 0 sites, never "
                      "silent (§3.10)".format(reg), "write", "asm")
        if reg in ("rsp", "rbp"):
            self._err(n, "C write to a variable bound to '%{}' (N2: the "
                      "frame pointer register — silent frame break)".format(
                          reg), "write", "asm")
        self._emit_expr(n.value)
        self._store(ty, "{}(%rbp)".format(off), at=n)
        self._reintern_stored(ty)
        if stable:
            self._e("movq %rax, %{}".format(reg))

    def _asm_c_rmw_blocked(self, n, kind: str) -> None:
        ra = self._asm_regasm(n.target.name) if isinstance(
            n.target, ast.Ident) else None
        if ra is not None:
            self._err(n, "{} on a §3.10 register-bound variable is a "
                      "0-site construct and never silently wrong (§3.10 "
                      "law covers reads/writes only)".format(kind),
                      "bind", "asm")

