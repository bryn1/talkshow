"""M59 (new cycle-2 range) — anonymous nested struct/union members, the
dominant first-blocker of the M2 sweep (300/300 blocked TUs at T+6), + the
§2.8 union-offset pin of the §2.13 fold. MC 12460 stage T+7.

gcc 11.4 -std=gnu89 LAW, re-measured this session (.tmp/m2-scratch/c5/
probes/p_anon.c — compile leg rc0 + RUN rc0, negative legs quoted there):
 - an UNTAGGED inline struct/union definition with no declarator is an
   anonymous MEMBER; its (recursively promoted) names join the enclosing
   struct's member namespace for access, offsetof and layout;
 - a struct/union specifier WITHOUT a declarator that carries a TAG
   (`struct U3 { int q; };`, `struct U6;`) DECLARES NOTHING but the tag
   (gcc "declaration does not declare anything", rc0) — no member, no
   promotion, no size contribution;
 - a member name that collides with any promoted name is gcc ERROR
   "duplicate member 'a'" (rc1) ⇒ blcc §8 LOUD mirror;
 - every union member sits at offset 0 (§2.8) — the offsetof fold mirrors
   it (measured: offsetof(union U, l) == 0; the T+6 fold answered 8 ⇒
   FINDING row in the c2 verdict, oracle wins).
Run legs pair against the gcc 11.4 twin.
"""
import os
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

ITMP = os.path.join(ROOT, ".tmp", "itstruct")


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
    if rg.returncode == 0:
        raise AssertionError("gcc twin must reject ({}):\n{}".format(
            tag, src))
    assert r.returncode == 2, "{}: expected LOUD (exit 2), got {} {}".format(
        tag, r.returncode, r.stderr)
    assert frag in r.stderr, "{}: stderr must name {!r}: {}".format(
        tag, frag, r.stderr)
    os.remove(src_path)


# ---- M59(a): anonymous union over anonymous struct, promoted names --------

ANON_UNION_STRUCT = (
    "struct S1 { union { struct { int a; int b; }; long c; }; int d; };\n"
)


def test_anon_union_over_struct_run_pair():
    # measured RUN (p_anon.c main): union alias + d-isolation ⇒ exit 0
    both_run(ANON_UNION_STRUCT + """
int main(void) {
    struct S1 s;
    s.a = 1; s.b = 2;
    if (s.a != 1 || s.b != 2) return 1;
    s.c = 3;
    if (s.a != 3) return 2;            /* long write aliases a */
    if (s.b != 0) return 3;            /* long write zeroed b   */
    s.d = 42;
    if (s.a != 3 || s.b != 0) return 4;
    return 0;
}
""", "anon-us")


def test_anon_sizeof_offsets_run_pair():
    # measured layout: S1 16 (a@0 b@4 c@0 d@8); S2 24 (x@0 y@8 z@16);
    # S5 24 (arr@0 n@8 tail@16); S4 4 (deep@0)
    both_run(ANON_UNION_STRUCT + """
struct S2 { struct { short x; long y; }; char z; };
struct S4 { union { struct { union { int deep; }; }; }; };
struct S5 { struct { int arr[2]; int n; }; long tail; };
int main(void) {
    long r = 0;
    if (sizeof(struct S1) == 16) r += 1;
    if (__builtin_offsetof(struct S1, a) == 0) r += 2;
    if (__builtin_offsetof(struct S1, b) == 4) r += 4;
    if (__builtin_offsetof(struct S1, c) == 0) r += 8;
    if (__builtin_offsetof(struct S1, d) == 8) r += 16;
    if (sizeof(struct S2) == 24) r += 32;
    if (__builtin_offsetof(struct S2, y) == 8) r += 64;
    if (__builtin_offsetof(struct S2, z) == 16) r += 128;
    if (sizeof(struct S4) == 4) r += 256;
    if (__builtin_offsetof(struct S4, deep) == 0) r += 512;
    if (sizeof(struct S5) == 24) r += 1024;
    if (__builtin_offsetof(struct S5, n) == 8) r += 2048;
    if (__builtin_offsetof(struct S5, tail) == 16) r += 4096;
    if (r != 8191) return 1;
    return 0;
}
""", "anon-size")


def test_anon_deep_write_read_run_pair():
    both_run("""
struct S4 { union { struct { union { int deep; }; long pad; }; }; };
struct S4 g;
int main(void) {
    struct S4 s;
    g.deep = 11;
    s.deep = 22;
    if (g.deep + s.deep != 33) return 1;
    s.pad = 1L << 33;
    if (s.deep != 0) return 2;         /* long write cleared the int half */
    return 0;
}
""", "anon-deep")


def test_anon_promoted_array_and_addressof_run_pair():
    both_run("""
struct S5 { struct { int arr[2]; int n; }; long tail; };
int main(void) {
    struct S5 t; int *pa;
    t.arr[0] = 4; t.arr[1] = 7; t.n = 9;
    if (t.arr[1] != 7 || t.n != 9) return 1;
    pa = &t.n; *pa += 1;
    if (t.n != 10) return 2;
    if (sizeof(((struct S5 *)0)->arr) != 8) return 3;
    return 0;
}
""", "anon-arr")


def test_anon_struct_init_local_and_global_run_pair():
    # positional brace lists: the anonymous member is ONE slot (blcc ships
    # no brace-elision walk; gcc agrees on these explicit shapes)
    both_run("""
struct S2 { struct { short x; long y; }; char z; };
struct S2 g = { { 1, 2 }, 3 };
int main(void) {
    struct S2 l = { { 4, 5 }, 6 };
    if (g.x != 1 || g.y != 2 || g.z != 3) return 1;
    if (l.x != 4 || l.y != 5 || l.z != 6) return 2;
    return 0;
}
""", "anon-init")


# ---- §2.8: union member offsets are 0 — the offsetof fold mirror ----------

def test_union_zero_offset_fold_pair():
    # FINDING c2-F1: the T+6 fold answered offsetof(union U, l) == 8; gcc
    # measures 0 for EVERY union member (§2.8) — oracle wins.
    both_run("""
union U { char c; long l; int arr[3]; };
struct W { union U u; char z; };
int main(void) {
    long r = 0;
    if (__builtin_offsetof(union U, c) == 0) r += 1;
    if (__builtin_offsetof(union U, l) == 0) r += 2;
    if (__builtin_offsetof(union U, arr) == 0) r += 4;
    if (sizeof(union U) == 16) r += 8;
    if (sizeof(struct W) == 16) r += 16;
    if (__builtin_offsetof(struct W, z) == 16) r += 32;
    if (r != 63) return 1;
    return 0;
}
""", "uoff")


# ---- M59(b): tagged specifier with no declarator declares NOTHING ---------

def test_tagged_nested_declares_nothing_run_pair():
    # gcc -std=gnu89: "declaration does not declare anything" rc0 — tag
    # registered (usable later), NO member, NO size contribution (S3==1).
    both_run("""
struct S3 { struct U3 { int q; }; char t; };
struct S6 { struct U6; int v; };
struct U3 later;                        /* the tag IS registered */
int main(void) {
    struct S3 s; struct U3 later2;
    s.t = 5; later.q = 7; later2.q = 1;
    if (sizeof(struct S3) != 1) return 1;
    if (sizeof(struct U3) != 4) return 2;
    if (sizeof(struct S6) != 4) return 3;
    if (__builtin_offsetof(struct S3, t) != 0) return 4;
    if (s.t + later.q + later2.q != 13) return 5;
    return 0;
}
""", "tagdecl")


def test_tagged_nested_promotes_nothing_loud():
    # `struct S3 { struct U3 {…}; char t; };` has NO member q (measured
    # gcc error: 'struct S3' has no member named 'q')
    both_loud("struct S3 { struct U3 { int q; }; char t; };\n"
              "int main(void){ struct S3 s; s.q = 1; return s.q; }\n",
              "tag-no-promo", "no member 'q'")


# ---- M59(c): duplicate promoted names are LOUD (measured gcc error) -------

def test_duplicate_member_anon_vs_plain_loud():
    both_loud("struct S { struct { int a; }; int a; };\n"
              "int main(void){ return 0; }\n",
              "dup-anon-plain", "duplicate member 'a'")


def test_duplicate_member_two_anons_loud():
    both_loud("struct S { struct { int a; }; union { int a; }; };\n"
              "int main(void){ return 0; }\n",
              "dup-anon-anon", "duplicate member 'a'")


def test_duplicate_member_plain_pair_loud():
    both_loud("struct S { int a; int a; };\n"
              "int main(void){ return 0; }\n",
              "dup-plain", "duplicate member 'a'")


def test_same_member_name_in_two_structs_ok():
    both_run("struct A { struct { int a; }; };\n"
             "struct B { struct { union { int a; }; }; };\n"
             "int main(void){ struct A x; struct B y;\n"
             "  x.a = 1; y.a = 2;\n"
             "  if (x.a + y.a != 3) return 1;\n"
             "  return 0; }\n",
             "dup-ok-across")


def test_cross_level_promoted_collision_loud():
    # gcc measures: a name promoted to B's level COLLIDES with B's own
    # member of that name — duplicate member 'a', rc1 (dup2 probe).
    both_loud("struct B { int a; struct { union { int a; }; }; };\n"
              "int main(void){ return 0; }\n",
              "dup-cross-level", "duplicate member 'a'")


# ---- M59(d): tag-namespace uniqueness — two inline defs on ONE line -------

def test_two_anon_defs_same_line_run_pair():
    # tags are minted unique, not per file:line (the kernel's post-pp
    # streams put whole structs on single lines)
    both_run("struct S { struct { int a; } x; struct { int b; } y; };\n"
             "int main(void){ struct S s; s.x.a = 1; s.y.b = 2;\n"
             "  if (s.x.a + s.y.b != 3) return 1;\n"
             "  return 0; }\n", "same-line")


# ---- sweep-witness regression: the ftrace_branch_data shape ---------------

def test_ftrace_branch_shape_run_pair():
    both_run("""
struct ftrace_branch_data {
    const char *func;
    const char *file;
    unsigned line;
    union {
        struct {
            unsigned long correct;
            unsigned long incorrect;
        };
        struct {
            unsigned long miss;
            unsigned long hit;
        };
        unsigned long miss_hit[2];
    };
};
int main(void) {
    struct ftrace_branch_data f;
    f.correct = 3; f.incorrect = 4;
    if (f.miss_hit[0] == 0) return 1;          /* aliasing: not zero */
    f.miss = 10; f.hit = 20;
    if (f.correct != 10 || f.incorrect != 20) return 2;
    return 0;
}
""", "ftrace-shape")
