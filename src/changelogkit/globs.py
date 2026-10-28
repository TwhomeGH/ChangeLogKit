"""glob → 正規式（支援 ``**`` 跨目錄、``*`` 單層、``?`` 單字元）。

``.changelog.toml`` 的 ``exclude`` 與文件分類都共用這裡，避免兩套 glob 語意。
"""

import re

_CACHE = {}


def regex(pattern):
    """把含 ``**`` 的 glob 轉成正規式；相同 pattern 會快取。"""
    if pattern not in _CACHE:
        out, i = "", 0
        while i < len(pattern):
            if pattern[i:i + 2] == "**":
                i += 2
                if pattern[i:i + 1] == "/":     # ``**/`` 可匹配零層目錄
                    out += "(?:.*/)?"
                    i += 1
                else:
                    out += ".*"
            elif pattern[i] == "*":
                out += "[^/]*"
                i += 1
            elif pattern[i] == "?":
                out += "[^/]"
                i += 1
            else:
                out += re.escape(pattern[i])
                i += 1
        _CACHE[pattern] = re.compile("^" + out + "$")
    return _CACHE[pattern]


def matches(pattern, path):
    """``path`` 是否符合 glob ``pattern``（兩者都用 ``/`` 分隔）。"""
    return bool(regex(pattern).match(path))
