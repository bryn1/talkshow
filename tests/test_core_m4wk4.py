# LINES reason: one wave of legs (M4 W-K COMMIT-4 — the INTERACTION TU:
# letter class + GNU sizeof(void) + offsetof-typeof in ONE translation
# unit; card 12404.2.79) — the wave's three classes must be SOUND
# TOGETHER, which per-class commits cannot show.
r"""M4 W-K COMMIT-4 — the interaction TU: the three shipped classes in
ONE translation unit, oracle-paired (card 12404.2.79).

The per-class commits each prove their own law; the kill-sim's combo rows
(SV+OT+IR = the shipped SET, predicted total 19) assume NO interference.
This file is the check of that assumption: a bitops-flavored set/return
pair (letters 'ir' imm AND reg + the CONST_MASK_ADDR void* walk), the
container_of/offsetof(typeof) chain IN THE SAME TU, static assertions
folding the same constants the runtime path computes, and a sizeof(void)
fold + arith + letter asm mixing in one function — every leg a run-pair
(values precomputed) or a BOTH-DIRECTION assertion pair.
"""
import os
import re
import subprocess
import sys

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


_MIX = """\
/* one TU, all three W-K classes touching the same objects */
#define WBYTE_ADDR(x)          "+m" (*(volatile char *) (x))
#define CONST_MASK_ADDR(nr, addr) WBYTE_ADDR((void *)(addr) + ((nr)>>3))
#define CONST_MASK(nr)         (1 << ((nr) & 7))
struct entry { int v; unsigned long word; struct entry *next; };
_Static_assert(sizeof(void) == 1, "sv law in the mix");
_Static_assert(__builtin_offsetof(typeof(struct entry), word) == 8,
               "ot law in the mix");
_Static_assert(__builtin_offsetof(typeof(*(struct entry *)0), next) == 16,
               "ot deref spelling");
static struct entry e = { 42, 0, 0 };
static void set_bit(long nr, volatile unsigned long *addr)
{
    asm volatile("orb %b1,%0" : CONST_MASK_ADDR(nr, addr)
                 : "iq" (CONST_MASK(nr)) : "memory");
}
static void set_bit_ir(long nr, volatile unsigned long *addr)
{
    asm volatile("btsq %1,%0" : "+m" (*(unsigned long *)addr)
                 : "ir" (nr) : "memory");
}
int main(void)
{
    void *p = &e.word;                 /* GNU void* arith: 1-byte scale */
    set_bit(3, (unsigned long *)((char *)p + 0));    /* word |= 8      */
    set_bit_ir(40, &e.word);           /* reg arm: word |= 1<<40       */
    if (e.word != (8UL | (1UL << 40))) return 1;
    p = (char *)p + 8;                 /* GNU arith round-trip: now at  */
    {   /* container_of over the typeof spelling recovers the object    */
        struct entry *back = (struct entry *)((char *)p -
            __builtin_offsetof(typeof(e), next));
        if (back == &e && back->v == 42) return 3;   /* all three hit */
    }
    return 2;
}
"""


def test_wk4_all_three_one_tu_pair(tmp_path):
    # every class exercised on the SAME object; the oracle says exit 3.
    _pair(tmp_path, "wk4_mix", _MIX, 3)


def test_wk4_mix_const_forms_anchor(tmp_path):
    # asm-form anchor over the mix TU: the imm arm ($8 via %b1's iq) and
    # the reg arm (btsq %reg) both visible in ONE -Os emission, no calls.
    s = tmp_path / "wk4_mix.c"
    s.write_text(_MIX)
    r = blcc(["--emit-asm", "-c", str(s), "-o",
              str(tmp_path / "wk4_mix.o")])
    assert r.returncode == 0, r.stderr
    a = r.stdout
    assert "$8" in a, "iq imm arm missing:\n" + a[-400:]
    assert re.search(r"btsq %(%r[a-z0-9]+|rax|rbx|rcx|rdx|rsi|rdi),", a), \
        "ir reg arm missing:\n" + a[-400:]
    for fn in ("set_bit", "set_bit_ir"):             # bit-op BODIES
        m = re.search(r"\n" + fn + r":\n(.*?)(?=\n[\w.]+:\n|\n    "
                      r"\.globl|\Z)", a, re.S)       # up to next label
        assert m, a[-300:]
        assert "call" not in m.group(1), \
            fn + " must be call-free:\n" + m.group(1)

