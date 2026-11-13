"""M42 (parse leg) — __attribute__ grammar: PARSE + STRIP the ignore-class,
LOUD wall for the layout-class until its rule ships. MC 12460 cycle-2,
§1 row 9: "IGNORE-class attrs ... parse + strip (sema-side for
__compiletime_assert/error per §2.9); layout-class `packed`/`aligned` MUST
ACT"; the ACTION (§2.13 pack legs) lands with the rest of M42 — until then
layout-class stays a §5 LOUD wall, never a silent strip (silent-strip would
lie about layout; the oracle says packed changes offsets).
The PARSE mechanism is needed NOW: the M58(d) FIXTURE-VDSO-SYNTH carries
`__attribute__((__gnu_inline__))`/`__attribute__((__unused__))` per §2.17.
gcc 11.4 -std=gnu89 twins pin every strip leg (rc0).
"""
import os
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

ITMP = os.path.join(ROOT, ".tmp", "itattr")


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
    assert rg.returncode == 0, "gcc twin must build ({}):\n{}".format(
        tag, rg.stderr)
    assert rb.returncode == 0, "blcc compile failed ({}):\n{}".format(
        tag, rb.stderr)
    pb = subprocess.run([out_b], capture_output=True, timeout=30)
    pg = subprocess.run([out_g], capture_output=True, timeout=30)
    assert (pb.returncode, pb.stdout) == (pg.returncode, pg.stdout), \
        "run-pair mismatch ({}): blcc={} gcc={}".format(
            tag, (pb.returncode, pb.stdout), (pg.returncode, pg.stdout))
    for f in (src_path, out_b, out_g):
        os.remove(f)


def loud(src, tag, frag):
    p = _fresh(tag)
    src_path = p + ".c"
    with open(src_path, "w", encoding="utf-8") as fh:
        fh.write(src)
    r = subprocess.run([sys.executable, "-m", "blcc", src_path,
                        "-o", p + ".out"], cwd=ROOT, capture_output=True,
                       text=True, timeout=60)
    os.remove(src_path)
    assert r.returncode == 2, "{}: expected LOUD, got {} {}".format(
        tag, r.returncode, r.stderr)
    assert frag in r.stderr, "{}: {} must name {!r}".format(tag, r.stderr,
                                                            frag)


# ---- strip-class legs (gcc-twin rc0, value untouched) ----------------------

def test_attr_on_function_and_var_run_pair():
    both_run("""
__attribute__((unused)) static int helper(int x) { return x + 1; }
static int g __attribute__((unused)) = 3;
int main(void) {
    int v __attribute__((unused)) = 5;
    return helper(g) + v - 9;
}
""", "attr-fnv")


def test_attr_chained_lists_and_multi_name_run_pair():
    both_run("""
__attribute__((unused)) __attribute__((noinline))
static int twice(int x) { return x + x; }
__attribute__((unused, gnu_inline)) static inline int id(int x)
{ return x; }
int main(void) { return twice(2) + id(1) - 5; }
""", "attr-chain")


def test_attr_with_args_and_strings_run_pair():
    # format(printf,…) on its REAL kernel shape (a declared printf-style
    # fn, gcc rc0; gcc REJECTS it on an int param — measured), section
    both_run("""
__attribute__((format(printf, 1, 2))) int my_printf(const char *fmt, ...);
__attribute__((section(".data.once"))) int once_slot = 7;
int main(void) { return once_slot - 7; }
""", "attr-args")


def test_attr_after_brace_on_typedef_run_pair():
    both_run("""
typedef struct { int a; char b; } pair_t __attribute__((may_alias));
static pair_t p;
int main(void) { p.a = 4; p.b = 1; return p.a - 4; }
""", "attr-typedef")


def test_attr_in_params_and_stmt_expr_run_pair():
    both_run("""
static int add(int a, int b __attribute__((unused))) { return a + b; }
int main(void) {
    int r = ({ __attribute__((unused)) int t = add(2, 3); t; });
    return r - 5;
}
""", "attr-param")


def test_compiletime_error_attr_shape_parses_strips_run_pair():
    # §2.9: the error attr rides DECLARATIONS only referenced in a FALSE
    # compile-time case; parse+strip. gcc twin (rc0, unreferenced).
    both_run("""
__attribute__((error("boom"))) extern int unreferenced_check;
int main(void) { return 0; }
""", "attr-cte")


def test_attr_on_struct_member_tail_run_pair():
    both_run("""
struct S { int a __attribute__((unused)); char b; };
struct S s;
int main(void) { s.a = 1; return s.a - 1; }
""", "attr-member")


# ---- layout-class: LOUD wall until the M42 layout rule ships (T+10) --------

def test_packed_struct_loud_wall():
    loud("struct P { char c; long l; } __attribute__((packed));\n"
         "int main(void){ return (int)sizeof(struct P); }\n",
         "attr-packed", "packed")


def test_aligned_struct_loud_wall():
    loud("struct A { int a; } __attribute__((aligned(16)));\n"
         "int main(void){ return (int)sizeof(struct A); }\n",
         "attr-aligned", "aligned")
