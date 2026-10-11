"""開發索引：唯讀 Git／文件／宣告索引。

提供功能清單（features.json）、原始碼宣告定位（文字掃描，非 Swift AST）、
Markdown 文件內容與近期 Git 改動。功能語意由版本控管的清單提供，程式只做
定位與呈現，不推測語意。

所有 HTTP 回應皆由 :func:`route` 產生，供 :mod:`changelog.server` 轉接；頁面
資產（HTML／CSS／JS）由 :mod:`changelog.assets` 載入。
"""

import html
import json
import re
import subprocess
from pathlib import Path
from urllib.parse import parse_qs

from . import assets, config, i18n
from .scanners import SUPPORTED_LANGUAGES, SUPPORTED_SUFFIXES, scan_symbols
from .scanners.common import link

def roots():
    """索引來源位置（由 .changelog.toml 的 sources 決定；不存在的路徑略過）。"""
    return {s.name: s.path for s in config.load().sources if s.path.is_dir()}


def default_repo():
    """未指定 repo 時使用的來源名稱（第一個設定的來源）。"""
    return config.load().sources[0].name


def git(root, *args):
    """固定參數呼叫 Git；不透過 shell，失敗明確回報。"""
    result = subprocess.run(["git", "-C", str(root), *args], capture_output=True,
                            encoding="utf-8", errors="replace", timeout=30)
    if result.returncode:
        raise ValueError("無法讀取 Git 資訊：" + result.stderr[:200])
    return result.stdout


def files(root):
    """只索引版本控管或未忽略的原始碼／Markdown，略過隱藏設定與產物。"""
    suffixes = SUPPORTED_SUFFIXES + (".md",)
    paths = git(root, "ls-files", "--cached", "--others", "--exclude-standard", "-z").split("\0")
    return sorted({p for p in paths if p and Path(p).suffix in suffixes
                   and not any(part.startswith(".") for part in Path(p).parts)})


def safe_file(repo, name):
    """檔案檢視僅允許索引內檔案，並阻擋路徑穿越及連到根目錄外的 symlink。"""
    root = roots().get(repo)
    if root is None or name not in files(root):
        raise ValueError("檔案不在索引範圍")
    path = (root / name).resolve()
    if not path.is_relative_to(root.resolve()) or not path.is_file() or path.stat().st_size > 2_000_000:
        raise ValueError("檔案不可讀取或超過 2 MB")
    return path


def validate():
    """驗證功能清單（存在才檢查）：``name`` 必填、``id`` 可省（預設取 name）、``files``/``docs`` 可省。

    其餘欄位一律原樣保留——「功能」分頁採通用 key-value 渲染，不綁定任何特定 schema，
    所以每個 repo 都能用自己的欄位（例如 platform／status）。
    """
    features = config.load().features
    if features is None or not features.exists():
        return []
    raw = json.loads(features.read_text(encoding="utf-8"))
    # 支援兩種形式：純陣列；或 { "labels": {...}, "features": [...] }（全域欄位標籤）。
    if isinstance(raw, dict):
        catalog, global_labels = raw.get("features") or [], raw.get("labels") or {}
    else:
        catalog, global_labels = raw, {}
    repo = default_repo()
    seen = set()
    result = []
    for feature in catalog:
        name = feature.get("name")
        if not name:
            raise ValueError("功能缺少欄位：name")
        fid = feature.get("id") or name
        if fid in seen:
            raise ValueError("重複功能 ID：" + fid)
        seen.add(fid)
        for path in list(feature.get("files") or []) + list(feature.get("docs") or []):
            safe_file(repo, path)
        item = dict(feature)
        item["id"] = fid
        item.setdefault("summary", "")
        item["labels"] = {**global_labels, **(feature.get("labels") or {})}
        item["files"] = list(feature.get("files") or [])
        item["docs"] = list(feature.get("docs") or [])
        result.append(item)
    return result


# ── 近期改動與差異 ────────────────────────────────────────────
# 提交欄位以 ASCII 控制字元分隔，避免標題含空白／符號時解析歧義。
_COMMIT_RS = "\x1e"   # 每筆提交的開頭（record separator）
_COMMIT_US = "\x1f"   # hash／時間／標題之間（unit separator）
_REV_RE = re.compile(r"^[0-9a-fA-F]{4,40}$")
MAX_DIFF = 400_000    # 單次差異回應上限（字元）


def _parse_commits(raw):
    """把 ``git log --format=%x1e… --name-only`` 解析成結構化提交清單。"""
    commits = []
    for chunk in raw.split(_COMMIT_RS):
        chunk = chunk.strip("\n")
        if not chunk:
            continue
        lines = chunk.split("\n")
        parts = lines[0].split(_COMMIT_US)
        if len(parts) < 3:
            continue
        commits.append({
            "hash": parts[0], "date": parts[1], "subject": parts[2],
            "files": [ln.strip() for ln in lines[1:] if ln.strip()],
        })
    return commits


def _safe_pathspec(name):
    """diff 用的路徑：擋絕對路徑、``..``、反斜線與開頭 ``-``（避免被當成 Git 選項）。"""
    name = (name or "").strip()
    if not name or name.startswith(("-", "/", "\\")) or "\\" in name:
        raise ValueError("不允許的路徑")
    parts = [p for p in name.split("/") if p not in ("", ".")]
    if not parts or any(p == ".." for p in parts):
        raise ValueError("不允許的路徑")
    return "/".join(parts)


def diff(repo, rev=None, path=None, worktree=False):
    """回傳某次提交（或工作區 ``git diff HEAD``）的差異文字；過大時截斷並標記。"""
    root = roots().get(repo)
    if root is None:
        raise ValueError("未知來源")
    if worktree or not rev:
        args = ["diff", "--no-color", "HEAD"]
    else:
        if not _REV_RE.match(rev):
            raise ValueError("無效的提交")
        args = ["show", "--no-color", "--format=medium", rev]
    if path:
        args += ["--", _safe_pathspec(path)]
    text = git(root, *args)
    truncated = len(text) > MAX_DIFF
    return {"diff": text[:MAX_DIFF] if truncated else text,
            "truncated": truncated, "empty": not text.strip()}


def _locked_packages():
    """根目錄 Package.resolved 的鎖定套件（v1 為 object.pins，v2/v3 為頂層 pins）。"""
    try:
        lock = json.loads((config.load().root / "Package.resolved").read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return []
    pins = lock.get("pins") or lock.get("object", {}).get("pins", [])
    return [{"identity": p.get("identity"), "revision": (p.get("state") or {}).get("revision")}
            for p in pins]


def snapshot():
    """即時取得版本和近期提交；不把 Git 修改檔案推測成新增功能。"""
    data = {"features": validate(), "repos": [], "symbols": [], "documents": [],
            "languages": SUPPORTED_LANGUAGES}
    for repo, root in roots().items():
        data["repos"].append({
            "name": repo,
            "head": git(root, "rev-parse", "HEAD").strip(),
            "changes": git(root, "status", "--short"),
            "commits": _parse_commits(git(
                root, "log", "-20", "--date=iso-strict",
                "--format=%x1e%h%x1f%ad%x1f%s", "--name-only")),
        })
        for name in files(root):
            try:
                path = (root / name).resolve()
                if not path.is_relative_to(root.resolve()) or path.stat().st_size > 2_000_000:
                    continue
                text = path.read_text(encoding="utf-8", errors="replace")
            except (ValueError, OSError):
                continue
            if name.endswith(".md"):
                data["documents"].append({"name": name, "repo": repo, "url": link(repo, name),
                                          "text": text[:100000]})
                continue
            data["symbols"].extend(scan_symbols(text, repo, name))
    data["lockedPackages"] = _locked_packages()
    return data


def _file_page(repo, name, line):
    """組出檔案檢視頁（含行號、目標行與語法上色用的 .code 容器）。"""
    source = safe_file(repo, name).read_text(encoding="utf-8", errors="replace")
    content = "".join(
        '<span class="ln" id="L%d"><a class="no" href="#L%d">%5d</a>'
        '<span class="code">%s</span></span>' % (i, i, i, html.escape(text))
        for i, text in enumerate(source.splitlines(), 1)
    )
    return assets.render(
        "file.html",
        title=html.escape(name), repo=html.escape(repo), path=html.escape(name),
        line=str(line), content=content,
        i18n_json=json.dumps(i18n.js_dict(), ensure_ascii=False), **i18n.subs())


def route(path, query):
    """回傳 (HTTP 狀態, 內容, MIME)，由既有本機工具提供服務。"""
    try:
        if path == "/development":
            return 200, assets.render("dev.html",
                                      i18n_json=json.dumps(i18n.js_dict(), ensure_ascii=False),
                                      **i18n.subs()), "text/html; charset=utf-8"
        if path == "/development/data":
            return 200, json.dumps(snapshot(), ensure_ascii=False), "application/json; charset=utf-8"
        if path == "/development/file":
            values = parse_qs(query)
            repo = values.get("repo", [default_repo()])[0]
            name = values.get("path", [""])[0]
            line_arg = values.get("line", [""])[0]
            line = int(line_arg) if line_arg.isdigit() else 0
            return 200, _file_page(repo, name, line), "text/html; charset=utf-8"
        if path == "/development/diff":
            values = parse_qs(query)
            repo = values.get("repo", [default_repo()])[0]
            rev = values.get("hash", [""])[0]
            name = values.get("path", [""])[0]
            worktree = values.get("worktree", ["0"])[0] in ("1", "true", "yes")
            return 200, json.dumps(diff(repo, rev, name, worktree), ensure_ascii=False), \
                "application/json; charset=utf-8"
    except (ValueError, OSError, subprocess.TimeoutExpired) as error:
        return 400, json.dumps({"error": str(error)}, ensure_ascii=False), "application/json; charset=utf-8"
    return 404, "找不到頁面", "text/plain; charset=utf-8"


if __name__ == "__main__":
    print("功能索引驗證通過：", len(validate()), "項")
