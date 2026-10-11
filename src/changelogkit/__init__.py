"""changelogkit：本機變更歷史 GUI 與開發索引。

通用工具，與任何特定 repo 解耦：

* 變更歷史 — 解析 ``Docs/ChangeHistory.md``（可設定路徑），提供網頁 GUI 與 CLI。
* 開發索引 — 唯讀索引 Git 近期改動（可展開 diff）、Swift 宣告定位、Markdown 文件。

每個 repo 的差異由 repo 根目錄的 ``.changelog.toml`` 提供；未提供時用預設值。
"""

__version__ = "0.1.0"
