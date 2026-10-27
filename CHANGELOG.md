# Changelog

ForgeGraph follows [semantic versioning](https://semver.org). Before 1.0, a minor version may change how graphs look or how specs are written. From 0.2.0 on, each release's entry links its visual changelog: before and after images of every catalog card and regression graph that changed, made with `scripts/visual_changelog.py`.

## Unreleased

### Changed

- **Breaking for existing specs and configs:** one built-in pack, `forgegraph_default`, replaces `forgegraph_base` and `forgegraph_base_2`. Its specs are `light_theme` (in place of `forgegraph_base/base_theme`), `compact_format` (`base_format`), `wide_format` (`base_layout_format`), `layout` (`layout_example`), `schedule` (`base_schedule`) and `graphspec_example`; `forgegraph_base_2` has no replacement. A main config listing `forgegraph_base` or `forgegraph_base_2` is an error: list `forgegraph_default` instead. light_theme draws 0.3's look, and fixes the font, the palette and its lists, the ticks' direction, sides and algorithms, the grid and the series' lines, so a GraphSpec that sets `grid.x.show` or a series' line width needs a theme that leaves them variable. The default layout draws no line between tiles and leaves 0.25 × the base size at the figure's edges.
- The specification files, which define each kind, are in `src/forgegraph/specifications/`, and their pages in `docs/specifications/`; no spec can name or extend them. The built-in pack's pages are in `docs/packs/forgegraph_default/`, and the catalog page is `catalog/forgegraph_default.html`.
- A category's brackets in a specification file say what the code reads about it, from a fixed set: its style, `same as <sibling>` for a category with a sibling's parameters, and `look from <theme category>` for a layer category whose look comes from the theme. Anything else there is an error, and descriptions are never read, so rewording one changes nothing.
- A reference layer's `fill.color` may be None: two lines with values make a band only when it isn't.
- **Breaking for existing specs:** a GraphSpec lists its series by name under `series`, each drawn from its own column (by default, the column of its name) with its own settings: `aggregation`, `split`, `order`, `color`, `color_scale`, `line`, `marker`, `bar` and `value_label`, and the theme's variable series parameters it sets for itself. They replace `axis.*.data.aggregation`, `encoding.*` and `mark.*`; the value axis's `data.column` is None. `arrangement.base_axis`, `arrangement.stacking`, `arrangement.offset` and `arrangement.total.show` replace `series.base_axis`, `series.aggregation`, `series.offset` and `series.value_label.total.show`. A series' color, line style, marker shape and fill take `first`, `series`, a value or a column; series take palette colors in the order they're listed.
- **Breaking for existing specs:** the `reference` layer replaces `reference_line`: `line_1` and `line_2`, each at a value or from a column, with its own `aggregation` and `offset` (aggregation styles), `scope`, line and label (with `label.inside`), and the `fill` of a band between them. The theme's `layer.reference` replaces `layer.reference_line`.
- An aggregation style (`function`, `multiplier`, `percentile`) for a series, a reference line and error bars; functions include `percentile`, `stddev`, `stderr` and `ci`.
- `line.interpolate` draws a series' line straight, in steps (`step_after`, `step_before`, `step_center`) or as a smooth curve that never overshoots its points.
- A note and a reference layer's lines, labels and fill may set the theme's variable look for themselves.
- A style key (one from `encoding.line.style.column`, `encoding.marker.shape.column` or `encoding.marker.fill.column`) follows `legend.key.title.text`, as the series' key does: `column_name`, the default, gives each key its own column's name, so default graphs are unchanged; `None` removes every key's title; a text titles one key, and with more than one key drawn it's an error. With no `encoding.color.column`, a style key's samples are drawn in the one series color, not the text color. `render --json` reports `style_keys`, the column each style key drawn explains (for a layout, each tile's), beside `labelling`.
- A range type `date`: a date, or a date and time, as YAML's bare date (`2025-08-25`, `2025-08-25 06:00:00`) or ISO 8601 text (`"2025-08-25T06:00"`); a time with a zone is at its clock time, as the data's are. `axis.x.min`, `axis.x.max`, `axis.y.min` and `axis.y.max`, a reference line's `value` and `benchmark.value` take it: on a datetime axis or column, a date is drawn exactly where its day number is, and numbers keep working as day numbers. A date on an axis that isn't dates is an error naming the axis's type. Text that reads as a date is a reference line's column only if the data has a column of that name. Provenance records write dates as ISO 8601 text.
- On a date value axis, what would draw nonsense is an error that says what to do: stacking (`series.aggregation` sum or percent), adding up rows (`axis.*.data.aggregation` sum), bars (`mark.bar.show`, which would start at 1970), and value labels without a date format. A reference line at a date column's aggregate is on a date axis only, at its mean, median, min or max, with multiplier 1. A date axis's `tick.label.format` must have a date directive.

### Fixed

- In a theme whose text is light, powers of ten on a log axis and superscripts in labels no longer give a `font-fallback` lint issue. They were always drawn in the theme's font and weight; the issue came from the faces matplotlib loads for maths but doesn't draw these with.
- The `outside-limits` and `log-axis-values` lint checks count only data points. A reference line's ends and an error bar's ends no longer count as points outside a set axis limit, or as values of 0 or below on a log axis.
- A style key on the benchmark's column matches the drawing: its entries are the groups the series are styled by, so a value after the benchmark no longer gets the next value's style, and the benchmark, drawn in its own style, has no style sample and is named once, by `legend.method`. When `legend.method: key` doesn't fit, the error says why: every position in `legend.key.positions` is taken or covers data, naming the position each style key took.
- YAML's null (`null`, `~` or nothing) is None everywhere a spec can say None. `extends: null` failed with `KeyError: None`, and a file extending null wasn't required to list every parameter.
- Computed values are compared with an axis's limits allowing for float noise: a value is past a limit only if it's past by more than 1e-9 of the axis's span, measured in powers of ten on a log axis. A stack that totals `axis.y.max` but for its last digits isn't reported by `outside-limits`; a reference line at a computed value that equals a set limit isn't an error; bars whose values are 0 but for float noise still stand on the axis; and a tick a hair past the end of the view, which matplotlib draws, is measured for layout and lint and counts when log labels choose between plain numbers and powers of ten.
- Dates and times draw the same on y as on x: every value placed on an axis (the data, its aggregates, stacks, reference lines, error bars and limits) becomes a number the same way, so a date y axis has date ticks, a reference line at a date column's aggregate lands on it, and error bars from a date column's spread are in days. With value labels off, a date `tick.label.format` such as `"%H:%M"` on y is no longer refused as a number format; value labels and a reference line's value on a date axis are written in a date format.

## 0.3.0 (2026-10-25)

Images that changed: the [visual changelog](docs/visual-changelog/0.3.0.html).

### Added

- `fg.blank` takes `registry=`, as `fg.render` does, and a blank canvas's `save` path is optional, as a graph's is: with none, it saves `canvas.png` and the format's other file types.

### Changed

- **Breaking for existing specs:** parameters follow one naming system. `_` joins words that name one thing (`error_bar`, `plot_area`), `.` goes from a thing to its parts and properties (`line.width`), an on/off switch is the thing's `.show`, and nothing is abbreviated. A spec still using an old name is an error that suggests the new one; an old name that's now a category, such as `encoding.color`, suggests that category's parameters. The Python API's keyword arguments (`fg.xy`'s `color=`, `line_style=`, `marker_shape=`, `marker_fill=`, `detail=`) are unchanged and set the new paths. Graphs draw the same as before. The renames, old → new:
  1. `grid.line_style` → `grid.line.style`; `grid.line_width` → `grid.line.width`
  2. `plot_area.line_color` → `plot_area.line.color`; `plot_area.line_width` → `plot_area.line.width`
  3. `layer.error_bar.line_width` → `layer.error_bar.line.width`; `layer.error_bar.cap_size` → `layer.error_bar.cap.width`
  4. `layer.reference_line.line_style` → `layer.reference_line.line.style`; `layer.reference_line.line_width` → `layer.reference_line.line.width`
  5. `series.marker.edge_color`, `series.marker.edge_width` → `series.marker.edge.color`, `series.marker.edge.width`, and the same in `series.bar`, `series.benchmark.marker` and `series.benchmark.bar`
  6. `legend.key.frame_width` → `legend.key.frame.width`
  7. `legend.key.sample.marker_size` → `legend.key.sample.marker.size`
  8. `legend.key.frame` → `legend.key.frame.show`
  9. `series.value_label.total` → `series.value_label.total.show`
  10. `axis.tick.minor.num` → `axis.tick.minor.count`
  11. `encoding.color` → `encoding.color.column`; `encoding.color_type` → `encoding.color.type`; `encoding.line_style` → `encoding.line.style.column`; `encoding.marker_shape` → `encoding.marker.shape.column`; `encoding.marker_fill` → `encoding.marker.fill.column`; `encoding.detail` → `encoding.detail.column` (`encoding.order` is unchanged)
  12. Layouts: `separators.line.border` → `separators.border.show`
  13. Schedules: `freshness.stamp` → `freshness.stamp.show`; `cadence.interval` → `cadence.interval.count`; `cadence.interval_unit` → `cadence.interval.unit`
- **Breaking for packs' catalog files:** a catalog's cards are chosen by a rule, not by hand. Every parameter gets one card, its value taken from its range and the baseline's data, drawn on the first baseline where it changes the drawing; the page shows the variable parameters' cards. A catalog file lists only its baselines, and a layer's settings: `variations`, `no_card` and the `{value, from, with}` forms are gone. A pack's catalog page draws with the pack's own theme and format values.
- Drawing and saving are about 3.7 times faster. Graphs and their files are the same as before.
- A pack's fonts are registered when a file drawn uses one of its specs, not whenever a config lists the pack.
- `forgegraph --help` gives each command a one-sentence summary, and `forgegraph catalog --help` names every kind it lists.
- The internal package `forgegraph.catalog` is `forgegraph.catalog_build`. The API is unchanged.
- One name is one pack. A config can't give a built-in pack's name, or a name the main config already gives, to another folder. Before, a folder config's copy of a pack replaced the one the main config lists, and what it drew wasn't marked non-standard.
- ForgeGraph needs matplotlib 3.11.2 and typer 0.15.4 or later; earlier versions installed but didn't work.
- The package's description and classifiers say what it is now: released, in alpha.

### Fixed

- Error bars on a date axis stand on their points, and error bars of aggregated rows on a date axis draw.
- Times with a time zone are drawn at the times their clocks show. Before, they raised an error.
- A reference line at a column's sum or standard deviation counts each row once when several y columns are drawn.
- Value labels written with format auto use the value axis's tick label format when it's set, as reference lines do.
- The catalog's record of what it was built from covers every module it draws with, so a change to the drawing code marks the catalog out of date.
- The package's metadata lists the bundled fonts' licences.
- A GraphSpec naming a list as its theme, format or graph type gets the error "must be a single value", not a crash.
- A config naming a pack that can't be found, or another pack problem, stops `catalog`, `pack-notes`, `schema` and `explain` with its problems listed (`error:` lines, exit 1), not a traceback; with `--json`, one problem each, not one joined line.

## 0.2.0 (2026-10-24)

Images that changed: the [visual changelog](docs/visual-changelog/0.2.0.html).

### Changed

- Error bars are black by default in both built-in themes, and their color (`layer.error_bar.color`) is a variable parameter: a GraphSpec may set `series` or any hex color.
- Three internal modules are renamed so none shares a name with the API: `forgegraph.render` is `forgegraph.drawing`, `forgegraph.layout` is `forgegraph.layouts` and `forgegraph.blank` is `forgegraph.canvas`. `import forgegraph.layouts as m` now gives the module, not `fg.layout`. The API is unchanged.

### Fixed

- `forgegraph --version` and `--help` no longer load matplotlib and pandas, so they answer at once, even on a new install. The API loads on first use.
- The README and the skill's reference say when the main config is written: the first time a command reads the configs, such as `catalog` or `render`.
- Error bars on side-by-side bars (`series.offset: side_by_side`) are drawn on their own bars. Before, every series but the middle one had its error bars drawn where they were first placed, before layout, usually off the axes.

## 0.1.0 (2026-10-24)

The first public release.

### Added

- **GraphSpecs:** a graph described in YAML or as a Python dict, drawn with `forgegraph render` or `fg.render`; `fg.xy` draws straight from a DataFrame.
- **The `xy` graph type:**
  - lines, markers and bars: grouped, stacked, 100 % stacked and horizontal;
  - dates and log axes, value labels, a benchmark series;
  - series named beside their lines or in a key.
- **Layers:** reference lines, notes and error bars, from the data or given.
- **Themes and formats:** a theme fixes what must stay the same and gives defaults for the rest; a format sets size, base font size, file types and resolution.
- **Packs and configs:**
  - every named spec comes from a pack, named `pack/name`; ForgeGraph's own is `forgegraph_base`, and `forgegraph_base_2` is a second look in this repository;
  - the main config (written on first use, or named by `FORGEGRAPH_CONFIG`) and folder configs (`forgegraph.toml`) say which packs may be used;
  - a pack only a folder config lists is non-standard: it works, and what's drawn with it is watermarked.
- **Lint on every render:** overlapping or clipped text, a key covering data, fonts too small for the format, missing fonts, dropped rows and more.
- **Provenance:** every saved file (PNG, JPEG, TIFF, SVG, PDF and HTML) records its GraphSpec and the specs it was drawn with, at the format's provenance level; `forgegraph load` reads it back.
- **Layouts:** several GraphSpecs in one figure, with spanning tiles, blank cells and set widths; tabs, and HTML dashboards.
- **Scheduled renders:** schedule files, `forgegraph job run`, a status file, `on_failure` and `on_success` hooks, a "data as of" footnote and a stale banner.
- **The themed canvas:** `forgegraph.blank(theme, format)` for what no graph type can draw, always watermarked as non-standard.
- **The agent skill** for Claude Code, installed with `forgegraph skill install`, with reference notes for themes, formats and configs, and for filing requests.
- **Commands:** `render`, `explain`, `catalog`, `schema`, `pack-notes`, `load`, `job run` and `skill install`, each with `--json`.
- **Catalogs:** a page for each pack in this repository, with a card for every parameter.

## 0.0.1 (2026-10-17)

The name, reserved on PyPI. No functionality.
