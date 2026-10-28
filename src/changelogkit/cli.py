"""命令列介面：serve / add / list / show / languages / locales / symbols / export / backfill-dates / community-init。

網頁 GUI 為主要介面；CLI 供腳本化使用。字串經 :mod:`i18n`（預設跟隨系統、
判定為非中文時回退 ``en``；可用 ``--locale`` 覆寫）。
"""

import argparse
import sys

from . import backfill, buildinfo, community, export as static_export, history, i18n, server


def _prescan_locale(argv):
    """在建立 parser 前先看 ``--locale``（argparse 的 help 是急切求值的）。"""
    for i, token in enumerate(argv):
        if token == "--locale" and i + 1 < len(argv):
            return argv[i + 1]
        if token.startswith("--locale="):
            return token.split("=", 1)[1]
    return None


def cmd_add(args):
    """插入新紀錄；日期／時間留空時帶入現在時刻。

    標題是唯一的位置參數；內文用 ``--problem``／``--cause``／``--change``
    （可重複）提供，第一行會成為該節的摘要，其餘行是細節。
    """
    date_str = args.date or history.now_parts()[0]
    time_str = args.time or history.now_parts()[1]
    changes = []
    for chunk in getattr(args, "change", []):
        changes.extend(chunk.splitlines())
    history.insert_block(history.build_block(
        date_str, args.title, args.type, args.file,
        problem=getattr(args, "problem", ""),
        root_cause=getattr(args, "cause", ""),
        changes=changes,
        refs=getattr(args, "ref", []), time_str=time_str))
    print(i18n.t("msg.inserted", date=date_str, time=time_str, title=args.title))


def _matches(e, args):
    """依 grep／file／type／since 篩選單筆紀錄。"""
    hay = (e["title"] + "\n" + e["raw"]).lower()
    if args.grep and args.grep.lower() not in hay:
        return False
    if args.file and args.file.lower() not in e["raw"].lower():
        return False
    if args.type and args.type.lower() not in e["raw"].lower():
        return False
    if args.since and (not e["date"] or e["date"] < args.since):
        return False
    return True


def cmd_backfill(args):
    """從 git 回填沒有日期的條目（預設只顯示，``--apply`` 才寫入）。"""
    r = backfill.backfill(apply=args.apply, strip_number=args.strip_number, sort=args.sort)
    for status, before, after, source in r["items"]:
        if status == "ok":
            print("%s  (%s)" % (after, source))
        else:
            print("? %s" % before)
    mode = "已寫入" if r["applied"] else "試跑（未寫入）"
    print(i18n.t("msg.backfill_summary", total=r["total"], converted=r["converted"],
                 skipped=r["skipped"], mode=mode))


def cmd_list(args):
    """列出符合條件的紀錄（序號、日期時間、標題）。"""
    entries = history.parse_entries()
    hits = [e for e in entries if _matches(e, args)]
    if args.limit:
        hits = hits[: args.limit]
    print(i18n.t("msg.list_summary", hits=len(hits), total=len(entries)) + "\n")
    for i, e in enumerate(hits, 1):
        when = e["date"] or "----------"
        if e["date"] and e["time"]:
            when += " " + e["time"]
        print("%3d  %-16s  %s" % (i, when, e["title"]))


def cmd_show(args):
    """以編號或關鍵字顯示單筆完整內容。"""
    entries = history.parse_entries()
    target = None
    if args.query.isdigit():
        idx = int(args.query) - 1
        if 0 <= idx < len(entries):
            target = entries[idx]
    if target is None:
        q = args.query.lower()
        target = next((e for e in entries if q in (e["title"] + "\n" + e["raw"]).lower()), None)
    if target is None:
        sys.exit(i18n.t("msg.not_found", query=args.query))
    print(target["raw"])


def cmd_languages(args):
    """列出支援的程式語言（API 宣告掃描涵蓋範圍）。"""
    from .scanners import SUPPORTED_LANGUAGES

    print(i18n.t("msg.languages_header"))
    for lang in SUPPORTED_LANGUAGES:
        print("  " + lang)


def cmd_locales(args):
    """列出支援的 UI 語系，並以 ``*`` 標示目前生效者。"""
    active = i18n.current()
    print(i18n.t("msg.locales_header", current=active))
    for name in i18n.available():
        print("  " + name + (" *" if name == active else ""))


def _symbol_matches(symbol, query, lang, kind, repo):
    """依關鍵字／語言／種類／來源篩選單一符號。"""
    if query and query not in (symbol["name"] + " " + symbol.get("signature", "")).lower():
        return False
    if lang and (symbol.get("lang") or "").lower() != lang.lower():
        return False
    if kind and symbol.get("kind") != kind:
        return False
    if repo and symbol.get("repo") != repo:
        return False
    return True


def cmd_docs(args):
    """檢查文件分類：列出解析後的群組與警告；設定錯誤回傳 1。"""
    from . import docs as docmeta, index

    records, groups, warnings = docmeta.resolve(index.documents())
    print(i18n.t("msg.docs_summary", docs=len(records), groups=len(groups)))
    for group in groups:
        items = [record for record in records if record["group"] == group["id"]]
        title = (group.get("title")
                 or (i18n.t(group["titleKey"]) if group.get("titleKey")
                     else i18n.t("docs.unclassified")))
        print("[%s] %s (%d)" % (group["id"], title, len(items)))
        if not args.summary:
            for record in items:
                note = ("  # " + record["note"]) if record.get("note") else ""
                print("  " + record["name"] + note)
    for warning in warnings:
        level = "ERROR" if warning.get("type") in docmeta.ERROR_TYPES else "WARN "
        print(level + " " + docmeta.warning_text(warning))
    errors = [w for w in warnings if w.get("type") in docmeta.ERROR_TYPES]
    if errors:
        print(i18n.t("msg.docs_errors", count=len(errors)))
        return 1
    if warnings:
        print(i18n.t("msg.docs_warnings", count=len(warnings)))
    else:
        print(i18n.t("msg.docs_ok"))
    return 0


def cmd_docs_init(args):
    """印出由目前資料夾推測的分類 TOML；不修改任何檔案。"""
    from . import docs as docmeta, index

    print(docmeta.toml_suggestion(index.documents()), end="")
    print(i18n.t("msg.docs_init_hint"), file=sys.stderr)


def cmd_symbols(args):
    """查詢開發索引掃到的 API 宣告（語言／種類／關鍵字）。"""
    from . import index

    data = index.snapshot()
    symbols = list(index.iter_symbols(data["symbols"]))
    query = (args.query or "").lower()
    hits = [s for s in symbols if _symbol_matches(s, query, args.lang, args.kind, args.repo)]
    if args.limit:
        hits = hits[: args.limit]
    print(i18n.t("msg.symbols_summary", hits=len(hits), total=len(symbols),
                 langs="、".join(data["languages"])) + "\n")
    for symbol in hits:
        print("%-22s %-9s %-10s %s:%d" % (symbol.get("lang") or "-", symbol.get("kind") or "",
                                          symbol["name"], symbol["file"], symbol["line"]))


def main(argv=None):
    """進入點：解析參數並分派。無子命令等同 ``serve``。"""
    argv = sys.argv[1:] if argv is None else list(argv)
    i18n.set_language(_prescan_locale(argv))
    p = argparse.ArgumentParser(description=i18n.t("cli.desc"))
    p.add_argument("--version", action="version", version=buildinfo.version_string())
    p.add_argument("--locale", default=None, help=i18n.t("cli.locale"))
    sub = p.add_subparsers(dest="cmd")

    sv = sub.add_parser("serve", help=i18n.t("cli.serve.help"))
    sv.add_argument("--port", type=int, default=8710, help=i18n.t("cli.serve.port"))
    sv.add_argument("--no-browser", action="store_true", help=i18n.t("cli.serve.no_browser"))

    a = sub.add_parser("add", help=i18n.t("cli.add.help"))
    a.add_argument("title", help=i18n.t("cli.add.title"))
    a.add_argument("--type", default="修復", help=i18n.t("cli.add.type"))
    a.add_argument("--file", default="", help=i18n.t("cli.add.file"))
    a.add_argument("--problem", default="", help=i18n.t("cli.add.problem"))
    a.add_argument("--cause", default="", help=i18n.t("cli.add.cause"))
    a.add_argument("--change", action="append", default=[], help=i18n.t("cli.add.change"))
    a.add_argument("--date", default="", help=i18n.t("cli.add.date"))
    a.add_argument("--time", default="", help=i18n.t("cli.add.time"))
    a.add_argument("--ref", action="append", default=[], help=i18n.t("cli.add.ref"))

    lst = sub.add_parser("list", help=i18n.t("cli.list.help"))
    lst.add_argument("--grep", default="", help=i18n.t("cli.list.grep"))
    lst.add_argument("--since", default="", help=i18n.t("cli.list.since"))
    lst.add_argument("--file", default="", help=i18n.t("cli.list.file"))
    lst.add_argument("--type", default="", help=i18n.t("cli.list.type"))
    lst.add_argument("--limit", type=int, default=0, help=i18n.t("cli.list.limit"))

    sh = sub.add_parser("show", help=i18n.t("cli.show.help"))
    sh.add_argument("query", help=i18n.t("cli.show.query"))

    sub.add_parser("languages", help=i18n.t("cli.languages.help"))
    sub.add_parser("locales", help=i18n.t("cli.locales.help"))

    dc = sub.add_parser("docs", help=i18n.t("cli.docs.help"))
    dc.add_argument("--check", action="store_true", help=i18n.t("cli.docs.check"))
    dc.add_argument("--summary", action="store_true", help=i18n.t("cli.docs.summary"))

    sub.add_parser("docs-init", help=i18n.t("cli.docs_init.help"))

    sy = sub.add_parser("symbols", help=i18n.t("cli.symbols.help"))
    sy.add_argument("query", nargs="?", default="", help=i18n.t("cli.symbols.query"))
    sy.add_argument("--lang", default="", help=i18n.t("cli.symbols.lang"))
    sy.add_argument("--kind", default="", help=i18n.t("cli.symbols.kind"))
    sy.add_argument("--repo", default="", help=i18n.t("cli.symbols.repo"))
    sy.add_argument("--limit", type=int, default=0, help=i18n.t("cli.symbols.limit"))

    ex = sub.add_parser("export", help=i18n.t("cli.export.help"))
    ex.add_argument("out", nargs="?", default="_site", help=i18n.t("cli.export.out"))
    ex.add_argument("--branch", default="main", help=i18n.t("cli.export.branch"))

    bf = sub.add_parser("backfill-dates", help=i18n.t("cli.backfill.help"))
    bf.add_argument("--apply", action="store_true", help=i18n.t("cli.backfill.apply"))
    bf.add_argument("--strip-number", action="store_true", help=i18n.t("cli.backfill.strip_number"))
    bf.add_argument("--sort", action="store_true", help=i18n.t("cli.backfill.sort"))

    sub.add_parser("community-init", help=i18n.t("cli.community.help"))

    args = p.parse_args(argv)
    if args.cmd in (None, "serve"):
        server.serve(getattr(args, "port", 8710), not getattr(args, "no_browser", False))
    elif args.cmd == "add":
        cmd_add(args)
    elif args.cmd == "list":
        cmd_list(args)
    elif args.cmd == "show":
        cmd_show(args)
    elif args.cmd == "languages":
        cmd_languages(args)
    elif args.cmd == "locales":
        cmd_locales(args)
    elif args.cmd == "docs":
        raise SystemExit(cmd_docs(args))
    elif args.cmd == "docs-init":
        cmd_docs_init(args)
    elif args.cmd == "symbols":
        cmd_symbols(args)
    elif args.cmd == "export":
        out = static_export.export(args.out, args.branch)
        print(i18n.t("msg.exported", path=str(out)))
    elif args.cmd == "backfill-dates":
        cmd_backfill(args)
    elif args.cmd == "community-init":
        path, created = community.write_template()
        print(i18n.t("msg.community_created" if created else "msg.community_exists", path=str(path)))


if __name__ == "__main__":
    main()
