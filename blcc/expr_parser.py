# LINES reason: the expression grammar is ONE precedence-climbing surface —
# splitting the operator levels across files would scatter the §4 subset law
# (incl. the §1c conditional entry) away from the table that defines it.
"""Expression parser for blcc (ARCHITECTURE.md §3).

Precedence climbing + casts + unary, producing ast expression nodes. The
parent Parser injects the hooks this grammar half needs (typedef test, type
parsing, callable lookup, light type-of-expression) so this module never
imports parser.py. §5 constructs met in expressions raise loud diagnostics.
"""
from __future__ import annotations

from typing import Callable, Optional

from blcc import ast
from blcc.lexer import DiagError
from blcc.types import what

BINARY_PREC = {
    "||": 1, "&&": 2,
    "|": 3, "^": 4, "&": 5,
    "==": 6, "!=": 6,
    "<": 7, "<=": 7, ">": 7, ">=": 7,
    "<<": 8, ">>": 8,
    "+": 9, "-": 9,
    "*": 10, "/": 10, "%": 10,
}
COMPOUND_ASSIGN_OPS = frozenset(
    {"+=", "-=", "*=", "/=", "%=", "&=", "|=", "^=", "<<=", ">>="})
_UNARY_PUNCT = frozenset({"-", "+", "!", "~", "&", "*"})
_CAST_KW = frozenset(
    {"char", "short", "int", "long", "void", "const", "struct", "union",
     "enum",
     "float", "double", "unsigned", "signed", "__signed__", "__signed",
     "volatile", "__volatile__", "restrict", "__restrict", "__restrict__",
     # M4 W-B (MC 12596): the 128-bit integer word in type position
     "__int128",
     # §1 row 6c: __typeof__ is legal in cast/sizeof type position
     "typeof", "__typeof__", "__typeof",
     # M4 W2 COMMIT-0 (MC 12545): C99 `_Bool` is a type keyword everywhere
     # (measured: `sizeof(_Bool)`, `(unsigned char)(x)` twins both rc 0).
     "_Bool"})
_LVALUE_KINDS = (ast.Ident, ast.Index, ast.Select)


class ExprParser:
    """Operates on a TokenStream shared with the owning Parser."""

    def __init__(self, stream, is_typename: Callable[[str], bool],
                 parse_type: Callable[[], ast.Node],
                 callable_known: Callable[[str], bool],
                 expr_type: Callable[[ast.Node], Optional[ast.Node]],
                 parse_stmts: Optional[Callable] = None,
                 fold_truthy: Optional[Callable] = None,
                 fold_offset: Optional[Callable] = None,
                 parse_init: Optional[Callable] = None,
                 norm_init: Optional[Callable] = None,
                 objsize: Optional[Callable] = None):
        self.s = stream
        self.is_typename = is_typename
        self.parse_type = parse_type
        self.callable_known = callable_known
        self.expr_type = expr_type
        self.parse_stmt_expr = parse_stmts        # §2.4 stmt-expression
        self.fold_truthy = fold_truthy            # §2.6 choose_expr control
        self.fold_offset = fold_offset            # §2.13 offsetof layout
        self.parse_init = parse_init              # §1 row 11 brace init
        self.norm_init = norm_init                # §1 row 10 normalization
        self.objsize = objsize                    # §1 row 19 object_size
        self._lenient_calls = False               # inside GNU fold args

    def _callable_view(self, ty):
        """M4 W3 (MC 12563) commit-2: the callable view OF A TYPE —
        qualifiers drop at every level the CALL reaches (`const struct
        op tbl[]`'s ARRAY, the const member view); FuncType rides,
        PtrType(FuncType) rides. None = not a call target."""
        while isinstance(ty, ast.Qualified):
            ty = ty.inner
        if isinstance(ty, ast.FuncType):
            return ty
        if isinstance(ty, ast.PtrType):
            inner = ty.inner
            while isinstance(inner, ast.Qualified):
                inner = inner.inner
            if isinstance(inner, ast.FuncType):
                return inner
        return None

    def _callable_ty(self, node):
        """M4 W3 (MC 12563) §2 R1: the call-TARGET view of a callee
        expression — its type DECAYED to a callable: PtrType(FuncType)
        (the fn-ptr value) or FuncType (the designator `(*fp)` — C folds
        the deref back through the decay). Qualifiers drop. None = NOT a
        call target; the §8 gcc-rc1-twin sentence answers. Light mirror
        of types._decay — parse-side only (the full engine types the same
        node again for the call's RETURN type)."""
        if isinstance(node, ast.Cast):
            # S14/S18 (W3 commit-2): `((fp_t)expr)(x)` — the CAST type IS
            # the target type; the operand only supplies the value.
            return self._callable_view(node.type)
        if isinstance(node, ast.Cond):
            # S22: `(c ? f1 : f2)(x)` — arms are FUNCTION VALUES; either
            # arm's callable view answers (the shipped fn-value/ternary
            # law types the SAME node for the engine; the gnu `c ?: b`
            # form has arm1 None and rides arm2).
            if node.arm1 is None:
                return self._callable_ty(node.arm2)
            return (self._callable_ty(node.arm1)
                    or self._callable_ty(node.arm2))
        if isinstance(node, ast.Ident) and self.callable_known(node.name):
            return "designator"        # the fn name itself (the ternary
                                       # arms above; truthiness only —
                                       # the engine retypes it via sigs)
        return self._callable_view(self.expr_type(node))

    # -- entry: assignment level (right-associative) ------------------------

    def parse_expression(self) -> ast.Node:
        left = self.parse_binary(0)
        t = self.s.peek()
        if t.kind == "punct":
            if t.text == "?":
                # §1c AMENDMENT v4.2 (MC 12486): assignment binds LOOSER
                # than `?:` — the conditional is the entry level's operator,
                # and its THIRD operand is a conditional-expression (no
                # assignment: `a ? b : c = d` is a syntax error, gcc rc1).
                return self._parse_cond_after_test(left, t)
            if t.text == "=" or t.text in COMPOUND_ASSIGN_OPS:
                self.s.next()
                value = self.parse_expression()
                self._check_lvalue(left, t, "assignment")
                if t.text != "=" and self._struct_type(left) is not None:
                    # M4 W-H COMMIT-2 (MC 12645): the plain `=` moved to
                    # the MEASURED block-copy law, decided by FULL types
                    # in _ex_assign (the light mirror cannot tell same-tag
                    # from mismatch — the false ACCEPT side of that
                    # bluntness was `int n = w` running garbage at tip).
                    # The COMPOUND ops keep the shipped §5 sentence:
                    # `s += t` is gcc rc1 (invalid types for binary +=),
                    # a wall this wave does not touch.
                    raise DiagError(
                        "sema", t.file, t.line, t.col,
                        "'struct assignment' is not in the subset (§5) — "
                        "assign member by member", t.text)
                if t.text == "=":
                    return ast.Assign(left.file, left.line, left.col,
                                      left, value)
                return ast.AssignOp(left.file, left.line, left.col,
                                    t.text, left, value)
        return left

    def _parse_cond_after_test(self, test: ast.Node, t) -> ast.Node:
        """`? [middle] : third` — test already parsed (binary level)."""
        self.s.next()                                    # consume '?'
        if self.s.at_punct(":"):
            # GNU `a ?: b` — MEASURED gcc 11.4 gnu89 SUPPORT (the kernel
            # uses it): a evaluated ONCE, its value when true.
            self.s.next()
            return ast.Cond(t.file, t.line, t.col, test, None,
                            self._parse_cond_tail(), gnu=True)
        middle = self.parse_comma_expression()           # full expr, commas
        self.s.expect_punct(":")
        return ast.Cond(t.file, t.line, t.col, test, middle,
                        self._parse_cond_tail())

    def _parse_cond_tail(self) -> ast.Node:
        """A conditional-expression: binary + nested `?:` (right-assoc
        chains ride the recursion) — WITHOUT the assignment level."""
        left = self.parse_binary(0)
        t = self.s.peek()
        if t.kind == "punct" and t.text == "?":
            return self._parse_cond_after_test(left, t)
        return left

    def parse_comma_expression(self) -> ast.Node:
        """C grammar's `expression`: assignment-expressions joined by the
        comma operator. M4 W-G COMMIT-1 (MC 12633) PROMOTES it from the
        one §1c site (conditional's MIDDLE operand, MC 12486) to EVERY
        slot the C grammar names `expression` — parenthesized primary,
        sizeof/alignof expr forms, subscript, statement, control
        conditions, for clauses, return. The cast as LEFT operand
        (spinlock.h:117 `(((void)(lock), 0))`, 492 streams) is the
        corpus carrier; the law table is .tmp/m4-wg/measure + the
        test-file docstring (value = RIGHT, LEFT sequenced first)."""
        left = self.parse_expression()
        while self.s.accept_punct(","):
            right = self.parse_expression()
            left = ast.Comma(left.file, left.line, left.col, left, right)
        return left

    # -- binary: precedence climbing, left-associative -----------------------

    def parse_binary(self, min_prec: int) -> ast.Node:
        left = self.parse_unary()
        while True:
            t = self.s.peek()
            if t.kind != "punct" or t.text not in BINARY_PREC:
                return left
            prec = BINARY_PREC[t.text]
            if prec < min_prec:
                return left
            self.s.next()
            right = self.parse_binary(prec + 1)
            if t.text in ("==", "!="):
                if self._struct_type(left) or self._struct_type(right):
                    raise DiagError(
                        "sema", t.file, t.line, t.col,
                        "'struct comparison' is not in the subset (§5)",
                        t.text)
            left = ast.Binary(t.file, t.line, t.col, t.text, left, right)

    # -- unary, casts, sizeof, inc/dec ----------------------------------------

    def parse_unary(self) -> ast.Node:
        t = self.s.peek()
        if t.kind == "punct" and t.text in _UNARY_PUNCT:
            self.s.next()
            return ast.Unary(t.file, t.line, t.col, t.text,
                             self.parse_unary())
        if t.kind == "punct" and t.text in ("++", "--"):
            self.s.next()
            operand = self.parse_unary()
            self._check_lvalue(operand, t, "'{}'".format(t.text))
            return ast.IncDec(t.file, t.line, t.col, t.text, operand, True)
        if t.kind == "kw" and t.text == "sizeof":
            return self.parse_sizeof()
        if t.kind == "kw" and t.text in self._ALIGNOF_WORDS:
            return self.parse_alignof()
        if t.kind == "punct" and t.text == "(" and self._starts_type(1):
            self.s.next()
            typ = self.parse_type()
            self.s.expect_punct(")")
            if self.s.at_punct("{") and self.parse_init is not None:
                # §1 row 11: cast-vs-literal — `(TYPE)` + brace group is a
                # COMPOUND LITERAL (gnu89 extension), not a cast.
                init = self.parse_init()
                if self.norm_init is not None:
                    init = self.norm_init(typ, init, t)
                return self._postfix_from(
                    ast.CompoundLit(t.file, t.line, t.col, typ, init))
            operand = self.parse_unary()
            return ast.Cast(t.file, t.line, t.col, typ, operand)
        return self.parse_postfix()

    def parse_sizeof(self) -> ast.Node:
        t = self.s.next()  # 'sizeof'
        if self.s.accept_punct("("):
            if self._starts_type(0):
                typ = self.parse_type()
                self.s.expect_punct(")")
                if self.s.at_punct("{") and self.parse_init is not None:
                    # sizeof `(int){7}` = sizeof (int): the literal rides
                    # the TYPE's size (§1 row 11) — consume the group.
                    self.parse_init()
                return ast.Sizeof(t.file, t.line, t.col, typ, None)
            expr = self.parse_comma_expression()
            # W-G (MC 12633): `sizeof (a, b)` = sizeof of the PARENTHESIZED
            # PRIMARY (m18: gcc rc0, size of the RIGHT operand's type).
            self.s.expect_punct(")")
            return ast.Sizeof(t.file, t.line, t.col, None, expr)
        if self._starts_type(0):
            typ = self.parse_type()
            return ast.Sizeof(t.file, t.line, t.col, typ, None)
        # 'sizeof x' (no parens): only a bare operand; anything past it is a
        # loud parse error, never silently mis-sized.
        return ast.Sizeof(t.file, t.line, t.col, None, self.parse_primary())

    # M4 W2.5 (MC 12557, AMENDMENT-3): the ONE alignof family, measured
    # gcc 11.4 gnu89 law (fx/a1-a3): the PARENTHESIZED form takes a TYPE
    # or an EXPR; the BARE form takes an EXPR ONLY (`__alignof__ long` is
    # gcc rc1); `alignof` (no underscores) is NOT an operator (identifier).
    _ALIGNOF_WORDS = ("__alignof__", "__alignof", "_Alignof")

    def parse_alignof(self) -> ast.Node:
        t = self.s.next()  # the operator word
        if self.s.accept_punct("("):
            if self._starts_type(0):
                typ = self.parse_type()
                self.s.expect_punct(")")
                if self.s.at_punct("{") and self.parse_init is not None:
                    # `__alignof__(int){7}` = alignof (int) — the literal
                    # rides the TYPE (§1 row 11, the sizeof law mirrored).
                    self.parse_init()
                return ast.Alignof(t.file, t.line, t.col, typ, None)
            expr = self.parse_comma_expression()
            self.s.expect_punct(")")
            return ast.Alignof(t.file, t.line, t.col, None, expr)
        # Bare form: EXPR ONLY. A type word answers the parse wall
        # (parse_primary), matching gcc's rc1 "expected expression".
        return ast.Alignof(t.file, t.line, t.col, None, self.parse_primary())

    # -- postfix chain: call, subscript, member, ++/-- -------------------------

    def parse_postfix(self) -> ast.Node:
        return self._postfix_from(self.parse_primary())

    def _postfix_from(self, node) -> ast.Node:
        while True:
            t = self.s.peek()
            if t.kind != "punct":
                return node
            if t.text == "(":
                if isinstance(node, ast.Ident) and node.name == (
                        "__builtin_va_arg"):
                    # §2.7: `va_arg(ap, TYPE)` — second argument is a
                    # TYPE NAME (like §2.12's), first a normal expression.
                    self.s.expect_punct("(")
                    a0 = self.parse_expression()
                    self.s.expect_punct(",")
                    d = self.s.peek()
                    if not ((d.kind == "kw") or
                            (d.kind == "id" and self.is_typename(d.text))):
                        raise DiagError(
                            "sema", t.file, t.line, t.col,
                            "'__builtin_va_arg' takes (expression, TYPE) "
                            "(§2.7)", d.text)
                    a1 = self.parse_type()
                    self.s.expect_punct(")")
                    node = ast.Call(t.file, t.line, t.col, node, [a0, a1])
                    continue
                if isinstance(node, ast.Ident) and node.name == (
                        "__builtin_types_compatible_p"):
                    # §2.12: the call's arguments are TYPE NAMES — not
                    # parseable as expressions; intercepted like the GNU
                    # folds, folded at codegen (needs TypeMap).
                    args = self._parse_type_args(t)
                    node = ast.Call(t.file, t.line, t.col, node, args)
                    continue
                if isinstance(node, ast.Ident) and node.name == (
                        "__builtin_constant_p"):
                    # §2.11 ARG-CLASS TABLE (no-lie rule): 1 ONLY for the
                    # constant closure (fold_truthy answers) plus string
                    # literals; EVERYTHING else answers 0 — the safe
                    # direction that selects the runtime arm.
                    args = self._parse_call_args(t)
                    if len(args) != 1:
                        raise DiagError(
                            "sema", t.file, t.line, t.col,
                            "'__builtin_constant_p' takes exactly 1 "
                            "argument (§2.11)", "__builtin_constant_p")
                    known = isinstance(args[0], ast.StrLit) or (
                        self.fold_truthy is not None
                        and self.fold_truthy(args[0]) is not None)
                    node = ast.IntLit(t.file, t.line, t.col, 1 if known
                                      else 0, "int")
                    continue
                if isinstance(node, ast.Ident) and node.name == (
                        "__builtin_offsetof"):
                    node = self._fold_offsetof(t)
                    continue
                if isinstance(node, ast.Ident) and node.name == (
                        "__builtin_extract_return_addr"):
                    # §1 row 19 IDENTITY FOLD: on x86-64 the canonical
                    # address IS the address (gcc 11.4 measured: the whole
                    # builtin lowers to movq %rdi,%rax). The argument rides
                    # on untouched; no call, no codegen arm.
                    args = self._parse_call_args(t)
                    if len(args) != 1:
                        raise DiagError(
                            "sema", t.file, t.line, t.col,
                            "'__builtin_extract_return_addr' takes exactly "
                            "1 argument (§1 row 19)", node.name)
                    node = args[0]
                    continue
                if isinstance(node, ast.Ident) and node.name == (
                        "__builtin_object_size"):
                    # §1 row 19: the compile-time object-size query folds
                    # to an INTEGER constant (SIZE_MAX when unidentified)
                    # — gcc emits no runtime code for it at all.
                    args = self._parse_call_args(t)
                    if len(args) != 2:
                        raise DiagError(
                            "sema", t.file, t.line, t.col,
                            "'__builtin_object_size' takes 2 arguments "
                            "(§1 row 19)", node.name)
                    if (self.fold_truthy is None
                            or self.fold_truthy(args[1]) not in (0, 1, 2, 3)):
                        raise DiagError(
                            "sema", args[1].file, args[1].line, args[1].col,
                            "'__builtin_object_size' needs a constant "
                            "0..3 type argument (§1 row 19)", node.name)
                    v = self.objsize(args[0]) if self.objsize else -1
                    node = ast.IntLit(t.file, t.line, t.col, v,
                                      "unsigned long")
                    continue
                if isinstance(node, ast.Ident) and node.name in (
                        "__builtin_add_overflow", "__builtin_sub_overflow",
                        "__builtin_mul_overflow"):
                    # §1 row 16 (M53): the OVERFLOW TRIO lowers to an
                    # Overflow NODE, never a fold — the store through the
                    # result pointer is a SIDE EFFECT (gcc -O0 emits the
                    # width-flag / truncation-check sequence; the law is
                    # measured in .tmp/m2-scratch/c6/probes/oflo3.c).
                    args = self._parse_call_args(t)
                    if len(args) != 3:
                        raise DiagError(
                            "sema", t.file, t.line, t.col,
                            "'{}' takes exactly 3 arguments (§1 row 16)"
                            .format(node.name), node.name)
                    node = ast.Overflow(t.file, t.line, t.col,
                                        node.name[len("__builtin_"):
                                                  -len("_overflow")],
                                        args[0], args[1], args[2])
                    continue
                if isinstance(node, ast.Ident) and node.name in (
                        "__builtin_expect", "__builtin_choose_expr"):
                    # §2.6: DEAD arms must not be analyzed — even the
                    # callable-existence check is analysis
                    # (`__builtin_choose_expr(1, 5, undeclared_fn())` rc0).
                    args = self._gnu_args(t)
                    node = self._fold_gnu_builtin(t, node.name, args)
                    continue
                args = self._parse_call_args(t)
                if not isinstance(node, ast.Ident):
                    # M4 W3 (MC 12563) §2 R1/R2/R5: the call TARGET may be
                    # any expression that TYPES as a function pointer
                    # (`(*fp)(x)`, `o->f(x)`, `t[i](x)`). The M1 §5 wall
                    # ("'function pointer' calls … only named calls") dies
                    # HERE; gcc's rc1 twin for a NON-callable target
                    # (`long x; x(1);`) replaces it — LOUD, never silent.
                    if not self._lenient_calls and \
                            self._callable_ty(node) is None:
                        raise DiagError(
                            "sema", t.file, t.line, t.col,
                            "called object is not a 'function' or a "
                            "'function pointer' (§8 — gcc rc1 twin)", "call")
                elif not self.callable_known(node.name):
                    if self._lenient_calls:
                        # Inside a __builtin_choose_expr/__builtin_expect
                        # argument: parse-and-discard (§2.6) — the arm that
                        # survives is re-checked downstream; the dead one
                        # is never analyzed.
                        node = ast.Call(t.file, t.line, t.col, node, args)
                        continue
                    if self.expr_type(node) is None:
                        raise DiagError(
                            "sema", t.file, t.line, t.col,
                            "no declaration for callable '{}' — not a "
                            "declared function or §6 builtin".format(
                                node.name), node.name)
                    if self._callable_ty(node) is None:
                        # declared but NOT callable (`long x; x(1);`):
                        # gcc rc1 "called object…" — the same §8 twin the
                        # expression-form target above answers with.
                        raise DiagError(
                            "sema", t.file, t.line, t.col,
                            "called object '{}' is not a 'function' or a "
                            "'function pointer' (§8 — gcc rc1 twin)".format(
                                node.name), node.name)
                    # M4 W3: a fn-ptr VARIABLE answers — the §2 R1 law.
                    # The undeclared-IDENTIFIER wall above keeps its exact
                    # sentence (expr_type None = name not in any scope).
                node = ast.Call(t.file, t.line, t.col, node, args)
            elif t.text == "[":
                self.s.next()
                # W-G (MC 12633): the C grammar's subscript holds a full
                # `expression` — a bare comma rides (`a[0, 1]` indexes 1;
                # measured m24-class gcc rc0 both spellings).
                index = self.parse_comma_expression()
                self.s.expect_punct("]")
                node = ast.Index(t.file, t.line, t.col, node, index)
            elif t.text in (".", "->"):
                self.s.next()
                member = self.s.expect_id()
                node = ast.Select(t.file, t.line, t.col, node,
                                  member.text, t.text == "->")
            elif t.text in ("++", "--"):
                self.s.next()
                self._check_lvalue(node, t, "'{}'".format(t.text))
                node = ast.IncDec(t.file, t.line, t.col, t.text, node, False)
            else:
                return node

    def _parse_call_args(self, open_tok) -> tuple:
        self.s.expect_punct("(")
        args = []
        if not self.s.accept_punct(")"):
            while True:
                t = self.s.peek()
                if t.kind == "punct" and t.text == "...":
                    raise DiagError(
                        "sema", t.file, t.line, t.col,
                        "'variadic' calls are not in the subset (§5)", "...")
                args.append(self.parse_expression())
                if self.s.accept_punct(","):
                    continue
                self.s.expect_punct(")")
                break
        return tuple(args)

    # -- primary ----------------------------------------------------------------

    def parse_primary(self) -> ast.Node:
        t = self.s.next()
        if t.kind == "int":
            return ast.IntLit(t.file, t.line, t.col, t.value, t.itype)
        if t.kind == "char":
            return ast.CharLit(t.file, t.line, t.col, t.value)
        if t.kind == "flt":
            # §1 row 14 (M2): STORAGE token (IEEE bits). Any arithmetic,
            # cast or conversion that touches it is a LOUD sema wall.
            return ast.FloatLit(t.file, t.line, t.col, t.value,
                                4 if t.itype == "float" else 8)
        if t.kind == "str":
            return ast.StrLit(t.file, t.line, t.col, t.value)
        if t.kind == "id":
            return ast.Ident(t.file, t.line, t.col, t.text)
        if t.kind == "kw" and t.text == "_Generic":
            # §1 row 6e (M35/M51): _Generic(control, …). Its association
            # FIRST field is a TYPE (or `default`), not an expression, so
            # it is parsed here (not as a call).
            return self.parse_generic(t)
        if t.kind == "punct" and t.text == "&&":
            # §2.6 (M2 row 4d): &&label — the ADDRESS of a C label (void *),
            # the `_THIS_IP_` shape. Computed goto stays out (row 4c): this
            # is ADDRESS-taking only, never `goto *`. (t consumed at head.)
            lt = self.s.expect_id("parse")
            return ast.LabelAddr(t.file, t.line, t.col, lt.text)
        if t.kind == "punct" and t.text == "(" and self.s.at_punct("{"):
            # §1 row 6 (M2-C5 leg 1): GNU statement-expression `({...})` —
            # NOT a cast (no type starts it) and not a compound literal
            # (row 11 needs a TYPE before `{`, §4 M43-46 stage).
            if self.parse_stmt_expr is None:   # bare unit-test harness
                raise DiagError("parse", t.file, t.line, t.col,
                                "expected an expression", "{")
            return self.parse_stmt_expr(t)
        if t.kind == "punct" and t.text == "(":
            # W-G (MC 12633): the C grammar's parenthesized primary holds
            # a full `expression` — the comma rides (`(void)f(), 0`
            # class); a comma in a CALL ARGUMENT list stays the
            # separator because _parse_call_args takes assignment level.
            expr = self.parse_comma_expression()
            self.s.expect_punct(")")
            return expr
        raise DiagError("parse", t.file, t.line, t.col,
                        "expected an expression", t.text)

    # -- helpers ------------------------------------------------------------------

    def _parse_type_args(self, t) -> list:
        self.s.expect_punct("(")
        args = []
        while True:
            d = self.s.peek()
            is_type = (d.kind == "kw") or (d.kind == "id" and
                                           self.is_typename(d.text))
            if not is_type:
                raise DiagError(
                    "sema", t.file, t.line, t.col,
                    "'__builtin_types_compatible_p' takes TYPE arguments "
                    "(§2.12)", d.text)
            args.append(self.parse_type())
            if not self.s.accept_punct(","):
                break
        self.s.expect_punct(")")
        return args

    def _gnu_args(self, t) -> list:
        old = self._lenient_calls
        self._lenient_calls = True
        try:
            return self._parse_call_args(t)
        finally:
            self._lenient_calls = old

    def _fold_offsetof(self, t):
        # §2.13: `__builtin_offsetof(TYPE, m [ [n] ] . m …)` folds at the
        # sema layer — TYPE resolves through the SAME parse_type (typedefs
        # and sizeof already resolved), the member chain walks the layout
        # table; NO second tokenization (§5 perf rule).
        self.s.expect_punct("(")
        d = self.s.peek()
        if not ((d.kind == "kw")
                or (d.kind == "id" and self.is_typename(d.text))):
            raise DiagError(
                "sema", t.file, t.line, t.col,
                "'__builtin_offsetof' first argument is a TYPE (§2.13)",
                d.text)
        ty = self.parse_type()
        self.s.expect_punct(",")
        chain = []
        while True:
            chain.append(self.s.expect_id("parse").text)
            while self.s.accept_punct("["):
                idx = self.parse_binary(1)
                self.s.expect_punct("]")
                v = self.fold_truthy(idx) if self.fold_truthy else None
                if v is None:
                    # M4 W-J (MC 12655): a NON-constant index no longer
                    # LOUDs (the rbtree_latch.h:72 `node[idx]` class).
                    # The walk folds the CONSTANT prefix and builds
                    # `off + idx * esize` through the shipped machinery;
                    # the LOUD arms (non-array, unsizable) ride the SAME
                    # sentences the constant arm has always had.
                    chain.append(("dyn", idx))
                else:
                    chain.append(v)
            if self.s.accept_punct("."):
                continue
            break
        self.s.expect_punct(")")
        if self.fold_offset is None:
            raise DiagError("sema", t.file, t.line, t.col,
                            "__builtin_offsetof is unavailable (§2.13)",
                            "__builtin_offsetof")
        off = self.fold_offset(ty, chain, t)
        if isinstance(off, ast.Node):
            return off          # runtime arm: already the expression
        return ast.IntLit(t.file, t.line, t.col, off, "int")

    def _fold_gnu_builtin(self, t, name: str, args):
        # §2A M2-C5 legs 2+4 (VERBATIM rows): __builtin_expect(a,b) folds
        # to `a` with result type LONG (§2.4e measured: sizeof == 8);
        # __builtin_choose_expr(c,a,b) folds to the constexpr-true arm and
        # the DEAD arm is parse-and-discard — never analyzed (§2.6 pinned:
        # `__builtin_choose_expr(1, 5, undeclared_fn())` is rc0).
        if name == "__builtin_expect":
            if len(args) != 2:
                raise DiagError(
                    "sema", t.file, t.line, t.col,
                    "'__builtin_expect' takes exactly 2 arguments (§2.4e)",
                    "__builtin_expect")
            return ast.Cast(t.file, t.line, t.col,
                            ast.BuiltinType(t.file, t.line, t.col, "long"),
                            args[0])
        if len(args) != 3:
            raise DiagError(
                "sema", t.file, t.line, t.col,
                "'__builtin_choose_expr' takes exactly 3 arguments (§2.6)",
                "__builtin_choose_expr")
        ctrl = self.fold_truthy(args[0]) if self.fold_truthy else None
        if ctrl is None:
            raise DiagError(
                "sema", t.file, t.line, t.col,
                "'__builtin_choose_expr' control is not a compile-time "
                "constant expression (§2.6)", "__builtin_choose_expr")
        return args[1] if ctrl != 0 else args[2]

    def parse_generic(self, t) -> ast.Node:
        """`_Generic ( ctrl, TYPE: expr | default: expr, … )` (§2.6d).
        Arm expressions parse in the lenient window (an UNSELECTED arm is
        not analyzed — probe-measured: `default: undeclared_fn()` rc0);
        the SELECTED arm re-checks downstream. Selection is a codegen
        decision (needs TypeMap); the node carries it faithfully."""
        self.s.expect_punct("(")
        control = self.parse_expression()
        assocs = []
        default = None
        while self.s.accept_punct(","):
            d = self.s.peek()
            old = self._lenient_calls
            self._lenient_calls = True
            try:
                if d.kind == "kw" and d.text == "default":
                    self.s.next()
                    self.s.expect_punct(":")
                    if default is not None:
                        raise DiagError(
                            "sema", d.file, d.line, d.col,
                            "'_Generic' has more than one 'default' "
                            "association (§2.6d)", "default")
                    default = self.parse_expression()
                    continue
                ty = self._generic_key()
                self.s.expect_punct(":")
                assocs.append((ty, self.parse_expression()))
            finally:
                self._lenient_calls = old
        self.s.expect_punct(")")
        return ast.Generic(t.file, t.line, t.col, control, tuple(assocs),
                           default)

    def _generic_key(self) -> ast.Node:
        """An association TYPE: `struct S`, `int`, `seqcount_t`, `int[4]`,
        `int(*)(void)` (M4 wall — the FUNCTION-TYPE part stays LOUD)."""
        d = self.s.peek()
        if d.kind == "id" and not self.is_typename(d.text):
            raise DiagError(
                "parse", d.file, d.line, d.col,
                "_Generic association needs a type name, not identifier "
                "'{}'".format(d.text), d.text)
        return self.parse_type()

    def _starts_type(self, k: int) -> bool:
        t = self.s.peek(k)
        if t.kind == "kw":
            return t.text in _CAST_KW
        return t.kind == "id" and self.is_typename(t.text)

    def _check_lvalue(self, node: ast.Node, tok, context: str) -> None:
        ok = isinstance(node, _LVALUE_KINDS) or (
            isinstance(node, ast.Unary) and node.op == "*")
        if not ok:
            raise DiagError(
                "parse", tok.file, tok.line, tok.col,
                "cannot apply {} to a non-l-value expression".format(context),
                what(node))

    def _struct_type(self, node: ast.Node):
        ty = self.expr_type(node)
        return ty if isinstance(ty, ast.StructType) else None
