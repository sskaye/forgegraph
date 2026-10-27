# GraphSpec: forgegraph_default/graphspec_example

This page mirrors src/forgegraph/packs/forgegraph_base_2/graphspecs/graphspec_example.yaml, which is the specification. A test fails if they ever differ.

name: graphspec_example          *# \[text\]; The name of the GraphSpec.*\
version: 0          *# \[int ≥ 0\]; The version number of the specification.*\
description: The default pack's example GraphSpec for its catalog.          *# \[text\]; The description of the GraphSpec.*\
extends: forgegraph_base/graphspec_example          *# \[None, graphspec\]; Each parameter not listed is inherited from this GraphSpec. If None, this file must list every parameter.*\
 \
parameters:          *# !var/!fix sets whether a GraphSpec may change a property. Subcategories/parameters inherit the setting of the one above them unless explicitly overridden.*\
    specifications:\
        theme: forgegraph_default/base_theme          *# \[theme\];*\
        format: forgegraph_default/compact_format          *# \[format\];*\
    data:\
        file: polarization.parquet          *# \[None, text\]; The Parquet file holding the DataFrame to draw: an absolute path, a path starting with \~, or a path relative to the folder of the file that sets it. If None, the DataFrame is passed through the Python API.*
