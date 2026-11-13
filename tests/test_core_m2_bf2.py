"""M2 FIX-G1 (MC 12460) — §1 row 12 bitfield LAW legs the shipped M45 suite
lacked (gate C1 verdict m2-test-verdict-c1.md, TRIGGER 1): NO shipped leg
ever STORED a bitfield member that does not start fresh in its unit, so the
unit-spill store silently vanished and mixed-unit stores corrupted.

EVERY expectation is a gcc 11.4 -std=gnu89 measurement taken this session
(.tmp/m2-fix-g1/probe/{win,bis,strd}.c, -O0 == -Os on every body):
the spill law (a field that would cross its aligned-unit boundary moves to
the NEXT unit and its store LANDS THERE — measured asm: `movb $-56,
4+ga(%rip)`, `2+gm`, `8+gl`), the straddle round-trip (mixed-size units
pack LSB-first, read-back through the spilled field returns the stored
value, sign-extended from bit w-1 for signed declarations), and mixed-unit
NEIGHBOUR integrity (the byte member between/after spilled fields keeps its
own bytes; the full 64-byte window matches the gcc-dumped one, byte for
byte). Shapes gcc ERRORS on (`char b:12` — "width of 'b' exceeds its type")
stay LOUD and are pinned here too.
"""
import os
import re
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

ITMP = os.path.join(ROOT, ".tmp", "itbf2")


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


def blcc_loud(src, tag, family):
    """blcc must exit 2 with a §8 diagnostic of the named family."""
    os.makedirs(ITMP, exist_ok=True)
    p = os.path.join(ITMP, "{}_{}_1".format(tag, os.getpid()))
    src_path = p + ".c"
    with open(src_path, "w", encoding="utf-8") as fh:
        fh.write(src)
    rb = subprocess.run([sys.executable, "-m", "blcc", src_path, "-o",
                         os.devnull], cwd=ROOT, capture_output=True,
                        text=True, timeout=60)
    os.remove(src_path)
    assert rb.returncode == 2, \
        "{} must LOUD, rc={}\n{}".format(tag, rb.returncode, rb.stderr)
    assert ": {}:".format(family) in rb.stderr, \
        "{} landed outside the {} family:\n{}".format(tag, family, rb.stderr)


# ------------------------------------------------------ spill store lands

def test_bitfield_unit_spill_store_run_pair():
    # win.c measured: spill stores land in the NEXT unit (gate C1 trigger 1
    # — blcc@tip wrote NOTHING for these, rc0 both, stale read-back).
    # gcc window truth (64B, -O0 == -Os, .tmp/m2-fix-g1/probe/win.c):
    #   07000000c8000000 3d3e0000 07300f00 f77a7900 f9ffff0ffb0000 00
    #   gg@28: 07000000 63000000 c8000000   gh@40: 07000000 06c80000
    #   gl@48: 05000000 00000000 c8000000 ... (gs spill byte 24 = fb)
    both_run("""
struct A {unsigned int a:28; unsigned int b:8;};
struct C {unsigned char a:6; unsigned char b:6;};
struct M {signed int a:12; signed char b:3; signed short c:5;};
struct T {unsigned int a:1; signed char b:7; signed char c:7; signed char d:7;};
struct G {int a:28; int x; unsigned int b:8;};
struct H {int a:28; char x; unsigned int b:8;};
struct L {unsigned long long a:60; unsigned long long b:8;};
struct SI {signed int a:28; signed int b:8;};
char window[64];
int main(void) {
    int i; char *p;
    struct A *ga; struct C *gc; struct M *gm; struct T *gt;
    struct G *gg; struct H *gh; struct L *gl; struct SI *gs;
    for (i = 0; i < 64; i++) window[i] = 0;
    ga = (struct A *)(window + 0);   gc = (struct C *)(window + 8);
    gm = (struct M *)(window + 12);  gt = (struct T *)(window + 16);
    gs = (struct SI *)(window + 20); gg = (struct G *)(window + 28);
    gh = (struct H *)(window + 40);  gl = (struct L *)(window + 48);
    ga->a = 7; ga->b = 200;
    gc->a = 61; gc->b = 62;
    gm->a = 7; gm->b = 3; gm->c = 15;
    gt->a = 1; gt->b = -5; gt->c = -6; gt->d = -7;
    gg->a = 7; gg->x = 99; gg->b = 200;
    gh->a = 7; gh->x = 6;  gh->b = 200;
    gl->a = 5; gl->b = 200;
    gs->a = -7; gs->b = -5;
    if (ga->b != 200 || gc->b != 62 || gm->c != 15) return 90;
    if (gt->b != -5 || gt->c != -6 || gt->d != -7) return 91;
    if (gg->b != 200 || gh->b != 200 || gl->b != 200) return 92;
    if (gs->b != -5 || gs->a != -7) return 93;
    ga->b = 0; ga->b = ga->b + ga->a;              /* RMW across units */
    if (ga->a != 7 || ga->b != 7) return 94;
    ga->b = 200;
    p = window;                                    /* gcc-pinned bytes */
    if (p[0] != 7 || p[1] != 0 || p[2] != 0 || p[3] != 0) return 1;
    if (p[4] != -56) return 2;                     /* ga spill 200 @byte4 */
    if (p[5] != 0 || p[6] != 0 || p[7] != 0) return 3;
    if (p[8] != 61 || p[9] != 62) return 4;        /* gc spill 62 @byte9 */
    if (p[12] != 7 || p[13] != 0x30 || p[14] != 15 || p[15] != 0) return 5;
    if (p[16] != -9 || p[17] != 0x7a || p[18] != 0x79 || p[19] != 0) return 6;
    if (p[20] != -7 && p[20] != 249) return 7;     /* gs: -7 28-bit signed */
    if ((p[21] & 0xff) != 0xff) return 8;
    if ((p[22] & 0xff) != 0xff) return 9;
    if (p[23] != 15) return 10;
    if ((p[24] & 0xff) != 0xfb) return 11;         /* gs signed spill fb */
    if (p[25] != 0 || p[26] != 0 || p[27] != 0) return 12;
    if (p[28] != 7 || p[29] != 0 || p[30] != 0 || p[31] != 0) return 13;
    if (p[32] != 99 || p[33] != 0) return 14;      /* gg->x NEIGHBOUR */
    if ((p[36] & 0xff) != 0xc8) return 15;         /* gg spill @byte8 */
    if (p[37] != 0 || p[38] != 0 || p[39] != 0) return 16;
    if (p[40] != 7 || p[44] != 6) return 17;       /* gh->x NEIGHBOUR */
    if ((p[45] & 0xff) != 0xc8) return 18;         /* gh b @byte5 */
    if (p[48] != 5 || p[49] != 0) return 19;
    if ((p[56] & 0xff) != 0xc8) return 20;         /* gl spill @byte8 */
    for (i = 57; i < 64; i++) if (p[i] != 0) return 21;
    return 0;
}
""", "spill")


def test_bitfield_straddling_readwrite_roundtrip_run_pair():
    # strd.c measured (straddle + mixed-unit roundtrips; gcc -O0 == -Os);
    # this body's own window (post-RMW, gcc -O0 == -Os, this session):
    #   01000000a5000000 dfbc0aa500000000 efcdab00efbe0000 ba190000
    #   bc9a7856341200005a000000 7f001f00... — P1 spill a5@4, P2 spill
    #   a5@3, P3 short-16 crosses into bytes 4-5, P4 mixed char/int/char,
    #   P5 ull:60 + uint spill 5a@8, P6 three short:7 pack then spill
    #   (b straddles byte0-1; clearing it leaves a and c intact).
    both_run("""
struct P1 { unsigned int a:28; unsigned char b:8; };
struct P2 { unsigned int a:20; unsigned char b:8; };
struct P3 { unsigned int a:24; unsigned short b:16; };
struct P4 { unsigned char a:4; unsigned char b:4; unsigned int c:1; unsigned char d:4; };
struct P5 { unsigned long long a:60; unsigned int b:8; };
struct P6 { unsigned short a:7; unsigned short b:7; unsigned short c:7; };
char win[64];
int main(void) {
    int i; char *p;
    struct P1 *s1=(struct P1*)(win+0);
    struct P2 *s2=(struct P2*)(win+8);
    struct P3 *s3=(struct P3*)(win+16);
    struct P4 *s4=(struct P4*)(win+24);
    struct P5 *s5=(struct P5*)(win+32);
    struct P6 *s6=(struct P6*)(win+48);
    for (i=0;i<64;i++) win[i]=0;
    s1->a=0x0BADF; s1->b=0xA5;
    s2->a=0xABCDF; s2->b=0xA5;
    s3->a=0xABCDEF; s3->b=0xBEEF;
    s4->a=0xA; s4->b=0xB; s4->c=1; s4->d=0xC;
    s5->a=0x123456789ABCull; s5->b=0x5A;
    s6->a=0x7F; s6->b=0x3F; s6->c=0x1F;
    if (s1->a != 0x0BADF || s1->b != 0xA5) return 90;
    if (s2->a != 0xABCDF || s2->b != 0xA5) return 91;
    if (s3->a != 0xABCDEF || s3->b != 0xBEEF) return 92;
    if (s4->a != 0xA || s4->b != 0xB || s4->c != 1 || s4->d != 0xC) return 93;
    if (s5->a != 0x123456789ABCull || s5->b != 0x5A) return 94;
    if (s6->a != 0x7F || s6->b != 0x3F || s6->c != 0x1F) return 95;
    s1->a = 1;                    /* RMW across the spill keeps b */
    if (s1->b != 0xA5 || s1->a != 1) return 96;
    s6->b = 0;                    /* straddling clear keeps a and c */
    if (s6->a != 0x7F || s6->c != 0x1F || s6->b != 0) return 97;
    p=win;
    if ((p[0]&0xff) != 0x01) return 1;             /* s1->a RMW landed */
    if ((p[1]&0xff) != 0x00) return 2;
    if ((p[4]&0xff) != 0xa5) return 3;             /* s1->b spill intact */
    if ((p[8]&0xff) != 0xdf || (p[9]&0xff) != 0xbc || (p[10]&0xff) != 0x0a) return 4;
    if ((p[11]&0xff) != 0xa5) return 5;            /* s2 spill byte3 */
    if ((p[16]&0xff) != 0xef || (p[17]&0xff) != 0xcd || (p[18]&0xff) != 0xab) return 6;
    if (p[19] != 0) return 7;                      /* gap byte stays 0 */
    if ((p[20]&0xff) != 0xef || (p[21]&0xff) != 0xbe) return 8;  /* s3 BEEF */
    if ((p[24]&0xff) != 0xba || (p[25]&0xff) != 0x19) return 9;  /* s4 pack */
    if ((p[32]&0xff) != 0xbc || (p[33]&0xff) != 0x9a) return 10; /* s5 a:60 */
    if ((p[37]&0xff) != 0x12 || p[38] != 0 || p[39] != 0) return 11;
    if ((p[40]&0xff) != 0x5a) return 12;           /* s5 spill byte8 */
    if ((p[48]&0xff) != 0x7f) return 13;           /* s6: a kept, b cleared */
    if ((p[49]&0xff) != 0x00) return 14;            /* b's straddled bits cleared */
    if ((p[50]&0xff) != 0x1f) return 15;           /* s6 spill byte2 */
    for (i=51;i<64;i++) if (p[i]!=0) return 16;
    return 0;
}
""", "strd")


def test_bitfield_wide_exceeds_type_stays_loud():
    # gcc 11.4 ERRORS `unsigned char b:12` ("width of 'b' exceeds its
    # type") — the spilled-field shapes gcc rejects stay LOUD in blcc too
    # (fix round must not turn the gate into silent acceptance).
    blcc_loud("""
struct P2 { unsigned int a:20; unsigned char b:12; };
int main(void) { return sizeof(struct P2); }
""", "bf2-wide", "sema")
