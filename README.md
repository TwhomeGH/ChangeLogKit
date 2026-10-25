# changelogkit

本機（開發機）用的兩合一工具，與特定 repo 解耦：

- **變更歷史 GUI**：解析 `Docs/ChangeHistory.md`（路徑可設定），提供網頁瀏覽／新增／編輯與 CLI 檢索。
- **開發索引**：唯讀索引 Git 近期改動（提交可展開看 unified diff，含語法上色）、Swift 宣告定位、Markdown 文件與鎖定套件。

不需要 Xcode；只要開發機有 Python 3.10+ 與 `git`。

## 安裝

```bash
pipx install changelogkit          # 建議：隔離安裝並提供全域指令
# 或
pip install changelogkit
```

## 在 PyPI 上線前如何使用

套件尚未發佈到 PyPI 時，有三種本機用法（擇一）。以下把 `<ChangeLogTools>` 換成套件所在目錄。

### 1. 零安裝（最快；改程式即時生效）

用**絕對路徑**的 `PYTHONPATH` 指向套件的 `src/`，即可在任何 repo 內執行：

```powershell
$env:PYTHONPATH = "<ChangeLogTools>\src"     # PowerShell；路徑要用絕對路徑
cd D:\某個repo
python -m changelogkit serve --no-browser
python -m changelogkit list
```

（可在該 repo 放一個薄殼 `change_log.cmd` 包住上述指令，之後雙擊即可。）

### 2. 可編輯安裝（開發套件本身）

```powershell
cd <ChangeLogTools>
pip install -e .
changelogkit serve
```

> ⚠️ **路徑含非 ASCII 字元時不要用 `-e`。** 若套件放在像 `…\桌面\…` 這種路徑，editable 安裝會寫出含中文路徑的 `.pth`；在 **cp950（繁體中文）語系的 Windows** 上，Python 以 locale 讀 `.pth` 會 `UnicodeDecodeError`，害**任何 `python`／`pip` 指令都啟動不了**（`Fatal Python error: init_import_site`）。
> 解法：刪掉那個 `.pth` 後改用一般安裝 `pip install <ChangeLogTools>`（複製進 site-packages，不產生 `.pth`）或第 3 種 pipx；也可先 `set PYTHONUTF8=1`。

### 3. 全域 CLI、又保持隔離（推薦）

```powershell
pipx install <ChangeLogTools>
# 之後更新程式：
pipx install --force <ChangeLogTools>
# 或直接從 git（不經 PyPI）：
pipx install git+https://github.com/TwhomeGH/ChangeLogKit.git
```

### 驗證「使用者真正拿到的成品」

```powershell
python -m build
python -m venv .venv
.\.venv\Scripts\pip install dist\changelogkit-0.1.0-py3-none-any.whl
.\.venv\Scripts\changelogkit --help
```

## 使用

在任何 repo 目錄下執行：

```bash
changelogkit                 # 等同 serve：啟動本機網頁 GUI
changelogkit serve --port 8710 --no-browser
changelogkit add "修正 XXX" --type 修復 --file a/b.swift \
    --problem "症狀" --cause "根因" --change "核心改動"
changelogkit list --grep RTMP
changelogkit show 3
```

網頁 GUI：`/` 為變更歷史，`/development` 為開發索引（功能／API 宣告／文件／近期改動）。

## 設定：`.changelog.toml`

放在 repo 根目錄（工具會從工作目錄往上尋找；找不到就用預設值）：

```toml
[tool.changelog]
title    = "ReplyKit 變更歷史"                    # 網頁標題
history  = "Docs/ChangeHistory.md"               # 變更歷史 markdown
features = "Docs/development/features.json"      # 選填：功能清單
assets   = "Scripts/changelog-overrides"         # 選填：覆寫預設網頁資產

[[tool.changelog.sources]]                       # 開發索引要一起看的 repo（預設只有自己）
name = "app"
path = "."
[[tool.changelog.sources]]
name = "haishinkit"
path = "${HAISHINKIT_ROOT}"                      # 支援環境變數；不存在就略過
```

未設定時預設：`history = Docs/ChangeHistory.md`、`features = Docs/development/features.json`、
`title = <repo 目錄名>`、單一來源（自己）。`path` 支援 `${ENV}` 展開。

### 覆寫網頁資產

`assets` 指向一個目錄；載入資產時**先找該目錄的同名檔，找不到才用套件預設**。因此可以：

- 只放 `theme.css` → 只換配色；
- 放整套 `index.*`／`dev.*`／`file.*` → 整包換掉版面。

## 文件

- [安裝與本地使用](Docs/install.md)：三種裝法、cp950／中文路徑地雷、解除安裝
- [用法](Docs/usage.md)：指令、`.changelog.toml` 全欄位、資產覆寫、變更歷史格式
- [GitHub Pages](Docs/pages.md)：靜態匯出的產物、限制與啟用方式
- [PyPI 發佈](Docs/publishing.md)：Trusted Publishing 設定與版本流程
- [架構](Docs/architecture.md)：模組結構與設計要點

## 開發

```bash
pip install -e .
python tests/test_changelogkit.py
```

網頁資產在 `src/changelogkit/assets/`，改版面／配色只需動這些檔案，不必改 Python。
