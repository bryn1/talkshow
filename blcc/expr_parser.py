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
     # §1 row 6c: __typeof__ is legal in cast/sizeof type position
     "typeof", "__typeof__", "__typeof"})
_LVALUE_KINDS = (ast.Ident, ast.Index, ast.Select)


class ExprParser:
    """Operates on a TokenStream shared with the owning Parser."""

    def __init__(self, stream, is_typename: Callable[[str], bool],
                 parse_type: Callable[[], ast.Node],
                 callable_known: Callable[[str], bool],
                 expr_type: Callable[[ast.Node], Optional[ast.Node]],
                 parse_stmts: Optional[Callable] = None,
                 fold_truthy: Optional[Callable] = None,
                 fold_offset: Optional[Callable] = None):
        self.s = stream
        self.is_typename = is_typename
        self.parse_type = parse_type
        self.callable_known = callable_known
        self.expr_type = expr_type
        self.parse_stmt_expr = parse_stmts        # §2.4 stmt-expression
        self.fold_truthy = fold_truthy            # §2.6 choose_expr control
        self.fold_offset = fold_offset            # §2.13 offsetof layout
        self._lenient_calls = False               # inside GNU fold args

    # -- entry: assignment level (right-associative) ------------------------

    def parse_expression(self) -> ast.Node:
        left = self.parse_binary(0)
        t = self.s.peek()
        if t.kind == "punct":
            if t.text == "?":
                raise DiagError(
                    "parse", t.file, t.line, t.col,
                    "'?:' conditional operator is not in the subset (§4)", "?")
            if t.text == "=" or t.text in COMPOUND_ASSIGN_OPS:
                self.s.next()
                value = self.parse_expression()
                self._check_lvalue(left, t, "assignment")
                if self._struct_type(left) is not None:
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
        if t.kind == "punct" and t.text == "(" and self._starts_type(1):
            self.s.next()
            typ = self.parse_type()
            self.s.expect_punct(")")
            operand = self.parse_unary()
            return ast.Cast(t.file, t.line, t.col, typ, operand)
        return self.parse_postfix()

    def parse_sizeof(self) -> ast.Node:
        t = self.s.next()  # 'sizeof'
        if self.s.accept_punct("("):
            if self._starts_type(0):
                typ = self.parse_type()
                self.s.expect_punct(")")
                return ast.Sizeof(t.file, t.line, t.col, typ, None)
            expr = self.parse_expression()
            self.s.expect_punct(")")
            return ast.Sizeof(t.file, t.line, t.col, None, expr)
        if self._starts_type(0):
            typ = self.parse_type()
            return ast.Sizeof(t.file, t.line, t.col, typ, None)
        # 'sizeof x' (no parens): only a bare operand; anything past it is a
        # loud parse error, never silently mis-sized.
        return ast.Sizeof(t.file, t.line, t.col, None, self.parse_primary())

    # -- postfix chain: call, subscript, member, ++/-- -------------------------

    def parse_postfix(self) -> ast.Node:
        node = self.parse_primary()
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
                    raise DiagError(
                        "sema", t.file, t.line, t.col,
                        "'function pointer' calls are not in the subset (§5) "
                        "— only named calls of declared functions or the §6 "
                        "builtins", "call")
                if not self.callable_known(node.name):
                    if self._lenient_calls:
                        # Inside a __builtin_choose_expr/__builtin_expect
                        # argument: parse-and-discard (§2.6) — the arm that
                        # survives is re-checked downstream; the dead one
                        # is never analyzed.
                        node = ast.Call(t.file, t.line, t.col, node, args)
                        continue
                    raise DiagError(
                        "sema", t.file, t.line, t.col,
                        "no declaration for callable '{}' — not a declared "
                        "function or §6 builtin".format(node.name), node.name)
                node = ast.Call(t.file, t.line, t.col, node, args)
            elif t.text == "[":
                self.s.next()
                index = self.parse_expression()
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
            expr = self.parse_expression()
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
                    raise DiagError(
                        "sema", t.file, t.line, t.col,
                        "__builtin_offsetof index is not a compile-time "
                        "constant (§2.13)", "__builtin_offsetof")
                chain.append(v)
            if self.s.accept_punct("."):
                continue
            break
        self.s.expect_punct(")")
        if self.fold_offset is None:
            raise DiagError("sema", t.file, t.line, t.col,
                            "__builtin_offsetof is unavailable (§2.13)",
                            "__builtin_offsetof")
        return ast.IntLit(t.file, t.line, t.col,
                          self.fold_offset(ty, chain, t), "int")

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
