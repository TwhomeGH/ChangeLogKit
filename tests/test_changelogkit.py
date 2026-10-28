"""changelogkit 單元測試：設定載入、歷史解析／寫入、開發索引路由、資產覆寫。

以暫存 git repo 為測試對象（不觸碰真實專案）。
"""

import importlib.util
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

_DEV_SPEC = importlib.util.spec_from_file_location(
    "ck_dev", Path(__file__).resolve().parents[1] / "tools" / "dev.py")
dev_tool = importlib.util.module_from_spec(_DEV_SPEC)
_DEV_SPEC.loader.exec_module(dev_tool)

from changelogkit import assets, backfill, cli, community, config, docs, export, history, index  # noqa: E402

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
            self.assertEqual(cfg.community, repo.root / "Docs/community.md")
            self.assertEqual([s.name for s in cfg.sources], ["app"])

    def test_doc_group_accepts_single_path_string(self):
        groups = config._doc_groups([{"id": "x", "paths": "Docs/**"}])
        self.assertEqual(groups[0].paths, ("Docs/**",))

    def test_parses_docs_section(self):
        with TempRepo() as repo:
            (repo.root / ".changelog.toml").write_text(
                TOML + '\n[tool.changelog.docs]\nunlisted = "folder"\nauto = false\n\n'
                '[[tool.changelog.docs.groups]]\nid = "dev"\ntitle = "開發者指南"\n'
                'color = "blue"\norder = 10\npaths = ["Docs/**"]\n\n'
                '[[tool.changelog.docs.entries]]\npath = "Docs/install.md"\nnote = "安裝"\n',
                encoding="utf-8")
            config.reset()
            cfg = config.load(repo.root)
            self.assertEqual(cfg.docs_unlisted, "folder")
            self.assertFalse(cfg.docs_auto)
            self.assertEqual(cfg.doc_groups[0].id, "dev")
            self.assertEqual(cfg.doc_groups[0].paths, ("Docs/**",))
            self.assertEqual(cfg.doc_entries[0].note, "安裝")


class DevToolTests(unittest.TestCase):
    def test_build_env_prepends_source(self):
        env = dev_tool.build_env({"PYTHONPATH": "existing"})
        self.assertTrue(env["PYTHONPATH"].startswith(str(dev_tool.SOURCE) + os.pathsep))
        self.assertTrue(env["PYTHONPATH"].endswith("existing"))

    def test_find_config_walks_up(self):
        with TempRepo() as repo:
            nested = repo.root / "Docs" / "development"
            nested.mkdir()
            self.assertEqual(dev_tool.find_config(nested), repo.root / ".changelog.toml")


class DocsTests(unittest.TestCase):
    @staticmethod
    def cfg(groups=(), entries=(), unlisted="other", auto=True):
        return config.Config(
            root=Path("."), title="t", history=Path("h"), features=None,
            community=None, assets=None, doc_groups=list(groups),
            doc_entries=list(entries), docs_unlisted=unlisted, docs_auto=auto)

    def test_groups_and_entry_override(self):
        cfg = self.cfg(
            groups=[config.DocGroup("dev", "開發者指南", "blue", "說明", 10,
                                    ("Docs/development/**", "Docs/api/**"))],
            entries=[config.DocEntry("Docs/api/README.md", "API 總覽", "先看這份")])
        result, groups, warnings = docs.resolve([
            {"name": "Docs/api/README.md", "repo": "app", "url": "u", "text": "x"},
            {"name": "Docs/development/testing.md", "repo": "app", "url": "u", "text": "x"},
            {"name": "Docs/misc.md", "repo": "app", "url": "u", "text": "x"},
        ], cfg)
        self.assertEqual([d["group"] for d in result], ["dev", "dev", "other"])
        self.assertEqual(result[0]["title"], "API 總覽")
        self.assertEqual(result[0]["note"], "先看這份")
        self.assertEqual(result[1]["title"], "testing")
        self.assertEqual(groups[-1]["id"], "other")
        self.assertEqual(warnings, [])

    def test_overlap_is_warning_not_guess(self):
        cfg = self.cfg(groups=[
            config.DocGroup("a", "A", "blue", "", 10, ("Docs/**",)),
            config.DocGroup("b", "B", "green", "", 20, ("Docs/api/**",)),
        ])
        result, _, warnings = docs.resolve([{"name": "Docs/api/x.md"}], cfg)
        self.assertEqual(result[0]["group"], "other")
        self.assertTrue(any(w["type"] == "overlap" for w in warnings))

    def test_bad_color_falls_back(self):
        cfg = self.cfg(groups=[config.DocGroup("a", "A", "pink", "", 10, ("Docs/**",))])
        result, _, warnings = docs.resolve([{"name": "Docs/x.md"}], cfg)
        self.assertEqual(result[0]["groupColor"], "slate")
        self.assertTrue(any(w["type"] == "bad_color" for w in warnings))

    def test_hidden_unlisted(self):
        result, _, _ = docs.resolve([{"name": "Docs/x.md"}], self.cfg(unlisted="hidden"))
        self.assertEqual(result, [])

    def test_folder_unlisted(self):
        result, _, _ = docs.resolve(
            [{"name": "Docs/api/x.md"}, {"name": "Docs/ops/y.md"}],
            self.cfg(unlisted="folder", auto=False))
        self.assertEqual([d["group"] for d in result], ["folder:api", "folder:ops"])

    def test_auto_fallback_groups(self):
        result, groups, warnings = docs.resolve([
            {"name": "Docs/api/README.md"},
            {"name": "Docs/development/guide.md"},
            {"name": "Docs/guide/start.md"},
            {"name": "Docs/deploy/run.md"},
            {"name": "Docs/design/adr.md"},
            {"name": "Docs/misc.md"},
        ], self.cfg())
        self.assertEqual([d["group"] for d in result],
                         ["auto:dev", "auto:dev", "auto:guide", "auto:ops",
                          "auto:design", "other"])
        self.assertEqual(result[0]["groupTitleKey"], "docs.auto.dev")
        self.assertEqual(warnings, [])

    def test_config_overrides_auto(self):
        cfg = self.cfg(groups=[config.DocGroup(
            "custom", "自訂", "violet", "", 5, ("Docs/api/**",))])
        result, _, _ = docs.resolve(
            [{"name": "Docs/api/x.md"}, {"name": "Docs/development/y.md"}], cfg)
        self.assertEqual([d["group"] for d in result], ["custom", "auto:dev"])

    def test_auto_disabled(self):
        result, _, _ = docs.resolve([{"name": "Docs/api/x.md"}], self.cfg(auto=False))
        self.assertEqual(result[0]["group"], "other")

    def test_auto_uses_deepest_folder(self):
        result, _, _ = docs.resolve([{"name": "Docs/guide/design/x.md"}], self.cfg())
        self.assertEqual(result[0]["group"], "auto:design")

    def test_unmatched_pattern_warning(self):
        cfg = self.cfg(groups=[config.DocGroup("a", "A", "blue", "", 10, ("Docs/none/**",))])
        _, _, warnings = docs.resolve([{"name": "Docs/x.md"}], cfg)
        self.assertTrue(any(w["type"] == "unmatched_pattern" for w in warnings))

    def test_all_patterns_count_as_used(self):
        cfg = self.cfg(groups=[config.DocGroup(
            "a", "A", "blue", "", 10, ("Docs/**", "Docs/api/**"))])
        _, _, warnings = docs.resolve([{"name": "Docs/api/x.md"}], cfg)
        self.assertFalse(any(w["type"] == "unmatched_pattern" for w in warnings))

    def test_snapshot_classifies_documents(self):
        with TempRepo() as repo:
            api = repo.root / "Docs" / "api"
            api.mkdir()
            (api / "README.md").write_text("# API\n", encoding="utf-8")
            (repo.root / ".changelog.toml").write_text(
                TOML + '\n[[tool.changelog.docs.groups]]\nid = "dev"\ntitle = "開發者指南"\n'
                'color = "blue"\npaths = ["Docs/api/**"]\n', encoding="utf-8")
            config.reset()
            config.load(repo.root)
            data = index.snapshot()
            doc = next(d for d in data["documents"] if d["name"] == "Docs/api/README.md")
            self.assertEqual(doc["group"], "dev")
            self.assertEqual(doc["groupTitle"], "開發者指南")
            self.assertTrue(any(g["id"] == "dev" for g in data["docGroups"]))


class ExportTests(unittest.TestCase):
    def test_doc_url_is_stable_and_encoded(self):
        self.assertEqual(export._doc_url("Docs/api/README.md"), "docs/Docs/api/README.html")
        self.assertEqual(export._doc_url("Docs/my doc.md"), "docs/Docs/my%20doc.html")

    def test_static_pages_use_stable_urls_and_split_repos(self):
        with TempRepo() as repo:
            api = repo.root / "Docs" / "api"
            api.mkdir()
            (api / "README.md").write_text("# API\n", encoding="utf-8")
            out = repo.root / "_site"
            export.export(out)

            self.assertTrue((out / "docs" / "Docs" / "api" / "README.html").is_file())
            self.assertFalse((out / "docs" / "0.html").exists())

            dev = (out / "development" / "index.html").read_text(encoding="utf-8")
            self.assertIn("../docs/Docs/api/README.html", dev)
            self.assertNotIn('class="commit"', dev)
            self.assertNotIn('class="sig"', dev)

            symbols_page = (out / "development" / "symbols.html").read_text(encoding="utf-8")
            self.assertIn('class="sig"', symbols_page)

            repos = (out / "development" / "repos.html").read_text(encoding="utf-8")
            self.assertIn('class="commit"', repos)
            self.assertIn("init", repos)

            doc = (out / "docs" / "Docs" / "api" / "README.html").read_text(encoding="utf-8")
            self.assertIn("../../../assets/theme.css", doc)
            self.assertIn("../../../development/", doc)
            self.assertIn('class="docbadge color-blue"', doc)
            self.assertIn("doc-group-auto-dev", doc)
            self.assertIn('id="doctoc"', doc)


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

    def test_add_cli_body(self):
        with TempRepo():
            cli.main(["add", "CLI 測試", "--type", "新增",
                      "--problem", "症狀摘要\n細節", "--cause", "根因摘要",
                      "--change", "核心改動", "--change", "其他改動"])
            raw = history.parse_entries()[0]["raw"]
            self.assertIn("### 問題 - 症狀摘要", raw)
            self.assertIn("細節", raw)
            self.assertIn("### 根因 - 根因摘要", raw)
            self.assertIn("### 修改 - 核心改動", raw)
            self.assertIn("- 其他改動", raw)

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

    def test_backfill_strip_number(self):
        # --strip-number 要去掉子標題的編號（含 73a. 與 4.1 兩種寫法），即使是已日期式條目。
        with TempRepo() as repo:
            p = repo.root / "Docs" / "ChangeHistory.md"
            p.write_text("# H\n\n## 2026.01.01 10:00 舊\n\n### 4.1 恢復速度加快\n\n"
                         "### 4.2 Zero-Byte\n\n### 73a. 動機\n", encoding="utf-8")
            backfill.backfill(apply=True, strip_number=True)
            t = p.read_text(encoding="utf-8")
            for kept in ("### 恢復速度加快", "### Zero-Byte", "### 動機"):
                self.assertIn(kept, t)
            self.assertNotIn("### 4.1", t)
            self.assertNotIn("### 73a.", t)

    def test_backfill_removes_declared_time_without_double_blank(self):
        # 移除 **時間** 行時不應留下連續空行（markdownlint MD012）。
        with TempRepo() as repo:
            p = repo.root / "Docs" / "ChangeHistory.md"
            p.write_text("# H\n\n## 12. 標題\n\n**時間**：2026/01/02 10:00:00\n\n**檔案**：\n\n- a\n",
                         encoding="utf-8")
            _git(repo.root, "add", "-A")
            _git(repo.root, "-c", "user.email=t@t", "-c", "user.name=t", "commit", "-qm", "x")
            backfill.backfill(apply=True)
            t = p.read_text(encoding="utf-8")
            self.assertIn("## 2026.01.02 10:00 標題", t)
            self.assertNotIn("**時間**", t)
            self.assertNotIn("\n\n\n", t)

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

    def test_rel_path(self):
        with TempRepo() as repo:
            self.assertEqual(index.rel_path(repo.root / "Docs/ChangeHistory.md"),
                             "Docs/ChangeHistory.md")
            self.assertIsNone(index.rel_path(repo.root.parent / "outside.md"))  # root 外 → None
            self.assertIsNone(index.rel_path(None))

    def test_snapshot_contexts(self):
        # 前端渲染 markdown 需要「來源文件脈絡」以改寫相對連結。
        with TempRepo():
            data = index.snapshot()
            self.assertEqual(data["contexts"]["history"],
                             {"repo": "app", "path": "Docs/ChangeHistory.md"})
            self.assertEqual(data["contexts"]["features"]["path"],
                             "Docs/development/features.json")

    def test_routes(self):
        with TempRepo():
            code, body, mime = index.route("/development/data", "")
            self.assertEqual(code, 200)
            self.assertIn("application/json", mime)
            self.assertIn("repos", json.loads(body))
            self.assertEqual(index.route("/development/diff", "repo=app&worktree=1")[0], 200)
            self.assertEqual(index.route("/development/diff", "repo=app&hash=zzz")[0], 400)
            self.assertEqual(index.route("/development/file", "repo=app&path=../x")[0], 400)


class CommunityTests(unittest.TestCase):
    SAMPLE = ("# 社群與開發交流\n\n## Discord 群\n交流使用心得、討論開發問題。\n"
              "[加入 Discord →](https://discord.gg/abc)\n\n## Twitch 直播\n追蹤直播。\n"
              "[前往 Twitch →](https://www.twitch.tv/x)\n")

    def test_parse(self):
        data = community.parse(self.SAMPLE)
        self.assertEqual(data["title"], "社群與開發交流")
        self.assertEqual([c["title"] for c in data["cards"]], ["Discord 群", "Twitch 直播"])
        self.assertEqual(data["cards"][0]["action"],
                         {"text": "加入 Discord →", "href": "https://discord.gg/abc"})
        self.assertEqual(data["cards"][0]["body"], "交流使用心得、討論開發問題。")  # 行動連結行已移除

    def test_action_link_is_standalone_line_only(self):
        # 行內連結不算行動按鈕，會留在說明中。
        data = community.parse("## A\n加入我們的 [Discord](https://x) 一起討論。\n")
        self.assertIsNone(data["cards"][0]["action"])
        self.assertIn("[Discord](https://x)", data["cards"][0]["body"])

    def test_missing_file_hidden(self):
        with TempRepo():
            self.assertIsNone(community.load())              # 無檔 → 不顯示
            self.assertEqual(community.html_block(None), "")

    def test_html_block_escapes(self):
        block = community.html_block(community.parse(
            "# A & B\n## <x>\n<img>\n[<a>](https://x/?a=1&b=2)\n"))
        self.assertIn("A &amp; B", block)
        self.assertIn("&lt;x&gt;", block)
        self.assertIn("[&lt;a&gt;](https://x/?a=1&amp;b=2)", block)  # 行動連結以 markdown 內嵌（前端解析）
        self.assertIn("&lt;img&gt;", block)

    def test_write_template(self):
        with TempRepo() as repo:
            path, created = community.write_template()
            self.assertTrue(created)
            self.assertEqual(path, repo.root / "Docs/community.md")
            self.assertTrue(path.read_text(encoding="utf-8").startswith("# "))
            self.assertFalse(community.write_template()[1])  # 已存在 → 不覆蓋

    def test_template_is_markdownlint_clean(self):
        # MD041（首行 H1）、MD022（標題前後空行）、MD047（結尾單一換行）。
        text = community.template()
        lines = text.split("\n")
        self.assertTrue(lines[0].startswith("# "))
        self.assertTrue(text.endswith("\n") and not text.endswith("\n\n"))
        for i, line in enumerate(lines):
            if line.startswith("#"):
                self.assertEqual(lines[i - 1] if i else "", "", "標題前需空行（MD022）：" + line)
                self.assertTrue(i + 1 < len(lines) and lines[i + 1] == "",
                                "標題後需空行（MD022）：" + line)


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


class VersionTests(unittest.TestCase):
    def test_source_version_matches_pyproject(self):
        # 以原始碼執行時版號須等於 pyproject（不被環境中殘留的舊安裝誤導）。
        import re

        import changelogkit

        text = (Path(__file__).resolve().parents[1] / "pyproject.toml").read_text(encoding="utf-8")
        match = re.search(r'^version\s*=\s*"([^"]+)"', text, re.MULTILINE)
        self.assertIsNotNone(match)
        self.assertEqual(changelogkit.__version__, match.group(1))


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

    def test_auto_doc_group_titles(self):
        for key in ("docs.auto.dev", "docs.auto.guide", "docs.auto.ops", "docs.auto.design"):
            for name, catalog in self.catalogs.items():
                self.assertIn(key, catalog, "%s 缺少 %s" % (name, key))


if __name__ == "__main__":
    unittest.main()
