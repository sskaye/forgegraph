# Catalog specification: error_bar layer

This page mirrors src/forgegraph/specifications/catalogs/layer_error_bar.yaml, which is the specification. A test fails if they ever differ.

name: error_bar          *# \[layer type\]; The layer type this catalog shows.*\
version: 0          *# \[int ≥ 0\]; The version number of the specification.*\
description: Cards for the error_bar layer.          *# \[text\]; The description of the catalog.*\
extends: None          *# \[None, catalog\]; The catalog this one extends. Its baselines come before this file's own, and a header field set to None here is taken from it. If None, this catalog extends no other.*\
baseline: forgegraph_default/graphspec_example          *# \[graphspec\]; The GraphSpec every card changes, without its own layers.*\
settings: {series.aggregation.function: mean, series.split: None}          *# The GraphSpec parameters every card sets so that the layer can be drawn. If there are none, this is None.*\
layer: None          *# The parameters of the layer every card draws, which is named after its type. If None, the layer's defaults are used.*\
 \
baselines:          *# Generic scenarios, each the baseline with one or more changes, numbered in the order they're first used. Every parameter gets one card, chosen by a rule: the first candidate value that changes the drawing, on the baseline or on the first of these scenarios where it does. The page shows the cards of the variable parameters. If there are no scenarios, this is None.*\
    power:          *# \[parameters and their values, or non-standard\]; Power density, whose values suit distances along either axis.*\
        layers.error_bar.value.lower: 4\
        layers.error_bar.value.upper: 4\
        series: {"Power Density (mW/cm²)": {color: Cell, split: None, aggregation: {function: mean}}}\
    percentile_spread: {layers.error_bar.value.aggregation: {function: percentile, multiplier: 0.02}}          *# \[parameters and their values, or non-standard\]; Distances that are a fiftieth of a percentile of each place's rows, so the percentile acts.*
