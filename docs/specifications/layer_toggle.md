# Layer specification: toggle

This page mirrors src/forgegraph/specifications/layer_toggle.yaml, which is the specification. A test fails if they ever differ.

name: toggle          *# \[text\]; The name of the layer type.*\
version: 0          *# \[int ≥ 0\]; The version number of the specification.*\
description: Buttons on an HTML page that show or hide series and layers, each drawn ahead of time.          *# \[text\]; The description of the layer type.*\
 \
parameters:\
    items: \[series\]          *# \[series, layers, text\]; What can be hidden: series for all series, layers for all layers, or those named.*\
    hidden: None          *# \[None, texts\]; The series and layers hidden when the page opens. If None, everything is shown.*
