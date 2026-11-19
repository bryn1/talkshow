# LINES reason: one wave of legs (M4 W-Q COMMIT-1 - block-scope TAG
# scope, card 12404.2.91): every leg is an arm of ONE tag-identity law;
# a split would separate the witness from its guards.
r"""M4 W-Q COMMIT-1 - BLOCK-SCOPE TAGS (plan AMENDMENT-18; card
12404.2.91). THE LAW (measured at gcc -Os: 19-row q-table beyond the
gate's b01-b15, .tmp/m4-wq/out/q-laws-tip.txt): a block-scope NAMED tag
gets a MINTED IDENTITY (`name#blk@file:line#n`) - it SHADOWS, never
completes, the outer tag (q01b: the file tag stays INCOMPLETE after an
inner definition, gcc rc1); layout keys on the IDENTITY, so ONE name
carries TWO live layouts in one TU (q05/q06/b13/b14) without mis-sizing
a live outer object (b15); a block reference to a NEW name declares a
block-scope tag (q09: the LATER file definition is a DIFFERENT type);
forward-decl arms complete IN THE SAME BLOCK (q08); block enum
constants are block-scoped and RESTORE on scope exit (q10 + LOUD q10b);
for-init tags stay §5-LOUD (q16, named twin, volume 0). THE WITNESS:
the walk wall arch/x86/include/asm/special_insns.h:225:11 - clwb's
`volatile struct { char x[64]; } *p` (anonymous block struct inside a
static-inline body) - VERBATIM from the pinned stream
arch_x86_kernel_process.c.i (own-hands slice, lines 9452-9464).
"""
import os
import re
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.environ.get("BLCC_REPO") or os.path.dirname(HERE)
TMP = "/dev/shm"


def blcc(args):
    return subprocess.run([sys.executable, "-m", "blcc"] + args,
                          capture_output=True, text=True, cwd=REPO,
                          env={"PYTHONPATH": REPO, "PATH": "/usr/bin:/bin"})


def gcc(args):
    return subprocess.run(["gcc", "-std=gnu89"] + args,
                          capture_output=True, text=True,
                          env={"PATH": "/usr/bin:/bin"})


REC = ["-Os", "-mno-sse", "-mno-mmx", "-mno-sse2", "-mno-80387",
       "-fno-stack-protector", "-fno-pic"]


def _run(p):
    return subprocess.run([p], env={"PATH": "/usr/bin:/bin"}).returncode


def _pair(tag, src, want=None, gcc_ok=True):
    """House idiom (test_core_m4wp1): both compilers; blcc object linked
    by gcc -no-pie; RUN; returns (grc, brc, gex, bex, btxt)."""
    c = "%s/wq1_%s.c" % (TMP, tag)
    open(c, "w").write(src)
    g = gcc(REC + [c, "-no-pie", "-o", "%s/wq1_%s.g" % (TMP, tag)])
    if gcc_ok:
        assert g.returncode == 0, "probe must be valid C: " + g.stderr
    gex = _run("%s/wq1_%s.g" % (TMP, tag)) if g.returncode == 0 else None
    o = "%s/wq1_%s.b.o" % (TMP, tag)
    b = blcc(["-c", c, "-o", o])
    bex = btxt = None
    if b.returncode == 0:
        assert gcc([o, "-no-pie", "-o", "%s/wq1_%s.b" % (TMP, tag)]
                   ).returncode == 0, "link must work"
        bex = _run("%s/wq1_%s.b" % (TMP, tag))
        blcc(["-c", c, "--emit-asm", "-o", "%s/wq1_%s.bt" % (TMP, tag)])
        btxt = open("%s/wq1_%s.bt.s" % (TMP, tag)).read()
    if want is not None:
        assert (gex, bex) == (want, want), \
            "%s: value pair %s vs %s" % (tag, gex, bex)
    return g.returncode, b.returncode, gex, bex, btxt


# VERBATIM (own-hands slice) of the pinned-corpus witness: the post-pp
# `clwb` definition of arch/x86_kernel_process.c.i lines 9452-9464 -
# special_insns.h:225:11, the walk's FIRST RED at the W-P close tree.
CLWB = r"""static inline __attribute__((__gnu_inline__)) __attribute__((__unused__)) __attribute__((no_instrument_function)) void clwb(volatile void *__p)
{
 volatile struct { char x[64]; } *p = __p;

 asm volatile("# ALT: oldinstr2\n" "661:\n\t" ".byte " "0x3e" "; clflush (%[pax])" "\n662:\n" "# ALT: padding2\n" ".skip -((" "((" "665""1""f-""664""1""f" ") ^ (((" "665""1""f-""664""1""f" ") ^ (" "665""2""f-""664""2""f" ")) & -(-((" "665""1""f-""664""1""f" ") < (" "665""2""f-""664""2""f" ")))))" " - (" "662b-661b" ")) > 0) * " "(" "((" "665""1""f-""664""1""f" ") ^ (((" "665""1""f-""664""1""f" ") ^ (" "665""2""f-""664""2""f" ")) & -(-((" "665""1""f-""664""1""f" ") < (" "665""2""f-""664""2""f" ")))))" " - (" "662b-661b" ")), 0x90\n" "663" ":\n" ".pushsection .altinstructions,\"a\"\n" " .long 661b - .\n" " .long " "664""1""f - .\n" " .word " "( 9*32+23)" "\n" " .byte " "663""b-661b" "\n" " .byte " "665""1""f-""664""1""f" "\n" " .long 661b - .\n" " .long " "664""2""f - .\n" " .word " "( 9*32+24)" "\n" " .byte " "663""b-661b" "\n" " .byte " "665""2""f-""664""2""f" "\n" ".popsection\n" ".pushsection .altinstr_replacement, \"ax\"\n" "# ALT: replacement " "1" "\n" "664""1"":\n\t" ".byte 0x66; clflush (%[pax])" "\n" "665""1" ":\n" "# ALT: replacement " "2" "\n" "664""2"":\n\t" ".byte 0x66, 0x0f, 0xae, 0x30" "\n" "665""2" ":\n" ".popsection\n"





  : [p] "+m" (*p)
  : [pax] "a" (p));
}
"""

WMAIN = """
char wqbuf[64];
int main(void){ wqbuf[0] = 3; wqbuf[63] = 4; clwb(wqbuf);
                return (wqbuf[0] + wqbuf[63]) % 100; }
"""


# -- THE WITNESS: special_insns.h:225 clwb, RED-first at tip 87f6c2e ----

def test_wq1_clwb_witness_pair():
    """RED AT TIP (`struct declaration in block scope` at :225); after:
    both compilers rc0, both RUN 7 (the clwb flush old-path executes)."""
    g, b, gex, bex, btxt = _pair("clwb", CLWB + WMAIN, want=7)
    assert b == 0, b


def test_wq1_clwb_alt_words():
    """The walk object's own ALTERNATIVE_2 asm: the .altinstructions
    section of the blcc object is BYTE-IDENTICAL to gcc's (the feature
    words 9*32+23/24 = 311/312 evaluate at the assembler on both trees
    - the W-P gate's byte-anchor idiom)."""
    src = CLWB + WMAIN
    open("/dev/shm/wq1_alt.c", "w").write(src)
    assert gcc(REC + ["-c", "/dev/shm/wq1_alt.c", "-o",
                      "/dev/shm/wq1_alt.g.o"]).returncode == 0
    assert blcc(["-c", "/dev/shm/wq1_alt.c", "-o",
                 "/dev/shm/wq1_alt.b.o"]).returncode == 0

    def alt(obj):
        r = subprocess.run(["objdump", "-s", "-j", ".altinstructions", obj],
                           capture_output=True, text=True)
        body = r.stdout.split("Contents of section")[-1]
        return "".join("".join(ln.split()[1:])
                       for ln in body.splitlines()[1:]
                       if re.match(r"^\s[0-9a-f]{4,8}\s", ln))
    ga, ba = alt("/dev/shm/wq1_alt.g.o"), alt("/dev/shm/wq1_alt.b.o")
    assert ga and ga == ba, \
        ".altinstructions bytes diverge: gcc=%s blcc=%s" % (ga, ba)
    assert "3701" in ba and "3801" in ba, "feature words 311/312 missing"


def test_wq1_anon_block_sizeof():
    """sizeof of the anonymous block struct IS 64 (the clwb window)."""
    _pair("asz", "int main(void){ struct S { char x[64]; };\n"
                  "return (int)sizeof(struct S) % 100; }\n", want=64)


def test_wq1_clwb_spliced_no_copy():
    """W-P x W-Q: clwb called twice in STATEMENT position is fully
    spliced - the standalone copy is gone, values still pair."""
    main = ("char wqbuf[64];\nint main(void){ wqbuf[0]=3; wqbuf[63]=4;"
            " clwb(wqbuf); clwb(wqbuf); return (wqbuf[0]+wqbuf[63]) % 100; }\n")
    _g, b, _ge, _be, btxt = _pair("clwb2", CLWB + main, want=7)
    assert b == 0
    assert not re.search(r"^clwb:", btxt, re.M), \
        "fully-spliced clwb kept a standalone copy"


# -- THE MEASURED LAW TABLE (q01..q16b; .tmp/m4-wq/qlaws.py at gcc -Os) --

def test_wq1_q01_shadow_new_type():
    _pair("q01", "struct S1;\nint g1;\nvoid f(void){ struct S1 "
          "{ char a[8]; } s; g1 = (int)sizeof(s); }\n"
          "int main(void){ f(); return g1 % 100; }\n", want=8)


def test_wq1_q01b_file_tag_stays_incomplete():
    """gcc rc1: the block definition does NOT complete the file tag."""
    g, b, _ge, _be, _bt = _pair(
        "q01b", "struct S1;\nint g1, g2;\nvoid f(void){ struct S1 "
        "{ char a[8]; } s; g1 = (int)sizeof(s); }\n"
        "int main(void){ f(); g2 = sizeof(struct S1); return 0; }\n",
        gcc_ok=False)
    assert g != 0 and b != 0


def test_wq1_q02_tentative_merge_later_file_completion():
    _pair("q02", "struct S2 gobj;\nint gtot;\nvoid f(void){ struct S2 "
          "{ int a; int b; } s; s.a = 1; gtot = (int)sizeof(s); }\n"
          "struct S2 { int a; };\n"
          "int eat(void){ gobj.a = 40; return gobj.a + "
          "(int)sizeof(struct S2); }\n"
          "int main(void){ f(); return gtot == 8 ? eat() : 1; }\n",
          want=44)


def test_wq1_q03_typedef_vs_tag_namespaces():
    """struct T3 SHADOWS; typedef T3 keeps the FILE layout (8 + 4)."""
    _pair("q03", "struct T3 { int a; };\ntypedef struct T3 T3;\n"
          "int main(void){ struct T3 { char c[8]; } s; T3 t;\n"
          "return (int)(sizeof(s) + sizeof(t)) % 100; }\n", want=12)


def test_wq1_q04_restore_on_scope_exit():
    """RUN-PAIR of the RESTORE law: 16 INSIDE the block (also in a
    nested block), 4 AFTER it (the file layout again)."""
    _pair("q04", "struct S4 { int a; };\nint g1b, g2b;\n"
          "void f(void){ struct S4 { char x[16]; }; "
          "g1b = sizeof(struct S4); { g2b = sizeof(struct S4); } }\n"
          "int h(void){ return sizeof(struct S4); }\n"
          "int main(void){ f(); return g1b == 16 && g2b == 16 && "
          "h() == 4 ? 7 : 1; }\n", want=7)


def test_wq1_q05_two_live_layouts_two_functions():
    """b13-class mis-SIZE guard by value: 8+3 and 4+4 both correct."""
    _pair("q05", "int gs, gk;\nvoid f(void){ struct S5 { char a[8]; } s; "
          "gs = sizeof(s); s.a[7] = 3; gs += s.a[7]; }\n"
          "void h(void){ struct S5 { int b; } t; gk = sizeof(t); "
          "t.b = 4; gk += t.b; }\n"
          "int main(void){ f(); h(); return gs == 11 && gk == 8 ? 5 : 1; }\n",
          want=5)


def test_wq1_q06_sibling_blocks_same_tag():
    _pair("q06", "int main(void){ int r = 0;\n"
          "  { struct S6 { char a[6]; } x; r += (int)sizeof(x); }\n"
          "  { struct S6 { long b; } y; r += (int)sizeof(y); }\n"
          "  return r % 100; }\n", want=14)


def test_wq1_q07_static_of_block_type():
    """A static local's type outlives the block; the layout rides the
    identity into the data layer (name.N)."""
    _pair("q07", "int g7;\nvoid f(void){ static struct SS { int a; } s; "
          "s.a += 3; g7 = s.a; }\nint main(void){ f(); f(); "
          "return g7 % 100; }\n", want=6)


def test_wq1_q08_forward_completed_in_block():
    _pair("q08", "int g8;\nvoid f(void){ struct F7 *fp; struct F7 "
          "{ int x; } v; v.x = 2; fp = &v; g8 = fp->x; }\n"
          "int main(void){ f(); return g8; }\n", want=2)


def test_wq1_q09_block_ref_vs_later_file_def():
    """Already PAIR-VALUE at tip (tip never needed the layout); kept as
    the identity law's anchor row: 4 + 1 = 5."""
    _pair("q09", "int g9;\nvoid f(void){ struct F8 *p; (void)p; }\n"
          "struct F8 { int y; };\nint h(void){ struct F8 z; z.y = 1; "
          "g9 = (int)sizeof(z); return g9 + z.y; }\n"
          "int main(void){ f(); return h(); }\n", want=5)


def test_wq1_q10_enum_sibling():
    _pair("q10", "int ge;\nvoid f(void){ enum E9 { EA = 7 }; ge = EA; }\n"
          "enum E9 { EB = 2 };\nint h(void){ return EB; }\n"
          "int main(void){ f(); return (ge + h()) % 100; }\n", want=9)


def test_wq1_q10b_enum_constant_scope_loud():
    """gcc rc1: a block enum constant is block-scoped; codegen's fold
    table RESTORES it on scope exit (never leaks file-wide)."""
    g, b, _ge, _be, _bt = _pair(
        "q10b", "void f(void){ enum E9 { EA = 7 }; (void)EA; }\n"
        "int g10b;\nint main(void){ g10b = EA; return 0; }\n",
        gcc_ok=False)
    assert g != 0 and b != 0


def test_wq1_q11_block_typedef_and_proto():
    """A block typedef of a block tag feeds a block prototype's param;
    8 (sizeof) + 5 = 13."""
    _pair("q11", "long gl;\nvoid f(void){\n"
          "    typedef struct QT { long v; } QT;\n"
          "    int take(QT *q);\n    QT q; q.v = 5;\n"
          "    extern int ext(QT *);\n    gl = sizeof(QT) + q.v;\n}\n"
          "int main(void){ f(); return (int)(gl % 100); }\n", want=13)


def test_wq1_q12_same_name_tag_param():
    """Passing a BLOCK same-name-tag object to a FILE-tag param: gcc
    warns, rc0; the value pairs through the file layout's FIRST member
    (2 + 1 = 3)."""
    _pair("q12", "struct S12 { int f; };\nint eat(struct S12 *p){ "
          "return p->f; }\nint main(void){ struct S12 { int f; int g; } "
          "o; o.f = 2; o.g = 1; return eat(&o) + 1; }\n", want=3)


def test_wq1_q13_anon_union_init_aliasing():
    """THE +2 ACCEPT SHAPE (boot_string / boot_compressed_string): the
    __div_u64_rem anonymous block union with brace-init + member
    aliasing."""
    _pair("q13", "typedef long long ll;\nint main(void){\n"
          "  union { ll v64; int v32[2]; } d = { 0x100000002LL };\n"
          "  d.v32[0] += 1;\n  return (d.v32[0] & 0xff); }\n", want=3)


def test_wq1_q16b_for_init_tag_loud():
    """gcc rc1 (for-init tag scope = the for statement); blcc stays the
    §5 single-declaration LOUD - NAMED twin, corpus volume 0 (a gcc-rc0
    for-init DECLARE shape is LOUD here: the §5 wall is pre-existing,
    see LEDGER M4 W-Q close row)."""
    g, b, _ge, _be, _bt = _pair(
        "q16b", "int main(void){ int g = 0;\n  for (struct F16 { int i; } "
        "it = { 1 }; it.i < 3; it.i++) g += it.i;\n  return (int)(g + "
        "sizeof(struct F16)) % 100; }\n", gcc_ok=False)
    assert g != 0 and b != 0
