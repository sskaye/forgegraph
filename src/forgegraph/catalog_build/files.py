"""Catalog files: each theme's, format's, graph type's and layer type's baselines.

A catalog file shows the file of that name: a theme's or format's is in its pack's
catalogs/themes/ or catalogs/formats/, named like the spec it shows (pack/name); a graph
type's or layer type's in ForgeGraph's specifications/catalogs/, named like its definition
file (graphtype_xy.yaml, layer_note.yaml). It names
the GraphSpec every card changes (`baseline`) and the numbered baselines (`baselines`: each
the baseline with one or more changes, non-standard, or footnoted, drawn with a footnote),
generic scenarios a card can be drawn on. A layer type's catalog also gives the GraphSpec
parameters every card sets so the layer can be drawn (`settings`) and the layer every card
draws (`layer`), named after its type. A file that extends another inherits its baselines
and adds its own.

No card is chosen here: every parameter of the file shown gets one card, its value and
baseline chosen by the rule in forgegraph.catalog_build.cards. The page shows the variable
parameters' cards; the perturbation test draws them all. A parameter that changes no
baseline's drawing is an error, fixed by adding a baseline that shows it.
"""

from __future__ import annotations

from dataclasses import dataclass, replace
from pathlib import Path
from typing import Any

from forgegraph.catalog_build.cards import Change, Scene, candidates, gets_card, moved, tied
from forgegraph.catalog_build.examples import SPECIAL, data
from forgegraph.graph import SpecError
from forgegraph.packs import Pack
from forgegraph.spec.common import ProblemsError
from forgegraph.spec.parameters import (
    KINDS,
    PREFIXES,
    Parameter,
    check_parameter,
    definitions,
    flatten,
    is_none,
    series_definitions,
    specifications_folder,
)
from forgegraph.spec.registry import Registry, load_yaml
from forgegraph.spec.resolve import Values, resolve
from forgegraph.spec.series import resolve_series
from forgegraph.spec.series import with_defaults as series_defaults

FOLDERS = {kind: KINDS[kind] for kind in ("theme", "format", "graph_type", "layer")}
HEADER = ("name", "version", "description", "extends", "baseline", "baselines")
LAYER_HEADER = (*HEADER[:5], "settings", "layer", *HEADER[5:])


class CatalogError(ProblemsError):
    """Catalog files that can't be built; `problems` lists each one."""


@dataclass(frozen=True)
class Catalog:
    kind: str  # theme, format, graph_type or layer
    name: str  # the file it shows
    baseline: str  # the GraphSpec every card changes
    parameters: tuple[Parameter, ...]  # every parameter of the file it shows, as defined
    # each card's parameter, and the changes of each of its candidates, in order
    cards: tuple[tuple[Parameter, tuple[tuple[Change, ...], ...]], ...]
    variable: frozenset[str] = frozenset()  # the cards the page shows: variable parameters'
    baselines: tuple[Change, ...] = ()  # the numbered baselines, in the catalog files' order
    always: tuple[Change, ...] = ()  # a layer type's catalog: its settings and layer, on every card


def find(packs: list[Pack]) -> dict[str, dict[str, tuple[dict[str, Any], Path]]]:
    """Every catalog file, by kind and name: ForgeGraph's for graph types and layer types, in
    specifications/catalogs/, and each pack's for its themes and formats, named pack/name."""
    found: dict[str, dict[str, tuple[dict[str, Any], Path]]] = {k: {} for k in FOLDERS}
    own = specifications_folder() / "catalogs"
    paths = [(k, p, "") for k in ("graph_type", "layer") for p in own.glob(f"{PREFIXES[k]}*.yaml")]
    for pack in packs:
        for kind in ("theme", "format"):
            paths += [
                (kind, p, f"{pack.name}/")
                for p in (pack.folder / "catalogs" / FOLDERS[kind]).glob("*.yaml")
            ]
    for kind, path, prefix in sorted(paths, key=lambda found: (found[2], str(found[1]))):
        doc = load_yaml(path)
        if isinstance(doc, dict) and "name" in doc:
            found[kind][f"{prefix}{doc['name']}"] = (doc, path)
    return found


def _settable(reg: Registry, graph_type: str) -> dict[str, Parameter]:
    """Every parameter a baseline may change."""
    out: dict[str, Parameter] = {}
    for kind in ("theme", "format", "graphspec"):
        out.update(definitions(kind))
    out.update(definitions("graph_type", graph_type))
    out.update(_series(graph_type))
    return out


def _series(graph_type: str) -> dict[str, Parameter]:
    """A graph type's series parameters, as series.<parameter>: a change to one sets it on
    every series the GraphSpec lists."""
    return {
        f"series.{p}": replace(q, path=f"series.{p}")
        for p, q in series_definitions(graph_type).items()
    }


def _check(where: str, p: Parameter, value: Any, reg: Registry) -> list[str]:
    return [f"{where}{suffix}: {msg}" for suffix, msg in check_parameter(p, value, reg.names())]


def _change(where: str, entry: Any, params: dict[str, Parameter], reg: Registry, name: str):
    """A numbered baseline, or a layer catalog's settings: one or more parameters and their
    values, as one change named name. A layer's parameter is written
    layers.<layer>.<parameter>, and checked when the card is drawn."""
    if entry in SPECIAL:
        return Change(str(entry), True), []
    if not isinstance(entry, dict) or not entry:
        return None, [f"{where}: must be parameters and their values, non-standard, or footnoted"]
    changes, problems = [], []
    for path, value in entry.items():
        if str(path).startswith("layers.") or path == "series":
            changes.append(Change(str(path), value))  # checked when it's drawn
            continue
        if path not in params:
            problems.append(f"{where}: unknown parameter '{path}'")
            continue
        problems += _check(f"{where}.{path}", params[path], value, reg)
        changes.append(Change(str(path), value))
    if len(entry) == 1 or problems:
        return (changes[0] if changes else None), problems
    return Change(name, None, tuple(changes)), problems


def _chain(kind: str, doc: dict[str, Any], found: dict, label: str) -> list[dict[str, Any]]:
    chain, seen, parent = [doc], set(), doc.get("extends")
    while not is_none(parent):
        if parent not in found[kind] or parent in seen:
            raise CatalogError([f"{label}: extends: no catalog '{parent}' to extend"])
        seen.add(parent)
        chain.append(found[kind][parent][0])
        parent = chain[-1].get("extends")
    return chain


def _scene(
    baseline: str,
    values: Values,
    always: tuple[Change, ...],
    params: dict[str, Parameter],
    reg: Registry,
) -> Scene:
    """The baseline's data, the values it's drawn with (always's on top; the GraphSpec's
    own layers aren't drawn), and the columns its column parameters name."""
    try:
        frame = data(baseline, reg)
    except SpecError as e:
        raise CatalogError([f"baseline '{baseline}': {p}" for p in e.problems]) from None
    drawn = {p: v for p, v in values.plain().items() if not p.startswith("layers.")}
    listed = resolve_series(reg.docs["graphspec"][baseline], reg)
    for name, r in list(listed.items())[:1]:  # what a series parameter's card changes
        entry = series_defaults(r.value)
        drawn.update({f"series.{p}": v for p, v in entry.items() if p != "look"})
        column = name if entry["column"] == "name" else entry["column"]
        drawn["series.column"] = column
    drawn.update({c.path: c.value for c in always})
    used: set[str] = set()
    for path, value in drawn.items():
        p = params.get(path)
        if p is not None and {"column", "columns"} & set(p.range.types):
            used.update(v for v in (value if isinstance(value, list) else [value]) if v in frame)
    return Scene(frame, drawn, frozenset(used))


def read(kind: str, name: str, reg: Registry) -> Catalog:
    """The catalog of one theme, format, graph type or layer type, checked against every
    rule, with each card's candidates. Themes' and formats' catalogs come from the registry's
    packs."""
    found = find(list(reg.packs.values()))
    label = f"catalogs/{FOLDERS[kind]}/{name.split('/')[-1]}.yaml"
    if name not in found[kind]:
        raise CatalogError([f"{label}: missing; every {kind.replace('_', ' ')} needs a catalog"])
    doc, path = found[kind][name]
    label = str(path.relative_to(path.parents[2]))
    header = LAYER_HEADER if kind == "layer" else HEADER
    problems = [f"{label}: {k}: required" for k in header if k not in doc]
    problems += [f"{label}: {k}: unknown field" for k in doc if k not in header]
    if problems:
        raise CatalogError(problems)
    chain = _chain(kind, doc, found, label)
    baseline = next(d["baseline"] for d in chain if not is_none(d.get("baseline")))
    if baseline not in reg.docs["graphspec"]:
        raise CatalogError([f"{label}: baseline: no GraphSpec '{baseline}'"])
    values = resolve("graphspec", reg.docs["graphspec"][baseline], reg)
    drawn = str(values["specifications.graph_type"].value)
    graph_type = name if kind == "graph_type" else drawn
    if kind == "graph_type" and drawn != name:
        problems.append(f"{label}: baseline: '{baseline}' draws {drawn}, not {name}")
    params = _settable(reg, graph_type)

    bases: dict[str, Change] = {}
    for d in reversed(chain):  # a file's own after those it extends; the nearest file wins
        listed = d.get("baselines")
        for bname, entry in (listed if isinstance(listed, dict) else {}).items():
            change, errs = _change(f"{label}: baselines.{bname}", entry, params, reg, str(bname))
            problems += errs
            if change is not None:
                bases[str(bname)] = change

    own = definitions(kind, name if kind in ("graph_type", "layer") else None)
    if kind == "graph_type":
        own = {**own, **_series(name)}
    always: tuple[Change, ...] = ()
    prefix = ""
    if kind == "layer":
        prefix = f"layers.{name}."
        layer = next((d["layer"] for d in chain if isinstance(d.get("layer"), dict)), {})
        settings = next((d["settings"] for d in chain if isinstance(d.get("settings"), dict)), {})
        if settings:
            change, errs = _change(f"{label}: settings", settings, params, reg, "settings")
            problems += errs
            if change is not None:
                always += change.parts or (change,)
        always = (
            *always,
            Change(f"{prefix}type", name),
            *(Change(f"{prefix}{p}", v) for p, v in flatten(layer).items()),
        )
        params = {**params, **{f"{prefix}{p}": q for p, q in own.items()}}
    if problems:
        raise CatalogError(problems)

    scene = _scene(str(baseline), values, always, params, reg)
    shown = resolve(kind, reg.docs[kind][name], reg) if kind != "layer" else Values()
    # the shown spec's values beneath the GraphSpec's; a layer's defaults beneath its own
    beneath = {f"{prefix}{p}": q.default for p, q in own.items()} if prefix else shown.plain()
    scene = Scene(scene.data, {**beneath, **scene.values}, scene.used)
    cards = []
    for p in own.values():
        if not gets_card(kind, p):
            continue
        options: list[tuple[Change, ...]] = []
        d = shown.value(p.path, p.default)
        for value in candidates(p, d, scene, name if kind == "layer" else ""):
            changes = moved(tied(p.path, value, prefix), scene)
            unset = p.required and is_none(value)  # check_parameter allows it unset
            if not unset and not _check("", p, value, reg) and changes not in options:
                options.append(changes)
        cards.append((p, tuple(options)))
    return Catalog(
        kind,
        name,
        str(baseline),
        tuple(own.values()),
        tuple(cards),
        frozenset(p.path for p, _ in cards if not shown.fixed(p.path, p.fixed)),
        tuple(bases.values()),
        always,
    )
