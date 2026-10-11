"""依副檔名分派的宣告掃描器（文字比對，非 AST）。

每個語言一個模組（`swift`／`javascript`／`python`／`cpp`），共用 `common` 的工具；
新增語言時只加一個模組並在 ``_SCANNERS`` 註冊即可。
"""

from . import cpp, javascript, python, swift
from .common import link

_SCANNERS = {
    ".swift": swift.scan,
    ".js": javascript.scan, ".mjs": javascript.scan, ".cjs": javascript.scan,
    ".ts": javascript.scan, ".jsx": javascript.scan, ".tsx": javascript.scan,
    ".py": python.scan,
    ".c": cpp.scan, ".cpp": cpp.scan, ".cc": cpp.scan, ".cxx": cpp.scan,
    ".h": cpp.scan, ".hpp": cpp.scan, ".hxx": cpp.scan, ".hh": cpp.scan, ".ino": cpp.scan,
}

# 被索引的原始碼副檔名（供 files() 過濾用）。
SUPPORTED_SUFFIXES = tuple(_SCANNERS)


def scan_symbols(text, repo, name):
    """依副檔名分派到對應語言的宣告掃描器；未支援的副檔名回空清單。"""
    from pathlib import Path

    scanner = _SCANNERS.get(Path(name).suffix.lower())
    return scanner(text, repo, name) if scanner else []
