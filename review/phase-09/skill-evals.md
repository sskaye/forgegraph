# Skill evals for phases 6 and 9

These cases test packs, configs and the blank canvas. They join the 57 cases of phases 4, 5 and 8, run as before: a fresh Claude Code session in a folder holding the case's data, the installed skill and ForgeGraph. A case's packs are copied into its folder, and its folder config, forgegraph.toml, allows them. Each case has its own main config, outside its folder, listing forgegraph_base and the case's packs.

## Coverage

| Case | Data | Packs allowed | What it tests |
| --- | --- | --- | --- |
| 58 | cell_polarization | acme | A house style, from a pack's specs and its reference note |
| 59 | iris | acme | A request for a spec the config doesn't allow |
| 60 | tips | forgegraph_base | A new theme for a project, which has to go in a pack |
| 61 | co2_monthly | forgegraph_base, forgegraph_base_2 | A theme from a pack the request names |
| 62 | tips | none: no config | A graph no graph type can draw, drawn anyway on the blank canvas |

### 58. A house style

- **Request:** "Can you plot the polarization curves in cell_polarization.csv for my slides? Please use our house style."
- **A good result:** the theme acme/acme and the format acme/slide (acme's reference note says slides use it).

### 59. A spec the config doesn't allow

- **Request:** "Make a scatter plot of sepal length vs. sepal width from iris.csv, colored by species, using ForgeGraph's base theme."
- **A good result:** the reply says the project's config (forgegraph.toml) allows only acme, and no other tool is used.

### 60. A theme for the project

- **Request:** "Make a theme called lab for this project with Paul Tol's muted palette, then use it to plot tip against total bill from tips.csv, colored by time."
- **A good result:** a theme named lab, in a pack the agent made and listed in forgegraph.toml, using tol_muted, and the graph drawn in it. The main config doesn't list the new pack, so the graph is watermarked as non-standard, and the reply says so.

### 61. A pack the request names

- **Request:** "Please draw the monthly CO₂ record in co2_monthly.csv as a line chart, using a theme from the forgegraph_base_2 pack."
- **A good result:** a theme from forgegraph_base_2.

### 62. Drawn anyway

- **Request:** "I'd like a violin plot of tip by day from tips.csv. If ForgeGraph can't make one, draw it anyway."
- **A good result:** a violin plot drawn on `forgegraph.blank`, so the image is watermarked and recorded as non-standard.

## Earlier cases, in full sentences

These earlier cases' requests are rewritten as full sentences. What each asks for is unchanged.

- **1.** "Make a scatter plot of petal length vs. petal width from iris.csv, with species as the color."
- **4.** "Plot chick weight as a function of age (day) from growth.csv. Draw each chick as its own line and color the lines by diet; there are four diets, so give each a distinct color."
- **5.** "From fmri.csv, take just the parietal rows and show signal across timepoints as individual subject traces, colored stim vs. cue."
- **7.** "Can you plot lifeExp vs gdpPercap from gapminder.csv with a log-scaled GDP axis, colored by continent?"
- **8.** "Make a log-log plot of price versus carat from diamonds.csv, color-coded by cut quality."
- **9.** "I'd like the dose-response data in dose_response.csv plotted with % response on y and concentration in µM on a logarithmic x axis, one curve per compound."
- **10.** "Plot a time series of sea-ice extent from seaice.csv. Where readings are missing, leave a gap in the line rather than joining across it."
- **11.** "Using the Old Faithful data in geyser.csv, plot x = eruption duration and y = waiting time to the next eruption, as points. Fix the y range at 40–100 min."
- **12.** "Show daily temp_max and temp_min from weather.xlsx as two lines on one plot, with the date along the bottom."
- **13.** "Can you plot conductivity (mS/cm) vs. temperature (°C) for the samples in lab_export.xlsx, with no connecting lines?"
- **16.** "From tips.csv, plot tip (y) versus total bill (x), with the dots colored by lunch/dinner."
- **17.** "Plot sepal length vs. sepal width from iris.csv, with the points colored by species. Please set it in a serif typeface."
- **19.** "Could you make a box plot of tip by day from tips.csv, please?"
- **20.** "Make a bubble chart of 2007 life expectancy vs. GDP per capita from gapminder.csv, with bubble size showing population."
- **21.** "Make a bar chart of the average tip on each day in tips.csv, with the days in calendar order: Thur, Fri, Sat, Sun."
- **22.** "From penguins.csv, count the birds of each species on each island and plot it as grouped bars, with islands along x and species side by side."
- **23.** "Using tips.csv, show the total tips per day as stacked bars, with lunch and dinner stacked, and write each day's total above its bar."
- **25.** "Draw horizontal bars of life expectancy in 2007 for the 12 countries in the Americas, sorted so the longest bar is at the top, with each value printed at the end of its bar."
- **26.** "Plot bars of mean % response at 10 µM for each compound in dose_response.csv. Compound A is the reference — set it apart from the two test compounds and put it last."
- **27.** "Make a line plot of monthly passengers from air_passengers.csv, with x ticks every two years, labelled with the year only."
- **28.** "Please plot unemployment (the unemploy column, in thousands) over time from economics.csv, and format the y tick labels with thousands separators."
- **29.** "Plot % response vs. dose (µM, log x) for each compound from dose_response.csv, with a horizontal line at 50 % labelled 'half-maximal'."
- **31.** "Plot reaction rate against substrate concentration for treated vs. untreated samples (enzyme_kinetics.csv), as points only. Mark each group's maximum observed rate with a horizontal line in that group's color."
- **32.** "Please plot co2_monthly.csv as a time series, with the note 'Mauna Loa Observatory' in the upper left corner of the plot."
- **33.** "Using the iris data, plot petal length vs. petal width with the points colored by species. Under the x-axis title, add a source line: 'Source: Fisher (1936), synthetic look-alike'."
- **34.** "Could you plot the mean ± SD of the three replicates at each dose, with one line per compound and dose on a log scale (dose_response.csv)?"
- **35.** "From fmri.csv, using the parietal region only, plot the mean signal over time for stim and cue, averaged across the 14 subjects, with 95% confidence-interval error bars."
- **36.** "Make a bar plot of mean total bill by party size from tips.csv, with standard-error bars."
- **38.** "Show the average body mass per species in penguins.csv as bars, plus a dashed line at the overall average across all birds."
- **46.** "I need a three-panel figure: voltage vs. hours and HFR vs. hours stacked in the left column (cell_durability.csv), and the polarization plot from cell_polarization.csv filling the whole right column."
- **47.** "Plot iris.csv as a 2×2 grid of scatter plots colored by species: sepal length vs sepal width, petal length vs petal width, and sepal length vs petal length, with the fourth cell left empty."
- **48.** "Build a dashboard from economics.csv as an HTML page, with unemployment over time across the full top row and, below it, the personal savings rate and median unemployment duration side by side."
- **50.** "Put two plots side by side from tips.csv: tip vs. total bill as points on the left, and average tip per day as bars on the right."
- **51.** "Show weekly throughput from lab_runs.xlsx as one bar per week: the number of completed runs across all instruments."
- **52.** "I need sea-ice extent for January 2019 from seaice.csv plotted with an x tick every week."
- **53.** "Make a line chart of the monthly CO₂ record in co2_monthly.csv, plus a schedule file that re-renders it every weekday at 7am."
- **54.** "Chart sea-ice extent from seaice.csv, and write me a schedule file to refresh it every two hours, at a quarter past."
- **55.** "Plot the dose-response curves from dose_response.csv (log dose axis, one line per compound), with a schedule file for 06:00 on the 1st of every month and the output going to a reports folder. Do one run now so I can check it works."

