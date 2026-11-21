# LINES reason: one law (M4 W-V COMMIT-V, card 12747): the void-value
# 2.4c DISCARD-context law ships with its one-level machinery, the
# risk-seam-3 negatives, the G-pairing interaction and the 7-stream
# queue — one law, one file.
r"""M4 W-V COMMIT-V (MC 12747) — the §2.4c void-value law, SHIPPED
AFTER G, NEVER ALONE (measured: +3 over {E} alone, +5 once G ships —
early-quirks and 8250_port carry G as their SECOND wall).

THE gcc 11.4 -Os REC LAW (sims rows e19/e23 accept; e24 + e20-e22
unchanged): a VOID statement-group `({…;})` is legal wherever its value
is provably DROPPED — a discarded conditional arm (the udelay() family,
the 7-stream §2.4c class) and the LHS of a comma (row e23, already
right at tip). It is NOT legal where a value is OWED: one void ternary
arm in a value context (e24 — gcc "void value not ignored", LOUD both
sides) — and risk seam 3 names the shapes that must NOT inherit the
context: assign-RHS, call-arg, binary-operand (tip postures, byte-
identical through this commit: e20/e22 QUIET, e21 the KeyError ICE —
all pinned below as pre-existing named divergences, none widened).

The mechanism is ONE one-level context: `_emit_expr` consumes
`_discarding` into `_discarded_parent` at dispatch; only the statement
arm, the comma LHS and the arms of a DISCARDED conditional re-arm it.
Every other descent REQUIRES a value, so the context CANNOT reach the
seam-3 doors by construction.
"""
import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.environ.get("BLCC_REPO") or os.path.dirname(HERE)
STREAMS = os.path.join(REPO, "..", ".tmp", "m4-plan", "streams")
REC = ["-std=gnu89", "-Os", "-mno-sse", "-mno-mmx", "-mno-sse2",
       "-mno-80387", "-fno-stack-protector", "-fno-pic"]
ENV = {"PYTHONPATH": REPO, "PATH": "/usr/bin:/bin"}


def blcc(args):
    return subprocess.run([sys.executable, "-m", "blcc"] + args,
                          capture_output=True, text=True, cwd=REPO, env=ENV)


def _w(tag, src):
    c = "/dev/shm/wv4_%s.c" % tag
    open(c, "w").write(src)
    return c


def _pair(tag, src):
    c = _w(tag, src)
    g = subprocess.run(["gcc"] + REC + [c, "-no-pie", "-o",
                                        "/dev/shm/wv4_%s.g" % tag],
                       capture_output=True, text=True)
    assert g.returncode == 0, "row must be valid C: " + g.stderr
    gex = subprocess.run(["/dev/shm/wv4_%s.g" % tag],
                         env={"PATH": "/usr/bin:/bin"}).returncode
    o = "/dev/shm/wv4_%s.o" % tag
    b = blcc(["-c", c, "-o", o])
    assert b.returncode == 0, "%s must compile (RED-first: tip LOUDs " \
        "§2.4c): " % tag + b.stderr
    assert subprocess.run(["gcc", "-no-pie", o, "-o",
                           "/dev/shm/wv4_%s.b" % tag],
                          capture_output=True).returncode == 0
    bex = subprocess.run(["/dev/shm/wv4_%s.b" % tag],
                         env={"PATH": "/usr/bin:/bin"}).returncode
    assert bex == gex, "%s run-pair: blcc=%d gcc=%d" % (tag, bex, gex)


# ---- VERBATIM corpus witnesses (>=3 required; 3 shipped) ----------------

UD_HEAD = ("void __const_udelay(unsigned long xloops){ (void)xloops; }\n"
           "void __udelay(unsigned long usecs){ (void)usecs; }\n"
           "void __bad_udelay(void){ }\n")


def test_wv4_early_quirks_udelay10_verbatim():
    # VERBATIM arch_x86_kernel_early-quirks.c.i:52378:45 — the udelay(10)
    # expansion: a ternary with BOTH arms void statement-groups, used as
    # an expression statement (value dropped). gcc rc0; tip LOUDs
    # "void value not ignored as it ought to be (§2.4c)".
    _pair("u10", UD_HEAD +
          "int q_ud(void){\n"
          "  ( (__builtin_constant_p(10) && (10)<=5) ? "
          "({ if (__builtin_constant_p((10)*1000)) { if (((10)*1000) / "
          "20000 >= 1) __bad_udelay(); else __const_udelay(((10)*1000) "
          "* 0x10c6ful); } else { __udelay((10)*1000); } }) : "
          "({ unsigned long __ms=(10); while (__ms--) { "
          "__const_udelay(1000); } }) );\n"
          "  return 5; }\n"
          "int main(void){ return q_ud(); }\n")


def test_wv4_pci_udelay1_verbatim():
    # VERBATIM drivers_pci_pci.c.i:50325:43 — the same family, udelay(1)
    # spelling (a SECOND stream proves it is the macro, not a quirk).
    _pair("u1", UD_HEAD +
          "int q_u1(void){\n"
          "  ( (__builtin_constant_p(1) && (1)<=5) ? "
          "({ if (__builtin_constant_p((1)*1000)) { if (((1)*1000) / "
          "20000 >= 1) __bad_udelay(); else __const_udelay(((1)*1000) "
          "* 0x10c6ful); } else { __udelay((1)*1000); } }) : "
          "({ unsigned long __ms=(1); while (__ms--) { ; } }) );\n"
          "  return 6; }\n"
          "int main(void){ return q_u1(); }\n")


def test_wv4_jobctrl_comma_lhs_verbatim():
    # VERBATIM drivers_tty_tty_jobctrl.c.i:31596 `for (({ ; }), (p) = …`
    # — the comma-LHS void group at the head of a for-init (row e23).
    _pair("jc", "int main(void){ int p; for (({ ; }), p = 3; p > 0; p--) "
                 "; return p + 4; }\n")


# ---- own shapes (sims law table) -----------------------------------------

def test_wv4_e19_void_arms_pair():
    _pair("e19", "void fv(void){}\nint g;\nint f(int c){ g=0;\n"
                  "  ( c ? ({ if (c) fv(); else fv(); })\n"
                  "      : ({ while (g < 2) { g++; fv(); } }) );\n"
                  "  return g; }\n"
                  "int main(void){ return f(0); }\n")


def test_wv4_e24_ternary_one_void_in_value_stays_loud():
    # The over-accept guard: value-context ternary with ONE void arm is
    # gcc LOUD ("void value not ignored") — Law V must NOT reach it.
    c = _w("e24", "void fv(void){}\n"
                   "int main(void){ int t = 1 ? ({ fv(); }) : 5; "
                   "return t+1; }\n")
    g = subprocess.run(["gcc"] + REC + ["-c", c, "-o", "/dev/null"],
                       capture_output=True, text=True)
    assert g.returncode == 1, "gcc LOUDS: " + g.stderr
    b = blcc(["-c", c, "-o", "/dev/null"])
    assert b.returncode == 2, "e24 must stay LOUD (value owed): " + b.stderr


def test_wv4_risk_seam3_postures_unchanged():
    # e20 (assign RHS) and e22 (call arg) stayed tip-QUIET through V;
    # e21 (binary operand) stays the named rc2. The measured V stub
    # NEITHER fixes NOR widens them — this leg pins "unchanged", NOT
    # "correct": they are named divergences with corpus volume 0.
    c = _w("e20", "void fv(void){}\nint v;\nint main(void){ v = "
                   "({ fv(); }); return 3; }\n")
    b = blcc(["-c", c, "-o", "/dev/shm/wv4_e20.o"])
    assert b.returncode == 0, "e20 tip posture (QUIET) unchanged: " \
        + b.stderr
    c = _w("e21", "void fv(void){}\nint v;\nint main(void){ v = "
                   "({ fv(); }) + 1; return 3; }\n")
    b = blcc(["-c", c, "-o", "/dev/null"])
    assert b.returncode == 2, "e21 tip posture (rc2) unchanged: " + b.stderr


def test_wv4_reads_a_G_initialized_global():
    # THE ORDERING WITNESS (V after G, never alone): the discarded arm
    # writes through a global whose initializer rode COMMIT-G's chain
    # law. Without G this TU walls at the initializer — the pair-ship
    # ordering is what the fixpoint measured ({E+V}=227 < {E+G+V}=268).
    _pair("gv", "struct L { int v; };\nstruct L obj = { 41 };\n"
                 "int *gp = &(obj.v);\nvoid fv(void){}\n"
                 "int f(int c){ ( c ? ({ *gp = 1; fv(); }) "
                 ": ({ *gp = 2; fv(); }) ); return obj.v; }\n"
                 "int main(void){ return f(0) == 2 ? 8 : 3; }\n")


# ---- corpus queue legs (7-stream §2.4c family, lands NAMED) ------------

def _first_wall(stream):
    import pytest
    if not os.path.isdir(STREAMS):
        pytest.skip("corpus streams absent (worktree posture)")
    import re
    su = re.compile(r"\b(0[xX][0-9a-fA-F]+|[0-9]+)[uU][lL]{0,2}\b")
    sl = re.compile(r"\b(0[xX][0-9a-fA-F]+|[0-9]+)[lL]+\b")
    clean = "/dev/shm/wv4_%s" % stream
    if not os.path.exists(clean):
        with open(os.path.join(STREAMS, stream),
                  encoding="utf-8", errors="replace") as fh, \
                open(clean, "w", encoding="utf-8") as out:
            for line in fh:
                if line.startswith("#"):
                    continue
                out.write(sl.sub(r"\1", su.sub(r"\1", line)))
    r = blcc(["-c", clean, "-o", "/dev/null"])
    first = ""
    for ln in r.stderr.splitlines():
        if ln.strip():
            first = ln
            break
    return r.returncode, first


def test_wv4_four_streams_now_green():
    # sims §4 predicted 3 at {E+2.4c}; with G shipped early-quirks
    # joined (it carried G as its SECOND wall — the +5-in-G-context).
    for s in ("drivers_rtc_rtc-mc146818-lib.c.i",
              "drivers_tty_tty_jobctrl.c.i",
              "lib_is_single_threaded.c.i",
              "arch_x86_kernel_early-quirks.c.i"):
        rc, first = _first_wall(s)
        assert rc == 0, s + " must ACCEPT at ship bytes: " + first[:150]


def test_wv4_the_other_three_rewall_named():
    # honest queue movement: the class dies, the streams land BEHIND
    # other, NAMED classes (measured own hands).
    for s, needle in (
            ("drivers_pci_pci.c.i", "bitfield member initializer"),
            ("drivers_tty_serial_8250_8250_port.c.i", "no member 'ier'"),
            ("kernel_panic.c.i", "address initializer inside a union")):
        rc, first = _first_wall(s)
        assert "void value not ignored" not in first, \
            s + ": the V-class wall must be EATEN: " + first[:150]
        assert needle in first, s + ": must re-wall on the NAMED " \
            "behind-class %r: " % needle + first[:170]
