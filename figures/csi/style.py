"""Pen weights, fills and type. One Style instance is shared by a whole figure."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class Style:
    """Drawing conventions for a figure.

    ISO's own figures use a single black pen at two weights on white, so that is the
    default. Change ``stroke``/``surface`` for a dark-background variant, or raise
    ``width`` for a figure that will be printed small.
    """

    stroke: str = "#000000"
    width: float = 1.5           # object outlines
    thin: float = 0.9            # axes, leaders, centre lines
    surface: str = "#ffffff"     # opaque so a nearer solid hides a farther one
    shade: str = "#d9d9d9"       # the grey ISO uses for a cut or end face
    font_family: str = "'Times New Roman', 'Nimbus Roman', 'Liberation Serif', serif"
    font_size: float = 15.0
    arrow_length: float = 11.0
    arrow_width: float = 4.2
    dash_centre: str = "14 3 3 3"
    dash_hidden: str = "6 4"
