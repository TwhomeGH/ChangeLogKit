"""從 git 回填變更歷史條目的日期（收編既有 changelog 用）。

對每個「標題沒有日期」的條目，找出它**首次出現的 commit**，用該 commit 的時間補成
``## YYYY.MM.DD HH:MM 標題``。預設只回報（dry-run）；``apply=True`` 才寫回。

設計：

* 日期來源優先序：條目緊接的 ``**時間**：<date>`` 宣告行 → git 首次加入的 commit。
* git 搜尋字串：編號式的 ``## N.``（穩定，標題被改過也找得到）；否則用整行標題（best-effort）。
* 找不到日期者**保持原樣**並在報告中列出（不填假日期）。
* ``strip_number``：順便去掉 ``## N.`` 與 ``### Na.`` 的編號。
* ``sort``：依補好的日期由新到舊重排（無日期者排最後）。
"""

import os
import re
import subprocess
from datetime import datetime

from . import config

DATED = re.compile(r"^## \d{4}\.\d{2}\.\d{2}(?:\s+\d{2}:\d{2})?\s+")
NUM = re.compile(r"^(\d+)\.\s+(.*)$")
SUBNUM = re.compile(r"^### \d+[a-z]?(?:\.\d+)*\.?\s+(.*)$")
DECL = re.compile(r"^\*\*時間\*\*[：:]\s*(.+)")
DECL_DATE = re.compile(r"(\d{4})[/.](\d{1,2})[/.](\d{1,2})(?:\s+(\d{1,2}):(\d{2}))?")
STAMP = "%s.%02d.%02d %02d:%02d"


def _first_add(root, relpath, needle):
    """``needle`` 首次出現在該檔案的 commit 作者時間（epoch）；找不到回 None。"""
    r = subprocess.run(["git", "-C", str(root), "log", "--reverse", "--format=%at",
                        "-S", needle, "--", relpath], capture_output=True, text=True)
    vals = [l.strip() for l in r.stdout.splitlines() if l.strip().isdigit()]
    return int(vals[0]) if vals else None


def _stamp_from_decl(text):
    m = DECL_DATE.search(text)
    if not m:
        return None
    y, mo, d, hh, mm = m.groups()
    return STAMP % (y, int(mo), int(d), int(hh or 0), int(mm or 0))


def _strip_subs(lines):
    """去掉子標題的編號（``### 73a.``／``### 4.1`` → ``### 標題``）。"""
    return [SUBNUM.sub(r"### \1", l) if SUBNUM.match(l) else l for l in lines]


def _sort_entries(lines):
    """依條目標題日期由新到舊重排（無日期者殿後）。前置內容維持在最上方。"""
    heads = [i for i, l in enumerate(lines) if l.startswith("## ")]
    if not heads:
        return lines
    pre = lines[:heads[0]]
    entries = [lines[heads[k]:(heads[k + 1] if k + 1 < len(heads) else len(lines))]
               for k in range(len(heads))]
    keyed = [(entries[k][0] if DATED.match(entries[k][0]) else "", entries[k])
             for k in range(len(entries))]
    dated = sorted([k for k in keyed if k[0]], key=lambda x: x[0], reverse=True)
    undated = [k for k in keyed if not k[0]]
    out = list(pre)
    for _, entry in dated + undated:
        out += entry
    return out


def backfill(apply=False, strip_number=False, sort=False):
    """回填日期。回傳 ``{"total", "converted", "skipped", "applied", "items"}``。

    ``items`` 為 ``(status, before, after, source)``；``status`` ∈ ok／skip。
    """
    cfg = config.load()
    path = cfg.history
    if not path.exists():
        return {"total": 0, "converted": 0, "skipped": 0, "applied": False, "items": []}
    rel = os.path.relpath(path, cfg.root).replace("\\", "/")
    lines = path.read_text(encoding="utf-8").splitlines()

    heads = [i for i, l in enumerate(lines) if l.startswith("## ")]
    out = list(lines[:heads[0]]) if heads else list(lines)
    items, total, converted, skipped, changed = [], 0, 0, 0, False
    for k, h in enumerate(heads):
        end = heads[k + 1] if k + 1 < len(heads) else len(lines)
        chunk = lines[h:end]
        head = lines[h]
        if DATED.match(head):
            body = _strip_subs(chunk) if strip_number else chunk
            if body != chunk:
                changed = True
            out += body
            continue
        total += 1
        body = head[3:].strip()
        m = NUM.match(body)
        num, title = (m.group(1), m.group(2).strip()) if m else (None, body)

        stamp, decl_idx = None, None
        for j in range(1, min(6, len(chunk))):
            md = DECL.match(chunk[j])
            if md:
                stamp, decl_idx = _stamp_from_decl(md.group(1)), j
                break
        source = "declared"
        if not stamp:
            ep = _first_add(cfg.root, rel, "## %s." % num if num else head)
            if ep:
                stamp = datetime.fromtimestamp(ep).strftime("%Y.%m.%d %H:%M")
                source = "git"
        if not stamp:
            skipped += 1
            items.append(("skip", head, "", ""))
            out += chunk
            continue

        new_head = "## %s %s" % (stamp, title)
        drop = set()
        if decl_idx is not None:
            # 移除宣告時間行的同時，也去掉緊鄰的一個空行，避免留下連續空行（markdownlint MD012）。
            drop.add(decl_idx)
            if chunk[decl_idx - 1].strip() == "":
                drop.add(decl_idx - 1)
            elif decl_idx + 1 < len(chunk) and chunk[decl_idx + 1].strip() == "":
                drop.add(decl_idx + 1)
        rest = [chunk[idx] for idx in range(1, len(chunk)) if idx not in drop]
        if strip_number:
            stripped = _strip_subs(rest)
            if stripped != rest:
                changed = True
            rest = stripped
        converted += 1
        items.append(("ok", head, new_head, source))
        out.append(new_head)
        out += rest

    if sort:
        out = _sort_entries(out)
    applied = False
    if apply and (converted or changed):
        path.write_text("\n".join(out).rstrip() + "\n", encoding="utf-8")
        applied = True
    return {"total": total, "converted": converted, "skipped": skipped,
            "applied": applied, "items": items}
