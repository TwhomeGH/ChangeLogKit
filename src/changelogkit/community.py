"""維護者的「社群與開發交流」區塊：解析 ``Docs/community.md``（慣例格式）並組出 HTML。

慣例格式（刻意極簡，重用既有 markdown 渲染器，不新增方言）::

    # <區塊標題>
    ## <卡片標題>
    <卡片說明（markdown）>
    [<行動文字>](<連結>)

* 第一個 ``#`` 為區塊標題；每個 ``##`` 起一張卡片。
* 卡片內**獨立成行的第一個連結**作為行動按鈕，該行不列入說明。
* 說明文的 markdown 由前端就地渲染；相對連結以本檔所在目錄為基準改寫
  （見 ``assets/markdown.js`` 的解析器）。

工具只在使用者執行 ``community-init`` 時寫入此檔；``serve``／``export`` 一律唯讀。
"""

import html
import re

from . import config

_H1 = re.compile(r"^\s{0,3}#\s+(.*?)\s*#*\s*$")
_H2 = re.compile(r"^\s{0,3}##\s+(.*?)\s*#*\s*$")
_ACTION = re.compile(r"^\s*\[([^\]]+)\]\(([^)\s]+)(?:\s+\"[^\"]*\")?\)\s*$")


def _finish(title, body_lines):
    """把一張卡片的原始行整理成 ``{title, body, action}``。"""
    action = None
    kept = []
    for line in body_lines:
        match = _ACTION.match(line)
        if match and action is None:      # 第一個獨立成行的連結 = 行動按鈕
            action = {"text": match.group(1).strip(), "href": match.group(2).strip()}
            continue
        kept.append(line)
    return {"title": title, "body": "\n".join(kept).strip("\n"), "action": action}


def parse(text):
    """解析慣例格式，回傳 ``{title, cards: [{title, body, action}]}``。"""
    lines = (text or "").replace("\r\n", "\n").split("\n")
    title, start = "", 0
    for index, line in enumerate(lines):
        match = _H1.match(line)
        if match:
            title, start = match.group(1).strip(), index + 1
            break
    cards, current, buf = [], None, []
    for line in lines[start:]:
        heading = _H2.match(line)
        if heading:
            if current is not None:
                cards.append(_finish(current, buf))
            current, buf = heading.group(1).strip(), []
            continue
        if current is not None:
            buf.append(line)
    if current is not None:
        cards.append(_finish(current, buf))
    return {"title": title, "cards": cards}


def load():
    """讀取設定的社群檔並解析；未設定或檔案不存在時回 None（該區塊不顯示）。"""
    path = config.load().community
    if path is None or not path.exists():
        return None
    return parse(path.read_text(encoding="utf-8", errors="replace"))


def html_block(data, default_title="Community"):
    """解析結果 → ``<section class="community">`` HTML；無卡片時回空字串。

    說明與行動連結都以 ``<template>`` 內嵌 markdown（HTML 轉義），由前端
    ``markdown.js`` 連同相對連結改寫一起渲染——與站內其他 markdown 走同一條路徑。
    """
    if not data or not data["cards"]:
        return ""
    cards = []
    for card in data["cards"]:
        parts = ["<h3>%s</h3>" % html.escape(card["title"])]
        if card["body"]:
            parts.append('<div class="rendered" data-md><template>%s</template></div>'
                         % html.escape(card["body"]))
        if card["action"]:
            link = "[%s](%s)" % (card["action"]["text"], card["action"]["href"])
            parts.append('<div class="rendered action" data-md><template>%s</template></div>'
                         % html.escape(link))
        cards.append('<article class="card">%s</article>' % "".join(parts))
    return ('<section class="community" id="community" aria-labelledby="community-title">'
            '<h2 class="section-title" id="community-title">%s</h2>'
            '<div class="cards">%s</div></section>'
            % (html.escape(data["title"] or default_title), "".join(cards)))


_TEMPLATE = """# 社群與開發交流

## 專案原始碼
問題回報、功能建議與開發討論。
[前往 GitHub →]({repo})

## 意見回饋
使用心得與需求都歡迎提出。
[開啟 Issues →]({issues})
"""


def template():
    """預設範本；能由 origin remote 判定 repo 時帶入連結，否則用 ``OWNER/REPO`` 佔位。"""
    from . import buildinfo

    slug = buildinfo.origin_slug()
    base = ("https://github.com/" + slug) if slug else "https://github.com/OWNER/REPO"
    return _TEMPLATE.format(repo=base, issues=base + "/issues")


def write_template():
    """把範本寫入設定的社群檔；已存在則不覆蓋。回傳 ``(path, created)``。"""
    path = config.load().community
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        return path, False
    path.write_text(template(), encoding="utf-8")
    return path, True
