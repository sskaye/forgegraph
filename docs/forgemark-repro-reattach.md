# <!-- fmc:4 -->Layer specification<!-- /fmc:4 -->: error_bar (proposed)

This page mirrors review/phase-05/specs/error_bar.yaml, which is the specification. A test fails if they ever differ.

name: error_bar          *# \[text\]; The name of the layer type.*\
version: 0          *# \[int\]; The version number of the specification.*\
description: <!-- fmc:3 -->An error bar on each point or bar<!-- /fmc:3 -->.          *# \[text\]; The description of the layer type.*\
 \
parameters:          *# The layer's parameters, which a GraphSpec's layers entry sets after its type.*\
    axis: y          *# \[x, y\]; Axis the bars extend along.*\
    value:\
        lower: None          *# \[float, column\]; <!-- fmc:1 -->Distance below each value: a number or a column.<!-- /fmc:1 --> A GraphSpec must set it.*\
        upper: None          *# \[float, column\]; <!-- fmc:2 -->Distance above each value: a number or a column.<!-- /fmc:2 --> A GraphSpec must set it.*

<!-- forgemark-comments
- id: 1
  anchor_text: "Distance below each value: a number or a column."
  context_before: "\\[x, y\\]; Axis the bars extend along.*\\ value:\\ lower: None # \\[float, column\\];"
  context_after: "A GraphSpec must set it.*\\ upper: None # \\[float, column\\]; Distance above each"
  author: Claude
  timestamp: 2026-10-22T13:34:27Z
  resolved: false
  body: |
    **Columns of distances,** never computed: one column for symmetric bars, a lower and an upper column for asymmetric ones (matplotlib's and Plotly Express's forms). Vega-Lite's signed second column is easy to get wrong. ggplot2 and Vega-Lite also take the bars' ends (low and high); converting ends to distances is one subtraction while preparing the data, so one form is enough. Vega-Lite's and seaborn's computed extents (SE, CI) are data preparation under the input contract.
    
    Errors: a missing column; a negative or missing distance; a lower end at or below 0 on a log axis; error columns not matching the y columns in number. On bar, each error bar is drawn at its bar's end wherever grouping put it (the graph type reports where it drew each row); on stacked bars it's an error, since a segment's uncertainty isn't the stack's.
  replies:
    - author: Steven
      timestamp: "2026-10-22T14:28:09.030Z"
      body: "See above"
- id: 2
  anchor_text: "Distance above each value: a number or a column."
  context_before: "A GraphSpec must set it.*\\ upper: None # \\[float, column\\];"
  context_after: "A GraphSpec must set it."
  author: Claude
  timestamp: 2026-10-22T13:34:27Z
  resolved: false
  body: |
    **Required:** Cumming, Fidler and Vaux's first rule is that error bars must always be described, and in 2012 5 % of Nature Methods' error bars weren't; Nature's reporting summary requires it. It's recorded in provenance, and the skill has the agent say it in a note or its reply. Drawing it automatically ("Error bars: ± 1 SD") would choose the wording and place for the user.
  replies:
    - author: Steven
      timestamp: "2026-10-22T14:28:14.627Z"
      body: "See above"
- id: 3
  anchor_text: "An error bar on each point or bar"
  context_before: "*\\ version: 0 # \\[int\\]; The version number of the specification.*\\ description:"
  context_after: ". # \\[text\\]; The description of the layer type.*\\ \\ parameters: # The layer's p"
  author: Claude
  timestamp: 2026-10-22T13:34:28Z
  resolved: false
  body: |
    **Error bars on bars** ("dynamite plots") are what Weissgerber et al. (2015), Riedel et al. (2022) and Nature Methods' editors argue against: bars of means hide the data; bars are for counts, totals and proportions. Proposed: allowed, with a lint warning suggesting points with error bars on a categorical xy axis; the skill steers "mean ± SEM per condition" there, and that eval checks for it. If the user explicitly asks for bars, the agent draws bars and lint warns.
  replies:
    - author: Steven
      timestamp: "2026-10-22T14:20:38.797Z"
      body: "No. This is not the purview of the forgemark code. If a user wants it and the org. pack allows it, then the software should draw it."
- id: 4
  anchor_text: "Layer specification"
  context_before: "#"
  context_after: ": error_bar (proposed) This page mirrors review/phase-05/specs/error_bar.yaml, w"
  author: Steven
  timestamp: "2026-10-22T14:21:01.980Z"
  resolved: false
  body: "See general comments on layers from the layer_text spec"
- id: 5
  anchor_text: "Axis the bars extend along."
  context_before: "ers, which a GraphSpec's layers entry sets after its type.*\\ axis: y # \\[x, y\\];"
  context_after: "\\ value:\\ lower: None # \\[float, column\\]; Distance below each value: a number o"
  author: Steven
  timestamp: "2026-10-22T14:27:48.317Z"
  resolved: false
  body: |-
    Cleaner parameters:
    - axis: x | y
    - value.lower: float | column (column can be the same as data.x|y.column)
    - value.upper: float | column (column can be the same as data.x|y.column)
    -  value.aggregation: [float, STDDEV | STDERR | CI] where the value becomes float * AGG(COLUMN) with column grouped according to the various groupby params (color, shape, etc.).
    
    This replaces all of your suggestions, including “represents”.
-->
