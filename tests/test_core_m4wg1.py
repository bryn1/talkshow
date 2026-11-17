"""M4 W-G COMMIT-1 (MC 12633, card 12404.2.70) — COMMA EXPRESSION AT THE
C GRAMMAR'S `expression` SLOTS (cast as LEFT operand of comma).

THE WALL (plan §5, AMENDMENT-5): 492/706 kernel streams die at
spinlock.h:448:43 `parse: expected ')', found ','` — the expansion of
spinlock.h:117 `#define raw_spin_is_contended(lock) (((void)(lock), 0))`
(nx1.c witness class, .tmp/m4-wb-gate/probes/nx1.c). blcc knew ONE
comma site — the conditional's MIDDLE operand (§1c MC 12486) — and
answered every other parenthesized/statement comma with the parse wall.

THE MEASURED LAW (gcc 11.4 -std=gnu89, this session, probes
.tmp/m4-wg/measure/m*.c — table in .tmp/m4-wg/out/gcc-law.txt):
  ACCEPT+evaluate (value = RIGHT, LEFT fully sequenced before RIGHT):
    expression statement `1, x = 5;` (m26); parenthesized primary
    (m2); for ALL THREE clauses (m3/m4/m29); call argument when FULLY
    parenthesized `p((1,2), 3)` — a BARE comma in an arg list stays
    the ARGUMENT SEPARATOR (m30 gcc rc1); nested chains cast
    left/right/middle (m7); if/while/do/switch conditions (m8/m11);
    return, bare AND parenthesized `return (void)0, 3;` (m12/m25);
    subscript — `[]` holds an expression (m24 + bare); sizeof/
    alignof over a parenthesized comma (m18/m27); GNU ({...}) tail
    (m31); ?: test position (m19); cast operand (m23 shape).
  Law arms: result TYPE = right operand (widening leg pins);
    consumers convert the RIGHT value (char c = (1,300) -> 44, m15);
    the comma result is NOT an lvalue (m9 rc1); void right operand:
    legal when the value is DROPPED — whole statement or the LEFT of
    an outer comma (m22 rc0) — error when consumed (m10/m34 rc1);
    void LEFT operand is the wall class itself, legal everywhere.
  REJECT (blcc mirrors LOUD, constant contexts): initializer element
    `int x = (1,2);` and `int a[] = {(1,2),3};` rc1 "not constant"
    (m16/m36 — the initializer takes an assignment-expression, and a
    parenthesized comma is NOT an integer constant); enumerator rc1
    (m35); `case (1,2):` rc1 (m28). A TAGGED nested specifier or the
    declarator-list comma is NOT this operator (m32 shape).

VOID-CONSUMPTION PRE-EXISTENCE (named, NOT fixed here): blcc at tip
accepts `int x = fv();` (void-returning fv) at rc0 where gcc is rc1
(v5/v6 measured) — the shipped SILENT-DIV class the W3 close row
already named for void returns. The comma legs PIN the divergence
shape (test_void_right_consumed_divergence_pin) rather than invent
an N-consumer-site mechanism in this wave; volume measured at close.

ONE MECHANISM: the shipped parse_comma_expression (conditional middle)
becomes the C `expression` nonterminal at exactly the arms the grammar
and the table above name: primary parens, sizeof/alignof expr forms,
subscript, if/while (ONE _parse_control_head), do-while, for ×3,
switch, return, expression statement. Call args, initializers, case,
enum, asm operands, va_arg and _Generic STAY assignment-level — the
separator/constant law they need is the one they already have.
"""
import os
import re
import subprocess
import sys

import pytest

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.environ.get("BLCC_REPO") or os.path.dirname(HERE)
STREAMS = os.path.join(REPO, "..", ".tmp", "m4-plan", "streams")


def blcc(args):
    return subprocess.run([sys.executable, "-m", "blcc"] + args,
                          capture_output=True, text=True, cwd=REPO,
                          env={"PYTHONPATH": REPO, "PATH": "/usr/bin:/bin"})


def gcc(args):
    return subprocess.run(["gcc", "-std=gnu89", "-Os"] + list(args),
                          capture_output=True, text=True, timeout=120)


def twin(tmp_path, tag, src):
    """Both compilers MUST accept the -c probe (parse-law twin)."""
    s = tmp_path / (tag + ".c")
    s.write_text(src)
    gr = gcc(["-c", str(s), "-o", str(tmp_path / (tag + ".g.o"))])
    assert gr.returncode == 0, "oracle must accept ({}):\n{}".format(
        tag, gr.stderr)
    br = blcc(["-c", str(s), "-o", str(tmp_path / (tag + ".b.o"))])
    assert br.returncode == 0, "blcc must accept ({}):\n{}".format(
        tag, br.stderr)


def run_pair(tmp_path, tag, src, expect=None):
    """ORACLE-DECIDES: link both exes, run both, SAME exit code."""
    s = tmp_path / (tag + ".c")
    s.write_text(src)
    gx = tmp_path / (tag + ".gcc")
    gr = gcc([str(s), "-o", str(gx)])
    assert gr.returncode == 0, "oracle must build:\n" + gr.stderr
    bx = tmp_path / (tag + ".blcc")
    br = blcc([str(s), "-o", str(bx)])
    assert br.returncode == 0, "blcc must build:\n" + br.stderr
    g = subprocess.run([str(gx)], capture_output=True, text=True, timeout=30)
    b = subprocess.run([str(bx)], capture_output=True, text=True, timeout=30)
    assert g.returncode == b.returncode, \
        "run-pair diverge: gcc {} vs blcc {} on\n{}".format(
            g.returncode, b.returncode, src)
    if expect is not None:
        assert g.returncode == expect, \
            "oracle answers {}, leg expects {} on\n{}".format(
                g.returncode, expect, src)
    return g.returncode


def loud(tmp_path, tag, src, needle):
    """gcc rc!=0 AND blcc rc 2 naming the class (mirror twin)."""
    s = tmp_path / (tag + ".c")
    s.write_text(src)
    gr = gcc(["-c", str(s), "-o", str(tmp_path / (tag + ".g.o"))])
    assert gr.returncode != 0, "oracle must REJECT ({}):\n{}".format(
        tag, gr.stderr)
    br = blcc(["-c", str(s), "-o", str(tmp_path / (tag + ".b.o"))])
    assert br.returncode == 2, \
        "blcc must LOUD ({}) rc2, got {}:\n{}".format(
            tag, br.returncode, br.stderr)
    assert needle in br.stderr, \
        "blcc must NAME the class ({}):\n{}".format(tag, br.stderr)
    return br.stderr


# ------------------------------------------------------ THE WALL

# nx1.c VERBATIM from the W-B gate probes (spinlock.h:448 witness class).
NX1 = ("struct L { struct { int a; } raw; };\n"
       "int g(struct L *l);\n"
       "int f(struct L *lock){ return ((void)(&lock->raw), 0) + g(lock); }\n")


def test_wg_nx1_witness_compiles_pair(tmp_path):
    # THE 492-stream wall: -c, both compilers, rc 0. RED at tip: blcc
    # answers `expected ')', found ','` (spinlock.h:448:43 class).
    twin(tmp_path, "wg_nx1", NX1)


def test_wg_spinlock_macro_verbatim_run_pair(tmp_path):
    # spinlock.h:117 macro VERBATIM shape used from a call argument —
    # the corpus consumer position. value = right operand (0), the
    # void-left evaluated for effect.
    src = ("struct L { int x; } l;\n"
           "#define IS_CONTENDED(lock) (((void)(lock), 0))\n"
           "int main(void){ int v = IS_CONTENDED(&l) + ((void)(l.x), 5);"
           " return v - 5; }\n")
    run_pair(tmp_path, "wg_macro", src, expect=0)


# ------------------------------------------------ grammar arms (run-pair)

def test_wg_expr_stmt_bare_comma(tmp_path):
    run_pair(tmp_path, "wg_stmt",
             "int main(void){ int x; 1, x = 5; return x - 5; }", expect=0)


def test_wg_expr_stmt_cast_left_effect(tmp_path):
    src = ("int sink; int f(void){ sink = 5; return 0; }\n"
           "int main(void){ (f(), (void)sink); return sink - 5; }\n")
    run_pair(tmp_path, "wg_stmt2", src, expect=0)


def test_wg_paren_primary_value(tmp_path):
    src = ("int f(void){ return 5; }\n"
           "int main(void){ int g = (1, 2); return (1, f()) - 5 - g + 2; }\n")
    run_pair(tmp_path, "wg_paren", src, expect=0)


def test_wg_for_third_cast_comma(tmp_path):
    src = ("int n = 0; int bump(void){ n++; return n; }\n"
           "int main(void){ int i, t = 0;"
           " for (i = 0; i < 3; (void)bump(), i++) t += i;"
           " return t + n - 6; }\n")
    run_pair(tmp_path, "wg_for3", src, expect=0)


def test_wg_for_first_and_second_clause(tmp_path):
    src = ("int main(void){ int i = 0, s = 0;"
           " for ((void)0, i = 1; i, (i < 3); i++) s += i;"
           " return s - 3; }\n")
    run_pair(tmp_path, "wg_for12", src, expect=0)


def test_wg_for_full_chain_effects(tmp_path):
    src = ("int side; int hit(void){ side = 1; return 1; }\n"
           "int main(void){ int i, s = 0;"
           " for (i = 0; (void)hit(), i < 3; (void)hit(), i++) s += i;"
           " return side ? s - 3 : 9; }\n")
    run_pair(tmp_path, "wg_forall", src, expect=0)


def test_wg_call_arg_parenthesized_comma(tmp_path):
    src = ("int p(int a, int b){ return a * 10 + b; }\n"
           "int main(void){ return p((1, 2), 3) - 23; }\n")
    run_pair(tmp_path, "wg_arg", src, expect=0)


def test_wg_call_arg_bare_comma_stays_separator(tmp_path):
    # m30: a BARE comma in an argument list is the SEPARATOR — two args
    # for a one-parameter fn; BOTH compilers reject (gcc rc1, blcc rc2
    # through the shipped arity law). Fairness: green in BOTH states.
    loud(tmp_path, "wg_argsep",
         "int p(int a){ return a; }\n"
         "int side; int hit(void){ side = 1; return 1; }\n"
         "int main(void){ return p((void)hit(), 2) + side; }\n",
         "argument(s)")


def test_wg_nested_chain_cast_left_right_middle(tmp_path):
    # m7 integerized: cast left, int-literal middle, call last.
    src = ("int side; int hit(void){ side = 1; return 7; }\n"
           "int main(void){ int v = ((void)hit(), (1, (long)29, hit()));"
           " int w = ((int)1, 2, (void)0, 3); return v + w - 10; }\n")
    run_pair(tmp_path, "wg_chain", src, expect=0)


def test_wg_and_or_neighbours(tmp_path):
    # m8: parenthesized comma as an &&/|| operand and comma at the
    # statement/condition edge — evaluation of the left side effects.
    src = ("int side = 0; int hit(void){ side = 1; return 1; }\n"
           "int main(void){ if ((void)hit(), 0) return 9;"
           " if (hit() && (1, 0)) return 8;"
           " if ((hit(), 1) || 0) return side; return 0; }\n")
    run_pair(tmp_path, "wg_andor", src, expect=1)


def test_wg_control_conditions(tmp_path):
    # m11: while/do-while/switch conditions take the comma.
    src = ("int i = 3;\n"
           "int main(void){ int s = 0;"
           " while ((void)i, --i) s += i;"
           " do { } while ((1, 0));"
           " switch ((void)s, 1) { case 1: return s - 3;"
           " default: return 99; } }\n")
    run_pair(tmp_path, "wg_cond", src, expect=0)


def test_wg_return_bare_and_paren(tmp_path):
    # m25 + m12: return takes a comma expression; the value is the
    # RIGHT-most operand of the chain.
    run_pair(tmp_path, "wg_ret1",
             "int main(void){ return (void)0, 1; }", expect=1)
    run_pair(tmp_path, "wg_ret2",
             "int main(void){ int t = 4; return (t, 2), 1; }", expect=1)


def test_wg_subscript_comma(tmp_path):
    # m24 + the BARE form: the subscript bracket holds an expression.
    src = ("int arr[4]; int main(void){ arr[0] = 1; arr[(0, 1)] = 5;"
           " arr[1, 0] = 9; return arr[0] + arr[1] - 14; }\n")
    run_pair(tmp_path, "wg_sub", src, expect=0)


def test_wg_stmt_expr_tail(tmp_path):
    # m31: the GNU ({...}) tail expression takes the statement comma.
    run_pair(tmp_path, "wg_sexpr",
             "int main(void){ int v = ({ 1, 2; }); return v - 2; }",
             expect=0)


def test_wg_generic_test_position(tmp_path):
    # m19 integerized: comma at the ?: test position (middle arm already
    # shipped §1c — this is the TEST side), plus value-side parens.
    src = ("int side = 0; int hit(void){ side = 1; return 1; }\n"
           "int main(void){ int v = ((void)hit(), 1) ? 5 : 6;"
           " if (v != 5) return 1; return side + (0 ? (1, 2) : (3, 4)) - 5; }\n")
    run_pair(tmp_path, "wg_test", src, expect=0)


def test_wg_cast_of_paren_comma(tmp_path):
    # m23 integerized: the cast operand is the parenthesized comma.
    run_pair(tmp_path, "wg_cast",
             "int main(void){ return (int)(1, 29) - 29; }", expect=0)


# --------------------------------------------------------- law arms

def test_wg_eval_order_left_fully_before_right(tmp_path):
    # m13: the left operand is evaluated COMPLETELY first (C11 sequenced).
    src = ("int log_[8]; int k = 0;\n"
           "int a(void){ log_[k++] = 1; return 10; }"
           " int b(void){ log_[k++] = 2; return 20; }\n"
           "int main(void){ int v = (a(), b());"
           " if (v != 20) return 1; if (k != 2) return 2;"
           " if (log_[0] != 1 || log_[1] != 2) return 3; return 0; }\n")
    run_pair(tmp_path, "wg_order", src, expect=0)


def test_wg_value_is_right_type_is_right(tmp_path):
    # Widening pair: (1, u) rides the unsigned int value 4294967295;
    # (1, (int)u) the signed -1 — the RESULT TYPE is the RIGHT operand's.
    src = ("unsigned u; int main(void){ u = 0xFFFFFFFF;"
           " long v = (1, u); long w = (1, (int)u);"
           " if (v != 4294967295L) return 1; if (w != -1) return 2;"
           " return 0; }\n")
    run_pair(tmp_path, "wg_type", src, expect=0)


def test_wg_consumer_converts_right(tmp_path):
    # m15: char c = (1, 300) -> 44 — the consumer converts the value
    # the SAME as a parenthesized scalar would.
    run_pair(tmp_path, "wg_conv",
             "int main(void){ char c = (1, 300); return (unsigned char)c; }",
             expect=44)


def test_wg_comma_not_lvalue(tmp_path):
    # m9: (a, b) = 3 -> gcc rc1 "lvalue required"; blcc LOUDs through
    # the shipped non-l-value sentence. RED at tip: the PARSE wall
    # answers first (different needle).
    loud(tmp_path, "wg_lval",
         "int main(void){ int a = 1, b = 2; (a, b) = 3; return 0; }\n",
         "non-l-value")


def test_wg_void_right_dropped_ok(tmp_path):
    # m22: the comma value is DROPPED (whole statement) — a void right
    # operand is legal there.
    src = ("int side; int hit(void){ side = 1; return 1; }\n"
           "int main(void){ (hit(), (void)side); (void)(hit(), (void)side);"
           " return side; }\n")
    run_pair(tmp_path, "wg_voidok", src, expect=1)


def test_void_right_consumed_divergence_pin(tmp_path):
    # NAMED SILENT-DIV pin (do NOT "fix" here): gcc rc1 "void value not
    # ignored"; blcc consumes it at rc0 — the PRE-EXISTING class the
    # W3 close row already named for void RETURNS (tip accepts
    # `int x = fv();` rc0, v5/v6 measured 9c84499). The comma rides
    # the same consumer paths; retiring the class is a separate card.
    s = tmp_path / "wg_voiddiv.c"
    s.write_text("void fv(void);\nint main(void){ int x = (1, fv());"
                 " return 0; }\n")
    gr = gcc(["-c", str(s), "-o", str(tmp_path / "wg_voiddiv.g.o")])
    assert gr.returncode != 0
    br = blcc(["-c", str(s), "-o", str(tmp_path / "wg_voiddiv.b.o")])
    assert br.returncode == 0, \
        "if blcc now LOUDs this, the class died — retire the pin, " \
        "update this leg and the LEDGER row:\n" + br.stderr


def test_wg_sizeof_comma_fold(tmp_path):
    # m18: sizeof over the parenthesized comma = the type size, folded
    # (array-size probe = gcc-verifiable both sides).
    src = ("int probe[sizeof((1, 2L)) == 8 ? 1 : -1];\n"
           "int main(void){ return probe == 0; }\n")
    run_pair(tmp_path, "wg_sizeof", src, expect=0)


def test_wg_alignof_comma_fold(tmp_path):
    # m27: __alignof__ over the parenthesized comma rides the type size.
    src = ("int probe[__alignof__((1, 2L)) == 8 ? 1 : -1];\n"
           "int main(void){ return probe == 0; }\n")
    run_pair(tmp_path, "wg_alignof", src, expect=0)


# ----------------------------------------------- REJECT mirrors (LOUD)

def test_wg_initializer_comma_not_constant(tmp_path):
    # m16/m36: the initializer takes an assignment-expression; the
    # parenthesized comma is NOT an integer constant (gcc rc1 both
    # spellings). RED at tip: the parse wall answers first.
    loud(tmp_path, "wg_init1", "int x = (1, 2);\n", "constant")
    loud(tmp_path, "wg_init2", "int a[] = { (1, 2), 3 };\n", "constant")


def test_wg_enum_comma_not_constant(tmp_path):
    # m35: enumerator value (1,2) — gcc rc1.
    loud(tmp_path, "wg_enum", "enum E { V = (1, 2) };\n"
         "int main(void){ return V - 2; }\n", "constant")


def test_wg_case_label_comma_not_constant(tmp_path):
    # m28: case label does not reduce to an integer constant.
    loud(tmp_path, "wg_case",
         "int main(void){ switch (1) { case (1, 2): return 1;"
         " default: return 0; } }\n", "constant")


def test_wg_declarator_comma_is_not_this_operator(tmp_path):
    # m32-class fairness twin: `int v = 1, 2 ? 3 : 4;` is DECLARATOR
    # territory (the comma separates declarators; `2` is not one) —
    # BOTH compilers reject; blcc's sentence is the declarator one.
    loud(tmp_path, "wg_decl",
         "int main(void){ int v = 1, 2 ? 3 : 4; return v; }\n",
         "expected an identifier")


# ------------------------------------------------------ corpus legs

CORPUS = ["init_main.c.i", "kernel_cpu.c.i", "kernel_capability.c.i"]


def _clean_i(path, tmp_path, tag):
    """m3/m4 corpus idiom: elide linemarkers, erase literal suffixes."""
    clean = tmp_path / (tag + ".c")
    su = re.compile(r"\b(0[xX][0-9a-fA-F]+|[0-9]+)[uU][lL]{0,2}\b")
    sr = re.compile(r"\b(0[xX][0-9a-fA-F]+|[0-9]+)[lL][uU][lL]?\b")
    sl = re.compile(r"\b(0[xX][0-9a-fA-F]+|[0-9]+)[lL]+\b")
    with open(path, encoding="utf-8", errors="replace") as fh, \
            open(clean, "w", encoding="utf-8") as out:
        for line in fh:
            if line.startswith("#"):
                continue
            out.write(sl.sub(r"\1", sr.sub(r"\1", su.sub(r"\1", line))))
    return clean


@pytest.mark.skipif(not (os.environ.get("KERNEL_510")
                         and os.path.isdir(STREAMS)),
                    reason="kernel tier + pinned streams corpus required")
@pytest.mark.parametrize("stream", CORPUS)
def test_wg_spinlock_comma_wall_is_dead(stream, tmp_path):
    # 492/706 streams' first-blocker sentence (spinlock.h:448 cast-
    # comma class `expected ')', found ','`) must be GONE. The stream
    # may still LOUD — the NEXT wall is honest; the histogram measures
    # where it lands (close-leg instrument).
    clean = _clean_i(os.path.join(STREAMS, stream), tmp_path, "corpwg")
    r = blcc(["-c", str(clean), "-o", str(tmp_path / "corpwg.o")])
    assert "expected ')', found ','" not in r.stderr, \
        "{} still hits the comma parse wall:\n{}".format(stream,
                                                         r.stderr[:600])
