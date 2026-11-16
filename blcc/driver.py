"""CLI driver per ARCHITECTURE.md §2/§8.

Concerns: argv parsing (M1 surface: -D/-U/-I/-isystem/-nostdinc/-include/
-std/-E, plus the GA --emit-asm and -v), the pipeline order
preproc -> lexer -> parser -> codegen, the exact external commands
`as --64 -o <tmp>.o <file>.s` and `ld -static -o <output> <tmp>.o`, scratch
files under the repo .tmp/, and the exit-code contract 0/2/3. `-E` runs the
preprocessor only and writes the pp output to stdout (exit 0, no -o needed;
pp diagnostics still exit 2, the §8 warning tier never changes the code).
`-c` (M4 W0, plan v4 §3.5): `main` is a LINK-MODE requirement — `-c` runs
parse→sema(no-main)→asm→`as --64 -o <o-operand verbatim>` and stops: no `ld`,
no `_require_main`. No `-c`: the gate runs unchanged. Any diagnostic on the
`-c` path leaves NO file at `-o` (unlink partial; kbuild/fixdep read the
target's existence). `-c` without `-o`: REJECT-LOUD exit 2.
"""
from __future__ import annotations

import os
import subprocess
import sys
from typing import List, Optional

from blcc import ast
from blcc.codegen import compile_tu
from blcc.lexer import DiagError, Lexer
from blcc.parser import parse_tokens
from blcc.preproc import PpOpts, Preprocessor
from blcc.runtime import BUILTINS, RUNTIME_ASM

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TMP_DIR = os.path.join(ROOT, ".tmp")

USAGE = ("usage: python3 -m blcc <input.c> [-o <output>] [--emit-asm] [-v]\n"
         "       python3 -m blcc -E <input.c> [-D name[=tokens]] [-U name]\n"
         "       [-I dir] [-isystem dir] [-nostdinc] [-include file] [-std=X]")

# -std aliases gcc 11.4 accepts and whose -dM captures are BYTE-IDENTICAL
# to the spelled alias (measured c7: `diff` of -std=c90/-std=c89 and of
# -std=gnu90/-std=gnu89 full predefine captures: empty). Aliasing here
# keeps the generated capture table the single source of truth.
_STD_ALIAS = {"c90": "c89", "gnu90": "gnu89"}


def _std_value(std: str) -> str:
    """Validate/alias one -std operand (shared by the split and attached
    spellings — ONE mechanism for both shapes)."""
    std = _STD_ALIAS.get(std, std)
    from blcc.pp_predefines import STDC_VERSIONS
    if std not in STDC_VERSIONS:
        raise SystemExit("blcc: unsupported -std '%s'\n%s" % (std, USAGE))
    return std


def _parse_args(argv: List[str]):
    in_path: Optional[str] = None
    out_path: Optional[str] = None
    emit_asm = False
    verbose = False
    pp_only = False
    compile_only = False
    opts = PpOpts()
    i = 0
    while i < len(argv):
        a = argv[i]
        if a == "-o":
            i += 1
            if i >= len(argv) or argv[i].startswith("-"):
                raise SystemExit("blcc: -o needs an output path\n" + USAGE)
            out_path = argv[i]
        elif a == "--emit-asm":
            emit_asm = True
        elif a == "-v":
            verbose = True
        elif a == "-E":
            pp_only = True
        elif a == "-c":                  # M4 W0 (§3.5): compile to the -o
            compile_only = True          # object and STOP — no ld, no gate
        elif a == "-nostdinc":
            pass                             # blcc HAS no default system dirs
        elif a in ("-I", "-isystem", "-include", "-std"):
            i += 1
            if i >= len(argv):
                raise SystemExit("blcc: %s needs an argument\n" % a + USAGE)
            if a == "-I":
                opts.includes_dir.append(argv[i])
            elif a == "-isystem":
                opts.isystem.append(argv[i])
            elif a == "-include":
                opts.preinclude.append(argv[i])
            else:
                opts.std = _std_value(argv[i])
        elif a.startswith("-I"):
            opts.includes_dir.append(a[2:])
        elif a.startswith("-isystem"):        # BOTH shapes measured rc 0
            opts.isystem.append(a[8:])        # at gcc 11.4 (c7 B05/B06)
        elif a.startswith("-include"):        # ditto (c7 B07/B08; -include
            opts.preinclude.append(a[8:])     # is the kernel's split form)
        elif a.startswith("-std="):
            opts.std = _std_value(a[5:])
        elif a.startswith("-D") or a.startswith("-U"):
            arg = a[2:]
            if not arg:
                i += 1
                if i >= len(argv):
                    raise SystemExit("blcc: %s needs an argument\n"
                                     % a[1] + USAGE)
                arg = argv[i]
            # NO argv-layer name check (F-c5-B, MC 12458): the operand
            # rides the SAME preproc readers as the in-source directives
            # (preproc._apply_cli); an invalid name is a §8 pp diagnostic
            # there, rc 2. (gcc is Joined-Separate: -D/-U consume the
            # NEXT token as the operand even when it starts with '-'.)
            opts.du.append((a[1], arg, None))
        elif a.startswith("-"):
            raise SystemExit("blcc: unknown flag '{}'\n{}".format(a, USAGE))
        elif in_path is None:
            in_path = a
        else:
            # LOUD naming the token, like gcc's trailing-operand posture
            # (`gcc: error: BAR: linker input file not found`): the
            # operand class must never silently swallow a stray file.
            raise SystemExit("blcc: more than one input file '%s'\n"
                             % a + USAGE)
        i += 1
    if in_path is None:
        raise SystemExit("blcc: need an input file\n" + USAGE)
    if compile_only and not pp_only and out_path is None:
        # §3.5 law: kbuild always carries -o (741/741); gcc's implicit
        # <stem>.o-in-cwd posture is deliberately NOT copied — LOUD.
        raise SystemExit("blcc: -c needs -o <output>\n" + USAGE)
    if not pp_only and out_path is None:
        raise SystemExit("blcc: need an input file and -o <output>\n" + USAGE)
    return (in_path, out_path, emit_asm, verbose, compile_only), pp_only, opts


def _require_main(tu: ast.TranslationUnit, eof, in_path: str) -> None:
    # LINK-MODE law (§3.5): called on the link path only — `-c` never
    # reaches this gate (kernel TUs have no main by nature).
    for d in tu.decls:
        if isinstance(d, ast.FuncDecl) and d.name == "main" and d.body is not None:
            return
    raise DiagError("sema", in_path, eof.line, eof.col,
                    "no 'main' function defined (§8)", "<eof>")


def _run_tool(cmd: List[str]) -> Optional[int]:
    try:
        proc = subprocess.run(cmd, capture_output=True)
    except OSError as exc:
        sys.stderr.write("blcc: cannot run '{}': {}\n".format(cmd[0], exc))
        return 3
    if proc.stdout:
        sys.stderr.buffer.write(proc.stdout)
        sys.stderr.buffer.flush()
    if proc.returncode != 0:
        sys.stderr.buffer.write(proc.stderr)
        sys.stderr.buffer.flush()
        return 3
    return None


def main(argv: List[str]) -> int:
    try:
        (in_path, out_path, emit_asm, verbose, compile_only), pp_only, opts = \
            _parse_args(argv)
    except SystemExit as exc:            # usage errors are §2 exit 2
        sys.stderr.write(str(exc) + "\n")
        return 2

    # §3.5 failure law (compile paths): any diagnostic leaves NO file at
    # -o — kbuild/fixdep read the target's existence, a surviving object
    # after a failed compile is a false green. (-E mode never unlinks: it
    # answers the pp-stream posture, where the oracle never deletes.)
    def _fail(code: int) -> int:
        if compile_only and not pp_only:
            try:
                os.remove(out_path)
            except OSError:
                pass
        return code

    opts.emit_pragmas = pp_only          # -E passes pragmas through (oracle);
    # compile mode keeps pp output comment- AND pragma-free for the lexer.
    pp = Preprocessor(opts, warn_out=lambda s: sys.stderr.write(s))
    try:
        lines = pp.preprocess_file(in_path)
    except DiagError as exc:
        sys.stderr.write(str(exc) + "\n")
        return _fail(2)
    except Exception as exc:            # §8 belt also guards the -E path
        sys.stderr.write("{}:0:0: pp: internal compiler error, found "
                         "'{}: {}'\n".format(in_path, type(exc).__name__,
                                             str(exc).replace("'", "")))
        return _fail(2)

    if pp_only:
        # gcc -E -o FILE sends the pp stream to FILE (measured c7 — the
        # kernel build line always carries -o); with no -o the stream
        # answers to stdout.
        if out_path:
            try:
                out = open(out_path, "w", encoding="utf-8")
            except OSError as exc:
                raise SystemExit("blcc: cannot open '%s': %s"
                                 % (out_path, exc.strerror))
        else:
            out = sys.stdout
        try:
            for sl in lines:
                out.write(sl.text + "\n")
        finally:
            if out_path:
                out.close()
        return 0

    try:
        toks = Lexer(lines).tokenize()
        tu = parse_tokens(toks)
        if not compile_only:
            # M4 W3 COMMIT-0 (MC 12563): the DEF arm of the re-declaration
            # law — `-c` accepts a user definition of a §6 builtin (the
            # blob is absent; nm answers `T strlen` == the gcc twin,
            # lib/string.c shape). LINK mode is different law: the
            # RUNTIME_ASM blob OWNS the builtin names, so a user body
            # there is a collision the §8 contract must answer as a
            # diagnostic BEFORE any tool runs (gcc rc0 links its libc —
            # LOUD-DIV row; kernel universe is -c-only, volume 0). This
            # replaces the old blanket parse-time wall for this shape.
            for d in tu.decls:
                if (isinstance(d, ast.FuncDecl) and d.body is not None
                        and d.name in BUILTINS):
                    raise DiagError("sema", d.file, d.line, d.col,
                                    "cannot define the §6 builtin '{}' in "
                                    "LINK mode — the runtime blob owns it "
                                    "(-c accepts the definition; §6)",
                                    d.name)
            _require_main(tu, toks[-1], in_path)
        # The RUNTIME_ASM blob is LINK-mode furniture: it defines `_start`
        # and references `U main` (M1 static-exe law). A relocatable `-c`
        # object must carry the TU and NOTHING else — the blob in a .o is
        # `U main` poison ×669 TUs and a _start redefinition wall at any
        # link (§6 nm-parity: blcc_U(TU) − gcc_U(TU) must stay ∅).
        asm_text = compile_tu(tu) if compile_only \
            else RUNTIME_ASM + compile_tu(tu)
    except DiagError as exc:
        sys.stderr.write(str(exc) + "\n")
        return _fail(2)
    except Exception as exc:            # §2/§8 belt: a raw traceback is NEVER
        # a permitted compiler behaviour — every internal fault becomes a
        # §8-format diagnostic, exit 2, and NOTHING is emitted.
        sys.stderr.write("{}:0:0: asm: internal compiler error, found "
                         "'{}: {}'\n".format(in_path, type(exc).__name__,
                                             str(exc).replace("'", "")))
        return _fail(2)

    os.makedirs(TMP_DIR, exist_ok=True)
    stem = os.path.basename(out_path) or "out"
    scratch_s = os.path.join(TMP_DIR, "{}.{}.s".format(stem, os.getpid()))
    scratch_o = scratch_s[:-1] + "o"

    if emit_asm:
        sys.stdout.write(asm_text)
        with open(out_path + ".s", "w", encoding="utf-8") as fh:
            fh.write(asm_text)
    with open(scratch_s, "w", encoding="utf-8") as fh:
        fh.write(asm_text)

    if compile_only:
        # §3.5 mode law: parse→sema(no-main)→asm→as -o <operand VERBATIM>
        # → STOP. No ld, no scratch object — the object answers to the
        # exact `-o` string kbuild spelled.
        as_cmd = ["as", "--64", "-o", out_path, scratch_s]
        if verbose:
            sys.stdout.write(" ".join(as_cmd) + "\n")
            sys.stdout.flush()
        code = _run_tool(as_cmd)
        if code is not None:
            return _fail(code)         # as left a partial: leave NOTHING
        os.remove(scratch_s)
        return 0

    as_cmd = ["as", "--64", "-o", scratch_o, scratch_s]
    ld_cmd = ["ld", "-static", "-o", out_path, scratch_o]
    for cmd in (as_cmd, ld_cmd):
        if verbose:
            sys.stdout.write(" ".join(cmd) + "\n")
            sys.stdout.flush()
        code = _run_tool(cmd)
        if code is not None:
            return code            # §8: scratch kept on failure, tool stderr shown

    os.remove(scratch_s)
    os.remove(scratch_o)
    return 0
