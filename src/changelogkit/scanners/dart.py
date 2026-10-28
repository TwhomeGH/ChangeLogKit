"""Dart 宣告掃描（文字比對，非 AST）。"""

import re

from .common import collect_block_comment, collect_signature, make_symbol

_MOD = r"(?:(?:abstract|base|interface|final|sealed|mixin|external)\s+)*"
_KIND_RE = re.compile(r"^\s*" + _MOD + r"(class|mixin|enum|extension|typedef)\s+([A-Za-z_]\w*)")
_FUN_RE = re.compile(
    r"^\s*(?!(?:if|for|while|switch|return|else|do|case)\b)"
    r"(?:[\w<>,\[\]?.]+\s+)?"
    r"([A-Za-z_]\w*)\s*\([^;{}]*\)\s*(?:async\*?|sync\*?)?\s*(?:\{|=>)"
)
_KIND = {"class": "class", "mixin": "mixin", "enum": "enum", "extension": "extension", "typedef": "typealias"}


def scan(text, repo, name):
    """回傳符號清單（class／mixin／enum／extension／typedef 與函式定義）。"""
    lines = text.splitlines()
    symbols, doc, index = [], [], 0
    while index < len(lines):
        stripped = lines[index].strip()
        if stripped.startswith("/**"):
            doc, index = collect_block_comment(lines, index)
            continue
        if stripped.startswith("///") or stripped.startswith("//"):
            doc.append(stripped.lstrip("/! ").strip())
            index += 1
            continue
        kind_match = _KIND_RE.match(stripped)
        fun_match = None if kind_match else _FUN_RE.match(stripped)
        if kind_match:
            symbols.append(
                make_symbol(
                    _KIND[kind_match.group(1)], kind_match.group(2), stripped, repo, name, index + 1, doc
                )
            )
            doc = []
            index += 1
            continue
        if fun_match:
            signature, following = collect_signature(lines, index)
            body = signature.split("{", 1)[0].split("=>", 1)[0].strip()
            symbols.append(make_symbol("func", fun_match.group(1), body, repo, name, index + 1, doc))
            doc = []
            index = following
            continue
        if stripped and not stripped.startswith(("@", "#")):
            doc = []
        index += 1
    return symbols
