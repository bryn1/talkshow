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

def test_fn1_verbatim_rp5f_run_pair(tmp_path):
    # gate rp5f verbatim: "m"(p[0]) reads WHERE p POINTS (7), not the
    # pointer's own bits (tip: 207-class garbage).
    src = ('int main(void){ long g2[4] = {100,7,0,0}; long *p = &g2[1];'
           ' long q = -1;\n  asm volatile("movq %1, %0" : "=a"(q) :'
           ' "m"(p[0])); return (int)(q % 251); }\n')
    g, b, err = _run_pair(tmp_path, "rp5f", src)
    assert b is not None, err
    assert (g, b) == (7, 7)


def test_fn1_verbatim_rp5l_run_pair(tmp_path):
    # gate rp5l verbatim: "m"(p[2]) at a nonzero const index (42).
    src = ('long f(void){ long g2[4] = {100,7,42,0}; long *p = &g2[0];'
           ' long q;\n  asm volatile("movq %1, %0" : "=a"(q) :'
           ' "m"(p[2])); return (int)(q % 251); }\n'
           'int main(void){ return (int)f(); }\n')
    g, b, err = _run_pair(tmp_path, "rp5l", src)
    assert b is not None, err
    assert (g, b) == (42, 42)


def test_fn1_verbatim_rp5p_write_pair(tmp_path):
    # gate rp5p verbatim: "=m"(p[0]) WRITES the pointed-to object
    # (write-corruption class: tip stored through the pointer slot).
    src = ('int main(void){ long g2[4] = {1,2,3,4}; long *p = &g2[1];\n'
           '  asm volatile("movq $77, %0" : "=m"(p[0]) : : "memory");\n'
           '  return (int)(g2[1] % 251); }\n')
    g, b, err = _run_pair(tmp_path, "rp5p", src)
    assert b is not None, err
    assert (g, b) == (77, 77)


def test_fn1_own_global_pointer_m_run_pair(tmp_path):
    # own shape 1: a GLOBAL pointer variable, "m" at index 1 — the sym
    # base of a pointer is NEVER the object base.
    src = ('long gs[4] = {5,9,13,17};\nlong *gp = gs;\n'
           'int main(void){ long q = -1;\n'
           '  asm volatile("movq %1, %0" : "=a"(q) : "m"(gp[1]));'
           ' return (int)(q % 251); }\n')
    g, b, err = _run_pair(tmp_path, "fno1", src)
    assert b is not None, err
    assert (g, b) == (9, 9)


def test_fn1_own_runtime_index_m_run_pair(tmp_path):
    # own shape 2: runtime index through a pointer — computed twice
    # over (the index AND the base are values).
    src = ('int main(void){ long g2[4] = {1,2,251 - 207,4};'
           ' long *p = &g2[0]; long i = 2; long q = -1;\n'
           '  asm volatile("movq %1, %0" : "=a"(q) : "m"(p[i]));'
           ' return (int)(q % 251); }\n')
    g, b, err = _run_pair(tmp_path, "fno2", src)
    assert b is not None, err
    assert g == b


def test_fn1_own_plus_m_rmw_run_pair(tmp_path):
    # own shape 3: "+m"(p[1]) — read the object, write it back through
    # the SAME computed base (input value + output store, one reg).
    src = ('int main(void){ long g2[2] = {3, 11}; long *p = g2;\n'
           '  asm volatile("addq %%rax, %0" : "+m"(p[1]) : "a"(31)'
           ' : "memory");\n  return (int)(g2[1] % 251); }\n')
    g, b, err = _run_pair(tmp_path, "fno3", src)
    assert b is not None, err
    assert (g, b) == (42, 42)


def test_fn1_own_char_size_form_run_pair(tmp_path):
    # own shape 4 (size form): a char pointer — esz 1 scaling rides the
    # computed address; byte load keeps the value.
    src = ('int main(void){ char c[4] = {1,2,3,4}; char *p = c;'
           ' int q = -1;\n'
           '  asm volatile("movzbl %1, %0" : "=a"(q) : "m"(p[2]));'
           ' return q % 251; }\n')
    g, b, err = _run_pair(tmp_path, "fno4", src)
    assert b is not None, err
    assert (g, b) == (3, 3)


def test_fn1_m_ptr_prints_base_reg(tmp_path):
    # the computed route PRINTS `(%reg)` — the operand text is the base
    # register, never a `$`-text and never the pointer's own slot.
    a = _blcc_asm(tmp_path, "fnotx",
                  'int main(void){ long g2[4] = {1,2,3,4}; long *p = g2;'
                  ' long q;\n'
                  '  asm volatile("movq %1, %0" : "=a"(q) : "m"(p[0]));'
                  ' return (int)q; }\n')
    assert re.search(r"movq \(%r[a-z0-9]+\), %rax", a), a


def test_fn1_frame_array_static_fold_still_green(tmp_path):
    # fairness (green BOTH states): an ARRAY-typed frame base keeps the
    # W-N static fold — the type law must not push arrays computed.
    a = _blcc_asm(tmp_path, "fnoarr",
                  'int main(void){ long a2[4] = {1,2,3,4}; long q;\n'
                  '  asm volatile("movq %1, %0" : "=a"(q) : "m"(a2[1]));'
                  ' return (int)q; }\n')
    assert re.search(r"movq -?\d+\(%rbp\), %rax", a), a


# ------------------------------------------------------- S18 (rp18) --

def test_s18_static_const_value_run_pair(tmp_path):
    # gate rp18 verbatim: "i"(fn-static const 42) folds the VALUE.
    src = ('long f(void) { static const int sc = 42; long r;\n'
           '  __asm__ volatile("movl %1, %%eax" : "=a"(r) : "i"(sc));'
           ' return r; }\n'
           'int main(void) { return (int)f(); }\n')
    g, b, err = _run_pair(tmp_path, "rp18", src)
    assert b is not None, err
    assert (g, b) == (42, 42)


def test_s18_static_const_value_text_pair(tmp_path):
    # byte-parity arm: both compilers print the folded constant `$7`.
    src = ('int main(void) { static const int sc = 7;\n'
           '  __asm__ volatile("movl %0, %%eax" : : "i"(sc) : "memory");'
           ' return 0; }\n')
    gt, gerr = _gcc_app(tmp_path, "s18t", src)
    assert gt is not None, gerr
    bt = _blcc_asm(tmp_path, "s18t", src)
    assert "$7" in gt, gt
    assert re.search(r"movl +\$7, *%eax", bt), bt
    assert not re.search(r"movl +\$sc", bt), bt


def test_s18_static_addr_form_still_green(tmp_path):
    # fairness (green BOTH states): "&sc" stays the SYMBOL address form.
    src = ('int main(void) { static const int sc = 7; long r;\n'
           '  __asm__ volatile("movq %1, %0" : "=a"(r) : "i"(&sc));'
           ' return (int)r & 3; }\n')
    gt, gerr = _gcc_app(tmp_path, "s18a", src)
    assert gt is not None, gerr
    bt = _blcc_asm(tmp_path, "s18a", src)
    assert "$sc" in gt, gt
    assert re.search(r"movq +\$sc(\.\d+)?, *%rax", bt), bt


def test_sym_nonconst_static_loud_twin(tmp_path):
    # LOUD-DIV twin (named, volume 0): a BARE non-const fn-static under
    # "i" — gcc folds it ONLY by dataflow propagation (rc0 $5), which
    # blcc cannot re-derive; the tip answered the symbol `$fs.0`
    # SILENTLY. blcc now refuses LOUD (the `gi` law made symmetric).
    s = tmp_path / "snc.c"
    s.write_text('int main(void) { static int fs = 5; long r;\n'
                 '  __asm__ volatile("movl %1, %%eax; movl %%eax, %0"'
                 ' : "=a"(r) : "i"(fs)); return (int)r; }\n')
    r = blcc(["-c", str(s), "-o", str(tmp_path / "snc.o")])
    assert r.returncode == 2, "blcc must refuse LOUD, got rc0:\n" + r.stderr
    assert "not a compile-time constant" in r.stderr, r.stderr


# ------------------------------------------------------- S19 (rp19) --

def test_s19_volatile_const_loud_pair(tmp_path):
    # gate rp19 verbatim: gcc rc1 'impossible constraint'; blcc must
    # answer LOUD (the tip folded $42 silently).
    src = ('volatile const int vc = 42;\n'
           'long f(void) { long r;\n'
           '  __asm__ volatile("movl %1, %%eax" : "=a"(r) : "i"(vc));'
           ' return r; }\n'
           'int main(void) { return (int)f(); }\n')
    s = tmp_path / "rp19.c"
    s.write_text(src)
    g = gcc(REC + ["-c", str(s), "-o", str(tmp_path / "rp19.g.o")])
    assert g.returncode == 1 and "impossible constraint" in g.stderr, g.stderr
    b = blcc(["-c", str(s), "-o", str(tmp_path / "rp19.b.o")])
    assert b.returncode == 2, "blcc must refuse LOUD:\n" + b.stderr
    assert "not a compile-time constant" in b.stderr, b.stderr


def test_s19_volatile_global_loud_pair(tmp_path):
    # bare volatile (no const) under "i": gcc LOUD too (measured).
    s = tmp_path / "s19v.c"
    s.write_text('volatile int vv = 6;\nint main(void){ long r;\n'
                 '  asm volatile("movl %1, %0" : "=a"(r) : "i"(vv));'
                 ' return (int)r; }\n')
    g = gcc(REC + ["-c", str(s), "-o", str(tmp_path / "s19v.g.o")])
    assert g.returncode == 1 and "impossible constraint" in g.stderr
    b = blcc(["-c", str(s), "-o", str(tmp_path / "s19v.b.o")])
    assert b.returncode == 2, "blcc must refuse LOUD:\n" + b.stderr


def test_s19_volatile_addr_form_still_green(tmp_path):
    # fairness (green BOTH states): the ADDRESS fold is qualifier-blind
    # — "&vc"/"&vv" print $sym on both sides (measured rc0/rc0).
    for tag, decl, name in (("s19d", "volatile const int vc = 5;", "vc"),
                            ("s19e", "volatile int vv = 6;", "vv")):
        src = (decl + '\nint main(void){ long r; asm volatile("movq %1, %0"'
               ' : "=a"(r) : "i"(&' + name + ')); return (int)r & 1; }\n')
        gt, gerr = _gcc_app(tmp_path, tag, src)
        assert gt is not None, gerr
        bt = _blcc_asm(tmp_path, tag, src)
        assert "$" + name in gt, (tag, gt)
        assert re.search(r"movq +\$" + name + r", *%rax", bt), (tag, bt)


# ------------------------------------------------------- S27 (rp27) --

def test_s27_defined_fn_text_pair(tmp_path):
    # a DEFINED function folds its address on BOTH sides (rc0, `$g`).
    # The run VALUE is not link-comparable (load addresses differ) —
    # the pair is rc + text, named.
    src = ('long g(void){ return 5; }\n'
           'long f(void){ long r; asm volatile("movq %1, %0"'
           ' : "=a"(r) : "i"(g)); return r & 7; }\n'
           'int main(void){ return (int)f(); }\n')
    gt, gerr = _gcc_app(tmp_path, "s27d", src)
    assert gt is not None, gerr
    bt = _blcc_asm(tmp_path, "s27d", src)
    assert "$g" in gt, gt
    assert re.search(r"movq +\$g, *%rax", bt), bt


def test_s27_defined_fn_addr_text_pair(tmp_path):
    # the `&g` spelling of a DEFINED function: same answer both sides.
    src = ('long g(void){ return 5; }\n'
           'int main(void){ long r; asm volatile("movq %1, %0"'
           ' : "=a"(r) : "i"(&g)); return (int)r & 3; }\n')
    gt, gerr = _gcc_app(tmp_path, "s27a", src)
    assert gt is not None, gerr
    bt = _blcc_asm(tmp_path, "s27a", src)
    assert "$g" in gt, gt
    assert re.search(r"movq +\$g, *%rax", bt), bt


def test_s27_undefined_fn_fold_text_pair(tmp_path):
    # S27 RE-MEASURED AT MY HANDS, kernel REC (-fno-pic in): gcc FOLDS
    # a declared-only function under "i" — `$f` rc0 (probes u2/u3/s27b,
    # .tmp/m4-wo/probes/) — both spellings. The gate's 'impossible
    # constraint' capture is the PIE-posture answer (its leg1 harness
    # carries no REC flags — grep-verified there); blcc is static
    # non-PIE by the §6 link law, so the W-N fold is the REC-pair
    # answer. Pair: both compilers print `$f`.
    src = ('int f(void);\nlong q;\n'
           'int main(void){ asm volatile("movq %1, %0" : "=a"(q)'
           ' : "i"(f)); return 0; }\n')
    gt, gerr = _gcc_app(tmp_path, "s27u", src)
    assert gt is not None, gerr
    bt = _blcc_asm(tmp_path, "s27u", src)
    assert "$f" in gt, gt
    assert re.search(r"movq +\$f, *%rax", bt), bt


def test_s27_undefined_fn_addr_fold_text_pair(tmp_path):
    # the `&f` spelling at REC: same fold, same pair (s27c rc0).
    src = ('int f(void);\nint main(void){ long r; asm volatile("movq %1, %0"'
           ' : "=a"(r) : "i"(&f)); return (int)r & 3; }\n')
    gt, gerr = _gcc_app(tmp_path, "s27c", src)
    assert gt is not None, gerr
    bt = _blcc_asm(tmp_path, "s27c", src)
    assert "$f" in gt, gt
    assert re.search(r"movq +\$f, *%rax", bt), bt


def test_s27_pie_posture_disclosure_pin(tmp_path):
    # The posture that produced the gate's LOUD capture, pinned so the
    # class cannot be re-filed blind: with Ubuntu's DEFAULT PIE posture
    # (no REC) gcc answers 'impossible constraint' for the SAME probe;
    # at the kernel REC it folds (leg above). blcc has no PIE mode —
    # the §6 non-PIE law makes the REC the only pair universe here.
    src = ('int f(void);\nlong q;\n'
           'int main(void){ asm volatile("movq %1, %0" : "=a"(q)'
           ' : "i"(f)); return 0; }\n')
    s = tmp_path / "s27p.c"
    s.write_text(src)
    r = gcc(["-O0", "-c", str(s), "-o", str(tmp_path / "s27p.o")])
    assert r.returncode == 1 and "impossible constraint" in r.stderr, r.stderr


def test_s27_static_char_array_decay_pair(tmp_path):
    # fairness (green BOTH states): a fn-static char ARRAY under "i"
    # decays to the symbol address on BOTH sides ($nm.0 — the W-N
    # statics arm stays; the VALUE law only touches scalar spines).
    src = ('int main(void){ static const char nm[] = "ab"; long r;\n'
           '  asm volatile("movq %1, %0" : "=a"(r) : "i"(nm));'
           ' return (int)r & 1; }\n')
    gt, gerr = _gcc_app(tmp_path, "s18e", src)
    assert gt is not None, gerr
    bt = _blcc_asm(tmp_path, "s18e", src)
    assert "$nm" in gt, gt
    assert re.search(r"movq +\$nm(\.\d+)?, *%rax", bt), bt
