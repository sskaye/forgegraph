"""The specifications: theme, format, graph type, layer type, GraphSpec, layout and schedule.

Each kind is defined by a file in specifications/: graph types and layer types each by their
own (graphtype_xy.yaml), the other kinds by theme.yaml and the rest, and the example
GraphSpec, graphspec_example.yaml. A definition file lists every parameter of its kind with
its value, and the comment on each line gives its range and description: `# [RANGE];
DESCRIPTION`. `parameters` reads those definitions. `registry` knows every spec and reads
files; `resolve` works out a file's values, `layers` and `layout` a GraphSpec's layers and a
layout's tabs, and `explain` every value a graph is drawn with; `loaded` holds a document as
loaded, with where its paths are found from; `access` says which packs a file may use and is
drawn with; and `validate` checks any file of a kind against its definitions.
"""
