"""hatchling 建置掛鉤：打包時把來源 commit 蓋章進套件。

產生 ``src/changelogkit/_buildinfo.py``（COMMIT／DIRTY／BUILT_AT），
讓**從 PyPI 安裝**的版本也能在 ``changelogkit --version`` 報出來源 commit。

此檔於建置時產生，已列入 ``.gitignore``（不要在版本控管裡手改）。因為被
gitignore，hatchling 預設不會將它納入 wheel，所以這裡用 ``force_include``
明確帶進 ``changelogkit/_buildinfo.py``。
"""

import datetime
import re
import subprocess
from pathlib import Path

from hatchling.builders.hooks.plugin.interface import BuildHookInterface

STAMP = "src/changelogkit/_buildinfo.py"


def _git(root, *args):
    """對 ``root`` 跑 git，成功回標準輸出去尾空白，失敗回空字串。"""
    try:
        out = subprocess.run(["git", "-C", str(root), *args], capture_output=True, text=True, timeout=10)
        return out.stdout.strip() if out.returncode == 0 else ""
    except Exception:
        return ""


def _read_stamp(target):
    """讀既有蓋章檔的 ``(COMMIT, DIRTY)``；沒有或無效回 ``None``。"""
    try:
        text = target.read_text(encoding="utf-8")
    except Exception:
        return None
    found = re.search(r"COMMIT = '([^']*)'", text)
    if not (found and found.group(1)):
        return None
    dirty = re.search(r"DIRTY = (True|False)", text)
    return found.group(1), (dirty and dirty.group(1) == "True")


class BuildInfoHook(BuildHookInterface):
    """在打包前寫入 ``_buildinfo.py`` 並強制納入 wheel。"""

    def initialize(self, version, build_data):
        root = Path(self.root)
        target = root / STAMP
        commit = _git(root, "rev-parse", "--short", "HEAD")
        dirty = bool(_git(root, "status", "--porcelain"))
        if not commit:
            # 沒有 git（例如從 sdist 解壓後建 wheel）：沿用既有蓋章，別覆蓋成空。
            prior = _read_stamp(target)
            if prior:
                commit, dirty = prior
        built_at = datetime.datetime.now().astimezone().strftime("%Y-%m-%d %H:%M %z")
        target.write_text(
            '"""建置時產生（見 hatch_build.py）；請勿手改。"""\n'
            "COMMIT = %r\n"
            "DIRTY = %r\n"
            "BUILT_AT = %r\n" % (commit, dirty, built_at),
            encoding="utf-8",
        )
        # 被 .gitignore 的檔案預設不會進 wheel，這裡明確帶上。
        build_data.setdefault("force_include", {})[str(target)] = STAMP[len("src/") :]
        self.app.display_info(
            "changelogkit buildinfo：%s%s @ %s" % (commit or "(非 git)", "+dirty" if dirty else "", built_at)
        )
