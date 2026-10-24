# Catalog specification: base_format

This page mirrors src/forgegraph/packs/forgegraph_base/catalogs/formats/base_format.yaml, which is the specification. A test fails if they ever differ.

name: base_format          *# \[format\]; The format this catalog shows.*\
version: 0          *# \[int\]; The version number of the specification.*\
description: Cards for the base format.          *# \[text\]; The description of the catalog.*\
extends: None          *# \[None, catalog\]; Each parameter not listed is taken from this catalog. If None, this file must list every parameter.*\
baseline: forgegraph_base/polarization          *# \[graphspec\]; The GraphSpec every card changes, drawn with the format this catalog shows.*\
 \
baselines: None          *# Numbered baselines: the baseline with one change, named for variations' from; numbered in order of first use. None if none.*\
 \
variations:          *# Every parameter of the format, by category: its card's value. {value, from, with}: start from a numbered baseline, or change other parameters too. no_card: no card.*\
    figure:\
        width: 120          *# \[auto, positive float\]; Width, mm. auto: from height and plot_area.aspect. Not both auto.*\
        height: 140          *# \[auto, positive float\]; Height, mm. auto: from width and plot_area.aspect.*\
        base_size: 12          *# \[positive float\]; Base size, pt. Text, lines, ticks and gaps are multiples of it.*\
    output:\
        file_types: no_card          *# \[png, jpg, tiff, svg, pdf\]; File types saved.*\
        dpi: no_card          *# \[positive int\]; Resolution of png, jpg and tiff, dots per inch.*\
    provenance:\
        level: no_card          *# \[full, minimal, off\]; Which entries of the provenance record (docs/specs/provenance) each saved file carries. off: none.*
