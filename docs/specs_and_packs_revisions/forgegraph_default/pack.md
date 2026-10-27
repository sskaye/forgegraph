# Pack specification: forgegraph_default.yaml

This page mirrors src/forgegraph/packs/forgegraph_default/pack.yaml, which is the specification. A test fails if they ever differ.

name: forgegraph_default          *# \[text\]; The pack's name, either a folder where the pack is stored or a pip pack's entry point.*\
version: 0.1.0          *# \[text\]; The pack's release version.*\
description: ForgeGraph's built-in default pack. So it’s always possible to create a graph.         *# \[text\]; One line, describing what the pack is.*\
issues: https://github.com/sskaye/forgegraph/issues          *# \[text\]; Where to file feature requests and bug reports about the pack.*\
requires: <!-- fmc:1 -->None<!-- /fmc:1 -->          *# \[None, version specifier\]; The ForgeGraph version required for the pack. pip format, e.g. ">=0.6, <1". If None, it works with any version.*

<!-- forgemark-comments
- id: 1
  anchor_text: None
  context_before: "xt\\]; Where to file feature requests and bug reports about the pack.*\\ requires:"
  context_after: "# \\[None, version specifier\\]; The ForgeGraph version required for the pack."
  author: "Steven Kaye"
  timestamp: "2026-10-27T19:04:29.273Z"
  resolved: false
  body: "Please add"
-->
