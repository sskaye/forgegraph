"""A resolved theme and format, as matplotlib settings and drawing values.

Every size in a theme is a multiple of the format's base size (figure.base_size). Drawing
happens inside `isolated()`, which starts from matplotlib's defaults plus these settings,
so a user's matplotlibrc or an earlier `plt.style.use()` can't leak in (architecture D2).
"""

from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager
from dataclasses import dataclass
from functools import cached_property
from typing import Any

import matplotlib
from matplotlib.colors import Colormap, LinearSegmentedColormap, to_rgb
from matplotlib.font_manager import FontProperties

from forgegraph.drawing import text
from forgegraph.fonts import WEIGHTS, register_fonts
from forgegraph.spec.parameters import NONE

MM_PER_INCH = 25.4
MARKERS = {
    "circle": "o",
    "square": "s",
    "triangle_up": "^",
    "triangle_down": "v",
    "diamond": "D",
    "cross": "x",
    "plus": "+",
}
LINE_STYLES = {"solid": "-", "dashed": "--", "dotted": ":", "dashdot": "-."}
COLOR_SCALES = {
    "viridis": "viridis",
    "cividis": "cividis",
    "plasma": "plasma",
    "inferno": "inferno",
    "magma": "magma",
    "greys": "Greys",
    "blues": "Blues",
    "red_blue": "RdBu_r",
}
# Named categorical palettes for series.colors, in their published order: Okabe & Ito,
# "Color Universal Design" (2008), without black and with yellow last (low contrast on
# white); Paul Tol's "bright" and "muted" schemes (muted without its pale grey, which Tol
# reserves for missing data); Tableau's "Tableau 10" and "Color Blind", as Tableau Desktop
# defines them (as recorded in the ggthemes R package). All but tableau_10 are color-blind safe.
PALETTES = {
    "okabe_ito": ["#0072B2", "#E69F00", "#009E73", "#D55E00", "#56B4E9", "#CC79A7", "#F0E442"],
    "tol_bright": ["#4477AA", "#EE6677", "#228833", "#CCBB44", "#66CCEE", "#AA3377", "#BBBBBB"],
    "tableau_10": [
        "#4E79A7", "#F28E2B", "#E15759", "#76B7B2", "#59A14F",
        "#EDC948", "#B07AA1", "#FF9DA7", "#9C755F", "#BAB0AC",
    ],
    "color_blind": [
        "#1170AA", "#FC7D0B", "#A3ACB9", "#57606C", "#5FA2CE",
        "#C85200", "#7B848F", "#A3CCE9", "#FFBC79", "#C8D0D9",
    ],
    "tol_muted": [
        "#CC6677", "#332288", "#DDCC77", "#117733", "#88CCEE",
        "#882255", "#44AA99", "#999933", "#AA4499",
    ],
}  # fmt: skip
TICK_DIRECTIONS = {"out": "out", "in": "in", "both": "inout"}
LAYOUT_DPI = 100  # figures are laid out at this resolution and saved at the format's dpi


def unset(value: Any) -> bool:
    return value is None or value == NONE


@dataclass(frozen=True)
class Style:
    theme: dict[str, Any]  # resolved theme values by path
    format: dict[str, Any]  # resolved format values by path
    fixed: frozenset[str] = frozenset()  # the theme parameters a GraphSpec can't set

    @property
    def base(self) -> float:
        """The format's base size (figure.base_size), in points."""
        return float(self.format["figure.base_size"])

    def pt(self, path: str) -> float:
        """A theme size (a multiple of the base size), in points."""
        return float(self.theme[path]) * self.base

    def weight(self, path: str) -> int:
        """A theme weight, as a font weight number."""
        return WEIGHTS[self.theme[path]]

    def font(self, size: str | float, weight: str) -> FontProperties:
        """The theme's font (font.family) at a theme size's path (or a size in points) and
        a theme weight's path."""
        points = self.pt(size) if isinstance(size, str) else float(size)
        return text.font(str(self.theme["font.family"]), points, self.weight(weight))

    def color(self, path: str) -> str:
        value = self.theme[path]
        return "none" if unset(value) else str(value)

    def series_colors(self) -> list[str]:
        """series.colors as a list: a named palette's colors, or the theme's own."""
        value = self.theme["series.colors"]
        return list(PALETTES[value]) if isinstance(value, str) else list(value)

    def colormap(self) -> Colormap:
        value = self.theme["legend.color_bar.colors"]
        if isinstance(value, list):
            return LinearSegmentedColormap.from_list("forgegraph", [to_rgb(c) for c in value])
        if value in COLOR_SCALES:
            return matplotlib.colormaps[COLOR_SCALES[value]]
        r, g, b = to_rgb(value)  # one hex color: from very light to that color
        light = (1 - 0.88 * (1 - r), 1 - 0.88 * (1 - g), 1 - 0.88 * (1 - b))
        return LinearSegmentedColormap.from_list("forgegraph", [light, (r, g, b)])

    @cached_property
    def settings(self) -> dict[str, Any]:
        """Matplotlib's defaults with rc() over them, checked once: what drawing uses."""
        checked = matplotlib.RcParams({**dict.copy(matplotlib.rcParamsDefault), **self.rc()})
        return {k: v for k, v in dict.items(checked) if k != "backend"}

    def rc(self) -> dict[str, Any]:
        t, family = self.theme, str(self.theme["font.family"])
        text = self.color("font.color")
        background = self.color("background.color")
        direction = TICK_DIRECTIONS[t["axis.tick.direction"]]
        return {
            "font.family": [family],
            "font.size": self.base,
            "text.color": text,
            "axes.labelcolor": text,
            "axes.edgecolor": self.color("plot_area.line.color"),
            "font.weight": self.weight("font.weight"),
            "xtick.color": text,
            "ytick.color": text,
            "axes.titlesize": self.pt("title.size"),
            "axes.titleweight": self.weight("title.weight"),
            "axes.labelsize": self.pt("axis.title.size"),
            "axes.labelweight": self.weight("axis.title.weight"),
            "xtick.labelsize": self.pt("axis.tick.label.size"),
            "ytick.labelsize": self.pt("axis.tick.label.size"),
            "xtick.direction": direction,
            "ytick.direction": direction,
            "xtick.major.size": self.pt("axis.tick.length"),
            "ytick.major.size": self.pt("axis.tick.length"),
            "xtick.major.width": self.pt("axis.tick.width"),
            # tick label pads are set from the visible gap by drawing.spacing
            "ytick.alignment": "baseline",
            "xtick.minor.size": self.pt("axis.tick.minor.length"),
            "ytick.minor.size": self.pt("axis.tick.minor.length"),
            "xtick.minor.width": self.pt("axis.tick.minor.width"),
            "ytick.minor.width": self.pt("axis.tick.minor.width"),
            "ytick.major.width": self.pt("axis.tick.width"),
            "xtick.minor.visible": False,
            "ytick.minor.visible": False,
            "axes.linewidth": self.pt("plot_area.line.width"),
            "axes.xmargin": float(t["plot_area.margin"]),
            "axes.ymargin": float(t["plot_area.margin"]),
            "axes.autolimit_mode": "data",
            "axes.grid": False,
            "grid.color": self.color("grid.color"),
            "grid.linewidth": self.pt("grid.line.width"),
            "grid.linestyle": LINE_STYLES[t["grid.line.style"]],
            "lines.linewidth": self.pt("series.line.width"),
            "lines.solid_capstyle": str(t["series.line.cap"]),
            "lines.solid_joinstyle": str(t["series.line.join"]),
            "lines.dash_joinstyle": str(t["series.line.join"]),
            "lines.markersize": self.pt("series.marker.size"),
            "lines.markeredgewidth": self.pt("series.marker.edge.width"),
            "figure.facecolor": background,
            "axes.facecolor": background,
            "savefig.facecolor": background,
            "savefig.transparent": background == "none",
            "figure.dpi": LAYOUT_DPI,
            # no hinting: text keeps the same shape and width at every resolution, so what's
            # laid out at LAYOUT_DPI is what's saved at the format's dpi
            "text.hinting": "no_hinting",
            "savefig.dpi": int(self.format["output.dpi"]),
            "mathtext.fontset": "custom",
            "mathtext.rm": family,
            "mathtext.it": f"{family}:italic",
            "mathtext.bf": f"{family}:bold",
            "mathtext.sf": family,
            "mathtext.tt": family,
            "mathtext.cal": family,
            "mathtext.default": "regular",
            "pdf.fonttype": 42,
            "ps.fonttype": 42,
            "svg.hashsalt": "forgegraph",
        }


@contextmanager
def isolated(style: Style) -> Iterator[None]:
    """Matplotlib's defaults plus the style, whatever the user's own settings are. The
    settings are checked once per style; entering and leaving copy them in and back, as
    matplotlib's own rc_context restores what it saved."""
    register_fonts()
    params = matplotlib.rcParams
    saved = dict.copy(params)  # raw: reading "backend" through rcParams would resolve it
    dict.update(params, style.settings)
    try:
        yield
    finally:
        dict.update(params, saved)
