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
# THE MEASURED LAW (own hands, kernel REC, probes r4a/r4b + the 18-stream
# census .tmp/m4-wo/out/rc3-census.json): the corpus dies inside the
# STANDALONE body of `static __always_inline` helpers whose switch
# control is `sizeof(...)` — a compile-time CONSTANT (gcc folds the
# switch and emits the matching arm ONLY (even at -O0, probe sw1), so
# the 1/2/4-byte `cmpxchgb %edx` texts never exist in gcc's .s; blcc
# emitted the compare chain AND every arm body — as rejects the dead
# arms' texts: `%edx' not allowed with cmpxchgb' (the 16-stream class)
# and `%cl' not allowed with cmpxchgl' (the %k family, below). LAW: at
# the ONE switch emission, when the control folds at the fold-entry law
# and the arms are plain (no markers nested under if/loop — conservative
# fallback, no bare decl in a SKIPPED arm — the name would stay in scope
# for the live region), SKIP evaluation of the (pure, foldable) control
# and every arm BEFORE the match, emit the match on forward. C
# fall-through from the matched arm keeps every LATER arm (cascade).
# =====================================================================

ATOM = """\
typedef unsigned char u8; typedef unsigned short u16;
typedef unsigned int u32; typedef unsigned long u64;
struct A { int counter; };
static inline __attribute__((__always_inline__)) int arch_atomic_cmpxchg(struct A *v, int old, int new)
{
  int ret;
  switch ((sizeof(v->counter))) {
    case 1: { volatile u8 *p = (volatile u8 *)&v->counter; asm volatile("cmpxchgb %2,%1" : "=a"(ret), "+m"(*p) : "q"(new), "0"(old) : "memory"); break; }
    case 2: { volatile u16 *p = (volatile u16 *)&v->counter; asm volatile("cmpxchgw %2,%1" : "=a"(ret), "+m"(*p) : "r"(new), "0"(old) : "memory"); break; }
    case 4: { volatile u32 *p = (volatile u32 *)&v->counter; asm volatile("cmpxchgl %2,%1" : "=a"(ret), "+m"(*p) : "r"(new), "0"(old) : "memory"); break; }
    case 8: { volatile u64 *p = (volatile u64 *)&v->counter; asm volatile("cmpxchgq %2,%1" : "=a"(ret), "+m"(*p) : "r"(new), "0"(old) : "memory"); break; }
    default: break;
  }
  return ret;
}
struct A target;
int main(void){ target.counter = 5; return arch_atomic_cmpxchg(&target, 5, 9) % 251; }
"""


def test_r4_verbatim_atomic_cmpxchg_pair(tmp_path):
    # the 16-stream class VERBATIM-shaped (arch_atomic_cmpxchg post-pp):
    # tip = the exact corpus as-death `%edx' not allowed with cmpxchgb`;
    # law = only the case-4 arm survives: text has cmpxchgl, never
    # cmpxchgb/w/q; value pairs (returns the old value 5).
    g, b, err = _run_pair(tmp_path, "r4a", ATOM)
    assert b is not None, err
    assert (g, b) == (5, 5), (g, b)
    bt = _blcc_asm(tmp_path, "r4t", ATOM)
    assert "cmpxchgl" in bt, bt
    for dead in ("cmpxchgb", "cmpxchgw", "cmpxchgq"):
        assert dead not in bt, (dead, bt)


def test_r4_runtime_control_keeps_every_arm(tmp_path):
    # the OTHER direction: a RUNTIME control keeps the compare chain and
    # EVERY arm (gcc law, sw2 probe; blcc byte-identical to the tip) —
    # the dispatch must not fire. Templates use the width modifiers so
    # all arms are as-legal: values pair, all arms print.
    src = ('long g(long i){ long r = 0; switch (i) {'
           ' case 1: asm volatile("movb $1, %0" : "=m"(r)); break;'
           ' case 2: asm volatile("movw $2, %0" : "=m"(r)); break;'
           ' case 8: asm volatile("movq $8, %0" : "=m"(r)); break;'
           ' default: r = -1; } return r; }\n'
           'int main(void){ long a = g(1), b = g(2), c = g(8), d = g(3);'
           ' return (int)((a + 2*b + 4*c + 8*(d == -1)) % 251); }\n')
    g, b, err = _run_pair(tmp_path, "r4b", src)
    assert b is not None, err
    assert (g, b) == (45, 45), (g, b)  # 1 + 2*2 + 4*8 + 8*(1) = 45
    bt = _blcc_asm(tmp_path, "r4b", src)
    for keep in ("movb", "movw", "movq $8"):
        assert keep in bt, (keep, bt)


def test_r4_default_selection_pair(tmp_path):
    # constant control matches NO label -> the default arm is the live
    # one; earlier arms skipped (their asm texts must NOT print).
    src = ('int main(void){ long r = 0; switch (sizeof(long)) {'
           ' case 1: asm volatile("movb $7, %0" : "=m"(r)); break;'
           ' default: r = 3; } return (int)r % 251; }\n')
    g, b, err = _run_pair(tmp_path, "r4d", src)
    assert b is not None, err
    assert (g, b) == (3, 3), (g, b)
    bt = _blcc_asm(tmp_path, "r4d", src)
    assert "movb" not in bt, bt


def test_r4_caserange_selection_pair(tmp_path):
    # gnu `case lo ... hi:` — the match is lo<=K<=hi (CaseRange arm).
    src = ('int main(void){ long r = 0; switch (sizeof(int)) {'
           ' case 8 ... 9: asm volatile("movq $11, %0" : "=m"(r)); break;'
           ' case 2 ... 4: r = 42; break;'
           ' default: r = 7; } return (int)r % 251; }\n')
    g, b, err = _run_pair(tmp_path, "r4g", src)
    assert b is not None, err
    assert (g, b) == (42, 42), (g, b)


def test_r4_fallthrough_cascade_pair(tmp_path):
    # C fall-through from the MATCHED arm cascades into the LATER arms —
    # the dispatch skips only EARLIER arms.
    src = ('int main(void){ long r = 0; switch (sizeof(long)) {'
           ' case 1: r = 100; break;'
           ' case 8: r += 3;      /* matched, no break */'
           ' case 16: r += 40; break;'
           ' default: r += 1000; } return (int)r % 251; }\n')
    g, b, err = _run_pair(tmp_path, "r4f", src)
    assert b is not None, err
    assert (g, b) == (43, 43), (g, b)


def test_r4_pct_materialized_live_arm_pair(tmp_path):
    # THE INTERACTION LAW (COMMIT-1 x COMMIT-2): the matched arm carries
    # `%P` on a COMPUTED address — the dead 1/2/4-byte arms would print
    # invalid texts AND the live arm needs the materialization. Both
    # laws compose at the walk shapes (special_insns + switch).
    src = ('long arr[4] = {1,2,3,4};\n'
           'long f(long *pp, long i){ long r = 0;'
           ' switch (sizeof(long)) {'
           ' case 1: asm volatile("movb $9, %P0" : "+m"(pp[i])); break;'
           ' case 8: asm volatile("movq $77, %P0" : "+m"(pp[i])); break;'
           ' default: break; } return pp[i]; }\n'
           'int main(void){ return (int)f(arr, 2) % 251; }\n')
    g, b, err = _run_pair(tmp_path, "r4x", src)
    assert b is not None, err
    assert (g, b) == (77, 77), (g, b)
    bt = _blcc_asm(tmp_path, "r4x", src)
    assert re.search(r"movq \$77, \(%r[a-z0-9]+\)", bt), bt
    assert "movb" not in bt, bt


def test_k32_modifier_is_32_bit_pair(tmp_path):
    # `%k` LAW MEASURED AT REC (probe kmod): gcc prints the 32-BIT name
    # of the assigned register (`movl %edi`); the tip's reg_name mapped
    # 'k' to the BYTE width (printed `%cl` — a WRONG VALUE, silent
    # wherever an as-valid template hid it, `%cl not allowed with
    # cmpxchgl` in the dead-arm family). Value-leg + negative text pin;
    # the loose W-M pin (test_asm_m1) still matches `%edi`.
    # the template's OUTPUT must be 32-bit too (`movl %edi, %rax` is
    # gas-invalid — a probe-shape lesson re-earned: -S hides as, the
    # pair runs it):
    src = ('long g = 0xAABBCCDD;\n'
           'int f(long x){ int r = 0;'
           ' asm volatile("movl %k1, %0" : "=a"(r) : "r"(x) : "cc");'
           ' return r; }\n'
           'int main(void){ return (f(g) & 0xff) % 251; }\n')
    g, b, err = _run_pair(tmp_path, "k32", src)
    assert b is not None, err
    assert (g, b) == (0xDD, 0xDD), (g, b)
    bt = _blcc_asm(tmp_path, "k32", src)
    assert not re.search(r"movl %[a-z]{1,2}l?, %eax", bt) or \
        re.search(r"movl %e[a-z]{2}, %eax", bt), bt


def test_r4_no_match_no_default_pair(tmp_path):
    src = ('int main(void){ long r = 9; switch (sizeof(long)) {'
           ' case 1: asm volatile("movb $5, %0" : "=m"(r)); break;'
           ' case 2: r = 4; } return (int)r % 251; }\n')
    g, b, err = _run_pair(tmp_path, "r4n", src)
    assert b is not None, err
    assert (g, b) == (9, 9), (g, b)
    bt = _blcc_asm(tmp_path, "r4n", src)
    assert "movb" not in bt, bt


def test_r4_bare_decl_arm_parse_wall(tmp_path):
    # The bare-decl fallback below the dispatch is belt-and-braces: the
    # PARSE law already LOUDs 'declaration in an unbraced statement'
    # (pre-existing W-wave wall) — pinned so the fallback is never
    # silently reachable by new syntax, and the dispatch law's scope is
    # exact (unbraced arms never compile here; the fallback keeps them
    # chain-emitted should that wall ever move).
    src = ('int main(void){ long r = 0; switch (sizeof(long)) {'
           ' case 1: long z = 5; r = z + 1;'
           ' case 8: r += 2; break;'
           ' default: r = -1; } return (int)r % 251; }\n')
    s = tmp_path / "r4v2.c"
    s.write_text(src)
    b = blcc(["-c", str(s), "-o", str(tmp_path / "r4v2.o")])
    assert b.returncode != 0 and "unbraced" in b.stderr, b.stderr
