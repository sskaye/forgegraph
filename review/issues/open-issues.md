# Open issues

Last updated: 11/07/26

## [#116](https://github.com/sskaye/forgegraph/issues/116): show or hide a series or a reference layer in HTML output

- **Filed by:** CoryONeill, from electrochemistry screening dashboards of about 64 graphs per page. Unlike #36, it comes from real use.
- **Summary:** a button for each series and each reference layer that shows or hides it on every graph on the page, without rescaling the axes. Rendering every combination would take 12 renders per graph.
- **Verification:** confirmed. The HTML page shows each figure as an SVG inside an `<img>`, so neither the page's style nor its script can reach anything inside the image. The author draws the figure, sets ids on the artists by hand, and adds buttons to a page of their own (#119 says it has its own tabs, toolbar and pickers).
- **Proposal:** one of:
  1. Build #117 now, and hold this one. #117 gives the author's own buttons a reliable way to find each series and layer, which removes the fragile part of the workaround. We then ask whether they would use buttons on ForgeGraph's page at all.
  2. Build #117 and this one together: a format parameter such as `output.toggles` adds the buttons to ForgeGraph's page. The script would rewrite each image's SVG with a style that hides the chosen ids, as the `<img>` keeps each figure's ids separate. Hiding a series would have to hide its readouts too. I haven't tried this, and a page of 64 images would rewrite all 64 on each click.

  Recommendation: 1. The author's page is their own, so built-in buttons may never be used, and 1 costs nothing if they turn out to be wanted later.
- **View controls (#116 and #118):** you asked for a simple, modular way to let a reader change the view, as a layer. How other tools do it:
  1. **Tableau:** filters and parameters appear as controls beside a view: one value from a list, a dropdown or a slider; several values as checkboxes; a range as a slider. Clicking a legend entry highlights its marks.
  2. **Plotly:** clicking a legend entry hides its trace, and double-clicking shows only that one. Buttons and dropdowns change which traces show, or change the layout, and sliders step through frames.
  3. **Vega-Lite:** values bound to radio buttons, dropdowns, checkboxes or sliders, and legends that select.

  All three draw in the browser, so a control can redraw anything. ForgeGraph draws with matplotlib before the page is opened, so a control can only choose among images drawn ahead of time. That gives two kinds of control, each a new layer type:
  1. A **toggle** layer lists the series and layers a reader can hide; by default, every series. The figure is drawn once, then each listed series or layer is also saved on its own as a transparent image laid exactly over it, and the page shows or hides those. The key's entries are the buttons, as in Plotly, and a listed layer gets a button of its own. The axes don't rescale, which #116 accepts. It costs one extra image for each item listed, not one for each combination.
  2. A **choice** layer names views, each a set of changes to the GraphSpec, such as another y column and title. ForgeGraph draws each view, and the page shows a dropdown or buttons. Two choice layers, one for x and one for y, draw every pair.

  In a layout, controls of the same name stay in step across tiles, as nested tabs do. A PNG or PDF shows the first view, with everything shown. One of:
  1. Both, choice first, as it reuses the tabs' way of switching images, then toggle, which needs a trial of laying images exactly over each other.
  2. A second drawing engine, such as Plotly, for HTML. Controls could then redraw anything, rescale axes and filter data. But every theme, format, label rule and lint check would have to be written again for it, and a graph would look different in HTML than in a PNG.

  Recommendation: 1. It keeps one drawing engine and one look, and each control stays small. If you agree, I'll propose the two layer types as specifications.
- **Drawing in the browser instead:** controls that switch images ForgeGraph has drawn (pre-drawn), against a library such as Plotly or Vega-Lite drawing in the reader's browser.
  1. **Pre-drawn, for:** one drawing engine, so the HTML page, PNG, PDF and SVG are the same drawing. Themes, formats, the placement of keys and labels, lint and provenance all apply as they are. Little new code, since tabs already switch images. It's tested as today, with image baselines and the catalog, and an agent can look at each view as a PNG. A page needs no library and works offline.
  2. **Pre-drawn, against:** only the views drawn ahead of time are possible, and they multiply (four x choices by four y choices is 16 images), so the page grows with the number of views. There are no continuous filters such as a date slider, no zooming or panning, and a hidden series doesn't rescale the axes.
  3. **In the browser, for:** any interaction: filters on ranges, rescaling, zooming, linked views. The data is sent once, so the page grows with the data, not with the views. Legend toggles and hover come built in.
  4. **In the browser, against:** everything visual has to be written a second time. That means mapping each theme and format to the library, and ForgeGraph's own rules for placing keys, direct labels, value labels and reference labels, which the libraries don't have. The same goes for reference layers, equation lines, error bar aggregations and grid cells, and every new feature thereafter. The HTML page and the PNG or PDF of one graph would look different. Lint, image tests and an agent's look at the PNG wouldn't see what the reader sees. Each page carries the library (about 3.5 MB for Plotly, under 1 MB for Vega-Lite) and the whole DataFrame, and shows nothing without scripts.

  Recommendation: pre-drawn. Most of what ForgeGraph offers is its look and its placement rules, and a second engine would mean keeping two copies of them. Drawing in the browser is worth revisiting if requests need continuous filters, zooming, or more combinations than can be drawn ahead of time.
- **Decision:** view controls drawn ahead of time by matplotlib, as two layer types: choice first, then toggle after a trial of laying images over each other. #118 is covered by the choice layer. The proposed specifications are review/issues/specs/layer_choice.md and layer_toggle.md, with the changes to the xy graph type and the example GraphSpec as comments on their pages in docs/specifications/.
- **Specifications:** agreed, with the choice control's values named `dropdown` and `radio`.

## [#117](https://github.com/sskaye/forgegraph/issues/117): name each series and layer in SVG output

- **Filed by:** CoryONeill.
- **Summary:** each drawn element in an SVG says which series or layer it belongs to, so that a page can style, hide or script it. The author now matches artists by color, which works only because every series and band has its own color.
- **Verification:** confirmed on a test graph. The groups are named `line2d_1`, `patch_2` and so on. Every reference layer's parts share the id `forgegraph-reference-line`, so layers can't be told apart, and that id is repeated within one file. Nothing names a series.
- **Proposal:** each artist's group gets an id that names its owner when the SVG is saved: `forgegraph-series-<name>-<n>` for a series' line, markers, bars, error bars, value labels and direct label, `forgegraph-layer-<name>-<n>` for a layer's lines, fill and label, and `forgegraph-key-<name>` for a key's entry. A page finds a whole series with a selector on the start of the id. There is no new parameter. The ids are set only while saving, because the drawing code uses its present ids to find what it drew.

  The issue's example has one group holding a whole series, with `class` and `data-series`. A series and a layer can be drawn between each other's parts, so one group for each would change the drawing order, and matplotlib writes only an id. So I propose one id for each part rather than one group.

  Recommendation: this proposal.
- **Naming:** the prefix isn't needed in a separate SVG file. On a page holding many inline SVGs, ids share one namespace with each other and with the page's own, so a short prefix keeps them from clashing. I propose `fg-`: `fg-series-0.1-1`, `fg-layer-baseline_2-1`, `fg-key-0.1`.
- **Decision:** the proposal, with the prefix `fg-`.

## [#118](https://github.com/sskaye/forgegraph/issues/118): let the reader choose an axis's column in HTML output

- **Filed by:** CoryONeill.
- **Summary:** two dropdowns on the page choose the columns for x and y, from four metrics. The author renders a GraphSpec for each of the 12 ordered pairs, for each electrode and view, and adds dropdowns of their own. The page is about 3 times larger and the build about 3 times slower.
- **Verification:** confirmed that a GraphSpec has one column for each axis. A layout can already do this without new code: a tab for each x column, holding a tab for each y column. Switching x keeps the same y where it exists, and otherwise shows the first, so the missing diagonal is handled. The size and build time come from drawing each pair ahead of time, which the issue accepts, so `choices` wouldn't reduce them.
- **Proposal:** one of:
  1. No change. The guide to layouts gets a short example of choosing axes with nested tabs.
  2. `axis.x.data.choices`, as the issue suggests. ForgeGraph would draw each pair from one GraphSpec and show two dropdowns. This saves writing the 12 GraphSpecs, but adds a second way of switching views to the tabs, along with the rule for an x and y that match.
  3. Drawing in the browser, which would remove the extra size. It would mean a second drawing engine, so I wouldn't consider it.

  Recommendation: 1. It meets the need with what exists, and the author's page has its own dropdowns anyway.
- **View controls:** a choice layer, under #116, does this: one choice layer for x and one for y, each listing the four metrics as views.
- **Decision:** the choice layer under #116.

## [#119](https://github.com/sskaye/forgegraph/issues/119): hover readouts for graphs embedded in another page

- **Filed by:** CoryONeill.
- **Summary:** the readouts' data for graphs placed on the author's own page, along with #128, which asks for the marks and their data rows for an app. The author now re-renders each GraphSpec, reads the artists' positions from matplotlib, and writes a hover script.
- **Verification:** confirmed. `forgegraph.drawing.readout.marks` finds this data, but it isn't public, so anyone using it depends on ForgeGraph's internals. The script is written into ForgeGraph's own page and looks for an `<img>`, so it wouldn't work on an inline SVG as it stands. #80 left a public record of the marks out until someone needed it outside an HTML page, and now someone does.
- **Proposal:** #119 and #128 are one change. `Graph.marks()` returns a list with one item for each data point drawn, and `Graph.plot_area` gives the plot's box. Each item has:
  - its series' name and x and y values;
  - where it is, as fractions of the figure from the top left;
  - its marker's radius, or for a bar or cell, its box;
  - its readout's lines, as (name, value) pairs;
  - the positions in the data of the rows it was drawn from: one for a plain point, several for an aggregated one.

  With row positions, two rows at the same x and y can be told apart, and a caller can look up an id column itself. The script, one of:
  1. Leave it out. The author keeps their own, which already works.
  2. Add `forgegraph.hover_script()`, or an `html_fragment` output, which the issue offers as alternatives. The script would have to work on an inline SVG as well as an `<img>`.

  Recommendation: 1. The data is what the author can't get reliably, and a public script would be one more thing to keep stable. For now this covers a `Graph`, and a layout's tiles can follow if someone asks.
- **Why the author needs it:** the readouts work only on ForgeGraph's own HTML page. The author puts 64 to 96 graphs on a page of their own, with the toolbar, pickers and toggles that our page lacks, so our readouts never reach them. Their workaround reads matplotlib's internals. If our page gains the view controls under #116, the author may be able to use it, and this need goes away. #128 is for an app that edits graphs, which #131 leaves for Studio.

  Recommendation (revised): hold #119 and #128 until the view controls are decided.
- **Decision:** decline for now, and #128 with it, as it's the same change.

## [#120](https://github.com/sskaye/forgegraph/issues/120): clip reference lines and bands at the axis limits

- **Filed by:** CoryONeill.
- **Summary:** a band that reaches past a set axis limit is drawn up to the edge of the plot, instead of stopping the graph with an error. The author now cuts each band to the axis range before writing the spec, and leaves out any that fall entirely outside.
- **Verification:** reproduced on 0.7.0 with a band from 25 to 67 and `axis.y.max: 50`: "layers.c.line_2: the line at 67 is outside axis.y.max; move the line or the limit". The band can be drawn, but the error protects against a mistyped value, or a limit that hides a line the author expects to see.
- **Proposal:** one of:
  1. A new layer parameter, `clip` (true or false, default false). With true, a band is filled up to the plot's edge, with no line at the cut side. A line outside the limits isn't drawn, nor is its label, and a layer with nothing left to draw gets a lint issue.
  2. Always clip, with a lint issue and no error. This needs no parameter, but it turns an error into a warning that can go unseen, against the rule that a request ForgeGraph can't carry out is an error.

  Recommendation: 1. The GraphSpec then asks for clipping, so nothing is substituted for what was asked. The issue's idea of an arrow at the cut side can wait for a request. A label at a chosen position that reaches past a set limit stays an error.
- **Decision:** no parameter. A line, or the part of a band, outside a set limit isn't drawn, and lint says so. A line that isn't drawn has no label. A label at a chosen position that reaches past a set limit stays an error.

## [#121](https://github.com/sskaye/forgegraph/issues/121): when a reference label's auto position has no room

- **Filed by:** CoryONeill.
- **Summary:** a crowded graph fails when a reference line's label has nowhere to go. The author catches the error and tries each position, then the band's other line, and finally leaves the label off with a warning, which can take 14 renders of one graph.
- **Verification:** reproduced on 0.7.0 with 400 points across the plot. `auto` already tries all six positions, so trying them one by one can't succeed where `auto` failed. A list of positions, which the issue offers, would add nothing to this. Only moving to the other line or giving up on the label would.
- **Proposal:** a new label parameter, `if_no_room`, one of:
  1. `error` (the default) and `drop`. `drop` draws the line without its label and adds a lint issue, so the graph says what's missing.
  2. As 1, and `overlap`, which draws the label at the first position regardless. It would need a background to be readable, and that's a new look to tune.
  3. As 1, and `other_line`, which moves a band's label to its other line before giving up.

  Recommendation: 1. The GraphSpec asks for it, so nothing is substituted silently, and it ends the repeated renders. 2 and 3 can follow if dropped labels turn out to matter.
- **Decision:** no parameter. The error says that all six positions were tried and what's in the way at each, that trying them one at a time won't help, and what to do. For example: "layers.c.line_1.label.position: auto, but none of the six positions beside the line is clear (end_above covers the data, …); trying them one at a time won't find another. Make room (widen the axis or the format, or shorten the label), or leave the label out with label.text: None".

## [#122](https://github.com/sskaye/forgegraph/issues/122): axis limits from a reference group's mean ± k standard deviations

- **Filed by:** CoryONeill.
- **Summary:** an axis that stops at a control group's mean ± 8 standard deviations, so that a few far outliers don't squash the data, but only where that's narrower than the automatic range. The author's scripts work out the control's statistics, reproduce ForgeGraph's own range to find the narrower of the two, and write it as a fixed limit, which also stops the axis growing for a key.
- **Verification:** confirmed. `axis.y.min` and `max` are fixed values, and a set limit stays where it is when a key needs room (#112). Points beyond a set limit already get the lint issue `outside-limits`. The statistics are easy to compute. What's hard is reproducing the automatic range and keeping the room for a key.
- **Proposal:** one of:
  1. New parameters `axis.x.auto_min`, `auto_max` and the same for y: the furthest the automatic limit may go. ForgeGraph works out its automatic range and narrows it to these values, and a key can still extend the axis. Setting `auto_max` together with `max` is an error. The caller computes the mean ± 8 standard deviations.
  2. The issue's `limit` block, which names the rows, the aggregation and the offset. ForgeGraph computes the statistics itself, but this adds a way of selecting rows, which belongs with data preparation and is outside ForgeGraph.

  Recommendation: 1. It moves the hard part into ForgeGraph and leaves the statistics with the caller. A reference line beyond `auto_max` would widen the axis only up to that value, and past it follows #120: an error, unless the layer sets `clip`.
- **Without a parameter:** `min` and `max` would take a rule as well as `auto` and a number. A rule only narrows the automatic range, so a key can still extend the axis. One of:
  1. `max: 8SD`, the mean plus 8 standard deviations of the values on the axis, as you suggest. A far outlier raises the standard deviation it's measured against, though. In a test with one outlier among normal values, the cut never removed it with 64 values or fewer, however far away it was.
  2. `max: 3IQR`, the upper quartile plus 3 × the interquartile range (Tukey's fence for far outliers, as box plots use), and `min: 3IQR` the lower quartile minus it. Quartiles barely move for an outlier, so in the same test it was removed at every count, and normally distributed values are never cut.
  3. Both.

  Recommendation: 2. It does what the rule is for, at any number of points. The author's own rule uses a control group's statistics. That would still need a number from the author, which fixes the limit, but 2 may serve them as well.
- **Decision:** 2. `min` and `max` take `auto`, a number or a rule such as `3IQR`, which only narrows the automatic range.

## [#123](https://github.com/sskaye/forgegraph/issues/123): geometric mean, SD and CI

- **Filed by:** CoryONeill, for ratio data that varies by a factor.
- **Summary:** aggregated points, error bars and reference bands worked out on the log scale. On a log axis, an arithmetic mean and CI are skewed, and a lower bound can go below 0. The author now computes these and passes them as columns and fixed values, which can't work for rows ForgeGraph aggregates itself.
- **Verification:** confirmed. `combine` and `spread` in drawing/layers.py are arithmetic. An error bar has one aggregation for its distances, and an offset is added to the aggregate, whereas a geometric SD multiplies and divides. So the two sides of a geometric error bar differ, and the readout already writes that as −a / +b.
- **Proposal:** one of:
  1. A new parameter of the aggregation style, `scale` (linear or log, default linear). With log, the function works on the values' logs, and the result is turned back: `mean` is the geometric mean, `stddev` the geometric SD and `ci` the CI of the mean in log terms. An offset's multiplier then acts in log terms, so −1 × `stddev` divides by the geometric SD. Values of 0 or below are an error, as is `sum`. `median`, `min`, `max` and `percentile` give the same result on either scale.
  2. New functions, as the issue shows: `geometric_mean`, `geometric_stddev`, `geometric_ci`. These read plainly, but they add three names and cover only those three functions.

  The functions, for positive values y₁ … yₙ with logs lᵢ = ln yᵢ, mean l̄ and standard deviation s of the logs:
  1. The geometric mean is exp(l̄).
  2. The geometric SD is exp(s), a factor: one geometric SD either side is exp(l̄) ÷ exp(s) to exp(l̄) × exp(s).
  3. The 95 % CI of the geometric mean is exp(l̄ ± t₀.₉₇₅,ₙ₋₁ × s / √n), the usual CI worked on the logs and turned back.

  They're right sometimes: when the values are positive and vary by a factor, so that their logs are roughly normal. Examples are concentrations, ratios and fold changes, and currents spanning orders of magnitude. For ratios, they also treat A/B and B/A alike. They're wrong when values can be 0 or below, when errors add rather than multiply, or when the question is about the arithmetic mean, such as a total. The geometric CI is for the typical, or median, value, not for the arithmetic mean. Neither option chooses for the user: both are a choice made in the GraphSpec.

  Recommendation: 1. It's one parameter, it works wherever an aggregation is used, and it matches the issue's alternative. An aggregate and its offset would have to use the same scale, and a mismatch is an error. The readout would need a word for it, such as 95%CI (geometric).
- **Decision:** 2, named `geom_mean`, `geom_stddev` and `geom_ci`: the data's being on a log axis isn't a reason to change what a function means. As an offset, `geom_stddev` and `geom_ci` multiply and divide rather than add: an offset of `geom_stddev` with multiplier k gives the aggregate × exp(s)^k. As error bars, they give each side its own distance, which the readout writes as −a / +b.

## [#124](https://github.com/sskaye/forgegraph/issues/124): widen the tick step when auto tick labels run together

- **Filed by:** CoryONeill.
- **Summary:** a wide axis fails because its automatic tick labels run together. The author catches the error and writes a manual step of about 4 ticks.
- **Verification:** reproduced on 0.7.0 at −150000 to 160000 in `compact_format`. The issue's own −1500 to 1600 fits at that format, so its graph was probably narrower. The automatic ticks are counted by the labels' height, not their width, as `check_fit` in drawing/axes.py notes. On a log axis, `LogTicks` already asks for one tick fewer when its labels come too close.
- **Proposal:** one of:
  1. With `tick.algorithm: auto` on a number axis, the algorithm is asked for fewer ticks until the labels fit. There is no new parameter, and no lint issue. Two ticks that still don't fit stay an error, as do `all`, `manual` and a categorical axis.
  2. A new parameter, `if_crowded: widen`, as the issue shows.

  Recommendation: 1. `auto` asks ForgeGraph to choose the ticks, so choosing ones that fit is what was asked for, and log axes already do it. A categorical axis stays an error, because thinning it further would leave most names unwritten without saying so.
- **Decision:** 1.

## [#125](https://github.com/sskaye/forgegraph/issues/125): wrap or shrink a title that doesn't fit

- **Filed by:** CoryONeill.
- **Summary:** long titles built from data stop the whole graph, and the error doesn't say that the title is the cause.
- **Verification:** reproduced on 0.7.0. In `compact_format`, a 50-character title draws and a 60-character one fails, with "size: too small for the titles, tick labels and keys around the plot box; make the format larger or its base font smaller". The issue's 109-character title also fails in `wide_format`. A line break written in the title already works, but a title built from data can't know where to put one.
- **Proposal:** the error names what doesn't fit, such as "the title is 620 pt wide and the figure 400 pt". For the title itself, one of:
  1. A new theme parameter, `title.max_wrap`, like `axis.tick.label.max_wrap`: a title wider than the figure wraps between words onto up to that many more lines. I'd default it to 1. A title that still doesn't fit is the error above.
  2. The issue's `title_fit` (wrap, shrink, ellipsis) in each GraphSpec. Shrinking changes a size the theme sets, and an ellipsis loses words without an error.

  Recommendation: 1. It follows how tick labels already wrap, loses nothing, and changes nothing for titles that fit. In a layout, I'd need to check that a wrapped title in one tile leaves the plots in its row lined up.
- **Decision:** 1, with `title.max_wrap` defaulting to 0, so titles don't wrap unless a theme asks, and the error naming the title.

## [#126](https://github.com/sskaye/forgegraph/issues/126): size, color, shape and opacity for single points

- **Filed by:** CoryONeill, for an app where a reader picks out single measurements.
- **Summary:** one point made bigger, recolored, reshaped or faded, without changing the rest of its series. The author moves the point's value into a new column and draws that as its own series, which needs the key turned off (#127), breaks a line at the point, and doesn't work on an aggregated series.
- **Verification:** confirmed. `marker.size` and `opacity` take one number per series, and a column is an error. A color column doesn't set a color either, because each of its values takes the next palette color, so a chosen color for one point isn't possible that way. Copying the value into the new column, instead of moving it, would keep the line whole and draw the highlight on top.
- **Proposal:** one of:
  1. Hold this one, and build #127. A highlight is then a second series, drawn from a copied column and left out of the key. This doesn't cover an aggregated series.
  2. Let `marker.size` and `opacity` take a column whose values are the sizes and opacities themselves. This doesn't cover a chosen color.
  3. The issue's `points` block, with styles for each row by an id column. This covers everything asked, but it's a second way of styling that every mark type has to respect.

  Recommendation: 1. It meets the stated need with one small parameter. The rest comes from the app in #131, whose controls belong with Studio. If aggregated highlights turn out to matter, 3 is the one to consider.
- **Revised, with #127 declined:** a highlight belongs in a layer, as you say. If this is wanted, it would be a new layer type that draws chosen rows again on top, picked by an id column, with its own marker size, color, shape and opacity, and never in the key. It works for an aggregated point too, if it picks by the point's rows.

  Recommendation (revised): hold, and build the highlight layer if someone asks again.
- **Decision:** hold. A highlight layer is built if someone asks again.

## [#127](https://github.com/sskaye/forgegraph/issues/127): leave a series out of the key

- **Filed by:** CoryONeill.
- **Summary:** a series that's drawn but not named, such as a highlight or helper series.
- **Verification:** reproduced on 0.7.0: a helper series named `__pt0` appears in the key. The only choice is to drop the whole key.
- **Proposal:** a new series parameter, `legend.show` (true or false, default true). With false, the series is left out of the key and gets no direct label. It's still in a readout, under its name. The code already has this case, because a series colored on a scale has no name to label.

  Recommendation: this proposal.
- **Examples:** the cases I can think of are better done another way:
  1. A highlight: a layer, as you say (see #126).
  2. All the data in light grey behind a highlighted group: the grey series is better named, such as "Other runs", so the key explains it.
  3. Raw points and their mean drawn as two series colored by the same column: the key already shows each group once.

  Recommendation (revised): decline.
- **Decision:** decline, unless the author's examples show otherwise.

## [#128](https://github.com/sskaye/forgegraph/issues/128): drawn marks and the plot area from the Python render

- **Filed by:** CoryONeill.
- **Summary:** where each mark is drawn and which row of data it came from, for an app with hover readouts, right-clicks and per-point editing. Matching points back to rows by their values fails when two rows share an x and a y.
- **Verification:** confirmed. See #119.
- **Proposal:** the same change as #119: `Graph.marks()` and `Graph.plot_area`.

  Recommendation: build it with #119 and close both.
- **Decision:** decline for now, with #119.

## [#129](https://github.com/sskaye/forgegraph/issues/129): smaller SVG output

- **Filed by:** CoryONeill, for a 96-graph page that came to 17.7 MB against a host's limit of 16 MB.
- **Summary:** shorter coordinates and no whitespace in SVG output. The author does this with regular expressions, and got the page to 14.5 MB with no visible change.
- **Verification:** measured on a graph of 170 points and a band, 79 kB. Removing whitespace saves about 6 %, and rounding coordinates to 2 decimals about 5 %. The metadata block, 14 % of that file, is ForgeGraph's provenance record, so removing it means `load` can no longer recover the GraphSpec. A setting for that already exists: on a smaller graph, `provenance.level: minimal` took the file from 47 kB to 39 kB.
- **Proposal:** one of:
  1. Always write SVG with coordinates to 2 decimals and no whitespace between tags, with no new parameter. It saves about 10 %, and 1/100 of a point can't be seen at any normal size. The docs point to `provenance.level` for pages where size matters most.
  2. Parameters for `precision` and `minify`, as the issue shows. These allow 1 decimal, which saves about 1 % more, but they are two settings no one needs to think about otherwise.

  Recommendation: 1. It helps every SVG and every HTML page, which holds SVGs. I'd check by drawing the files before and after, because I've only measured their sizes.
- **Revised:** the code is small, about 15 lines rewriting the SVG text, but it's one more thing to keep working through matplotlib upgrades, for 10 %. The author's page needed under 10 % to fit their limit, and `provenance.level: minimal` saves more than that today: 18 % on the 47 kB graph above.

  Recommendation (revised): decline, and point the author to `provenance.level`.
- **Decision:** decline.

## [#130](https://github.com/sskaye/forgegraph/issues/130): one setting for a graph's mark type

- **Filed by:** CoryONeill.
- **Summary:** `marks: scatter`, `line`, `line_markers` or `bar` in place of setting `line.show`, `marker.show` and `bar.show` on each series.
- **Verification:** confirmed that each mark type can be drawn, and that switching means setting up to three values on each series. It adds no new drawing, only a shorter way to write it, and the need comes from the reader-facing control in #131.
- **Proposal:** one of:
  1. Decline. You rejected scatter and line presets in the phase 5 review, because two fixed parameters are just as easy. A caller's code sets the three values on each series in a short loop.
  2. A GraphSpec parameter, `marks`, as the issue shows. It would need a rule for a series that sets its own marks.

  Recommendation: 1, unless a real use appears from someone writing GraphSpecs by hand.
- **Decision:** decline.

## [#131](https://github.com/sskaye/forgegraph/issues/131): reader edits saved as an overrides file

- **Filed by:** CoryONeill.
- **Summary:** a reader adjusts a graph on the page (axis range, chart type, markers, single points), and the changes are kept in a small file applied on top of the GraphSpec, so a rebuild keeps them. The author has built a local app that does this.
- **Verification:** confirmed that the HTML page is read-only and that a GraphSpec has no such file. `extends` can layer one GraphSpec on another, but it names a GraphSpec in a pack, not a file beside it. A Python app can already apply its overrides to the GraphSpec before calling `fg.render`, which is what this one does. This is close to what the architecture plans for Studio (D14): a local app whose options panel changes a graph, and which writes the result back to the spec. Studio comes after everything else works.
- **Proposal:** one of:
  1. No change for now. The file stays with the app that writes it. `Graph.marks()` (#119, #128) and the named SVG (#117) give that app what it can't get otherwise, and the page's controls wait for Studio.
  2. A GraphSpec parameter, `overrides`, naming a file that's applied last, with no controls on the page. This saves an app a few lines, but it adds a second way to layer specs beside `extends`.
  3. As 2, with controls on the page that download the file or post it to a URL. This starts Studio inside the HTML page, ahead of its turn.

  Recommendation: 1. It keeps Studio's work in its place and still helps this author directly. This author's app is a useful source of requirements when Studio comes up, so it's worth keeping these issues in mind for then.
- **Decision:** 1, no change.

## [#132](https://github.com/sskaye/forgegraph/issues/132): key and note placed over a reference band instead of extending the axis

- **Filed by:** sskaye.
- **Summary:** on a scatter with a shaded band and a dashed line inside it, the key is placed on the band and across the line at 70, and a note sits on the line at 81. The axis isn't extended, even with `axis.max_extension: 1`. Lint reports the key, but not the note.
- **Root cause:** what a key, note or reference label must keep clear of is decided in `Obstacles.of` (drawing/labels.py). Lines count only when at least one series draws its lines. In a scatter, neither the reference lines nor the error bars' stems count, and a band's fill never counts, in any graph. The lint check `key-over-data` counts every line, so lint and placement disagree, and there is no lint check for a note. The flag seems to exist to skip series whose lines are hidden, but `_drawn_points` already skips a line drawn without a line style. So the flag's only effect is to let keys and notes cover reference lines and error bars in a scatter. It predates the refactoring in #11, and I couldn't find a decision behind it.
- **Verification:** reproduced on 0.7.0 with the issue's GraphSpec. On 0.6.1, with `tick.algorithm: manual` in place of `none`, which 0.6.1 doesn't have, the image is the same pixel for pixel, with the same lint. So I couldn't reproduce the 0.6.1 error the issue mentions.
- **Proposal:** one of:
  1. Every line drawn with a line style, and every band's fill, counts for keys, notes and reference labels, whether or not a series draws lines. A key or note that has no room then makes the axis grow, as #112 and #38 already do for data, or raises an error.
  2. Lines and fills stay coverable, and lint is made to agree: `key-over-data` leaves out reference lines and fills, and a note gets the same check.

  Recommendation: 1. A band and a line carry information, and the issue's expected image is what this gives. Some existing graphs will change, such as scatters whose key sits over a reference line. The visual changelog would show which, and a graph with no room would now raise an error instead of covering the line.
- **Decision:** 1.

## [#133](https://github.com/sskaye/forgegraph/issues/133): ticks on the part of an axis extended for keys and notes

- **Filed by:** sskaye, from spectra in an HTML dashboard, where readers asked why part of the axis has no ticks.
- **Summary:** when an axis grows to fit a key, note or label, the added part has no ticks or tick labels. Normalized absorbance is ticked to 1.0 and runs on, unticked, to the top.
- **Verification:** reproduced on 0.7.0 with the issue's GraphSpec: the y-axis grows from about 1.05 to about 1.1 for the note, and its ticks stop at 1.0. `grow_until` in drawing/labels.py keeps the axis's ticks on purpose, as its docstring says ("keep its ticks, since the extra room is for labels"). Setting `axis.y.max` by hand gives up the automatic fit.
- **Proposal:** a new theme parameter, `axis.tick.extension` (true or false), variable so that a GraphSpec can set it. With true, the ticks continue at the same step to the axis's new end, without choosing new ticks for the whole axis. That keeps 0, 0.2, … and adds 1.2 and 1.4, rather than switching to 0, 0.5, 1.0, 1.5. On a log axis, they continue at the same factor. The default in `forgegraph_default`, one of:
  1. true: readers see a finished axis, but existing graphs whose axis was extended change.
  2. false: nothing changes until a theme or GraphSpec asks for it.

  Recommendation: the parameter, defaulting to 1 (true). The question came from readers, and an unticked part of an axis looks like a mistake whoever is reading it. It changes only graphs whose axis was extended, and the visual changelog will show them. The extension also applies to an x-axis grown for direct labels or an equation line's label.
- **Decision:** no parameter. Extending an axis always extends its ticks, at the same step, to its new end.

## [#134](https://github.com/sskaye/forgegraph/issues/134): star and asterisk marker shapes

- **Filed by:** sskaye.
- **Summary:** `star` (a filled five-pointed star) and `asterisk` (an open six-armed one), for use in `marker.shape` and in a theme's `series.marker.shapes`, so that more conditions can each have a shape that's easy to tell apart.
- **Verification:** confirmed. `MARKERS` in drawing/style.py has circle, square, triangle_up, triangle_down, diamond, cross and plus, as matplotlib's o, s, ^, v, D, x and +. A star is matplotlib's `*`, a filled shape like the circle. An asterisk, `(6, 2, 0)`, is made of lines like `cross` and `plus`. Checking those turned up the bug under "Found while checking", which an asterisk would share.
- **Proposal:** add both to the shapes, in each list of allowed values. A star is drawn as the other filled shapes are. An asterisk is drawn as `cross` and `plus` will be once their bug is fixed: in the series' color, with nothing to fill, so `marker.fill` has no effect on it. A star looks smaller than a circle of the same `marker.size`, because its points are thin. I'd check that in the catalog before settling its size. Neither goes into the default theme's `series.marker.shapes`, so no existing graph changes.

  Recommendation: this proposal, together with the fix below.
- **Decision:** agreed, with the fix below.

## Found while checking

### Readouts on points that aren't drawn

- **Summary:** points beyond a set axis limit aren't drawn, but their readouts are still on the HTML page. Pointing at the empty margin above the plot can show the values of a point that isn't there. This is what #119 means by skipping them by hand.
- **Root cause:** `_of` in drawing/readout.py keeps every point with a finite position, without checking that it's inside the plot. A bar's box isn't cut at the limit either.
- **Verification:** found on 0.7.0 with 170 points and `axis.y.max: 30`. 72 points are above the plot and all have records, 7 of them on the image, in the margin above the plot. I read this from the records and haven't pointed at one in a browser. A bar reaching past the limit has a box that runs past the plot too.
- **Proposal:** a point outside the plot has no readout, and a bar's box stops at the plot's edge. `Graph.marks()` would follow the same rule.
- **Decision:** agreed.

### The cross and plus markers aren't in their series' color

- **Summary:** a series drawn with `marker.shape: cross` or `plus` is drawn in the theme's marker outline, thin and black, instead of its own color. Every series' crosses look alike, and the default theme gives `cross` to the sixth group of a shape column.
- **Root cause:** a cross and a plus are made of lines, with nothing to fill, so only their outline shows. `_draw_marks` in drawing/xy.py draws every marker's outline in `series.marker.edge` (black, 0.05 × base size) and its fill in the series' color.
- **Verification:** found on 0.7.0 while checking #134. The series is #0072B2, and its cross and plus markers are drawn in #000000 at 0.9 pt.
- **Proposal:** a marker made of lines is drawn in the series' color, at the series' line width, with no outline. The key's sample follows it.
- **Decision:** agreed.

