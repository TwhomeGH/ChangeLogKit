# TODO — changelogkit 未完成事項

留待日後處理；完成後請刪掉對應條目。

## 已知問題（環境）

- [ ] cp950 Windows 上，對**非 ASCII 路徑**的專案做 `pip install -e` 會寫出含中文的 `.pth`，害 Python 啟動失敗。已在 README 加警告；長解可考慮文件化 `PYTHONUTF8=1` 或推廣 pipx。

## 功能／品質

- [ ] `dev.js` 的檔案連結寫死 `repo=app`（等同預設來源名）；改為由頁面資料帶入主要來源名。
- [ ] `.d.ts` 與 `.js` 的**卡片去重**（同一模組常有兩份：型別宣告 + 實作；可偏好 `.d.ts`）。跨檔案比對，較複雜。
- [ ] 「已安裝套件」檢視（讀 `package.json` dependencies → 解析 `types`／`exports` 型別入口）——**暫不做**，改用 `.changelog.toml` 的 `include` 納入 `.d.ts`。
- [ ] 非 Windows 的啟動腳本（目前多以 `.cmd` 雙擊）。

## GitHub Actions

- [ ] （可選）`lint.yml`：ruff / black 檢查。
- [ ] （可選）發佈前檢查 `pyproject.toml` 版本與 git tag 一致。

## 遷移（之後再說）

- [ ] 讓 ReplyKit 的 `Scripts/changelog/` 改用 `changelogkit`（各 repo 加 `.changelog.toml`；刪 vendored 副本或留薄殼）。
- [ ] 讓 HaishinKit fork 的 `Tools/changelog/` 改用 `changelogkit`。

## 文件

- [ ] 補 `CHANGELOG.md` 記錄工具自身版本（目前以 `Docs/ChangeHistory.md` 代替）。

## 已完成（供對照）

- [x] PyPI Trusted Publisher 設定與持續發佈（`publish.yml`，OIDC；目前 `0.1.9`）。
- [x] 建置時蓋章 `_buildinfo.py`（hatch build hook）：`--version` 可報來源 commit。
- [x] 本機 GUI「關於」頁（版本／來源 commit／UI 語系）。
- [x] GitHub Pages 唯讀靜態匯出與部署（`export` 子命令 + `pages.yml`；Pages Source = GitHub Actions）。
- [x] 多語系（zh-TW／zh-CN／ja／en）＋執行期跟隨瀏覽器偏好＋下拉切換。
- [x] API 宣告多語言掃描（11 種）＋語言／種類篩選＋**類別成員收納**＋**`.d.ts` 正確解析**。
- [x] 頁面標題由 `.changelog.toml` 的 `title` 注入；功能分頁依 `features.json` 通用渲染。
- [x] `.gitattributes` 統一換行為 LF。
