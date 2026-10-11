"""設定載入：從 repo 根目錄的 ``.changelog.toml`` 讀取。

設計原則：**所有與特定 repo 有關的差異都在這裡**，其餘模組只讀 :class:`Config`，
不硬編專案路徑。工具從工作目錄往上尋找 ``.changelog.toml``；找不到則用預設值
（歷史檔 ``Docs/ChangeHistory.md``、功能清單 ``Docs/development/features.json``、
標題為 repo 目錄名、單一來源＝自己）。

TOML 解析：Python 3.11+ 用標準庫 ``tomllib``；3.10 用 ``tomli``（pyproject 已條件式相依）。
"""

import os
from dataclasses import dataclass, field
from pathlib import Path

try:  # Python 3.11+
    import tomllib as _toml
except ModuleNotFoundError:  # 3.10：需 tomli
    try:
        import tomli as _toml
    except ModuleNotFoundError:  # pragma: no cover - 環境未安裝 tomli
        _toml = None

CONFIG_NAME = ".changelog.toml"
DEFAULT_HISTORY = "Docs/ChangeHistory.md"
DEFAULT_FEATURES = "Docs/development/features.json"


@dataclass
class Source:
    """一個被索引的 repo／來源。"""

    name: str
    path: Path


@dataclass
class Config:
    """一次執行所使用、已解析的設定。"""

    root: Path                       # repo 根目錄（.changelog.toml 所在，或工作目錄）
    title: str                       # 網頁標題
    history: Path                    # ChangeHistory.md
    features: Path | None            # 功能清單（可能不存在）
    assets: Path | None              # 覆寫資產目錄（可選）
    sources: list = field(default_factory=list)  # 開發索引來源
    include: tuple = ()      # 額外納入的 glob（相對 root；可涵蓋被 .gitignore 忽略者，如 node_modules）
    exclude: tuple = ()      # 排除的 glob（相對 root）


def _find_root(start):
    """從 start 往上尋找含 ``.changelog.toml`` 的目錄；找不到回傳 start。"""
    start = Path(start).resolve()
    for directory in [start, *start.parents]:
        if (directory / CONFIG_NAME).is_file():
            return directory
    return start


def _default_config(root):
    """沒有任何設定檔時的預設。"""
    return Config(
        root=root,
        title=root.name,
        history=root / DEFAULT_HISTORY,
        features=root / DEFAULT_FEATURES,
        assets=None,
        # 主來源固定命名為 "app"，讓預設網頁資產（連結用 repo=app）可直接運作。
        sources=[Source("app", root)],
    )


def _resolve(root, value):
    """把設定中的相對路徑接到 root，並展開 ``${ENV}``。"""
    return Path(os.path.expandvars(os.path.expanduser(str(value))))


def _from_table(root, table):
    """由 ``[tool.changelog]`` 表建出 :class:`Config`。"""
    history = root / table.get("history", DEFAULT_HISTORY)
    features = root / table["features"] if table.get("features") else root / DEFAULT_FEATURES
    assets = root / table["assets"] if table.get("assets") else None
    sources = [
        Source(str(s.get("name") or root.name), _resolve(root, s.get("path") or "."))
        for s in table.get("sources", [])
    ]
    return Config(
        root=root,
        title=table.get("title") or root.name,
        history=history,
        features=features,
        assets=assets,
        sources=sources or [Source("app", root)],
        include=tuple(str(x) for x in table.get("include", [])),
        exclude=tuple(str(x) for x in table.get("exclude", [])),
    )


_cache = None


def load(start=None, use_cache=True):
    """載入並快取設定。``start`` 預設為目前工作目錄。"""
    global _cache
    if use_cache and _cache is not None:
        return _cache
    start = Path(start) if start else Path.cwd()
    root = _find_root(start)
    config_file = root / CONFIG_NAME
    if config_file.is_file() and _toml is not None:
        data = _toml.loads(config_file.read_text(encoding="utf-8"))
        table = (data.get("tool") or {}).get("changelog") or {}
        config = _from_table(root, table)
    else:
        config = _default_config(root)
    if use_cache:
        _cache = config
    return config


def reset():
    """清除快取（測試用）。"""
    global _cache
    _cache = None
