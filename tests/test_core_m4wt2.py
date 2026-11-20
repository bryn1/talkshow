# LINES reason: one wave (M4 W-T COMMIT-2, BUILD_BUG-crowd fact-hoist
# at the block-stmt seam + the 13-row bitfield law pins, card
# 12404.2.99): the ordering legs and the bitfield pins share the ONE
# unlock story (the 111-crowd's wall is ORDERING, its bitfield law
# already paired at tip — measured); splitting separates a row from
# the unlock it belongs to.
r"""M4 W-T COMMIT-2 (MC 12736) — the 111-stream BUILD_BUG_ON_ZERO crowd:
`sizeof(struct { int:(-!!(e)); })` inside a FUNCTION BODY mints an anon
struct whose StructDecl sat in the parser's `_pending` until the NEXT
declaration spliced it — codegen then met the USE before the layout
fact ("undefined struct '<anon@…>'", the wall of 111 first-blockers at
the sealed tip sweep). THE LAW: an anon struct/enum DEFINITION minted
while parsing a block item is a fact of that item — `_block_stmts_until_
brace` hoists it IN FRONT of its statement (the ONE collection seam
shared by function bodies and compounds; declaration-position facts
keep their existing parse_decl splice).

MEASURED OWN-HANDS (this wave): the crowd is NOT a bitfield-layout gap
— the full bitfield law table (13 rows, .tmp/m4-wt/out/laws-bf-tip.txt:
signed/unsigned/char extracts, masks, cross-word posture, zero-width
pads, mixed-unit flush, packed x W-F, BUILD_BUG arms) PAIRS AT TIP
BYTES. The unlock is the ordering seam; the bitfield rows ride as LAW
PINS (W-S COMMIT-3 precedent: measure-before-commit, pin honestly).
Deviation NAMED: the brief's "bitfield at the W-F layout seam" premise
— measured false; layout already ships; the wall is the parser seam.
"""
import os
import subprocess
import sys

import pytest

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.environ.get("BLCC_REPO") or os.path.dirname(HERE)
PINNED = "/home/claudecode/Blaha/.tmp/m4-plan/streams"
REC = ["-Os", "-mno-sse", "-mno-mmx", "-mno-80387", "-fno-stack-protector",
       "-fno-pic"]


def blcc(args):
    return subprocess.run([sys.executable, "-m", "blcc"] + args,
                          capture_output=True, text=True, cwd=REPO,
                          env={"PYTHONPATH": REPO, "PATH": "/usr/bin:/bin"})


def _pair(tag, src):
    c = "/dev/shm/wt2_%s.c" % tag
    open(c, "w").write(src)
    g = subprocess.run(["gcc", "-std=gnu89"] + REC +
                       [c, "-no-pie", "-o", "/dev/shm/wt2_%s.g" % tag],
                       capture_output=True, text=True)
    assert g.returncode == 0, "law row must be valid C: " + g.stderr
    gex = subprocess.run(["/dev/shm/wt2_%s.g" % tag],
                         env={"PATH": "/usr/bin:/bin"}).returncode
    o = "/dev/shm/wt2_%s.o" % tag
    b = blcc(["-c", c, "-o", o])
    assert b.returncode == 0, "%s must COMPILE: " % tag + b.stderr
    assert subprocess.run(["gcc", "-no-pie", o, "-o",
                           "/dev/shm/wt2_%s.b" % tag],
                          capture_output=True).returncode == 0, "link"
    rex = subprocess.run(["/dev/shm/wt2_%s.b" % tag],
                         env={"PATH": "/usr/bin:/bin"}).returncode
    assert rex == gex, "%s: value pair gcc=%d blcc=%d" % (tag, gex, rex)


BBZ = "((int)(sizeof(struct { int:(-!!(e)); })))"


def test_wt2_sizeof_anon_before_next_decl_hoisted():
    # THE ordering law, minimal: the anon minted inside decl#1's init
    # must be a fact BEFORE decl#1 (RED-at-tip: `undefined struct
    # '<anon@…#1>'`). BUILD_BUG_ON_ZERO(false) folds to 0.
    _pair("order1", "int main(void){ int r = %s; int y = r; return y + 7; }"
          % BBZ.replace("(e)", "(0)"))


def test_wt2_sizeof_anon_in_if_then_decl_hoisted():
    # the if-condition mint + a following declaration — the i8259/
    # entry_common shape compressed (RED-at-tip).
    _pair("order2", "int g(void){return 0;}\nint main(void){ int x=g();"
          " if (x && %s) { } int y = x+1; return y+6; }"
          % BBZ.replace("(e)", "(23 != 23)"))


def test_wt2_hoist_keeps_tu_end_arm():
    # W-L law preserved: the LAST declaration's mints still land
    # (TU-end drain); the hoist must not eat them.
    _pair("wl_arm", "int main(void){ int r = (int)sizeof(struct {"
          " int:(-!!(1 != 1)); }); return r+8; }")


def test_wt2_enum_in_body_statement_pair():
    # the enum arm of the same hoist: a body-statement enum definition
    # keeps its sizeof-fold + constant use (defensive law, pair).
    _pair("enum_h", "int main(void){ int r = (int)sizeof(enum {EA,EB});"
          " int y = EA + r; return y+3; }")


def test_wt2_bbz_or_chain_corpus_shape():
    # the f04 corpus shape: BUILD_BUG_ON_ZERO arms inside a || chain
    # (constant-folded false widths), then a behind declaration.
    _pair("orchain", "int g(void){return 1;}\nint main(void){int r=0;"
          "if (g() || %s || %s) r=1; else r=2;"
          " int y=r; return y+1;}"
          % (BBZ.replace("(e)", "(23 != 23)"), BBZ.replace("(e)", "(3 != 3)")))


# ---- the bitfield law PINS (measured pair AT TIP, kept green here) ----

def test_wt2_signed_extract_signext():
    _pair("f05", "struct A{int x:3;};int main(void){struct A a;a.x=5;"
          "return a.x+8;}")                   # -3+8 = 5


def test_wt2_unsigned_assign_mask():
    _pair("f06", "struct B{unsigned y:3;};int main(void){struct B b;b.y=-1;"
          "return b.y+1;}")                   # 7+1 = 8


def test_wt2_char_unit_sign():
    _pair("f07", "struct C{char z:2;};int main(void){struct C c;c.z=2;"
          "return c.z+7;}")                   # -2+7 = 5


def test_wt2_cross_word_layout():
    _pair("f08", "struct D{int a:20;int b:20;};int main(void){struct D d;"
          "d.a=5;d.b=7;return d.a+d.b+(int)(sizeof(struct D)==8);}")


def test_wt2_zero_width_named_pad():
    _pair("f09", "struct E{int :0;char c;};"
          "int main(void){return (int)sizeof(struct E)+1;}")


def test_wt2_mixed_unit_flush():
    _pair("f10", "struct F{int a:3;char c;int b:5;};"
          "int main(void){struct F f;f.a=1;f.c=2;f.b=3;"
          "return f.a+f.b+f.c;}")


def test_wt2_enum_typed_field_pairs():
    # brief premise "enum-typed -> name refusal": MEASURED PAIR at tip
    # (no refusal exists to name) — deviation named; kept as a law pin.
    _pair("f11", "enum E{EA,EB};struct G{enum E v:2;};"
          "int main(void){struct G g;g.v=EB;return g.v+2;}")


def test_wt2_packed_bitfield_sizes():
    _pair("f12", "struct __attribute__((__packed__)) H{char c;int x:12;"
          "char d;};int main(void){return (int)sizeof(struct H)+1;}")


def test_wt2_bbz_negative_width_loud_pair():
    # BUILD_BUG_ON_ZERO(true): negative width — gcc LOUD, blcc ALREADY
    # LOUD at tip (pair-LOUD pin).
    c = "/dev/shm/wt2_f02.c"
    open(c, "w").write("int main(void){return %s;}" % BBZ.replace("(e)", "(1)"))
    g = subprocess.run(["gcc", "-std=gnu89"] + REC +
                       ["-c", c, "-o", "/dev/null"], capture_output=True)
    assert g.returncode != 0, "gcc must refuse the true-arm"
    b = blcc(["-c", c, "-o", "/dev/null"])
    assert b.returncode != 0, "blcc must stay LOUD on the true-arm: " + b.stderr


def test_wt2_stream_witness_walls_moved():
    # >=5 corpus witnesses from the 111-crowd: their first wall today
    # is `sema: undefined struct '<anon@…'` (BUILD_BUG class).
    # RED-first: after COMMIT-2 that CLASS must be gone from the FIRST
    # wall of every witness (the queue law lets it land BEHIND
    # elsewhere — the assertion keys on the CLASS, not on rc0).
    if not os.path.isdir(PINNED):
        pytest.skip("pinned corpus not linked (builder posture)")
    import json
    import re as _re
    rows = [json.loads(l) for l in open("/home/claudecode/Blaha/.tmp/"
                                        "m4-wt/out/rows-base-wt.json")]
    crowd = sorted(f for f, rc, first in rows
                   if rc != 0 and first.split(": ", 1)[-1].startswith(
                       "sema: undefined struct '<anon@"))
    witnesses = ["arch_x86_entry_common.c.i"] + [
        f for f in crowd if f != "arch_x86_entry_common.c.i"][:6]
    lm = _re.compile(r"^#\s+\d+\s+\"")
    for tu in witnesses:
        clean = "/dev/shm/wt2_witness_clean.c"
        with open(os.path.join(PINNED, tu), errors="replace") as fh, \
                open(clean, "w") as oh:
            for ln in fh:
                if not lm.match(ln):
                    oh.write(ln)
        r = blcc(["-c", clean, "-o", "/dev/shm/wt2_witness.o"])
        if r.returncode == 0:
            continue                      # full accept (best posture)
        first = next(ln for ln in r.stderr.splitlines() if ln.strip())
        assert "undefined struct '<anon@" not in first, \
            "%s: BUILD_BUG-anon wall must be EATEN by COMMIT-2: " % tu \
            + first[:200]
