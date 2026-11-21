# LINES reason: one law (M4 W-W COMMIT-2, card 12753): the two NAMED
# W-V global-init residuals — the tty_ldisc indexed-extern-element fold
# and the lib_crc32 bswap32 fold — ship together (+2 streams, byte-
# pinned), with their KEEP-law twins; one law, one file.
r"""M4 W-W COMMIT-2 (MC 12753) — the two NAMED W-V GLOBAL-INIT FOLDS.

W-V shipped the global-init address-constant door and LEFT two streams
at the §4 LOUD, named VERBATIM on that card (§6 residuals) — this
commit closes exactly those two, nothing beside them:

(a) THE tty_ldisc RESIDUAL — `&ext_arr[K]` where the array is extern
    INCOMPLETE: `extern int sysctl_vals[]; static int *p =
    &sysctl_vals[1];` (tty_ldisc.c:789). gcc's index-address law needs
    the ELEMENT size only — the object answers a .quad relocation
    `sysctl_vals+0x4` (pin below: R_X86_64_64 sysctl_vals+0x4, SAME
    text as gcc -fno-pic, sims §5-2). blcc@tip held the §4 LOUD
    (`global initializer wants a load-time constant`, found '&'):
    the index arm demanded ty.size.

(b) THE lib_crc32 RESIDUAL — `__builtin_bswapNN(CONST)` in a global
    initializer: the crc32 polynomial table (`((u32)((0x120717c8L)))`,
    lib/crc32.c:151) — gcc FOLDS byte-swap of a constant AT REC, the
    swapped literals land in .data as `.long`s (byte-pinned below;
    sims §5-2). blcc@tip answered the §4 LOUD (W-V NAMED-DIVERGE row —
    a §4-vs-fold door divergence, not a subset gap).

KEEP-laws PRESERVED (the W-V e28 law twins): a NON-CONSTANT index
(`&ext[k]`, runtime k) and an INCOMPLETE ELEMENT type (`extern
struct S ext[]; &ext[0]`) stay LOUD — the e28 row-e pair legs keep
passing UNCHANGED (green-at-base pins of the OLD wall, flipped
posture NAMED below).
"""
import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.environ.get("BLCC_REPO") or os.path.dirname(HERE)
STREAMS = os.path.join(REPO, "..", ".tmp", "m4-plan", "streams")
REC = ["-std=gnu89", "-Os", "-mno-sse", "-mno-sse2", "-mno-80387",
       "-fno-stack-protector", "-fno-pic"]
ENV = {"PYTHONPATH": REPO, "PATH": "/usr/bin:/bin", "LC_ALL": "C"}


def blcc(args):
    return subprocess.run([sys.executable, "-m", "blcc"] + args,
                          capture_output=True, text=True, cwd=REPO, env=ENV)


def _w(tag, src):
    c = "/dev/shm/ww2_%s_%d.c" % (tag, os.getpid())
    open(c, "w").write(src)
    return c


def _objs(tag, src):
    """compile with gcc AND blcc, return (go, bo); blcc rc0 asserted —
    RED-first: tip LOUDs both shapes."""
    c = _w(tag, src)
    go = "/dev/shm/ww2_%s_%d.g.o" % (tag, os.getpid())
    bo = "/dev/shm/ww2_%s_%d.b.o" % (tag, os.getpid())
    g = subprocess.run(["gcc"] + REC + [c, "-c", "-o", go],
                       capture_output=True, text=True, env=ENV)
    assert g.returncode == 0, "row must be valid C: " + g.stderr
    b = blcc(["-c", c, "-o", bo])
    assert b.returncode == 0, "must compile (RED-first: tip LOUDs): " \
        + tag + ": " + b.stderr
    return go, bo


def _relocs(o):
    p = subprocess.run(["objdump", "-sr", o], capture_output=True,
                       text=True)
    return [l.strip() for l in p.stdout.splitlines()
            if "R_X86_64" in l]


def _pair(tag, src, want=None):
    c = _w(tag, src)
    gex = "/dev/shm/ww2_%s_%d.g" % (tag, os.getpid())
    g = subprocess.run(["gcc"] + REC + [c, "-no-pie", "-o", gex],
                       capture_output=True, text=True, env=ENV)
    assert g.returncode == 0, "row must be valid C: " + g.stderr
    gx = subprocess.run([gex], env=ENV).returncode
    o = "/dev/shm/ww2_%s_%d.o" % (tag, os.getpid())
    b = blcc(["-c", c, "-o", o])
    assert b.returncode == 0, tag + ": " + b.stderr
    bex = "/dev/shm/ww2_%s_%d.b" % (tag, os.getpid())
    assert subprocess.run(["gcc", "-no-pie", o, "-o", bex],
                          capture_output=True).returncode == 0
    bx = subprocess.run([bex], env=ENV).returncode
    assert bx == gx, "%s run-pair: blcc=%d gcc=%d" % (tag, bx, gx)
    if want is not None:
        assert gx == want, "%s wants %d, both answered %d" % (tag, want, gx)


def _pair_two_tu(tag, src_a, src_b, want=None):
    """THE link-time law: the array is DEFINED IN THE OTHER TU (the
    tty_ldisc posture — the definition lives elsewhere). A per-TU copy
    cannot answer the value."""
    a, b = _w(tag + "_a", src_a), _w(tag + "_b", src_b)
    gx = "/dev/shm/ww2_%s_%d.g" % (tag, os.getpid())
    g = subprocess.run(["gcc"] + REC + [a, b, "-no-pie", "-o", gx],
                       capture_output=True, text=True, env=ENV)
    assert g.returncode == 0, "two-TU row must link with gcc: " + g.stderr
    gxv = subprocess.run([gx], env=ENV).returncode
    o_a = "/dev/shm/ww2_%s_%d.ba.o" % (tag, os.getpid())
    bb = blcc(["-c", a, "-o", o_a])
    assert bb.returncode == 0, tag + " blcc TU-a: " + bb.stderr
    b2 = subprocess.run(["gcc"] + REC + [b, "-c", "-o",
                        "/dev/shm/ww2_%s_%d.gbo.o" % (tag, os.getpid())],
                        capture_output=True, text=True, env=ENV)
    assert b2.returncode == 0, b2.stderr
    bx = "/dev/shm/ww2_%s_%d.b" % (tag, os.getpid())
    assert subprocess.run(
        ["gcc", "-no-pie", o_a,
         "/dev/shm/ww2_%s_%d.gbo.o" % (tag, os.getpid()), "-o", bx],
        capture_output=True).returncode == 0
    bxv = subprocess.run([bx], env=ENV).returncode
    assert bxv == gxv, "%s two-TU run-pair: blcc=%d gcc=%d" % (tag, bxv,
                                                               gxv)
    if want is not None:
        assert gxv == want, "%s wants %d, both answered %d" % (tag, want,
                                                               gxv)


# ------------------------------------------------ (a) index-the-element

def test_extern_incomplete_index_fold_reloc():
    """THE tty_ldisc residual shape: &ext[K] into an extern array of
    UNKNOWN length answers `symbol + K*elemsize` — the .quad
    relocation TEXT equals gcc's, byte-identical instrument (sims
    §5-2: R_X86_64_64 sysctl_vals+0x4)."""
    src = ("extern int sysctl_vals[];\n"
           "int *p = &sysctl_vals[1];\n")
    go, bo = _objs("idx1", src)
    rg, rb = _relocs(go), _relocs(bo)
    tok = lambda xs: sorted(x.split("R_X86_64_64")[1].strip() for x in xs)
    assert tok(rg) == tok(rb) and \
        any("sysctl_vals+0x0000000000000004" in x for x in rb), (rg, rb)


def test_extern_incomplete_index_fold_run_pair():
    """The answer-side law: the folded address IS the element address —
    two-TU (the array lives in the twin, the .i corpus posture): the
    extern-incomplete reference answers the REAL element, value 70."""
    _pair_two_tu("idxrun",
                 "extern char big[];\n"
                 "char *p = &big[3];   /* THE fold: global-init door */\n"
                 "int probe(void) { return *p; }\n",
                 "char big[8] = {0,1,2,70,4,5,6,7};\n"
                 "int probe(void);\n"
                 "int main(int argc, char **argv) { (void)argc;"
                 " (void)argv; return probe() & 255; }\n",
                 want=70)


def test_extern_incomplete_index_scales_by_element():
    """scaled arithmetic rides the law: &ext[2] of a long array is
    +0x10, and the STRUCT element scales by its size (pin vs gcc)."""
    src = ("extern long ea[];\n"
           "struct P { long x, y; };\n"
           "extern struct P pa[];\n"
           "long *q1 = &ea[2];\n"
           "struct P *q2 = &pa[1];\n")
    go, bo = _objs("idx2", src)
    rg, rb = _relocs(go), _relocs(bo)
    # the MULTISET of symbol+ADDEND pairs is the law; the relocation
    # POSITION inside .data is a layout choice (blcc.data compression,
    # sims §7-10) — strip the position, compare SORTED.
    tok = lambda xs: sorted(x.split("R_X86_64_64")[1].strip() for x in xs)
    assert tok(rg) == tok(rb), (rg, rb)
    assert any("ea+0x0000000000000010" in x for x in rb)
    assert any("pa+0x0000000000000010" in x for x in rb)


def test_runtime_index_stays_loud():
    """KEEP-law (W-V e28 twin): a NON-constant index is not a constant
    expression — LOUD unchanged (green-at-base posture pin)."""
    src = ("extern int ext[];\n"
           "int *f(int k) { int *p = &ext[k]; (void)p; return 0; }\n"
           "int *q = 0;\n")
    b = blcc(["-c", _w("rk", src), "-o",
              "/dev/shm/ww2_rk_%d.o" % os.getpid()])
    assert b.returncode == 0, b.stderr   # runtime index is in a FUNCTION
    src2 = ("extern int ext[];\n"
            "int k;\n"
            "int *q = &ext[k];\n")
    b = blcc(["-c", _w("rk2", src2), "-o",
              "/dev/shm/ww2_rk2_%d.o" % os.getpid()])
    assert b.returncode == 2, "global init with a runtime index stays LOUD"


def test_incomplete_element_stays_loud():
    """KEEP-law: the ELEMENT type must be COMPLETE — `extern struct S
    ext[]; &ext[0]` into an incomplete S stays LOUD (e28 row-e twin)."""
    src = ("struct S;\n"
           "extern struct S ext[];\n"
           "struct S *p = &ext[0];\n")
    b = blcc(["-c", _w("ie", src), "-o",
              "/dev/shm/ww2_ie_%d.o" % os.getpid()])
    assert b.returncode == 2, "incomplete element must stay LOUD"


# ------------------------------------------------------ (b) bswap folds

def test_bswap32_fold_data_bytes():
    """THE lib_crc32 residual: bswap32 of a constant folds at REC; the
    .data bytes equal gcc's BYTE FOR BYTE (sims §5-2 pin on the
    0x120717c8 class — here the same shape at own hands)."""
    src = ("typedef unsigned int u32;\n"
           "u32 tab[2] = { (u32)__builtin_bswap32(0x120717c8U),\n"
           "               (u32)__builtin_bswap32(0x00000001U) };\n")
    go, bo = _objs("bswap", src)

    def sec(o):
        out = o + ".data.bin"
        p = subprocess.run(["objcopy", "-O", "binary",
                            "--only-section=.data", o, out],
                           capture_output=True)
        assert p.returncode == 0, p.stderr
        return open(out, "rb").read()
    assert sec(go) == sec(bo)
    assert sec(bo)[:4] == b"\x12\x07\x17\xc8"   # value 0xc8170712 little-endian


def test_bswap64_fold_and_run_pair():
    """bswap64 rides the same door; a computed answer pins the VALUE
    through both objects."""
    _pair("bs64",
          "typedef unsigned long u64;\n"
          "static const u64 k = (u64)__builtin_bswap64(1UL);\n"
          "int probe(void) { return (int)(k & 255); }\n"
          "int main(int argc, char **argv) { (void)argc; (void)argv;"
          " return probe() & 255; }\n", want=0)
    src = ("typedef unsigned long u64;\n"
           "u64 v = (u64)__builtin_bswap64(0x0000000012345678UL);\n")
    go, bo = _objs("bs64d", src)

    def sec(o):
        out = o + ".data.bin"
        assert subprocess.run(["objcopy", "-O", "binary",
                               "--only-section=.data", o, out],
                              capture_output=True).returncode == 0
        return open(out, "rb").read()
    assert sec(go) == sec(bo)
    assert sec(bo) == bytes.fromhex("0000000012345678")  # value 0x7856341200000000 LE


def test_bswap_runtime_stays_call():
    """NOT a fold door opened for everything: a RUNTIME bswap is not a
    constant expression — its global init stays LOUD, exactly as at
    tip (green-at-base posture pin)."""
    src = ("unsigned f(unsigned x);\n"
           "extern int kk;\n"
           "unsigned g = __builtin_bswap32(kk + f(1));\n")
    b = blcc(["-c", _w("rt", src), "-o",
              "/dev/shm/ww2_rt_%d.o" % os.getpid()])
    assert b.returncode == 2, "runtime bswap must stay LOUD"


def test_bswap_wrong_arity_stays_loud():
    """an alias-shaped call `__builtin_bswap32(a, b)` is NOT the fold:
    the door is name+ARITY+constant (no new call-law surface)."""
    src = ("unsigned int g = __builtin_bswap32(1u, 2u);\n")
    b = blcc(["-c", _w("ar", src), "-o",
              "/dev/shm/ww2_ar_%d.o" % os.getpid()])
    assert b.returncode == 2, b.stderr


# ------------------------------------------------- corpus posture legs

def _first_wall(tu):
    s = os.path.join(STREAMS, tu)
    if not os.path.exists(s):
        return None, None
    txt = "".join(ln for ln in open(s, errors="replace")
                  if not ln.startswith("# "))
    c = "/dev/shm/ww2_c_%d.i" % os.getpid()
    open(c, "w").write(txt)
    o = "/dev/shm/ww2_co_%d.o" % os.getpid()
    p = blcc(["-c", c, "-o", o])
    first = ""
    for ln in p.stderr.splitlines():
        if ln.strip():
            first = ln
            break
    return p.returncode, first


def test_residue_streams_accept_at_ship():
    """THE two NAMED streams (W-V §6 residuals, VERBATIM): at ship
    bytes the residue rows are GONE — crc32 and tty_ldisc walk on."""
    if not os.path.isdir(STREAMS):
        sys.stdout.write("  [skip corpus streams]\n")
        return
    for s in ("lib_crc32.c.i", "drivers_tty_tty_ldisc.c.i"):
        rc, first = _first_wall(s)
        assert rc == 0, s + " must ACCEPT at ship bytes: " + first[:160]
