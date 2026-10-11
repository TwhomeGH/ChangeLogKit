"""changelogkit：本機變更歷史 GUI 與開發索引。

通用工具，與任何特定 repo 解耦：

* 變更歷史 — 解析 ``Docs/ChangeHistory.md``（可設定路徑），提供網頁 GUI 與 CLI。
* 開發索引 — 唯讀索引 Git 近期改動（可展開 diff）、Swift 宣告定位、Markdown 文件。

每個 repo 的差異由 repo 根目錄的 ``.changelog.toml`` 提供；未提供時用預設值。
"""

from importlib import metadata as _metadata

try:
    # 單一來源：安裝套件的中介資料（由 pyproject 的 version 產生）。
    __version__ = _metadata.version("changelogkit")
except _metadata.PackageNotFoundError:
    # 未安裝（例如 PYTHONPATH=src 直接跑）：退回字面值，需與 pyproject 同步。
    __version__ = "0.1.6"
