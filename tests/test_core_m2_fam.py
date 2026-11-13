"""§1 row 13 (M46): flexible array members — MC 12460 build cycle 3.

Law measured this session against gcc 11.4.0 -std=gnu89 -Os
(.tmp/m2-scratch/c6/probes, FAM section):
  * sizeof(struct-with-FAM) is the HEADER only (the member spans 0);
  * offsetof(S, fam) = the header end aligned to the ELEMENT's alignment
    (FD {int; double v[]} -> 8, align 8 — the element align joins the
    struct's alignment); FS {char c; char v[]} -> offsetof 1, sizeof 1;
  * &p->v and p->v[i] address normally; the legacy `int v[0];` spelling
    is a COMPLETED zero-size array (member sizeof == 0, rc0) while a
    real `v[]` member sizeof is a gcc ERROR (incomplete type);
  * the FAM must be the LAST member, never in a union, never alone
    (gcc "structure has no members");
  * a global with a value beyond the header is emitted by gcc BEYOND
    sizeof — DEFERRED LOUD here (§5); `{ 9 }` header init is fine.
"""
import os
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TMP = os.path.join(ROOT, ".tmp", "itfam")
_seq = [0]


def _paths(tag):
    os.makedirs(TMP, exist_ok=True)
    _seq[0] += 1
    base = os.path.join(TMP, "fam_{}_{}_{}".format(tag, os.getpid(), _seq[0]))
    return base + ".c", base + ".blcc", base + ".gcc"


def both_run(src, tag):
    """Run-pair: blcc binary vs gcc -w -std=gnu89 -O0 binary, compare
    (exitcode, stdout) — the shipped M2 witness mechanism."""
    src_path, b_out, g_out = _paths(tag)
    with open(src_path, "w", encoding="utf-8") as fh:
        fh.write(src)
    rb = subprocess.run([sys.executable, "-m", "blcc", src_path,
                         "-o", b_out], cwd=ROOT, capture_output=True,
                        text=True, timeout=60)
    try:
        assert rb.returncode == 0, \
            "blcc compile failed ({}):\n{}".format(tag, rb.stderr)
        rg = subprocess.run(["gcc", "-w", "-std=gnu89", "-O0", src_path,
                             "-o", g_out], capture_output=True, text=True,
                            timeout=60)
        assert rg.returncode == 0, "gcc twin must build ({}):\n{}".format(
            tag, rg.stderr)
        pb = subprocess.run([b_out], capture_output=True, timeout=30)
        pg = subprocess.run([g_out], capture_output=True, timeout=30)
        assert (pb.returncode, pb.stdout) == (pg.returncode, pg.stdout), \
            "run-pair mismatch ({}): blcc={} gcc={}".format(
                tag, (pb.returncode, pb.stdout), (pg.returncode, pg.stdout))
    finally:
        for p in (src_path, b_out, g_out):
            if os.path.exists(p):
                os.remove(p)


def blcc_loud(src, tag, family="sema", needle=None):
    src_path, b_out, _ = _paths(tag)
    with open(src_path, "w", encoding="utf-8") as fh:
        fh.write(src)
    try:
        rb = subprocess.run([sys.executable, "-m", "blcc", src_path,
                             "-o", b_out], cwd=ROOT, capture_output=True,
                            text=True, timeout=60)
        assert rb.returncode == 2, \
            "{} must LOUD, rc={}\n{}".format(tag, rb.returncode, rb.stderr)
        assert ": {}:".format(family) in rb.stderr, \
            "{} landed outside the {} family:\n{}".format(
                tag, family, rb.stderr)
        if needle is not None:
            assert needle in rb.stderr, \
                "{} must name {!r}:\n{}".format(tag, needle, rb.stderr)
    finally:
        for p in (src_path, b_out):
            if os.path.exists(p):
                os.remove(p)


# ---------------------------------------------------------------- law legs

def test_fam_sizeof_offsetof_run_pair():
    # Measured: F1 sizeof 4 offsetof(v) 4; FD {int;double v[]} off 8 al 8
    # (element align joins the struct); FS {char c; char v[]} sizeof 1
    # off 1; the legacy v[0] is a completed 0-size array (member sizeof 0).
    both_run("""
struct F1 { int n; int v[]; };
struct FD { int n; double v[]; };
struct FS { char c; char v[]; };
struct L0 { int n; int z[0]; };
struct PadFD { char c; struct FD s; };
int main(void) {
    struct L0 l;
    if (sizeof(struct F1)  != 4) return 1;
    if (__builtin_offsetof(struct F1, v) != 4) return 2;
    if (sizeof(struct FD)  != 8) return 3;   /* element align rounds up */
    if (__builtin_offsetof(struct FD, v) != 8) return 4;
    if (sizeof(struct PadFD) != 16) return 5;/* FD align 8 in a char pad */
    if (sizeof(struct FS)  != 1) return 6;
    if (__builtin_offsetof(struct FS, v) != 1) return 7;
    if (sizeof(struct L0)  != 4) return 8;
    if (sizeof(l.z)        != 0) return 9;   /* legacy v[0]: COMPLETED */
    if (__builtin_offsetof(struct L0, z) != 4) return 10;
    return 0;
}
""", "sz")


def test_fam_address_and_index_run_pair():
    # &p->v rc0 measured; p->v[i] indexes past the header into whatever
    # storage backs it — an over-allocated static arena is the honest
    # subset witness (no malloc). arena layout: n at 0..3, v[0] at 4.
    both_run("""
struct F1 { int n; int v[]; };
static int arena[16];
int main(void) {
    struct F1 *p;
    p = (struct F1 *)arena;
    p->n = 3;
    p->v[0] = 10; p->v[1] = 20; p->v[3] = 30;
    if (arena[0] != 3) return 1;             /* header shares storage */
    if (arena[1] != 10) return 2;
    if (arena[4] != 30) return 3;
    if (p->v[3] != 30) return 4;
    if (p->v != arena + 1) return 5;         /* &v = header end */
    { struct F1 s;                       /* dot through an object sized */
      s.n = 1;                           /* by hand: reuse p semantics */
      if (__builtin_offsetof(struct F1, v) != 4) return 6; }
    return 0;
}
""", "addr")


def test_fam_array_of_headers_run_pair():
    # Array of FAM structs: stride == sizeof(header) (measured rc0) —
    # tab[2].v[0] SHARES tab[3].n's word. Pin the aliasing: writing the
    # last row's v[0] lands exactly in the row-end header slot.
    both_run("""
struct F1 { int n; int v[]; };
struct F1 tab[4];
int main(void) {
    int i;
    for (i = 0; i < 4; i++) tab[i].n = i + 1;
    if (sizeof(tab) != 16) return 1;
    tab[2].v[0] = 99;                    /* aliases tab[3].n */
    if (tab[3].n != 99) return 2;
    tab[3].n = 4;
    if (tab[2].v[0] != 4) return 3;
    return 0;
}
""", "arr")


def test_fam_nested_run_pair():
    # Measured H { struct F1 f; int z; } rc0, sizeof 8, z at 4: the
    # embedded FAM aggregate contributes only its header.
    both_run("""
struct F1 { int n; int v[]; };
struct H { struct F1 f; int z; };
struct H h;
int main(void) {
    if (sizeof(struct H) != 8) return 1;
    if (__builtin_offsetof(struct H, z) != 4) return 2;
    h.f.n = 5; h.z = 6;
    if (h.f.n != 5 || h.z != 6) return 3;
    if (h.f.v != &h.z) return 4;          /* f.v shares the z slot */
    *h.f.v = 7;
    if (h.z != 7) return 5;
    return 0;
}
""", "nest")


def test_fam_bss_zero_run_pair():
    both_run("""
struct F1 { int n; int v[]; };
struct F1 g;
int main(void) {
    if (g.n != 0) return 1;
    g.n = 2;
    if (g.n != 2) return 2;
    return 0;
}
""", "bss")


# ---------------------------------------------------------------- LOUD legs

def test_fam_not_last_is_loud():
    blcc_loud("""
struct S { int a; char v[]; int b; };
int main(void) { return 0; }
""", "fam-last", needle="not at the end")


def test_fam_in_union_is_loud():
    blcc_loud("""
union U { int n; char v[]; };
int main(void) { return 0; }
""", "fam-union", needle="in a union")


def test_fam_alone_is_loud():
    blcc_loud("""
struct S { int v[]; };
int main(void) { return 0; }
""", "fam-alone", needle="named member")


def test_fam_member_sizeof_is_loud():
    # gcc ERROR: invalid application of sizeof to incomplete type — the
    # v[0] legacy spelling (completed, member sizeof 0) is the run-pair
    # sibling pinned in test_fam_sizeof_offsetof_run_pair.
    blcc_loud("""
struct S { int n; char v[]; };
struct S s;
int main(void) { return (int)sizeof(s.v); }
""", "fam-szof", needle="flexible array")


def test_fam_value_initializer_is_loud():
    # gcc EMITS bytes beyond sizeof for a supplied FAM (measured .data
    # 01000000 0203) — §5 DEFERRAL here; the header-only init survives.
    blcc_loud("""
struct S { int n; int v[]; };
struct S s = { 9, 2 };
int main(void) { return s.n; }
""", "fam-init")
