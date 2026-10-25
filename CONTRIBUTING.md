# Contributing

Contributions are welcome. For a bug or a feature request, open an [issue](https://github.com/sskaye/forgegraph/issues). For a change, open a pull request with tests, after running the checks below.

## Development setup

```bash
uv sync
uv run pre-commit install
```

While you work, `uv run pytest` runs the development suite: every test not marked slow, in parallel. The full suite adds the slow ones (every catalog card drawn, the image baselines, the catalog pages, and any test over a second). CI runs it on every pull request, and it's the one to run before a release:

```bash
uv run pytest --full && uv run ruff check . && uv run ruff format --check && uv run pyright
```

Mark a new test `@pytest.mark.slow` if it takes over a second (`uv run pytest --durations=20` lists the slowest).

## After changing a definition or how graphs are drawn

A new or changed parameter needs its card in the matching catalog file under `src/forgegraph/catalogs/`; the build refuses a catalog that misses one.

Rebuild the catalogs (it keeps its review comments; Node 18+ is needed once it has some), and the image baselines if graphs look different on purpose:

```bash
uv run forgegraph catalog build
uv run forgegraph catalog build --pack forgegraph_base_2
uv run python scripts/mirror_specs.py
uv run python scripts/build_recreations.py --baselines
```

`uv run python scripts/visual_changelog.py main` then shows every image that changed.

## Requesting a graph type

Open a GitHub issue describing the graph you need, ideally with an example image or sketch and a little sample data. No code is needed.

## Releasing

1. Set the new version in pyproject.toml and in each built-in pack's pack.yaml.
2. Rebuild the catalogs and mirrors (above).
3. Write the visual changelog, `uv run python scripts/visual_changelog.py v<last version>`, and the CHANGELOG entry, linking it.
4. Merge with CI green, and tag the merge commit `v<version>`.
5. Run the Publish workflow.
