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
    tab_bar:          *# <!-- fmc:3 -->The row of tab names at the top of the HTML page of a layout with more than one tab.<!-- /fmc:3 -->*\
        label:          *# \[text style\]; The tab names. Its defaults are the first tile's theme's text. The selected tab is underlined in its color.*\
        line:          *# \[line style\]; <!-- fmc:4 -->The line under the tab bar, and the border's top when the border is drawn.<!-- /fmc:4 --> Its defaults are the first tile's theme's line.*\
    tabs:          *# The layout's tabs, in order, <!-- fmc:1 -->each under the name shown on its tab<!-- /fmc:1 -->. A tab holds a grid and its tiles, or tabs of its own, to any depth. A layout's tabs replace those it inherits.*\
        main:\
            grid:\
                areas: \[\[a\]\]          *# \[text grid\]; A list of tiles for each row. A . leaves a cell blank. A name repeated over a rectangle of cells makes that tile span them, e.g. \[a, a\] makes tile a span two columns.*\
                column_widths: None          *# \[None, floats > 0\]; The relative widths of the columns' plot boxes. <!-- fmc:2 -->If None, they're equal.<!-- /fmc:2 -->*\
                row_heights: None          *# \[None, floats > 0\]; The relative heights of the rows' plot boxes. If None, they're equal, or as tall as the tiles need.*\
            tiles:          *# The GraphSpec drawn in each area of the grid, under the area's name.*\
                a: None          *# \[text\]; The GraphSpec file: an absolute path, a path starting with ~, or a path relative to this file. A layout must set it.*

<!-- forgemark-comments
- id: 1
  anchor_text: "each under the name shown on its tab"
  context_before: "faults are the first tile's theme's line.*\\ tabs: # The layout's tabs, in order,"
  context_after: ". A tab holds a grid and its tiles, or tabs of its own, to any depth."
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
  replies:
    - author: Steven
      timestamp: "2026-10-29T03:40:06.714Z"
      body: |-
        Better to have the control.
        Proposal:
        - Under tabs, add the param “tab_label” (or whatever the standard name is for the text that appears in a tab), which should be text_style, enabling setting of the params of the tab title text. 
        - The selected tab is underlined in that text color
        - Add an additional parameter for the line under the tab bar. Again, name whatever that’s normally called and make it line style.
        -  The page embeds the font, since a browser shows a typeface only if the viewer has it installed or the page carries it.
    - author: Claude
      timestamp: 2026-10-29T03:41:14Z
      body: |
        Agreed, with one change to where the parameters go and suggested names.
        
        1. They can't go under tabs. tabs is a mapping of the author's own tab names, so a parameter there would read as a tab named tab_label, and a layout couldn't name a tab that. They need a category of their own beside tabs and separators.
        2. Names: the usual name for the strip of tabs is the "tab bar", for the text in a tab its "label", and for the line under the bar a "divider". "line" matches separators.line, so I'd use it over divider.
        
        Proposed lines:
        
            tab_bar:          # The row of tab names at the top of the HTML page of a layout with more than one tab.
                label:          # [text style]; The tab names. Its defaults are the first tile's theme's text. The selected tab is underlined in its color.
                line:          # [line style]; The line under the tab bar. Its defaults are the first tile's theme's line.
        
        3. The selected tab is marked only by its underline. Today it's also drawn semibold; dropping that lets label.weight decide every tab's weight.
        4. With nested tabs (#67), every level's tab bar uses the same style.
        5. These change only the HTML page, since images and PDFs have no tab bar.
    - author: Claude
      timestamp: 2026-10-29T05:16:29Z
      body: |
        Built in sskaye/forgegraph#75 as agreed: tab_bar.label and tab_bar.line, below on this page. The selected tab is underlined in the label's color, the label's alignment places the names and its gap spaces them, the page embeds the label's font, and the line can be solid, dashed or dotted. The default pack's layout keeps no line under the bar.
- id: 2
  anchor_text: "If None, they're equal."
  context_before: "hs: None # \\[None, floats > 0\\]; The relative widths of the columns' plot boxes."
  context_after: "\\ row_heights: None # \\[None, floats > 0\\]; The relative heights of the rows' pl"
  author: Claude
  timestamp: 2026-10-29T15:02:28Z
  resolved: false
  body: |
    Problem: when the format's width is auto, the columns take the widths their tiles' aspect ratios need (drawing/layout.py), as row_heights already says for heights. The same text is in forgegraph_default's layout.
  suggested_edit:
    from: "If None, they're equal."
    to: "If None, they're equal, or as wide as the tiles need."
- id: 3
  anchor_text: "The row of tab names at the top of the HTML page of a layout with more than one tab."
  context_before: "; The radius of the corners of each tile's background, × base size.*\\ tab_bar: #"
  context_after: "\\ label: # \\[text style\\]; The tab names."
  author: Claude
  timestamp: 2026-10-29T15:02:28Z
  resolved: false
  body: |
    Problem: with nested tabs, the page has a row of tab names for each level (drawing/page.py). The same text is in forgegraph_default's layout.
  suggested_edit:
    from: "The row of tab names at the top of the HTML page of a layout with more than one tab."
    to: "The rows of tab names on the HTML page of a layout with more than one tab: one for the layout's tabs, and one under each tab that holds tabs."
- id: 4
  anchor_text: "The line under the tab bar, and the border's top when the border is drawn."
  context_before: "The selected tab is underlined in its color.*\\ line: # \\[line style\\];"
  context_after: "Its defaults are the first tile's theme's line.*\\ tabs: # The layout's tabs, in"
  author: Claude
  timestamp: 2026-10-29T15:02:28Z
  resolved: false
  body: |
    Problem: with nested tabs, every tab bar gets this line, and only the last one's is the border's top. The same text is in forgegraph_default's layout.
  suggested_edit:
    from: "The line under the tab bar, and the border's top when the border is drawn."
    to: "The line under each tab bar. When the border is drawn, the line under the last tab bar is the border's top."
-->
