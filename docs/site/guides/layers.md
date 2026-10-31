# Layers

Layers are drawn over a graph: reference lines and bands, error bars, and notes. A GraphSpec lists its layers under `layers`, each under a name it chooses, with its `type`. They're drawn in the order they're listed. The [layer specifications](../reference/specifications/layer_reference.md) list every parameter.

## Reference lines and bands

A `reference` layer draws a line across the plot at a value: horizontal with `axis: y`, vertical with `axis: x`. `line_1.value` is a number, a date, or a column, and a column's rows are combined by `line_1.aggregation`, so a line can sit at the data's mean, median, a percentile and so on. `offset` adds a distance to that, such as three standard deviations.

A second line, `line_2`, makes the layer a band, filled between the two lines. The savings rate has a band one standard deviation either side of its mean, drawn without its lines, and a second layer with a line at the mean:

```yaml
--8<-- "docs/examples/savings.yaml"
```

![The savings rate by month, with a grey band one standard deviation either side of the mean and a dashed line at the mean, labelled Mean: 14.9.](../images/savings.png){ width="480" }

- **label.text** writes the line's label: `aggregation` writes, for example, Mean, `value` writes 14.9, `aggregation_value` writes Mean: 14.9, and other text is written as it's given. `label.position` and `label.inside` place it; here it's outside the plot, at the line's end.
- **per_series: true** draws the layer for every series with matching color, marker shape, marker fill and line style, in its color and from its rows, instead of once for all the data.
- **scope: each** makes a line that follows the data, instead of a straight line over all the rows.

## Error bars

An `error_bar` layer draws a bar on each point or bar, along `axis` (y by default). Its distances below and above each value come from `value.lower` and `value.upper`:

- **data_column**, the default, takes them from the rows each point stands for, as `value.aggregation` says: their standard deviation by default, or their standard error, confidence interval and so on. The series must then be aggregated, so each point stands for several rows.
- **A number** is the same distance for every point.
- **A column** gives each point its own, with `value.aggregation.function: None` to use the column's values as they are.

The mean tip on each day, with the 95 % confidence interval of each mean:

```yaml
--8<-- "docs/examples/tips_side_by_side.yaml"
```

![Bars of the mean tip on each day, for women and men side by side, each with an error bar.](../images/tips_side_by_side.png){ width="480" }

When the data already holds the spread, the error bars read it from its column:

```yaml
--8<-- "docs/examples/assay_summary.yaml"
```

![Each compound's mean response at each dose, with error bars from the data's standard deviations.](../images/assay_summary.png){ width="480" }

## Notes

A `note` layer writes a block of text in or around the plot. Its `text` is written in label markup, and a line break starts a new line. `position: auto` puts it at the first clear place inside the plot area; `inside: false` puts it outside, at the `position` given.

```yaml
--8<-- "docs/examples/dose_response.yaml"
```

![The mean response of three compounds at each dose, with error bars and the note Mean ± SD of 3 replicates in the lower right.](../images/dose_response.png){ width="480" }

## The layers' look

Each layer's lines, labels, fill and text take their look from the theme's `layer` category. A layer may set the parts its theme marks `!var`, such as `line_1.line.style: None` above, which draws a band without its edges.
