"""C# 宣告掃描（文字比對，非 AST）。"""

import re

from .common import collect_block_comment, collect_signature, make_symbol

_MOD = (r"(?:(?:public|private|protected|internal|static|partial|sealed|abstract|virtual|"
        r"override|async|readonly|new|extern|unsafe|ref|volatile)\s+)*")
_KIND_RE = re.compile(r"^\s*" + _MOD + r"(class|interface|struct|enum|record|namespace)\s+([A-Za-z_]\w*)")
_METHOD_RE = re.compile(
    r"^\s*" + _MOD + r"(?:<[^>]+>\s*)?[\w<>\[\],.?]+(?:\s*\[\])?\s+"
    r"([A-Za-z_]\w*)\s*\([^;{}]*\)\s*(?:where[^{]+)?\{")
_KIND = {"class": "class", "interface": "interface", "struct": "struct",
         "enum": "enum", "record": "record", "namespace": "namespace"}


def scan(text, repo, name):
    """回傳符號清單（class／interface／struct／enum／record／namespace 與方法定義）。"""
    lines = text.splitlines()
    symbols, doc, index = [], [], 0
    while index < len(lines):
        stripped = lines[index].strip()
        if stripped.startswith("/**"):
            doc, index = collect_block_comment(lines, index)
            continue
        if stripped.startswith("///") or stripped.startswith("//"):
            doc.append(stripped.lstrip("/ ").strip())
            index += 1
            continue
        kind_match = _KIND_RE.match(stripped)
        method_match = None if kind_match else _METHOD_RE.match(stripped)
        if kind_match:
            symbols.append(make_symbol(_KIND[kind_match.group(1)], kind_match.group(2),
                                       stripped, repo, name, index + 1, doc))
            doc = []
            index += 1
            continue
        if method_match:
            signature, following = collect_signature(lines, index)
            body = signature.split("{", 1)[0].strip()
            symbols.append(make_symbol("func", method_match.group(1), body,
                                       repo, name, index + 1, doc))
            doc = []
            index = following
            continue
        if stripped and not stripped.startswith(("@", "#")):
            doc = []
        index += 1
    return symbols
