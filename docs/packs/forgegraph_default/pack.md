# Built-in pack: forgegraph_default's pack.yaml

This page mirrors src/forgegraph/packs/forgegraph_default/pack.yaml, which is the specification. A test fails if they ever differ.

name: forgegraph_default          *# \[text\]; The pack's name, which its specs' names start with (pack/name); a pip pack's must match its entry point.*\
version: 0.6.1          *# \[text\]; The pack's release version.*\
description: ForgeGraph's built-in default pack. So it’s always possible to create a graph.          *# \[text\]; One line, describing what the pack is.*\
issues: https://github.com/sskaye/forgegraph/issues          *# \[text\]; Where to file feature requests and bug reports about the pack.*\
requires: ">=0.6, <0.7"          *# \[None, version specifier\]; The ForgeGraph version required for the pack. pip format, e.g. ">=0.6, <1". If None, it works with any version.*
