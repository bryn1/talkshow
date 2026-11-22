r"""M4 W-X COMMIT-0 (MC 12756) — F6: the clocksource ICE and its SILENT twin.

THE MEASURED ROOT CAUSE (own hands at 816d516, stream kernel_time_clocksource.c.i):
the fold-side light `expr_type` mirror (parser.py) answers None for EVERY
integer-binary shape — `typeof(cs_nsec - wd_nsec)` never materialized — so
`__builtin_types_compatible_p(typeof(cs_nsec - wd_nsec), signed long long)`
folded NOT-compatible (the §2.12 safe direction, W-L MC 12665) where gcc
folds 1. The kernel abs() choose-chain then took its `((void)0)` arm:
* when the void arm reached the codegen UAC law, `_uac` did
  `_RANK['void']` → raw KeyError → the §8 catch-all printed
  `asm: internal compiler error, found 'KeyError: void'` (the F6 row);
* whenever BOTH arms typecheck, the same fold is SILENT — own run-pair at
  tip: blcc exits 142 (false arm `42`), gcc exits 102 (true abs arm).

THE FIX, two arms of ONE concern (the named ICE class):
1. THE MIRROR EXTENDS (parser.expr_type, the fold-side type law — the
   SAME peel _csize/_calign ride): the light twin of the engine's
   _binary_ty arithmetic law — comparisons answer int; a shift takes its
   promoted LEFT operand; `+ - * / %` take the usual arithmetic
   conversions (§2.2, promoted operands, engine rank tables imported).
   Every shape the mirror cannot type (fp operands, struct operands,
   unresolvable names, pointer-shape stays as before) answers None —
   the safe direction is UNCHANGED and pinned below.
2. THE UAC GUARD names void: an arithmetic/comparison operand typed
   `void` takes the shipped LOUD 'arithmetic on a non-numeric type'
   sentence (§4, gcc rc1 'invalid use of void expression' twin) — the
   KeyError: void ICE is REPLACED, never queued.

KEEP postures this commit PRESERVES (pinned): fp operands still fold
NOT-compatible (None = safe direction, l13-class NAMED-DIVERGE family);
the pointer-arithmetic arms of the mirror are UNTOUCHED (the call-gate
negative leg at expr_parser.py stays as shipped); the §2.12 top-level
qual law is untouched.

INTEGRATED PER GATE ORDER (W-W gate 12753 FAIL driver, brief clause
"joins commit-0 BEFORE C1"): FINDING F1 — the `_Bool` bitfield NORMALIZE
law completes on the DATA path (bottom section below); the gate's
signed-+1-over adjudication found the PRODUCT FINE (gcc silent AND blcc
silent, values PAIR-equal), so no truncation change ships here.
"""
import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.environ.get("BLCC_REPO") or os.path.dirname(HERE)
REC = ["-std=gnu89", "-Os", "-mno-sse", "-mno-sse2", "-mno-80387",
       "-fno-stack-protector", "-fno-pic"]
ENV = {"PYTHONPATH": REPO, "PATH": "/usr/bin:/bin", "LC_ALL": "C"}


def blcc(args):
    return subprocess.run([sys.executable, "-m", "blcc"] + args,
                          capture_output=True, text=True, cwd=REPO, env=ENV)


def _w(tag, src):
    c = "/dev/shm/wx0_%s_%d.c" % (tag, os.getpid())
    open(c, "w").write(src)
    return c


MAIN = ("int probe(void);\n"
        "int main(int argc, char **argv) { (void)argc; (void)argv;\n"
        "  return probe() & 255; }\n")


def _pair(tag, src, want=None):
    """Run-pair (sims convention): blcc object and gcc object each link
    into the SAME layout, exit = the memory answer, values must match."""
    c = _w(tag, src)
    g = subprocess.run(["gcc"] + REC + [c, "-no-pie", "-o",
                       "/dev/shm/wx0_%s_%d.g" % (tag, os.getpid())],
                       capture_output=True, text=True,
                       env={"PATH": "/usr/bin:/bin", "LC_ALL": "C"})
    assert g.returncode == 0, "row must be valid C: " + g.stderr
    gex = subprocess.run(["/dev/shm/wx0_%s_%d.g" % (tag, os.getpid())],
                         env=ENV).returncode
    o = "/dev/shm/wx0_%s_%d.o" % (tag, os.getpid())
    b = blcc(["-c", c, "-o", o])
    assert b.returncode == 0, "%s must compile (RED-first: tip ICEs): " \
        % tag + b.stderr
    assert subprocess.run(["gcc", "-no-pie", o, "-o",
                           "/dev/shm/wx0_%s_%d.b" % (tag, os.getpid())],
                          capture_output=True).returncode == 0
    bex = subprocess.run(["/dev/shm/wx0_%s_%d.b" % (tag, os.getpid())],
                         env=ENV).returncode
    assert bex == gex, "%s run-pair: blcc=%d gcc=%d" % (tag, bex, gex)
    if want is not None:
        assert gex == want, "%s wants %d, both answered %d" % (tag, want,
                                                               gex)


def rp(body, want=None, tag="x"):
    _pair(tag, body + MAIN, want)


HDR = "typedef long long s64;\ntypedef unsigned long long u64;\n"

# ------------------------------------------------ THE F6 WITNESS (VERBATIM
# kernel/time/clocksource.c clocksource_watchdog shape, WARN_ON-stripped)

def test_f6_clocksource_abs_pair():
    """THE stream shape: abs(cs_nsec - wd_nsec) with the void fallback arm.
    tip: ICE 'KeyError: void' rc2. Fix: compiles AND picks gcc's arm."""
    rp(HDR + r"""
#define abs(x) __builtin_choose_expr(					\
	__builtin_types_compatible_p(typeof(x), signed long long) ||	\
	__builtin_types_compatible_p(typeof(x), unsigned long long),	\
	({ signed long long __x = (x); __x < 0 ? -__x : __x; }),	\
	((void)0))
int probe(void) { s64 cs = 10; u64 wd = 30;
  return (int)(abs(cs - wd) > 15); }        /* u64 diff 2^64-20 > 15 → 1 */
""", want=1, tag="f6abs")


# -------------------------------------------------- THE SILENT TWIN (both
# arms typecheck: tip compiles rc0 and answers the WRONG arm)

def test_f6_silent_arm_pair():
    """tip rc0 SILENT: exit 142 vs gcc 102. The false-arm value 42 must
    NEVER answer again."""
    rp(HDR + r"""
#define absv(x) __builtin_choose_expr(					\
	__builtin_types_compatible_p(typeof(x), signed long long),	\
	({ signed long long __x = (x); __x < 0 ? -__x : __x; }), 42L)
int probe(void) { s64 a = 5, b = 3; return (int)absv(a - b) + 100; }
""", want=102, tag="silent")


# --------------------------------------------- THE MIRROR TRUTH TABLE (fold
# side answers, each arm of the light law pinned by a run-pair)

TABLE = (
    ("int-sub-s64", "(s64)0 - (s64)0", "signed long long", 10),
    ("cmp-int", "((s64)1 > (s64)2)", "int", 10),
    ("shift-left-takes-left", "(s64)3 << 2", "signed long long", 10),
    ("mixed-uac", "(s64)0 - (u64)0", "unsigned long long", 10),
    ("int-times-s64", "(int)3 * (s64)3", "signed long long", 10),
    ("char-promotes", "(char)1 + (char)2", "int", 10),
    # NEGATIVE control: the mirror answers the UAC type, NOT every type —
    # rank precision matters (shift result is long long, never int).
    ("not-everything", "(s64)3 << 2", "int", 20),
)


def test_mirror_truth_table():
    """tcp(typeof(arith-expr), T) folds the ENGINE's _binary_ty answers:
    same-sign UAC (wider rank), mixed-sign (s64-u64 = u64), shift =
    promoted LEFT, comparisons = int, narrow promotes. want=20 rows are
    the NEGATIVE controls (declared T ≠ the UAC answer → false arm)."""
    for i, (tag, expr, ty, want) in enumerate(TABLE):
        src = HDR + (
            "int probe(void) { return (int)__builtin_choose_expr( \\\n"
            "  __builtin_types_compatible_p(typeof(%s), %s), 10, 20); }\n"
            % (expr, ty))
        rp(src, want=want, tag="tbl%d" % i)


def test_safe_direction_fp_stays_none():
    """fp operands STAY None → NOT-compatible (the §2.12 safe direction,
    l13-class NAMED-DIVERGE family): gcc answers 1 here (10), the fold
    keeps answering 0 (20) until fp arithmetic ships — a NAMED, PINNED
    divergence, so the next change to the mirror is a DECISION, never a
    drift. blcc-side answer only (this row is divergence, not a pair)."""
    c = _w("fpsafe", "typedef double dbl;\nint probe(void) { dbl d = 1.0;\n"
           "  return (int)__builtin_choose_expr(\n"
           "    __builtin_types_compatible_p(typeof(d - d), double),\n"
           "    10, 20); }\n" + MAIN)
    o = "/dev/shm/wx0_fpsafe_%d.o" % os.getpid()
    b = blcc(["-c", c, "-o", o])
    assert b.returncode == 0, "the false arm must compile rc0: " + b.stderr
    link = subprocess.run(["gcc", "-no-pie", o, "-o",
                           "/dev/shm/wx0_fpsafe_%d.b" % os.getpid()],
                          capture_output=True)
    assert link.returncode == 0
    assert subprocess.run(["/dev/shm/wx0_fpsafe_%d.b" % os.getpid()],
                          env=ENV).returncode == 20, "safe direction flipped"


# ------------------------------------------------ THE UAC VOID GUARD (the
# ICE class itself: LOUD with the shipped §4 sentence, never a KeyError)

def test_void_operand_loud_not_ice():
    """`(void){0} > 5`-style void rvalue in an arithmetic position: gcc
    rc1 'invalid use of void expression'; blcc tip ICEs (KeyError);
    fix: rc2 with the non-numeric §4 sentence, NO 'internal compiler
    error' text, and NO object at -o."""
    c = _w("void", "extern void v(void);\nint f(void) { return v() > 5; }\n")
    o = "/dev/shm/wx0_void_%d.o" % os.getpid()
    p = blcc(["-c", c, "-o", o])
    assert p.returncode == 2, "must be LOUD rc2: " + p.stderr
    assert "internal compiler error" not in p.stderr, \
        "the KeyError class must be GONE: " + p.stderr
    assert "arithmetic on a non-numeric type" in p.stderr, p.stderr
    assert not os.path.exists(o), "a diagnostic leaves no object (§3.5)"


# ==================== W-W GATE F1 (MC 12753 gate, FAIL driver, SILENT):
# the _Bool NORMALIZE law was shipped on the codegen path only; the DATA
# path (global/static initializers, designated AND positional, struct AND
# union) stored the UNNORMALIZED truncated value — gcc byte-pinned 01 for
# `{ .f = 2 }` on `_Bool f:1`, blcc@8654eae stored 0 (exit 0 vs 1). Gate
# evidence: .tmp/evidence/m4-ww-gate-verdict.md F1. Corpus exposure 0 —
# this is a law-twin completion, pinned RUN-PAIR on every site.

BOOLD = "struct B { _Bool f : 1; unsigned pad : 7; };\n"
BOOLU = "union U { _Bool f : 1; unsigned pad : 7; };\n"

F1_ROWS = (
    ("gd", BOOLD + "struct B g = { .f = 2 };"),          # designated
    ("gp", BOOLD + "struct B g = { 2 };"),              # positional
    ("vd", BOOLU + "union U g = { .f = 258 };"),        # union, any even
    ("vp", BOOLU + "union U g = { 258 };"),
    ("w7", "struct B { _Bool f : 1; unsigned pad : 7; };\n"
           "struct B g = { .f = 2, .pad = 100 };"),  # normalize + neighbour
    # survives in the SAME unit (probe = f*100+pad: gcc 200, tip 100);
    # _Bool:7 itself is INVALID C (gcc 'width of f exceeds its type') —
    # this is the width-family row the gate asked for, on legal ground.
    ("v7", "struct B7 { _Bool f : 1; unsigned pad : 7; };\n"
           "struct B7 g = { 7, 7 };"),               # odd value 7: pair pin
    ("neg", BOOLD + "struct B g = { .f = -3 };"),       # negative → 1
    # CONTROL: a NON-_Bool field truncates, it never normalizes:
    # unsigned char q:3 = 15 → 7 (mod 2^w, the shipped W-W copy law).
    ("trunc", "struct C { unsigned char q : 3; };\n"
              "struct C g = { .q = 15 };"),
)
F1_WANT = {"gd": 1, "gp": 1, "vd": 1, "vp": 1, "w7": 200, "v7": 107,
           "neg": 1, "trunc": 7}


def test_f1_bool_normalize_data_paths():
    """gcc=1 on every _Bool data-path row (gate byte-pinned); tip stored
    the raw low bit (2&1=0, 258&1=0) — SILENT, exit 0."""
    for tag, decl in F1_ROWS:
        fld = "q" if tag == "trunc" else "f"
        extra = (" * 100 + (int)g.pad" if tag in ("w7", "v7") else "")
        body = decl + "int probe(void) { return (int)g.%s%s; }\n" % (fld,
                                                                    extra)
        rp(body, want=F1_WANT[tag], tag="f1" + tag)


def test_f1_static_local_twin():
    """The static-LOCAL data path (same law, same site — W-W COMMIT-1's
    'local' wording meant codegen; a static local is a DATA path)."""
    rp("struct B { _Bool f : 1; };\n"
       "int probe(void) { static struct B s = { .f = 2 };\n"
       "  return (int)s.f; }\n", want=1, tag="f1sl")
