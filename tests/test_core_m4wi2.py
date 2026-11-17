# LINES reason: one wave of legs (M4 W-I COMMIT-2 — the ATTACH + EMIT
# half of the attribute-between-* family: nm/objdump SECTION parity per
# family member, the dual-section conflict law, and the corpus witness
# legs; the parse positions and their law table live in
# test_core_m4wi1.py, the corpus wall guard in test_core_m4w25b.py).
"""M4 W-I COMMIT-2 (MC 12650) — attach + EMIT per the measured table.

The parse arm (COMMIT-1) routes the FINAL attr run — the one between
the last `*` and the declarator — into the SAME W2.5 sink the spec and
tail positions feed, so the shipped placement law acts here unchanged.
What this file proves is the EMISSION side of the DoD: for every family
member, WHICH attrs EMIT a .section in the oracle asm and which are
markers emitting NOTHING — and that neither side is silent.

  MEASURED EMISSION TABLE (gcc 11.4 -std=gnu89 -Os; probes
  .tmp/m4-wi/probes/ p1/r2/r18, all cross-checked at this tree):
    section(".X") @ entity position (fn)  → `.section .X,"ax",@progbits`
                                            + the symbol lands in .X
    section(".X") @ entity position (obj) → `.section .X,"aw"` + symbol
                                            in .X (array too, r2 a9)
    aligned(N)    @ entity position       → `.align max(N,8)`; the
                                            linked address honors %N
    markers (used/unused/cold/notrace/
    no_instrument_function)               → emit NOTHING (f3 stays in
                                            .text, p3v in .bss) — parse,
                                            attach to nothing, silent
                                            BY MEASUREMENT (no section
                                            exists to lose)
    weak                                  → nm letter V vs blcc B: the
                                            shipped W2.5 marker-drop
                                            divergence, NAMED below
    TYPE-position section (between stars) → "does not apply to types"
                                            warning, NO section emitted
                                            anywhere (r2 a6 in .bss) —
                                            blcc's drop is the OBSERVED
                                            behavior, pinned pair-clean
    TWO DIFFERENT sections on one
    declarator                            → gcc rc1 "section of 'f19'
                                            conflicts with previous
                                            declaration"; the same name
                                            twice is rc0 (probe dq) —
                                            blcc LOUD twin, never a
                                            silent pick-one.
"""
import os
import subprocess
import sys

import pytest

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.environ.get("BLCC_REPO") or os.path.dirname(HERE)
STREAMS = os.path.join(REPO, "..", ".tmp", "m4-plan", "streams")
sys.path.insert(0, HERE)
from test_core_m4w25b import _clean_i          # noqa: E402  (SHIPPED)


def blcc(args):
    return subprocess.run([sys.executable, "-m", "blcc"] + args,
                          capture_output=True, text=True, cwd=REPO,
                          env={"PYTHONPATH": REPO, "PATH": "/usr/bin:/bin"})


def gcc(args):
    return subprocess.run(["gcc", "-std=gnu89", "-Os"] + args,
                          capture_output=True, text=True)


def _compile(tmp_path, tag, src):
    s = tmp_path / (tag + ".c")
    s.write_text(src)
    return s, blcc(["-c", str(s), "-o", str(tmp_path / (tag + ".o"))])


def _objdump_sections(path):
    out = subprocess.run(["objdump", "-t", path],
                         capture_output=True, text=True).stdout
    secs = {}
    for ln in out.splitlines():
        f = ln.split()
        # '... g   F .init.text  size name' / 'g  .sy  size name'
        if len(f) in (5, 6) and (f[1].startswith("g")
                                 or f[1].startswith("l")):
            secs[f[-1]] = f[2] if len(f) == 5 else f[3]
    return secs


def _section_pair(tmp_path, tag, src, expect):
    """expect: {symbol: section} — objdump -t on BOTH objects."""
    s, b = _compile(tmp_path, tag, src)
    assert b.returncode == 0, "blcc must compile:\n" + b.stderr
    g = gcc(["-c", str(s), "-o", str(tmp_path / (tag + ".g.o"))])
    assert g.returncode == 0, "gcc twin must compile:\n" + g.stderr
    bs = _objdump_sections(str(tmp_path / (tag + ".o")))
    gs = _objdump_sections(str(tmp_path / (tag + ".g.o")))
    for sym, sec in expect.items():
        assert bs.get(sym) == sec, \
            "blcc {} in {!r}, want {!r}".format(sym, bs.get(sym), sec)
        assert gs.get(sym) == sec, \
            "gcc {} in {!r}, want {!r}".format(sym, gs.get(sym), sec)


# ------------------------------------------- the EMIT class: .section

def test_wi_fn_star_section_symbol_lands_in_section(tmp_path):
    # The witness DEFINITION shape (`* __init f(...) { ... }`): the
    # oracle emits `.section .init.text,"ax",@progbits` and f1 is IN it.
    _section_pair(tmp_path, "wi2_fnsec",
                  "struct X { int x; };\n"
                  "struct X * __attribute__((__section__(\".init.text\")))"
                  " f1(void) { return 0; }\n", {"f1": ".init.text"})


def test_wi_obj_star_section_symbol_lands(tmp_path):
    # static object: `.section .sd,"aw"` (r2); blcc's data layer
    # already spells the flags (W2.5 law), the new position feeds it.
    _section_pair(tmp_path, "wi2_objsec",
                  "char * __attribute__((__section__(\".sd\"))) o2 = 0;\n",
                  {"o2": ".sd"})


def test_wi_array_star_section_symbol_lands(tmp_path):
    _section_pair(tmp_path, "wi2_arrsec",
                  "char * __attribute__((__section__(\".pa\")))"
                  " o3[4];\n", {"o3": ".pa"})


def test_wi_initdata_static_object_pair(tmp_path):
    # the verbatim `static char * __section__(".init.data")
    # root_device_name;` census shape (51-file cold tail class). The
    # READER keeps the symbol alive on BOTH sides (an unreferenced
    # static is DCE'd out of the oracle object — measured, -Os).
    _section_pair(tmp_path, "wi2_id",
                  "static char * __attribute__((__section__("
                  "\".init.data\"))) root_device_name;\n"
                  "char *get_rdn(void) { return root_device_name; }\n",
                  {"root_device_name": ".init.data"})


def test_wi_addr_class_aligned_star_emits_align(tmp_path):
    # `char * __aligned__(16) o` — BOTH asms carry `.align 16` (r1: a1).
    s, b = _compile(tmp_path, "wi2_al",
                    "char * __attribute__((aligned(16))) o = 0;\n"
                    "int main(void) { return (int)(long)o; }\n")
    assert b.returncode == 0, b.stderr
    g = gcc(["-S", str(s), "-o", str(tmp_path / "wi2_al.g.s")])
    assert g.returncode == 0, g.stderr
    o = tmp_path / "wi2_al.o"
    ba = blcc([str(s), "--emit-asm", "-o", str(o)])
    assert ba.returncode == 0, ba.stderr
    with open(str(o) + ".s") as fh:
        assert ".align 16" in fh.read()
    with open(str(tmp_path / "wi2_al.g.s")) as fh:
        assert ".align 16" in fh.read()


def test_wi_group_star_aligned_emits_align(tmp_path):
    # P2 group-interior: `int (* __aligned__(16) fp)(void)` — the
    # OBJECT raises (r14 `.align 16`), same emission law.
    s, b = _compile(tmp_path, "wi2_ga",
                    "int (* __attribute__((aligned(16))) fp)(void) = 0;\n"
                    "int main(void) { return (int)(long)fp; }\n")
    assert b.returncode == 0, b.stderr
    o = tmp_path / "wi2_ga.o"
    ba = blcc([str(s), "--emit-asm", "-o", str(o)])
    assert ba.returncode == 0, ba.stderr
    with open(str(o) + ".s") as fh:
        assert ".align 16" in fh.read()


# ------------------------------------------ the MARKER class: no emit

def test_wi_star_markers_emit_nothing_pair(tmp_path):
    # used/unused/notrace: NO section, no directive — the symbols ride
    # their natural .text/.bss on BOTH compilers (p1 f3/p3v law).
    _section_pair(tmp_path, "wi2_mark",
                  "int * __attribute__((unused))"
                  " __attribute__((no_instrument_function))"
                  " f3(void) { return 0; }\n"
                  "int * __attribute__((used)) p3v = 0;\n",
                  {"f3": ".text", "p3v": ".bss"})


def test_wi_section_beats_cold_pair(tmp_path):
    # THE corpus shape (`* __section__(".init.text") __cold f(...)`
    # with a body — the __init definition form): the SECTION WINS over
    # the cold partition on BOTH sides (.init.text, measured).
    _section_pair(tmp_path, "wi2_sbc",
                  "struct X { int x; };\n"
                  "struct X * __attribute__((__section__(\".init.text\")))"
                  " __attribute__((__cold__)) fc(void) { return 0; }\n",
                  {"fc": ".init.text"})


def test_wi_bare_cold_split_named_divergence(tmp_path):
    # NAMED DIVERGENCE (shipped hot/cold law, NOT this wave's approval):
    # a bare `__cold__` MARKER at the star position makes gcc -Os move
    # the fn to `.text.unlikely`; blcc keeps `.text` (markers emit
    # nothing — the §1 row 9 ignore class). Corpus volume at my wave
    # positions: ZERO bare-cold sites (all 2369 cold hits ride a
    # section, which wins — leg above); retirement rides the hot/cold
    # split law, never a silent flip.
    s, b = _compile(tmp_path, "wi2_cold",
                    "int * __attribute__((__cold__)) f(void)"
                    " { return 0; }\n")
    assert b.returncode == 0, b.stderr
    g = gcc(["-c", str(s), "-o", str(tmp_path / "wi2_cold.g.o")])
    assert g.returncode == 0, g.stderr
    assert _objdump_sections(str(tmp_path / "wi2_cold.g.o"))["f"] == \
        ".text.unlikely"                      # gcc -Os measured
    assert _objdump_sections(str(tmp_path / "wi2_cold.o"))["f"] == ".text"


def test_wi_type_position_section_loses_nothing_pair(tmp_path):
    # `char * __section__(".sd") * p` — TYPE position: gcc WARNS and
    # emits NO section (r2 a6 in .bss); blcc drops it. The pair proves
    # there is no silently-LOST section: neither object even HAS .sd.
    s, b = _compile(tmp_path, "wi2_tp",
                    "char * __attribute__((__section__(\".sd\")))"
                    " * o6 = 0;\n")
    assert b.returncode == 0, b.stderr
    g = gcc(["-c", str(s), "-o", str(tmp_path / "wi2_tp.g.o")])
    assert g.returncode == 0, g.stderr
    for obj, tool in ((str(tmp_path / "wi2_tp.o"), "blcc"),
                      (str(tmp_path / "wi2_tp.g.o"), "gcc")):
        secs = subprocess.run(["objdump", "-h", obj],
                              capture_output=True, text=True).stdout
        assert ".sd" not in secs, tool + " must not carry .sd:\n" + secs
    _section_pair(tmp_path, "wi2_tp2",
                  "char * __attribute__((__section__(\".sd\")))"
                  " * o6 = 0;\n", {"o6": ".bss"})


# ------------------------------------------- the CONFLICT law (rc1)

def test_wi_dual_section_conflict_loud(tmp_path):
    # probe r19: two DIFFERENT sections on one declarator are a gcc
    # ERROR "section of 'f19' conflicts with previous declaration" —
    # blcc LOUDs too; silently picking one would be section loss.
    s, b = _compile(tmp_path, "wi2_conf",
                    "struct X { int x; };\n"
                    "struct X * __attribute__((__section__(\".sa\")))"
                    " __attribute__((__section__(\".sb\")))"
                    " f19(void) { return 0; }\n")
    assert b.returncode != 0, "must LOUD the conflict (measured rc1)"
    assert "conflict" in b.stderr, b.stderr


def test_wi_same_section_twice_accepted(tmp_path):
    # probe dq: the SAME name twice is rc0 both sides — the judge is
    # CONFLICT-shaped, not count-shaped.
    _section_pair(tmp_path, "wi2_dup",
                  "char * __attribute__((__section__(\".a\")))"
                  " __attribute__((__section__(\".a\"))) dq = 0;\n",
                  {"dq": ".a"})


# ------------------------------------------------ nm law: weak marker

def test_wi_weak_marker_nm_divergence_named(tmp_path):
    # NAMED DIVERGENCE (W2.5 marker law, NOT this wave's approval):
    # gcc gives a weak DEFINITION the nm letter V; blcc's marker class
    # parses-and-drops → B. Corpus volume of the STAR form of weak:
    # ONE site, an extern PROTOTYPE (no symbol) — zero acceptance
    # impact; retirement rides the weak-nm law, never a silent flip.
    s, b = _compile(tmp_path, "wi2_weak",
                    "int * __attribute__((__weak__)) w = 0;\n")
    assert b.returncode == 0, b.stderr
    g = gcc(["-c", str(s), "-o", str(tmp_path / "wi2_weak.g.o")])
    assert g.returncode == 0, g.stderr

    def letter(obj):
        out = subprocess.run(["nm", obj], capture_output=True,
                             text=True).stdout
        for ln in out.splitlines():
            f = ln.split()
            if f and f[-1] == "w":
                return f[1] if len(f) == 3 else "U"
        return "?"
    assert letter(str(tmp_path / "wi2_weak.g.o")) == "V"      # gcc
    assert letter(str(tmp_path / "wi2_weak.o")) == "B"         # blcc


# ------------------------------------------------- member layout pair

def test_wi_member_star_aligned_layout_pair(tmp_path):
    # The MEASURED member law (probes r7/r8): LAST-star aligned RAISES
    # the member and the struct (A align 16; B m@16; D c+pad, m@32).
    src = (
        "struct A { char * __attribute__((aligned(16))) m;"
        " char * after; };\n"
        "struct B { char * before; char * __attribute__((aligned(16)))"
        " m; char * after; };\n"
        "struct D { char c; char * __attribute__((aligned(32))) m;"
        " char * after; };\n"
        "int pA[__alignof__(struct A) == 16 ? 1 : -1];\n"
        "int pA2[__builtin_offsetof(struct A, after) == 8 ? 1 : -1];\n"
        "int pB1[__alignof__(struct B) == 16 ? 1 : -1];\n"
        "int pB2[__builtin_offsetof(struct B, m) == 16 ? 1 : -1];\n"
        "int pD1[__alignof__(struct D) == 32 ? 1 : -1];\n"
        "int pD2[__builtin_offsetof(struct D, m) == 32 ? 1 : -1];\n")
    s, b = _compile(tmp_path, "wi2_mem", src)
    assert b.returncode == 0, "blcc must honor the measured law:\n" \
        + b.stderr
    g = gcc(["-c", str(s), "-o", str(tmp_path / "wi2_mem.g.o")])
    assert g.returncode == 0, "the law pins must also hold for gcc:\n" \
        + g.stderr


@pytest.mark.parametrize("decl", [
    "struct C { char * __attribute__((aligned(16))) * m;"
    " char * after; }; int pC[__alignof__(struct C) == 8 ? 1 : -1];",
    "struct E { char c; char * __attribute__((aligned(32))) * m;"
    " char * after; }; int pE[__alignof__(struct E) == 8 ? 1 : -1];",
])
def test_wi_member_type_pos_aligned_loud_twin(tmp_path, decl):
    # The between-star `aligned` is the TYPE-position LOUD-DIV twin
    # (gcc rc0, the align lands on a POINTER TYPE with NO observable
    # effect — r7/r8: C align 8, E align 8 — and blcc keeps the W2.5
    # layout-class wall; the same law tests/test_core_m4wi1.py pins at
    # the var declarator; corpus volume 0 measured over 706 streams).
    s, b = _compile(tmp_path, "wi2_mt", decl + "\n")
    assert b.returncode != 0, "layout class must stay LOUD: " + decl
    assert "aligned" in b.stderr.replace(str(tmp_path), "")
    g = gcc(["-c", str(s), "-o", os.devnull])
    assert g.returncode == 0, "gcc rc0 measured: " + decl + g.stderr


# --------------------------------------------------- the corpus legs

@pytest.mark.skipif(not (os.environ.get("KERNEL_510")
                         and os.path.isdir(STREAMS)),
                    reason="kernel tier + pinned streams corpus required")
@pytest.mark.parametrize("stream", [
    "drivers_pci_quirks.c.i",       # 581 census sites (the biggest)
    "arch_x86_pci_fixup.c.i",       #  67
    "arch_x86_kernel_quirks.c.i",   #  41
    "drivers_pci_vpd.c.i",          #  23
    "arch_x86_events_core.c.i",     #  21
    "init_main.c.i",                #  21 — the percpu.h:105 walk TU
    "mm_sparse-vmemmap.c.i",        #  19
    "mm_memblock.c.i",              #  11
    "mm_debug.c.i",                 #     the verbatim witness line
    "drivers_tty_serial_serial_core.c.i",  #   + the multiline chain
])
def test_wi_cohort_attr_wall_is_dead(stream, tmp_path):
    # RED-at-tip (wall captured: the percpu.h:105 sentence; sweep
    # .tmp/m4-wi/out/wall-tip.jsonl 574 rows). After the wave the
    # attr-identifier wall must be DEAD — the stream may honestly
    # answer its NEXT wall (sizeof(void), unbraced-if, …), that wall
    # must just not be THIS family.
    clean = _clean_i(os.path.join(STREAMS, stream), tmp_path, "corpsi")
    r = blcc(["-c", str(clean), "-o", str(tmp_path / "corpsi.o")])
    assert "expected an identifier, found '__attribute__'" not in r.stderr, \
        "the attribute-between-* wall is STILL ALIVE:\n" + r.stderr[:400]


def test_wi_percpu_witness_verbatim_compiles(tmp_path):
    # VERBATIM percpu.h:105 stream line (the 574-family witness, mm_
    # debug.c.i form): compiles clean end to end.
    _compile_ok = _compile(tmp_path, "wi2_pc",
                           "struct pcpu_alloc_info;\n"
                           "extern struct pcpu_alloc_info *"
                           " __attribute__((__section__(\".init.text\")))"
                           " __attribute__((__cold__))"
                           " pcpu_alloc_alloc_info(int nr_groups);\n")
    assert _compile_ok[1].returncode == 0, _compile_ok[1].stderr
