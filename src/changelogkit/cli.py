"""命令列介面：add / list / show / serve。

網頁 GUI 為主要介面；CLI 供腳本化使用。
"""

import argparse
import sys

from . import buildinfo, export as static_export, history, server


def cmd_add(args):
    """插入新紀錄；日期／時間留空時帶入現在時刻。"""
    date_str = args.date or history.now_parts()[0]
    time_str = args.time or history.now_parts()[1]
    history.insert_block(history.build_block(
        date_str, args.title, args.type, args.file,
        refs=getattr(args, "ref", []), time_str=time_str))
    print("已插入: %s %s %s" % (date_str, time_str, args.title))


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


def cmd_list(args):
    """列出符合條件的紀錄（序號、日期時間、標題）。"""
    entries = history.parse_entries()
    hits = [e for e in entries if _matches(e, args)]
    if args.limit:
        hits = hits[: args.limit]
    print("符合 %d / 共 %d 筆\n" % (len(hits), len(entries)))
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
        sys.exit("找不到符合的紀錄: %s" % args.query)
    print(target["raw"])


def cmd_languages(args):
    """列出支援的程式語言（API 宣告掃描涵蓋範圍）。"""
    from .scanners import SUPPORTED_LANGUAGES

    for lang in SUPPORTED_LANGUAGES:
        print(lang)


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


def cmd_symbols(args):
    """查詢開發索引掃到的 API 宣告（語言／種類／關鍵字）。"""
    from . import index

    data = index.snapshot()
    symbols = data["symbols"]
    query = (args.query or "").lower()
    hits = [s for s in symbols if _symbol_matches(s, query, args.lang, args.kind, args.repo)]
    if args.limit:
        hits = hits[: args.limit]
    print("符合 %d / 共 %d 個符號（支援語言：%s）\n" % (len(hits), len(symbols), "、".join(data["languages"])))
    for symbol in hits:
        print("%-22s %-9s %-10s %s:%d" % (symbol.get("lang") or "-", symbol.get("kind") or "",
                                          symbol["name"], symbol["file"], symbol["line"]))


def main(argv=None):
    """進入點：解析參數並分派。無子命令等同 ``serve``。"""
    p = argparse.ArgumentParser(description="變更歷史：網頁 GUI + CLI")
    p.add_argument("--version", action="version", version=buildinfo.version_string())
    sub = p.add_subparsers(dest="cmd")

    sv = sub.add_parser("serve", help="啟動本機網頁 GUI")
    sv.add_argument("--port", type=int, default=8710)
    sv.add_argument("--no-browser", action="store_true")

    a = sub.add_parser("add", help="插入新紀錄骨架（CLI）")
    a.add_argument("title")
    a.add_argument("--type", default="修復")
    a.add_argument("--file", default="")
    a.add_argument("--date", default="")
    a.add_argument("--time", default="", help="時間 HH:MM（預設為現在時刻）")
    a.add_argument("--ref", action="append", default=[], help="相關文件（可重複，格式 [說明](路徑)）")

    l = sub.add_parser("list", help="檢索紀錄（CLI）")
    l.add_argument("--grep", default="")
    l.add_argument("--since", default="")
    l.add_argument("--file", default="")
    l.add_argument("--type", default="")
    l.add_argument("--limit", type=int, default=0)

    s = sub.add_parser("show", help="顯示單筆完整內容（編號或關鍵字）")
    s.add_argument("query")

    sub.add_parser("languages", help="列出支援的程式語言")

    sy = sub.add_parser("symbols", help="查詢 API 宣告（語言／種類／關鍵字）")
    sy.add_argument("query", nargs="?", default="")
    sy.add_argument("--lang", default="", help="限定語言（如 Python）")
    sy.add_argument("--kind", default="", help="限定種類（func／class／property…）")
    sy.add_argument("--repo", default="", help="限定來源名稱")
    sy.add_argument("--limit", type=int, default=0)

    ex = sub.add_parser("export", help="匯出唯讀靜態站（供 GitHub Pages）")
    ex.add_argument("out", nargs="?", default="_site", help="輸出目錄（預設 _site）")
    ex.add_argument("--branch", default="main", help="檔案連結指向的 branch（預設 main）")

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
    elif args.cmd == "symbols":
        cmd_symbols(args)
    elif args.cmd == "export":
        out = static_export.export(args.out, args.branch)
        print("已匯出靜態站：%s" % out)


if __name__ == "__main__":
    main()
