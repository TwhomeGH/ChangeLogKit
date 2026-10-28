# 用法

## 指令

```bash
changelogkit                       # 等同 serve：啟動本機網頁 GUI
changelogkit serve [--port 8710] [--no-browser]
changelogkit add "標題" [--type 修復] [--file a/b.swift] \
    [--problem "問題摘要"] [--cause "根因摘要"] [--change "修改摘要"（可重複）] \
    [--date YYYY.MM.DD] [--time HH:MM] [--ref "[說明](development/notes.md)"（可重複）]
changelogkit list [--grep X] [--since YYYY.MM.DD] [--file X] [--type X] [--limit N]
changelogkit show <編號|關鍵字>
changelogkit export [OUT] [--branch main]      # 匯出唯讀靜態站（預設 _site）
changelogkit community-init                    # 產生「社群與開發交流」範本（Docs/community.md）
changelogkit docs [--check] [--summary]        # 檢查文件分類（錯誤回 1）
changelogkit docs-init                         # 印出可貼上的 docs TOML 範本
```

`add` 的標題是唯一的位置參數；內文用 `--problem`／`--cause`／`--change` 提供。各節第一行是摘要（會接在 `### 問題 - ` 等標題後），其餘行是細節；`--change` 可重複，第一筆當摘要、其餘轉成條列。只給標題時插入空骨架。

未安裝時用 `python -m changelogkit …`（`PYTHONPATH` 指向 `src/`）。

全域旗標 **`--locale zh-TW|zh-CN|ja|en`** 可切換 **CLI 說明與網頁語系**（預設跟隨系統：`zh*` 依 Hant／Hans 判為 `zh-TW`／`zh-CN`、`ja*` → `ja`、其餘 → `en`）。

> 新增／修改字串時，`tests/test_changelogkit.py` 的 `I18nKeyTests` 會檢查：程式／HTML／JS 用到的 key 是否都已定義，以及各語系是否缺 key（語系漂移）——CI 會擋下少翻。

查詢類子命令：`languages`（列出**程式語言**：API 宣告掃描涵蓋範圍）與 `locales`（列出 **UI 語系**，`*` 標示目前生效者）。

## 本機開發（用工作區原始碼）

`changelogkit` 指令永遠是安裝版（`site-packages`）；要測這個 repo 的改動，用 `tools/dev.py`：

```powershell
# 在 ChangeLogTools repo 內，指向目標 repo
python tools\dev.py --repo F:\VideoServer serve --port 8710

# 或先 cd 到目標 repo，用工具的絕對路徑
cd F:\VideoServer
python C:\Users\agp05\OneDrive\桌面\ChangeLogTools\tools\dev.py serve
```

它會把 `src/` 前置到 `PYTHONPATH`、切到目標 repo（套用該 repo 的 `.changelog.toml`），再把參數原封不動轉給 `python -m changelogkit`。任何子命令都適用（`serve`／`export`／`add`／`list`）。啟動前會印出 `source`／`target`／`config`；`--dry-run` 只顯示指令。`tools/dev.ps1` 是等價的 PowerShell 外殼。

> 只影響該次執行，不會安裝或修改 `site-packages`。前端資產會被瀏覽器快取，改完記得 Ctrl+F5。單元測試仍用 `pytest`。

`--help` 是旗標的來源；要看 changelogkit 自己的子命令說明，用 `--` 傳給它：

```powershell
python tools\dev.py -- serve --help
python tools\dev.py -- docs --help
```

Python 沒有 PowerShell 的 `Get-Help`；等價的是 `--help`、`python -m pydoc tools.dev`（顯示模組 docstring 與範例），或在 REPL 用 `help(tools.dev)`。`Docs/usage.md` 只寫流程與範例，精確旗標以 `--help` 為準。

## 網頁 GUI

`serve` 之後：

| 路徑 | 內容 |
| --- | --- |
| `/` | 變更歷史：瀏覽／新增／編輯／刪除 |
| `/development` | 開發索引：功能／API 宣告／文件／近期改動（提交可展開看 diff） |
| `/development/file?repo=app&path=…` | 檔案檢視：行號、語法上色；`.md` 預設排版檢視 |

> 變更歷史與文件內部的**相對連結會自動改寫成站內連結**（詳見「變更歷史格式」），不需手寫 `/development/file?...`。

## 靜態站（export）

`changelogkit export [OUT]` 產生唯讀靜態站（預設 `_site`）。開發索引拆成三頁，避免一次載入所有 diff：

| 路徑 | 內容 |
| --- | --- |
| `development/index.html` | 文件（分組／顏色／備註）＋功能 |
| `development/symbols.html` | API 宣告 |
| `development/repos.html` | 近期改動與完整 diff |
| `docs/<原路徑>.html` | 每份文件的穩定頁面（例：`docs/Docs/api/README.html`） |
| `about/index.html` | 關於 |

文件頁會顯示群組 badge、來源路徑、備註與目錄（TOC）；標題有 anchor id。桌面版目錄固定在左側（sticky），手機版用右下角「目錄」按鈕開抽屜。文件 URL 以原路徑為準，不再使用排序編號（舊的 `docs/0.html` 會失效）。

## 設定：`.changelog.toml`

放 repo 根目錄；工具從工作目錄**往上**尋找，找不到用預設值。

```toml
[tool.changelog]
title    = "My Project 變更歷史"                # 網頁標題（預設＝repo 目錄名）
history  = "Docs/ChangeHistory.md"             # 變更歷史 markdown
features = "Docs/development/features.json"    # 選填：功能清單
community = "Docs/community.md"                # 選填：關於頁的「社群與開發交流」區塊
assets   = "Scripts/changelog-overrides"       # 選填：覆寫預設網頁資產

[[tool.changelog.sources]]                     # 開發索引要一起看的來源
name = "app"
path = "."
[[tool.changelog.sources]]
name = "lib"
path = "${SOME_LIB_ROOT}"                      # 支援 ${ENV} 展開；不存在就略過

include  = ["node_modules/kick-ws/dist/**/*.d.ts"]  # 額外納入（可含被 .gitignore 忽略者）
exclude  = ["**/dist/**", "**/*.min.js"]            # 排除（例如建置產物）
```

| 欄位 | 預設 | 說明 |
| --- | --- | --- |
| `title` | repo 目錄名 | 頁面標題 |
| `history` | `Docs/ChangeHistory.md` | 變更歷史檔（必要） |
| `features` | `Docs/development/features.json` | 功能清單（不存在則功能分頁留空） |
| `community` | `Docs/community.md` | 「關於」頁的社群區塊（不存在則不顯示） |
| `assets` | 無 | 覆寫資產目錄 |
| `sources` | 單一（`name="app"`、`path="."`） | 開發索引來源；`path` 支援 `${ENV}` |
| `include` | 無 | 額外納入的 glob（相對 root；**可涵蓋被 `.gitignore` 忽略者**，如特定 `node_modules` 套件的 `.d.ts`） |
| `exclude` | 無 | 排除的 glob（相對 root），例如 `**/dist/**`、`**/*.min.js` |

> glob 語法：`**` 跨目錄、`*` 單層、`?` 單字元。索引預設只看版本控管（含未忽略）的檔案；`include` 用於**選擇性**納入被忽略者（例如只看幾個已安裝套件的型別定義），`exclude` 用來排除建置產物。

## 文件分類（Documents 分頁）

`/development` 的「文件」分頁可在 `.changelog.toml` 手動分類、加備註與顏色：

```toml
[tool.changelog.docs]
unlisted = "other"            # other（預設）／folder／hidden
auto     = true               # 未命中設定時，依資料夾名稱自動分類（預設開）

[[tool.changelog.docs.groups]]
id = "dev"                    # 必填、唯一
title = "開發者指南"
color = "blue"                # blue／green／amber／violet／rose／cyan／slate
note = "開發流程、測試、資料模型與 API"
order = 10                    # 數字越小越前面（預設 100）
paths = ["Docs/development/**", "Docs/api/**"]

[[tool.changelog.docs.entries]]
path = "Docs/api/README.md"   # 精確路徑或 glob
title = "API 總覽"            # 選填：覆寫顯示標題
note = "先看這份，再看各端點"  # 選填：卡片備註
group = "dev"                 # 選填：強制指定群組
```

判定順序：

1. `entries` 命中 → 套用標題／備註；有 `group` 就強制使用。
2. 否則由 `groups.paths` 比對；**同一份文件最多只能命中一個群組**，重疊視為設定錯誤。
3. 都沒命中且 `auto = true` → 依路徑中的資料夾自動分類（取**最深**命中的資料夾）。
4. 還是沒有 → 依 `unlisted`：`other` 放「其他」（預設）、`folder` 依所在資料夾分組、`hidden` 不顯示。

自動分類的資料夾（不分大小寫；`api` 與 `development` 都歸「開發者指南」）：

| 資料夾 | 群組 |
| --- | --- |
| `api`、`apis`、`development`、`dev` | 開發者指南 |
| `guide`、`guides`、`manual`、`usage` | 使用指南 |
| `deploy`、`deployment`、`ops`、`operations` | 部署與維運 |
| `design`、`adr`、`architecture` | 架構與設計 |

設定群組永遠優先於自動分類；要改預設群組的標題／顏色，就定義一個 `paths` 相同的群組覆蓋它。`auto = false` 可完全關閉自動分類。

分類設定有問題時（群組重疊、未知群組／顏色、pattern 沒命中任何文件…），Documents 分頁上方會顯示警告；文件不會因此消失。glob 語法與上面 `include`／`exclude` 相同。Documents 分頁也有群組 chips 可篩選（會記住上次選擇）。

驗證與起始設定：

```bash
changelogkit docs --check            # 列出解析後的群組／文件與警告；設定錯誤 exit 1
changelogkit docs --check --summary  # 只看群組數量
changelogkit docs-init > docs.toml   # 依現有資料夾印出可貼上的 TOML（不修改任何檔案）
```

`docs-init` 只把 TOML 印到 stdout（提示訊息走 stderr），不會改寫 `.changelog.toml`。

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
- [說明](development/notes.md)
- [另一份](../guide.md)

---
```

相關文件：**單筆**可寫成一行 `**相關文件**: [說明](development/notes.md)`；**多筆**建議逐行條列（如上），避免原始檔出現一大長行。兩種寫法在 GUI 與靜態站都會正常渲染。

**相對連結以「該文件所在目錄」為基準**（與 GitHub 相同）自動改寫成站內連結，點擊即在站內開啟目標文件——不必手寫 `/development/file?...`。同一套改寫也適用於文件內互連：動態站指向檔案檢視頁，靜態站優先指向匯出的文件頁、其次 GitHub blob；外部 `https://` 連結維持原樣。

時間可省略（舊資料相容）。

## 社群與開發交流（選填）

在「關於」頁顯示社群／開發管道卡片（Discord、Twitch、原始碼、Issues…）。內容來自 `community` 指定的 markdown（預設 `Docs/community.md`）；**未設定或檔案不存在時該區塊不顯示**。

格式慣例（極簡，說明文用一般 markdown，不新增方言）：

```markdown
# <區塊標題>
## <卡片標題>
<卡片說明（markdown）>
[<行動文字>](<連結>)
```

- 第一個 `#` 為區塊標題；每個 `##` 起一張卡片。
- 卡片內**獨立成行的第一個連結**作為行動按鈕，該行不列入說明；行內連結則留在說明中。
- 相對連結以本檔所在目錄為基準改寫（同「相關文件」）。靜態站優先連到站內文件頁，其次 GitHub blob。

產生範本：

```bash
changelogkit community-init      # 寫入 Docs/community.md（已存在則不覆蓋）
```

> 工具對 repo **唯讀**：`serve`／`export` 不會自動建立或修改此檔，需以 `community-init` 明示產生。

## 資產覆寫

`assets` 指向一個目錄；載入時**先找該目錄的同名檔，找不到才用套件預設**：

- 只放 `theme.css` → 只換配色。
- 放整組 `index.*`／`dev.*`／`file.*` → 整包換掉版面。

可覆寫檔名：`theme.css`、`theme.js`、`index.html/css/js`、`dev.html/css/js`、`file.html/css/js`、`highlight.js`、`markdown.js`。

## 功能清單 `features.json`（選填）

物件陣列，**通用 schema**：只有 `name` 必填，其餘欄位自由定義，會逐列顯示在「功能」分頁。

```json
[
  { "name": "範例功能", "summary": "一句話說明（可選）。",
    "labels": { "platform": "平台", "status": "狀態" },
    "platform": "iOS / macOS", "status": "待驗證",
    "files": ["Sources/Foo.swift"], "docs": ["Docs/foo.md"] }
]
```

- 保留鍵：`name`（必填）、`id`（可選，預設取 `name`）、`summary`、`files`、`docs`、`labels`。
- 其餘欄位一律當「接入狀態」逐列渲染；欄位標籤可用同筆的 `labels` 對照（預設直接用 key）。
- `files`／`docs` 若填，必須是索引內（Git 可見）的相對路徑，否則載入時報錯。
- 也支援**物件形式**（共用標籤一次定義，適合多筆共用同一組欄位）：

```json
{ "labels": { "replaykit": "ReplayKit", "screencapturekit": "ScreenCaptureKit" },
  "features": [ { "name": "…", "replaykit": "支援" } ] }
```

  頂層 `labels` 為全域欄位標籤，逐筆的 `labels` 可覆寫。
