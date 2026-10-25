# Format specification: base_format

This page mirrors src/forgegraph/packs/forgegraph_base/formats/base_format.yaml, which is the specification. A test fails if they ever differ.

name: base_format          *# \[text\]; The name of the format.*\
version: 0          *# \[int\]; The version number of the specification.*\
description: The base format that others can inherit from.          *# \[text\]; The description of the format.*\
extends: None          *# \[None, format\]; Each parameter not listed is inherited from this format. If None, this file must list every parameter.*\
 \
fixed_parameters:          *# List of fixed parameters for the format.*\
    figure:\
        width: 150          *# \[auto, positive float\]; Width, mm. auto: from height and plot_area.aspect. Not both auto.*\
        height: auto          *# \[auto, positive float\]; Height, mm. auto: from width and plot_area.aspect.*\
        base_size: 18          *# \[positive float\]; Base size, pt. Text, lines, ticks and gaps are multiples of it.*\
    output:\
        dpi: 600          *# \[positive int\]; Resolution of png, jpg and tiff, dots per inch.*\
 \
variable_parameters:          *# List of variable parameters for the format, None if none.*\
    output:\
        file_types: \[png\]          *# \[png, jpg, tiff, svg, pdf, html\]; File types saved.*\
    provenance:\
        level: full          *# \[full, minimal, off\]; What each saved file records of how it was made. full: every value and the data file. minimal: the GraphSpec and specs, without them. off: nothing.*
