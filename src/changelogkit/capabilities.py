"""已知功能的機器可讀清單（``changelogkit capabilities``）。

這份清單刻意只描述**穩定的功能邊界**，不重抄所有旗標與欄位；旗標仍以
``--help`` 與 ``Docs/usage.md`` 為準。技能可先讀本清單，再依版本決定是否
具備某項能力；清單未列出的功能不代表不存在，必須回頭查目前版本。
"""

import json

from . import buildinfo

SCHEMA = 1

# 建立清單時的人工維護區：新增功能時同步補上，避免技能只能猜。
FEATURES = [
    {
        "id": "history.core",
        "summary": "Parse, insert, edit, delete and sort ChangeHistory-style Markdown entries.",
        "surfaces": ["cli", "web"],
        "config": ["history"],
    },
    {
        "id": "history.cli",
        "summary": "CLI add/list/show/sort/backfill-dates for change history.",
        "surfaces": ["cli"],
        "commands": ["add", "list", "show", "sort", "backfill-dates"],
    },
    {
        "id": "dev.index",
        "summary": "Development index: features, source symbols, documents and recent commits.",
        "surfaces": ["web", "static"],
        "config": ["features", "sources", "include", "exclude", "recent_commits"],
    },
    {
        "id": "symbols.scan",
        "summary": "Source-level API declaration scanning for supported languages.",
        "surfaces": ["cli", "web", "static"],
        "commands": ["symbols", "languages"],
    },
    {
        "id": "docs.classification",
        "summary": "Document groups, notes, colors, folder fallback and group filters.",
        "surfaces": ["cli", "web", "static"],
        "config": ["docs.unlisted", "docs.auto", "docs.groups", "docs.entries"],
        "commands": ["docs", "docs-init"],
    },
    {
        "id": "docs.localized",
        "summary": "Localized group and entry titles/notes.",
        "surfaces": ["web", "static"],
        "config": ["docs.groups", "docs.entries"],
    },
    {
        "id": "todo",
        "summary": "TODO.md task parsing, filtering, progress and live refresh.",
        "surfaces": ["web", "static"],
        "config": ["todo"],
    },
    {
        "id": "static.export",
        "summary": "Read-only static site export with stable document URLs and per-commit pages.",
        "surfaces": ["cli", "static"],
        "commands": ["export"],
    },
    {
        "id": "static.search",
        "summary": "Client-side document search on the static development index.",
        "surfaces": ["static"],
    },
    {
        "id": "api.docs",
        "since": "0.12.11",
        "summary": "Mount one or more local HTML or external API documentation sites.",
        "surfaces": ["web", "static"],
        "config": ["api"],
    },
    {
        "id": "serve.lan",
        "since": "0.13.0",
        "summary": "Optional LAN binding with read-only default for non-loopback clients.",
        "surfaces": ["cli", "web"],
        "commands": ["serve"],
    },
    {
        "id": "static.footer-timezone",
        "since": "0.13.1",
        "summary": "Static footer time with UTC offset and configurable timezone/epoch.",
        "surfaces": ["static"],
        "config": ["timezone"],
    },
    {
        "id": "static.footer-local",
        "since": "0.13.2",
        "summary": "Browser-localized static footer time with a no-JS fallback.",
        "surfaces": ["static"],
    },
    {
        "id": "i18n",
        "summary": "UI and CLI localization (en, zh-TW, zh-CN, ja).",
        "surfaces": ["cli", "web", "static"],
    },
    {
        "id": "capabilities",
        "since": "0.13.3",
        "summary": "Machine-readable known-feature and command index.",
        "surfaces": ["cli"],
        "commands": ["capabilities"],
    },
]

COMMANDS = [
    "serve",
    "add",
    "list",
    "show",
    "languages",
    "locales",
    "docs",
    "docs-init",
    "symbols",
    "export",
    "backfill-dates",
    "sort",
    "community-init",
    "capabilities",
]

CONFIG_KEYS = [
    "title",
    "project",
    "timezone",
    "history",
    "todo",
    "features",
    "community",
    "assets",
    "recent_commits",
    "sources",
    "include",
    "exclude",
    "docs",
    "api",
]

NOTES = [
    "This is a known-feature index, not an exhaustive command/config reference.",
    "If a requested feature is absent, inspect --help, Docs/usage.md and the installed source before assuming support.",
]


def snapshot():
    """回傳目前安裝版本的能力清單（可直接序列化為 JSON）。"""
    return {
        "schema": SCHEMA,
        "tool": "changelogkit",
        "version": buildinfo.version(),
        "commit": buildinfo.commit(),
        "scope": "known features; not exhaustive",
        "features": [dict(feature) for feature in FEATURES],
        "commands": list(COMMANDS),
        "config": list(CONFIG_KEYS),
        "notes": list(NOTES),
    }


def dumps():
    """輸出穩定的 JSON；技能與腳本應使用這個格式。"""
    return json.dumps(snapshot(), ensure_ascii=False, indent=2)


def render():
    """人類可讀摘要；``--json`` 才是給程式解析的介面。"""
    data = snapshot()
    lines = [
        "changelogkit %s (%s)" % (data["version"], data["commit"] or "unknown"),
        "capabilities schema %d · %s" % (data["schema"], data["scope"]),
        "",
        "Features:",
    ]
    for feature in data["features"]:
        since = " (since %s)" % feature["since"] if feature.get("since") else ""
        lines.append("  %-24s %s%s" % (feature["id"], feature["summary"], since))
    lines += ["", "Commands: " + ", ".join(data["commands"])]
    return "\n".join(lines)
