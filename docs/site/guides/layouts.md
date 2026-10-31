# Layouts and dashboards

A **layout** arranges GraphSpecs into one figure: a multi-panel figure for a paper, or a dashboard of tabs. A layout file's name ends in `.layout.yaml`, and it's drawn like a GraphSpec:

```bash
forgegraph render cell_performance.layout.yaml
```

From Python, `fg.layout("cell_performance.layout.yaml")` draws it. The [layout specification](../reference/specifications/layout_example.md) lists every parameter.

## A figure for a paper

This layout, from [examples/layouts/paper](https://github.com/sskaye/forgegraph/tree/main/examples/layouts/paper), puts three graphs of three fuel cells on one journal-width figure:

```yaml
--8<-- "examples/layouts/paper/cell_performance.layout.yaml"
```

![Voltage and resistance over time stacked on the left, and the polarization curves spanning both rows on the right.](../images/cell_performance.png)

- **extends** is the built-in pack's layout, so the file lists only what it changes.
- **specifications.format** sets the size and the file types of the whole figure. It replaces each tile's own format, so every tile is drawn at one text size. Each tile keeps its own theme.
- **grid.areas** draws the grid as rows of tile names. A name repeated over a rectangle of cells spans them, as `polarization` spans two rows here, and `.` leaves a cell blank.
- **column_widths** and **row_heights** are the relative sizes of the plot boxes. With none, they're equal, or as large as the tiles need.
- **tiles** names the GraphSpec drawn in each area: a path from the layout's folder. Each tile draws from its own data.

The plot boxes line up across the tiles, whatever their tick labels. A tile is never shrunk to fit: a figure too small for its tiles is an error that names them.

## Separators

`separators` sets the space between and around the tiles, in the first tile's theme's background color: `gap.outer` between neighboring tiles and `gap.inner` around them all. `separators.line` draws a line along the middle of each gap between tiles, and `separators.border.show` draws it around the outside too. `corner_radius` rounds the corners of each tile's background.

## Tabs and dashboards

A layout's `tabs` holds one or more tabs, each under the name shown on its tab. A tab holds a grid and its tiles, or tabs of its own, to any depth. This dashboard, from [examples/layouts/dashboard](https://github.com/sskaye/forgegraph/tree/main/examples/layouts/dashboard), has two tabs:

```yaml
--8<-- "examples/layouts/dashboard/lab_throughput.layout.yaml"
```

![The dashboard's Overview tab: completed runs per week across the top, failed runs, samples per week and run time below.](../images/lab_throughput-overview.png)

Each tab with a grid is a figure of its own. The file types save the tabs differently:

- **png, jpg, tiff and svg:** a file per tab, named by its tab, such as `lab_throughput-overview.png`.
- **pdf:** one file, with a page per tab.
- **html:** one page with every tab.

Tabs that hold tabs look like this, with a tab bar for each level on the HTML page:

```yaml
--8<-- "docs/examples/cells.layout.yaml"
```

[Open its HTML page](../pages/cells.html) to try the tabs and the readouts described below.

## The HTML page

A layout's HTML page, or a GraphSpec's, shows each figure as an image that shrinks to fit a narrow window. On a layout of several tabs, the tab names sit above the figures, in `tab_bar.label`'s look, with `tab_bar.line` under them; by default, they follow the first tile's theme. The tabs work where the page's scripts don't run. Where they run, each tab also has its own link, such as `#by-instrument`.

**Readouts.** Pointing at a data point on the page, or tapping it, shows its values in a box above it, with a ring around the point:

- each axis's title and the point's value, with its error bar and the error bar's aggregation where it has one, as in `8.0 ± 0.4 (95%CI)`;
- then the series' color, marker shape and line style, each where it varies, as the key's title and the point's group.

Markers, a line's points and bars respond; empty space, reference lines and notes don't. A number with an error bar is rounded to the error's last digit; one without has a decimal more than the tick labels. The page carries each figure's points and the font the readouts are written in, so it's larger than the image alone.
