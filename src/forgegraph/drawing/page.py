"""HTML pages: a graph, or a layout's tabs, as SVG in a minimal page (architecture D11).

Each figure is an SVG image, with its text as outlines (matplotlib's default svg.fonttype), so
it looks the same in every browser; it's shown at its own size and shrinks, without
reflowing, to fit a narrower window. The SVG carries its provenance record, as every SVG file
does, and the page carries the record of everything on it in its head, as JSON.

A layout with several tabs gets a tab bar, which is part of the page, not of any figure, as
wide as the figures, in the layout's tab_bar look (TabBar): its names in tab_bar.label's
font, which the page embeds, size, weight, color, gap and alignment, the selected one
underlined in that color, and tab_bar.line under it. Tabs holding tabs get a tab bar for
each level, the one under each tab showing the tabs in it. The page's style switches the
tabs, so they work where its scripts don't run: each name labels a hidden choice, one for
each name at each level, and the style shows the tab the choices pick (_tab_choices). A
choice is shared by the tabs of its name in every group, so choosing a tab that holds tabs
shows the tabs below it last chosen, where it has them, and the same chart can be compared
across groups; otherwise it shows its first. Where the scripts run, each name is
also a link (#overview, or the whole path, #platinum/voltage), so a tab can be linked to,
opened in a new window and returned to with Back. In a browser too old for the style (from
before 2023), there's no tab bar, and every tab shows, one after another under its name.

The tab bars stay at the top of the window while the page scrolls, over the figures and their
readouts, and switching tabs leaves the page where it is, so the same tile stays in view: the
choices are fixed to the window, so that choosing one doesn't scroll to it, and the script
handles a click on a link in place of the browser, which would scroll to the tab. A link
opened from elsewhere does scroll to its tab, which stops below the tab bars.
When the layout draws a border, the line under the tab bars is the border's top: each figure
is cropped to its border, without the border's own top side.

A scheduled run's page carries its data's time and how old the data may get (Freshness). A
short script compares them with the viewer's clock and shows a banner at the top when the
data is older: a job that stopped can't look current. It works where the page's scripts run;
the "data as of" footnote in each figure is what always shows.

A graph with choice layers (spec/views.py) has an image for each view, and the page shows a
control for each choice layer, above the figures and under the tab bars: a dropdown, or a
row of radio buttons, after the layer's label, in the tab bar's font (a graph's theme's
general text). The page's style shows the image of the views chosen, so the controls work
where its scripts don't run; a control a tab doesn't use is hidden while it's showing. In a
browser too old for the style, there are no controls, and each figure shows its first view.

A graph with a toggle layer (spec/toggles.py) is a stack of images (drawing/toggles.py), and
the page shows a checkbox for each item, with the controls; the style hides an image when
one of its items' boxes is unchecked, and the readouts of a hidden series' points. A
layout's items of the same name share one checkbox.

Each figure's data points have readouts (drawing/readout.py): pointing at a point, or tapping
it, shows its values in a box above it, with a ring around the point. The page carries each
figure's points beside its image, as JSON, with a script that finds the point under the
pointer and the font the readouts are written in. Where the page's scripts don't run, there
are no readouts.
"""

from __future__ import annotations

import base64
import html
import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from forgegraph.drawing.readout import Look, Mark
from forgegraph.drawing.toggles import Slice

SCRIPT_ID = "forgegraph"
STALE_ID = "forgegraph-stale"
READOUTS = "forgegraph-readouts"  # each figure's points, beside its image


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
class TabBar:
    """A page's tab bar: its names' font (family, size in points, weight number, color, the
    gap around each in points, and their alignment), the font's file, and the line under it
    (matplotlib's line style, "none" for none; its width in points; its color)."""

    family: str
    size: float
    weight: int
    color: str
    gap: float
    alignment: str
    font: Path
    line: str
    line_width: float
    line_color: str


CSS_LINES = {"-": "solid", "--": "dashed", ":": "dotted", "none": "none"}
JUSTIFY = {"left": "flex-start", "center": "center", "right": "flex-end"}


@dataclass(frozen=True)
class Shown:
    """One figure on a page: its tab's name and link (None for a graph or a one-tab layout),
    its SVG, and its tab's path, the names of the tabs it's in and its own."""

    name: str | None
    slug: str | None  # its link: platinum/voltage
    svg: bytes
    path: tuple[str, ...] = ()
    marks: tuple[Mark, ...] = ()  # its data points, for their readouts
    views: tuple[Viewed, ...] = ()  # with choice layers, every view's image, the first first
    slices: tuple[Slice, ...] = ()  # with toggles, its images to stack (drawing/toggles.py)
    boxes: tuple[KeyBox, ...] = ()  # with toggles, the checkboxes in its keys


@dataclass(frozen=True)
class Viewed:
    """One view's image of a figure: the view chosen at each control it uses, as (the
    control's name, the view's name), its SVG and its data points."""

    choices: tuple[tuple[str, str], ...]
    svg: bytes
    marks: tuple[Mark, ...] = ()
    slices: tuple[Slice, ...] = ()  # with toggles, its images to stack
    boxes: tuple[KeyBox, ...] = ()  # with toggles, the checkboxes in its keys


@dataclass(frozen=True)
class Text:
    """A control's text on a page: its font (family, size in points, weight number, color),
    the gap between its label and the rest in points, its alignment, and the font's file."""

    family: str
    size: float
    weight: int
    color: str
    gap: float
    alignment: str
    font: Path


@dataclass(frozen=True)
class Toggle:
    """A toggle's checkbox on a page: its item's name, whether it's hidden at first, and
    whether its checkboxes are in the figures' keys (KeyBox) rather than in the list."""

    name: str
    hidden: bool = False
    in_key: bool = False


@dataclass(frozen=True)
class Toggles:
    """A page's toggle checkboxes: each item's, the text before the list, where the list is
    (top, bottom or right), and its text."""

    items: tuple[Toggle, ...]
    label: str | None = None
    position: str = "right"
    text: Text | None = None


@dataclass(frozen=True)
class KeyBox:
    """A checkbox in a figure's key, for a toggle item: its centre and side, in points from
    the figure's top left."""

    item: str
    x: float
    y: float
    side: float


@dataclass(frozen=True)
class Control:
    """A control on a page: a choice layer's name, the text before it, dropdown or radio,
    and its views' names."""

    name: str
    label: str | None
    kind: str
    views: tuple[str, ...]
    position: str = "right"  # top, bottom or right of the figures
    text: Text | None = None


_STYLE = """
html { background: %(background)s; }
body { margin: 0; padding: 16px; font: 15px/1.4 system-ui, -apple-system, "Segoe UI",
  Roboto, sans-serif; color: #333333; }
%(font_face)s
main { max-width: %(main)s; }
.figures { max-width: %(width)s; flex: 1 1 auto; min-width: 0; }
.body.right { display: flex; align-items: flex-start; gap: 24px; }
@media (max-width: 640px) { .body.right { flex-direction: column; } }
img { display: block; width: 100%%; height: auto; }
.tabbars { display: none; margin-bottom: %(under)s; position: sticky; top: 0; z-index: 2;
  background: %(background)s; }
.tabs { position: relative; }
.tabs > input { position: fixed; top: 0; left: 0; margin: 0; opacity: 0;
  pointer-events: none; }
nav { display: flex; flex-wrap: wrap; justify-content: %(justify)s;
  border-bottom: %(rule_width)s %(rule_style)s %(rule)s; }
nav a, nav label, h2 { font-family: %(family)s; font-size: %(size)s;
  font-weight: %(weight)s; color: %(color)s; }
nav a, nav label { padding: %(gap)s; text-decoration: none; cursor: pointer;
  border-bottom: 3px solid transparent; margin-bottom: -%(rule_width)s; }
#forgegraph-stale { margin-bottom: 12px; padding: 8px 12px; background: #FFF4CE;
  border: 1px solid #E0B000; color: #4A3B00; }
section + section { margin-top: 24px; }
h2 { margin: 0 0 %(under)s; padding-bottom: %(gap)s;
  border-bottom: %(rule_width)s %(rule_style)s %(rule)s; }
.controls { display: none; flex-wrap: wrap; align-items: center; gap: 0.6em 1.5em;
  margin-bottom: 12px; }
.tabbars .controls { margin: 0.6em 0 0; }
.controls.bottom { margin: 12px 0 0; }
.controls.right { flex: 0 0 auto; flex-direction: column; align-items: stretch; gap: 1.2em;
  margin: 0; }
.control { display: flex; align-items: center; gap: var(--gap); }
.controls.right .control { flex-direction: column; align-items: var(--align); }
.options { display: flex; flex-wrap: wrap; align-items: center; gap: 0.25em 0.9em; }
.controls.right .options { flex-direction: column; align-items: var(--align); }
.control select { font: inherit; color: inherit; }
.control label { cursor: pointer; }
.control input { margin: 0 0.35em 0 0; accent-color: currentColor; }
.toggle { display: inline-flex; align-items: center; cursor: pointer; }
.toggle input { width: 0.9em; height: 0.9em; accent-color: currentColor; }
.kept input { position: absolute; width: 1px; height: 1px; margin: 0; opacity: 0;
  pointer-events: none; }
.boxed { position: relative; }
.keybox { position: absolute; aspect-ratio: 1; transform: translate(-50%%, -50%%);
  box-sizing: border-box; border: 1px solid var(--on); border-radius: 15%%;
  background: #FFFFFF; cursor: pointer; }
.stack { position: relative; }
.slice { position: absolute; top: 0; left: 0; pointer-events: none; }
.slice[data-hidden] { display: none; }
.view { display: none; }
.view[data-first] { display: block; }
@supports selector(:has(a)) {
  .tabbars { display: block; }
  .controls { display: flex; }
  main .view[data-first] { display: none; }
  main .slice[data-hidden] { display: block; }
  .tabbars nav:not([data-under=""]) { display: none; }
  .tabs section { display: none; margin-top: 0; }
  .tabs h2 { display: none; }
}
"""

# choices is a function of its arguments alone, so it can be tested: the choices a link sets,
# from each tab's id and choices. A link to a tab holding tabs sets only its own, so the
# style shows the tab below it last chosen, or its first.
_CHOICES = """
function choices(tabs, target) {
  var i, depth = target.split("/").length;
  for (i = 0; i < tabs.length; i++) if (tabs[i][0] === target) return tabs[i][1];
  for (i = 0; i < tabs.length; i++) {
    if (tabs[i][0].indexOf(target + "/") === 0) return tabs[i][1].slice(0, depth);
  }
  return tabs[0][1];
}
"""

_SCRIPT = (
    _CHOICES
    + """
(function () {
  var sections = document.querySelectorAll(".tabs section");
  if (!sections.length) return;
  var tabs = Array.prototype.map.call(sections, function (s) {
    return [s.id, s.getAttribute("data-choices").split(" ")];
  });
  document.querySelectorAll(".tabs > input").forEach(function (input) {
    input.tabIndex = -1;
    input.setAttribute("aria-hidden", "true");
  });
  document.querySelectorAll(".tabbars nav").forEach(function (nav) {
    nav.setAttribute("role", "tablist");
  });
  var links = Array.prototype.map.call(document.querySelectorAll(".tabbars nav label"),
    function (label) {
      var a = document.createElement("a"), to = label.getAttribute("data-path");
      a.href = "#" + to;
      a.setAttribute("role", "tab");
      a.setAttribute("data-path", to);
      a.textContent = label.textContent;
      label.parentNode.replaceChild(a, label);
      a.addEventListener("click", function (event) {
        if (event.button || event.ctrlKey || event.metaKey || event.shiftKey) return;
        event.preventDefault();
        if (location.hash !== "#" + to) history.pushState(null, "", "#" + to);
        show();
      });
      return a;
    });
  var bars = document.querySelector(".tabbars");
  function showing() {
    for (var i = 0; i < sections.length; i++) {
      if (getComputedStyle(sections[i]).display !== "none") return sections[i].id;
    }
    return tabs[0][0];
  }
  function show() {
    var target = decodeURIComponent(location.hash.slice(1));
    choices(tabs, target).forEach(function (c) { document.getElementById(c).checked = true; });
    var below = bars.offsetHeight + parseFloat(getComputedStyle(bars).marginBottom) + "px";
    sections.forEach(function (s) { s.style.scrollMarginTop = below; });
    var id = showing();
    if (target && target !== id) history.replaceState(null, "", "#" + id);
    links.forEach(function (a) {
      var to = a.getAttribute("data-path");
      a.setAttribute("aria-selected", id === to || id.indexOf(to + "/") === 0 ? "true" : "false");
    });
  }
  window.addEventListener("hashchange", show);
  show();
})();
"""
)


_READOUT_STYLE = """
.figure { position: relative; }
.forgegraph-readout { position: absolute; z-index: 1; pointer-events: none; white-space: nowrap;
  border: 1px solid; border-radius: 3px; padding: 6px 9px; line-height: 1.3;
  box-shadow: 0 1px 4px rgba(0, 0, 0, 0.18); }
.forgegraph-readout .name { opacity: 0.65; }
.forgegraph-ring { position: absolute; z-index: 1; pointer-events: none; border: 2px solid;
  border-radius: 50%; box-sizing: border-box; }
"""

# index and hit are functions of their arguments alone, so they can be tested. A point is
# found within 3 px of its marker, or 6 px of a line's point without one; the nearest wins,
# and a point beats the bar it sits on.
_HIT = """
function index(marks) {
  var cells = {}, boxes = [], reach = 0;
  marks.forEach(function (m, i) {
    if (m[3]) { boxes.push(i); return; }
    var key = Math.floor(m[0] * 64) + "," + Math.floor(m[1] * 64);
    (cells[key] = cells[key] || []).push(i);
    reach = Math.max(reach, m[2]);
  });
  return {cells: cells, boxes: boxes, reach: reach};
}
function hit(marks, found, x, y, width, height, on) {
  var best = -1, nearest = Infinity, reach = found.reach * width + 6;
  var across = Math.ceil(reach / width * 64), down = Math.ceil(reach / height * 64);
  var cx = Math.floor(x * 64), cy = Math.floor(y * 64), i, j, k, cell;
  for (i = cx - across; i <= cx + across; i++) {
    for (j = cy - down; j <= cy + down; j++) {
      cell = found.cells[i + "," + j] || [];
      for (k = 0; k < cell.length; k++) {
        var m = marks[cell[k]], dx = (m[0] - x) * width, dy = (m[1] - y) * height;
        if (on && !on(m)) continue;
        var d = Math.sqrt(dx * dx + dy * dy);
        if (d <= (m[2] > 0 ? m[2] * width + 3 : 6) && d < nearest) {
          best = cell[k];
          nearest = d;
        }
      }
    }
  }
  if (best >= 0) return best;
  for (k = 0; k < found.boxes.length; k++) {
    if (on && !on(marks[found.boxes[k]])) continue;
    var box = marks[found.boxes[k]][3];
    if (x >= box[0] && x <= box[2] && y >= box[1] && y <= box[3]) return found.boxes[k];
  }
  return -1;
}
"""

_READOUT_SCRIPT = (
    _HIT
    + """
(function () {
  document.querySelectorAll("script.%(class)s").forEach(function (source) {
    var figure = source.parentNode, image = figure.querySelector("img"), data = null, found;
    var tip = document.createElement("div"), ring = document.createElement("div");
    tip.className = "forgegraph-readout";
    ring.className = "forgegraph-ring";
    tip.hidden = ring.hidden = true;
    figure.appendChild(ring);
    figure.appendChild(tip);
    function hide() { tip.hidden = ring.hidden = true; }
    function shown(m) {  // a point of a series switched off has no readout
      return !(m.length > 7 && m[7] >= 0 && !document.getElementById("toggle" + m[7]).checked);
    }
    function show(event) {
      if (data === null) {
        data = JSON.parse(source.textContent);
        found = index(data.marks);
      }
      var shape = image.getBoundingClientRect(), width = shape.width, height = shape.height;
      var k = hit(data.marks, found, (event.clientX - shape.left) / width,
        (event.clientY - shape.top) / height, width, height, shown);
      if (k < 0) { hide(); return; }
      var m = data.marks[k], look = data.looks[m[5]], x = m[0] * width, y = m[1] * height;
      tip.textContent = "";
      m[6].forEach(function (line) {
        var row = document.createElement("div"), value = document.createElement("span");
        if (line[0] >= 0) {
          var name = document.createElement("span");
          name.className = "name";
          name.innerHTML = data.names[line[0]] + ":";
          row.appendChild(name);
          row.appendChild(document.createTextNode(" "));
        }
        value.innerHTML = line[1];
        row.appendChild(value);
        tip.appendChild(row);
      });
      tip.style.fontFamily = JSON.stringify(look.family);
      tip.style.fontWeight = look.weight;
      tip.style.fontSize = look.size * width + "px";
      tip.style.color = look.color;
      tip.style.background = look.background;
      tip.style.borderColor = look.border;
      var above = y, below = y;
      if (m[3]) {
        ring.hidden = true;
        above = m[3][1] * height;
        below = m[3][3] * height;
      } else {
        var radius = m[2] * width + 3;
        ring.style.width = ring.style.height = 2 * radius + "px";
        ring.style.left = x - radius + "px";
        ring.style.top = y - radius + "px";
        ring.style.borderColor = data.rings[m[4]];
        ring.hidden = false;
        above = y - radius;
        below = y + radius;
      }
      tip.hidden = false;
      var w = tip.offsetWidth, h = tip.offsetHeight;
      var top = above - 8 - h >= 0 ? above - 8 - h : Math.min(below + 8, height - h);
      tip.style.left = Math.max(0, Math.min(x - w / 2, width - w)) + "px";
      tip.style.top = Math.max(0, top) + "px";
    }
    image.addEventListener("pointermove", show);
    image.addEventListener("pointerdown", show);
    image.addEventListener("pointerleave", function (event) {
      if (event.pointerType === "mouse") hide();
    });
    document.addEventListener("pointerdown", function (event) {
      if (event.target !== image) hide();
    });
  });
})();
"""
)


_NO_BAR = {  # a page without a tab bar sets none of its look
    "font_face": "",
    "justify": "flex-start",
    "rule": "transparent",
    "rule_width": "0pt",
    "rule_style": "none",
    "family": "inherit",
    "size": "inherit",
    "weight": "inherit",
    "color": "inherit",
    "gap": "0",
}


def _bar_look(bar: TabBar) -> dict[str, str]:
    """The page style's values for a tab bar, with its font embedded."""
    data = base64.b64encode(bar.font.read_bytes()).decode("ascii")
    kind = "opentype" if bar.font.suffix.lower() == ".otf" else "truetype"
    family = json.dumps(bar.family)  # a CSS string: quoted, with quotes escaped
    face = (
        f"@font-face {{ font-family: {family}; font-weight: {bar.weight}; "
        f'src: url("data:font/{"otf" if kind == "opentype" else "ttf"};base64,{data}") '
        f'format("{kind}"); }}'
    )
    return {
        "font_face": face,
        "justify": JUSTIFY[bar.alignment],
        "rule": bar.line_color if bar.line_width > 0 else "transparent",
        "rule_width": f"{bar.line_width:g}pt",
        "rule_style": CSS_LINES[bar.line],
        "family": family,
        "size": f"{bar.size:g}pt",
        "weight": str(bar.weight),
        "color": bar.color,
        "gap": f"{bar.gap:g}pt",
    }


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
    bar: TabBar | None = None,
    framed: bool = False,
    freshness: Freshness | None = None,
    controls: tuple[Control, ...] = (),
    toggles: Toggles | None = None,
) -> Path:
    """Write the page. background: behind the figures; bar: the tab bar's look, for several
    tabs; framed: the figures are cropped to their border, so the tab bar's line is its top;
    freshness: a scheduled run's, for the stale banner; controls: the choice layers'
    controls, for figures with views; toggles: the toggle layers' checkboxes, for figures in
    slices."""
    tabbed = len(shown) > 1
    if tabbed and bar is None:
        raise ValueError("a page of several tabs needs its tab bar's look")
    items = toggles.items if toggles is not None else ()
    width = max(size(v.svg)[0] for s in shown for v in _figures(s))
    right = _controls(controls, toggles, "right")
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
        "width": f"{width:g}pt",
        "main": "none" if right else f"{width:g}pt",
        "under": "0" if framed else "12px",
    }
    look.update(_bar_look(bar) if bar is not None else _NO_BAR)
    parts.append(f"<style>{_STYLE % look}</style>")
    readouts = [[_readouts(v, items) for v in _figures(s)] for s in shown]
    faces: dict[tuple[str, int], Path] = {}
    if any(any(r) for r in readouts):
        for s in shown:
            for v in _figures(s):
                faces.update({(m.look.family, m.look.weight): m.look.font for m in v.marks})
    texts = [c.text for c in controls] + [toggles.text if toggles is not None else None]
    faces.update({(t.family, t.weight): t.font for t in texts if t is not None})
    if bar is not None:
        faces.pop((bar.family, bar.weight), None)  # the tab bar's face is already there
    if faces:
        parts.append(f"<style>{''.join(_font_face(*k, f) for k, f in faces.items())}</style>")
    if any(any(r) for r in readouts):
        parts.append(f"<style>{_READOUT_STYLE}</style>")
    choices, rules = _tab_choices(shown, look["color"], controls, items) if tabbed else ([], "")
    if tabbed:
        parts.append(f"<style>{rules}</style>")
    if controls:
        parts.append(f"<style>{_view_rules(shown, controls)}</style>")
    if items:
        on = toggles.text.color if toggles is not None and toggles.text else "#333333"
        parts.append(f"<style>{_toggle_rules(items, on)}</style>")
    parts += ["</head>", "<body>", '<main class="tabs">' if tabbed else "<main>", *choices]
    kept = [
        f'<input type="checkbox" id="toggle{i}"{"" if t.hidden else " checked"} '
        f'aria-label="{html.escape(t.name)}">'
        for i, t in enumerate(items)
        if t.in_key
    ]
    if kept:  # the checkboxes the keys' boxes stand for
        parts.append(f'<div class="kept">{"".join(kept)}</div>')
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
        bars = [*_tab_bars(shown), *_controls(controls, toggles, "top")]
        parts += ['<div class="tabbars">', *bars, "</div>"]
    else:
        parts += _controls(controls, toggles, "top")
    parts.append('<div class="body right">' if right else '<div class="body">')
    parts.append('<div class="figures">')
    for s, found in zip(shown, readouts, strict=True):
        alt = html.escape(f"{title}: {s.name}" if tabbed else title)
        heading = f"<h2>{html.escape(str(s.name))}</h2>" if tabbed else ""
        where = f' id="{s.slug}"' if s.slug else ""
        if tabbed:
            where += f' data-choices="{" ".join(_choices(s.path))}"'
        figures = []
        for i, (v, data) in enumerate(zip(_figures(s), found, strict=True)):
            image = base64.b64encode(v.svg).decode("ascii")
            name = alt
            if s.views:
                name += html.escape(" (" + ", ".join(n for _, n in s.views[i].choices) + ")")
            figure = f'<img alt="{name}" src="data:image/svg+xml;base64,{image}">'
            if v.slices:
                figure = _stack(v.slices, name, items)
            figure += _key_boxes(v.svg, v.boxes, items)
            if data is not None:
                figure = (
                    f"{figure}<script "
                    f'type="application/json" class="{READOUTS}">{_json(data)}</script>'
                )
            classes = ["figure"] if data is not None else []
            classes += ["stack"] if v.slices else []
            classes += ["boxed"] if v.boxes else []
            attributes = ""
            if s.views:
                classes.append("view")
                attributes = f' data-view="{_view_key(s.views[i], controls)}"'
                attributes += " data-first" if i == 0 else ""
            if classes:
                figure = f'<div class="{" ".join(classes)}"{attributes}>{figure}</div>'
            figures.append(figure)
        parts.append(f"<section{where}>{heading}{''.join(figures)}</section>")
    parts += ["</div>", *right, "</div>", *_controls(controls, toggles, "bottom"), "</main>"]
    if tabbed:
        parts.append(f"<script>{_SCRIPT}</script>")
    if any(any(r) for r in readouts):
        parts.append(f"<script>{_READOUT_SCRIPT % {'class': READOUTS}}</script>")
    parts += ["</body>", "</html>", ""]
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(parts), encoding="utf-8")
    return path


def _figures(s: Shown) -> tuple[Shown | Viewed, ...]:
    """A figure's images: each view's, or its one."""
    return s.views or (s,)


def _control_id(controls: tuple[Control, ...], name: str) -> str:
    return f"view{[c.name for c in controls].index(name)}"


def _view_key(v: Viewed, controls: tuple[Control, ...]) -> str:
    """A view's image's key: each control's and view's number, as 0-1 2-0."""
    by_name = {c.name: (i, c) for i, c in enumerate(controls)}
    return " ".join(f"{by_name[c][0]}-{by_name[c][1].views.index(n)}" for c, n in v.choices)


def _controls(controls: tuple[Control, ...], toggles: Toggles | None, position: str) -> list[str]:
    """The controls at a position (top, bottom or right): each a dropdown, or radio buttons,
    after or under its label; then the toggles' checkboxes not in a key."""
    here = [(i, c) for i, c in enumerate(controls) if c.position == position]
    listed = []
    if toggles is not None and toggles.position == position:
        listed = [(i, t) for i, t in enumerate(toggles.items) if not t.in_key]
    if not here and not listed:
        return []
    out = [f'<div class="controls {position}">']
    for i, c in here:
        cid = f"view{i}"
        label = html.escape(c.label) if c.label else ""
        style = _text_style(c.text)
        if c.kind == "radio":
            named = f' aria-label="{label}"' if label else ""
            out.append(f'<span class="control" data-control="{i}"{style} role="radiogroup"{named}>')
            if label:
                out.append(f"<span>{label}</span>")
            out.append('<span class="options">')
            for j, v in enumerate(c.views):
                checked = " checked" if j == 0 else ""
                out.append(
                    f'<label><input type="radio" name="{cid}" id="{cid}-{j}" value="{j}"'
                    f"{checked}>{html.escape(v)}</label>"
                )
            out.append("</span>")
        else:
            out.append(f'<span class="control" data-control="{i}"{style}>')
            if label:
                out.append(f'<label for="{cid}">{label}</label>')
            out.append(f'<select id="{cid}">')
            out += [f'<option value="{j}">{html.escape(v)}</option>' for j, v in enumerate(c.views)]
            out.append("</select>")
        out.append("</span>")
    if listed and toggles is not None:
        label = html.escape(toggles.label) if toggles.label else ""
        named = f' aria-label="{label}"' if label else ""
        style = _text_style(toggles.text)
        out.append(f'<span class="control toggles"{style} role="group"{named}>')
        if label:
            out.append(f"<span>{label}</span>")
        out.append('<span class="options">')
        for i, t in listed:
            checked = "" if t.hidden else " checked"
            out.append(
                f'<label class="toggle" data-toggle="{i}"><input type="checkbox" '
                f'id="toggle{i}"{checked}>{html.escape(t.name)}</label>'
            )
        out.append("</span></span>")
    out.append("</div>")
    return out


def _text_style(text: Text | None) -> str:
    """A control's text as an inline style: its font, its gap and its alignment."""
    if text is None:
        return ' style="--gap: 0.5em; --align: flex-start"'
    align = {"left": "flex-start", "center": "center", "right": "flex-end"}[text.alignment]
    return (
        f' style="font-family: {html.escape(json.dumps(text.family))}; '
        f"font-size: {text.size:g}pt; font-weight: {text.weight}; color: {text.color}; "
        f'--gap: {text.gap:g}pt; --align: {align}"'
    )


def _font_face(family: str, weight: int, font: Path) -> str:
    """An @font-face embedding a font."""
    data = base64.b64encode(font.read_bytes()).decode("ascii")
    kind = "opentype" if font.suffix.lower() == ".otf" else "truetype"
    return (
        f"@font-face {{ font-family: {json.dumps(family)}; font-weight: {weight}; "
        f'src: url("data:font/{"otf" if kind == "opentype" else "ttf"};base64,{data}") '
        f'format("{kind}"); }}'
    )


def _key_boxes(svg: bytes, boxes: tuple[KeyBox, ...], items: tuple[Toggle, ...]) -> str:
    """The checkboxes in a figure's keys: each a label for its item's checkbox, placed by
    its share of the image as shown (its SVG's view box)."""
    left, top, width, height = view_box(svg) if boxes else (0.0, 0.0, 1.0, 1.0)
    number = {t.name: i for i, t in enumerate(items)}
    out = []
    for b in boxes:
        if b.item not in number:
            continue
        x, y, side = (b.x - left) / width * 100, (b.y - top) / height * 100, b.side / width * 100
        out.append(
            f'<label class="keybox" for="toggle{number[b.item]}" title="{html.escape(b.item)}" '
            f'style="left: {x:.3f}%; top: {y:.3f}%; width: {side:.3f}%"></label>'
        )
    return "".join(out)


def _chosen(controls: tuple[Control, ...], name: str, view: str) -> str:
    """The selector that holds when a control has a view chosen."""
    i = [c.name for c in controls].index(name)
    j = controls[i].views.index(view)
    if controls[i].kind == "radio":
        return f":has(#view{i}-{j}:checked)"
    return f':has(#view{i} option[value="{j}"]:checked)'


def _view_rules(shown: list[Shown], controls: tuple[Control, ...]) -> str:
    """The rules that show each figure's image of the views chosen."""
    rules = {}
    for s in shown:
        for v in s.views:
            key = _view_key(v, controls)
            picked = "".join(_chosen(controls, c, n) for c, n in v.choices)
            rules[key] = f'  main{picked} .view[data-view="{key}"] {{ display: block; }}'
    return "\n".join(["@supports selector(:has(a)) {", *rules.values(), "}"])


def _stack(slices: tuple[Slice, ...], alt: str, toggles: tuple[Toggle, ...]) -> str:
    """A figure's images, stacked: the first sets its size, and each later one lies over it,
    marked with its items' numbers, and as hidden if one of them is at first."""
    number = {t.name: i for i, t in enumerate(toggles)}
    hidden = {t.name for t in toggles if t.hidden}
    out = []
    for i, part in enumerate(slices):
        image = base64.b64encode(part.svg).decode("ascii")
        if i == 0:
            out.append(f'<img alt="{alt}" src="data:image/svg+xml;base64,{image}">')
            continue
        items = " ".join(str(number[n]) for n in sorted(part.items, key=number.__getitem__))
        marks = f' data-items="{items}"' if items else ""
        marks += " data-hidden" if part.items & hidden else ""
        out.append(f'<img class="slice" alt=""{marks} src="data:image/svg+xml;base64,{image}">')
    return "".join(out)


def _toggle_rules(toggles: tuple[Toggle, ...], on: str) -> str:
    """The rules that hide each image whose items include one switched off, and that tick a
    key's checkbox for an item switched on, in on, the toggles' text color."""
    rules = [f"  .keybox {{ --on: {on}; }}"]
    for i in range(len(toggles)):
        rules += [
            f'  main:has(#toggle{i}:not(:checked)) .slice[data-items~="{i}"] {{ display: none; }}',
            f'  main:has(#toggle{i}:checked) .keybox[for="toggle{i}"] {{ background: {on}; }}',
            f'  main:has(#toggle{i}:checked) .keybox[for="toggle{i}"]::after {{ content: ""; '
            "position: absolute; left: 33%; top: 12%; width: 26%; height: 52%; "
            "border: solid #FFFFFF; border-width: 0 2px 2px 0; transform: rotate(45deg); }",
            f'  main:has(#toggle{i}:focus-visible) .keybox[for="toggle{i}"] '
            f"{{ outline: 2px solid {on}; outline-offset: 1px; }}",
        ]
    return "\n".join(["@supports selector(:has(a)) {", *rules, "}"])


def _readouts(s: Shown | Viewed, toggles: tuple[Toggle, ...] = ()) -> dict[str, Any] | None:
    """A figure's points for the page's script, in fractions of its image as shown (its SVG's
    view box): each [x, y, the marker's radius as a fraction of the width, the bar's box
    (left, top, right, bottom) or null, its ring's color, its look, and its lines, each
    [its name's index or -1 for none, its value]], with the tables they index: the looks,
    sizes as fractions of the width, and the names and rings."""
    if not s.marks:
        return None
    left, top, width, height = view_box(s.svg)
    looks: dict[Look, int] = {}
    names: dict[str, int] = {}
    rings: dict[str, int] = {}
    marks = []
    for m in s.marks:
        x, y = (m.x - left) / width, (m.y - top) / height
        if not (0 <= x <= 1 and 0 <= y <= 1):  # cut off with the border (layouts._framed)
            continue
        box = None
        if m.box is not None:
            a, b, c, d = m.box
            box = [_f((a - left) / width), _f((b - top) / height)]
            box += [_f((c - left) / width), _f((d - top) / height)]
        lines = [[names.setdefault(n, len(names)) if n else -1, v] for n, v in m.lines]
        ring = rings.setdefault(m.ring, len(rings))
        look = looks.setdefault(m.look, len(looks))
        mark = [_f(x), _f(y), _f(m.radius / width), box, ring, look, lines]
        if toggles:  # the number of its item's toggle, or -1
            mark.append(next((i for i, t in enumerate(toggles) if t.name == m.item), -1))
        marks.append(mark)
    return {
        "looks": [
            {
                "family": k.family,
                "weight": k.weight,
                "size": _f(k.size / width),
                "color": k.color,
                "background": k.background,
                "border": k.border,
            }
            for k in looks
        ],
        "names": list(names),
        "rings": list(rings),
        "marks": marks,
    }


def _f(v: float) -> float:
    return round(float(v), 4)


def view_box(svg: bytes) -> tuple[float, float, float, float]:
    """An SVG's view box: its left, top, width and height, in points."""
    m = re.search(rb'<svg[^>]*?viewBox="([^"]*)"', svg)
    assert m is not None
    left, top, width, height = (float(v) for v in m[1].split())
    return left, top, width, height


def _face(look: Look) -> str:
    """An @font-face embedding a readout look's font."""
    data = base64.b64encode(look.font.read_bytes()).decode("ascii")
    kind = "opentype" if look.font.suffix.lower() == ".otf" else "truetype"
    return (
        f"@font-face {{ font-family: {json.dumps(look.family)}; font-weight: {look.weight}; "
        f'src: url("data:font/{"otf" if kind == "opentype" else "ttf"};base64,{data}") '
        f'format("{kind}"); }}'
    )


def _choice(path: tuple[str, ...]) -> str:
    """The id of the hidden choice that picks a tab: one per name at each level, shared by the
    tabs of that name in every group, so choosing a group keeps the tabs below it."""
    from forgegraph.spec.layout import slug

    return f"tab{len(path)}-{slug(path[-1])}"


def _choices(path: tuple[str, ...]) -> list[str]:
    """The choices that show a tab: its own and those of the tabs it's in."""
    return [_choice(path[: d + 1]) for d in range(len(path))]


def _children(shown: list[Shown]) -> dict[tuple[str, ...], list[tuple[str, ...]]]:
    """Each tab holding tabs (the top level is ()), and its tabs' paths, in order."""
    out: dict[tuple[str, ...], list[tuple[str, ...]]] = {}
    for s in shown:
        for depth in range(len(s.path)):
            tabs = out.setdefault(s.path[:depth], [])
            if s.path[: depth + 1] not in tabs:
                tabs.append(s.path[: depth + 1])
    return out


def _tab_choices(
    shown: list[Shown],
    color: str,
    controls: tuple[Control, ...] = (),
    toggles: tuple[Toggle, ...] = (),
) -> tuple[list[str], str]:
    """The hidden choices, the first tab's checked, and the rules that show what they pick:
    at each level, the tab of the chosen name, or the group's first when it has none. The
    rules show that tab, the tab bar of the tabs in it, the line under its name, the
    controls its views use, and an outline around a name whose choice the keyboard is on."""
    from forgegraph.spec.layout import slug

    children = _children(shown)
    first = set(_choices(shown[0].path))
    choices: dict[str, int] = {}  # each choice, and its level
    for tabs in children.values():
        for path in tabs:
            choices.setdefault(_choice(path), len(path))
    inputs = [
        f'<input type="radio" name="tab{level}" id="{c}"' + (" checked>" if c in first else ">")
        for c, level in choices.items()
    ]

    def picked(path: tuple[str, ...]) -> str:
        """The selector that holds when path is the tab showing at its level and above."""
        out = ""
        for depth in range(1, len(path) + 1):
            tabs = children[path[: depth - 1]]
            if path[:depth] == tabs[0]:  # the first: unless another in its group is chosen
                others = ", ".join(f"#{_choice(p)}:checked" for p in tabs[1:])
                out += f":not(:has({others}))" if others else ""
            else:
                out += f":has(#{_choice(path[:depth])}:checked)"
        return out

    def link(path: tuple[str, ...]) -> str:
        return "/".join(slug(n) for n in path)  # a style's text isn't HTML: no escapes

    rules = [f'  .tabs{picked(s.path)} section[id="{s.slug}"] {{ display: block; }}' for s in shown]
    for under, tabs in children.items():
        if under:
            rules.append(
                f'  .tabs{picked(under)} nav[data-under="{link(under)}"] {{ display: flex; }}'
            )
        rules += [
            f'  .tabs{picked(path)} [data-path="{link(path)}"] {{ border-bottom-color: {color}; }}'
            for path in tabs
        ]
    rules += [
        f'  #{c}:focus-visible ~ .tabbars label[for="{c}"] {{ outline: 2px solid {color}; }}'
        for c in choices
    ]
    if controls:
        rules.append("  .controls .control[data-control] { display: none; }")
        for s in shown:
            used = sorted({_control_id(controls, c) for v in s.views for c, _ in v.choices})
            rules += [
                f'  .tabs{picked(s.path)} .control[data-control="{u.removeprefix("view")}"] '
                "{ display: flex; }"
                for u in used
            ]
    if toggles:
        number = {t.name: i for i, t in enumerate(toggles)}
        rules.append("  .controls .toggle { display: none; }")
        for s in shown:
            parts = [*s.slices, *(p for v in s.views for p in v.slices)]
            used = sorted({number[n] for p in parts for n in p.items})
            rules += [
                f'  .tabs{picked(s.path)} .toggle[data-toggle="{i}"] {{ display: inline-flex; }}'
                for i in used
            ]
    return inputs, "\n".join(["@supports selector(:has(a)) {", *rules, "}"])


def _tab_bars(shown: list[Shown]) -> list[str]:
    """A tab bar for each tab holding tabs, and one for the top level: each lists the tabs in
    it, each name choosing its tab. data-under: the path of the tab whose tabs it lists."""
    from forgegraph.spec.layout import slug

    out = []
    for under, tabs in _children(shown).items():
        link = "/".join(slug(n) for n in under)
        out.append(f'<nav data-under="{html.escape(link)}">')
        out += [
            f'<label for="{_choice(path)}" '
            f'data-path="{html.escape("/".join(slug(n) for n in path))}">'
            f"{html.escape(path[-1])}</label>"
            for path in tabs
        ]
        out.append("</nav>")
    return out


def read(path: Path) -> dict[str, Any] | None:
    """The provenance record in a page's head, or None if it has none."""
    m = re.search(
        rf'<script type="application/json" id="{SCRIPT_ID}">(.*?)</script>',
        path.read_text(encoding="utf-8"),
        re.S,
    )
    return json.loads(m.group(1)) if m else None
