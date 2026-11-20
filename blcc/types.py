# LINES reason: the type law (sizes, UAC, decay, fold, layout, typeof) is the
# single §4 answer-table shared by parser, sema and both codegens — one file
# keeps the measured gcc gnu89 law rows beside the code that implements them.
"""Type answers for codegen (ARCHITECTURE.md §4): sizes, the decay rule,
struct layout (§4 natural alignment), type-of-expression, and the §6 builtin
result kinds. This is the shared base of blcc.codegen.Codegen: every method
reads tables Codegen collects (structs/enums/globals/sigs/fn.locals/tu)."""
from __future__ import annotations

from typing import Dict, List, Tuple

from blcc import ast, predef
from blcc.lexer import DiagError
from blcc.runtime import BUILTINS

TYPE_SIZE = {
    # M2 §1 row 2 (gcc 11.4 LP64 measured): the full scalar family. Names are
    # the PARSER-NORMALIZED spellings (`signed int` → `int`, bare `signed`
    # → `int`; `signed char` keeps its distinct identity).
    # M4 W2 COMMIT-0 (MC 12545): C99 `_Bool` — measured sizeof == 1.
    "char": 1, "signed char": 1, "unsigned char": 1,
    "short": 2, "unsigned short": 2,
    "int": 4, "unsigned int": 4,
    "long": 8, "unsigned long": 8,
    "long long": 8, "unsigned long long": 8,
    # M4 W-B (MC 12596): __int128 family — sizeof/alignof MEASURED 16/16
    # (gcc 11.4, facts1.c); spec words commute with the sign family only.
    "__int128": 16, "unsigned __int128": 16,
    "float": 4, "double": 8,          # STORAGE only (§1 row 14): arith LOUD
    "_Bool": 1,                      # sizeof measured 1; promotes to int
    "void": 0,
}
UNSIGNED_NAMES = frozenset({"unsigned char", "unsigned short", "unsigned int",
                            "unsigned long", "unsigned long long",
                            "unsigned __int128"})
_RANK = {"int": 1, "unsigned int": 1, "long": 2, "unsigned long": 2,
         "long long": 3, "unsigned long long": 3,
         # M4 W-B (MC 12596): 128-bit sits ABOVE long long (gcc-measured
         # UAC: any 64-bit operand converts UP to the 128 operand's type).
         "__int128": 4, "unsigned __int128": 4}
_UNSIGNED_OF = {"int": "unsigned int", "long": "unsigned long",
                "long long": "unsigned long long",
                "__int128": "unsigned __int128"}

# M4 W-B (MC 12596): the 128-bit class, one membership test everywhere.
I128_NAMES = frozenset({"__int128", "unsigned __int128"})


def is_i128(ty) -> bool:
    return isinstance(ty, ast.BuiltinType) and ty.name in I128_NAMES


def is_unsigned(ty) -> bool:
    return isinstance(ty, ast.BuiltinType) and ty.name in UNSIGNED_NAMES


def _roundup8(n: int) -> int:
    return (n + 7) & ~7


def walk_fields(members, structs):
    """Flat (name, type) view of a member list with anonymous nested
    struct/union members PROMOTED (gcc 11.4 -std=gnu89 measured, MC 12460
    stage T+7: an untagged inline definition with no declarator is an
    anonymous member whose names join the enclosing namespace; a TAGGED
    specifier without declarator is never a Member record at all)."""
    for m in members:
        if m.name is not None:
            yield m.name, m.type
        elif getattr(m, "width", None) is None:
            # §1 row 12 (M45): an ANONYMOUS bitfield has no declarator
            # too, but contributes NO name — only bits (measured).
            nested = structs.get(m.type.tag)
            if nested:
                for pair in walk_fields(nested, structs):
                    yield pair



def what(n) -> str:
    """§8 literal-naming: the offending CONSTRUCT as found '...' — never a
    Python node class name (DA-c3 P1-1). Identifiers render as their own
    source token; the fallback never echoes a class name. Shared by the
    parser, sema and both codegens (module function: the mixins stay
    independent)."""
    if isinstance(n, ast.Ident):
        return n.name
    if isinstance(n, ast.IntLit):
        return "integer literal"
    if isinstance(n, ast.CharLit):
        return "char literal"
    if isinstance(n, ast.FloatLit):
        return "floating literal"
    if isinstance(n, ast.StrLit):
        return "string literal"
    if isinstance(n, ast.LabelAddr):
        return "&&label"
    if isinstance(n, ast.StmtExpr):
        return "statement expression"
    if isinstance(n, ast.TypeOf):
        return "__typeof__"
    if isinstance(n, ast.Qualified):
        return what(n.inner)
    if isinstance(n, ast.Call):
        return "call expression"
    if isinstance(n, ast.Cast):
        return "cast expression"
    if isinstance(n, ast.Sizeof):
        return "sizeof expression"
    if isinstance(n, ast.Alignof):
        return "alignof expression"              # M4 W2.5 (MC 12557)
    if isinstance(n, ast.Binary):
        return "{} expression".format(n.op)
    if isinstance(n, ast.Cond):
        return "conditional expression"        # §1c (MC 12486), §8 style
    if isinstance(n, ast.Comma):
        return "comma expression"              # §1c, §8 style
    if isinstance(n, ast.Unary):
        return "{} expression".format(n.op)
    if isinstance(n, ast.BuiltinType):
        return n.name
    if isinstance(n, ast.PtrType):
        return "pointer"
    if isinstance(n, ast.ArrayType):
        return "array"
    if isinstance(n, ast.FuncType):
        return "function"                             # M4 W1
    if isinstance(n, ast.StructType):
        return "struct {}".format(n.tag)
    if isinstance(n, ast.InitList):
        return "{"
    return "construct"


def stmt_children(s):
    """Statement children of a node — the ONE walk shared by the label
    pre-pass (§2A M2-C1), the statement-expression type simulation and
    the jump-depth accounting (Codegen._child_stmts delegates)."""
    if isinstance(s, ast.Compound):
        return list(s.body)
    if isinstance(s, ast.If):
        return [x for x in (s.then, s.orelse) if x is not None]
    if isinstance(s, (ast.While, ast.DoWhile, ast.For)):
        return [s.body]
    if isinstance(s, ast.Switch):
        return list(s.body)
    if isinstance(s, ast.StmtExpr):
        return list(s.stmts)      # §2.4: labels live inside `({...})`
    if isinstance(s, (ast.Case, ast.Default, ast.CaseRange, ast.Label)):
        return [s.stmt] if s.stmt is not None else []
    return []


class CompatLawMixin:
    """§2.12/§2.6d THE ONE type-identity law text (M4 W-L, MC 12665).
    Two hosts run it: TypeMap (codegen — the §2.12 call fold, _Generic)
    and the Parser fold host (bitfield-width/enum/SA folding through
    fold_truthy's compat arm). Each host supplies the
    `_tyof_materialize(expr)` hook — TypeMap._ty on the codegen side,
    the parser's shipped expr_type mirror on the fold side (the SAME
    peel _csize/_calign already ride) — and a `_fold_const(size, at)`
    constant law for the ArrayType arm."""

    # -- §2.12 / §2.6d: the two type-identity predicates ----------------------

    def _resolve_tyof(self, ty):
        """Resolve __typeof__ wrappers WITHOUT dropping qualifiers — the
        compatibility predicates need the pointee-level markers that
        _untype erases for layout (§2.12: `(int*, const int*)` = 0)."""
        while isinstance(ty, ast.TypeOf):
            ty = (ty.typ if ty.typ is not None
                  else self._tyof_materialize(ty.expr))
        return ty

    @staticmethod
    def _split_q(ty):
        """Top-level qualifier set + the unqualified spine."""
        qs = []
        while isinstance(ty, ast.Qualified):
            qs.append(ty.qual)
            ty = ty.inner
        return frozenset(qs), ty

    def _ty_eq_strict(self, a, b) -> bool:
        """C 'compatible types' as the oracle applies it to _Generic keys
        and to POINTER POINTERS (§2.6d: key qualifiers ARE significant;
        §2.12: `(int*, const int*)` = 0 — pointee qual is NOT top-level).
        Nominal struct identity by TAG; arrays by (element, size)."""
        qa, a = self._split_q(a)
        qb, b = self._split_q(b)
        if qa != qb:
            return False
        a = self._resolve_tyof(a)      # may expose a new Qualified layer
        b = self._resolve_tyof(b)
        qa, a = self._split_q(a)
        qb, b = self._split_q(b)
        if qa != qb:
            return False
        if isinstance(a, ast.BuiltinType) and isinstance(b, ast.BuiltinType):
            return a.name == b.name    # char vs signed char: distinct names
        if isinstance(a, ast.PtrType) and isinstance(b, ast.PtrType):
            return self._ty_eq_strict(a.inner, b.inner)
        if isinstance(a, ast.ArrayType) and isinstance(b, ast.ArrayType):
            if a.size is None or b.size is None:
                return False
            return (self._fold_const(a.size, a) ==
                    self._fold_const(b.size, b) and
                    self._ty_eq_strict(a.inner, b.inner))
        if isinstance(a, ast.StructType) and isinstance(b, ast.StructType):
            return a.tag == b.tag      # nominal: same-shape, new tag ⇒ 0
        if isinstance(a, ast.FuncType) and isinstance(b, ast.FuncType):
            # M4 W1: fn-ptr TYPE equality (reached through PtrType recursion
            # — `__builtin_types_compatible_p(hnd_t, hnd_t)` spells the TYPE
            # with a typedef NAME, no abstract declarator).
            return (a.variadic == b.variadic
                    and len(a.params) == len(b.params)
                    and self._ty_eq_strict(a.ret, b.ret)
                    and all(self._ty_eq_strict(x.type, y.type)
                            for x, y in zip(a.params, b.params)))
        return False

    def _types_compatible(self, a, b) -> bool:
        """__builtin_types_compatible_p (§2.12 MEASURED): TOP-LEVEL quals
        are IGNORED on both sides (`(int, const int)` = 1), everything
        below stays strict (`(int*, const int*)` = 0)."""
        _, a = self._split_q(self._resolve_tyof(a))
        _, b = self._split_q(self._resolve_tyof(b))
        return self._ty_eq_strict(a, b)


class TypeMap(CompatLawMixin):

    # -- compat-law host hook: codegen-side materializer ----

    def _tyof_materialize(self, expr):
        return self._ty(expr)

    # -- diagnostics ---------------------------------------------------------

    def _err(self, at, message: str, found: str, phase: str = "sema"):
        raise DiagError(phase, at.file, at.line, at.col, message, found)

    def _what(self, n) -> str:
        """§8 literal-naming — see module-level what()."""
        return what(n)

    # -- type sizing (§4 table lives HERE, never in ast.py) ---------------------

    def _untype(self, ty: ast.Node) -> ast.Node:
        """§2.6 / §2A M2-C5 leg 3: materialize `__typeof__` into the
        concrete type node it stands for — `__typeof__(expr)` is the type
        of the expression (TYPED, never evaluated: `__typeof__(called=1)`
        leaves `called` untouched, §2.6 measured), `__typeof__(type)` the
        type itself. Recursive through Ptr/Array wrappers.

        M4 W-H (MC 12645): the `auto` flag marks the __auto_type FORM —
        same walk PLUS the MEASURED value-conversion law: the declared
        type is the INITIALIZER'S type after value conversion (arrays/
        functions DECAY, TOP-level qualifiers DROP, pointed-to quals
        survive inside). That is exactly where the two forms differ
        (typeof(ca) is int[4]; typeof(ci) keeps const — measured
        difference table in tests/test_core_m4wh1.py)."""
        if isinstance(ty, ast.TypeOf):
            if ty.auto:
                return self._auto_value_ty(ty)
            if ty.typ is not None:
                return self._untype(ty.typ)
            return self._ty(ty.expr)
        if isinstance(ty, ast.Qualified):
            return self._untype(ty.inner)   # layout ignores qualifiers
        if isinstance(ty, ast.PtrType):
            return ast.PtrType(ty.file, ty.line, ty.col,
                               self._untype(ty.inner))
        if isinstance(ty, ast.ArrayType):
            # §1 row 13 (M46): the FAM marker must SURVIVE materialization
            # — dropping it turned sizeof(s.v) into the silent 8 of param
            # decay instead of the gcc ERROR (caught by test_fam_sof).
            return ast.ArrayType(ty.file, ty.line, ty.col,
                                 self._untype(ty.inner), ty.size,
                                 getattr(ty, "fam", False))
        return ty

    def _auto_value_ty(self, ty: ast.Node) -> ast.Node:
        """M4 W-H (MC 12645): the MEASURED __auto_type value law —
        type of the initializer after VALUE CONVERSION: top-level
        qualifiers drop (`__auto_type v = ci; v = 7;` rc 0, the typeof
        twin rc 1), arrays and functions DECAY (`ca` -> int*, `foo` ->
        fn ptr; sizeof 8 both, probes at_probe.py), pointed-to quals
        stay where they are (inside the spine — NOT re-wrapped, the
        law only strips the TOP). A `void` init has no value type: the
        same measured sentence the parser arm ships for the light
        forms (`variable or field declared void`, gcc rc1)."""
        vty = self._untype(self._ty(ty.expr))
        _qs, spine = self._split_q(vty)
        if isinstance(spine, ast.BuiltinType) and spine.name == "void":
            self._err(ty, "variable or field declared void (measured gcc "
                      "rc1: there is no type to infer from a void "
                      "expression)", "__auto_type")
        return self._decay(spine)

    def _ty_stmtexpr(self, n: ast.Node) -> ast.Node:
        """§2.4(c): type of `({...; e;})` = type of the final expression —
        resolved with the braced group's declarations IN SCOPE (types
        registered in a locals snapshot; no emission, restore always)."""
        saved = dict(self.fn.locals)
        try:
            stack = list(n.stmts)
            while stack:
                s = stack.pop(0)
                if isinstance(s, ast.VarDecl):
                    self.fn.locals[s.name] = (0, self._untype(s.type))
                stack.extend(stmt_children(s))
            if n.value is None:
                return ast.BuiltinType(n.file, n.line, n.col, "void")
            return self._ty(n.value)
        finally:
            self.fn.locals = saved

    def _size(self, ty: ast.Node, at=None) -> int:
        if isinstance(ty, (ast.TypeOf, ast.PtrType, ast.ArrayType,
                           ast.Qualified)):
            ty = self._untype(ty)
        if isinstance(ty, ast.BuiltinType):
            if ty.name == "void":
                # M4 W-K (MC 12663): the §4 wall is DEAD — GNU sizeof(void)
                # is 1 (gcc 11.4 MEASURED rc0 at every std flag, no
                # warning; sv_* probes) and the SAME 1 is the scale of
                # `void *p + k` / the byte-unit answer of `void *p - void
                # *q` — the bitops CONST_MASK_ADDR `(void *)(addr) +
                # ((nr)>>3)` carriers (236 first-blockers at the close
                # sweep). The fold mirror (`parser._csize_impl`) mirrors
                # this arm; the old law LOUDed here while the fold said
                # 0 — one compiler, two answers, neither gcc's.
                return 1
            return TYPE_SIZE[ty.name]
        if isinstance(ty, ast.PtrType):
            return 8
        if isinstance(ty, ast.StructType):
            return self._struct_layout(ty, at or ty)[1]
        if isinstance(ty, ast.ArrayType):
            esz = self._size(ty.inner, at)
            if ty.size is None:        # parameter: decays to pointer (§4)
                if getattr(ty, "fam", False):
                    # §1 row 13 (M46): gcc ERROR "invalid application of
                    # sizeof to incomplete type" — the legacy v[0] (a
                    # COMPLETED zero-size array) reads 0 instead; both
                    # pinned in test_core_m2_fam.
                    self._err(at or self.tu, "cannot apply 'sizeof' to a "
                              "flexible array member (gcc ERROR: incomplete "
                              "type, §1 row 13)", "sizeof")
                return 8
            return esz * self._arrlen(ty, at)
        if isinstance(ty, ast.FuncType):
            # M4 W1: `sizeof(FT)` for a typedef'd FUNCTION type — gcc
            # ERROR "invalid application of 'sizeof' to function type".
            # A fn-PTR (`sizeof(hnd_t)` where hnd_t is `(*…)(…)`) is a
            # PtrType and answers 8 on the arm above — never reaches here.
            self._err(at or self.tu, "'sizeof' of a 'function' type is a "
                      "gcc ERROR (§4 — a function is not an object)",
                      "function")
        self._err(at or self.tu, "cannot size this type", self._what(ty))

    # -- constant-folded array sizes (P1-2: §4 sizes are expressions) ------------

    def _fold_ty(self, n, at):
        """M4 W-B (MC 12596): the TYPE a fold subexpression carries — the
        fold becomes WIDTH-aware exactly for the 128-bit class (the 64-bit
        arms keep their shipped wording and masks UNCHANGED). Answers None
        when the node is untyped in this context (the caller keeps the
        legacy 64-bit law)."""
        try:
            return self._decay(self._untype(self._ty(n)))
        except DiagError:
            return None

    @staticmethod
    def _wrapw(v, wbits, signed):
        m = (1 << wbits) - 1
        v &= m
        return ((v + 2 ** (wbits - 1)) % 2 ** wbits) - 2 ** (wbits - 1) \
            if signed and wbits else v

    def _wrap128(self, v, unsigned):
        m = (1 << 128) - 1
        v &= m
        return v if unsigned else ((v + 2 ** 127) % 2 ** 128) - 2 ** 127

    def _fold_const(self, n, at) -> int:
        """Constant-fold an array-size expression (§4: integer literals, enum
        constants, + - * / % and parentheses; gcc's C rules)."""
        if isinstance(n, ast.IntLit):
            return n.value
        if isinstance(n, ast.CharLit):
            return n.value - 256 if n.value > 127 else n.value
        if isinstance(n, ast.Ident) and n.name in self.enums:
            return self.enums[n.name]
        if isinstance(n, ast.Ident) and getattr(self, "_inl_imm", None):
            # M4 W-R row i16 (MC 12714): a spliced-body param bound to
            # its caller arg's literal answers the SAME fold engine
            # THROUGH composed operand expressions — the cpufeature
            # `[bitnum] "i" (1 << (bit & 7))` folds at the site. The
            # map is only ever ACTIVE during a splice (the guard law at
            # `_splice_call` owns it); inert everywhere else. A symbol
            # closure (tuple) is NOT an int fold — the Ident stays on
            # the `_asm_fold` route that answers symbol texts.
            v = self._inl_imm.get(n.name)
            if isinstance(v, int):
                return v
        if isinstance(n, ast.Unary) and n.op == "~":
            v = self._fold_const(n.operand, at)
            oty = self._fold_ty(n.operand, at)
            if is_i128(oty):           # M4 W-B: 128-wide wrap (measured)
                return self._wrap128(~v, is_unsigned(oty))
            v = ~v & 0xFFFFFFFFFFFFFFFF
            return ((v + 2 ** 63) % 2 ** 64) - 2 ** 63
        if isinstance(n, ast.Unary) and n.op in ("-", "+"):
            v = self._fold_const(n.operand, at)
            return -v if n.op == "-" else v
        if isinstance(n, ast.Unary) and n.op == "!":
            return 0 if self._fold_const(n.operand, at) else 1
        if isinstance(n, ast.Sizeof):
            # M2-C5 (§2.6 e1 leg): sizeof may ride an array-size /
            # choose_expr control: `char a[sizeof(__typeof__(1L)) - 8]`.
            if n.typ is not None:
                return self._size(n.typ, at or n)
            return self._size(self._ty(n.arg), at or n)
        if isinstance(n, ast.Alignof):
            # M4 W2.5 (MC 12557): alignof folds through the SAME
            # TypeMap._align law the struct layout already computes.
            if n.typ is not None:
                return self._align(n.typ, at or n)
            return self._align(self._ty(n.arg), at or n)
        if isinstance(n, ast.Binary):
            if n.op in ("&&", "||"):
                a = self._fold_const(n.left, at)
                if n.op == "&&" and a == 0:
                    return 0
                if n.op == "||" and a != 0:
                    return 1
                return self._fold_const(n.right, at)
            if n.op in ("<", "<=", ">", ">=", "==", "!="):
                a = self._fold_const(n.left, at)
                b = self._fold_const(n.right, at)
                return {
                    "<": lambda: a < b, "<=": lambda: a <= b,
                    ">": lambda: a > b, ">=": lambda: a >= b,
                    "==": lambda: a == b, "!=": lambda: a != b}[n.op]() and 1 or 0
            if n.op in ("&", "|", "^"):
                a = self._fold_const(n.left, at)
                b = self._fold_const(n.right, at)
                return {"&": lambda: a & b, "|": lambda: a | b,
                        "^": lambda: a ^ b}[n.op]()
            if n.op in ("<<", ">>"):
                a = self._fold_const(n.left, at)
                b = self._fold_const(n.right, at)
                lty = self._fold_ty(n.left, at)
                if is_i128(lty):       # M4 W-B: 128-bit fold law, 0..127
                    if b < 0 or b > 127:
                        self._err(at or n, "shift amount must be a "
                                  "constant in 0..127 for a 128-bit "
                                  "value (§4)", n.op)
                    v = (a << b) & ((1 << 128) - 1) if n.op == "<<" \
                        else a >> b
                    return self._wrap128(v, is_unsigned(lty))
                if b < 0 or b > 63:
                    self._err(at or n, "shift amount must be a constant in "
                              "0..63 (§4)", n.op)
                v = (a << b) & 0xFFFFFFFFFFFFFFFF if n.op == "<<" else a >> b
                return ((v + 2 ** 63) % 2 ** 64) - 2 ** 63
        if isinstance(n, ast.Cast):
            v = self._fold_const(n.operand, at)
            sty = self._fold_ty(n.operand, at)
            tty = (self._decay(self._untype(n.type))
                   if n.type is not None else None)
            if is_i128(sty) or is_i128(tty):
                # M4 W-B: a fold that CROSSES the 128-bit boundary wraps
                # through the TARGET width (measured: (u64)((u128)1<<64)
                # is 0; (u128)(long)-1 keeps all ones).
                if isinstance(tty, ast.BuiltinType) \
                        and tty.name in TYPE_SIZE and tty.name != "void":
                    if is_i128(tty):
                        return self._wrap128(v, is_unsigned(tty))
                    w = 8 * TYPE_SIZE[tty.name]
                    return self._wrapw(v, w, not is_unsigned(tty)
                                       and tty.name not in
                                       ("unsigned char", "unsigned short",
                                        "unsigned int", "unsigned long",
                                        "unsigned long long"))
                if isinstance(tty, ast.PtrType):
                    return self._wrapw(v, 64, False)
            return v
        if isinstance(n, ast.Cond):
            # §1c (MC 12486): constant `?:` folds like C's own constant
            # expression rule — fold the TEST, then ONLY the chosen arm
            # (the dead arm is never folded: `0 ? gv : 1` is a legal
            # constant even when gv is not — C11 6.6 "not both").
            v = self._fold_const(n.test, at)
            if n.gnu:
                return v if v != 0 else self._fold_const(n.arm2, at)
            return self._fold_const(n.arm1 if v != 0 else n.arm2, at)
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
                  self._what(n))

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
            inner = ty.inner
            if isinstance(inner, ast.ArrayType) and init.items and \
                    not all(self._whole_elem(inner, it) for it in init.items):
                cap = self._leaf_cap(inner, at)      # brace-elided flat rows
                n = -(-self._leaf_count(init.items) // cap) if cap \
                    else len(init.items)
            else:
                n = len(init.items)
        elif isinstance(init, ast.StrLit) and isinstance(ty.inner, ast.BuiltinType) \
                and TYPE_SIZE[ty.inner.name] == 1:
            n = len(init.value.encode("utf-8", "surrogateescape")) + 1
        if n is None:
            return ty                       # scalar init: the loud §4 reject owns
        return ast.ArrayType(ty.file, ty.line, ty.col, ty.inner,
                             ast.IntLit(ty.file, ty.line, ty.col, n))

    # -- array initializer descent (§6.7.9 brace elision, DA-c3 P0-2) ----------

    def _whole_elem(self, inner, it) -> bool:
        """True when item `it` initializes ONE element of type `inner`
        wholesale: a brace list, or a string literal for a char array row."""
        if isinstance(it, ast.InitList):
            return True
        return isinstance(it, ast.StrLit) and isinstance(inner, ast.ArrayType) \
            and isinstance(inner.inner, ast.BuiltinType) \
            and TYPE_SIZE[inner.inner.name] == 1

    def _leaf_cap(self, ty, at) -> int:
        """Scalar slots one value of `ty` holds (0 = opaque aggregate)."""
        if isinstance(ty, ast.ArrayType):
            return self._arrlen(ty, at) * self._leaf_cap(ty.inner, at)
        return 0 if isinstance(ty, ast.StructType) else 1

    def _leaf_count(self, items) -> int:
        """Scalar values a (possibly nested) initializer stream carries."""
        tot = 0
        for it in items:
            if isinstance(it, ast.InitList):
                tot += self._leaf_count(it.items)
            elif isinstance(it, ast.StrLit):
                tot += len(it.value.encode("utf-8", "surrogateescape")) + 1
            else:
                tot += 1
        return tot

    def _fill_plan(self, ty: ast.ArrayType, items, at):
        """Walk an array's element stream in memory order honoring C brace
        elision (§6.7.9): an element consumes one item (brace list, char-row
        string, scalar) — or, when the element is itself an array and the
        item is not a whole-element init, draws items straight into its
        slots. When items run out the tail is ZERO-filled: partial init is
        legal C and must not inherit frame garbage (local) or exceed the
        object size (global). ty must be SIZED (_sized_array_decl owns that
        upstream). Returns (plan, items_consumed); plan entries are
        ('init', byte_off, elem_ty, item) | ('zero', byte_off, nbytes, None).
        Both blcc.data (byte runs) and blcc.codegen (frame stores) consume
        this — one elision rule, two writers (DA-c3 P0-2)."""
        plan: List[Tuple] = []
        pos = [0]

        def fill_arr(a_ty, base):
            n = self._arrlen(a_ty, at)
            esz = self._size(a_ty.inner, at)
            i = 0
            while i < n:
                off = base + i * esz
                if pos[0] >= len(items):
                    plan.append(("zero", off, esz * (n - i), None))
                    return
                it = items[pos[0]]
                inner = a_ty.inner
                if isinstance(it, ast.ZeroFill):
                    pos[0] += 1                 # §1 row 10 padding
                    plan.append(("zero", off, esz, None))
                    i += 1
                    continue
                if isinstance(inner, ast.ArrayType) \
                        and not self._whole_elem(inner, it):
                    mark = len(plan)
                    fill_arr(inner, off)      # elide: fill this row's slots
                    if len(plan) == mark:
                        return                # stream dry mid-row
                    i += 1
                    continue
                pos[0] += 1
                plan.append(("init", off, inner, it))
                i += 1

        fill_arr(ty, 0)
        return plan, pos[0]

    # -- alignments (P2-2: natural C layout, never a flat 8) ----------------------

    def _tag_attr_list(self, ty):
        return getattr(self, "struct_tag_attrs", {}).get(ty.tag, ())

    def _attr_packed(self, ty) -> bool:
        return any(nm == "packed" for nm, _a in self._tag_attr_list(ty))

    def _tag_aligned(self, ty, at):
        best = None
        for nm, arg in self._tag_attr_list(ty):
            if nm == "aligned":
                # M4 W2.5 (MC 12557): bare `aligned` (arg None) = the
                # max-fundamental alignment 16 (measured gcc rc0).
                v = 16 if arg is None else self._fold_const(arg, at or ty)
                if v <= 0:
                    self._err(at or ty, "'aligned' attribute needs a "
                              "positive constant (§1 row 9)", "aligned")
                best = v if best is None else max(best or 0, v)
        return best

    def _mem_raise(self, m, at):
        best = None
        for nm, arg in getattr(m, "attrs", ()):
            if nm == "aligned":
                v = 16 if arg is None else self._fold_const(arg, at)
                if v <= 0:
                    self._err(at, "'aligned' attribute needs a positive "
                              "constant (§1 row 9)", "aligned")
                best = v if best is None else max(best or 0, v)
        return best

    def _malign(self, m, packed, at):
        """§1 row 9 layout law (M42): packed lowers the member to align
        1; `aligned(N)` RAISES it and, through it, the struct's align.
        The parse-time mirror is blcc.parser.Parser._malign_f."""
        a = 1 if packed else self._align(m.type, at)
        v = self._mem_raise(m, at)
        return max(a, v) if v is not None else a

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
            # M4 W-S (MC 12716): the DEFINED/INCOMPLETE law keys on
            # `is None` (the registry stores `()` for a DEFINED EMPTY
            # struct — the spinlock_types_up.h:25 `typedef struct { }
            # arch_spinlock_t` class; the falsy test conflated empty-
            # defined with incomplete — gate s02-s07 law table). gcc
            # -Os MEASURED: sizeof(struct {}) = 0, align 1, empty
            # member occupies zero bytes (next member keeps its
            # offset), &empty-member == outer address.
            if members is None:
                self._err(at or ty, "undefined struct '{}' — only fully defined "
                          "structs are in the subset (§4)".format(ty.tag), ty.tag)
            packed = self._attr_packed(ty)
            a = 1
            for m in members:
                if getattr(m, "width", None) is not None:
                    # §1 row 12 (M45): named bitfields align to their
                    # unit; anonymous contribute nothing (measured).
                    # W-F (MC 12621) REPLACES the packed DEFER: under
                    # packed a bitfield contributes ONLY its `aligned`
                    # raise (families measure align 1: desc/idt/tss/
                    # IO_APIC all /1; E6 char aligned(4) -> 4; tag
                    # aligned(8) -> E7 8).
                    u = self._bf_unit(m, packed, at)
                    if m.width == 0 or m.name is None:
                        continue
                    r = self._mem_raise(m, at) or 0
                    a = max(a, (r if packed else max(u, r)))
                    continue
                a = max(a, self._malign(m, packed, at))
            ov = self._tag_aligned(ty, at)
            return max(a, ov or 0)
        return 8

    def _decay(self, ty: ast.Node) -> ast.Node:
        if isinstance(ty, ast.ArrayType):
            return ast.PtrType(ty.file, ty.line, ty.col, ty.inner)
        if isinstance(ty, ast.FuncType):
            # C 6.7.6.3p7 (M4 W1 1b): a FUNCTION type decays to pointer-to-
            # function — the parameter-position law of the fn-ptr declarator.
            return ast.PtrType(ty.file, ty.line, ty.col, ty)
        return ty

    def _struct_has_fp(self, ty: ast.Node, _seen=None) -> bool:
        # M4 W-M (MC 12670): the SSE-class test for the struct-return
        # door — a float/double ANYWHERE (member, array element, nested
        # struct/union) makes the return SSE/MEMORY class, outside the
        # GP-only subset (§1 row 14; kernel -mno-sse volume 0). A
        # by-value struct cannot legally cycle (C forbids it); the
        # _seen set is belt-and-braces over the tag walk.
        if _seen is None:
            _seen = set()
        if not isinstance(ty, ast.StructType) or ty.tag in _seen:
            return False
        _seen.add(ty.tag)
        for m in self.structs.get(ty.tag) or ():
            mt = self._untype(m.type)
            if (isinstance(mt, ast.BuiltinType)
                    and mt.name in ("float", "double")):
                return True
            if isinstance(mt, ast.ArrayType):
                it = self._untype(mt.inner)
                if (isinstance(it, ast.BuiltinType)
                        and it.name in ("float", "double")):
                    return True
                if isinstance(it, ast.StructType) and \
                        self._struct_has_fp(it, _seen):
                    return True
            if isinstance(mt, ast.StructType) and self._struct_has_fp(mt,
                                                                     _seen):
                return True
        return False

    def _struct_layout(self, ty: ast.StructType,
                       at) -> Tuple[Dict[str, int], int, List]:
        """Returns (flat name->byte-offset WITH promoted anonymous-member
        names, total size, declaration-order slots [(name-or-None, type,
        byte-offset, byte-size, bit-or-None)]).

        Natural C layout (P2-2): each member aligns to its own alignment;
        the struct's align is the widest member's; size rounds to that.
        Anonymous nested members (§1 T+7): the nested aggregate is EMBEDDED
        at the current offset exactly like a named member of that type,
        and its promoted names land at base + inner offset — a nested
        union's names all share the union's base (§2.8).

        M45 §1 row 12 BITFIELDS (gcc 11.4 -std=gnu89 measured law): a
        member with `width` set allocates BITS in bitnumber order inside
        the unit its declared type sizes (x86 little-endian, LSB first):
        the field rides the current aligned unit when it FITS, else moves
        to the next unit; `width 0` (anonymous only) pads to the next
        unit; ANONYMOUS fields consume bits but contribute NO alignment,
        named ones contribute the unit's alignment; a following byte
        member flushes the partial unit. Bitfields land in slots with
        byte-size 0 and a bit descriptor (unit byte-offset, bit-in-unit,
        width, unit type name) as the 5th element — never in the byte
        `offs` map: addressing/offsetof a bitfield stays LOUD (§2.13)."""
        members = self.structs.get(ty.tag)
        # W-S (MC 12716): `()` (defined EMPTY struct) LAYS OUT as size
        # 0/align 1 (gcc -Os measured); only `None` (incomplete) walls.
        if members is None:
            self._err(at or ty, "undefined struct '{}' — only fully defined "
                      "structs are in the subset (§4)".format(ty.tag), ty.tag)
        if not hasattr(self, "_bf_cache"):
            self._bf_cache = {}
        offs: Dict[str, int] = {}
        slots: List = []
        bits: Dict = {}
        packed = self._attr_packed(ty)
        if ty.is_union:
            # §2.8: EVERY member sits at offset 0; size/align = max member
            # (within the §2.13 layout table). M45: a bitfield member's
            # extent is ceil(w/8) at bit 0 (each union member restarts
            # the bit cursor — measured U1 word=9 after a=7,b=9).
            total = 0
            align = 1
            for m in members:
                w = getattr(m, "width", None)
                if w is not None:
                    u = self._bf_unit(m, packed, at or ty)
                    if w == 0:
                        continue
                    if m.name is not None:
                        # W-F: packed bitfields add NO alignment
                        # (measured U4 packed == 4/1; a raise still
                        # joins — U5 aligned(8) packed == 8/8). A
                        # raise NEVER repositions a union member (all
                        # ride bit 0, §2.8).
                        r = self._mem_raise(m, at or ty) or 0
                        mal = r if packed else max(u, r)
                        align = max(align, mal)
                        bits[m.name] = (0, 0, w, m.type.name)
                    slots.append((m.name, m.type, 0, 0, (0, 0, w,
                                                         m.type.name)))
                    total = max(total, (w + 7) // 8)
                    continue
                msz = self._size(m.type, at or ty)
                mal = self._malign(m, packed, at or ty)
                if m.name is None:
                    inner, _isz, _isl = self._struct_layout(m.type,
                                                            at or ty)
                    for n2, o2 in inner.items():
                        offs[n2] = o2
                    for n2, d2 in self._bf_cache.get(m.type.tag,
                                                     {}).items():
                        bits[n2] = (d2[0], d2[1], d2[2], d2[3])
                else:
                    offs[m.name] = 0
                slots.append((m.name, m.type, 0, msz, None))
                total = max(total, msz)
                align = max(align, mal)
            ov = self._tag_aligned(ty, at or ty)
            align = max(align, ov or 0)
            self._bf_cache[ty.tag] = bits
            return offs, (total + align - 1) // align * align, slots
        bit = 0
        align = 1
        for m in members:
            w = getattr(m, "width", None)
            if w is not None:
                u = self._bf_unit(m, packed, at or ty)
                ub = u * 8
                if w == 0:
                    if bit % ub:
                        bit = (bit // ub + 1) * ub
                    continue
                # W-F cursor law (MC 12621, measured X1/X2/X4/Y1): an
                # `aligned(N)` bitfield member POSITIONS at the next
                # N*8-bit boundary — packed AND unpacked, named AND
                # anonymous. Tip mis-laid the unpacked raised shapes in
                # SILENCE (X2 {u32 x:3; y:1 al4; z:3}: gcc 8, tip 4) —
                # found by the W-F law table, fixed here, pinned by legs.
                r = self._mem_raise(m, at or ty) or 0
                if r:
                    rb = r * 8
                    if bit % rb:
                        bit = (bit // rb + 1) * rb
                if packed:
                    # THE W-F LAW (gcc 11.4 measured, probes shapes.c/
                    # fams.c): the packed unit SHRINKS — the cursor runs
                    # BIT-CONTIGUOUS (fields cross bytes; never relocate
                    # to the next declared unit), named fields add no
                    # alignment, and the struct size is ceil(bits/8) at
                    # align 1 unless `aligned` raises it. Descriptor is
                    # (first byte, bit-in-byte, w, declared type);
                    # ACCESS stays LOUD (_bf_access_guard).
                    if m.name is not None:
                        align = max(align, r)
                        bits[m.name] = (bit // 8, bit % 8, w, m.type.name)
                    slots.append((m.name, m.type, bit // 8, 0,
                                  (bit // 8, bit % 8, w, m.type.name)))
                    bit += w
                    continue
                base = (bit // ub) * ub
                if bit + w > base + ub:
                    bit = base + ub
                    # FIX-G1 (gate C1 TRIGGER 1): the moved field RIDES the
                    # next unit — the descriptor must re-base with the
                    # cursor, else extract/RMW aim at the old unit and the
                    # spill store vanishes (gcc law measured: `movb $-56,
                    # 4+ga(%rip)` for {uint a:28; uint b:8}`).
                    base = bit
                d = (base // 8, bit - base, w, m.type.name)
                if m.name is not None:
                    mal = max(u, r)
                    align = max(align, mal)
                    bits[m.name] = d
                slots.append((m.name, m.type, base // 8, 0, d))
                bit += w
                continue
            if isinstance(m.type, ast.ArrayType) and m.type.fam:
                # §1 row 13 (M46): the flexible member spans ZERO bytes at
                # the header end (offset aligned to the ELEMENT's align,
                # which joins the struct's align — measured FD off 8 al 8,
                # FS off 1 sz 1). Nothing follows a FAM (§1 row 13), so
                # the bit cursor stays; the slot carries the "fam" marker
                # so a SUPPLIED initializer LOUDs (data/codegen §5 wall).
                mal = self._malign(m, packed, at or ty)
                align = max(align, mal)
                off = (bit + 7) // 8
                off = (off + mal - 1) // mal * mal
                if m.name is None:          # defensive: FAM is never anon
                    self._err(at or ty, "flexible array member needs a "
                              "name (§1 row 13)", "flexible array")
                offs[m.name] = off
                slots.append((m.name, m.type, off, 0, ("fam",)))
                continue
            msz = self._size(m.type, at or ty)
            mal = self._malign(m, packed, at or ty)
            align = max(align, mal)
            off = (bit + 7) // 8                     # flush partial bits
            off = (off + mal - 1) // mal * mal
            if m.name is None:
                inner = self._struct_layout(m.type, at or ty)[0]
                for n2, o2 in inner.items():
                    offs[n2] = off + o2
                for n2, d2 in self._bf_cache.get(m.type.tag, {}).items():
                    bits[n2] = (d2[0] + off, d2[1], d2[2], d2[3])
            else:
                offs[m.name] = off
            slots.append((m.name, m.type, off, msz, None))
            bit = (off + msz) * 8
        ov = self._tag_aligned(ty, at or ty)
        align = max(align, ov or 0)
        self._bf_cache[ty.tag] = bits
        nbytes = (bit + 7) // 8
        return offs, (nbytes + align - 1) // align * align, slots

    def _bf_unit(self, m, packed, at) -> int:
        """§1 row 12 (M45): the bitfield allocation unit = the SIZE of the
        declared type. M4 W-F COMMIT-1 (MC 12621) REPLACES the packed
        DEFER with the gcc-11.4-measured law: under `packed` the unit
        STILL sizes declared-type-wise (a width-0 member pads to the
        next DECLARED-unit boundary — measured {u16 x:3;:0;u16 y:3}
        packed == 3, {u32 x:3;:0;u32 y:3} == 5) but the FIELDS neither
        relocate to it nor align to it: the cursor runs bit-contiguous
        (S4 {u16 x:12,y:12} == 3, S6 {u8 a;u16 x:9,y:7} == 3, E3 == 2,
        E13 == 5, E4 {u64 x:20} == 3, A4 {__int128 x:4} == 1) and named
        bitfields contribute NO alignment (align stays 1 unless an
        `aligned(N)` member/tag raises — X3/X4/A1/E6/E7). Witnesses:
        .tmp/m4-wf/probes/shapes.c + fams.c (gcc 11.4 -std=gnu89).
        ACCESS codegen stays LOUD (expr_codegen._bf_access_guard)."""
        name = m.type.name if isinstance(m.type, ast.BuiltinType) else None
        if name is None or name not in TYPE_SIZE or name == "void" \
                or name in ("float", "double"):
            self._err(at, "bitfield unit is not a scalar integer type "
                      "(§1 row 12)", "bitfield")
        return TYPE_SIZE[name]

    def _bf_cache_get(self, tag):
        return getattr(self, "_bf_cache", {}).get(tag, {})

    def _bitfield(self, n: ast.Select):
        """Bit descriptor (unit byte-offset, bit-in-unit, width, unit type
        name) for a bitfield member SELECT, else None."""
        base = self._struct_of(n)
        if base.tag not in getattr(self, "_bf_cache", {}):
            self._struct_layout(base, n)
        return self._bf_cache.get(base.tag, {}).get(n.field)

    # M4 W-G COMMIT-0 (MC 12633, W-F gate finding P2-F1/T6): the ACCESS
    # guard's question is which struct DECLARED the resolved bitfield —
    # the descriptor's OWNER — not what the access base is typed as. A
    # descriptor hoisted from an ANON nested packed struct into an
    # UNPACKED outer keeps the packed law's shrunk-unit (byte,
    # bit-in-byte, w) form, and the unit-window codegen then SILENTLY
    # mis-reads a straddling field (measured at 9c84499: probes
    # t6gap2.c gcc exit 0, blcc rc 0 exit 1 — the lost top bit of
    # {p:4; x:29;} read through the outer). One walk, the same ANON
    # promotion path walk_fields yields; the declaring struct answers
    # with its own `packed` attribute (packed never leaks INTO an
    # unpacked nested member, so first-match order is the law).
    def _bf_owner_packed(self, n: ast.Select) -> bool:
        def walk(ty) -> bool:
            for m in self.structs.get(ty.tag) or ():
                if m.name == n.field:
                    if getattr(m, "width", None) is not None:
                        return self._attr_packed(ty)
                elif m.name is None and \
                        getattr(m, "width", None) is None and \
                        isinstance(m.type, ast.StructType):
                    if walk(m.type):
                        return True
            return False
        return walk(self._struct_of(n))


    # -- type-of-expression (only what addressing widths need) --------------------

    def _int(self, n) -> ast.BuiltinType:
        return ast.BuiltinType(n.file, n.line, n.col, "int")

    def _bt(self, n, name: str) -> ast.BuiltinType:
        return ast.BuiltinType(n.file, n.line, n.col, name)

    def _promote(self, ty: ast.Node) -> ast.Node:
        """Integer promotion (§2.2): the narrow types → int (unsigned short
        fits in int on LP64). M4 W2 COMMIT-0 (MC 12545): `_Bool` too —
        measured sizeof(b+1)==4; C11 6.3.1.1 gives it the LOWEST integer
        conversion rank, so the promotion to int is the only context a
        rank could show in, and the RUN-PAIRS pin the widths."""
        if isinstance(ty, ast.BuiltinType) and ty.name in (
                "char", "signed char", "unsigned char", "short",
                "unsigned short", "_Bool"):
            return ast.BuiltinType(ty.file, ty.line, ty.col, "int")
        return ty

    def _uac(self, lt: ast.Node, rt: ast.Node, n) -> ast.BuiltinType:
        """Usual arithmetic conversions (§2.2, gcc 11.4 measured): after
        promotion — same sign: wider rank wins; unsigned rank >= signed
        rank: unsigned of the max rank; else the signed type (on LP64 a
        strictly-higher signed rank represents every value of the lower
        unsigned rank: long ⊇ uint, long long ⊇ ulong)."""
        lt, rt = self._promote(lt), self._promote(rt)
        ln = lt.name if isinstance(lt, ast.BuiltinType) else None
        rn = rt.name if isinstance(rt, ast.BuiltinType) else None
        if ln is None or rn is None:
            self._err(n, "arithmetic on a non-numeric type is not in the "
                      "subset (§4)", self._what(n))
        if ln in ("float", "double") or rn in ("float", "double"):
            self._err(n, "'float' arithmetic is DEFERRED — storage only "
                      "(§1 row 14)", self._what(n))
        if ln == rn:
            return self._bt(n, ln)
        lu, ru = ln in UNSIGNED_NAMES, rn in UNSIGNED_NAMES
        lr, rr = _RANK[ln], _RANK[rn]
        if lu == ru:
            return self._bt(n, ln if lr >= rr else rn)
        un, ur = (ln, lr) if lu else (rn, rr)
        sn, sr = (rn, rr) if lu else (ln, lr)
        return self._bt(n, un if ur >= sr else sn)

    def _lvalue_convert(self, ty):
        """§2.6d arm of the selection rule: the control loses top-level
        qualifiers (lvalue conversion) and an ARRAY control is ADJUSTED to
        pointer-to-element (`int[4]:` key never matches, measured)."""
        ty = self._untype(ty)
        _, ty = self._split_q(ty)
        if isinstance(ty, ast.ArrayType):
            return ast.PtrType(ty.file, ty.line, ty.col, ty.inner)
        return ty

    def generic_select(self, n):
        """§2.6d MEASURED selection (gcc 11.4): dup-assoc check FIRST
        (fires regardless of the control — "'_Generic' specifies two
        compatible types"); control undergoes lvalue conversion (top quals
        dropped, array→pointer adjusted); selection is STRICT type
        identity — a key carrying a top-level qualifier matches NOTHING
        (the converted control is never qualified). Returns the chosen
        (key, arm) pair — codegen emits ONLY that arm (untaken arms'
        side effects never run); no match → `default:`; neither → LOUD."""
        for i in range(len(n.assocs)):
            for j in range(i + 1, len(n.assocs)):
                if self._ty_eq_strict(n.assocs[i][0], n.assocs[j][0]):
                    self._err(n, "'_Generic' specifies two compatible "
                              "types (§2.6d)", "_Generic")
        cty = self._lvalue_convert(self._ty(n.control))
        for pair in n.assocs:
            if self._ty_eq_strict(cty, pair[0]):
                return pair
        if n.default is not None:
            return (None, n.default)
        self._err(n, "_Generic controlling expression type not compatible "
                  "with any association (§2.6d)", "_Generic")

    def _ty(self, n: ast.Node) -> ast.Node:
        if isinstance(n, ast.Overflow):
            # §1 row 16 (M53): the trio answers int 0/1 (gcc measured).
            return self._bt(n, "int")
        if isinstance(n, ast.CompoundLit):
            return self._untype(n.ty)          # §1 row 11
        if isinstance(n, ast.IntLit):
            # §2.1 (M2): the literal's TYPE is the lexer's typed suffix/range
            # answer (hex may take unsigned early; decimal signed-first).
            return self._bt(n, n.itype)
        if isinstance(n, ast.CharLit):
            return self._int(n)
        if isinstance(n, ast.FloatLit):
            return self._bt(n, "float" if n.fsize == 4 else "double")
        if isinstance(n, ast.StrLit):
            return ast.PtrType(n.file, n.line, n.col,
                               ast.BuiltinType(n.file, n.line, n.col, "char"))
        if isinstance(n, ast.LabelAddr):
            # §2.6: `&&label` is void* (code address; _THIS_IP_ casts it to
            # unsigned long through the ordinary ptr->int path).
            return ast.PtrType(n.file, n.line, n.col,
                               ast.BuiltinType(n.file, n.line, n.col, "void"))
        if isinstance(n, ast.StmtExpr):
            # §2.4(c): the type of `({…; e;})` is the type of the final
            # expression; `({;})` is void (GCC ext).
            return self._ty_stmtexpr(n)
        if isinstance(n, ast.Sizeof):
            return ast.BuiltinType(n.file, n.line, n.col, "long")
        if isinstance(n, ast.Alignof):
            # M4 W2.5: alignof answers the SAME type as sizeof here
            # (the shipped unsigned-law convention; fx: sizeof of either
            # is 8).
            return ast.BuiltinType(n.file, n.line, n.col, "long")
        if isinstance(n, ast.Ident):
            return self._untype(self._ident_ty(n))
        if isinstance(n, ast.Cast):
            return self._untype(n.type)
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
                # M4 W2 VALUES (MC 12545): the W1 twin gate DIED — `!fp`
                # is the NULL/0-test spelling and rides the generic
                # truthiness law (the operand now TYPES to PtrType).
                return self._int(n)
            return self._ty(n.operand)
        if isinstance(n, ast.Binary):
            return self._binary_ty(n)
        if isinstance(n, ast.Cond):
            # §1c AMENDMENT v4.2 (MC 12486): the result type of the
            # runtime conditional — measured gcc 11.4 gnu89 in
            # _cond_ty below.
            return self._cond_ty(n)
        if isinstance(n, ast.Comma):
            # §1c: the comma operator's value is its RIGHT operand.
            return self._ty(n.right)
        if isinstance(n, ast.Call):
            if not isinstance(n.callee, ast.Ident):
                # M4 W3 (MC 12563) §2: the target is a VALUE — the call
                # types as the TARGET's return (`(*fp)(x)`, `o->f(x)`).
                return self._ind_call_ty(n)
            name = n.callee.name
            if (name not in self.sigs and name not in BUILTINS
                    and name not in predef.MEM_FOLDS
                    and name not in predef.MEM_PLAIN
                    and name not in predef.VA_FOLDS
                    and name not in predef.INTRINSIC_FOLDS
                    and not name.startswith("__builtin")):
                # M4 W3: a fn-ptr VARIABLE answers the name — the §2 R1
                # law (the parse gate already LOUDed non-callables).
                return self._ind_call_ty(n)
            if name in BUILTINS and name not in self.sigs:
                # M4 W3 COMMIT-0 (MC 12563) WINNER law: the §6 table
                # answers the UNDECLARED spelling only; a re-declared
                # builtin types from the user prototype below (measured:
                # `int strlen(const char*)` re-decl → the call is an int).
                kind = BUILTINS[name][1]
                return ast.BuiltinType(n.file, n.line, n.col,
                                       "long" if kind == "void" else kind)
            if name == "__builtin_types_compatible_p":
                return ast.BuiltinType(n.file, n.line, n.col, "int")
            if name == "__builtin_va_arg":
                return self._untype(n.args[1])     # §2.7: TYPE argument
            if name in ("__builtin_va_start", "__builtin_va_end",
                        "__builtin_va_copy"):
                return ast.BuiltinType(n.file, n.line, n.col, "void")
            if name in predef.MEM_FOLDS and name not in self.sigs:
                # §2.17: undeclared __builtin mem* still TYPES (fold-side
                # of the builtin posture): void*->void* classes return
                # char*, memcmp returns int. A user declaration wins.
                if name == "__builtin_memcmp":
                    return ast.BuiltinType(n.file, n.line, n.col, "int")
                return ast.PtrType(n.file, n.line, n.col,
                                   ast.BuiltinType(n.file, n.line, n.col,
                                                   "char"))
            if name in predef.INTRINSIC_FOLDS:
                # §1 row 19 TYPE arm (mirror of the codegen folds):
                # bswap16/32 and every ctz/clz spelling return int;
                # bswap64 returns unsigned long; the level-0 frame/return
                # address builtins return void* (gcc's type).
                if name == "__builtin_bswap64":
                    return ast.BuiltinType(n.file, n.line, n.col,
                                           "unsigned long")
                if name in ("__builtin_return_address",
                            "__builtin_frame_address"):
                    return ast.PtrType(n.file, n.line, n.col,
                                       ast.BuiltinType(n.file, n.line,
                                                       n.col, "void"))
                return ast.BuiltinType(n.file, n.line, n.col, "int")
            return self.sigs[name][1]
        if isinstance(n, ast.Generic):            # §2.6d: the type of the SELECTED association's expression.
            return self._ty(self.generic_select(n)[1])
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
        self._err(n, "cannot type this expression", self._what(n))

    def _ind_call_ty(self, n: ast.Call) -> ast.Node:
        """M4 W3 (MC 12563) §2 R1: type a call through a VALUE — the
        callee expression decays to PtrType(FuncType) (or the FuncType
        designator `(*fp)`, which the decay rebuilds); the call's type is
        the TARGET's return. A non-callable target answers the §8 twin
        (the parse gate is the first line; this is the engine's)."""
        tgt = self._decay(self._ty(n.callee))
        if isinstance(tgt, ast.PtrType) and \
                isinstance(tgt.inner, ast.FuncType):
            return tgt.inner.ret
        self._err(n, "called object is not a 'function' or a 'function "
                  "pointer' (§8 — gcc rc1 twin)", "call")

    def _cond_ty(self, n: ast.Cond) -> ast.Node:
        """§1c AMENDMENT v4.2 (MC 12486) — the conditional's result type,
        every row measured against gcc 11.4 -std=gnu89 THIS card
        (sizeof(__typeof__(ternary)) + assignability + run witnesses):
        * both arms the same type -> that type (scalars, pointers,
          structs — sizeof(c?s1:s2)==4 folds; the §5 struct-VALUE wall
          stops only the RUNTIME arm in codegen);
        * void arms: BOTH void -> void (statement shape, gcc rc0); a void
          arm mixed with a value arm -> LOUD BOTH sides (gcc: "'void'
          value not ignored as it ought to be", rc1);
        * pointer arms: void* + T* -> void* (C11 6.5.15p6); T* + a NULL
          POINTER CONSTANT (folded 0) -> T*; two pointers -> the FIRST
          arm's type (gcc WARNS on incompatibility, rc0, and the
          assignability probe measured int*/long* answering int*);
        * pointer + a NON-null integer: gnu89 warning-only (rc0,
          sizeof==8) -> the POINTER arm's type;
        * numeric arms: the USUAL ARITHMETIC CONVERSIONS, the exact law
          the binary family uses (_uac — measured i/u/l/ll matrix incl.
          promotion of char/short); float arms same kind type (4/8),
          mixed kinds LOUD through _uac's row-14 posture.
        * GNU `a ?: b` (arm1 None): the operands are TEST and arm2."""
        lt = self._decay(self._ty(n.test if n.gnu else n.arm1))
        rt = self._decay(self._ty(n.arm2))
        lv = isinstance(lt, ast.BuiltinType) and lt.name == "void"
        rv = isinstance(rt, ast.BuiltinType) and rt.name == "void"
        if lv or rv:
            if not (lv and rv):
                self._err(n, "'?:' with one void operand is 'void value "
                          "not ignored' (§1c measured: gcc rc1)", "?:")
            return self._bt(n, "void")
        ls = isinstance(lt, ast.StructType)
        rs = isinstance(rt, ast.StructType)
        if ls or rs:
            if not (ls and rs) or lt.tag != rt.tag:
                self._err(n, "'?:' arms of incompatible 'struct' types are "
                          "not in the subset (§4)", "?:")
            return lt
        lp = isinstance(lt, ast.PtrType)
        rp = isinstance(rt, ast.PtrType)
        if lp and rp:
            if isinstance(lt.inner, ast.BuiltinType) and \
                    lt.inner.name == "void":
                return lt
            if isinstance(rt.inner, ast.BuiltinType) and \
                    rt.inner.name == "void":
                return rt                          # C11 6.5.15p6: void* wins
            return lt                              # gcc posture on mismatch
        if lp or rp:
            # pointer vs scalar: NPC (folded 0) takes the other arm's
            # pointer type (constraint-clean); any other integer is the
            # gnu89 warning class — the pointer type still answers
            # (sizeof(__typeof__(pi?pi:1))==8, pi?1:pi measured likewise).
            return lt if lp else rt
        return self._uac(lt, rt, n)

    def _binary_ty(self, n: ast.Binary) -> ast.Node:
        if n.op in ("==", "!=", "<", "<=", ">", ">=", "&&", "||"):
            # M4 W2 VALUES (MC 12545, plan §2 R10): the fn-ptr compare
            # gate DIED — NULL/0/fn comparisons ride the SHIPPED
            # relational law unchanged (int answers, generic 64-bit
            # compares); no fn-ptr-specific arm survives here.
            return self._int(n)
        lt = self._decay(self._ty(n.left))
        rt = self._decay(self._ty(n.right))
        lp = isinstance(lt, ast.PtrType)
        rp = isinstance(rt, ast.PtrType)
        if n.op in ("+", "-") and (lp or rp):
            if n.op == "-" and lp and rp:
                return self._bt(n, "long")
            if n.op == "+" and lp and rp:
                # M2 fix-g2 (MC 12460): binary p + p was SILENT (scaled add
                # of the two address values). gcc: invalid operands — LOUD.
                self._err(n, "pointer + pointer is not in the subset (§4)",
                          n.op)
            return lt if lp else rt
        if n.op not in ("+", "-") and (lp or rp):
            self._err(n, "'{}' with a pointer operand is not in the subset (§4)"
                      .format(n.op), n.op)
        if n.op in ("<<", ">>"):
            # C: a shift's result type is its promoted LEFT operand alone.
            return self._promote(lt)
        return self._uac(lt, rt, n)

    def _ident_ty(self, n: ast.Ident) -> ast.Node:
        loc = self.fn.locals.get(n.name)
        if loc is not None:
            return loc[1]
        # §1c (MC 12486): a function-scope `static` local SHADOWS the
        # same-name global for the whole function (gcc law, w4 measured).
        st = getattr(self.fn, "statics", None)
        if st is not None and n.name in st:
            return st[n.name][1]
        if n.name in self.enums:
            return self._int(n)
        gd = self.globals.get(n.name)
        if gd is not None:
            return gd.type
        if n.name in self.sigs:
            # M4 W2 VALUES (MC 12545, plan §2 R1): a function name used
            # as a VALUE decays to a pointer to its function type — the
            # SAME _decay W1's type law ships; the sigs table (params,
            # ret, variadic) rebuilds the FuncType. This is the ONE arm:
            # _ty and _ex_ident share it so any context (assign, compare,
            # cast, arg, return) types identically.
            params, ret, variadic = self.sigs[n.name]
            ft = ast.FuncType(n.file, n.line, n.col, self._untype(ret),
                              tuple(params), variadic)
            return ast.PtrType(n.file, n.line, n.col, ft)
        # M3 §3.10: a register-asm bind TYPES as its declared T (the value
        # is C-visible; only its HOME differs — the register or a hidden
        # shadow slot). Resolution lands HERE so _ty and _ex_ident agree.
        ra = getattr(self.fn, "regasms", None)
        if ra is not None and n.name in ra:
            return ra[n.name][3]
        rg = getattr(self, "regasm_global", None)
        if rg is not None and n.name in rg:
            return rg[n.name][1]
        self._err(n, "'{}' undeclared — not a local, parameter, global or "
                     "enum constant".format(n.name), n.name)

    def _member_ty(self, n: ast.Select) -> ast.Node:
        base = self._struct_of(n)
        offsets = self._struct_layout(base, n)[0]
        if n.field not in offsets and n.field not in self._bf_cache_get(
                base.tag):
            self._err(n, "no member '{}' in struct '{}'".format(n.field, base.tag),
                      n.field)
        for name, mtype in walk_fields(self.structs[base.tag], self.structs):
            if name == n.field:
                return self._untype(mtype)   # §2.12 marker never leaks
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
        offsets = self._struct_layout(base, n)[0]
        if n.field not in offsets:
            if n.field in self._bf_cache_get(base.tag):
                # §1 row 12 (M45): a bitfield has NO address — gcc ERROR
                # "cannot take address of bit-field"; §2.13's offsetof
                # mirror above is the fold sibling of this wall.
                self._err(n, "address of 'bit-field' member '{}' is not in "
                          "the subset (§1 row 12 — a gcc ERROR)".format(
                              n.field), n.field)
            self._err(n, "no member '{}' in struct '{}'".format(n.field, base.tag),
                      n.field)
        return offsets[n.field]
