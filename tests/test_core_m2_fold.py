"""M49 (part) — __builtin_constant_p (§2.11) and __builtin_offsetof
(§2.13) folds, MC 12460. The §2.11 no-lie table is LAW: blcc answers 1
only for the classes gcc answers 1 at EVERY level (constant closure +
string literals), 0 everywhere else. Run legs pair against gcc 11.4; the
fold-in-array-size legs pin that the answer is a COMPILE-TIME int.
"""
import os
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

ITMP = os.path.join(ROOT, ".tmp", "itfold")


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
    assert rb.returncode == 0, "blcc compile failed ({}):\n{}".format(
        tag, rb.stderr)
    if rg.returncode != 0:
        raise AssertionError(
            "gcc twin must build ({}) rc{}:\n{}".format(
                tag, rg.returncode, rg.stderr))
    pb = subprocess.run([out_b], capture_output=True, timeout=30)
    pg = subprocess.run([out_g], capture_output=True, timeout=30)
    assert (pb.returncode, pb.stdout) == (pg.returncode, pg.stdout), \
        "run-pair mismatch ({}): blcc={} gcc={}".format(
            tag, (pb.returncode, pb.stdout), (pg.returncode, pg.stdout))
    for f in (src_path, out_b, out_g):
        os.remove(f)


def both_loud(src, tag, frag):
    """gcc must REJECT (rc!=0) AND blcc must §8-LOUD (rc2) with frag."""
    p = _fresh(tag)
    src_path = p + ".c"
    with open(src_path, "w", encoding="utf-8") as fh:
        fh.write(src)
    rg = subprocess.run(["gcc", "-w", "-std=gnu89", "-O0", "-c", "-o",
                         "/dev/null", src_path],
                        capture_output=True, text=True, timeout=60)
    r = subprocess.run([sys.executable, "-m", "blcc", src_path,
                        "-o", p + ".out"], cwd=ROOT, capture_output=True,
                       text=True, timeout=60)
    os.remove(src_path)
    assert rg.returncode != 0, "oracle must reject the twin too: " + \
        rg.stdout + rg.stderr
    assert r.returncode == 2, \
        "expected LOUD rc2, got {}:\n{}".format(r.returncode, r.stderr)
    assert frag in r.stderr, "diagnostic must name {!r}: {}".format(
        frag, r.stderr)


# ---- §2.11 constant_p --------------------------------------------------------

def test_cp_true_classes_run_pair():
    # Weights 1/2/4/8/16/32/64/128: every class is mod-256 distinguishable.
    both_run("enum MYENUM { M7 = 7 };\n"
             "#define TWENTY 20\n"
             "int main(void) {\n"
             "  return __builtin_constant_p(5)\n"
             "    + 2*__builtin_constant_p('c')\n"
             "    + 4*__builtin_constant_p(0xFF)\n"
             "    + 8*__builtin_constant_p(\"s\")\n"
             "    + 16*__builtin_constant_p(M7)\n"
             "    + 32*__builtin_constant_p(TWENTY)\n"
             "    + 64*__builtin_constant_p(3+4*2)\n"
             "    + 128*__builtin_constant_p(sizeof(int));\n"
             "}\n", "cp-true")   # gcc -O0: all 1 ⇒ exit 255


def test_cp_false_classes_run_pair():
    both_run("int glob = 3;\nint arr[8];\n"
             "long probe(int x) {\n"
             "  return __builtin_constant_p(x) + __builtin_constant_p(glob)\n"
             "    + __builtin_constant_p(glob+1) + __builtin_constant_p(&arr[3]);\n"
             "}\n"
             "int main(void) { return (int)probe(9); }\n", "cp-false")


def test_cp_static_known_scope_run_pairs():
    # §2.11 scope footnote: blcc answers 0 in BOTH scopes (no-lie rule).
    both_run("static int sg = 3;\nint fsa[__builtin_constant_p(sg) + 1];\n"
             "int in_body(void) { return __builtin_constant_p(sg); }\n"
             "int main(void) { return in_body() + sizeof(fsa) - 1; }\n",
             "cp-scope")   # 0 + 2 - 1 = 1 both


def test_cp_fold_in_array_size_pair():
    both_run("char a2[__builtin_constant_p(5) + 1];\n"
             "int main(void) { return (int)sizeof(a2) - 2; }\n", "cp-arr")


def test_cp_neg_size_loud_twin():
    # __builtin_constant_p(g) ⇒ 0 ⇒ size 0-1: blcc's existing §8 gate
    # ("array size must be positive (§4)"); gcc rc1 twin reject.
    both_loud("int g;\nchar a[__builtin_constant_p(g) - 1];\n"
              "int main(void){ return 0; }\n", "cp-neg", "positive")


def test_cp_arity_loud():
    both_loud("int main(void){ return __builtin_constant_p(1,2); }\n",
              "cp-arity", "__builtin_constant_p")


# ---- §2.13 offsetof ----------------------------------------------------------

def test_offsetof_run_pair():
    both_run("struct S { char c; long l; int i; };\n"
             "int main(void) {\n"
             "  long r = 0;\n"
             "  if (__builtin_offsetof(struct S, c) == 0) r += 1;\n"
             "  if (__builtin_offsetof(struct S, l) == 8) r += 2;\n"
             "  if (__builtin_offsetof(struct S, i) == 16) r += 4;\n"
             "  if (__builtin_offsetof(struct S, i) + 1 == 17) r += 8;\n"
             "  return (int)r;\n"
             "}\n", "off-plain")   # exit 15


def test_offsetof_typedef_and_size_legs_pair():
    both_run("struct S { char c; long l; int i; };\n"
             "typedef struct S T;\n"
             "char ob[__builtin_offsetof(T, l) + 1];   /* size 9 */\n"
             "int main(void) {\n"
             "  if (__builtin_offsetof(T, l) != 8) return 1;\n"
             "  return (int)sizeof(ob) - 9;\n"
             "}\n", "off-td")


def test_offsetof_member_chain_pair():
    both_run("struct S { char c; long l; int i; };\n"
             "struct A { char pad[3]; struct S s; long q[2]; };\n"
             "int main(void) {\n"
             "  long r = 0;\n"
             "  if (__builtin_offsetof(struct A, s) == 8) r += 1;\n"
             "  if (__builtin_offsetof(struct A, q[1]) == 40) r += 2;\n"
             "  return (int)r;\n"
             "}\n", "off-chain")   # exit 3


def test_offsetof_bad_member_loud():
    both_loud("struct S { char c; };\n"
              "int main(void){ return __builtin_offsetof(struct S, zzz); }\n",
              "off-zzz", "zzz")


def test_offsetof_bitfield_loud_mirror():
    # §2.13: bitfield member = gcc ERROR ⇒ blcc LOUD mirror, never a number.
    both_loud("struct B { int a : 3; };\n"
              "int main(void){ return __builtin_offsetof(struct B, a); }\n",
              "off-bit", "bit")
