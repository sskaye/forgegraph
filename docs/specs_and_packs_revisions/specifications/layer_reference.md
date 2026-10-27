# Layer specification: reference

This page mirrors src/forgegraph/layers/reference.yaml, which is the specification. A test fails if they ever differ.

name: reference          *# \[text\]; The name of the layer type.*\
version: 0          *# \[int ≥ 0\]; The version number of the specification.*\
description: A horizontal or vertical line, or a shaded band between two lines, at a value or drawn from the data.          *# \[text\]; The description of the layer type.*\
 \
parameters:\
    axis: None          *# \[x, y\]; The axis the values are on. y draws horizontal lines. A GraphSpec must set it.*\
    per_series: false          *# \[true, false\]; If true, the layer is drawn for every series with matching color. If false, it’s drawn for all data combined.*\
    line_1:          *# The first line. <!-- fmc:1 -->If both lines have a value, the layer is a band between them; if one is None, it's the other line alone.<!-- /fmc:1 -->*\
        value: None          *# \[None, float, date, column\]; A number, a date, or a column.*\
        aggregation:          *# \[aggregation style\]; How the column's rows are combined into the line's value. If its function is None, the values are used as-is.*\
        offset:          *# \[aggregation style\]; A distance added to the aggregate, e.g. 3\*stddev for three standard deviations above the aggregated value.*\
        scope: all          *# \[all, each\]; Which rows the aggregates are taken over: all for a straight line, or each, for a line that follows the data.*\
        line:          *# \[line style\]; The appearance of the line.*\
        label:          *# \[text style\]; The line's label.*\
            text: None          *# \[None, aggregation, value, aggregation_value, text\]; aggregation writes e.g. Mean, value e.g. 14.9, and aggregation_value e.g. Mean: 14.9. Other text is written as given.*\
            position: auto          *# \[auto, start_above, start_below, center_above, center_below, end_above, end_below\]; auto selects the first option that doesn't overlap the data and is invalid if inside is false.*\
            inside: true          *# \[true, false\]; Whether the label is inside the plot area. If false, it's beyond the plot area at the line's start or end, and a center position is invalid.*\
            format: auto          *# \[auto, format\]; The format of the value. auto uses one more decimal than the axis's tick labels, or on a date axis, the tick label format.*\
    line_2:          *# The second line. Same parameters as line_1.*\
    fill:          *# The fill between the lines of a band. Its look comes from the theme's layer.reference.fill, and a GraphSpec may change what the theme marks !var.*\
        color: "#808080"          *# \[<!-- fmc:2 -->series, hex color<!-- /fmc:2 -->\]; The fill color. series uses the series' color.*\
        opacity: 0.15          *# \[0-1\]; The fill opacity.*

<!-- forgemark-comments
- id: 1
  anchor_text: "If both lines have a value, the layer is a band between them; if one is None, it's the other line alone."
  context_before: "If false, it’s drawn for all data combined.*\\ line_1: # The first line."
  context_after: "\\ value: None # \\[None, float, date, column\\]; A number, a date, or a column.*\\"
  author: "Steven Kaye"
  timestamp: "2026-10-27T18:43:40.820Z"
  resolved: false
  body: "This should not be true. You can have two lines and no bands if color is None. Strike."
- id: 2
  anchor_text: "series, hex color"
  context_before: "l, and a GraphSpec may change what the theme marks !var.*\\ color: \"#808080\" # \\["
  context_after: "\\]; The fill color."
  author: "Steven Kaye"
  timestamp: "2026-10-27T18:47:27.786Z"
  resolved: false
  body: "Allow None."
-->
