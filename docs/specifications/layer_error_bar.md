# Layer specification: error_bar

This page mirrors src/forgegraph/specifications/layer_error_bar.yaml, which is the specification. A test fails if they ever differ.

name: error_bar          *# \[text\]; The name of the layer type.*\
version: 0          *# \[int ≥ 0\]; The version number of the specification.*\
description: An error bar on each point or bar.          *# \[text\]; The description of the layer type.*\
 \
parameters:\
    axis: y          *# \[x, y\]; The axis the bars extend along.*\
    value:\
        lower: data_column          *# \[data_column, float ≥ 0, column\]; The distance below each value: a number or a column. data_column uses the column drawn along the axis: the series' column on the value axis, or data.column on the base axis. It needs aggregation.function.*\
        upper: data_column          *# \[data_column, float ≥ 0, column\]; The distance above each value: a number or a column. data_column uses the column drawn along the axis: the series' column on the value axis, or data.column on the base axis. It needs aggregation.function.*\
        aggregation:          *# \[aggregation style\]; When the series is aggregated, the distances are this aggregate of the rows each mark stands for, in the lower and upper columns.*\
            function: stddev
