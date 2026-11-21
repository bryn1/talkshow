# LINES reason: one wave (M4 W-U COMMIT-2, extern-local binding, card
# 12404.2.102): the legs are the two arms of ONE §2.8 law (known-outward
# drop / unknown-outward TU reference) plus the class it deliberately
# still refuses; splitting them separates a ship from its boundary.
r"""M4 W-U COMMIT-2 (MC 12739) — an `extern` LOCAL declaration: §2.8 at the
one seam blcc already drops it (blcc/parser.py, parse_decl).

THE gcc 11.4 -Os REC LAW (own hands, .tmp/m4-wu/shapes/b1..b6): an extern
local RE-DECLARES THE SAME OBJECT the file scope would name — it is a
REFERENCE, never new storage:
  * if some enclosing scope already names it, the local declaration adds
    nothing → blcc's tip drop stands (b2 `int f(void){ extern int t; … }`
    with `t` defined later in the TU, b3 the array twin, b4 the plain
    re-decl: all three were and stay PAIR-quiet);
  * if NOTHING in this TU names it (the corpus `zero_pfn` class — the
    object is DEFINED IN ANOTHER TU and this TU only ever spells it
    inside a function), tip dropped the only declaration the name ever
    had and then LOUDed "'zero_pfn' undeclared — not a local, parameter,
    global or enum constant": a COMPILE-time refusal of what gcc correctly
    leaves a LINK-time fact (b1: gcc rc0, tip rc2). The ship binds it the
    way the file-scope `extern int x;` spelling binds it — ONE `is_extern`
    VarDecl hoisted through the parser's existing TU-hoist list and ONE
    entry in the file scope, so the use rides the SAME globals door
    `_ex_ident` already has and nm shows a bare `U name` with no storage
    (measured on the b6 twin). This REPLACES: the unconditional drop, and
    it is NOT the sim stub's posture — the stub gave the name a fresh
    LOCAL frame slot, which answers garbage where gcc answers the object
    (the two-TU value leg below pins the difference).
  * an extern INCOMPLETE-ARRAY local (`extern char __init_begin[],
    __init_end[];` — 304 corpus streams, the #1 first-wall class at the
    {A+B+D} bytes) stays LOUD, naming the class: gcc compiles it, the §4
    size wall still owns it, and freeing it is the W-V lever — the queue
    this wave walks BEHIND (b5: gcc rc0, blcc LOUD, accept-neutral).
"""
import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.environ.get("BLCC_REPO") or os.path.dirname(HERE)
REC = ["-Os", "-mno-sse", "-mno-mmx", "-mno-80387", "-fno-stack-protector",
       "-fno-pic"]
ENV = {"PYTHONPATH": REPO, "PATH": "/usr/bin:/bin"}


def blcc(args):
    return subprocess.run([sys.executable, "-m", "blcc"] + args,
                          capture_output=True, text=True, cwd=REPO, env=ENV)


def _w(tag, src):
    c = "/dev/shm/wu2_%s.c" % tag
    open(c, "w").write(src)
    return c


def _pair(tag, src):
    c = _w(tag, src)
    g = subprocess.run(["gcc", "-std=gnu89"] + REC +
                       [c, "-no-pie", "-o", "/dev/shm/wu2_%s.g" % tag],
                       capture_output=True, text=True)
    assert g.returncode == 0, "row must be valid C: " + g.stderr
    gex = subprocess.run(["/dev/shm/wu2_%s.g" % tag],
                         env={"PATH": "/usr/bin:/bin"}).returncode
    o = "/dev/shm/wu2_%s.o" % tag
    b = blcc(["-c", c, "-o", o])
    assert b.returncode == 0, "%s must compile: " % tag + b.stderr
    assert subprocess.run(["gcc", "-no-pie", o, "-o",
                           "/dev/shm/wu2_%s.b" % tag],
                          capture_output=True).returncode == 0
    bex = subprocess.run(["/dev/shm/wu2_%s.b" % tag],
                         env={"PATH": "/usr/bin:/bin"}).returncode
    assert bex == gex, "%s run-pair: blcc=%d gcc=%d" % (tag, bex, gex)


def _pair_two_tu(tag, src_a, src_b):
    """THE value law: the object lives in a SECOND TU, so only a real
    external reference can read it. A local frame slot (the sim stub's
    posture) answers garbage/zero and cannot match gcc's value."""
    a, b = _w(tag + "_a", src_a), _w(tag + "_b", src_b)
    exe_g = "/dev/shm/wu2_%s.g" % tag
    g = subprocess.run(["gcc", "-std=gnu89"] + REC + [a, b, "-no-pie",
                                                     "-o", exe_g],
                       capture_output=True, text=True)
    assert g.returncode == 0, "two-TU row must link with gcc: " + g.stderr
    gex = subprocess.run([exe_g], env={"PATH": "/usr/bin:/bin"}).returncode
    oa = "/dev/shm/wu2_%s_a.o" % tag
    r = blcc(["-c", a, "-o", oa])
    assert r.returncode == 0, "%s: the extern-local reference must " \
        "COMPILE (RED-first witness — tip LOUDs): " % tag + r.stderr
    ob = "/dev/shm/wu2_%s_b.gcc.o" % tag
    assert subprocess.run(["gcc", "-std=gnu89"] + REC + ["-c", b, "-o", ob],
                          capture_output=True).returncode == 0
    exe_b = "/dev/shm/wu2_%s.b" % tag
    assert subprocess.run(["gcc", "-no-pie", oa, ob, "-o", exe_b],
                          capture_output=True).returncode == 0, \
        "%s: the blcc object must carry the external reference" % tag
    bex = subprocess.run([exe_b], env={"PATH": "/usr/bin:/bin"}).returncode
    assert bex == gex, "%s two-TU run-pair: blcc=%d gcc=%d — a LOCAL slot " \
        "instead of a reference shows up here" % (tag, bex, gex)


def _loud(tag, src, needle):
    c = _w(tag, src)
    g = subprocess.run(["gcc", "-std=gnu89"] + REC + ["-c", c, "-o",
                                                     "/dev/null"],
                       capture_output=True, text=True)
    b = blcc(["-c", c, "-o", "/dev/null"])
    assert b.returncode != 0, "%s must be LOUD: " % tag + b.stderr
    assert needle in b.stderr, "%s: LOUD must name %r: " % (tag, needle) \
        + b.stderr
    return g.returncode


# ---- RED-first: the corpus class (gcc rc0, tip rc2) --------------------

def test_wu_b1_extern_local_naming_another_tus_object_compiles():
    # THE `zero_pfn` class: the TU never spells the object at file scope,
    # only `extern` inside a function. gcc: compiles (the symbol is a
    # LINK-time fact). tip: `'missing' undeclared` — the refusal this
    # commit exists for.
    c = _w("b1", "int main(void){ extern int missing; (void)&missing; "
                "return 0; }\n")
    g = subprocess.run(["gcc", "-std=gnu89"] + REC + ["-c", c, "-o",
                                                     "/dev/null"],
                       capture_output=True, text=True)
    assert g.returncode == 0, "gcc compiles it: " + g.stderr
    b = blcc(["-c", c, "-o", "/dev/null"])
    assert b.returncode == 0, "the extern local must bind as a TU " \
        "reference (RED at C0 bytes): " + b.stderr


def test_wu_b1b_extern_local_reads_a_second_tu_object_by_value():
    # the VALUE law, two TU's: `shared` is defined in the other object, so
    # only a genuine external reference answers 0. The sim stub's fresh
    # local slot answers garbage — this leg is what pins MY law over the
    # stub's, and it is the row the sims' law-D number (+22) cannot see.
    _pair_two_tu("b1b",
                 "int main(void){ extern int shared; shared += 3; "
                 "return shared - 9; }\n",
                 "int shared = 6;\n")


def test_wu_b1c_extern_local_call_target_unchanged():
    # posture pin: an extern local NAMING A FUNCTION rode the function
    # branch before this wave and must keep riding it (rc0, compile-only).
    c = _w("b1c", "int main(void){ extern int other(); "
                "return other() - 4; }\n")
    b = blcc(["-c", c, "-o", "/dev/null"])
    assert b.returncode == 0, "extern-local FUNCTION decl unchanged: " + b.stderr


# ---- the drop arm: known outward stays the tip posture (PAIR) ---------

def test_wu_b2_later_definition_resolves_to_the_same_object():
    # `t` is defined AFTER the function; the extern local and the file
    # scope name ONE object (gcc 0). Quiet at C0 bytes and here — the drop
    # arm must not regress into a second definition.
    _pair("b2", "int f(void){ extern int t; return t; }\nint t = 7;\n"
          "int main(void){ return f() - 7; }\n")


def test_wu_b3_b4_redecl_and_array_twin_stay_pair():
    # b3: the extern ARRAY twin where file scope already gave a size-ish
    # view; b4: the plain re-decl read through a pointer. Both PAIR.
    _pair("b3", "char arr[4];\nint main(void){ extern char arr[4]; "
          "arr[1] = 3; return arr[1] - 3; }\n")
    _pair("b4", "int g = 7;\nint main(void){ extern int g; int *p = &g; "
          "return *p - 7; }\n")


def test_wu_b2b_two_functions_same_extern_local_bind_once():
    # the same unknown extern name in TWO functions binds ONE TU entry
    # (a second `is_extern` VarDecl would trip the codegen re-definition
    # law; a per-function local slot would answer garbage).
    c = _w("b2b", "int f(void){ extern int lone; return lone; }\n"
          "int g(void){ extern int lone; lone = 2; return lone; }\n"
          "int main(void){ return f() + g() - 2; }\n")
    b = blcc(["-c", c, "-o", "/dev/null"])
    assert b.returncode == 0, "one binding, two uses: " + b.stderr
    assert "redefin" not in b.stderr.lower() and "redeclar" not in \
        b.stderr.lower(), "the name must be bound ONCE: " + b.stderr


# ---- the class this wave deliberately still refuses (queue-behind) ----

def test_wu_b5_extern_incomplete_array_local_is_loud_naming_the_class():
    # 304 corpus streams sit on THIS shape (`extern char __init_begin[],
    # __init_end[];`). gcc compiles it; blcc keeps the §4 size refusal and
    # NAMES the class — W-V's lever, the wall this wave's walk lands
    # behind. LOUD posture measured; the message must name the shape.
    rc_gcc = _loud("b5", "unsigned long f(void){ extern char __init_begin[], "
                   "__init_end[]; return (unsigned long)__init_end - "
                   "(unsigned long)__init_begin; }\n",
                   "incomplete-array extern")
    assert rc_gcc == 0, "gcc-side of the queue-behind row moved: the W-V " \
        "class must still be gcc-legal for the walk story to hold"


def test_wu_b6_extern_local_binds_no_storage():
    # nm leg: the binding must be a bare UNDEFINED reference, exactly what
    # the file-scope `extern int yy;` spelling produces — a COMMON or a
    # .bss emission here would move the link-readiness instrument.
    c = _w("b6", "int main(void){ extern int lone; return lone; }\n")
    o = "/dev/shm/wu2_b6.o"
    r = blcc(["-c", c, "-o", o])
    assert r.returncode == 0, r.stderr
    nm = subprocess.run(["nm", o], capture_output=True, text=True).stdout
    kinds = set()
    for line in nm.splitlines():
        f = line.split()
        if f and f[-1] == "lone":
            # an UNDEFINED symbol line carries no address: `U lone`
            kinds.add("U" if f[0] == "U" else f[-2])
    assert kinds == {"U"}, "extern local must be a bare reference, got " \
        "%r in:\n%s" % (sorted(kinds), nm)
