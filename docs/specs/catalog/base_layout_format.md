# Catalog specification: base_layout_format

This page mirrors src/forgegraph/packs/forgegraph_base/catalogs/formats/base_layout_format.yaml, which is the specification. A test fails if they ever differ.

name: base_layout_format          *# \[format\]; The format this catalog shows.*\
version: 0          *# \[int ≥ 0\]; The version number of the specification.*\
description: Cards for the base layout format.          *# \[text\]; The description of the catalog.*\
extends: forgegraph_base/base_format          *# \[None, catalog\]; The catalog this one extends. Its baselines come before this file's own, and a header field set to None here is taken from it. If None, this catalog extends no other.*\
baseline: forgegraph_base/graphspec_example          *# \[graphspec\]; The GraphSpec every card changes, drawn with the format this catalog shows.*\
 \
baselines: None          *# Generic scenarios, each the baseline with one or more changes, numbered in the order they're first used. Every parameter gets one card, chosen by a rule: the first candidate value that changes the drawing, on the baseline or on the first of these scenarios where it does. The page shows the cards of the variable parameters. If there are no scenarios, this is None.*
