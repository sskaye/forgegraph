# Layer specification: error_bar

This page mirrors src/forgegraph/specifications/layer_error_bar.yaml, which is the specification. A test fails if they ever differ.

name: error_bar          *# \[text\]; The name of the layer type.*\
version: 0          *# \[int ≥ 0\]; The version number of the specification.*\
description: An error bar on each point or bar.          *# \[text\]; The description of the layer type.*\
 \
parameters:\
    axis: y          *# \[x, y\]; The axis the bars extend along.*\
    value:\
        lower: data_column          *# \[<!-- fmc:2 -->data_column, float, column<!-- /fmc:2 -->\]; The distance below each value: a number or a column. <!-- fmc:3 -->data_column uses the axis's data column.<!-- /fmc:3 -->*\
        upper: data_column          *# \[data_column, float, column\]; The distance above each value: a number or a column. data_column uses the axis's data column.*\
        aggregation:          *# \[aggregation style\]; <!-- fmc:1 -->When the data columns are aggregated, the distances are this aggregate of the lower and upper columns.<!-- /fmc:1 -->*\
            function: stddev

<!-- forgemark-comments
- id: 1
  anchor_text: "When the data columns are aggregated, the distances are this aggregate of the lower and upper columns."
  context_before: "data_column uses the axis's data column.*\\ aggregation: # \\[aggregation style\\];"
  context_after: "\\ function: stddev"
  author: Claude
  timestamp: 2026-10-29T15:02:28Z
  resolved: false
  body: |
    Problem: it's the series that is aggregated, and the aggregate is over the rows each mark stands for (drawing/layers.py). Less sure: this may be a wording preference rather than an error.
  suggested_edit:
    from: "When the data columns are aggregated, the distances are this aggregate of the lower and upper columns."
    to: "When the series is aggregated, the distances are this aggregate of the rows each mark stands for, in the lower and upper columns."
- id: 2
  anchor_text: "data_column, float, column"
  context_before: "y # \\[x, y\\]; The axis the bars extend along.*\\ value:\\ lower: data_column # \\["
  context_after: "\\]; The distance below each value: a number or a column."
  author: Claude
  timestamp: 2026-10-29T15:02:39Z
  resolved: false
  body: |
    Problem: a negative distance is an error when drawing ("is below 0; it's a distance from each value", drawing/layers.py), so the range should say so. The same change applies to upper, on the next line.
  suggested_edit:
    from: "data_column, float, column"
    to: "data_column, float ≥ 0, column"
- id: 3
  anchor_text: "data_column uses the axis's data column."
  context_before: "ta_column, float, column\\]; The distance below each value: a number or a column."
  context_after: "\\ upper: data_column # \\[data_column, float, column\\]; The distance above each v"
  author: Claude
  timestamp: 2026-10-29T15:02:39Z
  resolved: false
  body: |
    Problem: on the value axis there's no axis data column (it must be None), so data_column means the series' own column there; and it's an error without aggregation.function (drawing/layers.py). The same change applies to upper, on the next line.
  suggested_edit:
    from: "data_column uses the axis's data column."
    to: "data_column uses the column drawn along the axis: the series' column on the value axis, or data.column on the base axis. It needs aggregation.function."
-->
