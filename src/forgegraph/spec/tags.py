"""The !var and !fix tags: whether a GraphSpec (or a layout, or a file that extends this one)
may change a parameter.

A tag goes before a parameter's value (`width: !var 0.15`) or on a category (`output: !var`),
where it applies to everything inside unless a tag further in says otherwise. A tag with no
value (`width: !var`) changes only the status; the value comes from the file it extends. A
parameter's status comes from the nearest file in the extends chain that tags it or a
category above it; within one file, the tag nearest the parameter decides.

In memory, a tagged category is a TaggedMap, a dict that also knows its status, and any
other tagged value is a Tagged. In JSON, as provenance records a GraphSpec, a tagged value is
a mapping with one key, the tag: {"!var": 0.15}.
"""

from __future__ import annotations

from typing import Any

from ruamel.yaml import YAML
from ruamel.yaml.constructor import SafeConstructor
from ruamel.yaml.nodes import MappingNode, ScalarNode, SequenceNode

VAR, FIX = "!var", "!fix"
TAGS = (VAR, FIX)


class _Unset:
    """A tag's missing value: `width: !var` sets only the status."""

    def __repr__(self) -> str:
        return "UNSET"

    def __deepcopy__(self, memo: dict[int, Any]) -> _Unset:
        return self


UNSET = _Unset()


class Tagged:
    """A parameter's value with a tag: fixed for !fix, variable for !var."""

    __slots__ = ("fixed", "value")

    def __init__(self, value: Any, fixed: bool) -> None:
        self.value = value
        self.fixed = fixed

    @property
    def tag(self) -> str:
        return FIX if self.fixed else VAR

    def __eq__(self, other: object) -> bool:
        return isinstance(other, Tagged) and (self.value, self.fixed) == (other.value, other.fixed)

    def __hash__(self) -> int:
        return hash((repr(self.value), self.fixed))

    def __repr__(self) -> str:
        return f"{self.tag} {self.value!r}"


class TaggedMap(dict[str, Any]):
    """A category with a tag: a dict, so it reads as any category does, that also knows
    whether it's fixed."""

    def __init__(self, *args: Any, fixed: bool, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        self.fixed = fixed

    @property
    def tag(self) -> str:
        return FIX if self.fixed else VAR

    def __deepcopy__(self, memo: dict[int, Any]) -> TaggedMap:
        import copy

        return TaggedMap({k: copy.deepcopy(v, memo) for k, v in self.items()}, fixed=self.fixed)

    def __reduce__(self) -> Any:
        return (_tagged_map, (dict(self), self.fixed))

    def __repr__(self) -> str:
        return f"{self.tag} {dict.__repr__(self)}"


def _tagged_map(items: dict[str, Any], fixed: bool) -> TaggedMap:
    return TaggedMap(items, fixed=fixed)


def var(value: Any = UNSET) -> Any:
    """A value, or a category (a dict), tagged !var."""
    return TaggedMap(value, fixed=False) if isinstance(value, dict) else Tagged(value, False)


def fix(value: Any = UNSET) -> Any:
    """A value, or a category (a dict), tagged !fix."""
    return TaggedMap(value, fixed=True) if isinstance(value, dict) else Tagged(value, True)


def status(node: Any) -> bool | None:
    """Whether a tagged node is fixed; None if it has no tag."""
    return node.fixed if isinstance(node, Tagged | TaggedMap) else None


def untag(node: Any) -> Any:
    """A node's value without its own tag; a TaggedMap stays as it is, being a dict."""
    return node.value if isinstance(node, Tagged) else node


def plain(node: Any) -> Any:
    """A tree with every tag removed, and tags with no value left out."""
    node = untag(node)
    if isinstance(node, dict):
        return {k: plain(v) for k, v in node.items() if untag(v) is not UNSET}
    if isinstance(node, list):
        return [plain(v) for v in node]
    return node


def status_at(tree: Any, path: str) -> bool | None:
    """The status a tree's tags give a dotted path: the tag nearest it, on it or on a
    category above it; None if none does."""
    found = status(tree)
    node = untag(tree)
    for key in path.split("."):
        if not isinstance(node, dict) or key not in node:
            break
        node = node[key]
        if (s := status(node)) is not None:
            found = s
        node = untag(node)
    return found


# --- YAML -----------------------------------------------------------------------------


def _construct(fixed: bool):
    def construct(constructor: Any, node: Any) -> Any:
        if isinstance(node, MappingNode):
            node.tag = "tag:yaml.org,2002:map"
            return TaggedMap(constructor.construct_mapping(node, deep=True), fixed=fixed)
        if isinstance(node, SequenceNode):
            node.tag = "tag:yaml.org,2002:seq"
            return Tagged(constructor.construct_sequence(node, deep=True), fixed)
        assert isinstance(node, ScalarNode)
        if node.value == "" and node.style is None:
            return Tagged(UNSET, fixed)
        plain_style = node.style is None  # a quoted scalar is text, as it would be untagged
        implicit = constructor.loader.resolver.resolve(ScalarNode, node.value, (plain_style, False))
        plain_node = ScalarNode(implicit, node.value, node.start_mark, node.end_mark, node.style)
        return Tagged(constructor.construct_object(plain_node, deep=True), fixed)

    return construct


def _represent(representer: Any, data: Any) -> Any:
    value = untag(data)
    if isinstance(data, TaggedMap):
        return representer.represent_mapping(data.tag, dict(data))
    if value is UNSET:
        return representer.represent_scalar(data.tag, "")
    if value is None:
        return representer.represent_scalar(data.tag, "~")
    if isinstance(value, list):
        return representer.represent_sequence(data.tag, value)
    node = representer.represent_data(value)
    node.tag = data.tag
    return node


class _Constructor(SafeConstructor):
    """YAML's safe constructor, also reading !var and !fix."""


for _tag in TAGS:
    _Constructor.add_constructor(_tag, _construct(_tag == FIX))


def loader() -> YAML:
    """A safe YAML reader that reads !var and !fix."""
    yaml = YAML(typ="safe", pure=True)
    yaml.Constructor = _Constructor
    return yaml


def with_tags(yaml: YAML) -> YAML:
    """A ruamel YAML instance that writes Tagged and TaggedMap values with their tags."""
    for cls in (Tagged, TaggedMap):
        yaml.representer.add_representer(cls, _represent)
    return yaml


# --- JSON -----------------------------------------------------------------------------


def to_json(node: Any) -> Any:
    """A tree for JSON: each tagged value as a mapping with one key, its tag. A tag with no
    value maps to null, so a tagged null is written as the word None, which means the same."""
    if isinstance(node, Tagged | TaggedMap):
        value = untag(node)
        if value is UNSET:
            return {node.tag: None}
        if isinstance(node, TaggedMap):
            return {node.tag: to_json(dict(node))}
        return {node.tag: "None" if value is None else to_json(value)}
    if isinstance(node, dict):
        return {k: to_json(v) for k, v in node.items()}
    if isinstance(node, list):
        return [to_json(v) for v in node]
    return node


def from_json(node: Any) -> Any:
    """The inverse of to_json."""
    if isinstance(node, dict):
        if len(node) == 1 and next(iter(node)) in TAGS:
            tag, value = next(iter(node.items()))
            fixed = tag == FIX
            if isinstance(value, dict):
                return TaggedMap(from_json(value), fixed=fixed)
            return Tagged(UNSET if value is None else from_json(value), fixed)
        return {k: from_json(v) for k, v in node.items()}
    if isinstance(node, list):
        return [from_json(v) for v in node]
    return node
