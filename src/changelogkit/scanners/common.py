"""跨語言共用的掃描工具：行號連結、簽名收集、符號項目、區塊註釋清理。"""

import re
from urllib.parse import urlencode


def link(repo, path, line=1):
    """檔案內某行的站內連結（以 hash 指向行號，不需重載）。"""
    return "/development/file?" + urlencode({"repo": repo, "path": path}) + "#L" + str(line)


def collect_signature(lines, start):
    """從 start 行往下收集到括號收合，回傳 (簽名, 下一行索引)，用於呈現多行簽名。"""
    parts = []
    depth = 0
    for index in range(start, min(start + 30, len(lines))):
        line = lines[index]
        parts.append(line.strip())
        depth += line.count("(") - line.count(")") + line.count("[") - line.count("]")
        if depth <= 0:
            return " ".join(part for part in parts if part), index + 1
    return " ".join(part for part in parts if part), min(start + 30, len(lines))


def make_symbol(kind, symbol_name, signature, repo, fname, line, doc):
    """組出一個符號項目（各語言掃描器共用）。"""
    return {
        "name": symbol_name or signature,
        "signature": signature,
        "kind": kind,
        "repo": repo,
        "file": fname,
        "line": line,
        "comment": "\n".join(doc).strip(),
        "url": link(repo, fname, line),
    }


def clean_block_doc(line):
    """清理 ``/** … */`` 區塊註釋的一行（去掉 ``/**``、``*/`` 與前後 ``*``）。"""
    text = re.sub(r"^\s*/\*\*?", "", line)
    text = re.sub(r"\*/?\s*$", "", text)
    return text.strip().lstrip("*").strip()


def collect_block_comment(lines, index):
    """從 index 起收集 ``/** … */`` 區塊，回傳 (doc 行清單, 下一個索引)。"""
    block = []
    while index < len(lines) and "*/" not in lines[index]:
        block.append(lines[index])
        index += 1
    if index < len(lines):
        block.append(lines[index])
        index += 1
    return [t for t in (clean_block_doc(b) for b in block) if t], index
