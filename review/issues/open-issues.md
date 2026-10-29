# Open issues, 2026-10-28

The 19 issues open on GitHub, checked on 0.4.0, and five bugs found while reproducing them. Each says who filed it: two came from another user, and the rest from your agent while rebuilding existing graphs, most of them a 29-chart, five-tab health dashboard.

## Summary

Closed on GitHub: #17 to #26, #31, #37, #38, #42, #45, #46, #48, #49, #50 and #52 (built or found working), and #39 and #57 (not planned).

Decided in the review but still open on GitHub: #30 (built in sskaye/forgegraph#58: labels and notes now grow the axis for room), and #27, #28, #41 and #53 (declined).

Filed by another user, waiting for your decision:
- **Requests:** #67, #68.

Filed by your agent, waiting for your decision:
- **Bugs:** #29, #44, #56, and the five found while checking (at the end).
- **Not reproducible:** #34.
- **Partly possible with existing settings:** #32, #33, #35, #40.
- **Missing:** #43.
- **Declined or deferred:** #36, #47, #51.

## #29: value labels on stacked bars: a minimum size, and per-segment ink

- **Filed by:** sskaye (your agent, while rebuilding the qs_tracker health dashboard).
- **Issue:** stacked bars with small segments fail ("'2' and '8' run together"). Zero-height segments draw a stray "0", and small segments' labels spill out of their bars.
- **Root cause:** stacked segments are labelled at their centre with no fit test, then any overlap raises an error. Single bars do get the fit test.
- **Verification:** reproduced. The ink part of the report is already done: each segment's label takes the ink that contrasts more with that segment.
- **Proposal:** use the existing fit test for segments. With auto, a segment's label is written only where it fits; with inside, a segment too small is an error naming it. No new parameter. About 15 lines.

## #32: tick formats for durations, clock times and units

- **Filed by:** sskaye (your agent, while rebuilding the qs_tracker health dashboard).
- **Request:** labels like "1.2 U/h", "6 am", "1h 27m".
- **Verification:** partly possible. Percents, a 12-hour clock (`%I %p`) and literal text in date formats work today. Literal text in number formats, unpadded hours (%-I), lowercase am/pm and durations don't. A duration column silently becomes categories.
- **Proposal:**
  1. A number format may be a one-field template, "{:.1f} U/h".
  2. ForgeGraph writes %-I and lowercase am/pm itself.
  3. Defer durations, which need their own data type. Until then, a duration column is an error saying to convert it to minutes or hours.

  Recommendation: all three. About 35 lines.

## #33: plot aspect per format or per tile, and sizing per tab

- **Filed by:** sskaye (your agent, while rebuilding the qs_tracker health dashboard).
- **Request:** half-width tiles as tall as full-width ones, and a format per tab.
- **Verification:** partly possible. A tile's theme can set a smaller `plot_area.aspect_ratio`; verified, though the heights only roughly match. With an auto height, a tab's rows already size themselves.
- **Proposal:** no change to the format or tiles: aspect belongs to the theme, and layouts have no per-tile settings. Document the half-width theme route. Recommendation: docs only.

## #34: reference lines inside the axis margin

- **Filed by:** sskaye (your agent, while rebuilding the qs_tracker health dashboard).
- **Issue:** a reference line appears to sit on the plot's edge.
- **Root cause:** none. The margin already includes reference lines; on a short tile, the 5 % margin is only a few points.
- **Verification:** not reproducible on 0.3.0 or 0.4.0. The gap above the line equals the gap below the data.
- **Proposal:** no change. Point to a reference layer's `line_1.label.position: end_above`, which grows the axis to fit the label above the line. Separately, replace a hard-coded 0.05 in layers.py with the theme's plot_area.gap.

## #35: text tiles in a layout: KPIs, captions, footnotes

- **Filed by:** sskaye (your agent, while rebuilding the qs_tracker health dashboard).
- **Request:** text-only tiles (KPIs), captions under titles, footnotes for a layout.
- **Verification:** partly possible. Notes outside the plot give per-chart captions and footnotes; a caption at the top needs #44's fix. KPI tiles and layout text are deferred by design (architecture §11, D11).
- **Proposal:** fix #44 and use an outside top note as the caption. Keep text tiles deferred, and decline layout footnotes; a note on a tab's last tile serves. Recommendation: that, with no new parameter.

## #36: interactive HTML: tooltips, and a selector over filters

- **Filed by:** sskaye (your agent, while rebuilding the qs_tracker health dashboard).
- **Request:** hover tooltips, and a picker that switches the data window.
- **Verification:** missing, and deliberately out of the MVP (architecture D1). One tab per window works for small cases.
- **Proposal:**
  1. Tooltips only, as a format switch for html (about 150 lines).
  2. A filter selector: many renders or a JavaScript renderer, near the data-prep line.

  Recommendation: defer both; if you want one now, tooltips. Decline the selector for the MVP.


## #40: variable fonts, including the macOS system font

- **Filed by:** sskaye (your agent, while rebuilding the qs_tracker health dashboard).
- **Request:** use the macOS system font (SF) at semibold and bold.
- **Verification:** partly possible. matplotlib can't choose a variable font's weight, so the system font registers only at regular. Static instances made with fontTools, in a pack's fonts folder, work; verified.
- **Proposal:** make the missing-weight error explain this for variable fonts, and give the one-line fontTools command in the skill's notes. Mention that Apple's licence restricts embedding SF. Recommendation: that. Defer making instances automatically; decline a per-machine system font, which breaks reproducibility.

## #43: a horizontal key

- **Filed by:** sskaye (your agent, while rebuilding the qs_tracker health dashboard).
- **Request:** a key laid out in a row above or below the plot.
- **Verification:** missing. A key is always one entry per row.
- **Proposal:**
  1. Keys outside at the top or bottom lay out in a row, wrapping as needed, as in Vega-Lite and ggplot.
  2. A theme setting for direction.

  Recommendation: 1. It changes no existing test or catalog card. About 60 lines.
- **Spec:** the key's gap.column, the gap between columns of entries × base size, beside gap.row in the theme's specification.

## #44: an outside note goes above the title

- **Filed by:** sskaye (your agent, while rebuilding the qs_tracker health dashboard).
- **Issue:** a note outside the plot at the top is drawn above the title, while a key there goes between the title and the plot.
- **Root cause:** top notes are anchored on the title, and only keys make the title move up.
- **Verification:** reproduced on 0.3.0 and 0.4.0.
- **Proposal:** anchor top notes on the plot box, and make room for them as for keys, so the order is title, note, key, plot. About 20 lines.


## #47: `extends` by path

- **Filed by:** sskaye (your agent, while rebuilding the qs_tracker health dashboard).
- **Request:** extend a GraphSpec by its file path, not a pack name.
- **Verification:** missing, by design: named specs come only from packs (architecture §5). A folder pack is the designed route.
- **Verification:** still missing on 0.4.0: `extends: ./b.yaml` is read as a spec in a pack named ".".
- **Proposal:** decline. The motivating case, a variant that only changes theme, was #39, which is closed as not planned. Revisit if asked again.


## #51: rounded bar corners

- **Filed by:** sskaye (your agent, while rebuilding the qs_tracker health dashboard).
- **Request:** bars with rounded corners.
- **Verification:** missing.
- **Proposal:** a theme corner radius for bars, about 30 lines. Recommendation: defer, as a low-value look setting, until asked again.

## #56: a title without descenders sits lower than its neighbors in a layout

- **Filed by:** sskaye (your agent, while making a summary of a 200 cm² cell test).
- **Issue:** in a layout row, "Polarization" sits lower than "Voltage" and "Typology", although the plots line up. A title is placed by the bottom of its ink, not by its baseline, so a title without g, j, p, q or y drops by the depth of the descenders. A single graph's height also changes with its title's letters.
- **Verification:** reproduced on 0.4.0 with the issue's three tiles. The tops of "Voltage" and "Typology" are at 37–38 px and the top of "Polarization" at 67 px, while their bottoms are within 2 px of each other.
- **Proposal:** none yet.

## #67: nested tabs in a layout

- **Filed by:** CoryONeill.
- **Request:** two levels of tabs in a layout: a tab per group (an electrode material) holding a tab per chart (a metric). Switching groups keeps the same metric showing, and a link can open a given pair of tabs.
- **Verification:** missing. A tab holds a grid of tiles, and can't hold tabs.
- **Proposal:** none yet.

## #68: separate tick label sizes for the x and y axes

- **Filed by:** CoryONeill.
- **Request:** different tick label sizes on x and y, so that 28 category labels fit along x while the y-axis numbers match the graphs beside it. The same for weight and color.
- **Verification:** missing. The tick labels are one text style, `axis.tick.label`, for both axes.
- **Proposal:** none yet.

## Found while checking

### Categorical tick labels can vanish on a narrow plot

- **Issue:** with 3 categories on a narrow plot, ticks can land between the categories, leaving every label blank.
- **Root cause:** the tick algorithm's whole-number rule checks the step but not the first tick.
- **Verification:** reproduced.
- **Proposal:** also require the first tick to be whole. A few lines.

### A duration column silently becomes categories

- **Issue:** a pandas duration column is drawn as categories labelled "0 days 06:40:00".
- **Root cause:** the axis type check has no case for durations.
- **Verification:** reproduced.
- **Proposal:** an error saying to convert durations to a number of minutes or hours, with #32.

### One row on a date axis gets a six-year axis

- **Issue:** a single-row date series gets an x axis from 2023 to 2029.
- **Root cause:** the margin of a zero range.
- **Verification:** reproduced.
- **Proposal:** with one distinct date, the axis spans one calendar unit either side of it. About 10 lines.

### Date tick labels on a y axis can collide

- **Issue:** on a date y axis whose range crosses midnight, the date's second line (e.g. "Jan 1, 2000") runs into the next tick label, and the render fails with labels running together.
- **Root cause:** a date axis writes the next unit up on a second line under a tick where it changes. That fits under x labels, but on y the second line sits where the next label goes.
- **Verification:** found while fixing #19, on the small test format, from midnight to 22:00.
- **Proposal:** on y, write the date on the same line as the time where it changes ("Jan 1 00:00"), instead of on a second line. No new parameter. Recommendation: do it, test first.

### The HTML page's own text is always dark grey

- **Issue:** a layout's HTML page draws its tab bar and text in dark grey whatever the theme, so with a dark background the tab bar is unreadable.
- **Root cause:** the page's colors are hard-coded in drawing/page.py.
- **Verification:** found while checking #39; still so on 0.4.0.
- **Proposal:** take the page's colors from the theme. No new parameter.
