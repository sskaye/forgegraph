# Format: forgegraph_base_2/compact_format

This page mirrors src/forgegraph/packs/forgegraph_base_2/formats/compact_format.yaml, which is the specification. A test fails if they ever differ.

name: compact_format          *# \[text\]; The name of the format.*\
version: 0          *# \[int ≥ 0\]; The version number of the specification.*\
description: About 4 in across at 11 pt, saved at 200 dpi.          *# \[text\]; The description of the format.*\
extends: forgegraph_base/base_format          *# \[None, format\]; Each parameter not listed is inherited from this format. If None, this file must list every parameter.*\
 \
parameters:          *# !var/!fix sets whether a GraphSpec or layout may change a property. Subcategories/parameters inherit the setting of the one above them unless explicitly overridden.*\
    figure:\
        width: 106          *# \[auto, float > 0\]; Width, mm. auto: from height and plot_area.aspect. Not both auto.*\
        base_size: 11          *# \[float > 0\]; Base size, pt. Text, lines, ticks and gaps are multiples of it.*\
    output:\
        dpi: 200          *# \[int > 0\]; Resolution of png, jpg and tiff, dots per inch.*
