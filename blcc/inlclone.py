"""W-R (MC 12714) support: pure label-clone for the per-site asm-goto
splice. Tree surgery only — rebuild a subtree with a label rename,
sharing every untouched node (so a second splice of one function never
mutates the first's labels/templates/operand objects). Lives beside the
inliner seam (`blcc/inliner.py`); no codegen knowledge here."""
import dataclasses

from blcc import ast


def inl_clone(node, fresh):
    """Rebuild with the label rename applied; untouched subtrees stay
    SHARED."""
    if isinstance(node, (tuple, list)):
        seq = [inl_clone(x, fresh) for x in node]
        if all(x is o for x, o in zip(seq, node)):
            return node
        return tuple(seq) if isinstance(node, tuple) else seq
    if not dataclasses.is_dataclass(node):
        return node
    repl = {}
    for f in dataclasses.fields(node):
        v = getattr(node, f.name, None)
        nv = inl_clone(v, fresh)
        if nv is not v:
            repl[f.name] = nv
    if isinstance(node, ast.Label) and node.name in fresh:
        repl["name"] = fresh[node.name]
    if isinstance(node, ast.AsmStmt) and node.labels:
        names = tuple(fresh.get(x, x) for x in node.labels)
        if names != tuple(node.labels):
            repl["labels"] = names
        tmpl = node.tmpl
        for old, lab in fresh.items():
            tmpl = tmpl.replace("%l[" + old + "]", "%l[" + lab + "]")
        if tmpl != node.tmpl:
            repl["tmpl"] = tmpl
    if not repl:
        return node
    return dataclasses.replace(node, **repl)
