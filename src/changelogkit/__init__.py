"""changelogkit：本機變更歷史 GUI 與開發索引。

通用工具，與任何特定 repo 解耦：

* 變更歷史 — 解析 ``Docs/ChangeHistory.md``（可設定路徑），提供網頁 GUI 與 CLI。
* 開發索引 — 唯讀索引 Git 近期改動（可展開 diff）、Swift 宣告定位、Markdown 文件。

每個 repo 的差異由 repo 根目錄的 ``.changelog.toml`` 提供；未提供時用預設值。
"""

from importlib import metadata as _metadata
from pathlib import Path

_PACKAGE_NAME = "changelogkit"


def _pyproject_version():
    """原始碼 checkout 的 ``pyproject.toml`` 版號；找不到或無法解析時回 None。

    自套件目錄往上找 ``pyproject.toml``（涵蓋 ``src/changelogkit`` 與 ``changelogkit``
    兩種版面），只採用 ``project.name`` 為本套件者。
    """
    try:
        import tomllib as _toml            # Python 3.11+ 標準庫
    except ModuleNotFoundError:
        try:
            import tomli as _toml          # Python 3.10（條件式相依）
        except ModuleNotFoundError:
            return None
    node = Path(__file__).resolve().parent
    for _ in range(3):
        node = node.parent
        candidate = node / "pyproject.toml"
        if not candidate.is_file():
            continue
        try:
            data = _toml.loads(candidate.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            continue
        project = data.get("project") or {}
        if project.get("name") == _PACKAGE_NAME and project.get("version"):
            return str(project["version"])
    return None


def _installed_version():
    """已安裝套件的中介資料版號；未安裝時回 None。"""
    try:
        return _metadata.version(_PACKAGE_NAME)
    except _metadata.PackageNotFoundError:
        return None


# 版號來源優先序：原始碼 checkout 的 pyproject → 已安裝中介資料 → 字面值備援。
# 優先原始碼，讓 `PYTHONPATH=src` 直接跑時「所見即所跑」，不被環境中殘留的舊安裝誤導。
__version__ = _pyproject_version() or _installed_version() or "0.10.0"
