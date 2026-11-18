# LINES reason: M4 W-M COMMIT-4 — the byval PARAM size law in ONE file
# (card 12404.2.83): the walk RED at time64.h:63 flipped from the
# return door to the param door and the SAME measured table (bp2_*.s
# arrivals) answers both directions; splitting per size class would
# separate the ladder law from its run-pairs.
r"""M4 W-M COMMIT-4 — STRUCT BY VALUE PARAMS (the walk unlock).

THE WALK EVIDENCE: with COMMIT-2 shipping the return, the kcopy walk's
first RED MOVED on the SAME line — include/linux/time64.h:63:133 now
answers `'struct' passed by value ... found 'lhs'` (timespec64_add
takes TWO 16-byte structs by value). The return alone could not walk
past it: the DoD's honest deviation, named — this commit completes the
by-value law.

THE LAW (gcc 11.4 kernel recipe, per-class ARRIVAL table
.tmp/m4-wm/out/measure-byval.txt — bp2_p1..p24, all probes at MY
hands, + the W-L §5 table rows):
  ≤8        INTEGER: ONE GP (the value; `leaq -1(%rsp)`-style spill
            when address-taken — blcc's uniform spill-to-slot is the
            same 8-byte object the oracle would spill into).
  9..16     INTEGER PAIR: TWO GPs (LOW half first: rdi:rsi for the
            first param, next pair rdx:rcx — measured pair2 probe:
            callee adds in-register).
  >16       MEMORY: NO GP consumed (W-L §5 row: "consumes no GP
            register"); the caller passes a COPY at the stack
            position. LOUD TWIN here — the multi-participant stack
            law (MEMORY param × scalar overflow × hidden return in
            ONE call) has 0 volume in the 706 census; implementing
            it blind would be the silent-ABI class W-M exists to
            kill. The twin names the measured behaviour.
  ladder    params consume GP slots in order (scalar 1, ≤8 1, pair
            2); the first GP EXHAUSTED moves every LATER param to the
            incoming stack area at 16(%rbp)+8i — the W-L law, ONE
            ladder shared with scalars (the hidden-return shift from
            COMMIT-3 composes).
  value     PASS-BY-VALUE: a callee write to the param (or a member)
            is NOT visible to the caller — pinned by a run-pair tooth.
  fp        an fp-member struct param = SSE class LOUD twin (row 14).
  union     keeps its shipped wall (measure gcc later — honest LOUD).
"""
import os
import re
import subprocess
import sys

import pytest

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.environ.get("BLCC_REPO") or os.path.dirname(HERE)


def blcc(args):
    return subprocess.run([sys.executable, "-m", "blcc"] + args,
                          capture_output=True, text=True, cwd=REPO,
                          env={"PYTHONPATH": REPO, "PATH": "/usr/bin:/bin"})


def gcc(args):
    return subprocess.run(["gcc", "-std=gnu89"] + args,
                          capture_output=True, text=True,
                          env={"PATH": "/usr/bin:/bin"})


def _pair(tmp_path, tag, src, expect):
    s = tmp_path / (tag + ".c")
    s.write_text(src)
    gx = tmp_path / (tag + ".gcc")
    gr = gcc(["-O0", str(s), "-o", str(gx)])
    assert gr.returncode == 0, "oracle must build:\n" + gr.stderr
    bx = tmp_path / (tag + ".blcc")
    br = blcc([str(s), "-o", str(bx)])
    assert br.returncode == 0, "blcc must build:\n" + br.stderr
    g = subprocess.run([str(gx)], capture_output=True, text=True, timeout=30)
    b = subprocess.run([str(bx)], capture_output=True, text=True, timeout=30)
    assert g.returncode == b.returncode == expect, \
        "run-pair: gcc {} blcc {} expect {}".format(
            g.returncode, b.returncode, expect)


def _asm(tmp_path, tag, src):
    s = tmp_path / (tag + ".c")
    s.write_text(src)
    o = tmp_path / (tag + ".bin")
    r = blcc([str(s), "--emit-asm", "-o", str(o)])
    assert r.returncode == 0, "blcc must emit:\n" + r.stderr
    return (tmp_path / (str(o) + ".s")).read_text()


def _fn_body(asm, name):
    body = asm.split(name + ":\n", 1)[1]
    nxt = re.search(r"\n\.[ \t]*\.globl|\n(\.|[A-Za-z_][\w.]*):\n", body)
    return body[:nxt.start()] if nxt else body


def _loud(tmp_path, tag, src, needle):
    s = tmp_path / (tag + ".c")
    s.write_text(src)
    o = tmp_path / (tag + ".o")
    r = blcc(["-c", str(s), "-o", str(o)])
    assert r.returncode != 0, "expected LOUD, got rc0 for " + tag
    assert needle in r.stderr, "{} LOUD missing {!r}:\n{}".format(
        tag, needle, r.stderr[:400])


# ------------------------------------------------ the size-class law,
# run-pairs through the PARAMETER direction (callee reads the fields —
# observable-write law: the RETURNED sum proves every byte arrived).

CLASSES = [
    ("p1", "struct S { char a; };\n", "s.a", 7),
    ("p2", "struct S { short a; };\n", "s.a", 44),     # 300 & 255
    ("p4", "struct S { int a; };\n", "s.a", 4),        # 1028 & 255
    ("p5", "struct S { int a; char b; };\n", "s.a + s.b", 41),
    ("p8", "struct S { long a; };\n", "s.a", 70),
    ("p9", "struct S { char a[9]; };\n", "s.a[0] + s.a[8]", 11),
    ("p12", "struct S { int a[3]; };\n", "s.a[0] + s.a[2]", 107),
    ("p16", "struct S { long a, b; };\n", "s.a + s.b", 89),
]


@pytest.mark.parametrize("tag,decl,expr,want", CLASSES)
def test_wm4_param_size_class_pair(tmp_path, tag, decl, expr, want):
    if tag == "p1":
        call = "f((struct S){7})"
    elif tag == "p2":
        call = "f((struct S){300})"
    elif tag == "p4":
        call = "f((struct S){1028})"
    elif tag == "p5":
        call = "f((struct S){38, 3})"
    elif tag == "p8":
        call = "f((struct S){70})"
    elif tag == "p9":
        call = "f((struct S){{4,0,0,0,0,0,0,0,7}})"
    elif tag == "p12":
        call = "f((struct S){{51,0,56}})"
    else:
        call = "f((struct S){50, 39})"
    _pair(tmp_path, "wm4" + tag, decl +
          "int f(struct S s){{ return (int)({}) & 255; }}\n"
          "int main(void){{ return {}; }}\n".format(expr, call), want)


def test_wm4_timespec64_shape_pair(tmp_path):
    # THE walk-shape: TWO 16-byte params, pair-split rdi:rsi rdx:rcx,
    # 16-byte return (timespec64_add). 50+39+1+2 = 92.
    _pair(tmp_path, "wm4ts",
          "struct T { long tv, ns; };\n"
          "struct T add(struct T l, struct T r){ struct T o;"
          " o.tv = l.tv + r.tv; o.ns = l.ns + r.ns; return o; }\n"
          "int main(void){ struct T a = {50, 1}, b = {39, 2};"
          " struct T c = add(a, b); return (int)(c.tv + c.ns) & 255; }",
          92)


def test_wm4_param_with_seven_scalars_pair(tmp_path):
    # LADDER interaction: 8-byte struct param + 7 scalars = 8 GP slots
    # → struct takes 1 (gp0), scalars 1..5 gp1..5, scalars 6-7 to the
    # stack (K=2, pad $16). Sum 1..7 = 28 (+ s.a 40) = 68.
    _pair(tmp_path, "wm4l",
          "struct S { long a; };\n"
          "long f(struct S s, long a, long b, long c, long d, long e,"
          " long g, long h){ return s.a + a+b+c+d+e+g+h; }\n"
          "int main(void){ struct S k = {40}; return (int)f(k,1,2,3,4,"
          "5,6,7) & 255; }", (40 + 28) & 255)


def test_wm4_pair_param_ladder_pair(tmp_path):
    # PAIR param NOT first: scalar then 16B struct then scalar —
    # scalar gp0=rdi, pair gp1:gp2=rsi:rdx, scalar gp3=rcx. 1+2+3+4=10.
    _pair(tmp_path, "wm4lad",
          "struct S { long a, b; };\n"
          "long f(long x, struct S s, long y){ return x+s.a+s.b+y; }\n"
          "int main(void){ struct S k = {2, 3}; return (int)f(1, k, 4)"
          " & 255; }", 10)


def test_wm4_value_semantics_tooth(tmp_path):
    # PASS-BY-VALUE: callee writes DO NOT reach the caller's object.
    # Caller still sees 9 after f set 77 → expect 9 (gcc -O0 decides).
    _pair(tmp_path, "wm4val",
          "struct S { long a; };\n"
          "void f(struct S s){ s.a = 77; }\n"
          "int main(void){ struct S k = {9}; f(k); return (int)k.a; }",
          9)


# ------------------------------------------------ asm anchors (the
# measured ARRIVAL law is FORCED): GP one-slot, pair two adjacent
# slots low-first, no register skipping.

def test_wm4_anchor_pair_arrival(tmp_path):
    a = _asm(tmp_path, "wm4a16",
             "struct S { long a, b; };\n"
             "long f(struct S s, long z){ (void)z; return s.a + s.b; }\n"
             "int main(void){ return 0; }\n")
    body = _fn_body(a, "f")
    m1 = re.search(r"movq %rdi, \-?(\d+)\(%rbp\)", body)
    m2 = re.search(r"movq %rsi, \-?(\d+)\(%rbp\)", body)
    assert m1 and m2, "pair halves not spilled from rdi/rsi:\n" + body
    lo, hi = -int(m1.group(1)), -int(m2.group(1))
    assert hi == lo + 8, \
        "pair spill must be low-first adjacent (got {} {}):\n{}".format(
            lo, hi, body)


def test_wm4_gp_param_still_one_slot(tmp_path):
    a = _asm(tmp_path, "wm4a8",
             "struct S { long a; };\n"
             "long f(struct S s, long z){ return s.a + z; }\n"
             "int main(void){ return 0; }\n")
    body = _fn_body(a, "f")
    assert re.search(r"movq %rdi, \-?\d+\(%rbp\)", body) and \
        re.search(r"movq %rsi, \-?\d+\(%rbp\)", body), body


# ------------------------------------------------ LOUD twins (named,
# measured, 0-volume-in-corpus)

def test_wm4_memory_param_loud_twin(tmp_path):
    # >16-byte param: gcc -Os passes the caller's COPY at the stack
    # position (measure-byval bp_mem row) — consumes no GP. Multi-
    # participant stack law unmeasured at volume; LOUD is honest.
    _loud(tmp_path, "wm4m",
          "struct S { char a[17]; };\nlong f(struct S s){return s.a[0];}\n",
          "passed by value")


def test_wm4_fp_member_param_loud_twin(tmp_path):
    _loud(tmp_path, "wm4fpp",
          "struct S { double a; };\nlong f(struct S s){return 0;}\n",
          "passed by value")


def test_wm4_union_param_keeps_wall(tmp_path):
    _loud(tmp_path, "wm4u",
          "union U { long a; char b[11]; };\nlong f(union U u){return u.a;}\n",
          "passed by value")
