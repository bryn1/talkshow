"""M54 (§1 row 8, §2.10 lineage): volatile = SUPPORT as accept-and-ignore.
The straight-line stack machine has no reordering to guard against, so the
qualifier is parsed and dropped and the OBSERVABLE behaviour (each access
emitted, in program order) already matches the gcc -Os twin. 356 412 sites
in 688 post-pp files ride this row — the acceptance must never regress.
"""
import os
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

ITMP = os.path.join(ROOT, ".tmp", "itvol")


def both_run(src, tag):
    os.makedirs(ITMP, exist_ok=True)
    p = os.path.join(ITMP, "{}_{}_1".format(tag, os.getpid()))
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


def test_volatile_locals_globals_ptrs_run_pair():
    both_run("""
volatile int g;
struct S { volatile int a; int b; };
struct S s;
int main(void) {
    volatile int v = 3;
    volatile int *p = &g;
    g = v + 1;              /* 4  */
    *p = *p + v;            /* 7  */
    s.a = v; s.b = v + 100;
    if (s.a != 3 || s.b != 103) return 1;
    v = v + 1;              /* volatile local: every access is re-read and
                               re-stored — blcc never caches, so the
                               accept-and-ignore stance IS the semantics */
    if (v != 4) return 2;
    return g - 7;
}
""", "v-acc")


def test_volatile_qualifier_spellings_run_pair():
    both_run("""
int volatile a = 1;               /* trailing spelling */
__volatile__ int b = 2;
static volatile char buf[4];
int main(void) {
    volatile const int c = 3;     /* mixed qualifiers */
    buf[0] = (char)(a + b + c);
    return buf[0] - 6;
}
""", "v-spell")
