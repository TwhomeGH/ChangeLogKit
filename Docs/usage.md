# 用法

## 指令

```bash
changelogkit                       # 等同 serve：啟動本機網頁 GUI
changelogkit serve [--port 8710] [--no-browser]
changelogkit add "標題" [--type 修復] [--file a/b.swift] \
    [--date YYYY.MM.DD] [--time HH:MM] [--ref "[說明](Docs/x.md)"（可重複）]
changelogkit list [--grep X] [--since YYYY.MM.DD] [--file X] [--type X] [--limit N]
changelogkit show <編號|關鍵字>
changelogkit export [OUT] [--branch main]      # 匯出唯讀靜態站（預設 _site）
```

未安裝時用 `python -m changelogkit …`（`PYTHONPATH` 指向 `src/`）。

## 網頁 GUI

`serve` 之後：

| 路徑 | 內容 |
| --- | --- |
| `/` | 變更歷史：瀏覽／新增／編輯／刪除 |
| `/development` | 開發索引：功能／API 宣告／文件／近期改動（提交可展開看 diff） |
| `/development/file?repo=app&path=…` | 檔案檢視：行號、語法上色；`.md` 預設排版檢視 |

## 設定：`.changelog.toml`

放 repo 根目錄；工具從工作目錄**往上**尋找，找不到用預設值。

```toml
[tool.changelog]
title    = "My Project 變更歷史"                # 網頁標題（預設＝repo 目錄名）
history  = "Docs/ChangeHistory.md"             # 變更歷史 markdown
features = "Docs/development/features.json"    # 選填：功能清單
assets   = "Scripts/changelog-overrides"       # 選填：覆寫預設網頁資產

[[tool.changelog.sources]]                     # 開發索引要一起看的來源
name = "app"
path = "."
[[tool.changelog.sources]]
name = "lib"
path = "${SOME_LIB_ROOT}"                      # 支援 ${ENV} 展開；不存在就略過
```

| 欄位 | 預設 | 說明 |
| --- | --- | --- |
| `title` | repo 目錄名 | 頁面標題 |
| `history` | `Docs/ChangeHistory.md` | 變更歷史檔（必要） |
| `features` | `Docs/development/features.json` | 功能清單（不存在則功能分頁留空） |
| `assets` | 無 | 覆寫資產目錄 |
| `sources` | 單一（`name="app"`、`path="."`） | 開發索引來源；`path` 支援 `${ENV}` |

## 變更歷史格式

最新在最上：

```markdown
## YYYY.MM.DD HH:MM 一句話標題
**類型**: 修復 · **檔案**: `a/b.swift`

### 問題 - 摘要
### 根因 - 摘要
### 修改 - 核心手法
- 其他改動

**相關文件**:
- [說明](Docs/x.md)
- [另一份](Docs/y.md)

---
```

相關文件：**單筆**可寫成一行 `**相關文件**: [說明](Docs/x.md)`；**多筆**建議逐行條列（如上），避免原始檔出現一大長行。兩種寫法在 GUI 與靜態站都會正常渲染。

時間可省略（舊資料相容）。

## 資產覆寫

`assets` 指向一個目錄；載入時**先找該目錄的同名檔，找不到才用套件預設**：

- 只放 `theme.css` → 只換配色。
- 放整組 `index.*`／`dev.*`／`file.*` → 整包換掉版面。

可覆寫檔名：`theme.css`、`theme.js`、`index.html/css/js`、`dev.html/css/js`、`file.html/css/js`、`highlight.js`、`markdown.js`。

## 功能清單 `features.json`（選填）

物件陣列，至少要有 `id`、`name`、`summary`、`files`、`docs`：

```json
[
  { "id": "my-feature", "name": "範例功能", "summary": "一句話說明。",
    "files": ["Sources/Foo.swift"], "docs": ["Docs/foo.md"] }
]
```

`files`／`docs` 必須是索引內（Git 可見）的相對路徑，否則載入時報錯。
