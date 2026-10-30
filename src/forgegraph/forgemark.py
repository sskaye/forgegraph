"""Forgemark's file format, and its command-line tool, pinned to one version.

A Forgemark document (Markdown, or an HTML page) holds its review comments as a pair of
markers around the text each one is on (MARKER) and one comment block at its end
(COMMENTS). keep() carries the block onto a rebuilt document, strip() takes the review
markup out, and rewrite() writes a rebuilt document and puts its comments back with the tool.

    uv run python scripts/forgemark.py lint review/phase-02/recreations.html
    uv run python scripts/forgemark.py reattach docs/specifications/theme.md --all

The tool is one JavaScript file from Forgemark's GitHub release (MIT licence), needing only
Node 18+. It's downloaded once into the user's cache folder, checked against the SHA-256
recorded here, and run with node. To move to a new version, change VERSION and SHA256 together.
"""

from __future__ import annotations

import hashlib
import os
import re
import shutil
import subprocess
import urllib.request
from collections.abc import Callable
from pathlib import Path

COMMENTS = "<!-- forgemark-comments"  # the start of a document's comment block
MARKER = re.compile(r"<!-- /?fmc:\d+ -->")  # a comment's start or end marker

VERSION = "1.12.2"
SHA256 = "df8c22a648aeaee9a181baae3ce31a374b9d9f6a5e4681b11c3d4ce9281b2faa"
URL = (
    f"https://github.com/sskaye/forgemark/releases/download/v{VERSION}/forgemark-cli-{VERSION}.mjs"
)
CACHE = Path(os.environ.get("XDG_CACHE_HOME") or Path.home() / ".cache") / "forgegraph"


class ForgemarkError(RuntimeError):
    """The tool can't be run."""


def tool() -> Path:
    """The pinned tool, downloaded and checked if it isn't here yet."""
    path = CACHE / f"forgemark-cli-{VERSION}.mjs"
    if path.exists() and hashlib.sha256(path.read_bytes()).hexdigest() == SHA256:
        return path
    CACHE.mkdir(parents=True, exist_ok=True)
    with urllib.request.urlopen(URL, timeout=60) as response:
        data = response.read()
    digest = hashlib.sha256(data).hexdigest()
    if digest != SHA256:
        raise ForgemarkError(f"forgemark {VERSION}: checksum mismatch ({digest}); not running it")
    path.write_bytes(data)
    return path


def ready() -> None:
    """Raise ForgemarkError unless the tool can run."""
    if shutil.which("node") is None:
        raise ForgemarkError("forgemark needs Node 18 or later on the PATH")
    tool()


def run(*args: str, check: bool = True) -> subprocess.CompletedProcess[str]:
    """Run the tool with these arguments, returning its output."""
    node = shutil.which("node")
    if node is None:
        raise ForgemarkError("forgemark needs Node 18 or later on the PATH")
    return subprocess.run([node, str(tool()), *args], text=True, capture_output=True, check=check)


def keep(new: str, old: str) -> str:
    """The new document with the old one's comment block carried over."""
    if COMMENTS not in old:
        return new
    return new.rstrip("\n") + "\n\n" + old[old.index(COMMENTS) :]


def strip(text: str) -> str:
    """A document without review markup: its comment block and markers."""
    if COMMENTS in text:
        text = text[: text.index(COMMENTS)].rstrip("\n") + "\n"
    return MARKER.sub("", text)


def rewrite(path: Path, text: str, reopen: Callable[[str], str] | None = None) -> str:
    """Write a rebuilt document, keeping the comments the old one had: carried over, put
    back by their element's id or their text (`reattach --all`), then the document passed
    through reopen if given. Returns the tool's lint report, or "" when there are no comments."""
    old = path.read_text(encoding="utf-8") if path.exists() else ""
    if COMMENTS in old:
        ready()  # fail before writing if the comments couldn't be put back
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(keep(text, old), encoding="utf-8", newline="\n")
    if COMMENTS not in old:
        return ""
    run("reattach", str(path), "--all", check=False)
    if reopen is not None:
        path.write_text(reopen(path.read_text(encoding="utf-8")), encoding="utf-8", newline="\n")
    lint = run("lint", str(path), check=False)
    return (lint.stdout + lint.stderr).strip()
