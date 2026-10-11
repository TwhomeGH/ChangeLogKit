"""JavaScript／TypeScript 宣告掃描（文字比對，非 AST）。"""

import re

from .common import collect_block_comment, collect_signature, make_symbol

# export／default／abstract／async 皆可選。
_FUNC_RE = re.compile(
    r"^(?:export\s+)?(?:default\s+)?(?:abstract\s+)?(?:async\s+)?"
    r"(function|class|interface|type|enum|namespace)\s+([A-Za-z_$][\w$]*)")
_VAR_RE = re.compile(r"^export\s+(?:const|let|var)\s+([A-Za-z_$][\w$]*)")
_KIND = {"function": "func", "class": "class", "interface": "interface",
         "type": "typealias", "enum": "enum", "namespace": "namespace"}


def scan(text, repo, name):
    """回傳符號清單（`function`／`class`／`interface`／`type`／`enum`／`namespace` 與 export 的 const 等）。"""
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
        match = _FUNC_RE.match(stripped)
        var = _VAR_RE.match(stripped) if not match else None
        if match or var:
            keyword = match.group(1) if match else "var"
            symbol_name = match.group(2) if match else var.group(1)
            signature, following = collect_signature(lines, index)
            body = signature.split("{", 1)[0].strip()
            if not match:
                body = body.split("=", 1)[0].strip()
            symbols.append(make_symbol(_KIND.get(keyword, "property"), symbol_name, body,
                                       repo, name, index + 1, doc))
            doc = []
            index = following
            continue
        if stripped and not stripped.startswith(("@", "#")):
            doc = []
        index += 1
    return symbols
