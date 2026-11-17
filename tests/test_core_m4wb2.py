"""M4 W-B COMMIT-2 (MC 12596) — __int128 CODEGEN: the pair arms.

Every shape below is MEASURED from gcc-11.4 -std=gnu89 (kernel recipe;
-Os bodies verbatim in .tmp/m4-wb/probes/ops2.Os.s, ops3/ops4) — blcc's
emission is the SAME instruction law over blcc's stack-machine idioms
(values are 16-byte objects, %rax carries the ADDRESS — commit-1):

  add  `addq lo; adcq hi`      sub  `subq lo; sbbq hi`
  and/or/xor  pairwise limb ops              ~  notq/notq
  neg  `negq lo; adcq $0,hi; negq hi`        ==/!=  xor,xor,or,set{e,ne}
  <u/>=u  `cmpq lo; movq ahi; sbbq bhi; set{c,nc}`; signed rides the SAME
      cmp/sbb with setl (measured flts body: the cross-sign cases fall out)
  shl imm N<64 `shldq $N,%rax,%rdx; salq $N,%rax`; N==64 `movq lo,%rdx;
      xorl %eax,%eax`; 64<N<128: hi=lo<<(N-64), lo=0 (fshl70);
  shr imm  `shrdq $N,%rdx,%rax; shrq|sarq $N,%rdx`; >=64 signed:
      `movq hi,%rax; cqto; sarq $N-64,%rax` (shrs70);
  VAR shifts INLINE with the `andb $64,%cl; cmovne` fixup (fshlv/fshrv/
      sgv measured) — NO libcall exists on this target (nm: no *shifti3);
  MUL  inline 3-term (fmul: two imulq + add for the cross, mulq for the
      square — NO __multi3 anywhere: nm-verified -O0 AND -Os);
  DIV/MOD → the FOUR libgcc calls __udivti3/__umodti3/__divti3/
      __modti3 (`call sym`, static link), a→rdi:rsi b→rdx:rcx, result
      rax:rdx, `pushq %rax`/`popq %rcx` alignment frame verbatim.

run-pair oracle: every value leg returns the byte fold
    fold(v) = l ^ (l>>32) ^ h ^ (h>>32)     (l = low limb, h = high limb)
    & 0xFF
whose expected value is PRE-COMPUTED in exact Python 128-bit arithmetic —
a THIRD witness beside both compilers (a wrong pair arm that agreed with
gcc would still have to agree with Python).

Truth of >64-bit LITERALS and shift counts >= 128 (both measured, both
gcc-WARN rc 0): blcc stays LOUD (the shipped lexer out-of-range law, the
§4 shift arm) — the twin legs pin the divergence so it can never go
silent. RED-first at cfb8fac: capture .tmp/m4-wb/out/red-commit2.txt.
"""
import os
import re
import subprocess
import sys

import pytest

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.environ.get("BLCC_REPO") or os.path.dirname(HERE)

MASK64 = (1 << 64) - 1
M128 = (1 << 128) - 1


def blcc(args):
    return subprocess.run([sys.executable, "-m", "blcc"] + args,
                          capture_output=True, text=True, cwd=REPO,
                          env={"PYTHONPATH": REPO, "PATH": "/usr/bin:/bin"})


def gcc(args):
    return subprocess.run(["gcc", "-std=gnu89", "-Os"] + args,
                          capture_output=True, text=True)


def fold(v):
    v &= M128
    l, h = v & MASK64, v >> 64
    return (l ^ (l >> 32) ^ h ^ (h >> 32)) & 0xFF


def sphex(v):
    """split a 128-bit value into two C ULL literals: HIULL * 2^64 + LOULL"""
    return "0x{:X}ULL * ((u128)1<<64) + 0x{:X}ULL".format(
        (v >> 64) & MASK64, v & MASK64)


def _pair(tmp_path, tag, src, expect):
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
    assert g.returncode == b.returncode == expect, \
        "run-pair: gcc {} blcc {} expect {}".format(
            g.returncode, b.returncode, expect)


def _asm(tmp_path, tag, src):
    s = tmp_path / (tag + ".c")
    s.write_text(src)
    r = blcc(["--emit-asm", "-c", str(s), "-o", str(tmp_path / (tag + ".o"))])
    assert r.returncode == 0, "blcc must compile:\n" + r.stderr
    return r.stdout


PRE = ("typedef unsigned long u64;\ntypedef unsigned int u32;\n"
       "typedef unsigned __int128 u128;\ntypedef __int128 i128;\n"
       "static unsigned foldp(u128 *p){ u64 l=(u64)*p, h=(u64)(*p>>64);\n"
       "  return (unsigned)(l ^ (l>>32) ^ h ^ (h>>32)); }\n"
       "#define fold(v) foldp(&(u128){v})\n")


def _fold_src(expr):
    return PRE + "int main(void){ return (int)fold(" + expr + "); }\n"


# ------------------------------------------------------- arithmetic pairs

def test_add_crosses_64(tmp_path):
    # (2^64-1) + 1 = 2^64: the CARRY must reach the hi limb. Dropping the
    # adcq leaves hi=0 — tooth plant #3 goes RED here.
    v = (1 << 64)
    src = _fold_src("((u128)0xFFFFFFFFFFFFFFFFULL) + (u128)1")
    _pair(tmp_path, "i128-add64", src, fold(v))


def test_add_hi_full(tmp_path):
    a, b = (1 << 64) + 0, (2 << 64) + 1
    src = _fold_src("((u128)1<<64) + (((u128)2<<64) + 1)")
    _pair(tmp_path, "i128-addhi", src, fold(a + b))


def test_sub_borrows(tmp_path):
    v = (1 << 65) - (1 << 40)
    src = _fold_src("((u128)1 << 65) - ((u128)1 << 40)")
    _pair(tmp_path, "i128-subb", src, fold(v))


def test_logic_pairwise(tmp_path):
    a = 0xF0F0F0F0F0F0F0F00F0F0F0F0F0F0F0F
    b = 0x0F0F0F0F0F0F0F0FF0F0F0F0F0F0F0F0
    src = (PRE + "u128 ga = " + sphex(a) + ";\nu128 gb = " + sphex(b)
            + ";\nint main(void){ return (int)(fold(ga & gb) ^ fold(ga | gb)"
              " ^ fold(ga ^ gb) ^ fold(~ga)); }\n")
    exp = (fold(a & b) ^ fold(a | b) ^ fold(a ^ b) ^ fold(~a & M128)) & 0xFF
    _pair(tmp_path, "i128-logic", src, exp)


def test_neg_pair(tmp_path):
    v = (1 << 128) - ((1 << 64) + 7)
    src = (PRE + "int main(void){ u128 a = ((u128)1<<64) + 7;\n"
           "  return (int)fold(-a); }\n")
    _pair(tmp_path, "i128-neg", src, fold(v))


# ------------------------------------------------------------ shifts

def test_shl_immediate_carry(tmp_path):
    v = 0xFF00000000000000 << 7
    src = _fold_src("((u128)0xFF00000000000000ULL) << 7")
    _pair(tmp_path, "i128-shl7", src, fold(v))


def test_shl_64_and_70(tmp_path):
    a = 12345678901234567890          # < 2^64
    _pair(tmp_path, "i128-shl64",
          _fold_src("((u128)12345678901234567890ULL) << 64"), fold(a << 64))
    c = 0xDEADBEEFCAFE
    _pair(tmp_path, "i128-shl70",
          _fold_src("((u128)0xDEADBEEFCAFEULL) << 70"), fold(c << 70))


def test_shr_imm_and_70(tmp_path):
    v = 0xFEDCBA9876543210_0123456789ABCDEF
    src = (PRE + "u128 ga = " + sphex(v) + ";\n"
           "int main(void){ return (int)fold(ga >> 7); }\n")
    _pair(tmp_path, "i128-shr7", src, fold(v >> 7))
    src2 = src.replace("ga >> 7", "ga >> 70")
    _pair(tmp_path, "i128-shr70", src2, fold(v >> 70))


def test_sar_signed(tmp_path):
    a = -(1 << 70)
    src = (PRE + "int main(void){ i128 a = -(((i128)1)<<70);\n"
           "  return (int)fold((u128)(a >> 7)); }\n")
    _pair(tmp_path, "i128-sar7", src, fold((a >> 7) & M128))


def test_shl_var(tmp_path):
    a = 0x1234567890ABCDEF
    src = (PRE + "u64 s7 = 7; u64 s64 = 64; u64 s70 = 70;\n"
           "int main(void){ u128 a = 0x1234567890ABCDEFULL;\n"
           "  return (int)(fold(a<<s7) ^ fold(a<<s64) ^ fold(a<<s70)); }\n")
    exp = (fold(a << 7) ^ fold(a << 64) ^ fold(a << 70)) & 0xFF
    _pair(tmp_path, "i128-shlv", src, exp)


def test_shrv_var(tmp_path):
    v = 0x0F00000000000000_0000000000000000
    src = (PRE + "u64 n71 = 71;\nu128 ga = " + sphex(v) + ";\n"
           "int main(void){ return (int)fold(ga >> n71); }\n")
    _pair(tmp_path, "i128-shrv", src, fold(v >> 71))


def test_sar_var_signed(tmp_path):
    a = -(1 << 60)
    src = (PRE + "u64 n8 = 8;\nint main(void){ i128 b = -(((i128)1)<<60);\n"
           "  return (int)fold((u128)(b >> n8)); }\n")
    _pair(tmp_path, "i128-sarv", src, fold((a >> 8) & M128))


# ---------------------------------------------------------- comparisons

def test_cmp_matrix(tmp_path):
    a, b, c = (1 << 64) + 7, 7, 1 << 64
    src = (PRE + "int main(void){\n"
           "  u128 a = ((u128)1<<64) + 7, b = 7, c = ((u128)1<<64);\n"
           "  return (int)((a>b) + 2*(a<b) + 4*(a==b) + 8*(a>=c)\n"
           "                + 16*(a!=c) + 32*(a<=b)); }\n")
    e = ((a > b) + 2 * (a < b) + 4 * (a == b) + 8 * (a >= c)
         + 16 * (a != c) + 32 * (a <= b)) & 0xFF
    _pair(tmp_path, "i128-cmpu", src, e)


def test_cmp_signed_across_sign(tmp_path):
    x, y, z = -1, 0, 1
    src = (PRE + "int main(void){\n"
           "  i128 x = -1, y = 0, z = 1;\n"
           "  return (int)((x<y) + 2*(y<x) + 4*(z>x) + 8*(x<z) + 16*(x==-1)"
           "); }\n")
    e = ((x < y) + 2 * (y < x) + 4 * (z > x) + 8 * (x < z)
         + 16 * (x == -1)) & 0xFF
    _pair(tmp_path, "i128-cmps", src, e)


def test_cmp_hi_only(tmp_path):
    # 2^64 vs 2^64+1: only the lo-limb differs and only the cmp leg sees it.
    a, b = 1 << 64, (1 << 64) + 1
    src = (PRE + "int main(void){ u128 a = (u128)1<<64, b = ((u128)1<<64)"
           " + 1;\n  return (int)((a<b) + 2*(b>a) + 4*(a==b) + 8*(b<=a)); }\n")
    e = ((a < b) + 2 * (b > a) + 4 * (a == b) + 8 * (b <= a)) & 0xFF
    _pair(tmp_path, "i128-cmph", src, e)


# ----------------------------------------------------------------- mul

def test_mul_terms(tmp_path):
    # 0x123456789 * 0x9ABCDEF0D is a 64-BIT product in C (both ULL) —
    # measured wrap mod 2^64 before the widen rides.
    e = (fold((0x123456789 * 0x9ABCDEF0D) & MASK64)
         ^ fold(3 * M128)
         ^ fold((1 << 63) * (1 << 63))) & 0xFF
    src = (PRE + "int main(void){ u128 a = 0x123456789ULL * 0x9ABCDEF0DULL;"
           "\n  u128 m1 = (u128)-1;\n"
           "  return (int)(fold(a) ^ fold(3*m1) ^ fold(((u128)1<<63) *"
           " ((u128)1<<63)));\n}\n")
    _pair(tmp_path, "i128-mul", src, e)


def test_mul_cross_term(tmp_path):
    # M4 W-F COMMIT-0 F1 (MC 12621, W-B gate F1 P2): BOTH limbs nonzero
    # in BOTH operands. Every pre-F1 mul product had hi==0 on one operand
    # or hi==lo on both — the cross term a_hi*b_lo + a_lo*b_hi then
    # collapses to the single imulq that survives, and mutant M10 (drop
    # the first `imulq (%rdx), %rcx`, blcc/i128.py) stayed GREEN over the
    # whole W-B battery. These three products split the two cross halves:
    #   (2^64+3)(2^64+5):   cross 5+3 = 8, M10 leaves 1+3 = 4
    #   (2^64+7)(3*2^64+11):cross 11+21 = 32, M10 leaves 1+21 = 22
    #   (2^64+2^63)^2:      cross 2^63+2^63 ≡ 0 carry-in, M10 leaves 1+2^63
    # RED capture (M10 applied, worktree at the shipped tree):
    # .tmp/m4-wf/out/red-m10-f1.txt — blcc runs exit wrong, pair assert.
    p1 = ((1 << 64) + 3) * ((1 << 64) + 5)
    p2 = ((1 << 64) + 7) * (3 * (1 << 64) + 11)
    p3 = ((1 << 64) + (1 << 63)) ** 2
    e = (fold(p1) ^ fold(p2) ^ fold(p3)) & 0xFF
    src = (PRE + "int main(void){\n"
           "  u128 a = (u128)1<<64, b = (u128)1<<63;\n"
           "  return (int)(fold((a+3)*(a+5)) ^ fold((a+7)*(3*a+11))\n"
           "                    ^ fold((a+b)*(a+b))); }\n")
    _pair(tmp_path, "i128-mulx", src, e)


def test_mul_no_libcall(tmp_path):
    # globals + (u64) trunc: the §6 byval wall (loud, corpus volume 0)
    # keeps function signatures OUT of these shape legs.
    s = tmp_path / "nm-mul.c"
    s.write_text(PRE + "u128 ga, gb;\nu64 m(void){ return (u64)(ga*gb); }\n")
    r = blcc(["-c", str(s), "-o", str(tmp_path / "nm-mul.o")])
    assert r.returncode == 0, r.stderr
    nm = subprocess.run(["nm", "-u", str(tmp_path / "nm-mul.o")],
                        capture_output=True, text=True).stdout
    assert "__multi3" not in nm and "ti3" not in nm, nm


def test_mul_asm_shape(tmp_path):
    asm = _asm(tmp_path, "mulsh",
               PRE + "u128 ga, gb;\nu64 m(void){ return (u64)(ga*gb); }\n")
    body = re.search(r"^m:.*?ret", asm, re.M | re.S).group(0)
    assert "mulq" in body and "imulq" in body, body       # measured fmul
    assert "call" not in body, body                       # NO libcall


# ------------------------------------------------------------ div/mod

def test_div_calls_libgcc(tmp_path):
    s = tmp_path / "nm-div.c"
    s.write_text(PRE + "u128 ga, gb; i128 sa, sb;\n"
                 "u64 d(void){ return (u64)(ga/gb); }\n"
                 "u64 r(void){ return (u64)(ga%gb); }\n"
                 "u64 ds(void){ return (u64)(sa/sb); }\n"
                 "u64 rs(void){ return (u64)(sa%sb); }\n")
    go = tmp_path / "nm-div.gcc.o"
    gr = gcc(["-c", str(s), "-o", str(go)])
    assert gr.returncode == 0, gr.stderr
    bo = tmp_path / "nm-div.o"
    br = blcc(["-c", str(s), "-o", str(bo)])
    assert br.returncode == 0, "blcc must compile:\n" + br.stderr

    def un(p):
        out = subprocess.run(["nm", "-u", str(p)], capture_output=True,
                             text=True).stdout
        return set(re.findall(r"__(?:u?div|u?mod)ti3|__multi3", out))
    gs, bs = un(go), un(bo)
    assert {"__udivti3", "__umodti3", "__divti3", "__modti3"} <= gs, \
        "oracle spellings: " + str(sorted(gs))
    assert gs == bs, "nm-parity: gcc {} blcc {}".format(sorted(gs),
                                                        sorted(bs))


def test_div_loud_at_link(tmp_path):
    s = tmp_path / "divlink.c"
    s.write_text(PRE + "int main(void){ u128 a = 100, b = 7;\n"
                 "  return (int)fold(a/b); }\n")
    r = blcc([str(s), "-o", str(tmp_path / "divlink")])
    assert r.returncode != 0, "must not silently link"
    assert "__udivti3" in (r.stdout + r.stderr), \
        "link failure must name the pair-runtime symbol:\n" + r.stderr


# ------------------------------------------------ the kernel crown

def test_mul_u64_u32_shr_witness(tmp_path):
    src = (PRE +
           "static inline u64 mul_u64_u32_shr(u64 a, u32 mul,"
           " unsigned int shift)\n{\n\treturn (u64)(((u128)a * mul) >>"
           " shift);\n}\n"
           "int main(void){\n"
           "  u64 x = mul_u64_u32_shr(3, 5, 2);\n"
           "  x ^= mul_u64_u32_shr(0xFFFFFFFFFFFFFFFFULL, 0x80000000U, 31);\n"
           "  x ^= mul_u64_u32_shr(0xDEADBEEFDEADBEEFULL, 0x12345678U, 64);\n"
           "  x ^= mul_u64_u32_shr(1, 1, 0);\n"
           "  return (int)(x & 255); }\n")

    def w(a, mul, sh):
        return ((a * mul) >> sh) & MASK64
    x = (w(3, 5, 2) ^ w(0xFFFFFFFFFFFFFFFF, 0x80000000, 31)
         ^ w(0xDEADBEEFDEADBEEF, 0x12345678, 64) ^ w(1, 1, 0)) & MASK64
    _pair(tmp_path, "i128-math64", src, x & 0xFF)


def test_truth_pair_test(tmp_path):
    src = (PRE + "int main(void){ u128 h = (u128)1 << 64;\n"
           "  u128 z = (u128)0;\n  int r = 0;\n"
           "  if (h) r |= 1;\n  if (z) r |= 2;\n"
           "  if (!h) r |= 4;\n  if (h && z) r |= 8;\n"
           "  if (h || z) r |= 16;\n  return r; }\n")
    _pair(tmp_path, "i128-truth", src, 1 | 16)


# ---------------------------------------------------------- twin walls

def test_literal_overflow_stays_loud(tmp_path):
    s = tmp_path / "lito.c"
    s.write_text("typedef unsigned long long ull;\n"
                 "ull a = 18446744073709551616;\n"
                 "int main(void){ return (int)(a & 255); }\n")
    g = gcc([str(s), "-o", str(tmp_path / "lito.gcc")])
    assert g.returncode == 0                            # wraps, warns
    b = blcc([str(s), "-o", str(tmp_path / "lito.b")])
    assert b.returncode == 2 and "out of range" in b.stderr, b.stderr


def test_shift_count_ge128_loud_twin(tmp_path):
    s = tmp_path / "shbig.c"
    s.write_text(PRE + "u128 ga;\nu128 f(void){ return ga << 128; }\n"
                 "int main(void){return 0;}\n")
    g = gcc(["-c", str(s), "-o", os.devnull])
    assert g.returncode == 0 and "shift-count" in g.stderr
    b = blcc(["-c", str(s), "-o", str(tmp_path / "shbig.o")])
    assert b.returncode == 2 and "128" in b.stderr, b.stderr
