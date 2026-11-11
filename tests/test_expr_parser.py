"""Expression parser tests: precedence, associativity, casts, sizeof, §5."""
import re

import pytest

from blcc import ast
from blcc.lexer import DiagError, Lexer, SourceLine, TokenStream
from blcc.expr_parser import ExprParser
from blcc.parser import parse_text

DIAG_RE = re.compile(r"^t\.c:\d+:\d+: (parse|sema): .+, found '.+'")


def expr_of(text):
    """Parse `text` as one expression through ExprParser with stub hooks."""
    lines = [SourceLine("e.c", 1, text)]
    stream = TokenStream(Lexer(lines).tokenize())

    def parse_type():
        t = stream.next()
        if t.kind != "kw" or t.text not in ("char", "short", "int", "long",
                                            "void"):
            raise DiagError("parse", t.file, t.line, t.col,
                            "expected a type", t.text)
        ty = ast.BuiltinType(t.file, t.line, t.col, t.text)
        while stream.accept_punct("*") is not None:
            ty = ast.PtrType(t.file, t.line, t.col, ty)
        return ty

    ep = ExprParser(stream,
                    is_typename=lambda name: False,
                    parse_type=parse_type,
                    callable_known=lambda name: True,
                    expr_type=lambda node: None)
    return ep.parse_expression()


def parse(src):
    return parse_text(src, "t.c")


def diag(src):
    with pytest.raises(DiagError) as ei:
        parse_text(src, "t.c")
    assert DIAG_RE.match(str(ei.value)), str(ei.value)
    return ei.value


def find(node, kind):
    if isinstance(node, kind):
        return node
    if hasattr(node, "__dataclass_fields__"):
        for field in node.__dataclass_fields__:
            hit = find(getattr(node, field), kind)
            if hit is not None:
                return hit
    elif isinstance(node, (list, tuple)):
        for item in node:
            hit = find(item, kind)
            if hit is not None:
                return hit
    return None


# -- precedence and associativity ------------------------------------------------

def test_parenthesized_times_shape():
    # (2+3)*4 -> Binary('*', left=Binary('+',2,3))
    e = expr_of("(2+3)*4")
    assert isinstance(e, ast.Binary) and e.op == "*"
    assert isinstance(e.left, ast.Binary) and e.left.op == "+"
    assert (e.left.left.value, e.left.right.value) == (2, 3)
    assert e.right.value == 4


def test_mul_binds_tighter_than_add():
    # a+b*c -> +(a, *(b,c))
    e = expr_of("a+b*c")
    assert isinstance(e, ast.Binary) and e.op == "+"
    assert isinstance(e.right, ast.Binary) and e.right.op == "*"


def test_left_associative_subtraction():
    # a-b-c -> -(-(a,b),c)
    e = expr_of("a-b-c")
    assert e.op == "-" and isinstance(e.left, ast.Binary)
    assert e.left.op == "-" and e.left.left.name == "a"
    assert e.right.name == "c"


def test_assignment_is_right_associative():
    # a=b=c -> Assign(a, Assign(b, c))
    e = expr_of("a=b=c")
    assert isinstance(e, ast.Assign)
    assert e.target.name == "a"
    assert isinstance(e.value, ast.Assign)
    assert e.value.target.name == "b" and e.value.value.name == "c"


def test_and_binds_tighter_than_or():
    # a || b && c -> ||(a, &&(b,c))
    e = expr_of("a || b && c")
    assert isinstance(e, ast.Binary) and e.op == "||"
    assert isinstance(e.right, ast.Binary) and e.right.op == "&&"


def test_shift_lower_than_add():
    # 1 << 2 + 3 -> <<(1, +(2,3))
    e = expr_of("1 << 2 + 3")
    assert e.op == "<<" and isinstance(e.right, ast.Binary)
    assert e.right.op == "+"


def test_equality_lower_than_relational():
    # a == b < c -> ==(a, <(b,c))
    e = expr_of("a == b < c")
    assert e.op == "==" and isinstance(e.right, ast.Binary)
    assert e.right.op == "<"


def test_bitand_lower_than_equality():
    # a & b == c -> &(a, ==(b,c))
    e = expr_of("a & b == c")
    assert e.op == "&" and isinstance(e.right, ast.Binary)
    assert e.right.op == "=="


# -- unary, casts, sizeof ---------------------------------------------------------

def test_unary_minus_binds_tighter_than_mul():
    # -a*b -> *(-(a), b)
    e = expr_of("-a*b")
    assert e.op == "*" and isinstance(e.left, ast.Unary)
    assert e.left.op == "-" and e.left.operand.name == "a"


def test_unary_chain_and_address_deref():
    e = expr_of("!*~x")
    assert e.op == "!" and e.operand.op == "*" and e.operand.operand.op == "~"
    e = expr_of("&x")
    assert e.op == "&" and e.operand.name == "x"
    e = expr_of("*p")
    assert e.op == "*" and e.operand.name == "p"


def test_cast_shape():
    e = expr_of("(long)x")
    assert isinstance(e, ast.Cast)
    assert isinstance(e.type, ast.BuiltinType) and e.type.name == "long"
    assert e.operand.name == "x"


def test_cast_binds_tighter_than_mul():
    # (long)p * 2 -> * (Cast(long,p), 2)
    e = expr_of("(long)p * 2")
    assert e.op == "*" and isinstance(e.left, ast.Cast)


def test_sizeof_both_forms():
    e = expr_of("sizeof(long)")
    assert isinstance(e, ast.Sizeof)
    assert isinstance(e.typ, ast.BuiltinType) and e.arg is None
    e = expr_of("sizeof(x + 1)")
    assert e.typ is None and isinstance(e.arg, ast.Binary)
    e = expr_of("sizeof(int *)")
    assert isinstance(e.typ, ast.PtrType)


# -- postfix: call, subscript, member, inc/dec ------------------------------------------

def test_call_shape_with_args():
    e = expr_of("f(g(1), 2)")
    assert isinstance(e, ast.Call) and e.callee.name == "f"
    assert len(e.args) == 2
    assert isinstance(e.args[0], ast.Call) and e.args[0].callee.name == "g"
    assert e.args[1].value == 2


def test_subscript_then_member_chain():
    # arr[i].y -> Select(Index(arr,i),'y')
    e = expr_of("arr[i].y")
    assert isinstance(e, ast.Select) and e.field == "y" and not e.arrow
    assert isinstance(e.base, ast.Index)
    assert e.base.base.name == "arr" and e.base.index.name == "i"


def test_arrow_member():
    e = expr_of("p->x")
    assert isinstance(e, ast.Select) and e.arrow and e.field == "x"


def test_prefix_postfix_incdec_shapes():
    e = expr_of("++i")
    assert isinstance(e, ast.IncDec) and e.prefix and e.op == "++"
    e = expr_of("i--")
    assert isinstance(e, ast.IncDec) and not e.prefix and e.op == "--"


def test_compound_assignment_shape():
    e = expr_of("x <<= 2")
    assert isinstance(e, ast.AssignOp) and e.op == "<<="
    assert e.target.name == "x" and e.value.value == 2


# -- §5 constructs met in/around expressions ---------------------------------------------

def test_ternary_operator_is_diagnostic():
    d = diag("int main(void){ int x = 1 ? 2 : 3; return x; }")
    assert "'?:'" in d.message
    assert d.found == "?"


def test_struct_assignment_is_diagnostic():
    d = diag("struct P { int x; };\nstruct P a, b;\n"
             "int main(void){ a = b; return 0; }")
    assert "'struct assignment'" in d.message
    assert (d.line, d.col) == (3, 19)


def test_struct_comparison_is_diagnostic():
    d = diag("struct P { int x; };\nstruct P a, b;\n"
             "int main(void){ if (a == b) return 1; return 0; }")
    assert "'struct comparison'" in d.message


def test_memberwise_scalar_assignment_is_in_subset():
    tu = parse("struct P { int x; int y; };\nstruct P a, b;\n"
               "int main(void){ a.x = b.y; return 0; }")
    assign = find(tu, ast.Assign)
    assert isinstance(assign.target, ast.Select)
    assert assign.target.field == "x" and assign.value.field == "y"


def test_call_through_non_identifier_is_diagnostic():
    # A call whose callee is itself an expression = call through a pointer:
    # only possible if function-pointer values existed — loud §5 diagnostic.
    d = diag("int g(void);\nint main(void){ g()(1); return 0; }")
    assert "'function pointer'" in d.message


def test_variadic_call_is_diagnostic():
    d = diag('int main(void){ _sys_write(1, "x", ...); return 0; }')
    assert "'variadic'" in d.message


def test_assign_to_non_lvalue_is_diagnostic():
    with pytest.raises(DiagError) as ei:
        expr_of("2 = x")
    assert "non-l-value" in str(ei.value)
