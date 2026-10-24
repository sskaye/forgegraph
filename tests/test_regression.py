"""Image regression: the recreation set against baselines in tests/baselines.

After an intended change to how graphs look, regenerate the baselines with
`uv run python scripts/build_recreations.py --baselines` and review the difference.
"""

from __future__ import annotations

import io
from pathlib import Path

import pytest
from matplotlib.testing.compare import compare_images
from recreations import LAYOUT_RECREATIONS, RECREATIONS

from forgegraph.drawing.style import isolated

pytestmark = pytest.mark.slow  # the full suite only (pytest --full)

BASELINES = Path(__file__).parent / "baselines"


@pytest.mark.parametrize("r", RECREATIONS, ids=[r.name for r in RECREATIONS])
def test_recreation_matches_its_baseline(r, tmp_path):
    graph = r.render()
    buffer = io.BytesIO()
    with isolated(graph.style):
        graph.figure.savefig(buffer, format="png", dpi=72)
    actual = tmp_path / f"{r.name}.png"
    actual.write_bytes(buffer.getvalue())
    result = compare_images(str(BASELINES / f"{r.name}.png"), str(actual), tol=2.0)
    assert result is None, result


@pytest.mark.parametrize("lr", LAYOUT_RECREATIONS, ids=[lr.name for lr in LAYOUT_RECREATIONS])
def test_layout_recreation_matches_its_baseline(lr, tmp_path):
    tab = lr.render(tmp_path).tabs[0]
    actual = tmp_path / f"{lr.name}.png"
    with tab.saving():
        tab.figure.savefig(actual, format="png", dpi=72)
    result = compare_images(str(BASELINES / f"{lr.name}.png"), str(actual), tol=2.0)
    assert result is None, result
