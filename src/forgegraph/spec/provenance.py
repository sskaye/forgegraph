"""The provenance record embedded in every saved file (architecture D13), as
src/forgegraph/spec/provenance.yaml specifies it.

minimal: the provenance level, the ForgeGraph version, the creation time, the GraphSpec as
written (without data.file and data.preprocessing), each spec used by name and version, and
whether the graph is non-standard. full: also every value it was drawn with (by kind), the
data's file and its preprocessing reference. off: no record.

A layout's files record the layout as written and, for each tab they show, each tile's
GraphSpec file and the same entries as a GraphSpec's, at the layout's format's level.
"""

from __future__ import annotations

import os
from datetime import UTC, datetime
from typing import Any, Literal

from pydantic import Field

from forgegraph.spec.common import Model


class DataRecord(Model):
    """What was read and drawn, for lint and a scheduled run's status: not recorded in files."""

    file: str | None = None  # data.file as written; None for a DataFrame passed in
    preprocessing: str | None = None  # data.preprocessing as written
    rows_read: int | None = Field(default=None, ge=0)
    rows_plotted: int | None = Field(default=None, ge=0)
    rows_dropped: dict[str, int] = {}  # reason -> count


class TileRecord(Model):
    file: str  # the GraphSpec file, as the layout names it
    graphspec: dict[str, Any]  # as written (minimal: without data.file, data.preprocessing)
    specs: dict[str, Any]  # each spec used, by kind: its name and version
    resolved: dict[str, dict[str, Any]] | None = None  # full only: every value, by kind
    data: str | None = None  # full only: data.file as written
    preprocessing: str | None = None  # full only: data.preprocessing as written


class ProvenanceRecord(Model):
    provenance_level: Literal["full", "minimal"]
    forgegraph_version: str
    created: str  # ISO 8601 UTC; from SOURCE_DATE_EPOCH when set
    graphspec: dict[str, Any] | None = None  # as written (minimal: without data.file,
    # data.preprocessing)
    specs: dict[str, Any] | None = None  # each spec used, by kind: its name and version
    nonstandard: bool = False  # drawn outside the specs the config permits (watermarked)
    nonstandard_packs: list[str] | None = None  # the packs used the main config doesn't list
    resolved: dict[str, dict[str, Any]] | None = None  # full only: every value, by kind
    data: str | None = None  # full only: data.file as written
    preprocessing: str | None = None  # full only: data.preprocessing as written
    layout: dict[str, Any] | None = None  # a layout's file, as written
    tabs: dict[str, dict[str, TileRecord]] | None = None  # a layout's tabs shown: each tile


def created() -> str:
    """When a record is made, in UTC: now, or SOURCE_DATE_EPOCH for reproducible builds."""
    epoch = os.environ.get("SOURCE_DATE_EPOCH")
    moment = datetime.fromtimestamp(int(epoch), UTC) if epoch else datetime.now(UTC)
    return moment.strftime("%Y-%m-%dT%H:%M:%SZ")


def plain(value: Any) -> Any:
    """Values as plain Python: NumPy scalars as Python numbers, inside dicts and lists too."""
    if isinstance(value, dict):
        return {k: plain(v) for k, v in value.items()}
    if isinstance(value, list):
        return [plain(v) for v in value]
    if hasattr(value, "item"):
        return value.item()
    return value
