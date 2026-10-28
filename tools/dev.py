#!/usr/bin/env python3
"""Run the working-tree changelogkit (``src/``) against another repo.

The installed ``changelogkit`` console script always imports from
``site-packages``. This runner prepends this repository's ``src/`` to
``PYTHONPATH``, changes into the target repo (so its ``.changelog.toml`` is
used), and forwards every remaining argument to ``python -m changelogkit``.

Examples::

    python tools/dev.py --repo F:\\VideoServer serve --port 8710
    python tools/dev.py serve                 # target = current directory
    python tools/dev.py --repo X export out

It never installs anything and never writes to the target repo.
"""

from __future__ import annotations

import argparse
import os
import shlex
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "src"


def find_config(root):
    """往上尋找目標 repo 的 ``.changelog.toml``；找不到回 None。"""
    for directory in [root, *root.parents]:
        candidate = directory / ".changelog.toml"
        if candidate.is_file():
            return candidate
    return None


def build_env(base=None):
    """回傳把 ``src/`` 前置到 ``PYTHONPATH`` 的環境變數。"""
    env = dict(os.environ if base is None else base)
    previous = env.get("PYTHONPATH", "")
    env["PYTHONPATH"] = str(SOURCE) + (os.pathsep + previous if previous else "")
    return env


def _display(command):
    """可讀的指令字串（只供顯示）。"""
    if os.name == "nt":
        return subprocess.list2cmdline(command)
    return " ".join(shlex.quote(part) for part in command)


def main(argv=None):
    parser = argparse.ArgumentParser(
        prog="tools/dev.py",
        description="Run the working-tree changelogkit (src/) against a target repo.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "Examples:\n"
            "  python tools/dev.py --repo F:\\VideoServer serve --port 8710\n"
            "  python tools/dev.py serve --port 8710\n"
            "  python tools/dev.py --repo F:\\VideoServer docs --check\n"
            "  python tools/dev.py --repo F:\\VideoServer docs-init > docs.toml\n"
            "  python tools/dev.py --repo F:\\VideoServer export C:\\Temp\\site\n"
            "\n"
            "Changelogkit's own help (after `--`):\n"
            "  python tools/dev.py -- serve --help\n"
            "  python tools/dev.py -- docs --help\n"
            "\n"
            "Python has no Get-Help; use --help or `python -m pydoc tools.dev`."
        ),
        allow_abbrev=False,
    )
    parser.add_argument("--repo", default="", help="target repo (default: current directory)")
    parser.add_argument("--dry-run", action="store_true", help="print the command and exit")
    raw = list(sys.argv[1:] if argv is None else argv)
    if "--" in raw:
        split = raw.index("--")
        own, tail = raw[:split], raw[split + 1:]
    else:
        own, tail = raw, []
    args, extra = parser.parse_known_args(own)
    forwarded = extra + tail

    target = Path(args.repo or Path.cwd()).expanduser().resolve()
    if not target.is_dir():
        parser.error("not a directory: %s" % target)
    if not (SOURCE / "changelogkit" / "__init__.py").is_file():
        parser.error("source package not found: %s" % SOURCE)

    command = [sys.executable, "-m", "changelogkit", *forwarded]
    # 診斷訊息走 stderr，避免污染 `docs-init > docs.toml` 之類的 stdout 管線。
    print("source : %s" % SOURCE, file=sys.stderr)
    print("target : %s" % target, file=sys.stderr)
    print("config : %s" % (find_config(target) or "(default; no .changelog.toml found)"),
          file=sys.stderr)
    print("command: %s" % _display(command), file=sys.stderr)
    if args.dry_run:
        return 0

    try:
        return subprocess.run(command, cwd=target, env=build_env()).returncode
    except KeyboardInterrupt:
        return 130


if __name__ == "__main__":
    raise SystemExit(main())
