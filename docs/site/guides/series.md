# Series

A GraphSpec's `series` lists what it draws against the x-axis, each under its name. This guide covers the marks a series draws, how its rows are grouped and combined, and how several series are arranged and named.

## One series or several

A series draws the column with its name, or the column it names with `column`. Its name is how the graph names it, so a series can have a readable name for a column that hasn't:

```yaml
    series:
        Savings rate:
            column: psavert
```

A GraphSpec may list several series, each drawing its own column against the same x-axis, and each takes the next color from the theme's palette. With several series, give the y-axis a title, since no one column names it.

## Lines, markers and bars

Each series chooses its marks: `line.show`, `marker.show` and `bar.show`. By default it draws lines and markers.

- **Lines** join the points in order of x, or in the order of the rows with `line.connect_order: data`. `line.interpolate` draws them straight, in steps, or as a smooth curve.
- **Missing values:** with `line.missing_values: drop`, a line joins across a row missing its x or y; with `gap`, the line breaks there. Either way, the lint counts the rows left out.
- **Markers** take the theme's shapes and fills, and `marker.size` sets their size.
- **Bars** stand on the x-axis, from 0, or from 1 on a log axis, and `bar.width` sets how much of the space between neighboring bars they fill.

The durability test draws lines without markers:

```yaml
--8<-- "docs/examples/durability.yaml"
```

![Each cell's voltage over 200 hours, as a line in its own color.](../images/durability.png){ width="480" }

## Groups

A series' rows can be split into groups by a column. Each of `color`, `line.style`, `marker.shape` and `marker.fill` can name a column, and each of that column's values gets its own color, line style, shape or fill, in the theme's order. The same column can set more than one, so each penguin species has its own color and shape:

```yaml
--8<-- "docs/examples/penguins.yaml"
```

![Bill depth against bill length, a color and a marker shape for each penguin species.](../images/penguins.png){ width="480" }

- **split** specifies how rows should be grouped for aggregation or line paths. This can be used to, for example, prevent averaging of data from replicates or draw independent lines for multiple runs under the same conditions.
- **order** puts the groups in sorted order, or with `data`, in the order they first appear.
- **A numeric color column** draws on a color scale, with a color bar beside the plot. `color_scale: categorical` gives each number a palette color instead.

## Combining rows

`aggregation` combines the rows at each x into one point: their mean, median, sum, minimum, maximum, a percentile, standard deviation, standard error, or half the 95 % confidence interval of the mean (`ci`). `multiplier` scales the result, and `percentile` sets which percentile.

```yaml
            aggregation:
                function: mean
```

## Arranging series

`arrangement` places the series, or the groups of a series, that share an x value:

- **stacking:** `sum` stacks them, and `percent` stacks them to 100 %. `total.show` writes each stack's total.
- **offset:** `side_by_side` draws them beside each other instead of over each other.
- **base_axis:** `y` turns the graph on its side, so bars lie along the y-axis.

The total of the bills on each day, stacked by lunch and dinner:

```yaml
--8<-- "docs/examples/tips_stacked.yaml"
```

![Bars of the total bills on each day, dinner and lunch stacked, with each day's total above.](../images/tips_stacked.png){ width="480" }

A categorical axis keeps the order of its categories in the data, or sorts them with `axis.x.data.order`: alphanumerically, or by their value, as here.

## Value labels

`value_label.show` writes each value next to its mark: inside the end of a bar or just beyond it, as `value_label.position` says. Its `format` is a Python number format, such as `.1f`, or `auto` for the format of the axis's tick labels.

## A benchmark

`benchmark` draws one series, or one group, in the theme's benchmark style, so the others are read against it. `data_column` names the column that identifies it, or `series` when the benchmark is one of the series, and `value` names it.

## Naming the series

`legend.method` chooses how a graph names its series, from the methods its theme allows:

- **direct:** each name beside its own series, touching no line, marker or other name.
- **key:** a key at the first of `legend.key.positions` that covers no data. With `legend.key.inside: false`, the key is outside the plot area.
- **none:** no names, where the theme allows it. The built-in theme doesn't.
- **auto**, the default, tries the theme's methods in order and uses the first that fits.

When no method fits, the graph isn't drawn: the error says what to change, such as putting the key outside the plot. The bar graphs above have their keys outside. A key's title is the column's name, or the text `legend.key.title.text` sets.
