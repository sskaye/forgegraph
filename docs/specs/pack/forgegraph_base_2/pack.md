# Pack specification: forgegraph_base_2's pack.yaml

This page mirrors src/forgegraph/packs/forgegraph_base_2/pack.yaml, which is the specification. A test fails if they ever differ.

name: forgegraph_base_2          *# \[text\]; The pack's name, either a folder where the pack is stored or a pip pack's entry point.*\
version: 0.3.0          *# \[text\]; The pack's release version.*\
description: Compact report graphs in Source Sans 3, a ten-color palette and a full box with short ticks.          *# \[text\]; One line, describing what the pack is.*\
issues: https://github.com/sskaye/forgegraph/issues          *# \[text\]; Where to file feature requests and bug reports about the pack's specs.*\
requires: ">=0.1.0, <1"          *# \[None, version specifier\]; The ForgeGraph versions the pack works with, as pip writes them, e.g. ">=0.6, <1". If None, it works with any version.*
