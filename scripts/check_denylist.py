"""Refuse commits that contain deny-listed terms (e.g. confidential names).

The terms themselves are confidential, so they never live in this repo. They come from
the FORGEGRAPH_DENYLIST environment variable (one term per line, or comma-separated) or,
failing that, from ~/.config/forgegraph-dev/denylist.txt. Matching ignores case and also
finds a term inside longer words. Hits are reported by term number, never by the term
itself, so the check is safe to run in CI logs.

Usage: check_denylist.py [FILE ...]   (no files: every file tracked by git)
Set FORGEGRAPH_DENYLIST_REQUIRED=1 to fail when no terms are configured.

Kept compatible with old Python versions, because pre-commit may run it with whatever
`python` is on the PATH.
"""

import os
import re
import subprocess
import sys
from pathlib import Path

DEFAULT_FILE = Path.home() / ".config" / "forgegraph-dev" / "denylist.txt"

# Embedded images (data URIs) are random-looking text that can contain any short term by
# chance; their contents are skipped, keeping line breaks so line numbers stay right.
BASE64_DATA = re.compile(r"(;base64,)([A-Za-z0-9+/=\s]+)")


def _strip_base64(text):
    return BASE64_DATA.sub(lambda m: m.group(1) + "\n" * m.group(2).count("\n"), text)


def load_terms():
    raw = os.environ.get("FORGEGRAPH_DENYLIST", "")
    if not raw.strip() and DEFAULT_FILE.is_file():
        raw = DEFAULT_FILE.read_text(encoding="utf-8")
    terms = []
    for line in raw.replace(",", "\n").splitlines():
        term = line.strip().lower()
        if term and not term.startswith("#"):
            terms.append(term)
    return terms


def tracked_files():
    out = subprocess.run(
        ["git", "ls-files", "-z"], check=True, stdout=subprocess.PIPE
    ).stdout.decode("utf-8")
    return [name for name in out.split("\0") if name]


def scan(paths, terms):
    """Return (path, line number, term number) for every hit."""
    hits = []
    for name in paths:
        path = Path(name)
        if not path.is_file():
            continue
        data = path.read_bytes()
        if b"\0" in data[:8192]:  # binary file, e.g. a font
            continue
        text = _strip_base64(data.decode("utf-8", errors="replace")).lower()
        for lineno, line in enumerate(text.splitlines(), 1):
            for number, term in enumerate(terms, 1):
                if term in line:
                    hits.append((name, lineno, number))
    return hits


def main(argv=None):
    args = sys.argv[1:] if argv is None else argv
    terms = load_terms()
    if not terms:
        if os.environ.get("FORGEGRAPH_DENYLIST_REQUIRED") == "1":
            print("deny-list: no terms configured", file=sys.stderr)
            return 1
        print("deny-list: no terms configured; skipping", file=sys.stderr)
        return 0
    hits = scan(args or tracked_files(), terms)
    for name, lineno, number in hits:
        print(f"{name}:{lineno}: contains deny-listed term #{number}")
    return 1 if hits else 0


if __name__ == "__main__":
    sys.exit(main())
