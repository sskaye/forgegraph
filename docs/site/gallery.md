# Gallery

Worked examples, each drawn from its GraphSpec as this site is built. The data is the [sample data](https://github.com/sskaye/forgegraph/tree/main/examples/sample-data) in the repository: synthetic look-alikes of the datasets data-visualization tutorials use, saved as Parquet. Open a GraphSpec to see how the graph is made; the [guides](guides/graphs.md) explain each part.

## Lines and markers

Polarization curves of three fuel cells, one line for each cell, named beside it. Data: cell_polarization.csv.

![Voltage against current density for cells A, B and C.](images/polarization.png){ width="480" }

??? example "GraphSpec"

    ```yaml
    --8<-- "docs/examples/polarization.yaml"
    ```

## Lines over time

Each cell's voltage over a 200-hour durability test, as lines without markers. Data: cell_durability.csv.

![Each cell's voltage over 200 hours.](images/durability.png){ width="480" }

??? example "GraphSpec"

    ```yaml
    --8<-- "docs/examples/durability.yaml"
    ```

## Dates

Monthly CO₂ at Mauna Loa on a date axis, with the line broken where a month is missing. Data: co2_monthly.csv, with its dates read as dates and −99.99, which marks a missing month, read as missing.

![Monthly CO2 from 1958, rising with a yearly cycle.](images/co2.png){ width="480" }

??? example "GraphSpec"

    ```yaml
    --8<-- "docs/examples/co2.yaml"
    ```

## Groups by color and shape

Bill depth against bill length for three penguin species, as markers with a color and a shape for each species. Data: penguins.csv.

![Bill depth against bill length, a color and shape for each species.](images/penguins.png){ width="480" }

??? example "GraphSpec"

    ```yaml
    --8<-- "docs/examples/penguins.yaml"
    ```

## Stacked bars

The total of the bills on each day, stacked by lunch and dinner, with each day's total, and the days in order of their totals. Data: tips.csv.

![Bars of the total bills on each day, dinner and lunch stacked.](images/tips_stacked.png){ width="480" }

??? example "GraphSpec"

    ```yaml
    --8<-- "docs/examples/tips_stacked.yaml"
    ```

## Bars side by side, with error bars

The mean tip on each day, for women and men side by side, each with the 95 % confidence interval of its mean. Data: tips.csv.

![Bars of the mean tip on each day, women and men side by side, with error bars.](images/tips_side_by_side.png){ width="480" }

??? example "GraphSpec"

    ```yaml
    --8<-- "docs/examples/tips_side_by_side.yaml"
    ```

## Error bars and a note

Three compounds' mean response at each dose, with error bars of one standard deviation of the replicates, and a note saying so. Data: dose_response.csv.

![The mean response of three compounds at each dose, with error bars and a note.](images/dose_response.png){ width="480" }

??? example "GraphSpec"

    ```yaml
    --8<-- "docs/examples/dose_response.yaml"
    ```

## A reference line and band

The personal savings rate by month, with a line at its mean, labelled outside the plot, and a band one standard deviation either side. Data: economics.csv, with its dates read as dates.

![The savings rate by month, with a band around the mean and a dashed line at it.](images/savings.png){ width="480" }

??? example "GraphSpec"

    ```yaml
    --8<-- "docs/examples/savings.yaml"
    ```

## A figure for a paper

Three graphs of three fuel cells on one journal-width figure, in the journal pack's format, from [examples/layouts/paper](https://github.com/sskaye/forgegraph/tree/main/examples/layouts/paper), where its GraphSpecs and data are.

![Voltage and resistance over time on the left, and the polarization curves spanning both rows on the right.](images/cell_performance.png)

??? example "Layout"

    ```yaml
    --8<-- "examples/layouts/paper/cell_performance.layout.yaml"
    ```

## A dashboard

The Overview tab of a lab's throughput dashboard, from [examples/layouts/dashboard](https://github.com/sskaye/forgegraph/tree/main/examples/layouts/dashboard). Its other tab shows the runs on each instrument.

![Completed runs per week across the top, with failed runs, samples per week and run time below.](images/lab_throughput-overview.png)

??? example "Layout"

    ```yaml
    --8<-- "examples/layouts/dashboard/lab_throughput.layout.yaml"
    ```

## A house style

The polarization curves in the example acme pack's theme, a serif look with a light grid and no box, and its 16:9 slide format. Its parameters differ from the first example's only in the theme and format. The pack is in [examples/packs/acme](https://github.com/sskaye/forgegraph/tree/main/examples/packs/acme).

![The polarization curves in a serif font with a light grid, on a wide slide.](images/acme_polarization.png)

??? example "GraphSpec"

    ```yaml
    --8<-- "docs/examples/acme_polarization.yaml"
    ```
