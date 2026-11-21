# LINES reason: one wave (M4 W-T COMMIT-3, the CL×bitfield×goto
# interaction table, card 12404.2.99): every leg is an arm of the
# cross-class interaction law the two prior commits must jointly
# honor; splitting separates an interaction from its pair.
r"""M4 W-T COMMIT-3 (MC 12736) — interactions: the two law changes
(CL normalization; pending-ownership hoist) must compose with each
other and with the shipped classes they touch. Every row MEASURED
own hands at gcc 11.4 -Os. NAMED PRE-EXISTING postures (W-F law in
force, measured at BASE bytes, NOT this wave's doing): a bitfield
member initialized from a compound-literal brace list, and a
bitfield-struct assignment, stay LOUD in blcc while gcc answers —
the W-F UNSUPPORTED-stays-LOUD row for bitfield value initializers;
pinned here so a W-F successor that ships them flips THIS leg, not
silently.
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
    c = "/dev/shm/wt3_%s.c" % tag
    open(c, "w").write(src)
    g = subprocess.run(["gcc", "-std=gnu89"] + REC +
                       [c, "-no-pie", "-o", "/dev/shm/wt3_%s.g" % tag],
                       capture_output=True, text=True)
    assert g.returncode == 0, "law row must be valid C: " + g.stderr
    gex = subprocess.run(["/dev/shm/wt3_%s.g" % tag],
                         env={"PATH": "/usr/bin:/bin"}).returncode
    o = "/dev/shm/wt3_%s.o" % tag
    b = blcc(["-c", c, "-o", o])
    assert b.returncode == 0, "%s must COMPILE: " % tag + b.stderr
    assert subprocess.run(["gcc", "-no-pie", o, "-o",
                           "/dev/shm/wt3_%s.b" % tag],
                          capture_output=True).returncode == 0, "link"
    rex = subprocess.run(["/dev/shm/wt3_%s.b" % tag],
                         env={"PATH": "/usr/bin:/bin"}).returncode
    assert rex == gex, "%s: value pair gcc=%d blcc=%d" % (tag, gex, rex)


def test_wt3_goto_label_then_cl_pair():
    # interaction (hoisted label class × CL object): a `goto` into a
    # block whose first statement declares a compound-literal-backed
    # object (§2.4d jump-INTO law meets the CL lifetime law).
    _pair("goto_cl", "int main(void){int r=0;goto here;return 3;"
          "here:{int*p=(int[]){7,9};return p[1]-2;}}")   # 7


def test_wt3_union_member_cl_pair():
    # interaction (union member × nested CL): the byte-identical
    # unwrap covers struct/array slots; union members ride the
    # existing union path — both must answer alike.
    _pair("union_cl", "union U{int i;char c;};struct H{union U u;int k;};"
          "int main(void){struct H h=(struct H){ (union U){.i=258}, 1 };"
          "return h.u.c+6;}")                # 8


def test_wt3_cond_arm_cl_pair():
    # interaction (?:-arm × CL temp): the CL object lives to the end
    # of the full expression on BOTH arms (C6.5.2.5p15).
    _pair("cond_cl", "int main(void){int a=1;"
          "int v=a?(int)((int[]){42}[0]):7;return v-34;}")   # 8


def test_wt3_bitfield_cl_named_postures():
    # NAMED PRE-EXISTING LOUD rows (measured at BASE bytes): W-F's
    # UNSUPPORTED-stays-LOUD law for bitfield value initializers —
    # gcc answers, blcc refuses. PIN: a W-F successor that SHIPS
    # these flips THIS leg to _pair (its own RED-first), never a
    # silent posture change.
    c = "/dev/shm/wt3_bf.c"
    for tag, src in (
            ("init", "struct BF{int x:3;int y:5;};"
             "int main(void){struct BF b=(struct BF){.x=3,.y=5};"
             "return b.x+b.y+1;}"),
            ("assign", "struct BF{int x:3;int y:5;};"
             "int main(void){struct BF b={1,2};"
             "b=(struct BF){.x=7,.y=9};return b.x+b.y-8;}")):
        open(c, "w").write(src)
        b = blcc(["-c", c, "-o", "/dev/null"])
        assert b.returncode != 0, \
            "bf_cl_%s: W-F bitfield-init LOUD posture MOVED — flip " \
            "this leg to _pair in the SAME commit that ships it." % tag


def test_wt3_combo_witnesses_own_classes_eaten():
    # THE pairing proof at stream level: these files' BASE first walls
    # carry the two wave classes (entry_common: anon-BUILD_BUG;
    # i8259: construct-behind-W-R — measured in the pre-wave sim
    # rows). After BOTH commits their first wall must name NEITHER
    # class any more. MEASURED queue-behind posture at the combo
    # bytes: the wall LANDS BEHIND on `not an addressable l-value
    # (§4), found 'statement expression'` — the ({...})-as-lvalue
    # class, NAMED CARRY (outside this wave's SET; it is the walk's
    # next candidate). Full-TU accept still satisfies the leg.
    if not os.path.isdir(PINNED):
        pytest.skip("pinned corpus not linked (builder posture)")
    import re as _re
    lm = _re.compile(r"^#\s+\d+\s+\"")
    for tu in ["arch_x86_entry_common.c.i",
               "arch_x86_kernel_i8259.c.i"]:
        clean = "/dev/shm/wt3_%s_clean.c" % tu[:20]
        with open(os.path.join(PINNED, tu), errors="replace") as fh, \
                open(clean, "w") as oh:
            for ln in fh:
                if not lm.match(ln):
                    oh.write(ln)
        r = blcc(["-c", clean, "-o", "/dev/shm/wt3_witness.o"])
        if r.returncode == 0:
            continue                      # full accept (close posture)
        first = next(ln for ln in r.stderr.splitlines() if ln.strip())
        assert "found 'construct'" not in first, \
            tu + ": construct wall must be EATEN: " + first[:160]
        assert "undefined struct '<anon@" not in first, \
            tu + ": BUILD_BUG-anon wall must be EATEN: " + first[:160]
        assert "not an addressable l-value" not in first \
            and "statement expression" not in first, \
            tu + ": the W-U group-lvalue carry must be EATEN here — " \
            "M4 W-U COMMIT-1 (MC 12739) took this NAMED carry class " \
            "(the `({...})`-as-lvalue wall) into its own SET: " + first[:200]
        # QUEUE FLIP, own hands at these bytes: with the carry eaten the
        # wall MOVED FORWARD onto the extern-local `zero_pfn` class
        # (entry_common :24792:16, i8259 :36317:16) — the class W-U
        # COMMIT-2 eats. Re-pinned on the MEASURED land.
        # M4 W-U COMMIT-2 (MC 12739) flipped this pin too: with the
        # extern-local class eaten, entry_common lands on the extern
        # INCOMPLETE-ARRAY wall (:32726:14, `__init_begin` — the W-V
        # lever this wave names and does NOT free, accept-neutral by
        # design) and i8259 on the packed-bitfield unit-window class
        # (:36560:6). Both lands re-measured at the COMMIT-3 bytes:
        # identical, so the wave's walk-land stands behind them.
        assert "'zero_pfn' undeclared" not in first, \
            tu + ": the W-U extern-local class must be EATEN: " \
            + first[:200]
        land = {"arch_x86_entry_common.c.i":
                (":32726:14", "extern local array"),
                "arch_x86_kernel_i8259.c.i":
                (":36560:6", "packed bitfield access")}[tu]
        assert land[0] in first and land[1] in first, \
            tu + ": behind-wall must land on the measured W-U " \
            "SITE+CLASS %r: " % (land,) + first[:220]
