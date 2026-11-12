r"""Regressions for the M1 TEST-c2 findings (m1-test-verdict-c2.md), fix
cycle MC 12436. Every expectation was re-measured against the live oracle
(gcc 11.4 -E) THIS session before being pinned — never from blcc:

F-1 (P0) include-cycle rule. gcc RE-OPENS a file that is already on the
    active include stack: its guard (already defined) skips the body and the
    stream terminates — a guarded re-entrant chain (the kernel's
    uapi/linux/timex.h <-> linux/time.h shape, 676/691 corpus deaths) is
    NORMAL. The rule shipped here dies on ANY active-stack re-entry,
    guard-blind. Pinned rule (oracle + the M20 diamond + the unguarded a<->b
    fixture jointly force it): a file already on the active stack may be
    re-opened EXACTLY ONCE (the guard-skim case); a SECOND re-entry can only
    come from a body that re-executes — a true cycle — and stays loud
    ("include cycle detected"); the depth-200 cap keeps linear runaways.
F-2 (P1) `##` paste consumed the parameter MAPPING (`mapping[p] = tail`),
    so a second paste of the SAME parameter in one body lost its right
    operand: asm("rsp") became asm("r") at rc 0 (SILENT), and the kernel's
    __ATTR_RW -> __ATTR chain died LOUD with a bogus arg count. Each
    parameter occurrence must see the full argument; the operand's REMAINING
    tokens stay in the stream (R8 `## __VA_ARGS__` keeps working).
F-3 (P1) a macro name PRODUCED by an expansion (object-like alias whose body
    is a function-like macro: `#define cpu_to_le16 __cpu_to_le16`; or a
    paste result: CAT(ID, N(...)) -> ID4) was never rescanned against the
    FOLLOWING `(`, so the call was emitted UN-expanded at rc 0 (SILENT).
    Fix: the replacement list is spliced into the token stream and rescanned
    in place (the C re-scan model); blue paint (hidden set) becomes a
    PER-TOKEN property so only the macro being expanded is hidden, never a
    name merely produced by its body.
F-4 (P1) predefines: gcc 11.4 predefines 365 names for the kernel profile,
    blcc shipped 24. Corpus-visible silent branch flips:
    __GCC_ASM_FLAG_OUTPUTS__ (asm.h:119 "=@ccs" branch) and
    __SIZEOF_INT128__ (math64.h:156). Also pinned: __STDC_UTF_16__/32__ are
    NOT defined under gnu89 (gcc fact; the old hand table had them in ALL
    stds) and __STDC_VERSION__ per -std. Table is GENERATED data
    (scripts/gen_predefines_table.py from the pinned oracle capture).
F-5 (P1) the conditional operator `?:` is part of the #if constant-expression
    grammar; gcc evaluates it (the kernel's 4 uapi byte-order headers use
    `#if defined(__BYTE_ORDER) ? ... : ...`). The gcc EXTENSION `x ?: y`
    (missing middle) is NOT accepted by gcc in #if ("operator '?' has no
    right operand", rc 1) — so it must stay LOUD here too, never silently
    accepted. Result type = usual arithmetic conversions of BOTH arms
    (oracle: `(1 ? -1 : 1u) > 0` is TRUE).
"""
import os
import re
import subprocess
import sys

import pytest

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PP_RE = re.compile(r"^.*:\d+:\d+: pp: .+, found '.+'")
PINS = ['-D__DATE__="Mon Nov  3 11:22:33 2025"', '-D__TIME__="11:22:33"']

_TOKEN = re.compile(
    r'"(?:\\.|[^"\\])*"?|\'(?:\\.|[^\'\\])*\'?'
    r"|[A-Za-z_][A-Za-z0-9_]*|[0-9][0-9A-Za-z_.]*"
    r"|\.\.\.|<<=|>>=|->|\+\+|--|<<|>>|&&|\|\||[=!<>*/%&|^+-]=|[{}()\[\];,.]"
    r"|[<>=*/%&|^!~?:#+-]", re.S)
_MARKER = re.compile(r"^#[ \t]*\d+[ \t]")
_BARE = re.compile(r"^#[ \t]*\d+[ \t]*$")


def norm(text):
    text = text.replace("\\\n", "")
    kept = [l for l in text.splitlines()
            if not _MARKER.match(l) and not _BARE.match(l)]
    return _TOKEN.findall("\n".join(kept))


def gcc_run(args):
    return subprocess.run(["gcc", "-E"] + args, capture_output=True,
                          text=True, timeout=120)


def blcc_run(args):
    env = dict(os.environ, PYTHONPATH=REPO)
    return subprocess.run([sys.executable, "-m", "blcc", "-E"] + args,
                          capture_output=True, text=True, timeout=120,
                          env=env)


def write(tmp_path, name, text):
    p = tmp_path / name
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(text, encoding="utf-8")
    return str(p)


def diff_snippet(tmp_path, src, extra=(), fname="t.c"):
    """Both sides on identical argv; both exit 0; token streams equal."""
    path = write(tmp_path, fname, src)
    g = gcc_run(list(extra) + [path] + PINS)
    b = blcc_run(list(extra) + [path] + PINS)
    assert g.returncode == 0, "gcc failed: %s" % g.stderr
    assert b.returncode == 0, "blcc failed: %s" % b.stderr
    assert norm(b.stdout) == norm(g.stdout), \
        "token mismatch:\n blcc: %r\n gcc:  %r" % (norm(b.stdout)[:80],
                                                   norm(g.stdout)[:80])
    return b.stdout, b



# ---------------------------------------------------------- F-1 cycle rule --


def test_guarded_self_chain_reopens(tmp_path):
    """timex.h <-> time.h shape: two GUARDED headers that include each
    other. gcc re-opens the cycle target once, the guard skips the body, rc
    0. Shipped blcc dies: 'include cycle detected' (the 676-file wall)."""
    write(tmp_path, "fx_base.h", "#ifndef _FX_BASE_H\n#define _FX_BASE_H\n"
                                 '#include "fx_inner.h"\nint base_marker;\n'
                                 "#endif\n")
    write(tmp_path, "fx_inner.h", "#ifndef _FX_INNER_H\n#define _FX_INNER_H\n"
                                  '#include "fx_base.h"\nint inner_marker;\n'
                                  "#endif\n")
    out, _ = diff_snippet(tmp_path, '#include "fx_base.h"\n'
                                    "int main_marker;\n")
    toks = norm(out)
    assert toks.count("base_marker") == 1            # body executed once
    assert toks.count("inner_marker") == 1


def test_guarded_self_include_reopens(tmp_path):
    """A guarded header that includes ITSELF: gcc rc 0 (reopen, guard
    skips); shipped blcc died 'cycle detected'."""
    write(tmp_path, "self.h", "#ifndef _SELF_H\n#define _SELF_H\n"
                              '#include "self.h"\nint self_marker;\n#endif\n')
    out, _ = diff_snippet(tmp_path, '#include "self.h"\nint after;\n')
    assert norm(out).count("self_marker") == 1


def test_guarded_reentrant_ring_reopens(tmp_path):
    """3-deep guarded ring: main -> a -> b -> c -> a (a is on the ACTIVE
    stack at the c -> a include). gcc reopens once, every guarded body
    executes exactly once."""
    write(tmp_path, "ring_a.h", "#ifndef _RA\n#define _RA\n"
                                '#include "ring_b.h"\nint a_body;\n#endif\n')
    write(tmp_path, "ring_b.h", "#ifndef _RB\n#define _RB\n"
                                '#include "ring_c.h"\nint b_body;\n#endif\n')
    write(tmp_path, "ring_c.h", "#ifndef _RC\n#define _RC\n"
                                '#include "ring_a.h"\nint c_body;\n#endif\n')
    out, _ = diff_snippet(tmp_path, '#include "ring_a.h"\nint tail;\n')
    toks = norm(out)
    for m in ("a_body", "b_body", "c_body"):
        assert toks.count(m) == 1, m
    assert "tail" in toks


def test_unguarded_true_cycle_loud(tmp_path):
    """The TRUE cycle (no guards at all) stays LOUD on both sides — the
    count>=2 rule must not regress the GA a<->b pin, and the diagnostic is
    the CYCLE one, not the depth-cap one (that names the chosen rule)."""
    write(tmp_path, "cyc_a.h", '#include "cyc_b.h"\n')
    write(tmp_path, "cyc_b.h", '#include "cyc_a.h"\n')
    path = write(tmp_path, "m.c", '#include "cyc_a.h"\nint v;\n')
    g = gcc_run([path])
    b = blcc_run([path])
    assert g.returncode != 0                         # gcc: depth 200, rc 1
    assert b.returncode == 2 and PP_RE.match(b.stderr)
    assert "include cycle detected" in b.stderr



# ------------------------------------------------------------- F-2 paste --


def test_paste_same_param_twice_full_arg(tmp_path):
    """Verbatim rc2_min.c kernel driver (arch/x86 asm.h:31/48/189 shape):
    the SECOND paste of one parameter used to lose its right operand —
    gcc emits "rsp", shipped blcc emitted "r" AT RC 0 (silent)."""
    src = ("#define __stringify_1(x...) #x\n"
           "#define __stringify(x...) __stringify_1(x)\n"
           "#define SEL_RAW(a,b) __stringify(b)\n"
           "#define REG(reg) SEL_RAW(e##reg, r##reg)\n"
           "R = REG(sp);\n")
    out, _ = diff_snippet(tmp_path, src)
    assert '"rsp"' in norm(out)                      # independent pin


def test_paste_attr_chain_loudless(tmp_path):
    """Verbatim include/linux/sysfs.h:101 device.h chain shape: shipped
    blcc died LOUD ('__ATTR takes 4 argument(s)') because the paste shrink
    ate the argument mapping mid-substitution."""
    src = ("#define __stringify_1(x...) #x\n"
           "#define __stringify(x...) __stringify_1(x)\n"
           "#define ___PASTE(a,b) a##b\n"
           "#define __PASTE(a,b) ___PASTE(a,b)\n"
           "#define __ATTR(_name, _mode, _show, _store) "
           "{ .attr = {.name = __stringify(_name), .mode = "
           "__PASTE(04,_mode) }, .show = _show, .store = _store }\n"
           "#define __ATTR_RW(_name) __ATTR(_name, 0644, _name##_show, "
           "_name##_store)\n"
           "#define DEVICE_ATTR_RW(_name) struct device_attribute "
           "dev_attr_##_name = __ATTR_RW(_name)\n"
           "DEVICE_ATTR_RW(foo);\n")
    out, b = diff_snippet(tmp_path, src)
    assert "'__ATTR' redefined" not in b.stderr
    joined = " ".join(norm(out))
    assert 'dev_attr_foo' in joined and '"foo"' in joined and '0644' in joined


def test_paste_va_args_tail_not_shrunk(tmp_path):
    """Discriminator for the R8 tail rule vs the mapping fix: a variadic
    tail used BOTH as a plain occurrence and as a paste operand — the plain
    occurrence must see the FULL tail (old code saw the shrunk mapping)."""
    src = ("#define BOTH(a...) a + Z ## a\n"
           "V = BOTH(1 , 2);\n")
    out, _ = diff_snippet(tmp_path, src)
    # oracle (measured): V = 1 , 2 + Z1 , 2 ;  — the plain occurrence sees
    # the FULL tail AND the paste takes its head, tail following (R8).
    assert " ".join(norm(out)) == "V = 1 , 2 + Z1 , 2 ;"



# ------------------------------------------------------------- F-3 rescan --


def test_objectlike_alias_rescanned_as_function(tmp_path):
    """#define ALIAS TWO (object-like alias of a function-like macro): the
    ALIAS(1,2) invocation must expand through the alias: gcc `(1)+(2)`,
    shipped blcc emitted TWO(1,2) AT RC 0 (silent)."""
    src = ("#define TWO(a,b) (a)+(b)\n"
           "#define ALIAS TWO\n"
           "E1 = ALIAS(1,2);\n")
    out, _ = diff_snippet(tmp_path, src)
    assert " ".join(norm(out)) == "E1 = ( 1 ) + ( 2 ) ;"


def test_paste_produced_name_invoked(tmp_path):
    """CAT(ID, N(...)) pastes the invocation head ID4; the following
    (...) must invoke it: gcc GOT_IT(1,2,3,4), shipped blcc emitted the
    UN-expanded ID4(1,2,3,4) at rc 0 (silent). Kernel driver: rmwcc.h:60."""
    src = ("#define ID4(a,b,c,d) GOT_IT(a,b,c,d)\n"
           "#define CAT2(a,b) a ## b\n"
           "#define CAT(a,b) CAT2(a,b)\n"
           "#define N(a,b,c,d,e...) 4\n"
           "#define F(...) CAT(ID, N(__VA_ARGS__))(__VA_ARGS__)\n"
           "X1 = F(1,2,3,4);\n")
    out, _ = diff_snippet(tmp_path, src)
    assert " ".join(norm(out)) == "X1 = GOT_IT ( 1 , 2 , 3 , 4 ) ;"


def test_cpu_to_le16_kernel_alias_shape(tmp_path):
    """The byteorder/generic.h:90 shape verbatim: 10 corpus files (and the
    silent module_signature.c row) carry this un-expanded today."""
    src = ("#define __cpu_to_le16(x) ((__u16)(x))\n"
           "#define cpu_to_le16 __cpu_to_le16\n"
           "v = cpu_to_le16(42);\n")
    out, _ = diff_snippet(tmp_path, src)
    toks = norm(out)
    assert "__cpu_to_le16" not in toks
    assert " ".join(toks) == "v = ( ( __u16 ) ( 42 ) ) ;"


def test_alias_blue_paint_still_terminates(tmp_path):
    """Rescan must not break blue paint: a doubling chain through an alias
    terminates with the hidden identifier surviving, exit 0 (gcc posture).
    """
    src = ("#define B A A\n"
           "#define A done\n"
           "E = A;\n")
    out, _ = diff_snippet(tmp_path, src)
    assert " ".join(norm(out)) == "E = done ;"
    src2 = ("#define A A\n"
            "P = A Q;\n")                           # A after A: rescanned
    out2, _ = diff_snippet(tmp_path, src2, fname="u.c")
    assert norm(out2).count("A") == 1                # gcc: P = A Q (blue)



# ------------------------------------------------------------ F-4 predefines --


def test_predefines_definedness_battery(tmp_path):
    """EVERY name of the shipped table answers DEFINED on the oracle, and
    the shipped table carries the full gcc 11.4 kernel-profile capture (not
    the old hand-picked 24). The stateful hooks (__LINE__ … __TIME__) are
    excluded: they answer at the use site, not as #ifdef names."""
    sys.path.insert(0, REPO)
    from blcc.pp_predefines import builtins
    names = sorted(builtins("gnu89"))
    assert len(names) >= 340, "predefine table too small: %d" % len(names)
    for probe in ("__GCC_ASM_FLAG_OUTPUTS__", "__SIZEOF_INT128__",
                  "__GNUC__", "__STDC__", "__INT64_C"):
        assert probe in names, probe
    lines = ["#ifndef %s\nMISS_%s\n#endif\n" % (n, n) for n in names
             if n not in ("__LINE__", "__FILE__", "__COUNTER__",
                          "__DATE__", "__TIME__")]
    path = write(tmp_path, "battery.c", "".join(lines))
    g = gcc_run(["-std=gnu89", path] + PINS)
    b = blcc_run(["-std=gnu89", path] + PINS)
    assert g.returncode == 0, g.stderr[:200]
    assert b.returncode == 0, b.stderr[:200]
    assert not any(t.startswith("MISS_") for t in norm(g.stdout))
    assert not any(t.startswith("MISS_") for t in norm(b.stdout))
    assert len(names) >= 340


def test_predefines_value_branches(tmp_path):
    """Silent-branch-flip rows + per-std value rows, token-equal to gcc:
    __GCC_ASM_FLAG_OUTPUTS__ (371 corpus files took the WRONG asm.h:119
    branch), __SIZEOF_INT128__ (math64.h:156), __STDC_UTF_16__ NOT defined
    under gnu89 (gcc fact), __STDC_VERSION__ per -std, __INT64_C paste."""
    src = ("#ifdef __GCC_ASM_FLAG_OUTPUTS__\nAFO\n#else\nAFO_NO\n#endif\n"
           "#if __SIZEOF_INT128__ == 16\nI128\n#else\nI128_NO\n#endif\n"
           "#ifdef __STDC_UTF_16__\nUTF\n#else\nUTF_NO\n#endif\n"
           "#ifndef __STDC_VERSION__\nNOSTDVC\n#endif\n"
           "C = __INT64_C(5);\nU = __UINT64_C(5);\n"
           "#if __GNUC__ * 10000 + __GNUC_MINOR__ * 100 + "
           "__GNUC_PATCHLEVEL__ == 110400\nGCCV\n#endif\n")
    out, _ = diff_snippet(tmp_path, src, extra=["-std=gnu89"])
    toks = norm(out)
    for tag in ("AFO", "I128", "UTF_NO", "NOSTDVC", "GCCV"):
        assert tag in toks, tag
    assert "C = 5L ;" in " ".join(toks)
    out17, _ = diff_snippet(tmp_path,
                            "#ifdef __STDC_VERSION__\nV17\n#endif\n"
                            "#ifdef __STDC_UTF_16__\nU17\n#endif\n",
                            extra=["-std=gnu17"], fname="t17.c")
    assert {"V17", "U17"} <= set(norm(out17))


def test_predefines_D_U_still_win(tmp_path):
    """The generated table must keep the R17 order: builtins first, then
    argv -D/-U left-to-right (interaction unchanged)."""
    out, _ = diff_snippet(tmp_path,
                          "#if __STDC__ == 0\nZERO\n#else\nONE\n#endif\n",
                          extra=["-std=gnu89", "-U__STDC__",
                                 "-D__STDC__=0"])
    assert "ZERO" in norm(out)
    out2, _ = diff_snippet(tmp_path, "#ifdef __SIZEOF_INT128__\nYES\n"
                                     "#else\nNO\n#endif\n",
                           extra=["-std=gnu89", "-U__SIZEOF_INT128__"],
                           fname="t2.c")
    assert "NO" in norm(out2)


