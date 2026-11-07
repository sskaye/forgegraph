# Layer specification: toggle

This page mirrors src/forgegraph/specifications/layer_toggle.yaml, which is the specification. A test fails if they ever differ.

name: toggle          *# \[text\]; The name of the layer type.*\
version: 0          *# \[int ≥ 0\]; The version number of the specification.*\
description: Checkboxes on an HTML page that show or hide series and layers, each drawn ahead of time.          *# \[text\]; The description of the layer type.*\
 \
<!-- fmc:1 -->parameters:<!-- /fmc:1 -->\
    <!-- fmc:2 -->items: \[series\]<!-- /fmc:2 -->          *# \[series, layers, text\]; What can be hidden: series for all series, layers for all layers, or those named.*\
    <!-- fmc:3 -->hidden: None<!-- /fmc:3 -->          *# \[None, texts\]; The series and layers hidden when the page opens. If None, everything is shown.*

<!-- forgemark-comments
- id: 1
  anchor_text: "parameters:"
  context_before: "# [text]; The description of the layer type."
  context_after: "items: [series] # [series, layers, text]; What can be hidden: series for all"
  author: Claude
  timestamp: 2026-11-07T20:57:53Z
  resolved: false
  body: |
    Problem: there's no way to set the checkboxes' text, as for the choice layer.
    
    Proposed change, as for the choice layer:
    
        parameters:          # [text style, look from layer.toggle]; The checkboxes.
    
    with layer.toggle in the theme (see the comment on theme.yaml).
- id: 2
  anchor_text: "items: [series]"
  context_before: "# [text]; The description of the layer type. parameters:"
  context_after: "# [series, layers, text]; What can be hidden: series for all series, layers for"
  author: Claude
  timestamp: 2026-11-07T20:57:53Z
  resolved: false
  body: |
    Problem: the checkboxes need a place on the page, and with position right, the text above them that you described. The toggle layer has no label.
    
    Proposed change: add before items:
    
        label: None          # [None, text]; The text before the checkboxes, e.g. Show. If None, there is none.
        position: right          # [top, bottom, right]; Where the checkboxes are on the HTML page: above the figure, below it, or to its right, under the label.
    
    With top or bottom, the checkboxes are in a row after the label. With right, they stand one under another, under the label. The rest is as for the choice layer's position: a narrow window moves the column below the figure, and in a layout, toggle layers sharing checkboxes must have the same position.
- id: 3
  anchor_text: "hidden: None"
  context_before: "can be hidden: series for all series, layers for all layers, or those named."
  context_after: "# [None, texts]; The series and layers hidden when the page opens."
  author: Claude
  timestamp: 2026-11-07T20:57:53Z
  resolved: false
  body: |
    Question: a checkbox next to each key entry, so the key does both jobs. The key is part of the figure's image, so the page can only lay a checkbox over it, and the key needs room for it. One of:
    
    1. The key leaves a checkbox's width before the sample of each toggled entry, in every file. The page puts a checkbox in that space. A png, pdf or svg file then shows a blank gap in its key.
    2. The key draws a small box before each toggled entry, ticked or empty, in every file. On the page, clicking the entry ticks or empties it. Files then show the boxes too, which looks like a form on paper.
    3. Only the page's figure gives the key room for the checkboxes: it's drawn a second time for the page, with the key widened. Files are unchanged; the page's figure differs from them only by the key's width, and saving the page takes about twice as long.
    
    Recommendation: 3. Files stay clean for papers, and the page gets real checkboxes in the key.
    
    Either way, series named in the key get their checkboxes there, and the rest (layers, and series with direct labels) stay in the list at position. If nothing is left, there's no list.
-->
