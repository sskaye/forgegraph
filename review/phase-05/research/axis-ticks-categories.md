# Axis ticks and categories: research for the phase 5 proposal

Input for the phase 5 proposal "axis ticks and categories". Every claim about another tool gives its source; the sources are listed at the end, by number.

## 0. Where ForgeGraph stands today (from the repository)

- `xy.yaml` gives each axis `data_column`, `title`, `scale` [linear, log], `min` and `max`. Nothing sets tick positions, steps or label text.
- `render/xy.py` rejects an x column that isn't numbers or dates ("isn't numbers or dates"). Number axes use `NiceTicks(axis.tick.algorithm)` with matplotlib's default number labels. Date axes use `_DateTicks` (AutoDateLocator, capped by the room on the axis) with `_DateLabels` (ConciseDateFormatter, with ForgeGraph's offset fix). Log axes use `LogTicks` with `_LogLabels`.
- **Label fitting differs by axis kind.** Only `LogTicks` measures its labels: it asks for one tick fewer while the drawn labels would overlap or come within `axis.tick.label.gap`. Linear axes and date axes get a count from the axis length alone (`ticks.target`: matplotlib's `get_tick_space`, clamped to 2–10). They never measure the labels, so a longer format could overlap there. Lint's `overlapping-text` is the only backstop.
- **Why months 1–12 got 2.5, 5, 7.5.** Talbot's Q list in `extended_wilkinson` is (1, 5, 2, 2.5, 4, 3). On the axis range 0.45–12.55 with a target of 5 or 6 labels, it returns 0, 2.5, 5, 7.5, 10, 12.5 (reproduced locally). With Q = (1, 5, 2) it returns 0, 3, 6, 9, 12 for a target of 5, and 0, 2, …, 12 for 6. D3 uses only 1, 2 and 5 times a power of ten [d3-ticks], so it would have given whole numbers here. The fix for whole-number data is a minimum step, not a different algorithm (§5.4).
- **Naming constraints:** parameters are nested snake_case; "a mapping inside a category is a sub-category"; "no path is a prefix of another, across kinds"; Vega-Lite's term is used where one exists. The theme already owns `axis.tick.*` and `axis.tick.label.*` (style); the graph type owns `axis.x.*` and `axis.y.*`.
- **One consequence of the grammar matters below:** a parameter whose *value* is a mapping (e.g. `{1: Jan, 2: Feb}`) would be read as a sub-category. A value-to-label map therefore needs either a grammar change or a different shape (§5.2).

## 1. How established tools set tick positions and labels

| Tool | Positions | Step / count | Label format | Labels for given values | Categories and order |
|---|---|---|---|---|---|
| **Vega-Lite** | `axis.values`: "Explicitly set the visible axis tick values" [vl-axis] | `axis.tickCount` (a desired count; "the resulting number may be different so that values are 'nice'"); `axis.tickMinStep`: "the minimum desired step between axis ticks, in terms of scale domain values" [vl-axis] | `axis.format` + `formatType` (`number`, `time`, or a custom type); d3-format for numbers, d3-time-format for dates [vl-format] | `axis.labelExpr`, a Vega expression over `datum.value` and `datum.label` [vl-axis]; e.g. `monthAbbrevFormat(m)` formats a zero-based month number "according to the current locale" [vega-expr] | Field `type`: quantitative, temporal, ordinal, nominal [vl-type]. x/y default to a `band` scale for bar, rect and rule marks, `point` for the others [vl-scale]. `sort`: ascending (default), descending, `null` (data order), an explicit array (listed values first, the rest after in their original order), or by another channel such as `"-y"` [vl-sort]. `scale.domain` gives an explicit list of valid values [vl-scale]. `timeUnit: month` gives "January, February, etc." [vl-timeunit] |
| **ggplot2 / scales** | `breaks`: NULL, `waiver()` (automatic), "a numeric vector of positions", or a function of the limits [gg-cont] | `n.breaks` ("an integer guiding the number of major breaks") [gg-cont]; `scales::breaks_width(width, offset)`, numeric or "1 month" style for dates [sc-width] | `labels` as a function: `label_number`, `label_percent`, `label_date`, `label_date_short`, `label_wrap`, `label_dictionary` ("labels from lookup tables") [sc-index] | `labels`: a character vector the same length as `breaks` [gg-cont]; a named vector maps level to label on discrete scales [gg-disc] | `scale_x_discrete(limits=)`: "a character vector that defines possible values of the scale and their order"; data outside the limits is dropped with a warning; `drop` controls unused factor levels; `na.translate` shows or removes NA [gg-disc]. `guide_axis(n.dodge, check.overlap, angle)` [gg-guide] |
| **matplotlib** | `FixedLocator`: "Place ticks at a set of fixed values" [mpl-ticker] | `MultipleLocator`: "every integer multiple of a base plus an offset"; `MaxNLocator(integer=True)`: "ticks will take only integer values" [mpl-ticker] | `StrMethodFormatter` (`str.format` spec) [mpl-ticker]; `DateFormatter` (strftime) [mpl-dates] | `FixedFormatter` ("should only be used together with FixedLocator. Otherwise, the labels may end up in unexpected positions"); `FuncFormatter` [mpl-ticker] | Strings can be passed directly since 2.1 [mpl-21]; `matplotlib.category` maps "unique categorical values" to integer ids [mpl-cat] at 0, 1, 2… in order of first appearance (shown by its examples; the docs don't state the rule) [mpl-catex] |
| **Plotly** | `tickmode: array` + `tickvals` [plotly-axis] | `dtick` (a step; for dates `"M<n>"`, n months) + `tick0`; `nticks` (a maximum) [plotly-axis] | `tickformat`: "d3 formatting mini-languages which are very similar to those in Python" [plotly-axis] | `ticktext`, parallel to `tickvals` [plotly-axis] | One `type` for the axis: linear, log, date, category, multicategory, inferred from the data by default; `categoryorder` (trace, category ascending/descending, array, or by total/mean/… of the values) + `categoryarray`; `tickangle: auto` takes the first of [0, 30, 90] "large enough to prevent label overlap" [plotly-axis] |
| **Datawrapper** | "Custom ticks" field [dw-dates] | automatic by default [dw-ticks] | Own token syntax: numbers `0,0`, `0.[00]`, `0a`, `0%` [dw-num]; dates `M`/`MM`/`MMM`/`MMMM`, `Q`, `ddd`/`dddd`, literal text in `[ ]` [dw-datefmt] | none (the data is the label) | Column charts rotate labels when there are many, which "makes reading the chart much harder"; for long names it recommends switching to a bar chart [dw-column] |
| **Flourish** | "Custom: specify individual ticks", listed as they appear in the data [fl-ticks] | "Auto" (fits the space) or "Number" (approximate count; numbers and dates only) [fl-ticks] | n/a | n/a | Long labels are wrapped to a maximum line count, default 2 [fl-wrap] |

**Which model is simplest and most declarative for a YAML spec.** Every tool converges on four independent knobs: *explicit positions*, *a step*, *a format string*, and *labels for given positions*. Plotly's model is the most declarative: data only, no functions or expressions (`tickvals` + `ticktext` + `dtick` + `tickformat`). It is also the closest to ForgeGraph's rule that rendering a spec never runs code. Vega-Lite's `labelExpr` and ggplot2's label functions are expressions or code, so they don't fit. Vega-Lite contributes the names (`values`, `format`) and `tickMinStep`; ggplot2 contributes `breaks_width`'s "1 month" step form for dates; matplotlib supplies the implementation for each knob (FixedLocator, MultipleLocator, StrMethodFormatter, DateFormatter, FixedFormatter).

## 2. Number and date format syntax

- **Numbers.** d3-format "is modeled after Python 3's format specification mini-language (PEP 3101)" [d3-format]. Its form is `[[fill]align][sign][symbol][0][width][,][.precision][~][type]`, against Python's `[[fill]align][sign]["z"]["#"]["0"][width][grouping][.precision][type]` [py-format]. Vega-Lite [vl-format] and Plotly [plotly-axis] both use d3-format. Python has no `~` (trim insignificant zeros), `s` (SI prefix) or `$` currency symbol. Its `g` type already drops trailing zeros [py-format]. Its `n` type is locale-dependent, and "the default locale is not the system locale" [py-format].
- **Dates.** d3-time-format is "an approximate JavaScript implementation of the venerable strptime and strftime functions from the C standard library" [d3-time]; `%b %B %a %A %m %d %Y %y` mean the same in both. `%q` (quarter) is d3-only. Python's strftime: `%a`, `%b` and `%B` follow the current locale, and "the full set of format codes supported varies across platforms, because Python calls the platform C library's strftime()" [py-dt]. Examples are `%-d` and other padding modifiers.
- **CLDR/LDML patterns** (`MMM`, `MMMM`, `EEE`, with separate "format" and "stand-alone" month forms for languages that inflect month names) [cldr-dates] are the localization standard. Python reaches them through Babel, whose patterns "are based on the Locale Data Markup Language specification" [babel]. Datawrapper's tokens are close to these [dw-datefmt].
- **Recommendation: one syntax family, Python's own.** Use Python format specs for numbers (`{:,.0f}` style without the braces, i.e. `,.0f`) and strftime for dates. That is what d3-format and d3-time-format were modelled on, so Vega-Lite and Plotly users already know it. It is native to the renderer (matplotlib's `StrMethodFormatter` and `DateFormatter`), so it needs no dependency. ForgeGraph should validate formats when it loads the spec and allow only a documented, platform-independent subset of directives (no `%-d`, no `n`), so the same spec draws the same text everywhere (principle 6, error-not-fallback). CLDR via Babel is the upgrade path if localized month names are ever needed; with explicit label text (§4) they aren't needed for the months case.

## 3. Categorical axes

- **Ordinal vs nominal.** Vega-Lite separates them: ordinal "represents ranked order", nominal "differentiates between values based only on their names" [vl-type]. On a position axis the drawing is the same; what differs is the *order*. Both sort ascending by default in Vega-Lite [vl-sort]. Plotly and matplotlib have a single category type [plotly-axis][mpl-cat]. So ForgeGraph can have one `categorical` axis kind plus an order parameter, without an ordinal/nominal split.
- **Ordering.** Wilke: "if the bars represent unordered categories, order them by ascending or descending data values". Where there is a natural order (age groups, income brackets), "we should retain that ordering" [wilke-amounts]. The tools offer: sorted, data order, explicit list, by value [vl-sort][plotly-axis][gg-disc]. For a DataFrame input there is a fourth, free source: a pandas `Categorical` holds its `categories` in a defined order, and "Order is defined by the order of categories, not lexical order of the values" [pandas-cat]. Sorting a Categorical column sorts by that order, so `sorted` already respects it (Jan…Dec if the agent made the column a Categorical). This fits the DataFrame input contract: getting the order into the data is data preparation.
- **Missing and unexpected categories.**
  - *Absent from the data but listed* (an explicit list, or unused levels of a pandas Categorical [pandas-cat]): ggplot2 drops unused factor levels by default (`drop = TRUE`) [gg-disc].
  - *In the data but not listed*: Vega-Lite appends them after the listed ones [vl-sort]; ggplot2 drops them with a warning [gg-disc].
  - *NaN*: ggplot2 shows NA as a category unless `na.translate = FALSE` [gg-disc].
  - ForgeGraph's rules point to: a listed value absent from the data gets an empty slot (the list is a deliberate request); a value in the data but not in the list is an error naming it; NaN rows are dropped and counted (as `mark.line.missing_values` and the `dropped-rows` lint already do).
- **Long labels: rotation vs wrapping vs horizontal bars.**
  - Wilke: "I am not a big proponent of rotated labels"; "the better solution for long labels is usually to swap the x and the y axis" [wilke-amounts].
  - Datawrapper says rotated labels make "reading the chart much harder" and recommends a bar chart for long names [dw-column].
  - The EU Data Visualisation Guide calls wrapping "not a very elegant solution", says rotated text "should be avoided", and says "horizontal bar charts do not suffer from the label overlap problem" [eu-bars]. Evergreen says the same [evergreen].
  - Cleveland's dot charts put category labels horizontally on the left axis for this reason [cleveland-mcgill, figure; Wikipedia summary in wiki-dot].
  - The tools' defaults go the other way: Vega-Lite's `labelAngle` defaults to −90 for nominal and ordinal fields [vl-axis-defaults]; Plotly auto-rotates [plotly-axis]; ggplot2 offers dodging and silent removal (`check.overlap`) [gg-guide]; Flourish wraps to 2 lines [fl-wrap].
  - I found no primary text from Stephen Few on this to cite.
- **Thinning.** Dropping every other label is fine on a number axis, but not on a nominal one, where each label names a mark. Vega-Lite's `labelOverlap` is `false` (no thinning) for nominal fields and parity or greedy otherwise [vl-axis]. ForgeGraph should never thin category labels.

## 4. Month and weekday names

- **Two separate cases:**
  - *Dates*: a datetime column. A format does it: `%b` (Jan–Dec), `%a` (Mon–Sun). Plotly `dtick: "M1"` + `tickformat: "%b"` [plotly-axis]; ggplot2 `date_breaks = "1 month"` + `label_date("%b")` [sc-width][sc-index]; Vega-Lite `timeUnit: month` [vl-timeunit].
  - *Numbers that stand for months or weekdays* (1–12, 0–6): no number format turns 12 into "Dec". Every tool uses explicit labels for given values: ggplot2 `breaks = 1:12, labels = month.abb` [gg-cont]; Plotly `tickvals` + `ticktext` [plotly-axis]; matplotlib FixedLocator + FixedFormatter [mpl-ticker]; Vega-Lite `labelExpr` with `monthAbbrevFormat(datum.value - 1)` [vega-expr].
- **A label map vs a format.** For the numbers case, a "labels for given values" mechanism is general (it also covers 1 → "Q1", 0 → "Control"), declarative, and locale-free, because the text is in the spec. A named format such as `month_abbrev` would cover only months and weekdays, and would pull in locale. The alternative is data preparation: the agent turns the column into dates, or into an ordered Categorical of names, and the axis is categorical. That needs no tick parameters but loses the numeric axis (lines, limits, reference lines at x = 6.5).
- **Locale.**
  - `%b` via Python follows the process's LC_TIME [py-dt]: a hidden input that breaks reproducibility. matplotlib's DateFormatter inherits this.
  - d3 and Vega default to US English unless a locale is set [d3-time][vl-config].
  - Proposal: ForgeGraph formats dates in English (the C locale) regardless of the process locale, and adds a theme-level locale only when a pack needs one (CLDR via Babel [babel]).

## 5. Recommended minimal parameter set

Six GraphSpec parameters per axis (variable, in the graph type file, so `axis.x.*` and `axis.y.*`), one change to an existing range, and a few theme parameters. Names follow the existing theme's `axis.tick.label.*` nesting, so a GraphSpec reads like the theme. The theme sets how ticks look; the GraphSpec sets where ticks go and what they say.

### 5.1 GraphSpec level (graph type: `axis.x.*`, likewise `axis.y.*`)

```yaml
axis:
    x:
        scale: auto          # [auto, linear, log, categorical]; Axis scale. auto: categorical for a text or pandas Categorical column, linear otherwise (dates: a calendar axis).
        order: sorted          # [sorted, data, values]; Category order (categorical scale only): sorted (a pandas Categorical's own order), as first seen, or as listed in tick.values.
        tick:
            values: None          # [None, numbers, dates, categories]; Where ticks go. None: the theme's algorithm.
            step: None          # [None, positive float, text]; Distance between ticks: a number, or for dates "N day(s)/week(s)/month(s)/year(s)". None: the theme's algorithm. Not with tick.values.
            label:
                format: None          # [None, text]; Number format (Python format spec, e.g. ",.0f") or date format (strftime, e.g. "%b %Y"). None: automatic.
                text: None          # [None, texts]; Label for each of tick.values, in order (e.g. Jan…Dec for 1…12). Needs tick.values, the same length.
```

| Parameter | Follows | Why |
|---|---|---|
| `axis.x.scale` gains `auto` and `categorical` | Plotly's single axis `type` (linear, log, date, category; inferred by default) [plotly-axis]; ForgeGraph's own `encoding.color_type: auto/categorical/continuous` | Adds no new parameter: text columns become categories automatically, and `categorical` forces numbers (years, months) to be categories. Vega-Lite would separate field `type` from `scale.type` (band/point) [vl-type][vl-scale]; `bar` vs `xy` can choose band vs point themselves, so users needn't. The default changes from `linear` to `auto`; existing specs draw the same. |
| `axis.x.order` | Vega-Lite `sort` [vl-sort]; Plotly `categoryorder` [plotly-axis]; ggplot2 `limits` [gg-disc]; the same words as ForgeGraph's `encoding.order` [sorted, data] | Wilke's two cases, natural order and by value [wilke-amounts]. `values` reuses `tick.values` as the explicit list, so no extra parameter (Plotly's `categoryarray` is the same idea). Ordering bars by value (`-y`) belongs to the `bar` graph type, not the axis. |
| `axis.x.tick.values` | Vega-Lite `axis.values` [vl-axis]; ggplot2 `breaks` [gg-cont]; Plotly `tickvals` [plotly-axis]; matplotlib FixedLocator [mpl-ticker] | Every tool has it; it's the answer for "ticks at 1, 6, 12" and the position half of Jan–Dec. On a categorical axis it is the category list (and order). |
| `axis.x.tick.step` | Plotly `dtick` [plotly-axis]; ggplot2 `breaks_width` / `date_breaks` [sc-width]; matplotlib MultipleLocator [mpl-ticker] | "Every 1", "every month", "every 5 years" without listing them. A date step is text in ggplot2's "1 month" form; a number step is a number. |
| `axis.x.tick.label.format` | Vega-Lite `axis.format` [vl-format]; Plotly `tickformat` [plotly-axis]; matplotlib StrMethodFormatter / DateFormatter [mpl-ticker][mpl-dates] | Thousands separators, decimals, percent, `%b` on dates. One string, Python syntax (§2). |
| `axis.x.tick.label.text` | Plotly `ticktext` [plotly-axis]; ggplot2 `labels` vector [gg-cont]; matplotlib FixedFormatter (with FixedLocator only) [mpl-ticker] | Jan–Dec for 1–12. A list parallel to `tick.values`, not a map, because a mapping value would be read as a sub-category under ForgeGraph's grammar (§0). A different length is an error. |

The months eval becomes:

```yaml
axis:
    x:
        data_column: month
        tick:
            values: [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12]
            label:
                text: [Jan, Feb, Mar, Apr, May, Jun, Jul, Aug, Sep, Oct, Nov, Dec]
```

A date column instead needs `tick.step: "1 month"` with `tick.label.format: "%b"`, and a text column of month names needs either an ordered pandas Categorical in the data or `order: values` with `tick.values: [Jan, …, Dec]`.

**Leaner alternatives, if six is too many:**

- *Merge `values` and `text` into one map*: Jan–Dec becomes a single parameter, but it needs a grammar rule for mapping-valued parameters. Only ggplot2's named vector and `label_dictionary` work this way [gg-disc][sc-index].
- *Drop `step`*: whole-number data is handled by §5.4, so `step` is then only a convenience over `values`. It remains the only way to say "every 3 months" without listing dates.
- *Drop `order`*: the order then comes only from the data (a pandas Categorical) or from `tick.values`.

### 5.2 Interactions with automatic ticks and label fitting

1. **Precedence.** `tick.values` > `tick.step` > the theme's algorithm. Setting both `values` and `step` is an error (as matplotlib, Plotly's `tickmode` and ggplot2 each take one at a time).
2. **Explicit ticks are never thinned.** With `values` or `step` set, if the labels overlap or come within `axis.tick.label.gap`, rendering fails with a message naming the remedies (fewer values, a larger step, a shorter format, the theme's wrap). This is D5's rule for series labels: a method fits cleanly or reports that it can't, with no silent fallback. Vega-Lite would hide labels instead (`labelOverlap`) [vl-axis].
3. **Automatic ticks use the measured fit everywhere.** A `format` changes label widths, so the count-from-length rule on linear and date axes can overlap where it couldn't before. Generalise `LogTicks._fits` (already measured with the axis's own formatter) to `NiceTicks` and `_DateTicks`: ask for one tick fewer until the formatted labels fit, as log axes do now.
4. **Category labels are never thinned** (Vega-Lite's nominal default [vl-axis]); they go through the theme's tick-label methods (§5.3), and if none fits, the error suggests a horizontal bar or shorter names.
5. **Format replaces the automatic labels entirely.** With `format` set on a date axis, there is no ConciseDateFormatter offset label (the format says what it shows); on a linear axis, no matplotlib offset or scientific multiplier.
6. **Limits.** `tick.values` outside `axis.x.min`/`max` (or the data range plus margin) — ggplot2 drops breaks outside the limits; options are error, drop, or extend the axis to the outermost value (owner decision, §6).
7. **Log axes.** `values` and `format` apply; `step` on a log axis is an error (or means a multiple of decades; owner decision).
8. **Layout and lint** need no change: the layout already measures the drawn tick labels, and `overlapping-text` and `clipped-text` remain the backstop.

### 5.3 Theme level (style, fixed by default)

- **`axis.tick.label.methods: [horizontal, wrap]`** [horizontal, wrap, rotate]: ways to fit category labels, in order of preference, the same pattern as `legend.methods`. `rotate` is available but left out of the default theme, following Wilke, Datawrapper and the EU guide [wilke-amounts][dw-column][eu-bars]; a pack that wants Vega-Lite's or Plotly's behaviour can list it.
- **`axis.tick.label.wrap.max_lines: 2`**: Flourish's default [fl-wrap]; wrapping at word boundaries like `scales::label_wrap` [sc-index].
- **`axis.tick.label.rotate.angle: 90`**: used only if `rotate` is listed (Plotly tries 30 then 90 [plotly-axis]; Vega-Lite uses −90 [vl-axis-defaults]).
- **Whole-number columns get whole-number ticks** (§5.4): theme or built-in.
- **Locale** (§4): fixed English unless a theme sets one.
- **Category ticks**: whether a categorical axis draws tick marks at all (bar charts often don't), and padding between bands (Vega-Lite `paddingInner`/`paddingOuter`). These belong with the `bar` theme parameters.
- **Not theme-level**: positions, steps, formats and label text vary per graph, so they are GraphSpec parameters, as `axis.x.min` already is. A theme-wide default number format (e.g. always thousands-separated) is possible later as a variable theme parameter. Vega-Lite has `config.numberFormat` and `config.timeFormat` for exactly this [vl-config].

### 5.4 Whole-number data

The months eval would have got 0, 2, 4… without any new parameter if steps below 1 were barred on integer-dtype columns. This is matplotlib's `MaxNLocator(integer=True)` and Vega-Lite's `tickMinStep: 1` [mpl-ticker][vl-axis], applied automatically. In Talbot's search it amounts to skipping candidate steps under 1 when the column's dtype is an integer. Making it automatic (or a fixed theme parameter, `axis.tick.whole_numbers: true`) fixes the common case with zero GraphSpec parameters. The label text (Jan–Dec) still needs §5.1.

## 6. Open questions for the owner

1. **Six parameters, or fewer?** Keep `step` and `order`, or rely on whole-number detection and the data's Categorical order?
2. **Value→label: parallel lists or a map?** A map is one parameter and can't get out of step, but it needs a grammar rule for mapping-valued parameters.
3. **`axis.x.scale: auto/categorical` (Plotly's model, no new parameter) or a separate `axis.x.type`** (Vega-Lite's model)? And should ordinal vs nominal ever be distinguished?
4. **Explicit tick values outside the axis range:** error, drop, or extend the axis?
5. **Labels for explicit ticks that don't fit:** an error (consistent with D5), or are explicit ticks the user's responsibility, so lint warns and the graph is drawn?
6. **Should `rotate` ever be in the default theme's `axis.tick.label.methods`?** The cited guidance says no; Vega-Lite and Plotly rotate by default.
7. **Whole-number ticks on integer columns: automatic, or a theme parameter?** Some integer columns are measurements (counts in the thousands) where it never matters; a column of 0/1 would get ticks only at 0 and 1.
8. **Format syntax:** Python's spec and strftime (native, the base of d3's), or d3's own (identical for Vega-Lite and Plotly users, with `~` and `s`, but needing a port)?
9. **Locale:** English only for now, or a theme `locale` with Babel/CLDR from the start?
10. **Categories absent from the data but in the list (or unused Categorical levels):** show an empty slot or omit? Values in the data but not in the list: an error, or appended as Vega-Lite does?
11. **Is a categorical x valid for `xy`** (points at categories, lines joining them in category order), or only for `bar`? Months as categories on a line plot is legitimate for ordinal data, but meaningless for nominal data.
12. **Do date steps need an offset** (ggplot2's `breaks_width(offset=)`, Plotly's `tick0`) for fiscal years and similar, or is that left out until requested?

## Sources

- [vl-axis] Vega-Lite, Axis: https://vega.github.io/vega-lite/docs/axis.html
- [vl-axis-defaults] same page, labelAngle "Default value: -90 for nominal and ordinal fields; 0 otherwise"; tickCount default ceil(width/40): https://vega.github.io/vega-lite/docs/axis.html
- [vl-format] Vega-Lite, Format: https://vega.github.io/vega-lite/docs/format.html
- [vl-sort] Vega-Lite, Sort: https://vega.github.io/vega-lite/docs/sort.html
- [vl-type] Vega-Lite, Type: https://vega.github.io/vega-lite/docs/type.html
- [vl-scale] Vega-Lite, Scale: https://vega.github.io/vega-lite/docs/scale.html
- [vl-timeunit] Vega-Lite, Time Unit: https://vega.github.io/vega-lite/docs/timeunit.html
- [vl-config] Vega-Lite, Config (numberFormat, timeFormat, locale): https://vega.github.io/vega-lite/docs/config.html
- [vega-expr] Vega, Expressions (monthFormat, monthAbbrevFormat, dayFormat): https://vega.github.io/vega/docs/expressions/
- [gg-cont] ggplot2, scale_x_continuous: https://ggplot2.tidyverse.org/reference/scale_continuous.html
- [gg-disc] ggplot2, scale_x_discrete: https://ggplot2.tidyverse.org/reference/scale_discrete.html
- [gg-guide] ggplot2, guide_axis: https://ggplot2.tidyverse.org/reference/guide_axis.html
- [sc-width] scales, breaks_width: https://scales.r-lib.org/reference/breaks_width.html
- [sc-index] scales, reference index (label_* functions): https://scales.r-lib.org/reference/index.html
- [mpl-ticker] matplotlib.ticker: https://matplotlib.org/stable/api/ticker_api.html
- [mpl-dates] matplotlib.dates: https://matplotlib.org/stable/api/dates_api.html
- [mpl-cat] matplotlib.category: https://matplotlib.org/stable/api/category_api.html
- [mpl-catex] matplotlib, Plotting categorical variables: https://matplotlib.org/stable/gallery/lines_bars_and_markers/categorical_variables.html
- [mpl-21] What's new in matplotlib 2.1.0 (string categorical values): https://matplotlib.org/3.4.1/users/prev_whats_new/whats_new_2.1.0.html
- [plotly-axis] Plotly, layout.xaxis reference: https://plotly.com/python/reference/layout/xaxis/
- [d3-format] d3-format: https://d3js.org/d3-format
- [d3-time] d3-time-format: https://d3js.org/d3-time-format
- [d3-ticks] d3-array ticks: https://d3js.org/d3-array/ticks
- [py-format] Python, Format Specification Mini-Language: https://docs.python.org/3/library/string.html#format-specification-mini-language
- [py-dt] Python, strftime() and strptime() format codes: https://docs.python.org/3/library/datetime.html#strftime-and-strptime-format-codes
- [cldr-dates] Unicode TR35 part 4, Dates: https://unicode.org/reports/tr35/tr35-dates.html
- [babel] Babel, Date and time formatting: https://babel.pocoo.org/en/latest/dates.html
- [pandas-cat] pandas, Categorical data: https://pandas.pydata.org/docs/user_guide/categorical.html
- [dw-num] Datawrapper, Number formats: https://www.datawrapper.de/academy/custom-number-formats-that-you-can-display-in-datawrapper
- [dw-datefmt] Datawrapper, Date formats you can display: https://www.datawrapper.de/academy/custom-date-formats-that-you-can-display-in-datawrapper
- [dw-dates] Datawrapper, How to work with dates: https://www.datawrapper.de/academy/how-to-work-with-dates-and-times
- [dw-ticks] Datawrapper blog, New axis ticks: https://www.datawrapper.de/blog/new-axis-ticks
- [dw-column] Datawrapper, How to create a column chart: https://www.datawrapper.de/academy/how-to-create-a-column-chart
- [fl-ticks] Flourish, How to edit axis ticks and labels: https://helpcenter.flourish.studio/hc/en-us/articles/8827970677391-How-to-edit-axis-ticks-and-labels
- [fl-wrap] Flourish, Customize line breaks in tick labels: https://helpcenter.flourish.studio/hc/en-us/articles/8761553430927-How-to-customize-the-line-breaks-in-your-tick-labels
- [wilke-amounts] Claus O. Wilke, Fundamentals of Data Visualization, ch. 6 "Visualizing amounts": https://clauswilke.com/dataviz/visualizing-amounts.html
- [eu-bars] EU Data Visualisation Guide, Vertical versus horizontal bars: https://data.europa.eu/apps/data-visualisation-guide/vertical-versus-horizontal-bars
- [evergreen] Stephanie Evergreen, Graph Text Should Be Horizontal: https://stephanieevergreen.com/graph-text-should-be-horizontal/
- [cleveland-mcgill] Cleveland & McGill, "Graphical Perception", JASA 79(387):531–554, 1984: https://www.jstor.org/stable/2288400 (dot charts with horizontal labels on the left axis)
- [wiki-dot] Wikipedia, Dot plot (statistics), on Cleveland's dot chart: https://en.wikipedia.org/wiki/Dot_plot_(statistics)
- Talbot, Lin & Hanrahan 2010 (extended Wilkinson; Q list) is already cited in src/forgegraph/render/ticks.py.

Not verified: a primary statement by Stephen Few on rotated labels (none found online); the matplotlib category ordering rule (first appearance) is shown by its examples but not stated in its API docs.
