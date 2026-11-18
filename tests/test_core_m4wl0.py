# LINES reason: M4 W-L COMMIT-0 legs (card 12404.2.81) — the F-5 LOUD
# restore (wave-caused) + the F-1..F-4/F-9 inventory pins. One file so the
# gate-fail carry and the MEASURED oracle table ship in one row.
r"""M4 W-L COMMIT-0 — F-5 LOUD RESTORE + INVENTORY PINS (gate MC 12664 F-rows,
AMENDMENT-13 carry).

MEASURED §5 TABLE (MY OWN probes, gcc 11.4.0 -std=gnu89 -Os
-fno-inline-functions-called-once -mno-red-zone, TWO-TU so every call is a
REAL call — inlining at -Os folds single-call functions and LIES rc-no-call;
the kernel builds the same way: -Os at Makefile:762, -fno-inline-functions-
called-once at Makefile:930, -mno-red-zone at arch/x86/Makefile:140;
captures .tmp/m4-wl/probes/m*.s):
  K=1 stack arg (7 scalars) m01: rdi..r9 + 1 pushed slot + ONE junk push
      for 16-byte alignment; `addq $24,%rsp` after the call; rsp % 16 == 0
      AT the call instruction, always.
  K=2 (8 scalars) m02: two pushes, right-to-left, NO extra pad (addq $24).
  K=3 (9 scalars) m03: three arg pushes + ONE junk pad push (addq $40).
  LAW: pushes are right-to-left (first stack arg LOWEST = at the return
      address); the call site keeps rsp ≡ 0 (mod 16) — an ODD number of
      stack args costs one pad push/push-equivalent, an EVEN number none.
  Callee read-back m04/m05: leaf: arg(7+i) rides {8+8i}(%rsp);
      an rbp-frame callee reads {16+8i}(%rbp) — 16(%rbp), 24(%rbp),
      32(%rbp) for args 7,8,9,10 (blcc's frame is the rbp form).
  Non-leaf callee m07: reads the incoming slot ONCE ({16}(%rsp) after its
      own pushes shift it) — the incoming area is authoritative.
  Address-taken stack param m14: NO copy — the address IS the incoming
      slot (blcc's spill-to-slot is its uniform law; value-equal, pinned
      by run-pairs).
  Widths m06: sub-8 args are EXTENDED to full 8-byte slots by the caller
      (movsbl for char) — every stack arg is exactly 8 bytes.
  Struct-by-value size classes m08 (all LOUD in blcc, pinned in COMMIT-1):
      ≤8 INTEGER = 1 GPR; 9..16 all-INTEGER = 2 GPR; padded char+long
      (16) = 2 GPR, char in the low byte; 12 (int,int,int) = 2 GPR
      (INTEGER eightbytes); 24 (MEMORY) = words ASCENDING from the stack,
      following scalars take %rdi — a MEMORY-class arg consumes NO GP
      registers at -Os.
  Red zone m09 (-mno-red-zone): a function that calls NEVER touches
      [rsp-128,%rsp); locals/temps live below a REAL subq — blcc's frames
      already honour this (locals negative-from-rbp inside the frame,
      temps positive-from-rsp INSIDE the frame, push block below rsp).
  varargs m12: `xorl %eax,%eax` before the call; stack extras right-to-left.
  Nested calls m11/m13: each inner call completes BEFORE the outer's push
      block stages its args; a stack-arg slot may be filled IN PLACE after
      its push (m13 `movq %rbp,(%rsp)`) — blcc stages to temps first (the
      shipped §2.14 law), value-equal.
  tail call m10: at -Os a >6-arg call in tail position is a REAL call +
      addq, NOT a jmp (register-only tail calls may jmp — blcc always
      emits call+ret, a correct superset).

F-5 (WAVE-CAUSED, gate MC 12664): `void a[4];` was LOUD rc2 at the W-K base
and became a SILENT ACCEPT rc0 when sizeof(void)=GNU-1 shipped (the array
element size stopped raising). gcc rc1 "declaration of 'a' as array of
voids" at EVERY void-array declarator spelling. Volume 0 in the 706. This
commit restores the LOUD verdict through the ONE declarator fold. The
NON-array void siblings (`void v;`, a bare void member) were ALREADY
accepted at the W-K base — pre-existing divergence, pinned below, not
touched here.
"""
import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.environ.get("BLCC_REPO") or os.path.dirname(HERE)


def blcc(args):
    return subprocess.run([sys.executable, "-m", "blcc"] + args,
                          capture_output=True, text=True, cwd=REPO,
                          env={"PYTHONPATH": REPO,
                               "PATH": "/usr/bin:/bin"})


def gcc(args):
    return subprocess.run(["gcc", "-std=gnu89"] + args,
                          capture_output=True, text=True,
                          env={"PATH": "/usr/bin:/bin"})


def _loud_both(tmp_path, tag, src, needle):
    """verdict-pair: gcc rc1 (its sentence in its stderr) AND blcc rc!=0
    naming the class; returns blcc stderr."""
    s = tmp_path / (tag + ".c")
    s.write_text(src)
    g = gcc(["-c", str(s), "-o", str(tmp_path / (tag + ".g.o"))])
    assert g.returncode == 1, "oracle must reject:\n" + g.stderr
    b = blcc(["-c", str(s), "-o", str(tmp_path / (tag + ".b.o"))])
    assert b.returncode != 0, \
        "F-5 silent-accept restored? blcc rc0 on:\n" + src
    assert needle in b.stderr, "blcc must name the class: " + b.stderr
    return b.stderr


# ------------------------------------------------- F-5 void-array LOUD

def test_wl0_f5_void_array_loud_again(tmp_path):
    # THE regression leg (RED at the W-K tip): gcc rc1 "declaration of 'a'
    # as array of voids"; W-K's sizeof(void)=1 made blcc answer rc0.
    _loud_both(tmp_path, "wl0_f5_a", "void a[4];\nint main(void){return 0;}\n",
               "array of 'voids'")


def test_wl0_f5_void_array_member(tmp_path):
    _loud_both(tmp_path, "wl0_f5_m",
               "struct S{ void v[4]; };\nint main(void){return 0;}\n",
               "array of 'voids'")


def test_wl0_f5_extern_void_array(tmp_path):
    # `extern void v[];` was SILENT at the base too (gate: same class);
    # gcc rc1 — the restore covers every void-array spelling.
    _loud_both(tmp_path, "wl0_f5_e",
               "extern void v[];\nint main(void){return 0;}\n",
               "array of 'voids'")


def test_wl0_f5_param_void_array(tmp_path):
    _loud_both(tmp_path, "wl0_f5_p",
               "int f(void v[]){return 0;}\nint main(void){return 0;}\n",
               "array of 'voids'")


def test_wl0_f5_sizeof_void_array(tmp_path):
    # sizeof TYPE arm: parse_type builds the suffix OUTSIDE _fold_ops —
    # the SAME judge rides both arms (one mechanism). gcc rc1.
    _loud_both(tmp_path, "wl0_f5_s",
               "int n = sizeof(void[2]);\nint main(void){return 0;}\n",
               "array of 'voids'")


def test_wl0_f5_sibling_void_decl_pins(tmp_path):
    # The NON-array void siblings were ALREADY blcc-accepted at the W-K
    # base (gate: "ALREADY accepted at base") — documented pre-existing
    # DIVERGENCE, volume 0; retires with the void-decl law, NOT here.
    s = tmp_path / "wl0_f5_v.c"
    s.write_text("void v;\nint main(void){return 0;}\n")
    g = gcc(["-c", str(s), "-o", str(tmp_path / "wl0_f5_v.g.o")])
    b = blcc(["-c", str(s), "-o", str(tmp_path / "wl0_f5_v.b.o")])
    assert g.returncode == 1 and b.returncode == 0, \
        "the pre-existing sibling must not drift silently"


# --------------------------------------- F-1..F-4, F-9 inventory pins

def test_wl0_f1_unsigned_imm32_div(tmp_path):
    # F-1 PRE-EXISTING: x86 `i` admits the unsigned imm32 half for 32-bit
    # operands — gcc rc0, blcc LOUD rc2 (the _IMMO signed law, identical
    # at the W-K base). Volume 0. LOUD-DIV pinned, NOT approved.
    s = tmp_path / "wl0_f1.c"
    s.write_text("unsigned long g;\nvoid f(void){ asm volatile(\"movl %1,"
                 "%0\" : \"=m\"(g) : \"i\" (3000000000U)); }\n"
                 "int main(void){return 0;}\n")
    g = gcc(["-c", str(s), "-o", str(tmp_path / "wl0_f1.g.o")])
    b = blcc(["-c", str(s), "-o", str(tmp_path / "wl0_f1.b.o")])
    assert g.returncode == 0 and b.returncode != 0, \
        "F-1 must stay a NAMED LOUD-DIV, not drift silent"


def test_wl0_f2_percent_b_on_imm_div(tmp_path):
    # F-2 PRE-EXISTING: `%b` over a folded immediate — gcc prints the
    # suffix-stripped `$imm` rc0; blcc LOUD. Volume 0.
    s = tmp_path / "wl0_f2.c"
    s.write_text("unsigned long w;\nvoid f(void){ asm volatile(\"btl %b1,%0\""
                 " : \"+m\"(w) : \"i\" (8)); }\nint main(void){return 0;}\n")
    g = gcc(["-c", str(s), "-o", str(tmp_path / "wl0_f2.g.o")])
    assert g.returncode == 0, "F-2 oracle shape must compile:\n" + g.stderr
    b = blcc(["-c", str(s), "-o", str(tmp_path / "wl0_f2.b.o")])
    assert b.returncode != 0, "F-2 must stay LOUD (named), not silent"


def test_wl0_f3_q_pool_value_pair(tmp_path):
    # F-3 PRE-EXISTING inventory: blcc's q-class pool is NARROWER than
    # gcc's (blcc excludes rsi/rdi/rbp/rsp; gcc's q measured to include
    # %dil). VALUE pair-clean — the register CHOICE differs, the result
    # does not. Pin the pair; the choice stays a named shape-div.
    s = tmp_path / "wl0_f3.c"
    s.write_text("long g;\nlong f(long v){ asm volatile(\"movq %1,%0\" :"
                 " \"=m\"(g) : \"iq\" (v)); return g; }\n"
                 "int main(void){ return f(4242) == 4242 ? 7 : 0; }\n")
    gx = tmp_path / "wl0_f3.g"
    g = gcc(["-O0", str(s), "-o", str(gx)])
    assert g.returncode == 0, g.stderr
    bx = tmp_path / "wl0_f3.b"
    b = blcc([str(s), "-o", str(bx)])
    assert b.returncode == 0, b.stderr
    gr = subprocess.run([str(gx)], capture_output=True, timeout=30)
    br = subprocess.run([str(bx)], capture_output=True, timeout=30)
    assert gr.returncode == br.returncode == 7, "F-3 value pair must hold"


def test_wl0_f4_reg_bind_ir_div(tmp_path):
    # F-4 (S17) PRE-EXISTING: a bind-ed register variable + "ir" — gcc
    # rc0, blcc LOUD. Volume 0.
    s = tmp_path / "wl0_f4.c"
    s.write_text("unsigned long g;\nint main(void){ register long x "
                 "asm(\"rax\") = 5; asm volatile(\"movq %1,%0\" :"
                 " \"=m\"(g) : \"ir\" (x)); return 0; }\n")
    g = gcc(["-c", str(s), "-o", str(tmp_path / "wl0_f4.g.o")])
    assert g.returncode == 0, "F-4 oracle shape:\n" + g.stderr
    b = blcc(["-c", str(s), "-o", str(tmp_path / "wl0_f4.b.o")])
    assert b.returncode != 0, "F-4 must stay LOUD (named)"


def test_wl0_f9_letter_set_loud(tmp_path):
    # F-9 inventory: the support set still refuses im/iI/irm/rE/J —
    # IDENTICALLY loud at the W-K base and tip (zero drift either way).
    for letters in ("im", "iI", "irm", "rE", "J"):
        s = tmp_path / ("wl0_f9_" + letters + ".c")
        s.write_text("unsigned long g;\nvoid f(long v){ asm volatile("
                     "\"movq %1,%0\" : \"=m\"(g) : \"" + letters +
                     "\" (v)); }\nint main(void){return 0;}\n")
        b = blcc(["-c", str(s), "-o", str(tmp_path / "wl0_f9.o")])
        assert b.returncode != 0 and "not in the M3 SUPPORT set" in b.stderr,\
            "F-9 letter {} must stay LOUD (inventory, volume 0)".format(letters)
