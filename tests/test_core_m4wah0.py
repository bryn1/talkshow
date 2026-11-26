# M4 W-AH WINDOW LAW — the bsup PRODUCER passes the packed field's OWN
# fold window (MC 12404.2.150 / job 12839, card 12839). One concern: the
# exit-encoded postures the one-home producer hunk moves, the honest
# refusals it must leave LOUD, and the corpus pair it lands.
r"""M4 W-AH COMMIT-WFW — the static packed bitfield fold rides the field's
OWN window `ceil((bit+w)/8)` at the bsup PRODUCER (data.py struct arm), the
SAME span expression the shipped W-X access law rides (expr_codegen read
`nb = (bit + w + 7) // 8`, store arm, read-modify arm). Under packed the
layout cursor is bit-contiguous (the shipped W-F law), so the DECLARED unit
size is the WRONG window: it walked off the shrunk extent — the base ICE
`IndexError: list index out of range` at data.py:369 is a WINDOW-ARITHMETIC
failure, not a guard failure (sims card 12838 ICE-traceback receipts).
`_bf_merge` is UNCHANGED: it already folds arbitrary (uoff, bit, w, ub, v)
windows little-endian and its label-overlap refusal keeps its teeth.

Battery idiom: the process EXIT CODE is the answer (gcc REC twin vs blcc,
`-no-pie`, run-encoded — the shipped W-W/W-X/W-AG law-battery idiom). Row
bodies are VERBATIM transplants of the sims 50-row law battery (card 12838,
all 50 gcc-REC-clean rows; the table STANDS — this repo battery carries the
representative moved faces + the blast controls).
"""
import os
import subprocess
import sys

import pytest

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
REPO = os.environ.get("BLCC_REPO", ROOT)
sys.path.insert(0, REPO)
TMP = "/dev/shm/m4wah0_%s_%d" % (os.environ.get("M4WAH_TAG", "x"), os.getpid())
GCC_REC = ["-std=gnu89", "-Os", "-mno-sse", "-mno-sse2", "-mno-80387",
           "-fno-stack-protector", "-fno-pic"]
MAIN = "\nint answer(void);\nint main(void) { return answer(); }\n"

PRE = {
    "A": """typedef unsigned int u32; typedef unsigned char u8; typedef unsigned short u16;
struct IO_APIC_route_entry {
 u32 vector : 8, delivery_mode : 3, dest_mode : 1, delivery_status : 1,
     polarity : 1, irr : 1, trigger : 1, mask : 1, __reserved_2 : 15;
 u32 __reserved_3 : 24, dest : 8;
} __attribute__ ((packed));
union entry_union { struct { u32 w1, w2; }; struct IO_APIC_route_entry entry; };
""",
    "B": """typedef unsigned short u16; typedef unsigned int u32;
struct desc_struct {
 u16 limit0;
 u16 base0;
 u16 base1: 8, type: 4, s: 1, dpl: 2, p: 1;
 u16 limit1: 4, avl: 1, l: 1, d: 1, g: 1, base2: 8;
} __attribute__((packed));
struct gdt_page { struct desc_struct gdt[16]; };
""",
    "C": """typedef unsigned short u16; typedef unsigned int u32;
struct idt_bits { u16 ist : 3, zero : 5, type : 5, dpl : 2, p : 1; } __attribute__((packed));
struct idt_data { unsigned int vector; unsigned int segment;
 struct idt_bits bits; const void *addr; };
#define GATE_INTERRUPT 0xE
""",
    "E": """typedef unsigned int uint; typedef signed int sint;
struct printf_spec { uint type:8; sint field_width:24; uint flags:8;
 uint base:8; sint precision:16; } __attribute__((__packed__));
""",
    "W": """typedef unsigned int u32; typedef unsigned long long ull;
struct w8  { u32 x:8;  } __attribute__((packed));
struct w9  { u32 x:9;  } __attribute__((packed));
struct cx  { u32 a:4, b:30; } __attribute__((packed));
struct p12 { u32 a:12, b:12; } __attribute__((packed));
struct bt  { u32 a:2; _Bool f:1; } __attribute__((packed));
struct u64w { unsigned long a:60, b:8; } __attribute__((packed));
""",
}

# rows the WINDOW law moves WALL -> PAIR (sims 50-row table, VERBATIM
# bodies; `*_guard` rows carry the trailing `gd = 0x5A` overrun sentinel):
ROWS = {
    "whA01_verbatim_local_union_mask": ("A", """
 union entry_union eu = { .entry.mask = 1 };
 return (int)((eu.entry.mask*3 + eu.entry.vector*7 + eu.entry.delivery_mode*11
   + (eu.w1 & 255u)*13 + ((eu.w1 >> 8) & 255u)*17 + ((eu.w1 >> 16) & 255u)*19
   + ((eu.w1 >> 24) & 255u)*23 + (eu.w2 & 255u)*29 + ((eu.w2 >> 8) & 255u)*31
   + ((eu.w2 >> 16) & 255u)*37 + ((eu.w2 >> 24) & 255u)*41) % 251);"""),
    "whA02_local_all_fields": ("A", """
 union entry_union eu = { .entry = { .vector = 0x21, .delivery_mode = 5,
   .dest_mode = 1, .delivery_status = 1, .polarity = 1, .irr = 1,
   .trigger = 1, .mask = 1, .dest = 0x0F } };
 return (int)((eu.entry.vector + eu.entry.delivery_mode*3 + eu.entry.mask*7
   + (eu.w1 & 255u)*11 + ((eu.w1 >> 8) & 255u)*13 + ((eu.w1 >> 16) & 255u)*17
   + ((eu.w1 >> 24) & 255u)*19 + (eu.w2 & 255u)*23 + ((eu.w2 >> 8) & 255u)*29
   + ((eu.w2 >> 16) & 255u)*31 + ((eu.w2 >> 24) & 255u)*37) % 251);"""),
    "whA07_compound_lit_assign": ("E", """
 struct printf_spec sp;
 sp = (struct printf_spec){ .flags = 32 | 16, .base = 16 };
 return (int)((sp.flags + sp.base*3 + sp.type*7 + sp.field_width*11
   + sp.precision*13) % 251);"""),
    "whA11_local_nonpacked_control": ("W", """
 struct np { u32 a:8, b:8; } x = { .a = 1, .b = 2 };
 return (int)((x.a*3 + x.b*7) % 251);"""),
    "whB05_w_exact8": ("W", """
 static struct w8 s = { .x = 0xAB };
 static unsigned char gd = 0x5A;
 return (int)((s.x + gd*3) % 251);"""),
    "whB06_w9_ice_shape_guard": ("W", """
 static struct w9 s = { .x = 0x155 };
 static unsigned char gd = 0x5A;
 return (int)((s.x % 251)*3 + gd*7 % 251);"""),
    "whB07_cross4_30_global_guard": ("W", """
 static struct cx s = { .a = 5, .b = 0x3FFFFFFu };
 static unsigned char gd = 0x5A;
 return (int)((s.a*3 + (s.b & 255u)*7 + ((s.b >> 15) & 255u)*11
   + ((s.b >> 22) & 255u)*13 + gd*17) % 251);"""),
    "whB08_p12_pair": ("W", """
 static struct p12 s = { .a = 0xFFF, .b = 0x123 };
 return (int)(((s.a % 251)*3 + (s.b % 251)*7 + (s.b >> 4)*11) % 251);"""),
    "whB10_bool_norm_packed": ("W", """
 static struct bt s = { .a = 3, .f = 2 };
 return (int)((s.a*3 + s.f*7) % 251);"""),
    "whB12_u64_w9_guard": ("W", """
 static struct u64w s = { .a = 0xF00000000ull, .b = 9 };
 static unsigned char gd = 0x5A;
 return (int)((((s.a >> 32) & 255ull)*3 + (s.a & 255ull)*7 + s.b*11
   + gd*13) % 251);"""),
    "whB13_nested_outer": ("B", """
 struct outer { int tag; struct desc_struct d; };
 static struct outer o = { .tag = 7, .d = { .type = 0xC, .p = 1 } };
 return (int)((o.tag*3 + o.d.type*7 + o.d.p*11 + o.d.base2*13) % 251);"""),
    "whB14_lastwins_packed": ("B", """
 static struct desc_struct one = { .type = 1, .type = 9 };
 return (int)(one.type % 251);"""),
    "whB15_plain_array_no_wrapper": ("B", """
 static struct desc_struct sg[2] = { [0].p = 1, [1].type = 3 };
 return (int)((sg[0].p*3 + sg[1].type*7 + sg[0].type*11 + sg[1].p*13) % 251);"""),
    "whC01_verbatim_early_idts": ("C", """
 void asm_exc_debug(void) {} void asm_exc_int3(void) {}
 int answer(void)
 {
 static const __attribute__((__section__(".init.rodata"))) struct idt_data early_idts[] = {
  { .vector = 1, .bits.ist = 0, .bits.type = GATE_INTERRUPT, .bits.dpl = 0x0,
    .bits.p = 1, .addr = asm_exc_debug, .segment = (2*8), },
  { .vector = 3, .bits.ist = 0, .bits.type = GATE_INTERRUPT, .bits.dpl = 0x3,
    .bits.p = 1, .addr = asm_exc_int3, .segment = (2*8), } };
 return (int)((early_idts[0].vector*3 + early_idts[0].bits.type*7
   + early_idts[0].bits.p*11 + early_idts[0].bits.dpl*13
   + early_idts[0].segment*17 + early_idts[1].bits.dpl*19
   + early_idts[1].vector*23 + (early_idts[0].addr != 0 ? 29 : 0)
   + (early_idts[1].addr != 0 ? 31 : 0) + early_idts[0].bits.ist*37
   + early_idts[0].bits.zero*41) % 251);
 }
""", True),
    "whC02_nested_dotted_only": ("C", """
 static struct idt_data e = { .bits.type = 0xE, .bits.p = 1 };
 return (int)((e.bits.type*3 + e.bits.p*7 + e.vector*11 + e.bits.ist*13
   + e.bits.zero*17) % 251);"""),
    "whC03_nested_brace_face": ("C", """
 static struct idt_data e = { .vector = 2, .bits = { .type = 0xE, .p = 1 } };
 return (int)((e.bits.type*3 + e.bits.p*7 + e.vector*11 + e.bits.dpl*13) % 251);"""),
    "whZ01_nonpacked_global_control": ("W", """
 struct npg { u32 a:8, b:8; } __attribute__((aligned(4))) g = { .a = 3, .b = 9 };
 return (int)((g.a*3 + g.b*7) % 251);"""),
    "whZ02_boolnorm_nonpacked": ("W", """
 struct bb { _Bool f:1; unsigned g:3; } s = { .f = 2, .g = 5 };
 return (int)((s.f*3 + s.g*7) % 251);"""),
}


def _src(name):
    ent = ROWS[name]
    if len(ent) > 2:              # whole-function row (the C01 idiom)
        return PRE[ent[0]] + "\n" + ent[1]
    return PRE[ent[0]] + "\nint answer(void)\n{\n" + ent[1] + "\n}\n"


def _build(src, tag, cc):
    os.makedirs(TMP, exist_ok=True)
    c = os.path.join(TMP, tag + ".c")
    with open(c, "w") as fh:
        fh.write(src + MAIN)
    if cc == "gcc":
        exe = os.path.join(TMP, tag + ".gcc")
        cmd = ["gcc", "-no-pie"] + GCC_REC + [c, "-o", exe]
    else:
        o = os.path.join(TMP, tag + ".blcc.o")
        exe = os.path.join(TMP, tag + ".blcc")
        b = subprocess.run([sys.executable, "-m", "blcc", "-c", c, "-o", o],
                           capture_output=True, text=True,
                           env=dict(os.environ, PYTHONPATH=REPO), cwd=REPO)
        if b.returncode != 0:
            return b, None
        cmd = ["gcc", "-no-pie", "-o", exe, o]
    r = subprocess.run(cmd, capture_output=True, text=True)
    return r, exe


@pytest.mark.parametrize("name", sorted(ROWS))
def test_wf_battery_exit_is_the_answer(name):
    src = _src(name)
    rg, gexe = _build(src, name, "gcc")
    assert rg.returncode == 0, "gcc twin must build:\n" + rg.stderr
    gx = subprocess.run([gexe], capture_output=True, timeout=60).returncode
    rb, bexe = _build(src, name, "blcc")
    assert rb.returncode == 0, (
        "%s: blcc refused rc=%d — the {WFW} wall the producer window law "
        "lands at this card:\n%s" % (name, rb.returncode,
                                     (rb.stdout + rb.stderr)[:300]))
    bx = subprocess.run([bexe], capture_output=True, timeout=60).returncode
    assert bx == gx, (
        "%s: SILENT/VALUE divergence blcc %d vs gcc %d — the window is "
        "the field's OWN ceil((bit+w)/8) bytes, little-endian (q2/q7 "
        "classes: floor windows and BE windows stay SILENT-WRONG)"
        % (name, bx, gx))


# ---- honest refusals KEPT LOUD (the sims' NAMED stub-boundary faces) ------


def test_wf_union_twin_stays_loud(tmp_path):
    # The codegen UNION twin (codegen.py:1268) was deliberately NOT opened
    # (sims honest-stub refusal, volume 0 in this corpus; whA08 pins it
    # LOUD at the wfw arm). If this leg ever flips, a second door opened
    # beside the ship set — that is not this card's law.
    src = PRE["W"] + """
int answer(void)
{
\tunion { u32 x:3; } __attribute__((packed)) u = { .x = 5 };
\treturn (int)((u.x*3 + 7) % 251);
}
"""
    p = tmp_path / "wau.c"
    p.write_text(src)
    br = subprocess.run([sys.executable, "-m", "blcc", "-c", str(p),
                         "-o", str(tmp_path / "wau.o")],
                        capture_output=True, text=True,
                        env=dict(os.environ, PYTHONPATH=REPO), cwd=REPO)
    assert br.returncode == 2, (
        "the codegen UNION twin moved off LOUD (rc=%d) — NAMED refusal, "
        "not this card:\n%s" % (br.returncode, br.stderr[:300]))
    assert "packed bitfield member initializer" in br.stderr, \
        "the union twin moved off its sentence: " + br.stderr[:300]


def test_wf_int128_unit_stays_loud(tmp_path):
    # `__int128`-unit fields stay LOUD (W-X guard twin; whB16 pins it at
    # the wfw arm): the extraction model does not exist, LOUD by name.
    src = PRE["W"] + """
 struct q128 { __int128 x:5; } __attribute__((packed));
 static struct q128 s = { .x = 1 };
 int answer(void) { return (int)(((int)s.x*3 + 7) % 251); }
"""
    p = tmp_path / "w128.c"
    p.write_text(src)
    br = subprocess.run([sys.executable, "-m", "blcc", "-c", str(p),
                         "-o", str(tmp_path / "w128.o")],
                        capture_output=True, text=True,
                        env=dict(os.environ, PYTHONPATH=REPO), cwd=REPO)
    assert br.returncode == 2, (
        "the __int128 unit LOUD moved (rc=%d):\n%s"
        % (br.returncode, br.stderr[:300]))
    assert "no extraction model" in br.stderr, \
        "the int128 LOUD moved off its sentence: " + br.stderr[:300]


# ---- kernel tier: the five corpus streams LAND, the control does not move -

from test_core_m4w1 import STREAMS                       # noqa: E402
from test_core_m4w25b import _clean_i                    # noqa: E402

WF_FIVE = ["arch_x86_kernel_cpu_common.c.i",
           "arch_x86_kernel_apic_io_apic.c.i",
           "arch_x86_kernel_head64.c.i",
           "arch_x86_kernel_idt.c.i",
           "lib_vsprintf.c.i"]


@pytest.mark.skipif(not (os.environ.get("KERNEL_510")
                         and os.path.isdir(STREAMS)),
                    reason="kernel tier + pinned streams corpus required")
@pytest.mark.parametrize("stream", WF_FIVE)
def test_wf_five_streams_land(stream, tmp_path):
    clean = _clean_i(os.path.join(STREAMS, stream), tmp_path, "wah")
    o = tmp_path / "wah.o"
    r = subprocess.run([sys.executable, "-m", "blcc", "-c", str(clean),
                        "-o", str(o)], capture_output=True, text=True,
                       env=dict(os.environ, PYTHONPATH=REPO), cwd=REPO)
    assert r.returncode == 0, (
        "%s must LAND at W-AH (the producer window law) — first wall:\n%s"
        % (stream, next((ln for ln in (r.stdout + r.stderr).splitlines()
                         if ln.strip()), "(no output)")))
    assert o.exists() and o.stat().st_size > 0, "empty object"


@pytest.mark.skipif(not (os.environ.get("KERNEL_510")
                         and os.path.isdir(STREAMS)),
                    reason="kernel tier + pinned streams corpus required")
def test_wf_nonpacked_control_unmoved(tmp_path):
    # lib_bitmap.c.i: the non-packed bitfield control — accepted rc0 at
    # tip AND ship (sims §1); zero collateral at stream grade.
    clean = _clean_i(os.path.join(STREAMS, "lib_bitmap.c.i"), tmp_path,
                     "wahctl")
    r = subprocess.run([sys.executable, "-m", "blcc", "-c", str(clean),
                        "-o", str(tmp_path / "wahctl.o")],
                       capture_output=True, text=True,
                       env=dict(os.environ, PYTHONPATH=REPO), cwd=REPO)
    assert r.returncode == 0, (
        "the non-packed control moved (collateral!):\n"
        + next((ln for ln in (r.stdout + r.stderr).splitlines()
                if ln.strip()), "(no output)"))
