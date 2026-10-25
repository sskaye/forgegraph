# Research: the `bar` graph type and the `scatter` / `line` presets (Phase 5)

Input for a proposal. Every claim has a source; the numbered source list is at the end, and claims cite it as [n]. "Recommendation" marks my own conclusions.

---

## 0. Summary

- **Every established tool uses the same model for bars.** Rows map to a category axis and a value axis. A grouping column is drawn either side by side ("dodge", "group", `xOffset`) or stacked, and stacked bars can be normalized to 100%. Orientation is either inferred from which axis holds the categories (Vega-Lite, ggplot2, Tableau) or set by a flag (matplotlib, Plotly, seaborn).
- **One row per bar is the established non-aggregating model.** ggplot2 calls it `geom_col` (`stat_identity`), Plotly has `px.bar`, and Vega-Lite draws one mark per row when no `aggregate` is set. ForgeGraph's DataFrame contract matches this exactly. A duplicate (category, group) row should be an error, not silently stacked.
- **The literature agrees on these points:**
  - bars start at zero (or at 1 on a log axis);
  - unordered categories are sorted by value, while ordered categories keep their order;
  - horizontal bars suit long or many labels;
  - stacking hurts comparison of every segment except the bottom one;
  - bars of means with error bars ("dynamite plots") hide the data.
- **Bar gaps from tool defaults are far tighter than Few recommends.** Few recommends gaps of 50–75% of bar width. Vega-Lite and ggplot2 default to about 11%, and matplotlib and seaborn to 25%. Gap width is look, so it belongs in the theme.
- **Presets:** every tool keeps look (Vega-Lite `config`, Plotly templates, ggplot2/Altair themes) separate from chart recipes (wrapper functions, `relplot(kind=)`, `px.line` vs `px.scatter`). The `scatter` and `line` presets should therefore set only the marks, and never the theme, format or theme parameters.

---

## 1. How established tools model bar charts

### Vega-Lite
- **Mark:** `mark: bar`. A discrete field on `x` gives vertical bars, and one on `y` gives horizontal bars [1].
  - `mark.orient` exists ("horizontal (default) or vertical"), but orientation normally follows the encodings [1].
- **Width and gaps:** bar width comes from the band scale. `paddingInner` is the gap as a fraction of the step, and `paddingOuter` is the gap at the ends [3]. The config defaults are:
  - `barBandPaddingInner` 0.1 for bars;
  - `bandWithNestedOffsetPaddingInner` 0.2 when bars are grouped;
  - `offsetBandPaddingInner` 0, so bars within a group touch;
  - `bandPaddingOuter` equal to paddingInner/2 [3].
  - A fixed or relative width can be set instead: `mark.width` as pixels or `{band: 0.7}` [1].
- **Other mark properties:** `cornerRadius` defaults to 0 and `cornerRadiusEnd` rounds only the value end [1].
- **Grouped bars:** the `xOffset` channel takes the group field, alongside `color` on the same field [4].
- **Stacking:** `stack` on the value channel takes these values [2]:
  - `zero` (or true), stacking from a zero baseline;
  - `normalize`, a 100% stack;
  - `center`, a streamgraph;
  - `null` (or false), layered and overlapping.
  - Stacking is the default for bar, area and arc marks when a non-position channel (such as color) holds an unaggregated field [2].
  - Stack order follows the grouping field, or the `order` channel [2].
- **Zero baseline:** `scale.zero` defaults to true for unbinned quantitative x/y fields [3].
- **Ordering:** `sort` takes several forms [5]:
  - `ascending` (the default for discrete fields, natural order) or `descending`;
  - another channel, such as `-x` (by x, descending);
  - a field with an aggregate `op` (the default op is sum for stacked plots, min otherwise);
  - an explicit array;
  - `null`, which keeps data order.
- **Value labels:** a separate `text` layer that shares the encodings, with `align`, `baseline` and `dx` offsets. The official example widens the domain by hand so the labels fit [6].
- **Error bars:** the `errorbar` mark takes pre-computed `y`/`y2` or `y` plus `yError`/`yError2`. It can also compute `stderr` (the default), `stdev`, `ci` or `iqr` from raw data [7].

### ggplot2
- **Two geoms:**
  - `geom_bar` uses `stat_count`: "it counts the number of cases at each x position" [8].
  - `geom_col` uses `stat_identity`: "it leaves the data as is". The page advises: "If you want the heights of the bars to represent values in the data, use geom_col()" [8].
- **Width:** the default is 0.9, that is 90% of the data's resolution, which leaves a gap of about 11% of bar width [8].
- **Orientation:** inferred from the aesthetic mapping, with an `orientation` argument for ambiguous cases [8]. `coord_flip()` is superseded: swap x and y, or set `orientation` [11].
- **Positions:**
  - `position_stack` is the default for bars [8].
  - `position_fill` stacks and scales each bar to the same height [10].
  - `position_dodge` and `position_dodge2` place bars side by side. `dodge2` has `padding` 0.1 between bars, and `preserve = "total" | "single"` sets whether a category with fewer groups gets wider bars [9].
- **Negative values** are stacked separately: positive values upward and negative values downward [10].
- **Base of the bar:** "the base of the bar must always be shown" [8].
  - On a log scale, `geom_bar` puts the base at 1 [8].
  - "never use stacked bars with a transformed scale, because scaling happens before stacking" [8].
- **Labels:** `geom_text` needs the same dodge width as the bars, and ggplot2 warns otherwise. Stacked labels use `position_stack(vjust = 0.5)` to sit at segment centres [12]. Matching the label and error-bar positions to the bars by hand is a known chore.

### matplotlib
- **Functions:** `bar` and `barh` take `width` (default 0.8, so the gap is 25% of bar width), `bottom` (used for stacking) and `align` [13].
  - They also take `xerr` and `yerr`, a shortcut for `errorbar`. `capsize` defaults to 0 [13].
- **Grouped bars:** `Axes.grouped_bar` (new in 3.11, API "still provisional") [14]:
  - takes `group_spacing` (default 1.5 bar widths between groups) and `bar_spacing` (default 0, so bars in a group touch);
  - has an `orientation` of vertical or horizontal;
  - accepts a DataFrame (index = categories, columns = datasets).
- **Value labels:** `Axes.bar_label` [15]:
  - `fmt` takes a %-style or {}-style format string, or a callable;
  - `label_type` is `edge` (shows the bar's end value) or `center` (shows the segment's length, for stacked bars);
  - `padding` is in points.

### seaborn
- **`barplot` aggregates:** `estimator='mean'` and `errorbar=('ci', 95)`, with `width` 0.8 and `gap` 0 [16].
  - The docs say a bar plot "shows only the mean (or other aggregate) value", and recommend `pointplot()` "for datasets where 0 is not a meaningful value" [16].
- **The 0.12 redesign:** the `errorbar` parameter replaced `ci` [17]. It has four methods, split two ways:
  - `sd` and `pi` show spread; `se` and `ci` show uncertainty in the estimate;
  - `sd` and `se` are parametric; `pi` and the bootstrap `ci` are nonparametric.
  - The tutorial ends: "Always look at the underlying distributions too" [17].

### Plotly
- **Layout settings:**
  - `layout.barmode` is one of `stack | group | overlay | relative`. `relative` stacks negative values below the axis and positive values above it [18][19].
  - `layout.barnorm` is `fraction | percent` [18].
  - `bargap` is the gap between locations and `bargroupgap` the gap within a group (default 0) [18].
- **Rows:** `px.bar` draws each row as one rectangle and doesn't aggregate. Rows that share an `x` are stacked by default, and `px.histogram` is the aggregating variant [19].
- **Value labels:** `text_auto` (a d3-format string), `texttemplate`, and `textposition` = `inside | outside | auto` [19].

### Datawrapper and Tableau
- **Datawrapper** offers bar variants as separate chart types [20]:
  - bar charts: bar, stacked bar, split bar, population pyramid, grouped bar and bullet bar;
  - column charts: column, stacked column and grouped column.
- **Datawrapper's bar options** are "Sort bars" (largest at top), "Reverse order", bar thickness, a value-label show/hide setting with alignment, and a number format [21].
- **Tableau** sets orientation by shelf. A category on Columns gives vertical bars and one on Rows gives horizontal bars. Its example aggregates the measure as SUM [22].

### What the tools share
| Concept | Vega-Lite | ggplot2 | matplotlib | Plotly |
| --- | --- | --- | --- | --- |
| One row per bar | no `aggregate` | `geom_col` | `bar` | `px.bar` |
| Side by side | `xOffset` channel | `position_dodge` | `grouped_bar` | `barmode` group |
| Stacked | `stack` zero | `position_stack` | `bottom` | `barmode` stack or relative |
| 100% stacked | `stack` normalize | `position_fill` | (by hand) | `barnorm` percent |
| Orientation | inferred from encodings | inferred, or `orientation` | `bar` or `barh`, `orientation` | `orientation` |
| Gap between bars (default) | paddingInner 0.1 | width 0.9 | width 0.8 | `bargap` |
| Bars within a group | touch (0) | touch | touch (0) | touch (`bargroupgap` 0) |

---

## 2. Best practice from the literature

**Bars start at zero.**
- Few: "Whenever you use bars, your quantitative scale must include zero"; when you need a narrowed scale, switch to points [23].
- Wilke: "Bars on a linear scale should always start at 0", and on a log scale "starting from 1, not 0" [24].
- Knaflic gives the same rule, and adds that the rule does not hold for line graphs [26].
- The ONS also requires it ("should always start from zero"), with a dot plot as the alternative [27].
- Recommendation: an axis minimum above 0 is an error that suggests xy with markers.

**Ordering.**
- Wilke: "If the bars represent unordered categories, order them by ascending or descending data values", but keep a natural order (age groups) where there is one [25].
- The ONS orders categories "from largest value to smallest" [27].
- Datawrapper defaults to spreadsheet order, with a "Sort bars" option [21].
- Recommendation: offer data order, label order and value order, with data order as the default. ForgeGraph can't know whether categories are ordered, so the agent chooses.

**Horizontal bars for long labels.**
- Few: horizontal bars work "especially well" when labels are long or there are many bars [23].
- Wilke: "The better solution for long labels is usually to swap the x and the y axis", rather than rotating labels [25].
- Knaflic gives the same advice [28].
- Datawrapper recommends switching from columns to bars rather than rotating labels [29].
- The ONS prefers horizontal bars generally, and vertical bars (columns) for time series [27].

**Bar width and gaps.**
- Few (2016) prefers gaps of 50–75% of bar width. Over 100% looks "exaggerated". His earlier book allowed 1:0.5 to 1:1.5 [30].
- Few also recommends that the longest bar be at least 10 times its width [30].
- These gaps are much wider than the tool defaults (see the table in §1).
- Recommendation: a theme default of about 0.6 × bar width, plus a lint check for "stubby" bars where the length/width ratio is under 10.

**Stacked, grouped or small multiples.**
- Cleveland & McGill found that comparing positions on a common scale is more accurate than comparing lengths. In their position-length experiment, judging segments inside stacked bars ranked worst [31]. Heer & Bostock replicated the ranking [32].
- Wilke: with stacked bars, "the different bars cannot be compared easily because they have different baselines". Stacking is appropriate when the total is meaningful, such as counts [25][33].
- Wilke also finds grouped bars "can be confusing", and suggests separate panels instead [25]. ForgeGraph does that with layouts in Phase 7.
- Few: "Use stacked bars only when you must display measures of the whole as well as the parts" [23].
- Datawrapper: stacked columns work for "compare the totals and one part of the total"; otherwise "consider split bars or small multiples" [34].
- **100% stacked bars** fit part-to-whole questions. Wilke shows relative proportions for that case [33], and Vega-Lite (`normalize`), ggplot2 (`position_fill`) and Plotly (`barnorm`) all support it [2][10][18].

**Value labels or an axis.**
- Few: tables (precise values) and graphs (shape) have different jobs [23].
- Datawrapper bar charts let value labels be shown or hidden, with alignment and a number format [21]. Datawrapper leaves axis titles out of bar charts because they would overlap the data [35].
- Matplotlib's `edge` / `center` distinction is a published convention: edge for the end value, center for a stacked segment's length [15].
- Plotly's `auto` puts a label inside if it fits, and outside otherwise [19].
- Recommendation: offer value labels, with labels inside a stacked segment showing that segment's value.

**Legends.**
- Few: "The more directly you can label data, the better". For grouped bars, arrange the legend entries in the same order as the bars [23].
- ggplot2 stacks in reverse group order so that the colours read in the same order as the legend [10].

**Dynamite plots (bars of means with error bars).**
- **The evidence:**
  - Weissgerber et al. (2015) reviewed 703 physiology papers. 85.6% had bar graphs, mostly mean ± SE. "Many different data distributions can lead to the same bar or line graph". They recommend univariate scatterplots for small samples, and box plots or histograms for larger ones. They also note that SE makes differences look larger than SD [36].
  - Riedel, Schulz, Kazezian & Weissgerber (2022): "Bar graphs combined with dot plots should be replaced", with a mean or median line plus error bars over a dot plot instead. "Bar graphs are intended to display counts or proportions" [37].
  - Nature Methods' editors and Streit & Gehlenborg: bars for counts, box plots for distributions, and mean-and-error points for 3–5 data points [38][39].
  - Irizarry: "Showing the data reveals more information" [40].
  - Weissgerber et al. (2019, Circulation) is a how-to primer [41].
- **What error bars should say:** Wilke: "Whenever you visualize uncertainty with error bars, you must specify what quantity" they show [42].
- **Recommendations:**
  - Bars plus error bars are fine for counts, totals and proportions.
  - For means of a few measurements, the skill should steer the agent to points with mean ± interval, using xy with a categorical x (the Phase 5 categories proposal) and later the Phase 11 `distribution` type.
  - Lint could warn when error bars sit on bars.

**Negative values.**
- Few: put the axis line at zero, and the axis labels outside the plot area [23].
- ggplot2 and Plotly (`relative`) stack negative and positive values separately [10][19].
- Recommendation:
  - Draw a zero baseline whenever the values cross zero.
  - Stack negative values downward.
  - Make normalized stacking with negative values an error, since a share of a mixed-sign total is undefined.

---

## 3. Aggregation: one row per bar

- **Tools that draw rows as given:** ggplot2 `geom_col`, Vega-Lite without `aggregate`, matplotlib `bar` and Plotly `px.bar` [8][43][13][19].
- **Tools that aggregate:** ggplot2 `geom_bar` (counts), seaborn `barplot` (mean with bootstrap CI), Tableau (SUM in its example) and `px.histogram` [8][16][22][19].
- **Duplicate rows:** Plotly draws rows with the same x as stacked rectangles without saying so [19]. Vega-Lite also stacks by default when a non-position channel holds an unaggregated field [2].
- **Recommendation:** adopt the `geom_col` model.
  - The DataFrame has one row per bar: category, value, and optionally a group.
  - A repeated (category, group) pair is an error that names the rows and says to aggregate first, rather than silently stacking them. This follows ForgeGraph's "error, don't fall back" rule.
  - The skill does the aggregation in pandas (the "weekly count by instrument" and "mean ± SEM" evals).
  - Error bars come from error columns, as the build plan says.

---

## 4. Recommended parameter set

### 4.1 Graph type `bar.yaml`
This is a sketch in xy.yaml's style. Shared concepts keep xy's names; new names are marked NEW.

```yaml
name: bar          # [text]; The name of the graph type.
version: 0          # [int]; The version number of the specification.
description: Draws one bar per row, a value for each category, optionally split into groups.          # [text]; ...
extends: None          # [None, graph type]; ...

fixed_parameters: None

variable_parameters:
    axis:
        x:
            data_column: None          # [column]; Horizontal axis column: categories for vertical bars, values for horizontal bars. A GraphSpec must set it.
            title: column_name          # [None, column_name, text]; Axis title.
            scale: linear          # [linear, log]; Value-axis scale. log: bars start at 1; not with stacked or normalized. A category axis takes linear only.
            min: None          # [None, float]; Value-axis minimum, at most 0 (1 on log). None: 0, or lowest value − plot_area.margin when values are negative.
            max: None          # [None, float]; Value-axis maximum. None: highest value + plot_area.margin, grown to fit outside value labels.
            order: data          # NEW [data, sorted, largest_first, smallest_first]; Category order, on the category axis only. sorted: by label, as encoding.order. largest_first: by value, or by total when grouped or stacked.
        y:
            (same as x)
    encoding:
        color: None          # [None, column]; Groups: one bar (or segment) per value of this column per category, in palette colors.
        order: sorted          # [sorted, data]; Group order (as xy).
    mark:
        bar:          # NEW
            orientation: auto          # [auto, vertical, horizontal]; auto: the axis whose column is text or categorical holds the categories; both or neither is an error that says to set this.
            arrangement: grouped          # [grouped, stacked, normalized]; How groups share a category: side by side; stacked, negative values downward; stacked to 100%.
    value_label:          # NEW
        show: false          # [true, false]; Write each bar's value on it.
        position: auto          # [auto, outside, inside]; outside: beyond the bar's end. inside: inside the end. auto: inside where it fits, else outside. Stacked segments are labelled at their centre. A label that fits nowhere is an error.
        format: None          # [None, text]; Number format, Python format-spec syntax (".1f", ",.0f", ".0%"). None: as the value axis's tick labels.
        total: false          # [true, false]; With stacked, also write each stack's total beyond its end.
    benchmark:          # as xy: the benchmark group or category drawn in series.benchmark color
        data_column: None
        value: None
    legend:          # as xy
        method: auto          # [auto, direct, key, none]
        key:
            title:
                text: column_name
```

**Why each parameter is shaped this way:**

- **axis.x / axis.y as in xy.** Vega-Lite and ggplot2 both use x/y and infer orientation from them, and ggplot2 superseded `coord_flip` in favour of swapping x and y [1][8][11]. Tableau does the same with shelves [22]. Keeping x/y means title, min, max and scale mean the same in xy and bar. The alternative is in §6, question 1.
- **min ≤ 0 and log bars starting at 1.** These follow [23][24][26][27][8]. Log axes are refused with stacking, following ggplot2 [8].
- **order.** Vega-Lite's `sort` offers data order (`null`), natural order and by-value order, with sum as the op for stacked bars [5]. Datawrapper has "Sort bars" [21], and Wilke's and the ONS's rules are in §2 [25][27]. Two naming notes:
  - Vega-Lite's word is `sort`. ForgeGraph's xy already uses `order` for group order, so `order` keeps ForgeGraph consistent with itself.
  - Vega-Lite's own `order` channel means stack order.
- **mark.bar.orientation.** This is Vega-Lite's `mark.orient`, plus the orientation flags in matplotlib, Plotly and seaborn [1][14][19][16]. `auto` follows the inference in Vega-Lite, ggplot2 and Tableau. The ambiguous case (a numeric category such as a year) is an error, never a guess.
- **mark.bar.arrangement.** No single standard term exists: Vega-Lite splits this between `xOffset` and `stack`, ggplot2 calls it `position` and Plotly `barmode`. The values follow those tools [2][4][9][10][18].
  - Overlaid bars (Vega-Lite `stack: null`, Plotly `overlay`) are left out, because they hide bars.
  - Diverging bars (Vega-Lite `center`) are left out for now.
- **value_label.** This follows Plotly's `textposition` (inside, outside, auto), matplotlib's `bar_label` (`label_type`, `fmt`) and Datawrapper's show, alignment and number format [19][15][21].
  - Python format-spec syntax suits matplotlib's `fmt` [15]. d3-format, used by Vega-Lite and Plotly, is "modeled after Python 3's format specification mini-language" [44].
  - This should be the same syntax as the Phase 5 tick-label proposal.
  - Labels in "auto" are placed or the graph errors, like legend methods. That is ForgeGraph's rule, and Plotly's `auto` is the precedent [19].
  - `total` for stacked bars matches common practice: it is the value Few and Datawrapper say stacked bars exist to show [23][34].
- **encoding.color.** This defines the groups. In ForgeGraph, colour and the side-by-side offset are the same column. Vega-Lite allows them to differ (`xOffset` alongside `color`) [4], but the simpler rule covers the common case.
  - `color_type: continuous`, `line_style`, `marker_*` and `detail` don't apply to bars.
  - `detail` would mean several bars per category and colour, which is the duplicate-row case and is refused.
- **benchmark and legend.** These are shared with xy for consistency.
  - The direct legend method needs bar-specific placement rules (§6, question 6).
  - The key order should follow the bar order and the stack order, per Few and ggplot2 [23][10].
- **Error bars** stay a layer, as the build plan says. The bar renderer must expose each bar's geometry (centre, end and width after grouping) so the `error_bar` layer and value labels line up automatically. The ggplot2 dodge-width chore is the problem this avoids [12].

### 4.2 Theme additions (`default.yaml`, a `bar:` heading)
Under D5, style values never live in a graph type, so everything below is look and goes in the theme.

```yaml
fixed_parameters:
    bar:
        gap: 0.6          # [float ≥ 0]; Gap between neighbouring categories' bars, × bar width.
        group:
            gap: 0          # [float ≥ 0]; Gap between bars within a group, × bar width.
            category_gap: 1.0          # [float ≥ 0]; Gap between groups, × bar width.
        edge:
            color: None          # [None, hex color]; Bar outline. None: none.
            width: 0.05          # [positive float]; × base size.
        corner_radius: 0          # [float ≥ 0]; Rounding of the value end, × base size.
        baseline:
            line_width: 0.08          # [positive float]; Line at 0 (1 on log) when values cross it, × base size.
        category_ticks: false          # [true, false]; Ticks on the category axis.
        color: first          # [first, hex color]; Single-series bar color: the palette's first, or this.
        value_label:
            size: 0.9          # [positive float]; × base size.
            gap: 0.25          # [positive float]; Gap from bar end, × base size.
            inside_color: auto          # [auto, hex color]; auto: black or white by contrast with the bar.
```

**Where the defaults come from:**

- **gap 0.6:** Few's range of 0.5–0.75 [30], against the tool defaults of 0.11–0.25 [3][8][13].
- **group.gap 0:** every tool lets bars within a group touch by default [3][9][14][18].
- **category_gap 1.0:** between Vega-Lite's doubled inner padding with grouping [3] and matplotlib's 1.5 [14].
- **corner_radius 0:** Vega-Lite's default [1].
- **baseline:** Few's axis line at zero [23].
- **category_ticks false:** a category axis has nothing to measure. Tufte notes ticks there act only as pointers to bar names [45]. This is a judgement call.

**What stays variable:** probably only `grid.show`, as now. Value-label and gap values are house style.

**Sizing many horizontal bars:** Vega-Lite sizes this case by step (`height: {step: 17}`) [1]. ForgeGraph's format has `height: auto` with `plot_area.aspect`, so many categories may need a step-based height. See §6, question 12.

### 4.3 Lint candidates
- **Stubby bars:** the longest bar is under 10 times its width [30].
- **Error bars on bars:** a dynamite-plot warning; see §6, question 9 [36][37].
- **Too many groups:** the existing too-many-groups check applies to bar colours.
- **Overlapping or clipped value labels:** the existing text checks apply.

---

## 5. Presets

### How tools package reuse
- **Look only, never data mapping:**
  - Vega-Lite `config` is "a consistent theme", with per-mark sections (`config.bar`, `config.line`) and named `style`s [46].
  - Altair treats top-level config as "a sort of theme for the whole chart" [47].
  - Plotly templates hold `layout` and per-trace-type defaults (`template.data.bar`) and combine with "+". They don't set data mappings [48].
  - ggplot2 themes customise "the non-data components of your plots" [49].
- **Recipes:** the ggplot2 book's reusable components, lists of layers and whole-plot functions that return a plot [50].
  - seaborn `relplot(kind="scatter" | "line")` is one function, where the kind picks `scatterplot` or `lineplot` [51].
  - Plotly line charts are "implemented as connected scatterplots", drawn as `go.Scatter` with a `mode` [52].
  - So `scatter` vs `line` is a mark choice on one underlying type. That is exactly xy + `mark.line.show` / `mark.marker.show`.

### Recommendation for `scatter` and `line`
```yaml
# graphspecs/scatter.yaml
name: scatter
description: Points only: y against x, without lines.
variable_parameters:
    specifications:
        graph_type: xy
    mark:
        line:
            show: false
        marker:
            show: true

# graphspecs/line.yaml
name: line
description: Lines only: y against x, joined in x order, without markers.
variable_parameters:
    specifications:
        graph_type: xy
    mark:
        line:
            show: true
        marker:
            show: false
```

**Rules for presets:**

- **Marks only.** They should not set `theme` or `format`. Resolve applies `extends` after the theme and format, so a preset naming `theme: default` would override a project's house theme. Plotly, Vega-Lite and ggplot2 all keep look out of recipes [46][48][49].
- **No theme variable parameters,** such as `series.marker.size`, for the same reason: the theme owns those defaults.
- **No columns or titles.** Those come from the data, and would make the preset a domain preset (like `acme/polarization-curve`), which is a pack's job.
- **Leave out `connect_order: x` and `missing_values: drop`** for `line`. They are already xy's defaults, so repeating them only creates a second source.
- The default xy (lines plus markers) stays the unnamed default. That is Few's "points connected by lines" [23].
- **No bar presets** (`stacked_bar`, `horizontal_bar`). Each would be one parameter. Datawrapper's separate chart types are a UI convenience [20], not a model to copy.

---

## 6. Open questions for the owner

1. **Orientation model.**
   - (a) x/y with `orientation: auto`, as in Vega-Lite, ggplot2 and Tableau. This shares xy's vocabulary, but switching orientation means swapping two columns and their titles.
   - (b) `axis.category` / `axis.value` with an orientation flag, as in matplotlib, Plotly and seaborn. Switching is one parameter, but the axis names differ from xy.
   - I recommend (a).
2. **Name and values of `arrangement`.** ggplot2 says `position`, Plotly `barmode`, and Vega-Lite splits it into `stack` plus `xOffset`. Should overlay or diverging (`center`) ever be offered?
3. **Duplicate (category, group) rows.** Error (recommended), or stack them like Plotly and Vega-Lite?
4. **Log value axis.** Allow it with bars from 1, except when stacked (Wilke, ggplot2), or refuse log on bars entirely?
5. **Value labels and the value axis.** When every bar is labelled, should the theme hide the value axis (Datawrapper style), or always keep it?
6. **Direct legend for grouped or stacked bars.** What placement rules (for example, beside the last category's segments), or key only for v0?
7. **Value order with groups.** For grouped bars, sort categories by total, or by one named group?
8. **Number format syntax.** Python format-spec, shared with the Phase 5 tick proposal? And should normalized bars show 0–100%?
9. **Dynamite plots.** Should lint warn on error bars over bars of means? Should the skill steer "mean ± SEM per condition" to points plus an interval rather than bars? That eval is the pattern the literature argues against [36][37]. Should the `error_bar` layer require saying what the bars show (SD, SE or 95% CI) [42]?
10. **Gaps.** One theme gap or the three proposed (category, within group, between groups)? The default of 0.6 × bar width follows Few, against the tools' 0.11–0.25.
11. **Preset files.** A preset omits required parameters (columns), and today `extends: None` means "lists every parameter". How do partial GraphSpecs validate? Does a preset named `scatter` risk being mistaken for a graph type in `forgegraph catalog`?
12. **Many horizontal bars.** Step-based plot height (as Vega-Lite does), or keep `plot_area.aspect`?
13. **Numeric colour on bars.** Is a continuous `encoding.color` with a colour bar needed in v0, or should it be deferred?

---

## Sources
1. Vega-Lite, Bar mark. https://vega.github.io/vega-lite/docs/bar.html
2. Vega-Lite, Stack. https://vega.github.io/vega-lite/docs/stack.html
3. Vega-Lite, Scale (band padding, config defaults, zero). https://vega.github.io/vega-lite/docs/scale.html
4. Vega-Lite example, Grouped Bar Chart (xOffset). https://vega.github.io/vega-lite/examples/bar_grouped.html
5. Vega-Lite, Sort. https://vega.github.io/vega-lite/docs/sort.html
6. Vega-Lite example, Bar chart with labels. https://vega.github.io/vega-lite/examples/layer_bar_labels.html
7. Vega-Lite, Error bar. https://vega.github.io/vega-lite/docs/errorbar.html
8. ggplot2, geom_bar / geom_col. https://ggplot2.tidyverse.org/reference/geom_bar.html
9. ggplot2, position_dodge / dodge2. https://ggplot2.tidyverse.org/reference/position_dodge.html
10. ggplot2, position_stack / fill. https://ggplot2.tidyverse.org/reference/position_stack.html
11. ggplot2, coord_flip (superseded). https://ggplot2.tidyverse.org/reference/coord_flip.html
12. ggplot2, geom_text (labelling dodged and stacked bars). https://ggplot2.tidyverse.org/reference/geom_text.html
13. matplotlib, Axes.bar. https://matplotlib.org/stable/api/_as_gen/matplotlib.axes.Axes.bar.html
14. matplotlib, Axes.grouped_bar (3.11, provisional). https://matplotlib.org/stable/api/_as_gen/matplotlib.axes.Axes.grouped_bar.html
15. matplotlib, Axes.bar_label. https://matplotlib.org/stable/api/_as_gen/matplotlib.axes.Axes.bar_label.html
16. seaborn, barplot. https://seaborn.pydata.org/generated/seaborn.barplot.html
17. seaborn, Statistical estimation and error bars. https://seaborn.pydata.org/tutorial/error_bars.html
18. Plotly, layout reference (barmode, barnorm, bargap, bargroupgap). https://plotly.com/python/reference/layout/
19. Plotly, Bar charts in Python. https://plotly.com/python/bar-charts/
20. Datawrapper Academy, Bar charts. https://www.datawrapper.de/academy/category/bar-charts ; Column charts: https://www.datawrapper.de/academy/category/column-charts
21. Datawrapper Academy, Customizing your bar chart. https://www.datawrapper.de/academy/customizing-your-bar-chart
22. Tableau Help, Build a Bar Chart. https://help.tableau.com/current/pro/desktop/en-us/buildexamples_bar.htm
23. Few, S. (2005). Effectively Communicating Numbers (white paper based on *Show Me the Numbers*). https://www.perceptualedge.com/articles/Whitepapers/Communicating_Numbers.pdf
24. Wilke, C. *Fundamentals of Data Visualization*, ch. 17 "The principle of proportional ink". https://clauswilke.com/dataviz/proportional-ink.html
25. Wilke, ch. 6 "Visualizing amounts". https://clauswilke.com/dataviz/visualizing-amounts.html
26. Knaflic, C. N., "bar charts must have a zero baseline". https://www.storytellingwithdata.com/blog/2012/09/bar-charts-must-have-zero-baseline
27. ONS Service Manual, Bar charts. https://service-manual.ons.gov.uk/data-visualisation/chart-types/bar-charts
28. Knaflic, "which bar chart orientation should I use?" https://www.storytellingwithdata.com/blog/2022/1/21/which-bar-orientation-should-i-use ; "my penchant for horizontal bar graphs" https://www.storytellingwithdata.com/blog/2012/10/my-penchant-for-horizontal-bar-graphs
29. Datawrapper Academy, How to create a column chart. https://www.datawrapper.de/academy/how-to-create-a-column-chart
30. Few, S. (2016). Bar Widths and the Spaces in Between. https://www.perceptualedge.com/articles/visual_business_intelligence/bar_widths.pdf
31. Cleveland, W. S. & McGill, R. (1984). Graphical Perception. JASA 79(387). https://doi.org/10.1080/01621459.1984.10478080
32. Heer, J. & Bostock, M. (2010). Crowdsourcing Graphical Perception. CHI. https://homes.cs.washington.edu/~jheer/files/2010-MTurk-CHI.pdf
33. Wilke, ch. 10 "Visualizing proportions". https://clauswilke.com/dataviz/visualizing-proportions.html
34. Datawrapper, What to consider when creating stacked column charts. https://www.datawrapper.de/academy/what-to-consider-when-creating-stacked-column-charts
35. Datawrapper Academy, Why many Datawrapper charts don't include axis labels. https://www.datawrapper.de/academy/why-datawrapper-does-not-include-axis-labels-for-many-charts
36. Weissgerber, T. L. et al. (2015). Beyond bar and line graphs. PLOS Biology 13(4): e1002128. https://pmc.ncbi.nlm.nih.gov/articles/PMC4406565/
37. Riedel, N., Schulz, R., Kazezian, V. & Weissgerber, T. (2022). Replacing bar graphs of continuous data with more informative graphics. Clinical Science. https://pmc.ncbi.nlm.nih.gov/articles/PMC9366861/
38. Nature Methods editors, "Bring on the box plots" (Methagora blog). https://blogs.nature.com/methagora/tag/data
39. Streit, M. & Gehlenborg, N. (2014). Bar charts and box plots. Nature Methods 11, 117. https://doi.org/10.1038/nmeth.2807
40. Irizarry, R. (2019). Open letter to journal editors: dynamite plots must die. https://simplystatistics.org/posts/2019-02-21-dynamite-plots-must-die/
41. Weissgerber, T. L. et al. (2019). Reveal, Don't Conceal. Circulation. https://mayoclinic.elsevierpure.com/en/publications/reveal-dont-conceal-transforming-data-visualization-to-improve-tr-2
42. Wilke, ch. 16 "Visualizing uncertainty". https://clauswilke.com/dataviz/visualizing-uncertainty.html
43. Vega-Lite, Aggregate. https://vega.github.io/vega-lite/docs/aggregate.html
44. d3-format documentation. https://d3js.org/d3-format
45. Tufte, E., Tick marks in graphs (notebook). https://www.edwardtufte.com/notebook/tick-marks-in-graphs/
46. Vega-Lite, Config. https://vega.github.io/vega-lite/docs/config.html
47. Altair, Customizing Visualizations (global config as theme). https://altair-viz.github.io/user_guide/customization.html
48. Plotly, Theming and templates. https://plotly.com/python/templates/
49. ggplot2, theme(). https://ggplot2.tidyverse.org/reference/theme.html
50. Wickham, H. et al. *ggplot2* book, ch. "Programming with ggplot2". https://ggplot2-book.org/programming.html
51. seaborn, relplot. https://seaborn.pydata.org/generated/seaborn.relplot.html
52. Plotly, Scatter plots in Python. https://plotly.com/python/line-and-scatter/

**Not verified in a primary source, so not used:** the ONS style guide's specific rules on direct value labels and gaps, which sit on a Notion page that didn't render. Plotly's default `bargap` value was also not used, because the reference shows two entries.
