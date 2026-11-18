# LINES reason: the M4 W-M interaction wave — hidden-pointer staging ×
# the M4 W-L >6-arg pad law in ONE size class family (card 12404.2.83);
# the arms share the pad invariant and split nothing per-arm.
r"""M4 W-M COMMIT-3/4 — the HIDDEN POINTER × >6-ARG PAD LAW INTERACTION.

W-L shipped: args 7+ push right-to-left, pad `subq $16` for an EVEN K
/ `$8` for an ODD K (rsp ≡ 0 mod 16 AT the call), callee reads arg 7+i
at 16(%rbp)+8i, ONE addq restores. W-M adds the MEMORY-class HIDDEN
POINTER as slot 0 — the interaction law this file pins (measured:
gcc -Os mem17 K=5/K=6/K=7 rows, .tmp/m4-wm/out/measure-byval.txt):
  * the hidden slot COUNTS toward the staged-arg total — K = (hidden +
    args) − 6, so a 7-arg MEMORY-return callee pushes K=2 slots + $16
    (not K=1 + $8 — the wrong count would leave rsp ≡ 8 at the call:
    the exact silent SSE-corruption class W-L's alignment invariant
    exists to kill);
  * the callee's GP ladder shifts by one (arg 6 lands at 16(%rbp));
  * the odd/even pad law still lands byte-identically for pure-scalar
    calls (the W-L pins ride untouched — this file re-adds only the
    struct-return-shaped variants).
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


S = "struct S { long a[3]; };\n"          # 24 bytes: MEMORY class
P = "struct P { long a, b; };\n"          # 16 bytes: pair class


# ------------------------------------------------ run-pairs: struct
# RETURN through a >6-arg callee — every arg must arrive (stack slots
# AND the shifted GP ladder) and the hidden write-back must land.

def test_wm3_memory_return_seven_args_pair(tmp_path):
    # hidden + 7 args = 8 slots: K = 2 (even) → pad $16. The callee
    # sums ALL args into the returned struct; a mis-shifted ladder or
    # a wrong-slot read breaks the sum.
    _pair(tmp_path, "wm3_k2", S +
          "struct S f(long a,long b,long c,long d,long e,long g,long h)"
          "{struct S r;r.a[0]=a+b;r.a[1]=c+d+e;r.a[2]=g+h;return r;}\n"
          "int main(void){struct S t=f(1,2,4,8,16,32,64);"
          "return (int)(t.a[0]+t.a[1]+t.a[2])&255;}", 127)


def test_wm3_memory_return_nine_args_pair(tmp_path):
    # hidden + 9 args = 10 slots: K = 4 (even) → pad $16; args 7..10
    # all ride the stack. 1..9 minus double-count guard: sum = 45 → 45.
    _pair(tmp_path, "wm3_k4", S +
          "struct S f(long a,long b,long c,long d,long e,long g,long h,"
          "long i,long j){struct S r;r.a[0]=a+j;r.a[1]=b+i;r.a[2]="
          "c+d+e+g+h;return r;}\n"
          "int main(void){struct S t=f(1,2,4,8,16,32,64,128,65);"
          "return (int)(t.a[0]+t.a[1]+t.a[2])&255;}", (66 + 130 + 124) & 255)


def test_wm3_memory_return_eight_args_pair(tmp_path):
    # hidden + 8 args = 9 slots: K = 3 (ODD) → pad $8 — the W-L odd
    # arm must stay byte-identical when the hidden slot tips parity.
    _pair(tmp_path, "wm3_k3", S +
          "struct S f(long a,long b,long c,long d,long e,long g,long h,"
          "long i){struct S r;r.a[0]=a+i;r.a[1]=b+h;r.a[2]=c+d+e+g;"
          "return r;}\n"
          "int main(void){struct S t=f(1,2,3,5,8,13,21,34);"
          "return (int)(t.a[0]+t.a[1]+t.a[2])&255;}", (35 + 23 + 29) & 255)


def test_wm3_pair_class_return_seven_args(tmp_path):
    # 16-byte return is NOT the MEMORY class: NO hidden pointer, the
    # GP ladder does NOT shift — arg 1 rides %rdi, args 7+ the stack
    # (K=1, odd → pad $8). Proves the shift is gated on >16 ONLY.
    a = _asm(tmp_path, "wm3p7", P +
             "struct P f(long a,long b,long c,long d,long e,long g,"
             "long h){struct P r;r.a=a;r.b=h;return r;}\n"
             "int main(void){struct P t=f(1,2,3,4,5,6,7);return "
             "(int)(t.a+t.b)&255;}\n")
    callee = _fn_body(a, "f")
    # NO hidden spill, arg 1 STILL rides %rdi into its slot (no shift):
    assert re.search(r"movq %rdi, \-?\d+\(%rbp\)", callee), \
        "pair class must spill arg 1 from %rdi (no ladder shift):\n" \
        + callee
    assert re.search(r"movq 8\(%rax\), %rdx", callee), \
        "pair door missing:\n" + callee
    _pair(tmp_path, "wm3p7v", P +
          "struct P f(long a,long b,long c,long d,long e,long g,"
          "long h){struct P r;r.a=a;r.b=h;return r;}\n"
          "int main(void){struct P t=f(1,2,3,4,5,6,7);return "
          "(int)(t.a+t.b)&255;}", 8)


# ------------------------------------------------ the alignment
# invariant at hidden-arg call sites (the W-L law, interaction form):
# stack bytes consumed BEFORE the call instruction = 8*K + pad, and
# pad = 16 for even K, 8 for odd K. blcc's frame is a 16-multiple and
# rsp ≡ 0 after pushq %rbp, so THIS is the whole invariant.

def _k_and_pad(body):
    pushes = len(re.findall(r"^\s+pushq (?!%rbp)", body, re.M))
    # the PAD subq is the LAST one (the FRAME subq opens the body) —
    # and it is the small one ($8/$16), the frame is a 16-multiple ≥32.
    subs = [int(x) for x in re.findall(r"subq \$(\d+), %rsp", body)]
    pads = [x for x in subs if x in (8, 16)]
    return pushes, (pads[-1] if pads else None)


@pytest.mark.parametrize("nargs,pad", [(7, 16), (8, 8), (9, 16)])
def test_wm3_pad_invariant_at_hidden_sites(tmp_path, nargs, pad):
    args = ",".join("long x%d" % i for i in range(nargs))
    calls = ",".join(str(i + 1) for i in range(nargs))
    a = _asm(tmp_path, "wm3inv%d" % nargs, S +
             "long rba;\nstruct S f({}){{struct S r;r.a[0]=rba;return r;}}\n"
             "int main(void){{struct S t=f({});"
             "return (int)t.a[0];}}\n".format(args, calls))
    caller = _fn_body(a, "main")
    k, p = _k_and_pad(caller)
    # K counts EVERY staged slot beyond the 6 GP slots — hidden included
    assert k == nargs + 1 - 6, "K mismatch: {}".format(k)
    assert p == pad, "pad for K={} must be ${}, got ${}".format(
        nargs + 1 - 6, pad, p)
    assert (8 * k + p) % 16 == 0, "rsp not ≡ 0 at the call"


# ------------------------------------------------ folded immediate
# INSIDE a struct-return call (the COMMIT-1 × W-M interaction; the
# fold arm itself is tests/test_core_m4wm1.py): an `'i'`-constraint
# operand that is a compile-time constant rides the fold law, while
# the call itself stages a hidden pointer — both mechanisms at once.

def test_wm4_fold_imm_through_memory_return_call(tmp_path):
    _pair(tmp_path, "wm4fold", S +
          "long gs;\nstruct S f(long a){struct S r;"
          "asm(\"movq %1, %%rax\\n\\t\" : \"=r\"(gs) : \"i\"(3 + 4));"
          "r.a[0]=a+gs;return r;}\n"
          "int main(void){struct S t=f(100);return (int)t.a[0]&255;}",
          107)
