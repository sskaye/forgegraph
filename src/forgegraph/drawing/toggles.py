"""Toggled items' images: a figure cut into images laid exactly over each other on a page.

A figure with a toggle layer (spec/toggles.py) is drawn once, with everything shown, so its
axes, keys and labels are placed as usual. Its items hidden when the page opens are then
hidden in the figure itself (hide), so files show the page's opening state.

For the page, the figure is cut into images (slices): its artists in the order matplotlib
draws them (the figure's background, then each Axes' background and children, each list by
zorder), each run of artists belonging to the same items becoming one image. The images are
the figure's own size, so they line up exactly, and stacked in that order they draw as the
figure does: an item's image stays under whatever is drawn over it, such as a reference
line under a series' markers. The page hides an image when any of its items is hidden.
"""

from __future__ import annotations

from collections.abc import Callable, Iterable
from dataclasses import dataclass
from typing import Any

from matplotlib.artist import Artist
from matplotlib.axes import Axes
from matplotlib.figure import Figure

from forgegraph.drawing import export

HIDDEN = "_forgegraph_hidden"  # on a figure: the artists hide() hid


@dataclass(frozen=True)
class Slice:
    """One image of a figure cut for its toggles: the items it draws, all of which must be
    shown for it to show (none: what can't be hidden), and its SVG."""

    items: frozenset[str]
    svg: bytes


Member = Callable[[Artist], frozenset[str]]  # the items an artist belongs to


def hide(fig: Figure, member: Member, names: Iterable[str]) -> None:
    """Hide the artists of these items, and keep them, so the slices can draw them."""
    names = set(names)
    hidden = [a for a in drawn(fig) if member(a) & names and a.get_visible()]
    for a in hidden:
        a.set_visible(False)
    setattr(fig, HIDDEN, [*getattr(fig, HIDDEN, []), *hidden])


def drawn(fig: Figure) -> list[Artist]:
    """The figure's artists in the order it draws them: its background, then its children by
    zorder, an Axes as its background and then its children by zorder."""
    out: list[Artist] = [fig.patch]
    children = [c for c in fig.get_children() if c is not fig.patch and not c.get_animated()]
    for a in sorted(children, key=lambda c: c.get_zorder()):
        if isinstance(a, Axes):
            out.append(a.patch)
            inside = [c for c in a.get_children() if c is not a.patch]
            out += sorted(inside, key=lambda c: c.get_zorder())
        else:
            out.append(a)
    return out


def slices(fig: Figure, member: Member, dpi: int) -> list[Slice]:
    """The figure cut into images, in the order they're stacked: each run of artists that
    belong to the same items (see the module), leaving out runs that draw nothing."""
    order = drawn(fig)
    hidden = {id(a) for a in getattr(fig, HIDDEN, [])}
    shown = {id(a): a.get_visible() or id(a) in hidden for a in order}
    runs: list[tuple[frozenset[str], list[Artist]]] = []
    for a in order:
        items = member(a)
        if runs and runs[-1][0] == items:
            runs[-1][1].append(a)
        else:
            runs.append((items, [a]))
    before = [(a, a.get_visible()) for a in order]
    out = []
    try:
        for items, run in runs:
            ids = {id(a) for a in run}
            if not any(shown[i] for i in ids):
                continue
            for a in order:
                a.set_visible(id(a) in ids and shown[id(a)])
            out.append(Slice(items, export.svg(fig, dpi)))
    finally:
        for a, visible in before:
            a.set_visible(visible)
    return out


def member_of(owned: dict[Any, dict[str, str]]) -> Member:
    """The items an artist belongs to, from its owners (drawing/owners.py): owned gives, for
    each Axes with toggles, each toggled owner's item."""
    from forgegraph.drawing import owners

    def member(a: Any) -> frozenset[str]:
        table = owned.get(getattr(a, "axes", None), {})
        return frozenset(table[o] for o in owners.of(a) if o in table)

    return member
