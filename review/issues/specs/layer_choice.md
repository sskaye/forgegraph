# Proposed layer specification: choice

This page mirrors review/issues/specs/layer_choice.yaml, the proposed specification.

name: choice          *# \[text\]; The name of the layer type.*\
version: 0          *# \[int ≥ 0\]; The version number of the specification.*\
description: A control on an HTML page that switches between views, each drawn ahead of time.          *# \[text\]; The description of the layer type.*\
 \
parameters:\
    label: None          *# \[None, text\]; The text before the control, e.g. Metric. If None, there is none.*\
    control: dropdown          *# <!-- fmc:2 -->\[dropdown, radio\]<!-- /fmc:2 -->; How the page shows the views' names: as a dropdown, or as a row of radio buttons.*\
    <!-- fmc:1 -->views:<!-- /fmc:1 -->          *# The views, each under the name the control shows. A GraphSpec lists two or more, and the page opens on the first.*\
        VIEW_1: {}          *# \[parameters and their values\]; What the view changes, e.g. a series' column and the y-axis title. {} changes nothing.*

<!-- forgemark-comments
- id: 1
  anchor_text: "views:"
  context_before: "the page shows the views' names: as a dropdown, or as a row of radio buttons."
  context_after: "# The views, each under the name the control shows."
  author: Claude
  timestamp: 2026-11-07T14:35:07Z
  resolved: false
  body: |
    How views are drawn and what they can change.
    
    1. ForgeGraph draws every view and puts each one's image on the page, as it does for tabs. The control switches between images in the same way, so the page works without its scripts. With two choice layers, such as one for x and one for y, every combination is drawn: 4 × 4 views is 16 images. The page's size and the time to draw it grow with the number of images.
    2. A view sets GraphSpec parameters, as a catalog's baselines do. It can't set specifications, data, output or provenance, or another choice or toggle layer, and doing so is an error. A view can still use a parameter the GraphSpec's theme has fixed only where a GraphSpec could.
    3. Each view has its own readouts, and the page's provenance records every view.
    4. "parameters and their values" would be a new range word for this, the form the catalog files' baselines already use.
- id: 2
  anchor_text: "[dropdown, radio]"
  context_before: "Metric. If None, there is none. control: dropdown #"
  context_after: "; How the page shows the views' names: as a dropdown, or as a row of radio"
  author: Steven
  timestamp: "2026-11-07T15:11:44.118Z"
  resolved: false
  body: "Is the standard term buttons or radio dial?"
  replies:
    - author: Claude
      timestamp: 2026-11-07T15:13:44Z
      body: |
        Radio buttons is the standard term: a set of options where choosing one clears the others. HTML's control is input type="radio", Vega-Lite binds a value to "radio" or "select", and Tableau's single-value list shows them. Radio dial isn't used for this, and the name comes from car radios, whose station buttons pop out when another is pressed.
        
        The same behavior has two common looks:
        1. Radio buttons: a small circle beside each option's name.
        2. A segmented control (Apple's term), or button group: a row of joined buttons with the chosen one pressed, much like our tab bar. Plotly's "buttons" and Bokeh's RadioButtonGroup look like this.
        
        I'd rename the value radio, so the range is [dropdown, radio]. It's the term people know, and it doesn't clash with the toggle layer's buttons, which turn things on and off independently. On the page I'd draw it as the row of joined buttons, in the tab bar's style, since that suits a few views and matches the page. The proposed line:
        
        control: dropdown          # [dropdown, radio]; How the page shows the views' names: as a dropdown, or as a row of radio buttons.
    - author: Steven
      timestamp: "2026-11-07T15:14:37.296Z"
      body: "agreed, name it radio"
    - author: Claude
      timestamp: 2026-11-07T15:14:59Z
      body: |
        Done: the value is radio, and the range is [dropdown, radio] in layer_choice.yaml and its page. The issues page records both specifications as agreed.
-->
