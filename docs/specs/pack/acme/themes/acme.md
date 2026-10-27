# Pack example: acme/acme, a theme

This page mirrors examples/packs/acme/themes/acme.yaml, which is the specification. A test fails if they ever differ.

name: acme          *# \[text\]; The name of the theme.*\
version: 0          *# \[int ≥ 0\]; The version number of the specification.*\
description: Acme's house style, a serif look with a light grid and no box.          *# \[text\]; The description of the theme.*\
extends: forgegraph_base/base_theme          *# \[None, theme\]; Each parameter not listed is inherited from this theme. If None, this file must list every parameter.*\
 \
parameters:          *# !var/!fix sets whether a GraphSpec may change a property. Subcategories/parameters inherit the setting of the one above them unless explicitly overridden.*\
    font:\
        family: IBM Plex Serif          *# \[text\]; Typeface for all text.*\
    title:\
        weight: medium          *# \[light, regular, medium, semibold, bold\]; Title weight.*\
    axis:\
        title:\
            weight: regular          *# \[light, regular, medium, semibold, bold\]; Axis title weight.*\
    plot_area:\
        sides: \[left, bottom\]          *# \[left, right, top, bottom, None\]; Sides with a border line. None: none.*\
        aspect: 1.6          *# \[float > 0\]; Plot area width ÷ height.*\
    grid:\
        color: "#DDDDDD"          *# \[hex color\]; Grid color.*\
        show: true          *# \[true, false\]; Draw a grid.*\
    series:\
        colors: tol_muted          *# \[okabe_ito, tol_bright, tol_muted, tableau_10, color_blind, hex colors\]; Colors for encoding.color.column groups, in order, then repeating: a named palette, or a list of colors.*
