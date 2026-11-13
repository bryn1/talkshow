"""Parser unit tests: AST shapes for every §4 construct, §5 loud diagnostics."""
import re

import pytest

from blcc import ast
from blcc.lexer import DiagError, Lexer
from blcc.parser import parse_text
from blcc.preproc import preprocess

DIAG_RE = re.compile(r"^t\.c:\d+:\d+: (parse|sema): .+, found '.+'")


def parse(src):
    return parse_text(src, "t.c")


def diag(src, require_main=False):
    with pytest.raises(DiagError) as ei:
        parse_text(src, "t.c", require_main=require_main)
    assert DIAG_RE.match(str(ei.value)), str(ei.value)
    return ei.value


def find(node, kind):
    """First node of `kind` in the dataclass tree, or None."""
    if isinstance(node, kind):
        return node
    if hasattr(node, "__dataclass_fields__"):
        for field in node.__dataclass_fields__:
            found = find(getattr(node, field), kind)
            if found is not None:
                return found
    elif isinstance(node, (list, tuple)):
        for item in node:
            found = find(item, kind)
            if found is not None:
                return found
    return None


def find_all(node, kind):
    out = []
    if isinstance(node, kind):
        out.append(node)
    if hasattr(node, "__dataclass_fields__"):
        for field in node.__dataclass_fields__:
            out.extend(find_all(getattr(node, field), kind))
    elif isinstance(node, (list, tuple)):
        for item in node:
            out.extend(find_all(item, kind))
    return out


# -- translation unit shape ---------------------------------------------------

def test_translation_unit_decl_kinds():
    tu = parse("""
static int g = 1;
struct point { int x; int y; };
struct fwd;
typedef char buf16[16];
enum Color { RED, GREEN = 3 };
int helper(int a);
int helper(int a) { return a; }
""")
    assert [type(d).__name__ for d in tu.decls] == [
        "VarDecl", "StructDecl", "StructDecl", "TypedefDecl", "EnumDecl",
        "FuncDecl", "FuncDecl"]
    assert tu.decls[0].is_static and tu.decls[0].init.value == 1
    assert tu.decls[1].members[1].name == "y"
    assert tu.decls[2].members is None            # forward declaration
    typedef = tu.decls[3]
    assert typedef.name == "buf16"
    assert isinstance(typedef.type, ast.ArrayType)
    assert typedef.type.inner.name == "char"
    assert tuple(tu.decls[4].constants) == (("RED", 0), ("GREEN", 3))


def test_prototype_vs_definition():
    tu = parse("int f(void);\nint f(void) { return 0; }\n")
    proto, definition = tu.decls
    assert proto.body is None and definition.body is not None
    assert proto.name == definition.name == "f"


def test_main_signature_recorded_faithfully():
    tu = parse("int main(int argc, char **argv) { return 0; }")
    main = tu.decls[0]
    assert main.name == "main"
    [(n1, _), (n2, _)] = [(p.name, p.type) for p in main.params]
    assert (n1, n2) == ("argc", "argv")
    argv = main.params[1].type
    assert isinstance(argv, ast.PtrType) and isinstance(argv.inner,
                                                        ast.PtrType)
    assert isinstance(argv.inner.inner, ast.BuiltinType)


def test_typedef_name_usable_as_type():
    tu = parse("typedef long myint;\nmyint v; myint *p;")
    v, p = tu.decls[1], tu.decls[2]
    assert isinstance(v.type, ast.BuiltinType) and v.type.name == "long"
    assert isinstance(p.type, ast.PtrType)


def test_qualified_type_with_const():
    tu = parse("void pstr(const char *s);")
    param = tu.decls[0].params[0]
    assert isinstance(param.type, ast.PtrType)
    # M2 RESYNC (§2.12): the pointee qualifier is now MARKED, not dropped
    # — `__builtin_types_compatible_p(int*, const char*)` must answer 0
    # (measured), which needs the marker below the PtrType spine. Layout
    # is unchanged: TypeMap._untype strips every Qualified wrapper.
    assert isinstance(param.type.inner, ast.Qualified)
    assert param.type.inner.qual == "const"
    assert isinstance(param.type.inner.inner, ast.BuiltinType)
    assert param.type.inner.inner.name == "char"


def test_enum_constants_are_in_scope_as_values():
    tu = parse("enum E { A, B = 5 };\nint v = B;\n")
    assert tu.decls[1].init.name == "B"  # recorded as an identifier node


def test_initializers_globals_and_strings():
    tu = parse("""
struct P { int x; int y; };
struct P pt = {3, 4};
char *msg = "hi";
int a[3] = {1, 2, 3};
char b[] = "abc";
""")
    assert isinstance(tu.decls[1].init, ast.InitList)
    assert [i.value for i in tu.decls[1].init.items] == [3, 4]
    assert isinstance(tu.decls[2].init, ast.StrLit)
    assert tu.decls[2].init.value == "hi"
    assert [i.value for i in tu.decls[3].init.items] == [1, 2, 3]
    assert isinstance(tu.decls[3].type, ast.ArrayType)
    assert isinstance(tu.decls[4].init, ast.StrLit)  # T a[] with string init


def test_every_node_carries_position():
    tu = parse("int f(void) {\n  int x = 1;\n  return x;\n}")
    decl = find(tu, ast.VarDecl)
    assert decl.name == "x"
    assert (decl.line, decl.col) == (2, 7)  # declarator-name position
    ret = find(tu, ast.Return)
    assert ret.line == 3


# -- statements ---------------------------------------------------------------

def test_if_else_while_do_for_shapes():
    tu = parse("""
int main(void) {
    int i = 0;
    if (i) i = 1; else { i = 2; }
    while (i) { break; }
    do { i--; } while (i);
    for (i = 0; i < 3; i++) { continue; }
    return i;
}
""")
    body = tu.decls[0].body.body
    kinds = [type(s).__name__ for s in body]
    assert kinds == ["VarDecl", "If", "While", "DoWhile", "For", "Return"]
    iff = body[1]
    assert iff.orelse is not None and isinstance(iff.orelse, ast.Compound)
    assert find(body[2], ast.Break) is not None
    assert isinstance(body[3], ast.DoWhile)
    assert isinstance(body[4], ast.For) and body[4].step is not None
    assert find(body[4], ast.Continue) is not None


def test_for_all_empty_parts_and_expression_init():
    tu = parse("""
int main(void) {
    int i = 3;
    for (;;) break;
    for (;i;) { }
    for (i = 0; ; ) { }
    return 0;
}
""")
    fors = find_all(tu, ast.For)
    assert len(fors) == 3
    assert fors[0].init is None and fors[0].cond is None \
        and fors[0].step is None


def test_for_init_simple_declaration():
    tu = parse("int main(void){ for (int i = 0; i < 2; i++) { } }")
    init = find(tu, ast.For).init
    assert isinstance(init, ast.VarDecl) and init.name == "i"


def test_nested_blocks():
    tu = parse("int main(void){ { int x; { x = 1; } } return 0; }")
    outer = find(tu.decls[0].body.body[0], ast.Compound)
    assert outer is not None


def test_empty_statement():
    tu = parse("int main(void){ ; return 0; }")
    stmt = tu.decls[0].body.body[0]
    assert isinstance(stmt, ast.ExprStmt) and stmt.expr is None


# -- switch (§4: in the subset, C fall-through) ---------------------------------

def test_switch_shape_with_fallthrough_and_default():
    tu = parse("""
void pzero(void); void ptwo(void); void pmany(void);
int main(void) {
    int i = 0;
    switch (i) {
        case 0: pzero(); break;
        case 1: case 2: ptwo(); break;
        default: pmany(); break;
    }
    return 0;
}
""")
    sw = find(tu, ast.Switch)
    assert isinstance(sw.control, ast.Ident) and sw.control.name == "i"
    cases = [s for s in sw.body if isinstance(s, ast.Case)]
    defaults = [s for s in sw.body if isinstance(s, ast.Default)]
    assert len(cases) == 2 and len(defaults) == 1
    case0, case1 = cases
    assert case0.value == 0 and isinstance(case0.stmt, ast.ExprStmt)
    # C fall-through: 'case 1: case 2: stmt' nests so case 1 shares stmt
    assert case1.value == 1
    assert isinstance(case1.stmt, ast.Case) and case1.stmt.value == 2
    assert isinstance(case1.stmt.stmt, ast.ExprStmt)
    assert isinstance(defaults[0].stmt, ast.ExprStmt)
    # 'break' exits the switch: a plain Break statement after the arm
    assert isinstance(sw.body[1], ast.Break)
    assert all(n.line >= 4 for n in (case0, case1, defaults[0]))


def test_switch_empty_body():
    tu = parse("int main(void){ switch (1) { } return 0; }")
    sw = find(tu, ast.Switch)
    assert sw.body == ()


# -- §5 constructs: one test each, diagnostic names it with file:line:col ------

def test_float_is_diagnostic():
    # M2 RESYNC (§1 row 14): float PARSES as a storage type; the LOUD wall
    # now guards FP ARITHMETIC (test_independent_negative::test_float_variable).
    tu = parse_text("int f(void) { float x; }", "t.c")
    vd = find(tu.decls[0].body, ast.VarDecl)
    assert isinstance(vd.type, ast.BuiltinType) and vd.type.name == "float"


def test_double_is_diagnostic():
    # M2 RESYNC (§1 row 14): double is a STORAGE type (.quad bytes).
    tu = parse_text("double d;", "t.c")
    assert isinstance(tu.decls[0].type, ast.BuiltinType)
    assert tu.decls[0].type.name == "double"


def test_goto_and_labels_parse():
    # M2 RESYNC (§1 row 4): goto + labels are real grammar now (the parse
    # wall is superseded); §2.5 rules (undefined/duplicate) stay LOUD —
    # pinned in test_independent_negative + tests/test_core_m2_lab.py.
    tu = parse_text("int main(void){ goto end; end: ; return 0; }", "t.c")
    body = tu.decls[0].body.body
    assert isinstance(body[0], ast.Goto) and body[0].name == "end"
    assert isinstance(body[1], ast.Label) and body[1].name == "end"


def test_union_is_diagnostic():
    d = diag("union U { int a; int b; };")
    assert "'union'" in d.message


def test_bitfield_is_diagnostic():
    d = diag("struct S { int flags : 4; };")
    assert "'bitfield'" in d.message


def test_function_pointer_declaration_is_diagnostic():
    d = diag("int (*cmp)(int, int);")
    assert "'function pointer'" in d.message
    assert (d.line, d.col) == (1, 5)


def test_variadic_is_diagnostic():
    d = diag("int sum(int n, ...);")
    assert "'variadic'" in d.message


def test_static_inside_function_is_diagnostic():
    d = diag("void f(void) { static int q; }")
    assert "'static'" in d.message and d.line == 1 and d.col == 16


def test_static_at_file_scope_is_accepted():
    tu = parse("static int g; int main(void){ return g; }")
    assert tu.decls[0].is_static


def test_extern_is_diagnostic():
    d = diag("extern int shared;")
    assert "'extern'" in d.message


def test_default_or_case_outside_switch_is_diagnostic():
    d = diag("int main(void){ default: return 0; }")
    assert "'default'" in d.message
    d = diag("int main(void){ case 2: return 0; }")
    assert "'case'" in d.message


def test_duplicate_case_labels_are_diagnostics():
    d = diag("int main(void){ switch(0){ case 1: break; case 1: break; } }")
    assert "'duplicate case'" in d.message
    d = diag("int main(void){ switch(0){ default: break; default: break; } }")
    assert "more than once" in d.message


def test_non_int_enum_value_is_diagnostic():
    d = diag('enum E { BAD = "x" };')
    assert "'enum'" in d.message


def test_unsigned_is_diagnostic():
    # M2 RESYNC (§1 row 2): the unsigned family PARSES (§2.1/§2.2 typing).
    tu = parse_text("unsigned int u;", "t.c")
    assert isinstance(tu.decls[0].type, ast.BuiltinType)
    assert tu.decls[0].type.name == "unsigned int"


def test_unsized_array_struct_member_is_diagnostic():
    d = diag("struct S { int tail[]; };")
    assert "'array'" in d.message


def test_for_init_beyond_one_simple_declaration():
    d = diag("int main(void){ for (int i = 0, j = 1; i < 1; i++) { } }")
    assert "'for' init" in d.message


def test_unsized_array_without_initializer_is_diagnostic():
    d = diag("int a[];")
    assert "'array'" in d.message


def test_builtins_are_known_callable_but_not_redeclarable():
    parse("int main(void){ char buf[8]; long n = _sys_write(1, \"hi\\n\", 3); "
          "_sys_read(0, buf, 4); long m = strlen(buf); "
          "m += strcmp(buf, buf); _sys_exit(n + m); }")
    d = diag("long strlen(const char *s);")
    assert "builtin" in d.message and "strlen" in d.message
    d = diag("int strcmp;")
    assert "builtin" in d.message


def test_undeclared_callable_is_diagnostic():
    d = diag("int main(void){ return mystery(1); }")
    assert "mystery" in d.message


def test_declared_function_is_callable_before_definition():
    parse("int helper(int);\nint main(void){ return helper(1); }")


def test_missing_main_when_required():
    d = diag("int only_helper(void){ return 0; }", require_main=True)
    assert "'main'" in d.message


# -- grammar errors -------------------------------------------------------------

def test_missing_semicolon_names_position():
    d = diag("int f(void) {\n    int x = 1\n    return x;\n}")
    assert "expected ';'" in d.message
    assert (d.line, d.col) == (3, 5)


def test_extra_closing_brace_is_diagnostic():
    d = diag("int x;\n};\n")
    assert "expected a top-level declaration" in d.message
    assert d.line == 2


def test_declaration_in_unbraced_statement_position():
    d = diag("int main(void){ if (1) int y = 2; return 0; }")
    assert "'declaration'" in d.message


# -- pipeline glue: preproc -> lexer -> parser -------------------------------------

def test_preprocessed_program_parses_with_true_positions(tmp_path):
    (tmp_path / "print.h").write_text(
        'void pstr(const char *s);\n#define NL "\\n"\n')
    src = ('#include "print.h"\n'
           "int main(void){ pstr(NL); _sys_exit(0); return 0; }\n")
    (tmp_path / "m.c").write_text(src)
    from blcc.parser import parse_tokens
    from blcc.preproc import preprocess_file
    lines = preprocess_file(str(tmp_path / "m.c"))
    tu = parse_tokens(Lexer(lines).tokenize())
    # The declaration came from the header: its node carries print.h:1.
    proto = [d for d in tu.decls if isinstance(d, ast.FuncDecl)
             and d.name == "pstr"][0]
    assert proto.file.endswith("print.h") and proto.line == 1
    # The macro expanded at the use site: pstr call is at m.c:2.
    call = find(tu, ast.Call)
    assert call.callee.name == "pstr" and call.line == 2
    arg = call.args[0]
    assert isinstance(arg, ast.StrLit) and arg.value == "\n"
    assert arg.file.endswith("m.c") and arg.line == 2
