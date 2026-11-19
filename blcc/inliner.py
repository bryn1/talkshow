"""M4 W-P (MC 12705, plan AMENDMENT-17): THE inline pass.

ONE mechanism at the existing statement seam. For a file-scope
`static inline` function (gnu89 header-helper shape, with or without
`__always_inline` — measured rows i05/i08: gcc -Os inlines AND discards
BOTH spellings) whose every call site sits in STATEMENT position and
whose body is inside the splice universe, the call is REPLACED by the
body: params copy-in to fresh caller-frame slots in left-to-right order
with the §2.2 conversion law (row i01: `f(i++, i)` measures 8 both
sides — the call-by-value copy, once per param), the body rides the SAME
statement emitter (`_stmt` — the pipeline is not forked), and a param
whose argument folds to a constant answers the imm-closure fold with
that literal (row i03: gcc answers `.word` with 245 post-inline — the
nospec-branch.h:375 `"i" (param)` law; `alternative_msr_write`'s `[f]
"i"(feature)` folds to $245 at the copy).

What it REPLACES (no parallel pipeline): (1) for a covered call site,
the `_stage_call` register staging + `call sym` text; (2) for a
static-inline whose sites are ALL spliced, the standalone `_emit_func`
copy in the compile() loop — which also makes a ZERO-call-site static
inline vanish (the discard the walk's first object, init/main.o with an
uncalled `alternative_msr_write`, needs; gcc's own -Os posture — rows
i03/i05: no symbol survives in its .s).

Universe guards — a MISS keeps today's call+copy posture untouched
(including today's LOUD walls; never a silent rewrite):
  * scalar/pointer params, void-or-scalar return (the sret door and the
    fp classes stay the CALL law; `self._sret` is masked during a splice
    so a spliced `return` can never write the CALLER's hidden pointer);
  * no `goto`, no label decls/refs, no `asm goto` operands, no static
    locals, no `register … asm` binds, no `__label__`;
  * not recursive, no call cycle (recursion stays today's twin — row
    i06: gcc answers 24 without a copy, blcc keeps the copy and the
    VALUE pairs);
  * not address-taken anywhere (fn-pointer use keeps the real symbol);
  * not an alias target (the §6 `.set` must have its body);
  * per-param: the imm-map applies only when the body neither writes the
    param (assignment, ++/--, nor an asm operand naming it) nor takes
    its address — slot and literal must not be able to diverge. A
    param without the map is slot-only: `"i"(param)` under a
    NON-constant arg keeps the S5/L4 refusal, one frame earlier (named
    LOUD twin; the closure itself is UNTOUCHED).
"""
import dataclasses

from blcc import ast
from blcc.expr_codegen import _fp
from blcc.types import stmt_children, is_i128

_NOT_SCALAR = (ast.StructType, ast.ArrayType)


class InlinerMixin:
    """Call-graph analysis at `_collect` time + the splice at `_stmt`."""

    def _inl_init(self):
        self._inl_map = {}          # callee name -> fd (sites to splice)
        self._inl_discard = set()   # names whose standalone copy is gone
        self._inl_imm_off = {}      # fd name -> slot-only param names
        self._inl_imm = {}          # ACTIVE imm map during a splice body
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
        # call cycles: a candidate reachable from itself (direct or
        # mutual) stays the CALL law (recursion LOUD twin).
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
            if not sites.get(n) or any(not p for p in sites[n]):
                continue
            self._inl_map[n] = fd
            self._inl_discard.add(n)

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
            if isinstance(s, ast.AsmStmt) and (s.goto_ or s.labels):
                return "asm goto"
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
        self._inl_imm = {}
        for p, a in zip(fd.params, call.args):
            self._emit_expr(a)
            self._convert(p.type, a)     # §2.2 conversion, the call law
            off = self._slot(p.type, a)
            self._e("movq %rax, {}(%rbp)".format(off))
            self.fn.locals[p.name] = (off, self._decay(
                self._untype(p.type)))
            v = self._asm_const(a)
            if isinstance(a, ast.Ident):
                v = None                 # no map for a passed Ident
            if v is not None and p.name not in \
                    self._inl_imm_off.get(fd.name, ()):
                self._inl_imm[p.name] = v
        self._stmt(fd.body)              # the ONE statement emitter
        self.fn.lines.append("{}:".format(self.fn.epilogue))
        (self.fn.locals, self._fn_ret, self._sret, self.fn.epilogue,
         self.loops, self._inl_imm) = saved


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
    """An EXPRESSION field value: any AST node that is neither a
    statement nor a struct/member declaration node (type nodes that are
    not structish are inert for the Call/Ident walks below)."""
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
    """Every expression of a body, descending statement fields,
    expression fields and statement-expression bodies."""
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
