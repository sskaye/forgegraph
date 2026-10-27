# Format example: journal/journal-double

This page mirrors examples/layouts/paper/journal/formats/journal-double.yaml, which is the specification. A test fails if they ever differ.

name: journal-double          *# \[text\]; The name of the format.*\
version: 0          *# \[int ≥ 0\]; The version number of the specification.*\
description: A two-column journal figure, 183 mm wide, with 7 pt text.          *# \[text\]; The description of the format.*\
extends: forgegraph_default/compact_format          *# \[None, format\]; Each parameter not listed is inherited from this format. If None, this file must list every parameter.*\
 \
parameters:          *# !var/!fix sets whether a GraphSpec or layout may change a property. Subcategories/parameters inherit the setting of the one above them unless explicitly overridden.*\
    figure:\
        width: 183          *# \[auto, float > 0\]; The figure's width in mm. auto calculates it from the height and plot_area.aspect_ratio. Width and height can't both be auto.*\
        height: auto          *# \[auto, float > 0\]; The figure's height in mm. auto calculates it from the width and plot_area.aspect_ratio.*\
        base_size: 7          *# \[float > 0\]; The base size in points. The sizes of text, lines, ticks and gaps are multiples of it.*\
    output:\
        file_types: \[pdf, png\]          *# \[png, jpg, tiff, svg, pdf, html\]; The file types to save.*
