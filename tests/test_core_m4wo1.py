# LINES reason: one wave of legs (M4 W-O COMMIT-0 — the F-N-1 pointer-
# index address law + the S18/S19/S27 fold-entry silents, card
# 12404.2.87) — every leg is an arm of the SAME fold/address TYPE law;
# splitting would separate a spelling from its type-law neighbour.
r"""M4 W-O COMMIT-0 — F-N-1 + S18/S19/S27: THE FOLD/ADDRESS LAW READS
TYPE PAST THE FIRST ARM (gate MC 12688 F-N-1; card 12404.2.87).

THE LAW (gcc 11.4 -std=gnu89 kernel recipe; probes .tmp/m4-wo/probes/,
ALL at MY hands this card; the gate's rp5f/rp5l/rp5p run-pairs
reproduced at my hands BEFORE building):

  F-N-1 INDEX-THROUGH-POINTER. `p[i]` where p is a POINTER variable has
  NO static address: the object lives where p POINTS, a runtime value.
  The W-N `_asm_elem_ty` legitimation (the dead `.pointee` attribute)
  turned the tip's LOUD ICE into a SILENT MISCOMPILE: `_asm_addr_base`
  folded the pointer's OWN frame/sym slot as the operand address, so
  "m"(p[0]) read the pointer bits, "=m"(p[0]) WROTE THROUGH the frame
  slot, and "p"(p[i]) printed the slot (gate: rp5f 7->207, rp5l 42->7,
  rp5p store landed in the wrong slot — write corruption). THE LAW:
  the Index arm of the static-address walk folds ONLY an ARRAY-typed
  base (esz scales, sym/frame base); a POINTER-typed base answers None
  — the shipped L3 COMPUTED route (address → aslot → base reg, the
  text `(%reg)`) carries the value. Arrays (frame or global) keep
  their static fold VERBATIM (the W-N legs stay green).

  S18 "i"(fn-static const scalar) folds to the VALUE ($7) — gcc-
  measured pair (`movl $7`); the tip printed the SYMBOL ($sc.0), a
  silent wrong value (rp18: gcc exit 42, blcc exit garbage). "&sc"
  keeps the ADDRESS form ($sc.0) — W-N F-3, green both sides. A
  NON-const fn-static bare under "i" now REFUSES (the `gi` law made
  symmetric; gcc folds it only by dataflow propagation, which blcc
  cannot re-derive — named LOUD-DIV, volume 0 in the 706).

  S19 a VOLATILE-qualified const under "i" is gcc LOUD ('impossible
  constraint' — measured for `volatile const` AND bare `volatile`):
  the VALUE fold must read the QUALIFIER, not just `const`. The
  address spelling "&vc" stays a foldable constant ($vc, measured).

  S27 RE-VERIFIED AT MY HANDS — THE GATE'S PREMISE FAILS AT THE KERNEL
  RECIPE. At the REC (-fno-pic in) gcc folds a function symbol under
  "i" DEFINED or declared-only, spellings `f` and `&f` alike (u2/u3/
  s27c rc0, `movq $f`); 'impossible constraint' is the PIE-posture
  answer (default-pie/-fPIE, pinned by a disclosure leg). The gate's
  leg1 harness runs gcc WITHOUT the REC flags (grep-verified), so its
  "gcc LOUD" capture is a posture artifact, not the law. The fold-law
  card leg S27 is PINNED AS MEASURED: fold at REC, LOUD under PIE,
  blcc non-PIE by §6 link law = the fold side — fix-forward with the
  repair named in the verdict (the F-N-1/S18/S19 repairs reproduce;
  this one does not). The run-VALUE of a folded function address is
  NOT link-comparable — the pair is rc + emitted text, named.

MECHANISM: the SAME ONE type check per recursion at the fold entry
(`asmsub._asm_sym` / `_asm_ctype`) plus the ONE static-address entry
(`asmsub._asm_addr_base`): decayed TYPE + qualifier + definedness open
or close each arm. No per-shape patch.
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


REC = ["-Os", "-mno-sse", "-mno-mmx", "-mno-sse2", "-mno-80387",
       "-fno-stack-protector", "-fno-pic"]


def _run_pair(tmp_path, tag, src):
    """(gcc_exit, blcc_exit_or_None, blcc_stderr) — both linked -no-pie
    at the kernel REC; exits are exit bytes (values mod 256)."""
    s = tmp_path / (tag + ".c")
    s.write_text(src)
    g = tmp_path / (tag + ".g")
    r = gcc(REC + [str(s), "-no-pie", "-o", str(g)])
    assert r.returncode == 0, "probe must be valid C: " + r.stderr
    gex = subprocess.run([str(g)], env={"PATH": "/usr/bin:/bin"}).returncode
    o = tmp_path / (tag + ".b.o")
    r = blcc(["-c", str(s), "-o", str(o)])
    if r.returncode:
        return gex, None, r.stderr
    b = tmp_path / (tag + ".b")
    r = gcc(REC + [str(o), "-no-pie", "-o", str(b)])
    assert r.returncode == 0, "link must work: " + r.stderr
    return gex, subprocess.run([str(b)],
                               env={"PATH": "/usr/bin:/bin"}).returncode, ""


def _blcc_asm(tmp_path, tag, src):
    # blcc in-function inline-asm is emitted BARE in the body (the
    # #APP wrap is the FILE-scope form) — text legs search the whole
    # file for the instruction.
    s = tmp_path / (tag + ".c")
    s.write_text(src)
    o = tmp_path / (tag + ".bin")
    r = blcc(["-c", str(s), "--emit-asm", "-o", str(o)])
    assert r.returncode == 0, "blcc must compile:\n" + r.stderr
    return (tmp_path / (str(o) + ".s")).read_text()


def _gcc_app(tmp_path, tag, src):
    s = tmp_path / (tag + ".c")
    s.write_text(src)
    x = tmp_path / (tag + ".s")
    r = gcc(REC + ["-S", str(s), "-o", str(x)])
    if r.returncode:
        return None, r.stderr
    return "\n".join(re.sub(r"^__asm__.*$", "", ln) for ln in
                     "".join(re.findall(r"#APP\n(.*?)#NO_APP\n",
                                        x.read_text(), re.S)).splitlines()), ""


# ------------------------------------------------- F-N-1: rp5f/rp5l/rp5p



# =====================================================================
# THE 12-SHAPE MEASUREMENT SET (.tmp/m4-wo/out/measure-pct-computed.txt,
# all at the kernel REC, own hands):
#   P1 clflush +m(*__p) ....... gcc `clflush (%rdi)`     [WITNESS leg]
#   P2 m(p[0]) ................ gcc `(%rdi)`             pair-VALUE
#   P3 m(arr[i]) global ....... gcc `arr(,%rdi,8)` INDEXED — blcc carries
#       the full address in the base reg: the documented L3 EQUIVALENCE
#       class (blcc computes, gcc folds disp; values pair, text differs)
#   P4 m(a[i]) frame array .... gcc `-64(%rsp,%rdi,8)`  same class
#   P5 "p"(pp) computed ....... gcc rc0 `movq %rdi, %rdx` — the 'p'
#       operand's PLAIN text is the bare reg (it CARRIES the value);
#       %P = plain text, so computed-'p' prints `%reg`, computed-'m'
#       prints `(%reg)` — one law, two texts (measured P5m vs P5c).
#       The tip's guard called every computed operand rc1: measured
#       FALSE (P5/P1 rc0) — rc1 is the FRAME-under-'p' posture (P12)
#   P6 m(&local) .............. gcc `-8(%rsp)` static frame text — shipped
#       W-N arm (fairness pin, green both states)
#   P7 +m(p[1]) ............... gcc `8(%rdi)` (offset folded into disp;
#       blcc: the address, offset included, lives in the base reg)
#   P8 m(p->b) ................ gcc `8(%rdi)`   P9 m(*p) .. gcc `(%rdi)`
#   P10 two computed + clobbers gcc `(%rdi)`/indexed — spill law: no
#       reload needed, both regs live across the asm
#   P11 *(char*)(p+2) ......... gcc `2(%rdi)` char size-form
#   P12 "p"(&local) ........... gcc rc1 'invalid expression as operand' —
#       the W-N frame guard, PAIR-LOUD pin (blcc rc2)
# =====================================================================

def test_p2_m_ptr_elem_run_pair(tmp_path):
    src = ('long g[4] = {11,22,33,44};\n'
           'long f(long *p){ long q = 0; asm volatile("movq %P1, %0"'
           ' : "=a"(q) : "m"(p[0])); return q; }\n'
           'int main(void){ return (int)f(g) % 251; }\n')
    g, b, err = _run_pair(tmp_path, "p2", src)
    assert b is not None, err
    assert (g, b) == (11, 11), (g, b)


def test_p9_m_deref_run_pair(tmp_path):
    src = ('long g[4] = {11,22,33,44};\n'
           'long f(long *p){ long q = 0; asm volatile("movq %P1, %0"'
           ' : "=a"(q) : "m"(*p)); return q; }\n'
           'int main(void){ return (int)f(g + 2) % 251; }\n')
    g, b, err = _run_pair(tmp_path, "p9", src)
    assert b is not None, err
    assert (g, b) == (33, 33), (g, b)


def test_p7_plus_m_rmw_run_pair(tmp_path):
    src = ('long g[4] = {11,22,33,44};\n'
           'long f(long *p){ asm volatile("addq $1, %P0" : "+m"(p[1])'
           ' : : "memory"); return 0; }\n'
           'int main(void){ f(g); return (int)(g[1] - 22) % 251; }\n')
    g, b, err = _run_pair(tmp_path, "p7", src)
    assert b is not None, err
    assert (g, b) == (1, 1), (g, b)


def test_int_forms_run_pair(tmp_path):
    src = ('int g[4] = {7,8,9,10};\n'
           'int f(int *p){ int q = 0; asm volatile("movl %P1, %0"'
           ' : "=a"(q) : "m"(p[2])); asm volatile("addl $5, %P0"'
           ' : "+m"(p[3]) : : "memory"); return q + g[3]; }\n'
           'int main(void){ return (int)f(g) % 251; }\n')
    g, b, err = _run_pair(tmp_path, "pi", src)
    assert b is not None, err
    assert (g, b) == (24, 24), (g, b)


def test_int_rmw_read_write_run_pair(tmp_path):
    src = ('int g[4] = {7,8,9,10};\n'
           'int main(void){ int v = 0; int *p = g;'
           ' asm volatile("movl %P1, %0" : "=a"(v) : "m"(p[1]));'
           ' asm volatile("addl %1, %P0" : "+m"(p[0]) : "a"(v));'
           ' return (int)(g[0] + g[1]) % 251; }\n')
    g, b, err = _run_pair(tmp_path, "pi2", src)
    assert b is not None, err
    # v = g[1] = 8; g[0] += v -> 15; answer g[0] + g[1] = 15 + 8 = 23
    assert (g, b) == (23, 23), (g, b)


def test_char_forms_run_pair(tmp_path):
    src = ('char g[8] = {1,2,3,4,5,6,7,8};\n'
           'int f(char *p){ int q = 0; asm volatile("movzbl %P1, %0"'
           ' : "=a"(q) : "m"(*(volatile char *)(p + 2)));'
           ' return q; }\n'
           'int main(void){ return f(g) % 251; }\n')
    g, b, err = _run_pair(tmp_path, "pc", src)
    assert b is not None, err
    assert (g, b) == (3, 3), (g, b)


def test_char_index_run_pair(tmp_path):
    src = ('char g[8] = {1,2,3,4,5,6,7,8};\n'
           'int main(void){ char *p = g; int q = 0;'
           ' asm volatile("movzbl %P1, %0" : "=a"(q) : "m"(p[5]));'
           ' asm volatile("addb $2, %P0" : "+m"(p[5]) : : "memory");'
           ' return (q + g[5]) % 251; }\n')
    g, b, err = _run_pair(tmp_path, "pc2", src)
    assert b is not None, err
    # q = g[5] = 6; g[5] += 2 -> 8; answer 6 + 8 = 14
    assert (g, b) == (14, 14), (g, b)


def test_p10_two_computed_spill_run_pair(tmp_path):
    src = ('long arr[8] = {1,2,3,4,5,6,7,8};\n'
           'long f(long *p, long i){ long q, r;'
           ' asm volatile("movq %P2, %0 ; movq %P3, %1"'
           ' : "=&a"(q), "=&r"(r) : "m"(p[0]), "m"(arr[i]) : "cc");'
           ' return q + r; }\n'
           'int main(void){ return (int)f(arr, 3) % 251; }\n')
    g, b, err = _run_pair(tmp_path, "p10", src)
    assert b is not None, err
    assert (g, b) == (5, 5), (g, b)


def test_p5_computed_p_compiles(tmp_path):
    # tip guard called EVERY computed operand rc1 — measured FALSE at
    # REC: "p"(pp) prints its BARE base reg (the operand carries the
    # VALUE; %P = the operand's plain text) — `movq %rdi, %rdx` rc0.
    # NOTE the %%-escape law this probe re-measured (W-K lesson
    # re-earned): a hardcoded target register inside a template with
    # operands is `%%rdx`; single-`%rcx` is a substitution reference.
    src = ('long f(long *pp){ asm volatile("movq %P0, %%rdx"'
           ' :: "p"(pp) : "memory"); return 0; }\n'
           'long g[2]; int main(void){ f(g); return 0; }\n')
    gt, gerr = _gcc_app(tmp_path, "p5", src)
    assert gt is not None, gerr
    assert re.search(r"movq %rdi, %rdx", gt), gt
    bt = _blcc_asm(tmp_path, "p5", src)
    assert re.search(r"movq %r[a-z0-9]+, %rdx", bt), bt


def test_p_plain_prints_bare_value_reg_pair(tmp_path):
    # The `%N` plain print of the SAME computed-'p' operand: the operand
    # CARRIES the pointer VALUE — printing `(%reg)` would load through
    # it (measured gcc exit 1 vs blcc exit 0 on this pair before the
    # one-arm fix: the value law `%P` already follows, extended to the
    # plain path — zero-volume silent edge, fixed in-wave by the same
    # doctrine as F-N-1, MC 12690).
    src = ('long g[4] = {5,6,7,8};\n'
           'int main(void){ long r = -1; long *pp = g + 2;'
           ' asm volatile("movq %1, %0" : "=a"(r) : "p"(pp));'
           ' return (r == (long)(g + 2)) % 251; }\n')
    g, b, err = _run_pair(tmp_path, "pp1", src)
    assert b is not None, err
    assert (g, b) == (1, 1), (g, b)
    bt = _blcc_asm(tmp_path, "pp1", src)
    assert re.search(r"movq %r[a-z0-9]+, %rax", bt), bt


def test_p2_prints_parenthesized_base_reg(tmp_path):
    src = ('long f(long *p){ long q; asm volatile("movq %P1, %0"'
           ' : "=a"(q) : "m"(p[0])); return q; }\n'
           'int main(void){ return 0; }\n')
    bt = _blcc_asm(tmp_path, "p2t", src)
    assert re.search(r"movq \(%r[a-z0-9]+\), %rax", bt), bt


def test_p7_offset_lives_in_the_address_reg(tmp_path):
    # gcc `8(%rdi)` (disp-fold) vs blcc `(%reg)` (the full address is
    # computed into the base reg) — the documented L3 equivalence law,
    # value-paired by test_p7_plus_m_rmw_run_pair.
    src = ('long f(long *p){ asm volatile("addq $1, %P0"'
           ' : "+m"(p[1]) : : "memory"); return 0; }\n'
           'int main(void){ return 0; }\n')
    bt = _blcc_asm(tmp_path, "p7t", src)
    assert re.search(r"addq \$1, \(%r[a-z0-9]+\)", bt), bt


def test_p3_global_index_equivalence_pair(tmp_path):
    # P3/P4 class: gcc folds arr(,%rdi,8) INTO the text; blcc's computed
    # route carries the full address in the base reg. Value pairs (run
    # leg); text differs BY THE PINNED L3 LAW — pinning both texts so
    # the class is visible, never silent.
    src = ('long arr[8]; long f(long i){ long q; asm volatile("movq %P1, %0"'
           ' : "=a"(q) : "m"(arr[i])); return q; }\n'
           'long g[8]; int main(void){ return (int)f(2); }\n')
    gt, gerr = _gcc_app(tmp_path, "p3", src)
    assert gt is not None, gerr
    assert "arr(,%rdi,8)" in gt, gt
    bt = _blcc_asm(tmp_path, "p3", src)
    assert re.search(r"movq \(%r[a-z0-9]+\), %rax", bt), bt
    g, b, err = _run_pair(tmp_path, "p3r", src.replace("long arr[8];", "long arr[8] = {0,1,2,7};"))
    assert b is not None, err
    assert (g, b) == (2, 2), (g, b)   # f(2) reads arr[2] == 2 — the pair



def test_p6_frame_static_pair_green(tmp_path):
    # fairness: the STATIC frame text arm (W-N) is UNTOUCHED by the
    # materialization — green both states.
    src = ('long f(void){ long v = 3; long q;'
           ' asm volatile("movq %P1, %0" : "=a"(q) : "m"(v)); return q; }\n'
           'int main(void){ return f() % 251; }\n')
    g, b, err = _run_pair(tmp_path, "p6", src)
    assert b is not None, err
    assert (g, b) == (3, 3), (g, b)


def test_p12_p_frame_pair_loud(tmp_path):
    # the W-N guard STAYS: gcc rc1 'invalid expression as operand' under
    # REC (probe P12); blcc rc2 at the frame wall — PAIR-LOUD pin.
    src = ('long f(void){ long v; asm volatile("movq %P0, %%rdx"'
           ' :: "p"(&v) : "memory"); return 0; }\n')
    s = tmp_path / "p12.c"
    s.write_text(src)
    g = gcc(REC + ["-c", str(s), "-o", str(tmp_path / "p12.g.o")])
    b = blcc(["-c", str(s), "-o", str(tmp_path / "p12.b.o")])
    assert g.returncode == 1 and "invalid expression" in g.stderr, g.stderr
    assert b.returncode != 0, b.stdout


# ---- THE TWO VERBATIM WALK WITNESSES (post-pp .i text from
# .tmp/m4-plan/streams/arch_x86_boot_compressed_cmdline.c.i — the same
# stream family the W-N walk carried; embedded verbatim, W-N CUR-style
# idiom). --------------------------------------------------------------

WA = r"""void clflushopt(volatile void *__p)
{
 asm __inline volatile ("# ALT: oldnstr\n" "661:\n\t" ".byte " "0x3e" "; clflush %P0" "\n662:\n" "# ALT: padding\n" ".skip -(((" "665""1""f-""664""1""f" ")-(" "662b-661b" ")) > 0) * " "((" "665""1""f-""664""1""f" ")-(" "662b-661b" ")),0x90\n" "663" ":\n" ".pushsection .altinstructions,\"a\"\n" " .long 661b - .\n" " .long " "664""1""f - .\n" " .word " "( 9*32+23)" "\n" " .byte " "663""b-661b" "\n" " .byte " "665""1""f-""664""1""f" "\n" ".popsection\n" ".pushsection .altinstr_replacement, \"ax\"\n" "# ALT: replacement " "1" "\n" "664""1"":\n\t" ".byte 0x66; clflush %P0" "\n" "665""1" ":\n" ".popsection\n" : "+m" (*(volatile char *)__p) : "i" (0))


                                              ;
}
"""

WB = r"""void alternative_msr_write(unsigned int msr, u64 val, unsigned int feature)
{
 asm volatile("# ALT: oldnstr\n" "661:\n\t" "" "\n662:\n" "# ALT: padding\n" ".skip -(((" "665""1""f-""664""1""f" ")-(" "662b-661b" ")) > 0) * " "((" "665""1""f-""664""1""f" ")-(" "662b-661b" ")),0x90\n" "663" ":\n" ".pushsection .altinstructions,\"a\"\n" " .long 661b - .\n" " .long " "664""1""f - .\n" " .word " "%c[feature]" "\n" " .byte " "663""b-661b" "\n" " .byte " "665""1""f-""664""1""f" "\n" ".popsection\n" ".pushsection .altinstr_replacement, \"ax\"\n" "# ALT: replacement " "1" "\n" "664""1"":\n\t" "wrmsr" "\n" "665""1" ":\n" ".popsection\n"
  : : "c" (msr),
      "a" ((u32)val),
      "d" ((u32)(val >> 32)),
      [feature] "i" (feature)
  : "memory");
}
"""

_PRE = ("typedef unsigned char u8; typedef unsigned int u32;"
        " typedef unsigned long u64;\n")


def test_witness_clflushopt_special_insns_217(tmp_path):
    # special_insns.h:217 clflushopt — the walk's %P wall, VERBATIM.
    # gcc -Os REC: `clflush (%rdi)` twice (old + replacement arms).
    # COMMIT-1 law: blcc rc0, the substituted text byte-forms
    # `clflush (%reg)` (register identity is blcc's own pool law — the
    # form is the pair; value is a cache op, not observable, named).
    s = tmp_path / "wa.c"
    s.write_text(_PRE + WA)
    gt, gerr = _gcc_app(tmp_path, "wa", _PRE + WA)
    assert gt is not None, gerr
    assert len(re.findall(r"clflush \(%rdi\)", gt)) == 2, gt
    bt = _blcc_asm(tmp_path, "wa", _PRE + WA)
    assert len(re.findall(r"clflush \(%r[a-z0-9]+\)", bt)) == 2, bt


def test_witness_alt_msr_write_375_pair_loud(tmp_path):
    # nospec-branch.h:375 alternative_msr_write — the walk's NEXT wall
    # (inline-PARAM under "i", the 485-crowd class): pair-LOUD (gcc rc1
    # 'impossible constraint' standalone; blcc rc2 the named 'i' wall).
    # The named WALK-STILL-BLOCKED witness: real streams reach it only
    # through gcc's inliner; blcc has none — the next wave's lever.
    s = tmp_path / "wb.c"
    s.write_text(_PRE + WB)
    g = gcc(REC + ["-c", str(s), "-o", str(tmp_path / "wb.g.o")])
    b = blcc(["-c", str(s), "-o", str(tmp_path / "wb.b.o")])
    assert g.returncode == 1 and "impossible constraint" in g.stderr, g.stderr
    assert b.returncode != 0 and "not a compile-time constant" in b.stderr, b.stderr


def test_witness_alt_msr_write_constant_variant_pair(tmp_path):
    # the same witness with the PARAM replaced by the constant real
    # callers pass (X86_FEATURE class): both compilers rc0 and BOTH
    # print ` .word 311` — byte-parity (measured; the earlier L3
    # guess `( 9*32+23)`/`$311` was measured FALSE at this call site:
    # gcc folds the %c constant too).
    src = _PRE + WB.replace('[feature] "i" (feature)',
                           '[feature] "i" (9*32+23)')
    gt, gerr = _gcc_app(tmp_path, "wc", src)
    assert gt is not None, gerr
    assert re.search(r"\.word 311", gt), gt
    bt = _blcc_asm(tmp_path, "wc", src)
    assert re.search(r"\.word 311", bt), bt


def test_pct_computed_guard_still_loud_for_cc(tmp_path):
    # the materialization is ONLY %P: the size modifier on a computed
    # memory operand stays the §3 L3 silent-size LOUD guard (no new
    # printing law beside the one).
    src = ('long f(long *p){ long q; asm volatile("movq %b1, %0"'
           ' : "=a"(q) : "m"(p[0])); return q; }\n'
           'int main(void){ return 0; }\n')
    s = tmp_path / "cc1.c"
    s.write_text(src)
    b = blcc(["-c", str(s), "-o", str(tmp_path / "cc1.o")])
    assert b.returncode != 0 and "silent-size" in b.stderr, b.stderr
