# Format example: journal-double

This page mirrors review/phase-07/deliverable/paper/formats/journal-double.yaml, which is the specification. A test fails if they ever differ.

name: journal-double          *# \[text\]; The name of the format.*\
version: 0          *# \[int\]; The version number of the specification.*\
description: A two-column journal figure, 183 mm wide, with 7 pt text.          *# \[text\]; The description of the format.*\
extends: forgegraph_base/base_format          *# \[None, format\]; Each parameter not listed is inherited from this format. If None, this file must list every parameter.*\
 \
fixed_parameters:          *# List of fixed parameters for the format.*\
    figure:\
        width: 183          *# \[auto, positive float\]; Width, mm. auto: from height and plot_area.aspect. Not both auto.*\
        height: auto          *# \[auto, positive float\]; Height, mm. auto: from width and plot_area.aspect.*\
        base_size: 7          *# \[positive float\]; Base size, pt. Text, lines, ticks and gaps are multiples of it.*\
 \
variable_parameters:          *# List of variable parameters for the format, None if none.*\
    output:\
        file_types: \[pdf, png\]          *# \[png, jpg, tiff, svg, pdf, html\]; File types saved.*
