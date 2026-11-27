# 用法

## 指令

```bash
changelogkit                       # 等同 serve：啟動本機網頁 GUI
changelogkit serve [--port 8710] [--host 127.0.0.1] [--allow-write] [--no-browser]
changelogkit add "標題" [--type 修復] [--file a/b.swift] \
    [--problem "問題摘要"] [--cause "根因摘要"] [--change "修改摘要"（可重複）] \
    [--change-detail "修改細節（可多行）"] \
    [--date YYYY.MM.DD] [--time HH:MM] [--ref "[說明](development/notes.md)"（可重複）]
changelogkit list [--grep X] [--since YYYY.MM.DD] [--file X] [--type X] [--limit N]
changelogkit show <編號|關鍵字>
changelogkit export [OUT] [--branch main]      # 匯出唯讀靜態站（預設 _site）
changelogkit sort [--apply]                    # 依標題日期／時間排序（預設只預覽）
changelogkit community-init                    # 產生「社群與開發交流」範本（Docs/community.md）
changelogkit docs [--check] [--summary]        # 檢查文件分類（錯誤回 1）
changelogkit docs-init                         # 印出可貼上的 docs TOML 範本
changelogkit capabilities [--json]              # 列出此安裝版本的已知功能
changelogkit workflows [--json] [--check]       # 掃描 GitHub Actions action runtime
```

`add` 的標題是唯一的位置參數；內文用 `--problem`／`--cause`／`--change` 提供。各節第一行是摘要（會接在 `### 問題 - …` 等標題後），其餘行是細節；`--change` 可重複，第一筆當摘要、其餘轉成條列；`--change-detail` 在修改摘要下補一段多行說明。Web 表單分「修改摘要」（單行）、「修改細節」（段落）、「其他修改」（每行一項）。只給標題時插入空骨架。

內文中的 `#`／`##` 子標題會自動轉成 `###`，並補上標題前後空行；紀錄邊界只認 `## YYYY.MM.DD`，避免單筆紀錄的內文被拆成多筆。

摘要末尾的 `.,;:!?。，；：！？` 會自動移除（markdownlint MD026）；`…`、`—` 不在規則內，會保留；內文與條列不受影響。

未安裝時用 `python -m changelogkit …`（`PYTHONPATH` 指向 `src/`）。

全域旗標 **`--locale zh-TW|zh-CN|ja|en`** 可切換 **CLI 說明與網頁語系**（預設跟隨系統：`zh*` 依 Hant／Hans 判為 `zh-TW`／`zh-CN`、`ja*` → `ja`、其餘 → `en`）。

> 新增／修改字串時，`tests/test_changelogkit.py` 的 `I18nKeyTests` 會檢查：程式／HTML／JS 用到的 key 是否都已定義，以及各語系是否缺 key（語系漂移）——CI 會擋下少翻。

查詢類子命令：`languages`（列出**程式語言**：API 宣告掃描涵蓋範圍）、`locales`（列出 **UI 語系**，`*` 標示目前生效者）與 `capabilities`（列出此安裝版本的已知功能）。

`capabilities --json` 是給技能／腳本使用的機器可讀清單；它只描述穩定的功能邊界，不取代 `--help` 與本文件。清單未列出的功能不代表不存在，應以實際版本的 `--help`／原始碼為準。

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

### VSCode 快速自檢

repo 內的 `.vscode/launch.json`／`tasks.json` 已預設使用工作區 `src/`，不需要先安裝成 site-packages：

- **Run and Debug**
  - `changelogkit: serve (source)`：本機 GUI，debugpy 進入點是 `python -m changelogkit serve`
  - `changelogkit: serve (LAN, read-only)`：`--host 0.0.0.0`，供平板／手機查看
  - `pytest: all`
  - `pdoc: preview Python API`：直接預覽 pdoc，不先產生靜態檔
- **Terminal → Run Task**
  - `changelogkit: generate Python API (pdoc)`：輸出到 `build/api`
  - `changelogkit: export static site`：輸出到 `_site`
  - `changelogkit: pytest`：使用 `-v --tb=short`，會列出測試名稱；`-q` 只顯示點狀進度與摘要

`pdoc` 在 `dev` extra 內；若使用乾淨虛擬環境，先 `pip install -e ".[dev]"`。這裡刻意用 pdoc 而不是 `pydoc -w`：pdoc 會產生模組索引、搜尋與可交叉連結的多頁 API 文件，適合掛進靜態站；`pydoc -w` 只適合臨時文字／單頁檢視。

> `pytest: all` 是 debug 模式。測試中會有刻意觸發的預期例外，例如：
>
> - 錯誤 tag 的 `check_version.py` 回 `SystemExit: 1`
> - `test_static_export_rejects_api_output_inside_site` 的 `ValueError`（由 `assertRaises` 接收）
>
> debugger 停在這些例外是預期行為，不是測試失敗。日常自檢請用 `Terminal → Run Task → changelogkit: pytest`；若要 debug 全套，請在「中斷點」面板取消勾選 **Raised Exceptions**、**Uncaught Exceptions** 與 **User Uncaught Exceptions**。VSCode debugger 有時會在例外被 `assertRaises` 接住前就停下；這不是測試失敗。launch 設定已關閉子程序除錯，避免 `check_version.py` 的子程序例外。

靜態檢查（CI 也會跑）：

```powershell
ruff check .
ruff format --check .
```

工具在 `pyproject.toml` 的 `dev` extra；本機可直接 `pip install ruff`（CJK 路徑避免 `pip install -e`）。

發版前檢查版本與 tag 一致（publish workflow 也會跑）：

```powershell
python tools\check_version.py --tag v0.11.1
```

## 網頁 GUI

`serve` 之後：

| 路徑 | 內容 |
| --- | --- |
| `/` | 變更歷史：瀏覽／新增／編輯／刪除 |
| `/development` | 開發索引：功能／API 宣告／文件／近期改動（提交可展開看 diff） |
| `/development/file?repo=app&path=…` | 檔案檢視：行號、語法上色；`.md` 預設排版檢視 |

> 變更歷史與文件內部的**相對連結會自動改寫成站內連結**（詳見「變更歷史格式」），不需手寫 `/development/file?...`。

### 從平板／其他裝置連線

預設只綁 `127.0.0.1`，其他裝置無法連線。要從同一個區網的平板或手機開啟：

```powershell
changelogkit serve --host 0.0.0.0
```

啟動訊息會列出本機與區網網址（例如 `http://192.168.1.10:8710/`）；Windows 防火牆若詢問，需允許該連接埠的私人網路存取。

非 loopback 綁定**預設唯讀**：新增／編輯／刪除會回 403。這是刻意的安全預設，因為工具沒有登入驗證；只在信任的區網使用，不要對外公開。確定需要從其他裝置寫入時才加 `--allow-write`。

## 靜態站（export）

`changelogkit export [OUT]` 產生唯讀靜態站（預設 `_site`）。開發索引拆成三頁，避免一次載入所有 diff：

| 路徑 | 內容 |
| --- | --- |
| `development/index.html` | 文件（分組／顏色／備註）＋功能 |
| `development/symbols.html` | API 宣告（依檔案折疊；展開時才上色） |
| `development/repos.html` | 近期改動列表（hash／標題／檔案） |
| `development/commits/<repo>/<hash>.html` | 單筆 commit 的完整 diff（按需載入） |
| `development/todo.html` | 待辦清單（有設定 `todo` 且有項目時才產生） |
| `docs/<來源>/<原路徑>.html` | 每份文件的穩定頁面（例：`docs/app/Docs/api/README.html`） |
| `about/index.html` | 關於 |

文件頁會顯示群組 badge、來源路徑、備註與目錄（TOC）；標題有 anchor id。桌面版目錄固定在左側（sticky），手機版用右下角「目錄」按鈕開抽屜。文件 URL 以「來源＋原路徑」為準，不再使用排序編號（舊的 `docs/0.html` 會失效）。

近期改動只列 `recent_commits` 筆；更舊的提交連到 GitHub（單一來源且有 origin 時），否則連回「變更歷史」。靜態開發首頁有文件搜尋（標題／路徑／備註／摘要），會即時過濾群組並更新數量。

## 設定：`.changelog.toml`

放 repo 根目錄；工具從工作目錄**往上**尋找，找不到用預設值。

```toml
[tool.changelog]
title    = "My Project 變更歷史"                # 網頁主標題（預設＝repo 目錄名）
project  = "My Project"                        # 選填：分頁標題的專案名（預設＝repo 目錄名）
timezone = "Asia/Taipei"                       # 選填：靜態頁尾時間（local／UTC／IANA／±HH:MM）
history  = "Docs/ChangeHistory.md"             # 變更歷史 markdown
todo     = "TODO.md"                           # 選填；預設自動偵測 TODO.md
features = "Docs/development/features.json"    # 選填：功能清單
community = "Docs/community.md"                # 選填：關於頁的「社群與開發交流」區塊
assets   = "Scripts/changelog-overrides"       # 選填：覆寫預設網頁資產
recent_commits = 20                            # 選填：列出的 commit 數（1–200）

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
| `title` | repo 目錄名 | 頁面主標題 |
| `project` | repo 目錄名 | 分頁標題的專案名（`<專案> · <頁面>`） |
| `timezone` | `local` | 靜態頁尾時間的時區；`local`／`UTC`／IANA（如 `Asia/Taipei`）／`+08:00`；未設定時瀏覽器顯示觀看者本地時間 |
| `history` | `Docs/ChangeHistory.md` | 變更歷史檔（必要） |
| `todo` | 自動偵測 `TODO.md`（root／`Docs`） | 待辦 markdown；指定路徑可覆寫，`false` 可關閉 |
| `features` | `Docs/development/features.json` | 功能清單（不存在則功能分頁留空） |
| `community` | `Docs/community.md` | 「關於」頁的社群區塊（不存在則不顯示） |
| `assets` | 無 | 覆寫資產目錄 |
| `recent_commits` | `20` | 開發索引／靜態近期改動列出的 commit 數（1–200） |
| `sources` | 單一（`name="app"`、`path="."`） | 開發索引來源；`path` 相對 repo 根目錄，支援 `${ENV}` |
| `include` | 無 | 額外納入的 glob（相對 root；**可涵蓋被 `.gitignore` 忽略者**，如特定 `node_modules` 套件的 `.d.ts`） |
| `exclude` | 無 | 排除的 glob（相對 root），例如 `**/dist/**`、`**/*.min.js` |

> glob 語法：`**` 跨目錄、`*` 單層、`?` 單字元。索引預設只看版本控管（含未忽略）的檔案；`include` 用於**選擇性**納入被忽略者（例如只看幾個已安裝套件的型別定義），`exclude` 用來排除建置產物。
>
> API 卡片去重：同一個 repo、同目錄且同檔名基底的 `.d.ts` 與 `.js`／`.mjs`／`.cjs`，若同名同種類，只保留 `.d.ts`；不同目錄或不同種類（例如 interface／class）不會互刪。

## Workflow 健康檢查（GitHub Actions）

repo 有 `.github/workflows` 時會自動提供 `/workflows` 頁面與靜態站 `development/workflows.html`。本地掃描 action 參照不需要 token；runtime 查詢需要 GitHub 認證：

- 本機優先使用已登入的 `gh api`（`gh auth login` 即可）。
- CI 使用標準 `GITHUB_TOKEN`／`GH_TOKEN`。
- **不要在 `.changelog.toml` 放 token**。
- 沒有認證或查詢失敗時，runtime 顯示 `unknown`，頁面仍可用。

```toml
[tool.changelog.workflows]
enabled = true          # 有 workflow 目錄時自動啟用；false 可關閉
runtime = true          # 設 false 只做本地掃描，不查 runtime
# path = ".github/workflows"  # 選填：自訂目錄
```

`node12`／`node16`／`node20` 會標成 EOL Node；`node24`、composite、Docker 與重用 workflow 會顯示各自狀態。CLI 可用 `changelogkit workflows --check` 在 EOL runtime 時回傳 1。

## 外部 API 文件（選填）

可以把 Doxygen、Sphinx、Go doc、pdoc 等產生的 HTML，或多個外部 API 站掛進 changelogkit。沒有設定時完全維持現狀；`kind` 只是未來深連結 adapter 的提示，**純掛載不需要指定**。

```toml
[[tool.changelog.api]]
id = "cpp"
title = "C++ API"
html = "build/doxygen/html"       # 本機 HTML 產物
mount = "cpp"                     # /api-docs/cpp/
order = 10
# kind = "doxygen"                # 選填；目前只用於提示

[[tool.changelog.api]]
id = "python"
title = "Python API"
html = "docs/_build/html"
mount = "python"
order = 20

[[tool.changelog.api]]
id = "swift"
title = "Swift API"
url = "https://example.com/documentation/"  # 外部站，不複製
order = 30
```

| 欄位 | 必要 | 說明 |
| --- | --- | --- |
| `id` | 是 | 唯一識別；不可重複 |
| `title` | 否 | 導覽顯示名稱（預設 `id`） |
| `html` | 二選一 | 本機 HTML 目錄；Doxygen 的 `HTML_OUTPUT` 目錄 |
| `url` | 二選一 | 外部 API 文件網址；設定後靜態站直接外連 |
| `mount` | 否 | 掛載路徑 `/api-docs/<mount>/`（預設 `id`，不可重複） |
| `kind` | 否 | 目前可省略；之後 Doxygen／Sphinx 深連結 adapter 會用到 |
| `embed` | 否 | 靜態匯出是否把 `html` 複製到 `api-docs/<mount>/`（預設 `false`） |
| `order` | 否 | 導覽排序（預設 `100`） |

- 動態 `serve`：`/api-docs/<mount>/...` 唯讀掛載，只服務 `html` 目錄內的真實檔案；`..` 與符號連結逃逸會被拒絕。
- 靜態 `export`：有 `url` 時直接外連；沒有 `url` 但 `embed = true` 時才複製。兩者都沒有時，靜態站不顯示入口並在 stderr 警告。
- 多個項目會收成「API 文件」下拉；單一項目直接顯示該站標題。
- 本專案自己的 Pages 用 `pdoc` 產生 Python API 參考到 `build/api`，再以 `embed = true` 掛到 `/api-docs/python/`。
- `html` 不可位於靜態匯出目錄內（例如 `export _site` 而 `html = "_site/api"`），否則匯出前的清理會刪掉 API 產物；工具會直接報錯，請改到獨立目錄。
- Doxygen 的 `.doccarchive`／DocC 不是一般 HTML；目前請用 `url` 指向已託管的文件。tagfile／`objects.inv` 的符號深連結留到後續版本。

## 排序與回填日期

```powershell
changelogkit sort                 # 檢查順序（不寫入）
changelogkit sort --apply         # 依標題日期／時間由新到舊寫回
changelogkit backfill-dates --sort --apply   # 回填缺少日期，同時排序
```

`sort` 依 `## YYYY.MM.DD [HH:MM]` 排序，沒有時間視為 `00:00`，沒有日期的條目排在最後；預設只預覽。

## 待辦（TODO）

預設會自動找 repo 根目錄的 `TODO.md`（大小寫不拘），其次 `Docs/TODO.md`／`docs/TODO.md`；找到就顯示「待辦」入口，不需要設定。要指定其他路徑或關閉：

```toml
[tool.changelog]
todo = "Docs/TODO.md"   # 指定；找不到就不顯示
# todo = false          # 有 TODO.md 但不想顯示時
```

頁面解析 `- [ ]`／`- [x]`（含縮排），忽略程式碼區塊；提供完成進度、全部／未完成／已完成篩選、搜尋，appbar 的「分類」下拉可快速跳到各分類（捲到任何位置都能換），並可連回原始檔。項目中的相對連結以 TODO 檔所在目錄為基準解析；動態站會開檔案檢視，靜態站優先連到站內文件頁，其次 GitHub blob。若 TODO 檔存在但沒有任何任務語法，入口仍會出現，頁面會提示改用 `- [ ]`／`- [x]`。`serve` 的 `/todo` 每 5 秒檢查內容 digest，有變更會更新清單並提示新增／完成筆數；右上角也可手動重新整理。靜態站 `development/todo.html` 是匯出當下的快照，不會自動更新。

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
                              # 別名：orange→amber、gray/grey→slate、purple→violet、red→rose、teal→cyan、yellow→amber
note = "開發流程、測試、資料模型與 API"
order = 10                    # 數字越小越前面（預設 100）
paths = ["Docs/development/**", "Docs/api/**"]

[[tool.changelog.docs.entries]]
path = "Docs/api/README.md"   # 精確路徑或 glob
title = "API 總覽"            # 選填：覆寫顯示標題
note = "先看這份，再看各端點"  # 選填：卡片備註
group = "dev"                 # 選填：強制指定群組
```

`title`／`note`（groups 與 entries 都適用）也可以寫成語系對照表：

```toml
title = { "zh-TW" = "開發者指南", "zh-CN" = "开发者指南", "ja" = "開発者ガイド", "en" = "Developer guide" }
note  = { "zh-TW" = "開發流程與 API", "en" = "Workflow and API" }
```

動態頁依目前 UI 語系選；靜態頁依 `--locale`。缺該語系時退到 `en`、第一個提供值，最後才是 id／預設標題。

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
