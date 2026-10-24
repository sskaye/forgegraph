# Contributing

Contributions are welcome. For a bug or a feature request, open an [issue](https://github.com/sskaye/forgegraph/issues). For a change, open a pull request with tests, after running the checks below.

## Development setup

```bash
uv sync
uv run pre-commit install
```

The checks a pull request must pass:

```bash
uv run pytest && uv run ruff check . && uv run pyright
```

## After changing a definition or how graphs are drawn

A new or changed parameter needs its card in the matching catalog file under `src/forgegraph/catalogs/`; the build refuses a catalog that misses one.


Rebuild the review catalog (it keeps its review comments; Node 18+ is needed once it has some), and the image baselines if graphs look different on purpose:

```bash
uv run forgegraph catalog build
uv run forgegraph catalog build --pack forgegraph_base_2
uv run python scripts/mirror_specs.py
uv run python scripts/build_recreations.py --baselines
```

`uv run python scripts/visual_changelog.py main` then shows every image that changed.

## Requesting a chart type

Open a GitHub issue describing the graph you need, ideally with an example image or sketch and a little sample data. No code is needed.

