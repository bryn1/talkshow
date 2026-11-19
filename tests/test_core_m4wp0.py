# LINES reason: one wave of legs (M4 W-P COMMIT-0 — the F-1 2-D row-fold
# law + the F-5 unbraced-break tail-walk, card 12404.2.89) — every leg is
# an arm of ONE dispatch/fold law; splitting would separate a spelling
# from its type-law neighbour.
r"""M4 W-P COMMIT-0 — F-1 + F-5: THE FOLD READS THE ROW OBJECT; THE
SWITCH DISPATCH WALKS THE ARM TAIL (gate MC 12704 F-1/F-5; card
12404.2.89).

F-1  2-D ARRAY FOLD IN "m" ADDRESSING (P2, PRE-EXISTING — measured
IDENTICAL at faed042 and 2bc5857 by the gate; constraint-window corpus
volume 0). `int mm[2][3]; "m"(mm[1][2])`: gcc `mm+20(%rip)`, the tip
`mm+16(%rip)` — the row step was taken from the DECAYED row POINTER
(esz 8), not the row OBJECT (sizeof int[3] = 12). THE LAW at the ONE
static-address fold entry (`asmsub._asm_elem_ty`): an element is the
UNDECAYED inner type — for a row of a 2-D array that IS the row object.
Scalar rows are unaffected (decay of a scalar is identity) and the
W-O F-N-1 array/pointer gate above it stays: a POINTER-typed base still
answers None and rides the computed route (the `(*q)[1]` fairness leg).

F-5  CONSTANT-SWITCH DISPATCH KEPT LATER DEAD ARMS AFTER AN UNBRACED
`break` (P2, latent, corpus volume 0 — the kernel arms are all braced).
`case 4: asm(...); break;` parses the break as a SIBLING of the Case
node; W-O's `_arm_terminates` read only `Case.stmt`, judged the tail
non-terminating, and kept every LATER arm — the reverse-order cmpxchg
probe as-died (`'%edx' not allowed with cmpxchgb'` rc3) where gcc
folds (rc0). THE LAW (W-P): the dispatch decides on the arm REGION's
last executed statement — the walk visits the region in execution
order and the predicate is deferred to the next marker; braced arms
and undetermined tails (if-without-else, loops) behave EXACTLY as at
W-O (cascade kept — never silent).
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
    """(gcc_exit, blcc_exit_or_None, blcc_stderr); exits are exit bytes."""
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
    s = tmp_path / (tag + ".c")
    s.write_text(src)
    o = tmp_path / (tag + ".bin")
    r = blcc(["-c", str(s), "--emit-asm", "-o", str(o)])
    assert r.returncode == 0, "blcc must compile:\n" + r.stderr
    return (tmp_path / (str(o) + ".s")).read_text()


def _gcc_asm(tmp_path, tag, src):
    s = tmp_path / (tag + ".c")
    s.write_text(src)
    x = tmp_path / (tag + ".s")
    r = gcc(REC + ["-S", str(s), "-o", str(x)])
    assert r.returncode == 0, "probe must be valid C: " + r.stderr
    return x.read_text()


# ------------------------------------------------------------- F-1 rows --

F1_G2D = """
int mm[2][3];
int main(void){ int v = 0; mm[1][2] = 122;
  asm("movl %1, %0" : "=r"(v) : "m"(mm[1][2]));
  return v & 255; }
"""


def test_wp0_f1_2d_global_run_pair(tmp_path):
    """Gate g12 shape: read mm[1][2] through "m" — the row step must be
    12, not the decayed row pointer's 8. Tip read mm+16 and exited 0
    where gcc exits 122: a SILENT value split, now pair-VALUE."""
    gex, bex, err = _run_pair(tmp_path, "wp0_f1a", F1_G2D)
    assert bex is not None, "blcc must compile:\n" + err
    assert (gex, bex) == (122, 122)


def test_wp0_f1_2d_global_fold_text(tmp_path):
    """The SAME shape's emission carries gcc's fold text EXACTLY:
    mm+20(%rip), never mm+16(%rip)."""
    txt = _blcc_asm(tmp_path, "wp0_f1t", F1_G2D)
    assert "mm+20(%rip)" in txt, txt
    assert "mm+16(%rip)" not in txt


def test_wp0_f1_frame_rows_run_pair(tmp_path):
    """Frame-local 2-D rows take the same law (-N(%rbp) at the row
    object's step); tip left mm[1][2] at 1 where gcc leaves 9."""
    src = """
int main(void) {
  int mm[2][3]; int i;
  for (i = 0; i < 6; i++) mm[i / 3][i % 3] = 1;
  asm volatile("movl $9, %0" : "=m"(mm[1][2]));
  return mm[1][2];
}
"""
    gex, bex, err = _run_pair(tmp_path, "wp0_f1b", src)
    assert bex is not None, err
    assert (gex, bex) == (9, 9)


def test_wp0_f1_char_rows_run_pair(tmp_path):
    """char rows: step = sizeof(char[5]) = 5, not 8 — the cc[2][1]
    write lands at byte 11; tip wrote cc+16 (both sides rc0, exit
    0 vs 4 — the silent split)."""
    src = """
char cc[3][5];
int main(void) {
  asm volatile("movb $4, %0" : "=m"(cc[2][1]));
  return cc[2][1];
}
"""
    gex, bex, err = _run_pair(tmp_path, "wp0_f1c", src)
    assert bex is not None, err
    assert (gex, bex) == (4, 4)


def test_wp0_f1_3d_rows_run_pair(tmp_path):
    """Three nested Index legs compose at the SAME entry: m3[1][2][3]
    = 1*48 + 2*16 + 3*4 = 92 (gcc text m3+92; tip m3+36 — decayed
    steps at two levels)."""
    src = """
int m3[2][3][4];
int main(void) {
  asm volatile("movl $66, %0" : "=m"(m3[1][2][3]));
  return m3[1][2][3];
}
"""
    gex, bex, err = _run_pair(tmp_path, "wp0_f1d", src)
    assert bex is not None, err
    assert (gex, bex) == (66, 66)


def test_wp0_f1_pointer_row_base_stays_computed(tmp_path):
    """FAIRNESS (green BOTH states, the W-O F-N-1 gate law): the base
    is a POINTER to array — the row address is a RUNTIME value; the
    fold answers None and the computed route carries the value.
    Pair-VALUE, and blcc's text stays the (%reg) form."""
    src = """
int mm[2][3];
int main(void){ int v = 0; mm[1][2] = 122;
  int (*q)[2][3] = mm;
  asm("movl %1, %0" : "=r"(v) : "m"((*q)[1][2]));
  return v & 255; }
"""
    gex, bex, err = _run_pair(tmp_path, "wp0_f1e", src)
    assert bex is not None, err
    assert (gex, bex) == (122, 122)


def test_wp0_f1_scalar_rows_untouched(tmp_path):
    """FAIRNESS green BOTH states: 1-D scalar rows (W-N/W-M legs'
    family) are UNCHANGED by the element-type switch — decay of a
    scalar is identity: la[2] of long la[4] stays byte 16. (Second
    self-instrument fix: the g13 spelling `movq` with an int "=r" is
    as-INVALID — operand mismatch — the int `movl` form runs.)"""
    src = """
int main(void){ long la[4]; int v = 0;
  la[0]=1; la[1]=2; la[2]=123; la[3]=4;
  asm("movl %1, %0" : "=r"(v) : "m"(la[2]));
  return (int)(v & 255); }
"""
    gex, bex, err = _run_pair(tmp_path, "wp0_f1f", src)
    assert bex is not None, err
    assert (gex, bex) == (123, 123)


def test_wp0_f1_row_object_type_law(tmp_path):
    """The TYPE law DIRECTLY: a same-symbol diff under "i" reads the
    row object too — `(long)&mm[1][2]-(long)&mm[0][0]` is 20 (gcc
    .word 20 at REC, measured); the fold's _asm_esz arm already read
    the UNDECAYED row — this leg pins BOTH mirrors on one number."""
    src = """
int mm[2][3];
int main(void){ asm volatile(".word %0" : : "i"((long)&mm[1][2]
   - (long)&mm[0][0])); return 3; }
"""
    gtxt = _gcc_asm(tmp_path, "wp0_f1g", src)
    btxt = _blcc_asm(tmp_path, "wp0_f1g", src)
    gr = [ln.strip() for ln in gtxt.splitlines() if ".word" in ln]
    br = [ln.strip() for ln in btxt.splitlines() if ".word" in ln]
    assert gr and br
    assert [re.sub(r"\s+", "", ln) for ln in gr] == \
           [re.sub(r"\s+", "", ln) for ln in br], (gr, br)


# ------------------------------------------------------------- F-5 rows --

F5_REV = """
typedef unsigned char u8; typedef unsigned int u32;
struct A { int counter; };
static inline __attribute__((__always_inline__)) int ac(struct A *v, int old, int new)
{
  int ret;
  switch ((sizeof(v->counter))) {
    case 4: asm volatile("cmpxchgl %2,%1" : "=a"(ret), "+m"(v->counter) : "q"(new), "0"(old) : "memory"); break;
    case 1: asm volatile("cmpxchgb %2,%1" : "=a"(ret), "+m"(v->counter) : "q"(new), "0"(old) : "memory"); break;
    default: break;
  }
  return ret;
}
struct A target;
int main(void){ target.counter = 5; return ac(&target, 5, 9) % 251; }
"""


def test_wp0_f5_unbraced_break_dispatch_run_pair(tmp_path):
    """The gate F-5 repro: live arm FIRST with an UNBRACED break, dead
    cmpxchgb arm AFTER it. gcc folds (rc0); the tip kept the later
    arm and DIED at as (`'%edx' not allowed with cmpxchgb'` rc3,
    captured RED at 2bc5857). Now pair-VALUE."""
    gex, bex, err = _run_pair(tmp_path, "wp0_f5a", F5_REV)
    assert bex is not None, "F-5 tail-walk regression:\n" + err
    assert (gex, bex) == (5, 5)


def test_wp0_f5_dead_arm_text_absent(tmp_path):
    """The dispatch law at TEXT level: the folded emission carries the
    live cmpxchgl and ZERO cmpxchgb texts — the dead arm never
    reaches `as` (the W-O cmpxchg pin, now also for the UNBRACED
    shape)."""
    txt = _blcc_asm(tmp_path, "wp0_f5t", F5_REV)
    assert "cmpxchgl" in txt
    assert "cmpxchgb" not in txt


def test_wp0_f5_return_tail_dispatch_pair(tmp_path):
    """A `return` sibling after an unbraced arm terminates the region
    the same way: the later arm's text stays dead."""
    src = """
struct A { int counter; };
static inline __attribute__((__always_inline__)) int f(struct A *v)
{
  int ret;
  switch ((sizeof(v->counter))) {
    case 4: asm volatile("movl $7, %0" : "=r"(ret)); return ret;
    case 1: asm volatile("movl $11, %0" : "=r"(ret)); return ret;
    default: break;
  }
  return 0;
}
struct A target;
int main(void){ return f(&target); }
"""
    gex, bex, err = _run_pair(tmp_path, "wp0_f5r", src)
    assert bex is not None, err
    assert (gex, bex) == (7, 7)
    txt = _blcc_asm(tmp_path, "wp0_f5r2", src)
    assert "movl $7" in txt and "movl $11" not in txt


def test_wp0_f5_unbraced_cascade_kept(tmp_path):
    """A FALL-THROUGH unbraced match keeps every later arm (C
    semantics; conservative side of the law): the region tail is a
    plain expression, gcc's folded .s keeps the cascade, exit is the
    SUM of both arms (7+1=8 pair-VALUE)."""
    src = """
struct A { int counter; };
static inline __attribute__((__always_inline__)) int f(struct A *v, int old, int new)
{
  int ret;
  switch ((sizeof(v->counter))) {
    case 4: asm volatile("movl $7, %0" : "=r"(ret));
    case 2: ret += 1; break;
    default: break;
  }
  return ret;
}
struct A target;
int main(void){ target.counter = 5; return f(&target, 5, 9); }
"""
    gex, bex, err = _run_pair(tmp_path, "wp0_f5b", src)
    assert bex is not None, err
    assert (gex, bex) == (8, 8)


def test_wp0_f5_braced_arms_w_o_unchanged(tmp_path):
    """FAIRNESS green BOTH states: the W-O braced-arm ascending cmpxchg
    (r4b shape) ships unchanged — its arms were already terminating;
    this leg is the F-5 law's no-regression pin beside the flip."""
    src = """
typedef unsigned char u8; typedef unsigned int u32;
struct A { int counter; };
static inline __attribute__((__always_inline__)) int ac(struct A *v, int old, int new)
{
  int ret;
  switch ((sizeof(v->counter))) {
    case 1: { volatile u8 *p = (volatile u8 *)&v->counter; asm volatile("cmpxchgb %2,%1" : "=a"(ret), "+m"(*p) : "q"(new), "0"(old) : "memory"); break; }
    case 4: { volatile u32 *p = (volatile u32 *)&v->counter; asm volatile("cmpxchgl %2,%1" : "=a"(ret), "+m"(*p) : "q"(new), "0"(old) : "memory"); break; }
    default: break;
  }
  return ret;
}
struct A target;
int main(void){ target.counter = 5; return ac(&target, 5, 9) % 251; }
"""
    gex, bex, err = _run_pair(tmp_path, "wp0_f5c", src)
    assert bex is not None, err
    assert (gex, bex) == (5, 5)
    txt = _blcc_asm(tmp_path, "wp0_f5c2", src)
    assert "cmpxchgl" in txt and "cmpxchgb" not in txt


def test_wp0_f5_runtime_control_unchanged(tmp_path):
    """FAIRNESS green BOTH states: a NON-folding control keeps the
    full compare chain and every arm text (the W-O runtime leg,
    re-pinned for the unbraced shape: all arms unbraced)."""
    src = """
int f(int k)
{
  int r = 0;
  switch (k) {
    case 1: r = 10; break;
    case 2: r = 20; break;
    default: r = 30; break;
  }
  return r;
}
int main(void){ return f(1) + f(2) + f(9) * 0 + 100; }
"""
    gex, bex, err = _run_pair(tmp_path, "wp0_f5d", src)
    assert bex is not None, err
    assert (gex, bex) == (130, 130)
