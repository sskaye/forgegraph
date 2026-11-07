# Skill evals for 0.8.0

These cases test what 0.8.0 adds that an agent has to find through the skill: the choice and toggle layers, which make HTML controls, and the new parameters it finds through `forgegraph schema` (IQR limits, the geometric statistics, title wrapping). They join the 61 cases of phases 4 to 9, run as before: a fresh Claude Code session in a folder holding the case's data, the installed skill and ForgeGraph, scored by scripts/run_skill_evals.py.

The skill's examples are now copies of the documentation's, so every earlier case reads different examples. The run is therefore the whole set, old and new, on opus and sonnet (haiku reported only), compared with the phase 9 results.

## Coverage

1. 63, penguins: a dropdown that switches the y column.
2. 64, co2_monthly: radio buttons above the graph, for a linear or log axis.
3. 65, iris: the reader picks both axes' columns (#118's request).
4. 66, air_passengers_by_month: a checkbox for each series.
5. 67, economics: a reference line the reader can show, hidden at first.
6. 68, penguins: a layout whose two panels share one dropdown.
7. 69, diamonds: a y-axis capped by an IQR rule.
8. 70, diamonds: the geometric mean, with geometric CI error bars.
9. 71, seaice: a long title allowed to wrap.

## New checks

Two checks the runner doesn't have yet:

1. `views: n`: the final GraphSpec draws n views (every combination of its choice layers' views).
2. `layout: {shared_control: true}`: the final layout has a control every tile shares, from choice layers of the same name in each tile. It's part of the layout check.

Every other check below is one the runner already has. A case's HTML page is checked with `files: ["*.html"]`.

## Cases

### 63. A dropdown for the y column

- **Request:** "Please make an HTML page of penguin bill length vs. body mass from penguins.csv, colored by species, with a dropdown that lets the reader swap bill length for bill depth or flipper length."
- **A good result:** a choice layer with three views, each setting the series' column and the y-axis title, shown as a dropdown on the page.
- **Checks:** `graph`, `files: ["*.html"]`, `layers: [{type: choice, control: dropdown}]`, `views: 3`.

### 64. Radio buttons above the graph

- **Request:** "I'd like the CO₂ record from co2_monthly.csv as a web page, with two radio buttons above the graph: one for a linear y-axis and one for a log y-axis."
- **A good result:** a choice layer with radio buttons at the top, its views setting `axis.y.scale`.
- **Checks:** `graph`, `files: ["*.html"]`, `layers: [{type: choice, control: radio, position: top}]`, `views: 2`.

### 65. Both axes chosen by the reader

- **Request:** "From iris.csv, make an interactive HTML plot where readers can pick any of the four measurements for the x-axis and for the y-axis, with the points colored by species."
- **A good result:** two choice layers, one for each axis, each with the four measurements as views, so the page holds every pair.
- **Checks:** `graph`, `files: ["*.html"]`, `layers: [{type: choice}, {type: choice}]`, `views: 16`.

### 66. A checkbox for each series

- **Request:** "Plot monthly airline passengers from air_passengers_by_month.csv, one line per month, and put checkboxes on the HTML page so readers can turn individual months on and off."
- **A good result:** twelve series and a toggle layer listing them; with a key, the checkboxes sit in it.
- **Checks:** `graph`, `files: ["*.html"]`, `lines: 12`, `layers: [{type: toggle, items: {contains: series}}]`.

### 67. A line the reader can show

- **Request:** "Could you plot the personal savings rate (psavert) by date from economics.csv as a web page? Add a line at its mean, and let readers show or hide that line with a checkbox, hidden when the page opens."
- **A good result:** a reference line at the mean, and a toggle layer that lists it and hides it at first.
- **Checks:** `graph`, `files: ["*.html"]`, `layers: [{type: reference, line_1.aggregation.function: mean}, {type: toggle, hidden: {matches: "."}}]`.

### 68. Two panels, one dropdown

- **Request:** "I need a two-panel web page from penguins.csv: bill length vs. body mass on the left and flipper length vs. body mass on the right. One dropdown should change how both panels are colored, by species, island or sex."
- **A good result:** a layout of two tiles, each with a choice layer of the same name and the same three views, sharing one control.
- **Checks:** `graph`, `files: ["*.html"]`, `layout: {tiles: 2, shared_control: true}`.

### 69. An axis capped by an IQR rule

- **Request:** "Plot price vs. carat from diamonds.csv. A few extreme prices squash the plot, so cap the y-axis at 3 interquartile ranges above the upper quartile."
- **A good result:** `axis.y.max: 3IQR`, with the points beyond it left out of the view.
- **Checks:** `graph`, `values: {graph_type:axis.y.max: {matches: "^3(\\.0)?IQR$"}}`.

### 70. Geometric statistics

- **Request:** "Using diamonds.csv, make a bar chart of the geometric mean price for each cut, with error bars showing the geometric 95% confidence interval."
- **A good result:** bars aggregated with `geom_mean`, and an error bar layer with `geom_ci`.
- **Checks:** `graph`, `values: {series:aggregation.function: geom_mean, series:bar.show: true}`, `layers: [{type: error_bar, value.aggregation.function: geom_ci}]`.

### 71. A title that wraps

- **Request:** "Can you graph sea-ice extent over time from seaice.csv with the title 'Daily Arctic sea-ice extent, 1978 to the present, from the NSIDC Sea Ice Index (synthetic look-alike)'? Let the title run onto a second line if it doesn't fit."
- **A good result:** the full title, with the theme's `title.max_wrap` set to 1 or more, rather than a shortened title.
- **Checks:** `graph`, `values: {theme:title.max_wrap: {in: [1, 2, 3]}, graphspec:text.title: {matches: "NSIDC"}}`.
