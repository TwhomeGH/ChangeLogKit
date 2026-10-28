"""Rust 宣告掃描（文字比對，非 AST）。"""

import re

from .common import collect_block_comment, collect_signature, make_symbol

_PUB = r"(?:pub(?:\s*\([^)]*\))?\s+)?"
_FN_MODS = r"(?:(?:async|unsafe|const|extern(?:\s+\"[^\"]*\")?|default)\s+)*"
_FN_RE = re.compile(r"^\s*" + _PUB + _FN_MODS + r"fn\s+([A-Za-z_]\w*)")
_KIND_RE = re.compile(r"^\s*" + _PUB + r"(struct|enum|trait|mod|type|union)\s+([A-Za-z_]\w*)")
_IMPL_RE = re.compile(r"^\s*(?:unsafe\s+)?impl(?:<[^>]*>)?\s+([A-Za-z_]\w*)")
_CONST_RE = re.compile(r"^\s*" + _PUB + r"(?:const|static)\s+([A-Za-z_]\w*)")
_KIND = {
    "struct": "struct",
    "enum": "enum",
    "trait": "trait",
    "mod": "module",
    "type": "typealias",
    "union": "union",
}


def scan(text, repo, name):
    """回傳符號清單（fn／struct／enum／trait／mod／type／impl／const）。"""
    lines = text.splitlines()
    symbols, doc, index = [], [], 0
    while index < len(lines):
        stripped = lines[index].strip()
        if stripped.startswith("/**"):
            doc, index = collect_block_comment(lines, index)
            continue
        if stripped.startswith("///") or stripped.startswith("//!"):
            doc.append(stripped.lstrip("/! ").strip())
            index += 1
            continue
        if stripped.startswith("//"):
            doc.append(stripped.lstrip("/ ").strip())
            index += 1
            continue
        fn_match = _FN_RE.match(stripped)
        kind_match = _KIND_RE.match(stripped)
        impl_match = _IMPL_RE.match(stripped)
        const_match = _CONST_RE.match(stripped)
        if fn_match:
            signature, following = collect_signature(lines, index)
            body = signature.split("{", 1)[0].strip()
            symbols.append(make_symbol("func", fn_match.group(1), body, repo, name, index + 1, doc))
            doc = []
            index = following
            continue
        if kind_match:
            symbols.append(
                make_symbol(
                    _KIND[kind_match.group(1)], kind_match.group(2), stripped, repo, name, index + 1, doc
                )
            )
            doc = []
            index += 1
            continue
        if impl_match:
            symbols.append(make_symbol("impl", impl_match.group(1), stripped, repo, name, index + 1, doc))
            doc = []
            index += 1
            continue
        if const_match:
            symbols.append(
                make_symbol("property", const_match.group(1), stripped, repo, name, index + 1, doc)
            )
            doc = []
            index += 1
            continue
        if stripped and not stripped.startswith(("@", "#")):
            doc = []
        index += 1
    return symbols
