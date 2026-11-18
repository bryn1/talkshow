# LINES reason: one wave of legs (M4 W-J COMMIT-4 — the TRIPLE
# INTERACTION: fallthrough + dyn offsetof + _Static_assert in one TU,
# card 12404.2.77) — the interactions are the point; splitting them
# separates what only fails (or holds) together.
r"""M4 W-J COMMIT-4 — the three features in ONE translation unit.

Each feature shipped RED-first (COMMIT-1/2/3). This wave proves the
COMPOSITIONS the corpus actually contains (kernel_signal.c.i: SA + FT in
one TU; arch_x86_entry_common.c.i: all THREE: top-level SA, FT in
switches, `container_of(…, node[idx])`) and the attr-placement edges the
`fallthrough` CAPTURE exposed — all measured at MY hands against gcc
11.4 gnu89 -Os before pinning:

  x_ft_decl: `__attribute__((fallthrough)) int y = 5;` — gcc rc0 with TWO
    warnings ("not followed by ';'" + position warning): the "invalid
    use" law binds ONLY the attribute-DECLARATION (attr+`;`) shape; a
    real declaration just IGNORES the marker. blcc: the sink entry
    filters past every judge → rc0 — PAIR-CLEAN, pinned fair-green.
  x_ft_param: `int g(int __attribute__((fallthrough)) x)` — gcc rc0
    "attribute ignored"; blcc drops the sink entry (COMMIT-0 param law
    filters BY NAME — the new ("fallthrough", None) tuple must not
    disturb the section/aligned judges) — PAIR-CLEAN, pinned.
  Triple arms: FT + block-scope SA in the same case body; container_of
    with a RUNTIME idx INSIDE a fall-through switch; a file-scope SA
    whose condition contains a dyn-index offsetof — the fold returns the
    runtime node, fold_truthy None → "not constant" — and gcc LOUDs the
    SAME verdict rc1 ("not constant"); the reject arm of the composition.
  Full mini-kernel TU (all three features, 4 functions) run-pair on the
    combined observable (magic recovered + fall-through sums + the kparam
    SA at file scope), the 461/205/118/327 classes in ONE file.
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


def gcc(args):
    return subprocess.run(["gcc", "-std=gnu89"] + args,
                          capture_output=True, text=True,
                          env={"PATH": "/usr/bin:/bin"})


def _compile(tmp_path, tag, src):
    s = tmp_path / (tag + ".c")
    s.write_text(src)
    return blcc(["-c", str(s), "-o", str(tmp_path / (tag + ".o"))])


def _gcc_rc(tmp_path, tag, src):
    s = tmp_path / (tag + ".c")
    s.write_text(src)
    return gcc(["-Os", "-c", str(s), "-o", str(tmp_path / (tag + ".g.o"))])


def _ok(tmp_path, tag, src):
    g = _gcc_rc(tmp_path, tag, src)
    assert g.returncode == 0, "gcc twin must rc0:\n" + src + g.stderr
    r = _compile(tmp_path, tag, src)
    assert r.returncode == 0, "blcc must ACCEPT:\n" + src + "\n" + r.stderr
    return r


def _pair(tmp_path, tag, src, expect):
    s = tmp_path / (tag + ".c")
    s.write_text(src)
    gx = tmp_path / (tag + ".gcc")
    gr = gcc(["-O0", str(s), "-o", str(gx)])
    assert gr.returncode == 0, "oracle must build:\n" + gr.stderr
    bx = tmp_path / (tag + ".blcc")
    br = blcc([str(s), "-o", str(bx)])
    assert br.returncode == 0, "blcc must build:\n" + br.stderr
    g = subprocess.run([str(gx)], capture_output=True, text=True, timeout=30)
    b = subprocess.run([str(bx)], capture_output=True, text=True, timeout=30)
    assert g.returncode == b.returncode == expect, \
        "run-pair: gcc {} blcc {} expect {}".format(
            g.returncode, b.returncode, expect)


FT = "__attribute__((__fallthrough__))"


# ------------------------------------------------- attr-placement edges

def test_wj4_ft_on_real_decl_pair_clean(tmp_path):
    # x_ft_decl: marker glued to a REAL declaration — gcc rc0, warnings
    # only ("not followed by ';'"); the invalid-use law binds ONLY the
    # attr+`;` shape. Fair-green at this tree, honestly named.
    _ok(tmp_path, "wj4_d",
        "int f(void){ " + FT + " int y = 5; return y; }\n")


def test_wj4_ft_on_param_pair_clean(tmp_path):
    # x_ft_param: gcc rc0 "attribute ignored"; the COMMIT-0 param judge
    # filters the sink BY NAME — the new capture tuple must not disturb
    # the section/aligned law. Fair-green, named.
    _ok(tmp_path, "wj4_p",
        "int g(int " + FT + " x){ return x; }\n")


# ------------------------------------------------------ the compositions

def test_wj4_ft_and_block_sa_same_case_body(tmp_path):
    # signal.h + kparam in ONE case body: the SA is a no-op declaration,
    # the FT marker still falls through — observable: both arms ran.
    _pair(tmp_path, "wj4_sb",
          '_Static_assert(1 == 1, "top");\n'
          "int f(int x){ int r = 0;\n"
          "  switch (x) { case 1: r += 1; _Static_assert(2 > 1, \"in\");\n"
          "    " + FT + ";\n"
          "    case 2: r += 10; }\n"
          "  return r; }\n"
          "int main(void){ return f(1) == 11 ? 0 : 1; }\n", 0)


def test_wj4_dyn_container_of_inside_fallthrough_switch(tmp_path):
    # entry_common.c.i's real composition: the runtime container_of rides
    # INSIDE a fall-through case arm; the file-scope SA guards the layout.
    # f(node[1], 1) enters case 1, recovers the owner, FALLS THROUGH into
    # case 2 which stamps the result.
    _pair(tmp_path, "wj4_dc",
          "struct rb_node { unsigned long c; struct rb_node *r, *l; };\n"
          "struct ltn { struct rb_node node[2]; void *priv; };\n"
          "struct owner { int magic; struct ltn ltn; };\n"
          "_Static_assert(__builtin_offsetof(struct owner, ltn) == 8,"
          ' "layout");\n'
          "#define container_of(ptr, type, member) \\\n"
          "  ((type *)((char *)(ptr) - __builtin_offsetof(type, member)))\n"
          "int f(struct rb_node *n, int idx){ int hit = 0;\n"
          "  switch (idx) { case 1: hit += 1;\n"
          "      if (container_of(n, struct owner, ltn.node[idx])->magic"
          " == 77) hit += 2;\n"
          "      " + FT + ";\n"
          "      case 2: hit += 4; }\n"
          "  return hit; }\n"
          "int main(void){ struct owner o; o.magic = 77;\n"
          "  return f(&o.ltn.node[1], 1) == 7 ? 0 : 1; }\n", 0)


def test_wj4_dyn_offsetof_in_sa_rejects_both(tmp_path):
    # The composition's REJECT arm: SA condition CONTAINING a runtime
    # index — the fold hands back the dyn node, fold_truthy None → blcc
    # "expression in static assertion is not constant"; gcc rc1 the same
    # verdict (same sentence). The dyn arm must NOT fake constness.
    g = _gcc_rc(tmp_path, "wj4_rej",
                "struct E { long v; };\nstruct A { struct E arr[4]; };\n"
                "int i;\n_Static_assert(__builtin_offsetof(struct A,"
                " arr[i]) == 8, \"x\");\n")
    assert g.returncode == 1, g.stderr
    assert "not constant" in g.stderr, g.stderr
    r = _compile(tmp_path, "wj4_rej",
                 "struct E { long v; };\nstruct A { struct E arr[4]; };\n"
                 "int i;\n_Static_assert(__builtin_offsetof(struct A,"
                 " arr[i]) == 8, \"x\");\n")
    assert r.returncode != 0 and "not constant" in r.stderr, r.stderr


def test_wj4_mini_kernel_triple_run_pair(tmp_path):
    # ALL THREE corpus classes in ONE TU (the 461+205+118+327 shapes):
    # file-scope kparam SA (the verbatim filename law), FT in a sigorsets
    # switch, dyn container_of, and the combined observable run-pair.
    src = (
        "struct filename { const char *name; int iname; };\n"
        "_Static_assert(__builtin_offsetof(struct filename, iname) %\n"
        '  sizeof(long) == 0, "kparam layout");\n'
        "struct rb_node { unsigned long c; struct rb_node *r, *l; };\n"
        "struct ltn { struct rb_node node[2]; };\n"
        "struct owner { int magic; struct ltn ltn; };\n"
        "#define container_of(ptr, type, member) \\\n"
        "  ((type *)((char *)(ptr) - __builtin_offsetof(type, member)))\n"
        "static unsigned long s0, s1;\n"
        "static void sigor(unsigned long *d, const unsigned long *a,\n"
        "                 const unsigned long *b, int words)\n"
        "{\n"
        "        switch (words) {\n"
        "         case 2: d[1] = a[1] | b[1];\n"
        "                  " + FT + ";\n"
        "         case 1: d[0] = a[0] | b[0];\n"
        "        }\n"
        "}\n"
        "struct owner *back(struct rb_node *n, int idx) {\n"
        "  return container_of(n, struct owner, ltn.node[idx]); }\n"
        "int main(void){ unsigned long a[2], b[2], d[2];\n"
        "  struct owner o; o.magic = 77;\n"
        "  a[0] = 3; a[1] = 1; b[0] = 4; b[1] = 2;\n"
        "  sigor(d, a, b, 2);\n"
        "  s0 = d[0]; s1 = d[1];\n"
        "  if (back(&o.ltn.node[1], 1)->magic != 77) return 9;\n"
        "  if (back(&o.ltn.node[0], 0)->magic != 77) return 8;\n"
        "  return (int)(s0 + s1 * 10); }\n")   # 7 + 3*10 = 37
    _pair(tmp_path, "wj4_mk", src, 37)


def test_wj4_sa_after_ft_file_scope_stays_valid(tmp_path):
    # file-scope sequence: attr+`;` no-op then a file-scope SA (the ft_i
    # exemption and the SA law side by side) — rc0 both, no interference.
    _ok(tmp_path, "wj4_seq",
        FT + ";\n"
        "struct S { int x; };\n"
        '_Static_assert(sizeof(struct S) == 4, "sized");\n'
        "int v = 1;\n")
