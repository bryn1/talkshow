# LINES reason: one wave (M4 W-S COMMIT-1, empty-anon completion at the
# ONE tag-identity seam, card 12404.2.95): every leg is an arm of the
# EMPTY-struct law table; splitting would separate a law row from its
# value witness.
r"""M4 W-S COMMIT-1 (MC 12716) — the EMPTY anon struct joins the layout
subset at the W-Q tag-identity seam (blcc/types.py — the ONLY two sites
where the defined/incomplete law still keyed on FALSY members; the
parser seam was W-Q'd to `is None` and the W-Q mint `<anon@file:line#N>`
identity carries an empty definition untouched).

THE gcc 11.4 -Os LAW TABLE (own-hands ws_laws.py rows s01..s13, out/
laws-gcc.txt; blcc posture measured at tip = LOUD "undefined struct
'<anon@…>'" on every empty row):
  s01/s02/s03  sizeof(struct {}) = 0 — C FORBITS, gcc ANSWERS 0.
  s04/s05      empty MEMBER occupies ZERO bytes and aligns 1: the next
               member sits at the SAME offset it would without it
               ({c,{},d} measures size 2, d@1).
  s06          two empty objects get DISTINCT addresses (the §-law
               blcc gets free from the min-8 frame slot).
  s07          nested-empty inside a defined struct pairs (already in —
               regression arm).
  s08          array of empty: sizeof = 0*n = 0.
  s09          anon-member promotion pairs (already in — regression arm).
  s11          two DISTINCT anon typedefs keep distinct identities
               (same-line mint #N — the mis-decl guard, gate s07 kin).
  s12          packed × empty (W-F layout interaction): the empty
               member shifts NOTHING under packed either (8/1).
  s13          address-of-empty-field == the OUTER address — EXACTLY
               the spinlock.h:184:58 `&lock->raw_lock` law.
  s14          empty struct as PARAM and as RETURN value: gcc accepts
               (copy of nothing); values unobservable, posture pairs.
Stream pin: init_main.c.i (the walk's init/main.o TU — the verbatim
spinlock.h:184:58 stream) — the anon wall MOVES (F-4 WALL-IS-A-QUEUE:
it lands on the named behind class, W-P/W-Q/W-R pin precedent).
"""
import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.environ.get("BLCC_REPO") or os.path.dirname(HERE)
PINNED = "/home/claudecode/Blaha/.tmp/m4-plan/streams"
REC = ["-Os", "-mno-sse", "-mno-mmx", "-mno-80387", "-fno-stack-protector",
       "-fno-pic"]


def blcc(args):
    return subprocess.run([sys.executable, "-m", "blcc"] + args,
                          capture_output=True, text=True, cwd=REPO,
                          env={"PYTHONPATH": REPO, "PATH": "/usr/bin:/bin"})


def _run(p):
    return subprocess.run([p], env={"PATH": "/usr/bin:/bin"}).returncode


def _pair(tag, src):
    """Compile BOTH sides, link blcc through gcc -no-pie (house idiom),
    run BOTH under a timeout, assert the exit codes are EQUAL."""
    c = "/dev/shm/ws1_%s.c" % tag
    open(c, "w").write(src)
    g = subprocess.run(["gcc", "-std=gnu89"] + REC +
                       [c, "-no-pie", "-o", "/dev/shm/ws1_%s.g" % tag],
                       capture_output=True, text=True)
    assert g.returncode == 0, "law row must be valid C: " + g.stderr
    gex = _run("/dev/shm/ws1_%s.g" % tag)
    o = "/dev/shm/ws1_%s.o" % tag
    b = blcc(["-c", c, "-o", o])
    assert b.returncode == 0, "empty-struct law must COMPILE: " + b.stderr
    assert subprocess.run(["gcc", "-no-pie", o, "-o", "/dev/shm/ws1_%s.b"
                           % tag], capture_output=True).returncode == 0
    assert _run("/dev/shm/ws1_%s.b" % tag) == gex, "%s: value pair" % tag


def test_ws1_empty_sizes_members():
    _pair("s01", "int main(){return (int)sizeof(struct {});}")
    _pair("s03", "typedef struct { } a_t; int main(){return (int)sizeof(a_t);}")
    _pair("s04", "typedef struct { } a_t; struct S { a_t a; int x; };"
          "int main(){struct S s; s.x=7; return s.x;}")
    _pair("s05", "struct W { char c; struct {} e; char d; };"
          "int main(){return (int)sizeof(struct W);}")          # 2: d@1
    _pair("s06", "int main(){struct {} q; struct {} p;"
          "return (&q==&p)?1:0;}")                              # distinct
    _pair("s08", "int main(){struct {} z[4]; return (int)sizeof(z)/8;}")


def test_ws1_identity_and_packed():
    # s11: distinct anon typedefs on ONE line — the mint #N guard (the
    # identity is the FULL minted tag, never name/line alone).
    _pair("s11", "typedef struct { int a; } t1; typedef struct { char b; } t2;"
          "int main(){t1 x; t2 y; return (int)(sizeof x*10 + sizeof y);}")
    _pair("s11b", "typedef struct { } e1_t; typedef struct { } e2_t;"
          "int main(){e1_t x; e2_t y;"
          "return (&x==&y)?1:(int)(sizeof x + sizeof y);}")
    # s12: packed x W-F — the empty member shifts nothing.
    _pair("s12", "struct __attribute__((__packed__)) PK { struct {} e;"
          " long v; }; int main(){return (int)sizeof(struct PK);}")


def test_ws1_address_of_empty_field():
    # s13: THE spinlock.h:184:58 law — &of an empty field == outer.
    _pair("s13", "struct N { struct {} z; char a[3]; };"
          "int main(){struct N n; return (int)(&n.z==(void*)&n);}")
    _pair("s13b", "struct E { int a; }; typedef struct { struct E in; } h;"
          "int main(){h v; v.in.a=5; return v.in.a;}")          # s07 nested


def test_ws1_empty_param_return():
    # s14: empty struct as PARAM and RETURN posture (gcc accepts).
    _pair("s14", "typedef struct { } e_t; e_t g(void){ e_t r; return r; }"
          "void f(e_t q); void f(e_t q){ (void)q; }"
          "int main(){ e_t x; f(x); f(g()); struct {} p;"
          "struct {} *pp=&p; return (int)(sizeof x + 3*(pp!=0));}")
    # s15: zero-byte COPY posture — assignment writes NOTHING and the
    # objects keep their own addresses (load answers the determinate 0,
    # the content is UNOBSERVABLE by construction).
    _pair("s15", "typedef struct { } e_t; e_t g(void){ e_t r; return r; }"
          "int main(){ e_t x, y; y = x; x = g(); y = (e_t){}; (void)x;"
          "(void)y; return (int)(&x==&y) + 7; }")


def test_ws1_anon_inside_asmgoto_splice():
    # INTERACTION TU (DoD): the EMPTY struct INSIDE a W-R asm-goto
    # splice — a local of type `struct {}` in the spliced body rides
    # the slot law (min-8 frame slot, distinct addresses), the imm-map
    # and the per-site label mint are UNTOUCHED by the completion.
    _pair("ix1", "typedef unsigned short u16; typedef int bool;"
          "typedef struct { } lk_t;\nchar fakecap[64];\n"
          "static inline __attribute__((__always_inline__)) bool f(u16 bit)\n"
          "{ lk_t held; (void)held;\n"
          "  asm goto(\"testb %[bitnum], %[cap]\\n\\t\" \"jnz %l[t_yes]\\n\\t\"\n"
          "           \"jmp %l[t_no]\\n\\t\"\n"
          "           : : [bitnum] \"i\" (1 << (bit & 7)), [cap] \"m\""
          " (fakecap[bit >> 3])\n           : : t_yes, t_no);\n"
          "  return 0;\nt_yes: return 1;\nt_no: return 0; }\n"
          "int main(void){ fakecap[0]=2; lk_t top;"
          "return (f(1) + (&top!=0)*0) & 0xff; }")


def test_ws1_empty_global_keeps_advance():
    # The zsize distinct-address law stays ARMED on the completed class:
    # an empty-struct global must not make the NEXT global share its
    # address (.zero-advance family, card MC 12460's concern).
    _pair("adv", "struct es { };\nstruct es es0;\nlong after;\n"
          "int main(void){return (int)(&(es0)==(void*)&after);}")


def test_ws1_spinlock_stream_wall_moved():
    """The verbatim spinlock.h:184:58 stream (the walk's init/main.o TU,
    init_main.c.i): RED-FIRST at tip — the first wall today is EXACTLY
    `sema: undefined struct '<anon@…:1897#8>'` at the `&lock->raw_lock`
    site (:11442:58 clean). COMMIT-1 eats it; the F-4 queue law says the
    wall LANDS BEHIND on the __label__/__here class (COMMIT-2's leg)."""
    if not os.path.isdir(PINNED):
        import pytest
        pytest.skip("pinned corpus not linked (builder posture)")
    import re as _re
    lm = _re.compile(r"^#\s+\d+\s+\"")
    clean = "/dev/shm/ws1_init_main_clean.c"
    with open(PINNED + "/init_main.c.i", errors="replace") as fh, \
            open(clean, "w") as oh:
        for ln in fh:
            if not lm.match(ln):
                oh.write(ln)
    r = blcc(["-c", clean, "-o", "/dev/shm/ws1_init_main.o"])
    first = next(ln for ln in r.stderr.splitlines() if ln.strip()) \
        if r.stderr else ""
    if r.returncode == 0:
        # COMMIT-2 landed and the whole TU takes — acceptable at close
        # posture ONLY if it really compiles (queue fully cleared).
        return
    assert "undefined struct '<anon" not in first, \
        "the empty-anon wall must be EATEN by COMMIT-1 (RED-FIRST pin): " \
        + first[:200]
