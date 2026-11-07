"""Which series or layer each drawn artist belongs to, for the ids an SVG gives them (#117).

Drawing marks each artist with its owner: fg-series-<name> for a series' line, markers,
bars, error bars, value labels and direct label; fg-layer-<name> for a layer's lines, fill
and label, and a note; fg-key-<name> for a key's entry, and fg-key for the rest of a key; and
fg-cells for a grid of cells. Saving an SVG (drawing/figure.GraphCanvas) gives each marked
artist the id fg-<owner>-<n>, numbered from 1 within its owner, so a page can find a whole
series or layer by the start of the ids. The ids are set only while saving, because the
drawing code finds what it drew by its own ids.
"""

from __future__ import annotations

import re
from collections.abc import Iterator
from contextlib import contextmanager
from typing import Any

OWNER = "_forgegraph_owner"
ALSO = "_forgegraph_also"  # a second owner (tag_new)


def name(kind: str, of: Any = None) -> str:
    """An owner: a kind (series, layer, key, cells), and the name it was given, as an id can
    hold it."""
    if of is None:
        return kind
    return f"{kind}-{re.sub(r'[^A-Za-z0-9._-]+', '_', str(of))}"


def tag(artist: Any, owner: str | None) -> Any:
    """Mark an artist with its owner, unless it has one; return the artist."""
    if owner is not None and not hasattr(artist, OWNER):
        setattr(artist, OWNER, owner)
    return artist


def tag_new(ax: Any, before: set[int], owner: str, also: bool = False) -> None:
    """Mark every artist drawn in ax since before (the ids of its children then); also: as
    a second owner, as an error bar has its series and its layer."""
    for artist in ax.get_children():
        if id(artist) not in before:
            if also:
                setattr(artist, ALSO, owner)
            else:
                tag(artist, owner)


def of(artist: Any) -> tuple[str, ...]:
    """An artist's owners: its own, and a second one if it has one."""
    return tuple(getattr(artist, a) for a in (OWNER, ALSO) if hasattr(artist, a))


def children(ax: Any) -> set[int]:
    return {id(a) for a in ax.get_children()}


@contextmanager
def named_ids(fig: Any) -> Iterator[None]:
    """Give every marked artist in fig the id fg-<owner>-<n> while an SVG is saved."""
    marked = fig.findobj(lambda a: hasattr(a, OWNER))
    old = [(a, a.get_gid()) for a in marked]
    counts: dict[str, int] = {}
    for a in marked:
        owner = getattr(a, OWNER)
        counts[owner] = counts.get(owner, 0) + 1
        a.set_gid(f"fg-{owner}-{counts[owner]}")
    try:
        yield
    finally:
        for a, gid in old:
            a.set_gid(gid)
