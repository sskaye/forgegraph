"""Which packs' specs a file may use, and which packs it's drawn with (packs has the configs'
rules).

A file being drawn may use the specs of the packs its configs allow; a pack's spec may build
on any spec that's loaded. Whatever is drawn with a pack the main config doesn't list is
non-standard.
"""

from __future__ import annotations

from typing import Any

from forgegraph.fonts import register_pack_fonts
from forgegraph.packs import fonts, user_config
from forgegraph.spec.common import kind_label, suggest
from forgegraph.spec.parameters import NONE
from forgegraph.spec.registry import Registry
from forgegraph.spec.resolve import chain, entries, resolve

PACK_TYPES = frozenset({"theme", "format", "graphspec", "layout", "schedule"})


def permission_problems(kind: str, doc: dict[str, Any], reg: Registry) -> list[str]:
    """Specs a file names itself (in extends, and a GraphSpec's or layout's theme and format)
    that it may not use. A file being drawn may use the specs of the packs its configs allow;
    a pack's spec may build on any spec that's loaded."""
    if reg.owner(kind, doc):
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
            problems.append(f"{where}: '{name}' is in the pack '{pack}', which {reg.allows()}")
    return problems


def packs_used(kind: str, doc: dict[str, Any], reg: Registry) -> set[str]:
    """The packs whose specs a file is drawn with: the specs it extends, and for a GraphSpec
    or layout, the theme and format it names (a layout, its format) with the specs they
    extend."""
    out = set()

    def add(k: str, d: dict[str, Any]) -> None:
        for link in chain(k, d, reg):
            pack = reg.owner(k, link)
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


def use_fonts(kind: str, doc: dict[str, Any], reg: Registry) -> None:
    """Register with matplotlib the fonts of the packs a file is drawn with (see
    packs_used), each font once."""
    for name in sorted(packs_used(kind, doc, reg)):
        register_pack_fonts(fonts(reg.packs[name]))


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
        unloaded = reg.unloaded(name)
        return [unloaded or f"no {kind_label(kind)} '{name}'{suggest(name, reg.docs[kind])}"]
    pack = reg.pack_of(kind, name)
    if pack is not None and pack not in reg.allowed:
        return [f"'{name}' is in the pack '{pack}', which {reg.allows()}"]
    return []


def found_problems(kind: str, name: str, reg: Registry) -> list[str]:
    """Why the spec of this kind and name can't be found, if it can't: a spec may be read
    and built on whether or not the configs allow its pack."""
    reg.reach(name)
    if name not in reg.docs[kind]:
        return [f"no {kind_label(kind)} '{name}'{suggest(name, reg.docs[kind])}"]
    return []
