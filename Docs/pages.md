# GitHub Pages 靜態匯出

工具本體是**本機 server**（要跑 `git`、處理 POST 編輯、即時查詢）；GitHub Pages 只能放靜態檔，因此提供 **`changelogkit export`** 產生一份**唯讀**快照。

## 產出

```bash
changelogkit export _site --branch main
```

```text
_site/
  index.html                    # 變更歷史（唯讀）
  development/index.html        # 文件＋功能
  development/symbols.html      # API 宣告
  development/repos.html        # 近期改動列表
  development/commits/…         # 單筆 commit 的完整 diff
  development/todo.html         # 待辦快照（有 TODO 檔時）
  docs/<來源>/<路徑>.html       # 每份 Markdown 的檢視頁
  about/index.html              # 關於頁
  assets/…                      # 網頁資產（相對路徑引用）
  api-docs/<mount>/…            # 選配：embed 的 API 文件
  .nojekyll
```

- 變更歷史：逐筆呈現，內文由前端 `markdown.js` 就地渲染。
- 開發索引：每個提交的 diff 放在**獨立頁面**（`development/commits/<repo>/<hash>.html`），列表頁只留摘要；展開／閱讀時才載入上色。
- 文件頁使用穩定路徑 `docs/<來源>/<repo 內原路徑>.html`；群組、備註與 TOC 都在匯出時寫入。
- 全部用**相對路徑**，所以能在 `https://<owner>.github.io/<repo>/` 這類子路徑下運作。
- 深／淺色可切換（`theme.js`；預設跟隨系統）。

## 限制（唯讀）

靜態站**沒有**：新增／編輯紀錄、即時檔案檢視、lazy 抓 diff。需要這些請在本機跑 `changelogkit serve`。

## 自動部署

`.github/workflows/pages.yml` 的目標流程：push 到預設分支（或手動觸發）→ 安裝 changelogkit → `changelogkit export _site --branch <分支>` → 部署 Pages。

- workflow 用 `actions/checkout` 的 `fetch-depth: 0`（列 commits／diff 需要完整歷史）。
- 目標 repo 建議安裝最新 tag（`pip install "git+https://github.com/TwhomeGH/ChangeLogKit.git@<tag>"`）；工具自身 repo 可用 `pip install -e .`。
- **啟用**：repo Settings → Pages → **Source = GitHub Actions**。
- 首次部署後網址為 `https://<owner>.github.io/<repo>/`。

## 快取與增量（CI）

GitHub Pages 的部署 artifact **每次都是完整上傳**；`actions/cache` 不會讓 `deploy-pages` 只傳差異。快取只能降低「建置」時間，不能降低 Pages 端的完整 artifact 體積。

目前 `export` 是**完整重建**：先清空輸出目錄，再寫入所有頁面；這是最安全、最不容易留下舊檔的模式。要降低 CI 成本，建議依序做：

1. **先量測** workflow 各步驟時間（尤其 `export`、Doxygen、artifact upload），不要憑感覺加快取。
2. **快取工具與相依**：`setup-python` 的 pip 快取、固定 `CHANGELOGKIT_REF` tag、快取 `build/doxygen/html`（key 用 `Doxyfile` 與標頭檔 hash）。Doxygen 輸出常比重新安裝快。
3. **避免重複複製 API 產物**：`embed = true` 會把整個 Doxygen HTML（可達數十 MB）複製進 `_site`。如果 API 站可獨立託管，優先用 `url` 外連；否則把 Doxygen 輸出直接放到最終站內，避免「產生一次、再複製一次」。
4. **要快取 `_site` 前，先讓輸出可重現**：`export` 的頁尾時間可用 `SOURCE_DATE_EPOCH` 固定（例如設為來源 commit 時間），否則每次產物都不同。還需要一份 manifest 記錄「輸入 → 輸出」，才能安全跳過未變更頁面並刪除已移除的文件；只還原整個 `_site` 而不清理，會留下已刪除的文件頁。
5. **增量匯出**（尚未內建）應是 opt-in：先寫 manifest、比對輸入 hash、只重建變更的文件／歷史／commit 頁，最後只刪除 manifest 有記錄且本次不再產生的檔案；預設仍保留完整清理模式。

> 目前不建議直接把 `_site` 當 GitHub Actions cache：`export` 會先清空輸出，且沒有 manifest 與穩定的頁尾時間，還原快取不會帶來正確的增量效果。
