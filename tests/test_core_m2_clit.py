"""M55 — compound literals (§1 row 11, post-pp 589 files / 3794 sites).
Cast-vs-literal disambiguation `(TYPE){init}`; storage law: inside a
function the literal is an unnamed AUTO object (frame slot, address may
escape); at file scope it is an unnamed STATIC object (bytes emitted,
`&`-in-initializer becomes an address constant). Scalar literals yield
the VALUE; aggregate literals yield the address (blcc's aggregate-value
convention). Designated inits ride inside `(struct T){ .f = v }` (T+9a
normalization, shared). Struct COPY from a literal (`s = (struct T){..}`)
stays the shipped §5 'struct assignment' wall — the row-11 RB_ROOT_CACHED
witness stays behind that wall by design, pinned here as a NEG leg.
"""
import os
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

ITMP = os.path.join(ROOT, ".tmp", "itclit")


def _fresh(tag):
    os.makedirs(ITMP, exist_ok=True)
    return os.path.join(ITMP, "{}_{}_1".format(tag, os.getpid()))


def both_run(src, tag):
    p = _fresh(tag)
    src_path = p + ".c"
    with open(src_path, "w", encoding="utf-8") as fh:
        fh.write(src)
    out_b = p + ".blcc"
    rb = subprocess.run([sys.executable, "-m", "blcc", src_path, "-o",
                         out_b], cwd=ROOT, capture_output=True, text=True,
                        timeout=60)
    out_g = p + ".gcc"
    rg = subprocess.run(["gcc", "-w", "-std=gnu89", "-O0", "-o", out_g,
                         src_path], capture_output=True, text=True,
                        timeout=60)
    assert rg.returncode == 0, "gcc twin must build ({}):\n{}".format(
        tag, rg.stderr)
    assert rb.returncode == 0, "blcc compile failed ({}):\n{}".format(
        tag, rb.stderr)
    pb = subprocess.run([out_b], capture_output=True, timeout=30)
    pg = subprocess.run([out_g], capture_output=True, timeout=30)
    assert (pb.returncode, pb.stdout) == (pg.returncode, pg.stdout), \
        "run-pair mismatch ({}): blcc={} gcc={}".format(
            tag, (pb.returncode, pb.stdout), (pg.returncode, pg.stdout))
    for f in (src_path, out_b, out_g):
        os.remove(f)


def loud(src, tag, frag):
    p = _fresh(tag)
    src_path = p + ".c"
    with open(src_path, "w", encoding="utf-8") as fh:
        fh.write(src)
    r = subprocess.run([sys.executable, "-m", "blcc", src_path,
                        "-o", p + ".out"], cwd=ROOT, capture_output=True,
                       text=True, timeout=60)
    os.remove(src_path)
    assert r.returncode == 2, "{}: expected LOUD, got {} {}".format(
        tag, r.returncode, r.stderr)
    assert frag in r.stderr, "{}: {} must name {!r}".format(tag, r.stderr,
                                                            frag)


def test_scalar_literal_value_run_pair():
    both_run("""
int main(void) {
    int x = (int){7} + 1;
    if (x != 8) return 1;
    if (sizeof (int){7} != 4) return 2;
    if ((int){-3} < (int){2}) return 0;
    return 3;
}
""", "c-scalar")


def test_array_literal_decays_to_pointer_run_pair():
    both_run("""
int main(void) {
    int *p = (int[]){4, 5, 6};
    unsigned long *u = (unsigned long[]){1, 0xffff00000000UL};
    if (p[0] != 4 || p[1] != 5 || p[2] != 6) return 1;
    if (u[1] != 0xffff00000000UL) return 2;
    *(int[]){0} = 0;                     /* literal is a modifiable lvalue */
    char *s = (char[]){'a', 'b', 0};
    if (s[1] != 'b') return 3;
    return 0;
}
""", "c-array")


def test_address_of_scalar_literal_run_pair():
    both_run("""
int main(void) {
    int *q = &(int){42};
    *q += 1;
    if (*q != 43) return 1;
    return 0;
}
""", "c-ampscalar")


def test_struct_literal_via_pointer_run_pair():
    both_run("""
struct P { int lo; int hi; };
int main(void) {
    struct P *pp = &(struct P){1, 2};
    if (pp->lo != 1 || pp->hi != 2) return 1;
    pp->hi = 9;
    if (pp->hi != 9) return 2;
    if ((struct P){5, 6}.hi != 6) return 3;
    return 0;
}
""", "c-struct")


def test_anon_union_literal_run_pair():
    both_run("""
union U { int v; char c; };
int main(void) {
    union U *u = &(union U){ .c = 1 };
    if (u->v != 1) return 1;
    if (((union U){ .v = 0x41 }).c != 0x41) return 2;
    return 0;
}
""", "c-union")


def test_designated_inside_literal_run_pair():
    both_run("""
struct A { int x; int y; };
struct T { struct A a; int z; };
int main(void) {
    struct T *t = &(struct T){ .z = 9, .a = { 1 } };
    if (t->a.x != 1 || t->a.y != 0 || t->z != 9) return 1;
    return 0;
}
""", "c-desig")


def test_filescope_literal_bytes_run_pair():
    # mut-clit target: a compound literal at file scope MUST NOT be
    # rejected — it names an unnamed STATIC object.
    both_run("""
struct T { int a; int b; };
static struct T g = (struct T){ 2, 3 };
static int *gp = (int[]){ 7, 8 };
static char *sp = (char[]){'h', 'i', 0};
int main(void) {
    if (g.a != 2 || g.b != 3) return 1;
    if (gp[0] != 7 || gp[1] != 8) return 2;
    if (sp[0] != 'h' || sp[2] != 0) return 3;
    return 0;
}
""", "c-file")


def test_literal_in_stmt_expr_and_call_run_pair():
    both_run("""
struct P { int lo; int hi; };
int id(struct P *p) { return p->lo * 10 + p->hi; }
int main(void) {
    int x = ({ int r = *(int[]){1, 2, 3} + 2; r; });
    if (x != 3) return 1;
    if (id(&(struct P){5, 6}) != 56) return 2;
    return 0;
}
""", "c-se")


def test_literal_struct_copy_stays_struct_assignment_wall():
    # §1 row 11 witness shape `head->rb_root = (struct rb_root_cached){…}`
    # — compound literal + struct assignment. The copy itself is the
    # SHIPPED §5 'struct assignment' wall; the literal must not smuggle
    # it through. Pinned so the wall cannot silently widen.
    loud("struct P { int a; int b; };\n"
         "int main(void){ struct P s = {0,0}; s = (struct P){1,2}; "
         "return s.a; }\n", "c-copy", "struct assignment")


def test_cast_vs_literal_disambiguation_run_pair():
    both_run("""
int main(void) {
    int v = 3;
    if ((long)v != 3) return 1;              /* plain CAST still works */
    if ((long){v} != 3) return 2;            /* same spelling + init = literal */
    if ((int)(long){2} != 2) return 3;       /* cast applied to a literal */
    return 0;
}
""", "c-disamb")
