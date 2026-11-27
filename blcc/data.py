# LINES reason: constant evaluation and the .rodata/.data/.bss emission it
# feeds are ONE fold (a byte list is the fold's output); the file crossed 600
# when W-X COMMIT-0 added the data-path _Bool normalize twin (+18 l, both
# bitfield init sites) — splitting the fold from its emitter would duplicate
# the ('b'|'q'|'z') stream contract.
"""Global data emission for blcc (ARCHITECTURE.md §4): constant evaluation of
file-scope initializers (integer/char constants, address-of-global, brace
lists; a string literal is a §5-style diagnostic naming the construct) and
their .rodata/.data/.bss assembly lines — bytes-immutable (const) objects
go to .rodata, all-zero objects to .bss, the rest to .data (MEASURED §6
parity law, M4 W2; see _is_const_obj). Mixin of blcc.codegen.Codegen, which
provides
globals/enums/structs/strings tables plus _size/_decay/_struct_layout/_err/
_str_label (strings interning stays on Codegen with the rodata pool)."""
from __future__ import annotations

import dataclasses

from typing import List, Tuple

from blcc import ast


def _has_stmtexpr(n: ast.Node) -> bool:
    """Does this (constant-expression-shaped) initializer subtree contain
    a statement-expression? Used for the §2.4d file-scope mirror-reject."""
    if isinstance(n, ast.StmtExpr):
        return True
    for f in dataclasses.fields(n) if dataclasses.is_dataclass(n) else ():
        v = getattr(n, f.name, None)
        if isinstance(v, ast.Node) and _has_stmtexpr(v):
            return True
        if isinstance(v, (tuple, list)):
            for x in v:
                if isinstance(x, ast.Node) and _has_stmtexpr(x):
                    return True
    return False


class DataEmitter:
    def _anon_static(self, lit) -> str:
        """§1 row 11: a file-scope compound literal is an unnamed STATIC
        object. Label + bytes are emitted with the data section; the
        initializer sees the label as an address constant."""
        anons = getattr(self, "_clit_anons", None)
        if anons is None:
            anons = self._clit_anons = []
            self._clit_anon_lbl = {}
        key = (lit.file, lit.line, lit.col)
        if key in self._clit_anon_lbl:
            return self._clit_anon_lbl[key]
        lab = "_blcc_clit_{}".format(len(anons))
        if isinstance(lit.ty, ast.ArrayType) and lit.ty.size is None:
            # `static int *gp = (int[]){7, 8};` — the literal's array
            # takes its size FROM THE INITIALIZER, like a var decl would.
            lit = ast.CompoundLit(
                lit.file, lit.line, lit.col,
                self._sized_array_decl(lit.ty, lit.init, lit), lit.init)
        anons.append((lab, lit))
        self._clit_anon_lbl[key] = lab
        return lab

    def _emit_anon(self, lab, lit):
        items = self._bytes_of(lit.ty, lit.init, lit)
        lines = ["    .align 8", "{}:".format(lab)]
        acc = []

        def flush():
            if acc:
                lines.append("    .byte {}".format(
                    ",".join(str(b) for b in acc)))
                acc.clear()

        for kind, val in items:
            if kind == "b":
                acc.append(val)
            elif kind == "z":
                flush()
                lines.append("    .zero {}".format(val))
            else:
                flush()
                lines.append("    .quad {}".format(val))
        flush()
        return lines

    def _const(self, n: ast.Node, ctx: str = "global"):
        """-> int | ('lab', label) for address-of-global constants.
        CTX names the initializer being folded for §8 construct wording:
        "global" (default — the shipped sentences, byte-identical) or
        "static" for a function-scope `static` local (§1c, MC 12486),
        which carries the SAME constant-expression law."""
        if isinstance(n, ast.IntLit):
            return n.value
        if isinstance(n, ast.CharLit):
            return n.value - 256 if n.value > 127 else n.value
        if isinstance(n, ast.Ident) and n.name in self.enums:
            return self.enums[n.name]
        if isinstance(n, ast.Ident):
            # T+10b: a BARE array-typed global (or a function name) in a
            # static initializer is an address constant — the decay the
            # kernel's pointer tables rely on (`[0][1] = t2`).
            gd = self.globals.get(n.name)
            if gd is not None and isinstance(self._untype(gd.type),
                                             ast.ArrayType):
                return ("lab", n.name)
            if n.name in getattr(self, "sigs", {}):
                return ("lab", n.name)
        if isinstance(n, ast.Unary) and n.op == "-":
            v = self._const(n.operand, ctx)
            if isinstance(v, int):
                return -v
        if isinstance(n, ast.Unary) and n.op == "&":
            if isinstance(n.operand, ast.CompoundLit):
                # §1 row 11 file scope: &literal names an unnamed STATIC
                # object — its bytes are emitted, the value is its address.
                return ("lab", self._anon_static(n.operand))
            if isinstance(n.operand, ast.Ident):
                sv = self._static_self_root(n.operand.name)
                if sv is not None:
                    # M4 W-AD twin of the fold root (MC 12801): `&self`
                    # of the static object being emitted is its own §1c
                    # symbol; the object's declarator shadows a
                    # same-named global, so the SELF check runs FIRST.
                    return ("lab", sv.name)
                if n.operand.name in self.globals:
                    return ("lab", n.operand.name)
            # M4 W-V COMMIT-G (MC 12747, law row e25): a `.`-select /
            # index CHAIN rooted at a global object is an address
            # constant (symbol + byte offset) — the corpus shape
            # `&(smn_mutex.list)` in a global init (the 39-family's
            # `&` half, 20/39 rows at the own-hands ladder).
            # And (row e26, the `(void *)&fn` __addressable_ shim):
            # &function-name is the function's address.
            v = self._fold_addr_member(n.operand)
            if v is not None:
                return v
            if isinstance(n.operand, ast.Ident) \
                    and n.operand.name in getattr(self, "sigs", {}):
                return ("lab", n.operand.name)
        # M4 W-V COMMIT-G (law row e26, 19/39 rows — the
        # `void *__addressable_x = (void *)&x` EXPORT shim): a CAST of
        # a constant folds to the SAME constant (address or int). A
        # NON-constant operand falls through — the §4 LOUD stands
        # (gcc's own "initializer element is not constant" twin, row
        # e28, measured LOUD both sides at the wave REC).
        if isinstance(n, ast.Cast):
            from blcc.lexer import DiagError as _DE
            try:
                v = self._const(n.operand, ctx)
            except _DE:
                v = None
            if v is not None:
                return v
        if isinstance(n, ast.CompoundLit):
            return self._const(n.init, ctx)  # scalar literal value
        if isinstance(n, ast.StrLit):
            self._err(n, "'string literal in {} initializer' is not in the "
                      "§4 set (integer/char constant or address-of-global; "
                      "string bytes belong in a char array initializer)".format(ctx),
                      "string literal")
        # §8 construct-naming (DA-c3 P1-1 completed at lead ruling): even the
        # two forms test_c2_orch_probes once pinned by node-class token are
        # named literally now — 'call expression' / '<op> expression'. The
        # sealed probe PREDATES the OBS-A/§8 adjudication; its re-sign is the
        # verifier's (TEST-c4). Until then those two token rows are RED by
        # design — reverting this line to 'found Call/Binary' would UNFIX the
        # product and is the wrong remedy.
        # §2.4(d) mirror-reject: a file-scope statement-expression gets the
        # gcc sentence verbatim-classed (measured rc1, no value assigned).
        try:    # T+10b: enums-style INTEGER constant expressions in global
                  # initializers (`inat_primary_table[0x00] = (1 << 12)`,
                  # VM-flag ORs, idt sizes) — the SAME folder as array sizes.
            from blcc.lexer import DiagError as _DE
            v = self._fold_const(n, None)
            if isinstance(v, int):
                return v
        except _DE:
            pass
        # M4 W-AK LEVER-A (MC 12404.2.156, sims card 12849 law rows
        # aj01-aj18): the §4 address-constant CLOSURE under +- and the
        # DECAY half, at THIS one home and AFTER every shipped fold above
        # answered (zero collateral: streams that already fold never reach
        # an arm). Corpus shapes: the defkeymap `func_buf + 0`
        # (drivers_tty_vt_defkeymap.c.i:11592:11), `k8nops + 1`
        # (alternative.c), `(unsigned long)&init_stack + sizeof(init_stack)
        # - 0` (process.c .sp1), the array-decay `units_10[1]`
        # (string_helpers) and `init_files.close_on_exec_init` (fs_file —
        # an unsigned long[] member). Produced value = the SAME
        # ("lab", sym[+off]) the shipped W-V _fold_addr_member law
        # (e25/e26) emits — NO new representation, NO new pass. Scalar
        # rvalues, struct rvalues, lab+lab and lab+var keep the §4 LOUD
        # (gcc's own not-constant twins, measured aj05/aj09/aj11).
        from blcc.lexer import DiagError as _DE

        def _aj_cv(x):
            try:
                return self._const(x, ctx)
            except _DE:
                return None
        if isinstance(n, ast.Binary) and n.op in ("+", "-"):
            lv, rv = _aj_cv(n.left), _aj_cv(n.right)
            if n.op == "-" and isinstance(lv, tuple) \
                    and isinstance(rv, tuple):
                # gcc law (aj10/aj10b/aj10c measured own hands): the
                # DIFFERENCE of two address constants IS constant when
                # SAME-SYMBOL and is NOT when crossing symbols (gcc rc1 —
                # stays LOUD, the arm does not fire).
                s1, _, o1 = lv[1].partition("+")
                s2, _, o2 = rv[1].partition("+")
                if s1.isidentifier() and s1 == s2:
                    try:
                        return int(o1 or 0) - int(o2 or 0)
                    except ValueError:
                        pass
            lab, delta, labx = None, 0, None
            if isinstance(lv, tuple) and isinstance(rv, int):
                lab, delta = lv, (rv if n.op == "+" else -rv)
                labx = n.left
            elif n.op == "+" and isinstance(rv, tuple) \
                    and isinstance(lv, int):
                lab, delta = rv, lv
                labx = n.right
            if lab is not None:
                # ELEMENT-SIZE SCALE (the SATURATING-PAIR law, sims p1):
                # `tab + 1` on an 8-byte-element array means +8 BYTES.
                # The +0 twins (aj01) HIDE a missing scale; the +N twins
                # (aj03/aj15) EXPOSE it as a SILENT, never a wall.
                # Integer-typed lab views (the .sp1 `(unsigned long)`
                # idiom) are BYTES already — scale 1. An unproven type
                # keeps the §4 LOUD (safe direction).
                try:
                    ety = self._ty(labx)
                    while isinstance(ety, ast.Qualified):
                        ety = ety.inner
                    if isinstance(ety, ast.ArrayType):
                        scale = self._size(ety.inner, labx)
                    elif isinstance(ety, ast.PtrType):
                        scale = self._size(ety.inner, labx)
                    elif isinstance(ety, ast.FuncType):
                        scale = 1        # gnu89 sizeof(function)=1
                    elif isinstance(ety, ast.BuiltinType):
                        scale = 1        # integer byte-view idiom
                    else:
                        scale = None
                except Exception:
                    scale = None
                if scale:
                    sym, _sep, extra = lab[1].partition("+")
                    if sym.isidentifier():
                        try:
                            cur = (int(extra) if extra else 0) + \
                                delta * scale
                        except ValueError:
                            cur = None
                        if cur is not None:
                            return ("lab", sym if cur == 0
                                    else "{}+{}".format(sym, cur))
        if isinstance(n, (ast.Ident, ast.Select, ast.Index)):
            # DECAY half: an ARRAY-typed rvalue of a global object IS an
            # address constant (array-to-pointer in a constant expr). A
            # SCALAR or STRUCT rvalue does not fold — the §4 LOUD stands
            # (gcc's own 'initializer element is not constant' twin, aj05).
            try:
                ty = self._ty(n)
                while isinstance(ty, ast.Qualified):
                    ty = ty.inner
                if isinstance(ty, ast.ArrayType):
                    if isinstance(n, ast.Ident):
                        if n.name in self.globals:
                            return ("lab", n.name)
                    else:
                        v = self._fold_addr_member(n)
                        if v is not None:
                            return v
            except Exception:
                pass                     # unproven shape: LOUD stands
        if _has_stmtexpr(n):
            self._err(n, "braced-group within expression allowed only "
                      "inside a function (§2.4d)", "statement expression")
        self._err(n, "{} initializer must be an integer/char constant "
                  "or address-of-global (§4)".format(ctx), self._what(n))

    def _fold_addr_member(self, n):
        """M4 W-V COMMIT-G (MC 12747): -> ('lab', sym[+off]) for a
        `&(G.f[i].g)` CHAIN rooted at a GLOBAL OBJECT (measured 20/39
        rows of the global-init family at the own-hands ladder). The
        offset is the SHIPPED layout law (`_struct_layout` slots,
        `_size` element sizes) expressed as `sym+off` in the label —
        the same symbol+offset addressing data.py already emits for
        `('q', label)` slots. ARROW selects, bitfields, non-constant
        indices, incomplete arrays and pointer-rooted chains are NOT
        address constants — return None keeps the caller's §4 LOUD,
        which is gcc's own posture at every one of those shapes
        (measured LOUD twins e27 bitfield / e28 non-constant index)."""
        from blcc.lexer import DiagError as _DE
        chain = []
        while isinstance(n, (ast.Select, ast.Index)):
            if isinstance(n, ast.Select):
                if n.arrow:
                    return None
                chain.append(("m", n.field))
                n = n.base
            else:
                try:
                    idx = self._fold_const(n.index, None)
                except _DE:
                    return None
                if not isinstance(idx, int):
                    return None
                chain.append(("i", idx))
                n = n.base
        if not chain or not isinstance(n, ast.Ident):
            return None
        sv = self._static_self_root(n.name)
        if sv is not None:
            # M4 W-AD (MC 12801): root the SAME walk at the §1c static
            # being emitted (the rt.c:2758 DEFINE_MUTEX self-address
            # family); ONE law, see _static_self_root. The offset walk
            # and its guards (arrow/bitfield/non-constant index) are
            # the shipped law — nothing below changes.
            off, ty, lab = 0, self._untype(sv.type), sv.name
        else:
            gd = self.globals.get(n.name)
            if gd is None:
                return None
            off, ty, lab = 0, self._untype(gd.type), n.name
        for kind, arg in reversed(chain):      # ROOT-most op first
            ty = self._untype(ty)
            if kind == "m":
                if not isinstance(ty, ast.StructType):
                    return None
                flat, total, slots = self._struct_layout(ty, n)
                hit = next((s for s in slots if s[0] == arg), None)
                if hit is None or hit[4] is not None:
                    return None                 # bitfield: not addressable
                off += hit[2]
                ty = hit[1]
            else:
                if not isinstance(ty, ast.ArrayType):
                    return None
                # M4 W-W COMMIT-2 (MC 12753): the tty_ldisc residual
                # (W-V §6 named). gcc's index-address law needs the
                # ELEMENT size only — an extern array of unknown
                # length still answers `&ext[i] = ext + i*elem`
                # (pin: R_X86_64_64 sysctl_vals+0x4, SAME text as
                # gcc). KEEP: a non-constant index and an INCOMPLETE
                # ELEMENT stay None (the §4 LOUD twins stay LOUD —
                # W-V e28 law).
                try:
                    esz = self._size(ty.inner, n)
                except _DE:
                    return None
                off += arg * esz
                ty = ty.inner
        if off == 0:
            return ("lab", lab)
        return ("lab", "{}+{}".format(lab, off))

    def _static_self_root(self, name):
        """M4 W-AD (MC 12801) — the ONE home of the static-root scope
        law for the shipped address-fold family. A function-scope
        `static` lives in TU-level storage under the §1c symbol
        "name.N" (codegen static_objs); while ITS OWN initializer is
        being emitted, a bare name spelling the object's own base
        binds to the object itself (rt.c:2758 / irq/proc.c:340:
        `&(mutex.wait_list)` INSIDE mutex's own init — measured self-
        reference; the corpus twins kernfs/reboot carry the SAME
        macro law). Returns that VarDecl (`.name` = the symbol the
        emit uses, `.type` = the sized type) or None.
        REFUSED by construction: any OTHER name — the sims stub that
        resolved the flat static_objs map at EMIT order measured
        SILENT-DIVERGE on the reuse rows ib19/ib30 (gcc 4 / stub 3),
        the DO-NOT-SHIP posture; without the emitting function's
        scope a cross-object name cannot bind honestly, so it keeps
        the §4 LOUD. Anchors: `_fold_addr_member` root + the `&Ident`
        twin arm in `_const` (TWO anchors, ONE law — the twins the
        sims row named); the current object arrives through the
        codegen §1c emit-scope anchor `_fold_static`."""
        vd = getattr(self, "_fold_static", None)
        if vd is None or "." not in vd.name:
            return None
        if name != vd.name.rsplit(".", 1)[0]:
            return None
        return vd

    def _bf_data_guard(self, init, ty, d) -> None:
        """M4 W-W COMMIT-1 (MC 12753) KEEP-laws + M4 W-AH COMMIT-WFW
        (MC 12404.2.150): the packed member-initializer LOUD OPENS — the
        shipped W-W materializer lands the value through the per-slot
        paths, and under packed the fold window is the field's OWN span
        (the bsup producer's window law below; the sims card 12838
        ICE-traceback receipts proved the DECLARED unit walking off the
        shrunk extent is the whole failure). Unit types outside the
        extraction model stay LOUD BY NAME (tip ICEd `unsigned __int128`;
        W-G named the LOUD)."""
        if d[3] not in self._BF_UNS:
            self._err(init, "bitfield unit type '{}' has no extraction "
                      "model (§1 row 12 LOUD twin)".format(d[3]),
                      "bitfield")

    def _bf_norm(self, init, bfx, v: int) -> int:
        """M4 W-X COMMIT-0 (MC 12756, W-W gate F1 — SILENT): a `_Bool`
        unit NORMALIZES to 0/1 BEFORE the width mask — C11 6.3.1.2, the
        same law the shipped codegen path rides through `_convert`
        (`_bf_store`'s `un == "_Bool"` arm) and the shipped plain-assign
        path. gcc byte-pinned (gate, out/bool-pairrun.txt): global
        `{ .f = 2 }` on `_Bool f:1` stores 01, `{ .f = 258 }` stores 01,
        `{ .f = -3 }` stores 01; tip masked the RAW value (2&1=0 → 0),
        a SILENT wrong object. Both data sites (struct bsup, union slot)
        route HERE — one law, one home. Non-_Bool units truncate mod 2^w
        exactly as shipped (row 'trunc' pins the control)."""
        if bfx[3] == "_Bool":
            return 1 if v else 0
        return v

    def _entries_from_maps(self, total, vals, labs):
        """THE rebuild law, one home for both materializers that carry a
        label window over a byte map: ('q', lab) where a label starts,
        ('b', byte) where a byte is set, and the '.zero'-compressed run
        beneath. Address order is the emission order, so a last-wins init
        stays last-wins and a label never floats ahead of the bytes that
        follow it (W-Y sims plant p_order: label-entries-first breaks
        y06/y07/y29 — this walk is what keeps them green).

        M4 W-Y COMMIT-Y (MC 12764): extracted from `_bf_merge` verbatim
        (byte-identical output, corpus-proved at the close leg) because
        the union address arm needs exactly this law and nothing else —
        a second copy beside it is the defect this repo names."""
        rebuilt = []
        i = 0
        while i < total:
            if labs[i] is not None:
                rebuilt.append(("q", labs[i]))
                i += 8
            elif vals[i]:
                rebuilt.append(("b", vals[i]))
                i += 1
            else:
                j = i
                while j < total and not vals[j] and labs[j] is None:
                    j += 1
                rebuilt.append(("z", j - i))   # the .zero compression
                i = j
        return rebuilt

    def _bf_merge(self, total, out, bsup, init):
        """Fold bitfield bit-contributions into the entry stream. Unit
        bytes are little-endian (x86, W-F layout law); a ('q') label
        overlapping a bit unit is LOUD (no gcc object does that: the
        layout law flushes a partial unit before any byte member)."""
        vals = [0] * total
        labs = [None] * total
        pos = 0
        for k, v in out:
            if k == "b":
                vals[pos] = v
                pos += 1
            elif k == "q":
                for p in range(pos, pos + 8):
                    labs[p] = v
                pos += 8
            else:
                pos += v
        for uoff, bit, w, ub, v in bsup:
            for p in range(uoff, uoff + ub):
                if labs[p] is not None:
                    self._err(init, "address initializer inside a "
                              "bitfield unit is not in the subset (§5)",
                              "initializer")
            cur = 0
            for p in range(uoff, uoff + ub):
                cur |= vals[p] << (8 * (p - uoff))
            cur = (cur & ~(((1 << w) - 1) << bit)
                   | (v & ((1 << w) - 1)) << bit) & ((1 << (8 * ub)) - 1)
            for p in range(uoff, uoff + ub):
                vals[p] = (cur >> (8 * (p - uoff))) & 255
        return self._entries_from_maps(total, vals, labs)

    def _scalar_brace(self, init):
        """M4 W-AC (MC 12404.2.133 / job 12787): THE brace-scalar collapse,
        ONE home for both shipped §4 doors (data below, `codegen
        ._init_local`). gnu89 brace-initializer-for-a-SCALAR (the REAL-MAKE
        FIRST-RED family, init/calibrate.c:251 DEFINE_PER_CPU `= { 0 }`):
        the list supplies the value of its FIRST item — collapse
        repeatedly, ONLY while the run is non-designated and non-empty
        (battery bs01-17 at gcc 11.4 -std=gnu89 -Os, sims card 12789:
        nested `{{0}}` collapses; `{5, 9}` WARNS but ACCEPTS, value =
        FIRST, never the last). Anything still an InitList when the
        collapse stops is the shipped §4 LOUD: empty `{ }` and designated
        `{ .x = 0 }` — gcc refuses BOTH (bs09/bs10/bs17 measured
        BOTH-REFUSE). The value then rides the ALREADY shipped scalar
        paths unchanged (_const, the .quad address law, the _Bool 0/1
        rule, the string-address law): zero new mechanism."""
        while (isinstance(init, ast.InitList) and len(init.items) >= 1
               and not any(isinstance(it, ast.Desig)
                           for it in init.items)):
            init = init.items[0]
        return init

    def _bytes_of(self, ty: ast.Node, init, at,
                  ctx: str = "global") -> List[Tuple[str, int]]:
        """-> list of ('b', byte) | ('q', label) | ('z', count) covering
        size(ty) bytes. Zero runs stay COMPRESSED ('z') so _emit_global can
        emit a .zero directive — a materialized byte list is what OOM-killed
        the compiler on large .bss (DA-c2 P2-2, exit 137 outside §2)."""
        ty = self._untype(ty)          # §2.6: `static __typeof__(long) gsl`
        if isinstance(init, ast.ZeroFill):
            return [("z", self._size(ty, at))]     # §1 row 10 padding
        if isinstance(init, ast.CompoundLit):
            if isinstance(init.ty, (ast.ArrayType, ast.StructType)):
                if isinstance(self._untype(ty),
                              (ast.BuiltinType, ast.PtrType)):
                    # pointer slot initialized from a literal's address
                    if self._size(ty, at) != 8:
                        self._err(init, "address initializer needs an "
                                  "8-byte pointer type (§4)", "initializer")
                    return [("q", self._anon_static(init))]
            init = init.init                        # byte-equal braces
        if isinstance(ty, ast.StructType) and ty.is_union \
                and isinstance(init, ast.InitList):
            # union slots OVERLAP: a sequential byte stream cannot carry
            # them; materialize (unions are object-sized, the .zero
            # compression rule protects .bss ARRAYS, not these).
            #
            # M4 W-Y COMMIT-Y (MC 12764) — THE UNION ADDRESS LAW: an
            # address inside a union initializer materializes as an
            # 8-byte label window at the MEMBER'S OWN offset. The walk
            # stopper is this one sentence at init/main.c:757 (sims §2:
            # 11 witnesses, all the `module_param` expansion
            # `…, -1, 0, { &sym } };`), and the read-back that makes it
            # a walk stopper DEREFERENCES the stored pointer — so a
            # zero-filled slot would compile and answer 0: every law row
            # is exit-encoded through a real read-back (y01=11, y02=42,
            # y06=9, y07=123, y20=67, y28=16, y29=3, y32=62).
            # Loud, never silent: a window that is NOT 8-aligned or runs
            # past the extent keeps the shipped §5 refusal (there is no
            # honest object to build), and a label that collides with
            # another label or with a live byte refuses too (sims y31:
            # gcc truncates a relocation there — volume 0 in this
            # corpus, NAMED rather than copied).
            total, slots = self._struct_layout(ty, at)[1:]
            buf = bytearray(total)
            labs = [None] * total       # the §Y label carrier
            for i, (sname, sty, mo, ssz, bfx) in enumerate(slots):
                if i < len(init.items) and \
                        not isinstance(init.items[i], ast.ZeroFill):
                    if bfx is not None:
                        # M4 W-W COMMIT-1 (MC 12753) data UNION twin:
                        # the init touches ONLY the designated member;
                        # the value lands at bit 0 of the zeroed extent,
                        # masked to w bits. KEEP-laws via _bf_data_guard.
                        self._bf_data_guard(init, ty, bfx)
                        v = self._const(init.items[i], ctx)
                        if not isinstance(v, int):
                            self._err(init, "address initializer inside a "
                                      "bitfield slot is not in the "
                                      "subset (§5)", "initializer")
                        vv = self._bf_norm(init, bfx, v) \
                            & ((1 << bfx[2]) - 1)
                        for p in range((bfx[2] + 7) // 8):
                            buf[p] = (vv >> (8 * p)) & 255
                        continue
                    sub = self._bytes_of(sty, init.items[i], at, ctx)
                    pos = 0
                    for kind, val in sub:
                        if kind == "b":
                            if labs[mo + pos] is not None:
                                self._err(init, "address initializer "
                                          "overlap in a union (§Y)",
                                          "initializer")
                            buf[mo + pos] = val
                            pos += 1
                        elif kind == "z":
                            pos += val
                        else:
                            if (mo + pos) % 8 or mo + pos + 8 > total:
                                self._err(init, "address initializer "
                                          "inside a union initializer is "
                                          "not in the subset (§5)",
                                          "initializer")
                            for p in range(mo + pos, mo + pos + 8):
                                if labs[p] is not None or buf[p]:
                                    self._err(init, "address initializer "
                                              "overlap in a union (§Y)",
                                              "initializer")
                                labs[p] = val
                            pos += 8
            return self._entries_from_maps(total, buf, labs)
        if isinstance(ty, (ast.BuiltinType, ast.PtrType)):
            sz = self._size(ty, at)
            if isinstance(init, ast.FloatLit):
                # §1 row 14: double/float STORAGE = IEEE-754 .quad/.long
                # bytes (M44; the .s is byte-anchored vs gcc's .rodata).
                if not isinstance(ty, ast.BuiltinType) \
                        or ty.name not in ("float", "double") \
                        or init.fsize != sz:
                    self._err(init, "'double'/'float' initializer needs the "
                              "matching storage type (§1 row 14)",
                              "floating literal")
                return [("b", (init.bits >> 8 * i) & 255) for i in range(sz)]
            if init is None:
                return [("z", sz)]
            if isinstance(init, ast.InitList):
                # M4 W-AC (MC 12404.2.133): the gnu89 brace-scalar door —
                # collapse through the ONE law (`_scalar_brace`, above);
                # what is still an InitList (empty `{ }`, designated) keeps
                # the shipped §4 LOUD. bs06/bs12/bs16 pin this DATA path.
                init = self._scalar_brace(init)
                if isinstance(init, ast.InitList):
                    self._err(init, "brace initializer for a scalar (§4)",
                              "{")
            if isinstance(init, ast.StrLit) and isinstance(
                    self._untype(ty), ast.PtrType):
                # M4 W-V COMMIT-S (MC 12747, the 37-row `.name = "noop"`
                # family, measured PAIRED with COMMIT-G): a string in a
                # POINTER slot is the ADDRESS CONSTANT of its bytes —
                # gcc emits `.quad .LC`. The bytes ride the SHIPPED
                # anon-static door (a char[] compound literal sized
                # from its initializer, the e30 byte law untouched);
                # dedup is by literal POSITION, never by value, so two
                # literals can never share a label. A string in any
                # OTHER scalar slot keeps the §4 LOUD below — gcc's own
                # int-from-pointer refusal (row e29, LOUD both sides).
                v = ("lab", self._anon_static(ast.CompoundLit(
                    init.file, init.line, init.col, ast.ArrayType(
                        init.file, init.line, init.col,
                        ast.BuiltinType(init.file, init.line, init.col,
                                        "char"), None), init)))
            else:
                v = self._const(init, ctx)
            if isinstance(v, int):
                # M4 W2 COMMIT-0 (MC 12545): the DATA-time mirror of the
                # measured 0/1 rule — `static _Bool gb = 7;` emits the byte
                # 1 (gcc-measured), same law as _store/_CONV.
                if isinstance(ty, ast.BuiltinType) and ty.name == "_Bool":
                    v = 1 if v else 0
                return [("b", (v >> 8 * i) & 255) for i in range(sz)]
            if sz != 8:
                self._err(init, "address initializer needs an 8-byte pointer "
                          "type (§4)", "initializer")
            return [("q", v[1])]
        if isinstance(ty, ast.ArrayType):
            n = 0 if ty.size is None else self._arrlen(ty, at)
            if isinstance(init, ast.StrLit):
                raw = init.value.encode("utf-8", "surrogateescape") + b"\0"
                if ty.size is not None and len(raw) > n:
                    self._err(init, "string initializer longer than char[{}] (§4)"
                              .format(n), "initializer")
                out = [("b", b) for b in raw]
                if n - len(raw) > 0:
                    out.append(("z", n - len(raw)))
                return out
            items = init.items if isinstance(init, ast.InitList) else \
                ([] if init is None else None)
            if items is None:
                self._err(init, "array initializer must be a brace list or "
                          "string literal (§4)", self._what(init))
            plan, used = self._fill_plan(ty, items, at)
            cap_note = n
            if isinstance(ty.inner, ast.ArrayType) and items and \
                    not all(self._whole_elem(ty.inner, it) for it in items):
                cap_note = n * self._leaf_cap(ty.inner, at)
            if used < len(items):
                self._err(init, "too many initializers for {} elements (§4)"
                          .format(cap_note), "initializer")
            out: List[Tuple[str, int]] = []
            for mode, off, a, b in plan:
                if mode == "zero":
                    out.append(("z", a))
                else:
                    out.extend(self._bytes_of(a, b, at, ctx))
            return out
        if isinstance(ty, ast.StructType):
            total, slots = self._struct_layout(ty, at)[1:]
            items = init.items if isinstance(init, ast.InitList) else \
                ([] if init is None else None)
            if items is None or len(items) > len(slots):
                self._err(init, "struct initializer must be a brace list of "
                          "member constants (§4)", "initializer")
            out = []
            bsup = []
            for i, (sname, sty, mo, ssz, bfx) in enumerate(slots):
                gap = mo - self._bytelen(out)
                if gap > 0:
                    out.append(("z", gap))
                if i < len(items) and \
                        not isinstance(items[i], ast.ZeroFill):
                    if bfx is not None:
                        if bfx == ("fam",):
                            self._err(init, "a flexible array member "
                                      "initializer is not in the subset "
                                      "(§5 — §1 row 13)", "initializer")
                        # M4 W-W COMMIT-1 (MC 12753) data STRUCT twin:
                        # the constant lands TRUNCATED (mod 2^w) at its
                        # bit position inside its unit; the field's
                        # signedness does NOT change stored bits (guard
                        # rows g1/g2 pin both). _Bool normalizes FIRST
                        # (W-X COMMIT-0 _bf_norm, gate F1). KEEP-laws ride
                        # _bf_data_guard (packed W-F, unit model).
                        self._bf_data_guard(init, ty, bfx)
                        v = self._const(items[i], ctx)
                        if not isinstance(v, int):
                            self._err(init, "address initializer inside a "
                                      "bitfield slot is not in the "
                                      "subset (§5)", "initializer")
                        # M4 W-F layout + M4 W-AH COMMIT-WFW
                        # (MC 12404.2.150): THE WINDOW LAW. Under packed
                        # the layout cursor is bit-contiguous (the
                        # shipped W-F cursor law, types.py), so a field's
                        # fold window is its OWN span ceil((bit+w)/8)
                        # bytes at its first byte — the SAME expression
                        # the shipped W-X access law rides at its three
                        # homes (expr_codegen read :1198 / store :1262 /
                        # read-modify :1363, `nb = (bit + w + 7) // 8`),
                        # NOT the DECLARED unit size, which walked off
                        # the shrunk extent (the base ICE at _bf_merge's
                        # label-overlap read — sims card 12838 traceback
                        # receipts). `_bf_merge` is UNCHANGED: it already
                        # folds arbitrary (uoff, bit, w, ub, v) windows
                        # little-endian and its refusal keeps its teeth,
                        # now bounded to the TRUE window. Unpacked rides
                        # the DECLARED unit exactly as shipped.
                        _wub = ((bfx[1] + bfx[2] + 7) // 8
                                if self._attr_packed(ty) else
                                self._size(ast.BuiltinType(
                                    init.file, init.line, init.col,
                                    bfx[3]), at))
                        bsup.append((bfx[0], bfx[1], bfx[2], _wub,
                                     self._bf_norm(init, bfx, v)))
                        continue
                    out.extend(self._bytes_of(sty, items[i], at, ctx))
            if total - self._bytelen(out) > 0:
                out.append(("z", total - self._bytelen(out)))
            if bsup:
                out = self._bf_merge(total, out, bsup, init)
            return out
        self._err(at or self.tu, "cannot initialize this type", self._what(ty))

    @staticmethod
    def _bytelen(entries) -> int:
        """REAL byte span of ('b'|'q'|'z') entries. len() counts TUPLES:
        every multi-byte ('z', k) run under-counts by k-1, which made the
        padding math emit members late and objects larger than sizeof
        (DA-c3 P0-1 — the round-3 zero-run regression, mutation M1 target)."""
        return sum(1 if k == "b" else (8 if k == "q" else v)
                   for k, v in entries)

    def _is_const_obj(self, ty) -> bool:
        """§6 section parity (M4 W2, MC 12545), MEASURED gcc law: the
        object is .rodata iff its BYTES are immutable — top-level
        Qualified(const) (scalars, pointers, structs: `const int ci`,
        `char *const cstr`, `const struct SA csc`), or const down the
        ARRAY element chain (`const fp_t ro[]` — every byte is reached
        only as a const element). NOT counted: pointee const
        (`const int *pi` → .data, measured) and const STRUCT MEMBERS
        (`struct SA { const int a; } sc;` → .data, measured). `int *const`
        keeps the W1 qualifier-drop's .data placement — section-only
        divergence, named in the LEDGER (values unaffected)."""
        while True:
            if isinstance(ty, ast.Qualified):
                if ty.qual == "const":
                    return True
                ty = ty.inner
            elif isinstance(ty, ast.ArrayType):
                ty = ty.inner
            else:
                return False

    def _aligned_of(self, vd) -> int:
        # M4 W2.5 (MC 12557): object `aligned(N)` — the emitted .align
        # RAISES to max(N, blcc's 8-byte global convention); bare `aligned`
        # is the max-fundamental 16 (measured). Measured law: the linked
        # address honors %N==0 (fx/L3+obj legs).
        al = 8
        from blcc.types import is_i128
        if is_i128(self._untype(getattr(vd, "type", None))):
            al = 16                   # M4 W-B (MC 12596): measured gcc
            # law — u128 globals carry `.align 16` (consts.c: gi/gz both
            # .align 16; the .data word rows sit 16-aligned)
        for _nm, _a in getattr(vd, "attrs", ()):
            if _nm == "aligned":
                v = 16 if _a is None else self._fold_const(_a, vd)
                al = max(al, v)
        return al

    def _section_of(self, vd):
        # M4 W2.5 (MC 12557): `section("name")` PLACEMENT — the object
        # lands in the NAMED section (measured gcc emission law: flags
        # "aw" for writable, "a" for const; zero-fill stays PROGBITS .zero
        # inside the named section — the name does NOT make it NOBITS).
        # The standard names keep the shipped buckets untouched.
        sec = next((v for k, v in getattr(vd, "attrs", ())
                    if k == "section"), None)
        return sec if sec and sec not in ("bss", "data", ".bss", ".data",
                                          ".rodata", "rodata") else None

    def _emit_global(self, vd: ast.VarDecl, ctx: str = "global"):
        items = self._bytes_of(vd.type, vd.init, vd, ctx)
        total = self._bytelen(items)
        is_const = self._is_const_obj(vd.type)
        align_line = "    .align {}".format(self._aligned_of(vd))
        # .align precedes the label (.data AND .bss): a label written before
        # its padding binds to the pre-padding address, not to the bytes.
        sec = self._section_of(vd)
        if not is_const and \
                all(k == "z" or (k == "b" and v == 0) for k, v in items):
            # FIX-G1 (gate C1 TRIGGER 2, F-gate-1): a DEFINED zero-sized
            # object still advances the layout by ONE byte — gcc emits
            # `.size N, 0` together with `.zero 1` (measured zsz.c:
            # y@0 after@1, a@4 after2@5, e0@8 after4@9) — so the NEXT
            # global lands at a distinct address. `.zero 0` made them
            # COLLIDE silently. sizeof stays 0; only the allocation foot
            # prints one byte.
            return (("sec", sec, "aw"), [align_line, "{}:".format(vd.name),
                     "    .zero {}".format(total if total else 1)]
                    ) if sec else (
                "bss", [align_line, "{}:".format(vd.name),
                        "    .zero {}".format(total if total else 1)])
        lines = [align_line, "{}:".format(vd.name)]
        acc: List[int] = []

        def flush():
            if acc:
                lines.append("    .byte {}".format(
                    ",".join(str(b) for b in acc)))
                acc.clear()

        for kind, val in items:
            if kind == "b":
                acc.append(val)
            elif kind == "z":
                flush()
                lines.append("    .zero {}".format(val))
            else:
                flush()
                lines.append("    .quad {}".format(val))
        flush()
        if sec:
            return ("sec", sec, "a" if is_const else "aw"), lines
        return ("rodata" if is_const else "data"), lines


