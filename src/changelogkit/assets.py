"""網頁資產（HTML／CSS／JS）載入。

預設資產在套件內的 ``changelogkit/assets/``。若 ``.changelog.toml`` 設定了
``assets`` 目錄，載入時**先找該目錄的同名檔，找不到才用套件預設**——因此各 repo
可以只放一個 ``theme.css`` 換配色，或放整組 ``index.*`` / ``dev.*`` / ``file.*``
把版面整包換掉。``render`` 提供極簡的 ``{{key}}`` 佔位替換，足以套用少量動態內容。
"""

from pathlib import Path

from . import config

ASSETS = Path(__file__).resolve().parent / "assets"

_MIME = {
    ".html": "text/html; charset=utf-8",
    ".css": "text/css; charset=utf-8",
    ".js": "application/javascript; charset=utf-8",
}


def _search_roots():
    """資產查找順序：repo 覆寫目錄 → 套件預設。"""
    override = config.load().assets
    return [override, ASSETS] if override else [ASSETS]


def path(name):
    """回傳資產檔的絕對路徑；僅允許單層檔名（阻擋路徑穿越）。"""
    if not name or "/" in name or "\\" in name or name.startswith("."):
        raise ValueError("不允許的資產名稱")
    for root in _search_roots():
        base = root.resolve()
        candidate = (root / name).resolve()
        if candidate.is_relative_to(base) and candidate.is_file():
            return candidate
    raise ValueError("找不到資產")


def read(name):
    """讀取資產全文。"""
    return path(name).read_text(encoding="utf-8")


def mime(name):
    """依副檔名回傳 Content-Type。"""
    return _MIME.get(Path(name).suffix, "application/octet-stream")


def render(name, **subs):
    """讀取模板並以 ``{{key}}`` 佔位替換。"""
    text = read(name)
    for key, value in subs.items():
        text = text.replace("{{" + key + "}}", value)
    return text
