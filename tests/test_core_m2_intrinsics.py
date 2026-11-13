"""M49-misc (§1 row 19): the small GCC intrinsic family. Contracts were
re-measured at this head with the gcc 11.4 -std=gnu89 -Os twin; each leg is
oracle-pinned first (heredoc loop), then pinned here as a run-pair (or a
loud wall for the §5-deferred arms).
"""
import os
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

ITMP = os.path.join(ROOT, ".tmp", "itmix")


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


def loud(src, tag, needle):
    p = _fresh(tag)
    src_path = p + ".c"
    with open(src_path, "w", encoding="utf-8") as fh:
        fh.write(src)
    r = subprocess.run([sys.executable, "-m", "blcc", src_path, "-o",
                        p + ".out"], cwd=ROOT, capture_output=True, text=True,
                       timeout=60)
    assert r.returncode == 2, (tag, r.returncode, r.stderr)
    assert needle in r.stderr, (tag, r.stderr)
    os.remove(src_path)


def test_bswap_run_pair():
    both_run("""
unsigned short a16; unsigned int a32; unsigned long a64;
int main(void) {
    if (__builtin_bswap16(0x1234) != 0x3412) return 1;
    if (__builtin_bswap32(0x12345678u) != 0x78563412u) return 2;
    if (__builtin_bswap64(0x0102030405060708UL) != 0x0807060504030201UL)
        return 3;
    a16 = 0x00ff; a32 = 0x00000100u; a64 = 0x100UL;
    if (__builtin_bswap16(a16) != 0xff00) return 4;
    if (__builtin_bswap32(a32) != 0x00010000u) return 5;
    if (__builtin_bswap64(a64) != 0x0001000000000000UL) return 6;
    return 0;
}
""", "x-bswap")


def test_ctz_clz_run_pair():
    both_run("""
unsigned long v = 1UL << 40;
int main(void) {
    if (__builtin_ctz(1u << 7) != 7) return 1;
    if (__builtin_ctz(0x80000000u) != 31) return 2;
    if (__builtin_ctzll(1ULL << 40) != 40) return 3;
    if (__builtin_ctzll(v) != 40) return 4;
    if (__builtin_clz(1u) != 31) return 5;
    if (__builtin_clz(0x80000000u) != 0) return 6;
    if (__builtin_clzll(1ULL << 60) != 3) return 7;
    return 0;
}
""", "x-ctz")


def test_unreachable_prefetch_run_pair():
    both_run("""
char buf[8];
int cls(int x) {
    if (x > 0) return 1;
    if (x < 0) return 2;
    __builtin_unreachable();
}
int main(void) {
    __builtin_prefetch(buf + 1, 0, 3);
    __builtin_prefetch(buf + 2);
    if (cls(3) != 1 || cls(-3) != 2) return 1;
    return 0;
}
""", "x-unr")


def test_frame_return_address_run_pair():
    # §1 row 19: level 0 only. The property pinned (gcc AND blcc frame
    # model): the slot just above the saved frame pointer IS the return
    # address, so frame_address(0)[1] == return_address(0) and the two
    # are distinct from the frame pointer itself.
    both_run("""
int check(void) {
    unsigned long *f = (unsigned long *)__builtin_frame_address(0);
    if (f[1] != (unsigned long)__builtin_return_address(0)) return 1;
    if ((unsigned long)__builtin_return_address(0) == (unsigned long)f)
        return 2;
    if (f[1] == 0) return 3;
    return 0;
}
int main(void) { return check(); }
""", "x-addr")


def test_extract_return_addr_identity_run_pair():
    # gcc 11.4 measured at -Os: __builtin_extract_return_addr(x) IS x
    # (movq %rdi,%rax); on x86-64 the canonicalization is the identity.
    both_run("""
void *target;
int main(void) {
    unsigned long x = 0x123400UL;
    void *p = __builtin_extract_return_addr(x);
    if ((unsigned long)p != 0x123400UL) return 1;
    target = __builtin_extract_return_addr((unsigned long)target);
    return 0;
}
""", "x-ert")


def test_object_size_run_pair():
    both_run("""
char gbuf[10];
char b[32];
struct { long v[2]; } gs;
extern char ext[];
char big[4096];
int main(void) {
    if (__builtin_object_size(gbuf, 0) != 10) return 1;
    if (__builtin_object_size(gbuf + 3, 0) != 7) return 2;
    if (__builtin_object_size(&gs.v[0], 0) != 16) return 3;
    if (__builtin_object_size(b, 0) != 32) return 4;
    if (__builtin_object_size(big, 1) != 4096) return 5;
    if (__builtin_object_size(ext, 0) != (unsigned long)-1) return 6;
    return 0;
}
""", "x-obs")


def test_intrinsics_loud_arity_and_level():
    # §5-DEFER: frame/return address levels above 0 need the caller chain.
    loud("int main(void){ return (int)__builtin_return_address(1); }\n",
         "x-ra1", "not in the subset")
    loud("int main(void){ return (int)__builtin_frame_address(1); }\n",
         "x-fa1", "not in the subset")
    loud("int main(void){ return __builtin_bswap32(1, 2); }\n",
         "x-bsa", "exactly 1 argument")
