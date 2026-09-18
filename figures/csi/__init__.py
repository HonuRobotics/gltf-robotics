"""csi — coordinate-system illustrations.

A small parallel-projection drawing kit for figures in the style of ISO 9787: white
solids with black outlines, coordinate triads, and italic labels with subscripts. A
figure is a Python script that builds a Scene and saves an SVG.

    from csi import *

    scene = Scene(camera=Camera(scale=90))
    scene.add(Box(center=(0, 0, 0.15), size=(1.4, 1.0, 0.3)))
    scene.add(Frame(origin=(0, 0, 0.3), subscript="1", length=1.1))
    scene.save("out/example.svg")
"""

from .camera import ISO_AZIMUTH, ISO_ELEVATION, Camera, Oblique, Projection, look_along
from .geom import add, cross, dot, lerp, mul, sub, unit
from .scene import Scene
from .shapes import (
    ON_TOP, Arrow, Arrow2, Box, Capsule2, Circle2, Dot2, Frame, Label, Label2, Leader,
    Path2, Poly, Poly2, Shape, Solid, arc2, arc_path, centre_line2, cylinder, disc, link, polar2,
    rect2,
)
from .style import Style

__all__ = [
    "Arrow", "Arrow2", "Box", "Camera", "Capsule2", "Circle2", "Dot2", "Frame",
    "ISO_AZIMUTH", "ISO_ELEVATION", "Label", "Label2", "Leader", "ON_TOP", "Path2",
    "Oblique", "Poly", "Poly2", "Projection", "Scene", "Shape", "Solid", "Style", "add",
    "arc2", "centre_line2",
    "arc_path", "cross", "cylinder", "disc", "dot", "lerp", "link", "look_along", "mul", "polar2",
    "rect2", "sub", "unit",
]
