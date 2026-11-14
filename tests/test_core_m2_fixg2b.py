"""M2 fix-g2 (MC 12460, card 12404.2.21) — C2-2: pointer compound assign.

p += n / p -= n DROPPED the xsizeof scale on non-char pointers (legacy
SILENT miscompile). The fix routes the compound path through the shipped
scaled binary law (_ptr_scale — _ptr_add's imulq $esz mechanism, now one
mechanism for both callers). Widths {char,short,int,long,struct 24B} x
{+=,-=} x {const,var} index x auto/static/global LHS; readbacks via
(p-arr)==n; real-kernel witness regs_get_kernel_stack_nth_addr (arch/x86/
include/asm/ptrace.h:292-301 `addr += n;`). SIBLING AUDIT: p++/-- non-char,
*p++, *p+=x, p[i]=, p-q measured scaled-GREEN (pinned); compound &=|=^= on
a pointer: gcc rc1 ERROR (measured) — blcc LOUD pinned; p+p/p+=p: gcc rc1
— blcc LOUD ("pointer + pointer"); i += p: gnu89 warning-shape (rc0) —
compiles; the stored value embeds the (ASLR) address so the leg pins
compile+exit parity, not the address value.
"""
import os
import subprocess
import sys

from test_core_m2_fixg2 import ROOT, _paths, both_run, loud

# ---------------------------------------------------------------- C2-2 ----
_PTR_MATRIX = """
struct Big { long a; long b; long c; };
char carr[8]  = {0,1,2,3,4,5,6,7};
short sarr[8] = {0,1,2,3,4,5,6,7};
int   iarr[8] = {10,11,12,13,14,15,16,17};
long  larr[8] = {20,21,22,23,24,25,26,27};
struct Big barr[4];
long one = 1, three = 3;
static char *sc1; static int *si1; static struct Big *sb1;
int *gp;
int main(void){
  char *p; short *q; int *r; long *u; struct Big *v;
  barr[0].a = 1;  barr[0].b = 2;  barr[0].c = 3;
  barr[1].a = 4;  barr[1].b = 5;  barr[1].c = 6;
  barr[2].a = 7;  barr[2].b = 8;  barr[2].c = 9;
  p = carr;   p += 3;   if ((int)(p-carr) != 3) return 1;  if (*p != 3) return 2;
  p = carr;   p += one; if ((int)(p-carr) != 1) return 3;
  p = carr+4; p -= 2;   if ((int)(p-carr) != 2) return 4;  if (*p != 2) return 5;
  q = sarr;   q += 3;   if ((int)(q-sarr) != 3) return 6;  if (*q != 3) return 7;
  q = sarr;   q += one; if ((int)(q-sarr) != 1) return 8;
  q = sarr+4; q -= 3;   if ((int)(q-sarr) != 1) return 9;  if (*q != 1) return 10;
  r = iarr;   r += 3;   if ((int)(r-iarr) != 3) return 11; if (*r != 13) return 12;
  r = iarr;   r += one; if ((int)(r-iarr) != 1) return 13;
  r = iarr+4; r -= three; if ((int)(r-iarr) != 1) return 14; if (*r != 11) return 15;
  u = larr;   u += 3;   if ((int)(u-larr) != 3) return 16; if (*u != 23) return 17;
  u = larr;   u += one; if ((int)(u-larr) != 1) return 18;
  u = larr+4; u -= three; if ((int)(u-larr) != 1) return 19; if (*u != 21) return 20;
  v = barr;   v += 2;   if ((int)(v-barr) != 2) return 21; if (v->b != 8) return 22;
  v = barr;   v += one; if ((int)(v-barr) != 1) return 23; if (v->c != 6) return 24;
  v = barr+2; v -= three; if ((int)(v-barr+1) != 0) return 25;
  sc1 = carr; sc1 += 3;   if ((int)(sc1-carr) != 3) return 26;
  si1 = iarr; si1 += one; if ((int)(si1-iarr) != 1) return 27;
  sb1 = barr; sb1 += 2;   if ((int)(sb1-barr) != 2) return 28; if (sb1->c != 9) return 29;
  sb1 = barr+1; sb1 -= 1; if ((int)(sb1-barr) != 0) return 30;
  gp = iarr;  gp += 2;    if ((int)(gp-iarr) != 2) return 31; if (*gp != 12) return 32;
  gp = iarr+2; gp -= three; if ((int)(gp-iarr+1) != 0) return 33;
  return 0;
}
"""


def test_ptr_compound_assign_scale_matrix():
    # C2-2: widths {char,short,int,long,struct 24B} x {+=,-=} x {const,var}
    # index x auto/static/global LHS; every readback via (p-arr)==n.
    both_run(_PTR_MATRIX, "ptr_scale_matrix")


_PTR_WITNESS = """
struct pt_regs { unsigned long sp; };
unsigned long stackarea[16];
int within_kernel(unsigned long a, unsigned long lo, unsigned long hi){
  return a >= lo && a < hi;
}
unsigned long *stack_nth_addr(struct pt_regs *regs, unsigned int n,
                              unsigned long lo, unsigned long hi){
  unsigned long *addr = (unsigned long *)regs->sp;
  addr += n;
  if (within_kernel((unsigned long)addr, lo, hi))
    return addr;
  return (unsigned long *)0;
}
long arg_nth(struct pt_regs *regs, int n){
  long *p = (long *)regs->sp;
  int i; long r = 0;
  for (i = 0; i < n; i++){ p += 1; r = *p; }
  return r;
}
int main(void){
  int i; struct pt_regs regs;
  for (i = 0; i < 16; i++) stackarea[i] = 100 + i;
  regs.sp = (unsigned long)&stackarea[8];
  {
    unsigned long lo = (unsigned long)stackarea;
    unsigned long hi = lo + 16 * 8;
    unsigned long *a = stack_nth_addr(&regs, 3, lo, hi);
    if (a == (unsigned long *)0) return 1;
    if (*a != 111) return 2;                    /* stackarea[8+3] scaled */
    if ((int)(a - stackarea) != 11) return 3;
    a = stack_nth_addr(&regs, 60, lo, hi);
    if (a != (unsigned long *)0) return 4;
    if (arg_nth(&regs, 3) != 111) return 5;     /* += walk, element step */
  }
  return 0;
}
"""


def test_ptr_compound_witness_regs_stack_nth():
    # real-kernel witness: regs_get_kernel_stack_nth_addr shape from
    # arch/x86/include/asm/ptrace.h:292-301 (`addr += n;` on unsigned long*)
    # and the regs_get_kernel_argument walk (offs_cpu_h.i:8010 chain).
    both_run(_PTR_WITNESS, "ptr_witness_cpu_h")


_INCDEC = """
struct Big { long a; long b; long c; };
struct Big barr[4];
int iarr[8] = {10,11,12,13,14,15,16,17};
long larr[8];
short sarr[8];
int main(void){
  int *p = iarr; struct Big *v = barr; long *u = larr; short *q = sarr;
  barr[0].a = 1; barr[1].a = 2; barr[2].a = 3; barr[3].a = 4;
  larr[0] = 50; sarr[1] = 7;
  if (*p++ != 10) return 1;   if ((int)(p-iarr) != 1) return 2;
  if (++*p != 12) return 3;                        /* iarr[1] = 12 */
  if ((*p)++ != 12) return 4;  if (*p != 13) return 5;
  ++p;  if ((int)(p-iarr) != 3) return 6;
  p--;  if ((int)(p-iarr) != 2) return 7;
  *p += 5; if (*p != 17 || iarr[2] != 17) return 8;
  iarr[2] += 2; if (iarr[2] != 19) return 9;
  p[3] = 99; if (iarr[5] != 99) return 10;
  if (v++->a != 1) return 11; if ((int)(v-barr) != 1) return 12;
  ++v; if ((int)(v-barr) != 2) return 13;
  *u += 3; if (larr[0] != 53) return 14;
  ++q; *q += 1; if (sarr[1] != 8) return 15;
  { int *e = iarr + 6; int *s = iarr + 1;
    if ((int)(e - s) != 5) return 16;
    if ((int)(iarr + 6 - s) != 5) return 17; }
  { struct Big *be = barr + 3, *bs = barr + 1;
    if ((int)(be - bs) != 2) return 18; }
  { int *be = iarr, *bs = iarr; be += 0; be = bs + 4;
    if ((int)(be - bs) != 4) return 19; }
  return 0;
}
"""


def test_incdec_index_diff_siblings_green():
    # SIBLING AUDIT rows (p++/-- non-char, *p++, *p+=x, p[i]=, p-q):
    # measured scaled-GREEN on gcc; pinned green here (they rode the
    # already-correct path — the SILENT sat only in compound assign).
    both_run(_INCDEC, "ptr_siblings")


def test_compound_bitwise_on_pointer_is_loud():
    # gcc posture measured: "error: invalid operands to binary & (have
    # 'int *' and 'int')" rc1 — blcc must LOUD, never raw andq/orq/xorq.
    for op in ("&", "|", "^"):
        loud("""
int main(void){ int a[4]; int *p = a; p %s= 3; return *p; }
""" % op, "compound_bitwise_ptr_" + op, "sema",
             "'{}' with a pointer operand is not in the subset".format(op))


def test_pointer_plus_pointer_is_loud():
    # gcc: binary + with 'int *' and 'int *' -> error rc1 (measured).
    loud("""
int main(void){ int a[4]; int *p = a; p += p; return 0; }
""", "pp_compound", "sema", "pointer + pointer")
    loud("""
int main(void){ int a[4]; int *p = a; int *q = p + p; return *q; }
""", "pp_binary", "sema", "pointer + pointer")


def test_array_lvalue_compound_is_loud():
    # SIBLING AUDIT: `arr += 1` — gcc rc1 "assignment to expression with
    # array type" (measured); the decayed target made the old compound
    # path store a POINTER into the array's first bytes (SILENT write
    # into arr[0..7]).
    loud("""
int main(void){ int a[4]; a += 1; return 0; }
""", "arr_compound", "sema", "assignment to expression with array type")


def test_int_plus_pointer_compound_gnu89_green():
    # gnu89 warning-shape (rc0 measured): int i; i += p compiles and runs.
    # The stored value embeds the stack address (ASLR) so nothing about it
    # is printable; this pins compile+exit parity (NOT loud — legal pointer
    # arithmetic plus gnu89 warning-only assignment).
    src = "int main(void){ int a[4] = {1,2,3,4}; int i = 7; int *p = a; " \
          "i += p; return 0; }"
    src_path, b_out, g_out = _paths("int_plus_ptr")
    with open(src_path, "w", encoding="utf-8") as fh:
        fh.write(src)
    try:
        rb = subprocess.run([sys.executable, "-m", "blcc", src_path,
                             "-o", b_out], cwd=ROOT, capture_output=True,
                            text=True, timeout=60)
        assert rb.returncode == 0, \
            "int += ptr must NOT loud (gnu89 warning-shape): " + rb.stderr
        rg = subprocess.run(["gcc", "-w", "-std=gnu89", "-O0", src_path,
                             "-o", g_out], capture_output=True,
                            text=True, timeout=60)
        assert rg.returncode == 0
        pb = subprocess.run([b_out], capture_output=True, timeout=30)
        pg = subprocess.run([g_out], capture_output=True, timeout=30)
        assert pb.returncode == pg.returncode == 0
    finally:
        for p in (src_path, b_out, g_out):
            if os.path.exists(p):
                os.remove(p)


