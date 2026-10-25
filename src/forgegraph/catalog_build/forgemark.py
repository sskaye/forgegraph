"""Run Forgemark's command-line tool, pinned to one version.

    uv run python scripts/forgemark.py lint review/phase-02/recreations.html
    uv run python scripts/forgemark.py reattach docs/specs/theme/base_theme.md --all

The tool is one JavaScript file from Forgemark's GitHub release (MIT licence), needing only
Node 18+. It's downloaded once into the user's cache folder, checked against the SHA-256
recorded here, and run with node. To move to a new version, change VERSION and SHA256 together.
"""

from __future__ import annotations

import hashlib
import os
import shutil
import subprocess
import urllib.request
from pathlib import Path

VERSION = "1.12.0"
SHA256 = "6963b01c8ddf64f159aeb8edf2cc29c0aca630d373072688e96b06284137916a"
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
