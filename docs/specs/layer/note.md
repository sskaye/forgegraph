# Layer specification: note

This page mirrors src/forgegraph/layers/note.yaml, which is the specification. A test fails if they ever differ.

name: note          *# \[text\]; The name of the layer type.*\
version: 0          *# \[int ≥ 0\]; The version number of the specification.*\
description: A block of text by the plot area, such as test conditions.          *# \[text\]; The description of the layer type.*\
 \
parameters:          *# \[text style, look from layer.note\]; The note.*\
    text: None          *# \[text\]; The note's text, in label markup. A line break starts a new line. A GraphSpec must set it.*\
    position: auto          *# \[auto, top_left, top_center, top_right, bottom_left, bottom_center, bottom_right\]; auto selects the first clear location inside the plot area and is invalid if inside is false.*\
    inside: true          *# \[true, false\]; Whether the note is inside the plot area or outside it.*
