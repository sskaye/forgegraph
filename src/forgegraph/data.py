"""A GraphSpec's data: where its Parquet file is, and the DataFrame it's drawn from."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pandas as pd

from forgegraph.drawn import SpecError
from forgegraph.spec.loaded import Loaded
from forgegraph.spec.parameters import is_none
from forgegraph.spec.provenance import DataRecord


def data_path(graphspec: Loaded) -> Path | None:
    """Where the Parquet file a GraphSpec's data.file names is, or None if it names none: a
    relative path is found from the folder of the GraphSpec file that sets it (see
    Loaded.place)."""
    return graphspec.place("data.file")


def read_data(
    graphspec: Loaded, values: dict[str, dict[str, Any]], data: pd.DataFrame | None
) -> tuple[pd.DataFrame, DataRecord]:
    """The DataFrame to draw: the one given, or the one in the Parquet file data.file names."""
    preprocessing = values["graphspec"]["data.preprocessing"]
    reference = None if is_none(preprocessing) else str(preprocessing)
    if data is not None:
        return data, DataRecord(preprocessing=reference, rows_read=len(data))
    where = data_path(graphspec)
    if where is None:
        raise SpecError(["data.file: None, so pass the data as a DataFrame"])
    if not where.is_file():
        raise SpecError([f"data.file: no file at '{where}'"])
    try:
        frame = pd.read_parquet(where)
    except Exception as e:  # pyarrow raises several kinds for a file that isn't Parquet
        problem = f"data.file: '{where}' isn't a Parquet file ({type(e).__name__})"
        raise SpecError([problem]) from None
    file = str(values["graphspec"]["data.file"])
    return frame, DataRecord(file=file, preprocessing=reference, rows_read=len(frame))
