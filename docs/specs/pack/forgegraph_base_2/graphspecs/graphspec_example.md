# GraphSpec: forgegraph_base_2/graphspec_example

This page mirrors src/forgegraph/packs/forgegraph_base_2/graphspecs/graphspec_example.yaml, which is the specification. A test fails if they ever differ.

name: graphspec_example          *# \[text\]; The name of the GraphSpec.*\
version: 0          *# \[int ≥ 0\]; The version number of the specification.*\
description: The base pack's example GraphSpec in this pack's theme and format, for its catalog.          *# \[text\]; The description of the GraphSpec.*\
extends: forgegraph_base/graphspec_example          *# \[None, graphspec\]; Each parameter not listed is inherited from this GraphSpec. If None, this file must list every parameter.*\
 \
parameters:          *# !var/!fix sets whether a GraphSpec may change a property. Subcategories/parameters inherit the setting of the one above them unless explicitly overridden.*\
    specifications:\
        theme: forgegraph_base_2/base_theme          *# \[theme\];*\
        format: forgegraph_base_2/compact_format          *# \[format\];*\
    data:\
        file: polarization.parquet          *# \[None, text\]; Parquet file holding the DataFrame to draw: an absolute path, one starting with ~, or one relative to the folder of the file that sets it. None: passed through the Python API.*
