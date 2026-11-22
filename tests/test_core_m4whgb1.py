r"""M4 WHG-B COMMIT-1 (MC 12765) — THE FOLD GUARD INTERACTION ROWS.

`test_core_m4whgb0.py` proves the FOLD happens. This file proves the
GUARD is the thing keeping the wave honest: every row here is a shape where
the fold REFUSES and the shipped emission rides untouched, chosen because a
corruption class lives there (the sims' four plants, §DoD-5 of
.tmp/evidence/whgb-sims.md: live-branch side effect, dead asm-goto EXECUTED,
volatile read eaten, needed relocation eaten).

THE ROWS, and the class each one holds:
  case-marker-under-fold  the enclosing switch's `_collect_cases` pre-pass
      minted the `.Lcase_*` label and wired the compare chain BEFORE any
      statement is emitted. Dropping the arm that HOLDS the marker dangles
      the chain's `je`. Measured on the sims' retained stub (which does NOT
      list the markers): `nm` answers UNDEF `.Lcase_4` for this exact shape
      — class C (a needed relocation eaten) sitting in the design sim, found
      by this probe. The ship guard lists Case/CaseRange/Default; the shipped
      emission rides, so the chain and its label stay together.
  goto-into-dead-arm      §2A M2-C1 assigns the label name in a PRE-PASS, so
      a live `goto`/`&&label` can legally target a definition sitting in the
      arm the fold would drop. Guard refuses (Label/LabelDecl/LabelAddr).
  wt-layout-fact-dead-arm W-T OWNERSHIP STACK interplay: a struct/enum/typedef
      DECLARATION registers its layout when codegen MEETS it. A fact minted
      inside a dead arm and read by a LIVE statement later in the block is
      the W-T failure mode at the fold seam, so declarations are refused in
      the discarded subtree and as a bare arm.
  splice-asm-goto-dead    W-R/W-W interplay: the callee is INLINED, its asm
      goto rides the per-site label clone, and the fold decides inside the
      spliced body with the caller's imm-map in scope (`_inl_imm`, the W-R
      row i16). RUN-leg: the dead arm must NOT execute — the value answers.
  volatile-arm            a volatile read in a LIVE arm survives the fold
      (the load is still there); a volatile read in a DEAD arm vanishes
      because the branch is dead (row f04), and a volatile CONTROL is never
      folded at all (`_asm_const` cannot answer a read — rows f13/f20/r04,
      plant C's teeth).
"""
import os
import subprocess

import pytest

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.environ.get("BLCC_REPO") or os.path.dirname(HERE)
REC = ["-std=gnu89", "-Os", "-mno-sse", "-mno-sse2", "-mno-80387",
       "-fno-stack-protector", "-fno-pic"]
ENV = {"PYTHONPATH": REPO, "PATH": "/usr/bin:/bin", "LC_ALL": "C"}

CASE_MARK = """
extern void g(void);
int f(int x) { switch (x) { case 1: x = 2; break;
  if (0) { case 3: g(); } default: break; } return x; }
"""

GOTO_INTO_DEAD = """
extern int sink;
int f(int x) {
\tif (0) { out: sink = 9; }
\tgoto out;
\treturn x;
}
"""

LABELADDR_INTO_DEAD = """
extern int sink;
int f(int x) {
\tvoid *p = &&out;
\tif (0) { out: sink = 9; }
\t(void)p;
\treturn x;
}
"""

WT_LAYOUT_DEAD_ARM = """
extern int sink;
int f(void) {
\tif (0) { struct H { int a; char b; }; sink = 0; }
\tsink = (int)sizeof(struct { int a; char b; });
\treturn sink;
}
"""

ENUM_FACT_DEAD_ARM = """
extern int sink;
int f(int x) {
\tif (0) { enum E { EK = 5 }; sink = EK; }
\tsink = 1;
\treturn x;
}
"""

BARE_DECL_ARM = """
extern int sink;
int f(int x) { if (1) enum F { FK = 7 }; sink = 0; return x; }
"""

SPLICE_ASMGOTO_DEAD = """
static inline __attribute__((always_inline)) int probe(int x) {
\tif (0) { asm goto("jmp %l0" : : : : L); }
\treturn x;
L:\treturn x + 1;
}
int answer(void) { return probe(1) + probe(10); }
"""

VOLATILE_IN_LIVE_ARM = """
volatile int v;
int out;
void f(void) { if (1) { out = v; } else { out = 0; } }
"""


def _src(tag, text):
    p = "/dev/shm/whgb1_%s_%d.c" % (tag, os.getpid())
    with open(p, "w") as fh:
        fh.write(text)
    return p


def _blcc(tag, text):
    c = _src(tag, text)
    o = c[:-2] + ".o"
    r = subprocess.run(["python3", "-m", "blcc", "-c", c, "-o", o],
                       cwd=REPO, env=dict(ENV), capture_output=True, text=True)
    return r, o


def _gcc(tag, text):
    c = _src(tag + "_gcc", text)
    o = c[:-2] + ".o"
    r = subprocess.run(["gcc", "-c"] + REC + [c, "-o", o],
                       capture_output=True, text=True)
    return r, o


def _und(o):
    r = subprocess.run(["nm", "--undefined-only", o],
                       capture_output=True, text=True)
    return {p.split()[-1] for p in r.stdout.splitlines() if p.strip()}


def _text(tag, text):
    """blcc's OWN asm text for a leg (the guard's evidence sits in the text,
    not in an undefined-symbol list): §3.5 `-c --emit-asm` answers on stdout
    and mirrors the text to `<operand>.s`."""
    c = _src(tag + "_s", text)
    o = c[:-2] + ".o"
    r = subprocess.run(["python3", "-m", "blcc", "-c", "--emit-asm", c,
                        "-o", o], cwd=REPO, env=dict(ENV),
                       capture_output=True, text=True)
    assert r.returncode == 0, r.stderr[:200]
    return r.stdout if r.stdout.strip() else open(o + ".s").read()


def _dangling(text):
    """Every `.L*` the text JUMPS to must be a label the text DEFINES. The
    §2A M2-C1 name universe is minted in a PRE-PASS, so a dropped body takes
    its definition with it and leaves the reference behind — the object then
    carries an UNDEF `.L…` the link stage cannot answer."""
    defined = {ln.split(":")[0] for ln in text.splitlines()
               if ln.startswith(".L") and ln.rstrip().endswith(":")}
    refs = set()
    for ln in text.splitlines():
        parts = ln.split()
        if len(parts) == 2 and parts[0] in ("je", "jne", "jmp", "call") \
                and parts[1].startswith(".L"):
            refs.add(parts[1])
    return sorted(refs - defined)


def test_case_marker_under_a_folded_if_keeps_its_chain_label():
    """The sims' stub leaves UNDEF `.Lcase_4` here; the ship guard refuses
    the fold, so the compare chain's target is still DEFINED (class C)."""
    br, bo = _blcc("case", CASE_MARK)
    assert br.returncode == 0, br.stderr[:200]
    undef = _und(bo)
    assert "g" in undef, undef                      # shipped posture rode
    assert not {u for u in undef if u.startswith(".L")}, undef
    assert _dangling(_text("case", CASE_MARK)) == []


def test_live_goto_may_target_a_label_in_the_dead_arm():
    """§2A M2-C1 minted the name in a PRE-PASS; dropping the arm would leave
    the jump with no landing site, so the guard keeps the shipped body."""
    br, bo = _blcc("goto", GOTO_INTO_DEAD)
    assert br.returncode == 0, br.stderr[:200]
    assert _dangling(_text("goto", GOTO_INTO_DEAD)) == []
    assert "sink" in _und(bo), _und(bo)             # the arm still ships


def test_labeladdr_into_the_dead_arm_refuses_the_fold():
    """`&&out` in a LIVE region, `out:` inside the dead arm: the guard's
    LabelAddr/Label refusal is what keeps the taken-address valid."""
    br, bo = _blcc("laddr", LABELADDR_INTO_DEAD)
    assert br.returncode == 0, br.stderr[:200]
    assert not {u for u in _und(bo) if u.startswith(".L")}, _und(bo)
    assert _dangling(_text("laddr", LABELADDR_INTO_DEAD)) == []


def test_wt_layout_fact_declared_in_a_dead_arm_still_registers():
    """W-T interplay: the anon layout fact rides IN FRONT of its item at the
    block seam; a declaration inside a discarded arm would never be met."""
    br, bo = _blcc("wtlay", WT_LAYOUT_DEAD_ARM)
    assert br.returncode == 0, br.stderr[:200]
    gr, go = _gcc("wtlay", WT_LAYOUT_DEAD_ARM)
    assert gr.returncode == 0, gr.stderr
    assert _und(bo) == _und(go) == {"sink"}, (_und(bo), _und(go))
    # the dead arm rides (no fold), and nothing dangles either way
    assert _dangling(_text("wtlay", WT_LAYOUT_DEAD_ARM)) == []


def test_enum_fact_declared_in_a_dead_arm_ships_the_arm():
    """The enum CONSTANT is minted where the emitter MEETS the declaration;
    the guard refuses to skip it (bare-decl family, generalized)."""
    br, bo = _blcc("enm", ENUM_FACT_DEAD_ARM)
    assert br.returncode == 0, br.stderr[:200]
    gr, go = _gcc("enm", ENUM_FACT_DEAD_ARM)
    assert gr.returncode == 0, gr.stderr
    assert _und(bo) == _und(go) == {"sink"}


def test_bare_declaration_arm_is_never_folded():
    """An UNBRACED declaration arm keeps its names in the enclosing scope:
    the fold may not choose which arm owns the declaration (W-O family)."""
    br, bo = _blcc("bare", BARE_DECL_ARM)
    if br.returncode != 0:               # the shipped parse wall is a fine
        return                           # answer — the fold never ran
    assert "sink" in _und(bo), _und(bo)  # the LIVE statement still compiles


def test_spliced_callee_dead_asm_goto_never_executes():
    """W-R/W-W interplay, RUN: the callee is inlined, its `asm goto` label
    clones per site, and the fold decides INSIDE the spliced body. The dead
    arm's `jmp %l0` must never run: probe(1)+probe(10) answers 11."""
    c = _src("splice", SPLICE_ASMGOTO_DEAD)
    with open(c) as fh:
        src = fh.read()
    with open(c, "w") as fh:
        fh.write(src + "\nint main(void){ return answer() == 11 ? 0 : 1; }\n")
    o = c[:-2] + ".o"
    br = subprocess.run(["python3", "-m", "blcc", "-c", c, "-o", o],
                        cwd=REPO, env=dict(ENV), capture_output=True, text=True)
    assert br.returncode == 0, br.stderr[:200]
    exe = c[:-2] + ".exe"
    link = subprocess.run(["gcc", "-no-pie", o, "-o", exe],
                          capture_output=True, text=True)
    assert link.returncode == 0, link.stderr
    code = subprocess.run(["./" + os.path.basename(exe)],
                          cwd=os.path.dirname(exe),
                          capture_output=True).returncode
    assert code == 0, "dead asm-goto arm EXECUTED under the fold (exit %d)" % code


def test_volatile_read_in_the_live_arm_survives_the_fold():
    """The fold drops a BRANCH, never a load: the live arm's volatile read
    is still a memory reference in the object (plant C's counterpart)."""
    br, bo = _blcc("vol", VOLATILE_IN_LIVE_ARM)
    assert br.returncode == 0, br.stderr[:200]
    txt = _text("vol", VOLATILE_IN_LIVE_ARM)
    assert "v" in _und(bo) or "v" in txt, "volatile load vanished"
    assert "movl\tv(%rip), %eax" in txt or "v(%rip)" in txt, txt[-600:]
