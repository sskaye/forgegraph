# Phase 9 research: annotation and area layers

Input for the phase 9 layer proposal. Every claim about an outside tool or paper carries its source; the full list is at the end. Where I couldn't open a primary page, I say so.

## 0. Bottom line

1. **Use d3-annotation's decomposition as the model:** subject, note, connector. In ForgeGraph terms the **layer type is the subject** (a point, a two-point span, an ellipse, a region). Every annotation type then shares the same optional `label` block (the note) and the same `connector` options. That keeps the set small, and each new type adds one subject, not a whole new schema. [d3a-src][ods][eu]
2. **Anchors are always data coordinates**, plus two *data-driven* forms: a point on a named series at an x, and a series' extreme (`max_y` and so on). Data-driven anchors keep annotations right when the data changes, which matters for scheduled graphs (D12). ChartAccent's survey of 106 published charts found these targets, data items and extremes, common. [ren]
3. **Six types instead of seven names:** `callout` (absorbs `text` and leader callouts), `arrow`, `delta` (with `shape: dimension | brace`, which absorbs `brace`), `ellipse`, `region` (the target region, also bands) and `band` (fill between curves, which covers decomposition). Stacked *sum* areas are probably a mark of `xy`, not a layer (§7, Q1).
4. **Placement is the agent's job**, but `label.position: auto` can reuse the deterministic candidate search in `render/labels.py`. That search is the discrete-candidate formulation from the point-feature labelling literature [cms]. Lint then checks letters against data, text, other annotations and the plot edge.

---

## 1. How other tools specify annotations

| Tool | Anchor / coordinates | Text position | Connector | Shapes |
|---|---|---|---|---|
| **matplotlib `annotate`** | `xy` in `xycoords`: `'data'` (the default), `'axes fraction'`, figure/axes points or pixels. A 2-tuple mixes systems per axis, e.g. `('data', 'axes fraction')` | `xytext` in `textcoords`, which also allows `'offset points'`, `'offset pixels'` and `'offset fontsize'` | `arrowprops`: `arrowstyle` (`->`, `<->`, `-[`, `\|-\|`, `fancy`, `simple`, `wedge`), `connectionstyle` (`arc3,rad`, `angle3`, `angle`, `arc`, `bar`), `shrinkA/B` (gap at each end, default 2 pt), `relpos` | Patches separately. `annotation_clip` hides annotations whose `xy` falls outside the axes. [mpl-ann][mpl-guide] |
| **Vega-Lite** | Constant positions through `datum` ("map a constant data value to an encoding channel via an underlying scale") | `text` mark with `dx`/`dy` pixel offsets (applied after `angle`), `align`, `baseline`, `limit` | A separate `rule` mark, layered | `rule`, `rect` marks; defaults in `config.text` [vl-text][vl-datum] |
| **ggplot2 `annotate()`** | Positions as vectors, not mapped from data: `x, y, xmin…ymax, xend, yend` | Same | `geom = "segment"` / `"curve"` | `"rect"`, `"pointrange"`. Annotations expand the scales and never enter the legend [gg-ann] |
| **ggforce `geom_mark_*`** | Selects *data rows* (a `filter` aesthetic) | Label and description placed automatically. A label that would overlap data is not drawn | `con.type` (elbow, straight, none), `con.cap`, `con.arrow` | `ellipse` (fitted, see §3), `hull`, `rect`, `circle`. `expand` and `radius` set the margin [ggforce] |
| **ggrepel** | Data points | Force simulation: labels repel each other, points and the panel edge; `force_pull` draws each back to its point | `min.segment.length` (default 0.5 lines): shorter leaders aren't drawn | Labels that overlap too much are dropped (`max.overlaps`, with a warning). A `seed` is needed for a repeatable layout [ggrepel] |
| **Plotly** | `x, y` with `xref/yref`: an axis, `'paper'`, or `'x domain'` | `ax, ay` tail offset (`axref` defaults to `'pixel'`), `xanchor/yanchor`, `xshift/yshift` | `showarrow`, `arrowhead` 0–8, `standoff`, `startstandoff` | `shapes`: `rect`, `circle`, `line`, `path` with `x0…y1`, `layer: below/between/above`, and a shape `label` [plotly-ann][plotly-shapes] |
| **Datawrapper** | Dragged into place in the editor; range positions can be typed as start and end values | Wrapping text box | Straight lines or arrows to a point; circles round an area | Range highlights: full-width or full-height bands drawn *behind* data, gridlines and reference lines, with a light colour or low opacity and optional hatching. Annotations always sit on top. On mobile, notes become numbered keys below the chart [dw-ann][dw-range] |
| **d3-annotation** (Susie Lu, Apache-2.0) | Subject at `x, y` (or computed from `data` through accessors) | Note at offset `dx, dy`, or absolute `nx, ny` | `connector.type`: line, elbow, curve; `end`: arrow, dot, none | Types: `annotationLabel`, `Callout`, `CalloutElbow`, `CalloutCurve`, `CalloutCircle`, `CalloutRect`, `XYThreshold`, `Badge`, plus `annotationCustomType`. Subject parameters: circle `radius, radiusPadding`; rect `width, height`; threshold `x1, x2, y1, y2`; badge `text, radius`. Note parameters: `title, label, wrap, align, orientation, padding, bgPadding, lineType`. `editMode` lets a person drag notes and export the positions as JSON [d3a-src][d3a][ods][d3a-gh] |

### Assessment of the subject, connector and note model

- **The model.** Its author describes "a subject (the thing the annotation is annotating), a note, and a connector joining the note to the subject" [ods]. The EU data-visualisation guide teaches the same three parts. It adds that the connector can be left out when the note sits close to its subject and shares its colour, and that a note can sit inside an area large enough to hold it [eu].
- **Why it fits declarative YAML.** The parts are orthogonal, so a type list stays short: each d3 type is just a preset combination of subject and connector. In YAML, the subject's parameters vary by type, while `label` and `connector` are one shared schema. That gives the catalog one table for each subject plus one shared table.
- **What doesn't carry over.** d3's notes are positioned in pixels (`dx, dy`), so they're tied to one rendering size. ForgeGraph renders one GraphSpec into several formats, so note offsets should be in × base size units, like every theme length, or in data coordinates (Q3). `editMode`'s "drag, then export positions as JSON" matches the agent workflow: placement is decided once and then stored.
- **ChartAccent's design space** classifies annotation *forms* as text, shapes, highlights and images. Shapes include line, arrow, curve, rectangle, ellipse and bracket. *Targets* are data items, sets and series; coordinate space (a value, a span, a two-dimensional region); chart elements; and prior annotations. The paper notes that one target often carries several forms at once, for example a highlighted point plus text plus an arrow [ren]. That supports one layer per subject, with an optional note and connector, rather than separate text and arrow layers that the agent must line up by hand.

---

## 2. Braces

| Implementation | Shape | Parameters |
|---|---|---|
| **TikZ `decorations.pathreplacing` brace** | "replaces a straight line path by a long brace"; only meaningful for straight paths | `amplitude` ("how much the brace rises above the path"), `aspect` (the fraction of the length where the middle point sits; default 0.5), `raise` (offset from the path), `mirror` (flip to the other side) [tikz-lib][tikz-dec] |
| **`curlyBrace`** (matplotlib port of the MATLAB `drawbrace`; v1.0.2, 2019; MIT; 53 stars; dated dependencies) | Four quarter-circle arcs and two straight segments. Arc radius = `k_r` × length | `p1, p2` (swap them to flip), `k_r` (default 0.1), `bool_auto` (corrects for axis scaling and log axes), `str_text` placed at the tip and rotated, `int_line_num` (gap set in newlines) [curly-src][curly-gh] |
| **Sum of two logistic curves** (named-arrays `brace_vertical`, and the widely copied Stack Overflow recipe) | Each half is `1/(1+e^(−β(z−z_min))) + 1/(1+e^(−β(z−z_max)))` about the centre, shifted by −1.5 and scaled by `width` | `x`, `width`, `ymin`, `ymax`, `beta` ("curlyness", default 2/width), `kind` left or right, `label` set in `offset fontsize` units from the tip [na-doc][na-src][so-brace, not fetchable] |
| **ggbrace (R)** | Computed from the selected data points | `rotate`, `outside`, `distance`, `outerstart`, `width`, `bending` (0–1), and a companion text stat [ggbrace] |
| **TeX `\underbrace`** | Assembled from extensible font pieces (tips, middle, extension) | No parameters; not reachable from matplotlib mathtext as a free-standing glyph |

**Recommendation.**

- Take **TikZ's parameter semantics**: amplitude, aspect, raise and mirror, with mirror called `side` in our terms. It is the most widely used published definition, and its four names cover every other tool's knobs.
- Draw the shape as **the logistic curve or the quarter-circle construction, in display space (points)**, from the two anchors projected to display coordinates. Then the brace keeps its shape on log axes and unequal x and y scales, which is what `curlyBrace`'s `bool_auto` patches.
- Amplitude and raise are × base size, set in the theme, so the brace looks the same on a slide and in a journal column.
- The label sits at the tip, `label.gap` beyond the amplitude. It is always horizontal for a vertical brace, not rotated as `curlyBrace` does.
- Don't depend on `curlyBrace`: about 100 lines, an unknown release state, dated pins. Port the geometry, crediting the source as was done for `breaks_log`.

---

## 3. Ellipse and region highlights

**Three different things share the word "ellipse".**

1. **A hand-placed ellipse:** centre, width, height and angle. Plotly's `circle` shape works this way, with `x0…y1` in data units [plotly-shapes]. In *data* coordinates it distorts with axis scaling and isn't an ellipse at all on a log axis.
2. **An enclosing ellipse around selected points.** ggforce fits a minimum-area ellipse with the **Khachiyan algorithm on the convex hull**, with a tolerance (`tol`, default 0.01). It notes that some points may fall slightly outside, then grows the ellipse by `expand` [ggforce].
3. **A covariance or confidence ellipse.** matplotlib's gallery recipe builds it from the Pearson correlation: radii √(1±r), rotated 45°, scaled by `n_std`·σ, centred on the means. Its caveat is that `n_std = 3` covers about 98.9% of points *only for normally distributed data* [mpl-conf].

**Recommendation.**

- `ellipse` selects **rows** (a filter on the DataFrame, as ggforce does) and draws the **minimum enclosing ellipse in display space**, plus `expand` × base size. The highlight then means "this group" and stays right when the data changes.
- Keep an explicit `center`/`size` form for highlighting empty space, as rarely needed. A *confidence* ellipse is a statistical claim, so it belongs with the phase 11 `fit` and statistics layers, not with annotations (Q5).

**A region or band** is one rectangle with optional open sides:

- **Datawrapper's range highlight** spans the full width or height of the chart, sits behind data, gridlines and reference lines, and uses a light colour, low opacity or optional hatching [dw-range].
- **Plotly** rect shapes have `layer: below` [plotly-shapes].
- **ChartAccent** lists the targets "a span along an attribute" and "a span along two dimensions" [ren].

So one `region` with `x: [min, max]` and `y: [min, max]`, where either end may be open, covers four cases. Open ends run to the plot edge.

| Case | Range |
|---|---|
| 1-D band | `x: [a, b]` only |
| 2-D box | both x and y ranges closed |
| One-sided "target corner" | e.g. `x: [None, 47]` with `y: [560, None]` |
| Dashed corner box | as above, drawn with outline only |

---

## 4. Fill between, stacked areas and target bands

- **matplotlib `fill_between(x, y1, y2, where, interpolate, step)`.** `where` excludes x-ranges. `interpolate=True` "calculate[s] the actual intersection point and extend[s] the filled region up to this point", so without it fills stop short where curves cross [mpl-fb].
- **matplotlib `stackplot(x, *ys, baseline)`.** The baselines are `zero` (an ordinary stack), `sym` (ThemeRiver), `wiggle`, and `weighted_wiggle` (streamgraph). It links Byron & Wattenberg's streamgraph page [mpl-stack][byron].
- **Vega-Lite `stack`.** The options are `zero`, `normalize` (percent), `center` (streamgraph) and `null` (overlaid). Order comes from the `order` channel, and by default from the colour field [vl-stack].
- **ggplot2.** `geom_ribbon` is "a y interval defined by `ymin` and `ymax`" per x. `geom_area` is the special case with `ymin = 0` and `position = "stack"`. It uses **`stat = "align"`, which "interpolates groups to a common set of x-coordinates"** so that groups sampled at different x can stack. `outline.type` is `both`, `upper`, `lower` or `full` [gg-ribbon]. ForgeGraph will need the same alignment step: lab series rarely share x values.
- **Best practice.**
  - Only the bottom layer of a stack has a common baseline. Wilke: "the different bars cannot be compared easily because they have different baselines". He recommends side-by-side or partial alternatives when the individual parts matter [wilke].
  - Byron & Wattenberg cover baseline choice and layer ordering for streamgraphs. Later work notes that their ordering exploits properties of their example data [byron][eg-stream].
  - For engineering decompositions (a total split into contributions):
    - use a **zero baseline**, or the reference curve;
    - order layers by meaning, as given by the user, not by an aesthetic algorithm;
    - label each layer **inside its widest part** when it fits (Vega's label transform has an area method `floodfill` for this [vega-label]), otherwise with a callout.
- **The decomposition in the examples is "fill between consecutive curves".** It runs from a top reference line down through each successive curve, each gap labelled by its cause. That is `band` with an ordered list of boundaries, not a stack of components. A stack of components (a sum from zero) is the other case.
- **Target bands.** Draw them behind the data, light, labelled once inside or at one end, and never as a legend entry. Datawrapper and ggplot2 both keep them out of the legend [dw-range][gg-ann].

---

## 5. Placement and overlap

**Research.**

- **Christensen, Marks & Shieber (1995)** show that point-feature label placement is NP-hard. They compare algorithms over a fixed set of **candidate positions per point**: discrete gradient descent and simulated annealing, which won given enough time [cms].
- **Kittivorawong, Moritz, Wongsuphasawat & Heer (2020)** detect overlaps with an **occupancy bitmap** of rasterised marks, much faster than approximating marks by points. This is now Vega's `label` transform, with `anchor` and `offset` candidate lists, `avoidMarks`, and area methods [kmwh][vega-label].
- **ggrepel's** force simulation needs a seed to be repeatable and can drop labels [ggrepel]. That conflicts with "re-render identically" and with "error, don't fall back". It was already rejected for series labels in phase 1, as were adjustText and matplotlib-label-lines.
- **Imhof (1975)**, the cartographic basis for all of the above: names close to their feature, on one side, never crossing other features. Cited from memory, not fetched.

**Style guidance.**

- Annotations go **above all other layers** [eu][dw-range].
- Labels must **never overlap each other or other text**; slight overlap with minor elements is tolerable [eu].
- Use a **halo or outline** on busy backgrounds [eu][dw-ann].
- Leave out a connector when the note is close by and colour-matched [eu].
- Keep text brief [eu].

**How this fits ForgeGraph.** `render/labels.py` already implements the discrete-candidate approach: 8 directions × 4 distances along the line, a hard clearance test against letters, lines and markers, scored preferences, and a search over orders. It is deterministic and reports failure rather than overlapping. `label.position: auto` for annotations should reuse it. The candidates are around the subject (for a callout, the target point; for a delta or brace, beyond the tip; for an ellipse, around its rim). If nothing fits, that's an error naming the annotation.

**What lint should test** (it runs on the finished figure, measures to the letters, and reports without changing anything):

1. **annotation-text-overlap**: annotation letters touch any other text (ticks, titles, series labels, keys, notes, other annotations), with clearance. Extends `overlapping-text`.
2. **annotation-over-data**: annotation letters closer than `annotation.clearance` to any drawn line, marker or error bar. Filled bands and regions are excluded unless the text sits on them without a halo (see 6).
3. **connector-crossing**: a connector or arrow crosses another annotation's text, or another connector.
4. **annotation-clipped**: any part (letters, arrowhead, brace tip, ellipse rim) is outside the figure, or outside the plot area where the theme forbids margins (Q4).
5. **anchor-outside-limits**: an anchor falls outside the axis limits. Per "error, don't fall back" this is better as an error before drawing than as a lint warning; matplotlib's `annotation_clip` would silently hide it [mpl-ann].
6. **low-contrast-text**: annotation text over a filled area whose contrast with the text colour is below WCAG's 4.5:1, with no halo.
7. **short-connector**: a connector shorter than a minimum, ggrepel's `min.segment.length` idea [ggrepel]. Report it, or don't draw it (Q6).
8. **detached-label**: a label nearer to another annotation's subject or another series than to its own, by the same `max_relative_distance` rule as direct labels.

---

## 6. Recommended layer types for ForgeGraph

### Shared pieces

**Anchor** (a new parameter kind, `[anchor]`):

```yaml
{x: 100, y: 1.23}                    # a data point; dates allowed on a date axis
{x: 100, series: "Series A"}         # y read off that series' drawn line at x
{series: "Series A", at: max_y}      # extreme: max_y, min_y, max_x, min_x, first, last
```

- **Reading y off a series.** Interpolate along the line *as drawn*: linear in display space, so log axes interpolate in log space.
- **Errors.** An x outside the series' range, an unknown series, or a series with replicates (`encoding.detail`) without a disambiguating name are all errors.

**Label (the note)**, the same block on every type:

```yaml
label:
    text: "Remaining gap"           # [None, text]; D8 markup; may hold {value} (delta only)
    color: None                     # [None, hex color, series name]; None: annotation.color
    position: auto                  # [auto, anchor, offset]; auto: first clear candidate
    side: auto                      # [auto, above, below, left, right]; with position auto
    at: None                        # [None, anchor]; when position is anchor
    offset: None                    # [None, two floats]; × base size from the subject
    connector: none                 # [none, line, arrow, elbow]; from note to subject
```

- **Colour by series name.** `color: <series name>` gives the "coloured rich text" in the examples: text in a series' colour. It resolves to that series' drawn colour, and an unknown name is an error.
- **Mixed colours within one string** (needed for one example) would extend the D8 markup. matplotlib has no multi-colour `Text`; its gallery chains `annotate(..., xycoords=previous_text, xy=(1, 0))` pieces [mpl-rainbow]. See Q7.

### Types

**`callout`**: note plus optional connector to a target. Replaces `text`, leader callouts and arrows pointing at a feature.

```yaml
-   type: callout
    target: {x: 30, y: 450}           # [None, anchor]; None: free text at label.at
    label:
        text: "Remaining gap"
        position: offset
        offset: [4, -3]
        connector: arrow
```

**`arrow`**: the arrow *is* the message, a change from A to B.

```yaml
-   type: arrow
    from: {series: "Before", at: max_y}
    to: {series: "After", at: max_y}
    shape: line                      # [line, block]; block: a wide filled arrow (matplotlib 'simple')
    curvature: 0                     # [-1-1]; matplotlib arc3 rad
    label: None
```

**`delta`**: the difference between two anchors, drawn as a dimension line (the engineering-drawing convention: dimension line, terminators, extension lines, value [dim-wiki][acad-dim]) or as a curly brace. Absorbs `brace`.

```yaml
-   type: delta
    from: {x: 150, series: "Series A"}
    to: {x: 150, series: "Series B"}
    shape: brace                     # [dimension, brace]
    measure: dy                      # [dx, dy]; which difference {value} holds
    side: right                      # [left, right, above, below]; TikZ mirror
    value_multiplier: 1000           # [positive float]; e.g. V shown in mV
    value_digits: 0                  # [int]
    label:
        text: "ΔV = {value} mV"
```

**`ellipse`**: encloses selected rows.

```yaml
-   type: ellipse
    rows: {column: batch, equals: "B7"}   # [None, filter]; the same filter syntax as elsewhere
    center: None                             # [None, anchor]; explicit form when rows is None
    size: None                               # [None, two floats]; × base size, with center
    label: {text: "Batch B7", connector: line}
```

**`region`**: the target region, band or corner box.

```yaml
-   type: region
    x: [None, 47]                    # [None, two values]; an open end runs to the plot edge
    y: [560, None]
    style: outline                   # [fill, outline]; fill: light, behind data; outline: dashed box
    label: {text: "Target", position: inside}  # inside: a corner of the region
```

**`band`**: fills between consecutive boundaries. A decomposition uses three or more.

```yaml
-   type: band
    boundaries:                      # [list of: series name, y column, float]
        -   1.6                      # a constant (e.g. a reference value)
        -   "Curve 1"
        -   "Curve 2"
        -   "Curve 3"
    names: ["Loss 1", "Loss 2", "Loss 3"]   # one per band; labelled inside the widest part, else a callout
    align_x: interpolate             # [interpolate, error]; ggplot2's stat_align
```

### What merges, and what doesn't

| Plan name | Proposal |
|---|---|
| `text` | `callout` with `target: None` |
| leader callouts | `callout` with a connector |
| `brace` | `delta` with `shape: brace` |
| `arrow` | stays: the A→B change has no computed value and can curve |
| `fill_between` + decomposition | `band` |
| target region | `region` (also covers bands, which phase 5's `reference_line` can't) |
| stacked sum | see Q1 |

`note` (phase 5) stays separate: it's the auto-placed conditions block, not anchored to data.

### Theme parameters

These follow the existing naming and × base size convention. Fixed or variable is the owner's call.

```yaml
annotation:
    color: "#404040"          # [hex color]; Lines and text, unless a layer sets label.color.
    line_width: 0.08          # [positive float]; × base size.
    clearance: 0.2            # [positive float]; Least gap from annotation letters to data and text, × base size.
    label:
        size: 0.85            # [positive float]; × base size.
        weight: regular       # [light, regular, medium, semibold, bold]
        gap: 0.3              # [positive float]; Subject to letters, × base size.
        halo: 0.15            # [0, positive float]; Background-coloured outline behind text, × base size. 0: none.
    arrow:
        head_length: 0.5      # [positive float]; × base size.
        head_width: 0.35      # [positive float]; × base size.
        gap: 0.2              # [positive float]; Tip to target, × base size (matplotlib shrinkB, Plotly standoff).
    delta:
        terminator: arrow     # [arrow, bar, dot]; Ends of a dimension line.
    brace:
        amplitude: 0.5        # [positive float]; TikZ amplitude, × base size.
        raise: 0.2            # [positive float]; TikZ raise, × base size.
    ellipse:
        expand: 0.4           # [positive float]; Margin round the enclosed points, × base size (ggforce expand).
region:
    fill_opacity: 0.12        # [0-1]
    line_style: dashed        # [solid, dashed, dotted]
band:
    opacity: 0.3              # [0-1]
```

### Drawing order

Bands and regions go behind the data, as Datawrapper's range highlights do and with Plotly's `layer: below`. Annotations go above everything [dw-range][plotly-shapes][eu].

---

## 7. Open questions for the owner

1. **Stacked sum areas: layer or mark?** By D5, encodings and marks of the main data belong to the graph type. A stacked area *of the plotted series* is Vega-Lite's area mark with `stack`, so it fits `xy` (`mark.area`, `stack: zero | normalize`) better than a layer. `band` (between existing curves) is clearly a layer.
2. **Should the six-type set replace the plan's names?** The plan names `text` and `brace` as types. The recommendation folds them into `callout` and `delta`. Trade-off: fewer schemas and catalog tabs, against names an agent or user might search for first.
3. **How are note positions stored?** The options are an offset in × base size from the subject (it survives a format change at the same distance from the subject; d3 and Plotly use pixels), a data anchor (stays with the data when axis limits change, but drifts in size relative to the text), or `auto` only, re-solved every render. Recommendation: `auto` by default and offset as the override. Stored data anchors are kept for free text.
4. **May annotation labels sit in the margin?** Direct labels never may (D5 rule 1). The examples put brace values and long callouts in the right margin, so the layout would have to make room for them.
5. **Is a confidence ellipse an annotation?** It is a statistical statement, so the recommendation is to keep it for phase 11 statistical layers.
6. **Short connectors:** draw them anyway, or leave them out like ggrepel? Leaving them out is a quiet substitution, which "error, don't fall back" argues against. Lint could warn instead.
7. **Multi-coloured text in one label.** Should D8 markup gain a colour span? Or is one colour per label, with several labels, enough?
8. **Value formatting in `delta`:** a multiplier and a number of digits, as above, or a restricted Python format spec (`{value:.0f}`)? Rendering never runs code, so fields would have to be whitelisted, because `str.format` allows attribute access.
9. **Does `position: auto` belong in the renderer at all?** The architecture gives placement judgement to the agent. Auto would make simple cases one line and stays deterministic, but it moves judgement into the library.

---

## Sources

- [mpl-ann] matplotlib `Axes.annotate`: https://matplotlib.org/stable/api/_as_gen/matplotlib.axes.Axes.annotate.html
- [mpl-guide] matplotlib annotations guide: https://matplotlib.org/stable/users/explain/text/annotations.html
- [mpl-conf] matplotlib confidence ellipse: https://matplotlib.org/stable/gallery/statistics/confidence_ellipse.html
- [mpl-fb] matplotlib `fill_between`: https://matplotlib.org/stable/api/_as_gen/matplotlib.axes.Axes.fill_between.html
- [mpl-stack] matplotlib `stackplot`: https://matplotlib.org/stable/api/_as_gen/matplotlib.axes.Axes.stackplot.html
- [mpl-rainbow] matplotlib, concatenating text objects: https://matplotlib.org/stable/gallery/text_labels_and_annotations/rainbow_text.html
- [vl-text] Vega-Lite text mark: https://vega.github.io/vega-lite/docs/text.html
- [vl-datum] Vega-Lite datum: https://vega.github.io/vega-lite/docs/datum.html
- [vl-stack] Vega-Lite stack: https://vega.github.io/vega-lite/docs/stack.html
- [vega-label] Vega label transform: https://vega.github.io/vega/docs/transforms/label/
- [gg-ann] ggplot2 `annotate()`: https://ggplot2.tidyverse.org/reference/annotate.html
- [gg-ribbon] ggplot2 `geom_ribbon`/`geom_area`: https://ggplot2.tidyverse.org/reference/geom_ribbon.html
- [ggforce] ggforce `geom_mark_ellipse`: https://ggforce.data-imaginist.com/reference/geom_mark_ellipse.html
- [ggrepel] ggrepel examples: https://ggrepel.slowkow.com/articles/examples.html
- [ggbrace] ggbrace: https://github.com/NicolasH2/ggbrace
- [plotly-ann] Plotly annotations: https://plotly.com/python/reference/layout/annotations/
- [plotly-shapes] Plotly shapes: https://plotly.com/python/reference/layout/shapes/
- [dw-ann] Datawrapper, responsive annotations: https://www.datawrapper.de/blog/better-more-responsive-annotations-in-datawrapper-data-visualizations/
- [dw-range] Datawrapper, range highlights and lines: https://www.datawrapper.de/academy/range-highlights-and-lines
- [d3a] d3-annotation docs: https://d3-annotation.susielu.com/
- [d3a-gh] d3-annotation repo: https://github.com/susielu/d3-annotation
- [d3a-src] d3-annotation source (type and property names read from the bundled build): https://www.ons.gov.uk/visualisations/dvc1221/lib/d3-annotation.js
- [ods] Susie Lu, "D3.Annotation: Design and Modes": https://opendatascience.com/?p=16369
- [eu] data.europa.eu, text annotations anatomy: https://data.europa.eu/apps/data-visualisation-guide/text-annotations-anatomy
- [ren] Ren, Brehmer, Lee, Höllerer, Choe, "ChartAccent: Annotation for Data-Driven Storytelling", PacificVis 2017: https://sites.cs.ucsb.edu/~holl/pubs/Ren-2017-PacificVis.pdf
- [cms] Christensen, Marks, Shieber, "An Empirical Study of Algorithms for Point-Feature Label Placement", ACM TOG 14(3), 1995, doi:10.1145/212332.212334: https://dash.harvard.edu/bitstream/1/2032678/2/AnEmpiricalStudy.pdf
- [kmwh] Kittivorawong, Moritz, Wongsuphasawat, Heer, "Fast and Flexible Overlap Detection for Chart Labeling with Occupancy Bitmap", IEEE VIS 2020: https://idl.uw.edu/papers/fast-labels
- [wilke] Wilke, *Fundamentals of Data Visualization*, ch. "Visualizing proportions": https://clauswilke.com/dataviz/visualizing-proportions.html
- [byron] Byron & Wattenberg, "Stacked Graphs – Geometry & Aesthetics", IEEE TVCG 2008: https://leebyron.com/streamgraph/
- [eg-stream] Di Bartolomeo & Hu, "There is More to Streamgraphs than Movies", EuroVis 2016: https://diglib.eg.org/handle/10.1111/cgf12910
- [tikz-lib] PGF/TikZ manual, decoration library (brace, amplitude, aspect): https://tikz.dev/library-decorations
- [tikz-dec] PGF/TikZ manual, decorations (raise, mirror): https://tikz.dev/tikz-decorations
- [curly-src] curlyBrace source: https://matplotlib-curly-brace.readthedocs.io/en/latest/_modules/curlyBrace.html
- [curly-gh] curlyBrace repo: https://github.com/iruletheworld/matplotlib-curly-brace
- [na-doc] named-arrays `brace_vertical`: https://named-arrays.readthedocs.io/en/latest/_autosummary/named_arrays.plt.brace_vertical.html
- [na-src] named-arrays source (`named_arrays/plt.py`, read via the GitHub API): https://github.com/sun-data/named-arrays
- [so-brace] Stack Overflow, "Annotating ranges of data" (could not be fetched; formula confirmed in [na-src]): https://stackoverflow.com/questions/18386210/annotating-ranges-of-data
- [dim-wiki] Dimensioning on drawings (ISO 129-1:2018 context): https://en.wikipedia.org/wiki/Dimensioning_on_drawings
- [acad-dim] Autodesk, parts of a dimension: https://help.autodesk.com/cloudhelp/2015/ENU/AutoCAD-LT/files/GUID-EEC547BD-477F-4FA8-9831-A3AC3BE80F92.htm
- Imhof, "Positioning Names on Maps", *The American Cartographer* 2(2), 1975 (cited from memory, not fetched).
