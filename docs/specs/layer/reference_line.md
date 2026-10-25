# Layer specification: reference_line

This page mirrors src/forgegraph/layers/reference_line.yaml, which is the specification. A test fails if they ever differ.

name: reference_line          *# \[text\]; The name of the layer type.*\
version: 0          *# \[int\]; The version number of the specification.*\
description: A horizontal or vertical line at a value or a column's aggregate, with a label.          *# \[text\]; The description of the layer type.*\
 \
parameters:          *# The layer's parameters, which a GraphSpec's layers entry sets after its type.*\
    axis: None          *# \[x, y\]; Axis the value is on: y draws a horizontal line. A GraphSpec must set it.*\
    value: None          *# \[float, column\]; The line's value, or a column to aggregate. A GraphSpec must set it.*\
    aggregation:          *# With a column: the line is at multiplier × the column's aggregate.*\
        function: None          *# \[None, mean, median, sum, min, max, stddev\]; The aggregate. None: value is a number.*\
        multiplier: 1          *# \[float\]; What the aggregate is multiplied by, e.g. 2 for twice the stddev.*\
    per_series: false          *# \[true, false\]; With a column: one line per named series, its replicates together, in its color.*\
    label:\
        text: None          *# \[None, aggregation, value, aggregation_value, text\]; aggregation: e.g. Mean. value: e.g. 14.9. aggregation_value: Mean: 14.9. None: no label. Other text: written as given.*\
        position: auto          *# \[auto, start_above, start_below, center_above, center_below, end_above, end_below\]; auto: the first clear one.*\
        format: auto          *# \[auto, text\]; Number format of the value, e.g. ".2f". auto: one decimal more than the axis's tick labels.*
