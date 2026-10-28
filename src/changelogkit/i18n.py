"""極簡 i18n：語系檔為 ``lang/<locale>.json``（key → 字串）。

語系解析順序：``--lang``（由 :func:`set_language` 設定）→ 環境變數
（``LC_ALL``／``LC_MESSAGES``／``LANG``／``LANGUAGE``）→ 系統預設；判定為非中文時
一律回退 ``en``。查表缺 key 時依序回退 ``en`` → key 本身，避免程式因缺字串而壞掉。
"""

import json
import os
import warnings
from pathlib import Path

LANG_DIR = Path(__file__).resolve().parent / "lang"
SUPPORTED = ("zh-TW", "zh-CN", "ja", "en")
_current = None
_cache = {}


def _catalog(locale):
    """載入（並快取）某語系的字典；讀不到就回空字典。"""
    if locale not in _cache:
        try:
            _cache[locale] = json.loads((LANG_DIR / (locale + ".json")).read_text(encoding="utf-8"))
        except (OSError, ValueError):
            _cache[locale] = {}
    return _cache[locale]


def _system_locale():
    """由環境變數或系統預設取得語系字串（可能為空）。"""
    for var in ("LC_ALL", "LC_MESSAGES", "LANG", "LANGUAGE"):
        value = os.environ.get(var)
        if value:
            return value
    try:
        import locale as _locale

        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            return _locale.getdefaultlocale()[0] or ""
    except Exception:
        return ""


def resolve_locale():
    """依 --lang／環境變數／系統預設決定語系；找不到對應語系檔則回退 ``en``。"""
    name = _system_locale().lower()
    guess = "en"
    if name.startswith("zh"):
        guess = "zh-TW" if any(tag in name for tag in ("tw", "hk", "mo", "hant")) else "zh-CN"
    elif name.startswith("ja"):
        guess = "ja"
    return guess if guess == "en" or guess in available() else "en"


def set_language(locale):
    """由 ``--lang`` 指定語系（None／空字串表示自動）。"""
    global _current
    _current = locale or None


def available():
    """可用語系（``lang/*.json`` 檔名，排序）。"""
    try:
        names = sorted(p.stem for p in LANG_DIR.glob("*.json"))
    except OSError:
        names = []
    return names or list(SUPPORTED)


def current():
    """目前生效的語系。"""
    return _current or resolve_locale()


def t(key, **fmt):
    """查表取字串；缺 key 回退 en，再不行回 key 本身。"""
    text = _catalog(current()).get(key) or _catalog("en").get(key) or key
    return text.format(**fmt) if fmt else text


def _merged():
    """合併語系（en 為底、現行語系覆蓋）以確保每個 key 都有值。"""
    catalog = dict(_catalog("en"))
    catalog.update(_catalog(current()))
    return catalog


def all_catalogs():
    """所有語系的完整字典（``en`` 為底、各語系覆蓋），供前端執行期切換。"""
    base = _catalog("en")
    out = {}
    for name in available():
        merged = dict(base)
        merged.update(_catalog(name))
        out[name] = merged
    return out


def _embed(data):
    """序列化成可安全放進 ``<script>`` 的 JSON（轉義 ``<``）。"""
    return json.dumps(data, ensure_ascii=False).replace("<", "\\u003c")


def subs():
    """供網頁模板的 ``{{…}}`` 佔位替換。

    提供 ``t.<key>``（目前語系的字串）、``lang_html``（``<html lang>``），以及前端
    執行期 i18n 所需的 ``CK_LOCALES``（全部語系）與 ``CK_LOCALE``（目前語系）。
    """
    result = {"t." + key: value for key, value in _merged().items()}
    low = current().lower()
    if low.startswith("zh"):
        result["lang_html"] = "zh-Hant" if any(t in low for t in ("tw", "hk", "mo", "hant")) else "zh-Hans"
    else:
        result["lang_html"] = current()
    result["CK_LOCALES"] = _embed(all_catalogs())
    result["CK_LOCALE"] = current()
    return result


def js_dict():
    """供前端 ``window.CK_I18N`` 的字典（全部 key）。"""
    return _merged()
