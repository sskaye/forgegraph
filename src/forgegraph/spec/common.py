"""Shared building blocks: the base of every document model, and of every error that lists
problems."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict


class Model(BaseModel):
    """Base for every document model: unknown fields are errors, never silently ignored."""

    model_config = ConfigDict(extra="forbid")


class ProblemsError(ValueError):
    """An error that lists its problems, one per line; `problems` keeps them as a list."""

    def __init__(self, problems: list[str]) -> None:
        self.problems = problems
        super().__init__("\n".join(problems))
