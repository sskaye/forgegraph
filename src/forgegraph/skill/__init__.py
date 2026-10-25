"""The agent skill, installed by `forgegraph skill install`.

The skill's files live in the package's skill/forgegraph/ folder. Installing writes them into
an agent's skills folder: ~/.claude/skills by default (every project), or a project's
.claude/skills. Review comments in the files (Forgemark markers and comment block) are left
out: they're for the people reviewing the skill, not for the agent using it.
"""

from __future__ import annotations

import shutil
from importlib.resources import files
from pathlib import Path

from forgegraph import forgemark

NAME = "forgegraph"


class InstallError(ValueError):
    """The skill can't be installed where asked."""


def source() -> Path:
    """The skill's folder inside the installed package."""
    return Path(str(files("forgegraph") / "skill" / NAME))


def contents() -> dict[str, bytes]:
    """The skill's files as installed, by path within the skill's folder."""
    out = {}
    for path in sorted(source().rglob("*")):
        rel_parts = path.relative_to(source()).parts
        if not path.is_file() or "__pycache__" in rel_parts or rel_parts[-1].startswith("."):
            continue  # caches and hidden files such as .DS_Store aren't part of the skill
        data = path.read_bytes()
        if path.suffix == ".md":
            data = forgemark.strip(data.decode("utf-8")).encode("utf-8")
        out[path.relative_to(source()).as_posix()] = data
    return out


def _installed(target: Path) -> dict[str, bytes]:
    return {
        p.relative_to(target).as_posix(): p.read_bytes()
        for p in sorted(target.rglob("*"))
        if p.is_file() and "__pycache__" not in p.parts
    }


def install(skills_folder: Path, force: bool = False) -> tuple[Path, str]:
    """Write the skill into skills_folder/forgegraph. Returns the folder and what happened:
    installed, updated or unchanged. A folder there with other contents is replaced only
    with force, since it may hold someone's edits."""
    target = skills_folder / NAME
    wanted = contents()
    what = "installed"
    if target.exists():
        if not target.is_dir():
            raise InstallError(f"{target} exists and isn't a folder")
        if _installed(target) == wanted:
            return target, "unchanged"
        if not force:
            raise InstallError(
                f"{target} already exists with different contents; "
                "use --force to replace it with this version's skill"
            )
        shutil.rmtree(target)
        what = "updated"
    for rel, data in wanted.items():
        path = target / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)
    return target, what
