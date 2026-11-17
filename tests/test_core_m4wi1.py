# LINES reason: one wave of legs (M4 W-I COMMIT-1 — the ATTRIBUTE-BETWEEN-
# * FAMILY parse arms; the measured law table is the contract and lives
# WITH its legs; splitting would separate the positions from the one
# declarator-walk mechanism that answers them all).
"""M4 W-I COMMIT-1 (MC 12650) — attributes BETWEEN `*` and the declarator.

THE WALL (measured at tip 1aaa558, .tmp/m4-wi/out/wall-tip.jsonl over the
pinned 706-stream corpus): 574 streams first-block at percpu.h:105:33
`expected an identifier, found '__attribute__'` — the shape
    extern struct pcpu_alloc_info * __init pcpu_alloc_alloc_info(...)
whose `__init` expands (in the preprocessed stream) to
`* __attribute__((__section__(".init.text"))) __attribute__((__cold__))`.
A corpus-wide classifier (.tmp/m4-wi census, all 706 streams) counts
2369 `* <attr>` sites in 604 files — EVERY one at the LAST-STAR (entity)
position; the between-star count is ZERO. The shipped M2/W2.5 skips visit
the specifier, between-type and declarator-tail positions only — the
pointer section of the declarator (`*` and what interleaves around it)
is the one position the ONE walk (_declarator_walk) never skips.

THE MEASURED LAW (gcc 11.4 -std=gnu89, probes .tmp/m4-wi/probes/
p1..r22; every leg below cites its row):

  P1 LAST-STAR — attr run after the FINAL `*`, before the declarator
     name / group: attaches to the ENTITY declared (like the spec and
     tail positions the W2.5 sink already serves):
       `int * __section__(".init.text") f(void){...}`  rc0 → asm
         `.section .init.text,"ax",@progbits` + f inside it
       `char * __section__(".sd") o = 0;`              rc0 → `.sd,"aw"`
       `char * __aligned__(16) o = 0;`                 rc0 → `.align 16`
       `char * __section__(".pa") a[4];`               rc0 → `.pa,"aw"`
       markers (used/unused/cold/no_instrument_function/notrace) rc0,
         emit NOTHING (f3 stays in .text, p3v in .bss — measured).
       Multiple attrs interleave (`* __section__(..) __cold __nif(`,
       the verbatim corpus form) and line breaks (the multiline
       extern shape) — all rc0.
  P2 LAST-STAR inside a paren group `(* __attr name)` — same law: the
     entity is raised (`int (* __aligned__(16) fp)(void)` → `.align 16`,
     probe r14).
  P3 TYPE POSITIONS — an attr run FOLLOWED by another `*`, by a group
     `(` whose interior opens with `*`, or sitting INSIDE the group
     before its `*`, attaches to the POINTER TYPE (probe r1/r2/r9):
       markers      rc0, "does not apply to types" warning class — the
                    effect is nothing; blcc PARSES AND DROPS.
       `section`    rc0 + warning, NO section emitted anywhere (r2 a6
                    stays .bss) — blcc drops too (no-sink posture, the
                    same shape W2.5 fixed for the cast position).
       `aligned`    rc0, NO effect on the entity (a2 stays `.align 8`;
                    the struct C row stays align 8, probe r7/r8) — the
                    TYPE align is unspellable without a typedef; blcc
                    keeps the W2.5 layout-class LOUD wall here
                    (LOUD-DIV twin, corpus volume 0 measured).
  P4 FORBIDDEN ENTITY POSITIONS (gcc rc1 twins, sentences mirrored):
       struct member  `section attribute not allowed for 'm'`   (r16)
       parameter      `section attribute not allowed for 'q'`   (r12)
       typedef name   `section attribute not allowed for 'td'`  (p2)
       `char * o __attr [2]` — attr between the NAME and `[` is a
                    SYNTAX error in gnu89 (r21) — no arm ships.
  P5 `weak` between the stars is a MARKER (parse, drop; the nm letter
     V-vs-B divergence rides the shipped W2.5 marker law — named leg).
  P6 spec position (before the FIRST `*`) with pointer declarators is
     entity-attaching — ALREADY SHIPPED (r11 y1/y2/y3 raise/land);
     this file pins it does not regress under the new walk.
  P7 typedef-rail `aligned` stays the shipped LOUD-DIV (the guid_t law,
     W2.5b) — the new position must not smuggle it into acceptance.

DUAL-SECTION conflict and the section/aligned EMISSION and SECTION-
parity legs ride COMMIT-2 (test_core_m4wi2.py).
"""
import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.environ.get("BLCC_REPO") or os.path.dirname(HERE)


def blcc(args):
    return subprocess.run([sys.executable, "-m", "blcc"] + args,
                          capture_output=True, text=True, cwd=REPO,
                          env={"PYTHONPATH": REPO, "PATH": "/usr/bin:/bin"})


def _compile(tmp_path, tag, src):
    s = tmp_path / (tag + ".c")
    s.write_text(src)
    return blcc(["-c", str(s), "-o", str(tmp_path / (tag + ".o"))])


def _gcc_rc(tmp_path, tag, src):
    s = tmp_path / (tag + ".c")
    s.write_text(src)
    return subprocess.run(["gcc", "-std=gnu89", "-Os", "-c", str(s),
                           "-o", str(tmp_path / (tag + ".g.o"))],
                          capture_output=True, text=True)


def _ok(tmp_path, tag, src):
    """Measured-gcc-rc0 arm: blcc must compile it clean too."""
    g = _gcc_rc(tmp_path, tag, src)
    assert g.returncode == 0, "gcc twin must rc0:\n" + src + g.stderr
    r = _compile(tmp_path, tag, src)
    assert r.returncode == 0, "blcc must ACCEPT (measured gcc rc0):\n" \
        + src + "\n" + r.stderr
    return r


def _loud(tmp_path, tag, src, needle=None, gcc_rc=None):
    g = _gcc_rc(tmp_path, tag, src)
    if gcc_rc is not None:
        assert g.returncode == gcc_rc, "gcc rc{} expected:\n{}".format(
            gcc_rc, g.stderr)
    r = _compile(tmp_path, tag, src)
    assert r.returncode != 0, "must LOUD:\n" + src + g.stderr
    if needle is not None:
        # needle matches the DIAGNOSTIC only — the tmp dir name can
        # carry the test's own words (this instrument's self-fix, the
        # RED-capture caught `aligned` matching the DIRECTORY name).
        diag = r.stderr.replace(str(tmp_path), "")
        assert needle in diag, r.stderr
    return r


# --------------------------------------------------- the witness itself

def test_wi_percpu_star_init_extern_accepted(tmp_path):
    # THE percpu.h:105 witness (preprocessed shape, verbatim stream form:
    # `* __init` → `* __section__(".init.text") __cold`). 574 streams
    # first-block right here at col 33.
    _ok(tmp_path, "wi_percpu",
        "struct pcpu_alloc_info;\n"
        "extern struct pcpu_alloc_info * __attribute__((__section__("
        "\".init.text\"))) __attribute__((__cold__)) pcpu_alloc_alloc_info"
        "(int nr_groups,\n\t\t\t\t\t\t     int nr_units);\n")


def test_wi_multiline_attr_chain_accepted(tmp_path):
    # the `other:` census class: attrs interleaved across LINES
    # (`struct uart_port * __section__(..) \n __cold \n name(...)`).
    _ok(tmp_path, "wi_multi",
        "struct uart_port;\n"
        "extern struct uart_port * __attribute__((__section__(\".init."
        "text\")))\n__attribute__((__cold__))\nserial_core_register_port"
        "(void);\n")


# ----------------------------------------------- P1 last-star entity arms

def test_wi_fn_def_star_section_accepted(tmp_path):
    _ok(tmp_path, "wi_fnsec",
        "struct X { int x; };\n"
        "struct X * __attribute__((__section__(\".init.text\")))"
        " f1(void) { return 0; }\n")


def test_wi_obj_star_section_accepted(tmp_path):
    _ok(tmp_path, "wi_objsec",
        "char * __attribute__((__section__(\".sd\"))) o2 = 0;\n")


def test_wi_array_star_section_accepted(tmp_path):
    _ok(tmp_path, "wi_arrsec",
        "char * __attribute__((__section__(\".pa\"))) o3[4];\n")


def test_wi_obj_star_markers_accepted(tmp_path):
    # marker class (used/unused): rc0, nothing emitted (probe p1 f3/p3v).
    _ok(tmp_path, "wi_objmark",
        "char * __attribute__((used)) o4 = 0;\n"
        "int * __attribute__((unused)) o5 = 0;\n")


def test_wi_fn_star_marker_chain_accepted(tmp_path):
    # the verbatim alloc_pages_exact_nid shape: section+cold+nif chain.
    _ok(tmp_path, "wi_chain",
        "void * __attribute__((__section__(\".meminit.text\"))) "
        "__attribute__((__cold__)) __attribute__((no_instrument_function))"
        " alloc_pages_exact_nid(int nid);\n")


def test_wi_qualifier_interleave_accepted(tmp_path):
    # `* <attr> volatile name` and `* volatile <attr> name` — qualifiers
    # and attrs interleave freely around the final star (both rc0).
    _ok(tmp_path, "wi_qual",
        "char * __attribute__((used)) volatile q1 = 0;\n"
        "char * volatile __attribute__((used)) q2 = 0;\n")


def test_wi_ptr_to_const_star_section_accepted(tmp_path):
    # the ptr-to-const star: `const char * __section__(...) s`.
    _ok(tmp_path, "wi_pc",
        "const char __attribute__((__section__(\".pc\"))) * s1 = 0;\n"
        "const char * __attribute__((__section__(\".pc2\"))) s2 = 0;\n")


def test_wi_spec_position_pointer_declarator_unregressed(tmp_path):
    # P6: the ALREADY-SHIPPED spec-position law with pointer declarators
    # must survive the new walk (r11: entity raises/lands through stars).
    _ok(tmp_path, "wi_spec",
        "char __attribute__((__section__(\".sy\"))) * y2 = 0;\n"
        "int v6;\nint main(void){ return (int)(v6 == 0); }\n")
    o = tmp_path / "wi_spec.o"
    asm = blcc([str(tmp_path / "wi_spec.c"), "--emit-asm", "-o", str(o)])
    assert asm.returncode == 0, asm.stderr
    with open(str(o) + ".s") as fh:        # the shipped §6 idiom
        txt = fh.read()
    assert ".section .sy" in txt, txt[:400]


# ------------------------------------- P2 group-interior entity position

def test_wi_group_star_entity_attr_accepted(tmp_path):
    # `int (* __aligned__(16) fp)(void)` — raises the OBJECT (r14:
    # `.align 16`); COMMIT-2 pins the emission, here the PARSE.
    _ok(tmp_path, "wi_grp",
        "int (* __attribute__((aligned(16))) fp1)(void) = 0;\n")


def test_wi_group_before_star_marker_dropped(tmp_path):
    # `int (__unused__ * fp)(void)` — TYPE position, marker: rc0 drop
    # (r9 p2d).
    _ok(tmp_path, "wi_grpm",
        "int (__attribute__((unused)) * fp2)(void) = 0;\n")


def test_wi_outer_star_group_marker_dropped(tmp_path):
    # `int * __used__ (*fp)(void)` — the outer star is followed by a
    # group opening with `*`: TYPE position, marker rc0 drop (r20).
    _ok(tmp_path, "wi_osg",
        "int * __attribute__((used)) (*fp3)(void) = 0;\n")


# -------------------------------------------------- P3 type-position law

def test_wi_between_star_markers_dropped(tmp_path):
    # `char * __used__ * p` — rc0 both sides (matrix multi-star row).
    _ok(tmp_path, "wi_btm",
        "char * __attribute__((used)) * b1 = 0;\n")


def test_wi_between_star_section_dropped(tmp_path):
    # `char * __section__(".sd") * p` — gcc rc0 + "does not apply to
    # types" warning, NO section emitted (r2 a6 stays .bss): blcc drops
    # the same (no-sink posture). The no-section EMISSION leg rides
    # COMMIT-2 (objdump parity).
    _ok(tmp_path, "wi_bts",
        "char * __attribute__((__section__(\".sd\"))) * b2 = 0;\n")


def test_wi_between_star_aligned_loud_twin(tmp_path):
    # LOUD-DIV twin (volume 0 measured): gcc rc0 (aligns the POINTER
    # TYPE, unspellable effect); blcc keeps the layout-class wall — the
    # W2.5 cast-position posture, never a silent strip.
    _loud(tmp_path, "wi_bta",
          "char * __attribute__((aligned(16))) * b3 = 0;\n",
          needle="aligned", gcc_rc=0)


def test_wi_cast_star_tail_loud_twin(tmp_path):
    # `sizeof(int * __aligned__(8))` — TYPE position inside a cast/
    # sizeof type (rc0+warning gcc; blcc LOUD layout wall, volume 0).
    _loud(tmp_path, "wi_ct",
          "int z3 = sizeof(int * __attribute__((aligned(8))));\n",
          needle="aligned", gcc_rc=0)


# -------------------------------------- P4 forbidden entity-position law

def test_wi_member_star_section_loud(tmp_path):
    # gcc rc1: "section attribute not allowed for 'm'" (r16).
    _loud(tmp_path, "wi_memsec",
          "struct S16 { char * __attribute__((__section__(\".mem\")))"
          " m; };\n", needle="not allowed", gcc_rc=1)


def test_wi_param_star_section_loud(tmp_path):
    # gcc rc1: "section attribute not allowed for 'q'" (r12).
    _loud(tmp_path, "wi_parsec",
          "int f15(int * __attribute__((__section__(\".sp\"))) q)"
          " { return 0; }\n", needle="not allowed", gcc_rc=1)


def test_wi_typedef_star_section_loud(tmp_path):
    # gcc rc1: "section attribute not allowed for 'td17'" (p2).
    _loud(tmp_path, "wi_tdsec",
          "typedef int * __attribute__((__section__(\".x\"))) td17;\n"
          "td17 o17 = 0;\n", needle="not allowed", gcc_rc=1)


def test_wi_name_before_bracket_attr_loud(tmp_path):
    # `char * o __attr [2]` is a gnu89 SYNTAX error (r21 rc1) — no arm
    # ships; blcc must LOUD, never accept a different reading.
    _loud(tmp_path, "wi_nbb",
          "char * o14 __attribute__((aligned(8))) [2] = {0, 0};\n",
          gcc_rc=1)


def test_wi_typedef_star_aligned_stays_loud_div(tmp_path):
    # P7: the W2.5b guid_t law — a layout attr on a typedef of a
    # NON-struct type stays LOUD-DIV (volume 0, measured). The new
    # star-position arm must not smuggle it into acceptance.
    _loud(tmp_path, "wi_tdal",
          "typedef char * __attribute__((aligned(16))) td16;\n"
          "td16 o16 = 0;\n", needle="LOUD-DIV", gcc_rc=0)


# ------------------------------------------------- controls (green both)

def test_wi_param_star_markers_accepted(tmp_path):
    _ok(tmp_path, "wi_pm",
        "int f14(int * __attribute__((unused)) q) { return *q; }\n")


def test_wi_param_star_aligned_accepted(tmp_path):
    # param TYPE-position aligned: gcc rc0 no-op (r13) — blcc parses
    # and drops (params have no emitted storage to raise).
    _ok(tmp_path, "wi_pa",
        "int f16(int * __attribute__((aligned(16))) q) { return *q; }\n")


def test_wi_member_star_aligned_accepted(tmp_path):
    # member last-star aligned parses rc0 (the RAISE itself is the
    # already-shipped W2.5 member law; the offset pair rides COMMIT-2).
    _ok(tmp_path, "wi_ma",
        "struct S13 { char * __attribute__((aligned(16))) m;"
        " char * after; };\n"
        "unsigned x13;\nvoid f(void){ x13 = 1; }\n")


def test_wi_weak_star_marker_accepted(tmp_path):
    # P5: `weak` at the star position parses and drops (the nm letter
    # V-vs-B divergence rides the shipped marker law; its named pair
    # leg lives in COMMIT-2).
    _ok(tmp_path, "wi_weak",
        "int * __attribute__((__weak__)) z4 = 0;\n")


def test_wi_plain_forms_control(tmp_path):
    # the shipped positions stay byte-familiar (control).
    _ok(tmp_path, "wi_ctrl",
        "int plain = 41;\n"
        "int *pn = &plain;\n"
        "int * __attribute__((unused)) *ppn = &pn;\n"
        "int main(void){ return *pn - 41; }\n")
