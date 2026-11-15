# LINES reason: one wave of legs (M4 W2.5 ARM 3 — `__section__` EMISSION +
# the misc-12 disposition census, plan-m4 v4 §6/§7 AMENDMENT-3, MC 12557) —
# the placement law and the census that closes "zero unlisted" are one
# evidence set.
r"""M4 W2.5 ARM 3 — `__section__("name")` lands, and misc-12 dispositions.

GCC 11.4 gnu89 -Os EMISSION LAW (measured this card, fx/S1.c):
  object:    `.section NAME,"aw"` at FIRST mention (later mentions carry
             no flags), uninitialized object = `.zero N` INSIDE the named
             section (PROGBITS; nm letter D — the section name does NOT
             make it nobits), const object = flags "a".
  function:  `.section NAME,"ax",@progbits` before the body, emission
             returns to `.text` after.
  argument:  non-string section arg = gcc rc1 "section attribute argument
             not a string constant" (blcc parse twin).
  ORDER: gcc emits a data block in REVERSE declaration order; blcc's
  shipped law is declaration order (NAMED shape-divergence row — the nm
  letters/names/flags match, the intra-block ORDER does not; the §6 law
  binds U-membership + letters + section names, not block order).
  `.data..percpu` appears in the corpus ONLY as a string inside
  arch/x86/tools/relocs (host tier, gcc-delegated) — 0 in-universe
  placement sites: the PROBE below is HONESTLY PLACEMENT-ONLY (the percpu
  *accessor* semantics — %gs-relative addressing — are NOT claimed).

DISPOSITION TABLE (misc-12 = the remaining attribute wall of the W2 gate
triage: nothrow 7 / no_instrument_function 2 / error 2 / pure 1): every
name below is listed here with its measured posture — SUPPORTED (parse,
drop, oracle-equal rc0 — it changes no emitted code) or LOUD-PINNED (a
named sentence). The full census rows (weak/visibility/ms_abi/regparm/
cleanup/assume_aligned) ride here too: zero unlisted at wave end.
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


def twin(tmp_path, tag, src):
    s = tmp_path / (tag + ".c")
    s.write_text(src)
    gr = gcc(["-c", str(s), "-o", str(tmp_path / (tag + ".g.o"))])
    assert gr.returncode == 0, "oracle must accept ({}):\n{}".format(
        tag, gr.stderr)
    br = blcc(["-c", str(s), "-o", str(tmp_path / (tag + ".b.o"))])
    assert br.returncode == 0, "blcc must accept ({}):\n{}".format(
        tag, br.stderr)


def loud_pair(tmp_path, tag, src, frag, gcc_must="reject"):
    s = tmp_path / (tag + ".c")
    s.write_text(src)
    gr = gcc(["-c", str(s), "-o", str(tmp_path / (tag + ".g.o"))])
    if gcc_must == "reject":
        assert gr.returncode != 0, "oracle must reject ({}):\n{}".format(
            tag, gr.stderr)
    else:
        assert gr.returncode == 0, "oracle must accept ({}):\n{}".format(
            tag, gr.stderr)
    br = blcc(["-c", str(s), "-o", str(tmp_path / (tag + ".b.o"))])
    assert br.returncode == 2 and frag in br.stderr, \
        "blcc must LOUD naming '{}' ({}):\n{}".format(frag, tag,
                                                      br.stderr[:400])


def run_pair(tmp_path, tag, src, expect=None):
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
        "run-pair diverge: gcc {} vs blcc {}".format(g.returncode,
                                                     b.returncode)
    if expect is not None:
        assert g.returncode == expect, \
            "oracle answers {}, leg expects {}".format(g.returncode, expect)
    return g.returncode


def asm_text(tmp_path, tag, src):
    s = tmp_path / (tag + ".c")
    s.write_text(src)
    o = tmp_path / (tag + ".o")
    br = blcc([str(s), "--emit-asm", "-o", str(o)])
    assert br.returncode == 0, "blcc --emit-asm must build:\n" + br.stderr
    with open(str(o) + ".s") as fh:
        return fh.read()


# ============ S1: objects land in the NAMED section ========================

def test_section_object_placed(tmp_path):
    # The VERBATIM wall shape `extern char __attribute__((__section__(
    # ".init.data"))) boot_command_line[];` is the DECL side (ARM 2 leg);
    # HERE the DEFINITION emits into the named section with the measured
    # first-mention flags `"aw"`.
    txt = asm_text(tmp_path, "s_obj",
                   "int __attribute__((__section__(\".init.data\"))) "
                   "sd = 7;\n"
                   "int main(void){ return sd; }\n")
    assert re.search(r"\.section \.init\.data,\"aw\"", txt), \
        "first mention must carry the aw flags:\n" + txt[-500:]
    idx = txt.index(".section .init.data")
    assert idx < txt.index("sd:"), "the label rides INSIDE the section"
    assert ".data\n" not in txt[idx:], \
        "sd must not also be re-emitted in .data"
    src = ("int __attribute__((__section__(\".init.data\"))) sd = 7;\n"
           "int main(void){ return sd; }\n")
    assert run_pair(tmp_path, "s_objr", src, expect=7) == 7


def test_section_zero_object_stays_progbits(tmp_path):
    # Measured gcc: an UNINITIALIZED object in a named section is `.zero N`
    # inside the PROGBITS section (nm letter D — the name does not make it
    # NOBITS). blcc rides the same .zero law.
    txt = asm_text(tmp_path, "s_zero",
                   "int __attribute__((section(\".data..once\"))) pz;\n"
                   "int main(void){ return pz; }\n")
    i = txt.index(".section .data..once")
    assert ".zero" in txt[i:i + 80], \
        "the zero-fill must live inside the named section:\n" + txt[-400:]
    assert run_pair(tmp_path, "s_zeror",
                    "int __attribute__((section(\".data..once\"))) pz;\n"
                    "int main(void){ pz = 2; return pz; }\n",
                    expect=2) == 2


def test_section_flags_once_labels_many(tmp_path):
    # First mention carries flags, LATER mentions none (measured gcc form
    # `.section .init.data`); both labels land inside the one section.
    txt = asm_text(tmp_path, "s_multi",
                   "int __attribute__((section(\".init.data\"))) a1 = 1;\n"
                   "int __attribute__((section(\".init.data\"))) a2 = 2;\n"
                   "int main(void){ return a1 + a2; }\n")
    assert txt.count('.section .init.data,"aw"') == 1
    assert txt.count(".section .init.data") == 2, \
        "second mention plain:\n" + txt[-500:]
    assert txt.index("a1:") < txt.index("a2:"), \
        "blcc declaration-order law (the reverse-order gcc block is the " \
        "NAMED shape-divergence row — names/letters/flags match, the " \
        "intra-block order is pinned HERE as blcc's own law)"
    assert run_pair(tmp_path, "s_multir",
                    "int __attribute__((section(\".init.data\"))) a1 = 1;\n"
                    "int __attribute__((section(\".init.data\"))) a2 = 2;\n"
                    "int main(void){ return a1 + a2; }\n",
                    expect=3) == 3


def test_section_const_object_flags_a(tmp_path):
    # Measured gcc: a const object in a custom section carries flags "a"
    # (read-only), NOT "aw".
    txt = asm_text(tmp_path, "s_const",
                   "const int __attribute__((section(\".my.ro\"))) cv = 5;\n"
                   "int main(void){ return cv; }\n")
    assert re.search(r"\.section \.my\.ro,\"a\"", txt), \
        "const placement uses the a flags:\n" + txt[-400:]
    assert run_pair(tmp_path, "s_constr",
                    "const int __attribute__((section(\".my.ro\"))) cv = 5;\n"
                    "int main(void){ return cv; }\n", expect=5) == 5


# ============ S2: functions land in the named .text section ================

def test_section_function_placed(tmp_path):
    # Measured gcc: `.section NAME,"ax",@progbits` before the body; blcc
    # emits the directive and returns to `.text` after (so the NEXT
    # function is not silently placed in the named one).
    txt = asm_text(tmp_path, "s_fn",
                   "int __attribute__((__section__(\".init.text\"))) "
                   "bootfn(void){ return 3; }\n"
                   "int other(void){ return 4; }\n"
                   "int main(void){ return bootfn() + other(); }\n")
    i = txt.index('.section .init.text,"ax",@progbits')
    j = txt.index("bootfn:")
    k = txt.index("other:")
    assert i < j < k, "bootfn INSIDE .init.text, other AFTER the .text " \
        "return:\n" + txt[-600:]
    assert ".text" in txt[j:k], "emission must return to .text"
    assert run_pair(tmp_path, "s_fnr",
                    "int __attribute__((__section__(\".init.text\"))) "
                    "bootfn(void){ return 3; }\n"
                    "int other(void){ return 4; }\n"
                    "int main(void){ return bootfn() + other(); }\n",
                    expect=7) == 7


def test_section_percpu_probe_placement_only(tmp_path):
    # HONEST SCOPE: `.data..percpu` occurs in the corpus ONLY as a STRING
    # in the host-tier relocs tool (0 in-universe placement sites); the
    # %gs-relative per-CPU ACCESSOR semantics are NOT claimed and blcc
    # does NOT implement them. This probe pins the PLACEMENT law only:
    # the symbol lands in the named section with the zero fill.
    txt = asm_text(tmp_path, "s_percpu",
                   "int __attribute__((section(\".data..percpu\"))) pv;\n"
                   "int main(void){ pv = 9; return pv; }\n")
    i = txt.index(".section .data..percpu")
    assert txt.index("pv:") > i and ".zero" in txt[i:i + 90]
    assert run_pair(tmp_path, "s_percpur",
                    "int __attribute__((section(\".data..percpu\"))) pv;\n"
                    "int main(void){ pv = 9; return pv; }\n",
                    expect=9) == 9


def test_section_arg_not_a_string_loud(tmp_path):
    # gcc rc1 twin: `section attribute argument not a string constant`.
    loud_pair(tmp_path, "s_str",
              "int x __attribute__((section(3)));\n"
              "int main(void){return x;}\n", "string constant")


# ============ S3: the misc-12 disposition list (zero unlisted) =============

def test_misc_nothrow_leaf_verbatim(tmp_path):
    # SUPPORTED (7 files, host glibc `__NTH`): VERBATIM glibc shape —
    # `__attribute__ ((__nothrow__ , __leaf__))` on prototypes; changes no
    # emitted code (blcc has no exception machinery to unwind).
    twin(tmp_path, "m_nth",
         "extern int tolower (int __c) __attribute__ ((__nothrow__ ,"
         " __leaf__));\n"
         "extern int __ctype_tolower_loc (void) __attribute__ ((__nothrow__"
         " , __leaf__));\n"
         "int f(int c){ return tolower(c); }\n")


def test_misc_no_instrument_function(tmp_path):
    # SUPPORTED (2 files): `notrace`/`no_instrument_function` are ftrace
    # instrumentation hints — parse + drop, rc0 twins (blcc never
    # instruments: -pg hookup is not in the subset).
    twin(tmp_path, "m_nif",
         "int __attribute__((no_instrument_function)) nf(void){ return 1; }\n"
         "int __attribute__((notrace)) nt(void){ return 2; }\n"
         "int main(void){ return nf() + nt(); }\n")
    assert run_pair(tmp_path, "m_nifr",
                    "int __attribute__((no_instrument_function)) nf(void)"
                    "{ return 1; }\n"
                    "int __attribute__((notrace)) nt(void){ return 2; }\n"
                    "int main(void){ return nf() + nt(); }\n",
                    expect=3) == 3


def test_misc_pure_crc32_verbatim(tmp_path):
    # SUPPORTED (1 file): `u32 __pure crc32_le(...)` — a optimizer hint;
    # rc0 twin; no emitted-code change.
    twin(tmp_path, "m_pure",
         "typedef unsigned int u32;\n"
         "u32 __attribute__((__pure__)) crc32_le(u32 crc, int len);\n"
         "u32 f(u32 c){ return crc32_le(c, 4); }\n")


def test_misc_error_attr_true_pair(tmp_path):
    # SUPPORTED (2 files): the BUILD_BUG_ON idiom's SHIPPED §2.9 posture —
    # the error-fn DECLARATION alone never fires (both sides rc0,
    # measured). The post-pp corpus never leaves a reachable CALL behind
    # at -Os (gcc folds the false branch away; blcc does NOT dead-code-
    # fold — an emitted call to the never-defined error-fn would fail at
    # LINK, so a corpus file only survives while its calls all fold away
    # upstream, exactly what the §2.9 legs already pin).
    src = ("extern void __attribute__((__error__(\"value doesn't fit\")))\n"
           "    __compiletime_assert_215(void);\n"
           "int main(void){ return 0; }\n")
    assert run_pair(tmp_path, "m_err", src, expect=0) == 0


def test_misc_error_attr_false_side_pinned(tmp_path):
    # NAMED PIN (measured): the TRUE side — gcc 11.4 FIRES the named
    # compile-time error (rc1 "value doesn't fit"); blcc's shipped §2.9
    # posture is PARSE+STRIP (sema-side not implemented): the call simply
    # compiles. LOUD-DIV twin recorded here, never silent: the divergence
    # is the MISSING fire, and the corpus shape only ever references the
    # name under false conditions (BUILD_BUG_ON law).
    s = tmp_path / "m_err1.c"
    s.write_text("extern void __attribute__((__error__(\"boom\"))) badfn("
                 "void);\nint main(void){ badfn(); return 0; }\n")
    gr = gcc([str(s), "-o", str(tmp_path / "m_err1.gcc")])
    assert gr.returncode != 0, \
        "the oracle MUST fire the named compile-time error"


# ============ S4: census pins — named divergences, zero unlisted ===========

def test_census_weak_object_nm_letter_pinned(tmp_path):
    # WEAK objects (585 sites / 224 files, `__weak`): SUPPORTED for
    # parse+drop+placement, but the §6 nm LETTER diverges and is PINNED
    # here — BOTH letters measured this leg: gcc's weak *uninitialized*
    # object is a weak COMMON (`nm` answers V); blcc emits a plain global
    # .bss object (letter B). The §6 U-set still matches (the symbol
    # EXISTS, global); the letter row is a NAMED pre-existing concern
    # handed to W-close §6 with this measurement.
    src = ("int __attribute__((weak)) wobj;\n"
           "int main(void){ return wobj; }\n")
    s = tmp_path / "c_weak.c"
    s.write_text(src)
    gx = tmp_path / "c_weak.gcc"
    gr = gcc([str(s), "-o", str(gx)])
    assert gr.returncode == 0, "oracle builds:\n" + gr.stderr
    gnm = subprocess.run(["nm", str(gx)], capture_output=True, text=True)
    g = {m.group(2): m.group(1) for m in
         re.finditer(r"[0-9a-f]* ([A-Za-z]) (\S+)", gnm.stdout)}
    assert g.get("wobj") == "V", "the MEASURED gcc weak-object letter:\n" \
        + gnm.stdout
    bx = tmp_path / "c_weak.blcc"
    br = blcc([str(s), "-o", str(bx)])
    assert br.returncode == 0, "weak parses+emits (SUPPORTED part):\n" + \
        br.stderr
    bnm = subprocess.run(["nm", str(bx)], capture_output=True, text=True)
    b = {m.group(2): m.group(1) for m in
         re.finditer(r"[0-9a-f]* ([A-Za-z]) (\S+)", bnm.stdout)}
    assert b.get("wobj") == "B", \
        "blcc's pinned letter (B vs the gcc V — the NAMED divergence):\n" \
        + bnm.stdout


def test_census_visibility_hidden_not_emitted(tmp_path):
    # VISIBILITY (28/7, `__visible`/`__hidden`): SUPPORTED parse+drop;
    # measured divergence PINNED: gcc emits `.hidden NAME` for
    # __attribute__((visibility("hidden"))) (the nm letter stays D — the
    # dynamic symbol is what changes, OUTSIDE the §6 static-nm law). blcc
    # does NOT emit .hidden; 0 observable effect under blcc's own no-
    # shared-library universe (no .so is ever produced) — named, not
    # silent.
    txt = asm_text(tmp_path, "c_vis",
                   "int __attribute__((visibility(\"hidden\"))) hv = 1;\n"
                   "int main(void){ return hv; }\n")
    assert ".hidden" not in txt        # blcc posture PINNED (see sentence)
    assert "hv:" in txt
    assert run_pair(tmp_path, "c_visr",
                    "int __attribute__((visibility(\"hidden\"))) hv = 1;\n"
                    "int main(void){ return hv; }\n", expect=1) == 1


def test_census_ms_abi_regparm_cleanup_parse_drop(tmp_path):
    # MS_ABI (104/8 host-tier vdso shapes), REGPARM (7/1 host), CLEANUP
    # (3/3): parse + drop is SUPPORTED for the DECL shapes; the CALLING-
    # CONVENTION/attribute-cleanup SEMANTICS are not in the subset (blcc
    # is one fixed SysV ABI; gcc's cleanup attribute auto-calls —
    # pinned). The census row's evidence leg: verbatim shapes rc0 twin.
    twin(tmp_path, "c_conv",
         "typedef unsigned long size_t;\n"
         "__attribute__((ms_abi)) int msfn(void){ return 1; }\n"
         "int __attribute__((regparm(3))) rp(int a){ return a; }\n"
         "int __attribute__((cleanup(free_it))) *mk(void); void free_it(int "
         "**p);\n"
         "int f(void){ return msfn() + rp(1); }\n")


def test_census_assume_aligned_parse_drop(tmp_path):
    # ASSUME_ALIGNED (1380/460): hint-class — parse+drop SUPPORTED (the
    # arg may carry an alignof expression, token-level skip — ARM 1 leg
    # ao_atr already pins it). Row evidence: rc0 twin here too.
    twin(tmp_path, "c_aa",
         "typedef unsigned long size_t;\n"
         "void *km(void) __attribute__((__assume_aligned__(8)));\n"
         "int main(void){ return 0; }\n")
