# Catalog: forgegraph_base_2's base_theme

This page mirrors src/forgegraph/packs/forgegraph_base_2/catalogs/themes/base_theme.yaml, which is the specification. A test fails if they ever differ.

name: base_theme          *# \[theme\]; The theme this catalog shows.*\
version: 0          *# \[int\]; The version number of the specification.*\
description: Cards for the forgegraph_base_2 theme, on the base theme's baselines and its own.          *# \[text\]; The description of the catalog.*\
extends: forgegraph_base/base_theme          *# \[None, catalog\]; The catalog this one extends: its baselines come before this file's own, and a header field set to None here is taken from it. None: it extends none.*\
baseline: forgegraph_base_2/graphspec_example          *# \[graphspec\]; The GraphSpec every card changes, drawn with the theme this catalog shows.*\
 \
baselines:          *# Numbered baselines: generic scenarios, each the baseline with one or more changes, numbered in order of first use. Every parameter gets one card, by rule (the page shows the variable ones): its first candidate value that changes the drawing, on the baseline or on the first of these where it does. None if none.*\
    direct_wide: {legend.method: direct, figure.width: 150}          *# \[parameters and their values, or non-standard\]; Series named beside the lines in a wider figure, where each label has more places to go.*\
    fanned_direct: {data.file: fanned.parquet, legend.method: direct}          *# \[parameters and their values, or non-standard\]; Fanned curves named beside the lines, so how far a label may be from its series has an effect.*\
    fanned_to_the_end: {data.file: fanned.parquet, legend.method: direct, axis.x.max: 100}          *# \[parameters and their values, or non-standard\]; Fanned curves named beside the lines, the x-axis ending where the data does, so it must grow for their labels.*\
    outlined:          *# \[parameters and their values, or non-standard\]; The bars, with a marker at each top and every outline drawn, so the outlines' widths act.*\
        axis.x.data.column: Cell\
        axis.y.data.column: "Power Density (mW/cm²)"\
        axis.y.data.aggregation: max\
        axis.x.tick.algorithm: all\
        encoding.color.column: None\
        encoding.detail.column: None\
        mark.bar.show: true\
        mark.line.show: false\
        series.bar.edge.style: solid\
        series.benchmark.bar.edge.style: solid\
        series.benchmark.marker.edge.style: solid
