"""M43 — designated initializers (§1 row 10, raw census 328/692 files):
`.field =`, `[i] =`, nested/brace-elided paths, ranges `[a ... b] =`,
OUT-OF-ORDER + re-designation, designators into ANONYMOUS-member promoted
names (rides the T+7 promotion), union member designators, at BOTH file
scope (data.py bytes) and block scope (zero-fill law: members the init
does not mention are ZERO, gcc-measured — this leg also closes a latent
gap: local positional inits used to leave unmentioned members uninitialised).
gcc 11.4 -std=gnu89 twin on every leg (GNU C89 accepts designated inits).
"""
import os
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

ITMP = os.path.join(ROOT, ".tmp", "itdesig")


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


def test_struct_field_and_positional_mix_run_pair():
    # MEASURED gnu89: the positional run RESUMES AFTER the designated
    # member (`{ .b = 7, 10 }` puts 10 in .c); members the init does not
    # mention are ZERO.
    both_run("""
struct S { int a; char b; int c; };
struct S sg = { .c = 3 };
int main(void) {
    struct S sl = { .b = 7, 10 };
    if (sg.a != 0 || sg.b != 0 || sg.c != 3) return 1;
    if (sl.a != 0 || sl.b != 7 || sl.c != 10) return 2;
    return 0;
}
""", "d-mix")


def test_excess_elements_stays_loud_wall():
    # the shipped §4 stricter-than-gcc wall (data/codegen "too many
    # initializers"): an EXCESS positional after the last slot is LOUD.
    loud("struct S { int a; }\nstruct S s = { .a = 1, 2 };\n"
         "int main(void){ return s.a; }\n", "d-excess", "excess")


def test_array_indexed_out_of_order_and_gaps_run_pair():
    both_run("""
int g[4] = { [2] = 5, [0] = 1 };
int main(void) {
    int l[5] = { [4] = 9, [1] = 2, 3 };   /* resumes at 2 after [1]=2? NO:
        after [1] the next positional lands at 2 (=3); 0 and 3 are ZERO */
    if (g[0]!=1 || g[1]!=0 || g[2]!=5 || g[3]!=0) return 1;
    if (l[0]!=0 || l[1]!=2 || l[2]!=3 || l[3]!=0 || l[4]!=9) return 2;
    return 0;
}
""", "d-arr")


def test_unsized_array_from_max_designator_run_pair():
    both_run("""
int a[] = { [3] = 8, [1] = 2 };
int main(void) {
    if (sizeof(a) != 16) return 1;
    if (a[0]!=0 || a[1]!=2 || a[2]!=0 || a[3]!=8) return 2;
    return 0;
}
""", "d-unsized")


def test_range_designator_run_pair():
    both_run("""
int r[6] = { [1 ... 3] = 7, 1 };
int main(void) {
    /* [1..3]=7; then positional resumes at 4: r[4]=1; r[0]=r[5]=0 */
    if (r[0]!=0 || r[1]!=7 || r[2]!=7 || r[3]!=7 || r[4]!=1 || r[5]!=0)
        return 1;
    return 0;
}
""", "d-range")


def test_nested_braces_and_elided_path_run_pair():
    both_run("""
struct A { int x; int y; };
struct T { struct A a; int z; };
struct T t1 = { .a = { .y = 6 }, .z = 9 };
struct T t2 = { .a.x = 1, .a.y = 2, 3 };      /* brace-elided path */
int main(void) {
    if (t1.a.x != 0 || t1.a.y != 6 || t1.z != 9) return 1;
    if (t2.a.x != 1 || t2.a.y != 2 || t2.z != 3) return 2;
    return 0;
}
""", "d-nest")


def test_anon_promoted_designator_run_pair():
    both_run("""
union U { struct { int p; int q; }; long v; };
union U u1 = { .q = 9 };
union U u2 = { .v = 0x11 };
struct W { int head; union { char c; long l; }; int tail; };
struct W w = { .head = 1, .c = 2, .tail = 3 };
int main(void) {
    if (u1.v != ((long)9 << 32)) return 1;
    if (u2.v != 0x11) return 2;
    if (w.head != 1 || w.c != 2 || w.l != 2 || w.tail != 3) return 3;
    return 0;
}
""", "d-anon")


def test_union_member_designator_zero_rest_run_pair():
    both_run("""
union V { char c; long v; };
union V a = { .c = 1 };
union V b = { .v = 2 };
int main(void) {
    if (a.c != 1 || a.v != 1) return 1;
    if (b.c != 2 || b.v != 2) return 2;
    return 0;
}
""", "d-union")


def test_designated_array_of_structs_run_pair():
    both_run("""
struct P { int lo; int hi; };
struct P tab[3] = { [0].hi = 5, [2] = { 7, 8 }, [1].lo = 1 };
int main(void) {
    if (tab[0].lo != 0 || tab[0].hi != 5) return 1;
    if (tab[1].lo != 1 || tab[1].hi != 0) return 2;
    if (tab[2].lo != 7 || tab[2].hi != 8) return 3;
    return 0;
}
""", "d-arrstruct")


def test_redesignation_last_wins_run_pair():
    both_run("""
int q[] = { [0] = 1, [0] = 2, 3 };
int main(void) {
    if (q[0] != 2) return 1;
    if (q[1] != 3) return 2;   /* resume after the re-designated slot */
    return 0;
}
""", "d-redesig")


def test_local_missing_members_zero_run_pair():
    # closes the latent local-zero-fill gap: positional too
    both_run("""
struct Big { int a[4]; char c; long l; };
int main(void) {
    struct Big b = { {1}, 2 };
    if (b.a[0] != 1 || b.a[1] || b.a[2] || b.a[3]) return 1;
    if (b.c != 2 || b.l != 0) return 2;
    return 0;
}
""", "d-zerofill")


def test_bad_field_designator_loud():
    loud("struct S { int a; };\nstruct S s = { .zz = 1 };\n"
         "int main(void){ return s.a; }\n", "d-badfield", "'zz'")


def test_nonconst_array_designator_loud():
    loud("int main(void) { int n = 2; int a[3] = { [n] = 5 }; return a[0]; }\n",
         "d-nonconst", "constant")
