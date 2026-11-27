"""GitHub Actions workflow scan and optional action-runtime enrichment.

Local refs are always available without network. Runtime metadata lives in
each action repository's ``action.yml``; it is fetched only when a GitHub
token or an authenticated ``gh`` CLI is available. Without either, runtime is
reported as ``unknown`` rather than guessed.
"""

import base64
import html
import json
import os
import re
import shutil
import subprocess
import time
import urllib.error
import urllib.parse
import urllib.request

from . import i18n

API = "https://api.github.com"
EOL_NODES = {"node12", "node16", "node20"}
CACHE_TTL = 600
_cache = {}
_USES = re.compile(r"^\s*(?:-\s*)?uses:\s*[\"']?([^\"'\s#]+)")


def _esc(value):
    return html.escape(str(value or ""), quote=True)


def _auth_mode():
    """回傳 env／gh／none；不讀取或回傳 token 本身。"""
    if os.environ.get("GITHUB_TOKEN") or os.environ.get("GH_TOKEN"):
        return "env"
    if shutil.which("gh"):
        return "gh"
    return "none"


def _http_json(endpoint, token):
    request = urllib.request.Request(
        API + endpoint,
        headers={
            "Authorization": "Bearer " + token,
            "Accept": "application/vnd.github+json",
            "User-Agent": "changelogkit-workflows",
        },
    )
    with urllib.request.urlopen(request, timeout=15) as response:
        return json.load(response)


def _gh_json(endpoint):
    """用已登入的 gh CLI 查詢；不把 token 帶進 changelogkit process。"""
    try:
        result = subprocess.run(
            ["gh", "api", endpoint],
            capture_output=True,
            text=True,
            timeout=20,
        )
    except (OSError, subprocess.SubprocessError):
        return None
    if result.returncode:
        return None
    try:
        return json.loads(result.stdout)
    except json.JSONDecodeError:
        return None


def _fetch_action_yml(repo, action_path, ref):
    """取得 action.yml 內容；回傳 ``(text, reason)``。"""
    mode = _auth_mode()
    if mode == "none":
        return None, "no-auth"
    token = os.environ.get("GITHUB_TOKEN") or os.environ.get("GH_TOKEN")
    names = []
    if action_path:
        names.append(action_path.rstrip("/") + "/action.yml")
        names.append(action_path.rstrip("/") + "/action.yaml")
    names += ["action.yml", "action.yaml"]
    for name in names:
        query = urllib.parse.urlencode({"ref": ref})
        endpoint = "/repos/%s/contents/%s?%s" % (repo, name, query)
        data = None
        if token:
            try:
                data = _http_json(endpoint, token)
            except urllib.error.HTTPError as error:
                if error.code == 404:
                    continue
                return None, "http-%d" % error.code
            except (OSError, ValueError):
                return None, "network"
        else:
            data = _gh_json(endpoint)
            if data is None:
                return None, "gh-auth"
        if not isinstance(data, dict) or not data.get("content"):
            continue
        try:
            return base64.b64decode(data["content"]).decode("utf-8", errors="replace"), ""
        except (ValueError, TypeError):
            continue
    return None, "metadata-missing"


def _runtime(repo, action_path, ref):
    """查詢 action runtime，回傳 ``(runtime, reason)``。"""
    key = (repo, action_path, ref)
    now = time.monotonic()
    cached = _cache.get(key)
    if cached and now - cached[0] < CACHE_TTL:
        return cached[1], cached[2]
    text, reason = _fetch_action_yml(repo, action_path, ref)
    if text is None:
        result = ("", reason)
    else:
        match = re.search(r"^\s*using:\s*['\"]?([A-Za-z0-9_-]+)", text, re.MULTILINE)
        result = ((match.group(1).lower() if match else ""), "" if match else "using-missing")
    _cache[key] = (now, result[0], result[1])
    return result


def clear_cache():
    """測試或需要重新查詢時清空 runtime cache。"""
    _cache.clear()


def classify(runtime, kind="action"):
    """把 runtime 轉成頁面狀態；未知值不猜測。"""
    if kind == "local":
        return "local"
    if kind == "docker":
        return "docker"
    if kind == "workflow":
        return "workflow"
    value = str(runtime or "").strip().lower()
    if value in EOL_NODES:
        return "eol"
    if value.startswith("node"):
        digits = value[4:]
        if digits.isdigit() and int(digits) >= 24:
            return "ok"
    if value in ("composite", "docker"):
        return "ok"
    return "unknown"


def _parse_uses(uses):
    """拆解 ``owner/repo[/path]@ref``；不支援的值回傳 kind=unknown。"""
    if uses.startswith("./"):
        return {"kind": "local", "repo": "", "path": uses[2:], "ref": ""}
    if uses.startswith("docker://"):
        return {"kind": "docker", "repo": "", "path": uses[len("docker://") :], "ref": ""}
    if "@" not in uses:
        return {"kind": "unknown", "repo": "", "path": uses, "ref": ""}
    target, ref = uses.rsplit("@", 1)
    parts = target.split("/")
    if len(parts) < 2:
        return {"kind": "unknown", "repo": target, "path": "", "ref": ref}
    repo = "/".join(parts[:2])
    action_path = "/".join(parts[2:])
    kind = "workflow" if ".github/workflows/" in action_path else "action"
    return {"kind": kind, "repo": repo, "path": action_path, "ref": ref}


def scan(cfg):
    """掃描 workflow 檔案；只做本地解析，不呼叫網路。"""
    root = cfg.workflows
    data = {"files": [], "actions": [], "auth": _auth_mode(), "warnings": list(cfg.workflow_warnings)}
    if not root:
        return data
    paths = sorted(list(root.glob("*.yml")) + list(root.glob("*.yaml")))
    for path in paths:
        try:
            lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
        except OSError:
            data["warnings"].append("無法讀取 workflow：%s" % path)
            continue
        rel = path.relative_to(cfg.root).as_posix() if path.is_relative_to(cfg.root) else path.as_posix()
        data["files"].append(rel)
        for line_no, line in enumerate(lines, 1):
            if line.lstrip().startswith("#"):
                continue
            match = _USES.match(line)
            if not match:
                continue
            uses = match.group(1).strip()
            if not uses:
                continue
            parsed = _parse_uses(uses)
            data["actions"].append(
                {
                    "workflow": rel,
                    "line": line_no,
                    "uses": uses,
                    "kind": parsed["kind"],
                    "repo": parsed["repo"],
                    "path": parsed["path"],
                    "ref": parsed["ref"],
                    "runtime": "",
                    "status": classify("", parsed["kind"]),
                    "reason": "",
                }
            )
    return data


def enrich(cfg, data):
    """在 scan 結果上補 runtime；沒有認證或關閉時保留 unknown。"""
    if not cfg.workflow_runtime:
        for action in data["actions"]:
            if action["kind"] == "action":
                action["reason"] = "runtime-disabled"
        data["auth"] = "disabled"
        return data
    for action in data["actions"]:
        if action["kind"] != "action":
            continue
        runtime, reason = _runtime(action["repo"], action["path"], action["ref"])
        action["runtime"] = runtime
        action["status"] = classify(runtime, action["kind"])
        action["reason"] = reason
    return data


def report(cfg):
    data = scan(cfg)
    enrich(cfg, data)
    data["summary"] = {
        status: sum(1 for action in data["actions"] if action["status"] == status)
        for status in ("ok", "eol", "unknown", "local", "docker", "workflow")
    }
    return data


def _status_text(status):
    key = {
        "ok": "workflows.ok",
        "eol": "workflows.eol",
        "unknown": "workflows.unknown",
        "local": "workflows.local",
        "docker": "workflows.docker",
        "workflow": "workflows.workflow",
    }.get(status, "workflows.unknown")
    return i18n.t(key)


def _source_link(action):
    repo = action.get("repo") or ""
    ref = action.get("ref") or ""
    if not repo or not ref:
        return _esc(action.get("uses") or "")
    url = "https://github.com/%s/tree/%s" % (repo, urllib.parse.quote(ref, safe=""))
    return '<a href="%s" rel="noopener">%s</a>' % (_esc(url), _esc(action.get("uses") or ""))


def render(data):
    """把 workflow 掃描結果轉成唯讀 HTML（動態與靜態共用）。"""
    actions = data.get("actions") or []
    summary = data.get("summary") or {}
    parts = ['<section class="workflow-summary">']
    parts.append(
        '<span class="muted">%s</span>'
        % _esc(
            i18n.t(
                "workflows.summary",
                actions=len(actions),
                eol=summary.get("eol", 0),
                unknown=summary.get("unknown", 0),
            )
        )
    )
    if data.get("auth") == "none":
        parts.append(
            '<p class="docwarn" data-i18n="workflows.no_auth">%s</p>' % _esc(i18n.t("workflows.no_auth"))
        )
    elif data.get("auth") == "disabled":
        parts.append(
            '<p class="muted" data-i18n="workflows.runtime_disabled">%s</p>'
            % _esc(i18n.t("workflows.runtime_disabled"))
        )
    parts.append("</section>")
    if not actions:
        parts.append('<p class="empty" data-i18n="workflows.empty">%s</p>' % _esc(i18n.t("workflows.empty")))
        return "\n".join(parts)
    parts.append('<div class="workflow-table-wrap"><table class="workflow-table">')
    parts.append(
        "<thead><tr><th>%s</th><th>%s</th><th>%s</th><th>%s</th><th>%s</th></tr></thead><tbody>"
        % (
            _esc(i18n.t("workflows.file")),
            _esc(i18n.t("workflows.action")),
            _esc(i18n.t("workflows.ref")),
            _esc(i18n.t("workflows.runtime")),
            _esc(i18n.t("workflows.status")),
        )
    )
    for action in actions:
        runtime = action.get("runtime") or "—"
        reason = action.get("reason") or ""
        title = (' title="%s"' % _esc(reason)) if reason else ""
        parts.append(
            "<tr>"
            "<td><code>%s:%d</code></td>"
            "<td>%s</td>"
            "<td><code>%s</code></td>"
            "<td><code>%s</code></td>"
            '<td><span class="wf-badge wf-%s"%s>%s</span></td>'
            "</tr>"
            % (
                _esc(action.get("workflow")),
                action.get("line", 0),
                _source_link(action),
                _esc(action.get("ref") or "—"),
                _esc(runtime),
                _esc(action.get("status") or "unknown"),
                title,
                _esc(_status_text(action.get("status") or "unknown")),
            )
        )
    parts.append("</tbody></table></div>")
    return "\n".join(parts)
