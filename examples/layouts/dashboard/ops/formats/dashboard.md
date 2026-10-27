# Format example: ops/dashboard

This page mirrors examples/layouts/dashboard/ops/formats/dashboard.yaml, which is the specification. A test fails if they ever differ.

name: dashboard          *# \[text\]; The name of the format.*\
version: 0          *# \[int ≥ 0\]; The version number of the specification.*\
description: A 16:9 dashboard page, 420 × 236 mm, with 14 pt text.          *# \[text\]; The description of the format.*\
extends: forgegraph_base/base_format          *# \[None, format\]; Each parameter not listed is inherited from this format. If None, this file must list every parameter.*\
 \
parameters:          *# !var/!fix sets whether a GraphSpec or layout may change a property. Subcategories/parameters inherit the setting of the one above them unless explicitly overridden.*\
    figure:\
        width: 420          *# \[auto, float > 0\]; The figure's width in mm. auto calculates it from the height and plot_area.aspect_ratio. Width and height can't both be auto.*\
        height: 236          *# \[auto, float > 0\]; The figure's height in mm. auto calculates it from the width and plot_area.aspect_ratio.*\
        base_size: 14          *# \[float > 0\]; The base size in points. The sizes of text, lines, ticks and gaps are multiples of it.*\
    output:\
        dpi: 300          *# \[int > 0\]; The resolution of png, jpg and tiff files, in dots per inch.*\
        file_types: \[png, html\]          *# \[png, jpg, tiff, svg, pdf, html\]; The file types to save.*
