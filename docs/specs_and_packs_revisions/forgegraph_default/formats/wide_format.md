# Format specification: wide_format

<!-- fmc:1 -->This page mirrors src/forgegraph/packs/forgegraph_base/formats/base_format.yaml,<!-- /fmc:1 --> which is the specification. A test fails if they ever differ.

name: graph_format          *# \[text\]; The name of the format.*\
version: 0.1          *# \[int ≥ 0\]; The version number of the specification.*\
description: Default format to use for individual graphs.          *# \[text\]; The description of the format.*\
extends: None          *# \[None, format\]; Each parameter not listed is inherited from this format. If None, this file must list every parameter.*\
 \
parameters: !var          *# !var/!fix sets whether a GraphSpec or layout may change a property. Subcategories/parameters inherit the setting of the one above them unless explicitly overridden.*\
    figure:\
        width: <!-- fmc:3 -->450<!-- /fmc:3 -->          *# \[auto, float > 0\]; The figure's width in mm. auto calculates it from the height and plot_area.aspect_ratio. Width and height can't both be auto.*\
        height: auto          *# \[auto, float > 0\]; The figure's height in mm. auto calculates it from the width and plot_area.aspect_ratio.*\
        base_size: 18          *# \[float > 0\]; The base size in points. The sizes of text, lines, ticks and gaps are multiples of it.*\
    output:\
        dpi: 600          *# \[int > 0\]; The resolution of png, jpg and tiff files, in dots per inch.*\
        file_types: \[png\]          *# \[png, jpg, tiff, svg, pdf, html\]; The file types to save.*\
    provenance:\
        level: full          *# \[full, minimal, off\]; What each saved file records about how it was made. full records every value and the data file. minimal records the GraphSpec and the specs. off records nothing.*

<!-- forgemark-comments
- id: 1
  anchor_text: "This page mirrors src/forgegraph/packs/forgegraph_base/formats/base_format.yaml,"
  context_before: "# Format specification: forgegraph_default_format"
  context_after: "which is the specification."
  author: "Steven Kaye"
  timestamp: "2026-10-27T19:05:05.573Z"
  resolved: false
  body: fix
- id: 3
  anchor_text: "450"
  context_before: "he setting of the one above them unless explicitly overridden.*\\ figure:\\ width:"
  context_after: "# \\[auto, float > 0\\]; The figure's width in mm."
  author: "Steven Kaye"
  timestamp: "2026-10-27T19:11:02.971Z"
  resolved: false
  body: "Please replace with what we’ve been using for layout formats."
-->
