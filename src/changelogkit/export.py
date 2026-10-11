"""靜態匯出：把本機工具產生為可部署到 GitHub Pages 的**唯讀**靜態站。

動態功能（新增／編輯紀錄、即時檔案檢視、lazy 抓 diff）都需要本機 server，靜態站
只提供瀏覽：

* 變更歷史：逐筆呈現，內文 markdown 由前端 ``markdown.js`` 就地渲染。
* 開發索引：列出功能／API 宣告／文件／近期改動；每個提交的 unified diff **直接
  內嵌**於 ``<details>``（免 server）；檔案連結指向 GitHub blob（由 origin remote 推得）。

輸出為純靜態檔，可直接丟到 GitHub Pages（含 ``.nojekyll``）。
"""

import html
import re
import shutil
import subprocess
from datetime import datetime
from pathlib import Path

from . import assets, buildinfo, config, history, i18n, index

# 需要複製到輸出 assets/ 的檔案（其餘為 server 動態用，不需要）。
STATIC_ASSETS = ("theme.css", "theme.js", "i18n.js", "dev.css", "file.css", "highlight.js", "markdown.js")


def _esc(text):
    """HTML 轉義（None 視為空字串）。"""
    return html.escape(str(text if text is not None else ""))


def _diff_class(line):
    """移植 ``assets/dev.js`` 的 diffLineClass：決定單行樣式類別。"""
    if line.startswith("@@"):
        return "d-hunk"
    if line.startswith(("+++", "---", "diff --git")):
        return "d-file"
    if line.startswith("+"):
        return "d-add"
    if line.startswith("-"):
        return "d-del"
    if line.startswith(("index ", "new file", "deleted file", "similarity", "rename ",
                        "old mode", "new mode", "Binary files", "\\ No newline")):
        return "d-meta"
    if line.startswith(" "):
        return "d-ctx"
    return "d-plain"


def _diff_html(text):
    """unified diff → ``<pre class="dpre">``（每行帶類別；內文行附 data-line 供前端上色）。"""
    lines = []
    for line in text.split("\n"):
        cls = _diff_class(line)
        attr = ' data-line="%s"' % _esc(line) if cls in ("d-add", "d-del", "d-ctx") else ""
        lines.append('<span class="dline %s"%s>%s</span>' % (cls, attr, _esc(line) or " "))
    return '<pre class="dpre">%s</pre>' % "".join(lines)


def _origin_slug():
    """origin remote 的 ``owner/repo``；非 GitHub 或無 remote 時回 None。"""
    try:
        url = subprocess.run(["git", "-C", str(config.load().root), "remote", "get-url", "origin"],
                             capture_output=True, text=True, timeout=5).stdout.strip()
    except Exception:
        url = ""
    if "github.com" not in url:
        return None
    return url.split("github.com", 1)[1].lstrip(":/").removesuffix(".git").strip("/")


def _github_base(branch):
    """由 origin remote 推得 GitHub blob 前綴；非 GitHub 或無 remote 時回 None。"""
    slug = _origin_slug()
    return "https://github.com/%s/blob/%s/" % (slug, branch) if slug else None


def _file_link(path, blob_base):
    """檔案連結：有 GitHub base 就指過去，否則純文字。"""
    if blob_base:
        return '<a href="%s%s">%s</a>' % (blob_base, path, _esc(path))
    return _esc(path)


def _md(raw):
    """以 ``<template>`` 內嵌原始 markdown（HTML 轉義）；前端 markdown.js 就地渲染。"""
    return '<div class="rendered" data-md><template>%s</template></div>' % _esc(raw)


def _render_history(cfg):
    """變更歷史頁內容；回傳 (HTML, 筆數)。"""
    entries = history.parse_entries()
    out = []
    for entry in entries:
        when = _esc(entry["date"] or "")
        if entry["time"]:
            when += " " + _esc(entry["time"])
        # 去掉標題行（卡片已有 h2）與結尾分隔線，避免重複標題與多餘 <hr>。
        body = "\n".join(entry["raw"].split("\n")[1:]).strip()
        body = re.sub(r"\n-{3,}\s*$", "", body).strip()
        out.append('<article class="card"><h2>%s</h2><div class="meta">%s</div>%s</article>'
                   % (_esc(entry["title"]), when, _md(body)))
    return "\n".join(out), len(entries)


def _symbol_card(sym, blob_base, nested):
    """單一 API 宣告卡片；型別若有 ``members`` 則收進可展開的 details。"""
    link = _file_link(sym["file"], blob_base)
    signature = ('<pre class="sig">%s</pre>' % _esc(sym["signature"])) if sym.get("signature") else ""
    comment = _md(sym["comment"]) if sym.get("comment") else '<p class="muted">' + i18n.t("dev.no_comment") + '</p>'
    head = ('<h2>%s</h2><div class="meta"><span class="kind">%s</span>%s · %s:%s</div>%s%s'
            % (_esc(sym["name"]), _esc(sym.get("kind", "")), _esc(sym["repo"]),
               link, sym["line"], signature, comment))
    members = sym.get("members") or []
    block = ""
    if members:
        block = ('<details class="members"><summary>%s (%d)</summary>%s</details>'
                 % (_esc(i18n.t("dev.members")), len(members),
                    "".join(_symbol_card(m, blob_base, True) for m in members)))
    return '<article class="card%s">%s%s</article>' % (" member" if nested else "", head, block)


def _render_symbols(symbols, blob_base):
    """API 宣告卡片。"""
    return "\n".join(_symbol_card(sym, blob_base, False) for sym in symbols)


def _render_documents(documents):
    """文件卡片（摘要預覽）；標題連到靜態文件頁 ``docs/<i>.html``。"""
    out = []
    for i, doc in enumerate(documents):
        text = doc["text"]
        preview = text[:260] + (" …" if len(text) > 260 else "")
        out.append('<article class="card"><h2><a href="../docs/%d.html">%s</a></h2>'
                   '<div class="meta">%s</div><div class="preview">%s</div></article>'
                   % (i, _esc(doc["name"]), _esc(doc["repo"]), _esc(preview)))
    return "\n".join(out)


def _render_repos(repos):
    """近期改動：每個提交一個可展開的 ``<details>``（diff 內嵌）。"""
    parts = []
    for repo in repos:
        commits = []
        for commit in repo["commits"]:
            change = index.diff(repo["name"], commit["hash"])
            files = "".join('<span class="cfile">%s</span>' % _esc(f) for f in commit["files"])
            body = _diff_html(change["diff"]) if not change["empty"] else '<p class="muted" data-i18n="static.no_diff">' + i18n.t("static.no_diff") + '</p>'
            when = (commit["date"] or "")[:16].replace("T", " ")
            summary = ('<summary><span class="cbody"><span class="commit-top">'
                       '<code class="hash">%s</code><span class="when">%s</span></span>'
                       '<span class="subject">%s</span></span></summary>'
                       % (_esc(commit["hash"]), _esc(when), _esc(commit["subject"])))
            commits.append('<details class="commit">%s'
                           '<div class="commit-files">%s</div>%s</details>' % (summary, files, body))
        parts.append('<article class="card"><h2>%s</h2><div class="meta">HEAD：%s</div>'
                     '<div class="commits">%s</div></article>'
                     % (_esc(repo["name"]), _esc(repo["head"]), "".join(commits)))
    return "\n".join(parts)


def _render_dev(data, blob_base):
    """開發索引頁內容；回傳 (HTML, symbols, documents, sources 計數)。"""
    blocks = ['<h1 data-i18n="tab.symbols">%s</h1><p class="muted"><span data-i18n="filter.supported">%s</span>%s</p>'
              % (_esc(i18n.t("tab.symbols")), _esc(i18n.t("filter.supported")),
                 _esc("、".join(data.get("languages", []))))
              + _render_symbols(data["symbols"], blob_base),
              '<h1 id="docs" data-i18n="tab.documents">%s</h1>' % _esc(i18n.t("tab.documents"))
              + _render_documents(data["documents"]),
              '<h1 data-i18n="tab.repos">%s</h1>' % _esc(i18n.t("tab.repos")) + _render_repos(data["repos"])]
    if data["features"]:
        cards = "".join(
            '<article class="card"><h2>%s</h2><div class="meta">%s</div><p>%s</p></article>'
            % (_esc(f.get("name")), _esc(f.get("id")), _esc(f.get("summary")))
            for f in data["features"])
        blocks.insert(0, '<h1 data-i18n="tab.features">%s</h1>' % _esc(i18n.t("tab.features")) + cards)
    return ("\n".join(blocks), sum(1 for _ in index.iter_symbols(data["symbols"])),
            len(data["documents"]), len(data["repos"]))


def _write_docs(out, documents, footer):
    """為每份 Markdown 文件產生一個靜態檢視頁 ``docs/<i>.html``。"""
    docs_dir = out / "docs"
    docs_dir.mkdir()
    for i, doc in enumerate(documents):
        (docs_dir / ("%d.html" % i)).write_text(assets.render(
            "static_doc.html", docname=_esc(doc["name"]), title=_esc(config.load().title),
            content=_esc(doc["text"]), footer=footer, **i18n.subs()), encoding="utf-8")


def _write_about(out, cfg, data, footer, slug):
    """產生靜態「關於」頁 ``about/index.html``：changelogkit 版本、來源 commit、UI 語系。"""
    head = data["repos"][0]["head"] if data["repos"] else ""
    if head and slug:
        source = '<a href="https://github.com/%s/commit/%s">%s@%s</a>' % (slug, head, slug, head[:7])
    elif head:
        source = "%s@%s" % (_esc(cfg.root.name), head[:7])
    else:
        source = _esc(i18n.t("about.unknown"))
    home = ('<a href="https://github.com/%s">github.com/%s</a>' % (slug, slug)) if slug else _esc(cfg.root.name)
    # 語系列：可點擊切換的 chips（目前生效者由前端 CK_applyI18n 高亮）。
    locales = '<span class="lchips">%s</span>' % "".join(
        '<button type="button" class="lchip" data-locale="%s">%s</button>' % (_esc(name), _esc(name))
        for name in i18n.available())
    about_dir = out / "about"
    about_dir.mkdir()
    (about_dir / "index.html").write_text(assets.render(
        "static_about.html", **i18n.subs(), title=_esc(cfg.title), footer=footer,
        version=_esc(buildinfo.version()), source=source, locales=locales, home=home), encoding="utf-8")


def export(out_dir, branch="main"):
    """把目前 repo 匯出成靜態站到 ``out_dir``；回傳輸出路徑（Path）。"""
    cfg = config.load()
    out = Path(out_dir).resolve()
    if out.exists():
        shutil.rmtree(out)
    (out / "assets").mkdir(parents=True)
    (out / "development").mkdir()
    for name in STATIC_ASSETS:
        shutil.copyfile(assets.path(name), out / "assets" / name)
    blob_base = _github_base(branch)
    data = index.snapshot()

    # 頁尾：顯示本產物對應的來源 commit 與產生時間。
    head = data["repos"][0]["head"] if data["repos"] else ""
    slug = _origin_slug()
    if head and slug:
        where = '<a href="https://github.com/%s/commit/%s">%s@%s</a>' % (slug, head, slug, head[:7])
    elif head:
        where = "%s@%s" % (_esc(cfg.root.name), head[:7])
    else:
        where = "（無 git 資訊）"
    footer = i18n.t("static.built_by", src=where, time=datetime.now().strftime("%Y-%m-%d %H:%M"))

    hist_content, count = _render_history(cfg)
    (out / "index.html").write_text(assets.render(
        "static_history.html", **i18n.subs(), title=_esc(cfg.title), content=hist_content,
        count=str(count), footer=footer), encoding="utf-8")

    dev_content, symbols, documents, sources = _render_dev(data, blob_base)
    (out / "development" / "index.html").write_text(assets.render(
        "static_dev.html", **i18n.subs(), title=_esc(cfg.title), content=dev_content,
        symbols=str(symbols), documents=str(documents), sources=str(sources),
        footer=footer), encoding="utf-8")

    _write_docs(out, data["documents"], footer)
    _write_about(out, cfg, data, footer, slug)

    (out / ".nojekyll").write_text("", encoding="utf-8")
    return out
