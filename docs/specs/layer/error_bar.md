# Layer specification: error_bar

This page mirrors src/forgegraph/layers/error_bar.yaml, which is the specification. A test fails if they ever differ.

name: error_bar          *# \[text\]; The name of the layer type.*\
version: 0          *# \[int\]; The version number of the specification.*\
description: An error bar on each point or bar.          *# \[text\]; The description of the layer type.*\
 \
parameters:          *# The layer's parameters, which a GraphSpec's layers entry sets after its type.*\
    axis: y          *# \[x, y\]; Axis the bars extend along.*\
    value:\
        lower: data_column          *# \[data_column, float, column\]; Distance below each value: a number or a column. data_column: the axis's data column.*\
        upper: data_column          *# \[data_column, float, column\]; Distance above each value: a number or a column. data_column: the axis's data column.*\
        aggregation:          *# With aggregated data columns: the distances are multiplier × an aggregate of lower's and upper's columns.*\
            function: stddev          *# \[None, stddev, stderr, ci\]; The aggregate; ci: half the 95 % confidence interval. None: the column's values as given.*\
            multiplier: 1          *# \[float\]; What the aggregate is multiplied by, e.g. 2 for two standard deviations.*
