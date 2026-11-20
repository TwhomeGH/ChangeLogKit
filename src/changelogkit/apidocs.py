"""選填的外部 API 文件站：導覽、掛載與靜態複製。

核心刻意不解析 Doxygen／Sphinx／DocC 的符號格式；這一層只處理「一個
HTML 目錄或一個外部 URL」。之後的深連結 adapter 再依 ``kind`` 擴充。
"""

import html
import shutil
from pathlib import Path

from . import i18n


def _esc(value):
    return html.escape(str(value or ""), quote=True)


def title(doc):
    """取得 API 文件站標題；支援 ``title`` 語系對照表。"""
    value = doc.title
    if isinstance(value, dict):
        current = i18n.current()
        return value.get(current) or value.get("en") or next(iter(value.values()), doc.id)
    return str(value or doc.id)


def href(doc, base=""):
    """導覽連結：外部 ``url`` 優先，其次站內掛載路徑。

    相對 ``url`` 也要接上目前頁面的站根前綴，否則巢狀文件頁會指錯位置。
    """
    if doc.url:
        if doc.url.startswith(("http://", "https://", "//", "/", "#")):
            return doc.url
        return base + doc.url
    return "%sapi-docs/%s/" % (base, doc.mount)


def nav_html(docs, base=""):
    """產生導覽列 HTML；單一項目顯示標題，多個項目收成下拉。"""
    docs = list(docs or [])
    if not docs:
        return ""
    links = []
    for doc in docs:
        external = doc.url.startswith(("http://", "https://", "//"))
        attrs = ' target="_blank" rel="noopener"' if external else ""
        links.append('<a href="%s"%s>%s</a>' % (_esc(href(doc, base)), attrs, _esc(title(doc))))
    if len(links) == 1:
        return links[0]
    return (
        '<details class="navdrop"><summary data-i18n="nav.api">%s</summary>'
        '<div class="navdrop-menu">%s</div></details>' % (_esc(i18n.t("nav.api")), "".join(links))
    )


def static_docs(docs):
    """靜態站可用的項目：外部 URL，或已允許複製且確實有 HTML 目錄。"""
    return [doc for doc in (docs or []) if doc.url or (doc.embed and doc.html and doc.html.is_dir())]


def resolve_asset(doc, rel):
    """安全解析 API 文件目錄內的相對檔案；逃逸或非檔案回傳 ``None``。"""
    if not doc.html:
        return None
    try:
        root = doc.html.resolve()
        target = (root / rel).resolve()
    except (OSError, RuntimeError, ValueError):
        return None
    if not target.is_relative_to(root) or not target.is_file():
        return None
    return target


def assert_export_safe(cfg, out):
    """拒絕把 API 產物放在會被匯出流程刪除／覆蓋的位置。"""
    out = Path(out).resolve()
    for doc in cfg.api:
        if not doc.html:
            continue
        source = doc.html.resolve()
        if source == out or source.is_relative_to(out) or out.is_relative_to(source):
            raise ValueError("API 文件 html 不可位於匯出目錄內：%s（請改到獨立目錄）" % source)


def copy_provider(doc, out):
    """把一個 API HTML 目錄複製到 ``out/api-docs/<mount>``。"""
    if not doc.embed or not doc.html or not doc.html.is_dir():
        return False
    source = doc.html.resolve()
    destination = (Path(out) / "api-docs" / doc.mount).resolve()
    if destination.is_relative_to(source) or source.is_relative_to(destination):
        raise ValueError("API 文件來源與複製目的地重疊：%s" % source)
    destination.parent.mkdir(parents=True, exist_ok=True)
    if destination.exists():
        shutil.rmtree(destination)
    shutil.copytree(source, destination)
    return True
