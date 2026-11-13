"""M42 — layout-class attributes ACT (§1 row 9: packed/aligned are not
ignore-class; §5 wall retires here). gcc 11.4 -std=gnu89 pins every
offset/size run-pair. aligned_with: 0 sites in the whole 5.10 tree
(grep-measured) — it stays the LOUD wall, pinned as the NEG leg.
"""
import os
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

ITMP = os.path.join(ROOT, ".tmp", "itlay")


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


def test_packed_layout_run_pair():
    both_run("""
struct S { char c; int i; char d; };
struct P { char c; int i; char d; } __attribute__((packed));
int main(void) {
    if (sizeof(struct S) != 12) return 1;
    if (sizeof(struct P) != 6) return 2;
    struct P p; p.c = 1; p.i = 0x02030405; p.d = 6;
    char *b = (char *)&p;
    if (b[0] != 1 || b[1] != 0x05 || b[2] != 0x04 || b[3] != 0x03
        || b[4] != 0x02 || b[5] != 6) return 3;
    if (p.i != 0x02030405) return 4;
    return 0;
}
""", "l-packed")


def test_packed_offsetof_fold_run_pair():
    # the §2.13 fold walks the SAME layout (mut-oflo2 class)
    both_run("""
struct P { char c; int i; char d; } __attribute__((packed));
int main(void) {
    if (__builtin_offsetof(struct P, i) != 1
        || __builtin_offsetof(struct P, d) != 5) return 1;
    struct P p; char *b = (char *)&p;
    if ((char*)&p.i - b != 1 || (char*)&p.d - b != 5) return 2;
    return 0;
}
""", "l-oflo")


def test_aligned_struct_run_pair():
    both_run("""
struct D { int x; } __attribute__((__aligned__(64)));
int main(void) {
    struct D arr[2];
    if (sizeof(struct D) != 64) return 1;
    if ((char*)&arr[1] - (char*)&arr[0] != 64) return 2;
    arr[1].x = 7;
    if (arr[1].x != 7) return 3;
    return 0;
}
""", "l-aligned")


def test_aligned_member_run_pair():
    both_run("""
struct A { char c; int i __attribute__((aligned(8))); char z; };
int main(void) {
    if (sizeof(struct A) != 16) return 1;
    struct A a; char *b = (char *)&a;
    if ((char*)&a.i - b != 8) return 2;
    if ((char*)&a.z - b != 12) return 3;
    return 0;
}
""", "l-memb")


def test_typedef_tail_packed_run_pair():
    both_run("""
typedef struct { unsigned a; unsigned long b; unsigned c; }
    __attribute__((packed)) pt_t;
int main(void) {
    if (sizeof(pt_t) != 16) return 1;
    pt_t p; char *b = (char *)&p;
    p.a = 1; p.b = 2; p.c = 3;
    if ((char*)&p.b - b != 4 || (char*)&p.c - b != 12) return 2;
    if (b[4] != 2 || b[12] != 3) return 3;
    return 0;
}
""", "l-td")


def test_packed_union_and_nested_run_pair():
    both_run("""
union U { char c[3]; int i; } __attribute__((packed));
struct N { char t; struct { char a; int b; } __attribute__((packed)) in;
           short s; } __attribute__((packed));
int main(void) {
    if (sizeof(union U) != 4) return 1;   /* packed drops ALIGNMENT, not the int's 4 bytes */
    if (sizeof(struct N) != 8) return 2;
    struct N n; char *b = (char *)&n;
    n.t = 1; n.in.a = 2; n.in.b = 0x03040506; n.s = 0x0708;
    if ((char*)&n.in - b != 1) return 3;
    if ((char*)&n.in.b - b != 2) return 4;
    if ((char*)&n.s - b != 6) return 5;
    if (b[2] != 0x06 || b[5] != 0x03) return 6;
    return 0;
}
""", "l-nest")


def test_packed_global_init_designators_run_pair():
    both_run("""
struct P { char c; int i; char d; } __attribute__((packed));
struct P g = { .i = 0x0a0b0c0d, 1 };
int main(void) {
    char *b = (char *)&g;
    if (sizeof(g) != 6) return 1;
    if (b[0] != 0) return 2;             /* positional resumes AFTER .i */
    if (g.i != 0x0a0b0c0d) return 3;
    if (b[5] != 1) return 4;             /* the 1 landed in .d */
    return 0;
}
""", "l-desig")


def test_packed_in_array_and_ptr_run_pair():
    both_run("""
struct P { char c; int i; } __attribute__((packed));
struct P tab[3] = { { 1, 10 }, { 2, 20 }, { 3, 30 } };
int main(void) {
    if (sizeof(tab) != 15) return 1;
    if ((char*)&tab[1] - (char*)&tab[0] != 5) return 2;
    if (tab[2].i != 30) return 3;
    struct P *p = &tab[0];
    p[1].i = 21;
    if (tab[1].i != 21) return 4;
    return 0;
}
""", "l-arr")


def test_aligned_with_stays_wall():
    # 0 sites in the whole 5.10 tree (grep-measured) — honest LOUD class.
    loud("struct A { int x; };\n"
         "struct B { int y; } __attribute__((aligned_with(A)));\n"
         "int main(void){ return 0; }\n", "l-aw", "aligned_with")
