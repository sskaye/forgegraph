"""Saving figures with their provenance record, and reading it back (architecture D13).

The record is one JSON document, stored invisibly in each file type:

- png: a text chunk with key "ForgeGraph";
- svg: the Dublin Core description in the SVG metadata;
- pdf: the document information dictionary, key /ForgeGraph;
- jpg: a JPEG comment segment;
- tiff: the ImageDescription tag;
- html: a JSON script in the page's head (render/page.py), with each figure's SVG carrying
  its own record too.

A layout's PDF has a page per tab, and the document's record covers them all.

With SOURCE_DATE_EPOCH set, PNG, SVG and PDF output is byte-identical between runs.
"""

from __future__ import annotations

import html
import io
import json
import re
import warnings
from collections.abc import Sequence
from pathlib import Path
from typing import Any, cast

import matplotlib
from matplotlib.backends.backend_pdf import PdfPages
from matplotlib.figure import Figure
from PIL import Image

from forgegraph.render import page

KEY = "ForgeGraph"
FILE_TYPES = ("png", "jpg", "tiff", "svg", "pdf", "html")
IMAGES = ("png", "jpg", "tiff", "svg", "pdf")  # what matplotlib saves
ALIASES = {"jpeg": "jpg", "tif": "tiff"}


def kind_of(target: Any, format: str | None = None) -> str:
    """The file type matplotlib will save: format if given, else the file name's suffix,
    else savefig.format (as matplotlib decides it)."""
    if format is None:
        suffix = Path(target).suffix.lstrip(".") if isinstance(target, str | Path) else ""
        format = suffix or str(matplotlib.rcParams["savefig.format"])
    kind = format.lower()
    return ALIASES.get(kind, kind)


def with_record(kind: str, kwargs: dict[str, Any], record: dict[str, Any] | None) -> dict[str, Any]:
    """savefig's keyword arguments with the record added in the file type's carrier. A caller
    that sets the carrier's own key (to None, say) keeps it; file types without a carrier
    (eps, webp...) are saved without a record."""
    if record is None:
        return kwargs
    blob = json.dumps(record, sort_keys=True)  # ASCII: safe in every carrier
    out = dict(kwargs)
    if kind in ("png", "svg", "pdf"):
        metadata = dict(out.get("metadata") or {})
        key = "Description" if kind == "svg" else KEY
        if key not in metadata:
            metadata[key] = blob
            if kind == "pdf":
                metadata.setdefault("Subject", "ForgeGraph provenance")
        out["metadata"] = metadata
    elif kind in ("jpg", "tiff"):
        pil = dict(out.get("pil_kwargs") or {})
        if kind == "jpg":
            pil.setdefault("comment", blob.encode())
        else:
            pil.setdefault("tiffinfo", {270: blob})
        out["pil_kwargs"] = pil
    return out


def save(fig: Figure, path: Path, dpi: int) -> Path:
    """Save fig to path (its suffix is the file type). A ForgeGraph figure's canvas adds the
    provenance record (forgegraph.render.figure.GraphCanvas)."""
    kind = kind_of(path)
    if kind not in IMAGES:
        raise ValueError(f"can't save as .{kind}; file types are {', '.join(FILE_TYPES)}")
    path.parent.mkdir(parents=True, exist_ok=True)
    pil = {"jpg": {"quality": 95}, "tiff": {"compression": "tiff_lzw"}}.get(kind)
    fig.savefig(path, format=kind, dpi=dpi, **({"pil_kwargs": pil} if pil else {}))
    return path


def svg(fig: Figure, dpi: int) -> bytes:
    """The figure as SVG, with its provenance record."""
    buffer = io.BytesIO()
    fig.savefig(buffer, format="svg", dpi=dpi)
    return buffer.getvalue()


def save_pages(figs: Sequence[Figure], path: Path, dpi: int, record: dict[str, Any] | None) -> Path:
    """Save figures as the pages of one PDF, whose document record is `record`."""
    path.parent.mkdir(parents=True, exist_ok=True)
    metadata = {"Subject": "ForgeGraph provenance", KEY: json.dumps(record, sort_keys=True)}
    with warnings.catch_warnings():
        warnings.filterwarnings("ignore", message="Unknown infodict keyword")
        with PdfPages(path, metadata=metadata if record is not None else None) as pdf:
            for fig in figs:
                fig.savefig(cast(Any, pdf), format="pdf", dpi=dpi)  # PdfPages: a page
    return path


def read(path: Path) -> dict[str, Any] | None:
    """The provenance record stored in a file, or None if it has none."""
    kind = kind_of(path)
    if kind == "html":
        return page.read(path)
    if kind in ("png", "jpg", "tiff"):
        with Image.open(path) as image:
            if kind == "png":
                blob = image.info.get(KEY) or getattr(image, "text", {}).get(KEY)
            elif kind == "jpg":
                raw = image.info.get("comment")
                blob = raw.decode() if isinstance(raw, bytes) and raw else None
            else:
                blob = image.tag_v2.get(270)  # type: ignore[attr-defined]
        return json.loads(blob) if blob else None
    data = path.read_bytes()
    if kind == "svg":
        m = re.search(rb"<dc:description>(.*?)</dc:description>", data, re.S)
        return json.loads(html.unescape(m.group(1).decode())) if m else None
    if kind == "pdf":
        m = re.search(rb"/ForgeGraph \((.*?)\)\s*(?:/|>>)", data, re.S)
        if not m:
            return None
        raw = re.sub(rb"\\([()\\])", rb"\1", m.group(1))
        return json.loads(raw.decode("latin-1"))
    raise ValueError(f"can't read .{kind}; file types are {', '.join(FILE_TYPES)}")
