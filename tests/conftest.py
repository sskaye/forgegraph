"""`uv run pytest` runs the development suite: every test not marked slow. `--full` runs
them all, as CI does and as a release needs.

Every test has its own main config, whatever the machine has: FORGEGRAPH_CONFIG names a
file in a folder of its own, listing the built-in packs, as ForgeGraph writes it on first
use. A test of the main config writes its own and points FORGEGRAPH_CONFIG at it."""

import pytest

from forgegraph import packs


@pytest.fixture(autouse=True)
def own_main_config(tmp_path_factory, monkeypatch):
    path = tmp_path_factory.mktemp("main") / "config.toml"
    path.write_text("packs = [" + ", ".join(f'"{p}"' for p in packs.BUILT_IN) + "]\n")
    monkeypatch.setenv(packs.MAIN_CONFIG_VARIABLE, str(path))


def pytest_addoption(parser):
    parser.addoption("--full", action="store_true", help="Run the slow tests too.")


def pytest_collection_modifyitems(config, items):
    if config.getoption("--full"):
        return
    slow = [i for i in items if i.get_closest_marker("slow")]
    if slow:
        config.hook.pytest_deselected(items=slow)
        items[:] = [i for i in items if not i.get_closest_marker("slow")]
