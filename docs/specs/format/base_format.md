# Format specification: base_format

This page mirrors src/forgegraph/packs/forgegraph_base/formats/base_format.yaml, which is the specification. A test fails if they ever differ.

name: base_format          *# \[text\]; The name of the format.*\
version: 0          *# \[int ≥ 0\]; The version number of the specification.*\
description: The base format that others can inherit from.          *# \[text\]; The description of the format.*\
extends: None          *# \[None, format\]; Each parameter not listed is inherited from this format. If None, this file must list every parameter.*\
 \
parameters: !fix          *# !var/!fix sets whether a GraphSpec or layout may change a property. Subcategories/parameters inherit the setting of the one above them unless explicitly overridden.*\
    figure:\
        width: 150          *# \[auto, float > 0\]; Width, mm. auto: from height and plot_area.aspect. Not both auto.*\
        height: auto          *# \[auto, float > 0\]; Height, mm. auto: from width and plot_area.aspect.*\
        base_size: 18          *# \[float > 0\]; Base size, pt. Text, lines, ticks and gaps are multiples of it.*\
    output:\
        dpi: 600          *# \[int > 0\]; Resolution of png, jpg and tiff, dots per inch.*\
        file_types: !var \[png\]          *# \[png, jpg, tiff, svg, pdf, html\]; File types saved.*\
    provenance: !var\
        level: full          *# \[full, minimal, off\]; What each saved file records of how it was made. full: every value and the data file. minimal: the GraphSpec and specs, without them. off: nothing.*
