"""Generate the blcc __has_attribute table by probing the pinned oracle.

blcc/pp_predefines.py carries the result as HAS_ATTRIBUTE (gcc 11.4 answers,
1 = supported). Canonical names drop leading/trailing '__'/'_' on both sides
(gcc's own normalization); the lookup in pp_expand applies the same. Re-run
with the exact oracle blcc targets:

    python3 scripts/gen_has_attribute_table.py > /tmp/table.py   # then paste

Kernel citation: include/linux/compiler_attributes.h guards every attribute
probe with `#ifndef __has_attribute`, so the answers decide ~9 lines of the
M1 kernel tier (plan R16). Stdlib-only.
"""
import re
import subprocess
import sys

# Canonical names (underscores stripped). Set = EVERY name queried anywhere
# in the v5.10 tree (harvest: grep -rhoE '__has_attribute[[:space:]]*\([[:space:]]*
# [A-Za-z_][A-Za-z0-9_]*' over *.h/*.c/*.S, then canonicalized — 16 names:
# assume_aligned copy designated_init error externally_visible fallthrough
# no_caller_saved_registers noclone noipa nonstring no_sanitize_coverage
# no_sanitize_thread no_sanitize_undefined uninitialized warning x)
# UNION gcc 11.4's common/x86 attribute set (GCC docs "Common Attributes"
# + the attributes linux/compiler_attributes.h / compiler-gcc.h apply).
NAMES = [
    # v5.10 queries (every name the kernel ever feeds __has_attribute)
    "assume_aligned", "copy", "designated_init", "error",
    "externally_visible", "fallthrough", "no_caller_saved_registers",
    "noclone", "noipa", "nonstring", "no_sanitize_coverage",
    "no_sanitize_thread", "no_sanitize_undefined", "uninitialized",
    "warning", "x",
    # gcc common / x86 set + the v5.10 compiler_attributes.h vocabulary
    "alloc_size", "allocate", "always_inline", "app_linkage",
    "artificial", "attribute_const", "aligned", "alias", "cold",
    "constructor", "cleanup", "const", "deprecated", "designated_init",
    "disable_tail_calls", "dllimport", "dllexport", "flatten",
    "format", "format_arg", "gnu_inline", "hot", "ifunc", "leaf",
    "long_call", "malloc", "may_alias", "no_binds_local", "no_clone",
    "no_icf", "no_inline", "no_instrument_function", "no_sanitize",
    "no_stack_protector", "noinline", "nomerge", "nonnull", "noreturn",
    "notail", "omit_pipeline_dependency",
    "optimize", "packed", "patchable_function_entry", "profile", "pure",
    "returns_nonnull", "section", "sentinel", "short_call",
    "syntax_error", "tls_model", "unused", "used", "visibility",
    "warn_if_not_aligned", "warn_unused_result", "weak", "weakref",
    # names probed 0 by earlier cards, kept so the table stays complete
    "attribute_const", "fallback", "forced_inline", "printf",
    "warn_unresolved_offsets",
]


def probe(name):
    src = "#if __has_attribute(%s)\nYES\n#endif\n" % name
    out = subprocess.run(["gcc", "-std=gnu89", "-E", "-x", "c", "-"],
                         input=src, capture_output=True, text=True).stdout
    return "YES" in out


def main():
    rows = []
    for n in sorted(set(NAMES)):
        rows.append('    "%s": %d,' % (n, 1 if probe(n) else 0))
    ver = subprocess.run(["gcc", "--version"], capture_output=True,
                         text=True).stdout.splitlines()[0]
    sys.stdout.write("# Pinned from %s via scripts/gen_has_attribute_table.py\n"
                     % re.sub(r"\s*\(.*?\)", "", ver))
    sys.stdout.write("HAS_ATTRIBUTE = {\n" + "\n".join(rows) + "\n}\n")


if __name__ == "__main__":
    main()
