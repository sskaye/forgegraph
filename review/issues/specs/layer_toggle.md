# Proposed layer specification: toggle

This page mirrors review/issues/specs/layer_toggle.yaml, the proposed specification.

name: toggle          *# \[text\]; The name of the layer type.*\
version: 0          *# \[int ≥ 0\]; The version number of the specification.*\
description: <!-- fmc:3 -->Buttons on an HTML page that show or hide series and layers, each drawn ahead of time.<!-- /fmc:3 -->          *# \[text\]; The description of the layer type.*\
 \
parameters:\
    <!-- fmc:1 -->items:<!-- /fmc:1 --> \[series\]          *# \[series, layers, texts\]; What can be hidden: series for all series, layers for all layers, or those named.*\
    <!-- fmc:2 -->hidden: None<!-- /fmc:2 -->          *# \[None, texts\]; The series and layers hidden when the page opens. If None, everything is shown.*

<!-- forgemark-comments
- id: 1
  anchor_text: "items:"
  context_before: "# [text]; The description of the layer type. parameters:"
  context_after: "[series] # [series, layers, texts]; What can be hidden: series for all series,"
  author: Claude
  timestamp: 2026-11-07T14:35:07Z
  resolved: false
  body: |
    How hiding works, and what it costs.
    
    1. The figure is drawn once, with everything shown, so the axes, keys and labels are placed as usual. The base image then leaves out every listed item, and each item is saved on its own as a transparent image the same size, laid exactly over the base. The page shows or hides those images.
    2. A hidden series loses its marks, error bars, value labels and direct label. Its key entry stays, because the key is part of the base image. A hidden layer loses its lines, fill and label. The axes don't rescale.
    3. It costs one image for each item, not one for each combination. With a choice layer as well, every view gets its own set.
    4. This needs a trial before it's built: checking that the separate images line up to the pixel at every size, as the page scales them.
    5. The buttons are named as the GraphSpec names the series and layers, and they sit above the figure in the theme's text style, as the choice control does.
- id: 2
  anchor_text: "hidden: None"
  context_before: "can be hidden: series for all series, layers for all layers, or those named."
  context_after: "# [None, texts]; The series and layers hidden when the page opens."
  author: Claude
  timestamp: 2026-11-07T14:35:08Z
  resolved: false
  body: |
    What files show.
    
    A png, pdf or svg file shows the page's opening state, so an item listed here is hidden there too. That gives a way to save a graph without, say, a control band, without editing the GraphSpec's layers.
- id: 3
  anchor_text: "Buttons on an HTML page that show or hide series and layers, each drawn ahead of time."
  context_before: "description:"
  context_after: "# [text]; The description of the layer type."
  author: Claude
  timestamp: 2026-11-07T14:35:08Z
  resolved: false
  body: |
    Layouts, and what's left for later.
    
    1. In a layout, toggle layers of the same name in several tiles share one row of buttons, shown once above the grid. A button hides the item of that name in every tile that has it.
    2. Left out for now: clicking a key's entry to hide its series, as Plotly does. The page would need to know where each entry is drawn, which it could, but buttons are simpler to start with.
-->
