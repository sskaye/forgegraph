# Catalog specification: xy

This page mirrors src/forgegraph/specifications/catalogs/graphtype_xy.yaml, which is the specification. A test fails if they ever differ.

name: xy          *# \[graph type\]; The graph type this catalog shows.*\
version: 0          *# \[int ≥ 0\]; The version number of the specification.*\
description: Cards for the xy graph type.          *# \[text\]; The description of the catalog.*\
extends: None          *# \[None, catalog\]; The catalog this one extends. Its baselines come before this file's own, and a header field set to None here is taken from it. If None, this catalog extends no other.*\
baseline: forgegraph_default/graphspec_example          *# \[graphspec\]; The GraphSpec every card changes, drawn with the graph type this catalog shows.*\
 \
baselines:          *# Generic scenarios, each the baseline with one or more changes, numbered in the order they're first used. Every parameter gets one card, chosen by a rule: the first candidate value that changes the drawing, on the baseline or on the first of these scenarios where it does. The page shows the cards of the variable parameters. If there are no scenarios, this is None.*\
    key_shown: {legend.method: key}          *# \[parameters and their values, or non-standard\]; Series named in a key, so the key's parameters act.*\
    colored_by_temperature: {series.color: "Temperature (°C)"}          *# \[parameters and their values, or non-standard\]; A numeric color column, so a color bar is drawn.*\
    colored_by_run: {series.color: Run}          *# \[parameters and their values, or non-standard\]; Colored by run, a column of numbers, so auto draws a color scale.*\
    temperatures:          *# \[parameters and their values, or non-standard\]; Each cell's peak power density at each temperature it ran at.*\
        axis.x.data.column: "Temperature (°C)"\
        series: {"Power Density (mW/cm²)": {color: Cell, split: None, aggregation: {function: max}}}\
    percentiles:          *# \[parameters and their values, or non-standard\]; Each cell's median power density at each temperature it ran at, so the percentile acts.*\
        axis.x.data.column: "Temperature (°C)"\
        series: {"Power Density (mW/cm²)": {color: Cell, split: None, aggregation: {function: percentile}}}\
    x_manual: {axis.x.tick.algorithm: manual, axis.x.tick.step: 20}          *# \[parameters and their values, or non-standard\]; x ticks every 20, so the step acts.*\
    y_manual: {axis.y.tick.algorithm: manual, axis.y.tick.step: 0.05}          *# \[parameters and their values, or non-standard\]; y ticks every 0.05, so the step acts.*\
    bars:          *# \[parameters and their values, or non-standard\]; Each cell's peak power density as a bar.*\
        axis.x.data.column: Cell\
        axis.x.tick.algorithm: all\
        series: {"Power Density (mW/cm²)": {color: series, split: None, aggregation: {function: max}, bar: {show: true}, line: {show: false}, marker: {show: false}}}\
    overlaid:          *# \[parameters and their values, or non-standard\]; Peak power by cell, a bar per run, the runs drawn over each other.*\
        axis.x.data.column: Cell\
        axis.x.tick.algorithm: all\
        legend.key.title.text: column_name\
        series: {"Power Density (mW/cm²)": {color: Run, split: None, aggregation: {function: max}, color_scale: categorical, bar: {show: true}, line: {show: false}, marker: {show: false}}}\
    stacked:          *# \[parameters and their values, or non-standard\]; The runs' bars stacked.*\
        axis.x.data.column: Cell\
        axis.x.tick.algorithm: all\
        legend.key.title.text: column_name\
        arrangement.stacking: sum\
        series: {"Power Density (mW/cm²)": {color: Run, split: None, aggregation: {function: max}, color_scale: categorical, bar: {show: true}, line: {show: false}, marker: {show: false}}}\
    labelled:          *# \[parameters and their values, or non-standard\]; The bars, each with its value.*\
        axis.x.data.column: Cell\
        axis.x.tick.algorithm: all\
        series: {"Power Density (mW/cm²)": {color: series, split: None, aggregation: {function: max}, bar: {show: true}, line: {show: false}, marker: {show: false}, value_label: {show: true}}}\
    horizontal_bars:          *# \[parameters and their values, or non-standard\]; Each cell's peak power density as a horizontal bar, so the categories are on y.*\
        arrangement.base_axis: y\
        axis.y.data.column: Cell\
        axis.x.data.column: None\
        series: {"Power Density (mW/cm²)": {color: series, split: None, aggregation: {function: max}, bar: {show: true}, line: {show: false}, marker: {show: false}}}\
    marked_categories:          *# \[parameters and their values, or non-standard\]; Each cell's highest temperature as a marker: categories drawn without bars, and few y values.*\
        axis.x.data.column: Cell\
        series: {"Temperature (°C)": {color: series, split: None, aggregation: {function: max}, line: {show: false}}}\
    marked_across:          *# \[parameters and their values, or non-standard\]; The same markers, the categories on y: few x values.*\
        arrangement.base_axis: y\
        axis.y.data.column: Cell\
        axis.x.data.column: None\
        series: {"Temperature (°C)": {color: series, split: None, aggregation: {function: max}, line: {show: false}}}\
    dated: {data.file: dated.parquet, axis.x.data.column: Date}          *# \[parameters and their values, or non-standard\]; Daily dates on x.*
