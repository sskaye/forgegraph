"""The documentation site's examples (scripts/docs_site.py): every GraphSpec and layout its
guides and gallery show draws, standard and lint-clean, and every image or page a page links
to is one the site builds."""

import importlib.util
import re
from pathlib import Path

import pytest

ROOT = Path(__file__).parents[1]
SITE = ROOT / "docs" / "site"
_spec = importlib.util.spec_from_file_location("docs_site", ROOT / "scripts" / "docs_site.py")
assert _spec is not None and _spec.loader is not None
docs_site = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(docs_site)


@pytest.mark.slow
def test_every_example_draws_and_every_linked_image_is_built():
    built = set(docs_site.example_images())  # raises on an example that isn't clean
    for spec in docs_site.EXAMPLES.glob("*.yaml"):
        name = spec.name.removesuffix(".yaml").removesuffix(".layout")
        assert any(Path(p).stem.startswith(name) for p in built), f"{spec.name} drew nothing"
    for page in SITE.rglob("*.md"):
        for link in re.findall(r"\]\(((?:\.\./)*(?:images|pages)/[^)]+)\)", page.read_text()):
            assert link.lstrip("./") in built, f"{page.relative_to(SITE)} links to {link}"
