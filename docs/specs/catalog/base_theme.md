# Catalog specification: base_theme

This page mirrors src/forgegraph/packs/forgegraph_base/catalogs/themes/base_theme.yaml, which is the specification. A test fails if they ever differ.

name: base_theme          *# \[theme\]; The theme this catalog shows.*\
version: 0          *# \[int ≥ 0\]; The version number of the specification.*\
description: Cards for the base theme.          *# \[text\]; The description of the catalog.*\
extends: None          *# \[None, catalog\]; The catalog this one extends. Its baselines come before this file's own, and a header field set to None here is taken from it. If None, this catalog extends no other.*\
baseline: forgegraph_base/graphspec_example          *# \[graphspec\]; The GraphSpec every card changes, drawn with the theme this catalog shows.*\
 \
baselines:          *# Generic scenarios, each the baseline with one or more changes, numbered in the order they're first used. Every parameter gets one card, chosen by a rule: the first candidate value that changes the drawing, on the baseline or on the first of these scenarios where it does. The page shows the cards of the variable parameters. If there are no scenarios, this is None.*\
    styled_by_size: {series.line.style: Cell Size}          *# \[parameters and their values, or non-standard\]; The theme's series.line.styles act only when a series' line.style is a column.*\
    colored_by_temperature: {series.color: "Temperature (°C)"}          *# \[parameters and their values, or non-standard\]; A numeric color column, so a color bar is drawn.*\
    fanned: {data.file: fanned.parquet}          *# \[parameters and their values, or non-standard\]; Curves ending at the same current: their labels fit only past the line ends.*\
    bars:          *# \[parameters and their values, or non-standard\]; Each cell's peak power density as a bar, so the bar parameters act.*\
        axis.x.data.column: Cell\
        axis.x.tick.algorithm: all\
        series: {"Power Density (mW/cm²)": {color: series, split: None, aggregation: {function: max}, bar: {show: true}, line: {show: false}, marker: {show: false}}}\
    grouped:          *# \[parameters and their values, or non-standard\]; Peak power by cell, a bar per run side by side, so the gap acts.*\
        axis.x.data.column: Cell\
        axis.x.tick.algorithm: all\
        legend.key.title.text: column_name\
        arrangement.offset: side_by_side\
        series: {"Power Density (mW/cm²)": {color: Run, split: None, aggregation: {function: max}, color_scale: categorical, bar: {show: true}, line: {show: false}, marker: {show: false}}}\
    error_bars:          *# \[parameters and their values, or non-standard\]; An error bar on every point, so the error bar parameters act.*\
        layers.spread.type: error_bar\
        layers.spread.value.lower: 0.02\
        layers.spread.value.upper: 0.02\
    log_x: {axis.x.scale: log}          *# \[parameters and their values, or non-standard\]; A log x axis, so the log tick algorithm acts.*\
    minor_ticks: {axis.tick.minor.count: 4}          *# \[parameters and their values, or non-standard\]; Minor tick sizes act only on minor ticks.*\
    grid_shown: {grid.x.show: true, grid.y.show: true}          *# \[parameters and their values, or non-standard\]; The grid's parameters act only on a shown grid.*\
    thick_lines: {series.line.width: 1.2}          *# \[parameters and their values, or non-standard\]; Thick lines, so their corners show.*\
    key_framed: {legend.method: key, legend.key.border.style: solid}          *# \[parameters and their values, or non-standard\]; The key, framed, so the frame's width acts.*\
    non_standard: non-standard          *# \[parameters and their values, or non-standard\]; Drawn on after ForgeGraph finished, so the watermark shows.*\
    footnoted: footnoted          *# \[parameters and their values, non-standard, or footnoted\]; With a footnote, as a scheduled run's stamp.*\
    dated: {data.file: dated.parquet, axis.x.data.column: Date, axis.x.title: Day}          *# \[parameters and their values, or non-standard\]; Daily dates on x, so date labels show.*\
    labelled:          *# \[parameters and their values, or non-standard\]; The bars, each with its value, so the value label parameters act.*\
        axis.x.data.column: Cell\
        axis.x.tick.algorithm: all\
        series: {"Power Density (mW/cm²)": {color: series, split: None, aggregation: {function: max}, bar: {show: true}, line: {show: false}, marker: {show: false}, value_label: {show: true}}}\
    labelled_beyond:          *# \[parameters and their values, or non-standard\]; The bars, each with its value beyond it, so the value labels' own color shows.*\
        axis.x.data.column: Cell\
        axis.x.tick.algorithm: all\
        series: {"Power Density (mW/cm²)": {color: series, split: None, aggregation: {function: max}, bar: {show: true}, line: {show: false}, marker: {show: false}, value_label: {show: true, position: outside}}}\
    wrapped:          *# \[parameters and their values, or non-standard\]; The bars, with a cell name wider than the space between ticks, so it wraps.*\
        axis.x.data.column: Cell\
        axis.x.tick.algorithm: all\
        data.file: reinforced.parquet\
        series: {"Power Density (mW/cm²)": {color: series, split: None, aggregation: {function: max}, bar: {show: true}, line: {show: false}, marker: {show: false}}}\
    target:          *# \[parameters and their values, or non-standard\]; A reference band with a labelled line, so its lines', label's and fill's parameters act.*\
        layers.target.type: reference\
        layers.target.axis: y\
        layers.target.line_1.value: 1.2\
        layers.target.line_1.label.text: Target\
        layers.target.line_2.value: 1.4\
    noted:          *# \[parameters and their values, or non-standard\]; A note, so its parameters act.*\
        layers.conditions.type: note\
        layers.conditions.text: "60 °C, 1 atm, H\_{2}/air"
