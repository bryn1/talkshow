"""M58 + §2.17 — mem* SIZE-CLASS INLINE FOLD: every __builtin_{memcpy,memset,
memcmp,memmove} site and every plain-spelled memcpy/memset/memcmp/memmove
site whose callee resolves to the standard extern signature folds to an
inline size-class expansion with ZERO callees (blcc's machine class is GP +
string only). Names with a visible DEFINITION in the TU are CALLED, never
folded (lib/string.c's own memcpy stays a function). Per-TU nm PARITY:
blcc_U ⊆ gcc_U ∪ ASM_ALLOW and gcc_U − blcc_U ⊆ {mem*} — corollary: ZERO
mem* U on every blcc object. MC 12460 cycle-2 stage T+8b.

Run pairs: gcc 11.4 -std=gnu89 calls the REAL libc (its oracle) — blcc's
inline expansion must produce byte-identical program behaviour, including
memcmp's exact unsigned-byte-diff return value (measured below; FINDING
c2-F2: §2.17's "signed byte-diff" wording contradicts the glibc oracle and
the kernel's own lib/string.c — both take the UNSIGNED-byte difference —
oracle wins).
"""
import os
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
FIXDIR = os.path.join(ROOT, "tests", "fixtures", "m58")

ITMP = os.path.join(ROOT, ".tmp", "itmem")


def _fresh(tag):
    os.makedirs(ITMP, exist_ok=True)
    return os.path.join(ITMP, "{}_{}_1".format(tag, os.getpid()))


def _compile_blcc(src_path, tag):
    """blcc compile; returns (exe, asm_path, obj_path)."""
    p = _fresh(tag)
    out_b = p + ".bin"
    rb = subprocess.run([sys.executable, "-m", "blcc", src_path, "-o",
                         out_b, "--emit-asm"], cwd=ROOT,
                        capture_output=True, text=True, timeout=120)
    assert rb.returncode == 0, "blcc compile failed ({}):\n{}".format(
        tag, rb.stderr)
    asm_path = out_b + ".s"
    obj_path = p + ".o"
    ra = subprocess.run(["as", "--64", "-o", obj_path, asm_path],
                        capture_output=True, text=True, timeout=60)
    assert ra.returncode == 0, "as failed: " + ra.stderr
    return out_b, asm_path, obj_path


def both_run(src, tag):
    p = _fresh(tag)
    src_path = p + ".c"
    with open(src_path, "w", encoding="utf-8") as fh:
        fh.write(src)
    out_g = p + ".gcc"
    rg = subprocess.run(["gcc", "-w", "-std=gnu89", "-O0", "-o", out_g,
                         src_path], capture_output=True, text=True,
                        timeout=60)
    assert rg.returncode == 0, "gcc twin must build ({}):\n{}".format(
        tag, rg.stderr)
    out_b, _, _ = _compile_blcc(src_path, tag)
    pb = subprocess.run([out_b], capture_output=True, timeout=30)
    pg = subprocess.run([out_g], capture_output=True, timeout=30)
    assert (pb.returncode, pb.stdout) == (pg.returncode, pg.stdout), \
        "run-pair mismatch ({}): blcc={} gcc={}".format(
            tag, (pb.returncode, pb.stdout), (pg.returncode, pg.stdout))
    return src_path


def nm_undefined(obj_path):
    r = subprocess.run(["nm", "-u", obj_path], capture_output=True,
                       text=True, timeout=30)
    assert r.returncode == 0, r.stderr
    return r.stdout


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


# ---- (a) RUN legs: every size class, both spellings ------------------------

MEMPROTOS = """
void *memcpy(void *, const void *, unsigned long);
void *memset(void *, int, unsigned long);
int memcmp(const void *, const void *, unsigned long);
void *memmove(void *, const void *, unsigned long);
"""


def test_memcpy_const_sizes_run_pair():
    # every literal size 0..16: each call site is a CONST class expansion
    # (mov8 + 4/2/1-width GP pairs) — the loop-variable class is mc-var.
    both_run(MEMPROTOS + """
#define CPK(k)                                              \
    for (i = 0; i < 24; i++) d[i] = (char)0xEE;             \
    memcpy(d, s, (k));                                      \
    for (i = 0; i < 24; i++) {                              \
        unsigned char want;                                 \
        if (i < (k)) want = (unsigned char)(i + 1);         \
        else want = (unsigned char)0xEE;                    \
        if ((unsigned char)d[i] != want) bad++;             \
    }
static char d[24], s[24];
static int i;
int main(void) {
    long bad = 0;
    for (i=0;i<24;i++) s[i]=(char)(i+1);
    CPK(0) CPK(1) CPK(2) CPK(3) CPK(4) CPK(5) CPK(6) CPK(7)
    CPK(8) CPK(9) CPK(10) CPK(11) CPK(12) CPK(13) CPK(14)
    CPK(15) CPK(16)
    if (bad) return 1;
    return 0;
}
""", "mc-const")


def test_memcpy_var_sizes_run_pair():
    both_run(MEMPROTOS + """
static char d[1100], s[1100];
static unsigned long nn;
int main(void) {
    int i; long bad = 0;
    for (i=0;i<1100;i++) s[i]=(char)(i*7+3);
    nn = 1000;
    memcpy(d, s, nn);                       /* VAR: rep movsb class   */
    for (i=0;i<1000;i++) if (d[i]!=s[i]) bad++;
    nn = 1;
    memcpy(d, s, nn);                       /* VAR tiny               */
    if (d[0]!=s[0]) bad++;
    if (bad) return 1;
    return 0;
}
""", "mc-var")


def test_memset_const_and_fill_rules_run_pair():
    both_run(MEMPROTOS + """
static char d[24];
int main(void) {
    int i, j, bad = 0;
    int fills[4]; fills[0]=0; fills[1]=0xA5; fills[2]=-1; fills[3]=256;
    for (j=0;j<4;j++) {
        int k;
        for (k=0;k<=16;k++) {
            memset(d, fills[j], k);
            for (i=0;i<k;i++)
                if ((unsigned char)d[i] != (unsigned char)fills[j]) bad++;
        }
    }
    if (bad) return 1;
    return 0;
}
""", "ms-const")


def test_memset_large_and_var_run_pair():
    both_run(MEMPROTOS + """
static char big[4096];
static unsigned long nn;
int main(void) {
    int i, bad = 0; long t = 0;
    memset(big, 0, 4096);                    /* CONST 4096 clear_page class */
    for (i=0;i<4096;i++) t += (unsigned char)big[i];
    if (t) return 1;
    nn = 4000;
    memset(big, 0x5A, nn);                  /* VAR class                  */
    for (i=0;i<4000;i++) if ((unsigned char)big[i]!=0x5A) bad++;
    if (bad) return 1;
    return 0;
}
""", "ms-large")


def test_memcmp_run_pair():
    # exact unsigned-byte-diff values (glibc oracle; FINDING c2-F2 row):
    both_run(MEMPROTOS + """
static unsigned char a[16], b[16];
int i;
int main(void) {
    int r, sum = 0;
    for (i=0;i<16;i++) { a[i]=(unsigned char)('a'+i%4); b[i]=a[i]; }
    b[11] = 'Z';
    r = memcmp(a, b, 12);                    /* CONST size, early exit at 11 */
    if (r < 0) sum += 1;
    r = memcmp(a, b, 16);
    if (r != (int)('a'+11%4) + 0 - (int)'Z' - 0) sum += 2;  /* exact value */
    b[11] = a[11];
    r = memcmp(a, b, 16);
    if (r != 0) sum += 4;
    b[14] = 'Q';                             /* outside the 12 bound: */
    r = memcmp(a, b, 12);
    if (r != 0) sum += 8;                    /* CONST bound respected */
    a[0] = 0xFF; b[0] = 0x01;
    r = memcmp(a, b, 3);
    if (r == 254) sum += 16;                 /* UNSIGNED byte diff, exact */
    return (int)sum;
}
""", "mc-cmp")


def test_memcmp_var_run_pair():
    both_run(MEMPROTOS + """
static unsigned char a[64], b[64];
static unsigned long nn;
int i;
int main(void) {
    int sum = 0, r;
    for (i=0;i<64;i++) { a[i]=(unsigned char)(i&31); b[i]=a[i]; }
    nn = 50;
    r = memcmp(a, b, nn); if (r != 0) sum += 1;
    b[33] ^= 1;
    r = memcmp(a, b, nn); if (r < 0) sum += 2;   /* first diff at 33 < nn */
    r = memcmp(a, b, 33);  if (r != 0) sum += 4; /* beyond the diff: 0    */
    return (int)sum;
}
""", "cmp-var")


def test_memmove_run_pair():
    both_run(MEMPROTOS + """
static char d[300];
static unsigned long nn;
int i, bad;
int main(void) {
    bad = 0;
    /* CONST 8, dst BEHIND src (must copy backward): */
    for (i=0;i<16;i++) d[i]=(char)i;
    memmove(d+4, d, 8);
    for (i=0;i<8;i++) if (d[4+i]!=(char)i) bad++;
    /* CONST 8, dst AHEAD of src (forward): */
    for (i=0;i<16;i++) d[i]=(char)i;
    memmove(d, d+4, 8);
    for (i=0;i<8;i++) if (d[i]!=(char)(4+i)) bad++;
    /* VAR 100 overlapping both directions: */
    nn = 100;
    for (i=0;i<256;i++) d[i]=(char)(i%61);
    memmove(d+50, d, nn);
    for (i=0;i<100;i++) if (d[50+i]!=(char)(i%61)) bad++;
    for (i=0;i<256;i++) d[i]=(char)(i%61);
    memmove(d, d+50, nn);
    for (i=0;i<100;i++) if (d[i]!=(char)((50+i)%61)) bad++;
    if (bad) return 1;
    return 0;
}
""", "mv")


def test_plain_spellings_zero_mem_refs_run_pair():
    p = _fresh("plain")
    src_path = p + ".c"
    with open(src_path, "w", encoding="utf-8") as fh:
        fh.write(MEMPROTOS + """
static char d[64], s[64];
static unsigned long nn;
int i;
int main(void) {
    for (i=0;i<64;i++) s[i]=(char)(i+1);
    nn = 40;
    memcpy(d, s, nn);
    if (d[39] != 40) return 1;
    memset(d, 0, nn);
    if (d[39] != 0) return 2;
    if (memcmp(s, s, nn) != 0) return 3;
    memmove(d, s, nn);
    if (d[0] != 1) return 4;
    return 0;
}
""")
    out_b, asm_path, obj_path = _compile_blcc(src_path, "plain")
    out = nm_undefined(obj_path)
    for nm_name in ("memcpy", "memset", "memcmp", "memmove"):
        assert nm_name not in out, \
            "blcc object must carry ZERO mem* U (§2.17 corollary): " + out
    asm_text = open(asm_path).read()
    assert "call memcpy" not in asm_text and "call memset" not in asm_text
    out_g = p + ".gcc"
    rg = subprocess.run(["gcc", "-w", "-std=gnu89", "-O0", "-o", out_g,
                         src_path], capture_output=True, text=True,
                        timeout=60)
    assert rg.returncode == 0, rg.stderr
    # gcc -O0 twin CALLS the libc — the parity direction (blcc_U ⊆ gcc_U):
    r = subprocess.run(["gcc", "-w", "-std=gnu89", "-O0", "-c", src_path,
                        "-o", p + ".gcc.o"], capture_output=True, timeout=60)
    gnm = nm_undefined(p + ".gcc.o")
    assert "memcpy" in gnm, "gcc twin must reference memcpy: " + gnm
    pb = subprocess.run([out_b], capture_output=True, timeout=30)
    pg = subprocess.run([out_g], capture_output=True, timeout=30)
    assert (pb.returncode, pb.stdout) == (pg.returncode, pg.stdout)


def test_fold_class_asm_shapes():
    # size-class pin: VAR memcpy → rep movsb, VAR memset → rep stosb,
    # CONST-8 memcpy → straight-line GP pairs (no rep, no call)
    src = MEMPROTOS + """
static char d[64], s[64];
static unsigned long nn;
void cp_var(void) { memcpy(d, s, nn); }
void fill_var(void) { memset(d, 7, nn); }
void cp_small(void) { memcpy(d, s, 8); }
int main(void) { cp_var(); fill_var(); cp_small(); return 0; }
"""
    p = _fresh("cls")
    src_path = p + ".c"
    open(src_path, "w").write(src)
    _, asm_path, _ = _compile_blcc(src_path, "cls")
    asm = open(asm_path).read()
    seg = asm.split("cp_var:")
    assert "rep movsb" in seg[1]
    seg = asm.split("fill_var:")
    assert "rep stosb" in seg[1]
    seg = asm.split("cp_small:")[1]
    nxt = min(i for i in [seg.find("\nmain:"), seg.find("\ncp_var:")]
              if i >= 0)
    body = seg[:nxt]
    assert "rep" not in body and "call" not in body, \
        "CONST-8 must be straight-line GP: " + body


def test_visible_definition_is_called_not_folded_run_pair():
    # lib/string.c posture: a TU with its OWN memcpy definition CALLS it.
    p = _fresh("visdef")
    src_path = p + ".c"
    with open(src_path, "w", encoding="utf-8") as fh:
        fh.write("""
void *memcpy(void *d, const void *s, unsigned long n) {
    char *dd = (char *)d; const char *ss = (char *)s;
    unsigned long i;
    for (i = 0; i < n; i++) dd[i] = ss[i];
    return d;
}
static char d[16], s[16];
int main(void) {
    int i;
    for (i=0;i<16;i++) s[i]=(char)(i+1);
    memcpy(d, s, 16);
    for (i=0;i<16;i++) if (d[i]!=(char)(i+1)) return 1;
    return 0;
}
""")
    out_b, asm_path, obj_path = _compile_blcc(src_path, "visdef")
    asm = open(asm_path).read()
    assert "call memcpy" in asm, \
        "visible-definition memcpy must be CALLED (never folded):\n" + asm
    assert "memcpy" not in nm_undefined(obj_path)
    r = subprocess.run([out_b], capture_output=True, timeout=30)
    assert r.returncode == 0, "visible-definition run failed"


def test_builtin_mem_arity_loud():
    loud("int main(void){ __builtin_memcpy((char*)0, (char*)0); return 0; }\n",
         "mem-arity", "memcpy")


# ---- (c)(d) FIXTURE legs: nm -u zero + -z,defs link + planted-hole red ----

def _fixture_legs(name, gcc_flags, run_ok=True):
    src = os.path.join(FIXDIR, name)
    p = _fresh(name)
    rb = subprocess.run([sys.executable, "-m", "blcc", src, "-o",
                         p + ".bin", "--emit-asm"], cwd=ROOT,
                        capture_output=True, text=True, timeout=120)
    assert rb.returncode == 0, "blcc fixture compile failed ({}):\n{}".format(
        name, rb.stderr)
    obj = p + ".bl.o"
    ra = subprocess.run(["as", "--64", "-o", obj, p + ".bin.s"],
                        capture_output=True, timeout=60)
    assert ra.returncode == 0, ra.stderr
    un = nm_undefined(obj)
    for nm_name in ("memcpy", "memset", "memcmp", "memmove"):
        assert nm_name not in un, "M58 nm-leg RED: {} in\n{}".format(
            nm_name, un)
    # leg 2: link with a support object that has NO mem* symbols
    sup = p + ".sup.o"
    rs = subprocess.run(["gcc", "-c", "-w", "-std=gnu89", "-Os",
                        os.path.join(FIXDIR, "support.c"), "-o", sup],
                        capture_output=True, text=True, timeout=60)
    assert rs.returncode == 0, rs.stderr
    rl = subprocess.run(["gcc", "-nostdlib", "-Wl,-z", "defs", obj, sup,
                         "-o", p + ".linked"],
                        capture_output=True, text=True, timeout=60)
    assert rl.returncode == 0, \
        "M58 link-leg RED (-z defs sees a hole):\n" + rl.stderr
    # the blcc exe runs ONLY for run-safe fixtures: the vdso spec file is
    # deliberately not runnable (memset 4096 into char d[64] — the spec's
    # point is the CODE SHAPE, gcc twin runs identically badly; its legs
    # are nm + link). Boot fixture is run-safe (bounded buffers).
    if run_ok:
        rr = subprocess.run([p + ".bin"], capture_output=True, timeout=30)
        assert rr.returncode == 0, "fixture run rc{}".format(rr.returncode)
    # leg 3: gcc twin compiled with its measured flags passes nm + link too
    gobj = p + ".gcc.o"
    gcmd = ["gcc", "-w", "-std=gnu89", "-fno-stack-protector"] + gcc_flags \
        + ["-c", src, "-o", gobj]
    g = subprocess.run(gcmd, capture_output=True, text=True, timeout=60)
    assert g.returncode == 0, "gcc twin compile failed:\n" + g.stderr
    gl = subprocess.run(["gcc", "-nostdlib", "-Wl,-z", "defs", gobj, sup,
                         "-o", p + ".gcc.linked"],
                        capture_output=True, text=True, timeout=60)
    assert gl.returncode == 0, "gcc twin link must pass:\n" + gl.stderr


def test_fixture_vdso_synth_legs():
    _fixture_legs("fixture_vdso_synth.c", ["-Os"], run_ok=False)


def test_fixture_boot_legs():
    _fixture_legs("fixture_boot_shape.c", ["-Os"])


def test_fixture_hole_negative_control_red():
    """The planted hole (§4.3 M58(d) control): compiled by GCC it MUST show
    U memcmp/U memcpy and MUST FAIL -z defs — the control leg's own proof
    that it can go red (mut-memfold plants this for BLCC at acceptance)."""
    src = os.path.join(FIXDIR, "fixture_hole_planted.c")
    p = _fresh("hole")
    gobj = p + ".gcc.o"
    r = subprocess.run(["gcc", "-w", "-std=gnu89", "-fno-stack-protector",
                        "-Os", "-c", src, "-o", gobj],
                       capture_output=True, text=True, timeout=60)
    assert r.returncode == 0, r.stderr
    un = nm_undefined(gobj)
    # measured today: this gcc -Os VAR-inlines memcpy (rep movsb) — the
    # planted hole that survives is the VAR memcmp (U) — enough for -z defs
    assert "U memcmp" in un, "planted hole must be nm-visible: " + un
    sup = p + ".sup.o"
    subprocess.run(["gcc", "-c", "-w", "-std=gnu89", "-Os",
                    os.path.join(FIXDIR, "support.c"), "-o", sup],
                   capture_output=True, timeout=60)
    rl = subprocess.run(["gcc", "-nostdlib", "-Wl,-z", "defs", gobj, sup,
                         "-o", p + ".linked"],
                        capture_output=True, text=True, timeout=60)
    assert rl.returncode != 0, \
        "planted hole MUST fail -z defs (leg cannot be trusted green)"
