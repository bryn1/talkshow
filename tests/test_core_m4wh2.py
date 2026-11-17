"""M4 W-H COMMIT-2 (MC 12645) — STRUCT-ASSIGNMENT: THE BLOCK-COPY LAW.

THE MEASURED LAW (gcc 11.4 -std=gnu89, probes .tmp/m4-wh/probes/p5.c —
every leg cites its measurement; emission shape table from the -Os
size-class probes s_assign*.c):

  SAME-TYPE AGGREGATE `=` IS A BLOCK COPY of sizeof bytes. gcc -Os
  ALWAYS inlines (measured to 100B, ZERO libcall): movq for <=8,
  movl/movw/movb tails for 9-15, movaps at 16, `rep movsb` from 15/33,
  `rep movsl` 40-100. blcc rides its OWN shipped copy machinery (the
  memfold `_copy_pairs` GPR-chunk + `rep movsb` law the i128 pair-copy
  already proved) — NAMED SHAPE DEVIATION ROWS (both inline, zero
  libcall either side): blcc uses GPR chunks where gcc movaps at 16,
  and blcc's chunk boundary is 16 where gcc starts `rep movsb` at 15;
  the OBSERVABLE law (bytes move, value of the copy, assignment VALUE
  = the target address, `(w = gs).a` and `v2 = w = gs` chain) is what
  the run-pairs below pin.

  REJECT twins (all measured rc 1; gcc sentences mirrored):
    different tag   — "incompatible types when assigning to type
                       'struct S' from type 'struct T'" (tip LOUDed the
                     old §5 sentence; tip ALSO false-ACCEPTed the
                     scalar twins below — both were wrong sides)
    struct<->scalar — "... to type 'int' from type 'struct S'" and the
                     reverse (tip FALSE-ACCEPTED: `int n = w` compiled
                     and RAN GARBAGE 11 at tip — the fixg2b audit row)
    plain-array LHS — "assignment to expression with array type"
                     (tip FALSE-ACCEPTED `a2 = b2` rc 0 — the guard at
                     expr_codegen:1406 only covered compound-assign)
  ACCEPT arms (rc 0): compound-literal RHS (`w = (struct P){1,2}` —
  the §1 row 11 witness shape), chained/self assign, struct-valued
  assignment as an EXPRESSION (`(w = gs).a` — value-as-address law,
  the i128 precedent), copy-INIT `struct S w = gs;` at EVERY size
  class (tip's 12-byte false wall `cannot load a 12-byte value (§4)`
  dies with this commit), struct-with-array-member, union same-tag.

  STAYS LOUD (named, NOT this wave's mechanism): struct compound-
  assign (`+=` — the §5 sentence stays for the non-`=` ops); struct
  arms of `?:` (gcc rc 0 — the shipped cond-arm wall, retirement rides
  the cond law); struct-returning CALL as RHS (gcc rc 0 — tip's by-
  value return/passthrough wall at codegen:486/520; this is what the
  capability.h:169 sweep rows keep LOUD, the honest close-leg move);
  struct comparison. NAMED DIVERGENCE (pin, NOT approval): const
  struct LHS — gcc rc1 "assignment of read-only variable", blcc's one
  store law never enforced quals (layout-ignores-quals doctrine).
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


def _pair(tmp_path, tag, src, e):
    s = tmp_path / (tag + ".c")
    s.write_text(src)
    g = subprocess.run(["gcc", "-std=gnu89", str(s), "-o",
                        str(tmp_path / (tag + ".g"))],
                       capture_output=True, text=True)
    assert g.returncode == 0, "gcc: " + g.stderr
    b = blcc([str(s), "-o", str(tmp_path / (tag + ".b"))])
    assert b.returncode == 0, "blcc: " + b.stderr
    gv = subprocess.run([str(tmp_path / (tag + ".g"))],
                        capture_output=True).returncode
    bv = subprocess.run([str(tmp_path / (tag + ".b"))],
                        capture_output=True).returncode
    assert gv == e, "gcc gave {} expected {}".format(gv, e)
    assert bv == e, "blcc gave {} expected {}".format(bv, e)


def _loud(tmp_path, tag, src, needle):
    r = _compile(tmp_path, tag, src)
    assert r.returncode != 0, "must LOUD (measured gcc rc1 twin):\n" + src
    assert needle in r.stderr, r.stderr
    return r


def _char(n, init_head, init_tail):
    # exact-size char-array struct (no padding — the size CLASS is
    # sizeof EXACTLY; head+tail witness: 1 + 2 = 3 under a full block
    # copy, anything else under a pointer swap or a truncated chunk).
    # NESTED braces `{ { … } }`: the FLAT brace-elision spelling is a
    # pre-existing blcc DATA-layer wall (`struct initializer must be a
    # brace list of member constants`, measured at tip — brace elision
    # never shipped there; corpus volume 0, named divergence in the
    # verdict, NOT this wave).
    return ("struct C{char b[%d];} gc = {{%s}};\n"
            "int g(void){ struct C w; w = gc;"
            " return (int)w.b[0] + (int)w.b[%d]; }\n"
            "int main(void){ return g(); }"
            % (n, ",".join(str(x) for x in
                           [init_head] + ["0"] * (n - 2) + [init_tail]),
               n - 1))


# ------------------------------------------------- the block-copy law

def test_wh2_copy_size_classes(tmp_path):
    # EVERY size class measured on gcc -Os (movq <=8, mov tails 9-15,
    # movaps 16, rep movsb 15/33, rep movsl 40-100 — all INLINE): the
    # OBSERVABLE law is that the BYTES move: head 1 + tail 2 = 3 in a
    # full block copy; a pointer-assign (the planted tooth) or a
    # truncated chunk leaves the tail at 0 -> 1.
    for n in (1, 4, 5, 8, 9, 12, 16, 17, 24, 33, 64, 100):
        if n == 1:
            src = ("struct C{char b[1];} gc = {{1}};\n"
                   "int g(void){ struct C w; w = gc; return w.b[0]; }\n"
                   "int main(void){ return g(); }")
            _pair(tmp_path, "wh2_s1", src, 1)
            continue
        _pair(tmp_path, "wh2_s%d" % n, _char(n, 1, 2), 3)


def test_wh2_copy_init_12byte(tmp_path):
    # The tip FALSE WALL: `struct S w = gs;` at 8 bytes worked by
    # ACCIDENT (movq); 12 bytes died `cannot load a 12-byte value
    # (§4)` — the copy-init law is the same block copy at _stmt_vardecl
    # (measured gcc rc 0 both sizes; natural padding makes this struct
    # 16 — the copy moves sizeof bytes regardless).
    _pair(tmp_path, "wh2_ci",
          "struct S{long a;int b;} gs = {1, 2};\n"
          "int g(void){ struct S w = gs; struct S v = gs;"
          " w.a = 0; return (int)(v.a + v.b); }\n"
          "int main(void){ return g(); }", 3)


def test_wh2_member_and_static_targets(tmp_path):
    # the copy STORES through any lvalue: a member lvalue and a STATIC
    # local (the §1c static-local storage, the file-scope object):
    _pair(tmp_path, "wh2_m",
          "struct S{long a;int b;} gs = {4, 7};\n"
          "struct W{ struct S s; } gw;\n"
          "int g(void){ struct W w; w.s = gs; static struct W sv;"
          " sv.s = gs; return (int)(w.s.b + sv.s.a); }\n"
          "int main(void){ return g(); }", 7 + 4)


def test_wh2_array_member_copy(tmp_path):
    # struct-with-array MEMBER copies block (measured rc 0; the array
    # member is bytes in the block — the array-assign wall is about
    # the ARRAY-TYPED LHS, not members):
    _pair(tmp_path, "wh2_am",
          "struct P{int a[3];} gp = {{1,2,3}};\n"
          "int g(void){ struct P p; p = gp; return p.a[2] + p.a[0]; }\n"
          "int main(void){ return g(); }", 4)


def test_wh2_union_copy(tmp_path):
    # union same-tag `=` is the SAME block-copy law (measured rc 0;
    # the 9-byte union copies through the mov-tail class):
    _pair(tmp_path, "wh2_u",
          "union U{long a; char b[9];} gu;\n"
          "int g(void){ gu.b[0] = 1; gu.b[8] = 2; union U u; u = gu;"
          " return (int)u.b[0] + (int)u.b[8]; }\n"
          "int main(void){ return g(); }", 3)


def test_wh2_clit_rhs(tmp_path):
    # §1 row 11 WITNESS SHAPE `head->rb_root = (struct rb_root_cached)
    # {…}` — the compound literal is an ADDRESS (the shipped aggregate
    # convention), the assign copies from it (measured rc 0):
    _pair(tmp_path, "wh2_cl",
          "struct P{int a;int b;};\n"
          "int g(void){ struct P s; s = (struct P){1,2};"
          " return s.a + s.b; }\n"
          "int main(void){ return g(); }", 3)


def test_wh2_value_is_target_address(tmp_path):
    # THE VALUE-AS-ADDRESS LAW (the i128 pair-copy precedent): the
    # assignment's VALUE is the target — `(w = gs).a` reads the COPY
    # (measured rc 0), and the chain `v2 = w = gs` fills both.
    _pair(tmp_path, "wh2_v",
          "struct S{long a;int b;} gs = {5, 7};\n"
          "int g(void){ struct S w, v2; v2 = w = gs;"
          " return (int)(w.b + v2.b + (w = gs).a * 0);"
          " }\n"
          "int main(void){ return g(); }", 14)


def test_wh2_deref_target(tmp_path):
    # copy through a pointer lvalue (`*p = gs` — Deref address law):
    _pair(tmp_path, "wh2_d",
          "struct S{long a;int b;} gs = {4, 7};\n"
          "int g(void){ struct S w; struct S *p = &w; *p = gs;"
          " return (int)(p->b + w.b); }\n"
          "int main(void){ return g(); }", 14)


# ------------------------------------------------------- reject twins

def test_wh2_diff_tag_loud(tmp_path):
    # measured gcc rc1, gcc sentence mirrored (tip LOUDed the old §5
    # sentence here too — the NEW sentence names the TYPES, which is
    # what the kcopy triage needs):
    _loud(tmp_path, "wh2_dt",
          "struct S{long a;} gs; struct T{long a;} gt;\n"
          "int g(void){ gs = gt; return 0; }\n"
          "int main(void){ return g(); }",
          "incompatible types when assigning to type 'struct S' "
          "from type 'struct T'")


def test_wh2_struct_to_int_loud(tmp_path):
    # TIP FALSE-ACCEPTED THIS (measured at tip: compiled, RAN 11 —
    # garbage). gcc rc1 `incompatible types when assigning to type
    # 'int' from type 'struct S'`:
    _loud(tmp_path, "wh2_s2i",
          "struct S{long a;} w; int n;\n"
          "int main(void){ n = w; return 0; }",
          "incompatible types when assigning to type 'int' "
          "from type 'struct S'")


def test_wh2_int_to_struct_loud(tmp_path):
    # the reverse arm (measured gcc rc1; tip false-accepted):
    _loud(tmp_path, "wh2_i2s",
          "struct S{long a;} w; int n;\n"
          "int main(void){ w = n; return 0; }",
          "incompatible types when assigning to type 'struct S' "
          "from type 'int'")


def test_wh2_array_assign_loud(tmp_path):
    # TIP FALSE-ACCEPTED `a2 = b2` rc 0 (measured at tip; the 1406
    # guard covered only compound-assign — fixg2b sibling audit).
    # gcc rc1, sentence verbatim:
    _loud(tmp_path, "wh2_aa",
          "int a2[4], b2[4];\nint main(void){ a2 = b2; return 0; }",
          "assignment to expression with array type")


def test_wh2_array_clit_assign_loud(tmp_path):
    # the array-LHS twin with a compound literal (gcc rc1 SAME
    # sentence — the wall is the LHS, not the RHS):
    _loud(tmp_path, "wh2_ac",
          "int a2[4];\nint main(void){ a2 = (int[4]){1,2,3,4};"
          " return 0; }",
          "assignment to expression with array type")


def test_wh2_union_vs_struct_loud(tmp_path):
    # same NAME, different KIND — blcc LOUDs EARLIER than gcc: its tag
    # namespace is shared and `struct K` after `union K` is refused at
    # parse ('struct/union K is already defined' — a stronger wall than
    # the assignment-level check, LOUD both sides for the tag-reuse
    # spelling). The is_union arm of the identity law is still the one
    # that guards the SAME tag pair (a union is never its struct), and
    # the redefinition sentence is pinned so a future tag-namespace
    # widening must pass through this leg on purpose.
    _loud(tmp_path, "wh2_us",
          "union K{long a;}; struct K{long a;} gk;\n"
          "int g(void){ union K u; u = gk; return 0; }\n"
          "int main(void){ return g(); }",
          "already defined")


def test_wh2_anon_pairs(tmp_path):
    # THE IDENTITY LAW observable (measured): anonymous types are the
    # SAME type only through their declaring specifier — anon-struct ×
    # anon-union rc1 and two anon-struct DECLARATIONS rc1 ("incompatible
    # types when assigning to type 'struct <anonymous>' from type
    # 'union …'"), while the same declaration's two variables COPY
    # (rc 0). blcc's law is the same mechanism: `rty is lty` identity
    # (one specifier node) vs the tag arm — no tag, no node identity,
    # LOUD; the sentence spells both sides "<anonymous>".
    _pair(tmp_path, "wh2_an1",
          "struct { int a; } x1, x2;\n"
          "int g(void){ x1 = x2; return x1.a + 2; }\n"
          "int main(void){ return g(); }", 2)
    _loud(tmp_path, "wh2_an2",
          "struct { int a; } x; union { int a; } y;\n"
          "int g(void){ x = y; return 0; }\n"
          "int main(void){ return g(); }",
          "incompatible types when assigning to type 'struct "
          "<anonymous>' from type 'union <anonymous>'")
    _loud(tmp_path, "wh2_an3",
          "struct { int a; } x; struct { int a; } y;\n"
          "int g(void){ x = y; return 0; }\n"
          "int main(void){ return g(); }",
          "incompatible types when assigning to type 'struct "
          "<anonymous>' from type 'struct <anonymous>'")


def test_wh2_compound_assign_stays_loud(tmp_path):
    # §5 wall STAYS for the non-`=` ops (the parse gate keeps its
    # sentence; gcc rc1 too — invalid types for binary +=):
    _loud(tmp_path, "wh2_cas",
          "struct S{int a;} x, y;\n"
          "int main(void){ x += y; return 0; }",
          "struct assignment")


def test_wh2_cond_arm_stays_loud(tmp_path):
    # NAMED DEFER (measured gcc rc 0): struct arms of `?:`. The shipped
    # cond-arm wall stays — retirement rides the conditional law, not
    # a copy path bolted onto Cond. capability.h-adjacent shapes too.
    r = _compile(tmp_path, "wh2_ca",
                 "struct S{int a;} x, y;\n"
                 "int gi;\nint g(void){ struct S z; z = gi ? x : y;"
                 " return z.a; }\nint main(void){ return g(); }")
    assert r.returncode != 0
    assert "conditional arm" in r.stderr, r.stderr


def test_wh2_call_rhs_stays_loud(tmp_path):
    # NAMED DEFER (measured gcc rc 0): `dest = cap_drop(a, set)` — the
    # capability.h:169 class (12 sweep rows). The wall is STRUCT
    # RETURN-BY-VALUE (codegen:486/520, shipped LOUD, §5 pass/return),
    # NOT the assignment: the copy law never fakes a caller-allocated
    # hidden return. The close-leg sweep keeps these rows LOUD — the
    # honest move, named. Retirement rides the by-value return law.
    r = _compile(tmp_path, "wh2_cr",
                 "struct S{int a;} x;\nstruct S fs(void){ return x; }\n"
                 "int g(void){ struct S d; d = fs(); return d.a; }\n"
                 "int main(void){ return g(); }")
    assert r.returncode != 0, (
        "when struct RETURN lands, FLIP to the run-pair expect 4")


def test_wh2_const_lhs_divergence(tmp_path):
    # SILENT-DIV PIN (NOT approval): gcc rc1 "assignment of read-only
    # variable 'cw'"; blcc's ONE store law never enforced quals
    # (measured at tip for every const path). Retirement rides the
    # const-store class — never this wave.
    r = _compile(tmp_path, "wh2_cw",
                 "struct S{int a;} gs; int g(void){ const struct S cw"
                 " = gs; cw = gs; return cw.a; }\n"
                 "int main(void){ return g(); }")
    assert r.returncode == 0, (
        "retire this leg with the const-store class:\n" + r.stderr)


# ------------------------------------------------- interaction arms

def test_wh2_auto_from_assign(tmp_path):
    # W-H PAIRING ARM (measured gcc rc 0): `__auto_type v = (w = gs);`
    # — the auto law types the ASSIGNMENT (struct S, the target's
    # type), the copy-init law moves the bytes, and the value-as-
    # address law lets the init expression FEED the copy:
    _pair(tmp_path, "wh2_af",
          "struct S{long a;int b;} gs = {5, 7};\n"
          "int g(void){ struct S w; __auto_type v = (w = gs);"
          " return (int)(v.b + w.b); }\n"
          "int main(void){ return g(); }", 14)


def test_wh2_auto_then_copy(tmp_path):
    # auto-typed struct var RE-ASSIGNED block copy (auto + the law):
    _pair(tmp_path, "wh2_acp",
          "struct S{long a;int b;} gs = {5, 7};\n"
          "int g(void){ __auto_type v = gs; struct S o = gs;"
          " v = o; o.a = 0; return (int)(v.a + v.b); }\n"
          "int main(void){ return g(); }", 12)


def test_wh2_typedef_same_tag(tmp_path):
    # copies ride the TAG, not the spelling — a typedef name is the
    # same struct (measured rc 0):
    _pair(tmp_path, "wh2_td",
          "struct S{int a;} g1; typedef struct S my_t;\n"
          "int g(void){ my_t v; v = g1; return v.a + 2; }\n"
          "int main(void){ return g(); }", 2)
