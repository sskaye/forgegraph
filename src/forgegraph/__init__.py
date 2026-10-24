"""ForgeGraph: consistent, high-quality graphs from a declarative GraphSpec."""

from importlib.metadata import PackageNotFoundError, version

try:
    __version__ = version("forgegraph")
except PackageNotFoundError:  # running from a source tree without installation
    __version__ = "0.0.0"

from forgegraph.blank import Blank, blank
from forgegraph.graph import Graph, SpecError, graphspec, load, render, xy
from forgegraph.layout import Layout
from forgegraph.layout import render_layout as layout

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
