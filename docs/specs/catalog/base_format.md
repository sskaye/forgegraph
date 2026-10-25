# Catalog specification: base_format

This page mirrors src/forgegraph/packs/forgegraph_base/catalogs/formats/base_format.yaml, which is the specification. A test fails if they ever differ.

name: base_format          *# \[format\]; The format this catalog shows.*\
version: 0          *# \[int\]; The version number of the specification.*\
description: Cards for the base format.          *# \[text\]; The description of the catalog.*\
extends: None          *# \[None, catalog\]; The catalog this one extends: its baselines come before this file's own, and a header field set to None here is taken from it. None: it extends none.*\
baseline: forgegraph_base/polarization          *# \[graphspec\]; The GraphSpec every card changes, drawn with the format this catalog shows.*\
 \
baselines: None          *# Numbered baselines: generic scenarios, each the baseline with one or more changes, numbered in order of first use. Every parameter gets one card, by rule (the page shows the variable ones): its first candidate value that changes the drawing, on the baseline or on the first of these where it does. None if none.*
