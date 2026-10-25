"""Check and resolve theme, format, graph type, GraphSpec, layout and schedule files against
their definitions (see parameters.py).

- Every file has exactly the header fields name, version, description, extends,
  fixed_parameters and variable_parameters; the header's ranges come from the definition
  file like any parameter's.
- extends names another file of the same kind, or is None; with None the file must list
  every parameter of its kind.
- A file lists each parameter once, under fixed_parameters or variable_parameters, by
  category. A file that extends another may change any parameter, fixed or variable.
- In a theme or format, a graph type's name may be used as a heading; parameters under it
  apply to that graph type only and beat the general ones in the same file.
- A GraphSpec may also set any parameter its graph type, theme or format lists
  as variable, under the same category. It may not change a parameter that a GraphSpec it
  extends lists as fixed.
- A GraphSpec's layers are keyed by names it chooses; each has a type, one of its graph
  type's layer.types, and that layer type's parameters. Through extends, layers merge by name:
  a GraphSpec changes an inherited layer's parameters by naming it, replaces it by giving
  another type, and removes it with None; it can't change a layer listed as fixed.
- A format's width and height can't both be auto; a graph type's legend.method must be one
  of the theme's legend.methods; benchmark.data_column and benchmark.value are set
  together or not at all; with several y columns, axis.y.title is text or None; and
  anything else impossible (no font, nothing drawn, a backwards or non-positive log
  axis) is an error, never a silent substitute.
"""

from __future__ import annotations

import copy
import unicodedata
from collections.abc import Callable
from dataclasses import dataclass, field
from difflib import get_close_matches
from functools import cache
from importlib.resources import files
from pathlib import Path
from typing import Any

from ruamel.yaml import YAML

from forgegraph.fonts import WEIGHTS, font_available, font_weights, register_pack_fonts
from forgegraph.packs import FOLDERS as PACK_FOLDERS
from forgegraph.packs import (
    Config,
    Pack,
    fonts,
    pip_packs,
    read_pack,
    setup,
    user_config,
)
from forgegraph.spec.parameters import (
    BASE,
    COLLECTIONS,
    CORE_KINDS,
    HEADER,
    KINDS,
    NONE,
    SECTIONS,
    STEP,
    Parameter,
    base_folder,
    categories,
    check_parameter,
    check_value,
    definitions,
    flatten,
    graph_type_files,
    header_definitions,
)
from forgegraph.spec.schedule import Cadence, CadenceError

_yaml = YAML(typ="safe", pure=True)
OTHER_KINDS = ("graph_type", "theme", "format")  # files a GraphSpec names
HEADINGS = ("theme", "format")  # kinds that may use graph-type headings
CHOICE = {
    "graph_type": "specifications.graph_type",
    "theme": "specifications.theme",
    "format": "specifications.format",
}


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
                    for named in _specs_named(doc):
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

    def use_fonts(self, kind: str, doc: dict[str, Any]) -> None:
        """Register with matplotlib the fonts of the packs a file is drawn with (see
        packs_used), each font once."""
        for name in sorted(packs_used(kind, doc, self)):
            register_pack_fonts(fonts(self.packs[name]))

    def pack_of(self, kind: str, name: str) -> str | None:
        """The pack a spec comes from: None for a drawn file, or a graph or layer type."""
        path = self.paths[kind].get(name)
        if path is None or kind in CORE_KINDS:
            return None
        return next((p.name for p in self.packs.values() if p.folder in path.parents), None)

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


def load_document(
    kind: str, spec: dict[str, Any] | str | Path, registry: Registry | None = None
) -> tuple[Any, Registry, Path]:
    """A document of a kind, given as a file path or the document itself; the registry it's
    checked against (registry, or else its folder's), holding it if it's named; and the
    folder its own relative paths are found from. registry itself is never changed."""
    if isinstance(spec, str | Path):
        path = Path(spec)
        doc = load_yaml(path)
        reg = (registry or registry_for(path.parent)).copy()
        if isinstance(doc, dict) and "name" in doc:
            reg.add(kind, doc, path)
        return doc, reg, path.parent
    reg = (registry or registry_for(Path.cwd())).copy()
    if isinstance(spec, dict) and "name" in spec and spec["name"] not in reg.docs[kind]:
        reg.add(kind, spec)
    return spec, reg, Path.cwd()


def _specs_named(doc: dict[str, Any]) -> list[Any]:
    """The specs a pack's spec builds on: what it extends, and the theme and format a
    GraphSpec or layout names."""
    named = [doc.get("extends")]
    for section in ("fixed_parameters", "variable_parameters"):
        chosen = doc.get(section)
        chosen = chosen.get("specifications") if isinstance(chosen, dict) else None
        if isinstance(chosen, dict):
            named += [chosen.get("theme"), chosen.get("format")]
    return named


def _suggest(name: str, known: Any) -> str:
    close = get_close_matches(name, list(known), n=1)
    return f"; did you mean '{close[0]}'?" if close else ""


def _label(kind: str) -> str:
    return {"graph_type": "graph type", "graphspec": "GraphSpec"}.get(kind, kind)


def entries(
    kind: str, doc: dict[str, Any], reg: Registry
) -> list[tuple[str, str | None, str, Any]]:
    """(section, graph-type heading or None, parameter path, value) for every listed value.
    Anything not shaped as category.parameter is kept as written, to be reported."""
    out: list[tuple[str, str | None, str, Any]] = []
    for section in SECTIONS:
        tree = doc.get(section)
        if tree in (None, NONE):
            continue
        if not isinstance(tree, dict):
            out.append((section, None, "", tree))
            continue
        for category, params in tree.items():
            if category in COLLECTIONS.get(kind, ()):
                continue  # layers and tabs: see layer_problems and spec/layout.py
            if kind in HEADINGS and category in reg.docs["graph_type"] and isinstance(params, dict):
                for sub, sub_params in params.items():
                    out += _category(section, str(category), str(sub), sub_params)
            else:
                out += _category(section, None, str(category), params)
    return out


def _category(section: str, heading: str | None, category: str, params: Any) -> list:
    if not isinstance(params, dict):
        return [(section, heading, category, params)]
    return [
        (section, heading, path, value) for path, value in flatten(params, f"{category}.").items()
    ]


def chain(kind: str, doc: dict[str, Any], reg: Registry) -> list[dict[str, Any]]:
    """The document, then each file it extends, nearest first."""
    chain = [doc]
    seen = [doc.get("name")]
    parent = doc.get("extends")
    while parent not in (None, NONE):
        if parent in seen:
            raise ValueError(
                f"extends: '{parent}' extends itself, through {' → '.join(map(str, seen))}"
            )
        nxt = reg.docs[kind].get(parent)
        if nxt is None:
            unloaded = _unloaded(str(parent), reg, bool(_owner(kind, chain[-1], reg)))
            if unloaded:
                raise ValueError(f"extends: {unloaded}")
            raise ValueError(
                f"extends: unknown {_label(kind)} '{parent}'{_suggest(parent, reg.docs[kind])}"
            )
        chain.append(nxt)
        seen.append(parent)
        parent = nxt.get("extends")
    return chain


def _definitions_for(kind: str, doc: dict[str, Any], reg: Registry) -> dict[str, Parameter]:
    """A graph type's parameters are those of the graph type at the root of its chain."""
    if kind != "graph_type":
        return definitions(kind)
    root = chain(kind, doc, reg)[-1]["name"]
    if root not in graph_type_files():
        defined = ", ".join(graph_type_files())
        raise ValueError(
            f"extends: None, but only ForgeGraph defines graph types; extend one of: {defined}"
        )
    return definitions("graph_type", root)


@dataclass(frozen=True)
class Resolved:
    """A parameter's value as resolved: whether it's fixed, and which file set it."""

    value: Any
    fixed: bool
    origin: str  # e.g. "theme 'journal'", or "theme 'journal', under xy"


def resolve_detailed(
    kind: str, doc: dict[str, Any], reg: Registry, graph_type: str | None = None
) -> dict[str, Resolved]:
    """Every listed parameter's value, whether it's fixed, and which file set it. The nearest
    file that lists a parameter decides it; within one file, an entry under the graph type's
    heading beats the general one."""
    out: dict[str, Resolved] = {}
    for d in chain(kind, doc, reg):
        own: dict[str, tuple[int, Resolved]] = {}
        label = f"{_label(kind)} '{d.get('name')}'"
        for section, heading, path, value in entries(kind, d, reg):
            if heading not in (None, graph_type):
                continue
            rank = 0 if heading else 1
            origin = f"{label}, under {heading}" if heading else label
            if path not in own or rank < own[path][0]:
                own[path] = (rank, Resolved(value, section == SECTIONS[0], origin))
        for path, (_, r) in own.items():
            out.setdefault(path, r)
    return out


def setter(kind: str, doc: dict[str, Any], reg: Registry, path: str) -> dict[str, Any] | None:
    """The file in doc's extends chain that sets a parameter, nearest first; None if none of
    them lists it."""
    for d in chain(kind, doc, reg):
        if any(p == path for _, _, p, _ in entries(kind, d, reg)):
            return d
    return None


def folder_of(
    kind: str, source: dict[str, Any] | None, doc: dict[str, Any], reg: Registry, folder: Path
) -> Path:
    """The folder relative paths in source, a file in doc's extends chain, are found from:
    its file's folder; `folder` for doc itself (or a file the registry has no path for)."""
    if source is None or source is doc:
        return folder
    known = reg.paths[kind].get(source["name"])
    return known.parent if known is not None else folder


def resolve(
    kind: str, doc: dict[str, Any], reg: Registry, graph_type: str | None = None
) -> dict[str, tuple[Any, bool]]:
    """Every listed parameter's value and whether it's fixed, as {path: (value, fixed)}."""
    return {p: (r.value, r.fixed) for p, r in resolve_detailed(kind, doc, reg, graph_type).items()}


def validate(kind: str, doc: Any, reg: Registry | None = None) -> list[str]:
    """Every problem with a file of `kind`, as '<location>: <what's wrong>'. Each step runs
    only if the ones before found nothing: the header, each listed parameter, then (with
    extends None) every parameter listed, then the kind's own rules and what the configs
    allow."""
    reg = reg or builtin()
    if not isinstance(doc, dict):
        return ["(document): must be a mapping of fields"]
    errors = _header(kind, doc, reg)
    if errors:
        return errors
    try:
        defs = _definitions_for(kind, doc, reg)
    except ValueError as e:
        return [str(e)]
    errors, listed = _entry_problems(kind, doc, reg, defs)
    if errors:
        return errors
    if doc["extends"] == NONE:
        missing = [path for path in defs if path not in listed]
        if missing:
            return [
                "extends: None, so every parameter must be listed; missing: " + ", ".join(missing)
            ]
    rules = _RULES.get(kind)
    errors = rules(doc, reg) if rules else []
    if kind == "graphspec" and errors:  # its layers or values can't be resolved: stop here
        return errors
    errors += permission_problems(kind, doc, reg)
    if kind == "format":
        errors += _format_size(doc, reg)
    return errors


def _entry_problems(
    kind: str, doc: dict[str, Any], reg: Registry, defs: dict[str, Parameter]
) -> tuple[list[str], set[str]]:
    """Each listed parameter's problems (unknown, fixed elsewhere, out of range, listed
    twice), and the paths listed without a graph-type heading."""
    errors: list[str] = []
    names = reg.names()
    others = (
        _settable(doc, reg)
        if kind == "graphspec"
        else _format_settable(doc, reg)
        if kind == "layout"
        else {}
    )
    seen: dict[tuple[str | None, str], str] = {}
    for section, heading, path, value in entries(kind, doc, reg):
        where = f"{section}." + (f"{heading}." if heading else "")
        if path == "":
            errors.append(f"{section}: must be categories of parameters, or None")
            continue
        if (heading, path) in seen:
            errors.append(f"{where}{path}: also listed in {seen[heading, path]}")
            continue
        seen[heading, path] = section
        p = defs.get(path)
        if p is None and path in others:
            p, owner, fixed = others[path]
            if fixed:
                errors.append(f"{where}{path}: fixed by {owner}")
                continue
        if p is None:
            known = [*defs, *others]
            if "." in path:
                errors.append(f"{where}{path}: unknown parameter{_suggest(path, known)}")
            else:
                categories = {k.split(".")[0] for k in known}
                errors.append(f"{where}{path}: unknown category{_suggest(path, categories)}")
            continue
        unloaded = (
            _unloaded(value, reg, bool(_owner(kind, doc, reg)))
            if PACK_TYPES.intersection(p.range.types)
            else None
        )
        if unloaded:
            errors.append(f"{where}{path}: {unloaded}")
            continue
        for suffix, message in check_parameter(p, value, names):
            errors.append(f"{where}{path}{suffix}: {message}")
    return errors, {path for (heading, path) in seen if heading is None}


def _graphspec_problems(doc: dict[str, Any], reg: Registry) -> list[str]:
    errors = layer_problems(doc, reg)
    if errors:
        return errors
    errors = _inherited_fixed(doc, reg)
    return errors or _graphspec_rules(resolve_graphspec(doc, reg))


def _layout_problems(doc: dict[str, Any], reg: Registry) -> list[str]:
    from forgegraph.spec.layout import layout_problems

    return layout_problems(doc, reg)


def _schedule_problems(doc: dict[str, Any], reg: Registry) -> list[str]:
    try:
        Cadence.from_values({p: v for p, (v, _) in resolve("schedule", doc, reg).items()})
    except CadenceError as e:
        return [str(e)]
    return []


def _format_size(doc: dict[str, Any], reg: Registry) -> list[str]:
    for gt in [None, *reg.docs["graph_type"]]:
        r = resolve("format", doc, reg, gt)
        if (
            r.get("figure.width", (None,))[0] == "auto"
            and r.get("figure.height", (None,))[0] == "auto"
        ):
            return ["size: width and height can't both be auto"]
    return []


def _owner(kind: str, doc: dict[str, Any], reg: Registry) -> str | None:
    """The pack a document is a spec of, or None for a file being drawn."""
    name = doc.get("name")
    if not isinstance(name, str) or reg.docs[kind].get(name) is not doc:
        return None
    return reg.pack_of(kind, name)


def permission_problems(kind: str, doc: dict[str, Any], reg: Registry) -> list[str]:
    """Specs a file names itself (in extends, and a GraphSpec's or layout's theme and format)
    that it may not use. A file being drawn may use the specs of the packs its configs allow;
    a pack's spec may build on any spec that's loaded."""
    if _owner(kind, doc, reg):
        return []
    named = []
    if doc.get("extends") not in (None, NONE):
        named.append(("extends", str(doc["extends"])))
    for section, _, path, value in entries(kind, doc, reg):
        if path in ("specifications.theme", "specifications.format") and isinstance(value, str):
            named.append((f"{section}.{path}", value))
    problems = []
    for where, name in named:
        pack = name.split("/")[0] if "/" in name else None
        if pack is not None and pack not in reg.allowed:
            problems.append(f"{where}: '{name}' is in the pack '{pack}', which {_allows(reg)}")
    return problems


PACK_TYPES = frozenset({"theme", "format", "graphspec", "layout", "schedule"})


def packs_used(kind: str, doc: dict[str, Any], reg: Registry) -> set[str]:
    """The packs whose specs a file is drawn with: the specs it extends, and for a GraphSpec
    or layout, the theme and format it names (a layout, its format) with the specs they
    extend."""
    out = set()

    def add(k: str, d: dict[str, Any]) -> None:
        for link in chain(k, d, reg):
            pack = _owner(k, link, reg)
            if pack is not None:
                out.add(pack)

    add(kind, doc)
    if kind not in ("graphspec", "layout"):
        return out
    names = resolve(kind, doc, reg)
    for k in ("theme", "format") if kind == "graphspec" else ("format",):
        name = names[f"specifications.{k}"][0]
        if isinstance(name, str) and name in reg.docs[k]:
            add(k, reg.docs[k][name])
    return out


def nonstandard_note(packs: Any) -> str:
    """What a command says when what it shows uses packs the main config doesn't list."""
    listed = sorted(packs)
    names = ", ".join(f"'{p}'" for p in listed)
    one = len(listed) == 1
    return (
        f"Non-standard: {'pack' if one else 'packs'} {names} {'isn' if one else 'aren'}'t in "
        f"the main config ({user_config()}), so whatever is drawn with "
        f"{'it' if one else 'them'} is watermarked"
    )


def name_problems(kind: str, name: str, reg: Registry) -> list[str]:
    """Why a file being drawn can't use the spec of this kind and name, if it can't."""
    if name not in reg.docs[kind]:
        unloaded = _unloaded(name, reg)
        return [unloaded or f"no {_label(kind)} '{name}'{_suggest(name, reg.docs[kind])}"]
    pack = reg.pack_of(kind, name)
    if pack is not None and pack not in reg.allowed:
        return [f"'{name}' is in the pack '{pack}', which {_allows(reg)}"]
    return []


def found_problems(kind: str, name: str, reg: Registry) -> list[str]:
    """Why the spec of this kind and name can't be found, if it can't: a spec may be read
    and built on whether or not the configs allow its pack."""
    reg.reach(name)
    if name not in reg.docs[kind]:
        return [f"no {_label(kind)} '{name}'{_suggest(name, reg.docs[kind])}"]
    return []


def _unloaded(value: Any, reg: Registry, in_pack: bool = False) -> str | None:
    """For a pack/name whose pack isn't among those loaded: why it can't be used, by a file
    being drawn, or, in_pack, by a pack's spec, which may build on any pack it can find."""
    if not isinstance(value, str) or "/" not in value:
        return None
    pack = value.split("/")[0]
    if pack in reg.packs:
        return None
    if in_pack:
        return (
            f"'{value}' is in the pack '{pack}', which can't be found: no config that applies "
            "lists it, and no installed pip pack has that name"
        )
    return f"'{value}' is in the pack '{pack}', which {_allows(reg)}"


def _allows(reg: Registry) -> str:
    if not reg.configs:
        return f"isn't allowed: no config lists it, and without one only {BASE} may be used"
    return " and ".join(str(c.path) for c in reg.configs) + " doesn't allow"


def _header(kind: str, doc: dict[str, Any], reg: Registry) -> list[str]:
    errors = [f"{k}: required" for k in HEADER if k not in doc]
    errors += [
        f"{k}: a category of parameters; it goes under {SECTIONS[1]} or {SECTIONS[0]}"
        if k in categories("graphspec", "theme", "format", "graph_type")
        else f"{k}: unknown field; a file has only {', '.join(HEADER)}"
        for k in doc
        if k not in HEADER
    ]
    if errors:
        return errors
    names = reg.names()
    names[kind] = names[kind] - {doc["name"]}  # a file can't extend itself
    for key, p in header_definitions(kind).items():
        if key == "extends" and doc[key] not in (None, NONE) and doc[key] not in reg.docs[kind]:
            continue  # reported by chain, with a suggestion
        if err := check_value(doc[key], p.range, names):
            errors.append(f"{key}: {err}")
    try:
        chain(kind, doc, reg)
    except ValueError as e:
        errors.append(str(e))
    return errors


def _choices(doc: dict[str, Any], reg: Registry) -> dict[str, Any]:
    spec = resolve("graphspec", doc, reg)
    return {kind: spec.get(path, (None,))[0] for kind, path in CHOICE.items()}


def _format_settable(doc: dict[str, Any], reg: Registry) -> dict[str, tuple[Parameter, str, bool]]:
    """A layout's format's parameters, with whether each is fixed there: a layout can set the
    variable ones, as a GraphSpec can."""
    try:
        name = str(resolve("layout", doc, reg).get("specifications.format", (None,))[0])
        fmt = reg.docs["format"].get(name)
        if fmt is None:
            return {}
        defs = _definitions_for("format", fmt, reg)
        resolved = resolve("format", fmt, reg)
    except ValueError:
        return {}
    return {
        path: (p, f"format '{name}'", resolved.get(path, (None, p.fixed))[1])
        for path, p in defs.items()
    }


def _settable(doc: dict[str, Any], reg: Registry) -> dict[str, tuple[Parameter, str, bool]]:
    """Parameters of the GraphSpec's graph type, theme and format, with whether each is
    fixed there: {path: (definition, owner, fixed)}."""
    try:
        chosen = _choices(doc, reg)
    except ValueError:
        return {}
    out = {}
    for kind in OTHER_KINDS:
        other = reg.docs[kind].get(chosen[kind])
        if other is None:
            continue
        try:
            defs = _definitions_for(kind, other, reg)
            resolved = resolve(kind, other, reg, chosen["graph_type"] if kind in HEADINGS else None)
        except ValueError:
            continue
        for path, p in defs.items():
            fixed = resolved.get(path, (None, p.fixed))[1]
            out[path] = (p, f"{_label(kind)} '{chosen[kind]}'", fixed)
    return out


def _inherited_fixed(doc: dict[str, Any], reg: Registry) -> list[str]:
    parent = doc["extends"]
    if parent == NONE:
        return []
    inherited = resolve("graphspec", reg.docs["graphspec"][parent], reg)
    return [
        f"{section}.{path}: fixed by GraphSpec '{parent}'"
        for section, _, path, _ in entries("graphspec", doc, reg)
        if inherited.get(path, (None, False))[1]
    ]


def explain(doc: dict[str, Any], reg: Registry | None = None) -> dict[str, dict[str, Resolved]]:
    """Every value a graph is drawn with, by kind, with whether it's fixed and which file set
    it: {"graphspec": {...}, "graph_type": {...}, "theme": {...}, "format": {...}}. The
    GraphSpec's settings replace variable values. "layers" holds each layer by name: its type
    and every parameter of that type, as {"type": ..., path: value}."""
    reg = reg or builtin()
    spec = resolve_detailed("graphspec", doc, reg)
    chosen = _choices(doc, reg)
    own = definitions("graphspec")
    out = {"graphspec": {p: r for p, r in spec.items() if p in own}}
    out["layers"] = {
        name: Resolved(_with_defaults(r.value), r.fixed, r.origin)
        for name, r in resolve_layers(doc, reg).items()
    }
    for kind in OTHER_KINDS:
        other = reg.docs[kind][chosen[kind]]
        defs = _definitions_for(kind, other, reg)
        heading = chosen["graph_type"] if kind in HEADINGS else None
        values = resolve_detailed(kind, other, reg, heading)
        values.update({p: r for p, r in spec.items() if p in defs})
        out[kind] = values
    return out


def resolve_graphspec(
    doc: dict[str, Any], reg: Registry | None = None
) -> dict[str, dict[str, Any]]:
    """The values a graph is drawn with, by kind (see explain)."""
    return {
        kind: {p: r.value for p, r in values.items()} for kind, values in explain(doc, reg).items()
    }


def _graphspec_rules(values: dict[str, dict[str, Any]]) -> list[str]:
    """What a GraphSpec's values, resolved once, may not combine."""
    return _method_allowed(values) + _benchmark_complete(values) + _graph_rules(values)


def _method_allowed(values: dict[str, dict[str, Any]]) -> list[str]:
    method = values["graph_type"].get("legend.method")
    methods = values["theme"]["legend.methods"]
    if method is None or method in methods:
        return []
    theme = values["graphspec"]["specifications.theme"]
    return [f"legend.method: theme '{theme}' allows only {', '.join(methods)}"]


def _benchmark_complete(values: dict[str, dict[str, Any]]) -> list[str]:
    gt = values["graph_type"]
    column, value = gt.get("benchmark.data_column"), gt.get("benchmark.value")
    if (column in (None, NONE)) == (value in (None, NONE)):
        return []
    return ["benchmark: set data_column and value together, or neither"]


def _graph_rules(values: dict[str, dict[str, Any]]) -> list[str]:
    """Combinations of graph-type values that ask for something impossible."""
    v = values["graph_type"]
    errors = []
    columns = v.get("axis.y.data.column")
    several = isinstance(columns, list) and len(columns) > 1
    if several and v.get("axis.y.title") == "column_name":
        errors.append("axis.y.title: several y columns have no single name; set a title, or None")
    if (
        several
        and v.get("encoding.color") == "column_name"
        and v.get("legend.key.title.text") == "column_name"
    ):
        errors.append(
            "legend.key.title.text: encoding.color is column_name, which has no single name; "
            "set a title, or None"
        )
    if all(v.get(f"mark.{m}.show") is False for m in ("line", "marker", "bar")):
        errors.append(
            "mark.line.show, mark.marker.show, mark.bar.show: all false, so nothing would be drawn"
        )
    for axis in ("axis.x", "axis.y"):
        algorithm, step = v.get(f"{axis}.tick.algorithm"), v.get(f"{axis}.tick.step")
        if algorithm == "manual" and step in (None, NONE):
            errors.append(f"{axis}.tick.algorithm: manual needs tick.step")
        if algorithm != "manual" and step not in (None, NONE):
            errors.append(f"{axis}.tick.step: applies only with tick.algorithm manual")
        if isinstance(step, str) and step != NONE and not STEP.match(step):
            errors.append(
                f"{axis}.tick.step: '{step}' isn't a count and a unit, e.g. \"2 week\" "
                "(units: sec, min, hour, day, week, month, year)"
            )
        lo, hi = v.get(f"{axis}.min"), v.get(f"{axis}.max")
        numbers = [x for x in (lo, hi) if isinstance(x, int | float) and not isinstance(x, bool)]
        if len(numbers) == 2 and numbers[0] >= numbers[1]:
            errors.append(f"{axis}.min: must be below {axis}.max ({lo} is not below {hi})")
        if v.get(f"{axis}.scale") == "log":
            for end, value in (("min", lo), ("max", hi)):
                if value in numbers and value <= 0:
                    errors.append(f"{axis}.{end}: a log axis needs values above 0, not {value}")
    return errors


def _theme_rules(doc: dict[str, Any], reg: Registry) -> list[str]:
    """A theme's fonts are installed (its packs' registered first), its weights are ones its
    family has, and its watermark text draws something."""
    reg.use_fonts("theme", doc)
    errors = []
    for section, heading, path, value in entries("theme", doc, reg):
        if path == "font.family" and isinstance(value, str) and not font_available(value):
            where = f"{section}." + (f"{heading}." if heading else "")
            errors.append(f"{where}font.family: no font '{value}' is bundled or installed")
    if errors:
        return errors
    headings = {h for d in chain("theme", doc, reg) for _, h, _, _ in entries("theme", d, reg)}
    for heading in sorted(headings, key=lambda h: h or ""):
        values = resolve("theme", doc, reg, heading)
        where = f" under {heading}" if heading else ""
        family = str(values["font.family"][0])
        has = font_weights(family)
        for path, (value, _) in values.items():
            if path.endswith("weight") and WEIGHTS.get(value) not in has:
                names = ", ".join(n for n, w in WEIGHTS.items() if w in has)
                errors.append(f"{path}{where}: {family} has no {value} weight; it has {names}")
        if "watermark.text" in values and not _visible(str(values["watermark.text"][0])):
            errors.append(
                f"watermark.text{where}: has no letters; the watermark is drawn from its "
                "letters' outlines, so it needs at least one visible character"
            )
    return errors


# Each kind's own rules, after its parameters are each found valid (see validate).
_RULES: dict[str, Callable[[dict[str, Any], Registry], list[str]]] = {
    "graphspec": _graphspec_problems,
    "layout": _layout_problems,
    "schedule": _schedule_problems,
    "theme": _theme_rules,
}


def _visible(text: str) -> bool:
    """Whether text has a character that draws something: not a space or a control or
    formatting character."""
    return any(not (c.isspace() or unicodedata.category(c).startswith("C")) for c in text)


def drawing_problems(doc: dict[str, Any], reg: Registry | None = None) -> list[str]:
    """What a valid GraphSpec still lacks before the graph can be drawn: parameters its
    graph type defines with no default."""
    reg = reg or builtin()
    values = resolve_graphspec(doc, reg)["graph_type"]
    gt = reg.docs["graph_type"][_choices(doc, reg)["graph_type"]]
    problems = [
        f"{path}: must be set before the graph can be drawn"
        for path, p in _definitions_for("graph_type", gt, reg).items()
        if p.required and values.get(path) in (None, NONE)
    ]
    for name, r in resolve_layers(doc, reg).items():
        layer = _with_defaults(r.value)
        problems += [
            f"layers.{name}.{path}: must be set before the graph can be drawn"
            for path, p in definitions("layer", layer["type"]).items()
            if p.required and layer.get(path) in (None, NONE)
        ]
    return problems


def _layers_in(d: dict[str, Any]) -> list[tuple[str, str, Any]]:
    """(section, name, entry) for each layer a file lists, in order."""
    out = []
    for section in SECTIONS:
        tree = d.get(section)
        layers = tree.get("layers") if isinstance(tree, dict) else None
        if isinstance(layers, dict):
            out += [(section, str(name), entry) for name, entry in layers.items()]
        elif layers is not None:
            out.append((section, "", layers))
    return out


def _merge(base: dict[str, Any], change: dict[str, Any]) -> dict[str, Any]:
    out = dict(base)
    for key, value in change.items():
        if isinstance(value, dict) and isinstance(out.get(key), dict):
            out[key] = _merge(out[key], value)
        else:
            out[key] = value
    return out


def resolve_layers(doc: dict[str, Any], reg: Registry) -> dict[str, Resolved]:
    """The GraphSpec's layers by name, in drawing order: those it inherits first, then its
    own. Each value is the layer as listed (type and parameters), merged by name down the
    extends chain."""
    out: dict[str, Resolved] = {}
    for d in reversed(chain("graphspec", doc, reg)):
        label = f"GraphSpec '{d.get('name')}'"
        for section, name, entry in _layers_in(d):
            if entry in (None, NONE):
                out.pop(name, None)
                continue
            if not isinstance(entry, dict):
                continue
            old = out.get(name)
            same = old is not None and entry.get("type", old.value.get("type")) == old.value.get(
                "type"
            )
            value = _merge(old.value, entry) if same and old is not None else dict(entry)
            out[name] = Resolved(value, section == SECTIONS[0], label)
    return out


def _with_defaults(layer: dict[str, Any]) -> dict[str, Any]:
    """A layer as {"type": ..., path: value}, with every parameter its type defines."""
    kind = layer["type"]
    listed = flatten({k: v for k, v in layer.items() if k != "type"})
    return {
        "type": kind,
        **{p: listed.get(p, d.default) for p, d in definitions("layer", kind).items()},
    }


def layer_problems(doc: dict[str, Any], reg: Registry) -> list[str]:
    """Problems with the layers a GraphSpec lists, and with the layers it ends up with."""
    errors = []
    try:
        gt_name = _choices(doc, reg)["graph_type"]
        gt = resolve("graph_type", reg.docs["graph_type"][gt_name], reg)
    except (ValueError, KeyError):
        return []
    accepted = gt.get("layer.types", ([],))[0] or []
    parent = doc.get("extends")
    inherited = (
        resolve_layers(reg.docs["graphspec"][parent], reg)
        if parent not in (None, NONE) and parent in reg.docs["graphspec"]
        else {}
    )
    names = reg.names()
    for section, name, entry in _layers_in(doc):
        where = f"{section}.layers"
        if name == "":
            errors.append(f"{where}: must be layers keyed by name, or None")
            continue
        where = f"{where}.{name}"
        if name in inherited and inherited[name].fixed:
            errors.append(f"{where}: fixed by {inherited[name].origin}")
            continue
        if entry in (None, NONE):
            continue
        if not isinstance(entry, dict):
            errors.append(f"{where}: must be a layer: its type, then its parameters")
            continue
        kind = entry.get("type", inherited[name].value.get("type") if name in inherited else None)
        if kind in (None, NONE):
            errors.append(f"{where}.type: required: one of {', '.join(map(str, accepted))}")
            continue
        if kind not in reg.docs["layer"]:
            errors.append(
                f"{where}.type: unknown layer type '{kind}'{_suggest(str(kind), reg.docs['layer'])}"
            )
            continue
        if kind not in accepted:
            errors.append(
                f"{where}.type: graph type '{gt_name}' takes only {', '.join(map(str, accepted))}"
            )
            continue
        defs = definitions("layer", str(kind))
        for path, value in flatten({k: v for k, v in entry.items() if k != "type"}).items():
            p = defs.get(path)
            if p is None:
                errors.append(f"{where}.{path}: unknown parameter of {kind}{_suggest(path, defs)}")
                continue
            for suffix, message in check_parameter(p, value, names):
                errors.append(f"{where}.{path}{suffix}: {message}")
    return errors
