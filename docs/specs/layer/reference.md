# Layer specification: reference

This page mirrors src/forgegraph/layers/reference.yaml, which is the specification. A test fails if they ever differ.

name: reference          *# \[text\]; The name of the layer type.*\
version: 0          *# \[int ≥ 0\]; The version number of the specification.*\
description: A horizontal or vertical line, or a shaded band between two lines, at a value or drawn from the data.          *# \[text\]; The description of the layer type.*\
 \
parameters:\
    axis: None          *# \[x, y\]; The axis the values are on. y draws horizontal lines. A GraphSpec must set it.*\
    per_series: false          *# \[true, false\]; Whether to draw the layer once per series, from its rows, in its color.*\
    line_1:          *# The first line. If both lines have a value, the layer is a band between them; if one is None, it's the other line alone.*\
        value: None          *# \[None, float, date, column\]; A number, a date, or a column.*\
        aggregation:          *# \[aggregation style\]; How the column's rows are combined into the line's value. If its function is None, the line follows each row.*\
        offset:          *# \[aggregation style\]; A distance added to the aggregate, e.g. stddev with multiplier 3 for three standard deviations above.*\
        scope: all          *# \[all, each\]; Which rows the aggregates are taken over: all of them, for a straight line, or those at each location, for a line that follows the data.*\
        line:          *# \[line style\]; The line. Its look comes from the theme's layer.reference.line, and a GraphSpec may change what the theme marks !var.*\
        label:          *# \[text style\]; The line's label. Its look comes from the theme's layer.reference.label, and a GraphSpec may change what the theme marks !var.*\
            text: None          *# \[None, aggregation, value, aggregation_value, text\]; aggregation writes e.g. Mean, value e.g. 14.9, and aggregation_value e.g. Mean: 14.9. Other text is written as given.*\
            position: auto          *# \[auto, start_above, start_below, center_above, center_below, end_above, end_below\]; auto selects the first option that doesn't overlap the data and is invalid if inside is false.*\
            inside: true          *# \[true, false\]; Whether the label is inside the plot area. If false, it's beyond the plot area at the line's start or end, and a center position is invalid.*\
            format: auto          *# \[auto, format\]; The format of the value. auto uses one more decimal than the axis's tick labels, or on a date axis, the tick label format.*\
    line_2:          *# The second line. Same parameters as line_1.*\
    fill:          *# The fill between the lines of a band. Its look comes from the theme's layer.reference.fill, and a GraphSpec may change what the theme marks !var.*\
        color: "#808080"          *# \[series, hex color\]; The fill color. series uses the series' color.*\
        opacity: 0.15          *# \[0-1\]; The fill opacity.*
