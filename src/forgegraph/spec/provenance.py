"""The provenance record embedded in every saved file (architecture D13), as
src/forgegraph/specifications/provenance.yaml specifies it.

minimal: the provenance level, the ForgeGraph version, the creation time, the GraphSpec as
written (without data.file and data.preprocessing), each spec used by name and version, and
whether the graph is non-standard. full: also every value it was drawn with (by kind), the
data's file and its preprocessing reference. off: no record.

A layout's files record the layout as written and, for each tab they show, each tile's
GraphSpec file and the same entries as a GraphSpec's, at the layout's format's level.
"""

from __future__ import annotations

import copy
import os
from datetime import UTC, date, datetime
from typing import Any, Literal

from pydantic import Field

from forgegraph import __version__
from forgegraph.spec.common import Model
from forgegraph.spec.parameters import NAMES, PARAMETERS
from forgegraph.spec.registry import Registry
from forgegraph.spec.tags import to_json


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


def record(level: Literal["full", "minimal"], **fields: Any) -> dict[str, Any]:
    """The provenance record saved files carry, at a level: ForgeGraph's version, when it
    was made, and the fields given, as plain values."""
    made = ProvenanceRecord(
        provenance_level=level,
        forgegraph_version=__version__,
        created=created(),
        **fields,
    )
    return plain(made.model_dump(exclude_none=True))


def graph_fields(
    spec: dict[str, Any], values: dict[str, dict[str, Any]], data: DataRecord, full: bool
) -> dict[str, Any]:
    """What a graph's or a tile's record says about it: its GraphSpec as recorded and, in a
    full record, every value it was drawn with and its data's file and preprocessing."""
    return {
        "graphspec": recorded(spec, full),
        "resolved": plain(values) if full else None,
        "data": data.file if full else None,
        "preprocessing": data.preprocessing if full else None,
    }


def plain(value: Any) -> Any:
    """Values as plain Python, as JSON writes them: NumPy scalars as Python numbers, and dates
    (YAML's, in a spec) as ISO 8601 text, inside dicts and lists too."""
    if isinstance(value, dict):
        return {k: plain(v) for k, v in value.items()}
    if isinstance(value, list):
        return [plain(v) for v in value]
    if hasattr(value, "item"):
        value = value.item()
    return value.isoformat() if isinstance(value, date) else value


def recorded(spec: dict[str, Any], full: bool) -> dict[str, Any]:
    """A GraphSpec as provenance records it, its tags in their JSON form (see tags.py): below
    full, without the data's file and preprocessing reference."""
    spec = copy.deepcopy(spec)
    listed = spec.get(PARAMETERS)
    if not full and isinstance(listed, dict) and isinstance(listed.get("data"), dict):
        listed["data"].pop("file", None)
        listed["data"].pop("preprocessing", None)
        if not listed["data"]:
            del listed["data"]
    return to_json(spec)


def used(values: dict[str, dict[str, Any]], reg: Registry) -> dict[str, Any]:
    """Each spec a graph is drawn with, by kind, as its name and version (and its pack's)."""
    chosen = values["graphspec"]
    out: dict[str, Any] = {}
    for kind in NAMES["graphspec"]:
        out[kind] = reg.spec_record(kind, chosen[f"specifications.{kind}"])
    layers = values.get("layers") or {}
    if layers:
        out["layers"] = {
            n: {"type": v["type"], "version": reg.docs["layer"][v["type"]]["version"]}
            for n, v in layers.items()
        }
    return out
