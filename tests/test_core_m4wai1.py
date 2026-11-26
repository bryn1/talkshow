# M4 W-AI THE OWED DOOR — the expansion-time deferral at the imm-context
# seams S1-S5 (MC 12404.2.153 / job 12846, card 12846). One concern: the
# deferral DOOR law rows (the sims 14-sentence family, run-encoded) and the
# refusal faces the door must leave UNMOVED.
r"""M4 W-AI COMMIT-1 — THE OWED DOOR: a `'i'`-class operand whose fold
fails inside the NEVER-EXPANDED standalone copy of a zero-site `static
inline` (no caller ever decided the operand) is DEFERRED, not refused: the
fold answers the third imm-context sentinel and the operand materializes
as the placeholder imm (the body has no caller — the bytes never execute;
gas rejects the reg-slot alternative — measured rc3 `%ecx' not allowed
with `testb'`). REUSE, ONE home: the SAME imm-context seam the shipped
splice imm-map rides — `_inl_analyze` (defer SET, S1), the compile-loop
emit decision (CONTEXT push/clear, S2), `_asm_fold`'s failed-fold arm
(sentinel ANSWER, S3), the `_asm_opnd` S5/L4 arm (MATERIALIZE, S4). The
two EXISTING imm contexts (spliced-site map, global-init closure) are
UNTOUCHED (S5) — the door is the THIRD context beside them.

STANDING REJECTIONS (measured reasons, sims §2.3/§2.4 — this battery is
their run-encoded home): pp_expand/pp_args placement is DEAD on the corpus
(the streams are preprocessed `.i`; refusal is CODEGEN-time), and
slot-materialization is gas-invalid (rc3). Locals under `'i'` inside dead
copies STAY LOUD (param-anchoring: only an operand that itself mentions a
param of the copy defers — the r3 plant measures why). `'+'` never opens:
a DEFERRED `'+i'` keeps the SAME S5/L4 sentence. The crossing-`'i'` 2^32
over-loud face stays PINNED (not fixed). bcp (sema-phase) neither feeds
nor is fed (phase-order separation, sims §3.1 F1/F2).

Rows are VERBATIM transplants of the sims `law/src` probes on LIVE
cpufeature.h:187 shapes (the exit IS the answer; gcc REC twin + blcc,
`-no-pie`, run). ai01 is the walk-blocker shape itself: WALL at tip, PAIR
at ship — the RED-first row of this battery.
"""
import os
import subprocess
import sys

import pytest

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
REPO = os.environ.get("BLCC_REPO", ROOT)
sys.path.insert(0, REPO)
TMP = "/dev/shm/m4wai1_%s_%d" % (os.environ.get("M4WAI_TAG", "x"),
                                 os.getpid())
GCC_REC = ["-std=gnu89", "-Os", "-mno-sse", "-mno-sse2", "-mno-80387",
           "-fno-stack-protector", "-fno-pic"]
MAIN = "\nint answer(void);\nint main(void) { return answer(); }\n"

# cpufeature.h:187 VERBATIM shape (GOTO_FN), the walk blocker at the door:
GOTO = """char capb[64] = { CAPVAL };
static __inline__ int _my_cpu_has(unsigned bit)
{
\tasm goto("1: testb %[bitnum], %[cap_byte]\\n\\t"
\t\t "jnz %l[t_yes]\\n\\t"
\t\t "jmp %l[t_no]\\n"
\t\t : : [feature] "i" (bit), [bitnum] "i" (1 << (bit & 7)),
\t\t     [cap_byte] "m" (((const char *)capb)[bit >> 3])
\t\t : : t_yes, t_no);
\treturn 0;
t_yes:
\treturn 1;
t_no:
\treturn 0;
}
"""
PRE = "typedef unsigned int u32; typedef unsigned char u8;\ntypedef unsigned short u16; typedef unsigned long ul;\n"

# row -> (source WITHOUT the answer(), answer() body, posture)
# postures: ("PAIR",) exit is gcc's == blcc's; ("BOTHREFUSE",);
# ("LOUD", gcc_exit, sentence-or-None) blcc rc2 with that sentence.
ROWS = {
    # THE walk-blocker shape, zero-site copy: WALL rc2 at tip (S5/L4),
    # PAIR at ship (deferred imm-0 materialization). RED-FIRST row.
    "ai01_zero_site_verbatim": (GOTO.replace("CAPVAL", "32"), "return 42;", ("PAIR",)),
    # REAL sites answer as ALWAYS (the two existing imm contexts ride
    # untouched — the splice imm-map is NOT the door):
    "ai02_site_const_pair": (GOTO.replace("CAPVAL", "32"),
                             "return 40 + _my_cpu_has(5) + _my_cpu_has(6);",
                             ("PAIR",)),
    "ai03_runtime_site": (GOTO.replace("CAPVAL", "32"),
                          "volatile int v = 5; return 30 + _my_cpu_has(v);",
                          ("BOTHREFUSE",)),
    # an address-taken copy is LIVE — its 'i'(param) refusal stays LOUD
    # (the door is for copies NOBODY can call):
    "ai04_addr_taken": (GOTO.replace("CAPVAL", "32") + """int (*tbl[1])(unsigned) = { _my_cpu_has };
""", "return 7;", ("BOTHREFUSE",)),
    # constants inside a dead copy fold NORMALLY — the defer face is the
    # failed fold, not every fold (× const-fold row lives in m4wai2; this
    # is the law twin the placeholder arm must never swallow):
    "ai05_dead_const_ok": (PRE + """static __inline__ int deadv(void)
{
\tint r = 0;
\tasm("movl %1, %0" : "=r"(r) : "i"(8));
\treturn r;
}
""", "return 3;", ("PAIR",)),
    # '+i' at a dead copy: the DEFERRED answer must keep the SAME S5/L4
    # LOUD — the door never opens a readwrite face (r2_readwrite plant):
    "ai08_dead_plus_i_pinned": (PRE + """static __inline__ void dead8(unsigned bit)
{\tasm volatile("" : "+i"(bit));
}
""", "return 9;", ("LOUD", 9, "operand is not a "
                               "compile-time constant")),
    # a LIVE global (never an inline) keeps its LOUD refusal:
    "ai11_live_global": (PRE + """int g(int bit)
{\tint r = 0;
\tasm("movl %1, %0" : "=r"(r) : "i"(bit));
\treturn r;
}
""", "volatile int v = 3; return g(v);", ("BOTHREFUSE",)),
    # an alt constraint ('iq') keeps the house S2 posture at a dead copy —
    # the sentinel must NOT reach the alt path (reg-silent would open a
    # face the sims measured as reg/materialize-pair TODAY):
    "ai12_alt_iq_dead": (PRE + """static __inline__ int deadq(unsigned bit)
{\tasm volatile("" : : "iq"(bit));
\treturn 1;
}
""", "return 4;", ("PAIR",)),
    # 'g' = m, then i, then r (S4): a BARE param at 'g' resolves to the
    # reg form at BOTH trees (mem-first; the sentinel never reaches it —
    # sims §5 ai19/ai13 measurement; the r4 plant proves the g-guard that
    # keeps a SENTINEL out of `imm` is load-bearing on composed shapes).
    "ai13_g_face_dead": (PRE + """static __inline__ int deadg(unsigned bit)
{\tasm volatile("" : : "g"(bit));
\treturn 1;
}
""", "return 6;", ("PAIR",)),
    # bcp neither feeds nor is fed by the door (sema-phase; sims F1):
    "ai15_bcp_face": (PRE + """static __inline__ int bp(int x)
{\treturn __builtin_choose_expr(__builtin_constant_p(x), 1, 2);
}
""", "volatile int v = 4; return bp(v) + 40;", ("PAIR",)),
    # nested transitive: a zero-site outer calling the zero-site inner —
    # sites cover VALUE sites too (W-R law UNMOVED):
    "ai16_nested_transitive": (GOTO.replace("CAPVAL", "128") + """static __inline__ int outer(unsigned q)
{\treturn _my_cpu_has(q + 2);
}
""", "return 60 + outer(5) * 7;", ("PAIR",)),
    # LOCALS under 'i' inside a dead copy STAY LOUD (param-anchoring law;
    # r3_paramblind — deferral by BODY instead of OPERAND would turn these
    # two SILENT rc0):
    "ai17_dead_local_operand": (PRE + """static __inline__ int deadl(void)
{\tint x = 5;
\tint r = 0;
\tasm("movl %1, %0" : "=r"(r) : "i"(x));
\treturn r;
}
""", "return 5;", ("LOUD", 5, "constraint 'i' operand is not a "
                              "compile-time constant")),
    "ai18_dead_param_copy_local_operand": (PRE + """static __inline__ int deadp(unsigned bit)
{\tint x = bit + 1;
\tint r = 0;
\tasm("movl %1, %0" : "=r"(r) : "i"(x));
\treturn r;
}
""", "return 5;", ("LOUD", 5, "constraint 'i' operand is not a "
                              "compile-time constant")),
    "ai19_g_operand_in_template": (PRE + """static __inline__ int deadt(unsigned bit)
{\tint r = 0;
\tasm("movl %1, %0" : "=r"(r) : "g"(bit));
\treturn r;
}
""", "return 6;", ("PAIR",)),
    "ai20_g_composed_param_operand": (PRE + """static __inline__ int deadc(unsigned bit)
{\tint r = 0;
\tasm("movl %1, %0" : "=r"(r) : "g"(bit + 0));
\treturn r;
}
""", "return 6;", ("PAIR",)),
}


def _src(name):
    body, answer = ROWS[name][0], ROWS[name][1]
    return body + "int answer(void) { " + answer + " }\n"


def _sides(name):
    src = _src(name)
    os.makedirs(TMP, exist_ok=True)
    c = os.path.join(TMP, name + ".c")
    with open(c, "w") as fh:
        fh.write(src + MAIN)
    gexe = os.path.join(TMP, name + ".gcc")
    rg = subprocess.run(["gcc", "-no-pie"] + GCC_REC + [c, "-o", gexe],
                        capture_output=True, text=True)
    gx = None
    if rg.returncode == 0:
        gx = subprocess.run([gexe], capture_output=True, timeout=60).returncode
    o = os.path.join(TMP, name + ".blcc.o")
    rb = subprocess.run([sys.executable, "-m", "blcc", "-c", c, "-o", o],
                        capture_output=True, text=True,
                        env=dict(os.environ, PYTHONPATH=REPO), cwd=REPO)
    bx = None
    if rb.returncode == 0:
        l = subprocess.run(["gcc", "-no-pie", "-o", o + ".bin", o],
                           capture_output=True, text=True)
        assert l.returncode == 0, "blcc object must link:\n" + l.stderr[:300]
        bx = subprocess.run([o + ".bin"], capture_output=True,
                            timeout=60).returncode
    return rg, gx, rb, bx


@pytest.mark.parametrize("name", sorted(ROWS))
def test_wai_deferral_door_law(name):
    post = ROWS[name][2]
    rg, gx, rb, bx = _sides(name)
    if post[0] == "PAIR":
        assert rg.returncode == 0, "gcc twin must build:\n" + rg.stderr[:300]
        assert rb.returncode == 0, (
            "%s: blcc REFUSED rc=%d a shape the door lands (PAIR): "
            "the deferral died, or the shape stopped being zero-site:\n%s"
            % (name, rb.returncode, (rb.stdout + rb.stderr)[:300]))
        assert bx == gx, ("%s: SILENT divergence blcc %s vs gcc %s"
                          % (name, bx, gx))
    elif post[0] == "BOTHREFUSE":
        assert rg.returncode != 0, ("%s: gcc built it but the row is "
                                    "BOTH-REFUSE — the corpus oracle moved; "
                                    "re-measure before believing" % name)
        assert rb.returncode != 0, (
            "%s: blcc ACCEPTED a refusal face the door must leave UNMOVED "
            "(exit %s) — the deferral leaked past its zero-site/param "
            "conditions" % (name, bx))
    else:                              # LOUD: gcc answers, blcc refuses
        _, gcc_exit, sentence = post
        assert rg.returncode == 0 and gx == gcc_exit, (
            "%s: gcc moved off rc0 exit=%d (rc=%d exit=%s) — re-measure"
            % (name, gcc_exit, rg.returncode, gx))
        assert rb.returncode == 2, (
            "%s: the pinned LOUD face moved (rc=%d, blcc-exit=%s) — this "
            "face is NAMED, not this card's law" % (name, rb.returncode, bx))
        if sentence:
            assert sentence in (rb.stdout + rb.stderr), (
                "%s: rc2 but NOT the named sentence:\n%s"
                % (name, (rb.stdout + rb.stderr)[:300]))


# ---- kernel tier: the 14-sentence family the census moved (sims C3): 13
# LAND, defkeymap RE-WALLS one door later at the NAMED new sentence ------

from test_core_m4w1 import STREAMS                       # noqa: E402
from test_core_m4w25b import _clean_i                    # noqa: E402

GAINED_13 = ["arch_x86_kernel_cpu_intel_pconfig.c.i",
             "arch_x86_kernel_cpu_rdrand.c.i",
             "arch_x86_kernel_cpu_tsx.c.i",
             "arch_x86_kernel_platform-quirks.c.i",
             "lib_debug_locks.c.i",
             "lib_dec_and_lock.c.i",
             "lib_iomap_copy.c.i",
             "lib_irq_regs.c.i",
             "lib_lockref.c.i",
             "lib_rbtree.c.i",
             "lib_refcount.c.i",
             "lib_siphash.c.i",
             "lib_uuid.c.i"]


@pytest.mark.skipif(not (os.environ.get("KERNEL_510")
                         and os.path.isdir(STREAMS)),
                    reason="kernel tier + pinned streams corpus required")
@pytest.mark.parametrize("stream", GAINED_13)
def test_wai_door_lands_the_gained_13(stream, tmp_path):
    clean = _clean_i(os.path.join(STREAMS, stream), tmp_path, "wai")
    o = tmp_path / "wai.o"
    r = subprocess.run([sys.executable, "-m", "blcc", "-c", str(clean),
                        "-o", str(o)], capture_output=True, text=True,
                       env=dict(os.environ, PYTHONPATH=REPO), cwd=REPO)
    assert r.returncode == 0, (
        "%s must LAND at W-AI (the deferral door) — first wall:\n%s"
        % (stream, next((ln for ln in (r.stdout + r.stderr).splitlines()
                         if ln.strip()), "(no output)")))
    assert o.exists() and o.stat().st_size > 0, "empty object"


@pytest.mark.skipif(not (os.environ.get("KERNEL_510")
                         and os.path.isdir(STREAMS)),
                    reason="kernel tier + pinned streams corpus required")
def test_wai_defkeymap_rewalls_at_new_sentence(tmp_path):
    # the 14th family stream: the asm-'i' wall DIES and the stream re-walls
    # ONE door later — the door does NOT own the §4 globals-initializer
    # law (brief: NAMED, not closable here). The leg pins the NEW sentence
    # VERBATIM; if the §4 door ever opens, this leg flips and the sentence
    # is the retarget point.
    clean = _clean_i(
        os.path.join(STREAMS, "drivers_tty_vt_defkeymap.c.i"), tmp_path,
        "waikey")
    r = subprocess.run([sys.executable, "-m", "blcc", "-c", str(clean),
                        "-o", str(tmp_path / "waikey.o")],
                       capture_output=True, text=True,
                       env=dict(os.environ, PYTHONPATH=REPO), cwd=REPO)
    first = next((ln for ln in (r.stdout + r.stderr).splitlines()
                  if ln.strip()), "(no output)")
    assert r.returncode != 0, "defkeymap must NOT accept (the §4 wall is " \
                              "another card's law)"
    assert "global initializer must be an integer/char constant or " \
           "address-of-global" in first, \
        "defkeymap moved off its NEW re-wall sentence: " + first[:200]
    assert "constraint 'i' operand" not in first, \
        "the asm-'i' wall survived at defkeymap — the door missed it: " \
        + first[:200]
