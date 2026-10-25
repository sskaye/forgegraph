"""Catalog files: each theme's, format's, graph type's and layer type's cards.

A catalog file shows the file of that name: a theme's or format's is in its pack's
catalogs/themes/ or catalogs/formats/, named like the spec it shows (pack/name); a graph
type's or layer type's in ForgeGraph's catalogs/graph_types/ or catalogs/layers/. It names
the GraphSpec every card changes (`baseline`), the numbered baselines (`baselines`, each
the baseline with one or more changes, non-standard, or footnoted: drawn with a footnote)
and, for every parameter of the file it shows, its card's value (`variations`): a value,
{value, from, with}, or no_card. A layer type's catalog also gives the GraphSpec parameters
every card sets so the layer can be drawn (`settings`) and the layer every card draws
(`layer`), named after its type; its cards change that layer's parameters, and a `with` may
name them alone. A file that extends another catalog lists only what differs.
"""

from __future__ import annotations

from dataclasses import dataclass
from importlib.resources import files
from pathlib import Path
from typing import Any

from forgegraph.catalog_build.examples import SPECIAL, Change, Variation
from forgegraph.packs import Pack
from forgegraph.spec.common import ProblemsError
from forgegraph.spec.parameters import (
    KINDS,
    NONE,
    Parameter,
    check_parameter,
    definitions,
    flatten,
)
from forgegraph.spec.registry import Registry, load_yaml
from forgegraph.spec.resolve import resolve

FOLDERS = {kind: KINDS[kind] for kind in ("theme", "format", "graph_type", "layer")}
HEADER = ("name", "version", "description", "extends", "baseline", "baselines", "variations")
LAYER_HEADER = (*HEADER[:5], "settings", "layer", *HEADER[5:])
NO_CARD = "no_card"
FORMS = ("value", "from", "with")


class CatalogError(ProblemsError):
    """Catalog files that can't be built; `problems` lists each one."""


@dataclass(frozen=True)
class Catalog:
    kind: str  # theme, format, graph_type or layer
    name: str  # the file it shows
    baseline: str  # the GraphSpec every card changes
    variations: tuple[tuple[Parameter, Variation | None], ...]  # in the catalog file's order
    always: tuple[Change, ...] = ()  # a layer type's catalog: its settings and layer, on every card


def find(packs: list[Pack]) -> dict[str, dict[str, tuple[dict[str, Any], Path]]]:
    """Every catalog file, by kind and name: ForgeGraph's for graph types and layer types,
    and each pack's for its themes and formats, named pack/name."""
    found: dict[str, dict[str, tuple[dict[str, Any], Path]]] = {k: {} for k in FOLDERS}
    roots: list[tuple[Path, str]] = [(Path(str(files("forgegraph") / "catalogs")), "")]
    roots += [(p.folder / "catalogs", f"{p.name}/") for p in packs]
    for base, prefix in roots:
        for kind, folder in FOLDERS.items():
            if (kind in ("graph_type", "layer")) == bool(prefix):
                continue  # graph types and layer types are ForgeGraph's; the rest packs'
            for path in sorted((base / folder).glob("*.yaml")):
                doc = load_yaml(path)
                if isinstance(doc, dict) and "name" in doc:
                    found[kind][f"{prefix}{doc['name']}"] = (doc, path)
    return found


def _settable(reg: Registry, graph_type: str) -> dict[str, Parameter]:
    """Every parameter a card or baseline may change."""
    out: dict[str, Parameter] = {}
    for kind in ("theme", "format", "graphspec"):
        out.update(definitions(kind))
    out.update(definitions("graph_type", graph_type))
    return out


def _check(where: str, p: Parameter, value: Any, reg: Registry) -> list[str]:
    return [f"{where}{suffix}: {msg}" for suffix, msg in check_parameter(p, value, reg.names())]


def _change(where: str, entry: Any, params: dict[str, Parameter], reg: Registry, name: str = ""):
    """A numbered baseline (one or more parameters and their values; name: the group's) or a
    `with` (one). A layer's parameter is written layers.<layer>.<parameter>, and checked when
    the card is drawn."""
    if entry in SPECIAL:
        return Change(str(entry), True), []
    if not isinstance(entry, dict) or not entry or (len(entry) > 1 and not name):
        return None, [f"{where}: must be parameters and their values, non-standard, or footnoted"]
    changes, problems = [], []
    for path, value in entry.items():
        if str(path).startswith("layers."):
            changes.append(Change(str(path), value))
            continue
        if path not in params:
            problems.append(f"{where}: unknown parameter '{path}'")
            continue
        problems += _check(f"{where}.{path}", params[path], value, reg)
        changes.append(Change(str(path), value))
    if len(entry) == 1 or problems:
        return (changes[0] if changes else None), problems
    return Change(name, None, tuple(changes)), problems


def _cards(node: dict[str, Any], prefix: str) -> dict[str, Any]:
    """{path: card entry} in variations: a mapping of value, and from or with, is a card;
    any other mapping is a category (which may hold a parameter named value)."""
    out: dict[str, Any] = {}
    for key, entry in node.items():
        card = isinstance(entry, dict) and "value" in entry and set(entry) <= set(FORMS)
        if isinstance(entry, dict) and not card:
            out.update(_cards(entry, f"{prefix}{key}."))
        else:
            out[f"{prefix}{key}"] = entry
    return out


def _chain(kind: str, doc: dict[str, Any], found: dict, label: str) -> list[dict[str, Any]]:
    chain, seen, parent = [doc], set(), doc.get("extends")
    while parent not in (None, NONE):
        if parent not in found[kind] or parent in seen:
            raise CatalogError([f"{label}: extends: no catalog '{parent}' to extend"])
        seen.add(parent)
        chain.append(found[kind][parent][0])
        parent = chain[-1].get("extends")
    return chain


def read(kind: str, name: str, reg: Registry) -> Catalog:
    """The catalog of one theme, format, graph type or layer type, checked against every
    rule. Themes' and formats' catalogs come from the registry's packs."""
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
    baseline = next(d["baseline"] for d in chain if d.get("baseline") not in (None, NONE))
    if baseline not in reg.docs["graphspec"]:
        raise CatalogError([f"{label}: baseline: no GraphSpec '{baseline}'"])
    values = resolve("graphspec", reg.docs["graphspec"][baseline], reg)
    drawn = str(values["specifications.graph_type"].value)
    graph_type = name if kind == "graph_type" else drawn
    if kind == "graph_type" and drawn != name:
        problems.append(f"{label}: baseline: '{baseline}' draws {drawn}, not {name}")
    params = _settable(reg, graph_type)

    bases: dict[str, Change] = {}
    entries: dict[str, Any] = {}
    for d in reversed(chain):  # nearest file wins
        listed = d.get("baselines")
        for bname, entry in (listed if isinstance(listed, dict) else {}).items():
            change, errs = _change(
                f"{label}: baselines.{bname}", entry, params, reg, name=str(bname)
            )
            problems += errs
            if change is not None:
                bases[str(bname)] = change
        cards = d.get("variations")
        entries.update(_cards(cards if isinstance(cards, dict) else {}, ""))

    own = definitions(kind, name if kind in ("graph_type", "layer") else None)
    always: tuple[Change, ...] = ()
    prefix = ""
    if kind == "layer":
        prefix = f"layers.{name}."
        drawn = next((d["layer"] for d in chain if isinstance(d.get("layer"), dict)), {})
        settings = next((d["settings"] for d in chain if isinstance(d.get("settings"), dict)), {})
        if settings:
            change, errs = _change(f"{label}: settings", settings, params, reg, name="settings")
            problems += errs
            if change is not None:
                always += change.parts or (change,)
        always = (
            *always,
            Change(f"{prefix}type", name),
            *(Change(f"{prefix}{p}", v) for p, v in flatten(drawn).items()),
        )
    missing = [p for p in own if p not in entries]
    if missing:
        problems.append(f"{label}: variations: missing {', '.join(missing)}")
    problems += [f"{label}: variations.{p}: unknown parameter" for p in entries if p not in own]

    variations: list[tuple[Parameter, Variation | None]] = []
    for path_ in entries:  # in the catalog files' order, the nearest file's after its base's
        p = own.get(path_)
        if p is None:
            continue
        where = f"{label}: variations.{path_}"
        entry = entries[path_]
        if entry == NO_CARD:
            variations.append((p, None))
            continue
        form = entry if isinstance(entry, dict) else {"value": entry}
        unknown = [k for k in form if k not in FORMS]
        if unknown or "value" not in form:
            problems.append(f"{where}: must be a value, {{value, from, with}} or {NO_CARD}")
            continue
        problems += _check(where, p, form["value"], reg)
        own_path = f"{prefix}{path_}"
        base = None
        if "from" in form:
            base = bases.get(str(form["from"]))
            if base is None:
                problems.append(f"{where}: from: no numbered baseline '{form['from']}'")
        withs: list[Change] = []
        for wpath, wvalue in (form.get("with") or {}).items():
            if kind == "layer" and wpath in own:  # the layer's own parameter
                wpath = f"{prefix}{wpath}"
            change, errs = _change(f"{where}: with", {wpath: wvalue}, params, reg)
            problems += errs
            if change is not None:
                withs.append(change)
        variations.append((p, Variation(p, (Change(own_path, form["value"]), *withs), base)))
    if problems:
        raise CatalogError(problems)
    return Catalog(kind, name, str(baseline), tuple(variations), always)
