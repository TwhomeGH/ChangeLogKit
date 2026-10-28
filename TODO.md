# TODO — changelogkit 未完成事項

留待日後處理；完成後請刪掉對應條目。

## 已知問題（環境）

- [ ] cp950 Windows 上，對**非 ASCII 路徑**的專案做 `pip install -e` 會寫出含中文的 `.pth`，害 Python 啟動失敗。已文件化 `PYTHONUTF8=1`／pipx，並提供 `tools/dev.py` 避開 editable install；長期可推廣 pipx。

## 功能／品質

- [ ] 「已安裝套件」檢視（讀 `package.json` dependencies → 解析 `types`／`exports` 型別入口）——**暫不做**，改用 `.changelog.toml` 的 `include` 納入 `.d.ts`。

## 遷移（之後再說）

- [ ] 讓 ReplyKit 的 `Scripts/changelog/` 改用 `changelogkit`（各 repo 加 `.changelog.toml`；刪 vendored 副本或留薄殼）。
- [ ] 讓 HaishinKit fork 的 `Tools/changelog/` 改用 `changelogkit`。

## 已完成（供對照）

- [x] PyPI Trusted Publisher 設定與持續發佈（`publish.yml`，OIDC；目前 `0.11.0`）。
- [x] 建置時蓋章 `_buildinfo.py`（hatch build hook）：`--version` 可報來源 commit；原始碼 checkout 優先 git HEAD。
- [x] 本機 GUI「關於」頁（版本／來源 commit／UI 語系）。
- [x] GitHub Pages 唯讀靜態匯出與部署（`export` + `pages.yml`；Pages Source = GitHub Actions）。
- [x] 多語系（zh-TW／zh-CN／ja／en）＋執行期跟隨瀏覽器偏好＋下拉切換。
- [x] API 宣告多語言掃描（11 種）＋語言／種類篩選＋**類別成員收納**＋**`.d.ts` 正確解析**。
- [x] 頁面標題由 `.changelog.toml` 的 `title` 注入；功能分頁依 `features.json` 通用渲染。
- [x] `.gitattributes` 統一換行為 LF。
- [x] 語言感知語法上色（PowerShell `#` 註釋、URL 不誤判；0.7.4）。
- [x] CLI `add` 可帶 `--problem`／`--cause`／`--change`（0.7.5）。
- [x] 文件分類：群組／顏色／備註＋資料夾自動 fallback（0.8.0）。
- [x] 靜態站三頁化、穩定文件 URL、文件頁 TOC（sticky／手機抽屜／scroll-spy；0.9.0）。
- [x] `docs --check`／`docs-init`、Documents 群組 chips（0.10.0）。
- [x] 跨平台開發啟動器 `tools/dev.py`（`dev.ps1` 僅 Windows 外殼）；`--help`／`--` 轉發子命令說明。
- [x] 靜態 `repos.html` 改為每筆 commit 一頁（`development/commits/<repo>/<hash>.html`），列表不再內嵌 diff。
- [x] `dev.js` 功能檔案連結改用 `contexts.features.repo`，不再寫死 `repo=app`。
- [x] 近期改動上限可用 `recent_commits` 設定（1–200）；靜態 repos 頁提供「更舊的提交 → GitHub／變更歷史」。
- [x] 每語系群組標題／備註（groups／entries；動態依 UI 語系、靜態依 `--locale`）。
- [x] 靜態首頁文件搜尋（標題／路徑／備註／摘要；過濾群組並更新數量）。
- [x] `symbols.html` 依檔案 `<details>` 折疊；展開時才上色／渲染註釋，附展開／收合全部。
- [x] 多來源同名文件：文件頁改為 `docs/<來源>/<路徑>.html`，`doc_pages` 以 `來源:路徑` 為 key；`sources.path` 相對 repo 根目錄解析。
- [x] 文件目錄收 h2–h4（h4 縮排）；動態與靜態共用。
- [x] `.d.ts` 與同目錄同名 `.js`／`.mjs`／`.cjs` 的同名同種類卡片只留 `.d.ts`。
- [x] `lint.yml`：ruff check＋format check；`pyproject.toml` 加 `dev` extra 與 ruff 設定。
- [x] 發版前檢查 `pyproject.toml` 版本、`__init__` fallback 與 git tag 一致（`tools/check_version.py`；publish workflow 執行）。
- [x] 工具自身 changelog 移至根目錄 `CHANGELOG.md`（單一來源；`.changelog.toml` 指向它）。
