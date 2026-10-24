# Skill evals for review

These cases replace the old skill evals and the hand trial for phase 4. Each one gives a fresh Claude Code session an empty folder holding one sample dataset from `examples/sample-data`, the installed skill and ForgeGraph, then sends the request. Requests are written as expert users write them: each asks for a specific graph and says what goes where, worded the way different scientists word things (terse or chatty, column names or plain names, "vs.", "as a function of", "x = …"). Every final turn ends with "After you finish, please share the graph and any notes on issues that came up or you had to work around." Each case runs once on Opus, once on Sonnet and once on Haiku.

A case is graded two ways:

- **By script:** the values in the final GraphSpec, the lint on redrawing it, the files made, and that the data file is unchanged.
- **By me:** I look at every graph and read every reply, and report anything the script can't judge.

Every case also checks that the agent created no theme or format unless asked, and that the GraphSpec, graph and Parquet file are in the case's folder.

## Coverage

| Case | Data | What it tests |
| --- | --- | --- |
| 1 | iris | A scatter of groups |
| 2 | co2_monthly | Dates, a long series, −99.99 as a missing value, a single series |
| 3 | penguins | Missing values written NA; a second turn adding marker shapes |
| 4 | growth | A numeric group column (diet 1–4) as categories; one line per animal |
| 5 | fmri | Filtering, one line per subject, colored by event |
| 6 | stocks | Dates written "Jan 1 2000"; series of different lengths |
| 7 | gapminder | Log x, 55 countries in 5 groups: naming the groups is hard |
| 8 | diamonds | 15,000 points, log-log: markers need shrinking |
| 9 | dose_response | Dose 0 on a log axis |
| 10 | seaice | Breaking the line at missing data |
| 11 | geyser | Fixed axis limits |
| 12 | weather.xlsx | Excel, data on the second sheet, two y columns |
| 13 | lab_export.xlsx | Title rows, a units row, "-" and "n/a", an Average row and a footer |
| 14 | sensor_log_eu | Semicolons, decimal commas, day-first dates, Windows-1252 |
| 15 | air_passengers_by_month | Wide data (a column per month) to reshape; a log y axis |
| 16 | tips | Three turns editing one graph: title, then more file types |
| 17 | iris | A fixed theme parameter (font) asked for |
| 18 | iris | A theme explicitly asked for |
| 19 | tips | A bar chart (not supported) |
| 20 | gapminder | Point size by population (not supported) |

## Basic graphs

### 1. Iris scatter

- **Data:** iris.csv
- **Request:** "Scatter of petal length vs. petal width from iris.csv, species as color."
- **A good result:** petal_width on x and petal_length on y, colored by species, markers only, clean lint.
- **Why:** the most common graph there is: a scatter of groups.

### 2. CO2 record

- **Data:** co2_monthly.csv
- **Request:** "Plot the full monthly CO₂ record in co2_monthly.csv as a line over time."
- **A good result:** the date or decimal-year column on x, the −99.99 months treated as missing (the y axis stays above 300), one line, with no label beside it repeating the y-axis title, and only the dropped-rows lint, for those 5 months.
- **Why:** sentinel values, a long series and the single-series naming rule.

## Groups and encodings

### 3. Penguins, then marker shapes

- **Data:** penguins.csv
- **Requests:** "Using penguins.csv, put bill depth on the x-axis and bill length on the y-axis, points only, one color per species." then "Distinguish males and females with different symbols."
- **A good result:** bill depth on x, bill length on y, colored by species, marker shape by sex, lines off, one GraphSpec edited across both turns, and the dropped-rows lint for the rows with NA.
- **Why:** missing values written NA, a second encoding, and editing the same GraphSpec.

### 4. Chick growth by diet

- **Data:** growth.csv
- **Request:** "Chick weight as a function of age (day) from growth.csv. Draw each chick as its own line and color the lines by diet; there are four diets, so give each a distinct color."
- **A good result:** day on x, weight on y, a palette color per diet (`encoding.color_type: categorical`, or diet made text), one line per animal (`encoding.detail: animal`), clean lint.
- **Why:** a numeric column meant as categories, and lines split by another column.

### 5. fMRI subject traces

- **Data:** fmri.csv
- **Request:** "From fmri.csv, take just the parietal rows and show signal across timepoints: individual subject traces, colored stim vs. cue."
- **A good result:** only parietal rows, timepoint on x, signal on y, colored by event, one line per subject, clean lint.
- **Why:** filtering while preparing the DataFrame, and detail lines inside color groups.

### 6. Stock prices

- **Data:** stocks.csv
- **Request:** "Can you chart each ticker's price through time from stocks.csv?"
- **A good result:** dates written "Jan 1 2000" read as dates, price on y, colored by symbol, clean lint.
- **Why:** an unusual date format, and series that start at different times.

## Axes and scales

### 7. Gapminder, log x

- **Data:** gapminder.csv
- **Request:** "lifeExp vs gdpPercap from gapminder.csv, log-scaled GDP axis, colored by continent."
- **A good result:** GDP per capita on a log x axis, life expectancy on y, colored by continent, and a graph made. Direct labels and a key don't fit at first, so render stops with an error; the agent has to find a way to fit them (axis limits, label settings, markers only), not give up.
- **Why:** recovering from a labelling error.

### 8. Diamonds, dense

- **Data:** diamonds.csv
- **Request:** "diamonds.csv: log-log plot of price versus carat, color-coded by cut quality."
- **A good result:** both axes log, colored by cut, markers only, `series.marker.size` below the default 0.5, clean lint.
- **Why:** 15,000 points; the agent has to see the overlap in the image and use the theme's variable marker size.

### 9. Dose-response on a log axis

- **Data:** dose_response.csv
- **Request:** "Dose-response from dose_response.csv: % response on y, concentration in µM on a logarithmic x axis, one curve per compound."
- **A good result:** dose on a log x axis, response on y, colored by compound. The dose-0 rows can't go on a log axis; the agent leaves them out and says so in its reply.
- **Why:** a request that conflicts with the data, and being told about it.

### 10. Sea ice with gaps

- **Data:** seaice.csv
- **Request:** "Time series of sea-ice extent (seaice.csv). Where readings are missing, leave a gap in the line rather than joining across it."
- **A good result:** dates on x, `mark.line.missing_values: gap`, and only the dropped-rows lint.
- **Why:** a drawing option for missing data.

### 11. Geyser with fixed limits

- **Data:** geyser.csv
- **Request:** "Old Faithful, geyser.csv: x = eruption duration, y = waiting time to the next eruption, as points. Fix the y range at 40–100 min."
- **A good result:** duration on x, waiting on y, `axis.y.min: 40`, `axis.y.max: 100`, markers only, clean lint.
- **Why:** fixed axis limits.

## Messy files

### 12. Weather in Excel

- **Data:** weather.xlsx
- **Request:** "Show daily temp_max and temp_min from weather.xlsx as two lines on one plot, date along the bottom."
- **A good result:** data read from the Daily sheet, not the About sheet; temp_max and temp_min against date, both named; clean lint.
- **Why:** Excel, data on the second sheet, two y columns.

### 13. Instrument export

- **Data:** lab_export.xlsx
- **Request:** "Conductivity (mS/cm) vs. temperature (°C) for the samples in lab_export.xlsx, no connecting lines."
- **A good result:** read from the Data sheet past its title rows and units row; temperature and conductivity numeric; "-" and "n/a" missing; the Average row and "End of report" left out (40 samples at most); the units in the axis titles; markers only.
- **Why:** the most realistic messy file in the set.

### 14. European sensor log

- **Data:** sensor_log_eu.csv
- **Request:** "Graph the temperature readings in sensor_log_eu.csv over the logging period."
- **A good result:** semicolons and decimal commas read correctly, dates read day-first (all in March 2026), the °C header read from Windows-1252, clean lint.
- **Why:** locale and encoding problems.

### 15. Passengers, wide

- **Data:** air_passengers_by_month.csv
- **Request:** "air_passengers_by_month.csv has one row per year and a column per month. I'd like it as a single monthly time series, Jan 1949 through Dec 1960, with passengers on a log scale."
- **A good result:** reshaped to one row per month with a date, one line from 1949 to 1960, a log y axis, clean lint.
- **Why:** data laid out the wrong way, and a log axis.

## Iteration and output

### 16. Tips, three turns

- **Data:** tips.csv
- **Requests:** "tips.csv — tip (y) versus total bill (x), dots colored by lunch/dinner." then "Retitle it: Tips at lunch and dinner" then "Export SVG and PDF copies too."
- **A good result:** total_bill on x, tip on y, colored by time, markers only; the title set; png, svg and pdf files; one GraphSpec across the three turns.
- **Why:** follow-up edits to the same graph, as an expert user would make them.

## Themes and formats

### 17. A fixed theme parameter

- **Data:** iris.csv
- **Request:** "Sepal length vs. sepal width from iris.csv, points colored by species. Please set it in a serif typeface."
- **A good result:** the graph drawn, and the reply saying the font is fixed by the theme. No theme created.
- **Why:** step 2's rule against creating themes unless asked.

### 18. A theme asked for

- **Data:** iris.csv
- **Request:** "Set up a new theme, big_labels, based on the default but with tick labels at 1.3× the default size. Then use it for a scatter from iris.csv: sepal width on x, sepal length on y, one color per species."
- **A good result:** a theme file named big_labels that extends default and sets axis.tick.label.size to 1.3, used by the GraphSpec, clean lint.
- **Why:** the "unless the user asks" side of the same rule.

## Limits

### 19. A bar chart

- **Data:** tips.csv
- **Request:** "Bar chart, please: mean tip per day of the week, from tips.csv."
- **A good result:** no graph drawn some other way; the reply says bar charts aren't supported yet and offers the closest xy graph.
- **Why:** an unsupported graph type.

### 20. Point size by population

- **Data:** gapminder.csv
- **Request:** "Bubble chart of 2007 life expectancy vs. GDP per capita from gapminder.csv, bubble size = population."
- **A good result:** the reply says point size isn't supported yet. A graph without sizing is fine if the agent says that's what it drew.
- **Why:** an unsupported encoding inside an otherwise supported graph.
