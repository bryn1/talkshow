# LINES reason: one wave (M4 W-U COMMIT-1, statement-expression-as-lvalue,
# card 12404.2.102): every leg is an arm of the ONE gcc `({...})`-as-lvalue
# law (L1-L5) measured as a table; splitting the refusals from the ships
# would let one arm of the table move without the row that bounds it.
r"""M4 W-U COMMIT-1 (MC 12739) — `({...})` as an lvalue: the law table.

THE gcc 11.4 -Os REC LAW (own hands, .tmp/m4-wu/shapes/a17..a26 + the W-U
sims' 22-row table, every row re-pinned here):
  L1 a TRANSPARENT group — one expression statement, empties and label
     wrappers allowed — IS a modifiable lvalue, through any nesting; it
     ALIASES the object its final expression names (no temp materializes).
  L2 any OTHER statement in the body (call, declaration, assignment,
     control flow, asm, `(void)` cast) kills lvalue-ness — LOUD, never a
     silent temp copy of a side-effecting body.
  L3 in VALUE / copy-SOURCE position (struct return, `->`, `[]` over a
     pointer-or-array final, `*` operand, plain read) the group answers
     its source address for ANY body — this is the 279-stream cmpxchg/
     `pmdp_establish` crowd that stopped init/main.o at tip.
  L4 a final expression that is not itself modifiable (`({1;})`, or no
     final at all) is never an lvalue — LOUD.
  L5 a VOLATILE-qualified final kills it — LOUD, even for a transparent
     body (`({ *(volatile int *)&v; }) += 5` is gcc rc1).

The gate lives where the CONTEXT is known (blcc/expr_parser.py
`_se_lvalue_law`, reached from `_check_lvalue` — assignment / `++--` / the
`.`-base chain — and from the unary `&`), and the address law where the
copy is (blcc/expr_codegen.py `_emit_addr` → `Codegen._se_run(as_addr)`).
This REPLACES: the tip's blunt `_LVALUE_KINDS` wall, which answered every
group with "cannot apply assignment to a non-l-value expression" (rows
a17/a18/a19/a21: gcc rc0, tip rc2), and the tip's sema "not an addressable
l-value" on a group that sits behind a `.`-select (a21/a22).

Named residual (instrument, not posture): an asm `+r`/`=r` OUTPUT whose
group operand is NON-transparent is refused only if the operand reaches
`_check_lvalue`; the sims' 22-row table has no such row and the corpus has
no such shape (volume 0), so it is listed, not gated.
"""
import os
import subprocess
import sys

import pytest

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.environ.get("BLCC_REPO") or os.path.dirname(HERE)
REC = ["-Os", "-mno-sse", "-mno-mmx", "-mno-80387", "-fno-stack-protector",
       "-fno-pic"]


def blcc(args):
    return subprocess.run([sys.executable, "-m", "blcc"] + args,
                          capture_output=True, text=True, cwd=REPO,
                          env={"PYTHONPATH": REPO, "PATH": "/usr/bin:/bin"})


def _src(tag, src):
    c = "/dev/shm/wu1_%s.c" % tag
    open(c, "w").write(src)
    return c


def _pair(tag, src):
    """gcc and blcc build the SAME source and must answer the SAME value —
    the aliasing rows are proved by VALUE, not by exit code."""
    c = _src(tag, src)
    g = subprocess.run(["gcc", "-std=gnu89"] + REC +
                       [c, "-no-pie", "-o", "/dev/shm/wu1_%s.g" % tag],
                       capture_output=True, text=True)
    assert g.returncode == 0, "law row must be valid C: " + g.stderr
    gex = subprocess.run(["/dev/shm/wu1_%s.g" % tag],
                         env={"PATH": "/usr/bin:/bin"}).returncode
    o = "/dev/shm/wu1_%s.o" % tag
    b = blcc(["-c", c, "-o", o])
    assert b.returncode == 0, "%s must COMPILE (L1/L3 ship arm): " % tag \
        + b.stderr
    assert subprocess.run(["gcc", "-no-pie", o, "-o",
                           "/dev/shm/wu1_%s.b" % tag],
                          capture_output=True).returncode == 0
    bex = subprocess.run(["/dev/shm/wu1_%s.b" % tag],
                         env={"PATH": "/usr/bin:/bin"}).returncode
    assert bex == gex, "%s run-pair: blcc=%d gcc=%d" % (tag, bex, gex)


def _loud(tag, src, needle):
    """gcc refuses the row; blcc must refuse it too, naming the class."""
    c = _src(tag, src)
    g = subprocess.run(["gcc", "-std=gnu89"] + REC + ["-c", c, "-o",
                                                      "/dev/null"],
                       capture_output=True, text=True)
    assert g.returncode != 0, "gcc must reject the law row: " + g.stderr
    b = blcc(["-c", c, "-o", "/dev/null"])
    assert b.returncode != 0, "%s must be LOUD (L2/L4/L5 arm): " % tag \
        + b.stderr
    assert needle in b.stderr, \
        "%s: refusal must name %r: " % (tag, needle) + b.stderr


# ---- L3: the crowd shapes (VERBATIM witnesses), multi-statement bodies --

def test_wu_l01_cmpxchg_return_is_copy_source():
    # THE 279-crowd shape: instrumented `pmdp_establish` return — a struct
    # value produced by a nested multi-statement group, copied out of the
    # group's own slots. tip: `sema: not an addressable l-value`.
    _pair("l01", """
typedef struct { unsigned long pmd; } pmd_t;
pmd_t est(pmd_t *pmdp, pmd_t pmd) {
 return ({ typeof(pmdp) __ai_ptr = (pmdp); ({ __typeof__(*(__ai_ptr)) __ret = ((pmd)); __ret; }); });
}
int main(void){ pmd_t p={7},q={0}; q.pmd=40; p=est(&p,q); return (int)(p.pmd+q.pmd-80); }
""")


def test_wu_l12_xchg_switch_macro_verbatim():
    # VERBATIM `__xchg` size-switch + instrumented establish, asm outputs
    # on locals and struct-valued groups in return: the wall line the
    # 279 streams stop at. Value proves the xchg ran (old=1, new=9).
    _pair("l12", """
typedef struct { unsigned long val; } pmd_t;
typedef unsigned char u8; typedef unsigned long u64;
static inline u8 x86_xchg8(volatile void *ptr, u8 val)
{ u8 old; __asm__ volatile("xchgb %b0, %1" : "=q" (old), "+m" (*(u8 *)ptr) : "0" (val) : "memory"); return old; }
static inline u64 x86_xchg64(volatile void *ptr, u64 val)
{ u64 old; __asm__ volatile("xchgq %q0, %1" : "=r" (old), "+m" (*(u64 *)ptr) : "0" (val) : "memory"); return old; }
#define __xchg(op, ptr, ...) \\
 ({ __typeof__(*(ptr)) __ret = (op); \\
   switch (sizeof(*(ptr))) { case 1: __ret = (typeof(__ret))x86_xchg8((void *)(ptr), (unsigned char)(op)); break; \\
     case 8: __ret = (typeof(__ret))x86_xchg64((void *)(ptr), (unsigned long)(op)); break; \\
     default: __ret = ({__ret;}); break; } \\
   __ret; })
typedef u64 pmdval_cast;
#define pmd_mval(v) ((pmd_t){ .val = (v) })
pmd_t pmdp_establish(pmd_t *pmdp, pmd_t pmd) {
 if (1) {
  return ({ typeof(pmdp) __ai_ptr = (pmdp); ({ __typeof__(*(__ai_ptr)) __ret = pmd_mval(__xchg(pmd.val, (pmdval_cast *)__ai_ptr, )); __ret; }); });
 } else { pmd_t old = *pmdp; *(volatile typeof(*pmdp) *)&(*pmdp) = (pmd); return old; }
}
int main(void){ pmd_t p={1}, q={9}, r; r = pmdp_establish(&p, q); return (int)(r.val+p.val-10); }
""")


def test_wu_l09_pagetail_address_of_arrow_member():
    # CORPUS VERBATIM class (`PageTail`/compound_head instrumentation):
    # `&(({…; ptr; })->flags)` — the `&(`-prefix that fills 581 streams.
    # L3: rvalue group + arrow + address-of; needs NO L1 transparency.
    _pair("l09", """
typedef struct page { unsigned long flags; int tail; } PAGE;
struct page *compound_head(struct page *p);
int test_bit(int n, const volatile unsigned long *a);
struct page *compound_head(struct page *p){ return p; }
int test_bit(int n, const volatile unsigned long *a){ return (int)((*a >> n) & 1); }
static inline int PageTail(struct page *page) { return test_bit(0, &({ ((void)(sizeof(( long)(0 && 0)))); ({ ((void)(sizeof(( long)(0)))); compound_head(page); }); })->flags); }
int main(void){ struct page p; p.flags = 2; p.tail=0; return PageTail(&p) + 0; }
""")


def test_wu_l08_two_struct_groups_distinct_temps():
    # L3 lifetime row: two struct-valued groups in ONE expression, field
    # reads off each — a shared temp would fold them (measured 6).
    _pair("l08", """
struct S{int a;int b;};
int main(void){ return (({ struct S s={1,2}; s; })).a + (({ struct S s={1,2}; s; })).b + 3; }
""")


def test_wu_l02_l13_rvalue_reads_stand():
    # L3 read class + the READ_ONCE/WRITE_ONCE family the crowd sits in:
    # posture pins — these were ALREADY quiet at tip and must stay PAIR.
    _pair("l02", "int x; int main(void){ x = ({ x = 4; x; }); return x + 1; }")
    _pair("l13", """
typedef unsigned long u64;
#define READ_ONCE(x) (*(volatile typeof(x) *)&(x))
#define WRITE_ONCE(x, val) do { *(volatile typeof(x) *)&(x) = (val); } while (0)
struct s { u64 a; u64 b; };
int main(void){ struct s v={1,2}; u64 t; WRITE_ONCE(v.a, 4); t = READ_ONCE(v.b) + READ_ONCE(v.a); return (int)(t - 6); }
""")


# ---- L1: transparent bodies ARE lvalues (the ship arm) ------------------

def test_wu_l03_transparent_assign_compound_dec():
    # all three operator classes on transparent finals (ident, deref, and
    # the `;`-prefixed empty statement) — compound-assign row included.
    _pair("l03", "int main(void){ int v=0; int *p=&v; ({ v; }) = 5; "
          "({ *p; }) += 2; ({ ; *p; })--; return v-6; }")


def test_wu_l04_transparency_through_nesting():
    # L1 recurses: a transparent group whose final is itself a transparent
    # group. An outward-only gate would refuse the outer one.
    _pair("l04", "int main(void){ int v=0; (({ ({ v; }); })) = 9; "
          "(({ ({ ({ v; }); }); })) += 1; return v-10; }")


def test_wu_l10_two_group_lvalues_one_expression():
    # LIFETIME RUN-PAIR: two group lvalues, two objects, ONE expression —
    # a shared/early-freed group slot shows up as a != 3 (the corruption
    # the W-U guard shapes plant). Proved by value.
    _pair("l10", "int main(void){ int a=1,b=2; int *p=&a,*q=&b; "
          "int r = (({*p;}) = 3) + (({*q;}) = 4); (void)r; "
          "return a+b-4; }")


def test_wu_l11_group_lvalue_in_for_init_control_incr():
    # for-init, control and increment all through groups on one object.
    _pair("l11", "int main(void){ int s=0; for (({s;}) = 100; ({s;}) < 103; "
          "({s;})++) { } return s-103; }")


def test_wu_l15_address_of_transparent_group_aliases():
    # `&({v;})` IS `&v`: writing through the pointer is visible in v.
    _pair("l15", "int main(void){ int v=1; int *p = &({ v; }); *p += 4; "
          "return v-5; }")


def test_wu_l16_asm_output_through_transparent_group():
    # `+r` output operand on a group (gcc takes the aliased object's
    # address); the value round-trips through the group.
    _pair("l16", "int main(void){ int v=7; __asm__ volatile(\"\" : \"+r\" "
          "(({ v; }))); v+=1; return v-8; }")


def test_wu_a17_group_lvalue_of_a_global():
    # OWN row (a17): the final names a GLOBAL — the statics/globals arms
    # of `_emit_addr` must answer the object, not a copy (gcc rc0, 0).
    _pair("a17", "int x; int main(void){ int *p; ({ x; }) = 5; "
          "p = &({ x; }); *p += 2; return x-7; }")


def test_wu_a18_group_on_both_sides_of_compound_assign():
    # OWN row (a18): `(({a;}) += ({b;}))` — source AND target are groups
    # in one expression (two live group slots; gcc rc0, 0).
    _pair("a18", "int main(void){ int a=1,b=2; (({a;}) += ({b;})); "
          "(({a;}) -= 1); return a-2; }")


def test_wu_a19_group_lvalue_with_index_final():
    # OWN row (a19): an Index final inside the group is an lvalue final.
    _pair("a19", "int main(void){ int arr[3]={1,2,3}; ({ arr[1]; }) = 7; "
          "({ arr[2]; }) += 1; return arr[1]+arr[2]-11; }")


def test_wu_a21_dot_select_of_transparent_group():
    # OWN row (a21): `(({g;}).a) = 4` — the `.` base is a transparent
    # group. tip died at sema "not an addressable l-value"; gcc rc0, 5.
    _pair("a21", "struct S{int a;int b;}; struct S g; "
          "int main(void){ (({g;}).a) = 4; return (({g;}).a) + 1; }")


def test_wu_a23_a24_a25_a26_arrow_index_deref_of_any_group():
    # OWN rows (L3, measured gcc rc0 4/4/4/9): `->` over a pointer-valued
    # group, `[]` over a pointer- OR array-valued group, `*` over a
    # pointer-valued group — all legal with a NON-transparent body; the
    # gate must NOT reach these (they are rvalue-position uses).
    _pair("a23", "struct S{int a;int b;}; struct S g; int f(void){return 0;} "
          "int main(void){ struct S *p=&g; (({ f(); p; })->a) = 4; "
          "return g.a; }")
    _pair("a24", "int arr[3]; int f(void){return 0;} "
          "int main(void){ (({ f(); arr; })[1]) = 4; return arr[1]; }")
    _pair("a25", "int arr[3]; int f(void){return 0;} int *fp(void){return arr;} "
          "int main(void){ (({ f(); fp(); })[1]) = 4; return arr[1]; }")
    _pair("a26", "int arr[3]; int f(void){return 0;} int *fp(void){return arr;} "
          "int main(void){ *({ f(); fp(); }) = 9; return arr[0]; }")


# ---- L2 / L4 / L5: the refusal arms (REFUSE-LOUD, never a temp copy) ---

def test_wu_l05_nontransparent_body_refused():
    # L2 with a CALL statement in the body. THE named sim-stub overpredict
    # row: the stub shipped it; gcc LOUDs — the gate is the law, not the
    # stub. RED-tooth: deleting the gate turns this leg green-and-wrong.
    _loud("l05", "int cnt; int f(void){cnt++;return 0;}\n"
          "int main(void){ int v=1; ({ f(); v; }) = 4; return v+cnt; }",
          "lvalue required")


def test_wu_l14d_address_of_nontransparent_body_refused():
    # L2 through unary `&` (gcc "lvalue required as unary '&' operand").
    _loud("l14d", "int cnt; int f(void){cnt++;return 0;}\n"
          "int main(void){ int v=1; int *p = &({ f(); v; }); (void)p; "
          "return v; }", "lvalue required")


def test_wu_a22_dot_select_of_nontransparent_body_refused():
    # OWN row (a22): the `.`-base chain carries the law too — a
    # non-transparent group under `.a` is not an lvalue (gcc LOUD).
    _loud("a22", "struct S{int a;int b;}; struct S g; int f(void){return 0;}\n"
          "int main(void){ (({ f(); g; }).a) = 4; return g.a; }",
          "lvalue required")


def test_wu_l05b_declaration_statement_refused():
    # L2 with a DECLARATION in the body (the `__ai_ptr` idiom shape — it
    # stays legal in COPY-SOURCE position, row l01; only as an lvalue is
    # it refused).
    _loud("l05b", "int main(void){ int v=1; ({ int a=2; v; }) = 4; "
          "return v; }", "lvalue required")


def test_wu_l07_volatile_final_refused():
    # L5: a volatile-qualified final kills the lvalue EVEN with a
    # transparent body (gcc rc1). The volatile refusal pair for the
    # non-volatile twin below.
    _loud("l07", "int main(void){ volatile int v=10; "
          "({ *(volatile int *)&v; }) += 5; return v-15; }",
          "volatile")


def test_wu_l07b_nonvolatile_cast_final_ships():
    # The other half of the pair: the same shape WITHOUT volatile ships
    # and PAIRS (value 15) — proves the refusal is the qualifier, not the
    # cast-deref form.
    _pair("l07b", "int main(void){ int v=10; ({ *(int *)&v; }) += 5; "
          "return v-15; }")


def test_wu_l14_rvalue_final_refused_three_ways():
    # L4: assign, `++`, and `&` on an rvalue final (`({1;})`) — three
    # refusals, one law; plus the no-final group `({;})` which gcc calls
    # "invalid use of void expression".
    _loud("l14", "int main(void){ ({ 1; }) = 2; return 0; }", "lvalue required")
    _loud("l14b", "int main(void){ ({ 1; })++; return 0; }", "lvalue required")
    _loud("l14c", "int main(void){ int *p = &({ 1; }); (void)p; return 0; }",
          "lvalue required")
    _loud("a20", "int main(void){ int v=0; ({ ; }) = 1; return v; }",
          "lvalue required")


def test_wu_l06_conditional_wrapper_still_refused():
    # the `?:` wrapper is NOT an lvalue in C and must stay refused on BOTH
    # sides — posture pin on the SHIPPED generic gate: the conditional is
    # not a group, so it keeps the tip's sentence (my law covers `&({1;})`
    # at tip too, and blcc's wording differs from gcc's — the pair is
    # rc!=0 on both sides, the message is blcc's own).
    _loud("l06", "int main(void){ int a=1,b=2; int *p=&a,*q=&b; "
          "(p ? ({*p;}) : ({*q;}) ) = 5; return a+b+3; }", "non-l-value")


# ---- cost posture: the corpus class the gate must NOT touch ------------

def test_wu_l17_scoped_label_rows_unmoved():
    # Cross-commit pin: the F-G3 label rows (COMMIT-0) still hold at these
    # bytes — the value-chain walk in `_collect_labels` and the group
    # lvalue gate must not move a label-scoping refusal.
    _loud("l17", "int main(){int r=1; __label__ h; if(({ __label__ h; "
          "({ r+=2; if(r<9) goto h; 0; }); })) r+=0; r+=40; h: return r+50;}",
          "used but not defined")
