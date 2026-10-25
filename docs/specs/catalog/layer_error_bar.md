# Catalog specification: error_bar layer

This page mirrors src/forgegraph/catalogs/layers/error_bar.yaml, which is the specification. A test fails if they ever differ.

name: error_bar          *# \[layer type\]; The layer type this catalog shows.*\
version: 0          *# \[int\]; The version number of the specification.*\
description: Cards for the error_bar layer.          *# \[text\]; The description of the catalog.*\
extends: None          *# \[None, catalog\]; The catalog this one extends: its baselines come before this file's own, and a header field set to None here is taken from it. None: it extends none.*\
baseline: forgegraph_base/polarization          *# \[graphspec\]; The GraphSpec every card changes, without its own layers.*\
settings: {axis.y.data.aggregation: mean, encoding.detail.column: None}          *# GraphSpec parameters every card sets so the layer can be drawn. None if none.*\
layer: None          *# The layer every card draws, named after its type: its parameters. None: its defaults.*\
 \
baselines:          *# Numbered baselines: generic scenarios, each the baseline with one or more changes, numbered in order of first use. Every parameter gets one card, by rule (the page shows the variable ones): its first candidate value that changes the drawing, on the baseline or on the first of these where it does. None if none.*\
    power:          *# \[parameters and their values, or non-standard\]; Power density, whose values suit distances along either axis.*\
        axis.y.data.column: "Power Density (mW/cm²)"\
        layers.error_bar.value.lower: 4\
        layers.error_bar.value.upper: 4
