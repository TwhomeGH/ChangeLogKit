"""Python 宣告掃描（文字比對，非 AST）。"""

import re

from .common import collect_signature, make_symbol

_DECL_RE = re.compile(r"^(?:async\s+)?(def|class)\s+([A-Za-z_]\w*)")
_KIND = {"def": "func", "class": "class"}


def scan(text, repo, name):
    """回傳符號清單（``def``／``async def``／``class``，相鄰 ``#`` 註釋當說明）。"""
    lines = text.splitlines()
    symbols, doc, index = [], [], 0
    while index < len(lines):
        stripped = lines[index].strip()
        if stripped.startswith("#") and not stripped.startswith("#!"):
            doc.append(stripped.lstrip("#").strip())
            index += 1
            continue
        match = _DECL_RE.match(stripped)
        if match:
            signature, following = collect_signature(lines, index)
            body = re.sub(r":\s*$", "", signature).strip()
            symbols.append(
                make_symbol(_KIND[match.group(1)], match.group(2), body, repo, name, index + 1, doc)
            )
            doc = []
            index = following
            continue
        if stripped and not stripped.startswith(("@", "#")):
            doc = []
        index += 1
    return symbols
