"""依副檔名分派的宣告掃描器（文字比對，非 AST）。

每個語言一個模組，共用 `common` 的工具；新增語言時只加一個模組並在 ``_SCANNERS``
註冊即可。
"""

from . import cpp, csharp, dart, go, java, javascript, kotlin, python, ruby, rust, swift
from .common import link

_SCANNERS = {
    ".swift": swift.scan,
    ".js": javascript.scan, ".mjs": javascript.scan, ".cjs": javascript.scan,
    ".ts": javascript.scan, ".jsx": javascript.scan, ".tsx": javascript.scan,
    ".py": python.scan,
    ".c": cpp.scan, ".cpp": cpp.scan, ".cc": cpp.scan, ".cxx": cpp.scan,
    ".h": cpp.scan, ".hpp": cpp.scan, ".hxx": cpp.scan, ".hh": cpp.scan, ".ino": cpp.scan,
    ".kt": kotlin.scan, ".kts": kotlin.scan,
    ".java": java.scan,
    ".go": go.scan,
    ".rs": rust.scan,
    ".cs": csharp.scan,
    ".rb": ruby.scan,
    ".dart": dart.scan,
    ".swiftinterface": swift.scan,
}

# 副檔名 → 語言顯示名稱。
_SUFFIX_LANG = {
    ".swift": "Swift", ".swiftinterface": "Swift",
    ".js": "JavaScript/TypeScript", ".mjs": "JavaScript/TypeScript", ".cjs": "JavaScript/TypeScript",
    ".ts": "JavaScript/TypeScript", ".jsx": "JavaScript/TypeScript", ".tsx": "JavaScript/TypeScript",
    ".py": "Python",
    ".c": "C/C++", ".cpp": "C/C++", ".cc": "C/C++", ".cxx": "C/C++",
    ".h": "C/C++", ".hpp": "C/C++", ".hxx": "C/C++", ".hh": "C/C++", ".ino": "C/C++",
    ".kt": "Kotlin", ".kts": "Kotlin",
    ".java": "Java", ".go": "Go", ".rs": "Rust", ".cs": "C#",
    ".rb": "Ruby", ".dart": "Dart",
}

# 支援語言（顯示順序；前端「API 宣告」頁列出與篩選用）。
SUPPORTED_LANGUAGES = ["Swift", "JavaScript/TypeScript", "Python", "C/C++", "Kotlin",
                       "Java", "Go", "Rust", "C#", "Ruby", "Dart"]

# 被索引的原始碼副檔名（供 files() 過濾用）。
SUPPORTED_SUFFIXES = tuple(_SCANNERS)


def scan_symbols(text, repo, name):
    """依副檔名分派到對應語言的宣告掃描器；未支援的副檔名回空清單。"""
    from pathlib import Path

    suffix = Path(name).suffix.lower()
    scanner = _SCANNERS.get(suffix)
    if not scanner:
        return []
    lang = _SUFFIX_LANG.get(suffix)
    symbols = scanner(text, repo, name)
    for symbol in symbols:
        symbol["lang"] = lang
    return symbols
