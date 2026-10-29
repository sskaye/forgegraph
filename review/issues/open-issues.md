# Open issues

<!-- fmc:2 -->Last updated: 10/28/26<!-- /fmc:2 -->

## <!-- fmc:4 -->[#29](https://github.com/sskaye/forgegraph/issues/29)<!-- /fmc:4 -->: value labels on stacked bars: a minimum size, and per-segment ink

- **Filed by:** sskaye.
- **<!-- fmc:5 -->Summary<!-- /fmc:5 -->:** stacked bars with small segments fail ("'2' and '8' run together"). Zero-height segments draw a stray "0", and small segments' labels spill out of their bars.
- **Root cause:** stacked segments are labelled at their centre with no fit test, then any overlap raises an error. Single bars do get the fit test.
- **Verification:** reproduced. The ink part of the report is already done: each segment's label takes the ink that contrasts more with that segment.
- **Proposal:** use the existing fit test for segments. With auto, a segment's label is written only where it fits; with inside, a segment too small is an error naming it. No new parameter. About 15 lines.

## [#32](https://github.com/sskaye/forgegraph/issues/32): tick formats for durations, clock times and units

- **Filed by:** sskaye.
- **Summary:** labels like "1.2 U/h", "6 am", "1h 27m".
- **Verification:** partly possible. Percents, a 12-hour clock (`%I %p`) and literal text in date formats work today. Literal text in number formats, unpadded hours (%-I), lowercase am/pm and durations don't. A duration column silently becomes categories.
- **Proposal:**
  1. A number format may be a one-field template, "{:.1f} U/h".
  2. ForgeGraph writes %-I and lowercase am/pm itself.
  3. Defer durations, which need their own data type. Until then, a duration column is an error saying to convert it to minutes or hours.

  Recommendation: all three. About 35 lines.

## [#33](https://github.com/sskaye/forgegraph/issues/33): plot aspect per format or per tile, and sizing per tab

- **Filed by:** sskaye.
- **Summary:** half-width tiles as tall as full-width ones, and a format per tab.
- **Verification:** partly possible. A tile's theme can set a smaller `plot_area.aspect_ratio`; verified, though the heights only roughly match. With an auto height, a tab's rows already size themselves.
- **Proposal:** no change to the format or tiles: aspect belongs to the theme, and layouts have no per-tile settings. Document the half-width theme route. Recommendation: docs only.

## [#34](https://github.com/sskaye/forgegraph/issues/34): reference lines inside the axis margin

- **Filed by:** sskaye.
- **Summary:** a reference line appears to sit on the plot's edge.
- **Root cause:** none. The margin already includes reference lines; on a short tile, the 5 % margin is only a few points.
- **Verification:** not reproducible on 0.3.0 or 0.4.0. The gap above the line equals the gap below the data.
- **Proposal:** no change. Point to a reference layer's `line_1.label.position: end_above`, which grows the axis to fit the label above the line. Separately, replace a hard-coded 0.05 in layers.py with the theme's plot_area.gap.

## [#35](https://github.com/sskaye/forgegraph/issues/35): text tiles in a layout: KPIs, captions, footnotes

- **Filed by:** sskaye.
- **Summary:** text-only tiles (KPIs), captions under titles, footnotes for a layout.
- **Verification:** partly possible. Notes outside the plot give per-chart captions and footnotes; a caption at the top needs #44's fix. KPI tiles and layout text are deferred by design (architecture §11, D11).
- **Proposal:** fix #44 and use an outside top note as the caption. Keep text tiles deferred, and decline layout footnotes; a note on a tab's last tile serves. Recommendation: that, with no new parameter.

## [#36](https://github.com/sskaye/forgegraph/issues/36): interactive HTML: tooltips, and a selector over filters

- **Filed by:** sskaye.
- **Summary:** hover tooltips, and a picker that switches the data window.
- **Verification:** missing, and deliberately out of the MVP (architecture D1). One tab per window works for small cases.
- **Proposal:**
  1. Tooltips only, as a format switch for html (about 150 lines).
  2. A filter selector: many renders or a JavaScript renderer, near the data-prep line.

  Recommendation: defer both; if you want one now, tooltips. Decline the selector for the MVP.

## [#40](https://github.com/sskaye/forgegraph/issues/40): variable fonts, including the macOS system font

- **Filed by:** sskaye.
- **Summary:** use the macOS system font (SF) at semibold and bold.
- **Verification:** partly possible. matplotlib can't choose a variable font's weight, so the system font registers only at regular. Static instances made with fontTools, in a pack's fonts folder, work; verified.
- **Proposal:** make the missing-weight error explain this for variable fonts, and give the one-line fontTools command in the skill's notes. Mention that Apple's licence restricts embedding SF. Recommendation: that. Defer making instances automatically; decline a per-machine system font, which breaks reproducibility.

## [#43](https://github.com/sskaye/forgegraph/issues/43): a horizontal key

- **Filed by:** sskaye.
- **Summary:** a key laid out in a row above or below the plot.
- **Verification:** missing. A key is always one entry per row.
- **Proposal:**
  1. Keys outside at the top or bottom lay out in a row, wrapping as needed, as in Vega-Lite and ggplot.
  2. A theme setting for direction.

  Recommendation: 1. It changes no existing test or catalog card. About 60 lines.
- **Spec:** the key's gap.column, the gap between columns of entries × base size, beside gap.row in the theme's specification.

## [#44](https://github.com/sskaye/forgegraph/issues/44): an outside note goes above the title

- **Filed by:** sskaye.
- **Summary:** a note outside the plot at the top is drawn above the title, while a key there goes between the title and the plot.
- **Root cause:** top notes are anchored on the title, and only keys make the title move up.
- **Verification:** reproduced on 0.3.0 and 0.4.0.
- **Proposal:** anchor top notes on the plot box, and make room for them as for keys, so the order is title, note, key, plot. About 20 lines.

## [#47](https://github.com/sskaye/forgegraph/issues/47): `extends` by path

- **Filed by:** sskaye.
- **Summary:** extend a GraphSpec by its file path, not a pack name.
- <!-- fmc:6 -->**Verification:** missing on 0.4.0, by design: named specs come only from packs (architecture §5), so `extends: ./b.yaml` is read as a spec in a pack named ".". A folder pack is the designed route.<!-- /fmc:6 -->
- **Proposal:** decline. The motivating case, a variant that only changes theme, was #39, which is closed as not planned. Revisit if asked again.

## <!-- fmc:8 -->[#56](https://github.com/sskaye/forgegraph/issues/56)<!-- /fmc:8 -->: a title without descenders sits lower than its neighbors in a layout

- **Filed by:** sskaye.
- **Summary:** in a layout row, "Polarization" sits lower than "Voltage" and "Typology", although the plots line up. A title is placed by the bottom of its ink, not by its baseline, so a title without g, j, p, q or y drops by the depth of the descenders. A single graph's height also changes with its title's letters.
- **Root cause:** the title is placed so that title.gap separates the plot box from the title's lowest letter (`_title_pad` in drawing/spacing.py). In a title with descenders, the lowest letter is below the baseline, so the baseline sits higher by the depth of the descenders. The room above the plot box is measured to the letters too, so a single graph's height changes with its title. A y-axis title reading upward on the left is spaced the same way, from its lowest letter to the tick labels, and has the same fault.
- **Verification:** reproduced on 0.4.0 with the issue's three tiles. The tops of "Voltage" and "Typology" are at 37–38 px and the top of "Polarization" at 67 px, while their bottoms are within 2 px of each other.
- <!-- fmc:9 -->**Proposal:** measure title.gap to the title's baseline instead of its lowest letter, so descenders hang into the gap. Titles in a layout row then share a baseline, and a graph's height no longer depends on its title's letters. Do the same for a y-axis title reading upward on the left. No new parameter.<!-- /fmc:9 -->

## [#67](https://github.com/sskaye/forgegraph/issues/67): nested tabs in a layout

- **Filed by:** CoryONeill.
- **Summary:** two levels of tabs in a layout: a tab per group (an electrode material) holding a tab per chart (a metric). Switching groups keeps the same metric showing, and a link can open a given pair of tabs.
- **Verification:** missing. A tab holds a grid of tiles, and can't hold tabs.
- <!-- fmc:10 -->**Proposal:**
  1. A tab may hold `tabs` in place of `grid` and `tiles`, one level deep. The HTML page draws a second tab bar under the first. Switching the top tab keeps the second tab of the same name if there is one, and a link such as `#platinum/voltage` opens that pair, as a link opens a tab today. Image and PDF files are named by both tabs, such as `results-platinum-voltage.png`.
  2. No new structure: a tab named "Platinum / Voltage" makes the HTML page draw two tab bars. This needs no spec change, but it's a hidden naming rule.

  Recommendation: 1, with two levels only and no option for keeping the second tab, since keeping it is what the request asks for.<!-- /fmc:10 -->

## [#68](https://github.com/sskaye/forgegraph/issues/68): separate tick label sizes for the x and y axes

- **Filed by:** CoryONeill.
- **Summary:** different tick label sizes on x and y, so that 28 category labels fit along x while the y-axis numbers match the graphs beside it. The same for weight and color.
- **Verification:** missing. The tick labels are one text style, `axis.tick.label`, for both axes.
- <!-- fmc:11 -->**Proposal:**
  1. The theme keeps `axis.tick.label` for both axes and adds `axis.x.tick.label` and `axis.y.tick.label`, each `[text style, look from axis.tick.label]`. Each takes every parameter it doesn't set from `axis.tick.label`, and is fixed or variable as `axis.tick.label` is, by the rule for general style parameters. A GraphSpec sets `axis.x.tick.label.size: 1.2` beside `axis.x.tick.label.format`.
  2. Replace `axis.tick.label` with `axis.x.tick.label` and `axis.y.tick.label`. This needs no new rule, but every theme sets both, and a GraphSpec changing both axes sets both.

  Recommendation: 1. It covers size, weight and color, as the request asks, and existing themes and GraphSpecs keep working.<!-- /fmc:11 -->

## Found while checking

### The HTML page's tab bar is always dark grey

- **Summary:** a layout's HTML page draws its tab names in dark grey and in the browser's font, whatever the theme, so with a dark background the tab bar is unreadable.
- **Root cause:** the page's colors are hard-coded in drawing/page.py.
- **Verification:** found while checking #39; still so on 0.4.0.
- <!-- fmc:16 -->**Proposal:** the layout gets a text style for its tab names, beside `separators`:

  ```yaml
  tab_label:          # [text style]; The tab names in the HTML page's tab bar. Its defaults are the first tile's theme's text.
  ```

  The selected tab's underline and the line under the tab bar take its color. The page embeds the style's font, since a browser shows a typeface only if the viewer has it or the page carries it.<!-- /fmc:16 -->

<!-- forgemark-comments
- id: 1
  floating: true
  author: Steven
  timestamp: "2026-10-29T02:53:35.249Z"
  resolved: false
  body: "Remove all of this. This is meant to be an open issues list with proposed changes for me to review and comment on. The summary doesn’t add anything."
  replies:
    - author: Claude
      timestamp: 2026-10-29T03:08:45Z
      body: |
        Removed the introduction and the summary. The page now starts with the first open issue.
- id: 2
  anchor_text: ", 2026-10-28"
  context_before: "# Open issues"
  context_after: "The 14 issues open on GitHub, checked on 0.4.0, and five bugs found while reprod"
  author: Steven
  timestamp: "2026-10-29T02:54:01.537Z"
  edited_at: "2026-10-29T02:54:11.863Z"
  resolved: false
  body: "Move this to the next line, and reword: “Last updated: MM/DD/YY” in regular font."
  replies:
    - author: Claude
      timestamp: 2026-10-29T03:08:46Z
      body: |
        Moved to its own line under the heading, in regular text: "Last updated: 10/28/26".
- id: 3
  floating: true
  author: Steven
  timestamp: "2026-10-29T02:55:17.445Z"
  resolved: false
  body: "Simplify. Just “Filed by: sskaye” rest just makes it harder to read and requires more inference on your part, risking error."
  replies:
    - author: Claude
      timestamp: 2026-10-29T03:08:46Z
      body: |
        Every issue now says only "Filed by: sskaye." or "Filed by: CoryONeill."
- id: 4
  anchor_text: "#29"
  context_before: "Missing: #43. Declined or deferred: #36, #47, #51."
  context_after: ": value labels on stacked bars: a minimum size, and per-segment ink Filed by: ss"
  author: Steven
  timestamp: "2026-10-29T02:56:05.456Z"
  resolved: false
  body: "Link to actual GitHub issue so I can inspect if needed."
  replies:
    - author: Claude
      timestamp: 2026-10-29T03:08:46Z
      body: |
        Every issue's heading now links to its GitHub issue.
- id: 5
  anchor_text: Issue
  context_before: "Filed by: sskaye (your agent, while rebuilding the qs_tracker health dashboard)."
  context_after: ": stacked bars with small segments fail (\"'2' and '8' run together\")."
  author: Steven
  timestamp: "2026-10-29T02:56:16.374Z"
  resolved: false
  body: "“Summary\""
  replies:
    - author: Claude
      timestamp: 2026-10-29T03:08:46Z
      body: |
        Renamed to "Summary" on every issue. I also renamed "Request" to "Summary", since both labels said what the issue reports; say if you want "Request" back for feature requests.
- id: 6
  anchor_text: "Verification: missing, by design: named specs come only from packs (architecture §5). A folder pack is the designed route. Verification: still missing on 0.4.0: extends: ./b.yaml is read as a spec in a pack named \".\"."
  context_before: "Request: extend a GraphSpec by its file path, not a pack name."
  context_after: "Proposal: decline."
  author: Steven
  timestamp: "2026-10-29T02:57:54.578Z"
  resolved: false
  body: "Do not repeat “Verification”. Ok to update, but should have one."
  replies:
    - author: Claude
      timestamp: 2026-10-29T03:08:46Z
      body: |
        Merged into one Verification line, checked on 0.4.0.
- id: 7
  floating: true
  author: Steven
  timestamp: "2026-10-29T02:58:12.350Z"
  resolved: false
  body: "Decline and close."
  replies:
    - author: Claude
      timestamp: 2026-10-29T03:08:46Z
      body: |
        Closed #51 on GitHub as not planned, with a comment saying it's a low-value look setting, and removed it from the page.
- id: 8
  anchor_text: "#56"
  context_before: "Recommendation: defer, as a low-value look setting, until asked again."
  context_after: ": a title without descenders sits lower than its neighbors in a layout Filed by:"
  author: Steven
  timestamp: "2026-10-29T02:58:47.738Z"
  resolved: false
  body: "Root cause is missing."
  replies:
    - author: Claude
      timestamp: 2026-10-29T03:08:46Z
      body: |
        Added the root cause. The title is placed so that title.gap separates the plot box from the title's lowest letter (_title_pad in drawing/spacing.py), so a title with descenders has its baseline raised by their depth. A y-axis title reading upward on the left is spaced the same way and has the same fault.
- id: 9
  anchor_text: "Proposal: none yet"
  context_before: "p of \"Polarization\" at 67 px, while their bottoms are within 2 px of each other."
  context_after: ". #67: nested tabs in a layout Filed by: CoryONeill."
  author: Steven
  timestamp: "2026-10-29T02:59:15.873Z"
  resolved: false
  body: "Why not?"
  replies:
    - author: Claude
      timestamp: 2026-10-29T03:08:46Z
      body: |
        I hadn't analyzed it. The proposal is now to measure title.gap to the title's baseline instead of its lowest letter, so descenders hang into the gap and titles in a row share a baseline. The same fix applies to a y-axis title reading upward. No new parameter.
- id: 10
  anchor_text: "Proposal: none yet."
  context_before: "Verification: missing. A tab holds a grid of tiles, and can't hold tabs."
  context_after: "#68: separate tick label sizes for the x and y axes Filed by: CoryONeill."
  author: Steven
  timestamp: "2026-10-29T02:59:46.057Z"
  resolved: false
  body: "Don’t just skip proposals. When you add something to this list, analyze and add your recommendation."
  replies:
    - author: Claude
      timestamp: 2026-10-29T03:08:47Z
      body: |
        Added a proposal with two options. I recommend a tab holding tabs of its own, two levels deep, with the second tab kept by name when the top tab changes and a link that opens a pair. The other option, a naming rule such as "Platinum / Voltage", needs no spec change but hides the structure in tab names.
- id: 11
  anchor_text: "Proposal: none yet."
  context_before: "The tick labels are one text style, axis.tick.label, for both axes."
  context_after: "Found while checking Categorical tick labels can vanish on a narrow plot Issue:"
  author: Steven
  timestamp: "2026-10-29T03:00:00.762Z"
  resolved: false
  body: "Don’t just skip proposals. When you add something to this list, analyze and add your recommendation."
  replies:
    - author: Claude
      timestamp: 2026-10-29T03:08:47Z
      body: |
        Added a proposal with two options. I recommend new axis.x.tick.label and axis.y.tick.label text styles that take what they don't set from axis.tick.label, as text styles take theirs from text, so existing themes and GraphSpecs keep working and a GraphSpec can set axis.x.tick.label.size. The other option, replacing axis.tick.label with the two, makes every theme set both.
- id: 12
  floating: true
  author: Steven
  timestamp: "2026-10-29T03:00:46.550Z"
  resolved: false
  body: Remove.
  replies:
    - author: Claude
      timestamp: 2026-10-29T03:08:47Z
      body: |
        Removed from the page.
- id: 13
  floating: true
  author: Steven
  timestamp: "2026-10-29T03:01:04.276Z"
  resolved: false
  body: Remove.
  replies:
    - author: Claude
      timestamp: 2026-10-29T03:08:47Z
      body: |
        Removed from the page.
- id: 14
  floating: true
  author: Steven
  timestamp: "2026-10-29T03:01:12.691Z"
  resolved: false
  body: Remove.
  replies:
    - author: Claude
      timestamp: 2026-10-29T03:08:47Z
      body: |
        Removed from the page.
- id: 15
  floating: true
  author: Steven
  timestamp: "2026-10-29T03:01:16.707Z"
  resolved: false
  body: Remove.
  replies:
    - author: Claude
      timestamp: 2026-10-29T03:08:47Z
      body: |
        Removed from the page.
- id: 16
  anchor_text: "Proposal: take the page's colors from the theme. No new parameter."
  context_before: "Verification: found while checking #39; still so on 0.4.0."
  context_after: ""
  author: Steven
  timestamp: "2026-10-29T03:04:44.008Z"
  resolved: false
  body: "If the layoutspec can create tabs, their look should be controllable. Make tabs text style so that the text params (font, color, etc.) can be modified."
  replies:
    - author: Claude
      timestamp: 2026-10-29T03:08:47Z
      body: |
        Changed the proposal: the layout gets a tab_label text style, whose defaults are the first tile's theme's text, as separators.line takes its defaults from that theme's line. The page also has to embed the style's font, since a browser shows a typeface only if the viewer has it or the page carries it. I retitled the section to say it's about the tab bar.
-->
