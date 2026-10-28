# Pack specification: forgegraph_specifications

This page mirrors src/forgegraph/specifications/pack.yaml, which is the specification. A test fails if they ever differ.

name: forgegraph_specifications          *# \[text\]; The pack's name, either a folder where the pack is stored or a pip pack's entry point.*\
version: 0.4.0          *# \[text\]; The pack's release version.*\
description: ForgeGraph's base specs, to define the specifications.          *# \[text\]; One line, describing what the pack is.*\
issues: https://github.com/sskaye/forgegraph/issues          *# \[text\]; Where to file feature requests and bug reports about the pack's specs.*\
requires: <!-- fmc:1 -->">=0.4, <0.5"<!-- /fmc:1 -->          *# \[None, version specifier\]; The ForgeGraph versions the pack works with, as pip writes them, e.g. ">=0.6, <1". If None, it works with any version.*

<!-- forgemark-comments
- id: 1
  anchor_text: "\">=0.4, <0.5\""
  context_before: "ere to file feature requests and bug reports about the pack's specs.*\\ requires:"
  context_after: "# \\[None, version specifier\\]; The ForgeGraph versions the pack works with, as p"
  author: "Steven Kaye"
  timestamp: "2026-10-27T18:50:53.882Z"
  resolved: false
  body: "Seems like this should have a value."
  replies:
    - author: Claude
      timestamp: 2026-10-27T21:14:27Z
      body: |
        It now reads ">=0.4, <0.5", as we agreed.
-->
