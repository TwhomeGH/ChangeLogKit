"""文件分類：依 ``.changelog.toml`` 的 ``[tool.changelog.docs]`` 把文件分群。

設定形狀::

    [tool.changelog.docs]
    unlisted = "other"          # other（預設）／folder／hidden
    auto     = true             # 未命中設定時依資料夾自動分類（預設開）

    [[tool.changelog.docs.groups]]
    id = "dev"
    title = "開發者指南"
    color = "blue"              # 固定色票；未知值退回 slate
    note = "開發流程、測試、資料模型與 API"
    order = 10
    paths = ["Docs/development/**", "Docs/api/**"]

    [[tool.changelog.docs.entries]]
    path = "Docs/onboarding.md" # 精確路徑或 glob
    title = "新手導覽"
    note = "第一次接手從這裡開始"
    group = "dev"               # 可省略；省略時仍由 groups.paths 決定

判定順序：entries 覆寫 → groups.paths（同一份文件最多命中一個群組）
→ 資料夾自動分類（``auto = true``，預設開）→ unlisted。
設定問題（重疊、未知群組／顏色、沒命中的 pattern）只回警告，不讓服務中斷；
未分類文件預設進「其他」，不會消失。
"""

from pathlib import PurePosixPath

from . import config
from .globs import matches

PALETTE = ("blue", "green", "amber", "violet", "rose", "cyan", "slate")
DEFAULT_COLOR = "slate"
UNLISTED_ID = "other"
UNLISTED_ORDER = 9999
UNLISTED_MODES = ("other", "folder", "hidden")

# 自動分類（config 沒有命中時才用）：資料夾名稱 → 群組。
AUTO_GROUPS = {
    "dev": {"titleKey": "docs.auto.dev", "color": "blue", "order": 10},
    "guide": {"titleKey": "docs.auto.guide", "color": "green", "order": 20},
    "ops": {"titleKey": "docs.auto.ops", "color": "amber", "order": 30},
    "design": {"titleKey": "docs.auto.design", "color": "rose", "order": 40},
}
AUTO_FOLDERS = {
    "api": "dev", "apis": "dev", "development": "dev", "dev": "dev",
    "guide": "guide", "guides": "guide", "manual": "guide", "usage": "guide",
    "deploy": "ops", "deployment": "ops", "ops": "ops", "operations": "ops",
    "design": "design", "adr": "design", "architecture": "design",
}


def normalize(path):
    """正規化文件路徑：反斜線轉 ``/``、去掉開頭的 ``./`` 與多餘斜線。"""
    text = str(path or "").replace("\\", "/")
    while text.startswith("./"):
        text = text[2:]
    return text.strip("/")


def _has_glob(pattern):
    return "*" in pattern or "?" in pattern


def _entry_for(name, entries):
    """回傳第一個命中的 entry；精確路徑與 glob 都支援，依宣告順序。"""
    for entry in entries:
        pattern = normalize(entry.path)
        if pattern == name or (_has_glob(pattern) and matches(pattern, name)):
            return entry
    return None


def _default_title(name):
    """沒有 entry.title 時的顯示標題：``README.md`` 用資料夾名，其餘用檔名去副檔名。"""
    path = PurePosixPath(name)
    if path.stem.lower() == "readme":
        return path.parent.name or path.stem
    return path.stem or path.name


def _folder(name):
    """未分類改按資料夾分組時使用的名稱（最接近檔案的資料夾）。"""
    return PurePosixPath(name).parent.name or "."


def _group_meta(group):
    """設定群組 → 輸出用的 dict（顏色已正規化）。"""
    return {
        "id": group.id,
        "title": group.title or group.id,
        "titleKey": "",
        "color": group.color if group.color in PALETTE else DEFAULT_COLOR,
        "note": group.note,
        "order": group.order,
    }


def _auto_meta(category):
    """自動分類群組 → 輸出用的 dict；標題交給前端／靜態站的 i18n 解析。"""
    spec = AUTO_GROUPS[category]
    return {
        "id": "auto:" + category,
        "title": "",
        "titleKey": spec["titleKey"],
        "color": spec["color"],
        "note": "",
        "order": spec["order"],
    }


def _auto_group(name):
    """依路徑中的資料夾名稱自動分類；取最深命中的資料夾，沒有回 None。"""
    category = None
    for segment in PurePosixPath(name).parts[:-1]:
        category = AUTO_FOLDERS.get(segment.lower(), category)
    return _auto_meta(category) if category else None


def _resolve_groups(cfg, warnings):
    """驗證並排序設定群組；重複 id 只保留第一個。"""
    seen, groups = set(), []
    for group in cfg.doc_groups:
        if not group.id:
            warnings.append({"type": "group_without_id"})
            continue
        if group.id in seen:
            warnings.append({"type": "duplicate_group", "group": group.id})
            continue
        if group.color not in PALETTE:
            warnings.append({"type": "bad_color", "group": group.id, "color": group.color})
        seen.add(group.id)
        groups.append((_group_meta(group), group))
    return groups


def resolve(documents, cfg=None):
    """把 ``documents`` 分類；回傳 ``(documents, groups, warnings)``。

    每份文件會多出 ``group``／``groupTitle``／``groupColor``／``title``／``note``。
    ``unlisted = "hidden"`` 會直接略過未分類文件；其餘模式不會丟掉任何文件。
    """
    cfg = cfg or config.load()
    warnings = []
    configured = _resolve_groups(cfg, warnings)
    by_id = {meta["id"]: meta for meta, _ in configured}

    mode = cfg.docs_unlisted
    if mode not in UNLISTED_MODES:
        warnings.append({"type": "bad_unlisted", "value": mode})
        mode = "other"

    used_patterns, used_entries = set(), set()
    records = []

    for doc in documents:
        name = normalize(doc.get("name"))
        entry = _entry_for(name, cfg.doc_entries)
        if entry is not None:
            used_entries.add(id(entry))

        # 一律計算群組命中，讓「沒命中的 pattern」警告仍然準確。
        # 同一群組的多個 pattern 都算「用過」，但群組只記一次。
        hits = []
        for meta, group in configured:
            matched = False
            for pattern in group.paths:
                if matches(normalize(pattern), name):
                    used_patterns.add((group.id, pattern))
                    matched = True
            if matched:
                hits.append(meta)

        chosen, blocked = None, False
        if entry is not None and entry.group:
            chosen = by_id.get(entry.group)
            if chosen is None:
                warnings.append({"type": "unknown_group", "path": name, "group": entry.group})
                blocked = True
        elif len(hits) == 1:
            chosen = hits[0]
        elif len(hits) > 1:
            warnings.append({"type": "overlap", "path": name,
                             "groups": [meta["id"] for meta in hits]})
            blocked = True

        # 設定的明確錯誤（未知群組／群組重疊）不猜；其餘才用資料夾自動分類。
        if chosen is None and not blocked and cfg.docs_auto:
            auto = _auto_group(name)
            if auto is not None:
                chosen = by_id.get(auto["id"])
                if chosen is None:
                    chosen = auto
                    by_id[auto["id"]] = chosen

        if chosen is None:
            if mode == "hidden":
                continue
            if mode == "folder":
                folder = _folder(name)
                group_id = "folder:" + folder
                chosen = by_id.get(group_id)
                if chosen is None:
                    chosen = {"id": group_id, "title": folder, "color": DEFAULT_COLOR,
                              "note": "", "order": UNLISTED_ORDER}
                    by_id[group_id] = chosen
            else:
                chosen = by_id.get(UNLISTED_ID)
                if chosen is None:
                    chosen = {"id": UNLISTED_ID, "title": "", "color": DEFAULT_COLOR,
                              "note": "", "order": UNLISTED_ORDER}
                    by_id[UNLISTED_ID] = chosen

        records.append(dict(
            doc,
            title=(entry.title if entry is not None else "") or _default_title(name),
            note=entry.note if entry is not None else "",
            group=chosen["id"],
            groupTitle=chosen["title"],
            groupTitleKey=chosen.get("titleKey", ""),
            groupColor=chosen["color"],
            groupNote=chosen["note"],
            groupOrder=chosen["order"],
        ))

    # 沒命中的設定：通常是檔案改名或 pattern 打錯，讓它們能被看到而不是默默失效。
    for _, group in configured:
        for pattern in group.paths:
            if (group.id, pattern) not in used_patterns:
                warnings.append({"type": "unmatched_pattern", "group": group.id, "pattern": pattern})
    for entry in cfg.doc_entries:
        if id(entry) not in used_entries:
            warnings.append({"type": "unmatched_entry", "path": entry.path})

    # 群組順序：order → 宣告順序；folder 產生的群組依名稱排序。
    configured_ids = {meta["id"] for meta, _ in configured}
    extra = [meta for key, meta in by_id.items() if key not in configured_ids]
    extra.sort(key=lambda meta: meta["title"])
    groups = [meta for meta, _ in configured] + extra
    groups.sort(key=lambda meta: (meta["order"],
                                  meta["title"] if meta["id"].startswith("folder:") else ""))
    index = {meta["id"]: i for i, meta in enumerate(groups)}
    records.sort(key=lambda record: index.get(record["group"], UNLISTED_ORDER))
    return records, groups, warnings
