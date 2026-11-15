# LINES reason: one wave of legs (M4 W2 — COMMIT-0 grammar unlock + fn-ptr
# VALUES, plan-m4 v4 §7 W2 row + AMENDMENT-2, MC 12545) — every leg is one
# posture pinned against the gcc oracle; splitting would separate legs from
# the law.
r"""M4 W2 — COMMIT-0 (_Bool, struct-member comma-lists, `long unsigned`)
+ fn-ptr VALUES, plan-m4.md v4 §7 W2 row, AMENDMENT-2 (W1 gate LEG 4,
MC 12544) and §2 R1/R8/R10/R11 (values only — INDIRECT CALLS are W3).

COMMIT-0 LAW (AMENDMENT-2, measured facts, W1 gate verdict §LEG 4):
 (a) `_Bool` is a C99 keyword type: sizeof == 1, PROMOTES to int in
     arithmetic (sizeof(b+1)==4), and every assignment normalizes to 0/1
     (gcc -Os emits `test*; setne` — measured, never assumed). It is its OWN
     type (types_compatible_p(_Bool, unsigned char) == 0). The kernel's
     first-blocker is the VERBATIM line include/linux/types.h:30
     `typedef _Bool bool;` — the one site behind ALL 689 kernel streams.
 (b) struct-member comma-lists: `struct list_head { struct list_head *next,
     *prev; };` — the ONE next shape behind _Bool for all 689. One
     declarator, comma, declarator, ';' — bitfield widths ride each member
     of the list; typedef-name members included. REUSES the declarator path
     (one mechanism, the same parse_declarator the single form rides).
 (c) small arm: specifier ORDER `long unsigned` / `long signed` / `long
     unsigned long` (stddef.h family — `#define __SIZE_TYPE__ long unsigned
     int`; host-tier carriers per §0.1, not kernel-blocking).
     Specifier words COMMOTE; the composed type is what the gcc facts pin.

W2 VALUES LAW (plan §2 rows for W2, §7 W2 row "values: &fn, designated/
table fills, NULL/0 cmp, fn↔void*/long"):
 a bare function name / `&fn` in a VALUE position yields the function's
 ADDRESS as an 8-byte scalar (R8/R1: no new mechanism — the symbol is a
 defined name, the value a normal 8-byte rvalue). The ORACLE EMISSION for
 the kernel recipe is `-fno-pic` (kernel Makefile KBUILD_CFLAGS law; the
 Ubuntu default -fPIC twin answers through the GOT and is NOT the §6
 universe — measured both, named here). -fno-pic -Os `gp = add;` emits
 `movq $add, gp(%rip)` (R_X86_64_32S — a DATA reference; PLT32 is only
 what `call add` emits — the brief's named gotcha, measured).
 NULL/0 comparisons ride the integer compare law (R10); fn↔void*/long
 CASTS are width-identical no-ops (R11) — and the abstract fn-ptr
 declarator `(int (*)(void))x` in CAST/§Generic-KEY position is exactly
 that cast's spelling, so it lands here too (the W1 pin flips same-commit,
 named). Table fills (positional + designated `[i] = fn`, `.m = fn`) are
 static ADDRESS CONSTANTS (data.py _const decay, T+10b law) — they land in
 the ORACLE'S SECTION (R/.rodata for const, .data/.bss otherwise) with
 exact nm/section parity (§6).
 STAY LOUD (W3): any CALL through a pointer-valued fn (`fp(x)`, `(*fp)(x)`,
 `tbl[i](x)`) and the 1g/1h twins.

Every leg: gcc 11.4 -std=gnu89 -Os oracle FIRST; blcc posture; RUN-PAIRS
(gcc-linked exe vs blcc-linked exe, same exit code) wherever a value,
offset or width is claimed — the oracle decides ALL semantics.
"""
import os
import re
import subprocess
import sys

import pytest

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
STREAMS = os.path.join(REPO, "..", ".tmp", "m4-plan", "streams")


def blcc(args):
    e = dict(os.environ, PYTHONPATH=REPO)
    return subprocess.run([sys.executable, "-m", "blcc"] + list(args),
                          capture_output=True, text=True, timeout=600,
                          cwd=REPO, env=e)


def gcc(args):
    return subprocess.run(["gcc", "-std=gnu89", "-Os"] + list(args),
                          capture_output=True, text=True, timeout=120)


def probe(tmp_path, tag, src, c_only=True):
    """gcc-oracle-first twin compile (W1 idiom): the oracle MUST accept
    valid C. Returns (gcc_res, blcc_res)."""
    s = tmp_path / (tag + ".c")
    s.write_text(src)
    go = tmp_path / (tag + ".gcc.o")
    gr = gcc(["-c", str(s), "-o", str(go)])
    bo = tmp_path / (tag + ".blcc.o")
    args = (["-c", str(s), "-o", str(bo)] if c_only
            else [str(s), "-o", str(bo)])
    br = blcc(args)
    return gr, br


def run_pair(tmp_path, tag, src, expect=None):
    """ORACLE-DECIDES: link both exes, run both, SAME exit code; if
    `expect` (0..255) is given, BOTH must answer it."""
    s = tmp_path / (tag + ".c")
    s.write_text(src)
    gx = tmp_path / (tag + ".gcc")
    gr = gcc([str(s), "-o", str(gx)])
    assert gr.returncode == 0, "oracle must build:\n" + gr.stderr
    bx = tmp_path / (tag + ".blcc")
    br = blcc([str(s), "-o", str(bx)])
    assert br.returncode == 0, "blcc must build:\n" + br.stderr
    g = subprocess.run([str(gx)], capture_output=True, text=True, timeout=30)
    b = subprocess.run([str(bx)], capture_output=True, text=True, timeout=30)
    assert g.returncode == b.returncode, \
        "run-pair diverge: gcc {} vs blcc {} on\n{}".format(
            g.returncode, b.returncode, src)
    if expect is not None:
        assert g.returncode == expect, \
            "oracle answers {}, leg expects {} on\n{}".format(
                g.returncode, expect, src)
    return g.returncode


# ============ COMMIT-0 arm (a): _Bool = the types.h:30 first-blocker ========

BOOL_FACTS = r"""
typedef _Bool bool;
"""

def test_bool_typedef_types_h30_verbatim(tmp_path):
    # include/linux/types.h:30 verbatim: `typedef _Bool bool;` — the ONE
    # site behind all 689 first-blockers. Oracle first, then blcc ACCEPTS.
    gr, br = probe(tmp_path, "b_typedef", BOOL_FACTS +
                   "struct h { bool a, b; };\n"
                   "int main(void){ struct h k; k.a = 2; return k.a; }\n")
    assert gr.returncode == 0, gr.stderr
    assert br.returncode == 0, br.stderr
    assert run_pair(tmp_path, "b_typedef_r", BOOL_FACTS +
                    "struct h { bool a, b; };\n"
                    "int main(void){ struct h k; k.a = 2; return k.a; }\n",
                    expect=1) == 1     # measured: k.a = 2 normalizes to 1


def test_bool_sizeof_is_one(tmp_path):
    # sizeof(_Bool)==1, sizeof(bool)==1, bool[3]==3 — MEASURED gcc fact;
    # the W1 gate's soft-accept-as-unsigned-char plant is SIZE-lucky, so
    # the rank/promotion legs below carry the rest of the law.
    src = ("typedef _Bool bool;\n"
           "int main(void){ bool arr[3]; _Bool *p;\n"
           "  return (int)(sizeof(_Bool) + sizeof(bool)*2"
           "    + sizeof arr*8 + sizeof p*64);\n  }\n")
    # 1 + 2 + 24 + 512 = 539; both exes exit 539 % 256 = 27 (measured).
    assert run_pair(tmp_path, "b_size", src, expect=539 % 256) == 27


def test_bool_promotes_to_int(tmp_path):
    # MEASURED: sizeof(b+1)==4, sizeof(b+(long)1)==8 (long wins),
    # sizeof(b+unsigned char)==4 (int after promotion), sizeof(b*2)==4.
    # An _Bool stored as `unsigned char` (the gate's plant) answers 1 for
    # sizeof(b+1) — this leg is what KILLS that plant.
    src = ("typedef _Bool bool;\n"
           "int main(void){ bool b = 0; unsigned char u = 0; long L = 0;\n"
           "  return (int)(sizeof(b+1) + sizeof(b+L)*2 + sizeof(b+u)*4);\n"
           "  }\n")   # 4 + 16 + 16 = 36
    assert run_pair(tmp_path, "b_promo", src, expect=4 + 16 + 16) == 36


def test_bool_assign_normalizes(tmp_path):
    # gcc -Os emits test*/setne (measured): EVERY _Bool assignment
    # normalizes to 0/1 — from long 0x100, from -1, from unsigned char
    # 200, and from a ternary producing 2. Exit = sum of the four bools.
    src = (
        "_Bool z;\n"
        "unsigned long f(unsigned long x){ z = x; return z; }\n"
        "int main(void){ _Bool a = 0x100; long m = -1; _Bool c;\n"
        "  unsigned char u = 200; _Bool d; int k = 1; unsigned char e = 3;\n"
        "  c = m; d = (k ? 2 : e);\n"
        "  return (int)(a + f(7) + c + d); }\n")     # 1+1+1+1 = 4
    assert run_pair(tmp_path, "b_norm", src, expect=4) == 4


def test_bool_static_global_init(tmp_path):
    # A static _Bool with initializer 7 normalizes at DATA time too
    # (oracle: the byte IS 1). Run reads it back through extern access.
    src = ("static _Bool gb = 7;\n"
           "_Bool get(void){ return gb; }\n"
           "int main(void){ return get() + get()*2; }\n")   # 1 + 2 = 3
    assert run_pair(tmp_path, "b_static", src, expect=3) == 3


def test_bool_not_unsigned_char_identity(tmp_path):
    # _Bool is its OWN type: __builtin_types_compatible_p folds measure
    # (_Bool, unsigned char) == 0, (_Bool, _Bool) == 1 (both gcc-measured).
    src = ("typedef _Bool bool;\n"
           "int main(void){ return (int)(1 * _Generic(0, int: 1, default: 0)"
           "  + (__builtin_types_compatible_p(_Bool, unsigned char) ? 0 : 2)"
           "  + (__builtin_types_compatible_p(_Bool, bool) ? 4 : 0)); }\n")
    assert run_pair(tmp_path, "b_ident", src, expect=1 + 2 + 4) == 7


def test_bool_member_and_bitfield_layout(tmp_path):
    # struct { bool f; char c; } — measured size 2, c at 1 (bool aligns 1);
    # `bool x:1` bitfield (measured gcc accepts, 1-BYTE unit, 3->1).
    src = ("typedef _Bool bool;\n"
           "struct K { bool f; char c; };\n"
           "struct BF { bool x:1; char pad; };\n"
           "int main(void){ struct K k; struct BF b; k.c = 2; b.x = 3;\n"
           "  return (int)(sizeof k*8 + b.x*4 + sizeof b); }\n")
    # measured facts: sizeof K == 2, BF sizeof == 2, b.x == 1
    assert run_pair(tmp_path, "b_layout", src,
                    expect=2 * 8 + 1 * 4 + 2) == 22


# ============ COMMIT-0 arm (b): struct-member comma-lists ===================

def test_member_comma_list_head_verbatim(tmp_path):
    # THE shape behind the 689 (W1 gate LEG 4 witness mm_vmstat:331):
    # struct list_head { struct list_head *next, *prev; };
    src = ("struct list_head { struct list_head *next, *prev; };\n"
           "int main(void){ struct list_head h; h.next = 0; h.prev = 0;\n"
           "  return (int)(sizeof h + (h.prev == h.next) * 16); }\n")
    assert run_pair(tmp_path, "cm_lh", src, expect=16 + 16) == 32


def test_member_comma_mixed_declarators(tmp_path):
    # ONE comma list mixing a pointer, an ARRAY and a plain member —
    # measured gcc layout: m=40 p@0 a@8 c@24 q@32.
    src = ("struct m { int *p, a[4]; char c, *q; };\n"
           "int main(void){ struct m *z = (struct m*)0;\n"
           "  return (int)(sizeof(struct m) + ((char*)&z->a - (char*)z)/8"
           "    + ((char*)&z->c - (char*)z)*2);\n  }\n")
    # 40 + 1 + 48 = 89
    assert run_pair(tmp_path, "cm_mix", src, expect=40 + 1 + 48) == 89


def test_member_comma_typedef_names(tmp_path):
    # typedef-name members in ONE comma list: `fp a, b;` and the
    # fn-TYPE-typedef star form `FT *f, *g;` — measured 16/0/8 each.
    src = ("typedef int (*fp)(void);\n"
           "typedef int FT(int);\n"
           "struct s { fp a, b; };\n"
           "struct t { FT *f, *g; };\n"
           "int main(void){ struct s *z = (struct s*)0;\n"
           "  struct t *w = (struct t*)0;\n"
           "  return (int)(sizeof(struct s) + ((char*)&z->b - (char*)z)*2\n"
           "    + ((char*)&w->g - (char*)w)); }\n")
    # 16 + 16 + 8 = 40
    assert run_pair(tmp_path, "cm_td", src, expect=16 + 8 * 2 + 8) == 40


def test_member_comma_bitfields_ride_each(tmp_path):
    # `unsigned a:3, b:5;` — the width applies to EACH declarator, and the
    # anonymous-bitfield form continues the list too (measured gcc: `int
    # :2, x:3;` rc 0, sizeof 4 (int unit), x holds).
    src = ("struct b2 { unsigned a:3, b:5; };\n"
           "struct e { int :2, x:3; };\n"
           "int main(void){ struct b2 v; struct e w; v.a = 5; v.b = 9;\n"
           "  w.x = 5;\n"
           "  return (int)(v.a*16 + v.b + sizeof w*16); }\n")
    # measured: a==5, b==9, sizeof(struct e)==4 -> 80 + 9 + 64 = 153
    assert run_pair(tmp_path, "cm_bf", src, expect=5 * 16 + 9 + 4 * 16) == 153


def test_member_comma_array_and_second_plain(tmp_path):
    # `int *first[2], second;` — pointer-to-ARRAY member then a plain one.
    # measured gcc: arr=24 first@0 second@16.
    src = ("struct arr { int *first[2], second; };\n"
           "int main(void){ struct arr *z = (struct arr*)0;\n"
           "  return (int)(sizeof(struct arr) + ((char*)&z->second - (char*)z)\n"
           "    * 2); }\n")     # 24 + 32 = 56
    assert run_pair(tmp_path, "cm_ar", src, expect=24 + 32) == 56


def test_member_comma_anonymous_dup_none(tmp_path):
    # tip FALSE-LOUD (found by recon, fixed in this commit): TWO anonymous
    # bitfields — `int :2; int :3;` — is gcc rc 0 (measured); the old
    # member-namespace slot collected None as a member NAME and the second
    # anonymous bitfield answered `duplicate member 'None'` (RED capture:
    # W1-snapshot `sema: duplicate member 'None'`). ANONYMOUS members
    # carry no name: None never enters the namespace. The measured sizeof
    # of `struct S { int :2; int :3; char c; }` is 2 BOTH sides (anonymous
    # bitfields contribute NO alignment — the int storage unit is 5 bits
    # of one byte here; run-pair pins it).
    src = ("struct S { int :2; int :3; char c; };\n"
           "int main(void){ return (int)sizeof(struct S); }\n")
    assert run_pair(tmp_path, "cm_anon", src, expect=2) == 2


def test_member_comma_file_scope_fn_protos(tmp_path):
    # The SAME comma law at FILE SCOPE with FUNCTION declarators (the
    # S20/S22 probe wall `int f1(int), f2(int);`): prototypes in one list
    # are valid C the corpus carries; direct calls must link.
    src = ("int f(int x), h(int y);\n"
           "int f(int x){ return x + 1; }\n"
           "int h(int y){ return y + 2; }\n"
           "int main(void){ return f(1) + h(2); }\n")   # 2 + 4 = 6
    assert run_pair(tmp_path, "cm_fn", src, expect=6) == 6


def test_member_comma_negatives_stay_loud(tmp_path):
    # The tail must stay honest: an EMPTY second declarator is a gcc ERROR
    # rc 1 — the blcc twin stays LOUD rc 2 (no silent member invented);
    # a duplicate name in the list is the measured duplicate-member ERROR.
    for tag, src in (
            ("cm_n1", "struct bad { int a, ; };\nint main(void){return 0;}\n"),
            ("cm_n2", "struct bad { int a, a; };\nint main(void){return 0;}\n"),
            ("cm_n3", "struct bad { int a, b( };\n"
                      "int main(void){return 0;}\n")):
        s = tmp_path / (tag + ".c")
        s.write_text(src)
        g = gcc(["-c", str(s), "-o", str(tmp_path / (tag + ".o"))])
        assert g.returncode != 0, "oracle must reject: " + tag
        b = blcc(["-c", str(s), "-o", str(tmp_path / (tag + ".b.o"))])
        assert b.returncode == 2, (tag, b.stderr)
        assert not (tmp_path / (tag + ".b.o")).exists()


# ============ COMMIT-0 arm (c): `long unsigned` specifier order =============

def test_long_unsigned_order_variants(tmp_path):
    # Specifier words COMMUTE (gcc gnu89, all measured this card):
    # `long unsigned int` == unsigned long (size 8, WRAPS: s-1 > s);
    # `long signed int` == int (-3 round-trips);
    # `long unsigned long` == unsigned long long (size 8, holds 7).
    src = ("typedef long unsigned int size_t2;\n"
           "typedef long signed int ssize_t2;\n"
           "int main(void){ size_t2 s = 0; ssize_t2 n = -3;\n"
           "  long unsigned long ull = 7;\n"
           "  return (int)(((s - 1) > s) + (n == -3) * 2"
           "    + sizeof(s) * 4 + (int)ull * 8); }\n")   # 1+2+32+56 = 91
    assert run_pair(tmp_path, "lu1", src, expect=1 + 2 + 32 + 56) == 91


def test_unsigned_fairness_unchanged(tmp_path):
    # FAIRNESS (green BEFORE and AFTER): the shipped spellings keep their
    # exact widths — `unsigned long`, `long long`, bare `unsigned`,
    # `unsigned long long` — the commutative rework must not move them.
    src = ("int main(void){ unsigned long a; long long b; unsigned c;\n"
           "  unsigned long long d;\n"
           "  return (int)(sizeof a + sizeof b*2 + sizeof c*4"
           "    + sizeof d*8); }\n")     # 8 + 16 + 16 + 64 = 104
    assert run_pair(tmp_path, "lu2", src, expect=104) == 104


# ============ COMMIT-0 corpus legs (kernel tier): the 689 fall =============

def _clean_i(path, tmp_path, tag):
    """m3/m4 corpus idiom: elide linemarkers, erase literal suffixes."""
    clean = tmp_path / (tag + ".c")
    su = re.compile(r"\b(0[xX][0-9a-fA-F]+|[0-9]+)[uU][lL]{0,2}\b")
    sr = re.compile(r"\b(0[xX][0-9a-fA-F]+|[0-9]+)[lL][uU][lL]?\b")
    sl = re.compile(r"\b(0[xX][0-9a-fA-F]+|[0-9]+)[lL]+\b")
    with open(path, encoding="utf-8", errors="replace") as fh, \
            open(clean, "w", encoding="utf-8") as out:
        for line in fh:
            if line.startswith("#"):
                continue
            out.write(sl.sub(r"\1", sr.sub(r"\1", su.sub(r"\1", line))))
    return clean


@pytest.mark.skipif(not (os.environ.get("KERNEL_510")
                         and os.path.isdir(STREAMS)),
                    reason="kernel tier + pinned streams corpus required")
@pytest.mark.parametrize("stream", [
    "arch_x86_boot_string.c.i",    # W1 gate LEG 4 witness #1 (types.h:30)
    "mm_vmstat.c.i",               # witness #2 + the list_head site 331
    "fs_buffer.c.i",               # witness #3
])
def test_corpus_bool_wall_is_dead(stream, tmp_path):
    # The 689-file uniform first-blocker `parse: expected a type, found
    # '_Bool'` at types.h:30 FALLS (AMENDMENT-2 close-leg): the stream may
    # still LOUD (the next wall is honest — fn-ptr value/call territory),
    # but the _Bool sentence must be GONE.
    clean = _clean_i(os.path.join(STREAMS, stream), tmp_path, "corpw2")
    r = blcc(["-c", str(clean), "-o", str(tmp_path / "corpw2.o")])
    assert "found '_Bool'" not in r.stderr, \
        "{} still hits the _Bool wall:\n{}".format(stream, r.stderr[:600])


# ============ W2 VALUES: fn-name decays to an 8-byte address rvalue ========

VAL_PRE = ("typedef int (*fp_t)(int);\n"
           "int add(int x){ return x + 1; }\n"
           "int sub(int x){ return x - 1; }\n")

def test_fn_value_battery_run_pair(tmp_path):
    # §2 R1: `gp = add;` (bare-name decay), fn-ptr == fn, != &add, the
    # NULL spellings 0/(void*)0, the bang, fn↔long and fn↔void* casts,
    # copy through a block-scope var, table slots. MEASURED answer 10.
    src = (VAL_PRE +
           "int takes(fp_t f){ return f == add; }\n"
           "fp_t gives(void){ return add; }\n"
           "fp_t tab[2] = { add, 0 };\n"
           "int main(void){ int r = 0; fp_t gp; gp = add;\n"
           "  r += (gp == add) + (gp != &add) + (gp != 0) + (gp != (void*)0)\n"
           "    + !gp + (gp == 0);\n"
           "  r += ((long)add == (long)gp) + ((void*)add == (void*)gp);\n"
           "  r += takes(add) + takes(gives()) + (gives() == add);\n"
           "  r += (tab[0] == add) + (tab[1] == 0);\n"
           "  return r; }\n")
    assert run_pair(tmp_path, "v_batt", src, expect=10) == 10


def test_fn_value_dynamic_run_pair(tmp_path):
    # Values NOT constant-foldable: fn-ptr returned through a Cond,
    # re-assigned to 0 mid-run, and the raw fn==fn / fn!=fn compares.
    # MEASURED oracle answer 8.
    src = (VAL_PRE +
           "fp_t pick(int k){ return k ? add : sub; }\n"
           "int main(void){ fp_t gp = pick(1); int r = 0;\n"
           "  r += (gp == add); r += (gp == &add); r += (gp != 0);\n"
           "  r += (gp != (void*)0); r += !gp; gp = 0; r += !gp;\n"
           "  r += (gp == 0); r += (add == add); r += (add != sub);\n"
           "  return r; }\n")
    assert run_pair(tmp_path, "v_dyn", src, expect=8) == 8


def test_fn_value_static_null(tmp_path):
    # A zero-initialised table slot and an uninitialised static compare
    # equal to 0 and (void*)0; the SET slot does not. MEASURED answer 5.
    src = (VAL_PRE +
           "fp_t gs;\nfp_t tab[2] = { add, 0 };\n"
           "int main(void){ return !gs + (gs == 0) + (gs == (void*)0)\n"
           "  + (tab[1] == 0) + (tab[0] == 0) + !!tab[0]; }\n")
    assert run_pair(tmp_path, "v_null", src, expect=5) == 5


def test_fn_addr_is_data_reference_not_plt(tmp_path):
    # THE GOTCHA (measured): the kernel recipe (-fno-pic -Os, plan §6's
    # universe) answers a fn-ADDRESS with an ABSOLUTE relocation —
    # R_X86_64_32/R_X86_64_32S on `mov/cmp $add` — a DATA reference.
    # PLT32 belongs to the direct-CALL arm ONLY; GOTPCREL is the
    # Ubuntu-DEFAULT -fPIC world, which is NOT §6's universe (measured
    # twin: gcc's own -fPIC object carries U _GLOBAL_OFFSET_TABLE_ —
    # asserting the PIC shape would contradict the kernel law).
    src = (VAL_PRE +
           "fp_t gp;\nint k;\n"
           "int main(int argc){ if (argc > 1) gp = add;\n"
           "  k = (gp == add); return k; }\n")
    s = tmp_path / "v_law.c"
    s.write_text(src)
    go = tmp_path / "v_law.gcc.o"
    gr = gcc(["-fno-pic", "-c", str(s), "-o", str(go)])
    assert gr.returncode == 0, gr.stderr
    bo = tmp_path / "v_law.blcc.o"
    br = blcc(["-c", str(s), "-o", str(bo)])
    assert br.returncode == 0, br.stderr
    for tag, obj in (("gcc", go), ("blcc", bo)):
        txt = subprocess.run(["objdump", "-dr", str(obj)],
                             capture_output=True, text=True).stdout
        assert "GOTPCREL" not in txt, \
            "{} fn-address rode a GOT load (§6 kernel universe: -fno-pic)".format(tag)
        assert re.search(r"R_X86_64_32S?\s+add\b", txt), \
            "{}: no ABSOLUTE fn-address reloc on add (data-reference law):\n{}".format(
                tag, txt[-600:])


def test_fn_cast_roundtrip(tmp_path):
    # §2 R11: fn↔void*/long casts are WIDTH-IDENTICAL no-ops — the
    # roundtrip `(fp_t)(long)add == add` holds; NULL-casts ride R10.
    # MEASURED answer: 4 terms all true.
    src = (VAL_PRE +
           "int main(void){ fp_t gp = (fp_t)(long)add;\n"
           "  return (gp == add) + ((long)(void*)add == (long)add)\n"
           "    + ((fp_t)(void*)0 == 0) + ((fp_t)0L == (void*)0); }\n")
    assert run_pair(tmp_path, "v_cast", src, expect=4) == 4


def test_fn_value_param_return_run_pair(tmp_path):
    # fn-ptr PARAM and RETURN carry the value law; `takes(add)` passes
    # the decayed address. MEASURED oracle answer 4.
    src = (VAL_PRE +
           "int takes(fp_t f){ return f == add; }\n"
           "fp_t gives(void){ return add; }\n"
           "int main(void){ return takes(add) * 2 + takes(gives())\n"
           "  + (gives() == add); }\n")
    assert run_pair(tmp_path, "v_argret", src, expect=4) == 4


def test_table_positional_designated(tmp_path):
    # Positional { add, 0 } AND designated { [1] = add, [0] = 0 } table
    # inits are ADDRESS CONSTANTS in data.py (the T+10b decay arm):
    # designated order cannot reorder the fills, unset slots stay 0.
    # MEASURED: des(=7) + tab(=3) legs.
    src = (VAL_PRE +
           "fp_t tab[2] = { add, 0 };\n"
           "fp_t des[3] = { [1] = add, [0] = 0 };\n"
           "int main(void){ return (des[1] == add) * 4 + (des[2] == 0) * 2\n"
           "  + (des[0] == 0) + (tab[0] == add) * 2 + (tab[1] == 0); }\n")
    assert run_pair(tmp_path, "v_tab", src, expect=10) == 10
