"""ForgeGraph: consistent, high-quality graphs from a declarative GraphSpec.

The API loads on first use, so `forgegraph --version` and `--help` don't load matplotlib and
pandas.
"""

from __future__ import annotations

from importlib import import_module
from importlib.metadata import PackageNotFoundError, version
from typing import TYPE_CHECKING, Any

try:
    __version__ = version("forgegraph")
except PackageNotFoundError:  # running from a source tree without installation
    __version__ = "0.0.0"

if TYPE_CHECKING:
    from forgegraph.canvas import Blank, blank
    from forgegraph.graph import Graph, SpecError, graphspec, load, render, xy
    from forgegraph.layouts import Layout
    from forgegraph.layouts import render_layout as layout

_API = {  # name: (module, attribute)
    "Blank": ("forgegraph.canvas", "Blank"),
    "blank": ("forgegraph.canvas", "blank"),
    "Graph": ("forgegraph.graph", "Graph"),
    "SpecError": ("forgegraph.graph", "SpecError"),
    "graphspec": ("forgegraph.graph", "graphspec"),
    "load": ("forgegraph.graph", "load"),
    "render": ("forgegraph.graph", "render"),
    "xy": ("forgegraph.graph", "xy"),
    "Layout": ("forgegraph.layouts", "Layout"),
    "layout": ("forgegraph.layouts", "render_layout"),
}


def __getattr__(name: str) -> Any:
    if name not in _API:
        raise AttributeError(f"module 'forgegraph' has no attribute {name!r}")
    module, attribute = _API[name]
    value = globals()[name] = getattr(import_module(module), attribute)
    return value


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
