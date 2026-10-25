# Layouts research for ForgeGraph phase 7

Input for the phase 7 layout-spec proposal. Sources are numbered [S#] and listed at the end. Where a primary source could not be read (Science and Cell author pages return HTTP 403 to automated fetches), this is stated, and the claim is marked as coming from secondary sources only.

## 0. Short answer

- **Placement:** use a named-areas string, the convention shared by CSS `grid-template-areas` [S1], matplotlib `subplot_mosaic` [S2] and patchwork's `design` [S3]. Then a mapping of tiles keyed by those names, which matches ForgeGraph's "mappings keyed by name" rule (docs/decisions.md, phase 1). It is the most declarative of the models reviewed, it reads as a picture of the figure, and all three implementations agree on the rules: a name repeated over a rectangle spans it, `.` (or `#` in patchwork) is an empty cell, and a non-rectangular area is an error. matplotlib 3.11.2, the version in the repo's venv, raises `ValueError ... specifies a non-rectangular or non-contiguous area` (checked locally).
- **Alignment:** align the plot boxes, not the tiles' outer boxes. patchwork, egg, cowplot `align="hv"` and matplotlib constrained layout all do this [S3][S5][S6][S7]. Each grid column's left margin is the largest left room any tile starting in that column needs, and likewise for the other sides and for rows. ForgeGraph must implement this itself in the style of render/figure.py, because the project has ruled out matplotlib's layout engines: they space text by its box, not its letters (docs/decisions.md, phase 3).
- **Sharing:** borrow the `shared | independent` semantics of Vega-Lite's `resolve` [S8] and the `columns | rows | all` granularity of Plotly's `shared_xaxes` [S12]. When tiles share an axis, they get one range and one set of ticks, and only the outermost tile draws tick labels and the axis title, as patchwork's `axes = "collect"` does [S3][S4].
- **Panel labels** are set by the journal, and the conventions differ: Nature uses 8 pt bold lowercase a, b, c [S15]; PLOS gives "(A) or (a)" [S17]; Science and Cell are reported as using capitals (secondary sources only). So the label's style belongs in the **format**, and the layout only turns labels on and sets their order.
- **Size:** the layout's format sizes the whole figure and sets one base size for every tile. Journals require figures at final size, with text in a narrow range: Nature 5–7 pt [S15][S16], Elsevier 7 pt [S18], PLOS 8–12 pt [S17]. A tile's own format is replaced by the layout's format.

---

## 1. Declarative multi-panel layout models

| Model | How placement is given | Sizing | Sharing and legends | Panel labels | Fit for YAML |
| --- | --- | --- | --- | --- | --- |
| **patchwork** (R) | Operators `+ / \|` for composition, or `plot_layout(design=)` given as a text string or as `area()` calls [S3][S4] | `widths` and `heights` are relative sizes that apply only to the panel area; they can also be absolute units [S4] | `guides="collect"` gathers legends, `guide_area()` places them [S4]; `axes` and `axis_titles` collect duplicate axes in contiguous rows or columns [S3][S4] | `plot_annotation(tag_levels='a'\|'A'\|'1'\|'i'\|'I', tag_prefix, tag_suffix, tag_sep)`; nested levels [S19][S20] | Operators: no. The `design` string: yes |
| **cowplot** `plot_grid` | A list of plots with `ncol` and `nrow`; nest calls to get spans | `rel_widths`, `rel_heights` [S6] | `align = "none"\|"h"\|"v"\|"hv"`; `axis` takes any of l, r, t, b [S6]. Alignment is "independent of how they are arranged" [S7] | `labels="AUTO"` (upper case) or `"auto"`; default size 14, bold; `label_x=0`, `label_y=1`, i.e. the top left of each subplot [S6] | Simple, but spans need nesting |
| **egg** `ggarrange` | A list of plots | `set_panel_size` sets panel sizes in absolute units [S5] | Aligns panels by splitting each plot into a 3×3 layout and fixing the core cell [S5] | Has labels, not reviewed in detail | Same as cowplot |
| **Vega-Lite** | `hconcat`, `vconcat`, `concat` (wraps at `columns`), `facet`, `repeat` [S9][S10] | View `width`/`height`; `spacing` defaults to 20 px [S9] | `resolve: {scale\|axis\|legend: {channel: shared\|independent}}` [S8]. Facets share by default [S10]; concat keeps position scales independent and does not support shared axes [S9] | None built in | Very declarative, but nesting-heavy; there is no spanning |
| **Vega** layout | `align: all\|each\|none`, `bounds: full\|flush`, `columns`, `padding`, `center`, `offset`, `titleBand` [S11] | `align: each` gives a clean grid in which rows and columns can differ in size; `flush` sizes by the plot area only [S11] | — | — | Good vocabulary for alignment options |
| **matplotlib `subplot_mosaic`** | An ASCII-art string (rows separated by `;` or newlines), or nested lists for longer names; `.` is empty [S2][S21] | `width_ratios`, `height_ratios` [S21] | `sharex`/`sharey` apply to the whole mosaic; `per_subplot_kw` gives per-tile settings [S21] | None | **Excellent**, with one-character names |
| **GridSpec / constrained layout** | Index slices `gs[0, :]` | Ratios; margins are shared per row and column, so spines in a row or column align [S22] | `Figure.align_labels` aligns axis titles in the same row or column of one GridSpec [S23]; `supxlabel` adds a figure-wide x title [S24] | None | Not declarative (code) |
| **UltraPlot** (ProPlot's successor) | Arrays or GridSpec | Reference subplot `refwidth`/`refaspect` drive the figure size; `journal='nat1'` gives Nature's single-column width [S25] | Sharing levels 0–4 plus `'auto'`; `span` labels across a row or column [S25] | `abc` template, `abc.loc`, `abc.weight`, `abc.size` [S25] | Its ideas carry over: refaspect sizing, abc labels |
| **Plotly `make_subplots`** | `rows`, `cols`, `specs` with `rowspan`/`colspan`; `None` is empty [S12] | `column_widths`, `row_heights` [S12] | `shared_xaxes: True\|'columns'\|'rows'\|'all'` [S12] | `subplot_titles` only [S12] | Verbose: a span is described away from its picture |
| **Observable Plot facets** | `fx`/`fy` channels partition the data into small multiples [S26] | — | Facets of one plot | — | For small multiples from one dataset, not for compound figures |
| **CSS grid** | `grid-template-areas` strings, `.` for a null cell; areas must be rectangles or the declaration is invalid [S1] | `grid-template-columns`/`rows` | — | — | The web standard behind the named-areas idea |

**Which is simplest and most declarative for YAML?** The named-areas string. One YAML literal block (`|`, in which all line breaks are significant [S27]) draws the grid. Spans, empty cells and reading order can all be seen at a glance, and it is the same idea in three established tools [S1][S2][S3]. Two variants exist:

- **One character per cell** (matplotlib's string form [S2]): compact. But names can't be descriptive, which matters for dashboards (`throughput`, `queue`).
- **Space-separated names** (CSS [S1]): names can be any length. Recommended. Single letters still work for paper figures (`a b` / `c b`).

The alternatives cost more:

- Per-tile coordinates (Grafana's `gridPos {x, y, w, h}` [S13], Plotly's `rowspan`/`colspan` [S12]) put each span away from the picture of the figure and make overlaps possible.
- Nesting (Vega-Lite concat [S9], cowplot) makes even simple spans deep.

**Is subplot_mosaic-style ASCII art a good fit?** Yes, with three rules taken from the sources:

- A non-rectangular or non-contiguous area is an error [S1][S2][S3].
- A name in the grid that has no tile, or a tile that isn't in the grid, is an error. This follows the project's "error, don't fall back" rule.
- Nested layouts (patchwork, `subplot_mosaic`'s nested lists [S2]) are left out of v1. Spans cover the paper and dashboard deliverables.

## 2. Alignment

- **The problem.** Tiles with different tick-label widths get plot boxes of different widths and positions: "because the y axis labels have different lengths" [S7]. Similarly, `grid.arrange()` "makes no attempt at aligning the plot panels" [S5]. Wilke: "Misalignments are ugly and should be avoided" [S28].
- **The established solution.** Every system reviewed aligns the **panel areas** (plot boxes). Their methods:
  - **egg and gtable** set each plot's core cell, then combine the plots and take the largest widths with `unit.pmax` [S5].
  - **patchwork** sizes only the panel area: "sizing only affects the plotting region (_panel area_)" [S4].
  - **Constrained layout** gives each row shared top and bottom margins, and each column shared left and right margins, "widened until all the decorators in that row are accommodated" [S22].
  - **Vega's `align: each`** gives "a clean grid structure, but each row or column may be of variable size" [S11].
- **For ForgeGraph.** Generalise `render/figure.py`'s `layout()` from one Axes to a grid. For each tile, measure the room each side needs (left, right, bottom, top) exactly as now, to letters. Then:
  - each column's left margin = the largest left room among tiles whose **first** column it is; each column's right margin = the largest right room among tiles whose **last** column it is. Rows work the same way with top and bottom;
  - a spanning tile's plot box runs across the interior margins and gaps it covers. constrained layout makes the same choice and calls it deliberate [S22]. It means a spanning panel lines up with the outer edges of the panels beside it;
  - the iteration and the alternation guard stay as they are (6 passes, then the largest room either of the last two passes needed), because larger plot boxes still change tick labels;
  - **axis titles align too.** A y-axis title sits at the column's outer edge rather than a fixed gap from that tile's tick labels, which is what matplotlib's `align_ylabels` does [S23]. In the tile with narrower labels, the gap grows.
- **Shared axes.**
  - Tiles that share an axis get one range (the union of their limits) and one set of ticks, as Vega-Lite's shared scales do [S8].
  - Only the bottom tile of a column (for x) or the left tile of a row (for y) draws tick labels and the axis title, as patchwork's `axes = "collect"` and matplotlib's `sharex` do [S3][S21]. The tick marks stay.
  - The gap between tiles that share an axis can shrink, since there are no labels to clear.
  - With x shared, one figure-wide title (like `supxlabel` [S24]) is only right when a whole row of columns shares; a per-column title on the bottom tile is the general case.
- **Shared legends.**
  - `guides = "collect"` hoists identical legends into one; `guide_area()` gives them a place [S4].
  - Wilke: one consistent visual language means "we need only a single legend" [S28].
  - That requires the same group to get the same color in every tile. So with collection on, the layout must give each group one color, from the union of every tile's groups in order. Today each GraphSpec assigns colors on its own.
  - Recommendation: a reserved area name `legend` in the grid, which works like `guide_area()`.
- **Consistent text.**
  - One format means one base size, so every tile's text is the same size, which is the "visual language" point [S28].
  - Journals require final size: Nature asks for all fonts between 5 and 7 pt [S15][S16]; Elsevier's rule of thumb is 7 pt [S18]; PLOS allows 8–12 pt [S17].
  - The layout must never scale a tile down, which would shrink its text. Tiles are drawn at the layout's base size into the space their cell gives.

## 3. Panel labels

| Source | Style | Size | Placement |
| --- | --- | --- | --- |
| Nature | "8-pt bold, upright (not italic) and lowercase a, b, c" [S15] | 8 pt, while other text is 5–7 pt [S15] | Not specified on the guide page; panels in alphabetical order [S16] |
| PLOS | "(A) or (a)", "a lettered panel label" [S17] | Text 8–12 pt [S17] | Not specified |
| Science | Bold capitals, per secondary sources [S29]; the primary page returned 403 | — | — |
| Cell Press | Upper case, "(A), (B), (C) or A, B, C in top-left", per secondary summaries [S30]; the primary page returned 403 | — | Top left [S30] |
| cowplot | `"AUTO"` or `"auto"`, bold, 14 pt default | — | `label_x=0, label_y=1`: the top left of the whole subplot, not of its panel [S6] |
| patchwork | `tag_levels`, plus prefix and suffix, e.g. `(` `)` [S19] | Set with the theme's `plot.tag` | By default the tag gets its own row and column at the top left; `plot.tag.position` can overlay it instead [S20] |
| UltraPlot | `abc='A.'` template | `abc.size`, `abc.weight` | `abc.loc`, with automatic offset from titles [S25] |
| Wilke | Understated: "The labels should not be the first thing you see" [S28] | Not large or heavy | Consistent across a document [S28] |

**Recommendation.**

- **Placement:** the top-left corner of the tile's **cell**, outside the axes, with the label's left edge at the column's outer edge (left of the y-axis title). Labels then line up down a column whatever the tick labels, which is what patchwork's own tag row and column achieves [S20]. The label's cap height lines up with the top of the tile's title, or with the top of what's drawn above the plot box if there is no title. That is measured to letters, as ForgeGraph already does.
- **Order:** reading order of each tile's top-left cell, which is alphabetical as Nature asks [S16]. A tile can override its label text, for example to continue from a previous figure. Text tiles and the legend area get no label.
- **Style in the format:** case (lower, upper), weight, size (× base size; Nature's 8 pt over a 7 pt base is about 1.15), and brackets (none, or `()`).

## 4. Dashboards and HTML output

- **Grids in dashboard tools.**
  - Grafana divides the width into 24 columns, with rows 30 px high [S13].
  - Bootstrap uses "a twelve column system" with responsive breakpoints [S14].
  - Tableau has tiled items ("a single-layer grid") and floating ones, and fixed, range or automatic dashboard sizes. Fixed "remains the same size, regardless of the size of the window" [S31].
  - Quarto dashboards build rows and columns from headings with relative `height`/`width` attributes, and `fill` or `flow` rows [S32].
  - Evidence has `<Grid cols=N>`, which stacks vertically on small screens [S33].
  - Datawrapper has no dashboard feature; its small multiples set separate desktop and mobile layouts [S34].
- **For ForgeGraph.** The named-areas grid already covers what these tools do: any number of columns, spans and empty cells. A 12- or 24-column convention is only needed for drag-and-drop editors, so it matters for Studio later, not for the YAML. ForgeGraph's HTML is Tableau's **fixed** size, the trade-off D11 already accepts: no reflow on phones.
- **SVG in the page.**
  - Inline `<svg>` "saves an HTTP request" and can be styled and scripted. `<img>` can't be manipulated with JavaScript but can be cached [S35]. Inline suits a single-file page, and the stale banner script can sit beside it.
  - matplotlib's default `svg.fonttype: path` draws text as outlines, so the page looks the same on every machine. `none` keeps text as text, but "the appearance may vary based on the SVG viewer and what fonts are available" [S36].
  - ForgeGraph lays text out to Roboto's letters, so a fallback font would break the spacing. Either keep `path`, or embed Roboto in the page with `@font-face` (the SIL Open Font License allows that). An owner decision (§6).
  - Give the SVG its natural width plus `max-width: 100%; height: auto`. Then it shrinks to fit a narrow window without reflowing.
- **"Data as of".**
  - D12 already settles this: the stamp is in the image, taken from the Parquet file's modification time, and the HTML shows a stale banner.
  - The tools reviewed differ. Looker Studio shows "Last updated" small at the bottom left, and a forum answer recommends showing the data's latest timestamp rather than the time the page was rendered [S37].
  - With several data files in a layout, the stamp should be the **oldest** of them, so the page never looks fresher than its stalest tile. An owner decision.
  - Place the stamp in the layout's footer, at the base size, unobtrusive.
- **Provenance:** per D13, the page carries it in `<script type="application/json">`, and the SVG carries the Dublin Core description.

## 5. Recommended layout spec

The spec follows the four-default-file convention: four-space indents and `name: default          # [RANGE]; DESCRIPTION`. The parameter names are proposals.

### 5.1 What goes where

| Where | Parameters | Why |
| --- | --- | --- |
| **Format** (destination) | `figure.width`, `figure.height`, `figure.base_size`, `output.dpi` (as now); new: `panel_label.case`, `.weight`, `.size`, `.brackets`; `output.file_types` gains `html` (layouts only) | Journals set sizes and label conventions [S15][S17]. One layout can be re-rendered for another journal by changing only its format |
| **Theme** (look) | New: `layout.gap` (between tiles, × base size), `layout.shared_gap` (between tiles that share an axis), `text_tile.size`, `.weight`, `.align`, `stamp.size`, `stamp.color` | Spacing and type are house style |
| **Layout** (this figure) | Theme and format names; title; `grid.areas`, `column_widths`, `row_heights`; `tiles`; `axis.x.shared`, `axis.y.shared`; `legend.collect`; `panel_label.show`, `.start`; output file types | What's arranged and how it's shared |
| **Tile GraphSpec** | Everything about the graph. Its theme and format are **replaced** by the layout's, and `forgegraph explain` shows the origin as "layout" | One visual language and one text size [S28] |

**Sizing.**

- The format's width is the whole figure (e.g. Nature double column, 183 mm [S16]; Elsevier full width, 190 mm [S18]).
- With `figure.height: auto`, the height is fitted so that a plot box of column-width ratio 1 and row-height ratio 1 has the theme's `plot_area.aspect`. That is UltraPlot's `refaspect` idea [S25] and today's single-graph rule generalised.
- With both width and height given, the plot boxes take the space left, split by the ratios.
- `row_heights` may be `auto` for a row that holds only text tiles or the legend. Such a row is sized to its content, like Quarto's `flow` [S32].
- `column_widths` and `row_heights` size the **plot boxes**, not the cells, as patchwork's do [S4]. Aligned panels then come out in exactly the ratios given.

### 5.2 Default file (sketch)

```yaml
name: default          # [text]; The name of the layout.
version: 0          # [int]; The version number of the specification.
description: The base layout that others can inherit from.          # [text]; The description of the layout.
extends: None          # [None, layout]; Each parameter not listed is inherited from this layout. If None, this file must list every parameter.

fixed_parameters: None          # List of fixed parameters for the layout, None if none.

variable_parameters:          # List of variable parameters for the layout, None if none.
    specifications:
        theme: default          # [theme]; Theme for the whole figure; it replaces each tile's theme.
        format: default          # [format]; Format for the whole figure (size, base size, panel-label style); it replaces each tile's format.
    text:
        title: None          # [None, text]; Title over the whole layout. None: none.
    grid:
        areas: a          # [text]; One line per row and one name per cell, separated by spaces. A name repeated over a rectangle spans it; . is an empty cell; legend is where a collected legend goes.
        column_widths: None          # [None, positive floats]; Relative widths of each column's plot boxes. None: equal.
        row_heights: None          # [None, positive floats or auto]; Relative heights of each row's plot boxes; auto: sized to the row's text. None: equal.
    tiles:          # One entry per name in grid.areas.
        a:
            graph: None          # [None, text]; GraphSpec file drawn in this tile: an absolute path, one starting with ~, or one relative to this file's folder. Set graph or text.
            text: None          # [None, text]; Text drawn in this tile, with ForgeGraph's label markup. Set graph or text.
            panel_label: auto          # [auto, None, text]; This tile's panel label. auto: next in reading order. None: none.
    axis:
        x:
            shared: none          # [none, columns, rows, all]; Tiles sharing the x axis: one range and ticks; tick labels and title only on the bottom tile of each column.
        y:
            shared: none          # [none, columns, rows, all]; Tiles sharing the y axis: one range and ticks; tick labels and title only on the left tile of each row.
    legend:
        collect: false          # [true, false]; Draw identical legends once, in the legend area, with one color per group across tiles.
    panel_label:
        show: false          # [true, false]; Label each graph tile, in the format's panel-label style.
        start: 1          # [positive int]; Position of the first label: 1 is a (or A).
    output:
        file_types: [png]          # [png, pdf, svg, html]; File types saved. html: the figure as SVG in a page with the data-as-of stamp.
```

### 5.3 Paper figure: 2×2 grid with one spanning panel, labels, shared x

Tiles a and c share a time axis, one above the other; b spans both rows.

```yaml
name: cell_performance
version: 0
description: Voltage and current over time, and the polarization curves, for cells A–C.
extends: default

fixed_parameters: None

variable_parameters:
    specifications:
        format: nature-double          # 183 mm wide, height auto, base size 7 pt, labels 8 pt bold lowercase
    grid:
        areas: |
            a       b
            c       b
            legend  legend
        column_widths: [1, 1.3]
        row_heights: [1, 1, auto]
    tiles:
        a:
            graph: graphs/voltage_time.graph.yaml
        b:
            graph: graphs/polarization.graph.yaml
        c:
            graph: graphs/current_time.graph.yaml
    axis:
        x:
            shared: columns          # a and c: one time axis; tick labels and title on c only
    legend:
        collect: true          # one key for cells A–C under the figure
    panel_label:
        show: true          # a, b, c in reading order
    output:
        file_types: [pdf, png]
```

### 5.4 Ops dashboard with text tiles

```yaml
name: lab_throughput
version: 0
description: Daily operations view of lab throughput and queues.
extends: default

fixed_parameters: None

variable_parameters:
    specifications:
        format: dashboard          # e.g. 420 mm (≈1600 px) wide, height auto, larger base size
    text:
        title: Lab throughput
    grid:
        areas: |
            weekly    weekly    queue
            failures  uptime    notes
        column_widths: [1, 1, 1]
        row_heights: [1.2, 1]
    tiles:
        weekly:
            graph: throughput_weekly.graph.yaml
        queue:
            graph: queue_by_instrument.graph.yaml
        failures:
            graph: failures_daily.graph.yaml
        uptime:
            graph: uptime_daily.graph.yaml
        notes:
            text: "Updated daily 06:00. Owner: ops team. Targets: ≥ 95 % uptime."
    axis:
        x:
            shared: rows          # failures and uptime: one date axis
    output:
        file_types: [png, html]          # the html page carries the data-as-of stamp (oldest data file) and the stale banner
```

**How tiles are referenced.**

- Recommended: by path (`graph:`), using the same path rule as `data.file`. The GraphSpec stays the one source for that graph and stays usable on its own, the agent can iterate on one tile with `forgegraph render tile.graph.yaml`, and each data file is read once per render however many tiles name it.
- Inline GraphSpecs make the layout self-contained but duplicate content. If wanted, an inline tile could be a GraphSpec body with `extends: path`, which reuses the existing `extends` mechanism instead of adding a second override syntax. matplotlib's `per_subplot_kw` is the analogue [S21].

## 6. Questions only the owner can decide

1. **Theme and format of tiles.** Should a tile's own theme and format be silently replaced by the layout's (recommended, shown by `explain`), or should a tile that names a different theme be an error?
2. **Per-tile overrides.** Should a tile be able to override its GraphSpec's variable parameters inside the layout (e.g. hide its title), or must every change go into the GraphSpec file?
3. **Inline GraphSpecs.** Allowed in v1 (via `extends:`), or path only?
4. **Panel-label style: format or theme?** The research favours the format, because journals specify it. What are the defaults: Nature-style bold lowercase, or capitals?
5. **Panel-label anchor.** Top-left of the cell, outside the axis titles (recommended), or overlaid at the plot box's corner (patchwork's overlay option [S20])?
6. **Shared legend.** Is a reserved `legend` area name acceptable, and should the layout force one color per group across tiles even when `legend.collect` is false? Consistency argues yes [S28].
7. **Axis titles with shared x.** One title per column on the bottom tile (recommended), or one figure-wide title when every column shares?
8. **Nested layouts** (a sub-grid inside a cell): leave them out of v1?
9. **HTML text.** Text drawn as outlines (exact, larger, not selectable) or Roboto embedded with `@font-face` (smaller, selectable)?
10. **Freshness stamp with several data files.** Oldest modification time (recommended), or one stamp per tile? And should the dashboard page reload itself on a timer for wall displays?
11. **Text tiles.** Plain text with label markup only, or also headings and big-number "KPI" tiles? Neither deliverable strictly needs KPI tiles, but ops dashboards commonly have them.
12. **Dashboard format.** Is a built-in `dashboard` format wanted (its width, base size and screen dpi), or does each organisation supply its own?
13. **Lint.** Should layouts lint against the format's minimum text size at final size (e.g. 5 pt for Nature [S15])? That would add a format parameter.

---

## Sources

- [S1] MDN, `grid-template-areas`: https://developer.mozilla.org/en-US/docs/Web/CSS/grid-template-areas
- [S2] matplotlib, Complex and semantic figure composition (subplot_mosaic): https://matplotlib.org/stable/users/explain/axes/mosaic.html
- [S3] patchwork, `plot_layout()` reference: https://patchwork.data-imaginist.com/reference/plot_layout.html
- [S4] patchwork, Controlling Layouts guide: https://patchwork.data-imaginist.com/articles/guides/layout.html
- [S5] egg, Overview vignette and Ecosystem vignette (gtable alignment): https://cran.r-project.org/web/packages/egg/vignettes/Overview.html , https://cran.r-project.org/web/packages/egg/vignettes/Ecosystem.html
- [S6] cowplot, `plot_grid()` reference: https://wilkelab.org/cowplot/reference/plot_grid.html
- [S7] cowplot, Aligning plots: https://wilkelab.org/cowplot/articles/aligning_plots.html
- [S8] Vega-Lite, Scale and guide resolution: https://vega.github.io/vega-lite/docs/resolve.html
- [S9] Vega-Lite, Concatenating views: https://vega.github.io/vega-lite/docs/concat.html
- [S10] Vega-Lite, Faceting: https://vega.github.io/vega-lite/docs/facet.html
- [S11] Vega, Layout: https://vega.github.io/vega/docs/layout/
- [S12] Plotly, Subplots in Python: https://plotly.com/python/subplots/
- [S13] Grafana, Dashboard JSON model (`gridPos`): https://grafana.com/docs/grafana/latest/dashboards/build-dashboards/view-dashboard-json-model/
- [S14] Bootstrap 5.3, Grid system: https://getbootstrap.com/docs/5.3/layout/grid/
- [S15] Nature Research Figure Guide, Preparing figures, our specifications: https://research-figure-guide.nature.com/figures/preparing-figures-our-specifications/
- [S16] Nature Research Figure Guide, Building and exporting figure panels: https://research-figure-guide.nature.com/figures/building-and-exporting-figure-panels/
- [S17] PLOS ONE, Figures: https://journals.plos.org/plosone/s/figures
- [S18] Elsevier, Artwork sizing: https://www.elsevier.com/authors/policies-and-guidelines/artwork-and-media-instructions/artwork-sizing
- [S19] patchwork, `plot_annotation()` reference: https://patchwork.data-imaginist.com/reference/plot_annotation.html
- [S20] patchwork, Adding Annotation and Style guide: https://patchwork.data-imaginist.com/articles/guides/annotation.html
- [S21] matplotlib, `Figure.subplot_mosaic` API: https://matplotlib.org/stable/api/_as_gen/matplotlib.figure.Figure.subplot_mosaic.html
- [S22] matplotlib, Constrained layout guide: https://matplotlib.org/stable/users/explain/axes/constrainedlayout_guide.html
- [S23] matplotlib, `Figure.align_labels`: https://matplotlib.org/stable/api/_as_gen/matplotlib.figure.Figure.align_labels.html
- [S24] matplotlib, `Figure.supxlabel`: https://matplotlib.org/stable/api/_as_gen/matplotlib.figure.Figure.supxlabel.html
- [S25] UltraPlot, Subplots: https://ultraplot.readthedocs.io/en/latest/subplots.html
- [S26] Observable Plot, Facets (doc source): https://observablehq.com/plot/features/facets , https://github.com/observablehq/plot/blob/main/docs/features/facets.md
- [S27] YAML 1.2.2 specification (literal style): https://yaml.org/spec/1.2.2/
- [S28] C. O. Wilke, Fundamentals of Data Visualization, ch. 21 Multi-panel figures: https://clauswilke.com/dataviz/multi-panel-figures.html
- [S29] Secondary only, since science.org returned 403: Editage, How to create figures for a research paper: https://www.editage.com/blog/figures-research-paper/ ; primary to check: https://www.science.org/content/page/instructions-preparing-initial-manuscript
- [S30] Secondary only, since cell.com returned 403: conceptviz, How to make figures for Nature, Science and Cell: https://conceptviz.app/blog/how-to-make-figures-for-nature-science-journals ; primary to check: https://www.cell.com/information-for-authors/figure-guidelines
- [S31] Tableau, Size and lay out your dashboard (tiled and floating): https://help.tableau.com/current/pro/desktop/en-us/dashboards_organize_floatingandtiled.htm
- [S32] Quarto, Dashboard layout: https://quarto.org/docs/dashboards/layout.html
- [S33] Evidence, Grid component: https://docs.evidence.dev/components/grid/
- [S34] Datawrapper, Multiple lines (small multiples): https://datawrapper.de/charts/multiple-lines
- [S35] MDN, Including vector graphics in HTML: https://developer.mozilla.org/en-US/docs/Learn_web_development/Core/Structuring_content/Including_vector_graphics_in_HTML
- [S36] matplotlib, Fonts in Matplotlib (`svg.fonttype`): https://matplotlib.org/stable/users/explain/text/fonts.html
- [S37] Google Developers forum, How to add "Data last updated" in a Looker Studio report: https://discuss.google.dev/t/how-to-add-data-last-updated-in-the-looker-studio-report/165234
