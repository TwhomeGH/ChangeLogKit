"""C／C++ 宣告掃描（文字比對，非 AST，啟發式）。

收錄 `class`／`struct`／`union`／`enum`／`namespace`，以及函式**定義**（行尾 ``{``）
與**宣告**（行尾 ``;``，且具回傳型別前綴）；以關鍵字排除 `if`／`for`／`while` 等控制行，
並以「呼叫陳述句通常沒有型別前綴、也不以 ``{`` 結尾」降低誤判。
"""

import re

from .common import collect_block_comment, make_symbol

_TYPE_RE = re.compile(
    r"^\s*(?:typedef\s+)?(class|struct|union|enum|namespace)\s+(?:class\s+)?([A-Za-z_]\w*)")
_KIND = {"class": "class", "struct": "struct", "union": "union",
         "enum": "enum", "namespace": "namespace"}
_STOP = (r"(?!(?:if|for|while|switch|return|catch|else|do|case|sizeof|new|delete|"
         r"typedef|using|#)\b)")
_FUNC_DEF_RE = re.compile(
    r"^\s*" + _STOP +
    r"(?:[A-Za-z_][\w:<>,.*&\s]*?\s)?"                     # 可選的回傳型別
    r"([A-Za-z_]\w*(?:::[A-Za-z_]\w*)*)\s*\([^;{}]*\)\s*"  # 名稱（可含 ::）
    r"(?:const\s*)?(?:noexcept\s*)?(?:override\s*)?(?:->[^{;]*)?\{")
_FUNC_DECL_RE = re.compile(
    r"^\s*" + _STOP +
    r"[A-Za-z_][\w:<>,.*&\s]*?\s"                          # 必要：回傳型別
    r"([A-Za-z_]\w*(?:::[A-Za-z_]\w*)*)\s*\([^;{}]*\)\s*"
    r"(?:const\s*)?(?:noexcept\s*)?(?:override\s*)?;")


def scan(text, repo, name):
    """回傳符號清單（型別與函式定義／宣告）。"""
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
        type_match = _TYPE_RE.match(stripped)
        func_match = None if type_match else (
            _FUNC_DEF_RE.match(stripped) or _FUNC_DECL_RE.match(stripped))
        if type_match:
            symbols.append(make_symbol(_KIND[type_match.group(1)], type_match.group(2),
                                       stripped, repo, name, index + 1, doc))
            doc = []
            index += 1
            continue
        if func_match:
            symbols.append(make_symbol("func", func_match.group(1), stripped,
                                       repo, name, index + 1, doc))
            doc = []
            index += 1
            continue
        if stripped and not stripped.startswith(("@", "#")):
            doc = []
        index += 1
    return symbols
