"""Shared building blocks for ForgeGraph's document models."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict


class Model(BaseModel):
    """Base for every document model: unknown fields are errors, never silently ignored."""

    model_config = ConfigDict(extra="forbid", populate_by_name=True)
