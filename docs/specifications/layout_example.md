# Layout specification: layout_example

This page mirrors src/forgegraph/specifications/layout_example.yaml, which is the specification. A test fails if they ever differ.

name: layout_example          *# \[text\]; The name of the layout.*\
version: 0          *# \[int ≥ 0\]; The version number of the specification.*\
description: An example layout to define the specification.          *# \[text\]; The description of the layout.*\
extends: None          *# \[None, layout\]; Each parameter not listed is inherited from this layout. If None, this file must list every parameter.*\
 \
parameters: !var          *# !var/!fix sets whether a layout may change a property. Subcategories/parameters inherit the setting of the one above them unless explicitly overridden.*\
    specifications:\
        format: forgegraph_default/wide_format          *# \[format\]; The format that sets the layout's size and output, in place of its tiles' formats.*\
    separators:          *# The space and lines between and around the figures. The gaps use the background.color of the first tile's theme.*\
        gap:\
            inner: 1.5          *# \[float ≥ 0\]; The space between the figure's edges and the outer tiles, × base size.*\
            outer: 1.5          *# \[float ≥ 0\]; The space between neighboring tiles, from the outermost text or line of one to that of the next, × base size.*\
        line:          *# \[line style\]; The line along the middle of each gap between tiles. Its defaults are the first tile's theme's line.*\
        border:\
            show: false          *# \[true, false\]; Whether to also draw the line around the outside of the tiles, through the middle of the inner gap.*\
        corner_radius: 0          *# \[float ≥ 0\]; The radius of the corners of each tile's background, × base size.*\
    tabs:          *# The layout's tabs, in order, <!-- fmc:1 -->each under the name shown on its tab<!-- /fmc:1 -->. A layout's tabs replace those it inherits.*\
        main:\
            grid:\
                areas: \[\[a\]\]          *# \[text grid\]; A list of tiles for each row. A . leaves a cell blank. A name repeated over a rectangle of cells makes that tile span them, e.g. \[a, a\] makes tile a span two columns.*\
                column_widths: None          *# \[None, floats > 0\]; The relative widths of the columns' plot boxes. If None, they're equal.*\
                row_heights: None          *# \[None, floats > 0\]; The relative heights of the rows' plot boxes. If None, they're equal, or as tall as the tiles need.*\
            tiles:          *# The GraphSpec drawn in each area of the grid, under the area's name.*\
                a: None          *# \[text\]; The GraphSpec file: an absolute path, a path starting with ~, or a path relative to this file. A layout must set it.*

<!-- forgemark-comments
- id: 1
  anchor_text: "each under the name shown on its tab"
  context_before: "s of each tile's background, × base size.*\\ tabs: # The layout's tabs, in order,"
  context_after: ". A layout's tabs replace those it inherits.*\\ main:\\ grid:\\ areas: \\[\\[a\\]\\] #"
  author: Claude
  timestamp: 2026-10-29T03:24:33Z
  resolved: false
  body: |
    Proposal for the HTML page's tab bar, with no new parameter.
    
    Problem: the page draws the tab names in the browser's font and in dark grey (#333333), whatever the theme. A layout with a dark background gets an unreadable tab bar, and the tab names never match the figures' text.
    
    Proposed change: the tab bar takes its look from what the layout already has, as the gaps already take the first tile's theme's background.color.
    1. Each tab's name, as written under tabs, is drawn in the first tile's theme's general text: its font, weight and color, at text.size × the layout's base size.
    2. The selected tab is underlined in that text color.
    3. The line under the tab bar is separators.line, whose defaults are the first tile's theme's line.
    4. The page embeds the font, since a browser shows a typeface only if the viewer has it installed or the page carries it.
    
    Nothing is added to this specification or the theme's. The tabs description would end: "Their names are written in the first tile's theme's text."
    
    Alternative: a tab_label text style here, with the first tile's theme's text as its defaults, as separators.line takes the theme's line. It would let a layout style its tab names apart from the figures' text, but nothing has asked for that.
    
    Recommendation: no new parameter.
-->
