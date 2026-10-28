# 範例 repo

把這個目錄當成一個獨立 repo 的縮影，示範 `changelogkit` 需要的檔案與設定：

```text
repo/
  .changelog.toml                 # 設定（可省略，用預設值）
  Docs/ChangeHistory.md           # 變更歷史（必要）
  Docs/development/features.json  # 功能清單（選填）
  Sources/Sample.swift            # 被索引的原始碼（開發索引用）
```

試跑（先 `pip install -e ..`，或在 repo 內設定 `PYTHONPATH` 指向套件的 `src`）：

```bash
cd examples/repo
changelogkit serve --no-browser      # 開 / 與 /development
changelogkit list
```

複製 `.changelog.toml` 到你的專案根目錄，再依需要調整 `title` / `history` /
`features` / `assets` / `sources` 即可。
