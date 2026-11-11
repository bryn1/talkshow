"""Preprocessor unit tests: defines, includes, conditionals, undef, cycle guard."""
import os
import re

import pytest

from blcc.lexer import DiagError
from blcc.preproc import preprocess, preprocess_file

PP_RE = re.compile(r"^.*:\d+:\d+: pp: .+, found '.+'")


def texts(lines):
    return [l.text for l in lines]


def joined(text, path="t.c"):
    return "\n".join(texts(preprocess(path, text)))


# -- object-like + function-like defines -------------------------------------

def test_object_like_define():
    out = joined('#define NL "\\n"\nchar *s = NL;\n')
    assert 'char *s = "\\n";' in out


def test_function_like_define_expansion():
    out = joined("#define ADD(a,b) ((a)+(b))\nint x = ADD(1, 2);\n")
    assert "int x = ((1)+(2));" in out


def test_function_like_nested_and_expression_args():
    out = joined("#define ADD(a,b) ((a)+(b))\n"
                 "#define TWO 2\n"
                 "int x = ADD(ADD(TWO, 1), y * 3);\n")
    assert "int x = ((((2)+(1)))+(y * 3));" in out


def test_macro_name_inside_string_and_comment_not_expanded():
    out = joined("#define FOO 1\n"
                 'char *s = "FOO"; // FOO here\n'
                 "int FOO_bar = 2;\n")
    assert 'char *s = "FOO"; // FOO here' in out
    assert "int FOO_bar = 2;" in out


def test_zero_arg_function_like_define():
    out = joined("#define HERE 9\n#define P() q(HERE)\nint v = P();\n")
    assert "int v = q(9);" in out


def test_macro_arg_count_mismatch_is_pp_diagnostic():
    with pytest.raises(DiagError) as ei:
        preprocess("t.c", "#define ADD(a,b) ((a)+(b))\nint x = ADD(1);\n")
    assert "ADD" in str(ei.value) and "argument" in str(ei.value)
    assert PP_RE.match(str(ei.value))


def test_runaway_macro_is_loud_not_infinite():
    with pytest.raises(DiagError) as ei:
        preprocess("t.c", "#define A A+1\nint x = A;\n")
    assert "macro expansion limit" in str(ei.value)


# -- conditionals --------------------------------------------------------------

def test_ifdef_else_endif():
    out = joined("#define ON\n#ifdef ON\nint a;\n#else\nint b;\n#endif\n")
    assert "int a;" in out and "int b;" not in out


def test_ifndef_and_undef():
    out = joined("#define X\n#ifndef X\nint a;\n#else\nint b;\n#endif\n"
                 "#undef X\n#ifndef X\nint c;\n#endif\n")
    assert "int a;" not in out and "int b;" in out and "int c;" in out


def test_nested_conditionals_skip_inactive_defines():
    out = joined("#define A\n#ifdef A\n#ifdef B\n#define HIDDEN 1\n"
                 "int hidden;\n#endif\n"
                 "int shown;\n#endif\nint Y = HIDDEN;\n")
    assert "int hidden;" not in out
    assert "int shown;" in out
    assert "int Y = HIDDEN;" in out  # #define inside inactive branch didn't run


def test_unbalanced_conditional_directives():
    with pytest.raises(DiagError) as ei:
        preprocess("t.c", "#endif\n")
    assert "without" in str(ei.value)
    with pytest.raises(DiagError) as ei:
        preprocess("t.c", "#else\n")
    assert "without" in str(ei.value)


# -- includes ---------------------------------------------------------------------

def test_quoted_include_inlines_relative_to_including_file(tmp_path):
    (tmp_path / "h.h").write_text("int from_h;\n")
    sub = tmp_path / "sub"
    sub.mkdir()
    (sub / "m.c").write_text('#include "../h.h"\nint main_var;\n')
    lines = preprocess_file(str(sub / "m.c"))
    assert any("int from_h;" in l.text for l in lines)
    # included content carries the header's own path, not the .c's
    assert any(l.file.endswith("h.h") and "int from_h;" in l.text
               for l in lines)


def test_unknown_include_is_pp_diagnostic(tmp_path):
    p = tmp_path / "m.c"
    p.write_text('#include "nope.h"\n')
    with pytest.raises(DiagError) as ei:
        preprocess_file(str(p))
    assert "pp" in str(ei.value)
    assert "nope.h" in str(ei.value)
    assert PP_RE.match(str(ei.value))


def test_angle_include_diagnostic_names_construct():
    with pytest.raises(DiagError) as ei:
        preprocess("t.c", "#include <stdio.h>\nint main(void){}\n")
    msg = str(ei.value)
    assert "#include <" in msg and "stdio.h" in msg
    assert PP_RE.match(msg)


def test_include_cycle_guard(tmp_path):
    (tmp_path / "a.h").write_text('#include "b.h"\n')
    (tmp_path / "b.h").write_text('#include "a.h"\n')
    (tmp_path / "m.c").write_text('#include "a.h"\nint v;\n')
    with pytest.raises(DiagError) as ei:
        preprocess_file(str(tmp_path / "m.c"))
    assert "cycle" in str(ei.value)
    assert "a.h" in str(ei.value)


def test_self_include_cycle_guard(tmp_path):
    (tmp_path / "s.h").write_text('#include "s.h"\nint v;\n')
    with pytest.raises(DiagError) as ei:
        preprocess_file(str(tmp_path / "s.h"))
    assert "cycle" in str(ei.value)


# -- directives and positions -----------------------------------------------------

def test_unsupported_directive_is_pp_diagnostic():
    with pytest.raises(DiagError) as ei:
        preprocess("t.c", "#if 1\nint x;\n#endif\n")
    assert "#if" in str(ei.value)
    assert PP_RE.match(str(ei.value))


def test_positions_survive_expansion_and_inclusion(tmp_path):
    (tmp_path / "k.h").write_text("int in_header;\n")
    lines = preprocess_file(str(tmp_path / "k.h"))
    assert lines[0].line == 1 and lines[0].file.endswith("k.h")
    out = preprocess("t.c", "#define V 7\nint x = V;\n\nint y = V;\n")
    got = [(l.line, l.text) for l in out if l.text.strip()]
    assert got == [(2, "int x = 7;"), (4, "int y = 7;")]


def test_undef_of_unknown_name_is_fine():
    assert "int z;" in joined("#undef NOTHING\nint z;\n")
