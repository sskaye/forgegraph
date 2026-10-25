"""Direct labels' geometry (drawing/labels.py): distances from drawn points to candidate
label boxes, computed for many boxes at once."""

from __future__ import annotations

import numpy as np
import pytest

from forgegraph.drawing.labels import _near, _rect_dist


def _brute(points: np.ndarray, boxes: np.ndarray, reach: float) -> np.ndarray:
    exact = np.array([_rect_dist(points, tuple(b)) for b in boxes])
    return np.where(exact <= reach, exact, np.inf)


def _boxes(rng: np.random.Generator, n: int, span: float) -> np.ndarray:
    corner = rng.uniform(0, span, (n, 2))
    size = rng.uniform(0, span / 5, (n, 2))
    return np.c_[corner, corner + size]


@pytest.mark.parametrize("seed", range(20))
@pytest.mark.parametrize("reach", [0.0, 3.0, 25.0, 400.0, np.inf])
def test_near_is_the_exact_distance_within_reach(seed, reach):
    """Within reach, the same value _rect_dist gives, to the last bit; beyond it, inf."""
    rng = np.random.default_rng(seed)
    points = rng.uniform(0, 300, (rng.integers(1, 400), 2))
    boxes = _boxes(rng, int(rng.integers(1, 300)), 300)
    assert np.array_equal(_near(points, boxes, reach), _brute(points, boxes, reach))


def test_near_at_exactly_the_reach():
    points = np.array([[0.0, 0.0], [10.0, 0.0]])
    boxes = np.array([[3.0, -1.0, 4.0, 1.0], [13.0, 0.0, 14.0, 0.0]])  # 3 from a point
    assert _near(points, boxes, 3.0).tolist() == [3.0, 3.0]
    assert _near(points, boxes, 2.999).tolist() == [np.inf, np.inf]


def test_near_with_no_points_or_no_boxes():
    boxes = np.array([[0.0, 0.0, 1.0, 1.0]])
    assert _near(np.empty((0, 2)), boxes, 5.0).tolist() == [np.inf]
    assert _near(np.ones((3, 2)), np.empty((0, 4)), 5.0).shape == (0,)


def test_near_with_points_inside_a_box_is_zero():
    points = np.array([[5.0, 5.0], [50.0, 50.0]])
    boxes = np.array([[0.0, 0.0, 10.0, 10.0]])
    assert _near(points, boxes, 1.0).tolist() == [0.0]


def test_near_with_many_points_in_line_and_boxes_far_apart():
    """Boxes far apart along x each see only their own neighborhood of points."""
    xs = np.linspace(0, 10_000, 20_001)
    points = np.c_[xs, np.zeros_like(xs)]
    boxes = np.array([[x, 2.0, x + 5, 4.0] for x in range(0, 10_000, 97)], dtype=float)
    assert np.array_equal(_near(points, boxes, 3.0), _brute(points, boxes, 3.0))


def test_placing_direct_labels_reads_the_axes_without_drawing(monkeypatch):
    """Where labels can go is worked out from the axes as they are now: placing them, or
    probing whether they'd fit, draws nothing."""
    from render_helpers import render

    from forgegraph.drawing import labels
    from forgegraph.drawing.figure import GraphFigure

    inside, draws = [], []
    place = labels.place_interior

    def watched(*args, **kwargs):
        inside.append(True)
        try:
            return place(*args, **kwargs)
        finally:
            inside.pop()

    original = GraphFigure.draw

    def counting_draw(self, renderer):
        if inside:
            draws.append(renderer)
        original(self, renderer)

    monkeypatch.setattr(labels, "place_interior", watched)
    monkeypatch.setattr(GraphFigure, "draw", counting_draw)
    g = render(settings={"legend.method": "direct"})
    assert g.labelling == "direct" and draws == []
