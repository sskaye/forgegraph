# Catalog: forgegraph_base_2's compact_format

This page mirrors src/forgegraph/packs/forgegraph_base_2/catalogs/formats/compact_format.yaml, which is the specification. A test fails if they ever differ.

name: compact_format          *# \[format\]; The format this catalog shows.*\
version: 0          *# \[int\]; The version number of the specification.*\
description: Cards for the forgegraph_base_2 format, on the base format's baselines.          *# \[text\]; The description of the catalog.*\
extends: forgegraph_base/base_format          *# \[None, catalog\]; The catalog this one extends: its baselines come before this file's own, and a header field set to None here is taken from it. None: it extends none.*\
baseline: forgegraph_base_2/example          *# \[graphspec\]; The GraphSpec every card changes, drawn with the format this catalog shows.*\
 \
baselines: None          *# Numbered baselines: generic scenarios, each the baseline with one or more changes, numbered in order of first use. Every variable parameter gets one card, by rule: its first candidate value that changes the drawing, on the baseline or on the first of these where it does. None if none.*
