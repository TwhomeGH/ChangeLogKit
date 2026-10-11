"""JavaScript／TypeScript 宣告掃描（文字比對，非 AST）。"""

import re

from .common import collect_block_comment, collect_signature, make_symbol

# export／default／abstract／async 皆可選。
_FUNC_RE = re.compile(
    r"^(?:export\s+)?(?:default\s+)?(?:abstract\s+)?(?:async\s+)?"
    r"(function|class|interface|type|enum|namespace)\s+([A-Za-z_$][\w$]*)")
_VAR_RE = re.compile(r"^export\s+(?:const|let|var)\s+([A-Za-z_$][\w$]*)")
# 類別成員方法：`name(args) {`（可帶 static／async／get／set／* 修飾），排除控制關鍵字。
_MEMBER_RE = re.compile(
    r"^(?:static\s+|async\s+|get\s+|set\s+|\*\s*)*([A-Za-z_$][\w$]*)\s*\([^;{}]*\)\s*\{")
_MEMBER_SKIP = {"if", "for", "while", "switch", "catch", "do", "else", "return",
                "function", "typeof", "new", "await", "yield", "super", "with", "try"}
_KIND = {"function": "func", "class": "class", "interface": "interface",
         "type": "typealias", "enum": "enum", "namespace": "namespace"}


def scan(text, repo, name):
    """回傳符號清單（`function`／`class`／`interface`／`type`／`enum`／`namespace`、
    export 的 const，以及類別成員方法）。成員之後由 index 依縮排收進所屬類別。"""
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
        member = _MEMBER_RE.match(stripped) if not (match or var) else None
        if member and member.group(1) in _MEMBER_SKIP:
            member = None
        if match or var or member:
            if match:
                keyword, symbol_name = match.group(1), match.group(2)
            elif var:
                keyword, symbol_name = "var", var.group(1)
            else:
                keyword, symbol_name = "function", member.group(1)
            signature, following = collect_signature(lines, index)
            body = signature.split("{", 1)[0].strip()
            if keyword == "var":
                body = body.split("=", 1)[0].strip()
            symbols.append(make_symbol(_KIND.get(keyword, "func"), symbol_name, body,
                                       repo, name, index + 1, doc))
            doc = []
            index = following
            continue
        if stripped and not stripped.startswith(("@", "#")):
            doc = []
        index += 1
    return symbols
