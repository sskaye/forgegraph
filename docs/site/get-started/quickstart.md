# Quickstart

## In Python

```python
import pandas as pd
import forgegraph as fg

runs = pd.DataFrame({
    "hours": [0, 1, 2, 3, 0, 1, 2, 3],
    "voltage": [0.72, 0.71, 0.70, 0.69, 0.73, 0.73, 0.72, 0.72],
    "cell": ["A", "A", "A", "A", "B", "B", "B", "B"],
})
g = fg.xy(runs, x="hours", y="voltage", color="cell", title="Cell voltage")
g.save("voltage")  # voltage.png, with its GraphSpec inside
```

![Cell voltage against hours, one line for each of cells A and B, in the built-in theme.](voltage.png){ width="480" }

`g.issues` lists what the lint found, and `fg.load("voltage.png")` reads back the record saved inside the file, with its GraphSpec under `"graphspec"`. The [Python API](../reference/python-api.md) covers every function.

## From the command line

With the DataFrame saved as runs.parquet and a GraphSpec, voltage.yaml:

```yaml
name: voltage
version: 0
description: Cell voltage over a test, one line per cell.
extends: None
parameters: !var
    specifications:
        graph_type: xy
        theme: forgegraph_default/light_theme
        format: forgegraph_default/compact_format
    text:
        title: Cell voltage
    data:
        file: runs.parquet
        preprocessing: None
    axis:
        x:
            data:
                column: hours
    series:
        voltage:
            color: cell
```

```bash
forgegraph render voltage.yaml
```

`render` saves the graph in each file type its format lists, beside the GraphSpec, and reports the lint. `forgegraph explain voltage.yaml` shows every value the graph is drawn with, and which file set it. `forgegraph schema graphspec --graph-type xy --theme forgegraph_default/light_theme --format forgegraph_default/compact_format` lists every parameter a GraphSpec can set; the [specifications](../reference/specifications/index.md) show them too.
