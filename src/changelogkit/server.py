"""本機 HTTP 伺服器：網頁 GUI、檔案檢視與 JSON API。

路由分工：

* ``/``                    變更歷史 GUI
* ``/assets/<name>``       共用網頁資產（CSS／JS／HTML 片段）
* ``/development*``        開發索引（轉交 :mod:`changelogkit.index`）
* ``/api/*``               GUI 用的 JSON API
"""

import json
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, urlparse

from . import assets, buildinfo, history, i18n, index


class Handler(BaseHTTPRequestHandler):
    def log_message(self, *a):
        """靜音：避免每個請求都印到終端機。"""
        pass

    def _page(self, name):
        """以 i18n 佔位與前端字典渲染 html 資產。"""
        return assets.render(name, i18n_json=json.dumps(i18n.js_dict(), ensure_ascii=False),
                             **i18n.subs())

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

    # ── GET ──
    def do_GET(self):
        u = urlparse(self.path)
        if u.path.startswith("/development"):
            return self._send(*index.route(u.path, u.query))
        if u.path.startswith("/assets/"):
            return self._serve_asset(u.path[len("/assets/"):])
        if u.path == "/":
            return self._send(200, self._page("index.html"), "text/html; charset=utf-8")
        if u.path == "/about":
            return self._send(200, self._page("about.html"), "text/html; charset=utf-8")
        if u.path == "/api/buildinfo":
            return self._send(200, json.dumps(
                {"version": buildinfo.version(), "commit": buildinfo.commit()}, ensure_ascii=False))
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
        u = urlparse(self.path)
        n = int(self.headers.get("Content-Length", "0"))
        try:
            body = json.loads(self.rfile.read(n) or b"{}")
        except Exception:
            body = {}
        try:
            if u.path == "/api/add":
                history.insert_block(history.build_block(
                    body.get("date") or history.today_str(),
                    body.get("title", "(無標題)"), body.get("type", "修復"),
                    body.get("file", ""), body.get("problem", ""),
                    body.get("root_cause", ""), body.get("changes", []), body.get("refs", ""),
                    time_str=body.get("time", "")))
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


def serve(port=8710, open_browser=True):
    """啟動本機伺服器；埠被占用或被 Windows 保留時改用系統自動配置。"""
    import threading
    import webbrowser

    try:
        httpd = _Server(("127.0.0.1", port), Handler)
    except OSError:
        httpd = _Server(("127.0.0.1", 0), Handler)
    url = "http://127.0.0.1:%d/" % httpd.server_address[1]
    print("變更歷史 GUI: %s" % url)
    print("（Ctrl+C 結束）")
    if open_browser:
        threading.Timer(0.4, lambda: webbrowser.open(url)).start()
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\nbye")
