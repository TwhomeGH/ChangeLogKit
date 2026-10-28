# 安裝與本地使用

只要開發機有 **Python 3.10+** 與 **git** 即可（不需要 Xcode／Node）。

PyPI 上線前，用以下任一方式在本機使用。

## 1. 零安裝（最快、改程式即時生效）

用**絕對路徑**的 `PYTHONPATH` 指向套件的 `src/`，即可在任何 repo 內執行：

```powershell
$env:PYTHONPATH = "<ChangeLogTools>\src"    # 要絕對路徑
cd D:\某個repo
python -m changelogkit serve --no-browser
python -m changelogkit list
```

可在常看的 repo 放一個薄殼 `change_log.cmd` 包住上述指令，之後雙擊即可。

## 2. 一般安裝（複製進 site-packages）

```powershell
python -m pip install "<ChangeLogTools>"
changelogkit list
```

- 用 **`python -m pip`**（不要只用 `pip`）：多版本 Python 時兩者可能指向不同環境。
- 之後更新：重新 `python -m pip install --force-reinstall "<ChangeLogTools>"`。
- 移除：`python -m pip uninstall changelogkit`。

## 3. pipx（隔離、全域 CLI，推薦）

```powershell
python -m pip install --user pipx
python -m pipx ensurepath          # 把 pipx 的 bin 目錄加進 PATH
# ── 關掉並重開終端機 ──
pipx install "<ChangeLogTools>"     # 或：pipx install git+https://github.com/TwhomeGH/ChangeLogKit.git
changelogkit --help
```

`pipx` 會為套件建獨立 venv（在 `%USERPROFILE%\.local`，純 ASCII 路徑）並公開 `changelogkit` 指令，不污染其他環境。更新：`pipx install --force "<ChangeLogTools>"`。

## 驗證「使用者真正拿到的成品」

```powershell
python -m build
python -m venv .venv
.\.venv\Scripts\pip install dist\changelogkit-0.1.0-py3-none-any.whl
.\.venv\Scripts\changelogkit --help
```

## ⚠️ 地雷：中文路徑 + `pip install -e`

**不要對「路徑含非 ASCII 字元」的專案做 editable 安裝。** 例如套件放在 `…\桌面\ChangeLogTools`：

- `pip install -e` 會產生 `_editable_impl_changelogkit.pth`，內容是含中文的 **UTF-8** 路徑。
- 在 **cp950（繁體中文）語系的 Windows**，Python 的 `site.py` 以 **locale** 讀 `.pth` → `UnicodeDecodeError`。
- 後果是**任何 `python`／`pip`／console script 都啟動不了**（`Fatal Python error: init_import_site`）。

### 解法（任一）

1. 刪掉那個 `.pth` 後改用**一般安裝**（`pip install "<ChangeLogTools>"`）或 **pipx**（都不產生 `.pth`）。
2. 安裝前先 `set PYTHONUTF8=1`（讓 Python 以 UTF-8 讀 `.pth`）。
3. 把專案移到**純英文路徑**再用 `-e`。

## 解除安裝

```powershell
python -m pip uninstall changelogkit     # 或：pipx uninstall changelogkit
```
