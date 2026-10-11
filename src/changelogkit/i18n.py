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
SUPPORTED = ("zh-TW", "en")
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
    """依 --lang／環境變數／系統預設決定語系；非中文回退 ``en``。"""
    name = _system_locale().lower()
    return "zh-TW" if name.startswith("zh") else "en"


def set_language(locale):
    """由 ``--lang`` 指定語系（None／空字串表示自動）。"""
    global _current
    _current = locale or None


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


def subs():
    """供網頁模板的 ``{{t.<key>}}`` 佔位替換（另附 ``lang_html``）。"""
    result = {"t." + key: value for key, value in _merged().items()}
    result["lang_html"] = "zh-Hant" if current().lower().startswith("zh") else "en"
    return result


def js_dict():
    """供前端 ``window.CK_I18N`` 的字典（全部 key）。"""
    return _merged()
