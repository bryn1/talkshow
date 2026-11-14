"""M2 fix-g2 (MC 12460 verify-loop cycle 2, card 12404.2.21) — C2-1.

__builtin_{add,sub,mul}_overflow w=8 mixed-shape flags NEVER SET (SILENT):
the wide path's jno leg was dead (xorl cleared OF before jno read it) and
mul had no predicate at all. The fix (expr_codegen._ex_overflow) carries
the TRUE result as (hi, lo) and fits that range — the law MEASURED against
gcc 11.4.0 -std=gnu89, run-pair twins at -O0 AND -Os (truth tables:
.tmp/fixg2/probes/oflaw.O0.out, -O0 == -Os verified): flag = the true
result of the operands' true values outside the RESULT type; stored = low
64 bits. add/sub w=8 ride the SAME law — CF alone is WRONG for mixed
signs (-1L + 1UL -> u64 does NOT flag; -2L + 1UL DOES; UMAX + 1UL flags).
Sibling pins: all-signed w=8 legs stay green; w<8 family untouched.

The run-pair harness here is SHARED (imported) by test_core_m2_fixg2b.py
(pointer compound scale, C2-2) and test_core_m2_fixg2c.py (bitfield
compound assign) — one harness, one mechanism.
"""
import os
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TMP = os.path.join(ROOT, ".tmp", "itofixg2")
_seq = [0]
_I64 = 1 << 64
_SMIN = -(1 << 63)
_SMAX = (1 << 63) - 1
_UMAX = (1 << 64) - 1


def _paths(tag):
    os.makedirs(TMP, exist_ok=True)
    _seq[0] += 1
    base = os.path.join(TMP, "g2_{}_{}_{}".format(tag, os.getpid(), _seq[0]))
    return base + ".c", base + ".blcc", base + ".gcc"


def both_run(src, tag):
    """Run-pair blcc vs gcc at -O0 AND -Os; byte-compare (rc, stdout)."""
    src_path, b_out, g_out = _paths(tag)
    with open(src_path, "w", encoding="utf-8") as fh:
        fh.write(src)
    try:
        rb = subprocess.run([sys.executable, "-m", "blcc", src_path,
                             "-o", b_out], cwd=ROOT, capture_output=True,
                            text=True, timeout=120)
        assert rb.returncode == 0, \
            "blcc compile failed ({}):\n{}".format(tag, rb.stderr)
        for opt in ("-O0", "-Os"):
            rg = subprocess.run(["gcc", "-w", "-std=gnu89", opt, src_path,
                                 "-o", g_out], capture_output=True,
                                text=True, timeout=60)
            assert rg.returncode == 0, "gcc twin {} must build ({})".format(
                opt, tag)
            pb = subprocess.run([b_out], capture_output=True, timeout=30)
            pg = subprocess.run([g_out], capture_output=True, timeout=30)
            assert (pb.returncode, pb.stdout) == (pg.returncode, pg.stdout), \
                "run-pair mismatch ({} {}): blcc rc={} gcc rc={}".format(
                    tag, opt, pb.returncode, pg.returncode)
    finally:
        for p in (src_path, b_out, g_out):
            if os.path.exists(p):
                os.remove(p)


def loud(src, tag, family, needle):
    src_path, b_out, _ = _paths(tag)
    with open(src_path, "w", encoding="utf-8") as fh:
        fh.write(src)
    try:
        rb = subprocess.run([sys.executable, "-m", "blcc", src_path,
                             "-o", b_out], cwd=ROOT, capture_output=True,
                            text=True, timeout=60)
        assert rb.returncode == 2, \
            "{} must LOUD, rc={}\n{}".format(tag, rb.returncode, rb.stderr)
        assert ": {}:".format(family) in rb.stderr, \
            "{} landed outside the {} family:\n{}".format(
                tag, family, rb.stderr)
        assert needle in rb.stderr, \
            "{} must name {!r}:\n{}".format(tag, needle, rb.stderr)
    finally:
        for p in (src_path, b_out):
            if os.path.exists(p):
                os.remove(p)


# ---------------------------------------------------------------- C2-1 ----
def _lit_signed(v):
    return "(-9223372036854775807L - 1)" if v == _SMIN else "{}L".format(v)


def _lit_unsigned(v):
    return "{}ul".format(v)


def _truth(mn, av, bv, ru):
    """(flag, value-literal): the MEASURED gcc law — true result outside
    the result-type range flags; stored = low 64 bits reinterpreted."""
    t = {"add": av + bv, "sub": av - bv, "mul": av * bv}[mn]
    lo, hi = (0, _UMAX) if ru else (_SMIN, _SMAX)
    f = 1 if (t < lo or t > hi) else 0
    low = t % _I64
    if ru:
        return f, _lit_unsigned(low)
    return f, _lit_signed(low - _I64 if low >= (1 << 63) else low)


def _of_prog(mn, a_signed, a, b_signed, b, gs, rows):
    """rows: (kind, result_unsigned) — operands: gu/gv unsigned, gs signed."""
    body, code = [], 1
    for (kind, ru) in rows:
        if kind == "uu":
            x, xs, y, ys = a, False, b, False
        elif kind == "su":
            x, xs, y, ys = gs, True, b, False
        elif kind == "us":
            x, xs, y, ys = a, False, gs, True
        elif kind == "ss":
            x, xs, y, ys = gs, True, gs, True
        f, lit = _truth(mn, x, y, ru)
        var, decl = ("ur", "unsigned long ur = 7;") if ru else \
            ("sr", "long sr = 7L;")
        body.append(
            "  {{ int ff; {} ff = __builtin_{}_overflow({}, {}, &{}); "
            "if (ff != {}) return {}; if ({} != {}) return {}; }}".format(
                decl, mn, "gs" if xs else "gu", "gs" if ys else "gv",
                var, f, code, var, lit, code + 1))
        code += 2
    return ("""
unsigned long gu = {}ul, gv = {}ul;
long gs = {};
int main(void){{
{}  return 0;
}}
""".format(a, b, _lit_signed(gs) if not (0 <= gs < (1 << 63))
           else "{}L".format(gs), "\n".join(body)))


def _of_run(mn, pairs, tag):
    for (a, b) in pairs:
        gs = -1 if (a >> 63) else a
        src = _of_prog(mn, True, a, False, b, gs,
                       [("uu", True), ("su", True), ("us", True),
                        ("ss", True), ("uu", False), ("su", False),
                        ("us", False)])
        both_run(src, tag + "_" + hex(a)[-6:] + "_" + hex(b)[-6:])


def test_mul_overflow_w8_unsigned_runtime():
    # Boundary legs measured against gcc (oflaw.O0.out): max*2 flags,
    # max*max flags, just-fits, just-over (2^63 DOES fit u64!), x0/x1.
    _of_run("mul", [(1 << 63, 2), (4611686018427387903, 2), (1 << 62, 2),
                    (_UMAX, _UMAX), (_UMAX, 0), (_UMAX, 1)], "mul_uu")


def test_mul_overflow_w8_signedxsigned_runtime():
    # signed x signed with an UNSIGNED result (case_a false — the mixed
    # posture row; -1 x LONG_MIN = 2^63 fits u64: flag 0) and the s64
    # result sibling stays on the green hw path (flag 0, value 1).
    f1, v1 = _truth("mul", -1, _SMIN, True)
    src = """
long ga = -1, gb = -9223372036854775807L - 1;
int main(void){{
  unsigned long ur = 7; long sr = 7; int f;
  f = __builtin_mul_overflow(ga, gb, &ur);
  if (f != {}) return 1; if (ur != {}) return 2;
  f = __builtin_mul_overflow(ga, ga, &sr);
  if (f != 0) return 3; if (sr != 1) return 4;
  f = __builtin_mul_overflow(ga, 0L, &ur);
  if (f != 0) return 5; if (ur != 0) return 6;
  return 0;
}}
""".format(f1, v1)
    both_run(src, "mul_ss_u")


def test_mul_overflow_w8_constfold_agreement():
    # gcc CONSTANT-FOLDS these legs; blcc rides the runtime engine — the
    # cross-check: SAME answers on both paths (trigger said rc 1/0).
    f1, v1 = _truth("mul", 1 << 63, 2, True)
    f2, v2 = _truth("mul", _UMAX, _UMAX, True)
    f3, v3 = _truth("mul", -3, 5, True)
    src = """
int main(void){{
  unsigned long ur = 7; int f;
  f = __builtin_mul_overflow(9223372036854775808UL, 2UL, &ur);
  if (f != {}) return 1; if (ur != {}) return 2;
  f = __builtin_mul_overflow(18446744073709551615UL,
                             18446744073709551615UL, &ur);
  if (f != {}) return 3; if (ur != {}) return 4;
  f = __builtin_mul_overflow(-3, 5, &ur);
  if (f != {}) return 5; if (ur != {}) return 6;
  f = __builtin_mul_overflow(3, 5, &ur);
  if (f != 0) return 7; if (ur != 15ul) return 8;
  return 0;
}}
""".format(f1, v1, f2, v2, f3, v3)
    both_run(src, "mul_constfold")


def test_add_overflow_w8_audit():
    # AUDIT: add at w=8 is the SAME silent class. Measured law: -1L+1UL->u
    # flag 0 (CF says 1!), -2L+1UL->u flag 1 (CF says 0!), UMAX+1UL flag 1.
    _of_run("add", [(_UMAX, 1), (1 << 63, 1 << 63), (_UMAX, _UMAX),
                    (5, 7), (_UMAX, 2)], "add_w8")


def test_sub_overflow_w8_audit():
    _of_run("sub", [(0, 1), (0, 0), (_UMAX, 1), (1, _UMAX), (2, 3)],
            "sub_w8")


def test_overflow_w8_all_signed_green():
    # case_a siblings stay green: all-signed w=8 add (addq+seto) and mul
    # (imulq+seto) — the legs the validator pinned at L3_3b.
    src = """
long ga = 9223372036854775807L, gb = 4294967296L;
int main(void){
  long r = 0; int f;
  f = __builtin_add_overflow(ga, 1L, &r);
  if (f != 1) return 1; if (r != -9223372036854775807L - 1) return 2;
  f = __builtin_add_overflow(-9223372036854775807L - 1, -1, &r);
  if (f != 1) return 3;
  f = __builtin_add_overflow(1L, 2L, &r);
  if (f != 0) return 4; if (r != 3) return 5;
  f = __builtin_mul_overflow(gb, gb, &r);
  if (f != 1) return 6;
  f = __builtin_mul_overflow(3L, 5L, &r);
  if (f != 0) return 7; if (r != 15) return 8;
  f = __builtin_mul_overflow(-9223372036854775807L - 1, 1L, &r);
  if (f != 0) return 9;
  return 0;
}
"""
    both_run(src, "oflo_ss_w8")


