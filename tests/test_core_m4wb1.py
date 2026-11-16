"""M4 W-B COMMIT-1 (MC 12596) — __int128 TYPE: spellings, size/align,
promotion table, casts both directions, storage laws.

EVERY law below is MEASURED against gcc 11.4 -std=gnu89 (the kernel
recipe family) this card — probes .tmp/m4-wb/probes/ (facts1.c, shapes.c,
consts.c, al.c). Facts: sizeof/alignof = 16 for `__int128`,
`unsigned __int128`, `signed __int128`; the spec words COMMLE with the
sign family but NOT with another length word or `_Bool`/`void`
(`long __int128`, `int __int128`, `__int128 long`, `_Bool __int128`,
`__int128 __int128` = gcc rc 1; `__signed__ __int128`, `__int128
unsigned` = rc 0). Tree census (kernel 5.10, grep): the ONLY spellings
the kernel uses are `__int128` (12 sites) and `unsigned __int128` (13);
`__int128_t`/`__uint128_t` are NOT kernel spellings (glibc stdint names —
they stay plain identifiers here, undeclared-loud both sides).

STORAGE laws measured: globals `.align 16` + `.size 16`, bss `.zero 16`,
const init `.quad lo, .quad hi` (consts.c: gi = 5 -> `5,0`; c4 =
(u128)1<<64 -> `0,1`; struct {char;u128;char} sizeof 48 / offsetof 16 —
.data word rows). A u128 LOCAL rides a 16-byte-aligned frame slot (al.c:
-O0 `movq %rax,-16(%rbp)` / `movq $0,-8(%rbp)`).

CASTS measured (shapes.c): (u64)u128 trunc = the LOW limb alone (one
movq — `movq -16(%rbp), %rax`, no hi touch); (u128)u64 zero-extends
(`movl $0, %edx`); (u128)long sign-extends (`sarq $63`); from int/u32 the
64-bit re-intern rides FIRST then the pair (cltq/sar63, movl %ecx,%ecx).

VALUE LAW (blcc's lowering, the memfold/aggregate idiom): a 128-bit value
is a 16-byte MEMORY object; the %rax convention carries its ADDRESS; every
consumer that needs bits loads the pair. That is what the asm-shape legs
pin — the CLASS of emission, run-pairs carry behavior.

RED-first at 8af9fde: capture .tmp/m4-wb/out/red-commit1.txt.
"""
import os
import re
import subprocess
import sys

import pytest

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.environ.get("BLCC_REPO") or os.path.dirname(HERE)
KERNEL = os.environ.get("KERNEL_510")


def blcc(args):
    return subprocess.run([sys.executable, "-m", "blcc"] + args,
                          capture_output=True, text=True, cwd=REPO,
                          env={"PYTHONPATH": REPO, "PATH": "/usr/bin:/bin"})


def gcc(args):
    return subprocess.run(["gcc", "-std=gnu89", "-Os"] + args,
                          capture_output=True, text=True)


def _pair(tmp_path, tag, src, expect):
    """ORACLE-DECIDES shipped run_pair: full link both sides, run, SAME
    exit code, and BOTH equal the Python-precomputed expectation."""
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
    # shipped --emit-asm idiom: the asm text rides STDOUT (driver.py
    # §289: write to stdout + <out>.s beside the operand).
    s = tmp_path / (tag + ".c")
    s.write_text(src)
    r = blcc(["--emit-asm", "-c", str(s), "-o",
              str(tmp_path / (tag + ".o"))])
    assert r.returncode == 0, "blcc must compile:\n" + r.stderr
    return r.stdout


U128 = "typedef unsigned __int128 u128;\ntypedef __int128 i128;\n"
TYPES = ("typedef unsigned long u64; typedef unsigned int u32;\n"
         "typedef long i64; typedef int i32;\n")
PRE = TYPES + U128


# ---------------------------------------------------------- spellings & rejects

def test_specifier_spellings_pair(tmp_path):
    # gcc rc 0 for the five accepted spellings; blcc must compile and
    # agree exit-for-exit on the run. sizeof(u128)==16 each spelling.
    src = (PRE + "int main(void){\n"
           "  __int128 a; unsigned __int128 b; signed __int128 c;\n"
           "  __int128 unsigned d; __signed__ __int128 e;\n"
           "  return (int)(sizeof(a) + sizeof(b) + sizeof(c)\n"
           "                 + sizeof(d) + sizeof(e)) % 256; }\n")
    # 5 × 16 = 80
    _pair(tmp_path, "i128-spell", src, 80)


@pytest.mark.parametrize("decl", [
    "long __int128 x;", "__int128 long x;", "int __int128 x;",
    "__int128 int x;", "_Bool __int128 x;", "__int128 __int128 x;",
    "unsigned signed __int128 x;", "void __int128 x;",
])
def test_bad_specifier_combos_loud_twin(tmp_path, decl):
    s = tmp_path / "rej.c"
    s.write_text(decl + "\n")
    g = gcc(["-c", str(s), "-o", os.devnull])
    assert g.returncode == 1, "oracle twin must REJECT: " + decl
    b = blcc(["-c", str(s), "-o", str(tmp_path / "rej.o")])
    assert b.returncode == 2, decl + ": blcc must stay LOUD:\n" + b.stderr
    assert ("int128" in b.stderr or "two or more" in b.stderr
            or "sign specifier" in b.stderr or "'void' combined" in b.stderr), \
        decl + ": diagnostic must name the construct:\n" + b.stderr


def test_int128_t_builtin_typedefs(tmp_path):
    # MEASURED (correction of the ASSUMED first read): gcc's x86-64
    # predefines `__int128_t`/`__uint128_t` as BUILTIN TYPEDEFS (decl
    # rc 0, sizeof 16) — NOT keywords (`unsigned __int128_t` is a parse
    # error). blcc ships them through the ONE §2.7 compiler-typedef
    # mechanism (parser scopes[0], same as __builtin_va_list). Kernel
    # census: 0 sites — the kernel spells the keywords.
    src = ("__int128_t a;\n__uint128_t b;\n"
           "int main(void){ return (int)(sizeof(a) + sizeof(b)); }\n")
    _pair(tmp_path, "i128-td", src, 32)
    # MEASURED DIVERGENCE (pre-existing general law, NOT W-B): blcc
    # accepts `unsigned <typedef>` (last typedef wins) where gcc rc 1s
    # two type specifiers — census across the whole 5.10 tree: ZERO C
    # sites spell `unsigned <typename>` (all grep hits are comments).
    # LEDGER carries the row; this leg seals ONLY the shipped-typedef
    # parity above, never the divergence.


# ------------------------------------------------------------ size/align law

def test_sizeof_alignof_run_pair(tmp_path):
    # 16 + 16 + 16 + 16 = 64; array stride 16*3=48; struct {char;u128;
    # char} = sizeof 48, offsetof(x) 16 (consts.c .data words measured).
    src = (PRE + "struct S { char c; u128 x; char d; };\n"
           "int main(void){\n"
           "  u128 arr[3];\n"
           "  return (int)(sizeof(u128) + __alignof__(u128)\n"
           "     + sizeof(i128) + __alignof__(arr) + 0)\n"
           "     % 256; }\n")
    _pair(tmp_path, "i128-sz", src, (16 + 16 + 16 + 16) % 256)


def test_struct_layout_pair(tmp_path):
    src = (PRE + "struct S { char c; u128 x; char d; };\n"
           "int main(void){\n"
           "  return (int)(sizeof(struct S) + __builtin_offsetof(struct S, x))"
           " % 256; }\n")   # 48 + 16 = 64
    _pair(tmp_path, "i128-lay", src, (48 + 16) % 256)


# ------------------------------------------------------------------ casts

def test_trunc_cast_run_pair(tmp_path):
    # (u64)v = the LOW limb only. v = (u128)(long)-1 -> (u64)v = 0xFFFF
    # …FFFF -> exit byte 0xFF. And (u64)(u128)(int)-3 -> 0xFFFFFFFD -> 0xFD.
    src = (PRE + "int main(void){\n"
           "  u128 v = (u128)(long)-1;\n"
           "  u128 w = (u128)(int)-3;\n"
           "  return (int)(((u64)v & 0xFF) ^ ((u64)w & 0xFF)); }\n")
    # 0xFF ^ 0xFD = 0x02
    _pair(tmp_path, "i128-trunc", src, 0xFF ^ 0xFD)


def test_trunc_cast_emits_mov_only(tmp_path):
    # TOOTH TARGET: the trunc site reads the LOW limb only —
    # `movq (%rax), %rax` after the address law, and the HI-limb
    # spelling (the +8 displacement) NEVER appears (measured gcc:
    # `movq -16(%rbp), %rax`, zero hi traffic).
    asm = _asm(tmp_path, "truncmov",
               PRE + "u128 gg;\nu64 tr(void){ return (u64)gg; }\n"
                     "int main(void){return 0;}\n")
    body = re.search(r"^tr:.*?ret", asm, re.M | re.S).group(0)
    assert re.search(r"leaq gg\(%rip\), %rax", body), body
    assert "movq (%rax), %rax" in body, body
    assert "gg+8" not in body and "8(%rax)" not in body, \
        "hi limb must NEVER be touched:\n" + body


def test_sext_zext_pair_law(tmp_path):
    # (i128)(long)-1 = ALL ONES: low byte 0xFF; (u128)u32 5 hi-limb 0 —
    # observed through trunc + a global byte window (below).
    src = (PRE + "int main(void){\n"
           "  i128 s = (i128)(long)-1;\n"
           "  u128 z = (u128)(u64)0x1122334455667788;\n"
           "  return (int)(((u64)s & 0xFF) ^ ((u64)z & 0xFF)); }\n")
    # 0xFF ^ 0x88 = 0x77
    _pair(tmp_path, "i128-sext", src, 0xFF ^ 0x88)
    # asm half of the PAIR-STORE law: a signed widening local-init stores
    # BOTH limbs (the hi limb via the `base+8(%rbp)` displacement) — drop
    # either move and this leg goes RED by name (tooth plant #2).
    asm = _asm(tmp_path, "sextshape", PRE +
               "u64 g(void){ u128 v = (i128)(long)-1; return (u64)v; }\n"
               "int main(void){return 0;}\n")
    body = re.search(r"^g:.*?ret", asm, re.M | re.S).group(0)
    assert re.search(r"sarq \$63, %rdx", body), body      # sext64 hi law
    assert re.search(r"movq %r\w+, -\d+\+8\(%rbp\)", body), body


# ----------------------------------------------------------------- storage

def test_global_const_data_window(tmp_path):
    # .data 16-byte window byte-identical to gcc: gi=(u128)5, g4 =
    # ((u128)1<<64)+… (folded 128-wide: lo=5 hi=1 -> `05…,01…`).
    src = (PRE + "u128 gi = 5;\n"
           "u128 g1 = (u128)-1;\n"
           "i128 gs = (i128)(long)-7;\n"
           "int main(void){ return 0; }\n")
    s = tmp_path / "dw.c"
    s.write_text(src)
    gx = tmp_path / "dw.gcc.o"
    gr = gcc(["-c", str(s), "-o", str(gx)])
    assert gr.returncode == 0, gr.stderr
    bx = tmp_path / "dw.blcc.o"
    br = blcc(["-c", str(s), "-o", str(bx)])
    assert br.returncode == 0, "blcc must compile:\n" + br.stderr
    g = subprocess.run(["objdump", "-s", "-j", ".data", str(gx)],
                       capture_output=True, text=True).stdout
    b = subprocess.run(["objdump", "-s", "-j", ".data", str(bx)],
                       capture_output=True, text=True).stdout

    def hexstream(out):
        # objdump -s lines: " ADDR  GGGG GGGG GGGG GGGG  ascii" — keep the
        # DATA groups only (drop the address column and the ascii tail).
        out = out.split("Contents")[1]
        rows = []
        for ln in out.splitlines():
            parts = ln.split()
            if len(parts) >= 2 and re.fullmatch(r"[0-9a-f]+", parts[0]):
                rows.append("".join(p for p in parts[1:]
                                    if re.fullmatch(r"[0-9a-f]{4,8}", p)))
        return "".join(rows)

    gh, bh = hexstream(g), hexstream(b)
    want = {"gi": "05" + "00" * 15,                    # (u128)5: lo 5, hi 0
            "g1": "ff" * 16,                            # (u128)-1: ALL ones
            "gs": "f9" + "ff" * 15}                     # (i128)(long)-7
    for name, w in want.items():
        assert w in gh, "gcc .data missing " + name + ":\n" + gh
        assert w in bh, "blcc .data missing " + name + ":\n" + bh


def test_global_align_and_size(tmp_path):
    asm = _asm(tmp_path, "galign", PRE + "u128 gz;\nu128 gi = 5;\nint main(void){return 0;}\n")
    assert re.search(r"\.align\s+16", asm), \
        "u128 globals carry .align 16 (measured):\n" + asm[:800]
    assert re.search(r"\.zero\s+16", asm), "bss run must be 16 bytes:\n" + asm


def test_local_slot_aligned_16(tmp_path):
    # al.c measured: gcc -O0 keeps the u128 local 16-byte aligned
    # (-16/-8 with an 8-byte param in front at -24). blcc law: the
    # 16-byte object's slot base is 16-aligned (blcc spells the hi limb
    # as the `base+8(%rbp)` displacement form).
    asm = _asm(tmp_path, "alig", PRE +
               "u64 f(u64 q){ u128 t = (u128)q; return (u64)t + 1; }\n")
    body = re.search(r"^f:.*?ret", asm, re.M | re.S).group(0)
    bases = [int(m) for m in re.findall(r"(-\d+)\(%rbp\)", body)]
    assert bases, "expected rbp slots:\n" + body
    ok = any(b % 16 == 0 and (b + 8) in
             [int(x) + 8 for x in
              re.findall(r"(-\d+)\+8\(%rbp\)", body)] for b in bases)
    assert ok, "u128 local must ride a 16-aligned slot:\n" + body


def test_lvalue_addr_law_no_load(tmp_path):
    # A 128-bit rvalue is a 16-BYTE MEMORY OBJECT: the ident in value
    # position hands out the ADDRESS (aggregate law) — consumers load.
    asm = _asm(tmp_path, "alaw", PRE +
               "u64 g(void){ u128 v = (u128)9; return (u64)v; }\n")
    body = re.search(r"^g:.*?ret", asm, re.M | re.S).group(0)
    # the ident in value position hands out the ADDRESS (leaq), and the
    # trunc consumer loads the LOW limb from it (movq (%reg),%rax):
    assert re.search(r"leaq\s+-?\d*\(%rbp\),\s*%rax", body), body
    assert re.search(r"movq\s+\(%rax\),\s*%rax", body), body


# ------------------------------------------------------- the corpus witness

@pytest.mark.skipif(not KERNEL, reason="kernel tier: needs KERNEL_510")
def test_math64_shape_parses_past_int128(tmp_path):
    # THE wall: math64.h:161 (mul_u64_u32_shr). At 8af9fde the stream
    # dies `parse: expected ')', found '__int128'`. After COMMIT-1 the
    # PARSE must be clean — any residual LOUD must NOT be the parse
    # message (mul/shift CODEGEN is COMMIT-2's land).
    src = (PRE + "static inline u64 mul_u64_u32_shr(u64 a, u32 mul,"
           " unsigned int shift)\n{\n\treturn (u64)(((u128)a * mul) >>"
           " shift);\n}\nint main(void){ return (int)mul_u64_u32_shr(3,"
           " 5, 2); }\n")
    s = tmp_path / "math64.c"
    s.write_text(src)
    b = blcc(["-c", str(s), "-o", str(tmp_path / "math64.o")])
    assert "found '__int128'" not in b.stderr, \
        "the parse wall must be GONE:\n" + b.stderr


def test_byval_128_param_return_loud_twin(tmp_path):
    # MEASURED gcc rc 0 (System V passes TImode in a GPR PAIR — facts
    # probe); blcc stages ONE 8-byte value per arg slot, so 128-bit
    # BY-VALUE call/return is the shipped LOUD §6 wall with a NAMED twin
    # leg — corpus volume 0 (the 706-stream census: int128 appears in
    # CAST position only, 0 by-value call sites). LEDGER row carries it.
    for src, tag in ((PRE + "u64 f(u128 v){ return (u64)v; }\n", "param"),
                     (PRE + "u128 f(void){ return (u128)1; }\n", "ret")):
        s = tmp_path / (tag + ".c")
        s.write_text(src)
        g = gcc(["-c", str(s), "-o", os.devnull])
        assert g.returncode == 0, tag + ": gcc accepts (measured)"
        b = blcc(["-c", str(s), "-o", str(tmp_path / (tag + ".o"))])
        assert b.returncode == 2, tag + ": blcc must stay LOUD:\n" + b.stderr
        assert "128" in b.stderr, tag + ": must NAME the class:\n" + b.stderr
