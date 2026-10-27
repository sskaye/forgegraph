# Config specification: config.toml and forgegraph.toml

This page mirrors src/forgegraph/packs/config.toml, which is the specification. A test fails if they ever differ.

packs = \["forgegraph_base", "forgegraph_base_2"\]          *# \[texts\]; The packs whose specs may be used: built-in and pip packs by name, and folder packs by their path from this file.*
