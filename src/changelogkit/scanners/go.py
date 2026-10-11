"""Go 宣告掃描（文字比對，非 AST）。"""

import re

from .common import collect_block_comment, collect_signature, make_symbol

_FUNC_RE = re.compile(r"^func\s+(?:\([^)]*\)\s*)?([A-Za-z_]\w*)\s*[([]")
_TYPE_RE = re.compile(r"^type\s+([A-Za-z_]\w*)\s+(struct|interface|func|map|chan|\[|[*A-Za-z_]|\()")
_VAR_RE = re.compile(r"^(?:var|const)\s+([A-Za-z_]\w*)\s")


def _type_kind(keyword):
    return {"struct": "struct", "interface": "interface"}.get(keyword, "type")


def scan(text, repo, name):
    """回傳符號清單（func／method、type、var／const）。"""
    lines = text.splitlines()
    symbols, doc, index = [], [], 0
    while index < len(lines):
        stripped = lines[index].strip()
        if stripped.startswith("/*"):
            doc, index = collect_block_comment(lines, index)
            continue
        if stripped.startswith("//"):
            doc.append(stripped.lstrip("/ ").strip())
            index += 1
            continue
        func_match = _FUNC_RE.match(stripped)
        type_match = _TYPE_RE.match(stripped)
        var_match = _VAR_RE.match(stripped)
        if func_match:
            signature, following = collect_signature(lines, index)
            body = signature.split("{", 1)[0].strip()
            symbols.append(make_symbol("func", func_match.group(1), body,
                                       repo, name, index + 1, doc))
            doc = []
            index = following
            continue
        if type_match:
            symbols.append(make_symbol(_type_kind(type_match.group(2)), type_match.group(1),
                                       stripped, repo, name, index + 1, doc))
            doc = []
            index += 1
            continue
        if var_match:
            symbols.append(make_symbol("property", var_match.group(1), stripped,
                                       repo, name, index + 1, doc))
            doc = []
            index += 1
            continue
        if stripped and not stripped.startswith(("@", "#")):
            doc = []
        index += 1
    return symbols
