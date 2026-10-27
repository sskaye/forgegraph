"""The !var and !fix tags: reading them from YAML, writing them back, the status they give a
parameter, and their JSON form in provenance records."""

from __future__ import annotations

import io
import json

import pytest
from ruamel.yaml import YAML
from ruamel.yaml.constructor import ConstructorError

from forgegraph.spec.tags import (
    UNSET,
    Tagged,
    TaggedMap,
    fix,
    from_json,
    loader,
    plain,
    status_at,
    to_json,
    var,
    with_tags,
)


def load(text: str):
    return loader().load(text)


def dump(data) -> str:
    out = io.StringIO()
    with_tags(YAML()).dump(data, out)
    return out.getvalue()


@pytest.mark.parametrize(
    ("text", "value"),
    [
        ("!var 0.15", 0.15),
        ("!fix 3", 3),
        ("!var true", True),
        ("!var None", "None"),
        ("!var ~", None),
        ('!var "#000000"', "#000000"),
        ("!fix okabe_ito", "okabe_ito"),
        ("!var [solid, dashed]", ["solid", "dashed"]),
        ('!var ""', ""),
    ],
)
def test_a_tagged_value_keeps_its_type(text, value):
    """A tag replaces YAML's own tag, so the value is read as it would be untagged."""
    got = load(f"a: {text}")["a"]
    assert isinstance(got, Tagged)
    assert got.value == value
    assert type(got.value) is type(value)
    assert got.fixed == text.startswith("!fix")


def test_a_tag_with_no_value_sets_only_the_status():
    got = load("a: !var\nb: 1\n")
    assert got["a"] == Tagged(UNSET, False)


def test_a_tagged_category_is_a_dict_with_a_status():
    got = load("output: !var\n    dpi: 600\n    types: !fix [png]\n")
    out = got["output"]
    assert isinstance(out, TaggedMap)
    assert isinstance(out, dict)
    assert out.fixed is False
    assert out["dpi"] == 600
    assert out["types"] == Tagged(["png"], True)


def test_an_unknown_tag_is_an_error():
    with pytest.raises(ConstructorError):
        load("a: !variable 0.15")


@pytest.mark.parametrize(
    "text",
    [
        "parameters: !fix\n    a: 1\n    b: !var 2\n    c: !var\n",
        "parameters:\n    line: !var\n    x: !fix [a, b]\n    y: !var ~\n    z: !fix '#FFFFFF'\n",
    ],
)
def test_tags_are_written_back_as_read(text):
    data = load(text)
    assert load(dump(data)) == data


def test_status_comes_from_the_nearest_tag():
    tree = load(
        """parameters: !fix
    a:
        b: 1
        c: !var 2
    d: !var
        e: 3
        f: !fix 4
"""
    )["parameters"]
    assert status_at(tree, "a.b") is True  # the category's tag
    assert status_at(tree, "a.c") is False  # its own, nearer
    assert status_at(tree, "d.e") is False
    assert status_at(tree, "d.f") is True
    assert status_at(tree, "d.g") is False  # not listed here, but under a tagged category
    assert status_at({"a": {"b": 1}}, "a.b") is None  # no tag anywhere


def test_plain_drops_the_tags_and_status_only_entries():
    tree = {"a": var(1), "b": fix({"c": var(), "d": 2}), "e": [fix(1)]}
    assert plain(tree) == {"a": 1, "b": {"d": 2}, "e": [1]}


def test_the_json_form_round_trips():
    tree = fix({"a": var(0.15), "b": var(), "c": {"d": fix([1, 2])}, "e": var(None)})
    written = json.loads(json.dumps(to_json(tree)))
    assert written == {
        "!fix": {"a": {"!var": 0.15}, "b": {"!var": None}, "c": {"d": {"!fix": [1, 2]}},
                 "e": {"!var": "None"}}
    }  # fmt: skip
    back = from_json(written)
    assert back["a"] == var(0.15)
    assert back["b"] == var()
    assert back["e"] == var("None")  # a tagged null comes back as the word None
    assert isinstance(back, TaggedMap) and back.fixed


def test_reading_tags_leaves_other_yaml_readers_as_they_were():
    """The definition files are read with ruamel's own round-trip reader, which keeps a tag
    on the value; setting up the tag reader and writer mustn't change it."""
    from ruamel.yaml.comments import TaggedScalar

    load("a: !var 1")
    dump({"a": var(1)})
    assert isinstance(YAML().load("a: !var 1")["a"], TaggedScalar)
    with pytest.raises(ConstructorError):
        YAML(typ="safe", pure=True).load("a: !var 1")
