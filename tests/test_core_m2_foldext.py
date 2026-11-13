"""T+10b — constant-fold closure for the classes the §1 row 10 walk
exposed BEHIND the fn-ptr wall (corpus witnesses, re-measured at head):
  inat.c   `const insn_attr_t tab[256] = { [0x00] = (1 << ...), … }`
  idt_64   enum/`<<` initializers          mmap.c  VM-flag `|` ORs
  `int * const` / `int const *` — qualifiers on either side of every `*`
(kernel style; the same walk exposed the missing declarator arms).
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


def test_enum_and_case_shift_bitwise_run_pair():
    both_run("""
enum { A = (1 << 3) | 2, B = ~(1 << 0) & ~7, C = 1 << 30 };
int cls(int x) {
    switch (x) {
    case A | 16: return 1;
    case (1 << 8): return 2;
    default: return 0;
    }
}
int main(void) {
    if (A != 10) return 1;
    if (B != -8) return 2;                    /* ~1 & ~7 = -2 & -8 = -8 */
    if (C != 1073741824) return 3;            /* (1<<31 is UB-fold width
        territory: kernel text uses 1UL — noted in the verdict) */
    if (cls(26) != 1 || cls(256) != 2 || cls(3) != 0) return 4;
    return 0;
}
""", "f-enum")


def test_global_init_shift_or_table_run_pair():
    # inat_primary_table shape: designated CONST-size table of (1 << N)
    both_run("""
typedef unsigned int attr_t;
const attr_t tab[4] = { [0] = (1 << 12), [1] = (1 << 13), 0,
                        [3] = (1 << 12) | (1 << 0) };
unsigned long flags = (1UL << 20) | (1UL << 0);
int main(void) {
    if (tab[0] != 4096 || tab[1] != 8192) return 1;
    if (tab[2] != 0 || tab[3] != 4097) return 2;
    if (flags != 1048577UL) return 3;
    return 0;
}
""", "f-glob")


def test_star_qualified_declarators_run_pair():
    both_run("""
int g = 3;
int * const p = &g;
int const * const q = &g;
int const r = 4;
int main(void) {
    int const * s = &r;
    if (*p != 3 || *q != 3 || r != 4 || *s != 4) return 1;
    *p = 5;                        /* the POINTER is const, target is not */
    if (g != 5) return 2;
    return 0;
}
""", "f-star")


def test_const_array_of_ptrs_designated_run_pair():
    # inat_escape_tables shape: [i][j] designators over a pointer matrix
    both_run("""
int t1[2] = { 1, 2 };
int t2[2] = { 3, 4 };
const int * const tables[2][2] = { [0][1] = t2, [1][0] = t1 };
int main(void) {
    if (tables[0][1][0] != 3 || tables[1][0][1] != 2) return 1;
    if (tables[0][0] != 0 || tables[1][1] != 0) return 2;   /* zero gaps */
    return 0;
}
""", "f-arr")


def test_register_keyword_run_pair():
    # M47 keyword row: bare `register` is a hint — it parses and drops
    # (blcc is a stack machine: no allocation choice exists to make).
    both_run("""
int f(void) {
    register int y = 2;            /* gnu89: address-of-register = gcc ERROR
                                      (measured rc1) — trees never take it;
                                      blcc's stack machine treats register
                                      as a hint and does not implement the
                                      error side (documented laxness). */
    return y + 7;
}
int main(void) {
    register int x;
    x = 4;
    register long z = x + f();
    if (z != 13) return 1;
    return (int)z - 13;
}
""", "g-register")
