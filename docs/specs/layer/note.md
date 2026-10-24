# Layer specification: note

This page mirrors src/forgegraph/layers/note.yaml, which is the specification. A test fails if they ever differ.

name: note          *# \[text\]; The name of the layer type.*\
version: 0          *# \[int\]; The version number of the specification.*\
description: A block of text by the plot area, such as test conditions.          *# \[text\]; The description of the layer type.*\
 \
parameters:          *# The layer's parameters, which a GraphSpec's layers entry sets after its type.*\
    text: None          *# \[text\]; The note, in label markup; a line break starts a new line. A GraphSpec must set it.*\
    position: auto          *# \[auto, top_left, top_center, top_right, bottom_left, bottom_center, bottom_right\]; auto: the first clear one.*\
    inside: true          *# \[true, false\]; Inside the plot area, or outside it.*
