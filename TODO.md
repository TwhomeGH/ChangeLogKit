# TODO — changelogkit 未完成事項

留待日後處理；完成後請刪掉對應條目。`[x]` 已建好、待你推送／設定。

## 已知問題（環境）
- [ ] cp950 Windows 上，對**非 ASCII 路徑**的專案做 `pip install -e` 會寫出含中文的 `.pth`，害 Python 啟動失敗。已在 README 加警告；長解可考慮文件化 `PYTHONUTF8=1` 或推廣 pipx。

## 發佈（PyPI）
- [ ] 取得 PyPI 帳號，並在專案頁設定 **Trusted Publisher**：
  - Owner：`TwhomeGH`、Repository：`ChangeLogKit`、Workflow：`publish.yml`、Environment：`pypi`。
- [ ] 首次發佈 `0.1.0` 以保留 `changelogkit` 名稱（`python -m build` → `twine upload dist/*`）。
- [x] 之後正式發佈走 `.github/workflows/publish.yml`（打 `v*` tag → OIDC Trusted Publishing，**不需 API token**）。
- [ ] 版本升版流程：改 `pyproject.toml` 的 `version` → commit → 打 `vX.Y.Z` tag → push。

## GitHub Actions
- [x] `tests.yml`：push / PR 執行單元測試（Python 3.10 與 3.12）。
- [x] `publish.yml`：tag `v*`（或 GitHub Release）時發佈到 PyPI。
- [ ] （可選）`lint.yml`：ruff / black 檢查。
- [ ] （可選）發佈前檢查 `pyproject.toml` 版本與 git tag 一致。

## 功能／品質
- [ ] 頁面**標題**由 `.changelog.toml` 的 `title` 注入（`index.html` / `dev.html` / `file.html` 加 `{{app_title}}`，server 端 `assets.render`）；目前沿用預設文案。
- [ ] 開發索引「功能與接入」分頁目前欄位**寫死**（ReplayKit／ScreenCaptureKit／前端入口／驗證狀態）；改為依 `features.json` 的 key **通用渲染**（`id`/`name`/`summary` 特例，其餘以 dl 動態列出）。
- [ ] `dev.js` 的檔案連結寫死 `repo=app`（等同預設來源名）；改為由頁面資料帶入主要來源名。
- [ ] 補 `--version` 與更完整的 `--help`。
- [ ] 非 Windows 的啟動腳本（目前多以 `.cmd` 雙擊）。

## 遷移（之後再說）
- [ ] 讓 ReplyKit 的 `Scripts/changelog/` 改用 `changelogkit`（各 repo 加 `.changelog.toml`；刪 vendored 副本或留 3 行薄殼）。
- [ ] 讓 HaishinKit fork 的 `Tools/changelog/` 改用 `changelogkit`。

## 文件
- [ ] README 補「發佈步驟」與「Trusted Publishing 設定」一節。
- [ ] 補 `CHANGELOG.md` 記錄工具自身版本。

## GitHub Pages（唯讀靜態匯出）
- [x] `changelogkit export <OUT>`：產生可部署到 Pages 的唯讀靜態站（**預先渲染 HTML**，非改寫 SPA）。
  - 複製資產並以相對路徑引用（`assets/...`）。
  - 變更歷史頁：靜態渲染，內文 markdown 由前端 `markdown.js` 就地渲染。
  - 開發索引：預先渲染 symbols／documents／repos；每個提交的 diff 內嵌於 `<details>`（前端 `highlight.js` 上色）；檔案連結指向 GitHub blob。
- [x] `.github/workflows/pages.yml`：push main → `changelogkit export _site` → `configure-pages` / `upload-pages-artifact` / `deploy-pages`。
- [ ] 啟用 Pages：repo Settings → Pages → Source = **GitHub Actions**。
- [ ] 限制：靜態站為**唯讀**——沒有新增／編輯紀錄、沒有即時檔案檢視、沒有 lazy diff（這些需要本機 server）。
