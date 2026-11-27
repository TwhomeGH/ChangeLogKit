"""本機 HTTP 伺服器：網頁 GUI、檔案檢視與 JSON API。

路由分工：

* ``/``                    變更歷史 GUI
* ``/assets/<name>``       共用網頁資產（CSS／JS／HTML 片段）
* ``/development*``        開發索引（轉交 :mod:`changelogkit.index`）
* ``/api/*``               GUI 用的 JSON API
"""

import html
import json
import mimetypes
import socket
import sys
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, unquote, urlencode, urlparse

from . import apidocs, assets, buildinfo, community, config, history, i18n, index, todo


class Handler(BaseHTTPRequestHandler):
    # 非 loopback 綁定時預設唯讀，避免無驗證的寫入 API 暴露在區網。
    allow_write = True

    def log_message(self, *a):
        """靜音：避免每個請求都印到終端機。"""
        pass

    def _page(self, name):
        """以 i18n 佔位與前端字典渲染 html 資產。"""
        return assets.render(name, i18n_json=json.dumps(i18n.js_dict(), ensure_ascii=False), **i18n.subs())

    def _send(self, code, body, ctype="application/json; charset=utf-8"):
        data = body.encode("utf-8") if isinstance(body, str) else body
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def _serve_asset(self, name):
        """提供 assets/ 底下的資產；名稱由 assets.path 驗證。"""
        try:
            return self._send(200, assets.read(name), assets.mime(name))
        except (ValueError, OSError):
            return self._send(404, b"", "text/plain; charset=utf-8")

    def _serve_api_doc(self, path):
        """提供 ``/api-docs/<mount>/...``：只讀取設定目錄內的真實檔案。"""
        path = unquote(path)
        for doc in config.load().api:
            bare = "/api-docs/%s" % doc.mount
            if path == bare:
                self.send_response(302)
                self.send_header("Location", bare + "/")
                self.end_headers()
                return None
            if not path.startswith(bare + "/"):
                continue
            rel = path[len(bare) + 1 :] or "index.html"
            target = apidocs.resolve_asset(doc, rel)
            if target is None:
                return self._send(404, b"Not found", "text/plain; charset=utf-8")
            ctype = mimetypes.guess_type(str(target))[0] or "application/octet-stream"
            return self._send(200, target.read_bytes(), ctype)
        return self._send(404, b"Not found", "text/plain; charset=utf-8")

    # ── GET ──
    def do_GET(self):
        u = urlparse(self.path)
        if u.path.startswith("/api-docs/"):
            return self._serve_api_doc(u.path)
        if u.path.startswith("/development"):
            return self._send(*index.route(u.path, u.query))
        if u.path.startswith("/assets/"):
            return self._serve_asset(u.path[len("/assets/") :])
        if u.path == "/":
            # 歷史頁的 markdown 連結以歷史檔所在目錄為基準改寫（前端注入 CK_HISTORY）。
            meta = json.dumps(
                {"repo": index.default_repo(), "path": index.rel_path(config.load().history) or ""},
                ensure_ascii=False,
            )
            return self._send(
                200,
                assets.render(
                    "index.html",
                    i18n_json=json.dumps(i18n.js_dict(), ensure_ascii=False),
                    history_json=meta,
                    project=html.escape(config.load().project),
                    todo_link=index.todo_link(),
                    api_nav=index.api_nav(),
                    **i18n.subs(),
                ),
                "text/html; charset=utf-8",
            )
        if u.path == "/todo":
            cfg = config.load()
            if not cfg.todo or not cfg.todo.is_file():
                return self._send(404, b"Not found", "text/plain; charset=utf-8")
            data = todo.parse(cfg.todo)
            rel = index.rel_path(cfg.todo) or cfg.todo.name
            source = "/development/file?" + urlencode({"repo": index.default_repo(), "path": rel})
            pct = round(data["done"] / data["total"] * 100) if data["total"] else 0
            hint = (
                ""
                if data["total"]
                else '<p class="docwarn" id="todo-hint">%s</p>' % html.escape(i18n.t("todo.no_tasks"))
            )
            return self._send(
                200,
                assets.render(
                    "todo.html",
                    **i18n.subs(),
                    i18n_json=json.dumps(i18n.js_dict(), ensure_ascii=False),
                    project=html.escape(cfg.project),
                    content=todo.render(data),
                    total=str(data["total"]),
                    done=str(data["done"]),
                    open_count=str(data["open"]),
                    sections=str(sum(1 for s in data["sections"] if s.get("items"))),
                    pct=str(pct),
                    todo_hint=hint,
                    version=todo.version(cfg.todo),
                    source_url=html.escape(source),
                    api_nav=index.api_nav(),
                    todo_repo=json.dumps(index.default_repo(), ensure_ascii=False),
                    todo_path=json.dumps(rel, ensure_ascii=False),
                ),
                "text/html; charset=utf-8",
            )
        if u.path == "/api/todo":
            cfg = config.load()
            if not cfg.todo or not cfg.todo.is_file():
                return self._send(
                    200,
                    json.dumps({"configured": False}, ensure_ascii=False),
                    "application/json; charset=utf-8",
                )
            data = todo.parse(cfg.todo)
            pct = round(data["done"] / data["total"] * 100) if data["total"] else 0
            return self._send(
                200,
                json.dumps(
                    {
                        "configured": True,
                        "version": todo.version(cfg.todo),
                        "html": todo.render(data),
                        "total": data["total"],
                        "done": data["done"],
                        "open": data["open"],
                        "pct": pct,
                    },
                    ensure_ascii=False,
                ),
                "application/json; charset=utf-8",
            )
        if u.path == "/workflows":
            return self._send(200, index.workflows_page(), "text/html; charset=utf-8")
        if u.path == "/about":
            # 社群區塊：未設定或無檔時為空字串（不顯示）；卡片說明的連結以該檔目錄為基準。
            block = community.html_block(community.load(), i18n.t("about.community_title"))
            meta = json.dumps(
                {"repo": index.default_repo(), "path": index.rel_path(config.load().community) or ""},
                ensure_ascii=False,
            )
            return self._send(
                200,
                assets.render(
                    "about.html",
                    i18n_json=json.dumps(i18n.js_dict(), ensure_ascii=False),
                    community=block,
                    community_json=meta,
                    project=html.escape(config.load().project),
                    todo_link=index.todo_link(),
                    api_nav=index.api_nav(),
                    **i18n.subs(),
                ),
                "text/html; charset=utf-8",
            )
        if u.path == "/api/buildinfo":
            return self._send(
                200,
                json.dumps(
                    {
                        "version": buildinfo.version(),
                        "commit": buildinfo.commit(),
                        "locale": i18n.current(),
                        "locales": i18n.available(),
                    },
                    ensure_ascii=False,
                ),
            )
        if u.path == "/favicon.ico":
            return self._send(204, b"")
        if u.path == "/api/entries":
            qs = parse_qs(u.query)
            q = qs.get("q", [""])[0].lower()
            ty = qs.get("type", [""])[0].lower()
            out = []
            for i, e in enumerate(history.parse_entries()):
                hay = (e["title"] + "\n" + e["raw"]).lower()
                if q and q not in hay:
                    continue
                if ty and ty not in e["raw"].lower():
                    continue
                out.append({"i": i, "date": e["date"], "time": e["time"], "title": e["title"]})
            return self._send(200, json.dumps(out, ensure_ascii=False))
        if u.path == "/api/entry":
            i = int(parse_qs(u.query).get("i", ["0"])[0])
            entries = history.parse_entries()
            if 0 <= i < len(entries):
                return self._send(200, json.dumps(entries[i], ensure_ascii=False))
            return self._send(404, "{}")
        if u.path == "/api/gitdiff":
            return self._send(200, json.dumps(history.git_changed_files(), ensure_ascii=False))
        return self._send(404, "{}")

    # ── POST ──
    def do_POST(self):
        if not self.allow_write:
            # 先讀完 body，避免 keep-alive 連線把下一個請求解析錯。
            length = int(self.headers.get("Content-Length", "0"))
            if length:
                self.rfile.read(length)
            return self._send(
                403,
                json.dumps({"ok": False, "error": i18n.t("serve.read_only_error")}, ensure_ascii=False),
            )
        u = urlparse(self.path)
        n = int(self.headers.get("Content-Length", "0"))
        try:
            body = json.loads(self.rfile.read(n) or b"{}")
        except Exception:
            body = {}
        try:
            if u.path == "/api/add":
                history.insert_block(
                    history.build_block(
                        body.get("date") or history.today_str(),
                        body.get("title", "(無標題)"),
                        body.get("type", "修復"),
                        body.get("file", ""),
                        body.get("problem", ""),
                        body.get("root_cause", ""),
                        body.get("changes", []),
                        body.get("refs", ""),
                        time_str=body.get("time", ""),
                        change_detail=body.get("change_detail", ""),
                    )
                )
                return self._send(200, json.dumps({"ok": True}))
            if u.path == "/api/save":
                history.update_entry(int(body["i"]), body["raw"])
                return self._send(200, json.dumps({"ok": True}))
            if u.path == "/api/delete":
                history.delete_entry(int(body["i"]))
                return self._send(200, json.dumps({"ok": True}))
        except Exception as ex:
            return self._send(400, json.dumps({"ok": False, "error": str(ex)}, ensure_ascii=False))
        return self._send(404, "{}")


class _Server(ThreadingHTTPServer):
    # Windows 上 allow_reuse_address=1 會讓第二個實例「搶綁」同一埠，
    # 造成兩個 server 同時 LISTEN、瀏覽器連到舊的。關掉它，綁不到就換埠。
    allow_reuse_address = False


def writable_for(host, allow_write=None):
    """是否允許寫入：loopback 預設可寫，其他介面預設唯讀。"""
    loopback = (host or "127.0.0.1").strip() in ("127.0.0.1", "localhost", "::1")
    return loopback if allow_write is None else bool(allow_write)


def _lan_addresses():
    """找出目前主機可從區網連到的 IPv4 位址（可能為空）。"""
    addresses = []

    def add(value):
        if value and value not in addresses and not value.startswith("127."):
            addresses.append(value)

    try:
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as probe:
            # UDP connect 不會送出封包；只用來取得預設路由所用的本機位址。
            probe.connect(("8.8.8.8", 80))
            add(probe.getsockname()[0])
    except OSError:
        pass
    try:
        for info in socket.getaddrinfo(socket.gethostname(), None, socket.AF_INET):
            add(info[4][0])
    except OSError:
        pass
    return [ip for ip in addresses if not ip.startswith("169.254.")]


def serve(port=8710, open_browser=True, host="127.0.0.1", allow_write=None):
    """啟動本機伺服器；埠被占用或被 Windows 保留時改用系統自動配置。

    ``host="0.0.0.0"`` 會監聽所有 IPv4 介面，供同一個區網的平板／手機連線。
    非 loopback 綁定預設唯讀；要允許新增／編輯／刪除需明確傳入
    ``allow_write=True``。
    """
    import threading
    import webbrowser

    bind = (host or "127.0.0.1").strip()
    loopback = bind in ("127.0.0.1", "localhost", "::1")
    writable = writable_for(bind, allow_write)
    Handler.allow_write = writable
    try:
        httpd = _Server((bind, port), Handler)
    except OSError:
        try:
            httpd = _Server((bind, 0), Handler)
        except OSError as error:
            print("無法啟動伺服器（%s:%s）：%s" % (bind, port, error), file=sys.stderr)
            raise SystemExit(1) from error
    actual = httpd.server_address[1]
    local_host = bind if not loopback else "127.0.0.1"
    if bind in ("0.0.0.0", "::"):
        local_host = "127.0.0.1"
    url = "http://%s:%d/" % (local_host, actual)
    print("變更歷史 GUI: %s" % url, flush=True)
    if not loopback:
        for ip in _lan_addresses():
            print("區域網路: http://%s:%d/" % (ip, actual), flush=True)
        print(
            "警告: 這是沒有登入驗證的本機工具；只應在信任的區網使用，勿對外公開。",
            file=sys.stderr,
            flush=True,
        )
        if writable:
            print("警告: 已允許區網寫入（新增／編輯／刪除）。", file=sys.stderr, flush=True)
        else:
            print("區網預設唯讀；需要寫入請加 --allow-write。", file=sys.stderr, flush=True)
    elif bind == "127.0.0.1":
        print("僅限本機；要從平板／其他裝置連線請加 --host 0.0.0.0。", flush=True)
    for warning in config.load().api_warnings:
        print("warning: %s" % warning, file=sys.stderr, flush=True)
    print("（Ctrl+C 結束）", flush=True)
    if open_browser:
        threading.Timer(0.4, lambda: webbrowser.open(url)).start()
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\nbye")
