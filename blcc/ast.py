"""AST node dataclasses ONLY (ARCHITECTURE.md §3) — no behavior beyond fields.

Every node carries file:line:col (from the Node base). Type nodes are recorded
faithfully so codegen can derive size/width from the §4 size table; sizing is
NOT done here. Plain helper records (Member, Param) are not grammar nodes and
carry no position.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Optional, Tuple


# --------------------------------------------------------------------------
# Base
# --------------------------------------------------------------------------

@dataclass(frozen=True)
class Node:
    file: str
    line: int
    col: int


# --------------------------------------------------------------------------
# Types (§4: char short int long void; pointers 8 bytes — codegen's table)
# --------------------------------------------------------------------------

@dataclass(frozen=True)
class BuiltinType(Node):
    name: str          # char | short | int | long | void


@dataclass(frozen=True)
class PtrType(Node):
    inner: Node


@dataclass(frozen=True)
class ArrayType(Node):
    inner: Node
    size: Optional[Node]   # IntLit; None only for parameters (§4)


@dataclass(frozen=True)
class StructType(Node):
    tag: str               # codegen derives layout from the StructDecl by tag


# --------------------------------------------------------------------------
# Helper records (no position: they are fields, not grammar nodes)
# --------------------------------------------------------------------------

@dataclass(frozen=True)
class Member:
    name: str
    type: Node


@dataclass(frozen=True)
class Param:
    name: Optional[str]
    type: Node


# --------------------------------------------------------------------------
# Declarations / translation unit
# --------------------------------------------------------------------------

@dataclass(frozen=True)
class TranslationUnit(Node):
    decls: Tuple[Node, ...]


@dataclass(frozen=True)
class StructDecl(Node):
    tag: str
    members: Optional[Tuple[Member, ...]]   # None = forward declaration only


@dataclass(frozen=True)
class EnumDecl(Node):
    constants: Tuple[Tuple[str, int], ...]  # int-valued (§4)


@dataclass(frozen=True)
class TypedefDecl(Node):
    name: str
    type: Node


@dataclass(frozen=True)
class FuncDecl(Node):
    name: str
    ret_type: Node
    params: Tuple[Param, ...]
    body: Optional[Node]     # Compound; None = prototype only
    is_static: bool = False


@dataclass(frozen=True)
class VarDecl(Node):
    name: str
    type: Node
    init: Optional[Node]     # None = no initializer
    is_static: bool = False  # only ever True at file scope (§5 elsewhere)


@dataclass(frozen=True)
class InitList(Node):
    items: Tuple[Node, ...]


# --------------------------------------------------------------------------
# Statements (§4)
# --------------------------------------------------------------------------

@dataclass(frozen=True)
class Compound(Node):
    body: Tuple[Node, ...]


@dataclass(frozen=True)
class ExprStmt(Node):
    expr: Optional[Node]


@dataclass(frozen=True)
class If(Node):
    cond: Node
    then: Node
    orelse: Optional[Node]


@dataclass(frozen=True)
class While(Node):
    cond: Node
    body: Node


@dataclass(frozen=True)
class DoWhile(Node):
    body: Node
    cond: Node


@dataclass(frozen=True)
class For(Node):
    init: Optional[Node]     # VarDecl | ExprStmt | None
    cond: Optional[Node]
    step: Optional[Node]
    body: Node


@dataclass(frozen=True)
class Break(Node):
    pass


@dataclass(frozen=True)
class Continue(Node):
    pass


@dataclass(frozen=True)
class Return(Node):
    value: Optional[Node]


@dataclass(frozen=True)
class Switch(Node):
    control: Node
    body: Tuple[Node, ...]   # statements incl. Case/Default markers


@dataclass(frozen=True)
class StmtExpr(Node):
    # §1 row 6 / §2.4: GNU statement-expression `({ stmts… final; })`.
    # stmts run at that point; value = final ExprStmt's expression (None =
    # void, `({;})`). FILE scope is a mirror-reject (§2.4d) in data.py.
    stmts: Tuple[Node, ...]
    value: Optional[Node]


@dataclass(frozen=True)
class TypeOf(Node):
    # §1 row 6c / §2.6: __typeof__(expr|type) — a TYPE node that stands for
    # its operand's type; resolved by TypeMap._untype (§2A M2-C5 leg 3).
    # Exactly one of expr / typ is set. Operand NOT evaluated (only typed).
    expr: Optional[Node]
    typ: Optional[Node]


@dataclass(frozen=True)
class Goto(Node):
    name: str


@dataclass(frozen=True)
class Label(Node):
    name: str
    stmt: Node


@dataclass(frozen=True)
class LabelDecl(Node):
    names: Tuple[str, ...]         # __label__ a, b;  (§1 row 4d)


@dataclass(frozen=True)
class LabelAddr(Node):
    name: str                      # &&label  (§2.6; _THIS_IP_ shape)


@dataclass(frozen=True)
class Case(Node):
    value: int               # compile-time constant (§4)
    stmt: Optional[Node]


@dataclass(frozen=True)
class CaseRange(Node):
    lo: int                  # gnu89 `case lo ... hi:` (§1 row 4b; measured
    hi: int                  # IN in this gcc; reversed range = empty,
    stmt: Optional[Node]     # gcc accepts it silently)


@dataclass(frozen=True)
class Default(Node):
    stmt: Optional[Node]


# --------------------------------------------------------------------------
# Expressions (§4 operators)
# --------------------------------------------------------------------------

@dataclass(frozen=True)
class IntLit(Node):
    value: int
    itype: str = "int"       # §2.1 typed literal kind (lexer suffix/range)


@dataclass(frozen=True)
class CharLit(Node):
    value: int


@dataclass(frozen=True)
class FloatLit(Node):
    # §1 row 14 (M2): IEEE-754 BITS for double/float STORAGE. Any FP
    # arithmetic/cast/conversion is a LOUD sema wall (DEFER).
    bits: int
    fsize: int = 8


@dataclass(frozen=True)
class StrLit(Node):
    value: str               # decoded; bytes are .rodata's concern (§4)


@dataclass(frozen=True)
class Ident(Node):
    name: str


@dataclass(frozen=True)
class Unary(Node):
    op: str                  # - + ! ~ & *
    operand: Node


@dataclass(frozen=True)
class Binary(Node):
    op: str
    left: Node
    right: Node


@dataclass(frozen=True)
class Assign(Node):
    target: Node
    value: Node


@dataclass(frozen=True)
class AssignOp(Node):
    op: str                  # += -= *= /= %= &= |= ^= <<= >>=
    target: Node
    value: Node


@dataclass(frozen=True)
class IncDec(Node):
    op: str                  # ++ | --
    operand: Node
    prefix: bool


@dataclass(frozen=True)
class Cast(Node):
    type: Node
    operand: Node


@dataclass(frozen=True)
class Sizeof(Node):
    typ: Optional[Node]      # exactly one of typ/arg is set (§4 forms)
    arg: Optional[Node]


@dataclass(frozen=True)
class Call(Node):
    callee: Node
    args: Tuple[Node, ...]


@dataclass(frozen=True)
class Select(Node):
    base: Node
    field: str
    arrow: bool              # True = ->, False = .


@dataclass(frozen=True)
class Index(Node):
    base: Node
    index: Node
