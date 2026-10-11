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
