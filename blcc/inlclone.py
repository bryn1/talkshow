"""W-R (MC 12714) support: pure label-clone for the per-site asm-goto
splice. Tree surgery only — rebuild a subtree with a label rename,
sharing every untouched node (so a second splice of one function never
mutates the first's labels/templates/operand objects). Lives beside the
inliner seam (`blcc/inliner.py`); no codegen knowledge here.

M4 W-S (MC 12716) extends the SAME mechanism with the gcc scope law for
`({...})` groups: `scoped` maps the group's doc-order seq to its fresh
name map, `seq_by_id` finds a group's seq by NODE IDENTITY (original
instances; shared untouched subtrees keep ids, and a rebuilt parent is
numbered from its original before rebuilding). Entering a group pushes
its fresh names onto the ACTIVE rename chain (innermost wins — l11's
shadow law); Label DEFINITIONS, `&&label` (LabelAddr) references and
`goto` (Goto) references all rename through the chain TOGETHER — a
partial rename is the plant-1 class, and an un-renamed nested `goto`
would silently capture a SAME-NAMED label of the CALLER (wrong target,
never silent law)."""
import dataclasses

from blcc import ast
from blcc.types import stmt_children, stmtexprs_in_expr


def inl_clone(node, fresh, scoped=None, seq_by_id=None):
    """Rebuild with the label rename applied; untouched subtrees stay
    SHARED."""
    return _clone(node, fresh, scoped, seq_by_id)


def _clone(node, active, scoped, seq_by_id):
    if isinstance(node, (tuple, list)):
        seq = [_clone(x, active, scoped, seq_by_id) for x in node]
        if all(x is o for x, o in zip(seq, node)):
            return node
        return tuple(seq) if isinstance(node, tuple) else seq
    if not dataclasses.is_dataclass(node):
        return node
    if scoped is not None and isinstance(node, ast.StmtExpr):
        sq = (seq_by_id or {}).get(id(node))
        if sq is not None and sq in scoped:
            merged = dict(active)
            merged.update(scoped[sq])          # innermost wins (l11 law)
            active = merged
    repl = {}
    for f in dataclasses.fields(node):
        v = getattr(node, f.name, None)
        nv = _clone(v, active, scoped, seq_by_id)
        if nv is not v:
            repl[f.name] = nv
    if isinstance(node, ast.Label) and node.name in active:
        repl["name"] = active[node.name]
    if isinstance(node, ast.LabelAddr) and node.name in active:
        repl["name"] = active[node.name]
    if isinstance(node, ast.Goto) and node.name in active:
        repl["name"] = active[node.name]
    if isinstance(node, ast.AsmStmt) and node.labels:
        names = tuple(active.get(x, x) for x in node.labels)
        if names != tuple(node.labels):
            repl["labels"] = names
        tmpl = node.tmpl
        for old, lab in active.items():
            tmpl = tmpl.replace("%l[" + old + "]", "%l[" + lab + "]")
        if tmpl != node.tmpl:
            repl["tmpl"] = tmpl
    if not repl:
        return node
    return dataclasses.replace(node, **repl)


def _inl_group_defs(body):
    """Group-scoped label defs of a candidate body, M4 W-S (MC 12716).
    Returns (defs, seq_by_id); defs = {seq: [(name, def_depth)]} in
    DOCUMENT order (seq = the group's doc-order number, id-keyed via
    seq_by_id so the CLONE finds each group's fresh map by node identity
    — shared untouched subtrees keep their ids, rebuilt parents look
    their original up before rebuilding). defs is None on a DUPLICATE
    name inside one group (invalid C, gcc l12: the candidate stays
    CALL law and the copy posture LOUDs the §2.5 wall)."""
    defs = {}
    seq_by_id = {}
    dup = []

    # One recursive walk; groups reachable both as statement children
    # and through expression fields share the SAME doc-order numbering:
    # both routes visit nodes in source order (dataclass field order).
    def walk2(nodes, depth, seq):
        for s in nodes:
            if isinstance(s, ast.Label) and seq is not None:
                ent = defs.setdefault(seq, [])
                if any(nm == s.name for nm, _ in ent):
                    dup.append(s.name)
                ent.append((s.name, depth))
            nd = depth + (1 if isinstance(s, ast.StmtExpr) else 0)
            if isinstance(s, ast.StmtExpr):
                sq = seq_by_id.setdefault(id(s), len(seq_by_id))
                walk2(stmt_children(s), nd, sq)
            else:
                walk2(stmt_children(s), nd, seq)
            for e in stmtexprs_in_expr(s):
                sq2 = seq_by_id.setdefault(id(e), len(seq_by_id))
                walk2(e.stmts, depth + 1, sq2)
                # groups NESTED in e.stmts are covered by walk2 above;
                # groups riding e.value's expression fields too:
                for g in stmtexprs_in_expr(e):
                    sq3 = seq_by_id.setdefault(id(g), len(seq_by_id))
                    walk2(g.stmts, depth + 1, sq3)
    walk2(stmt_children(body), 0, None)
    return (None, None) if dup else (defs, seq_by_id)
