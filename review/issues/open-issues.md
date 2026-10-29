# Open issues

Last updated: 10/28/26

## [#44](https://github.com/sskaye/forgegraph/issues/44): an outside note goes above the title

- **Filed by:** sskaye.
- **Summary:** a note outside the plot at the top is drawn above the title, while a key there goes between the title and the plot.
- **Root cause:** top notes are anchored on the title, and only keys make the title move up.
- **Verification:** reproduced on 0.3.0 and 0.4.0.
- **Proposal:** anchor top notes on the plot box, and make room for them as for keys, so the order is title, note, key, plot. About 20 lines.
- **Decision:** agreed.

## [#56](https://github.com/sskaye/forgegraph/issues/56): a title without descenders sits lower than its neighbors in a layout

- **Filed by:** sskaye.
- **Summary:** in a layout row, "Polarization" sits lower than "Voltage" and "Typology", although the plots line up. A title is placed by the bottom of its ink, not by its baseline, so a title without g, j, p, q or y drops by the depth of the descenders. A single graph's height also changes with its title's letters.
- **Root cause:** the title is placed so that title.gap separates the plot box from the title's lowest letter (`_title_pad` in drawing/spacing.py). In a title with descenders, the lowest letter is below the baseline, so the baseline sits higher by the depth of the descenders. The room above the plot box is measured to the letters too, so a single graph's height changes with its title. A y-axis title reading upward on the left is spaced the same way, from its lowest letter to the tick labels, and has the same fault.
- **Verification:** reproduced on 0.4.0 with the issue's three tiles. The tops of "Voltage" and "Typology" are at 37–38 px and the top of "Polarization" at 67 px, while their bottoms are within 2 px of each other.
- **Proposal:** measure title.gap to the title's baseline instead of its lowest letter, so descenders hang into the gap. Titles in a layout row then share a baseline, and a graph's height no longer depends on its title's letters. Do the same for a y-axis title reading upward on the left. No new parameter.
- **Decision:** agreed.

## [#67](https://github.com/sskaye/forgegraph/issues/67): nested tabs in a layout

- **Filed by:** CoryONeill.
- **Summary:** two levels of tabs in a layout: a tab per group (an electrode material) holding a tab per chart (a metric). Switching groups keeps the same metric showing, and a link can open a given pair of tabs.
- **Verification:** missing. A tab holds a grid of tiles, and can't hold tabs.
- **Proposal:**
  1. A tab may hold `tabs` in place of `grid` and `tiles`, nested as deep as the layout needs. The HTML page draws a tab bar for each level. Switching a tab keeps the tab of the same name below it if there is one, and a link such as `#platinum/voltage` opens that path, as a link opens a tab today. Image and PDF files are named by every tab on the path, such as `results-platinum-voltage.png`.
  2. No new structure: a tab named "Platinum / Voltage" makes the HTML page draw two tab bars. This needs no spec change, but it's a hidden naming rule.

  Decision: 1, at any depth, with no option for keeping the tab below, since keeping it is what the request asks for. Nothing in the layout code limits the depth: tabs are checked and drawn by code that can recurse.

## [#68](https://github.com/sskaye/forgegraph/issues/68): separate tick label sizes for the x and y axes

- **Filed by:** CoryONeill.
- **Summary:** different tick label sizes on x and y, so that 28 category labels fit along x while the y-axis numbers match the graphs beside it. The same for weight and color.
- **Verification:** missing. The tick labels are one text style, `axis.tick.label`, for both axes.
- **Proposal:**
  1. The theme keeps `axis.tick.label` for both axes and adds `axis.x.tick.label` and `axis.y.tick.label`, each `[text style, look from axis.tick.label]`. Each takes every parameter it doesn't set from `axis.tick.label`, and is fixed or variable as `axis.tick.label` is, by the rule for general style parameters. A GraphSpec sets `axis.x.tick.label.size: 1.2` beside `axis.x.tick.label.format`.
  2. Replace `axis.tick.label` with `axis.x.tick.label` and `axis.y.tick.label`. This needs no new rule, but every theme sets both, and a GraphSpec changing both axes sets both.

  Decision: 1. It covers size, weight and color, as the request asks, and existing themes and GraphSpecs keep working.

## Found while checking

### The HTML page's tab bar is always dark grey

- **Summary:** a layout's HTML page draws its tab names in dark grey and in the browser's font, whatever the theme, so with a dark background the tab bar is unreadable.
- **Root cause:** the page's colors are hard-coded in drawing/page.py.
- **Verification:** found while checking #39; still so on 0.4.0.
- <!-- fmc:1 -->**Proposal:**<!-- /fmc:1 --> a `tab_bar` category in the layout, beside `tabs` and `separators`: `tab_bar.label`, a text style for the tab names, and `tab_bar.line`, a line style for the line under the bar, each with the first tile's theme's text or line as its defaults. The selected tab is underlined in the label's color, and the page embeds the label's font. The discussion is on the layout specification, docs/specifications/layout_example.md.
- **Decision:** agreed.

<!-- forgemark-comments
- id: 1
  anchor_text: "Proposal:"
  context_before: "Verification: found while checking #39; still so on 0.4.0."
  context_after: "the layout gets a text style for its tab names, beside separators: yaml tab_labe"
  author: Steven
  timestamp: "2026-10-29T03:14:58.630Z"
  resolved: false
  body: "Please propose via comment in the layout specification. While doing, please consider if this can be done without adding a parameter. We already have the tab label as the name of the tab and it would be nice to not require an extra param."
  replies:
    - author: Claude
      timestamp: 2026-10-29T03:25:09Z
      body: |
        Proposed in a comment on the layout specification (docs/specifications/layout_example.md, on the tabs line), with no new parameter: the tab names are written in the first tile's theme's text, the selected tab is underlined in its color, the line under the bar is separators.line, and the page embeds the font. A tab_label text style is there as the alternative.
-->
