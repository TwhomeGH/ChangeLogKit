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
