"""A document as loaded: its kind, the document, the registry it's checked against and the
folder its own relative paths are found from (Loaded), read by load_document.

A path a file names is found from the folder of the file that sets it: `~` is the home
folder, an absolute path is used as is, and a relative one is joined to that folder.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from forgegraph.spec.explain import Explained, explain
from forgegraph.spec.parameters import is_none
from forgegraph.spec.registry import Registry, load_yaml, registry_for
from forgegraph.spec.resolve import Values, resolve, setter


@dataclass(frozen=True)
class Loaded:
    """A document of a kind, the registry it's checked against, holding it if it's named,
    and the folder its own relative paths are found from."""

    kind: str
    doc: Any
    reg: Registry
    folder: Path

    def resolve(self, graph_type: str | None = None) -> Values:
        """Every listed parameter's value (see resolve.resolve)."""
        return resolve(self.kind, self.doc, self.reg, graph_type)

    def explain(self, format: Values | None = None) -> Explained:
        """Every value a GraphSpec's graph is drawn with (see explain.explain)."""
        return explain(self.doc, self.reg, format)

    def setter(self, path: str) -> dict[str, Any] | None:
        """The file in the extends chain that sets a parameter (see resolve.setter)."""
        return setter(self.kind, self.doc, self.reg, path)

    def folder_for(self, source: dict[str, Any] | None) -> Path:
        """The folder relative paths in source, a file in the extends chain, are found from:
        its file's folder; `folder` for the document itself (or a file the registry has no
        path for)."""
        if source is None or source is self.doc:
            return self.folder
        known = self.reg.paths[self.kind].get(source["name"])
        return known.parent if known is not None else self.folder

    def place(self, path: str) -> Path | None:
        """Where the file or folder a parameter names is, found from the folder of the file
        that sets it; None if it's unset."""
        value = self.resolve().value(path)
        if is_none(value):
            return None
        return placed(value, self.folder_for(self.setter(path)))


def placed(value: Any, folder: Path) -> Path:
    """Where a path a file names is, for a file in folder (see the module)."""
    where = Path(str(value)).expanduser()
    return where if where.is_absolute() else folder / where


def load_document(
    kind: str, spec: dict[str, Any] | str | Path, registry: Registry | None = None
) -> Loaded:
    """A document of a kind, given as a file path or the document itself, checked against
    registry, or else its folder's (the working folder's for a document). registry itself
    is never changed."""
    if isinstance(spec, str | Path):
        path = Path(spec)
        doc = load_yaml(path)
        reg = (registry or registry_for(path.parent)).copy()
        if isinstance(doc, dict) and "name" in doc:
            reg.add(kind, doc, path)
        return Loaded(kind, doc, reg, path.parent)
    reg = (registry or registry_for(Path.cwd())).copy()
    if isinstance(spec, dict) and "name" in spec and spec["name"] not in reg.docs[kind]:
        reg.add(kind, spec)
    return Loaded(kind, spec, reg, Path.cwd())
