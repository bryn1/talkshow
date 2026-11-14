# LINES reason: the inline-asm FRONT half (grammar L0 + constraint model +
# the §3.2-N normalization and §3.2 implicit-use tables) is ONE concern —
# what a construct MEANS before any register is chosen; codegen lives in
# blcc/asmgen.py (§3 concern boundary; keeps each file under the 400 law).
"""M3 GNU inline asm — grammar, constraints, clobber tables (contract v3.1).

AsmParseMixin (blcc.parser.Parser base) parses the L0 grammar:
    asm [__inline|inline] [volatile|__volatile__] [goto]
        ( template [ : outs [ : ins [ : clobbers [ : labels ]]]] ) ;
The template is ONE merged literal (M1 zero-gap lexer merge + M2 §6g
juxtaposition law — reused here with the same merge). Constraints and
clobber names are kept RAW (parsed at codegen once the target exists).

Tables owned here, consumed by blcc/asmgen.py:
  POOL / CALLEE_SAVED / FIXED  — §3.2/L2 color universe
  norm_clobber()               — §3.2-N: legacy + modern spellings in,
                                 UNKNOWN = §8 `asm:` loud NAMING it
  implicit_regs()              — §3.2 implicit-use table (F-5, 21 rows)
  parse_constraint()           — S1-S9 SUPPORT set; L1/L3 letters LOUD
  reg_name()                   — §3.5 size-modifier register names
"""
from __future__ import annotations

import re
from typing import List, Optional, Tuple

from blcc import ast
from blcc.lexer import DiagError

# §3.2 pool: allocatable set (rsp/rbp NEVER enter — N2). Greedy order; A16
# re-runs the allocator under PERMUTED orders — pool order must not change
# correctness (an operand never occupies a clobber-named reg).
POOL: List[str] = ["rax", "rcx", "rdx", "rbx", "rsi", "rdi",
                   "r8", "r9", "r10", "r11", "r12", "r13", "r14", "r15"]

# §6/§3.6-T: callee-saved regs; T brackets save/restore them around any
# asm statement that writes them.
CALLEE_SAVED = ("rbx", "r12", "r13", "r14", "r15")

# §3.10: register-asm bind classes. STABLE = persistent reg (C-read rides
# the reg); SCRATCH = everything else (shadow slot is the C value's home).
STABLE_BIND = frozenset(("rbx", "r12", "r13", "r14", "r15", "rsp", "rbp"))

# §3.5/L2: fixed constraint letters → physical register.
FIXED = {"a": "rax", "c": "rcx", "d": "rdx", "S": "rsi", "D": "rdi",
         "b": "rbx"}

# ---------------------------------------------------------------- §3.2-N --
_REG_ALIAS = {}
for _p, _names in (("rax", ("ax", "eax", "rax")),
                   ("rbx", ("bx", "ebx", "rbx")),
                   ("rcx", ("cx", "ecx", "rcx")),
                   ("rdx", ("dx", "edx", "rdx")),
                   ("rsi", ("si", "esi", "rsi")),
                   ("rdi", ("di", "edi", "rdi")),
                   ("rsp", ("sp", "esp", "rsp")),
                   ("rbp", ("bp", "ebp", "rbp"))):
    for _n in _names:
        _REG_ALIAS[_n] = _p
for _r in ("r8", "r9", "r10", "r11", "r12", "r13", "r14", "r15"):
    for _s in (_r, _r + "d", _r + "b", "%" + _r):
        _REG_ALIAS[_s] = _r


def norm_clobber(name: str) -> Tuple[str, ...]:
    """Resolve one clobber-section string to normalized tokens:
    ("memory",) | ("cc",) | (phys-reg,). ValueError = the caller raises the
    §8 `asm:` diagnostic NAMING THE CLOBBER (§3.2-N(4): UNKNOWN = loud,
    NEVER silently dropped). Legacy 16/32-bit spellings ride the measured
    table (uaccess.h:225 "ebx", msr.h:234 "ecx", hypercall "flags"→cc)."""
    s = name.strip()
    if s.startswith("%"):
        s = s[1:]
    low = s.lower()
    if low == "memory":
        return ("memory",)
    if low in ("cc", "flags"):                  # flags → cc class (§N(3))
        return ("cc",)
    if low in _REG_ALIAS:
        return (_REG_ALIAS[low],)
    raise ValueError(name)


# --------------------------------------------------------- §3.2 implicit --
# (mnemonic stem, implicit USES, implicit DEFS) — the contract's F-5 table.
# Suffix-tolerant word match ("idivq" ⊢ "idiv"). Rows are pinned so a future
# site that does NOT declare its implicit regs stays SOUND by construction:
# every use/def reg leaves the FREE pool; DEFS ∩ callee-saved join T.
_IMPLICIT = (
    ("cmpxchg16b", ("rax", "rdx"), ("rax",)),
    ("cmpxchg8b", ("rax", "edx"), ("rax",)),
    ("cmpxchg", ("rax",), ("rax",)),
    ("idiv", ("rdx", "rax"), ("rax", "rdx")),
    ("div", ("rdx", "rax"), ("rax", "rdx")),
    ("imul", ("rax",), ("rdx", "rax")),
    ("mul", ("rax",), ("rdx", "rax")),
    ("rdtscp", (), ("rax", "rdx", "rcx")),
    ("rdtsc", (), ("rax", "rdx")),
    ("rdpmc", ("rcx",), ("rax", "rdx")),
    ("rdmsr", ("rcx",), ("rax", "rdx")),
    ("wrmsr", ("rcx", "rax", "rdx"), ()),
    ("cpuid", ("rax", "rcx"), ("rax", "rbx", "rcx", "rdx")),
    ("xgetbv", ("rcx",), ("rax", "rdx")),
    ("xsetbv", ("rcx", "rax", "rdx"), ("rax",)),
    ("mulx", ("rdx",), ()),
    ("shlx", (), ()), ("shrx", (), ()), ("sarx", (), ()),
    ("lahf", ("rax",), ()), ("sahf", ("rax",), ()),
    ("monitor", ("rax", "rcx", "rdx"), ("rax", "rcx", "rdx")),
    ("mwait", ("rax", "rcx"), ("rax", "rcx", "rdx")),
    ("loopne", ("rcx",), ("rcx",)), ("loope", ("rcx",), ("rcx",)),
    ("loop", ("rcx",), ("rcx",)),
    ("syscall", ("rcx", "r11", "rax"), ("rcx", "r11", "rax")),
    ("sysret", ("rcx", "r11", "rax"), ("rcx", "r11", "rax")),
    ("repnz", ("rcx", "rsi", "rdi"), ("rcx", "rsi", "rdi")),
    ("repne", ("rcx", "rsi", "rdi"), ("rcx", "rsi", "rdi")),
    ("repz", ("rcx", "rsi", "rdi"), ("rcx", "rsi", "rdi")),
    ("repe", ("rcx", "rsi", "rdi"), ("rcx", "rsi", "rdi")),
    ("rep", ("rcx", "rsi", "rdi"), ("rcx", "rsi", "rdi")),
    # ud2 / int3: NONE — operand-less volatile traps (§1.3 measured 4 sites).
)

_WORD_RE = re.compile(r"[A-Za-z][A-Za-z0-9_]*")


def implicit_regs(template: str) -> Tuple[List[str], List[str]]:
    """Scan the template ONCE per stmt (§3.2): (uses, defs). Over-matching
    costs pool colors only — never a wrong color."""
    uses: List[str] = []
    defs: List[str] = []
    hit = set()
    for w in _WORD_RE.findall(template):
        w = w.lower()
        for stem, u, d in _IMPLICIT:
            if w == stem or (w.startswith(stem)
                             and set(w[len(stem):]) <= set("blwq016")):
                if stem not in hit:
                    hit.add(stem)
                    uses.extend(x for x in u if x not in uses)
                    defs.extend(x for x in d if x not in defs)
                break
    if "%cl" in template or "%ecx" in template:
        if "rcx" not in uses:                   # shift/rotate by cl row
            uses.append("rcx")
    return uses, defs


# ------------------------------------------------------- constraint model --
_IMMO = {"i": (-2 ** 31, 2 ** 31 - 1),          # imm32
         "I": (0, 63), "N": (0, 255), "n": (0, 255)}   # range-checked L4


class CInfo:
    __slots__ = ("mods", "cls", "alt", "fixed", "match", "sym", "raw")

    def __init__(self):
        self.mods = ""          # subset of "+&" ("=" implicit unless +)
        self.cls = ""           # fixed r q m p g i I N n match
        self.alt = ""           # composite fallback class (rm/iq/Ir/qm)
        self.fixed = ""         # physical reg when cls == fixed
        self.match = None       # numeric matching index (S9)
        self.sym = None         # symbolic matching output name (S9)
        self.raw = ""

    @property
    def is_out(self) -> bool:
        return "+" in self.mods

    @property
    def readwrite(self) -> bool:
        return "+" in self.mods

    @property
    def early(self) -> bool:
        return "&" in self.mods


def _loud(at, message: str, found: str) -> None:
    raise DiagError("asm", at.file, at.line, at.col, message, found)


def parse_constraint(cstr: str, at) -> CInfo:
    """Parse ONE constraint string. Every unsupported letter/modifier/spelling
    LOUDs naming it (L1/L3/N1 — never silent, never a downgraded class)."""
    ci = CInfo()
    ci.raw = cstr
    m = re.fullmatch(r"\[([A-Za-z_][A-Za-z0-9_]*)\]", cstr.strip())
    if m:
        ci.cls = "match"
        ci.sym = m.group(1)                      # symbolic matching (S9)
        return ci
    if cstr.startswith("=@") or "=@cc" in cstr:
        _loud(at, "flag-output constraint '\"=@cc…\"' (N1) is LOUD: blcc "
                  "never predefines __GCC_ASM_FLAG_OUTPUTS__ (§3.7-L7)",
              "@cc")
    letters = ""
    for ch in cstr:
        if ch in "=+&":
            ci.mods += ch
            continue
        if ch == "!":
            _loud(at, "constraint modifier '!' is not in the §3 SUPPORT set "
                      "(L3/L8 posture — 0 sites)", "!")
        if ch.isdigit():
            ci.cls = "match"
            ci.match = int(ch)                   # numeric matching (S9)
            continue
        letters += ch
    if ci.cls == "match":
        return ci
    lset = set(letters)
    if not lset:
        _loud(at, "constraint '{}' names no operand class (§3 L0)".format(
            cstr), cstr)
    if lset in ({"N", "d"}, {"n", "d"}):
        # io.h BUILDIO (1098 LIVE io.c.i sites): "Nd"/"dN" port = dx-fixed
        # preferred — the gcc-11.4 -Os oracle picks %dx for `outb %0,%w1`
        # (measured this session); the $imm alternative is the contract's
        # L4 class, reserved for a future rdx-busy site (0 today).
        ci.cls = "fixed"
        ci.fixed = "rdx"
        ci.alt = "i"
        return ci
    fixed = lset & set(FIXED)
    if fixed:
        if len(fixed) > 1 or lset - fixed:
            _loud(at, "constraint '{}' mixes a fixed-register letter with "
                      "another class (§3 L2)".format(cstr), cstr)
        ci.cls = "fixed"
        ci.fixed = FIXED[next(iter(fixed))]
        return ci
    if lset <= {"m"}:
        ci.cls = "m"
    elif lset == {"p"}:
        ci.cls = "p"                             # address-only, m-lowering
    elif lset == {"g"}:
        ci.cls = "g"                             # m, then r, then i (S4)
    elif lset <= {"r", "e"}:
        ci.cls = "r"                             # e ⊆ "er" ≡ r (S2)
    elif lset == {"q"}:
        ci.cls = "q"                             # REX-reachable regs (S2)
    elif lset == {"i"}:
        ci.cls = "i"
    elif lset == {"I"}:
        ci.cls = "I"
    elif lset == {"N"}:
        ci.cls = "N"
    elif lset == {"n"}:
        ci.cls = "n"
    elif lset in ({"r", "m"}, {"q", "m"}):
        ci.cls = "m"                             # rm/qm: memory-preferred
        ci.alt = "r" if "r" in lset else "q"
    elif lset == {"i", "q"}:
        ci.cls = "i"
        ci.alt = "q"                             # iq: imm-or-REX-reg (S2)
    elif lset == {"I", "r"}:
        ci.cls = "I"
        ci.alt = "r"                             # Ir: imm-or-reg (bitops)
    else:
        _loud(at, "constraint letter(s) '{}' are not in the M3 SUPPORT set "
                  "(§2 S1-S9 / L1: k,x,t,u,z,s,v,o,Z08,A,f,Q,M,J,w are "
                  "guard-inactive or absent)".format("".join(sorted(lset))),
              "".join(sorted(lset)))
    return ci


# ------------------------------------------------------ §3.5 size names --
# ------------------------------------------------------ S3.5 size names --
_HIGH8 = {"rax": "%ah", "rcx": "%ch", "rdx": "%dh", "rbx": "%bh"}
_NAMES = {  # reg -> (64, 32, 16, 8) spellings; %b/%w/%q/%k ride the table
    "rax": ("%rax", "%eax", "%ax", "%al"),
    "rbx": ("%rbx", "%ebx", "%bx", "%bl"),
    "rcx": ("%rcx", "%ecx", "%cx", "%cl"),
    "rdx": ("%rdx", "%edx", "%dx", "%dl"),
    "rsi": ("%rsi", "%esi", "%si", "%sil"),     # sil/dil/bpl/spl need REX
    "rdi": ("%rdi", "%edi", "%di", "%dil"),     # (as encodes it; %k forces)
    "rbp": ("%rbp", "%ebp", "%bp", "%bpl"),
    "rsp": ("%rsp", "%esp", "%sp", "%spl"),
    "r8": ("%r8", "%r8d", "%r8w", "%r8b"),
    "r9": ("%r9", "%r9d", "%r9w", "%r9b"),
    "r10": ("%r10", "%r10d", "%r10w", "%r10b"),
    "r11": ("%r11", "%r11d", "%r11w", "%r11b"),
    "r12": ("%r12", "%r12d", "%r12w", "%r12b"),
    "r13": ("%r13", "%r13d", "%r13w", "%r13b"),
    "r14": ("%r14", "%r14d", "%r14w", "%r14b"),
    "r15": ("%r15", "%r15d", "%r15w", "%r15b"),
}
_WIDX = {8: 0, 4: 1, 2: 2, 1: 3}


def reg_name(reg: str, width: int, mod: Optional[str] = None,
             at=None) -> str:
    """S3.5: assigned physical reg printed at a C width / size modifier.
    %b/%w/%q/%k map onto the width table; %h = legacy high byte only
    (ah/ch/dh/bh -- r8+ LOUD, never silent); unknown reg = LOUD."""
    if mod == "h":
        if reg not in _HIGH8:
            _loud(at, "'%h' (high byte) exists only for the legacy regs "
                      "(ah/ch/dh/bh); '%{}' has none -- S3.5 LOUD".format(
                          reg), "%h")
        return _HIGH8[reg]
    if mod in ("b", "k"):
        width = 1
    elif mod == "w":
        width = 2
    elif mod == "q":
        width = 8
    names = _NAMES.get(reg)
    if names is None or width not in _WIDX:
        _loud(at, "no S3.5 register name for '%{}' at width {}".format(
            reg, width), "%" + reg)
    return names[_WIDX[width]]


# ------------------------------------------------------------- grammar --
class AsmParseMixin:
    """Parser mixin: asm statements + the L10 `register … asm("…")`
    declarator suffix (S17 parse posture)."""

    def parse_asm_statement(self) -> ast.Node:
        t = self.s.next()                        # asm / __asm__ keyword
        self._accept("__inline", "__inline__", "inline")
        vol = self._accept("volatile", "__volatile__") is not None
        goto = self._accept("goto") is not None
        self.s.expect_punct("(")
        tmpl = self._asm_lit_run(t, "template")
        outs: List[ast.Node] = []
        ins: List[ast.Node] = []
        clo: List[str] = []
        labels: List[str] = []
        if self.s.accept_punct(":"):
            if not self.s.at_punct(":"):
                outs = self._asm_operand_list()
            if self.s.accept_punct(":"):
                if not self.s.at_punct(":"):
                    ins = self._asm_operand_list()
                if self.s.accept_punct(":"):
                    if not self.s.at_punct(":"):
                        clo = self._asm_clobber_list(t)
                    if self.s.accept_punct(":"):
                        if not self.s.at_punct(")"):
                            labels = self._asm_label_list()
        self.s.expect_punct(")")
        self.s.expect_punct(";")
        return ast.AsmStmt(t.file, t.line, t.col, vol, goto, tmpl,
                           tuple(outs), tuple(ins), tuple(clo),
                           tuple(labels))

    # -- helpers --------------------------------------------------------
    def _asm_parse_err(self, tok, message):
        # grammar walls INSIDE an asm statement carry the `asm:` phase —
        # the §8 sweep law: an asm-class wall must be countable as such.
        raise DiagError("asm", tok.file, tok.line, tok.col, message,
                        tok.text)

    def _asm_lit_run(self, at, what: str) -> str:
        """ONE merged literal: juxtaposed StrLit tokens concat (M1 zero-gap
        + M2 §6g same-line-gap/cross-line law). Anything else = L5 LOUD."""
        tok = self.s.peek()
        if tok.kind != "str":
            self._asm_parse_err(
                tok, "asm {} must be a single string literal — a COMPUTED "
                "template is L5 LOUD (S13 grammar note)".format(what))
        parts = []
        while self.s.peek().kind == "str":
            parts.append(self.s.next().value)   # Token.value is the DECODED
        return "".join(parts)                   # literal (lexer law)

    def _asm_operand_list(self) -> List[ast.Node]:
        out = []
        while True:
            out.append(self._asm_operand())
            if not self.s.accept_punct(","):
                return out

    def _asm_operand(self) -> ast.Node:
        pos = self.s.peek()
        name = None
        if self.s.at_punct("["):                 # [name] operand name
            self.s.next()
            name = self.s.expect_id().text
            self.s.expect_punct("]")
        cstr = self._asm_lit_run(pos, "constraint")
        self.s.expect_punct("(")
        expr = self.expr.parse_expression()
        self.s.expect_punct(")")
        folded = None
        try:
            folded = self.fold_truthy(expr)      # parse-time const (§3.2
        except DiagError:                        # imm classes use it)
            folded = None
        return ast.AsmOperand(pos.file, pos.line, pos.col, name, cstr,
                              expr, folded)

    def _asm_clobber_list(self, at) -> List[str]:
        out = []
        while True:
            tok = self.s.peek()
            if tok.kind == "str":
                out.append(self._asm_lit_run(tok, "clobber name"))
                if self.s.at_punct("("):         # clobber section carries
                    self._asm_parse_err(               # an OPERAND (paravirt
                        self.s.peek(),              # _PARAVIRT_TYPE shape):
                        "clobber-section entry is an OPERAND (the paravirt "
                        "ASM_CALL_CONSTRAINT-in-clobbers shape) — §8 loud, "
                        "the SUPPORT posture never models it (§1.3)")
            elif tok.kind == "id" or tok.kind == "punct" and tok.text == "[":
                self._asm_parse_err(
                    tok, "clobber-section entry must be a quoted string; a "
                    "bare [op]/operand spelling is §8 loud (§3 L0)")
            else:
                self._asm_parse_err(tok, "malformed clobber section (§3 L0)")
            if not self.s.accept_punct(","):
                return out

    def _asm_label_list(self) -> List[str]:
        out = []
        while True:
            out.append(self.s.expect_id().text)
            if not self.s.accept_punct(","):
                return out

    def asm_bind_suffix(self, at) -> Optional[str]:
        """L10 parse posture: accept `asm("binding")` on a var declarator.
        The CALLER enforces the `register`-specifier law and the L4
        non-register alias wall (parser.py). Returns the raw binding text."""
        self.s.next()                            # the asm keyword
        self.s.expect_punct("(")
        raw = self._asm_lit_run(at, "register-bind")
        self.s.expect_punct(")")
        return raw
