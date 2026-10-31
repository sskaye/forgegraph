# Graphs

A graph is drawn from a **GraphSpec**, a YAML file that names the data and sets the graph's parameters. This guide follows one GraphSpec from the file to the saved graph.

## A GraphSpec

These are the polarization curves of three fuel cells, from `cell_polarization.csv` in [examples/sample-data](https://github.com/sskaye/forgegraph/tree/main/examples/sample-data), saved as Parquet:

```yaml
--8<-- "docs/examples/polarization.yaml"
```

![Voltage against current density for cells A, B and C, each named beside its line.](../images/polarization.png){ width="480" }

- **name, version and description** identify the GraphSpec. The saved files are named after the GraphSpec's file: polarization.yaml saves polarization.png.
- **extends** is the GraphSpec this one builds on. With `None`, the file lists every parameter it sets, and `!var` on `parameters` lets a GraphSpec that extends it change any of them (see [Building on a GraphSpec](#building-on-a-graphspec)).
- **specifications** names the graph type, the theme and the format. The theme sets the look and the format sets the size and the file types. Both come from a [pack](themes-formats-packs.md), and are named `pack/name`.
- **data.file** is the Parquet file holding the DataFrame, as a path from the GraphSpec's folder. `data.preprocessing` says where the code that made it is; it's recorded in the saved files and never read.
- **axis.x.data.column** is the column along the x-axis. Each axis can also set its `title`, `scale` (`linear` or `log`), `min` and `max`, its ticks and their label format.
- **series** lists what's drawn against it, each under its name. A series draws the column with its name unless it sets `column`, and `color: cell` gives each cell its own color. The [Series guide](series.md) covers the rest.

Titles are written in label markup: `^2` or `^{...}` makes a superscript and `_{...}` a subscript, so `A/cm^2` draws as A/cm². A column's name is always drawn as it's written.

Every parameter, with its default, the values it allows and its description, is in the [GraphSpec specification](../reference/specifications/graphspec_example.md). `forgegraph schema graphspec --graph-type xy --theme <theme> --format <format>` lists the same for a theme and format, including the theme's and format's parameters a GraphSpec may set.

## Drawing it

```bash
forgegraph render polarization.yaml
```

`render` saves the graph in each file type its format lists, beside the GraphSpec, and reports the lint. `--out` saves it elsewhere, and a suffix there picks one file type: `--out curves.svg`.

The format's file types, size and resolution can be set in the GraphSpec too, where the format allows it. The built-in formats allow all of them:

```yaml
    output:
        file_types: [png, svg, html]
```

From Python, `fg.render` draws a GraphSpec file or document, and takes the DataFrame directly when `data.file` is None:

```python
import forgegraph as fg

g = fg.render("polarization.yaml")
g.save("polarization")  # every file type the format lists
```

`fg.xy(df, x=..., y=..., color=...)` draws a graph straight from a DataFrame, and `g.save` keeps its GraphSpec inside the file, so it can be [recovered](provenance.md) and drawn again.

## Checking it

Every render lints the graph it drew, and lists what it found: text that overlaps or runs off the figure, a key over the data, rows left out, and more. [Troubleshooting](../help/troubleshooting.md) explains each issue and what to change. A GraphSpec that can't be drawn is an error that says what's wrong and what to do; ForgeGraph never draws something else in its place.

```bash
forgegraph explain polarization.yaml
```

`explain` shows every value the graph is drawn with, whether it's fixed, and which file set it: the GraphSpec, the graph type, the theme or the format.

## Fixed and variable parameters

A theme or format marks each of its parameters `!fix` or `!var`. A GraphSpec may set the variable ones and not the fixed ones, so a theme keeps the parts of a house style that shouldn't change between graphs. In the built-in theme, the font and the colors are fixed and the marker size is variable. Setting a fixed one is an error that names the theme:

```text
title.font: fixed by theme 'forgegraph_default/light_theme'
```

`forgegraph explain` and the [catalog](https://github.com/sskaye/forgegraph/blob/main/catalog/forgegraph_default.html) show which parameters are fixed.

## Building on a GraphSpec

A GraphSpec in a pack can be the start of another. `extends: pack/name` inherits every parameter the GraphSpec doesn't list, so it lists only what it changes, and it may change only what the GraphSpec it extends marks `!var`. Packs use this for house versions of a graph, such as the example pack's [polarization curve](https://github.com/sskaye/forgegraph/blob/main/examples/packs/acme/graphspecs/polarization-curve.yaml), which a GraphSpec extends and gives its data.
