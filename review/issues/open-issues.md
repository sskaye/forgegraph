# Open issues

Last updated: 10/30/26

## [#80](https://github.com/sskaye/forgegraph/issues/80): hover readouts on data points in HTML output

- **Filed by:** CoryONeill, from a materials team's lab dashboards in 0.5.0. Unlike #36, which was declined because it came from an agent test, it comes from real use.
- **Summary:** pointing at a data point on a graph in an HTML page, or tapping it, shows its x and y values, and its series' name when there's more than one series. Only data responds: markers, a line's points, the point an error bar is drawn from, and anywhere on a bar. Empty space, reference lines and bands, error bars' whiskers and notes show nothing. A categorical axis shows the category's label. It works in a layout's tiles too.
- **Verification:** confirmed. The HTML page shows each figure as an SVG image and records nothing about its marks, so it can't tell what's under the pointer. The team's workaround reads ForgeGraph's internals (its artists' ids and its bars' attributes), which can change in any release. ForgeGraph already knows each point's series, values and category label as it draws it, and value labels already have a format, which defaults to the value axis's tick label format.
- **Proposal:** while drawing, ForgeGraph records each data point: where it is in the image, its x and y as the axes write them, and its series' name. A category is written as its label, a date in its axis's date format, a value in the series' value label format, and a number on the base axis in that axis's tick label format. The HTML page holds the records beside each figure, with a small script that shows a readout for the bar under the pointer, or for the point within its marker's size. A stacked bar shows its own value, as its value label does, and an aggregated point shows the aggregate. Where the page's scripts don't run, the page is as it is now.

  When it's on, one of:
  1. Always, in every HTML page, with no new parameter.
  2. When a new format parameter, `output.hover`, is true (default false).

  Recommendation: 1. It adds no parameter, and the records are small next to the SVG they describe, so a page with many points grows in proportion to its image. 2 lets a page stay static, but no one has asked for that.

  With the format at auto, a readout rounds as the tick labels do, which may be coarser than the data. Setting the series' value label format gives more digits.

  The issue's lighter alternative, a documented record of the marks for other tools (`Graph.marks()`, or a JSON file beside each image), is left out until someone needs the marks outside an HTML page.
- **Decision:** open.

## [#81](https://github.com/sskaye/forgegraph/issues/81): ask the user to file a feature request after making something non-standard

- **Filed by:** sskaye.
- **Summary:** users ask their agents for features ForgeGraph doesn't have, and the agents make them anyway, so the request never reaches ForgeGraph unless someone reminds the user to file one. Whenever an agent makes a non-standard graph or layout, or any visual not drawn by ForgeGraph, it should ask the user whether they'd like to file a feature request.
- **Verification:** confirmed. The skill offers a request only before drawing, when a fixed parameter or a missing graph type blocks the request (SKILL.md, workflow step 2). Nothing asks after something non-standard has been drawn: a graph from a pack only a folder config lists, a drawing on `forgegraph.blank`, or a chart made some other way.
- **Proposal:**
  1. A step in the skill's workflow, after step 5: "If anything you drew is non-standard or wasn't drawn by ForgeGraph, say what ForgeGraph couldn't do and ask the user whether to file a feature request (references/requests.md)."
  2. As 1, and ForgeGraph's own message about a non-standard file (from `render` and the API) also says that what's missing can be requested at the pack's `issues` address, so agents that haven't loaded the skill see it too.

  Recommendation: 1, the smallest change that meets the need. 2 reaches agents without the skill, but adds a line to every non-standard message, including when someone is just trying out their own pack.

  In either case, references/requests.md tells the agent to write a request under the feature request form's headings (what you're trying to make, what ForgeGraph does today, an example, and the version), so requests filed by agents read like those filed with the form.
- **Decision:** open.

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
- **Decision:** open.
