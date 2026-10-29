# Pack specification: forgegraph_specifications

This page mirrors src/forgegraph/specifications/pack.yaml, which is the specification. A test fails if they ever differ.

name: forgegraph_specifications          *# \[text\]; <!-- fmc:2 -->The pack's name, either a folder where the pack is stored or a pip pack's entry point.<!-- /fmc:2 -->*\
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
    - author: Claude
      timestamp: 2026-10-29T15:02:29Z
      body: |
        Problem: version and requires here still say 0.4 (version: 0.4.0, requires: ">=0.4, <0.5"). forgegraph schema pack prints them as the example values, and a pack that copied them would be refused on 0.5.
        Proposed change: version 0.5.0 and requires ">=0.5, <0.6", as forgegraph_default's pack.yaml has, and add this file to the Releasing steps in CONTRIBUTING.md so it's updated with each minor version.
- id: 2
  anchor_text: "The pack's name, either a folder where the pack is stored or a pip pack's entry point."
  context_before: "A test fails if they ever differ. name: forgegraph_specifications # \\[text\\];"
  context_after: "\\ version: 0.4.0 # \\[text\\]; The pack's release version.*\\ description: ForgeGra"
  author: Claude
  timestamp: 2026-10-29T15:02:29Z
  resolved: false
  body: |
    Problem: a folder pack's name isn't checked against its folder; only built-in and pip packs must match (packs/__init__.py). The proposed text is the wording the example layouts' pack.yaml files already use. The same text is in forgegraph_default's and acme's pack.yaml.
  suggested_edit:
    from: "The pack's name, either a folder where the pack is stored or a pip pack's entry point."
    to: "The pack's name, which its specs' names start with (pack/name); a pip pack's must match its entry point."
-->
