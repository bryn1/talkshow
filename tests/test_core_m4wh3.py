"""M4 W-H COMMIT-3 (MC 12645) — INTERACTION ARMS: auto_type x copy law.

The pairing AMENDMENT-7 predicted: the 406 __auto_type streams' second
wall was struct-assignment (392/406), and the two COMMITs' mechanisms
already carry every interaction arm — measured FIRST (gcc 11.4 gnu89 vs
blcc, both sides run this session), these legs are CONTROLS: they pin
the measured shape so a later wave cannot regress the pair without a
named RED here. Where blcc and gcc LOUD differently (different
sentences, same rc!=0 verdict) the leg pins the verdict and records
both sentences — never silently.
"""
import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.environ.get("BLCC_REPO") or os.path.dirname(HERE)

H = ("struct S{long a;int b;} gs = {5,7}; struct W{struct S s;} gw = {{1,2}};\n"
     "const struct S cgs = {1,1}; struct S *ps;\n"
     "union U{long x; char c[9];} gu;\n")


def blcc(args):
    return subprocess.run([sys.executable, "-m", "blcc"] + args,
                          capture_output=True, text=True, cwd=REPO,
                          env={"PYTHONPATH": REPO, "PATH": "/usr/bin:/bin"})


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


# ------------------------------------------------------- accept arms

def test_wh3_qual_auto_writes(tmp_path):
    # CONTROL (measured pair 7): the TOP-QUAL-DROP law OBSERVABLE end
    # to end — `__auto_type v = cgs;` (const struct) is WRITABLE after
    # the drop, the re-assignment `v = gs` is the block copy, the run
    # answers 7. The typeof twin (`__typeof__(cgs) v; v = gs;`) is gcc
    # rc 1 — the measured difference table, now with a struct witness.
    _pair(tmp_path, "wh3_q", H +
          "int g(void){ __auto_type v = cgs; v = gs; return (int)v.b; }"
          "int main(void){ return g(); }", 7)


def test_wh3_deref_auto(tmp_path):
    # CONTROL (measured pair 7): `__auto_type v = *ps;` — value
    # conversion of a struct lvalue IS the copy; the init rides the
    # source-ADDRESS law (Deref → _emit_addr).
    _pair(tmp_path, "wh3_d", H +
          "int g(void){ ps = &gs; __auto_type v = *ps; return (int)v.b; }"
          "int main(void){ return g(); }", 7)


def test_wh3_member_auto(tmp_path):
    # CONTROL (measured pair 2): nested member `__auto_type m = gw.s;`
    # — the auto law reads the MEMBER type (struct S), the copy-init
    # moves it from the member address:
    _pair(tmp_path, "wh3_m", H +
          "int g(void){ __auto_type m = gw.s; return (int)m.b; }"
          "int main(void){ return g(); }", 2)


def test_wh3_union_auto(tmp_path):
    # CONTROL (measured pair 3): a UNION materializes through the auto
    # law (is_union rides the type node — a later `v = gu` stays the
    # same-tag-union copy, never its same-named struct):
    _pair(tmp_path, "wh3_u", H +
          "int g(void){ gu.c[0] = 1; gu.c[8] = 2; __auto_type v = gu;"
          " return (int)v.c[0] + (int)v.c[8]; }"
          "int main(void){ return g(); }", 3)


def test_wh3_sizeof_typeof_auto(tmp_path):
    # CONTROL (measured pair 16): `sizeof(typeof(v))` of an auto struct
    # var — the stream's own arithmetic (ktime class uses exactly this
    # sizeof/typeof combo on the __auto_type locals):
    _pair(tmp_path, "wh3_sz", H +
          "int g(void){ __auto_type v = gs;"
          " return (int)sizeof(typeof(v)); }"
          "int main(void){ return g(); }", 16)


# ---------------------------------------------------------- LOUD arms

def test_wh3_static_nonconst_loud(tmp_path):
    # LOUD both sides (measured gcc rc1 "initializer element is not
    # constant"; blcc's data law LOUDs its §4 sentence
    # "struct initializer must be a brace list of member constants" —
    # DIFFERENT SENTENCES, same rc!=0 verdict, pinned so a future
    # sentence-sync pass sees it): a static (or file-scope) auto struct
    # cannot copy at init time. The runtime `static __auto_type v;`
    # DECLARATION then a block copy is the legal shape (§1c + the copy
    # law — see m4wh2 member_and_static_targets).
    s = tmp_path / "wh3_st.c"
    s.write_text(H + "int g(void){ static __auto_type v = gs; return 0; }"
                 "int main(void){ return g(); }")
    r = blcc(["-c", str(s), "-o", str(tmp_path / "wh3_st.o")])
    assert r.returncode != 0, "static non-constant struct init stays LOUD"


def test_wh3_file_nonconst_loud(tmp_path):
    # The file-scope twin (measured rc1 both sides, same sentence note):
    s = tmp_path / "wh3_fs.c"
    s.write_text(H + "__auto_type gv = gs;\nint main(void){ return 0; }")
    r = blcc(["-c", str(s), "-o", str(tmp_path / "wh3_fs.o")])
    assert r.returncode != 0, "file-scope non-constant struct init LOUD"


def test_wh3_stream_shape_end_to_end(tmp_path):
    # THE corpus shape in miniature (measured run-pair 3): an auto
    # local saving the struct through the copy law, then the path.h
    # empty-literal reset `*path = (struct path) { };` — BOTH walls of
    # the 406+76 crowd in ONE file, no by-value return smuggle:
    _pair(tmp_path, "wh3_e2e",
          "struct path{long m; long d;};\n"
          "void path_put(struct path *p){ (void)p; }\n"
          "int put_init(struct path *path)\n"
          "{\n"
          " __auto_type saved = *path;\n"
          " path_put(path);\n"
          " *path = (struct path) { };\n"
          " return (int)(saved.m + path->m);\n"
          "}\n"
          "int main(void){ struct path p = {3, 0};"
          " return put_init(&p); }", 3)
