# LINES reason: one wave of legs (M4 W-K COMMIT-1 — the asm CONSTRAINT-
# LETTER class {'i','r'} = ir/ri, the kill-sim-proven accept lever, 41
# first-blockers on top of the 236 sizeof-void carriers that die there
# too; card 12404.2.79) — splitting would separate the letter arm from
# the run-pairs that prove the reg/imm choice.
r"""M4 W-K COMMIT-1 — the constraint-letter class {'i','r'} (spellings
"ir" AND "ri" — the model is SET-based: lset == {"i","r"}).

THE WALL (gate LEG 9 kill-sim): with the trio stubbed, the FIRST blocker
on 329 of 470 candidate streams is `constraint letter(s) 'ir' are not in
the M3 SUPPORT set` — one macro family in arch/x86/include/asm/bitops.h
(the LOCK bts/btr/btc arms spell `"ir" (nr)`) plus arch/x86/boot/boot.h:141
(41 first-blockers at the CLOSE tree WITHOUT any stub). Census of my own
at the pinned 706 streams (.tmp/m4-wk/census3.py, the §3.5 juxtaposed-
literal merge + section split — clobbers classified separately): the
REJECTED constraint literals are exactly {'i','r'} (4515+13554 sites,
658 streams) and the 1-2-site `A`/`bdS` shapes (deferred, sim-named);
every other literal the corpus spells is already in the shipped S-set.

MEASURED LAW (gcc 11.4 gnu89 -Os, my probes .tmp/m4-wk/probes/lt_*, the
letter table in the verdict — rc + emitted asm per letter):
  "ir"/"ri" const 42   rc0  `movq $42,g(%rip)`       — the imm wins
  "ir" var           rc0  `movq %rdi,g(%rip)`        — the reg takes it
  "ir"/"iq"/"i" (1UL<<63) rc1 — gcc keeps the imm arm, emits
                          `movq $-9223372036854775808,g(%rip)` and the
                          ASSEMBLER rejects it (measured under -c; an
                          -S-only first probe had skipped `as` and lied
                          rc0). blcc's shipped §3 L4 range LOUD answers
                          rc2: SAME VERDICT, pinned below.
  bts $imm / bts %reg both rc0 — the bitops arms' real shapes.
MECHANISM (extend, no parallel rail): ONE new arm in the shipped
parse_constraint — lset == {"i","r"} → cls "i", alt "r" — the EXACT
mirror of the shipped {"i","q"}→i/alt-q arm the bitops "iq" sites already
ride: foldable → imm through the §3.5 fold closure; not foldable → alt
re-parse → the POOL allocator (full r-class, not the q subset). No
asmgen change: the i/alt machinery is the shipped one.
"""
import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.environ.get("BLCC_REPO") or os.path.dirname(HERE)
STREAMS = os.path.join(REPO, "..", ".tmp", "m4-plan", "streams")


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


# ------------------------------------------------- THE run-pairs (values)

def test_wk1_ir_imm_pair(tmp_path):
    # "ir" with a compile-time constant: imm arm (oracle `btsq $5`) —
    # w 0 → bit 5 set = 32. exit 5 iff the value is RIGHT.
    _pair(tmp_path, "wk1_ir_imm",
          "unsigned long w;\nint main(void){ w = 0;\n"
          "  asm volatile(\"btsq %1,%0\" : \"+m\"(w) : \"ir\" (5));\n"
          "  return w == 32UL ? 5 : 0; }\n", 5)


def test_wk1_ir_reg_pair(tmp_path):
    # "ir" with a runtime value: reg arm (oracle `btsq %rdi`) — bit 11.
    _pair(tmp_path, "wk1_ir_reg",
          "unsigned long w;\nunsigned long f(long nr){ w = 0;\n"
          "  asm volatile(\"btsq %1,%0\" : \"+m\"(w) : \"ir\" (nr));\n"
          "  return w; }\n"
          "int main(void){ return f(11) == 2048UL ? 3 : 0; }\n", 3)


def test_wk1_ri_mov_pair(tmp_path):
    # the ri SPELLING (set-equal; set_memory_16 shape `movw %1,%0 : "ri"`)
    # with BOTH an imm and a var operand in one TU.
    _pair(tmp_path, "wk1_ri_mov",
          "unsigned short m16;\nvoid put16(unsigned short v){\n"
          "  asm volatile(\"movw %1,%0\" : \"+m\"(m16) : \"ri\" (v)); }\n"
          "int main(void){ m16 = 0; asm volatile(\"movw %1,%0\" :"
          " \"+m\"(m16) : \"ri\" (0x1234));\n"
          "  if (m16 != 0x1234) return 1;\n"
          "  put16(0); if (m16) return 2; return 4; }\n", 4)


def test_wk1_negative_var_reg_arm_pair(tmp_path):
    # a runtime NEGATIVE long takes the reg arm on both sides (the imm32
    # closure never sees it). A NEGATIVE bts INDEX is UB-shaped (bts on
    # memory walks out of the object — layout-dependent), so the law is
    # pinned through a plain movq: value round-trips through $-3-as-reg.
    _pair(tmp_path, "wk1_neg",
          "long g;\nlong f(long v){ asm volatile(\"movq %1,%0\" :"
          " \"=m\"(g) : \"ir\" (v)); return g; }\n"
          "int main(void){ return f(-3) == -3 ? 6 : 0; }\n", 6)


# ------------------------------------------------- asm-form parity legs

def _asm(tmp_path, tag, src):
    s = tmp_path / (tag + ".c")
    s.write_text(src)
    r = blcc(["--emit-asm", "-c", str(s), "-o",
              str(tmp_path / (tag + ".o"))])
    assert r.returncode == 0, r.stderr
    return r.stdout


def test_wk1_ir_asm_forms_imm_and_reg(tmp_path):
    # the two observable FORMS at -Os: the const operand substitutes as
    # $5 (the shipped imm substitution path), the runtime operand as a
    # REGISTER — and NO libcall on either arm.
    s_imm = _asm(tmp_path, "wk1_form_i",
                 "unsigned long w;\nint f(void){ asm volatile(\"btsq "
                 "%1,%0\" : \"+m\"(w) : \"ir\" (5)); return 0; }\n")
    assert "$5" in s_imm, s_imm
    s_reg = _asm(tmp_path, "wk1_form_r",
                 "unsigned long w;\nint f(long v){ asm volatile(\"btsq "
                 "%1,%0\" : \"+m\"(w) : \"ir\" (v)); return 0; }\n")
    assert "call" not in s_reg, s_reg
    import re
    assert re.search(r"btsq %(%r[a-z0-9]+|rdi|rsi|rdx|rcx|rax|rbx),",
                     s_reg), s_reg


def test_wk1_iq_b_modifier_reg_pair(tmp_path):
    # fairness (green BOTH states): the bitops CONST_MASK face is the
    # %b size name over a RUNTIME operand — the shipped q-reg arm must
    # stay pair-clean (a constant-folded %b-on-imm is a pinned PRE-
    # EXISTING LOUD vs gcc's `$8` below, corpus volume 0: blcc folds no
    # parameters, the bitops nr never reaches it folded).
    _pair(tmp_path, "wk1_iq_b",
          "unsigned char w;\nunsigned char g(unsigned char v){ w = 0x0F;\n"
          "  asm volatile(\"orb %b1,%0\" : \"+m\"(w) : \"iq\" (v));\n"
          "  return w; }\n"
          "int main(void){ return g(0x30) == 0x3F ? 9 : 0; }\n", 9)


def test_wk1_i_out_of_range_same_verdict(tmp_path):
    # MEASURED law row (RE-MEASURED under the real ASSEMBLE step, -c —
    # an earlier -S-only probe had SKIPPED the assembler and read rc0):
    # a constant that does not fit imm32 — gcc keeps the imm arm, emits
    # `movq $-9223372036854775808,g(%rip)` and the ASSEMBLER rejects it
    # (rc1 "operand type mismatch for `movq'"); blcc's SHIPPED §3 L4
    # range LOUD answers rc2 FIRST (probe big2..big5: the law is identical
    # for i, ir AND iq — the shipped arm is SAME-VERDICT, never a value-
    # identity claim).
    src = ("unsigned long g;\nint f(void){ asm volatile(\"movq %1,%0\" :"
           " \"=m\"(g) : \"ir\" (1UL << 63)); return 0; }\n")
    s = tmp_path / "wk1_big.c"
    s.write_text(src)
    g = gcc(["-Os", "-c", str(s), "-o", "/dev/null"])
    r = blcc(["-c", str(s), "-o", str(tmp_path / "wk1_big.o")])
    assert g.returncode == 1 and "operand type mismatch" in g.stderr, \
        g.stderr
    assert r.returncode == 2 and "out of range" in r.stderr, r.stderr


# ------------------------------------------------ corpus witnesses (kern)

import pytest

_IR_STREAMS = ["arch_x86_boot_memory.c.i", "arch_x86_boot_pm.c.i",
               "arch_x86_lib_iomem.c.i"]


def _clean_i(path, tmp_path, tag):
    out = tmp_path / (tag + ".clean.i")
    keep = []
    with open(path, "r", errors="replace") as fh:
        for ln in fh:
            if ln.startswith("# "):
                continue
            keep.append(ln)
    out.write_text("".join(keep))
    return out


@pytest.mark.skipif(
    not (os.environ.get("KERNEL_510") and os.path.isdir(STREAMS)),
    reason="kernel tier: pinned corpus streams + KERNEL_510 must be set")
@pytest.mark.parametrize("stream", _IR_STREAMS)
def test_wk1_ir_wall_dead_in_streams(stream, tmp_path):
    # the boot.h:141 / bitops 'ir' sentence must be GONE — RED at tip
    # where the sweep says these answer `not in the M3 SUPPORT set`.
    src = _clean_i(os.path.join(STREAMS, stream), tmp_path, "wk1c")
    r = blcc(["-c", str(src), "-o", str(tmp_path / "o.o")])
    diag = r.stderr.replace(str(tmp_path), "")
    assert "not in the M3 SUPPORT set" not in diag, \
        "ir wall ALIVE in " + stream + ":\n" + diag[:400]
