# LINES reason: THE inline pass is ONE seam (W-P/W-R/W-S doctrine: no
# second pipeline); label-law helpers live in blcc/inlclone.py.
"""M4 W-P (MC 12705, plan AMENDMENT-17): THE inline pass. W-R (MC
12714, plan AMENDMENT-19) extends THE SAME seam — no second pipeline.

ONE mechanism at the existing seam. For a file-scope `static inline`
(gnu89 header-helper, with or without `__always_inline` — rows i05/i08:
gcc -Os inlines AND discards BOTH spellings) whose every call site is
covered — statement seam (W-P) AND, since W-R, value seam too (the
epilogue answers %rax; the §2.2 copy-in law UNCHANGED: blcc stays
left-to-right, the ORDER-UNDEFINED twin values stand) — and whose body
is in the splice universe, the call is REPLACED by the body: params
copy-in to fresh caller-frame slots left-to-right with the §2.2
conversion law (row i01: `f(i++, i)` measures 8 both sides — one
call-by-value copy per param), the body rides the SAME statement
emitter (`_stmt` — the pipeline is not forked), and a param whose
argument folds to a constant answers the imm-closure fold with that
literal (row i03: gcc answers `.word` 245 post-inline — the
nospec-branch.h:375 `"i" (param)` law; W-R row i16: the SAME engine
answers the literal THROUGH composed operands — cpufeature `[bitnum]
"i" (1 << (bit & 7))` folds 16 at a bit=4 site — and W-R TRANSITIVELY
through nested splices, own table w02).

What it REPLACES: (1) at a covered site, the `_stage_call` staging +
`call sym` text; (2) for a static-inline whose sites are ALL spliced
AND that HAS sites, the standalone `_emit_func` copy. MEASURED-TRUTH
REPAIR (W-Q MC 12712, gate MC 12708 F-1 — the earlier "zero-site =
never emitted" wording was CONTRADICTED): a ZERO-call-site static
inline KEEPS its copy in all three spellings (nm pin
test_wp1_zero_site_keeps_copy) where gcc -Os keeps none — W-R's honest
accepts 50→50 with the cpufeature first-wall 483→14 proves the law
stream-by-stream (the 14 remnant are ALL zero-site; the SIM's 54 was
the copy-DISCARD instrument deleting even those). Gate nm sizing:
W-P removed 1120 dead copies (local-text 12453→11333; gcc: 14); the
zero-site discard routes to the code-size family (AMENDMENT-18 F-8).

Universe guards — a MISS keeps today's call+copy posture untouched
(including today's LOUD walls; never a silent rewrite):
  * scalar/pointer params, void-or-scalar return (sret door and fp
    classes stay the CALL law; `self._sret` masked during a splice);
  * no C `goto`, no `__label__`, no static locals, no `register … asm`
    binds. W-R: an `asm goto` whose targets are C labels defined FLAT
    at the body top (the cpufeature.h:187 `_static_cpu_has` shape) is
    IN — each splice emits a PER-SITE clone with FRESH minted labels
    (w01: shared `t_yes` merges the arms; w11: caller-same-named
    labels must not collide). `asm goto` WITH outputs (w05: gcc value
    DIVERGE — refused, named), a plain C `goto` (w03), a label no
    asm-goto targets, and any label below top level stay the CALL law;
  * not recursive / no call cycle (row i06 twin: values pair, copy
    kept);
  * not address-taken; not an alias target (§6 `.set` needs its body);
  * per-param: the imm-map applies only when the body neither writes
    the param nor takes its address — slot and literal must not
    diverge. A slot-only param keeps the S5/L4 refusal at
    `"i"(param)`-under-runtime (named LOUD twin; closure UNTOUCHED).
"""
import dataclasses

from blcc import ast
from blcc.expr_codegen import _fp
from blcc.inlclone import inl_clone, _inl_group_defs
from blcc.types import stmt_children, is_i128

_NOT_SCALAR = (ast.StructType, ast.ArrayType)


class InlinerMixin:
    """Call-graph analysis at `_collect` time + the splice at `_stmt`."""

    def _inl_init(self):
        self._inl_map = {}          # callee name -> fd (sites to splice)
        self._inl_discard = set()   # names whose standalone copy is gone
        self._inl_imm_off = {}      # fd name -> slot-only param names
        self._inl_imm = {}          # ACTIVE imm map during a splice body
        self._inl_goto = {}         # fd name -> asm-goto body-label names
        self._inl_scoped = {}       # fd name -> ({seq: [(name, depth)]},
                                    #                    {id(group): seq})
        self._inl_analyze()

    # ---------------------------------------------------------- analysis --

    def _inl_analyze(self):
        cands = {n: fd for n, fd in self.funcs.items()
                 if fd.is_static and fd.inline_kind == "static-inline"
                 and fd.body is not None and not fd.variadic}
        alias_tgt = {t for t, _s, _n in self.aliases.values()}
        for n, fd in list(cands.items()):
            why = self._inl_universe(fd)
            if why:
                del cands[n]
        # call cycles (direct or mutual) stay the CALL law.
        calls = {n: self._inl_calls(fd.body) for n, fd in cands.items()}
        for n in list(cands):
            seen, stack, cyc = set(), list(calls.get(n, ())), False
            while stack:
                c = stack.pop()
                if c == n:
                    cyc = True
                    break
                if c in seen:
                    continue
                seen.add(c)
                stack.extend(calls.get(c, ()))
            if cyc:
                del cands[n]
        taken = set()
        for fd in self.funcs.values():
            if fd.body is not None:
                taken |= self._inl_addr_names(fd.body)
        for vd in self.globals.values():
            if vd.init is not None:
                taken |= self._inl_addr_names(vd.init)
        sites = {}
        for fd in self.funcs.values():
            if fd.body is not None:
                self._inl_sites(fd.body, sites)
        for n, fd in cands.items():
            if n in alias_tgt or n in taken:
                continue
            if not sites.get(n):
                continue                       # W-R: VALUE sites cover too
            self._inl_map[n] = fd
            self._inl_discard.add(n)
            gl = _inl_goto_names(fd.body)
            if gl:
                self._inl_goto[n] = gl

    def _inl_universe(self, fd):
        """Reason the fd CANNOT be spliced, or None. Records per-param
        slot-only names for the imm-map guard."""
        slot_only = set()
        rt = self._decay(self._untype(fd.ret_type))
        is_void = isinstance(rt, ast.BuiltinType) and rt.name == "void"
        if not is_void and (isinstance(rt, (ast.StructType, ast.ArrayType))
                            or _fp(rt) or is_i128(rt)):
            return "return type not void/scalar/pointer"
        for p in fd.params:
            pt = self._decay(self._untype(p.type))
            if _fp(pt) or isinstance(pt, ast.StructType) or is_i128(pt):
                return "param not scalar/pointer/array"
        pnames = {p.name for p in fd.params}
        for s in _stmts_of(fd.body):
            if isinstance(s, ast.VarDecl) and (s.is_static
                                               or s.asm_bind is not None):
                return "static/register-asm local"
            if isinstance(s, ast.LabelDecl):
                return "__label__"
            if isinstance(s, ast.Goto):
                return "C goto in the body stays the CALL law"  # w03
            if isinstance(s, ast.AsmStmt) and (s.goto_ or s.labels):
                # W-R: asm-goto enters under the label law below;
                # outputs+goto is the measured gcc w05 value-DIVERGE.
                if s.outs:
                    return "asm goto with outputs stays the CALL law"
                if not s.goto_:
                    return "asm label section without goto"
            if isinstance(s, ast.Return) and s.value is not None and is_void:
                return "value return in void fn"
            if isinstance(s, ast.AsmStmt):
                # Only WRITING operands pin a param to its slot: outputs
                # and `+`/`=` constraints. A read-only `"i"(feat)` input
                # is exactly the W-P witness — it rides the imm-map.
                def writes(o):
                    return o in s.outs or "=" in o.constraint \
                        or "+" in o.constraint
                for o in tuple(s.outs) + tuple(s.ins):
                    if not writes(o):
                        continue
                    e = o.expr
                    while isinstance(e, ast.Cast):
                        e = e.operand
                    if isinstance(e, ast.Ident) and e.name in pnames:
                        slot_only.add(e.name)
        labels = {s.name for s in _stmts_of(fd.body)
                  if isinstance(s, ast.Label)}
        gnames = _inl_goto_names(fd.body)
        # M4 W-S (MC 12716): labels DEFINED inside `({...})` groups ride
        # a per-site scoped mint (the `_THIS_IP_` 191-crowd shape: a
        # group-local `__label__`+def+`&&ref` spliced into a caller that
        # never saw it). A DUPLICATE inside ONE group is invalid C
        # (gcc l12 LOUD) — the candidate stays CALL law so the callee's
        # own copy emits the honest §2.5 wall, never a silent splice.
        gdefs, gseq = _inl_group_defs(fd.body)
        if gdefs is None:
            return "duplicate label inside one braced group (invalid C "  \
                   "— gcc l12; the copy posture catches it LOUD)"
        if gdefs:
            self._inl_scoped[fd.name] = (gdefs, gseq)
        if gnames:
            # W-R label law (cpufeature.h:187 shape): targets sit
            # FLAT at the body top, no other label anywhere (below-
            # top = `({...})` groups stay CALL law; §2.5 not re-lit).
            # W-S COMMIT-0 (MC 12716, gate 12715 F-1): the former clause
            # "asm-goto body with a statement-expression" is REMOVED —
            # structurally dead: _stmts_of surfaces only stmt_children
            # outputs and stmt_children never yields an expression-
            # position StmtExpr (VarDecl/ExprStmt yield []), so the
            # isinstance test could never fire. The shape it NAMED
            # measures PAIR (gate x15; suite leg test_ws0_stmtexpr_body_
            # splices): asm-goto NESTED inside a `({...})` stays LOUD
            # through the clauses below — the goto-name walk is
            # statement-based, so a nested goto never claims a flat
            # label and the plain-label clause owns the shape (own
            # probe f1_se1: refusal + the copy's S5/L4 'i' twin).
            top = {s.name for s in fd.body.body
                   if isinstance(s, ast.Label)}
            if labels != top:
                return "asm-goto label below the body top"
            if not labels >= gnames:
                return "asm-goto target label never defined"
            if labels - gnames:
                return "plain label w/o asm-goto stays the CALL law"
        elif labels:
            return "labels without asm-goto stay the CALL law"
        for e in _exprs_of(fd.body):
            nm = _writes_ident(e)
            if nm is not None:
                slot_only.add(nm)
        self._inl_imm_off[fd.name] = slot_only
        return None

    def _inl_calls(self, body):
        return {e.callee.name for e in _exprs_of(body)
                if isinstance(e, ast.Call)
                and isinstance(e.callee, ast.Ident)}

    def _inl_addr_names(self, node):
        """Names used as VALUES (anything but a direct callee position):
        every Ident mention MINUS the names that appear only as the
        callee of a direct call (a bare mention of a function name —
        `&f`, `= f`, `[f]` in an initializer — is the address). Type/
        struct positions carry no Idents; conservative either way."""
        names, callees = set(), set()
        for e in _exprs_of(node):
            if isinstance(e, ast.Ident):
                names.add(e.name)
            elif isinstance(e, ast.Call) and isinstance(e.callee,
                                                       ast.Ident):
                callees.add(e.callee.name)
        return names - callees

    def _inl_sites(self, body, sites):
        # W-R: coverage is positional-INDEPENDENT (statement seam AND
        # value seam); the True/False split of the W-P all-statement law
        # is gone — every Ident call site counts.
        pos = set()
        for s in _stmts_of(body):
            if isinstance(s, ast.ExprStmt) and \
                    isinstance(s.expr, ast.Call) and \
                    isinstance(s.expr.callee, ast.Ident):
                pos.add(id(s.expr))
                sites.setdefault(s.expr.callee.name, []).append(True)
        for e in _exprs_of(body):
            if isinstance(e, ast.Call) and isinstance(e.callee, ast.Ident) \
                    and id(e) not in pos:
                sites.setdefault(e.callee.name, []).append(False)

    # ------------------------------------------------------------- splice --

    def _splice_call(self, call):
        fd = self._inl_map[call.callee.name]
        if len(call.args) != len(fd.params):
            self._err(call, "inline splice arity mismatch (internal law)",
                      call.callee.name)
        saved = (dict(self.fn.locals), self._fn_ret, self._sret,
                 self.fn.epilogue, self.loops, self._inl_imm)
        self.fn.epilogue = self._label("inlend")
        self._fn_ret = fd.ret_type
        self._sret = None
        self.loops = []                  # stray break/continue LOUD law
        outer = self._inl_imm
        imm = {}
        for p, a in zip(fd.params, call.args):
            self._emit_expr(a)
            self._convert(p.type, a)     # §2.2 conversion, the call law
            off = self._slot(p.type, a)
            self._e("movq %rax, {}(%rbp)".format(off))
            self.fn.locals[p.name] = (off, self._decay(
                self._untype(p.type)))
            # W-R TRANSITIVE SITE LAW (own table w02): an argument
            # folds THROUGH the map of the splice we are nested in
            # (`h(0)` maps bit=0; its body's `g(8 + bit)` site folds
            # 8; that body's `f(bit)` answers 8) — the chain gcc -Os
            # propagation walks. A RUNTIME Ident folds to None from
            # the engine (the slot-only S5/L4 twin stands); the old
            # blanket Ident-ban only blocked this sound chain.
            v = self._asm_const(a)
            if v is not None and p.name not in \
                    self._inl_imm_off.get(fd.name, ()):
                imm[p.name] = v
        self._inl_imm = imm
        self._stmt(self._inl_site_body(fd))   # the ONE statement emitter
        self.fn.lines.append("{}:".format(self.fn.epilogue))
        (self.fn.locals, self._fn_ret, self._sret, self.fn.epilogue,
         self.loops, self._inl_imm) = saved

    def _inl_site_body(self, fd):
        """THE per-site splice body. An asm-goto candidate gets a CLONE
        whose body labels carry FRESH minted names — the measured gcc
        law of per-copy label scoping (own table w01/w11: shared `t_yes`
        merges the arms; a caller's own same-named label must not
        collide). The minted names ride fn_labels as identity entries
        (flat depth 0, §2.5); the clone rewrites Label stmt, asm-goto
        label list AND `%l[old]` escapes TOGETHER (a partial rename is
        the plant-1 class). Other candidates splice the shared body
        untouched (W-P posture, byte-for-byte)."""
        names = self._inl_goto.get(fd.name)
        scoped = self._inl_scoped.get(fd.name)
        if not names and not scoped:
            return fd.body
        fresh = {}
        for nm in sorted(names or ()):
            fresh[nm] = self._label("inl_" + nm)
            self.fn_labels[fresh[nm]] = fresh[nm]
        scoped_fresh = None
        if scoped:
            # W-S per-site scoped mint: ONE fresh name per (group, name)
            # per site — two groups sharing `__here` in one body get TWO
            # freshes (the l13 pair law), and each minted name registers
            # flat with the §2.4d depth of ITS def (a jump INTO the
            # cloned group stays LOUD at the caller too).
            gdefs, gseq = scoped
            scoped_fresh = {}
            for seq in sorted(gdefs):
                m = {}
                for nm, d in sorted(gdefs[seq]):
                    m[nm] = self._label("inl_" + nm)
                    self.fn_labels[m[nm]] = m[nm]
                    self._lbl_depth[m[nm]] = d
                scoped_fresh[seq] = m
        return inl_clone(fd.body, fresh, scoped=scoped_fresh,
                         seq_by_id=gseq if scoped else None)


# --------------------------------------------------------------- walkers --

def _stmts_of(body):
    out, stack = [], [body]
    while stack:
        s = stack.pop()
        if s is None or not _is_stmt(s):
            continue
        out.append(s)
        stack.extend(stmt_children(s))
    return out


def _is_expr(x):
    """An EXPRESSION field value: an AST node that is neither a
    statement nor a struct/member decl node."""
    return (isinstance(x, ast.Node) and not _is_stmt(x)
            and not isinstance(x, (ast.StructType, ast.Member)))


def _is_stmt(s):
    return isinstance(s, (ast.Compound, ast.ExprStmt, ast.If, ast.While,
                          ast.DoWhile, ast.For, ast.Switch, ast.Case,
                          ast.CaseRange, ast.Default, ast.Break,
                          ast.Continue, ast.Return, ast.Goto, ast.Label,
                          ast.LabelDecl, ast.AsmStmt, ast.VarDecl,
                          ast.StmtExpr))


def _exprs_of(node):
    """Every expression of a body (descends `({...})` bodies too).
    W-R repair: an EXPRESSION root (`int (*p)(void) = f;` — the whole
    vd.init is a bare Ident/Call) now walks too; the statement-root
    assumption left every global-init address-taken blind (the taken
    law never saw `= f`, `[f]`-style decay — W-P hid it because plain
    value sites were not covered then)."""
    out = []

    def ex(e):
        if not _is_expr(e):
            return
        out.append(e)
        if not dataclasses.is_dataclass(e) or isinstance(
                e, (ast.StructType, ast.Member)):
            return
        for f in dataclasses.fields(e):
            v = getattr(e, f.name, None)
            for x in (v if isinstance(v, (tuple, list)) else (v,)):
                if isinstance(x, ast.StmtExpr):
                    st(x)
                elif _is_expr(x):
                    ex(x)

    def st(s):
        if s is None:
            return
        if isinstance(s, ast.StmtExpr):
            for x in s.stmts:
                st(x)
            if s.value is not None:
                ex(s.value)
            return
        if not _is_stmt(s) or not dataclasses.is_dataclass(s):
            return
        for f in dataclasses.fields(s):
            v = getattr(s, f.name, None)
            for x in (v if isinstance(v, (tuple, list)) else (v,)):
                if _is_expr(x):
                    ex(x)
                elif x is not None and _is_stmt(x):
                    st(x)

    if _is_expr(node):          # W-R: an expression root (vd.init) walks
        ex(node)
    else:
        st(node)
    return out


def _writes_ident(e):
    """Param-name written by this expression (assign / ++ / --), else None."""
    if isinstance(e, (ast.Assign, ast.AssignOp)):
        t = e.target
        while isinstance(t, ast.Cast):
            t = t.operand
        if isinstance(t, ast.Ident):
            return t.name
    if isinstance(e, ast.IncDec) and isinstance(e.operand, ast.Ident):
        return e.operand.name
    return None


def _inl_goto_names(body):
    """C identifiers the body's asm-gotos target."""
    names = set()
    for s in _stmts_of(body):
        if isinstance(s, ast.AsmStmt) and (s.goto_ or s.labels):
            names.update(s.labels)
    return names
