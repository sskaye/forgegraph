# Pack example: acme/dashboard, a layout

This page mirrors examples/packs/acme/layouts/dashboard.yaml, which is the specification. A test fails if they ever differ.

name: dashboard          *# \[text\]; The name of the layout.*\
version: 0          *# \[int ≥ 0\]; The version number of the specification.*\
description: Acme's dashboard spacing on a slide; a layout extends it and lists its own tabs.          *# \[text\]; The description of the layout.*\
extends: forgegraph_default/layout          *# \[None, layout\]; Each parameter not listed is inherited from this layout. If None, this file must list every parameter.*\
 \
parameters:          *# !var/!fix sets whether a layout may change a property. Subcategories/parameters inherit the setting of the one above them unless explicitly overridden.*\
    specifications:\
        format: acme/slide          *# \[format\]; The format that sets the size and output of the whole layout.*\
    separators:\
        gap:\
            outer: 2          *# \[float ≥ 0\]; The space between neighboring tiles, from the outermost text or line of one to that of the next, × base size.*\
        line:\
            width: 0.05          *# \[float ≥ 0\]; The width of the line along the middle of each gap between tiles, × base size. If 0, no line is drawn.*

