# Catalog specification: xy

This page mirrors src/forgegraph/catalogs/graph_types/xy.yaml, which is the specification. A test fails if they ever differ.

name: xy          *# \[graph type\]; The graph type this catalog shows.*\
version: 0          *# \[int\]; The version number of the specification.*\
description: Cards for the xy graph type.          *# \[text\]; The description of the catalog.*\
extends: None          *# \[None, catalog\]; The catalog this one extends: its baselines come before this file's own, and a header field set to None here is taken from it. None: it extends none.*\
baseline: forgegraph_base/graphspec_example          *# \[graphspec\]; The GraphSpec every card changes, drawn with the graph type this catalog shows.*\
 \
baselines:          *# Numbered baselines: generic scenarios, each the baseline with one or more changes, numbered in order of first use. Every parameter gets one card, by rule (the page shows the variable ones): its first candidate value that changes the drawing, on the baseline or on the first of these where it does. None if none.*\
    key_shown: {legend.method: key}          *# \[parameters and their values, or non-standard\]; Series named in a key, so the key's parameters act.*\
    colored_by_temperature: {encoding.color.column: "Temperature (°C)"}          *# \[parameters and their values, or non-standard\]; A numeric encoding.color.column, so a color bar is drawn.*\
    colored_by_run: {encoding.color.column: Run}          *# \[parameters and their values, or non-standard\]; Colored by run, a column of numbers, so auto draws a color scale.*\
    temperatures:          *# \[parameters and their values, or non-standard\]; Each cell's peak power density at each temperature it ran at.*\
        axis.x.data.column: "Temperature (°C)"\
        axis.y.data.column: "Power Density (mW/cm²)"\
        axis.y.data.aggregation: max\
        encoding.detail.column: None\
    x_manual: {axis.x.tick.algorithm: manual, axis.x.tick.step: 20}          *# \[parameters and their values, or non-standard\]; x ticks every 20, so the step acts.*\
    y_manual: {axis.y.tick.algorithm: manual, axis.y.tick.step: 0.05}          *# \[parameters and their values, or non-standard\]; y ticks every 0.05, so the step acts.*\
    bars:          *# \[parameters and their values, or non-standard\]; Each cell's peak power density as a bar.*\
        axis.x.data.column: Cell\
        axis.y.data.column: "Power Density (mW/cm²)"\
        axis.y.data.aggregation: max\
        axis.x.tick.algorithm: all\
        encoding.color.column: None\
        encoding.detail.column: None\
        mark.bar.show: true\
        mark.line.show: false\
        mark.marker.show: false\
    overlaid:          *# \[parameters and their values, or non-standard\]; Peak power by cell, a bar per run, the runs drawn over each other.*\
        axis.x.data.column: Cell\
        axis.y.data.column: "Power Density (mW/cm²)"\
        axis.y.data.aggregation: max\
        axis.x.tick.algorithm: all\
        encoding.color.column: Run\
        encoding.color.type: categorical\
        encoding.detail.column: None\
        legend.key.title.text: column_name\
        mark.bar.show: true\
        mark.line.show: false\
        mark.marker.show: false\
    stacked:          *# \[parameters and their values, or non-standard\]; The runs' bars stacked.*\
        axis.x.data.column: Cell\
        axis.y.data.column: "Power Density (mW/cm²)"\
        axis.y.data.aggregation: max\
        axis.x.tick.algorithm: all\
        encoding.color.column: Run\
        encoding.color.type: categorical\
        encoding.detail.column: None\
        legend.key.title.text: column_name\
        mark.bar.show: true\
        mark.line.show: false\
        mark.marker.show: false\
        series.aggregation: sum\
    labelled:          *# \[parameters and their values, or non-standard\]; The bars, each with its value.*\
        axis.x.data.column: Cell\
        axis.y.data.column: "Power Density (mW/cm²)"\
        axis.y.data.aggregation: max\
        axis.x.tick.algorithm: all\
        encoding.color.column: None\
        encoding.detail.column: None\
        mark.bar.show: true\
        mark.line.show: false\
        mark.marker.show: false\
        series.value_label.show: true\
    horizontal_bars:          *# \[parameters and their values, or non-standard\]; Each cell's peak power density as a horizontal bar, so the categories are on y.*\
        series.base_axis: y\
        axis.x.data.column: "Power Density (mW/cm²)"\
        axis.x.data.aggregation: max\
        axis.y.data.column: Cell\
        encoding.color.column: None\
        encoding.detail.column: None\
        mark.bar.show: true\
        mark.line.show: false\
        mark.marker.show: false\
    marked_categories:          *# \[parameters and their values, or non-standard\]; Each cell's highest temperature as a marker: categories drawn without bars, and few y values.*\
        axis.x.data.column: Cell\
        axis.y.data.column: "Temperature (°C)"\
        axis.y.data.aggregation: max\
        encoding.color.column: None\
        encoding.detail.column: None\
        mark.line.show: false\
    marked_across:          *# \[parameters and their values, or non-standard\]; The same markers, the categories on y: few x values.*\
        series.base_axis: y\
        axis.x.data.column: "Temperature (°C)"\
        axis.x.data.aggregation: max\
        axis.y.data.column: Cell\
        encoding.color.column: None\
        encoding.detail.column: None\
        mark.line.show: false\
    dated: {data.file: dated.parquet, axis.x.data.column: Date}          *# \[parameters and their values, or non-standard\]; Daily dates on x.*
