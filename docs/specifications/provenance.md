# Provenance specification: the record in every saved file

This page mirrors src/forgegraph/specifications/provenance.yaml, which is the specification. A test fails if they ever differ.

name: provenance          *# \[text\]; The name of the record.*\
version: 0          *# \[int ≥ 0\]; The version number of the specification.*\
description: The record ForgeGraph writes into every saved file, at the format's provenance.level.          *# \[text\]; The description of the record.*\
 \
off:          *# Written at off: there is no metadata.*\
 \
minimal:          *# Written at minimal and full.*\
    provenance_level: minimal          *# \[full, minimal\]; The provenance level at which the record was written.*\
    forgegraph_version: X.Y.Z          *# \[text\]; The ForgeGraph version that drew the file.*\
    created: "2026-10-24T09:00:00Z"          *# \[text\]; When the file was drawn, in ISO 8601 and UTC. If SOURCE_DATE_EPOCH is set, it's taken from that.*\
    graphspec: {}          *# \[mapping\]; <!-- fmc:1 -->The GraphSpec as written, without data.file and data.preprocessing.<!-- /fmc:1 --> There is none for a blank canvas.*\
    specs: {}          *# \[mapping\]; Each spec used, by kind: its name and version, and its pack's version if it's in a pack.*\
    nonstandard: false          *# \[true, false\]; Whether something was drawn outside the specs the config permits, so the graph is watermarked.*\
    nonstandard_packs: \[\]          *# \[texts\]; The packs used that the main config doesn't list, which make the graph non-standard. It's left out if there are none.*\
 \
full:          *# Written at full only, as well as everything in minimal.*\
    resolved: {}          *# \[mapping\]; Every value the graph was drawn with, by kind: GraphSpec, graph type, theme, format and layers.*\
    data: polarization.parquet          *# \[None, text\]; The data file as listed in the GraphSpec. It's left out for a DataFrame passed in directly.*\
    preprocessing: None          *# \[None, text\]; data.preprocessing as listed in the GraphSpec: where the code that made the data is.*\
 \
layout:          *# Written for a layout, at the layout's level, in place of graphspec, resolved, data and preprocessing.*\
    layout: {}          *# \[mapping\]; The layout file as written.*\
    tabs: {}          *# \[mapping\]; <!-- fmc:2 -->For each tab the file shows, each tile's GraphSpec file<!-- /fmc:2 --> and the entries above for it, at the layout's level.*

<!-- forgemark-comments
- id: 1
  anchor_text: "The GraphSpec as written, without data.file and data.preprocessing."
  context_before: "f SOURCE_DATE_EPOCH is set, it's taken from that.*\\ graphspec: {} # \\[mapping\\];"
  context_after: "There is none for a blank canvas.*\\ specs: {} # \\[mapping\\]; Each spec used, by"
  author: Claude
  timestamp: 2026-10-29T15:02:28Z
  resolved: false
  body: |
    Problem: at full, data.file and data.preprocessing are kept (spec/provenance.py, recorded).
  suggested_edit:
    from: "The GraphSpec as written, without data.file and data.preprocessing."
    to: "The GraphSpec as written; at minimal, without data.file and data.preprocessing."
- id: 2
  anchor_text: "For each tab the file shows, each tile's GraphSpec file"
  context_before: "layout: {} # \\[mapping\\]; The layout file as written.*\\ tabs: {} # \\[mapping\\];"
  context_after: "and the entries above for it, at the layout's level."
  author: Claude
  timestamp: 2026-10-29T15:02:29Z
  resolved: false
  body: |
    Problem: with nested tabs, only tabs with a grid are recorded, keyed by their path (layouts/__init__.py).
  suggested_edit:
    from: "For each tab the file shows, each tile's GraphSpec file"
    to: "For each tab with a grid that the file shows, under its path (e.g. Platinum / Voltage), each tile's GraphSpec file"
-->
