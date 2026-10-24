# Contributing

ForgeGraph is in early development and isn't accepting outside contributions yet. This page will grow before the first public release.

## Development setup

```bash
uv sync
uv run pre-commit install
uv run pytest
```

## After changing a definition or how graphs are drawn

A new or changed parameter needs its card in the matching catalog file under `src/forgegraph/catalogs/`; the build refuses a catalog that misses one.


Rebuild the review catalog (it keeps its review comments; Node 18+ is needed once it has some), and the image baselines if graphs look different on purpose:

```bash
uv run forgegraph catalog build
uv run python scripts/build_recreations.py --baselines
```

`uv run python scripts/visual_changelog.py main` then shows every image that changed.

## Requesting a chart type

Open a GitHub issue describing the graph you need, ideally with an example image or sketch and a little sample data. No code is needed.
