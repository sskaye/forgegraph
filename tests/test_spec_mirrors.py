"""Each default specification file has a Markdown mirror that matches it exactly."""

import pytest
from spec_mirror import MIRRORS, body, mirror_path, page


@pytest.mark.parametrize("kind", MIRRORS)
def test_mirror_matches_its_file(kind):
    path = mirror_path(kind)
    assert path.exists(), f"run scripts/mirror_specs.py to create {path.name}"
    assert body(path.read_text(encoding="utf-8")) == body(page(kind)), (
        f"{path.name} differs from its YAML file: carry any edits made on the page into "
        "the YAML file, then run scripts/mirror_specs.py"
    )
