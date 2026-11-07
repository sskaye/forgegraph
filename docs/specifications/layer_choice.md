# Layer specification: choice

This page mirrors src/forgegraph/specifications/layer_choice.yaml, which is the specification. A test fails if they ever differ.

name: choice          *# \[text\]; The name of the layer type.*\
version: 0          *# \[int ≥ 0\]; The version number of the specification.*\
description: A control on an HTML page that switches between views, each drawn ahead of time.          *# \[text\]; The description of the layer type.*\
 \
<!-- fmc:2 -->parameters:<!-- /fmc:2 -->\
    label: None          *# \[None, text\]; The text before the control, e.g. Metric. If None, there is none.*\
    <!-- fmc:1 -->control: dropdown          *# \[dropdown, radio\]; How the page shows the views' names: as a dropdown, or as a row of radio buttons.*<!-- /fmc:1 -->\
    views:          *# The views, each under the name the control shows. A GraphSpec lists two or more, and the page opens on the first.*\
        VIEW_1: {}          *# \[parameters and their values\]; What the view changes, e.g. a series' column and the y-axis title. {} changes nothing.*

<!-- forgemark-comments
- id: 1
  anchor_text: "control: dropdown # [dropdown, radio]; How the page shows the views' names: as a dropdown, or as a row of radio buttons."
  context_before: "Metric. If None, there is none."
  context_after: "views: # The views, each under the name the control shows."
  author: Claude
  timestamp: 2026-11-07T20:57:53Z
  resolved: false
  body: |
    Problem: the control's place on the page is fixed, above the figure.
    
    Proposed change: add after control:
    
        position: right          # [top, bottom, right]; Where the control is on the HTML page: above the figure, below it, or to its right, with the label above it.
    
    1. With top or bottom, the label is to the left of the control, as now. With right, the label is above the control, and the controls on the right stand one under another, in the order the GraphSpec lists the layers.
    2. On a narrow window, such as a phone's, the right column moves below the figure, so the figure keeps the width.
    3. In a layout, the controls go beside or around the whole grid. Choice layers of the same name in several tiles share one control, so they must have the same position, or it's an error, as their views already must match.
- id: 2
  anchor_text: "parameters:"
  context_before: "# [text]; The description of the layer type."
  context_after: "label: None # [None, text]; The text before the control, e.g."
  author: Claude
  timestamp: 2026-11-07T20:57:53Z
  resolved: false
  body: |
    Problem: there's no way to set the control's text. On a graph's page it takes the theme's general text, and on a layout's page the tab bar's look.
    
    Proposed change: give the choice layer a text style from the theme, as the note layer has:
    
        parameters:          # [text style, look from layer.choice]; The control.
    
    and add the theme category in theme.yaml (see the comment there). A GraphSpec's choice layer may then set the parts its theme leaves variable, such as size: 1.1, and in a layout the shared control takes its first tile's look.
-->
