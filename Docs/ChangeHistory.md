# ChangeHistory

## 2026.10.14 changelogkit 0.7.2 發佈

**類型**: 修正 · **檔案**: `assets/highlight.js`、`assets/file.js`

### 問題 - 檔案檢視底部的連結失效，無法點擊跳轉

Markdown 檔（如 `Docs/development/METRICKIT.md`）底部「參考」行在排版檢視中，`[文字](URL)` 的方括號消失、也生不出可點的連結。

### 根因 - 上色器會改字，且來源取自「已上色」的 DOM

`highlight.js` 的 `markdownLine` 把 `[文字](URL)` 換成 `<span>文字</span>(URL)`（吃掉 `[` `]`）；而 `file.js` 又以「已上色」逐行 span 的 `textContent` 當作 markdown 來源，連結語法因此被破壞，`renderMarkdown` 解析不到連結。

### 修改 - 上色只加色不改字；來源改取上色前的原文

- `markdownLine` 的連結規則保留方括號（輸出純文字必須等於原字串）。
- `file.js` 先保留原始逐行文字、再上色；排版檢視改用該原文。

---

## 2026.10.14 changelogkit 0.7.1 發佈

**類型**: 修正 · **檔案**: `community.py`、`tests/test_changelogkit.py`

### 問題 - `community-init` 產生的範本不符 markdownlint

預設範本的 `##` 標題後沒有空行，觸發 markdownlint MD022。

### 根因 - 範本字串的 `##` 與說明之間少了空行

`_TEMPLATE` 在每個 `##` 標題後直接接說明段落。

### 修改 - 補上標題後空行並加測試

- `_TEMPLATE` 的每個 `##` 標題後補空行（MD022）。
- 新增測試檢查範本符合 MD041／MD022／MD047。

---

## 2026.10.14 changelogkit 0.7.0 發佈

**類型**: 功能 · **檔案**: `community.py`、`config.py`、`server.py`、`export.py`、`cli.py`、`buildinfo.py`、`__init__.py`、`assets/about.html`、`assets/static_about.html`、`assets/theme.css`、`lang/*.json`

### 問題 - 無法展示維護者的社群／開發管道

想在「關於」頁放一組社群卡片（Discord／Twitch／原始碼…），但工具只呈現變更歷史與開發索引，沒有可配置的展示區塊。

### 根因 - 缺少可配置的展示內容與對應渲染

沒有 `community` 設定，也沒有把一段 markdown 轉成卡片版面的慣例與樣式。

### 修改 - 新增 `community` 設定與「關於」頁社群區塊

- `config.py` 新增 `community`（預設 `Docs/community.md`）；`community.py` 以慣例解析（`#` 標題／`##` 卡片／說明／獨立成行的連結＝行動），組成 `<section class="community">`，說明與行動連結都交給 `markdown.js` 就地渲染，沿用同一套相對連結改寫。
- `server.py`／`export.py` 於「關於」頁注入區塊與來源脈絡（動態 `CK_COMMUNITY`、靜態 `CK_DOC_PATH` 等）；`about.html`／`static_about.html` 加上渲染腳本；`theme.css` 新增卡片樣式。
- 新增 CLI `community-init`：明示產生 `Docs/community.md` 範本（已存在不覆蓋）；`serve`／`export` 仍唯讀，未設定或無檔時該區塊不顯示。
- `buildinfo.py` 抽出 `origin_slug()`，`export.py` 改為共用（去除重複）。
- `__init__.py` 版號來源優先序改為「原始碼 `pyproject.toml` → 已安裝中介資料 → 字面值」：以 `PYTHONPATH=src` 直接跑時「所見即所跑」，不再被環境中殘留的舊安裝版號誤導。

---

## 2026.10.14 changelogkit 0.6.0 發佈

**類型**: 修正 · **檔案**: `assets/markdown.js`、`assets/index.js`、`assets/index.html`、`assets/dev.js`、`assets/file.js`、`assets/static_history.html`、`assets/static_doc.html`、`assets/static_dev.html`、`index.py`、`server.py`、`export.py`

### 問題 - 變更歷史的「相關文件」相對連結在站內找不到

歷史／文件內的相對連結（如 `development/RECORDING_COMPRESSION.md`）被瀏覽器對站根解析成 `/development/RECORDING_COMPRESSION.md`，落入開發索引的 404；在 GitHub 上可用的連結，進了 changelogkit 反而打不開（動態 404、靜態相對路徑也算錯）。

### 根因 - 連結改寫只接在檔案檢視一處

`markdown.js` 早有 `resolveHref` 機制，但只有 `file.js` 接了；變更歷史頁另寫一套 `mdToHtml`、靜態歷史／文件／開發頁與 `dev.js` 的 `mdInline` 都原樣輸出 href。

### 修改 - 抽出共用解析器，所有渲染點統一接上

- `markdown.js`：`resolve` 改為顯式傳參（不再用模組級狀態）；新增 `window.markdownResolver(repo, docPath, options)`（動態：相對路徑 → `/development/file?…`）與 `window.markdownStaticResolver(docPath)`（靜態：命中匯出的文件頁，否則 GitHub blob）。
- `file.js` 改用共用解析器（移除本地重複實作）；`dev.js` 的功能摘要與符號註釋也接上。
- 變更歷史頁改用 `markdown.js` 渲染（移除自寫的 `mdToHtml`），並由 `server.py` 注入 `window.CK_HISTORY`（歷史檔的 repo 相對路徑）作為相對基準；`index.py` 新增 `rel_path` 並在 `snapshot()` 提供 `contexts`。
- 靜態匯出由 `export.py` 注入 `CK_SITE_BASE`／`CK_DOC_PAGES`／`CK_BLOB_BASE`／`CK_DOC_PATH`，歷史／文件／開發頁與符號註釋皆以來源文件路徑為基準改寫。
- 文件：`usage.md`／`architecture.md` 說明相對連結語意（以文件所在目錄為基準，與 GitHub 相同）；`history.py` 格式範例一併更正。

---

## 2026.10.11 changelogkit 0.5.0 發佈

**類型**: 功能 · **檔案**: `assets/markdown.js`、`assets/dev.js`、`assets/static_dev.html`、`assets/dev.css`、`export.py`、`lang/*.json`

### 問題 - JSDoc 註釋未結構化，參數擠成一團

API 宣告卡片的註釋原本整段當 markdown 渲染；`@param {Object} options …` 這類 JSDoc 標籤會與相鄰行併成同一段，難以閱讀。

### 根因 - 只有純 markdown 渲染，沒有標籤解析

掃描器只把整段 doc comment 存成 `comment`，前端以 `renderMarkdown` 原樣輸出，未解析 JSDoc 標籤。

### 修改 - 新增 renderDoc：描述＋參數表＋回傳＋其他標籤

- `markdown.js` 新增 `window.renderDoc(text)`：描述用 markdown；`@param {型別} 名稱 說明` → 參數表（參數／型別／說明）；`@returns` → 回傳列；其他標籤（`@example`／`@throws`…）逐項列出；型別以**巢狀大括號平衡掃描**解析（如 `{{post: Function}}`）；**無標籤時退回 `renderMarkdown`**（向後相容）。
- 動態（`dev.js`）改用 `renderDoc`；靜態頁把原始註釋放進 `data-raw`、由 `static_dev.html` 前端渲染。
- `dev.css` 新增參數表／回傳／標籤樣式；`lang/*.json` 新增 `dev.p_name`／`dev.p_type`／`dev.p_desc`／`dev.returns`（4 語系）。

---

## 2026.10.11 changelogkit 0.4.2 發佈

**類型**: 修正 · **檔案**: `assets/dev.js`、`assets/static_dev.html`

### 問題 - API 宣告卡片的簽名沒有語法上色

符號卡片（尤其被收進「成員」的 `.d.ts` 宣告）的簽名以 `<pre class="sig">` 呈現，但只做 HTML 轉義、沒有上色，閱讀不佳。

### 根因 - 簽名未經 highlight.js

`dev.js` 的 `symbolCard` 對 `r.signature` 只做 `esc()`；靜態頁的簽名也未經前端上色（`export.py` 同）。

### 修改 - 簽名套用 highlight.js

- 動態：`symbolCard` 改用 `window.HL.block(r.signature)`。
- 靜態：`static_dev.html` 載入後對 `pre.sig` 逐一套用 `window.HL.block()`。
- 與檔案檢視／diff 共用同一套上色（Swift 近似掃描），各語言簽名也能大致分色（關鍵字／型別／呼叫）。

---

## 2026.10.11 changelogkit 0.4.1 發佈

**類型**: 修復 · **檔案**: `assets/dev.css`、`assets/dev.js`、`assets/static_dev.html`

### 問題 - 分頁列蓋住 appbar，且三層固定吃掉太多高度

0.4.0 讓分頁列與 appbar 都 `sticky; top: 0`，但分頁列 z-index 更高 → 捲動時**蓋住 appbar**（搜尋列被遮）；且 appbar＋分頁＋篩選三層都固定，固定高度過大。

### 根因 - 固定列各自貼頂、偏移寫死

分頁列未考慮 appbar 已固定；偏移用寫死的 px，而 appbar 會換行、高度並不固定。

### 修改 - 固定列改為堆疊、以實測高度計算，篩選列改為不固定

- 分頁列改貼在 appbar 之下（`top: var(--appbar-h)`），分組小標題再往下堆疊。
- `dev.js` 量測 appbar／分頁列高度寫入 CSS 變數（換行也正確）並監聽 resize；靜態頁同理（量 appbar → `--appbar-h`）。
- 篩選列改為**不固定**（往下捲時捲出），減少固定佔位；appbar 與分頁列仍固定、隨時可切換。

---

## 2026.10.11 changelogkit 0.4.0 發佈

**類型**: 功能 · **檔案**: `assets/dev.js`、`assets/dev.css`、`assets/dev.html`、`assets/static_dev.html`、`export.py`、`lang/*.json`

### 問題 - API 宣告一多，導覽就難用

捲到深處時分頁列早已滑出畫面（要拉回頂端才切得了）；清單是一條平的卡片流、看不出結構；且超過 250 筆就直接截斷、看不到。

### 修改 - 分頁固定、記住瀏覽狀態、依檔案分組、lazy 載入、回到頂端

- **分頁列／篩選列 sticky**：捲到哪都在上方可切換。
- **記住上次瀏覽**（`localStorage`）：分頁、語言、種類、分組下次自動還原。
- **API 宣告預設依檔案分組**：每個檔案一個 sticky 小標題，可切「不分組」。
- **lazy 載入**：每次先渲染 80 筆，捲到底自動追加（移除原本 250 筆上限與提示）。
- **回到頂端**浮動鈕。
- 靜態匯出同步受益：`_render_symbols` 依檔案分組；靜態頁加回到頂端鈕（共用 `dev.css`，sticky 生效）。
- 移除已無用的 `dev.more` 文案；新增 `filter.group`／`filter.by_file`／`filter.no_group`／`dev.showing`。

---

## 2026.10.11 changelogkit 0.3.2 發佈

**類型**: 修復 · **檔案**: `backfill.py`

### 問題 - 回填後殘留連續空行（markdownlint MD012）

`backfill-dates` 轉換條目時會移除 `**時間**：` 宣告行，但只刪了那一行——它前後的兩個空行於是相鄰，變成**連續空行**（MD012）。

### 根因 - 只移除宣告行，未一併收斂緊鄰空行

原始格式為「空行／`**時間**：…`／空行」；刪掉中間那行後，上下兩個空行就黏在一起。

### 修改 - 移除宣告行時同時去掉緊鄰的一個空行

- 轉換時，刪除 `**時間**：` 行的同時也移除其前（或後）緊鄰的空行，避免留下連續空行。
- 補測試（含 `**時間**` 的條目 → 轉換後不得出現連續空行）。

---

## 2026.10.11 changelogkit 0.3.1 發佈

**類型**: 修復 · **檔案**: `backfill.py`

### 修改 - `--strip-number` 也處理「數字點數字」的子編號

- `### 4.1`／`### 11.3` 這類子編號（第一段其實是舊條目編號）現在也會被去除；原本只認得 `### 73a.` 的「字母」寫法。
- `--strip-number` 改為**對所有條目的子標題**生效（含已日期式的條目），並改以「內容是否變動」決定是否寫入（先前只在有條目被轉換時才寫）。

---

## 2026.10.11 changelogkit 0.3.0 發佈

**類型**: 功能 · **檔案**: `backfill.py`、`cli.py`、`lang/*.json`

### 修改 - 新增 `backfill-dates`：從 git 回填缺少日期的條目

- 收編既有 changelog 用：對「標題沒有日期」的條目，找出它**首次出現的 commit**，補成 `## YYYY.MM.DD HH:MM 標題`。
- 日期來源優先序：條目緊接的 `**時間**：<date>` 宣告行 → git 首次加入的 commit（編號式用穩定的 `## N.` 當搜尋字串，標題被改過也找得到）。
- 預設**試跑**（只列出每筆 before→after），加 `--apply` 才寫入；**找不到日期者保持原樣**並列出，不填假日期。
- 選項：`--strip-number`（去掉 `## N.`／`### Na.` 編號）、`--sort`（依日期由新到舊重排；**預設保留原順序**）。
- 補測試（暫存 repo：無日期條目 → 從 git 補上）。

---

## 2026.10.11 changelogkit 0.2.0 發佈

**類型**: 修復 · **檔案**: `history.py`

### 問題 - 產出的 ChangeHistory 有 markdownlint 警告

`changelogkit add` 產生的紀錄檔第一行是 `## …`（沒有 top-level 標題），多筆「相關文件」的清單前也少一個空行，觸發 markdownlint MD041／MD032。

### 根因 - 建檔與組版未顧及 H1 與清單空行

`insert_block` 直接把新區塊插在第一筆 `## ` 之前、`add` 建檔時也沒寫 H1；`build_block` 在 `**相關文件**:` 標籤行後直接接清單。

### 修改 - 寫入時確保 H1，清單前補空行

- `_write` 統一確保內容以 `# ChangeHistory` 開頭（MD041；已有 H1 則不覆寫）。
- `build_block` 在多筆「相關文件」的標籤行與清單之間補空行（MD032）。
- 補測試（`test_history_starts_with_h1`、更新多筆相關文件斷言）。

---

## 2026.10.11 changelogkit 0.1.9 發佈

**類型**: 功能 · **檔案**: `scanners/javascript.py`

### 修改 - 正確解析 `.d.ts`（TypeScript 型別宣告檔）

- **支援 `declare`**：`declare class`／`function`／`const`／`namespace`／`module` 皆納入掃描（前綴修飾接受 `declare`）。
- **支援 `;` 結尾的簽名成員**：`.d.ts` 中沒有實作的方法／屬性簽名（`name(args): T;`、`readonly x: T;`）也抓成成員，配合既有的依縮排收納。
- 一般原始碼不受影響：`.js`／`.ts` 的 `declare` 同樣可用；**`;` 簽名僅在 `.d.ts` 啟用**，避免誤判。
- 實測：TTWChat 的 `.d.ts` → 463 個頂層符號；`WebSocketManager` → 18 個成員、`KickWebSocket` → 6 個、`EventEmitter` → 11 個。

---

## 2026.10.11 changelogkit 0.1.8 發佈

**類型**: 優化 · **檔案**: `lang/*.json`、`assets/dev.js`、`Docs/*.md`

### 修改

- `--locale` 的說明改為**泛用描述**（「介面語系（預設跟隨系統；用 changelogkit locales 查詢）」），**不再逐一列出語系**——避免日後新增語系時說明越堆越長、與實際不同步。
- 移除 `dev.js` 中已被 `markdown.js` 取代的 `mdDoc`（死碼）。
- 文件（`architecture.md`／`usage.md`）的語系清單更新為四個，並修正語系判定說明（`zh*` 依 Hant／Hans 判 zh-TW／zh-CN、`ja*` → ja）。

---

## 2026.10.11 changelogkit 0.1.7 發佈

**類型**: 功能 · **檔案**: `index.py`、`scanners/javascript.py`、`assets/dev.js`、`assets/dev.css`、`export.py`

### 修改 - API 宣告新增「類別成員」（依縮排收納、可展開）

- **掃描器新增類別成員**：JS/TS 原本只抓 `function`／`export const`，新增抓類別方法（`name(args) {`）；其餘語言本就允許縮排宣告，故成員已被抓到。
- `index._nest()`：依符號所在行的**縮排**把成員收進所屬型別（型別符號帶 `members`，遞迴巢狀）；新增 `iter_symbols()` 走訪全部。
- 型別卡片內新增可展開的「**成員 (N)**」區塊（動態 GUI 與靜態站一致）；成員卡片縮排並以左側 accent 邊條標示。
- **搜尋**會命中成員（資料結構即含 `members`）；**種類篩選**也涵蓋「含有該種類成員的型別」。
- CLI `symbols` 改走 `iter_symbols`，成員可被查詢。
- 實測：TTWChat 的 `WebSocketManager` → 33 個成員、`KickWebSocket` → 5 個（`onAllEvents`…）；全 repo `top-level 1120 / 全部 1753`。

---

## 2026.10.11 changelogkit 0.1.6 發佈

**類型**: 修復 · **檔案**: `assets/dev.js`、`assets/dev.html`、`assets/theme.css`、`assets/file.css`

### 問題 - 符號註釋的程式碼區塊沒被渲染

開發索引頁的 API 註釋（例如 JS 的 JSDoc 內含 ```typescript 範例）會以**純文字**呈現，連 ``` 標記都露出來。

### 根因 - 動態 dev 頁用簡化的 mdDoc，且未載入樣式

`dev.js` 的 `mdDoc` 只處理段落與 `-` 條列，**不支援 ``` 程式碼區塊**；dev 頁也沒有載入 `markdown.js`；而 `.rendered` 的**內容樣式**僅放在 `file.css`（dev 頁未載入）。

### 修改 - 改用完整 markdown 並共用樣式

- `dev.js` 的註釋改用 `window.renderMarkdown`（完整 markdown：程式碼區塊／表格／清單…），wrapper 加上 `.rendered`。
- `dev.html` 載入 `markdown.js`。
- 把 `.rendered` 的**內容樣式**由 `file.css` 移到共用的 `theme.css`（外框版面仍留在 `file.css`）。
- 驗證：TTWChat 的 `KickWebSocket` JSDoc → 已渲染為 `<pre class="code"><code>`（含語法上色），不再出現裸 ```

---

## 2026.10.11 changelogkit 0.1.5 發佈

**類型**: 優化 · **檔案**: `assets/i18n.js`、`assets/theme.css`

### 修改 - 語系切換改為下拉選單

- 頂列 `🌐` 鈕由「**循環切換**」改為「**下拉選單**」：展開列出**全部語系**、目前生效者高亮、點選即切換；點選單外或按 Esc 關閉。語系一多也不必一再點擊輪替。
- 關於頁的語系 chips 仍可直接點選（同一套 `data-locale` 機制）。

---

## 2026.10.11 changelogkit 0.1.4 發佈

**類型**: 功能 · **檔案**: `lang/zh-CN.json`、`lang/ja.json`、`i18n.py`、`assets/i18n.js`、`assets/theme.css`

### 修改 - 新增簡中／日文語系；「UI 語系」改為可點選 chips

- 新增 `lang/zh-CN.json`（簡體）與 `lang/ja.json`（日文），key 與其他語系**完全對齊**（測試把關）。
- 語系判定細分中文：`zh-TW`／`zh-Hant`／`zh-HK`／`zh-MO` → zh-TW，其餘 `zh*` → zh-CN；`ja*` → ja；`<html lang>` 對應 `zh-Hant`／`zh-Hans`。
- 關於頁「UI 語系」由空格串接的長字串改為**可點選的 chips**（自動換行）；點擊即切換語系，目前生效者高亮。避免未來語系變多時擠成一大行。

---

## 2026.10.11 changelogkit 0.1.3 發佈

**類型**: 功能 · **檔案**: `assets/index.html`、`assets/dev.html`、`assets/file.html`、`assets/about.html`、`assets/i18n.js`

### 修改 - 本機 GUI 也能切換語系

- 動態 GUI（變更歷史／開發索引／檔案檢視／關於）頂列新增**語系切換鈕**；頁面內嵌全部語系（`CK_LOCALES`），依 `navigator.language`＋localStorage 選擇（與靜態站相同機制）。
- 動態頁介面文字加 `data-i18n`（含 placeholder 的 `data-i18n-ph`）；切換語系後**重新載入**以重繪 JS 產生的內容。
- `i18n.js`：`CK_setLocale` 僅在**使用者主動切換**時發出 `ck-locale-change`（初始載入不發，避免無限重載）。

---

## 2026.10.11 changelogkit 0.1.2 發佈

**類型**: 功能 · **檔案**: `assets/i18n.js`、`export.py`、`assets/static_about.html`

### 修改 - 靜態站跟隨訪客語系 + 新增「關於」頁

- 前端 i18n 改為**執行期**：頁面內嵌**全部語系**，載入時依 `navigator.language`（＋ localStorage）選擇，右上角新增**語系切換鈕**；不再固定為建置機器（CI＝en）的語系。
- 靜態匯出新增 **about 頁**（`about/`）：顯示 changelogkit 版本、網站來源 commit（連 GitHub）、UI 語系清單；導覽列加「關於」。
- `i18n.subs()` 內嵌 `CK_LOCALES`／`CK_LOCALE`；`STATIC_ASSETS` 納入 `i18n.js`；靜態頁文字加上 `data-i18n`。

---

## 2026.10.11 changelogkit 0.1.1 發佈

**類型**: 功能 · **檔案**: `pyproject.toml`、`src/changelogkit/__init__.py`

### 修改 - 發佈 0.1.1（含建置蓋章）

- `__version__` 改為讀取**安裝中介資料**（單一來源＝`pyproject.toml`），避免版本雙軌。
- 自此版起，**從 PyPI 安裝**的版本 `changelogkit --version` 會附上來源 commit（建置蓋章）。

---

## 2026.10.11 建置蓋章：`--version` 可報來源 commit

**類型**: 功能 · **檔案**: `hatch_build.py`、`src/changelogkit/buildinfo.py`、`.github/workflows/publish.yml`

### 問題 - 從 PyPI 安裝的版本無法得知來源 commit

`--version` 只在「套件目錄是 git checkout」或「pip 記錄了來源目錄（direct_url）」時才報得出 commit；從 PyPI 裝的 wheel 兩者皆無，於是只顯示版本號。

### 根因 - wheel 是自包含的，不帶來源資訊

安裝後既不是 git、也沒有 `direct_url.json`；除非在**建置時**就把 commit 寫進套件，否則安裝端無從得知。

### 修改 - 建置時把 commit 蓋章進套件

- 新增 `hatch_build.py`（hatchling build hook）：打包時將 `COMMIT`／`DIRTY`／`BUILT_AT` 寫入 `src/changelogkit/_buildinfo.py`（列入 `.gitignore`），並以 `force_include` 帶進 wheel（被 gitignore 的檔預設不會納入）。
- `buildinfo.commit()` 優先讀蓋章（`_buildinfo`），其次 git、再次 `direct_url`。
- `publish.yml` 改為**分別從原始碼**建 `--sdist` 與 `--wheel`（`python -m build` 預設會「從 sdist 再建 wheel」，那裡沒有 git，蓋章會是空的）。
- 驗證：本地 wheel 安裝後 `changelogkit --version` → `0.1.0 (1754080)`。

---

## 2026.10.11 changelogkit 0.1.0 首度發佈 PyPI

**類型**: 功能 · **檔案**: `pyproject.toml`、`.github/workflows/publish.yml`

### 修改 - 正式上架 PyPI（Trusted Publishing）

- `pyproject.toml` metadata 收斂：作者由 `ReplyKit` 改為 `TwhomeGH`、補齊 classifiers（12 條）與 `project.urls`。
- PyPI 端設定 pending publisher（OIDC：Owner／Repo／Workflow／Environment）。
- 推 `v0.1.0` tag 觸發 `publish.yml`，以 OIDC 換短效權杖上傳；`python -m build` 與 `twine check` 皆通過。
- 已上架：`changelogkit 0.1.0`（wheel + sdist）。

---

## 2026.10.11 changelogkit 0.1.0 初次抽離

**類型**: 功能 · **檔案**: `src/changelogkit/`

### 修改 - 自 ReplyKit 抽離為通用套件

- `config.py`：以 `.changelog.toml` 提供各 repo 差異（title／history／features／assets／sources）。
- `history.py`／`index.py`／`server.py`／`cli.py`／`assets.py`：移除硬編碼專案路徑。
- 預設網頁資產置於 `src/changelogkit/assets/`，可於設定的 assets 目錄逐一覆寫。
- `publish.yml` 採 PyPI Trusted Publishing（OIDC）。

---

## 2026.10.11 開發索引：近期改動可展開檢視 diff

**類型**: 功能 · **檔案**: `src/changelogkit/index.py`

### 修改 - 結構化提交與 lazy diff

- `git log` 改為結構化提交；新增 `/development/diff` 路由（防注入、防路徑穿越、大小截斷）。
- 前端提交卡片可展開、unified diff 語法上色。

---
