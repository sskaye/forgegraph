# Catalog: forgegraph_base_2's compact_format

This page mirrors src/forgegraph/packs/forgegraph_base_2/catalogs/formats/compact_format.yaml, which is the specification. A test fails if they ever differ.

name: compact_format          *# \[format\]; The format this catalog shows.*\
version: 0          *# \[int\]; The version number of the specification.*\
description: Cards for the forgegraph_base_2 format, the base format's cards drawn in it.          *# \[text\]; The description of the catalog.*\
extends: forgegraph_base/base_format          *# \[None, catalog\]; Each parameter not listed is taken from this catalog. If None, this file must list every parameter.*\
baseline: forgegraph_base_2/example          *# \[graphspec\]; The GraphSpec every card changes, drawn with the format this catalog shows.*\
 \
baselines: None          *# Numbered baselines: the baseline with one or more changes, named for variations' from; numbered in order of first use. None if none.*\
 \
variations: None          *# Every parameter of the format, by category: its card's value. {value, from, with}: start from a numbered baseline, or change other parameters too. no_card: no card.*
