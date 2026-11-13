"""M2 FIX-G1 (MC 12460) — CORPUS witnesses: REAL kernel constructs from
kernel .i streams whose run-pairs the fix turned GREEN (gate C1 acceptance:
"corpus witnesses >= 3 kernel constructs from .i streams ... run-pair newly
green, quote before/after").

Corpus instrument (measured THIS session, .tmp/m2-fix-g1): every bitfield
struct/anonymous-run window extractable from 460+ kernel .i streams
(drivers/{base,tty/vt,pci,input/char}, arch/x86, net-adjacent headers,
fs, mm, block, kernel/, lib + crypto/sound/drm/net headers; generated with
per-TU flags from the kernel build's own .o.cmd files) — 603+ windows,
~380 gcc-buildable, ~217 buildable by BOTH compilers — was fingerprinted
through store+raw-byte+read-back probes against gcc 11.4 -std=gnu89,
blcc@tip 2404fd7 and blcc@fixed. EXACTLY ONE construct in this tree
exposes the unit-spill law: `struct kbd_struct` from
include/linux/kbd_kern.h (verbatim in drivers_tty_vt_vt.c.i) — two of its
members spill (`default_ledflagstate:4` after 5 bits used in byte 2 ->
byte 3; `modeflags:5` after 31 bits -> byte 4). That scarcity IS the
corpus-gate's root cause for missing the class: nothing in the shipped
kernel corpus could reach the spill branch. These legs pin the three law
facets (store-lands / extract-through-real-kernel-inlines / neighbour
integrity) as run-pairs. BEFORE/AFTER (probe .tmp/m2-fix-g1/probe/kbdw*.c,
gcc -O0 == -Os): gcc & fixed blcc ->
  `a55a0d5a1f00 ld=06 df=0a md=1f k=05 L2=01 M4=01` rc=0; blcc@tip ->
  `a55a0d500000 ld=06 df=00 md=00 k=05 L2=01 M4=00` rc=0  (SILENT).
"""
import os
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

ITMP = os.path.join(ROOT, ".tmp", "itcorp")

# struct kbd_struct verbatim from drivers_tty_vt_vt.c.i (5.10-
# include/linux/kbd_kern.h) — member order and declarations untouched;
# the two vc_kbd_* helpers are the header's OWN accessors, copied verbatim
# from the same .i stream.
KBD = """
struct kbd_struct {
	unsigned char lockstate;
	unsigned char slockstate;
	unsigned char ledmode:1;
	unsigned char ledflagstate:4;
	unsigned char default_ledflagstate:4;
	unsigned char kbdmode:3;
	unsigned char modeflags:5;
};
static inline int vc_kbd_mode(struct kbd_struct * kbd, int flag)
{
	return ((kbd->modeflags >> flag) & 1);
}
static inline int vc_kbd_led(struct kbd_struct * kbd, int flag)
{
	return ((kbd->ledflagstate >> flag) & 1);
}
static struct kbd_struct probe_kbd;
char after_kbd;
"""

STORES = """
	probe_kbd.lockstate = 0xA5; probe_kbd.slockstate = 0x5A;
	probe_kbd.ledmode = 1; probe_kbd.ledflagstate = 6;
	probe_kbd.default_ledflagstate = 0xA; probe_kbd.kbdmode = 5;
	probe_kbd.modeflags = 0x1F;
"""


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
    return pb.returncode


# ---- witness 1: spilled stores LAND in the next unit (window bytes) -----

def test_kbd_struct_spill_store_lands_window():
    # gcc-pinned window (measured -O0 == -Os, .tmp/m2-fix-g1/probe/kbdw.c):
    #   p[0]=a5 p[1]=5a p[2]=0d p[3]=5a(default_ledflagstate SPILL@lo nibble
    #   + kbdmode@hi) p[4]=1f (modeflags SPILL) p[5]=00.
    # blcc@tip window: a5 5a 0d 00 00 00 — spill stores silently vanished.
    rc = both_run(KBD + """
int main(void) {
	char *p = (char *)&probe_kbd;
""" + STORES + """
	if (p[0] != -91) return 11;                  /* a5 lockstate */
	if (p[1] != 90) return 12;                   /* 5a slockstate */
	if (p[2] != 13) return 13;                   /* 0d ledmode|ledflag */
	if (p[3] != 90) return 14;                   /* 5a SPILL df|kbdmode */
	if (p[4] != 31) return 15;                   /* 1f SPILL modeflags */
	if (p[5] != 0) return 16;
	return 0;
}
""", "kbdw")
    assert rc == 0


# ---- witness 2: read-back THROUGH THE KERNEL'S OWN inline accessors ------

def test_kbd_struct_extract_via_kernel_inlines():
    # The header's OWN vc_kbd_led/vc_kbd_mode helpers plus direct spilled
    # reads: gcc truth df=0a md=1f k=05 L2=1 M4=1. blcc@tip: df=00 md=00,
    # vc_kbd_mode(&probe_kbd,4) reads 0 through the stale descriptor
    # (the gate bf_read class — EXTRACT path, shlq $64 no-op).
    rc = both_run(KBD + """
int main(void) {
""" + STORES + """	if (probe_kbd.default_ledflagstate != 0xA) return 21;
	if (probe_kbd.modeflags != 0x1F) return 22;
	if (probe_kbd.kbdmode != 5) return 23;
	if (probe_kbd.ledmode != 1) return 24;
	if (probe_kbd.ledflagstate != 6) return 25;
	if (vc_kbd_led(&probe_kbd, 2) != 1) return 26;
	if (vc_kbd_mode(&probe_kbd, 4) != 1) return 27;
	probe_kbd.modeflags = 0x0F;                  /* RMW keeps unit */
	if (probe_kbd.modeflags != 0x0F) return 28;
	if (vc_kbd_mode(&probe_kbd, 4) != 0) return 29;
	if (vc_kbd_mode(&probe_kbd, 3) != 1) return 30;
	if (probe_kbd.kbdmode != 5) return 31;       /* neighbour field kept */
	return 0;
}
""", "kbdr")
    assert rc == 0


# ---- witness 3: neighbour integrity around BOTH spilled members ---------

def test_kbd_struct_neighbour_integrity_and_adjacency():
    # Plain byte members keep their bytes across spilled stores, the
    # byte-2 run (ledmode+ledflagstate) survives the default_ledflagstate
    # spill RMW, and the ADJACENT global after_kbd is written and read
    # back (tip corrupted byte 2 through the stale-unit RMW).
    rc = both_run(KBD + """
int main(void) {
	unsigned char *p = (unsigned char *)&probe_kbd;
	int i;
	for (i = 0; i < (int)sizeof(probe_kbd); i++) p[i] = 0;
	after_kbd = 77;
""" + STORES + """
	probe_kbd.default_ledflagstate = 0x5;        /* second spill store */
	if (probe_kbd.lockstate != 0xA5) return 41;
	if (probe_kbd.slockstate != 0x5A) return 42;
	if (probe_kbd.ledmode != 1) return 43;
	if (probe_kbd.ledflagstate != 6) return 44;
	if (probe_kbd.default_ledflagstate != 5) return 45;
	if (probe_kbd.kbdmode != 5) return 46;
	if (probe_kbd.modeflags != 0x1F) return 47;
	if (after_kbd != 77) return 48;
	{   /* layout law: two spills push the struct to 5 bytes (gcc) */
	    if ((int)sizeof(probe_kbd) != 5) return 49;
	}
	return after_kbd;
}
""", "kbdn")
    assert rc == 77
