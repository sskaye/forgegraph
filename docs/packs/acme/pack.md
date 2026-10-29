# Pack example: acme's pack.yaml

This page mirrors examples/packs/acme/pack.yaml, which is the specification. A test fails if they ever differ.

name: acme          *# \[text\]; The pack's name, which its specs' names start with (pack/name); a pip pack's must match its entry point.*\
version: 1.2.0          *# \[text\]; The pack's release version.*\
description: Example pack with a deliberately different house style.          *# \[text\]; One line, describing what the pack is.*\
issues: https://github.com/acme/forgegraph-pack/issues          *# \[text\]; Where to file feature requests and bug reports about the pack's specs.*\
requires: ">=0.0.1, <1"          *# \[None, version specifier\]; The ForgeGraph versions the pack works with, as pip writes them, e.g. ">=0.6, <1". If None, it works with any version.*
