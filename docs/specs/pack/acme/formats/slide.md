# Pack example: acme/slide, a format

This page mirrors examples/packs/acme/formats/slide.yaml, which is the specification. A test fails if they ever differ.

name: slide          *# \[text\]; The name of the format.*\
version: 0          *# \[int ≥ 0\]; The version number of the specification.*\
description: A full-width graph on a 16:9 slide.          *# \[text\]; The description of the format.*\
extends: forgegraph_base/base_format          *# \[None, format\]; Each parameter not listed is inherited from this format. If None, this file must list every parameter.*\
 \
parameters:          *# !var/!fix sets whether a GraphSpec or layout may change a property. Subcategories/parameters inherit the setting of the one above them unless explicitly overridden.*\
    figure:\
        width: 254          *# \[auto, float > 0\]; The figure's width in mm. auto calculates it from the height and plot_area.aspect_ratio. Width and height can't both be auto.*\
        height: 143          *# \[auto, float > 0\]; The figure's height in mm. auto calculates it from the width and plot_area.aspect_ratio.*\
        base_size: 20          *# \[float > 0\]; The base size in points. The sizes of text, lines, ticks and gaps are multiples of it.*
