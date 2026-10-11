"""JavaScript／TypeScript 宣告掃描（文字比對，非 AST）。

除一般原始碼外，也處理 TypeScript **型別宣告檔（``.d.ts``）**：``declare`` 開頭的宣告、
以及介面／宣告類別中**以 ``;`` 結尾的簽名成員**（method／property）。
"""

import re

from .common import collect_block_comment, collect_signature, make_symbol

# 前置修飾：export／declare／default／abstract／async 皆可選。
_FUNC_RE = re.compile(
    r"^(?:export\s+)?(?:declare\s+)?(?:default\s+)?(?:abstract\s+)?(?:async\s+)?"
    r"(function|class|interface|type|enum|namespace|module)\s+([A-Za-z_$][\w$]*)")
# 只有 export 或 declare 開頭才算模組層級常數（避免把函式內的區域變數當 API）。
_VAR_RE = re.compile(r"^(?:export\s+|declare\s+)+(?:const|let|var)\s+([A-Za-z_$][\w$]*)")
# 類別成員方法：`name(args) {`（可帶 static／async／get／set／* 修飾），排除控制關鍵字。
_MEMBER_RE = re.compile(
    r"^(?:static\s+|async\s+|get\s+|set\s+|\*\s*)*([A-Za-z_$][\w$]*)\s*\([^;{}]*\)\s*\{")
# 型別宣告檔中的簽名成員（以 `;` 結尾、無實作）。
_SIG_METHOD_RE = re.compile(
    r"^(?:static\s+|async\s+|get\s+|set\s+|\*\s*|readonly\s+)*([A-Za-z_$][\w$]*)\s*\([^;{}]*\)\s*(?::\s*[^;={]+)?;")
_SIG_PROP_RE = re.compile(r"^(?:static\s+|readonly\s+)*([A-Za-z_$][\w$]*)\s*\??\s*:\s*[^;={]+;")
_MEMBER_SKIP = {"if", "for", "while", "switch", "catch", "do", "else", "return",
                "function", "typeof", "new", "await", "yield", "super", "with", "try"}
_KIND = {"function": "func", "class": "class", "interface": "interface",
         "type": "typealias", "enum": "enum", "namespace": "namespace", "module": "namespace"}


def scan(text, repo, name):
    """回傳符號清單（function／class／interface／type／enum／namespace、export 的 const、
    類別成員方法，以及 ``.d.ts`` 的 ``declare`` 宣告與 ``;`` 簽名成員）。
    成員之後由 index 依縮排收進所屬型別。"""
    is_decl = name.endswith(".d.ts")
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
        sig = sig_kind = None
        if is_decl and not (match or var or member):
            sig = _SIG_METHOD_RE.match(stripped)
            sig_kind = "func"
            if not sig:
                sig = _SIG_PROP_RE.match(stripped)
                sig_kind = "property"
            if sig and sig.group(1) in _MEMBER_SKIP:
                sig = sig_kind = None
        if match or var or member or sig:
            if match:
                keyword, symbol_name = match.group(1), match.group(2)
                kind = _KIND.get(keyword, "property")
            elif var:
                kind, symbol_name = "property", var.group(1)
            elif member:
                kind, symbol_name = "func", member.group(1)
            else:
                kind, symbol_name = sig_kind, sig.group(1)
            signature, following = collect_signature(lines, index)
            body = signature.split("{", 1)[0].strip()
            if kind == "property" and "=" in body:
                body = body.split("=", 1)[0].strip()
            symbols.append(make_symbol(kind, symbol_name, body, repo, name, index + 1, doc))
            doc = []
            index = following
            continue
        if stripped and not stripped.startswith(("@", "#")):
            doc = []
        index += 1
    return symbols
