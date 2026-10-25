"""Shared building blocks: the base of every document model and of every error that lists
problems, and the words problems share."""

from __future__ import annotations

from difflib import get_close_matches
from typing import Any

from pydantic import BaseModel, ConfigDict


class Model(BaseModel):
    """Base for every document model: unknown fields are errors, never silently ignored."""

    model_config = ConfigDict(extra="forbid")


class ProblemsError(ValueError):
    """An error that lists its problems, one per line; `problems` keeps them as a list."""

    def __init__(self, problems: list[str]) -> None:
        self.problems = problems
        super().__init__("\n".join(problems))


def suggest(name: str, known: Any) -> str:
    """'; did you mean ...?' with the known names inside name, if it's a category of them,
    else the known name closest to name, or '' if none is close."""
    inside = [k for k in known if k.startswith(f"{name}.")]
    if inside:
        return f"; did you mean {' or '.join(repr(k) for k in inside)}?"
    close = get_close_matches(name, list(known), n=1)
    return f"; did you mean '{close[0]}'?" if close else ""


def kind_label(kind: str) -> str:
    """A kind as problems name it: "graph type", "GraphSpec", "theme" and so on."""
    return {"graph_type": "graph type", "graphspec": "GraphSpec"}.get(kind, kind)
