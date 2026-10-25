# Format example: ops/dashboard

This page mirrors examples/layouts/dashboard/ops/formats/dashboard.yaml, which is the specification. A test fails if they ever differ.

name: dashboard          *# \[text\]; The name of the format.*\
version: 0          *# \[int\]; The version number of the specification.*\
description: A 16:9 dashboard page, 420 × 236 mm, with 14 pt text.          *# \[text\]; The description of the format.*\
extends: forgegraph_base/base_format          *# \[None, format\]; Each parameter not listed is inherited from this format. If None, this file must list every parameter.*\
 \
fixed_parameters:          *# List of fixed parameters for the format.*\
    figure:\
        width: 420          *# \[auto, positive float\]; Width, mm. auto: from height and plot_area.aspect. Not both auto.*\
        height: 236          *# \[auto, positive float\]; Height, mm. auto: from width and plot_area.aspect.*\
        base_size: 14          *# \[positive float\]; Base size, pt. Text, lines, ticks and gaps are multiples of it.*\
    output:\
        dpi: 300          *# \[positive int\]; Resolution of png, jpg and tiff, dots per inch.*\
 \
variable_parameters:          *# List of variable parameters for the format, None if none.*\
    output:\
        file_types: \[png, html\]          *# \[png, jpg, tiff, svg, pdf, html\]; File types saved.*
