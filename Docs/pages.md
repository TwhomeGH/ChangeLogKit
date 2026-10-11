# GitHub Pages 靜態匯出

工具本體是**本機 server**（要跑 `git`、處理 POST 編輯、即時查詢）；GitHub Pages 只能放靜態檔，因此提供 **`changelogkit export`** 產生一份**唯讀**快照。

## 產出

```bash
changelogkit export _site --branch main
```

```
_site/
  index.html              # 變更歷史（唯讀）
  development/index.html  # 開發索引（API 宣告／文件／近期改動）
  docs/<i>.html           # 每份 Markdown 的檢視頁
  assets/…                # 網頁資產（相對路徑引用）
  .nojekyll
```

- 變更歷史：逐筆呈現，內文由前端 `markdown.js` 就地渲染。
- 開發索引：每個提交的 diff **內嵌**於 `<details>`（前端 `highlight.js` 上色）；檔案連結指向 **GitHub blob**（由 origin remote 推得）。
- 全部用**相對路徑**，所以能在 `https://<owner>.github.io/<repo>/` 這類子路徑下運作。
- 深／淺色可切換（`theme.js`；預設跟隨系統）。

## 限制（唯讀）

靜態站**沒有**：新增／編輯紀錄、即時檔案檢視、lazy 抓 diff。需要這些請在本機跑 `changelogkit serve`。

## 自動部署

`.github/workflows/pages.yml`：push 到 `main`（或手動觸發）→ `pip install -e .` → `changelogkit export _site` → 部署 Pages。

- workflow 用 `actions/checkout` 的 `fetch-depth: 0`（列 commits／diff 需要完整歷史）。
- **啟用**：repo Settings → Pages → **Source = GitHub Actions**。
- 首次部署後網址為 `https://<owner>.github.io/<repo>/`。
