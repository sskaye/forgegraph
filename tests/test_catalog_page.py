"""The catalog page: the committed pages' contents, categories opened where a comment is,
and the pinned Forgemark tool."""

from __future__ import annotations

import hashlib
import io
import re
from pathlib import Path

import pytest

import forgegraph
from forgegraph import forgemark
from forgegraph.catalog_build.page import Card, Instance, Kind, Row, figures, open_commented, page

CATALOG = Path(__file__).parents[1] / "catalog" / "forgegraph_base.html"


def test_a_packs_table_shows_its_own_values():
    """A row shows the value the shown spec draws with, and whether it fixes it, not the
    definition's: the forgegraph_base_2 theme's, not the base theme's."""
    text = (CATALOG.parent / "forgegraph_base_2.html").read_text(encoding="utf-8")

    def cells(row: str) -> list[str]:
        start = text.index(f'<tr id="{row}">')
        row_text = text[start : text.index("</tr>", start)]
        found = re.findall(r"<td[^>]*>(.*?)</td>", row_text)
        return [re.sub(r"<[^>]+>", "", c) for c in found[1:]]  # after the parameter's name

    theme = "theme-forgegraph_base_2-base_theme-param-"
    assert cells(theme + "title-size")[0] == "1.45"
    assert cells(theme + "series-marker-edge_color")[0] == "#000000"
    assert cells("format-forgegraph_base_2-compact_format-param-output-dpi")[0] == "200"


def test_a_packs_catalog_shows_graph_and_layer_types_in_its_theme():
    text = (CATALOG.parent / "forgegraph_base_2.html").read_text(encoding="utf-8")
    panels = set(re.findall(r'<section class="panel" id="([^"]+)"', text))
    assert {"graphtype-xy", "layer-error_bar", "layer-note", "layer-reference_line"} <= panels
    assert f'<p id="version" class="version">version {forgegraph.__version__}</p>' in text


def test_figures_gives_each_cards_image_by_its_figures_id():
    row = Row("grid.show", "false", "true | false", "variable", "Draw a grid.")
    cards = (Card("t-baseline", "Baseline", b"one", 100), Card("t-card", "Card", b"two", 90))
    text = page([Kind("theme", "Themes", (Instance("t", "t", "Theme > t", (row,), cards),))], "0")
    assert figures(text) == {"t-baseline-figure": b"one", "t-card-figure": b"two"}


def test_commented_categories_are_open():
    page_ = (
        '<details class="category" id="a"><summary>a</summary>'
        '<details class="category" id="a-b"><summary>a.b</summary><!-- fmc:1 -->x<!-- /fmc:1 -->'
        '</details></details><details class="category" id="c"></details>'
    )
    opened = open_commented(page_)
    assert opened.count(" open") == 2 and 'category" open id="c"' not in opened
    assert open_commented(opened) == opened


def test_forgemark_is_downloaded_once_and_refused_if_its_checksum_differs(tmp_path, monkeypatch):
    served = []

    def urlopen(url, timeout):
        served.append(url)
        return io.BytesIO(body)

    monkeypatch.setattr(forgemark, "CACHE", tmp_path)
    monkeypatch.setattr(forgemark.urllib.request, "urlopen", urlopen)
    body = b"not the pinned tool"
    with pytest.raises(forgemark.ForgemarkError, match=r"checksum mismatch.*not running it"):
        forgemark.tool()
    assert not list(tmp_path.iterdir())  # nothing kept
    monkeypatch.setattr(forgemark, "SHA256", hashlib.sha256(body).hexdigest())
    path = forgemark.tool()
    assert path.read_bytes() == body and forgemark.tool() == path
    assert served == [forgemark.URL, forgemark.URL]  # the second good call used the cache
