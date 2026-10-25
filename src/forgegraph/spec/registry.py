"""The registry: every spec ForgeGraph knows, by kind and name, and where each was read from.

ForgeGraph's graph types and layer types and the base pack are always known; a file being
drawn also knows the packs its configs list (see packs), and the installed pip packs their
specs build on.
"""

from __future__ import annotations

import copy
from dataclasses import dataclass, field
from functools import cache
from importlib.resources import files
from pathlib import Path
from typing import Any

from ruamel.yaml import YAML

from forgegraph.packs import FOLDERS as PACK_FOLDERS
from forgegraph.packs import Config, Pack, pip_packs, read_pack, setup
from forgegraph.spec.parameters import BASE, CORE_KINDS, KINDS, NAMES, SECTIONS, base_folder

_yaml = YAML(typ="safe", pure=True)


def load_yaml(path: Path) -> Any:
    """A YAML file's contents. Each file is parsed once while it's unchanged (same size and
    modification time); every caller gets its own copy."""
    stat = path.stat()
    key = (str(path.resolve()), stat.st_mtime_ns, stat.st_size)
    if key not in _parsed:
        with path.open(encoding="utf-8") as f:
            _parsed[key] = _yaml.load(f)
    return copy.deepcopy(_parsed[key])


_parsed: dict[tuple[str, int, int], Any] = {}  # by path, modification time and size


@dataclass
class Registry:
    """Every known file of each kind, by name, and where each was read from. A pack's specs
    are named pack/name; graph types and layer types, ForgeGraph's code, have plain names.
    `packs` are the packs loaded, which specs may build on, `allowed` those whose specs a
    drawn file may name, and `nonstandard` those of them the main config doesn't list."""

    docs: dict[str, dict[str, dict[str, Any]]] = field(
        default_factory=lambda: {kind: {} for kind in KINDS}
    )
    paths: dict[str, dict[str, Path]] = field(default_factory=lambda: {kind: {} for kind in KINDS})
    packs: dict[str, Pack] = field(default_factory=dict)
    allowed: frozenset[str] = frozenset({BASE})
    configs: tuple[Config, ...] = ()
    nonstandard: frozenset[str] = frozenset()

    def names(self) -> dict[str, set[str]]:
        """Every known file's name, by kind."""
        return {kind: set(d) for kind, d in self.docs.items()}

    def add(self, kind: str, doc: dict[str, Any], path: Path | None = None) -> None:
        """Know a file of a kind by its name, and where it was read from, if it was."""
        self.docs[kind][doc["name"]] = doc
        if path is not None:
            self.paths[kind][doc["name"]] = path

    def add_pack(self, pack: Pack) -> Registry:
        """Add every spec in a pack's folders, each named pack/name."""
        self.packs[pack.name] = pack
        for kind, folder in PACK_FOLDERS.items():
            for path in sorted((pack.folder / folder).glob("*.yaml")):
                doc = load_yaml(path)
                if isinstance(doc, dict) and "name" in doc:
                    self.add(kind, {**doc, "name": f"{pack.name}/{doc['name']}"}, path)
                    for named in _specs_named(kind, doc):
                        self.reach(named)
        return self

    def reach(self, name: Any) -> None:
        """Load the installed pip pack that pack/name is in, if it isn't loaded, so specs can
        build on it; it isn't allowed by being loaded."""
        if not isinstance(name, str) or "/" not in name:
            return
        pack = name.split("/")[0]
        if pack in self.packs or pack not in pip_packs():
            return
        self.add_pack(read_pack(pip_packs()[pack], "pip", pack))

    def pack_of(self, kind: str, name: str) -> str | None:
        """The pack a spec comes from: None for a drawn file, or a graph or layer type."""
        path = self.paths[kind].get(name)
        if path is None or kind in CORE_KINDS:
            return None
        return next((p.name for p in self.packs.values() if p.folder in path.parents), None)

    def owner(self, kind: str, doc: dict[str, Any]) -> str | None:
        """The pack a document is a spec of, or None for a file being drawn."""
        name = doc.get("name")
        if not isinstance(name, str) or self.docs[kind].get(name) is not doc:
            return None
        return self.pack_of(kind, name)

    def unloaded(self, value: Any, in_pack: bool = False) -> str | None:
        """For a pack/name whose pack isn't among those loaded: why it can't be used, by a
        file being drawn, or, in_pack, by a pack's spec, which may build on any pack it can
        find."""
        if not isinstance(value, str) or "/" not in value:
            return None
        pack = value.split("/")[0]
        if pack in self.packs:
            return None
        if in_pack:
            return (
                f"'{value}' is in the pack '{pack}', which can't be found: no config that "
                "applies lists it, and no installed pip pack has that name"
            )
        return f"'{value}' is in the pack '{pack}', which {self.allows()}"

    def allows(self) -> str:
        """How a pack that may not be used is described: '... which <this>'."""
        if not self.configs:
            return f"isn't allowed: no config lists it, and without one only {BASE} may be used"
        return " and ".join(str(c.path) for c in self.configs) + " doesn't allow"

    def copy(self) -> Registry:
        """A registry to add to without changing this one."""
        return Registry(
            {k: dict(v) for k, v in self.docs.items()},
            {k: dict(v) for k, v in self.paths.items()},
            dict(self.packs),
            self.allowed,
            self.configs,
            self.nonstandard,
        )


@cache
def _core() -> Registry:
    """ForgeGraph's graph types and layer types, and the base pack, which every pack's specs
    may extend."""
    reg = Registry()
    for kind in CORE_KINDS:
        for path in sorted(Path(str(files("forgegraph") / KINDS[kind])).glob("*.yaml")):
            doc = load_yaml(path)
            if isinstance(doc, dict) and "name" in doc:
                reg.add(kind, doc, path)
    return reg.add_pack(read_pack(base_folder(), "built in", BASE))


def builtin() -> Registry:
    """The registry with no config: only the base pack may be used."""
    return _core().copy()


def registry_for(start: Path) -> Registry:
    """The registry for a file in folder start: every pack its configs list, and the
    installed pip packs their specs build on; the packs it may use are those its configs
    allow (see packs)."""
    found = setup(start)
    reg = _core().copy()
    for pack in found.listed.values():
        if pack.name != BASE:
            reg.add_pack(pack)
    reg.allowed = frozenset(found.packs)
    reg.configs = found.configs
    reg.nonstandard = found.nonstandard
    return reg


def _specs_named(kind: str, doc: dict[str, Any]) -> list[Any]:
    """The specs a pack's spec builds on: what it extends, and the packs' specs a GraphSpec
    or layout names (see NAMES)."""
    named = [doc.get("extends")]
    for section in SECTIONS:
        chosen = doc.get(section)
        chosen = chosen.get("specifications") if isinstance(chosen, dict) else None
        if isinstance(chosen, dict):
            named += [chosen.get(k) for k in NAMES.get(kind, ()) if k not in CORE_KINDS]
    return named
