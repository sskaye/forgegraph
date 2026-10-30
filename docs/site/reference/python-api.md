# Python API

```python
import forgegraph as fg
```

- `fg.xy(df, x, y, ...)`: draw y against x from a DataFrame.
- `fg.render(spec, data=None)`: draw a GraphSpec, given as a file or a document.
- `fg.graphspec(name, graph_type, ...)`: write a GraphSpec document.
- `fg.layout(spec, data=None)`: draw a layout.
- `fg.load(path)`: a saved graph's record; its GraphSpec is under `"graphspec"`.
- `fg.blank(theme, format)`: a themed canvas for drawing with matplotlib what no graph type can; what's drawn on it is watermarked.
- A `Graph` has `.save(path)`, `.figure` and `.axes` (matplotlib's), `.issues` (the lint) and `.check()`.

A spec that can't be drawn raises `fg.SpecError`, whose `problems` lists each problem.

## Drawing

::: forgegraph.graph.xy
    options:
      heading: fg.xy
      toc_label: fg.xy

::: forgegraph.graph.render
    options:
      heading: fg.render
      toc_label: fg.render

::: forgegraph.layouts.render_layout
    options:
      heading: fg.layout
      toc_label: fg.layout

::: forgegraph.canvas.blank
    options:
      heading: fg.blank
      toc_label: fg.blank

## GraphSpecs and records

::: forgegraph.graph.graphspec
    options:
      heading: fg.graphspec
      toc_label: fg.graphspec

::: forgegraph.graph.load
    options:
      heading: fg.load
      toc_label: fg.load

## What they return

::: forgegraph.graph.Graph
    options:
      heading: fg.Graph
      toc_label: fg.Graph
      inherited_members: true
      members: [save, check, figure, axes, issues]

::: forgegraph.layouts.Layout
    options:
      heading: fg.Layout
      toc_label: fg.Layout
      inherited_members: true
      members: [save, tabs, issues]

::: forgegraph.canvas.Blank
    options:
      heading: fg.Blank
      toc_label: fg.Blank
      inherited_members: true
      members: [save, figure, axes]

::: forgegraph.drawn.SpecError
    options:
      heading: fg.SpecError
      toc_label: fg.SpecError
