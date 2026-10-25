"""Packs, and the configs that say which may be used (architecture D4).

A pack is a folder of specs with a pack.yaml at its top: themes/, formats/, graphspecs/,
layouts/ and schedules/, with catalogs/, references/ and fonts/. Its specs are named
`pack/name`. ForgeGraph's built-in packs, forgegraph_base and forgegraph_base_2, are in
this package, and a config names them like pip packs.

A config lists the packs that may be used: `packs = [...]`, each the name forgegraph_base,
a pip pack's name, or a folder pack's path from the config file. Two configs can apply to a
file being drawn: the main config, for all work, and a folder config, forgegraph.toml in the
file's folder or the nearest folder above it. The main config is ~/.config/forgegraph/
config.toml, or the file FORGEGRAPH_CONFIG names; when there's none, it's written, listing
the built-in packs. With a folder config, a file may use only the packs it lists; one the
main config doesn't list may be used, but it's non-standard: whatever is drawn with it is
watermarked. Every problem is an error naming its file.

The configs restrict use, not access: a pack's spec may build on any spec ForgeGraph can
find, in a pack a config that applies lists or in an installed pip pack.

A pip pack declares an entry point in the group forgegraph.packs, naming the top-level
package that holds its pack.yaml. It's found without importing it.
"""

from __future__ import annotations

import importlib.util
import os
import sys
import tomllib
from dataclasses import dataclass
from functools import cache
from importlib.metadata import entry_points
from importlib.resources import files
from pathlib import Path
from typing import Any

from packaging.specifiers import InvalidSpecifier, SpecifierSet
from ruamel.yaml import YAML

from forgegraph import __version__
from forgegraph.spec.common import ProblemsError

BASE = "forgegraph_base"
FOLDER_CONFIG = "forgegraph.toml"
MAIN_CONFIG_VARIABLE = "FORGEGRAPH_CONFIG"
BUILT_IN = (BASE, "forgegraph_base_2")  # the packs ForgeGraph ships, which a new main config lists
ENTRY_POINTS = "forgegraph.packs"
FIELDS = ("name", "version", "description", "issues", "requires")
FOLDERS = {
    "theme": "themes",
    "format": "formats",
    "graphspec": "graphspecs",
    "layout": "layouts",
    "schedule": "schedules",
}
_yaml = YAML(typ="safe", pure=True)


class PackError(ProblemsError):
    """A pack or config that can't be used; `problems` lists each problem."""


@dataclass(frozen=True)
class Pack:
    """A pack, as its pack.yaml describes it, and where it is."""

    name: str
    version: str
    description: str
    issues: str
    requires: str | None
    folder: Path
    source: str  # "built in", "pip", or "folder"


@dataclass(frozen=True)
class Config:
    """A config file: where it is, and the packs it lists."""

    path: Path
    packs: tuple[str, ...]  # as written


@dataclass(frozen=True)
class Setup:
    """What applies to one file being drawn: the configs found, the main one first, the packs
    that may be used, every pack they list, by name, and the packs that may be used that the
    main config doesn't list."""

    configs: tuple[Config, ...]
    packs: dict[str, Pack]
    listed: dict[str, Pack]
    nonstandard: frozenset[str] = frozenset()


def user_config() -> Path:
    """The main config's path: FORGEGRAPH_CONFIG's, or ~/.config/forgegraph/config.toml."""
    named = os.environ.get(MAIN_CONFIG_VARIABLE)
    return (
        Path(named).expanduser()
        if named
        else Path.home() / ".config" / "forgegraph" / "config.toml"
    )


def write_main_config(path: Path) -> None:
    """A new main config, listing the built-in packs."""
    listed = ", ".join(f'"{p}"' for p in BUILT_IN)
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
            "# ForgeGraph's main config: the packs any file may use (forgegraph schema config).\n"
            f"packs = [{listed}]\n",
            encoding="utf-8",
        )
    except OSError as e:
        raise PackError(
            [f"{path}: can't write the main config ({e.strerror}); set {MAIN_CONFIG_VARIABLE} "
             "to a file that can be written, or write it yourself"]
        ) from None  # fmt: skip
    print(f"ForgeGraph wrote its main config, {path}, listing {listed}.", file=sys.stderr)


def built_in_folder(name: str) -> Path:
    """A built-in pack's folder, in this package."""
    return Path(str(files(__package__) / name))


def base_folder() -> Path:
    return built_in_folder(BASE)


def read_pack(folder: Path, source: str, expected: str | None = None) -> Pack:
    """A pack's pack.yaml, checked: its five fields, its name and its ForgeGraph versions."""
    where = folder / "pack.yaml"
    if not where.is_file():
        raise PackError([f"{where}: no pack.yaml, so {folder} isn't a pack"])
    data = _yaml.load(where.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise PackError([f"{where}: must be a mapping of fields"])
    problems = [f"{where}: {k}: required" for k in FIELDS if k not in data]
    fields = ", ".join(FIELDS)
    problems += [
        f"{where}: {k}: unknown field; a pack.yaml has {fields}" for k in data if k not in FIELDS
    ]
    if problems:
        raise PackError(problems)
    name = str(data["name"])
    if expected is not None and name != expected:
        raise PackError([f"{where}: name: '{name}', but the pack is listed as '{expected}'"])
    requires = None if data["requires"] in (None, "None") else str(data["requires"])
    if requires is not None:
        try:
            versions = SpecifierSet(requires)
        except InvalidSpecifier:
            raise PackError(
                [f"{where}: requires: '{requires}' isn't a version specifier"]
            ) from None
        if not versions.contains(__version__, prereleases=True):
            raise PackError(
                [f"{where}: requires ForgeGraph {requires}; this is ForgeGraph {__version__}"]
            )
    return Pack(name, str(data["version"]), str(data["description"]), str(data["issues"]),
                requires, folder, source)  # fmt: skip


@cache
def pip_packs() -> dict[str, Path]:
    """Each installed pip pack's folder, by its entry point's name, found without importing."""
    out = {}
    for ep in entry_points(group=ENTRY_POINTS):
        spec = importlib.util.find_spec(ep.value.split(":")[0]) if "." not in ep.value else None
        if spec is not None and spec.submodule_search_locations:
            out[ep.name] = Path(next(iter(spec.submodule_search_locations)))
    return out


def read_config(path: Path) -> Config:
    """A config file, checked: TOML holding only a list of packs."""
    try:
        data: dict[str, Any] = tomllib.loads(path.read_text(encoding="utf-8"))
    except tomllib.TOMLDecodeError as e:
        raise PackError([f"{path}: not TOML: {e}"]) from None
    problems = [
        f"{path}: {k}: unknown setting; a config has only packs" for k in data if k != "packs"
    ]
    listed = data.get("packs")
    if not isinstance(listed, list) or not all(isinstance(p, str) for p in listed):
        problems.append(f"{path}: packs: a list of pack names or folder paths is required")
    if problems:
        raise PackError(problems)
    return Config(path, tuple(listed))  # type: ignore[arg-type]


def find_configs(start: Path) -> tuple[Config, ...]:
    """The configs that apply to a file in folder start: the main one, written if there's
    none, then the folder's."""
    user = user_config()
    if not user.is_file():
        write_main_config(user)
    found = [read_config(user)]
    for folder in [start.resolve(), *start.resolve().parents]:
        candidate = folder / FOLDER_CONFIG
        if candidate.is_file():
            found.append(read_config(candidate))
            break
    return tuple(found)


def _is_path(entry: str) -> bool:
    return entry.startswith((".", "~", "/")) or "/" in entry or "\\" in entry


def _resolve(entry: str, config: Config) -> Pack:
    if entry in BUILT_IN:
        return read_pack(built_in_folder(entry), "built in", entry)
    if _is_path(entry):
        folder = Path(entry).expanduser()
        if not folder.is_absolute():
            folder = config.path.parent / folder
        return read_pack(folder.resolve(), "folder")
    known = pip_packs()
    if entry not in known:
        hint = "; a folder pack is written as a path, e.g. ./" + entry
        raise PackError([f"{config.path}: packs: no pack '{entry}' is installed{hint}"])
    return read_pack(known[entry], "pip", entry)


def _packs(config: Config) -> dict[str, Pack]:
    out: dict[str, Pack] = {}
    problems = []
    for entry in config.packs:
        try:
            pack = _resolve(entry, config)
        except PackError as e:
            problems += e.problems
            continue
        if pack.name in out:
            problems.append(f"{config.path}: packs: two packs named '{pack.name}'")
        out[pack.name] = pack
    if problems:
        raise PackError(problems)
    return out


def setup(start: Path) -> Setup:
    """The configs and packs that apply to a file in folder start."""
    configs = find_configs(start)
    main = _packs(configs[0])
    allowed = _packs(configs[-1]) if len(configs) == 2 else main
    _one_pack_per_name(configs, main, allowed)
    nonstandard = frozenset(n for n in allowed if n not in main)
    return Setup(configs, allowed, {**main, **allowed}, nonstandard)


def _one_pack_per_name(
    configs: tuple[Config, ...], main: dict[str, Pack], allowed: dict[str, Pack]
) -> None:
    """One name is one pack: a config can't give a built-in pack's name, or a name the main
    config gives, to another folder."""
    known = {name: built_in_folder(name).resolve() for name in BUILT_IN}
    problems = []
    for config, listed in zip(configs, (main, allowed), strict=False):
        for name, pack in listed.items():
            folder = pack.folder.resolve()
            if known.setdefault(name, folder) != folder:
                problems.append(
                    f"{config.path}: packs: '{name}' is the pack in {folder}, but '{name}' is "
                    f"already the pack in {known[name]}; give it a name of its own"
                )
    if problems:
        raise PackError(problems)


def references(pack: Pack) -> dict[str, str]:
    """A pack's reference notes, named pack/note, each with its description: the front
    matter's description, or else its first line."""
    out = {}
    for path in sorted((pack.folder / "references").glob("*.md")):
        lines = [ln for ln in path.read_text(encoding="utf-8").splitlines() if ln.strip()]
        described = [ln for ln in lines[1:] if ln.startswith("description:")]
        if lines and lines[0] == "---" and described:
            out[f"{pack.name}/{path.stem}"] = described[0].split(":", 1)[1].strip()
        else:
            out[f"{pack.name}/{path.stem}"] = lines[0].lstrip("# ").strip() if lines else ""
    return out


def fonts(pack: Pack) -> list[Path]:
    """A pack's font files."""
    folder = pack.folder / "fonts"
    return sorted([*folder.glob("*.ttf"), *folder.glob("*.otf")])
