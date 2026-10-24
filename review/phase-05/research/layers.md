# Layers for ForgeGraph: research for the phase 5 layer spec

Scope: how established tools model layers, reference lines, notes and error bars; what the literature says about error bars; a recommended layer spec in ForgeGraph's style that also takes the phase 9 layers; and the questions only the owner can decide. Every claim about another tool or paper carries its source.

## 0. What the repo already fixes

- A layer is "an optional addition that compatible charts accept", with the same structure as a graph type, defined by its own YAML file beside its drawing code, core only, never in packs (architecture.md §2, D4, D5; principle 3).
- Things drawn on the graph, including things computed from its data (error bars, a reference line at the mean, a fitted curve), are layers, not graph-type parameters (D5; decisions.md, "Specification review, round 1").
- Error-bar look stays in the theme's `error_bar` category (`cap_size: 0.25`, `line_width: 0.08`, both × base size, fixed) (decisions.md round 1; themes/default.yaml).
- In a GraphSpec, `layers` is a list; each item starts `-   type: note`, with content four spaces after the dash (decisions.md, "YAML layout").
- Resolve: `layers` **append** across extends/presets; everything else replaces (architecture.md §3).
- Phase 9 annotation layers (`arrow`, `brace`, `ellipse`, `text`, `delta`) are "anchored in data coordinates"; the agent chooses what and where, lint checks overlaps (architecture.md §5).
- Invalid requests are errors, never silent substitutes (decisions.md, phase 2).

Two small inconsistencies to settle while writing the spec:
- decisions.md round 1 still says "Each axis names its data column and error column", but xy.yaml has no error column and the same entry makes error bars a layer. The layer replaces the axis error column.
- architecture.md puts layers at `src/forgegraph/layers/<name>/layer.yaml`, but graph types are now flat files (`graph_types/xy.yaml`). Its GraphSpec example uses flow style (`- {type: reference_line, y: 1.0, label: ...}`), which the YAML-layout decision no longer allows for multi-key items.

## 1. How grammar-of-graphics tools model layers

### Vega-Lite
- **Layer:** a view whose `layer` property is an array of unit (single-mark) or layered specs drawn on top of each other; data and `encoding` may be shared at the top and inherited; scales, axes and legends are shared by default, and their domains are unioned ([layer](https://vega.github.io/vega-lite/docs/layer.html)).
- **Reference line = `rule` mark.** With only `y` it is horizontal and spans the full width; with only `x` it is vertical; `x`+`x2` or `y`+`y2` makes a ranged rule ([rule](https://vega.github.io/vega-lite/docs/rule.html)).
  - Fixed value: `"encoding": {"y": {"datum": 300}}`, with `strokeDash: [2, 2]` in the mark ([datum](https://vega.github.io/vega-lite/docs/datum.html); [example layer_line_datum_rule](https://github.com/vega/vega-lite/blob/main/examples/specs/layer_line_datum_rule.vl.json)).
  - At a statistic: `"y": {"aggregate": "mean", "field": "precipitation"}` on a rule layered over bars ([layer_precipitation_mean](https://github.com/vega/vega-lite/blob/main/examples/specs/layer_precipitation_mean.vl.json); aggregate ops include mean, median, min, max, q1, q3, stdev, stderr, ci0, ci1: [aggregate](https://vega.github.io/vega-lite/docs/aggregate.html)).
  - Labelled: a nested layer sharing `y: {datum: 300}`, holding a `rule` and a `text` mark with `align: right`, `baseline: bottom`, `dx: -2`, `dy: -2`, `x: "width"`, i.e. text at the right end, just above the line ([layer_bar_annotations](https://github.com/vega/vega-lite/blob/main/examples/specs/layer_bar_annotations.vl.json)).
- **Error bars = `errorbar` composite mark**, which expands into rules plus optional end `ticks` (caps); `size` sets tick size and `thickness` the line ([errorbar](https://vega.github.io/vega-lite/docs/errorbar.html); [errorbar.ts](https://github.com/vega/vega-lite/blob/main/src/compositemark/errorbar.ts)).
  - Computed from raw rows: `extent` is `stderr` (default), `stdev`, `ci` (95% **bootstrapped** CI of the mean) or `iqr` (q1 to q3) (same pages).
  - Pre-computed, two ways: ends as `y` + `y2` (absolute low/high), or centre `y` + `yError` (+ `yError2`). Without `yError2` the bars are symmetric; for asymmetric, one of `yError`/`yError2` is positive and the other negative ([errorbar](https://vega.github.io/vega-lite/docs/errorbar.html); examples [symmetric](https://github.com/vega/vega-lite/blob/main/examples/specs/layer_point_errorbar_pre_aggregated_symmetric_error.vl.json), [asymmetric](https://github.com/vega/vega-lite/blob/main/examples/specs/layer_point_errorbar_pre_aggregated_asymmetric_error.vl.json) with data like `yield_error: 7.55, yield_error2: -10.55`, [upper/lower](https://github.com/vega/vega-lite/blob/main/examples/specs/layer_point_errorbar_pre_aggregated_upper_lower.vl.json)).
  - `errorband` is the continuous counterpart, a filled band plus optional `borders`, with the same `extent` and pre-computed forms ([errorband](https://vega.github.io/vega-lite/docs/errorband.html)).
- **Notes = `text` mark:** `align` (left/center/right), `baseline` (alphabetic, top, middle, bottom…), `dx`/`dy` pixel offsets, `angle`, `limit` ([text](https://vega.github.io/vega-lite/docs/text.html)). Position is data (`field`/`datum`) or pixels (`value`, e.g. `x: "width"`), as in the annotation example above.
- **Overlap:** Vega (not Vega-Lite) has a `label` transform that tries a list of `anchor` directions and `avoidMarks` so that labels overlap neither each other nor chosen marks ([label transform](https://vega.github.io/vega/docs/transforms/label/)).

### ggplot2
- A plot is a sum of layers; each geom is one layer.
- **Reference lines:** `geom_hline(yintercept)`, `geom_vline(xintercept)`, `geom_abline(slope, intercept)` ([geom_abline](https://ggplot2.tidyverse.org/reference/geom_abline.html)).
  - They don't inherit the plot's aesthetics (`inherit.aes = FALSE`).
  - Values given as arguments draw the same line in every facet. For a line per facet, such as a mean, "construct the data frame yourself" (the docs' example is `geom_hline(aes(yintercept = wt), mean_wt)`).
  - They "do not affect the x and y scales": a line outside the data range is simply not visible (same page).
- **Error bars:** `geom_errorbar`, `geom_linerange`, `geom_pointrange` and `geom_crossbar` need `ymin`/`ymax` (or `xmin`/`xmax`), i.e. the **absolute ends** of each bar. `orientation` is guessed from the mappings ([geom_linerange](https://ggplot2.tidyverse.org/reference/geom_linerange.html)). Cap `width` defaults to 0.9 of the data's resolution (the spacing between x values) ([geom-errorbar.R](https://github.com/tidyverse/ggplot2/blob/main/R/geom-errorbar.R)).
- **Notes:** `annotate(geom, x, y, xmin, …, label)` adds a layer from fixed values instead of mapped columns; its position values expand the plot limits ([annotate](https://ggplot2.tidyverse.org/reference/annotate.html)). Placement tools ([ggplot2 book, Annotations](https://ggplot2-book.org/annotations.html)):
  - `-Inf`/`Inf` place text at the panel edges;
  - `hjust`/`vjust = "inward"` keep text inside the plot;
  - `nudge_x`/`nudge_y` offset it;
  - `check_overlap` drops text that would overlap;
  - `geom_label` draws a box behind it;
  - ggrepel repels labels from each other and from points.

### matplotlib (ForgeGraph's renderer)
- **Reference lines:** `axhline(y, xmin, xmax)`. `y` is in data coordinates; `xmin`/`xmax` are axes fractions (0–1), so the line spans the plot whatever the x range. `axhspan` and `axline` draw spans and sloped lines ([axhline](https://matplotlib.org/stable/api/_as_gen/matplotlib.axes.Axes.axhline.html)). Because `y` is data, the line takes part in y autoscaling (inferred from the transform; the page doesn't state it, so check against the source).
- **Error bars:** `errorbar(x, y, yerr, xerr)` ([errorbar](https://matplotlib.org/stable/api/_as_gen/matplotlib.axes.Axes.errorbar.html)):
  - `yerr` is a scalar, shape (N,) for symmetric, or shape (2, N) for asymmetric (first row lower, second row upper). All values must be ≥ 0, i.e. **distances from the value**, not ends.
  - `capsize` is in points; the default `rcParams["errorbar.capsize"]` is 0, so no caps.
  - `elinewidth`, `capthick` and `ecolor` (defaults to the line's color) set the look.
  - `barsabove=False` by default: the bars are drawn **below** the markers.
  - `errorevery` thins the bars when series share x values; `lolims`/`uplims` mark limits.
- **Notes:** `annotate(text, xy, xytext, xycoords, textcoords, arrowprops)` ([annotate](https://matplotlib.org/stable/api/_as_gen/matplotlib.axes.Axes.annotate.html)):
  - `xycoords` is `'data'` (the default), `'axes fraction'`, figure units, or a tuple blending x and y systems;
  - `textcoords` adds `'offset points'` and `'offset fontsize'`;
  - `arrowprops` draws an arrow from the text to the point, which is the basis for phase 9's arrow callout;
  - `annotation_clip` hides data-anchored text whose point is outside the axes.

### Plotly
- **Error bars:** `error_y = {type: 'data', array, arrayminus, symmetric}`. `array` and `arrayminus` are **distances** above and below; `type` can also be `percent`, `constant` or `sqrt`. Plotly Express takes `error_y` and `error_y_minus` as column names ([error bars](https://plotly.com/python/error-bars/)). Cap `width` is in px and defaults to 4; `thickness` defaults to 2 px ([attributes.js](https://github.com/plotly/plotly.js/blob/master/src/components/errorbars/attributes.js), [defaults.js](https://github.com/plotly/plotly.js/blob/master/src/components/errorbars/defaults.js)).
- **Reference lines and regions:** layout `shapes` of `type` line, rect, circle or path, with `x0/x1/y0/y1` and `xref`/`yref` set to an axis (data), `paper` (0–1 of the plot) or `x domain` ([shapes](https://plotly.com/python/reference/layout/shapes/)):
  - `layer` is `below`, `between` (gridlines and traces) or `above` (the default);
  - `line.dash` sets the dash; a `label` with `textposition` start, middle or end labels a line.
  - Helpers: `add_hline(y, line_dash, annotation_text, annotation_position="bottom right")`, `add_hrect`, `add_vrect` ([horizontal and vertical shapes](https://plotly.com/python/horizontal-vertical-shapes/)).
- **Notes:** layout `annotations` have `x`, `y`, `xref`/`yref` (axis or `paper`), `xanchor`/`yanchor` (default `auto`), `xshift`/`yshift` in px, and `showarrow` with `ax`/`ay` for the arrow tail ([annotations](https://plotly.com/python/reference/layout/annotations/)).

### Datawrapper and Flourish
- **Datawrapper:** "Highlight range" draws either a line (one value) or a range (two values) on an axis ([range highlights and lines](https://www.datawrapper.de/academy/range-highlights-and-lines)).
  - Lines: width 1–3 px, solid, dotted or dashed. Ranges: light, desaturated fills.
  - Layering is fixed: ranges sit behind data and gridlines, lines above them, and text annotations on top of everything.
  - Highlights can repeat in every panel or apply to one.
  - Text annotations can be moved and given arrows or circles. A text outline keeps them readable over data, and on mobile they become a numbered key below the chart ([responsive annotations](https://www.datawrapper.de/blog/better-more-responsive-annotations-in-Datawrapper-data-visualizations/)).
  - In bar charts each annotation is tied to a data row ([annotations in bar charts](https://www.datawrapper.de/blog/annotations-in-bar-charts)).
- **Flourish:** annotations are anchored to x and y axis values, not screen positions, so they stay on the right point when the chart is resized ([introducing annotations](https://flourish.studio/2020/11/17/introducing-annotations/)).

### What they share: the minimal declarative model
Every tool reduces a layer to **a type (mark) + geometry bound to data or to fixed values + a few look properties**. They differ only in where geometry comes from:

| Geometry source | Vega-Lite | ggplot2 | matplotlib | Plotly |
| --- | --- | --- | --- | --- |
| fixed data value | `datum` | argument (`yintercept=1`) | `axhline(y)` | `shapes` with `yref: y` |
| statistic of a column | `aggregate: mean` | you compute a data frame | you compute | you compute |
| per-row columns | `field` (`y2`, `yError`) | `aes(ymin, ymax)` | arrays | `array`/`arrayminus` |
| plot-relative position | `value` (px), `"width"` | `-Inf`/`Inf` | `axes fraction` | `paper` |

A GraphSpec `layers:` list whose items each have `type:` plus parameters is exactly the Vega-Lite `layer` array, restricted to fixed layer types. Vega-Lite's per-layer `data` and `encoding` are replaced by explicit column parameters on the layer.

## 2. Error bars: published practice

- **Say what they are.** "Rule 1: when showing error bars, always describe in the figure legends what they are", and Rule 2 says to state n (Cumming, Fidler & Vaux 2007, *J Cell Biol* 177:7–11, [doi:10.1083/jcb.200611141](https://doi.org/10.1083/jcb.200611141); full text [Europe PMC PMC2064100](https://europepmc.org/article/PMC/PMC2064100)).
  - In 2012 Nature Methods papers, 45% of error bars were s.d., 49% s.e.m., 5% unstated, and only one figure used 95% CI. The authors' first step is "to be clear about which measure of uncertainty is being represented" (Krzywinski & Altman 2013, *Nat Methods* 10:921–922, [doi:10.1038/nmeth.2659](https://doi.org/10.1038/nmeth.2659)).
  - Nature Portfolio's Reporting Summary requires, in the figure legend, table legend, main text or Methods, the exact n per group, "central tendency (e.g. means)… AND variation (e.g. standard deviation) or associated estimates of uncertainty (e.g. confidence intervals)" ([Reporting Summary](https://www.nature.com/documents/nr-reporting-summary-flat.pdf)).
  - Cumming & Finch's seven "rules of eye" begin: seek bars that relate directly to the effects of interest, be sensitive to experimental design, and interpret the intervals (Cumming & Finch 2005, *Am Psychol* 60:170–180, [doi:10.1037/0003-066X.60.2.170](https://doi.org/10.1037/0003-066X.60.2.170)).
- **SD vs SEM vs CI** (Krzywinski & Altman 2013; Cumming et al. 2007):
  - SD is descriptive: it shows the spread of the data and predicts the range of new samples.
  - SEM = SD/√n is inferential and shrinks with n. When SEM bars just touch, P ≈ 0.17 (n = 10).
  - A 95% CI is about 2 × SEM for n > 15 and about 4 × SEM for n = 3. 95% CI bars can overlap by up to about half an arm and still give P < 0.05; when they just touch, P ≈ 0.005.
  - Comparing with controls usually calls for SE or CI (Rule 4). Researchers misread these thresholds widely (Belia et al. 2005, *Psychol Methods* 10:389, [doi:10.1037/1082-989X.10.4.389](https://doi.org/10.1037/1082-989X.10.4.389)).
- **Small n and replicates.**
  - Show error bars only for independently repeated experiments, never for technical replicates (Rule 3).
  - At n = 3, plot the individual points rather than bars (Rule 4; Krzywinski & Altman).
  - Bar charts of means with error bars hide the distribution: Weissgerber et al. 2015, *PLOS Biol* 13:e1002128, [doi:10.1371/journal.pbio.1002128](https://doi.org/10.1371/journal.pbio.1002128). They also cause the within-the-bar bias, which Correll & Gleicher tested alternatives to (2014, *IEEE TVCG* 20:2142–2151, [doi:10.1109/TVCG.2014.2346298](https://doi.org/10.1109/TVCG.2014.2346298)).
  - This is skill and lint guidance for ForgeGraph, not a renderer rule.
- **Asymmetric errors.** All four tools support them: matplotlib (2, N), Plotly `arrayminus`, Vega-Lite `yError2`, ggplot2 `ymin`/`ymax`. They arise naturally from CIs of ratios or log-scale quantities and from percentile intervals. A symmetric ± bar on a log axis can reach ≤ 0. By ForgeGraph's error rule that should stop the render with a message, not be clipped. (The log-axis point is reasoning, not from a source.)
- **Caps.** No published standard was found. Tool defaults disagree:
  - matplotlib: no caps (`capsize` 0);
  - Vega-Lite: no ticks unless `ticks: true`;
  - Plotly: 4 px;
  - ggplot2: 0.9 × data resolution (a fraction of category spacing).
  ForgeGraph's theme `cap_size` × base size is a reasonable house choice. It should be absolute (× base size, as now), not a fraction of the bar width, so caps match across xy and bar.
- **Drawing order.** matplotlib draws bars below markers by default (`barsabove=False`). On bar charts the error bar has to sit on top of the bar fill to be seen.

## 3. Reference lines

- **Fixed and statistic.** Every tool has a fixed value (`datum`, `yintercept`, `axhline(y)`, `add_hline(y)`). Only Vega-Lite computes a statistic inside the spec (`aggregate: mean | median | …`). ggplot2 shows that per-group lines (one mean per facet or series) are the common next need.
  - The build plan's wording, "reference lines (fixed, or at a statistic such as the mean)", fits a small fixed set: mean, median, min, max. These are the only statistics ForgeGraph would compute, and over the rows as drawn.
  - A target is just a fixed value with a label.
- **Labelling.**
  - Vega-Lite's own annotation example puts the label at the right end, just above the line (`align: right`, `baseline: bottom`, `x: width`, small `dx`/`dy`) ([layer_bar_annotations](https://github.com/vega/vega-lite/blob/main/examples/specs/layer_bar_annotations.vl.json)).
  - Plotly offers `annotation_position` (e.g. "bottom right", "top left") and shape labels at start, middle or end ([shapes](https://plotly.com/python/horizontal-vertical-shapes/)).
  - ONS: every line or range annotation needs explanatory text, placed as close as possible to what it describes, short (about 50 characters), and touching no other text or chart element ([ONS annotations guidance](https://service-manual.ons.gov.uk/data-visualisation/guidance/annotations)).
- **Style.**
  - ONS specifies reference lines as 2 px, dashed 4 px on and 4 px off, grey #B3B3B3; arrows as 1 px dark grey #414042; ranges as #ECECEC with no stroke ([ONS chart elements](https://service-manual.ons.gov.uk/data-visualisation/build-specifications/chart-elements)).
  - Datawrapper's lines are 1–3 px, solid, dotted or dashed. Vega-Lite's example uses `strokeDash: [2, 2]`.
  - Thin, grey and dashed is the common convention. These values belong in the theme.
- **Axis limits.** Tools disagree: ggplot2's hline/vline don't affect the scales (a line outside the data is invisible), while matplotlib's axhline takes part in autoscaling. Under ForgeGraph's no-silent-substitutes rule, an invisible line is a silent drop. Either the automatic axis limits include the line, or a line outside fixed limits is an error.

## 4. Notes

- **Two anchoring systems recur:** data coordinates (Vega-Lite `datum`/`field`, matplotlib `xycoords='data'`, Plotly `xref: 'x'`, Flourish axis values) and plot-relative coordinates (matplotlib `axes fraction`, Plotly `paper`, ggplot2 `±Inf`, Vega-Lite `value`). A "conditions" text block is plot-relative. A callout is data-anchored, and that is phase 9's `text`.
- **Anchor convention:** an anchor point plus the text's own alignment (Vega-Lite `align`/`baseline`; Plotly `xanchor`/`yanchor`; ggplot2 `hjust`/`vjust`) plus an offset (Vega-Lite `dx`/`dy`, matplotlib `offset points`/`offset fontsize`, Plotly `xshift`). ForgeGraph would give the offset × base size, which is matplotlib's `offset fontsize` idea.
- **Avoiding overlap:**
  - ggplot2 drops overlapping text (`check_overlap`) or repels it (ggrepel); Vega tries a list of anchors against marks to avoid ([label transform](https://vega.github.io/vega/docs/transforms/label/)); Datawrapper adds a text outline; ONS says not to overlap.
  - ForgeGraph already has the deterministic piece: the key is placed "in a corner whose box no line, marker or error bar passes through", and it doesn't fit if no corner is clear (architecture D5). A note with `position: auto` can use the same corner search. Since ForgeGraph never draws over data as a fallback, a note that fits no corner is an error.

## 5. Recommended layer spec

### 5.1 Definition files: one per layer type, like graph types
`src/forgegraph/layers/reference_line.yaml`, `note.yaml` and `error_bar.yaml`, with drawing code beside them. They use the same header as other definition files (`name`, `version`, `description`, `extends`) plus one header line naming where the layer applies, then `fixed_parameters` and `variable_parameters`:

```yaml
name: reference_line          # [text]; The name of the layer.
version: 0          # [int]; The version number of the specification.
description: A horizontal or vertical line at a value or a statistic of the data, with an optional label.          # [text]; The description of the layer.
extends: None          # [None, layer]; Each parameter not listed is inherited from this layer. If None, this file must list every parameter.
graph_types: [xy, bar]          # [graph types]; Graph types that accept this layer.

fixed_parameters: None          # List of fixed parameters for the layer, None if none.

variable_parameters:          # List of variable parameters for the layer, None if none.
    axis: None          # [x, y]; Axis whose value the line marks: y draws a horizontal line. A GraphSpec must set it.
    value: None          # [float, mean, median, min, max]; A value on that axis, or a statistic of statistic_column over the rows drawn. A GraphSpec must set it.
    statistic_column: axis          # [axis, column]; Column for a statistic. axis: the axis's data column.
    per: all          # [all, series]; all: one line. series: one line per series, in its color.
    label:
        text: None          # [None, auto, text]; auto: the value, e.g. "Mean 1.23 V". None: none.
        position: end_above          # [start_above, start_below, end_above, end_below]; Along the line, which end and side.
```

- Validation is discriminated on `type`, as GraphSpecs are on `graph_type`, so an error names only that layer's fields.
- Typed models are generated from these files, as for graph types (architecture principle 3, D2).
- Each layer type gets a catalog file and tab, so the catalog's "Baseline + parameter = value" cards work unchanged. The baseline is the example GraphSpec plus one layer of that type.

### 5.2 In a GraphSpec: a `layers:` list of `type:` plus that layer's parameters

```yaml
variable_parameters:
    ...
    layers:
        -   type: error_bar
            axis: y
            error:
                data_column: "Voltage SEM (V)"
            represents: sem
        -   type: reference_line
            axis: y
            value: 1.0
            label:
                text: MVP target
        -   type: reference_line
            axis: y
            value: mean
            per: series
            label:
                text: auto
        -   type: note
            text: "60 °C, 1 atm, H₂/air"
            position: auto
```

- **Order:** list order is z-order within a drawing tier (Vega-Lite: later layers on top).
- **Tiers:** each layer type has a fixed tier, after Datawrapper and Plotly's `below` / `between` / `above`:
  - regions below the grid;
  - reference lines;
  - the data;
  - error bars just below markers but above bar fills;
  - text and annotations on top.
- **Placement order:** layers that take space (notes, labels, annotations) are placed after the data and before series labels' final check. Direct labels and keys then avoid them, the way the key already avoids error bars.

### 5.3 Error bars: bound to columns, never computed

```yaml
name: error_bar
...
graph_types: [xy, bar]          # [graph types]; Graph types that accept this layer.
variable_parameters:
    axis: y          # [x, y]; Axis the bars extend along. On bar, the value axis.
    error:
        data_column: None          # [None, columns]; ± this distance, symmetric. With several y columns, one per y column, in order.
        lower_data_column: None          # [None, columns]; Distance below the value. Set with upper_data_column, instead of data_column.
        upper_data_column: None          # [None, columns]; Distance above the value. Set with lower_data_column.
    ends: distance          # [distance, value]; distance: the columns hold distances from the value (matplotlib, Plotly). value: they hold the bar's ends (ggplot2 ymin/ymax, Vega-Lite y2).
    represents: None          # [sd, sem, ci95, range, text]; What the bars show, recorded in provenance. A GraphSpec must set it.
```

- **Columns:** symmetric is one column; asymmetric is a lower and an upper column. This follows Plotly Express's `error_y` / `error_y_minus` and matplotlib's (2, N), and avoids Vega-Lite's signed `yError2`, which is easy to get wrong.
- **Ends:** `ends: value` also covers ggplot2-style prepared intervals (percentile CIs). Drop it if the owner wants one form only (see §6).
- **Per row:** each row carries its own error, so error bars follow every series with no series selection.
  - On `bar`, the layer needs the graph type to report each row's drawn position (the bar's centre after grouping), not the raw x.
  - This is the one hook between layers and graph types. Phase 9's `delta` and `brace` need it too.
- **Errors, not fallbacks:**
  - a missing or negative distance column;
  - a lower end ≤ 0 on a log axis;
  - error columns that don't match the y columns in count.
- **Look:** in the theme's `error_bar` category, which already has `cap_size` and `line_width`. Add `color: series` [series, hex color], since tools default to the series color (matplotlib `ecolor=None`).
- **No `extent`.** Vega-Lite's `extent: stderr | stdev | ci | iqr` would be statistics computed from raw rows, outside ForgeGraph's DataFrame-in contract. The agent computes them (the phase 5 eval "mean ± SEM per condition" is exactly this). `represents` keeps Cumming's Rule 1 satisfiable.

### 5.4 Note

```yaml
variable_parameters:
    text: None          # [text]; The note, one or more lines, in label markup. A GraphSpec must set it.
    position: auto          # [auto, top_left, top_right, bottom_left, bottom_right]; Plot-area corner. auto: the most open corner no line, marker, error bar or other label passes through.
```

- The look lives in the theme `note` category: size, weight, color, line gap, inset, and an optional frame, mirroring `legend.key`.
- Positions are in plot-relative corners only. The general data-anchored text is phase 9's `text`.

### 5.5 Theme categories for layers
- Every layer type's look goes in a theme category of the same name: `error_bar` (exists), `reference_line` (`line.color`, `line.style: dashed`, `line.width`, `label.size`, `label.gap`), `note`, and later `region`, `arrow`, `brace`, and so on.
- A theme decides fixed vs variable as now. A layer item in a GraphSpec may set that layer's *variable* theme parameters under the same names (`line: {style: dotted}`), the same way a GraphSpec sets `series.line.width` today. No style values live in layer files (D5).

### 5.6 Phase 9 layers fit without changing the model
Each is `type` + geometry in data coordinates (+ an optional `label`) + a theme category:

| Layer | Geometry parameters | Precedent |
| --- | --- | --- |
| `region` (target region) | `x: {min, max}`, `y: {min, max}`; None = to the plot edge, which gives the open-corner box | Vega-Lite `rect`; Plotly `add_hrect`/`add_vrect`; matplotlib `axhspan`; Datawrapper range |
| `fill_between` | `lower_data_column`, `upper_data_column` (or a y column and a value), per series | Vega-Lite `area` with `y2`/`errorband`; ggplot2 `geom_ribbon(ymin, ymax)`; matplotlib `fill_between` |
| `text` | `x`, `y`, `align`, `baseline`, `offset` (× base size) | Vega-Lite `text` (`align`, `baseline`, `dx`, `dy`); matplotlib `annotate` |
| `arrow` | `from: {x, y}`, `to: {x, y}`, optional label at `from` | matplotlib `annotate(arrowprops)`; Plotly `ax`/`ay` |
| `brace` | `from: {x, y}`, `to: {x, y}`, `side`, label (e.g. ΔV) | none native; drawn as a path |
| `ellipse` | `center: {x, y}`, `width`, `height` in data units | ggforce `geom_mark_ellipse`; Plotly circle shape |
| `delta` | two points (or two series at one x), label with the difference | none native; arrow + text |

- The list, the tiers, the theme categories and the per-type definition files stay as they are.
- `fill_between` overlaps an error *band*: a continuous-x error band can be a `fill_between` from lower and upper columns rather than a second error-bar style.
- "Stacked decomposition" means cumulative sums. Either the agent prepares cumulative columns (keeping the DataFrame contract), or ForgeGraph stacks. See §6.

## 6. Decisions only the owner can make

1. **Which statistics a reference line may compute:** mean, median, min, max over drawn rows, and whether `per: series` is in phase 5. A broader list (quantiles, mean ± k SD) moves toward computing statistics.
2. **Error-column forms:** symmetric plus lower/upper distances only, or also `ends: value` (absolute bounds)? One form is simpler; two match how agents usually hold CIs.
3. **Is `represents` required, and is it drawn?** Options: provenance only; added to an auto note or caption ("Error bars: ±1 SEM, n = 3"); or a lint warning when missing. An `n_column` is related.
4. **Axis limits:** does a reference line, region or note outside the data extend the automatic limits (matplotlib-like), or is it an error when the limits are fixed? ggplot2 silently hides it, which the error rule rules out.
5. **Draw tiers:** fixed per layer type in code, or a theme parameter? ONS and Datawrapper disagree on whether reference lines sit above or below data.
6. **Removing or overriding inherited layers:** `layers` append through extends. Should a layer item have an optional `name`, so a GraphSpec can replace or remove a preset's layer?
7. **Plot-relative positions:** corners only for `note`, or general axes-fraction anchors (matplotlib `axes fraction`, Plotly `paper`) for later annotations too?
8. **The GraphSpec definition file:** polarization.yaml "sets every parameter". Does it carry one example of each layer, or does each layer's catalog file supply its own baseline layer?
9. **Stacking in phase 9:** does ForgeGraph compute cumulative sums for stacked decomposition, or does the agent prepare cumulative columns?
10. **File location:** flat `layers/<name>.yaml` like `graph_types/xy.yaml`, or the per-folder `layers/<name>/layer.yaml` that architecture.md still describes?
