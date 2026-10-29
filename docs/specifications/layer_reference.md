# Layer specification: reference

This page mirrors src/forgegraph/specifications/layer_reference.yaml, which is the specification. A test fails if they ever differ.

name: reference          *# \[text\]; The name of the layer type.*\
version: 0          *# \[int ≥ 0\]; The version number of the specification.*\
description: A horizontal or vertical line, or a shaded band between two lines, at a value or drawn from the data.          *# \[text\]; The description of the layer type.*\
 \
parameters:\
    axis: None          *# \[x, y\]; The axis the values are on. y draws horizontal lines. A GraphSpec must set it.*\
    per_series: false          *# \[true, false\]; If true, the layer is drawn for every series with matching color. If false, it's drawn for all data combined.*\
    line_1:          *# <!-- fmc:1 -->The first line.<!-- /fmc:1 -->*\
        value: None          *# \[None, float, date, column\]; A number, a date, or a column.*\
        aggregation:          *# \[aggregation style\]; How the column's rows are combined into the line's value. If its function is None, the values are used as-is.*\
        offset:          *# \[aggregation style\]; A distance added to the aggregate, e.g. 3 × stddev for three standard deviations above the aggregated value.*\
        scope: all          *# \[all, each\]; Which rows the aggregates are taken over: all for a straight line, or each, for a line that follows the data.*\
        line:          *# \[line style, look from layer.reference.line\]; The appearance of the line.*\
        label:          *# \[text style, look from layer.reference.label\]; The line's label.*\
            text: None          *# \[None, aggregation, value, aggregation_value, text\]; aggregation writes e.g. Mean, value e.g. 14.9, and aggregation_value e.g. Mean: 14.9. Other text is written as given.*\
            position: auto          *# \[auto, start_above, start_below, center_above, center_below, end_above, end_below\]; auto selects the first option that doesn't overlap the data and is invalid if inside is false.*\
            inside: true          *# \[true, false\]; Whether the label is inside the plot area. If false, it's beyond the plot area at the line's start or end, and a center position is invalid.*\
            format: auto          *# \[auto, format\]; The format of the value. <!-- fmc:3 -->auto uses one more decimal than the axis's tick labels, or on a date axis, the tick label format.<!-- /fmc:3 -->*\
    line_2:          *# \[same as line_1\]; The second line.*\
    fill:          *# \[look from layer.reference.fill\]; The fill between the lines of a band.*\
        color: "#808080"          *# \[None, <!-- fmc:2 -->series, hex color<!-- /fmc:2 -->\]; The fill color. series uses the series' color. If None, there is no fill.*\
        opacity: 0.15          *# \[0-1\]; The fill opacity.*

<!-- forgemark-comments
- id: 1
  anchor_text: "The first line."
  context_before: "If false, it's drawn for all data combined.*\\ line_1: #"
  context_after: "\\ value: None # \\[None, float, date, column\\]; A number, a date, or a column.*\\"
  author: "Steven Kaye"
  timestamp: "2026-10-27T18:43:40.820Z"
  resolved: false
  body: "This should not be true. You can have two lines and no bands if color is None. Strike."
  replies:
    - author: Claude
      timestamp: 2026-10-27T21:14:27Z
      body: |
        Struck. Two lines with values make a band only when fill.color isn't None.
- id: 2
  anchor_text: "series, hex color"
  context_before: "rence.fill\\]; The fill between the lines of a band.*\\ color: \"#808080\" # \\[None,"
  context_after: "\\]; The fill color."
  author: "Steven Kaye"
  timestamp: "2026-10-27T18:47:27.786Z"
  resolved: false
  body: "Allow None."
  replies:
    - author: Claude
      timestamp: 2026-10-27T21:14:27Z
      body: |
        Done. fill.color takes None, which draws no fill, here and in the theme's layer.reference.fill.color.
- id: 3
  anchor_text: "auto uses one more decimal than the axis's tick labels, or on a date axis, the tick label format."
  context_before: "position is invalid.*\\ format: auto # \\[auto, format\\]; The format of the value."
  context_after: "\\ line_2: # \\[same as line_1\\]; The second line.*\\ fill: # \\[look from layer.ref"
  author: Claude
  timestamp: 2026-10-29T15:02:28Z
  resolved: false
  body: |
    Problem: auto uses the axis's tick.label.format whenever it's set (drawing/axes.py, number_text), as the 0.3 changelog says; on a date axis with both auto, it's an error.
  suggested_edit:
    from: "auto uses one more decimal than the axis's tick labels, or on a date axis, the tick label format."
    to: "auto uses the axis's tick label format if it's set, and otherwise one more decimal than the tick labels show. On a date axis, it uses the tick label format, which must then be set."
-->
