# LINES reason: one COMMIT-0 wave of legs (M4 W-S gate-F-1 repair, card
# 12404.2.95): all three legs witness ONE law — the StmtExpr-refusal
# clause was dead and is REMOVED; a split would separate the law from
# its witnesses.
r"""M4 W-S COMMIT-0 (MC 12716) — gate 12715 F-1 REPAIR.

THE LAW: the W-R named refusal "asm-goto body with a statement-
expression" was STRUCTURALLY DEAD and is REMOVED (not made reachable —
the shape MEASURES PAIR, so refusing it would make blcc LOUDER than
gcc on a measured-pairing body for no safety gain; the dangerous
nested shape is owned by the label-law clauses, leg 3). Deadness,
own-hands (the gate's stated mechanism "_is_stmt(StmtExpr)=False" was
a probe bug — the tree measures True; the REAL deadness is the walker):
`stmt_children` returns [] for VarDecl/ExprStmt, and a StmtExpr lives
ONLY in expression fields, so `_stmts_of` can never surface one and
`isinstance(s, ast.StmtExpr)` over it can never fire.

Legs:
 1. test_ws0_stmtexpr_body_splices — gate x15 shape (StmtExpr in a DECL
    INITIALIZER of an asm-goto candidate): SPLICES, value-pairs gcc, and
    the removed message never appears (a REACHABLE re-add would flip
    this leg RED: the refusal would make rc!=0).
 2. test_ws0_se1_nested_asmgoto_loud — gate se1 shape (asm-goto NESTED
    in the stmtexpr targeting a flat-top label): the TRUE guard is the
    label law — the goto-name walk is statement-based, the flat label
    looks untargeted, the CALL law stands and the copy's S5/L4 'i' twin
    answers LOUD. NEVER silent; no StmtExpr-message claim.
 3. test_ws0_stmts_of_never_surfaces_stmtexpr — the walker unit law
    proving the clause could not fire (documents WHY it was dead; if
    stmt_children ever starts yielding expression nodes, this pin
    screams and the law must be re-measured before any revival).
"""
import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.environ.get("BLCC_REPO") or os.path.dirname(HERE)
sys.path.insert(0, REPO)


def blcc(args):
    return subprocess.run([sys.executable, "-m", "blcc"] + args,
                          capture_output=True, text=True, cwd=REPO,
                          env={"PYTHONPATH": REPO, "PATH": "/usr/bin:/bin"})


def _run(p):
    return subprocess.run([p], env={"PATH": "/usr/bin:/bin"}).returncode


def _cc(tag, src, extra=()):
    c = "/dev/shm/ws0_%s.c" % tag
    open(c, "w").write(src)
    return blcc(["-c", c, "-o", "/dev/shm/ws0_%s.o" % tag, *extra]), c


BEH = """
typedef unsigned short u16;
typedef int bool;
char fakecap[64];
static inline __attribute__((__always_inline__)) bool f(u16 bit)
{
    int pre = ({ 40 + 2; });
    asm goto("testb %[bitnum], %[cap]\\n\\t" "jnz %l[t_yes]\\n\\t"
             "jmp %l[t_no]\\n\\t"
             : : [bitnum] "i" (1 << (bit & 7)), [cap] "m" (fakecap[bit >> 3])
             : : t_yes, t_no);
    return 0;
t_yes: return pre - 40;
t_no:  return 0;
}
int main(void) { fakecap[0] = 2; return f(1) & 0xff; }
"""

SE1 = """
typedef unsigned short u16;
typedef int bool;
char fakecap[64];
int g;
static inline __attribute__((__always_inline__)) bool f(u16 bit)
{
t_yes:
    g = ({ asm goto("testb %[bitnum], %[cap]\\n\\t" "jz %l[t_yes]\\n\\t"
                    : : [bitnum] "i" (1 << (bit & 7)),
                     [cap] "m" (fakecap[bit >> 3]) : : t_yes); 5; });
    return 0;
}
int main(void) { fakecap[0] = 2; f(1); return g ? 5 : 9; }
"""


def test_ws0_stmtexpr_body_splices():
    # Leg 1: the x15 body SPLICES and value-pairs; the dead refusal is
    # gone from the observable surface (message grep-zero on stderr).
    b, c = _cc("beh", BEH)
    assert b.returncode == 0, "x15 body must compile: " + b.stderr
    assert "statement-expression" not in b.stderr
    g = subprocess.run(["gcc", "-std=gnu89", "-Os", "-mno-sse", "-mno-mmx",
                        "-mno-80387", "-fno-stack-protector", "-fno-pic",
                        "-no-pie", c, "-o", "/dev/shm/ws0_beh.g"],
                       capture_output=True, text=True)
    assert g.returncode == 0, g.stderr
    assert gcc_link_run("/dev/shm/ws0_beh.o", "/dev/shm/ws0_beh.b") == \
        _run("/dev/shm/ws0_beh.g") == 2, "value pair (taken arm = 2)"


def gcc_link_run(o, out):
    assert subprocess.run(["gcc", "-no-pie", o, "-o", out],
                          capture_output=True, text=True,
                          env={"PATH": "/usr/bin:/bin"}).returncode == 0
    return _run(out)


def test_ws0_se1_nested_asmgoto_loud():
    # Leg 3's counterpart: the nested shape stays LOUD — and it is the
    # label law that owns it (call posture -> copy's S5/L4 'i' wall),
    # never the (removed) stmtexpr clause, never silent.
    b, _ = _cc("se1", SE1)
    assert b.returncode != 0, "nested asm-goto must stay LOUD"
    assert "statement-expression" not in b.stderr
    first = b.stderr.splitlines()[0]
    assert "constraint 'i'" in first, "true guard = the CALL-law copy's " \
        "S5/L4 wall: " + first


def test_ws0_stmts_of_never_surfaces_stmtexpr():
    # The walker law: WHY the clause was dead (own probe f1_dead.py).
    from blcc import ast
    from blcc.inliner import _stmts_of
    from blcc.parser import parse_text
    src = "int f(void) { int v = ({ 1; }); v = ({ v; }); return v; }\n"
    tu = parse_text(src, "ws0.c")
    fd = [u for u in tu.decls if isinstance(u, ast.FuncDecl)][0]
    surfaced = _stmts_of(fd.body)
    assert not any(isinstance(s, ast.StmtExpr) for s in surfaced), \
        "stmt_children never yields expression nodes: a StmtExpr " \
        "isolation test over _stmts_of can NEVER fire (deadness law)"
    # and the tree DOES treat StmtExpr as a _is_stmt (the gate's probe
    # claimed False via a positional-args TypeError; measured True):
    from blcc.inliner import _is_stmt
    assert _is_stmt(ast.StmtExpr("ws0.c", 1, 1, (), None))
