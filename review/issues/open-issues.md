# Open issues

Last updated: 10/28/26

## [#44](https://github.com/sskaye/forgegraph/issues/44): an outside note goes above the title

- **Filed by:** sskaye.
- **Summary:** a note outside the plot at the top is drawn above the title, while a key there goes between the title and the plot.
- **Root cause:** top notes are anchored on the title, and only keys make the title move up.
- **Verification:** reproduced on 0.3.0 and 0.4.0.
- <!-- fmc:6 -->**Proposal:**<!-- /fmc:6 --> anchor top notes on the plot box, and make room for them as for keys, so the order is title, note, key, plot. About 20 lines.
- **Decision:** agreed.

## [#56](https://github.com/sskaye/forgegraph/issues/56): a title without descenders sits lower than its neighbors in a layout

- **Filed by:** sskaye.
- **Summary:** in a layout row, "Polarization" sits lower than "Voltage" and "Typology", although the plots line up. A title is placed by the bottom of its ink, not by its baseline, so a title without g, j, p, q or y drops by the depth of the descenders. A single graph's height also changes with its title's letters.
- **Root cause:** the title is placed so that title.gap separates the plot box from the title's lowest letter (`_title_pad` in drawing/spacing.py). In a title with descenders, the lowest letter is below the baseline, so the baseline sits higher by the depth of the descenders. The room above the plot box is measured to the letters too, so a single graph's height changes with its title. A y-axis title reading upward on the left is spaced the same way, from its lowest letter to the tick labels, and has the same fault.
- **Verification:** reproduced on 0.4.0 with the issue's three tiles. The tops of "Voltage" and "Typology" are at 37–38 px and the top of "Polarization" at 67 px, while their bottoms are within 2 px of each other.
- <!-- fmc:4 -->**Proposal:**<!-- /fmc:4 --> measure title.gap to the title's baseline instead of its lowest letter, so descenders hang into the gap. Titles in a layout row then share a baseline, and a graph's height no longer depends on its title's letters. Do the same for a y-axis title reading upward on the left. No new parameter.
- **Decision:** agreed.

## [#67](https://github.com/sskaye/forgegraph/issues/67): nested tabs in a layout

- **Filed by:** CoryONeill.
- **Summary:** two levels of tabs in a layout: a tab per group (an electrode material) holding a tab per chart (a metric). Switching groups keeps the same metric showing, and a link can open a given pair of tabs.
- **Verification:** missing. A tab holds a grid of tiles, and can't hold tabs.
- **Proposal:**
  1. A tab may hold `tabs` in place of `grid` and `tiles`, nested as deep as the layout needs. The HTML page draws a tab bar for each level. Switching a tab keeps the tab of the same name below it if there is one, and a link such as `#platinum/voltage` opens that path, as a link opens a tab today. Image and PDF files are named by every tab on the path, such as `results-platinum-voltage.png`.
  2. No new structure: a tab named "Platinum / Voltage" makes the HTML page draw two tab bars. This needs no spec change, but it's a hidden naming rule.

  <!-- fmc:3 -->Decision:<!-- /fmc:3 --> 1, at any depth, with no option for keeping the tab below, since keeping it is what the request asks for. Nothing in the layout code limits the depth: tabs are checked and drawn by code that can recurse.

## [#68](https://github.com/sskaye/forgegraph/issues/68): separate tick label sizes for the x and y axes

- **Filed by:** CoryONeill.
- **Summary:** different tick label sizes on x and y, so that 28 category labels fit along x while the y-axis numbers match the graphs beside it. The same for weight and color.
- **Verification:** missing. The tick labels are one text style, `axis.tick.label`, for both axes.
- **Proposal:**
  1. The theme keeps `axis.tick.label` for both axes and adds `axis.x.tick.label` and `axis.y.tick.label`, each `[text style, look from axis.tick.label]`. Each takes every parameter it doesn't set from `axis.tick.label`, and is fixed or variable as `axis.tick.label` is, by the rule for general style parameters. A GraphSpec sets `axis.x.tick.label.size: 1.2` beside `axis.x.tick.label.format`.
  2. Replace `axis.tick.label` with `axis.x.tick.label` and `axis.y.tick.label`. This needs no new rule, but every theme sets both, and a GraphSpec changing both axes sets both.

  <!-- fmc:2 -->Decision: 1<!-- /fmc:2 -->. It covers size, weight and color, as the request asks, and existing themes and GraphSpecs keep working.

## Found while checking

### The HTML page's tab bar is always dark grey

- **Summary:** a layout's HTML page draws its tab names in dark grey and in the browser's font, whatever the theme, so with a dark background the tab bar is unreadable.
- **Root cause:** the page's colors are hard-coded in drawing/page.py.
- **Verification:** found while checking #39; still so on 0.4.0.
- <!-- fmc:1 -->**Proposal:**<!-- /fmc:1 --> in a comment on the layout specification, docs/specifications/layout_example.md, with no new parameter: the tab names take the first tile's theme's text.

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
- id: 2
  anchor_text: "Recommendation: 1"
  context_before: "w rule, but every theme sets both, and a GraphSpec changing both axes sets both."
  context_after: ". It covers size, weight and color, as the request asks, and existing themes and"
  author: Steven
  timestamp: "2026-10-29T03:15:33.444Z"
  resolved: false
  body: Agreed.
  replies:
    - author: Claude
      timestamp: 2026-10-29T03:25:09Z
      body: |
        Recorded as the decision.
- id: 3
  anchor_text: "Recommendation:"
  context_before: "This needs no spec change, but it's a hidden naming rule."
  context_after: "1, with two levels only and no option for keeping the second tab, since keeping"
  author: Steven
  timestamp: "2026-10-29T03:17:09.039Z"
  resolved: false
  body: "Agreed, but can we remove the two level limit? I don’t see any reason for not allow whatever number of tabs the author specifies. If it can’t be arbitrary, then do 3."
  replies:
    - author: Claude
      timestamp: 2026-10-29T03:25:09Z
      body: |
        Yes: nothing in the layout code limits the depth, since tabs are checked and drawn by code that can recurse. The proposal and decision now say any depth, with a tab bar per level and a link naming the whole path.
- id: 4
  anchor_text: "Proposal:"
  context_before: "p of \"Polarization\" at 67 px, while their bottoms are within 2 px of each other."
  context_after: "measure title.gap to the title's baseline instead of its lowest letter, so desce"
  author: Steven
  timestamp: "2026-10-29T03:17:42.430Z"
  resolved: false
  body: Agreed
  replies:
    - author: Claude
      timestamp: 2026-10-29T03:25:10Z
      body: |
        Recorded as the decision.
- id: 5
  floating: true
  author: Steven
  timestamp: "2026-10-29T03:18:02.947Z"
  resolved: false
  body: "Agreed. Decline and remove."
  replies:
    - author: Claude
      timestamp: 2026-10-29T03:25:10Z
      body: |
        Closed #47 on GitHub as not planned, with a comment saying a GraphSpec meant to be extended goes in a folder pack, and removed it from the page.
- id: 6
  anchor_text: "Proposal:"
  context_before: "Verification: reproduced on 0.3.0 and 0.4.0."
  context_after: "anchor top notes on the plot box, and make room for them as for keys, so the ord"
  author: Steven
  timestamp: "2026-10-29T03:18:26.562Z"
  resolved: false
  body: Agreed.
  replies:
    - author: Claude
      timestamp: 2026-10-29T03:25:10Z
      body: |
        Recorded as the decision.
- id: 7
  floating: true
  author: Steven
  timestamp: "2026-10-29T03:19:43.742Z"
  resolved: false
  body: "Decline and close. Wait for request based on a real use case (this was an non-reviewed agent test by me)"
  replies:
    - author: Claude
      timestamp: 2026-10-29T03:25:10Z
      body: |
        Closed on GitHub as not planned, with a comment saying it came from an unreviewed agent test rather than a real use case and will be revisited if one asks for it, and removed it from the page.
- id: 8
  floating: true
  author: Steven
  timestamp: "2026-10-29T03:20:25.688Z"
  resolved: false
  body: "Decline and close. Wait for request based on a real use case (this was an non-reviewed agent test by me)"
  replies:
    - author: Claude
      timestamp: 2026-10-29T03:25:10Z
      body: |
        Closed on GitHub as not planned, with a comment saying it came from an unreviewed agent test rather than a real use case and will be revisited if one asks for it, and removed it from the page.
- id: 9
  floating: true
  author: Steven
  timestamp: "2026-10-29T03:20:37.735Z"
  resolved: false
  body: "Decline and close. Wait for request based on a real use case (this was an non-reviewed agent test by me)"
  replies:
    - author: Claude
      timestamp: 2026-10-29T03:25:10Z
      body: |
        Closed on GitHub as not planned, with a comment saying it came from an unreviewed agent test rather than a real use case and will be revisited if one asks for it, and removed it from the page.
- id: 10
  floating: true
  author: Steven
  timestamp: "2026-10-29T03:20:50.537Z"
  resolved: false
  body: "Decline and close. Wait for request based on a real use case (this was an non-reviewed agent test by me)"
  replies:
    - author: Claude
      timestamp: 2026-10-29T03:25:10Z
      body: |
        Closed on GitHub as not planned, with a comment saying it came from an unreviewed agent test rather than a real use case and will be revisited if one asks for it, and removed it from the page.
- id: 11
  floating: true
  author: Steven
  timestamp: "2026-10-29T03:21:30.435Z"
  resolved: false
  body: "Close due to non-reproducibility. Include note on github explaining if possible."
  replies:
    - author: Claude
      timestamp: 2026-10-29T03:25:11Z
      body: |
        Closed on GitHub as not reproducible, with a comment explaining that the gap above the data already counts reference lines and is only a few points on a short tile, and how a label above the line grows the axis. Removed from the page.
- id: 12
  floating: true
  author: Steven
  timestamp: "2026-10-29T03:22:25.985Z"
  resolved: false
  body: "Close. Include note on github with your explanation if possible."
  replies:
    - author: Claude
      timestamp: 2026-10-29T03:25:11Z
      body: |
        Closed on GitHub, with a comment explaining that a half-width tile can be about as tall as a full-width one through a theme with a smaller plot_area.aspect_ratio, that layouts have no per-tile settings, and that a format per tab isn't planned. Removed from the page.
- id: 13
  floating: true
  author: Steven
  timestamp: "2026-10-29T03:22:46.174Z"
  resolved: false
  body: "Decline and close. Wait for request based on a real use case (this was an non-reviewed agent test by me)"
  replies:
    - author: Claude
      timestamp: 2026-10-29T03:25:10Z
      body: |
        Closed on GitHub as not planned, with a comment saying it came from an unreviewed agent test rather than a real use case and will be revisited if one asks for it, and removed it from the page.
- id: 14
  floating: true
  author: Steven
  timestamp: "2026-10-29T03:22:50.686Z"
  resolved: false
  body: "Decline and close. Wait for request based on a real use case (this was an non-reviewed agent test by me)"
  replies:
    - author: Claude
      timestamp: 2026-10-29T03:25:11Z
      body: |
        Closed on GitHub as not planned, with a comment saying it came from an unreviewed agent test rather than a real use case and will be revisited if one asks for it, and removed it from the page.
-->
