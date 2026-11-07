"""The skill's examples: copies of the documentation's (scripts/skill_examples.py), with
their data, and the list in SKILL.md names each one it bundles."""

from __future__ import annotations

import importlib.util
import re
from pathlib import Path

ROOT = Path(__file__).parents[1]
_spec = importlib.util.spec_from_file_location(
    "skill_examples", ROOT / "scripts" / "skill_examples.py"
)
assert _spec is not None and _spec.loader is not None
skill_examples = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(skill_examples)


def test_the_skills_examples_are_the_documentations():
    assert skill_examples.stale() == [], "run scripts/skill_examples.py"


def test_skill_md_lists_each_example_it_bundles():
    text = (skill_examples.SKILL.parent / "SKILL.md").read_text(encoding="utf-8")
    listed = re.findall(r"^- \[examples/([^\]]+)\]\(examples/\1\)", text, re.M)
    assert listed == list(skill_examples.LISTED)
