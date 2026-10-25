# Catalog specification: note layer

This page mirrors src/forgegraph/catalogs/layers/note.yaml, which is the specification. A test fails if they ever differ.

name: note          *# \[layer type\]; The layer type this catalog shows.*\
version: 0          *# \[int\]; The version number of the specification.*\
description: Cards for the note layer.          *# \[text\]; The description of the catalog.*\
extends: None          *# \[None, catalog\]; The catalog this one extends: its baselines come before this file's own, and a header field set to None here is taken from it. None: it extends none.*\
baseline: forgegraph_base/polarization          *# \[graphspec\]; The GraphSpec every card changes, without its own layers.*\
settings: None          *# GraphSpec parameters every card sets so the layer can be drawn. None if none.*\
layer:          *# The layer every card draws, named after its type: its parameters.*\
    text: "60 °C, 1 atm, H\_{2}/air"          *# \[text\]; The note, in label markup; a line break starts a new line.*\
    position: bottom_left          *# \[auto, top_left, top_center, top_right, bottom_left, bottom_center, bottom_right\]; auto: the first clear place inside the plot area; set a position when inside is false.*\
 \
baselines: None          *# Numbered baselines: generic scenarios, each the baseline with one or more changes, numbered in order of first use. Every parameter gets one card, by rule (the page shows the variable ones): its first candidate value that changes the drawing, on the baseline or on the first of these where it does. None if none.*
