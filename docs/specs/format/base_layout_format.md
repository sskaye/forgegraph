# Format specification: base_layout_format

This page mirrors src/forgegraph/packs/forgegraph_base/formats/base_layout_format.yaml, which is the specification. A test fails if they ever differ.

name: base_layout_format          *# \[text\]; The name of the format.*\
version: 0          *# \[int ≥ 0\]; The version number of the specification.*\
description: Twice the base format's width, for two graphs side by side at its text size.          *# \[text\]; The description of the format.*\
extends: forgegraph_base/base_format          *# \[None, format\]; Each parameter not listed is inherited from this format. If None, this file must list every parameter.*\
 \
parameters:          *# !var/!fix sets whether a GraphSpec or layout may change a property. Subcategories/parameters inherit the setting of the one above them unless explicitly overridden.*\
    figure:\
        width: 300          *# \[auto, float > 0\]; The figure's width in mm. auto calculates it from the height and plot_area.aspect_ratio. Width and height can't both be auto.*
