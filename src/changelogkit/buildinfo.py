"""版本與來源資訊。

``changelogkit --version`` 會顯示版本，並盡量附上**此安裝的來源 commit**。
取得順序（任一成功即用）：

1. 建置時蓋章的 ``_buildinfo.py``（打包時寫入，隨 wheel 帶走）。
2. 套件目錄本身是 git checkout（例如以 ``PYTHONPATH=src`` 直接跑）。
3. pip 的 ``direct_url.json``（``pip install <路徑>`` 會記錄來源目錄）。
"""

import json
import re
import subprocess
from importlib import metadata
from pathlib import Path
from urllib.parse import unquote, urlparse

from . import __version__


def _git_head(path):
    """回傳 ``<短hash>[+dirty]``；非 git 或失敗回空字串。"""
    try:
        out = subprocess.run(["git", "-C", str(path), "rev-parse", "--short", "HEAD"],
                             capture_output=True, text=True, timeout=5)
        if out.returncode:
            return ""
        head = out.stdout.strip()
        dirty = subprocess.run(["git", "-C", str(path), "status", "--porcelain"],
                               capture_output=True, text=True, timeout=5).stdout.strip()
        return head + ("+dirty" if dirty else "")
    except Exception:
        return ""


def _from_direct_url():
    """讀 pip ``direct_url.json`` 的來源目錄，嘗試取 commit。"""
    try:
        raw = metadata.distribution("changelogkit").read_text("direct_url.json")
        url = (json.loads(raw) or {}).get("url", "")
        if not url.startswith("file:"):
            return ""
        path = unquote(urlparse(url).path)
        if re.match(r"^/[A-Za-z]:", path):   # Windows：file:///C:/… → /C:/…
            path = path[1:]
        return _git_head(Path(path))
    except Exception:
        return ""


def commit():
    """盡量找出此安裝的來源 commit（失敗回空字串）。"""
    try:
        from . import _buildinfo
        stamped = getattr(_buildinfo, "COMMIT", "")
        if stamped:
            return stamped + ("+dirty" if getattr(_buildinfo, "DIRTY", False) else "")
    except Exception:
        pass
    return _git_head(Path(__file__).resolve().parent) or _from_direct_url()


def version():
    """純版本號（如 ``0.1.0``）。"""
    return __version__


def version_string():
    """``--version`` 要印的一行字。"""
    source = commit()
    return "changelogkit %s%s" % (__version__, (" (%s)" % source) if source else "")
