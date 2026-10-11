"""changelogkit 單元測試：設定載入、歷史解析／寫入、開發索引路由、資產覆寫。

以暫存 git repo 為測試對象（不觸碰真實專案）。
"""

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from changelogkit import assets, backfill, config, history, index  # noqa: E402

SAMPLE = """# 變更歷史

## 2026.01.02 10:00 第二筆

**類型**: 修正 · **檔案**: `a.swift`

### 問題 - 有問題
細節

---

## 2026.01.01 第一筆

**類型**: 功能

### 修改 - 新功能
- 細節

---
"""

SWIFT = """/// 一個測試型別。
public struct Thing {
    /// 執行。
    public func run() {}
}
"""

TOML = """[tool.changelog]
title = "測試專案"
history = "Docs/ChangeHistory.md"
"""


def _git(root, *args):
    subprocess.run(["git", "-C", str(root), *args], capture_output=True, text=True)


class TempRepo:
    """建立含 Git、變更歷史、Swift 與設定的暫存 repo。"""

    def __enter__(self):
        self._tmp = tempfile.TemporaryDirectory()
        root = self.root = Path(self._tmp.name)
        (root / "Docs").mkdir(parents=True)
        (root / "Docs" / "ChangeHistory.md").write_text(SAMPLE, encoding="utf-8")
        (root / "Sources").mkdir()
        (root / "Sources" / "Thing.swift").write_text(SWIFT, encoding="utf-8")
        (root / "Package.resolved").write_text(
            json.dumps({"pins": [{"identity": "x", "state": {"revision": "abc123"}}]}),
            encoding="utf-8")
        (root / ".changelog.toml").write_text(TOML, encoding="utf-8")
        _git(root, "init", "-q")
        _git(root, "add", "-A")
        _git(root, "-c", "user.email=t@t", "-c", "user.name=t", "commit", "-qm", "init")
        config.reset()
        config.load(root)
        return self

    def __exit__(self, *exc):
        config.reset()
        self._tmp.cleanup()


class ConfigTests(unittest.TestCase):
    def test_loads_table(self):
        with TempRepo() as repo:
            cfg = config.load()
            self.assertEqual(cfg.title, "測試專案")
            self.assertEqual(cfg.root, repo.root.resolve())
            self.assertEqual(cfg.history, repo.root / "Docs/ChangeHistory.md")
            self.assertEqual([s.name for s in cfg.sources], ["app"])


class HistoryTests(unittest.TestCase):
    def test_parse(self):
        with TempRepo():
            entries = history.parse_entries()
            self.assertEqual([e["title"] for e in entries], ["第二筆", "第一筆"])
            self.assertEqual(entries[0]["date"], "2026.01.02")
            self.assertEqual(entries[0]["time"], "10:00")

    def test_insert_prepends(self):
        with TempRepo():
            history.insert_block(history.build_block("2026.02.01", "新紀錄", "功能", "b.swift"))
            self.assertEqual(history.parse_entries()[0]["title"], "新紀錄")

    def test_git_changed_files(self):
        with TempRepo() as repo:
            (repo.root / "new.txt").write_text("x", encoding="utf-8")
            self.assertIn("new.txt", history.git_changed_files())

    def test_multi_refs_multiline(self):
        with TempRepo():
            history.insert_block(history.build_block(
                "2026.04.01", "多筆相關文件", "功能", "",
                refs=["[A](a.md)", "[B](b.md)", "[C](c.md)"]))
            raw = history.parse_entries()[0]["raw"]
            self.assertIn("**相關文件**:\n\n- [A](a.md)", raw)   # 標籤與清單間空行（MD032）
            self.assertIn("- [C](c.md)", raw)

    def test_history_starts_with_h1(self):
        # 沒有 H1 的舊檔，寫入後要自動補上（markdownlint MD041）。
        with TempRepo() as repo:
            p = repo.root / "Docs" / "ChangeHistory.md"
            p.write_text(SAMPLE.replace("# 變更歷史\n\n", ""), encoding="utf-8")
            history.insert_block(history.build_block("2026.05.01", "H1", "功能", ""))
            self.assertTrue(history.read_history().startswith("# ChangeHistory\n"))

    def test_backfill_dates_from_git(self):
        # 沒有日期的條目 → 用「首次加入的 commit」時間補上日期。
        with TempRepo() as repo:
            p = repo.root / "Docs" / "ChangeHistory.md"
            p.write_text("# H\n\n## 沒有日期的條目\n\n內容\n", encoding="utf-8")
            _git(repo.root, "add", "-A")
            _git(repo.root, "-c", "user.email=t@t", "-c", "user.name=t", "commit", "-qm", "x")
            r = backfill.backfill(apply=False)
            self.assertEqual(r["converted"], 1)
            self.assertEqual(r["items"][0][0], "ok")
            self.assertRegex(r["items"][0][2], r"^## \d{4}\.\d{2}\.\d{2} \d{2}:\d{2} 沒有日期的條目$")

    def test_missing_history_is_graceful(self):
        # 沒有 ChangeHistory.md 時回空、不中斷；insert_block 會自動建立（含父目錄）。
        with TempRepo() as repo:
            (repo.root / "Docs" / "ChangeHistory.md").unlink()
            self.assertEqual(history.parse_entries(), [])
            history.insert_block(history.build_block("2026.03.01", "第一筆", "功能", ""))
            self.assertEqual(history.parse_entries()[0]["title"], "第一筆")


class IndexTests(unittest.TestCase):
    def test_roots_and_symbols(self):
        with TempRepo() as repo:
            self.assertEqual(index.roots(), {"app": repo.root.resolve()})
            data = index.snapshot()
            self.assertTrue(any(s["name"] == "Thing" for s in data["symbols"]))
            self.assertEqual(data["lockedPackages"], [{"identity": "x", "revision": "abc123"}])

    def test_glob_re(self):
        dist = index._glob_re("**/dist/**")
        self.assertTrue(dist.match("a/b/dist/c.js"))
        self.assertTrue(dist.match("dist/c.js"))
        self.assertFalse(dist.match("a/b/c.js"))
        mini = index._glob_re("*.min.js")
        self.assertTrue(mini.match("a.min.js"))
        self.assertFalse(mini.match("a/b.min.js"))

    def test_scanners(self):
        js = "export function foo() {}\nclass Bar {}\nexport const BAZ = () => {}"
        js_names = [s["name"] for s in index.scan_symbols(js, "app", "a.js")]
        self.assertIn("foo", js_names)
        self.assertIn("Bar", js_names)
        self.assertIn("BAZ", js_names)
        ts = ("export declare class KickWebSocket {\n"
              "  connect(channel: string): void;\n  readonly ready: boolean;\n}\n"
              "export declare function create(): void;")
        ts_names = [s["name"] for s in index.scan_symbols(ts, "app", "k.d.ts")]
        for expected in ("KickWebSocket", "connect", "ready", "create"):
            self.assertIn(expected, ts_names)
        py = "def alpha():\n    pass\nclass Beta:\n    pass"
        py_names = [s["name"] for s in index.scan_symbols(py, "app", "a.py")]
        self.assertIn("alpha", py_names)
        self.assertIn("Beta", py_names)
        c = "class Foo {};\nstruct Pt { int x; };\nvoid setup() {\n}\nint add(int a, int b);"
        c_names = [s["name"] for s in index.scan_symbols(c, "app", "a.cpp")]
        for expected in ("Foo", "Pt", "setup", "add"):
            self.assertIn(expected, c_names)
        cases = {
            "a.kt": ("data class User(val id: Int)\nfun greet(name: String): String {\n return name\n}\ninterface Repo", ("User", "greet", "Repo")),
            "a.java": ("public class Main {\n  public static void main(String[] a) {\n  }\n}\ninterface Svc", ("Main", "main", "Svc")),
            "a.go": ("type Server struct {\n}\nfunc (s *Server) Handle() {\n}\nfunc New() {}", ("Server", "Handle", "New")),
            "a.rs": ("pub struct Config {\n}\npub fn run() {\n}\nimpl Config {\n}", ("Config", "run")),
            "a.cs": ("public class Api {\n  public void Get() {\n  }\n}\ninterface IApi", ("Api", "Get", "IApi")),
            "a.rb": ("class Widget\n  def render(x)\n  end\n  def self.build\n  end\nend\nmodule Util", ("Widget", "render", "build", "Util")),
            "a.dart": ("class HomePage {\n}\nmixin Logger {\n}\nvoid main() {\n}\nFuture<void> fetch() async {\n}", ("HomePage", "Logger", "main", "fetch")),
        }
        for fname, (src, expected) in cases.items():
            names = [s["name"] for s in index.scan_symbols(src, "app", fname)]
            for name in expected:
                self.assertIn(name, names, "%s 少了 %s" % (fname, name))
        self.assertEqual(index.scan_symbols("x = 1", "app", "a.rb"), [])  # 未支援 → 空

    def test_validate_absent_features(self):
        with TempRepo():
            self.assertEqual(index.validate(), [])  # 沒有 features.json → 空清單

    def test_routes(self):
        with TempRepo():
            code, body, mime = index.route("/development/data", "")
            self.assertEqual(code, 200)
            self.assertIn("application/json", mime)
            self.assertIn("repos", json.loads(body))
            self.assertEqual(index.route("/development/diff", "repo=app&worktree=1")[0], 200)
            self.assertEqual(index.route("/development/diff", "repo=app&hash=zzz")[0], 400)
            self.assertEqual(index.route("/development/file", "repo=app&path=../x")[0], 400)


class AssetTests(unittest.TestCase):
    def test_default_asset(self):
        config.reset()
        self.assertIn("--accent", assets.read("theme.css"))

    def test_override_wins(self):
        with tempfile.TemporaryDirectory() as d:
            override = Path(d)
            (override / "theme.css").write_text("/* custom */", encoding="utf-8")
            cfg = config.load()
            original = cfg.assets
            cfg.assets = override
            try:
                self.assertEqual(assets.read("theme.css"), "/* custom */")
                self.assertIn("#tabs", assets.read("dev.css"))  # 未覆寫者仍用預設
            finally:
                cfg.assets = original


class I18nTests(unittest.TestCase):
    def test_lookup_and_fallback(self):
        from changelogkit import i18n

        i18n.set_language("en")
        self.assertEqual(i18n.t("cli.list.help"), "Search entries (CLI)")
        i18n.set_language("zh-TW")
        self.assertEqual(i18n.t("cli.list.help"), "檢索紀錄（CLI）")
        self.assertEqual(i18n.t("nope.key"), "nope.key")
        i18n.set_language(None)

    def test_available_locales(self):
        from changelogkit import i18n
        self.assertIn("zh-TW", i18n.available())
        self.assertIn("en", i18n.available())


class I18nKeyTests(unittest.TestCase):
    """確保程式／HTML／JS 用到的 i18n key 都有定義，且各語系不缺 key（避免少翻）。"""

    @classmethod
    def setUpClass(cls):
        import re

        root = Path(__file__).resolve().parents[1] / "src" / "changelogkit"
        cls.catalogs = {p.stem: json.loads(p.read_text(encoding="utf-8"))
                        for p in (root / "lang").glob("*.json")}
        used = set()
        for path in list(root.glob("*.py")) + list((root / "scanners").glob("*.py")):
            text = path.read_text(encoding="utf-8")
            used |= set(re.findall(r'i18n\.t\(\s*"([\w.]+)"', text))
            used |= set(re.findall(r'(?<![\w.])t\(\s*"([\w.]+)"', text))
        for path in (root / "assets").glob("*.html"):
            used |= set(re.findall(r"\{\{t\.([\w.]+)\}\}", path.read_text(encoding="utf-8")))
        for path in (root / "assets").glob("*.js"):
            used |= set(re.findall(r'CK_T\(\s*"([\w.]+)"', path.read_text(encoding="utf-8")))
        cls.used = used

    def test_reference_defines_used_keys(self):
        missing = sorted(k for k in self.used if k not in self.catalogs["en"])
        self.assertEqual(missing, [], "用到但 en 未定義的 key：" + ", ".join(missing))

    def test_locales_not_drifted(self):
        reference = self.catalogs["en"]
        for name, catalog in self.catalogs.items():
            missing = sorted(k for k in reference if k not in catalog)
            self.assertEqual(missing, [], "%s 缺少 en 有的 key：%s" % (name, ", ".join(missing)))


if __name__ == "__main__":
    unittest.main()
