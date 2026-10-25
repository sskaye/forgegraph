# Catalog specification: base_theme

This page mirrors src/forgegraph/packs/forgegraph_base/catalogs/themes/base_theme.yaml, which is the specification. A test fails if they ever differ.

name: base_theme          *# \[theme\]; The theme this catalog shows.*\
version: 0          *# \[int\]; The version number of the specification.*\
description: Cards for the base theme.          *# \[text\]; The description of the catalog.*\
extends: None          *# \[None, catalog\]; The catalog this one extends: its baselines come before this file's own, and a header field set to None here is taken from it. None: it extends none.*\
baseline: forgegraph_base/polarization          *# \[graphspec\]; The GraphSpec every card changes, drawn with the theme this catalog shows.*\
 \
baselines:          *# Numbered baselines: generic scenarios, each the baseline with one or more changes, numbered in order of first use. Every variable parameter gets one card, by rule: its first candidate value that changes the drawing, on the baseline or on the first of these where it does. None if none.*\
    styled_by_size: {encoding.line_style: Cell Size}          *# \[parameters and their values, or non-standard\]; series.line.style acts only with encoding.line_style set.*\
    colored_by_temperature: {encoding.color: "Temperature (°C)"}          *# \[parameters and their values, or non-standard\]; A numeric encoding.color, so a color bar is drawn.*\
    fanned: {data.file: fanned.parquet}          *# \[parameters and their values, or non-standard\]; Curves ending at the same current: their labels fit only past the line ends.*\
    bars:          *# \[parameters and their values, or non-standard\]; Each cell's peak power density as a bar, so the bar parameters act.*\
        axis.x.data.column: Cell\
        axis.y.data.column: "Power Density (mW/cm²)"\
        axis.y.data.aggregation: max\
        axis.x.tick.algorithm: all\
        encoding.color: None\
        encoding.detail: None\
        mark.bar.show: true\
        mark.line.show: false\
        mark.marker.show: false\
    grouped:          *# \[parameters and their values, or non-standard\]; Peak power by cell, a bar per run side by side, so the gap acts.*\
        axis.x.data.column: Cell\
        axis.y.data.column: "Power Density (mW/cm²)"\
        axis.y.data.aggregation: max\
        axis.x.tick.algorithm: all\
        encoding.color: Run\
        encoding.color_type: categorical\
        encoding.detail: None\
        legend.key.title.text: column_name\
        mark.bar.show: true\
        mark.line.show: false\
        mark.marker.show: false\
        series.offset: side_by_side\
        series.bar.width: 1.8\
        series.benchmark.bar.width: 1.8\
    error_bars:          *# \[parameters and their values, or non-standard\]; An error bar on every point, so the error bar parameters act.*\
        layers.spread.type: error_bar\
        layers.spread.value.lower: 0.02\
        layers.spread.value.upper: 0.02
