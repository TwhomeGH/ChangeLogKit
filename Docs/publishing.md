# PyPI 發佈

採 **Trusted Publishing（OIDC）**，**不需要 API token**。`publish.yml` 已備好 `permissions: id-token: write` 與 `environment: pypi`。

## 一次性設定

1. 註冊 PyPI 帳號並開啟 2FA。
2. PyPI → 右上 **Publishing → Add a pending publisher**，填：

   | 欄位 | 值 |
   | --- | --- |
   | PyPI Project Name | `changelogkit` |
   | Owner | `TwhomeGH` |
   | Repository | `ChangeLogKit` |
   | Workflow name | `publish.yml` |
   | Environment | `pypi` |

## 發佈

```bash
git tag v0.1.0
git push origin v0.1.0
```

→ `.github/workflows/publish.yml` 觸發，以 OIDC 換取短效權杖並上傳。發佈後 pending publisher 會轉為正式。

> **建置蓋章**：workflow 會分別從原始碼建 `--sdist` 與 `--wheel`（不是預設的「sdist → wheel」，因為那條路徑沒有 git）。`hatch_build.py` 會在打包時把來源 `COMMIT`／`DIRTY`／`BUILT_AT` 寫進 `changelogkit/_buildinfo.py`，所以從 PyPI 安裝的版本 `changelogkit --version` 也會顯示來源 commit。

## 手動（備用）

```bash
pip install -U build twine
python -m build
twine upload dist/*        # 帳號填 __token__、密碼貼 API token
```

名稱在**第一次上傳**時被佔用、之後不可改。

## TestPyPI（建議先試一輪）

到 [test.pypi.org](https://test.pypi.org) 設同樣的 publisher，再：

```bash
twine upload --repository testpypi dist/*
```

先確認 **metadata／README 在專案頁顯示正常**，再發正式站。

## 版本流程

1. 改 `pyproject.toml` 的 `version`。
2. commit。
3. `git tag vX.Y.Z && git push origin vX.Y.Z`。
