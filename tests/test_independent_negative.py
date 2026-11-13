"""Independent adversarial negative suite (grader: test profile, MC 12409).

Every §5 construct ALONE and every malformed input must exit 2 with a §8
diagnostic: `file:line:col: <phase>: <message>, found '<token-or-construct>'`
naming the construct literally, and must NOT leave an output binary (§8:
"nothing is ever emitted for input the contract rejects"). Driven through the
real CLI (`python3 -m blcc`) end-to-end, not through parser units. Also
re-checks the §2 CLI contract independently: --emit-asm keeps <output>.s,
-v echoes the exact as/ld commands, and a linker failure passes through at
exit 3.
"""
import os
import re
import subprocess
import sys

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
NTMP = os.path.join(ROOT, ".tmp", "itneg")

_seq = [0]


def _paths(tag):
    os.makedirs(NTMP, exist_ok=True)
    _seq[0] += 1
    base = os.path.join(NTMP, "neg_{}_{}_{}".format(tag, os.getpid(), _seq[0]))
    return base + ".c", base + ".out"


def blcc_compile(src_text, tag, *extra):
    """Run the real CLI on a single-construct source. Returns
    (CompletedProcess, src_path, out_path)."""
    src, out = _paths(tag)
    with open(src, "w", encoding="utf-8") as fh:
        fh.write(src_text)
    r = subprocess.run([sys.executable, "-m", "blcc", src, "-o", out]
                       + list(extra),
                       cwd=ROOT, capture_output=True, text=True, timeout=30)
    return r, src, out


# §8 line shape: file:line:col: phase: message, found 'x' — one line.
DIAG_RE = re.compile(r"^(\S+):(\d+):(\d+): (lex|pp|parse|sema|asm): .+, "
                     r"found '[^']*'$", re.M)


def assert_loud(src_text, tag, name, line=None, col=None):
    r, src, out = blcc_compile(src_text, tag)
    assert r.returncode == 2, \
        "{}: expected exit 2, got {} stdout={!r} stderr={!r}".format(
            tag, r.returncode, r.stdout, r.stderr)
    m = DIAG_RE.search(r.stderr)
    assert m, "{}: stderr is not a §8 diagnostic: {!r}".format(tag, r.stderr)
    assert m.group(1) == src, "{}: diagnostic names {!r}, expected {!r}" \
        .format(tag, m.group(1), src)
    assert name in r.stderr, \
        "{}: diagnostic must name '{}' literally: {!r}".format(tag, name, r.stderr)
    if line is not None:
        assert (m.group(2), m.group(3)) == (str(line), str(col)), \
            "{}: expected :{}:{} got :{}:{} — {!r}".format(
                tag, line, col, m.group(2), m.group(3), r.stderr)
    assert not os.path.exists(out), \
        "{}: rejected input must not emit a binary".format(tag)
    assert r.stdout == "", "{}: rejected compile must not print to stdout: {!r}" \
        .format(tag, r.stdout)
    return r


# -- §5 constructs, each alone, named literally ---------------------------------

def test_float_variable():
    # M2 RESYNC (§1 row 14): float DECLARATION is storage — SUPPORT. FP
    # ARITHMETIC stays LOUD; the wall moved from parse-time to use-time.
    r, src, out = blcc_compile("float f;\nint main(void){ return 0; }\n",
                               "floatvar")
    assert r.returncode == 0, r.stderr
    if os.path.exists(out):
        os.remove(out)
    r, src, out = blcc_compile("float f;\nfloat g;\nint main(void){ g = f + "
                               "1.0f; return 0; }\n", "floatarith")
    assert r.returncode == 2, "FP arithmetic must stay LOUD: " + r.stderr
    assert "float" in r.stderr and "DEFERRED" in r.stderr, r.stderr


def test_float_literal():
    assert_loud("int main(void){ return 2.5; }\n", "floatlit", "float")


def test_double_type():
    # M2 RESYNC (§1 row 14): double STORAGE SUPPORT; int->double CONVERSION
    # and any FP arith remain the LOUD wall (gcc accepts both — measured;
    # the contract DEFERs them: blcc has no SSE value materialization).
    r, src, out = blcc_compile("static double x = 4195835.0;\n"
                               "int main(void){ return 0; }\n", "dblstore")
    assert r.returncode == 0, r.stderr
    if os.path.exists(out):
        os.remove(out)
    assert_loud("int main(void){ double d = 2; return 0; }\n",
                "double", "double")


def test_goto():
    # M2 RESYNC (§1 row 4 / §2.5): goto + labels are SUPPORT. The GA-era
    # rejection is superseded; what MUST stay LOUD is the §2.5 RULES:
    # undefined target (gcc: "label 'nosuch' used but not defined") and
    # duplicate labels — pinned via assert_loud below, run-leg in
    # tests/test_core_m2_lab.py.
    assert_loud("int main(void)\n{\n    goto nosuch;\n    return 0;\n}\n",
                "golabel", "nosuch", line=3, col=5)


def test_label():
    # duplicate label 'A' (§2.5, gcc rc1 measured) stays LOUD; a plain
    # label statement COMPILES (acceptance leg lives in test_core_m2_lab).
    assert_loud("int main(void){ A: ; A: ; return 0; }\n",
                "dlabel", "A")


def test_union():
    assert_loud("union U { int a; long b; };\nint main(void){ return 0; }\n",
                "union", "union")


def test_bitfield():
    assert_loud("struct S { int a : 3; };\nint main(void){ return 0; }\n",
                "bitfield", "bitfield")


def test_function_pointer_declaration():
    assert_loud("int (*fp)(int);\nint main(void){ return 0; }\n",
                "fptrdecl", "function pointer")


def test_function_pointer_call_through():
    assert_loud("int x;\nint main(void){ return (*x)(); }\n",
                "fptrcall", "function pointer")


def test_function_name_used_as_value():
    assert_loud("int g(void){ return 1; }\nint h;\nint main(void){ h = g; "
                "return 0; }\n", "fnvalue", "function pointer")


def test_variadic_declaration():
    assert_loud("int f(...) { return 0; }\nint main(void){ return 0; }\n",
                "variadic", "variadic")


def test_variadic_call_site():
    assert_loud("int f(long a){ return a; }\nint main(void){ return f(1, ...); }\n",
                "variadicall", "variadic")


def test_struct_assignment():
    assert_loud("struct S{ int a; int b; };\nstruct S x;\nstruct S y;\n"
                "int main(void){ x = y; return 0; }\n",
                "structasg", "struct assignment")


def test_struct_comparison():
    assert_loud("struct S{ int a; int b; };\nstruct S x;\nstruct S y;\n"
                "int main(void){ return x == y; }\n",
                "structcmp", "struct comparison")


def test_angle_include_names_construct():
    r = assert_loud('#include <stdio.h>\nint main(void){ return 0; }\n',
                    "angleinc", "<stdio.h>")
    assert "pp:" in r.stderr, r.stderr


def test_static_inside_function():
    assert_loud("int main(void){ static int s = 1; return s; }\n",
                "staticfn", "static")


def test_extern():
    assert_loud("extern int e;\nint main(void){ return 0; }\n",
                "extern", "extern")


def test_case_outside_switch():
    assert_loud("int main(void){ case 1: return 0; }\n", "caseout", "case")


def test_default_outside_switch():
    assert_loud("int main(void){ default: return 0; }\n", "defout", "default")


def test_unsigned_is_loud():
    # M2 RESYNC (§1 row 2, contract SUPERSEDES the GA wall): the unsigned
    # family is SUPPORT — declaration, wrap and unsigned compare run.
    r, src, out = blcc_compile(
        "int main(void){ unsigned u = 0; u = u - 1; "
        "if (u != 0xFFFFFFFFU) return 1; return 0; }\n", "unsup")
    assert r.returncode == 0, r.stderr
    import subprocess
    proc = subprocess.run([out], capture_output=True, timeout=10)
    assert proc.returncode == 0, "unsigned wrap mis-executes (rc={})".format(
        proc.returncode)
    os.remove(out)


def test_conditional_operator_loud():
    assert_loud("int main(void){ return 1 ? 2 : 3; }\n",
                "condop", "?")


def test_user_array_size_beyond_simple_decl():
    # §5: for-init beyond ONE simple declaration is out.
    assert_loud("int main(void){ int t = 0; for (int i = 0, j = 1; i < 2; "
                "i = i + 1) { t = t + 1; } return t; }\n",
                "formulti", "declaration")


# -- malformed input -----------------------------------------------------------

def test_empty_file_missing_main():
    assert_loud("", "empty", "main")


def test_comment_only_file():
    assert_loud("/* nothing */\n// still nothing\n", "cmt", "main")


def test_missing_main_only_other_functions():
    assert_loud("int f(void){ return 1; }\nint g(void){ return f(); }\n",
                "nomain", "main")


def test_unterminated_string():
    r = assert_loud('int main(void){ return "abc; }\n', "unterm", "unterminated")
    assert "lex:" in r.stderr


def test_unbalanced_extra_brace():
    r = assert_loud("int main(void){ return 0; }\n}\n", "extrabrace", "parse:")
    assert "expected" in r.stderr


def test_missing_semicolon_names_position():
    r = assert_loud("int main(void)\n{\n    return 1\n}\n", "nosemi", "expected")
    assert ":3:" in r.stderr or ":4:" in r.stderr, r.stderr


def test_unknown_identifier():
    assert_loud("int main(void){ return zz; }\n", "unkid", "zz")


def test_call_undeclared_function():
    assert_loud("int main(void){ return nope(1); }\n", "unkfn", "nope")


def test_unknown_include_pp_phase():
    r = assert_loud('#include "definitely_not_here_zz.h"\n'
                    'int main(void){ return 0; }\n', "unkinc", "#include")
    assert "pp:" in r.stderr, r.stderr


def test_redeclare_builtin_is_loud():
    assert_loud("long strlen(const char *s) { return 0; }\n"
                "int main(void){ return 0; }\n", "redecl", "strlen")


def test_call_arity_mismatch_loud():
    assert_loud("int f(long a){ return a; }\nint main(void){ return f(1, 2); }\n",
                "arity2", "f")
    assert_loud("int f(long a, long b){ return a + b; }\n"
                "int main(void){ return f(1); }\n", "arity1", "f")


def test_break_continue_outside_loop_loud():
    assert_loud("int main(void){ break; return 0; }\n", "brk", "break")
    assert_loud("int main(void){ continue; return 0; }\n", "cont", "continue")


def test_stray_hash_is_lex_diagnostic():
    r = assert_loud("int main(void){ # return 0; }\n", "hash", "#")
    assert "lex:" in r.stderr


# -- §2 CLI contract, independent re-check --------------------------------------

def test_emit_asm_prints_keeps_and_still_links():
    src_text = "int main(void){ return 0; }\n"
    r, src, out = blcc_compile(src_text, "emitasm", "--emit-asm")
    assert r.returncode == 0, r.stderr
    s_path = out + ".s"
    assert os.path.isfile(s_path), "contract §2: --emit-asm keeps <output>.s"
    with open(s_path, "r", encoding="utf-8") as fh:
        kept = fh.read()
    assert kept == r.stdout, "printed asm must equal the kept file"
    assert "_start:" in kept and "call main" in kept
    p = subprocess.run([out], capture_output=True, timeout=10)
    assert p.returncode == 0
    os.remove(out)
    os.remove(s_path)
    os.remove(src)


def test_verbose_echoes_exact_commands():
    src_text = "int main(void){ return 0; }\n"
    r, src, out = blcc_compile(src_text, "verbose", "-v")
    assert r.returncode == 0, r.stderr
    assert re.search(r"as --64 -o \S+\.o \S+\.s\n", r.stdout), r.stdout
    assert re.search(r"ld -static -o \S+ \S+\.o\n", r.stdout), r.stdout
    os.remove(out)
    os.remove(src)


def test_linker_failure_exit3_passthrough():
    src_text = "int main(void){ return 0; }\n"
    src, _ = _paths("ldfail")
    with open(src, "w", encoding="utf-8") as fh:
        fh.write(src_text)
    r = subprocess.run([sys.executable, "-m", "blcc", src, "-o",
                        "/nonexistent-dir-12409/out"],
                       cwd=ROOT, capture_output=True, text=True, timeout=30)
    assert r.returncode == 3, (r.returncode, r.stdout, r.stderr)
    assert r.stderr.strip() != "", "tool stderr must be passed through"
    os.remove(src)


def test_usage_errors_exit2():
    r = subprocess.run([sys.executable, "-m", "blcc", "--no-such-flag"],
                       cwd=ROOT, capture_output=True, text=True, timeout=10)
    assert r.returncode == 2
    r = subprocess.run([sys.executable, "-m", "blcc",
                        os.path.join(ROOT, "samples", "hello.c")],
                       cwd=ROOT, capture_output=True, text=True, timeout=10)
    assert r.returncode == 2


def test_all_construction_rejects_leave_stdout_clean_and_binary_absent():
    # The §8 promise as a sweep: for EVERY reject above the binary is absent.
    # Individual checks live in assert_loud; this re-verifies the sweep on a
    # cross-section after everything has run.
    leftovers = []
    for name in sorted(os.listdir(NTMP)):
        if name.endswith(".out") and not name.startswith("keep"):
            leftovers.append(name)
    assert leftovers == [], "rejected compiles emitted outputs: {}".format(leftovers)


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(pytest.main([__file__, "-q"]))
