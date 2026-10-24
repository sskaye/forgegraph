"""ForgeGraph: consistent, high-quality graphs from a declarative GraphSpec.

The API loads on first use, so `forgegraph --version` and `--help` don't load matplotlib and
pandas. Three of its names are also submodules (forgegraph.render, forgegraph.blank and
forgegraph.layout); the package's own module type makes each name mean the API whichever is
imported first.
"""

from __future__ import annotations

import sys
from importlib import import_module
from importlib.metadata import PackageNotFoundError, version
from types import ModuleType
from typing import TYPE_CHECKING, Any

try:
    __version__ = version("forgegraph")
except PackageNotFoundError:  # running from a source tree without installation
    __version__ = "0.0.0"

if TYPE_CHECKING:
    from forgegraph.blank import Blank, blank
    from forgegraph.graph import Graph, SpecError, graphspec, load, render, xy
    from forgegraph.layout import Layout
    from forgegraph.layout import render_layout as layout

_API = {  # name: (module, attribute)
    "Blank": ("forgegraph.blank", "Blank"),
    "blank": ("forgegraph.blank", "blank"),
    "Graph": ("forgegraph.graph", "Graph"),
    "SpecError": ("forgegraph.graph", "SpecError"),
    "graphspec": ("forgegraph.graph", "graphspec"),
    "load": ("forgegraph.graph", "load"),
    "render": ("forgegraph.graph", "render"),
    "xy": ("forgegraph.graph", "xy"),
    "Layout": ("forgegraph.layout", "Layout"),
    "layout": ("forgegraph.layout", "render_layout"),
}
_LOADED: dict[str, Any] = {}


class _Package(ModuleType):
    def __getattribute__(self, name: str) -> Any:
        if name in _API:
            if name not in _LOADED:
                module, attribute = _API[name]
                _LOADED[name] = getattr(import_module(module), attribute)
            return _LOADED[name]
        return super().__getattribute__(name)


sys.modules[__name__].__class__ = _Package

__all__ = [
    "Blank",
    "Graph",
    "Layout",
    "SpecError",
    "__version__",
    "blank",
    "graphspec",
    "layout",
    "load",
    "render",
    "xy",
]
