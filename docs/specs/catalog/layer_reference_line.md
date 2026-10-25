# Catalog specification: reference_line layer

This page mirrors src/forgegraph/catalogs/layers/reference_line.yaml, which is the specification. A test fails if they ever differ.

name: reference_line          *# \[layer type\]; The layer type this catalog shows.*\
version: 0          *# \[int\]; The version number of the specification.*\
description: Cards for the reference_line layer.          *# \[text\]; The description of the catalog.*\
extends: None          *# \[None, catalog\]; The catalog this one extends: its baselines come before this file's own, and a header field set to None here is taken from it. None: it extends none.*\
baseline: forgegraph_base/polarization          *# \[graphspec\]; The GraphSpec every card changes, without its own layers.*\
settings: None          *# GraphSpec parameters every card sets so the layer can be drawn. None if none.*\
layer:          *# The layer every card draws, named after its type: its parameters. None: its defaults.*\
    axis: y          *# \[x, y\]; Axis the value is on: y draws a horizontal line.*\
    value: 1.45          *# \[float, column\]; The line's value, or a column to aggregate.*\
 \
baselines:          *# Numbered baselines: generic scenarios, each the baseline with one or more changes, numbered in order of first use. Every variable parameter gets one card, by rule: its first candidate value that changes the drawing, on the baseline or on the first of these where it does. None if none.*\
    aggregated:          *# \[parameters and their values, or non-standard\]; A line at the highest cell voltage.*\
        layers.reference_line.value: "Cell Voltage (V)"\
        layers.reference_line.aggregation.function: max\
    valued:          *# \[parameters and their values, or non-standard\]; A line at the mean cell voltage, labelled with it.*\
        layers.reference_line.value: "Cell Voltage (V)"\
        layers.reference_line.aggregation.function: mean\
        layers.reference_line.label.text: aggregation_value
