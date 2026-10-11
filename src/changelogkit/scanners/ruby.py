"""Ruby 宣告掃描（文字比對，非 AST）。"""

import re

from .common import make_symbol

_CLASS_RE = re.compile(r"^\s*(class|module)\s+([A-Z]\w*(?:::[A-Z]\w*)*)")
_DEF_RE = re.compile(r"^\s*def\s+(?:self\.)?([A-Za-z_]\w*[!?=]?)")
_CONST_RE = re.compile(r"^\s*([A-Z][A-Z0-9_]{1,})\s*=")


def scan(text, repo, name):
    """回傳符號清單（class／module／def／常數），取相鄰 ``#`` 註釋。"""
    lines = text.splitlines()
    symbols, doc, index = [], [], 0
    while index < len(lines):
        stripped = lines[index].strip()
        if stripped.startswith("#") and not stripped.startswith("#!"):
            doc.append(stripped.lstrip("#").strip())
            index += 1
            continue
        class_match = _CLASS_RE.match(stripped)
        def_match = _DEF_RE.match(stripped)
        const_match = _CONST_RE.match(stripped)
        if class_match:
            kind = "module" if class_match.group(1) == "module" else "class"
            symbols.append(make_symbol(kind, class_match.group(2), stripped,
                                       repo, name, index + 1, doc))
            doc = []
            index += 1
            continue
        if def_match:
            symbols.append(make_symbol("func", def_match.group(1), stripped,
                                       repo, name, index + 1, doc))
            doc = []
            index += 1
            continue
        if const_match:
            symbols.append(make_symbol("property", const_match.group(1), stripped,
                                       repo, name, index + 1, doc))
            doc = []
            index += 1
            continue
        if stripped:
            doc = []
        index += 1
    return symbols
