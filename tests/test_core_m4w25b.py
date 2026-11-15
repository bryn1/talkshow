# LINES reason: one wave of legs (M4 W2.5 ARM 2 — the attribute POSITION
# wall + `aligned(N)` layout ACT, plan-m4 v4 §7 AMENDMENT-3, MC 12557) —
# splitting would separate the position fix from the layout it unlocks.
r"""M4 W2.5 ARM 2 — the 167-file `__attribute__` position wall + aligned.

THE WALL (measured at tip, wall-postcommit2.jsonl): every attr first-blocker
answers `parse: expected an identifier, found '__attribute__'` — the
attribute sits BETWEEN the base type and the declarator IDENTIFIER, a
position the shipped M2 skip never visited. Kernel shapes (kernel-source
lines under the 160 mapped rows):
  88  `__u64 __attribute__((aligned(8))) flags;`   (#define __aligned_u64)
  67  `extern char __attribute__((__section__(".init.data"))) boot_command_line[];`
   2  `extern u64 notrace trace_clock_x86_tsc(void);`
   2  `extern void __compiletime_error("…") __compiletime_assert_NNN(void);`
   1  `u32 __pure crc32_le(...)`
plus `struct __attribute__((__packed__)) S {…}` (tag-prefix, 3 sites).

GCC 11.4 gnu89 -Os LAYOUT LAW (measured this card, fx/L*.c):
  member `aligned(N)`: RAISES placement + the struct align; member SIZE is
  the TYPE's size (union member al16: z@8, sizeof 16 — NOT 24); N below
  natural lowers NOTHING (`int i __attribute__((aligned(1)))` keeps int@4,
  sizeof 8); `aligned(32)` on char: 32 + pad = 64.
  object `aligned(N)`: emitted .align max(N, blcc's 8) — address%N==0.
  MULTI-DECLARATOR: `char __attribute__((aligned(8))) gc, gd;` RAISES BOTH
  (measured alignof gc == alignof gd == 8).
  auto (stack) local: gcc aligned(16) rides blcc's 16-ABI; gcc aligned(64)
  REALIGNS the frame (`andq $-64,%rsp` measured) — blcc's frame base is
  16: auto locals RAISE up to 16 and answer LOUD above 16 (gcc rc0: a
  named LOUD-DIV twin; the corpus volume is measured by the W2.5 sweep
  counting this wall name).
  bare `aligned` (no args) = max-fundamental 16 (measured alignof==16).
  args: aligned(3)/(−8)/non-constant → gcc rc1 ERROR twins; aligned(0) →
  gcc rc0 + WARNING, no effect (corpus volume 0 → blcc keeps the positive-
  constant LOUD wall, twin named below).
  typedef-of-TAG attr (`typedef guid_t efi_guid_t __attribute__((__aligned__
  (__alignof__(u32))));`, 8 streams): gcc attaches it to the NEW NAME only
  (tag untouched, size unchanged); blcc's M42 registration attaches to the
  TAG — layout-NEUTRAL on every corpus site (aligned(4) == guid_t natural,
  MEASURED equal both sides); the general law stays a NAMED deviation.
  typedef-of-SCALAR attr: blcc LOUD (volume 0 measured; gcc rc0 — LOUD-DIV
  twin named). `mode` attr: blcc LOUD — gcc WIDENS (mode(__word__) on int
  is sizeof 8, measured); volume 14/14 host-tier streams, 0 kernel.
Cast/sizeof TYPE position keeps the layout-class LOUD wall (no object to
lay out; gcc rc0 twin named — LOUD-DIV preserved, never silent).
"""
import os
import re
import subprocess
import sys

import pytest

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
STREAMS = os.path.join(REPO, "..", ".tmp", "m4-plan", "streams")


def blcc(args):
    e = dict(os.environ, PYTHONPATH=REPO)
    return subprocess.run([sys.executable, "-m", "blcc"] + list(args),
                          capture_output=True, text=True, timeout=600,
                          cwd=REPO, env=e)


def gcc(args):
    return subprocess.run(["gcc", "-std=gnu89", "-Os"] + list(args),
                          capture_output=True, text=True, timeout=120)


def twin(tmp_path, tag, src):
    s = tmp_path / (tag + ".c")
    s.write_text(src)
    gr = gcc(["-c", str(s), "-o", str(tmp_path / (tag + ".g.o"))])
    assert gr.returncode == 0, "oracle must accept ({}):\n{}".format(
        tag, gr.stderr)
    br = blcc(["-c", str(s), "-o", str(tmp_path / (tag + ".b.o"))])
    assert br.returncode == 0, "blcc must accept ({}):\n{}".format(
        tag, br.stderr)


def loud_pair(tmp_path, tag, src, frag, gcc_must="reject"):
    """gcc fact + blcc LOUD with the fragment — both postures measured."""
    s = tmp_path / (tag + ".c")
    s.write_text(src)
    gr = gcc(["-c", str(s), "-o", str(tmp_path / (tag + ".g.o"))])
    if gcc_must == "reject":
        assert gr.returncode != 0, "oracle must reject ({}):\n{}".format(
            tag, gr.stderr)
    else:
        assert gr.returncode == 0, "oracle must accept ({}):\n{}".format(
            tag, gr.stderr)
    br = blcc(["-c", str(s), "-o", str(tmp_path / (tag + ".b.o"))])
    assert br.returncode == 2 and frag in br.stderr, \
        "blcc must LOUD naming '{}' ({}):\n{}".format(frag, tag,
                                                      br.stderr[:400])


def run_pair(tmp_path, tag, src, expect=None):
    s = tmp_path / (tag + ".c")
    s.write_text(src)
    gx = tmp_path / (tag + ".gcc")
    gr = gcc([str(s), "-o", str(gx)])
    assert gr.returncode == 0, "oracle must build:\n" + gr.stderr
    bx = tmp_path / (tag + ".blcc")
    br = blcc([str(s), "-o", str(bx)])
    assert br.returncode == 0, "blcc must build:\n" + br.stderr
    g = subprocess.run([str(gx)], capture_output=True, text=True, timeout=30)
    b = subprocess.run([str(bx)], capture_output=True, text=True, timeout=30)
    assert g.returncode == b.returncode, \
        "run-pair diverge: gcc {} vs blcc {}".format(g.returncode,
                                                     b.returncode)
    if expect is not None:
        assert g.returncode == expect, \
            "oracle answers {}, leg expects {}".format(g.returncode, expect)
    return g.returncode


def asm_text(tmp_path, tag, src):
    """blcc asm text (the .align / directive law is a TEXT fact) — the
    shipped §6 idiom: `blcc <in> --emit-asm -o <o>` drops the asm beside
    the -o path as `<o>.s`."""
    s = tmp_path / (tag + ".c")
    s.write_text(src)
    o = tmp_path / (tag + ".o")
    br = blcc([str(s), "--emit-asm", "-o", str(o)])
    assert br.returncode == 0, "blcc --emit-asm must build:\n" + br.stderr
    with open(str(o) + ".s") as fh:
        return fh.read()


# ============ P1: the FIVE kernel position shapes (verbatim) ===============

def test_position_aligned_u64_member(tmp_path):
    # VERBATIM wall line (88 files): `__u64 __attribute__((aligned(8)))
    # flags;` — member raises placement per the measured law (o 8/12/16,
    # size 24, align 8).
    src = ("typedef unsigned long __u64;\n"
           "struct M { char a; __u64 __attribute__((aligned(8))) flags;\n"
           "           char c; long d; };\n"
           "int p1[__builtin_offsetof(struct M, flags) == 8 ? 1 : -1];\n"
           "int p2[__builtin_offsetof(struct M, c) == 16 ? 1 : -1];\n"
           "int p3[__builtin_offsetof(struct M, d) == 24 ? 1 : -1];\n"
           "int p4[sizeof(struct M) == 32 ? 1 : -1];\n")
    twin(tmp_path, "p_u64", src)


def test_position_initdata_extern(tmp_path):
    # VERBATIM wall line (67 files) — the __section__ extern PARSES (the
    # emission law is ARM 3's leg).
    src = ("extern char __attribute__((__section__(\".init.data\")))\n"
           "    boot_command_line[];\n"
           "int f(void){ return boot_command_line[0]; }\n")
    twin(tmp_path, "p_init", src)


def test_position_notrace_error_pure(tmp_path):
    # VERBATIM wall lines 2+2+1: fn attrs between the return type and the
    # declarator name — ignore-class, PARSE + DROP at this position too.
    src = ("typedef unsigned long u64;\ntypedef unsigned int u32;\n"
           "extern u64 __attribute__((notrace)) trace_clock_x86_tsc(void);\n"
           "extern void __attribute__((__error__(\"value doesn't fit\")))\n"
           "    __compiletime_assert_215(void);\n"
           "u32 __attribute__((__pure__)) crc32_le(u32 c, int b);\n"
           "int main(void){ return 0; }\n")
    twin(tmp_path, "p_fn", src)


def test_position_tag_prefix_packed(tmp_path):
    # `struct __attribute__((__packed__)) S { … }` (3 corpus sites): the
    # tag-PREFIX position joins the tag-tail law — the attr ACTS.
    src = ("struct __attribute__((__packed__)) S { char c; long l; };\n"
           "int p1[sizeof(struct S) == 9 ? 1 : -1];\n")
    twin(tmp_path, "p_tag", src)


# ============ P2: the aligned(N) layout law (fx/L*.c measured) ============

def test_aligned_member_law(tmp_path):
    # RAISES placement + struct align; member SIZE unchanged: union member
    # al16 keeps size 8 (z@8, sizeof 16 — NOT 24); ptr member al16: c@8,
    # size 16; al(1)/(2) lower NOTHING (int stays at 4, sizeof 8).
    src = (
        "struct Q { char a; char b __attribute__((aligned(32))); };\n"
        "struct U { union { char c; long l; } u __attribute__((__aligned__"
        "(16))); char z; };\n"
        "struct Pt { int *p __attribute__((aligned(16))); char c; };\n"
        "struct Lo { char a; int b __attribute__((aligned(1))); };\n"
        "int q1[sizeof(struct Q) == 64 ? 1 : -1];\n"
        "int q2[__alignof__(struct Q) == 32 ? 1 : -1];\n"
        "int u1[__builtin_offsetof(struct U, z) == 8 ? 1 : -1];\n"
        "int u2[sizeof(struct U) == 16 ? 1 : -1];\n"
        "int t1[__builtin_offsetof(struct Pt, c) == 8 ? 1 : -1];\n"
        "int t2[sizeof(struct Pt) == 16 ? 1 : -1];\n"
        "int l1[struct_Lo_guard(0)];\n"
        "int struct_Lo_guard(int);\n")
    # l1 replaced below — keep probe simple: Lo sizeof == 8 (aligned(1)
    # lowers nothing — int b stays at 4).
    src = src.replace("int l1[struct_Lo_guard(0)];\n"
                      "int struct_Lo_guard(int);\n",
                      "int l1[sizeof(struct Lo) == 8 ? 1 : -1];\n")
    twin(tmp_path, "p_law", src)


def test_aligned_object_align_emitted(tmp_path):
    # File-scope object: the emitted .align RAISES to max(N, 8) and the
    # linked address satisfies %64==0 (run-pair, same answer 0 both).
    txt = asm_text(tmp_path, "p_obj",
                   "int __attribute__((aligned(64))) gb;\n"
                   "char __attribute__((aligned(8))) gc, gd;\n"
                   "int main(void){ return (int)(gb + gc + gd); }\n")
    assert re.search(r"\.align 64\n+gb:", txt), \
        ".align 64 must precede gb:\n" + txt[:400]
    src = ("int __attribute__((aligned(64))) gb;\n"
           "char __attribute__((aligned(8))) gc, gd;\n"
           "int main(void){ unsigned long a = (unsigned long)&gb;\n"
           "  unsigned long b = (unsigned long)&gc, c = (unsigned long)&gd;\n"
           "  return (int)((a % 64 == 0) + (b % 8 == 0) + (c % 8 == 0) - 3);\n"
           "  }\n")     # 0 when all three addresses honor the alignment
    assert run_pair(tmp_path, "p_objr", src, expect=0) == 0


def test_aligned_local_slot16(tmp_path):
    # auto local: blcc's frame is 16-aligned at every call (§6 law) — an
    # aligned(16) local honors 16 through the slot RAISE. gcc measured rc0.
    src = ("int main(void){ int x __attribute__((aligned(16)));\n"
           "  unsigned long a = (unsigned long)&x;\n"
           "  x = 1; return (int)(a % 16 == 0 && x == 1); }\n")
    assert run_pair(tmp_path, "p_loc", src, expect=1) == 1


def test_aligned_local_beyond16_loud(tmp_path):
    # LOUD-DIV TWIN (measured): gcc REALIGNS the frame (andq $-64,%rsp,
    # rc0); blcc's frame base is the 16-ABI — auto storage above 16 is
    # LOUD, never a silently-misaligned slot. static storage is FINE at
    # any N (ARM 3 .align leg covers it).
    loud_pair(tmp_path, "p_loc64",
              "int main(void){ int x __attribute__((aligned(64)));\n"
              "  x = 1; return x; }\n",
              "aligned", gcc_must="accept")


def test_aligned_bare_and_expr_args(tmp_path):
    # bare `aligned` = 16 (measured); the ARGUMENT rides the fold engines:
    # `__aligned__(__alignof__(long long))` == aligned(8).
    src = ("struct BA { char c; int i __attribute__((aligned)); };\n"
           "struct AA { char c; long v __attribute__((__aligned__"
           "(__alignof__(long long)))); };\n"
           "int p1[__alignof__(struct BA) == 16 ? 1 : -1];\n"
           "int p2[sizeof(struct BA) == 32 ? 1 : -1];\n"
           "int p3[__builtin_offsetof(struct AA, v) == 8 ? 1 : -1];\n"
           "int p4[sizeof(struct AA) == 16 ? 1 : -1];\n")
    twin(tmp_path, "p_bare", src)


def test_aligned_arg_twins_loud(tmp_path):
    # gcc rc1 twins: aligned(3) (not power-of-two), aligned(-8), and a
    # non-constant argument all ERROR on the oracle; blcc LOUDs naming
    # aligned. aligned(0): gcc rc0+WARNING-noop, corpus volume 0 — blcc
    # keeps the positive-constant LOUD wall (named twin below).
    loud_pair(tmp_path, "p_a3", "int x __attribute__((aligned(3)));\n"
              "int main(void){return x;}\n", "aligned")
    loud_pair(tmp_path, "p_aneg", "int x __attribute__((aligned(-8)));\n"
              "int main(void){return x;}\n", "aligned")
    # aligned(0): the oracle ANSWERS rc0 + warning (no effect, measured);
    # corpus volume 0 (measured over the streams) — blcc keeps the
    # positive-constant LOUD wall (a LOUD-DIV twin, never silent).
    loud_pair(tmp_path, "p_a0", "int x __attribute__((aligned(0)));\n"
              "int main(void){return x;}\n", "aligned", gcc_must="accept")


def test_attr_in_cast_type_stays_loud(tmp_path):
    # LOUD-DIV (measured gcc rc0): a layout attr inside a CAST/sizeof TYPE
    # has no object to lay out — blcc keeps it LOUD, never silent.
    loud_pair(tmp_path, "p_cast",
              "long f(long p){ return (long)(int __attribute__((aligned(8))))"
              " p; }\n", "aligned", gcc_must="accept")


# ============ P3: typedef law corners (measured, volume-pinned) ===========

def test_typedef_of_tag_efi_verbatim(tmp_path):
    # VERBATIM 8-stream line. gcc attaches the attr to the NEW name (tag
    # untouched); blcc's M42 registration attaches to the TAG — for THIS
    # shape the values are IDENTICAL (aligned(__alignof__(u32)) == the
    # tag's natural 4, measured): sizes and alignments equal on both
    # sides, the general typedef-of-tag law stays the NAMED deviation.
    src = ("typedef unsigned int u32;\ntypedef unsigned short u16;\n"
           "typedef unsigned char u8;\n"
           "typedef struct { u32 data1; u16 data2; u16 data3; u8 data4[8]; }"
           " guid_t;\n"
           "typedef guid_t efi_guid_t __attribute__((__aligned__("
           "__alignof__(u32))));\n"
           "int p1[sizeof(efi_guid_t) == 16 ? 1 : -1];\n"
           "int p2[__alignof__(efi_guid_t) == 4 ? 1 : -1];\n"
           "struct V { efi_guid_t g; char c; };\n"
           "int p3[sizeof(struct V) == 20 ? 1 : -1];\n")
    twin(tmp_path, "p_efi", src)


def test_typedef_of_scalar_attr_loud(tmp_path):
    # LOUD-DIV twin, volume-0 (measured over all 706 streams: every
    # typedef+aligned line is the guid_t shape; scalar-typedef attrs 0).
    loud_pair(tmp_path, "p_tdef",
              "typedef long al64_t __attribute__((aligned(64)));\n"
              "al64_t g; int main(void){return (int)g;}\n",
              "aligned", gcc_must="accept")


def test_mode_attr_loud(tmp_path):
    # gcc WIDENS: `typedef int register_t __attribute__ ((__mode__
    # (__word__)));` is sizeof 8 (measured) — a silent strip would LIE.
    # Volume: 14 sites / 14 files, ALL arch/x86/tools host-tier (0 kernel
    # sites, host tier is gcc-delegated per §0.1). blcc: LOUD, naming mode.
    loud_pair(tmp_path, "p_mode",
              "typedef int register_t __attribute__ ((__mode__ (__word__)));\n"
              "register_t g; int main(void){return (int)g;}\n",
              "mode", gcc_must="accept")


# ============ P4: corpus legs — the attr first-blocker must MOVE ===========

def _clean_i(path, tmp_path, tag):
    clean = tmp_path / (tag + ".c")
    su = re.compile(r"\b(0[xX][0-9a-fA-F]+|[0-9]+)[uU][lL]{0,2}\b")
    sr = re.compile(r"\b(0[xX][0-9a-fA-F]+|[0-9]+)[lL][uU][lL]?\b")
    sl = re.compile(r"\b(0[xX][0-9a-fA-F]+|[0-9]+)[lL]+\b")
    with open(path, encoding="utf-8", errors="replace") as fh, \
            open(clean, "w", encoding="utf-8") as out:
        for line in fh:
            if line.startswith("#"):
                continue
            out.write(sl.sub(r"\1", sr.sub(r"\1", su.sub(r"\1", line))))
    return clean


@pytest.mark.skipif(not (os.environ.get("KERNEL_510")
                         and os.path.isdir(STREAMS)),
                    reason="kernel tier + pinned streams corpus required")
@pytest.mark.parametrize("stream", [
    "arch_x86_events_amd_core.c.i",    # RED-at-tip: __aligned_u64 member
    "init_main.c.i",                   # RED-at-tip: __initdata extern+def
    "lib_crc32.c.i" if os.path.exists(
        os.path.join(STREAMS, "lib_crc32.c.i")) else "lib_cmdline.c.i",
])
def test_corpus_attr_wall_is_dead(stream, tmp_path):
    # The `expected an identifier, found '__attribute__'` first-blocker
    # (167 files) FALLS: the next wall may honestly answer, but THE
    # ATTR-Identifier WALL must not.
    clean = _clean_i(os.path.join(STREAMS, stream), tmp_path, "corpw25b")
    r = blcc(["-c", str(clean), "-o", str(tmp_path / "corpw25b.o")])
    assert "found '__attribute__'" not in r.stderr, \
        "{} still hits the attr-position wall:\n{}".format(
            stream, r.stderr[:600])
