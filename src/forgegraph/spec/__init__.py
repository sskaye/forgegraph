"""The specifications: theme, format, graph type, layer type, GraphSpec, layout and schedule.

Graph types and layer types are each defined by their own file (graph_types/xy.yaml); the
other kinds by the base pack's complete specs (packs/forgegraph_base/themes/base_theme.yaml
and the rest) and its example GraphSpec (graphspecs/graphspec_example.yaml). A
definition file lists every parameter of its kind with its value, and the comment on each
line gives its range and description: `# [RANGE]; DESCRIPTION`. `parameters` reads those
definitions. `registry` knows every spec and reads files; `resolve` works out a file's
values, `layers` and `layout` a GraphSpec's layers and a layout's tabs, and `explain` every
value a graph is drawn with; `loaded` holds a document as loaded, with where its paths are
found from; `access` says which packs a file may use and is drawn with; and `validate`
checks any file of a kind against its definitions.
"""
