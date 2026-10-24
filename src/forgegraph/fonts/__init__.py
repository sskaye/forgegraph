"""The bundled fonts, and those of the packs in use."""

from importlib.resources import files
from pathlib import Path

FONT_FAMILY = "Roboto"  # the base theme's
# A theme's weight names, as the numbers font files record (matplotlib's own "light" is 200).
WEIGHTS = {"light": 300, "regular": 400, "medium": 500, "semibold": 600, "bold": 700}


def font_dir() -> Path:
    """Return the folder holding the bundled font files."""
    return Path(str(files(__package__)))


def register_fonts() -> list[Path]:
    """Register the bundled fonts with matplotlib, once, and return their paths. (Adding a
    font clears matplotlib's font lookup cache, so adding them on every call is slow.)"""
    from matplotlib import font_manager

    paths = sorted(font_dir().glob("*.ttf"))
    known = {f.fname for f in font_manager.fontManager.ttflist}
    for path in paths:
        if str(path) not in known:
            font_manager.fontManager.addfont(str(path))
    return paths


def register_pack_fonts(paths: list[Path]) -> None:
    """Register a pack's font files with matplotlib, each once."""
    from matplotlib import font_manager

    known = {f.fname for f in font_manager.fontManager.ttflist}
    for path in paths:
        if str(path) not in known:
            font_manager.fontManager.addfont(str(path))


def font_available(family: str) -> bool:
    """True if matplotlib can draw text in this family (bundled or installed), without falling
    back to another font."""
    from matplotlib import font_manager

    register_fonts()
    try:
        font_manager.findfont(font_manager.FontProperties(family=family), fallback_to_default=False)
    except ValueError:
        return False
    return True


def font_weights(family: str) -> set[int]:
    """The upright weights this family has, bundled or installed."""
    from matplotlib import font_manager

    register_fonts()
    return {
        int(f.weight)
        for f in font_manager.fontManager.ttflist
        if f.name == family and f.style == "normal" and str(f.weight).isdigit()
    }
