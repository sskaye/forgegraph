"""HTML pages: a graph, or a layout's tabs, as SVG in a minimal page (architecture D11).

Each figure is an SVG image, with its text as outlines (matplotlib's default svg.fonttype), so
it looks the same in every browser; it's shown at its own size and shrinks, without
reflowing, to fit a narrower window. The SVG carries its provenance record, as every SVG file
does, and the page carries the record of everything on it in its head, as JSON.

A layout with several tabs gets a tab bar, which is part of the page, not of any figure, in
the system's interface font, as wide as the figures. Each tab's link (#overview) opens it.
Where scripts don't run, every tab shows, one after another under its name. When the layout
draws a border, the line under the tab bar is the border's top: each figure is cropped to
its border, without the border's own top side.

A scheduled run's page carries its data's time and how old the data may get (Freshness). A
short script compares them with the viewer's clock and shows a banner at the top when the
data is older: a job that stopped can't look current. It works where the page's scripts run;
the "data as of" footnote in each figure is what always shows.
"""

from __future__ import annotations

import base64
import html
import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

SCRIPT_ID = "forgegraph"
STALE_ID = "forgegraph-stale"


@dataclass(frozen=True)
class Freshness:
    """A scheduled page's data time (ISO 8601 with its UTC offset), the age in hours after
    which it's stale, and the cadence in words."""

    as_of: str
    stale_after_hours: float
    cadence: str


# staleMessage is a function of its arguments alone, so it can be tested with any clock.
_STALE = """
function staleMessage(asOf, now, hours, cadence) {
  var age = (now - asOf) / 3600000;
  if (!(age > hours)) return null;
  var whole = age < 48 ? Math.floor(age) : Math.floor(age / 24);
  var unit = age < 48 ? (whole === 1 ? "hour" : "hours") : (whole === 1 ? "day" : "days");
  return "This page's data is " + whole + " " + unit + " old; it should update " +
    cadence + ".";
}
(function () {
  var data = JSON.parse(document.getElementById("%(id)s-data").textContent);
  var message = staleMessage(Date.parse(data.as_of), Date.now(), data.stale_after_hours,
    data.cadence);
  if (message === null) return;
  var banner = document.getElementById("%(id)s");
  banner.textContent = message;
  banner.hidden = false;
})();
"""


@dataclass(frozen=True)
class Shown:
    """One figure on a page: its tab's name and slug (None for a graph or a one-tab layout)
    and its SVG."""

    name: str | None
    slug: str | None
    svg: bytes


_STYLE = """
html { background: %(background)s; }
body { margin: 0; padding: 16px; font: 15px/1.4 system-ui, -apple-system, "Segoe UI",
  Roboto, sans-serif; color: #333333; }
main { max-width: %(width)s; }
img { display: block; width: 100%%; height: auto; }
nav { display: flex; flex-wrap: wrap; gap: 4px 20px; margin-bottom: %(under)s;
  border-bottom: %(rule_width)s solid %(rule)s; }
nav a { padding: 6px 0; color: inherit; text-decoration: none;
  border-bottom: 3px solid transparent; margin-bottom: -%(rule_width)s; }
nav a[aria-selected="true"] { border-bottom-color: #333333; font-weight: 600; }
#forgegraph-stale { margin-bottom: 12px; padding: 8px 12px; background: #FFF4CE;
  border: 1px solid #E0B000; color: #4A3B00; }
section + section { margin-top: 24px; }
h2 { font-size: 15px; font-weight: 600; margin: 0 0 %(under)s; padding-bottom: 6px;
  border-bottom: %(rule_width)s solid %(rule)s; }
.tabbed section { display: none; margin-top: 0; }
.tabbed section.shown { display: block; }
.tabbed h2 { display: none; }
"""

_SCRIPT = """
(function () {
  var sections = document.querySelectorAll("section");
  var links = document.querySelectorAll("nav a");
  if (!links.length) return;
  document.body.classList.add("tabbed");
  function show() {
    var id = decodeURIComponent(location.hash.slice(1)) || sections[0].id;
    if (!document.getElementById(id)) id = sections[0].id;
    sections.forEach(function (s) { s.classList.toggle("shown", s.id === id); });
    links.forEach(function (a) {
      a.setAttribute("aria-selected", a.getAttribute("href") === "#" + id ? "true" : "false");
    });
  }
  window.addEventListener("hashchange", show);
  show();
})();
"""


def _json(record: dict[str, Any] | None) -> str:
    """The record as JSON that can't end the script element it's in."""
    return json.dumps(record, sort_keys=True).replace("</", "<\\/")


def size(svg: bytes) -> tuple[float, float]:
    """An SVG's width and height, in points, as matplotlib writes them."""
    m = re.search(rb'<svg[^>]*?width="([\d.]+)pt" height="([\d.]+)pt"', svg)
    assert m is not None
    return float(m[1]), float(m[2])


def crop(svg: bytes, left: float, top: float, right: float, bottom: float) -> bytes:
    """An SVG cut down to the box from (left, top) to (right, bottom), in points from its top
    left: what's outside isn't shown."""
    width, height = right - left, bottom - top
    start = svg.index(b"<svg")
    end = svg.index(b">", start)
    head = svg[start:end]
    head = re.sub(rb'width="[\d.]+pt"', f'width="{width:.4f}pt"'.encode(), head, count=1)
    head = re.sub(rb'height="[\d.]+pt"', f'height="{height:.4f}pt"'.encode(), head, count=1)
    box = f'viewBox="{left:.4f} {top:.4f} {width:.4f} {height:.4f}"'.encode()
    head = re.sub(rb'viewBox="[^"]*"', box, head, count=1)
    return svg[:start] + head + svg[end:]


def write(
    path: Path,
    title: str,
    shown: list[Shown],
    record: dict[str, Any] | None,
    background: str = "#FFFFFF",
    rule: str = "#D9D9D9",
    rule_width: float = 0.75,
    framed: bool = False,
    freshness: Freshness | None = None,
) -> Path:
    """Write the page. background: behind the figures; rule and rule_width: the tab bar's
    line, in points; framed: the figures are cropped to their border, so the tab bar's line
    is its top; freshness: a scheduled run's, for the stale banner."""
    tabbed = len(shown) > 1
    width = max(size(s.svg)[0] for s in shown)
    parts = [
        "<!doctype html>",
        '<html lang="en">',
        "<head>",
        '<meta charset="utf-8">',
        '<meta name="viewport" content="width=device-width, initial-scale=1">',
        f"<title>{html.escape(title)}</title>",
        '<meta name="generator" content="ForgeGraph">',
    ]
    if record is not None:
        parts.append(f'<script type="application/json" id="{SCRIPT_ID}">{_json(record)}</script>')
    look = {
        "background": background,
        "rule": rule,
        "rule_width": f"{rule_width:g}pt",
        "width": f"{width:g}pt",
        "under": "0" if framed else "12px",
    }
    parts.append(f"<style>{_STYLE % look}</style>")
    parts += ["</head>", "<body>", "<main>"]
    if freshness is not None:
        data = json.dumps(
            {
                "as_of": freshness.as_of,
                "stale_after_hours": freshness.stale_after_hours,
                "cadence": freshness.cadence,
            }
        ).replace("</", "<\\/")
        parts.append(f'<div id="{STALE_ID}" role="alert" hidden></div>')
        parts.append(f'<script type="application/json" id="{STALE_ID}-data">{data}</script>')
        parts.append(f'<script id="{STALE_ID}-script">{_STALE % {"id": STALE_ID}}</script>')
    if tabbed:
        parts.append('<nav role="tablist">')
        parts += [f'<a role="tab" href="#{s.slug}">{html.escape(str(s.name))}</a>' for s in shown]
        parts.append("</nav>")
    for s in shown:
        image = base64.b64encode(s.svg).decode("ascii")
        alt = html.escape(f"{title}: {s.name}" if tabbed else title)
        heading = f"<h2>{html.escape(str(s.name))}</h2>" if tabbed else ""
        where = f' id="{s.slug}"' if s.slug else ""
        parts.append(
            f'<section{where}>{heading}<img alt="{alt}" src="data:image/svg+xml;base64,{image}">'
            "</section>"
        )
    parts.append("</main>")
    if tabbed:
        parts.append(f"<script>{_SCRIPT}</script>")
    parts += ["</body>", "</html>", ""]
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(parts), encoding="utf-8")
    return path


def read(path: Path) -> dict[str, Any] | None:
    """The provenance record in a page's head, or None if it has none."""
    m = re.search(
        rf'<script type="application/json" id="{SCRIPT_ID}">(.*?)</script>',
        path.read_text(encoding="utf-8"),
        re.S,
    )
    return json.loads(m.group(1)) if m else None
