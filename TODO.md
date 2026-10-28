# TODO — changelogkit 未完成事項

留待日後處理；完成後請刪掉對應條目。

## 文件分類／靜態站（2C）

- [ ] 每語系群組標題／備註：`[[tool.changelog.docs.groups]]` 的 `title`／`note` 支援 `{ "zh-TW" = "...", en = "..." }`；動態頁依 UI 語系、靜態頁依 `--locale` 解析。
- [ ] 靜態站文件搜尋：首頁或文件頁加 client-side filter（標題／路徑／備註）；目前只有動態開發索引有搜尋與群組 chips。
- [ ] `symbols.html` lazy：VideoServer 約 352 KB；依語言／資料夾 `<details>` 或分頁。
- [ ] 多來源同名文件：`doc_pages` 與文件頁 URL 目前只用 repo 內相對路徑當 key；兩個 source 有同名文件會碰撞，需把 source 納入 key／路徑（連帶改 `markdownResolver`）。
- [ ] 目錄層級：目前只收 h2–h3；若要 h4，加「更多」折疊。

## 已知問題（環境）

- [ ] cp950 Windows 上，對**非 ASCII 路徑**的專案做 `pip install -e` 會寫出含中文的 `.pth`，害 Python 啟動失敗。已文件化 `PYTHONUTF8=1`／pipx，並提供 `tools/dev.py` 避開 editable install；長期可推廣 pipx。

## 功能／品質

- [ ] `.d.ts` 與 `.js` 的**卡片去重**（同一模組常有兩份：型別宣告 + 實作；可偏好 `.d.ts`）。跨檔案比對，較複雜。
- [ ] 「已安裝套件」檢視（讀 `package.json` dependencies → 解析 `types`／`exports` 型別入口）——**暫不做**，改用 `.changelog.toml` 的 `include` 納入 `.d.ts`。

## GitHub Actions

- [ ] （可選）`lint.yml`：ruff / black 檢查。
- [ ] （可選）發佈前檢查 `pyproject.toml` 版本與 git tag 一致。

## 遷移（之後再說）

- [ ] 讓 ReplyKit 的 `Scripts/changelog/` 改用 `changelogkit`（各 repo 加 `.changelog.toml`；刪 vendored 副本或留薄殼）。
- [ ] 讓 HaishinKit fork 的 `Tools/changelog/` 改用 `changelogkit`。

## 文件

- [ ] 補 `CHANGELOG.md` 記錄工具自身版本（目前以 `Docs/ChangeHistory.md` 代替）。

## 已完成（供對照）

- [x] PyPI Trusted Publisher 設定與持續發佈（`publish.yml`，OIDC；目前 `0.10.0`）。
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
