"""Verify the package version and ``src`` fallback match a release tag."""

import argparse
import re
import sys
from pathlib import Path

try:
    import tomllib
except ModuleNotFoundError:  # Python 3.10
    import tomli as tomllib

ROOT = Path(__file__).resolve().parents[1]
VERSION_FILE = ROOT / "pyproject.toml"
INIT_FILE = ROOT / "src" / "changelogkit" / "__init__.py"


def package_version():
    """Read ``[project].version`` from pyproject.toml."""
    data = tomllib.loads(VERSION_FILE.read_text(encoding="utf-8"))
    return str(data["project"]["version"])


def fallback_version():
    """Read the literal fallback in ``__init__.py``."""
    match = re.search(r'or\s+"([^"]+)"', INIT_FILE.read_text(encoding="utf-8"))
    return match.group(1) if match else ""


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--tag", default="", help="release tag, e.g. v0.11.1")
    args = parser.parse_args(argv)
    version = package_version()
    fallback = fallback_version()
    errors = []
    if fallback != version:
        errors.append("src fallback %r != pyproject %r" % (fallback, version))
    if args.tag and args.tag != "v" + version:
        errors.append("tag %r != v%s" % (args.tag, version))
    if errors:
        for error in errors:
            print("ERROR: " + error, file=sys.stderr)
        return 1
    print("version OK: %s%s" % (version, (" (%s)" % args.tag) if args.tag else ""))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
