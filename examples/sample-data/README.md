# Sample data for trying ForgeGraph

Datasets for trying the `forgegraph` command and its skill by hand. Each is a **synthetic look-alike** of a dataset that data-visualization tutorials use (seaborn, ggplot2, Vega-Lite, R's built-in datasets): the same columns, shapes and quirks, with generated values. Country names, stock symbols and the like are real names on made-up numbers, so don't quote any figure from these files. The exception is `anscombe.csv`, which holds Anscombe's published quartet (1973).

`scripts/build_sample_data.py` writes them. To try them, copy the folder somewhere outside the repository and open Claude Code there:

```bash
cp -R examples/sample-data ~/forgegraph-trial
```

## The files

| File | Look-alike of | What's in it |
| --- | --- | --- |
| iris.csv | iris | 150 flowers, 3 species; plain snake_case columns |
| penguins.csv | Palmer penguins | Missing values written `NA`; several categorical columns (species, island, sex) |
| anscombe.csv | Anscombe's quartet (real values) | Four small datasets in long format |
| co2_monthly.csv | Mauna Loa CO₂ | Monthly dates; a long series; **−99.99 marks a missing month**, as in NOAA's file |
| air_passengers.csv | AirPassengers | Monthly dates written `1949-01`; steady growth |
| air_passengers_by_month.csv | AirPassengers, as R prints it | Wide: one row per year, a column per month |
| stocks.csv | Vega's stocks | Dates written `Jan 1 2000`; series of different lengths |
| gapminder.csv | gapminder | 55 countries in 5 continents over 12 years; life expectancy, GDP per capita, population |
| diamonds.csv | ggplot2's diamonds | 15,000 rows; price and carat over orders of magnitude; cut, color and clarity grades |
| weather.xlsx | Seattle weather | Excel with real dates; the data on the second sheet |
| fmri.csv | seaborn's fmri | Repeated measures: 14 subjects × 2 events × 2 regions × 19 timepoints |
| enzyme_kinetics.csv | Puromycin | Reaction rate by concentration, two replicates each, two conditions |
| dose_response.csv | a typical dose-response assay | 3 compounds × 3 replicates; doses from 0 to 100 µM |
| assay_summary.csv | dose_response.csv, summarised | Each compound and dose's mean response and its SD, one row each |
| cell_durability.csv | a fuel-cell durability test | 3 cells over 200 hours at constant current: voltage and resistance every 2 hours; one cell's log has a gap |
| cell_polarization.csv | the same cells' polarization curves | Voltage against current density, measured after the test |
| geyser.csv | Old Faithful | Eruption durations and waiting times in two clusters |
| tips.csv | seaborn's tips | Mostly categories: day, time, sex, smoker, party size |
| growth.csv | ChickWeight | 50 animals on 4 diets; some series end early; **diet is a number** (1–4) |
| seaice.csv | seaborn's seaice | Daily dates; a month of missing values |
| economics.csv | ggplot2's economics | Several monthly series in different units |
| lab_export.xlsx | an instrument export | Summary sheet first; title rows above the header; a units row; `-` and `n/a` for missing; an Average row and "End of report" under the data |
| lab_runs.xlsx | a LIMS run log | One row per instrument run over 15 weeks; title rows above the header; statuses typed inconsistently; runs still in progress; a total under the data; an Instruments sheet |
| sensor_log_eu.csv | a European-locale CSV | Semicolons, decimal commas, day-first dates, Windows-1252 |
