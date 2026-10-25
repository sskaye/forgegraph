"""The errors drawing raises: each says what in the specs to change."""


class DrawError(ValueError):
    """A GraphSpec whose data can't be drawn as asked."""


class LayoutError(ValueError):
    """The format is too small for what has to be drawn around the plot box."""
