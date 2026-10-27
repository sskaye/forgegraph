# Catalog specification: reference layer

This page mirrors src/forgegraph/catalogs/layers/reference.yaml, which is the specification. A test fails if they ever differ.

name: reference          *# \[layer type\]; The layer type this catalog shows.*\
version: 0          *# \[int\]; The version number of the specification.*\
description: Cards for the reference layer.          *# \[text\]; The description of the catalog.*\
extends: None          *# \[None, catalog\]; The catalog this one extends: its baselines come before this file's own, and a header field set to None here is taken from it. None: it extends none.*\
baseline: forgegraph_base/graphspec_example          *# \[graphspec\]; The GraphSpec every card changes, without its own layers.*\
settings: None          *# GraphSpec parameters every card sets so the layer can be drawn. None if none.*\
layer:          *# The layer every card draws, named after its type: its parameters. None: its defaults.*\
    axis: y          *# \[x, y\]; The axis the values are on. y draws horizontal lines.*\
    line_1:\
        value: 1.45          *# \[None, float, date, column\]; A number, a date, or a column.*\
 \
baselines:          *# Numbered baselines: generic scenarios, each the baseline with one or more changes, numbered in order of first use. Every parameter gets one card, by rule (the page shows the variable ones): its first candidate value that changes the drawing, on the baseline or on the first of these where it does. None if none.*\
    aggregated:          *# \[parameters and their values, or non-standard\]; A line at the highest cell voltage.*\
        layers.reference.line_1.value: "Cell Voltage (V)"\
        layers.reference.line_1.aggregation.function: max\
    valued:          *# \[parameters and their values, or non-standard\]; A line at the mean cell voltage, labelled with it.*\
        layers.reference.line_1.value: "Cell Voltage (V)"\
        layers.reference.line_1.aggregation.function: mean\
        layers.reference.line_1.label.text: aggregation_value\
    labelled:          *# \[parameters and their values, or non-standard\]; A band between two lines, each labelled at a chosen position, so the labels can go beyond the plot area.*\
        layers.reference.line_1.label: {text: Target, position: end_above}\
        layers.reference.line_2: {value: 1.3, label: {text: Limit, position: end_below}}\
    band:          *# \[parameters and their values, or non-standard\]; A band two standard deviations either side of the mean cell voltage, each line labelled with its value.*\
        layers.reference.line_1: {value: "Cell Voltage (V)", aggregation: {function: mean}, offset: {function: stddev, multiplier: 2}, label: {text: aggregation_value}}\
        layers.reference.line_2: {value: "Cell Voltage (V)", aggregation: {function: mean}, offset: {function: stddev, multiplier: -2}, label: {text: aggregation_value}}\
    quartiles:          *# \[parameters and their values, or non-standard\]; A band between the cell voltage's first and third quartiles, so each line's percentile acts.*\
        layers.reference.line_1: {value: "Cell Voltage (V)", aggregation: {function: percentile, percentile: 25}}\
        layers.reference.line_2: {value: "Cell Voltage (V)", aggregation: {function: percentile, percentile: 75}}\
    percentile_offsets:          *# \[parameters and their values, or non-standard\]; Lines at the median cell voltage, each offset by a fraction of a percentile, so each offset's percentile acts.*\
        layers.reference.line_1: {value: "Cell Voltage (V)", aggregation: {function: median}, offset: {function: percentile, percentile: 10, multiplier: 0.05}}\
        layers.reference.line_2: {value: "Cell Voltage (V)", aggregation: {function: median}, offset: {function: percentile, percentile: 90, multiplier: -0.05}}
