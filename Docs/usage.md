# 用法

## 指令

```bash
changelogkit                       # 等同 serve：啟動本機網頁 GUI
changelogkit serve [--port 8710] [--no-browser]
changelogkit add "標題" [--type 修復] [--file a/b.swift] \
    [--date YYYY.MM.DD] [--time HH:MM] [--ref "[說明](development/notes.md)"（可重複）]
changelogkit list [--grep X] [--since YYYY.MM.DD] [--file X] [--type X] [--limit N]
changelogkit show <編號|關鍵字>
changelogkit export [OUT] [--branch main]      # 匯出唯讀靜態站（預設 _site）
changelogkit community-init                    # 產生「社群與開發交流」範本（Docs/community.md）
```

未安裝時用 `python -m changelogkit …`（`PYTHONPATH` 指向 `src/`）。

全域旗標 **`--locale zh-TW|zh-CN|ja|en`** 可切換 **CLI 說明與網頁語系**（預設跟隨系統：`zh*` 依 Hant／Hans 判為 `zh-TW`／`zh-CN`、`ja*` → `ja`、其餘 → `en`）。

> 新增／修改字串時，`tests/test_changelogkit.py` 的 `I18nKeyTests` 會檢查：程式／HTML／JS 用到的 key 是否都已定義，以及各語系是否缺 key（語系漂移）——CI 會擋下少翻。

查詢類子命令：`languages`（列出**程式語言**：API 宣告掃描涵蓋範圍）與 `locales`（列出 **UI 語系**，`*` 標示目前生效者）。

## 網頁 GUI

`serve` 之後：

| 路徑 | 內容 |
| --- | --- |
| `/` | 變更歷史：瀏覽／新增／編輯／刪除 |
| `/development` | 開發索引：功能／API 宣告／文件／近期改動（提交可展開看 diff） |
| `/development/file?repo=app&path=…` | 檔案檢視：行號、語法上色；`.md` 預設排版檢視 |

> 變更歷史與文件內部的**相對連結會自動改寫成站內連結**（詳見「變更歷史格式」），不需手寫 `/development/file?...`。

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
