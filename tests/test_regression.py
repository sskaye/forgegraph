"""Image regression: the recreation set against baselines in tests/baselines.

After an intended change to how graphs look, regenerate the baselines with
`uv run python scripts/build_recreations.py --baselines` and review the difference.
"""

from __future__ import annotations

from pathlib import Path

import pytest
from matplotlib.testing.compare import compare_images
from recreations import LAYOUT_RECREATIONS, RECREATIONS, baseline_image

pytestmark = pytest.mark.slow  # the full suite only (pytest --full)

BASELINES = Path(__file__).parent / "baselines"
ALL = [*RECREATIONS, *LAYOUT_RECREATIONS]


@pytest.mark.parametrize("r", ALL, ids=[r.name for r in ALL])
def test_recreation_matches_its_baseline(r, tmp_path):
    actual = baseline_image(r, tmp_path / f"{r.name}.png", tmp_path)
    result = compare_images(str(BASELINES / f"{r.name}.png"), str(actual), tol=2.0)
    assert result is None, result
