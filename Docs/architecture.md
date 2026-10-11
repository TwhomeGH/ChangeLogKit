# 模組結構與設計

`src/changelogkit/`：

| 模組 | 職責 |
| --- | --- |
| `config.py` | 讀 `.changelog.toml`（3.11+ 用標準庫 `tomllib`、3.10 用 `tomli`） |
| `history.py` | 變更歷史（`ChangeHistory.md`）的解析／組版／讀寫 |
| `index.py` | 開發索引：Git 近期改動（含 `/development/diff`）、Swift 宣告掃描、文件 |
| `server.py` | 本機 HTTP server 與路由（`/`、`/development*`、`/assets/*`、`/api/*`） |
| `cli.py` | 命令列：serve／add／list／show／export |
| `export.py` | 靜態匯出（唯讀，供 GitHub Pages） |
| `assets.py` + `assets/` | 網頁資產載入（含 repo 覆寫查找）與預設資產 |

## 設計要點

- **所有 repo 差異集中在 `config.py`／`.changelog.toml`**，其餘模組不硬編專案路徑。
- 工具只對 repo **唯讀**；唯一寫入是變更歷史檔（`add`／GUI 編輯）。
- 靜態匯出**預先渲染 HTML**（不是改寫 SPA），避免依賴動態端點。
- 開發索引的 API 掃描是**文字比對**（非 AST）：Swift（`func`／型別／存取修飾屬性）、JS／TS（`function`／`class`／`interface`／`type`／`enum`／`export` 的 const 等）、Python（`def`／`class`）；不含呼叫關係，也不保證完整。未支援的副檔名不會被索引。
- 相依：執行期需 `git`；`tomli` 僅 Python 3.10 需要。

## 檔案檢視與開發索引的差異

| | 動態（`serve`） | 靜態（`export`） |
| --- | --- | --- |
| 變更歷史 | 可新增／編輯／刪除 | 唯讀 |
| 近期改動 diff | lazy 抓取 | 內嵌 `<details>` |
| 檔案檢視 | 站內帶行號／上色 | 僅 `.md` 檢視頁 + GitHub blob 連結 |
| API 宣告／文件 | 即時掃描 | 預先渲染 |
