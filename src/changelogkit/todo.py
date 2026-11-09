"""TODO.md 的 checkbox 解析與唯讀 HTML 呈現。"""

import hashlib
import html
import re
from pathlib import Path

from . import i18n

_HEADING = re.compile(r"^(#{1,6})\s+(.*)$")
_CHECKBOX = re.compile(r"^(\s*)[-*+]\s+\[([ xX])\]\s+(.*)$")


def version(path):
    """檔案內容 digest，供前端判斷是否需要更新。"""
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def parse(path):
    """讀取 TODO markdown；無法讀取時回空結果。"""
    try:
        text = Path(path).read_text(encoding="utf-8", errors="replace")
    except OSError:
        return {"sections": [], "total": 0, "done": 0, "open": 0}
    return parse_text(text)


def parse_text(text):
    """解析標題與 ``- [ ]``／``- [x]``；忽略程式碼區塊內的內容。

    回傳 ``sections``（只含有項目的段落）、``total``／``done``／``open`` 計數。
    每個項目含 ``text``／``done``／``line``／``indent``。
    """
    sections = []
    current = {"title": "", "level": 0, "items": []}
    fence = ""
    for number, raw in enumerate(text.splitlines(), 1):
        stripped = raw.strip()
        if stripped.startswith(("```", "~~~")):
            marker = stripped[:3]
            if not fence:
                fence = marker
            elif fence == marker:
                fence = ""
            continue
        if fence:
            continue
        heading = _HEADING.match(stripped)
        if heading:
            if current["items"]:
                sections.append(current)
            current = {"title": heading.group(2).strip(), "level": len(heading.group(1)), "items": []}
            continue
        task = _CHECKBOX.match(raw)
        if task:
            current["items"].append(
                {
                    "text": task.group(3).strip(),
                    "done": task.group(2).lower() == "x",
                    "line": number,
                    "indent": len(task.group(1).expandtabs(4)),
                }
            )
    if current["items"]:
        sections.append(current)
    total = sum(len(section["items"]) for section in sections)
    done = sum(1 for section in sections for item in section["items"] if item["done"])
    return {"sections": sections, "total": total, "done": done, "open": total - done}


def has_tasks(data):
    """解析結果是否至少有一個待辦項目。"""
    return bool(data.get("total"))


def render(data):
    """把解析結果轉成唯讀任務清單 HTML（動態與靜態共用）。"""
    out = []
    for index, section in enumerate(data.get("sections") or []):
        items = section.get("items") or []
        if not items:
            continue
        done = sum(1 for item in items if item["done"])
        title = section.get("title") or i18n.t("todo.untitled")
        out.append('<section class="todo-section" id="todo-sec-%d" data-section>' % index)
        out.append('<h2>%s <span class="count">(%d/%d)</span></h2>' % (html.escape(title), done, len(items)))
        out.append("<ul>")
        for item in items:
            depth = min(item.get("indent", 0) // 2, 5)
            label = html.escape(item["text"])
            out.append(
                '<li class="todo-item%s depth-%d" data-done="%s">'
                '<span class="tick" aria-hidden="true">%s</span>'
                '<span class="label" data-raw="%s">%s</span></li>'
                % (
                    " done" if item["done"] else "",
                    depth,
                    "true" if item["done"] else "false",
                    "✓" if item["done"] else "",
                    label,
                    label,
                )
            )
        out.append("</ul></section>")
    return "\n".join(out)
