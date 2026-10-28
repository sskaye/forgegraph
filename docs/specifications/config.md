# Config specification: config.toml and forgegraph.toml

This page mirrors src/forgegraph/specifications/config.toml, which is the specification. A test fails if they ever differ.

packs = \[<!-- fmc:1 -->"forgegraph_specifications"<!-- /fmc:1 -->\]          *# \[texts\]; The packs whose specs may be used: built-in and pip packs by name, and folder packs by their path from this file.*

<!-- forgemark-comments
- id: 1
  anchor_text: "\"forgegraph_specifications\""
  context_before: "A test fails if they ever differ. packs = \\["
  context_after: "\\] # \\[texts\\]; The packs whose specs may be used: built-in and pip packs by nam"
  author: "Steven Kaye"
  timestamp: "2026-10-27T18:40:17.644Z"
  resolved: false
  body: |-
    this file is the specification, so I’m leaving a placeholder pack. This should not be installed anywhere.
    
    Pick a location where the default config is stored (the one that is installed on first use). That should have all the forgegraph built-in packs listed except for the specifications pack.
  replies:
    - author: Claude
      timestamp: 2026-10-27T21:14:27Z
      body: |
        Done. This file is now src/forgegraph/specifications/config.toml: the config's specification, listing your placeholder pack, and nothing installs it. ForgeGraph writes the default config, ~/.config/forgegraph/config.toml, on first use from its list of built-in packs in src/forgegraph/packs/__init__.py, which is now forgegraph_default alone.
-->
