"""Label markup for text a user writes (architecture D8).

- `^2`, `^-1`: a caret, an optional minus and digits make a superscript.
- `^{...}` and `_{...}`: a superscript or subscript of anything; braces are always needed.
- `$` is a literal dollar sign, and everything else is drawn as written.

Labels that come from column names are never parsed: `literal()` draws them exactly.
"""

from __future__ import annotations

import re

_SCRIPT = re.compile(r"\^\{([^}]*)\}|\^(-?\d+)|_\{([^}]*)\}")


def _plain(text: str) -> str:
    return text.replace("$", r"\$")


def _math(text: str) -> str:
    return text.replace("\\", r"\\").replace("$", r"\$").replace(" ", r"\ ")


def markup(label: str) -> str:
    """Text a user wrote -> matplotlib text, with only the script fragments as maths."""
    out, pos = [], 0
    for m in _SCRIPT.finditer(label):
        out.append(_plain(label[pos : m.start()]))
        sup_braced, sup_digits, sub = m.groups()
        if sub is not None:
            out.append(f"$_{{{_math(sub)}}}$")
        else:
            out.append(f"$^{{{_math(sup_braced if sup_braced is not None else sup_digits)}}}$")
        pos = m.end()
    out.append(_plain(label[pos:]))
    return "".join(out)


def literal(label: str) -> str:
    """A column name or data value -> matplotlib text drawn exactly as written."""
    return _plain(str(label))
