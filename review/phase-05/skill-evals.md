# Skill evals for phase 5

These cases test what phase 5 added: bars, categorical axes and their order, tick placement and label formats, the three layers, and questions about what ForgeGraph can do. They join the 20 phase 4 cases, with case 19 replaced, since bar charts are now supported. As before, each case gives a fresh Claude Code session an empty folder holding its sample data from `examples/sample-data`, the installed skill and ForgeGraph, then sends the request. Requests are written as expert users write them, worded the way different scientists word things. Every graph request's final turn ends with "After you finish, please share the graph and any notes on issues that came up or you had to work around." A question's turn is sent as written, with nothing added.

A case is graded two ways:

- **By script:** the values in the final GraphSpec (its layers included), the lint on redrawing it, the files made, that the data file is unchanged, and for a question, that no graph was made and the reply names what it should.
- **By me:** I look at every graph and read every reply, and report anything the script can't judge.

## Models

Each case runs once on Opus, once on Sonnet and once on Haiku. A case passes on Opus and Sonnet or it fails: those are the results that decide changes to the skill. Haiku's results are reported beside them, but a Haiku failure alone doesn't call for a change, since it won't see much use.

## Coverage

| Case | Data | What it tests |
| --- | --- | --- |
| 19 | tips | A box plot (not supported), replacing the bar chart case |
| 21 | tips | A bar chart; a category order the data doesn't give |
| 22 | penguins | Grouped bars of counts the agent computes |
| 23 | tips | Stacked bars with each stack's total |
| 24 | diamonds | Bars stacked to 100 %; a key that needs room |
| 25 | gapminder | Horizontal bars in value order, values printed |
| 26 | dose_response | A reference compound drawn as the benchmark, placed last |
| 27 | air_passengers | Date ticks every two years, labelled by year |
| 28 | economics | A number format for tick labels |
| 29 | dose_response | A reference line at a value, labelled |
| 30 | economics | A reference line at a column's mean, labelled with it |
| 31 | enzyme_kinetics | A reference line per series |
| 32 | co2_monthly | A note inside the plot, in a corner |
| 33 | iris | A note outside the plot, under the x-axis title |
| 34 | dose_response | Error bars of ±1 SD across replicates |
| 35 | fmri | Error bars of a 95 % confidence interval |
| 36 | tips | Bars with standard-error bars |
| 37 | assay_summary | Error bars from a column of SDs |
| 38 | penguins | Bars with a reference line at the overall mean |
| 39–44 | none | Questions about what ForgeGraph can do |

## Bars

### 21. Mean tip by day

- **Data:** tips.csv
- **Request:** "Bar chart of the average tip on each day in tips.csv, days in calendar order: Thur, Fri, Sat, Sun."
- **A good result:** bars, with lines and markers off; day on x, in the order Thur, Fri, Sat, Sun (an ordered pandas category in the Parquet file, which `axis.x.data.order.method: source` keeps); tip on y, as the mean (`axis.y.data.aggregation: mean`, or means computed in the DataFrame); clean lint.
- **Why:** the basic bar chart, and an order that neither the data nor sorting gives.

### 22. Penguins by island

- **Data:** penguins.csv
- **Request:** "From penguins.csv, count the birds of each species on each island and plot it as grouped bars — islands along x, species side by side."
- **A good result:** counts computed in the DataFrame, island on x, colored by species, `series.offset: side_by_side`, the series named in a key, clean lint.
- **Why:** grouped bars, a count the agent prepares, and naming bars (no names beside bars).

### 23. Tips stacked by meal

- **Data:** tips.csv
- **Request:** "tips.csv: total tips per day as stacked bars, lunch and dinner stacked, and write each day's total above its bar."
- **A good result:** colored by time, `series.aggregation: sum`, `series.value_label.total: true`, tips summed per day and meal, clean lint.
- **Why:** stacking, and totals.

### 24. Diamond cuts by color grade

- **Data:** diamonds.csv
- **Request:** "For each color grade in diamonds.csv, show the share of each cut as a 100% stacked bar."
- **A good result:** counts per color and cut, `series.aggregation: percent`, colored by cut, the color grades along x, and a graph made. The key needs room above the bars, so the agent has to find it (e.g. a higher `axis.y.max`), not give up.
- **Why:** shares, and a key that doesn't fit at first.

### 25. Life expectancy in the Americas

- **Data:** gapminder.csv
- **Request:** "Horizontal bars of life expectancy in 2007 for the 12 countries in the Americas, sorted so the longest bar is at the top, with each value printed at the end of its bar."
- **A good result:** only the 2007 rows for the Americas; `series.base_axis: y`, with country on y and life expectancy on x; `axis.y.tick.algorithm: all`; `axis.y.data.order.method: value`, ascending, so the longest bar is at the top; `series.value_label.show: true`; clean lint.
- **Why:** horizontal bars, value order and value labels together.

### 26. A reference compound

- **Data:** dose_response.csv
- **Request:** "Bars of mean % response at 10 µM for each compound in dose_response.csv. Compound A is the reference — set it apart from the two test compounds and put it last."
- **A good result:** only the 10 µM rows, the mean response per compound, `benchmark.data_column: compound`, `benchmark.value: Compound A`, `benchmark.side: end`, clean lint.
- **Why:** the benchmark in a bar chart, and its side.

## Axes and ticks

### 27. Passengers with yearly ticks

- **Data:** air_passengers.csv
- **Request:** "Line plot of monthly passengers (air_passengers.csv) with x ticks every two years, labelled with the year only."
- **A good result:** month read as dates, `axis.x.tick.algorithm: manual`, `axis.x.tick.step: "2 year"`, `axis.x.tick.label.format: "%Y"`, clean lint.
- **Why:** date tick steps and date formats.

### 28. Unemployment with separators

- **Data:** economics.csv
- **Request:** "Unemployment (the unemploy column, in thousands) over time from economics.csv; format the y tick labels with thousands separators."
- **A good result:** date on x, unemploy on y, `axis.y.tick.label.format` with a comma (e.g. ",.0f"), clean lint.
- **Why:** number formats for tick labels.

## Layers

### 29. A 50 % line

- **Data:** dose_response.csv
- **Request:** "% response vs. dose (µM, log x) per compound from dose_response.csv, with a horizontal line at 50 % labelled 'half-maximal'."
- **A good result:** a reference_line layer on axis y at 50, labelled "half-maximal"; dose on a log x axis with dose 0 left out, and the reply says so.
- **Why:** a reference line at a value, with a label.

### 30. Savings rate and its mean

- **Data:** economics.csv
- **Request:** "Plot psavert, the personal savings rate, by date from economics.csv. Add a line across at its mean, labelled with the mean's value."
- **A good result:** a reference_line layer on axis y with `value: psavert`, `aggregation.function: mean` and `label.text: value`; clean lint.
- **Why:** a reference line at an aggregate of a column, not a number the agent works out.

### 31. Each group's maximum rate

- **Data:** enzyme_kinetics.csv
- **Request:** "Reaction rate against substrate concentration, treated vs. untreated (enzyme_kinetics.csv), points only. Mark each group's maximum observed rate with a horizontal line in that group's color."
- **A good result:** colored by state, markers only, a reference_line layer with the rate column as its value, `aggregation.function: max` and `per_series: true`; clean lint.
- **Why:** a reference line per series.

### 32. A corner note

- **Data:** co2_monthly.csv
- **Request:** "co2_monthly.csv as a time series, please, with the note 'Mauna Loa Observatory' in the upper left corner of the plot."
- **A good result:** a note layer with that text, `position: top_left`, inside; the −99.99 months treated as missing.
- **Why:** a note inside the plot at a chosen corner.

### 33. A source line

- **Data:** iris.csv
- **Request:** "Iris: petal length vs. petal width, points colored by species. Under the x-axis title, add a source line: 'Source: Fisher (1936), synthetic look-alike'."
- **A good result:** a note layer with that text, `inside: false` and a bottom position; markers only; clean lint.
- **Why:** a note outside the plot.

### 34. Replicates, mean ± SD

- **Data:** dose_response.csv
- **Request:** "Mean ± SD of the three replicates at each dose, one line per compound, dose on a log scale (dose_response.csv)."
- **A good result:** `axis.y.data.aggregation: mean`, one line per compound (no detail split by replicate), an error_bar layer at its defaults (the data column's standard deviation); dose 0 left out and the reply says so.
- **Why:** the error bar layer's default, and aggregating replicates.

### 35. fMRI with confidence intervals

- **Data:** fmri.csv
- **Request:** "fmri.csv, parietal region only: mean signal over time for stim and cue, averaged across the 14 subjects, with 95% confidence-interval error bars."
- **A good result:** only parietal rows, timepoint on x, `axis.y.data.aggregation: mean`, colored by event with no line per subject, an error_bar layer with `value.aggregation.function: ci`; clean lint.
- **Why:** a confidence interval of a mean across subjects.

### 36. Bill by party size, ± SE

- **Data:** tips.csv
- **Request:** "Bar plot of mean total bill by party size from tips.csv, with standard-error bars."
- **A good result:** bars, party size on x, `axis.y.data.aggregation: mean`, an error_bar layer with `value.aggregation.function: stderr`; clean lint.
- **Why:** error bars on bars.

### 37. SDs from a column

- **Data:** assay_summary.csv (new: one row per compound and dose, with the mean response and its SD, from the dose_response data)
- **Request:** "assay_summary.csv already has the mean and SD for each compound and dose. Plot mean response against dose for each compound, with error bars from the sd column."
- **A good result:** an error_bar layer with `value.lower` and `value.upper` set to the sd column and `value.aggregation.function: None`; no aggregation of the means.
- **Why:** error bars from a column, the common case of a summary table.

### 38. Body mass with the overall mean

- **Data:** penguins.csv
- **Request:** "Average body mass per species in penguins.csv as bars, plus a dashed line at the overall average across all birds."
- **A good result:** bars of the mean body mass per species, and a reference_line layer at the mean of body_mass_g (a column and `aggregation.function: mean`, or the number); the dashed style is the theme's default; the NA rows left out.
- **Why:** a layer on bars, and a request that the theme's default already meets.

## Questions about ForgeGraph

A question gets an answer, not a graph. A good answer comes from ForgeGraph's own commands (`forgegraph catalog`, `forgegraph schema`), not from memory, and says what's fixed by the theme or format and what a GraphSpec can change.

### 39. What it can draw

- **Request:** "What kinds of graphs can ForgeGraph make?"
- **A good result:** no graph; the reply names the xy graph type with lines, markers and bars; saying what isn't supported is fine, not required.

### 40. What a GraphSpec can change

- **Request:** "Which settings in the default theme can I change from a GraphSpec, and which are locked by the theme?"
- **A good result:** no graph; the reply lists all parameters and whether or not they can be changed.

### 41. Default size and file types

- **Request:** "What size and resolution are graphs saved at by default, and what other file types can I get?"
- **A good result:** no graph; the reply gives 150 mm wide, height from the plot's aspect and 600 dpi, and names the file types it can save: PNG, JPG, TIFF, SVG and PDF.

### 42. Annotations

- **Request:** "Can I annotate a graph — say a target line or a short text note — and how?"
- **A good result:** no graph; the reply names the reference_line and note layers and how a GraphSpec lists them.

### 43. Error bars

- **Request:** "I have replicate measurements. What can ForgeGraph's error bars show?"
- **A good result:** no graph; the reply names standard deviation, standard error, 95 % confidence interval, a multiplier, and distances from a column, and says the spreads need the values aggregated.

### 44. Palette and font

- **Request:** "Is there a way to change the colour palette or the font?"
- **A good result:** no graph; the reply says both are fixed in the default theme, names the built-in palettes, and says a new theme can set them.

## Limits

### 19. A box plot (replaces the bar chart case)

- **Data:** tips.csv
- **Request:** "Box plot of tip by day from tips.csv, please."
- **A good result:** no graph drawn some other way; the reply says box plots aren't supported yet and offers the closest graph ForgeGraph can draw (e.g. mean tip per day as bars with error bars).
- **Why:** an unsupported graph type, now that bar charts are supported.

## What the runner needs

- **Questions:** a case can leave out the closing line; `no_graph` and `says` already exist.
- **Layers:** an expectation that the final GraphSpec has a layer of a type with given parameters, under any name.
- **Models:** the summary reports Opus and Sonnet as pass or fail, and Haiku alongside.

