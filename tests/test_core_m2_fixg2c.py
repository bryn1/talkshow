"""M2 fix-g2 (MC 12460, card 12404.2.21) — bitfield compound assign.

s.a |= m (and &= ^= += -= <<= >>=) on a bit-field lvalue was LOUD-rejected
(the §5 &bitfield wall). Measured gcc 11.4 gnu89 law (probes/bfc.O0.out,
-O0 == -Os): RMW on the storage UNIT — read the field (sign/zero-extended
by its own width), arithmetic at the promoted unit type, then mask-merge
back into the unit (neighbours byte-intact: fix-g1 byte-window instrument
in test_bf_compound_neighbour_window); the expression value is the
CONVERTED STORED value (gcc: 3 += 1 in int:3 reads -4). gcc-error shapes
(pointer operand, fp operand) stay LOUD, never silent.
"""
from test_core_m2_fixg2 import both_run, loud

# --------------------------------------------------------------- ----
_BF_C = r"""
struct S  { int a:3; int b:29; unsigned int uf:5; int nb; signed char sc:4; };
struct M  { int x; int a:3; int b:29; int y; };
struct SA { int a:3; int b:5; };
struct S s; struct M m; struct SA sa; int junk = 12345;
int main(void){
  struct S *ps;
  s.a = 3;  s.b = 7;  s.uf = 3;  s.nb = 99; s.sc = -1;
  s.a += 1;  if (s.a != -4) return 1;   if (s.b != 7) return 2;
  s.a -= 4;  if (s.a != 0) return 3;    if (s.nb != 99) return 4;
  s.uf |= 20;  if (s.uf != 23) return 5;  if (s.b != 7) return 6;
  s.uf ^= 31;  if (s.uf != 8) return 7;
  s.uf &= 6;   if (s.uf != 0) return 8;   if (s.nb != 99) return 9;
  s.sc += -8;  if (s.sc != 7) return 10;  if (s.nb != 99) return 11;
  s.b -= 1;    if (s.b != 6) return 12;   if (s.a != 0) return 13;
  s.a = 3; s.a += 1;        if (s.a != -4) return 14;
  s.a = 3; if ((s.a |= -1) != -1) return 15;   /* expr value = stored */
  ps = &s; ps->nb |= 2; ps->a += 1;
  if (ps->nb != 99) return 16; if (ps->a != 0) return 17;
  m.x = 5; m.a = 2; m.b = 3; m.y = 77;
  m.a += 1; m.b |= 4;
  if (m.x != 5 || m.a != 3 || m.b != 7 || m.y != 77) return 18;
  sa.a = 3; sa.b = 5; sa.a += 1; sa.b |= 8;
  if (sa.a != -4 || sa.b != -3) return 19;
  return 0;
}
"""


def test_bf_compound_law_matrix():
    # RMW-on-unit law measured (bfc.O0.out): truncate to w bits + sign
    # read-back; neighbours intact; expression value = stored value.
    both_run(_BF_C, "bf_compound_matrix")


def test_bf_compound_neighbour_window():
    # fix-g1 instrument: the byte window around the RMW units matches gcc.
    # Truth bytes MEASURED from gcc 11.4 -O0 == -Os (probes/bfw.O0.out,
    # -36,-1,-1,-1, 11,0,0,0, 91,90,90,90, 12,0,0,0, ..., 7,0,0,0,
    # -1,-1,-1,127, 1,0,0,0, 43,43,43,43).
    both_run("""
struct S  { int a:3; int b:29; unsigned int uf:5; int nb; signed char sc:4; };
struct M  { int x; int a:31; int b:20; int y; };
char window[64];
struct S *gs; struct M *gm;
int main(void){
  int i; char *p;
  for (i = 0; i < 64; i++) window[i] = 0;
  gs = (struct S *)(window + 0);  gm = (struct M *)(window + 24);
  gs->a = 3; gs->b = -5; gs->uf = 31; gs->nb = 0x5A5A5A5A; gs->sc = -1;
  gm->x = 7; gm->a = -1; gm->b = -2; gm->y = 0x2B2B2B2B;
  gs->a += 1; gs->uf ^= 20; gs->nb |= 1; gs->sc -= 3;
  gm->a |= 1; gm->b += 3;
  p = window;
  if (p[0] != -36) return 1;     /* unit1: a=4|b:29 spill, b NEIGHBOUR */
  if (p[1] != -1 || p[2] != -1 || p[3] != -1) return 2;
  if (p[4] != 11) return 3;      /* uf ^= 20: 31^20 = 11 */
  if (p[8] != 91 || p[9] != 90 || p[10] != 90 || p[11] != 90) return 4;
  if (p[12] != 12) return 5;     /* sc: -1-3 -> 0xC in the unit */
  if (p[24] != 7) return 6;      /* gm->x NEIGHBOUR */
  if (p[28] != -1 || p[31] != 127) return 7;   /* a:31 |= 1 stays -1 */
  if (p[32] != 1) return 8;      /* b:20 -2+3 = 1 */
  if (p[36] != 43 || p[39] != 43) return 9;    /* gm->y NEIGHBOUR */
  return 0;
}
""", "bf_window")


def test_bf_compound_loud_shapes():
    # gcc-error shapes stay LOUD: bitwise on a bf lvalue with a POINTER
    # operand is invalid C (rc1 measured) — same §4 law as the sibling.
    loud("""
struct S { int a:3; };
int main(void){ struct S s; int arr[4]; int *p = arr; s.a &= p; return 0; }
""", "bf_ptr_and", "sema", "'&' with a pointer operand is not in the subset")
