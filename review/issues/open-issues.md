# Open issues

Last updated: 10/30/26

## [#80](https://github.com/sskaye/forgegraph/issues/80): hover readouts on data points in HTML output

- **Filed by:** CoryONeill, from a materials team's lab dashboards in 0.5.0. Unlike #36, which was declined because it came from an agent test, it comes from real use.
- **Summary:** pointing at a data point on a graph in an HTML page, or tapping it, shows its x and y values, and its series' name when there's more than one series. Only data responds: markers, a line's points, the point an error bar is drawn from, and anywhere on a bar. Empty space, reference lines and bands, error bars' whiskers and notes show nothing. A categorical axis shows the category's label. It works in a layout's tiles too.
- **Verification:** confirmed. The HTML page shows each figure as an SVG image and records nothing about its marks, so it can't tell what's under the pointer. The team's workaround reads ForgeGraph's internals (its artists' ids and its bars' attributes), which can change in any release. ForgeGraph already knows each point's series, values and category label as it draws it, and value labels already have a format, which defaults to the value axis's tick label format.
- **<!-- fmc:1 -->Proposal<!-- /fmc:1 -->:** while drawing, ForgeGraph records each data point: where it is in the image, and its readout. The readout has one line for each axis, then one for each of the series' color, marker shape and line style, each only when it varies:

  - X title: value ± error (aggregation)
  - Y title: value ± error (aggregation)
  - Color title: value
  - Shape title: value
  - Line title: value

  An axis's title is its title, or with none, its column's name. A color, shape or line title is its key's title, or with none, its column's name; one with neither, such as the series' name in an untitled key, is written alone. Two that name the same column share a line. The error and its aggregation appear only when the point has an error bar, and the aggregation only when its distances are aggregated. The aggregation is written in a reader's terms: 95%CI, SD, SE, min, max, or e.g. 90th percentile, with a multiplier other than 1 in front, e.g. (2 × SD).

  A category is written as its label and a date in its axis's date format. A number with an error bar is rounded to the error's significant digit, with the error rounded to one significant figure: 8.0 ± 0.4 (95%CI). A number without one is written in the series' value label format for the value, or the axis's tick label format for the base axis; at auto, with one more decimal than the tick labels, which are rounded for reading along an axis, not for reading one value. The HTML page holds the records beside each figure, with a small script that shows a readout for the bar under the pointer, or for the point within its marker's size. A stacked bar shows its own value, as its value label does, and an aggregated point shows the aggregate. Where the page's scripts don't run, the page is as it is now.

  When it's on, one of:
  1. Always, in every HTML page, with no new parameter.
  2. When a new format parameter, `output.hover`, is true (default false).

  Recommendation: 1. It adds no parameter, and the records are small next to the SVG they describe, so a page with many points grows in proportion to its image. 2 lets a page stay static, but no one has asked for that.

  The issue's lighter alternative, a documented record of the marks for other tools (`Graph.marks()`, or a JSON file beside each image), is left out until someone needs the marks outside an HTML page.
- **Decision:** 1, with the readout as proposed.

## [#81](https://github.com/sskaye/forgegraph/issues/81): ask the user to file a feature request after making something non-standard

- **Filed by:** sskaye.
- **Summary:** users ask their agents for features ForgeGraph doesn't have, and the agents make them anyway, so the request never reaches ForgeGraph unless someone reminds the user to file one. Whenever an agent makes a non-standard graph or layout, or any visual not drawn by ForgeGraph, it should ask the user whether they'd like to file a feature request.
- **Verification:** confirmed. The skill offers a request only before drawing, when a fixed parameter or a missing graph type blocks the request (SKILL.md, workflow step 2). Nothing asks after something non-standard has been drawn: a graph from a pack only a folder config lists, a drawing on `forgegraph.blank`, or a chart made some other way.
- <!-- fmc:2 -->**Proposal:**<!-- /fmc:2 -->
  1. A step in the skill's workflow, after step 5: "If anything you drew is non-standard or wasn't drawn by ForgeGraph, say what ForgeGraph couldn't do and ask the user whether to file a feature request (references/requests.md)."
  2. As 1, and ForgeGraph's own message about a non-standard file (from `render` and the API) also says that what's missing can be requested at the pack's `issues` address, so agents that haven't loaded the skill see it too.

  Recommendation: 1, the smallest change that meets the need. 2 reaches agents without the skill, but adds a line to every non-standard message, including when someone is just trying out their own pack.

  In either case, references/requests.md tells the agent to write a request under the feature request form's headings (what you're trying to make, what ForgeGraph does today, an example, and the version), so requests filed by agents read like those filed with the form.
- **Decision:** 1, worded as suggested in SKILL.md and references/requests.md.

## [#82](https://github.com/sskaye/forgegraph/issues/82): proper documentation

- **Filed by:** sskaye.
- **Summary:** a documentation site a new user can learn ForgeGraph from, organized like [TabPFN's](https://docs.priorlabs.ai). Theirs has getting started (overview, quickstart, FAQ), a page per capability, guides to improving results, troubleshooting, a cookbook of worked examples, a changelog, and an API reference for every public class and function.
- **Verification:** confirmed. ForgeGraph's documentation is files in the repository: the README, the definition files' mirrors in docs/specifications, the built-in pack's in docs/packs, the catalog page, the CHANGELOG, the visual changelogs, the architecture document and the commands' `--help`. There's no site, no guide to a task such as making a layout, a pack or a schedule, no gallery of examples, and no API reference beyond the README's signatures.
- **Proposal:** a site with these sections:
  - Get started: an overview, installation, a quickstart, and the agent skill.
  - Guides: one per task (graphs, series, layers, layouts and dashboards, themes, formats and packs, configs, schedules, provenance).
  - Gallery: worked examples, each with its image, GraphSpec and data.
  - Reference: the specifications (generated from the definition files, as the mirrors are now), the commands, and the Python API (generated from the docstrings).
  - Lint issues and troubleshooting, the changelog, and the FAQ.

  How it's built, one of:
  1. MkDocs with the Material theme, built from Markdown in the repository and published to GitHub Pages by CI with each release. The pages are Markdown, like the mirrors, so you can review them with Forgemark before they're published, and the API reference can be generated from the docstrings (mkdocstrings).
  2. A hosted service, as TabPFN uses (Mintlify). It's the most polished, with search built in, but it needs an outside account, and its pages use its own format.
  3. Sphinx on Read the Docs, the usual choice for Python libraries. It keeps a version of the docs for each release, but the pages are written in reStructuredText or MyST, not the Markdown the repository uses now.

  Recommendation: 1, starting with Get started and the generated Reference, which mostly reuse what exists. The guides and the gallery come after, each reviewed as a page.
- **Decision:** 1, starting with Get started and the generated Reference.

<!-- forgemark-comments
- id: 1
  anchor_text: Proposal
  context_before: "els already have a format, which defaults to the value axis's tick label format."
  context_after: ": while drawing, ForgeGraph records each data point: where it is in the image, i"
  author: Steven
  timestamp: "2026-10-30T22:50:22.493Z"
  resolved: false
  body: |-
    I like the proposal, but one suggestion, one concern, one request:
    - Include additional details: error bar value and the values of the colorby, lineby, and shapeby params each only if present. 
    - At what number of points will this become a speed or file size issue? Graphs could get made with very large numbers of datapoints and we don’t want to program to bog down or crash.
    - Please propose an exact design for the tooltip so we can agree on it before building.
  replies:
    - author: Claude
      timestamp: 2026-10-30T22:58:38Z
      body: |
        1. Details: added to the proposal. Each only when present, the readout shows the point's error bar and the values of the columns its series is grouped by. I've included marker fill and split columns beside color, line style and marker shape, since they also tell a point's group apart; say if you'd rather leave them out. An error bar is written as ± its distance, or as −lower / +upper when the two differ.
        
        2. Size and speed. I measured a line of 1,000 to 100,000 points, with records like those proposed:
           1. The page: the records are about 30 % of the SVG's size (3.9 MB against 12.8 MB at 100,000 points). The page holds the SVG in base64, a third larger, so the records add about a quarter to the page.
           2. Rendering: working out 100,000 points' positions takes 0.04 s, against 1.1 s to draw and save the graph.
           3. The browser: each figure's records are read the first time the pointer enters it. At 100,000 points, reading them takes about 40 ms and indexing them by position 5 ms; finding the point under the pointer then takes 10 µs a move. At a million points, reading takes about 0.25 s (35 MB of records), but the SVG would be about 130 MB, which the browser already struggles to show.
           So the image becomes the problem well before the readout does, and I'd add no limit of its own: a limit would mean a page losing its readout without saying so. Category and column names longer than these make the records larger, but not by enough to change this.
        
        3. Design: review/issues/hover-readout-mock.html shows it on a real ForgeGraph graph, with the readout placed by hand over one point.
           1. When it shows: when the pointer is within 3 px of a point's marker (6 px of a line's point that has no marker), or anywhere on a bar, or on a tap. The nearest point wins. It shows at once, and goes when the pointer leaves or on a tap elsewhere.
           2. The point: a 2 px ring in the series' color, 3 px outside its marker. A bar has no ring, since the pointer is on it.
           3. The box: the theme's background color, a 1 px border in the axis line's color, 3 px corners, a light shadow, and 6 px × 9 px of padding. It sits centred above the point, 8 px clear of the ring; below it when there's no room above; and moved sideways to stay inside the figure.
           4. The text: the series' value label text style (font, size and color), scaled with the image as the graph's own text is, with the font embedded as the tab bar's is. The names are in that color at 65 % opacity, and the values are aligned right in figures of equal width.
           5. The rows: the series' key sample and name; the x axis's title and the point's x; the y axis's title and its y, with its error bar; then each grouping column's name and value. An axis with no title uses its column's name.
           6. The values: as in the proposal. In the mock, the tick labels have one decimal, so the readout has two: 7.99 ± 0.43.
    - author: Claude
      timestamp: 2026-10-30T23:10:31Z
      body: |
        Done: the proposal now gives the readout in your format, and the mock shows it: "Additive: TiO₂", "Hardness (GPa): 8.0 ± 0.4 (ci)", "Fired at: 1300 °C". Marker fill and split columns are left out, as in your list. The rest of the design (when it shows, the ring, the box and the text style) is as before.
        
        1. The value is 8.0, not 7.9: the mean is 7.985, which rounds to 8.0 in the tenths place. The error bar in the mock is half the 95 % confidence interval (ci), not the standard deviation, so it reads (ci).
        2. "Fired at" is the mock's key title, which I made up; the readout uses whatever title the key has, or the column's name when it has none.
        3. The aggregation's name, one of:
           1. As the GraphSpec writes it: ci, stddev, stderr, min, max, percentile. With a multiplier other than 1, it's written in front, e.g. (2 × stddev).
           2. Names a reader knows: 95 % CI, SD, SE, min, max, 90th percentile, with the multiplier written the same way.
           Recommendation: 2, since the readout is for people reading the page, not the GraphSpec.
        4. The parentheses name the error's aggregation only, not the point's (the mean here). I'd leave the point's out, since a title such as "Mean hardness (GPa)" can say it, and the line stays short.
    - author: Claude
      timestamp: 2026-10-30T23:14:49Z
      body: |
        Done: the aggregation is written in a reader's terms (95%CI, SD, SE, min, max, or e.g. 90th percentile, with a multiplier in front, e.g. 2 × SD), and the mock reads 8.0 ± 0.4 (95%CI).
    - author: Steven
      timestamp: "2026-10-30T23:15:15.597Z"
      body: Agreed
- id: 2
  anchor_text: "Proposal:"
  context_before: "der config lists, a drawing on forgegraph.blank, or a chart made some other way."
  context_after: "A step in the skill's workflow, after step 5: \"If anything you drew is non-stand"
  author: Steven
  timestamp: "2026-10-30T22:51:31.252Z"
  resolved: false
  body: "Agreed. Please propose the change directly in the skill.md so I can review the exact wording and position."
  replies:
    - author: Claude
      timestamp: 2026-10-30T22:58:38Z
      body: |
        Proposed as suggestions in src/forgegraph/skill/forgegraph/SKILL.md, on the end of step 6, and in references/requests.md, for writing requests under the issue forms' headings. I put the new step after the final inspection rather than after step 5, so it's asked once, when the graph is shared, not on every iteration. The decision is recorded as 1.
    - author: Steven
      timestamp: "2026-10-30T23:16:48.730Z"
      body: "Accepted in the skill.md."
-->
