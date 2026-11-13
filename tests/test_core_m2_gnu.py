"""M30/M31 statement-expressions + M32 __builtin_expect + M33 __typeof__ +
M34 __builtin_choose_expr — §1 rows 6/6b/6c/6d, §2.4/§2.6, §2A M2-C5
(VERBATIM legs). gcc 11.4 -std=gnu89 twin: ACCEPT + run-pair equality;
mirror-reject legs pinned per §2.4(d)/§2.6. — MC 12460
"""
import os
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

ITMP = os.path.join(ROOT, ".tmp", "itgnu")


def _fresh(tag):
    os.makedirs(ITMP, exist_ok=True)
    return os.path.join(ITMP, "{}_{}_1".format(tag, os.getpid()))


def both_run(src, tag):
    p = _fresh(tag)
    src_path = p + ".c"
    with open(src_path, "w", encoding="utf-8") as fh:
        fh.write(src)
    out_b = p + ".blcc"
    rb = subprocess.run([sys.executable, "-m", "blcc", src_path, "-o",
                         out_b], cwd=ROOT, capture_output=True, text=True,
                        timeout=60)
    out_g = p + ".gcc"
    rg = subprocess.run(["gcc", "-w", "-std=gnu89", "-O0", "-o", out_g,
                         src_path], capture_output=True, text=True,
                        timeout=60)
    assert rg.returncode == 0, "gcc twin must build: " + rg.stderr
    assert rb.returncode == 0, "blcc compile failed ({}):\n{}".format(
        tag, rb.stderr)
    pb = subprocess.run([out_b], capture_output=True, timeout=30)
    pg = subprocess.run([out_g], capture_output=True, timeout=30)
    assert (pb.returncode, pb.stdout) == (pg.returncode, pg.stdout), \
        "run-pair mismatch ({}): blcc={} gcc={}".format(
            tag, (pb.returncode, pb.stdout), (pg.returncode, pg.stdout))
    for f in (src_path, out_b, out_g):
        os.remove(f)


def _loud(src, tag, frag):
    p = _fresh(tag)
    src_path = p + ".c"
    with open(src_path, "w", encoding="utf-8") as fh:
        fh.write(src)
    r = subprocess.run([sys.executable, "-m", "blcc", src_path,
                        "-o", p + ".out"], cwd=ROOT, capture_output=True,
                       text=True, timeout=60)
    os.remove(src_path)
    assert r.returncode == 2, \
        "{}: expected LOUD (exit 2), got {} stderr={!r}".format(
            tag, r.returncode, r.stderr)
    assert frag in r.stderr, "{}: stderr must name {!r}: {}".format(
        tag, frag, r.stderr)
    assert not os.path.exists(p + ".out"), "rejected input emitted a binary"


# ---- M30: statement expressions (§2.4 a–d) ----------------------------------

def test_stmtexpr_value_and_side_effects_run_pair():
    # §2.4(a): final expr is the value; side effects persist; declared
    # names DIE at `})`.
    both_run(r"""
int g(void) { return 7; }
int main(void) {
    int eff = 0;
    int v = ({ int t = g(); eff = t + 1; t * 2; });
    if (v != 14) return 1;              /* value = final expr            */
    if (eff != 8) return 2;             /* side effect persists          */
    int q = ({ 0; });
    q = ({ int t = 1; q + t; });        /* inner t dies; outer q lives   */
    if (q != 1) return 3;
    return 0;
}
""", "se-basic")


def test_stmtexpr_nested_run_pair():
    # §2.4(b): nesting.
    both_run("int main(void){ int v = ({ ({ 2; }) + ({ ({3;}) * 1; }); });"
             " if (v != 5) return 1; return 0; }\n", "se-nest")


def test_stmtexpr_void_as_statement_ok_as_value_loud():
    # §2.4(c): `({;})` is void — legal as a statement, LOUD as a value.
    both_run("int main(void){ ({ int x = 1; x = x + 1; ; }); return 0; }\n",
             "se-void-ok")
    _loud("int main(void){ int v = ({ ; }); return v; }\n", "se-void-val",
          "void value not ignored as it ought to be")


def test_stmtexpr_file_scope_loud():
    # §2.4(d): file-scope braced-group — mirror the gcc error.
    _loud("static int a = ({2+3;});\nint main(void){ return a; }\n",
          "se-file", "braced-group within expression allowed only inside a "
          "function")


def test_stmtexpr_in_call_and_cond_run_pair():
    both_run(r"""
int p(int a, int b) { return a * 100 + b; }
int main(void) {
    int x = 3;
    int v = p(({ x + 1; }), ({ int y = x; y - 1; }));
    if (v != 402) return 1;
    if (({ x > 2; })) { x += 10; }
    if (x != 13) return 2;
    return 0;
}
""", "se-args")


# ---- M32: __builtin_expect folds to `a`, result type LONG (§2.4e) ----------

def test_expect_fold_run_pair():
    both_run("int main(void){ int c = 1; if (__builtin_expect(c != 0, 1)) "
             "return 0; return 7; }\n", "be-fold")


def test_expect_result_type_long_run_pair():
    # §2.4(e) MEASURED: sizeof(__builtin_expect(1U,0)) == 8 (long).
    both_run("int main(void){ long s = sizeof(__builtin_expect(1U,0)); "
             "if (s != 8) return 1; long v = __builtin_expect(1U, 0); "
             "if (v != 1) return 2; return 0; }\n", "be-long")


# ---- M33: __typeof__ folds to the expression type (§2.6) -------------------

def test_typeof_decl_and_sizeof_run_pair():
    both_run(r"""
static __typeof__(long) gsl = 7;          /* file scope OK (§2.6)        */
int main(void) {
    int a = 4;
    __typeof__(a) b;                      /* b is int                    */
    b = a + 1;
    if (b != 5) return 1;
    if (sizeof(__typeof__(1L)) != 8) return 2;
    if (gsl != 7) return 3;
    char ar[sizeof(__typeof__(1L))];      /* array-declarator leg (e1)   */
    ar[7] = 9;
    if (ar[7] != 9) return 4;
    return 0;
}
""", "ty-decl")


def test_typeof_operand_not_evaluated_run_pair():
    both_run("int main(void){ int called = 0; __typeof__(called = 1) t; "
             "t = 3; if (called != 0) return 1; if (t != 3) return 2; "
             "return 0; }\n", "ty-lazy")


def test_typeof_cast_run_pair():
    # uaccess.h:133 shape: (x) = (__typeof__(*(ptr))) v — plain cast here.
    both_run("int main(void){ int x = 0; char v = 250; "
             "x = (__typeof__(x))(unsigned char)v; if (x != 250) return 1; "
             "return 0; }\n", "ty-cast")


# ---- M34: __builtin_choose_expr (§2.6 — dead arm NOT analyzed) -------------

def test_choose_dead_arm_not_checked_run_pair():
    # §2.6 pinned: `__builtin_choose_expr(1, 5, undeclared_fn())` rc0.
    both_run("int main(void){ int v = __builtin_choose_expr(1, 5, "
             "undeclared_fn()); if (v != 5) return 1; int w = "
             "__builtin_choose_expr(0, 7, 9); if (w != 9) return 2; "
             "return 0; }\n", "ce-dead")


def test_choose_inttype_shape_run_pair():
    # __inttype (uaccess.h:97/104) shape: nested choose, sizeof<=sizeof,
    # unsigned-cast arms.
    both_run(r"""
#define __typefits(_type, _x) __builtin_choose_expr(sizeof(_x) <= sizeof(_type), (_type)0, (long long)0)
int main(void) {
    unsigned char c = 0;
    unsigned short s = 0;
    long l = __typefits(unsigned char, c);
    long m = __typefits(unsigned char, l);
    if (l != 0) return 1;                 /* true arm: (unsigned char)0    */
    if (m != 0) return 2;                 /* false arm: (long long)0      */
    if (sizeof(__typefits(unsigned short, s)) != 2) return 3;  /* u-arm  */
    if (sizeof(__typefits(unsigned char, l)) != 8) return 4;   /* ll arm */
    return 0;
}
""", "ce-inttype")


def test_choose_nonconstant_control_loud():
    _loud("int main(void){ int n = 1; int v = __builtin_choose_expr(n, 5, "
          "7); return v; }\n", "ce-ctrl", "not a compile-time constant")


def test_thisip_stmtexpr_shape_run_pair():
    # kernel.h:175 `_THIS_IP_` = ({ __label__ h; h: (unsigned long)&&h; })
    # — stmt-expr + label + &&label together; value non-zero on both sides.
    both_run("int main(void){ if (({ __label__ h; h: (unsigned long)&&h; })"
             " == 0) return 1; return 0; }\n", "se-thisip")


def test_array_size_fold_gnu_legs():
    # M2 RESYNC of test_regress_c5 w2/w5: gcc accepts `sizeof(...)` and
    # `(long)3` as array-size constants (measured rc0 above); the widened
    # _fold_const now agrees — run-pair (exit = return value, no _sys_exit
    # needed: both compilers leave the same status).
    both_run("enum { A = 2, B = 3 };\n"
             "int main(void){ int a[A*B + sizeof(long)]; a[0]=1; "
             "return a[0]; }\n", "fold-w2")
    both_run("int main(void){ int a[(long)3]; a[2]=5; return a[2]; }\n",
             "fold-w5")
