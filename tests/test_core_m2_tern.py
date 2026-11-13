"""§1c AMENDMENT v4.2 row 1 (MC 12486): runtime conditional `e1 ? e2 : e3`.

Law measured THIS session against gcc 11.4.0 -std=gnu89 (probes under
/tmp-free scratch .tmp/gf-tern/probes, re-run at -O0 AND -Os):
* RESULT TYPE = usual arithmetic conversions of the arms — same law the
  binary + family uses (i?u: is unsigned int — `ui ? -1 : 1` assigned to
  long is 4294967295, NOT -1); narrow arms promote (short?x:1 is int).
* POINTER ARMS: pointer vs pointer -> first arm's type when incompatible
  (gcc WARNS, rc0 — measured `int*/long*` assigns to int* clean); void*
  mixed with T* -> void* (C11 6.5.15p6, warning-free); a null pointer
  constant (folded 0) takes the OTHER arm's pointer type; pointer vs a
  NON-zero integer is a warning-only gnu89 accept with the POINTER type
  (sizeof(__typeof__(pi?pi:1)) == 8, sizeof(pi?1:pi) == 8).
* GNU `a ?: b` — ACCEPTED in gnu89 (kernel uses it): a evaluated ONCE,
  its value when true; result type = UAC of the two operands (measured
  sizeof(__typeof__(si ?: sl)) == 8 AND (sl ?: si) == 8).
* VOID arms (both) accepted as a statement; struct arms SAME type are
  accepted by gcc (sizeof(__typeof__(c?s1:s2)) == 4) — blcc MIRRORS its
  shipped §5 struct-VALUE wall for the RUNTIME arm (sizeof still folds);
  float arms same kind type (4/8) — blcc keeps row-14 storage posture.
* Precedence: assignment binds LOOSER than ?:; the middle is a full
  expression INCLUDING the comma operator (`1 ? 2, 3 : 4` == 3 measured);
  the THIRD operand is a conditional-expression (right-associative
  chains; `a ? b : c = d` is a syntax error — gcc rc1).
"""
import os
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TMP = os.path.join(ROOT, ".tmp", "ittern")
_seq = [0]


def _paths(tag):
    os.makedirs(TMP, exist_ok=True)
    _seq[0] += 1
    base = os.path.join(TMP, "tern_{}_{}_{}".format(tag, os.getpid(),
                                                    _seq[0]))
    return base + ".c", base + ".blcc", base + ".gcc"


def both_run(src, tag):
    src_path, b_out, g_out = _paths(tag)
    with open(src_path, "w", encoding="utf-8") as fh:
        fh.write(src)
    rb = subprocess.run([sys.executable, "-m", "blcc", src_path,
                         "-o", b_out], cwd=ROOT, capture_output=True,
                        timeout=60, text=True)
    try:
        assert rb.returncode == 0, \
            "blcc compile failed ({}):\n{}".format(tag, rb.stderr)
        rg = subprocess.run(["gcc", "-w", "-std=gnu89", "-O0", src_path,
                             "-o", g_out], capture_output=True, text=True,
                            timeout=60)
        assert rg.returncode == 0, "gcc twin must build ({}):\n{}".format(
            tag, rg.stderr)
        pb = subprocess.run([b_out], capture_output=True, timeout=30)
        pg = subprocess.run([g_out], capture_output=True, timeout=30)
        assert (pb.returncode, pb.stdout) == (pg.returncode, pg.stdout), \
            "run-pair mismatch ({}): blcc={} gcc={}".format(
                tag, (pb.returncode, pb.stdout), (pg.returncode, pg.stdout))
    finally:
        for p in (src_path, b_out, g_out):
            if os.path.exists(p):
                os.remove(p)


def both_rc(src, tag, expect):
    """Run-pair where main() RETURNS the check code: gcc twin must build
    and BOTH binaries answer the same exit code == expect."""
    both_run(src, tag)
    # both_run already asserts (rc,stdout) equality; pin the VALUE here:
    src_path, b_out, g_out = _paths(tag)
    with open(src_path, "w", encoding="utf-8") as fh:
        fh.write(src)
    rb = subprocess.run([sys.executable, "-m", "blcc", src_path,
                         "-o", b_out], cwd=ROOT, capture_output=True,
                        timeout=60, text=True)
    try:
        assert rb.returncode == 0, "blcc failed:\n" + rb.stderr
        rg = subprocess.run(["gcc", "-w", "-std=gnu89", "-O0", src_path,
                             "-o", g_out], capture_output=True, text=True)
        assert rg.returncode == 0, "gcc twin failed:\n" + rg.stderr
        pb = subprocess.run([b_out], capture_output=True, timeout=30)
        assert pb.returncode == expect, "blcc answered {}, expected {}".format(
            pb.returncode, expect)
    finally:
        for p in (src_path, b_out, g_out):
            if os.path.exists(p):
                os.remove(p)


def blcc_loud(src, tag, family="parse", needle=None):
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
        if needle is not None:
            assert needle in rb.stderr, \
                "{} must name {!r}:\n{}".format(tag, needle, rb.stderr)
    finally:
        for p in (src_path, b_out):
            if os.path.exists(p):
                os.remove(p)


# ---------------------------------------------------------------- run-pairs

def test_tern_basic_true_false():
    both_rc("""
int main(void){
  int r = 0;
  if ((1 ? 2 : 3) != 2) r |= 1;
  if ((0 ? 2 : 3) != 3) r |= 2;
  if ((5 - 5 ? 2 : 3) != 3) r |= 4;
  return r; }
""", "basic", 0)


def test_tern_precedence_and_init_contexts():
    both_rc("""
int g = 1 ? 6 : 7;                    /* init context, fold */
int main(void){
  int r = 0;
  int a = g ? 1 : 2;                  /* auto init, runtime  */
  int y = 1 + 0 ? 4 : 5 + 6;          /* binary binds tighter than ?: */
  int z = 0 ? 1 : 2 + 3;              /* third arm is a full cond-expr */
  int w = (a ? w * 0 + 1 : 2);        /* parens */
  int u; u = (a ? 5 : 6);
  if ((g ? 1 : 2) + 10 != 11) r |= 1;
  if (a != 1 || y != 4 || z != 5 || w != 1 || u != 5) r |= 2;
  if (g != 6) r |= 4;
  return r; }
""", "prec", 0)


def test_tern_middle_assignment_allowed():
    # the middle is a full expression: assignment binds there (gcc rc0).
    both_rc("""
int main(void){
  int z = 0, x;
  x = 1 ? (z = 3) : 4;
  if (x != 3 || z != 3) return 1;
  x = 0 ? (z = 9) : 4;
  if (x != 4 || z != 3) return 2;
  return 0; }
""", "midassign", 0)


def test_tern_right_assoc_chains():
    both_rc("""
int main(void){
  int r = 0;
  if ((0 ? 11 : 1 ? 22 : 33) != 22) r |= 1;      /* a?b:(c?d:e) */
  if ((1 ? 11 : 0 ? 22 : 33) != 11) r |= 2;
  if ((0 ? 1 : 0 ? 2 : 3) != 3) r |= 4;
  if ((1 ? 0 : 1 ? 0 : 1 ? 7 : 8) != 0) r |= 8;  /* deep chain */
  return r; }
""", "rassoc", 0)


def test_tern_right_assoc_counters():
    # association PROVEN by side effects: middle-true shortens the chain.
    both_rc("""
int e1, e2, e3;
int c1(void){ e1++; return 0; }
int c2(void){ e2++; return 1; }
int c3(void){ e3++; return 7; }
int main(void){
  int x = c1() ? c3() : c2() ? c3() : c3();
  /* c1=0 -> right cond c2=1 -> value c3 (ONE of the two c3 arms) */
  if (x != 7) return 1;
  if (e1 != 1 || e2 != 1) return 2;
  if (e3 != 1) return 3;                       /* exactly one arm ran */
  return 0; }
""", "rassoc2", 0)


def test_tern_comma_in_middle():
    both_rc("""
int add2(int a, int b){ return a + b; }
int main(void){
  int r = 0;
  int x = 1 ? 2, 3 : 4;              /* middle eats the comma (gcc rc0) */
  if (x != 3) r |= 1;
  x = 0 ? 2, 3 : 4;                  /* false: the comma part never runs */
  if (x != 4) r |= 2;
  x = 1 ? 10, 20, 30 : 40;
  if (x != 30) r |= 4;
  if (add2(1 ? 2, 3 : 4, 10) != 13) r |= 8;   /* arg split at the OUTER comma */
  return r; }
""", "commamid", 0)


def test_tern_comma_middle_side_effects():
    both_rc("""
int left, right;
int L(void){ left++; return 1; }
int R(void){ right++; return 2; }
int main(void){
  int x = 1 ? L(), R() : 99;
  if (x != 2 || left != 1 || right != 1) return 1;
  x = 0 ? L(), R() : 99;
  if (x != 99 || left != 1 || right != 1) return 2;  /* neither runs */
  return 0; }
""", "commase", 0)


def test_tern_condition_eval_once():
    both_rc("""
int n;
int ge(void){ n++; return 5; }
int main(void){
  int a = ge() ? 1 : 2;
  if (a != 1 || n != 1) return 1;     /* condition evaluated EXACTLY once */
  return 0; }
""", "once", 0)


def test_tern_arm_side_effects_both_counts():
    both_rc("""
int bc, gc;
int be(void){ bc++; return 5; }
int ge(void){ gc++; return 7; }
int main(void){
  int x = 1 ? be() : ge();
  if (x != 5 || bc != 1 || gc != 0) return 1;   /* only the TRUE arm ran */
  x = 0 ? be() : ge();
  if (x != 7 || bc != 1 || gc != 1) return 2;   /* only the FALSE arm ran */
  return 0; }
""", "arms", 0)


def test_tern_pointer_arms():
    both_rc("""
int main(void){
  int v1 = 1, v2 = 2;
  int pick = 0;
  int *p = pick ? &v1 : &v2;
  if (*p != 2) return 1;
  p = pick ? &v1 : 0;                  /* null pointer constant arm */
  if (p != 0) return 2;
  pick = 1;
  p = pick ? &v1 : &v2;
  if (*p != 1) return 3;
  return 0; }
""", "ptr", 0)


def test_tern_void_ptr_mix():
    both_rc("""
int main(void){
  int i = 42; int c = 0; void *pv;
  pv = c ? (void *)0 : &i;             /* void-mixed T* -> void* result */
  if (*(int *)pv != 42) return 1;      /* the &i arm ran through void* */
  c = 1;
  pv = c ? (void *)0 : &i;             /* the void-null arm */
  if (pv != 0) return 2;
  return 0; }
""", "voidptr", 0)


def test_tern_signed_unsigned_runtime():
    both_rc("""
int main(void){
  unsigned ui = 1; int si = 0; long L;
  /* THE mixed-sign law: the CONDITION never joins the type; one UNSIGNED
     arm makes the result unsigned, so -1 widens to 4294967295 (measured
     w1b: `unsigned ? : int` == unsigned int, sizeof 4). */
  L = (ui ? -1 : 1u);
  if (L != 4294967295L) return 1;
  si = 1;
  L = (si ? -1 : 1);                   /* int-vs-int: -1 stays -1 */
  if (L != -1) return 2;
  if ((si ? 3 : 4) + 0 != 3) return 3;
  return 0; }
""", "signmix", 0)


def test_tern_promotion_types():
    both_rc("""
short sh; char ch;
#define TSZ(expr) (long)sizeof(1 ? (expr) : 1)
int main(void){
  if (sizeof(1 ? sh : 1) != 4) return 1;   /* short promotes to int */
  if (sizeof(1 ? ch : 1u) != 4) return 2;  /* char vs unsigned -> uint */
  return 0; }
""", "promo", 0)


def test_tern_elvis_gnu_form():
    both_rc("""
int main(void){
  long sl = 9; int si = 0;
  if ((sl ?: 4) != 9) return 1;        /* truthy: FIRST operand's value */
  if ((si ?: 4) != 4) return 2;        /* falsy: the other arm */
  long r = (si ?: sl);                 /* result type UAC(si,sl) = long */
  if (r != 9) return 3;
  return 0; }
""", "elvis", 0)


def test_tern_elvis_eval_once():
    both_rc("""
int n;
int c0(void){ n++; return 0; }
int c7(void){ n++; return 7; }
int main(void){
  int x = c0() ?: 55;
  if (x != 55 || n != 1) return 1;     /* the FALSE side: a ran once, b once */
  x = c7() ?: 55;
  if (x != 7 || n != 2) return 2;      /* the TRUE side: a once — NOT twice */
  return 0; }
""", "elvisonce", 0)


def test_tern_sizeof_folds_constant_arms():
    both_rc("""
char a[1 ? 4 : 9];
char b[0 ? 4 : 9];
int main(void){
  if (sizeof(1 ? 2 : 3) != 4) return 1;          /* int arms fold */
  if (sizeof(1 ? 2L : 3) != 8) return 2;         /* UAC picks long */
  if (sizeof(a) != 4 || sizeof(b) != 9) return 3;/* array sizes fold */
  return 0; }
""", "sizeoffold", 0)


def test_tern_global_init_fold():
    both_rc("""
int gv = 3;
int g0 = 1 ? 5 : 7;                   /* folded at the data layer */
long g1 = 0 ? 3 : 4;
int garr[2 ? 3 : 9];
int main(void){
  if (g0 != 5) return 1;
  if (g1 != 4) return 2;
  if (sizeof(garr) != 12) return 3;
  garr[2] = 9;                        /* the folded size is REAL storage */
  if (garr[2] != 9) return 4;
  return 0; }
""", "ginit", 0)


def test_tern_enum_and_case_fold():
    both_rc("""
enum { E = 0 ? 9 : 7 };
int sw(int k){ switch (k){ case 1 ? 2 : 3: return 22; default: return 0; } }
int main(void){
  if (E != 7) return 1;
  if (sw(2) != 22) return 2;
  if (sw(1) != 0) return 3;
  return 0; }
""", "enumcase", 0)


def test_tern_sizeof_struct_arms_fold():
    # sizeof folds the struct result (gcc: same-type struct arms rc0,
    # sizeof == 4); blcc folds the TYPE — no struct VALUE is materialized.
    both_rc("""
struct S { int x; };
struct S s1, s2;
int main(void){
  if (sizeof(1 ? s1 : s2) != 4) return 1;
  return 0; }
""", "structsizeof", 0)


def test_tern_void_arms_statement():
    both_rc("""
int tc, gc;
void tv(void){ tc++; }
void gv(void){ gc++; }
int main(void){
  1 ? tv() : gv();                     /* void arms, statement context */
  if (tc != 1 || gc != 0) return 1;
  0 ? tv() : gv();
  if (tc != 1 || gc != 1) return 2;
  return 0; }
""", "voidarms", 0)


def test_tern_nested_in_call_args():
    both_rc("""
int add3(int a, int b, int c){ return a + b + c; }
int main(void){
  int i = 1;
  if (add3(i ? 1 : 2, i ? 3 : 4, i ? 5 : 6) != 9) return 1;
  return 0; }
""", "callargs", 0)


def test_tern_cond_used_in_bigger_expr():
    both_rc("""
int arr[4];
int main(void){
  int i = 2;
  arr[0] = 10; arr[1] = 20;
  int v = (i ? arr[1] : arr[0]) * 2 + (i ? 1 : 2);
  if (v != 41) return 1;
  return 0; }
""", "bigger", 0)


# ------------------------------------------------------------------- LOUDs

def test_tern_struct_arms_runtime_loud():
    # gcc SUPPORTS same-type struct arms; blcc mirrors its shipped §5
    # struct-VALUE wall (assignment precedent) — LOUD, never silent.
    blcc_loud("""
struct S { int x; };
struct S s1, s2; int c;
int main(void){ struct S s = c ? s1 : s2; return s.x; }
""", "structloud", "sema", "struct")


def test_tern_assign_to_result_loud():
    blcc_loud("""
int x, y, c;
int main(void){ (c ? x : y) = 1; return x; }
""", "assterm", "parse", "non-l-value")


def test_tern_assign_in_third_operand_loud():
    # `a ? b : c = d` is a syntax error in standard C (gcc rc1): the
    # third operand is a conditional-expression, assignments bind looser.
    blcc_loud("""
int x, c;
int main(void){ int r = c ? 1 : x = 5; return r; }
""", "thirdassign", "parse")


def test_tern_statement_comma_stays_loud():
    # `x = 1 ? 2 : 3, 5;` — gcc rc0 (top-level comma operator); blcc's
    # comma-operator wall is shipped §5 (the census names it separately).
    blcc_loud("""
int main(void){ int x; x = 1 ? 2 : 3, 5; return x; }
""", "stmtcomma", "parse")


def test_tern_nonconst_global_init_loud():
    blcc_loud("""
int gv;
int g = gv ? 1 : 2;                   /* gcc: initializer element is not
                                         constant (rc1) */
""", "gnonconst", "sema")


def test_tern_pp_if_unchanged():
    # the PREPROCESSOR's ?: (pp_eval, M1 F-5) is a DIFFERENT mechanism —
    # untouched by the runtime row; this leg pins it still answers.
    both_rc("""
#if 1 ? 2 : 3
int branch = 2;
#else
int branch = 3;
#endif
int main(void){ return branch == 2 ? 0 : 1; }
""", "ppif", 0)
