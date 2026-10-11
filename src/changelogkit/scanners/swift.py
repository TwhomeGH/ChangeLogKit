"""Swift 宣告掃描：相鄰 ``///`` 文件註釋與宣告（文字比對，非 AST）。"""

import re

from .common import collect_signature, make_symbol

_ACCESS = r"(?:public|private|internal|fileprivate|open)"
_MODIFIERS = (r"(?:public|private|internal|fileprivate|open|final|static|class|"
              r"nonisolated|override|mutating|convenience|required|dynamic|lazy|weak|unowned|indirect)")

# 函式／型別／擴充等一定會收錄。
_DECL_RE = re.compile(
    r"^\s*(?:" + _MODIFIERS + r"\s+)*(?:" + _ACCESS + r"\s+)?"
    r"(func|struct|class|enum|protocol|actor|extension|typealias|init|subscript)\b")
# 屬性只在本行具存取修飾詞時收錄，避免把函式內的區域 var/let 當成 API。
_PROP_RE = re.compile(
    r"^\s*(?:" + _MODIFIERS + r"\s+)*" + _ACCESS + r"\s*"
    r"(?:\([^)]*\)\s*)?"  # 例如 private(set)
    r"(var|let)\b")
_NAME_RE = re.compile(
    r"\b(?:func|struct|class|enum|protocol|actor|extension|typealias|var|let)\s+"
    r"([A-Za-z_][A-Za-z0-9_.]*)")
_KIND = {
    "func": "func", "struct": "struct", "class": "class", "enum": "enum",
    "protocol": "protocol", "actor": "actor", "extension": "extension",
    "typealias": "typealias", "init": "init", "subscript": "subscript",
    "var": "property", "let": "property",
}


def _decl_keyword(line):
    """行首是否為宣告；回傳關鍵字（func／struct／var…）或 None。"""
    match = _DECL_RE.match(line) or _PROP_RE.match(line)
    return match.group(1) if match else None


def _symbol_name(keyword, signature):
    """從簽名取出可讀名稱（init／subscript 直接回關鍵字）。"""
    if keyword in ("init", "subscript"):
        return keyword
    match = _NAME_RE.search(signature)
    return match.group(1) if match else ""


def scan(text, repo, name):
    """掃描相鄰 ``///`` 註釋與宣告，回傳符號清單。

    註釋與宣告之間允許屬性（@…）與條件編譯（#…）行；其餘非空行視為中斷註釋。
    """
    lines = text.splitlines()
    symbols, doc, index = [], [], 0
    while index < len(lines):
        stripped = lines[index].strip()
        if stripped.startswith("///"):
            doc.append(stripped[3:].strip())
            index += 1
            continue
        keyword = _decl_keyword(stripped)
        if keyword:
            signature, following = collect_signature(lines, index)
            body = signature.split("{", 1)[0].strip()
            if keyword in ("var", "let", "typealias"):
                body = body.split("=", 1)[0].strip()
            symbols.append(make_symbol(_KIND[keyword], _symbol_name(keyword, body) or body,
                                       body, repo, name, index + 1, doc))
            doc = []
            index = following
            continue
        if stripped and not stripped.startswith(("@", "#", "//")):
            doc = []
        index += 1
    return symbols
