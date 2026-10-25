"""A parameter's comment, wherever a spec file restates it (a pack's themes, formats and
GraphSpecs, the catalog files, the skill's examples), is its definition's comment, word for
word: one source, so a description can't drift from what the code does. A file restating
a parameter sets it, so "A GraphSpec must set it." is left out; a file that writes no
comment for a parameter doesn't restate it."""

from __future__ import annotations

import re
from collections.abc import Iterator
from pathlib import Path
from typing import Any

from ruamel.yaml import YAML

import forgegraph
from forgegraph.spec.parameters import _comment, definition_file, graph_type_files

PKG = Path(forgegraph.__file__).parent
SECTIONS = ("fixed_parameters", "variable_parameters")
FOLDERS = {  # a spec file's folder, and the kind of spec it holds
    "themes": "theme",
    "formats": "format",
    "graphspecs": "graphspec",
    "layouts": "layout",
    "schedules": "schedule",
    "graph_types": "graph_type",
    "layers": "layer",
}


def _load(path: Path) -> Any:
    return YAML(typ="rt").load(path.read_text(encoding="utf-8"))


def _comments(node: Any, prefix: str = "") -> Iterator[tuple[str, str | None]]:
    """(dotted path, comment) of every parameter under node; a catalog card's {value, from,
    with} is one parameter."""
    if not hasattr(node, "items"):
        return
    for key in node:
        value, path = node[key], f"{prefix}.{key}" if prefix else str(key)
        if hasattr(value, "items") and not set(value) <= {"value", "from", "with"}:
            yield from _comments(value, path)
        else:
            yield path, _comment(node, key)


def _defined(path: Path) -> dict[str, str | None]:
    data = _load(path)
    return {
        p: c
        for section in SECTIONS
        for p, c in _comments(data.get(section))
        if not p.startswith(("layers", "tabs"))
    }


KIND = {k: _defined(definition_file(k)) for k in ("theme", "format", "graphspec", "layout")}
KIND["schedule"] = _defined(definition_file("schedule"))
GRAPH_TYPE = {
    p: c
    for gt in graph_type_files()
    for p, c in _defined(definition_file("graph_type", gt)).items()
}
RESTATES = {  # the definitions a file of each kind may restate
    "theme": KIND["theme"],
    "format": KIND["format"],
    "graphspec": {**KIND["theme"], **KIND["format"], **GRAPH_TYPE},
    "layout": {**KIND["format"], **KIND["layout"]},
    "schedule": KIND["schedule"],
    "graph_type": GRAPH_TYPE,
}
LAYER = {p.stem: dict(_comments(_load(p)["parameters"])) for p in (PKG / "layers").glob("*.yaml")}


def _kind(path: Path) -> str:
    for part in reversed(path.parts[:-1]):
        if part in FOLDERS:
            return FOLDERS[part]
    for kind in ("layout", "schedule"):
        if path.name.endswith(f".{kind}.yaml"):
            return kind
    return "graphspec"


def _drifted(path: Path) -> Iterator[tuple[str, str, str]]:
    """Each parameter whose comment in this file isn't its definition's."""
    data, rel, kind = _load(path), path.relative_to(PKG), _kind(path)
    if "catalogs" in rel.parts:  # its cards, a layer catalog's layer, and its settings
        own = LAYER[data["name"]] if kind == "layer" else RESTATES[kind]
        found = [(p, c, own) for s in ("variations", "layer") for p, c in _comments(data.get(s))]
        found += [(p, c, RESTATES["graphspec"]) for p, c in _comments(data.get("settings"))]
    else:
        found = []
        for section in SECTIONS:
            node = data.get(section)
            for p, c in _comments(node):
                if p.startswith("layers."):  # a layer's own parameter, by its type
                    _, name, *rest = p.split(".")
                    layer = LAYER.get(str(node["layers"][name].get("type")), {})
                    found.append((".".join(rest), c, {} if rest == ["type"] else layer))
                elif not p.startswith("tabs"):
                    found.append((p, c, RESTATES[kind]))
    for p, comment, definitions in found:
        expected = definitions.get(p)
        if expected is not None:
            expected = re.sub(r" A \w+ must set it\.", "", expected)
        if comment is not None and expected is not None and comment != expected:
            yield p, comment, expected


def restating_files() -> list[Path]:
    """The package's spec files that may restate parameters' comments: not the files that
    define them, except the reference GraphSpec, which restates other kinds'."""
    defining = {definition_file(k) for k in ("theme", "format", "layout", "schedule")}
    found = [p for p in PKG.rglob("*.yaml") if {"packs", "catalogs", "skill"} & set(p.parts)]
    return sorted(p for p in found if p.name != "pack.yaml" and p not in defining)


def drifted(path: Path) -> list[tuple[str, str, str]]:
    """(parameter, its comment here, its definition's) for each that differs."""
    return list(_drifted(path))


def test_every_restated_comment_is_its_definitions():
    found = [f"{p.relative_to(PKG)}: {d[0]}" for p in restating_files() for d in drifted(p)]
    assert found == []
