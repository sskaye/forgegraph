# Pack specification: forgegraph_base's pack.yaml

This page mirrors src/forgegraph/packs/forgegraph_base/pack.yaml, which is the specification. A test fails if they ever differ.

name: forgegraph_base          *# \[text\]; The pack's name, which its specs' names start with (pack/name); a pip pack's must match its entry point.*\
version: 0.3.0          *# \[text\]; The pack's release version.*\
description: ForgeGraph's base specs, complete, for other specs to extend or to use as they are.          *# \[text\]; One line, describing what the pack is.*\
issues: https://github.com/sskaye/forgegraph/issues          *# \[text\]; Where to file feature requests and bug reports about the pack's specs.*\
requires: None          *# \[None, version specifier\]; The ForgeGraph versions the pack works with, as a pip version specifier. None: any.*
