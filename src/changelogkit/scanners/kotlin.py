"""Kotlin 宣告掃描（文字比對，非 AST）。"""

import re

from .common import collect_block_comment, collect_signature, make_symbol

_VIS = (
    r"(?:(?:public|private|protected|internal|open|abstract|final|inline|suspend|operator|"
    r"infix|external|override|tailrec|const|lateinit|companion|expect|actual)\s+)*"
)
_MOD_CLASS = r"(?:(?:enum|data|sealed|value|annotation|inner|open|abstract|final)\s+)*"
_KIND_RE = re.compile(r"^\s*" + _VIS + _MOD_CLASS + r"(class|interface|object|typealias)\s+([A-Za-z_]\w*)")
_FUN_RE = re.compile(
    r"^\s*" + _VIS + r"(?:suspend\s+)?fun\s+(?:<[^>]+>\s*)?(?:[A-Za-z_][\w.<>?]*\.)?"
    r"([A-Za-z_]\w*)\s*[(<]"
)
_PROP_RE = re.compile(
    r"^\s*(?:public|private|protected|internal|const|lateinit)\s+(?:val|var)\s+([A-Za-z_]\w*)"
)
_ENUM_RE = re.compile(r"^\s*" + _VIS + r"enum\s+class\s+([A-Za-z_]\w*)")
_KIND = {"class": "class", "interface": "interface", "object": "object", "typealias": "typealias"}


def scan(text, repo, name):
    """回傳符號清單（class／interface／object／fun／公開的 val/var…）。"""
    lines = text.splitlines()
    symbols, doc, index = [], [], 0
    while index < len(lines):
        stripped = lines[index].strip()
        if stripped.startswith("/**"):
            doc, index = collect_block_comment(lines, index)
            continue
        if stripped.startswith("//"):
            doc.append(stripped.lstrip("/ ").strip())
            index += 1
            continue
        enum_match = _ENUM_RE.match(stripped)
        kind_match = _KIND_RE.match(stripped)
        fun_match = _FUN_RE.match(stripped)
        prop_match = _PROP_RE.match(stripped)
        if enum_match or kind_match or fun_match or prop_match:
            if enum_match:
                kind, symbol_name = "enum", enum_match.group(1)
            elif kind_match:
                kind, symbol_name = _KIND[kind_match.group(1)], kind_match.group(2)
            elif fun_match:
                kind, symbol_name = "func", fun_match.group(1)
            else:
                kind, symbol_name = "property", prop_match.group(1)
            signature, following = collect_signature(lines, index)
            body = signature.split("{", 1)[0].split("=", 1)[0].strip()
            symbols.append(make_symbol(kind, symbol_name, body, repo, name, index + 1, doc))
            doc = []
            index = following
            continue
        if stripped and not stripped.startswith(("@", "#")):
            doc = []
        index += 1
    return symbols
