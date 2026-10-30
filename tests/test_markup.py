"""Label markup test vectors (architecture D8)."""

import pytest

from forgegraph.drawing.markup import literal, markup, to_html


@pytest.mark.parametrize(
    ("written", "drawn"),
    [
        ("Cell Voltage (V)", "Cell Voltage (V)"),
        ("Cell Current (mA/cm^2)", "Cell Current (mA/cm$^{2}$)"),
        ("Rate (mol L^-1 s^-1)", "Rate (mol L$^{-1}$ s$^{-1}$)"),
        ("Volume (10^{3} L)", "Volume (10$^{3}$ L)"),
        ("P_{max} in 6M KOH_{aq}", "P$_{max}$ in 6M KOH$_{aq}$"),
        ("x^{a b}", r"x$^{a\ b}$"),
        ("Cost ($)", r"Cost (\$)"),
        ("a^b", "a^b"),  # a caret not followed by digits or braces stays as written
        ("current_density", "current_density"),  # an underscore without braces stays
    ],
)
def test_markup(written, drawn):
    assert markup(written) == drawn


@pytest.mark.parametrize(
    ("name", "drawn"),
    [("current_density", "current_density"), ("x^2", "x^2"), ("$/kWh", r"\$/kWh")],
)
def test_column_names_are_drawn_exactly(name, drawn):
    assert literal(name) == drawn


@pytest.mark.parametrize(
    ("written", "shown"),
    [
        ("Cell Current (mA/cm^2)", "Cell Current (mA/cm<sup>2</sup>)"),
        ("P_{max} in 6M KOH_{aq}", "P<sub>max</sub> in 6M KOH<sub>aq</sub>"),
        ("Rate (mol L^-1)", "Rate (mol L<sup>-1</sup>)"),
        ("a < b & $c", "a &lt; b &amp; $c"),
        ("x_{<i>}", "x<sub>&lt;i&gt;</sub>"),
    ],
)
def test_markup_in_html(written, shown):
    assert to_html(written) == shown
