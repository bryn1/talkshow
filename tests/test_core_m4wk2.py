# LINES reason: one wave of legs (M4 W-K COMMIT-2 — sizeof(void) = GNU 1
# + void* arithmetic; card 12404.2.79) — the fold/codegen mirrors of ONE
# law split across files; one test file keeps the law's witnesses together.
r"""M4 W-K COMMIT-2 — sizeof(void) is GNU 1: the void law ships everywhere
at once (236 first-blockers; the bitops CONST_MASK_ADDR carriers).

MEASURED LAW (gcc 11.4 -std=gnu89, my probes .tmp/m4-wk/probes/sv_*):
  sizeof(void) == 1              rc0 at EVERY std flag I tried
                                 (gnu89/c89/c99/c11/c2x), no warning even
                                 with -Wall -Werror (only -pedantic
                                 mentions it; the kernel recipe has none)
  sizeof(*(void*)0) == 1         rc0 — the deref spells the SAME thing
  void* + k                      scale factor 1 (byte units)   rc0
  void* - void*                  byte difference (probe sv_sub: 10) rc0
  __alignof__(void)              1 (sv_al2.s: `.long 1`)
TIP POSTURE (measured, the same TU): the fold mirror answers sizeof(void)
= 0 (TYPE_SIZE["void"]), the codegen mirror LOUDs `'sizeof(void)' is not
in the subset (§4)` (types.py:243) — ONE compiler, TWO wrong answers, gcc
has one right one. `_Static_assert(sizeof(void) == 0)` passes at tip.
THE SWEEP'S BIGGEST WALL: 236 streams first-fail at bitops.h:56 — the
CONST_MASK_ADDR expansion `(void *)(addr) + ((nr)>>3)` inside the LOCK
orb sites: void* arithmetic needs the GNU scale = sizeof(void) = 1.

MECHANISM: GNU 1 in BOTH mirrors of the shipped layout law — the fold
mirror `_csize_impl` BuiltinType arm and the codegen mirror `TypeMap.
_size` — NO third rail, NO table entry change (TYPE_SIZE["void"]=0 stays:
it documents that void has no OBJECT, the arm carries the law).
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


# ----------------------------------------------------------- fold mirror

def test_wk2_sizeof_void_is_one_not_zero(tmp_path):
    # BOTH directions in one leg (RED both ways at tip: the fold answers
    # 0, so ==1 fails and ==0 WRONGLY passes).
    s1 = tmp_path / "sv_eq1.c"
    s1.write_text('_Static_assert(sizeof(void) == 1, "one");\n'
                  "int f(void){ return 0; }\n")
    r = blcc(["-c", str(s1), "-o", str(tmp_path / "sv1.o")])
    assert r.returncode == 0, \
        "sizeof(void) must fold GNU 1:\n" + r.stderr
    g = gcc(["-Os", "-c", str(s1), "-o", "/dev/null"])
    assert g.returncode == 0, g.stderr
    s0 = tmp_path / "sv_eq0.c"
    s0.write_text('_Static_assert(sizeof(void) == 0, "zero");\n'
                  "int f(void){ return 0; }\n")
    r0 = blcc(["-c", str(s0), "-o", str(tmp_path / "sv0.o")])
    g0 = gcc(["-Os", "-c", str(s0), "-o", "/dev/null"])
    assert g0.returncode == 1, g0.stderr          # oracle REJECTS == 0
    assert r0.returncode == 2 and "static assertion failed" in r0.stderr, \
        "the old fold-zero law must die with the wave:\n" + r0.stderr


def test_wk2_sizeof_deref_voidptr_pair(tmp_path):
    # `sizeof(*(void*)0)` — the deref spelling of the SAME law: gcc rc0
    # (incomplete-type rule is BYPASSED for void under GNU; sv_deref).
    _pair(tmp_path, "wk2_deref",
          "unsigned long f(void){ return sizeof(*(void *)0); }\n"
          "int main(void){ return f() == 1 ? 5 : 0; }\n", 5)


# ------------------------------------------------------ codegen mirrors

def test_wk2_void_arith_pair(tmp_path):
    # GNU void* + k scales by 1 (byte units) and void* - void* is the
    # BYTE difference — values 4 and 10, precomputed, oracle-run.
    _pair(tmp_path, "wk2_arith",
          "unsigned char buf[64];\n"
          "unsigned long f(void){ void *p = buf; p = p + 4;\n"
          "  return (unsigned long)((char *)p - (char *)buf); }\n"
          "unsigned long g(void){ void *p = buf + 10; void *q = buf;\n"
          "  return (unsigned long)(p - q); }\n"
          "int main(void){ if (f() != 4) return 1; if (g() != 10) "
          "return 2; return 3; }\n", 3)


def test_wk2_alignof_void_pair(tmp_path):
    # fairness (green at tip AND after): __alignof__(void) is ALREADY 1
    # through the shipped align fold — the wave must not move it.
    _pair(tmp_path, "wk2_al",
          "int a = __alignof__(void);\n"
          "int main(void){ return a == 1 ? 6 : 0; }\n", 6)


# ------------------------------------- THE kill-sim witness, verbatim

def test_wk2_bitops_const_mask_addr_pair(tmp_path):
    # arch/x86/include/asm/bitops.h:45-46 + 54-58 VERBATIM (kcopy), the
    # kill-sim's single proof of the accept law — REAL bit-op values:
    # nr=11 -> byte (11>>3)=1 gets mask 1<<(11&7)=8 -> word 0x0800.
    src = (
        "#define LOCK_PREFIX \"\"          /* uniprocessor: measure keeps "
        "the macro shape */\n"
        "#define WBYTE_ADDR(x)\t\t\"+m\" (*(volatile char *) (x))\n"
        "#define CONST_MASK_ADDR(nr, addr)\tWBYTE_ADDR((void *)(addr) + "
        "((nr)>>3))\n"
        "#define CONST_MASK(nr)\t\t\t(1 << ((nr) & 7))\n"
        "unsigned long w;\n"
        "static inline void arch_set_bit(long nr, volatile unsigned long "
        "*addr)\n{\n"
        "\tasm volatile(LOCK_PREFIX \"orb %b1,%0\"\n"
        "\t\t: CONST_MASK_ADDR(nr, addr)\n"
        "\t\t: \"iq\" (CONST_MASK(nr))\n"
        "\t\t: \"memory\");\n}\n"
        "int main(void){ w = 0; arch_set_bit(11, &w);\n"
        "  return w == 0x0800UL ? 9 : 0; }\n")
    _pair(tmp_path, "wk2_bitops", src, 9)


# ------------------------------------------------- corpus witnesses (kern)

import pytest

_SV_STREAMS = ["arch_x86_entry_common.c.i",
               "arch_x86_entry_syscall_64.c.i", "mm_vmacache.c.i"]


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
@pytest.mark.parametrize("stream", _SV_STREAMS)
def test_wk2_sizeof_void_wall_dead_in_streams(stream, tmp_path):
    # the §4 sentence must be GONE on the bitops carriers (they may die
    # LATER at other walls — the assert is ONLY on this wall).
    src = _clean_i(os.path.join(STREAMS, stream), tmp_path, "wk2c")
    r = blcc(["-c", str(src), "-o", str(tmp_path / "o.o")])
    diag = r.stderr.replace(str(tmp_path), "")
    assert "sizeof(void)' is not in the subset" not in diag, \
        "sizeof-void wall ALIVE in " + stream + ":\n" + diag[:300]
