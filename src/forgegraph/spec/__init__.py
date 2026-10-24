"""The specifications: theme, format, graph type, layer type, GraphSpec, layout and schedule.

Graph types and layer types are each defined by their own file (graph_types/xy.yaml); the
other kinds by the base pack's complete specs (packs/forgegraph_base/themes/base_theme.yaml
and the rest) and its example GraphSpec (graphspecs/polarization.yaml). A
definition file lists every parameter of its kind with its value, and the comment on each
line gives its range and description: `# [RANGE]; DESCRIPTION`. `parameters` reads those
definitions; `documents` checks and resolves any file of a kind against them.
"""
