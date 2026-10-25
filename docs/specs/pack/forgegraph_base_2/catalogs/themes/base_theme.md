# Catalog: forgegraph_base_2's base_theme

This page mirrors src/forgegraph/packs/forgegraph_base_2/catalogs/themes/base_theme.yaml, which is the specification. A test fails if they ever differ.

name: base_theme          *# \[theme\]; The theme this catalog shows.*\
version: 0          *# \[int\]; The version number of the specification.*\
description: Cards for the forgegraph_base_2 theme, the base theme's cards drawn in it.          *# \[text\]; The description of the catalog.*\
extends: forgegraph_base/base_theme          *# \[None, catalog\]; Each parameter not listed is taken from this catalog. If None, this file must list every parameter.*\
baseline: forgegraph_base_2/example          *# \[graphspec\]; The GraphSpec every card changes, drawn with the theme this catalog shows.*\
 \
baselines:          *# Numbered baselines: the baseline with one or more changes, named for variations' from; numbered in order of first use. None if none.*\
    direct_named: {legend.method: direct}          *# \[parameters and their values, or non-standard\]; Series named beside the lines, so the direct labels' parameters act.*\
    fanned_direct: {data.file: fanned.parquet, legend.method: direct}          *# \[parameters and their values, or non-standard\]; Fanned curves named beside the lines, so the axis grows for their labels.*\
 \
variations:          *# Every parameter of the theme, by category: its card's value. {value, from, with}: start from a numbered baseline, or change other parameters too. no_card: no card.*\
    series:          *# This theme draws no bar or benchmark outlines, so their widths change nothing.*\
        bar:\
            edge_width: no_card          *# \[positive float\]; Bar outline width, × base size.*\
        benchmark:\
            marker:\
                edge_width: no_card          *# \[positive float\]; Benchmark marker outline width, × base size.*\
            bar:\
                edge_width: no_card          *# \[positive float\]; Benchmark bar outline width, × base size.*\
    legend:\
        color_bar:\
            colors: {value: cividis, from: colored_by_temperature}          *# \[viridis, cividis, plasma, inferno, magma, greys, blues, red_blue, hex color, two hex colors\]; Colors for a numeric encoding.color: a named scale, one hex color (light to it) or two (first to second).*\
        direct:\
            clearance: {value: 0.4, from: direct_named}          *# \[positive float\]; Minimum gap around a direct label, × base size.*\
            max_relative_distance: {value: 0.5, from: direct_named}          *# \[0-1\]; Most a label's distance to its series may be, ÷ its distance to the next nearest.*\
            max_axis_extension: {value: 0.4, from: fanned_direct}          *# \[0-1\]; Most the x-axis may grow to fit labels, × its range.*
