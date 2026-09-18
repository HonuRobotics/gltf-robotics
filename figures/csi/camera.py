"""Parallel (axonometric) projection: world coordinates in, drawing coordinates out.

The world is right-handed with +Z up, matching ISO 9787 and REP 103. The camera is
described the way an engineering drawing is: an azimuth about the world +Z axis and an
elevation above the horizon. Output is in SVG user units, so y grows downwards.

Two projections are offered. ``Camera`` is axonometric, set by azimuth and elevation;
its default reproduces ISO 9787 Figures 3 and 5 — +Z straight up the page, +Y to the
upper right, +X to the lower right. ``Oblique`` puts two axes in the plane of the page
and lets the third recede, which is how ISO 9787 Figure 7 is drawn.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import List, Tuple

from .geom import Vec2, Vec3, basis_for, circle_points, dot, mul, unit

ISO_AZIMUTH = -60.0
ISO_ELEVATION = 20.0


class Projection:
    """Shared projection maths: everything follows from right, up and toward_viewer."""

    scale: float = 1.0

    @property
    def right(self) -> Vec3:  # pragma: no cover - supplied by subclasses
        raise NotImplementedError

    @property
    def up(self) -> Vec3:  # pragma: no cover
        raise NotImplementedError

    @property
    def toward_viewer(self) -> Vec3:  # pragma: no cover
        raise NotImplementedError

    def project(self, p: Vec3) -> Vec2:
        """World point -> drawing point (y down)."""
        return (self.scale * dot(p, self.right), -self.scale * dot(p, self.up))

    def project_dir(self, v: Vec3) -> Vec2:
        """World direction -> drawing direction (y down)."""
        return self.project(v)

    def depth(self, p: Vec3) -> float:
        """How near the viewer a point is; larger is nearer, so it paints later."""
        return dot(p, self.toward_viewer)

    def faces_viewer(self, normal: Vec3) -> bool:
        return dot(unit(normal), self.toward_viewer) > 1e-9

    def project_circle(self, center: Vec3, normal: Vec3, radius: float):
        """Project a 3-D circle to its exact drawing ellipse.

        Returns ``(cx, cy, rx, ry, rotation_degrees)`` so the result can be written as a
        single SVG <ellipse>, which stays editable by hand and in Inkscape.
        """
        e1, e2 = basis_for(normal)
        cx, cy = self.project(center)
        ax, ay = self.project_dir(mul(e1, radius))
        bx, by = self.project_dir(mul(e2, radius))
        # Conjugate semi-diameters (a, b) -> principal axes (Rytz's construction).
        num = 2.0 * (ax * bx + ay * by)
        den = (ax * ax + ay * ay) - (bx * bx + by * by)
        t0 = 0.5 * math.atan2(num, den)
        mx = ax * math.cos(t0) + bx * math.sin(t0)
        my = ay * math.cos(t0) + by * math.sin(t0)
        nx = -ax * math.sin(t0) + bx * math.cos(t0)
        ny = -ay * math.sin(t0) + by * math.cos(t0)
        return cx, cy, math.hypot(mx, my), math.hypot(nx, ny), math.degrees(math.atan2(my, mx))

    def project_circle_points(
        self, center: Vec3, normal: Vec3, radius: float, segments: int = 64
    ) -> List[Vec2]:
        return [self.project(p) for p in circle_points(center, normal, radius, segments)]


@dataclass
class Camera(Projection):
    """An axonometric parallel projection.

    azimuth:   degrees about world +Z; rotating it spins the scene on the page.
    elevation: degrees above the horizontal plane; 0 is a side elevation, 90 a plan view.
    scale:     drawing units per world unit.
    """

    azimuth: float = ISO_AZIMUTH
    elevation: float = ISO_ELEVATION
    scale: float = 1.0

    @property
    def right(self) -> Vec3:
        a = math.radians(self.azimuth)
        return (-math.sin(a), math.cos(a), 0.0)

    @property
    def up(self) -> Vec3:
        a, e = math.radians(self.azimuth), math.radians(self.elevation)
        return (-math.cos(a) * math.sin(e), -math.sin(a) * math.sin(e), math.cos(e))

    @property
    def toward_viewer(self) -> Vec3:
        a, e = math.radians(self.azimuth), math.radians(self.elevation)
        return (math.cos(a) * math.cos(e), math.sin(a) * math.cos(e), math.sin(e))


@dataclass
class Oblique(Projection):
    """An oblique projection: +Y across the page, +Z up it, +X receding.

    True lengths survive on the two axes lying in the page, which is why drafting uses
    this view for anything with a face worth measuring. ``foreshortening`` of 0.5 is the
    cabinet convention and 1.0 the cavalier; ``receding`` is the angle of the third axis
    below the horizontal, measured on the page.
    """

    receding: float = 40.0
    foreshortening: float = 0.62
    scale: float = 1.0

    @property
    def _recede(self) -> Vec2:
        a = math.radians(self.receding)
        k = self.foreshortening
        return (-k * math.cos(a), -k * math.sin(a))

    @property
    def right(self) -> Vec3:
        return (self._recede[0], 1.0, 0.0)

    @property
    def up(self) -> Vec3:
        return (self._recede[1], 0.0, 1.0)

    @property
    def toward_viewer(self) -> Vec3:
        dx, dy = self._recede
        return unit((1.0, -dx, -dy))


def look_along(axis: str, scale: float = 1.0) -> Camera:
    """Orthographic views for plan and elevation drawings.

    ``"-x"`` looks down the -X axis (a front elevation, +Y right, +Z up);
    ``"-z"`` looks down from above (a plan view, +X right, +Y up).
    """
    presets = {
        "-x": Camera(azimuth=-90.0, elevation=0.0, scale=scale),
        "-y": Camera(azimuth=0.0, elevation=0.0, scale=scale),
        "-z": Camera(azimuth=-90.0, elevation=90.0, scale=scale),
    }
    if axis not in presets:
        raise ValueError(f"unknown view axis {axis!r}; use one of {sorted(presets)}")
    return presets[axis]
