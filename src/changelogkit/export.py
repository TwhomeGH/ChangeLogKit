"""靜態匯出：把本機工具產生為可部署到 GitHub Pages 的**唯讀**靜態站。

動態功能（新增／編輯紀錄、即時檔案檢視、lazy 抓 diff）都需要本機 server，靜態站
只提供瀏覽：

* 變更歷史：逐筆呈現，內文 markdown 由前端 ``markdown.js`` 就地渲染。
* 開發索引：列出功能／API 宣告／文件／近期改動；每個提交的 unified diff **直接
  內嵌**於 ``<details>``（免 server）；檔案連結指向 GitHub blob（由 origin remote 推得）。

輸出為純靜態檔，可直接丟到 GitHub Pages（含 ``.nojekyll``）。
"""

import html
import json
import re
import shutil
import subprocess
from datetime import datetime
from pathlib import Path
from urllib.parse import quote

from . import assets, buildinfo, community, config, docs as docmeta, history, i18n, index

# 需要複製到輸出 assets/ 的檔案（其餘為 server 動態用，不需要）。
STATIC_ASSETS = ("theme.css", "theme.js", "i18n.js", "dev.css", "file.css", "highlight.js", "markdown.js")


def _esc(text):
    """HTML 轉義（None 視為空字串）。"""
    return html.escape(str(text if text is not None else ""))


def _doc_stem(name):
    """文件路徑去掉 ``./``、開頭斜線與 ``.md``。"""
    clean = str(name).replace("\\", "/")
    while clean.startswith("./"):
        clean = clean[2:]
    clean = clean.strip("/")
    return clean[:-3] if clean.lower().endswith(".md") else clean


def _doc_rel(repo, name):
    """文件在站內的相對檔案路徑：``docs/<source>/<path>.html``（避免同名碰撞）。"""
    return "docs/" + str(repo).replace("\\", "/") + "/" + _doc_stem(name) + ".html"


def _doc_url(repo, name):
    """文件頁 URL（站根相對；source 與路徑逐段 percent-encode）。"""
    stem = "/".join(quote(part, safe="") for part in _doc_stem(name).split("/"))
    return "docs/" + quote(str(repo), safe="") + "/" + stem + ".html"


def _site_base(rel):
    """從站根相對的路徑推得該頁面回到站根的相對前綴（``../`` …）。"""
    return "../" * len(Path(rel).parent.parts)


def _group_anchor(group_id):
    """群組標題的 HTML id（``auto:dev`` → ``doc-group-auto-dev``）。"""
    slug = re.sub(r"[^A-Za-z0-9_-]+", "-", str(group_id)).strip("-")
    return "doc-group-" + (slug or "other")


def _commit_rel(repo, commit_hash):
    """單筆 commit 頁的站根相對路徑（repo 名稱逐段 encode 成一個目錄）。"""
    return "development/commits/%s/%s.html" % (
        quote(str(repo), safe=""), quote(str(commit_hash), safe=""))


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
    """origin remote 的 ``owner/repo``（委派 :func:`buildinfo.origin_slug`）。"""
    return buildinfo.origin_slug()


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
    comment = ('<div class="doc rendered" data-repo="%s" data-file="%s" data-raw="%s"></div>'
               % (_esc(sym["repo"]), _esc(sym["file"]), _esc(sym["comment"]))) \
        if sym.get("comment") else '<p class="muted">' + i18n.t("dev.no_comment") + '</p>'
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
    """API 宣告卡片：依檔案收進 ``<details>``；展開時才上色／渲染註釋。"""
    by_file, order = {}, []
    for sym in symbols:
        name = sym.get("file") or ""
        if name not in by_file:
            by_file[name] = []
            order.append(name)
        by_file[name].append(sym)
    out = []
    for name in order:
        cards = "".join(_symbol_card(sym, blob_base, False) for sym in by_file[name])
        out.append('<details class="symgroup"><summary><span class="sfile">%s</span>'
                   '<span class="count">(%d)</span></summary>'
                   '<div class="syms">%s</div></details>'
                   % (_esc(name), len(by_file[name]), cards))
    return "\n".join(out)


def _render_doc_warnings(warnings):
    """文件分類設定的警告；沒有就回空字串。"""
    if not warnings:
        return ""
    items = "".join("<li>%s</li>" % _esc(docmeta.warning_text(w)) for w in warnings)
    return ('<div class="docwarn"><strong>%s</strong><ul>%s</ul></div>'
            % (_esc(i18n.t("docs.warn_title")), items))


def _render_documents(documents, groups, base="../"):
    """文件卡片（摘要預覽）；依群組分節，標題連到穩定的 ``docs/<path>.html``。"""
    by_group = {}
    for doc in documents:
        by_group.setdefault(doc.get("group", ""), []).append(doc)
    out = []
    for group in groups:
        items = by_group.get(group["id"]) or []
        if not items:
            continue
        title = (group.get("title")
                 or (i18n.t(group["titleKey"]) if group.get("titleKey")
                     else i18n.t("docs.unclassified")))
        gnote = ('<span class="gnote">%s</span>' % _esc(group.get("note"))) if group.get("note") else ""
        out.append('<section class="doc-section" data-doc-group="%s">' % _esc(group["id"]))
        out.append('<h2 id="%s" class="docgroup color-%s"><span class="dot"></span>'
                   '<span class="gtitle">%s</span><span class="count">(%d)</span>%s</h2>'
                   % (_esc(_group_anchor(group["id"])), _esc(group.get("color", "slate")),
                      _esc(title), len(items), gnote))
        for doc in items:
            text = doc["text"]
            preview = text[:260] + (" …" if len(text) > 260 else "")
            dnote = ('<div class="docnote">%s</div>' % _esc(doc["note"])) if doc.get("note") else ""
            href = base + _doc_url(doc.get("repo", ""), doc["name"])
            out.append('<article class="card"><h2><a href="%s">%s</a></h2>'
                       '<div class="meta">%s%s</div>%s<div class="preview">%s</div></article>'
                       % (_esc(href), _esc(doc.get("title") or doc["name"]), _esc(doc["name"]),
                          (" · " + _esc(doc["repo"])) if doc.get("repo") else "", dnote,
                          _esc(preview)))
        out.append('</section>')
    return "\n".join(out)


def _render_repo_list(repos):
    """近期改動列表：只列 commit 與檔案；完整 diff 在各自的 commit 頁。"""
    parts = []
    for repo in repos:
        rows = []
        for commit in repo["commits"]:
            when = (commit["date"] or "")[:16].replace("T", " ")
            files = "".join('<span class="cfile">%s</span>' % _esc(f) for f in commit["files"])
            href = "commits/%s/%s.html" % (
                quote(str(repo["name"]), safe=""), quote(str(commit["hash"]), safe=""))
            rows.append(
                '<a class="commit-row" href="%s"><span class="commit-top">'
                '<code class="hash">%s</code><span class="when">%s</span></span>'
                '<span class="subject">%s</span><span class="files">%s</span></a>'
                % (_esc(href), _esc(commit["hash"]), _esc(when), _esc(commit["subject"]), files))
        parts.append('<article class="card"><h2>%s</h2><div class="meta">HEAD：%s</div>'
                     '<div class="commit-list">%s</div></article>'
                     % (_esc(repo["name"]), _esc(repo["head"]), "".join(rows)))
    return "\n".join(parts)


def _write_commits(out, repos, footer):
    """為每筆 commit 產生獨立頁面（完整 diff，不塞進列表頁）。"""
    for repo in repos:
        for commit in repo["commits"]:
            rel = _commit_rel(repo["name"], commit["hash"])
            base = _site_base(rel)
            change = index.diff(repo["name"], commit["hash"])
            diff = (_diff_html(change["diff"]) if not change["empty"]
                    else '<p class="muted" data-i18n="static.no_diff">'
                         + i18n.t("static.no_diff") + '</p>')
            files = "".join('<span class="cfile">%s</span>' % _esc(f) for f in commit["files"])
            when = (commit["date"] or "")[:16].replace("T", " ")
            target = out / rel
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(assets.render(
                "static_commit.html", **i18n.subs(), title=_esc(config.load().title),
                hash=_esc(commit["hash"]), repo=_esc(repo["name"]),
                subject=_esc(commit["subject"]), when=_esc(when), files=files,
                diff=diff, footer=footer, base=base), encoding="utf-8")


def _render_overview(data):
    """靜態開發索引首頁：文件優先，其次是功能；API／近期改動各自獨立一頁。"""
    blocks = ['<h1 id="docs" data-i18n="tab.documents">%s</h1>' % _esc(i18n.t("tab.documents"))
              + _render_doc_warnings(data.get("docWarnings") or [])
              + _render_documents(data["documents"], data.get("docGroups") or [])]
    if data["features"]:
        cards = "".join(
            '<article class="card"><h2>%s</h2><div class="meta">%s</div><p>%s</p></article>'
            % (_esc(f.get("name")), _esc(f.get("id")), _esc(f.get("summary")))
            for f in data["features"])
        blocks.append('<h1 data-i18n="tab.features">%s</h1>' % _esc(i18n.t("tab.features")) + cards)
    return "\n".join(blocks), len(data["documents"]), len(data["features"])


def _render_symbols_page(data, blob_base):
    """靜態 API 宣告頁；回傳 (HTML, symbols 計數)。"""
    hint = ('<p class="muted"><span data-i18n="filter.supported">%s</span>%s</p>'
            % (_esc(i18n.t("filter.supported")), _esc("、".join(data.get("languages", [])))))
    return (hint + _render_symbols(data["symbols"], blob_base),
            sum(1 for _ in index.iter_symbols(data["symbols"])))


def _write_docs(out, documents, footer, doc_pages_json, blob_base_json):
    """為每份 Markdown 文件產生穩定的靜態頁 ``docs/<path>.html``。

    巢狀路徑要依深度改寫 ``base``／``site_base``，文件內的相對連結才會
    指回正確的站內頁（或 GitHub blob）。
    """
    for doc in documents:
        rel = _doc_rel(doc.get("repo", ""), doc["name"])
        base = _site_base(rel)
        target = out / rel
        target.parent.mkdir(parents=True, exist_ok=True)
        gtitle = (doc.get("groupTitle")
                  or (i18n.t(doc["groupTitleKey"]) if doc.get("groupTitleKey")
                      else i18n.t("docs.unclassified")))
        note = doc.get("note") or ""
        note_html = ('<div class="rendered docnote" data-md><template>%s</template></div>'
                     % _esc(note)) if note else ""
        target.write_text(assets.render(
            "static_doc.html", docname=_esc(doc.get("title") or doc["name"]),
            title=_esc(config.load().title), content=_esc(doc["text"]), footer=footer,
            **i18n.subs(), base=base, docpath=_esc(doc["name"]),
            grouptitle=_esc(gtitle), groupcolor=_esc(doc.get("groupColor") or "slate"),
            groupanchor=_esc(_group_anchor(doc.get("group", ""))), docnote=note_html,
            site_base=json.dumps(base), doc_pages=doc_pages_json, blob_base=blob_base_json,
            doc_path=json.dumps(doc["name"], ensure_ascii=False),
            doc_repo=json.dumps(doc.get("repo", ""), ensure_ascii=False)), encoding="utf-8")


def _write_about(out, cfg, data, footer, slug, community_html, doc_pages_json, blob_base_json,
                 community_path):
    """產生靜態「關於」頁 ``about/index.html``：changelogkit 版本、來源 commit、UI 語系、社群區塊。"""
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
        version=_esc(buildinfo.version()), source=source, locales=locales, home=home,
        community=community_html, site_base=json.dumps("../"),
        doc_pages=doc_pages_json, blob_base=blob_base_json,
        doc_path=json.dumps(community_path, ensure_ascii=False),
        doc_repo=json.dumps(index.default_repo(), ensure_ascii=False)), encoding="utf-8")


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

    # 站內連結脈絡：文件相對路徑 → 穩定文件頁；其餘退回 GitHub blob。
    doc_pages_json = json.dumps({
        "%s:%s" % (doc.get("repo", ""), doc["name"]):
            _doc_url(doc.get("repo", ""), doc["name"])
        for doc in data["documents"]}, ensure_ascii=False)
    blob_base_json = json.dumps(blob_base, ensure_ascii=False)
    hist_rel = index.rel_path(cfg.history) or ""

    hist_content, count = _render_history(cfg)
    (out / "index.html").write_text(assets.render(
        "static_history.html", **i18n.subs(), title=_esc(cfg.title), content=hist_content,
        count=str(count), footer=footer,
        site_base=json.dumps(""), doc_pages=doc_pages_json, blob_base=blob_base_json,
        doc_path=json.dumps(hist_rel, ensure_ascii=False),
        doc_repo=json.dumps(index.default_repo(), ensure_ascii=False)), encoding="utf-8")

    overview_content, documents, features = _render_overview(data)
    (out / "development" / "index.html").write_text(assets.render(
        "static_dev.html", **i18n.subs(), title=_esc(cfg.title), content=overview_content,
        documents=str(documents), features=str(features), footer=footer, base="../",
        site_base=json.dumps("../"), doc_pages=doc_pages_json,
        blob_base=blob_base_json, doc_path=json.dumps(""),
        doc_repo=json.dumps(index.default_repo(), ensure_ascii=False)), encoding="utf-8")

    symbols_content, symbols = _render_symbols_page(data, blob_base)
    (out / "development" / "symbols.html").write_text(assets.render(
        "static_symbols.html", **i18n.subs(), title=_esc(cfg.title), content=symbols_content,
        symbols=str(symbols), sources=str(len(data["repos"])), footer=footer, base="../",
        site_base=json.dumps("../"), doc_pages=doc_pages_json,
        blob_base=blob_base_json, doc_path=json.dumps("")), encoding="utf-8")

    if slug and len(data["repos"]) == 1:
        older_url = "https://github.com/%s/commits/%s" % (slug, quote(branch, safe="/"))
        more = '<a href="%s">%s</a>' % (_esc(older_url), _esc(i18n.t("static.older_github")))
    else:
        more = '<a href="../">%s</a>' % _esc(i18n.t("static.older_history"))
    (out / "development" / "repos.html").write_text(assets.render(
        "static_repos.html", **i18n.subs(), title=_esc(cfg.title),
        content=_render_repo_list(data["repos"]), footer=footer, base="../",
        count=str(cfg.recent_commits), more=more), encoding="utf-8")
    _write_commits(out, data["repos"], footer)

    _write_docs(out, data["documents"], footer, doc_pages_json, blob_base_json)
    community_html = community.html_block(community.load(), i18n.t("about.community_title"))
    _write_about(out, cfg, data, footer, slug, community_html, doc_pages_json, blob_base_json,
                 index.rel_path(cfg.community) or "")

    (out / ".nojekyll").write_text("", encoding="utf-8")
    return out
