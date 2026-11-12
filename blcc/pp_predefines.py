"""Builtin macro table for the M1 preprocessor (plan R16/R17).

Concern: DATA only — the x86-64 gcc-11.4-pinned predefines, the per-attribute
__has_attribute table (pinned by scripts/gen_has_attribute_table.py against
the oracle), and the assembly order builtins -> argv -D/-U left-to-right (the
R17 rule lives in preproc). stdlib-only.

__KERNEL__ is NOT predefined (the kernel Makefile passes -D__KERNEL__);
__STDC_VERSION__ is NOT defined under c89/gnu89 (gcc 11.4 answer, overriding
the plan's "gnu89 -> 199409L" — see the M1 verdict, oracle rule).
"""
from __future__ import annotations

from typing import Dict, Optional

from blcc.pp_expand import Macro, tokenize

# Pinned from gcc 11.4.0 by scripts/gen_has_attribute_table.py — regenerate
# there if the oracle ever moves; 1 = __has_attribute(<name>) is true.
HAS_ATTRIBUTE = {
    "alloc_size": 1, "always_inline": 1, "assume_aligned": 1,
    "attribute_const": 0, "copy": 1, "deprecated": 1, "designated_init": 1,
    "fallthrough": 1, "flatten": 1, "forced_inline": 0, "format": 1,
    "gnu_inline": 1, "malloc": 1, "no_inline": 0, "no_sanitize_address": 1,
    "no_sanitize_undefined": 1, "no_stack_protector": 1, "noinline": 1,
    "nonnull": 1, "optimize": 1, "packed": 1, "printf": 0, "pure": 1,
    "section": 1, "sentinel": 1, "syntax_error": 0, "tls_model": 1,
    "unused": 1, "used": 1, "warn_unresolved_offsets": 0,
    "warn_unused_result": 1, "weak": 1, "aligned": 1, "cold": 1, "hot": 1,
    "visibility": 1, "alias": 1,
}

# -std value -> __STDC_VERSION__ body (None = macro NOT defined, gcc answer)
STDC_VERSIONS = {
    "c89": None, "gnu89": None, "iso9899:1990": None,
    "c94": "199409L", "gnu94": "199409L", "iso9899:199409": "199409L",
    "c99": "199901L", "gnu99": "199901L", "iso9899:1999": "199901L",
    "c11": "201112L", "gnu11": "201112L", "iso9899:2011": "201112L",
    "c17": "201710L", "gnu17": "201710L", "c2x": "201710L",
    "gnu2x": "201710L", "": "201710L",
}

# Oracle capture: gcc 11.4 `gcc -dM -E -x c /dev/null`, the rows that matter
# to the M1 kernel profile (x86-64, LP64, little-endian, GNU 11.4).
_PLAIN = [
    ("__STDC__", "1"), ("__STDC_HOSTED__", "1"),
    ("__STDC_UTF_16__", "1"), ("__STDC_UTF_32__", "1"),
    ("__GNUC__", "11"), ("__GNUC_MINOR__", "4"), ("__GNUC_PATCHLEVEL__", "0"),
    ("__SIZEOF_LONG__", "8"),
    ("__x86_64__", "1"), ("__x86_64", "1"), ("__LP64__", "1"),
    ("__BYTE_ORDER__", "__ORDER_LITTLE_ENDIAN__"),
    ("__ORDER_LITTLE_ENDIAN__", "1234"), ("__ORDER_BIG_ENDIAN__", "4321"),
]

# Stateful / expansion-time hooks: value supplied by pp_expand at the use
# site (R18/R19), not a stored body.
_HOOKED = {
    "__LINE__": "line", "__FILE__": "file", "__BASE_FILE__": "base",
    "__COUNTER__": "counter", "__DATE__": "date", "__TIME__": "time",
}


def builtins(std: str) -> Dict[str, Macro]:
    """The builtin macro table for one -std value (plan R16)."""
    m: Dict[str, Macro] = {}
    for name, body in _PLAIN:
        m[name] = Macro(name, tokenize(body), None, builtin=True)
    ver: Optional[str] = STDC_VERSIONS.get(std, STDC_VERSIONS["gnu17"])
    if ver is not None:
        m["__STDC_VERSION__"] = Macro("__STDC_VERSION__", tokenize(ver), None,
                                      builtin=True)
    for name, kind in _HOOKED.items():
        m[name] = Macro(name, [], None, kind=kind, builtin=True)
    m["__INT64_C"] = Macro("__INT64_C", tokenize("c ## L"), ["c"],
                           builtin=True)
    m["__UINT64_C"] = Macro("__UINT64_C", tokenize("c ## UL"), ["c"],
                            builtin=True)
    m["__has_attribute"] = Macro("__has_attribute", [], ["x"],
                                 kind="hasattr", builtin=True)
    m["_Pragma"] = Macro("_Pragma", [], ["x"], kind="pragma", builtin=True)
    return m
