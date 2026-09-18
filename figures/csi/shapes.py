"""The drawing vocabulary: solids, coordinate frames, arrows, labels, flat 2-D linework.

Every shape knows three things — how deep it sits (so the scene can paint far to near),
how to draw itself, and roughly how much room it takes up (so the scene can size the
page). Solids are filled with an opaque white, so a nearer one hides a farther one
without any hidden-line computation.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Sequence, Tuple, Union

from . import svgout as S
from .camera import Camera, Projection
from .geom import (
    Vec2, Vec3, add, centroid, convex_hull, cross, dot, length, lerp, mul, sub, unit,
)
from .style import Style

ON_TOP = 1e9  # depth used by annotation: axes and labels always paint over the solids

AXES: Dict[str, Vec3] = {"x": (1.0, 0.0, 0.0), "y": (0.0, 1.0, 0.0), "z": (0.0, 0.0, 1.0)}


@dataclass
class Shape:
    """Base class. ``z`` overrides the painter's-algorithm depth when set."""

    z: Optional[float] = None

    def depth(self, cam: Projection) -> float:  # pragma: no cover - overridden
        return 0.0

    def sort_key(self, cam: Projection) -> float:
        return self.depth(cam) if self.z is None else self.z

    def draw(self, cam: Projection, style: Style) -> List[str]:  # pragma: no cover
        raise NotImplementedError

    def extent(self, cam: Projection, style: Style) -> List[Vec2]:  # pragma: no cover
        return []


# --------------------------------------------------------------------------- solids


@dataclass
class Box(Shape):
    """A rectangular block, drawn as its three visible faces."""

    center: Vec3 = (0.0, 0.0, 0.0)
    size: Vec3 = (1.0, 1.0, 1.0)
    axes: Optional[Tuple[Vec3, Vec3, Vec3]] = None   # a tilted block, e.g. a camera body
    fill: Optional[str] = None
    top_fill: Optional[str] = None
    width: Optional[float] = None
    name: str = "box"

    def _frame(self) -> Tuple[Vec3, Vec3, Vec3]:
        if self.axes is None:
            return AXES["x"], AXES["y"], AXES["z"]
        return tuple(unit(a) for a in self.axes)  # type: ignore[return-value]

    @classmethod
    def from_corners(cls, a: Vec3, b: Vec3, **kwargs) -> "Box":
        center = tuple((a[i] + b[i]) / 2.0 for i in range(3))
        size = tuple(abs(b[i] - a[i]) for i in range(3))
        return cls(center=center, size=size, **kwargs)  # type: ignore[arg-type]

    def _corner(self, sx: float, sy: float, sz: float) -> Vec3:
        ex, ey, ez = self._frame()
        hx, hy, hz = (s / 2.0 for s in self.size)
        return add(self.center, add(mul(ex, sx * hx), add(mul(ey, sy * hy), mul(ez, sz * hz))))

    def corners(self) -> List[Vec3]:
        return [self._corner(sx, sy, sz)
                for sx in (-1, 1) for sy in (-1, 1) for sz in (-1, 1)]

    def faces(self) -> List[Tuple[Vec3, List[Vec3]]]:
        ex, ey, ez = self._frame()
        corner = self._corner

        def normal(nx, ny, nz):
            return add(mul(ex, nx), add(mul(ey, ny), mul(ez, nz)))

        return [
            (normal(1, 0, 0), [corner(1, -1, -1), corner(1, 1, -1), corner(1, 1, 1), corner(1, -1, 1)]),
            (normal(-1, 0, 0), [corner(-1, -1, -1), corner(-1, -1, 1), corner(-1, 1, 1), corner(-1, 1, -1)]),
            (normal(0, 1, 0), [corner(-1, 1, -1), corner(-1, 1, 1), corner(1, 1, 1), corner(1, 1, -1)]),
            (normal(0, -1, 0), [corner(-1, -1, -1), corner(1, -1, -1), corner(1, -1, 1), corner(-1, -1, 1)]),
            (normal(0, 0, 1), [corner(-1, -1, 1), corner(1, -1, 1), corner(1, 1, 1), corner(-1, 1, 1)]),
            (normal(0, 0, -1), [corner(-1, -1, -1), corner(-1, 1, -1), corner(1, 1, -1), corner(1, -1, -1)]),
        ]

    def depth(self, cam: Projection) -> float:
        return cam.depth(self.center)

    def draw(self, cam: Projection, style: Style) -> List[str]:
        visible = [(n, f) for n, f in self.faces() if cam.faces_viewer(n)]
        visible.sort(key=lambda nf: cam.depth(centroid(nf[1])))
        out = []
        for normal, face in visible:
            is_top = self.top_fill and dot(unit(normal), self._frame()[2]) > 0.99
            fill = self.top_fill if is_top else (self.fill or style.surface)
            out.append(S.polygon(
                [cam.project(p) for p in face], fill, style.stroke,
                self.width or style.width,
            ))
        return out

    def extent(self, cam: Projection, style: Style) -> List[Vec2]:
        return [cam.project(p) for p in self.corners()]


@dataclass
class Solid(Shape):
    """A solid whose outline is the hull of a set of 3-D circles and points.

    This one primitive covers a cylinder (two circles on a common axis), a tapered arm
    link (two circles sharing the joint axis), a wheel, and a capsule. The silhouette is
    exact for any convex body built this way, which is what the ISO figures draw.
    """

    circles: Sequence[Tuple[Vec3, Vec3, float]] = ()
    points: Sequence[Vec3] = ()
    rims: Union[str, Sequence[int]] = "facing"   # "facing", "all", "none", or indices
    fill: Optional[str] = None
    rim_fill: Optional[str] = None
    width: Optional[float] = None
    segments: int = 72
    name: str = "solid"

    def _samples(self, cam: Projection) -> List[Vec2]:
        out = [cam.project(p) for p in self.points]
        for center, normal, radius in self.circles:
            out += cam.project_circle_points(center, normal, radius, self.segments)
        return out

    def _anchor_points(self) -> List[Vec3]:
        return list(self.points) + [c for c, _, _ in self.circles]

    def depth(self, cam: Projection) -> float:
        return cam.depth(centroid(self._anchor_points()))

    def _rim_indices(self, cam: Projection) -> List[int]:
        if self.rims == "none":
            return []
        if self.rims == "all":
            return list(range(len(self.circles)))
        if self.rims == "facing":
            return [i for i, (_, n, _) in enumerate(self.circles) if cam.faces_viewer(n)]
        return list(self.rims)  # type: ignore[arg-type]

    def draw(self, cam: Projection, style: Style) -> List[str]:
        width = self.width or style.width
        out = [S.polygon(
            convex_hull(self._samples(cam)), self.fill or style.surface,
            style.stroke, width,
        )]
        for i in self._rim_indices(cam):
            center, normal, radius = self.circles[i]
            cx, cy, rx, ry, rot = cam.project_circle(center, normal, radius)
            out.append(S.ellipse(
                cx, cy, rx, ry, rot, self.rim_fill or self.fill or style.surface,
                style.stroke, width,
            ))
        return out

    def extent(self, cam: Projection, style: Style) -> List[Vec2]:
        return self._samples(cam)


def cylinder(p0: Vec3, p1: Vec3, radius: float, **kwargs) -> Solid:
    """A circular cylinder between two points."""
    axis = unit(sub(p1, p0))
    return Solid(
        circles=[(p0, mul(axis, -1.0), radius), (p1, axis, radius)], **kwargs
    )


def link(p0: Vec3, r0: float, p1: Vec3, r1: float, axis: Vec3, thickness: float, **kwargs) -> Solid:
    """An arm segment: two joint cylinders of the given thickness joined by a tapered body.

    ``axis`` is the joint axis, shared by both ends — the shape ISO 9787 draws for an
    articulated arm. Only the joint rims facing the viewer are drawn, so the result reads
    as a solid rather than a wireframe.
    """
    a = unit(axis)
    half = mul(a, thickness / 2.0)
    return Solid(circles=[
        (sub(p0, half), mul(a, -1.0), r0), (add(p0, half), a, r0),
        (sub(p1, half), mul(a, -1.0), r1), (add(p1, half), a, r1),
    ], **kwargs)


def disc(center: Vec3, normal: Vec3, radius: float, thickness: float, **kwargs) -> Solid:
    """A short cylinder — a wheel, a flange, a puck."""
    n = unit(normal)
    half = mul(n, thickness / 2.0)
    return cylinder(sub(center, half), add(center, half), radius, **kwargs)


@dataclass
class Poly(Shape):
    """A polygon or polyline given directly in 3-D, filled or not."""

    points: Sequence[Vec3] = ()
    fill: Optional[str] = None
    closed: bool = True
    width: Optional[float] = None
    dash: Optional[str] = None
    name: str = "poly"

    def depth(self, cam: Projection) -> float:
        return cam.depth(centroid(self.points))

    def draw(self, cam: Projection, style: Style) -> List[str]:
        return [S.polygon(
            [cam.project(p) for p in self.points], self.fill, style.stroke,
            self.width or style.width, dash=self.dash, closed=self.closed,
        )]

    def extent(self, cam: Projection, style: Style) -> List[Vec2]:
        return [cam.project(p) for p in self.points]


# ----------------------------------------------------------------- annotation in 3-D


def _head(tip: Vec2, direction: Vec2, style: Style) -> Tuple[str, Vec2]:
    """A solid arrowhead at ``tip``; also returns the point where the shaft should stop."""
    dx, dy = direction
    n = math.hypot(dx, dy) or 1.0
    ux, uy = dx / n, dy / n
    base = (tip[0] - style.arrow_length * ux, tip[1] - style.arrow_length * uy)
    px, py = -uy * style.arrow_width, ux * style.arrow_width
    poly = S.polygon(
        [tip, (base[0] + px, base[1] + py), (base[0] - px, base[1] - py)],
        style.stroke, style.stroke, style.thin,
    )
    return poly, base


@dataclass
class Arrow(Shape):
    """A straight arrow between two world points, with an optional label past the tip."""

    start: Vec3 = (0.0, 0.0, 0.0)
    end: Vec3 = (1.0, 0.0, 0.0)
    label: Optional[str] = None
    label_offset: Vec2 = (0.0, 0.0)
    label_gap: float = 13.0
    label_anchor: Optional[str] = None
    head: bool = True
    width: Optional[float] = None
    dash: Optional[str] = None
    name: str = "arrow"

    def depth(self, cam: Projection) -> float:
        return ON_TOP if self.z is None else self.z

    def sort_key(self, cam: Projection) -> float:
        return self.z if self.z is not None else ON_TOP

    def _label_point(self, cam: Projection) -> Tuple[Vec2, str]:
        p0, p1 = cam.project(self.start), cam.project(self.end)
        dx, dy = p1[0] - p0[0], p1[1] - p0[1]
        n = math.hypot(dx, dy) or 1.0
        x = p1[0] + self.label_gap * dx / n + self.label_offset[0]
        y = p1[1] + self.label_gap * dy / n + self.label_offset[1]
        anchor = self.label_anchor
        if anchor is None:
            anchor = "start" if dx > 2.0 else "end" if dx < -2.0 else "middle"
        return (x, y), anchor

    def draw(self, cam: Projection, style: Style) -> List[str]:
        p0, p1 = cam.project(self.start), cam.project(self.end)
        out = []
        stop = p1
        if self.head:
            poly, stop = _head(p1, (p1[0] - p0[0], p1[1] - p0[1]), style)
            out.append(poly)
        out.insert(0, S.line(p0, stop, style.stroke, self.width or style.thin, dash=self.dash))
        if self.label:
            (x, y), anchor = self._label_point(cam)
            out.append(S.text(x, y, self.label, style, anchor=anchor))
        return out

    def extent(self, cam: Projection, style: Style) -> List[Vec2]:
        out = [cam.project(self.start), cam.project(self.end)]
        if self.label:
            (x, y), _ = self._label_point(cam)
            out += S.text_extent(x, y, self.label, style.font_size)
        return out


@dataclass
class Frame(Shape):
    """A coordinate system drawn the way ISO 9787 draws one: three arrows and a named origin.

    ``subscript`` labels all four names at once — ``subscript="0"`` gives
    *O*₀, *X*₀, *Y*₀, *Z*₀. Pass ``directions`` to point the axes anywhere (a mechanical
    interface frame is rarely axis-aligned), ``lengths`` to stretch one axis, and
    ``offsets`` to nudge a label clear of the geometry.
    """

    origin: Vec3 = (0.0, 0.0, 0.0)
    subscript: str = "0"
    length: float = 1.0
    lengths: Dict[str, float] = field(default_factory=dict)
    directions: Dict[str, Vec3] = field(default_factory=dict)
    offsets: Dict[str, Vec2] = field(default_factory=dict)
    anchors: Dict[str, str] = field(default_factory=dict)
    origin_label: Optional[str] = None      # defaults to O with the subscript
    origin_offset: Vec2 = (-11.0, 9.0)
    origin_anchor: str = "middle"
    dot: bool = True
    axes: str = "xyz"
    name: str = "frame"

    def _arrows(self) -> List[Arrow]:
        out = []
        for key in self.axes:
            direction = unit(self.directions.get(key, AXES[key]))
            tip = add(self.origin, mul(direction, self.lengths.get(key, self.length)))
            out.append(Arrow(
                start=self.origin, end=tip,
                label=f"{key.upper()}_{self.subscript}" if self.subscript else key.upper(),
                label_offset=self.offsets.get(key, (0.0, 0.0)),
                label_anchor=self.anchors.get(key),
                z=self.z,
            ))
        return out

    def sort_key(self, cam: Projection) -> float:
        return self.z if self.z is not None else ON_TOP

    def draw(self, cam: Projection, style: Style) -> List[str]:
        out: List[str] = []
        for arrow in self._arrows():
            out += arrow.draw(cam, style)
        ox, oy = cam.project(self.origin)
        if self.dot:
            out.append(S.circle(ox, oy, 2.2, style.stroke))
        name = self.origin_label if self.origin_label is not None else (
            f"O_{self.subscript}" if self.subscript else "O"
        )
        if name:
            out.append(S.text(
                ox + self.origin_offset[0], oy + self.origin_offset[1], name, style,
                anchor=self.origin_anchor,
            ))
        return out

    def extent(self, cam: Projection, style: Style) -> List[Vec2]:
        out: List[Vec2] = [cam.project(self.origin)]
        for arrow in self._arrows():
            out += arrow.extent(cam, style)
        return out


@dataclass
class Label(Shape):
    """Text pinned to a world point, nudged by a drawing-space offset."""

    at: Vec3 = (0.0, 0.0, 0.0)
    text: str = ""
    offset: Vec2 = (0.0, 0.0)
    anchor: str = "middle"
    math: bool = True
    size: Optional[float] = None
    name: str = "label"

    def sort_key(self, cam: Projection) -> float:
        return self.z if self.z is not None else ON_TOP

    def _xy(self, cam: Projection) -> Vec2:
        x, y = cam.project(self.at)
        return (x + self.offset[0], y + self.offset[1])

    def draw(self, cam: Projection, style: Style) -> List[str]:
        x, y = self._xy(cam)
        return [S.text(x, y, self.text, style, anchor=self.anchor, math=self.math, size=self.size)]

    def extent(self, cam: Projection, style: Style) -> List[Vec2]:
        x, y = self._xy(cam)
        return S.text_extent(x, y, self.text, self.size or style.font_size)


@dataclass
class Leader(Shape):
    """A thin polyline in world space: the line from a key number to the thing it names."""

    points: Sequence[Vec3] = ()
    head: bool = False
    width: Optional[float] = None
    dash: Optional[str] = None
    name: str = "leader"

    def sort_key(self, cam: Projection) -> float:
        return self.z if self.z is not None else ON_TOP

    def draw(self, cam: Projection, style: Style) -> List[str]:
        flat = [cam.project(p) for p in self.points]
        out = []
        if self.head and len(flat) >= 2:
            poly, stop = _head(flat[-1], (flat[-1][0] - flat[-2][0], flat[-1][1] - flat[-2][1]), style)
            out.append(poly)
            flat = flat[:-1] + [stop]
        out.insert(0, S.polygon(
            flat, None, style.stroke, self.width or style.thin, dash=self.dash, closed=False,
        ))
        return out

    def extent(self, cam: Projection, style: Style) -> List[Vec2]:
        return [cam.project(p) for p in self.points]


# ------------------------------------------------------------------- flat 2-D linework
# Coordinates are drawing units with y up, so a flat figure reads like graph paper.
# These ignore the camera, which is what makes a plan or elevation view straightforward.


def _flat(p: Vec2) -> Vec2:
    return (p[0], -p[1])


@dataclass
class Flat(Shape):
    def sort_key(self, cam: Projection) -> float:
        return self.z if self.z is not None else 0.0


@dataclass
class Poly2(Flat):
    """A polyline or polygon in flat drawing coordinates."""

    points: Sequence[Vec2] = ()
    fill: Optional[str] = None
    closed: bool = False
    width: Optional[float] = None
    dash: Optional[str] = None
    name: str = "poly2"

    def draw(self, cam: Projection, style: Style) -> List[str]:
        return [S.polygon(
            [_flat(p) for p in self.points], self.fill, style.stroke,
            self.width or style.width, dash=self.dash, closed=self.closed,
        )]

    def extent(self, cam: Projection, style: Style) -> List[Vec2]:
        return [_flat(p) for p in self.points]


def rect2(x: float, y: float, w: float, h: float, **kwargs) -> Poly2:
    """A rectangle with its lower-left corner at (x, y)."""
    kwargs.setdefault("closed", True)
    return Poly2(points=[(x, y), (x + w, y), (x + w, y + h), (x, y + h)], **kwargs)


@dataclass
class Path2(Flat):
    """Raw SVG path data in flat coordinates — for arcs and anything hand-tuned.

    Write the ``d`` string with y up; it is flipped on output, so ``A`` sweep flags read
    counter-clockwise as they do in maths.
    """

    d: str = ""
    fill: Optional[str] = None
    width: Optional[float] = None
    dash: Optional[str] = None
    bbox: Sequence[Vec2] = ()
    name: str = "path2"

    def draw(self, cam: Projection, style: Style) -> List[str]:
        return [S.path(
            self.d, self.fill, style.stroke, self.width or style.width, dash=self.dash,
            transform="scale(1,-1)",
        )]

    def extent(self, cam: Projection, style: Style) -> List[Vec2]:
        return [_flat(p) for p in self.bbox]


@dataclass
class Circle2(Flat):
    center: Vec2 = (0.0, 0.0)
    radius: float = 1.0
    fill: Optional[str] = None
    width: Optional[float] = None
    dash: Optional[str] = None
    name: str = "circle2"

    def draw(self, cam: Projection, style: Style) -> List[str]:
        x, y = _flat(self.center)
        return [S.ellipse(
            x, y, self.radius, self.radius, 0.0, self.fill, style.stroke,
            self.width or style.width, stroke_dasharray=self.dash,
        )]

    def extent(self, cam: Projection, style: Style) -> List[Vec2]:
        x, y = _flat(self.center)
        return [(x - self.radius, y - self.radius), (x + self.radius, y + self.radius)]


@dataclass
class Arrow2(Flat):
    """A straight arrow in flat coordinates, with an optional label past the tip."""

    start: Vec2 = (0.0, 0.0)
    end: Vec2 = (1.0, 0.0)
    label: Optional[str] = None
    label_offset: Vec2 = (0.0, 0.0)
    label_gap: float = 13.0
    label_anchor: Optional[str] = None
    head: bool = True
    width: Optional[float] = None
    dash: Optional[str] = None
    name: str = "arrow2"

    def _label_point(self, style: Style) -> Tuple[Vec2, str]:
        p0, p1 = _flat(self.start), _flat(self.end)
        dx, dy = p1[0] - p0[0], p1[1] - p0[1]
        n = math.hypot(dx, dy) or 1.0
        x = p1[0] + self.label_gap * dx / n + self.label_offset[0]
        y = p1[1] + self.label_gap * dy / n + self.label_offset[1]
        anchor = self.label_anchor or ("start" if dx > 2 else "end" if dx < -2 else "middle")
        return (x, y), anchor

    def draw(self, cam: Projection, style: Style) -> List[str]:
        p0, p1 = _flat(self.start), _flat(self.end)
        out = []
        stop = p1
        if self.head:
            poly, stop = _head(p1, (p1[0] - p0[0], p1[1] - p0[1]), style)
            out.append(poly)
        out.insert(0, S.line(p0, stop, style.stroke, self.width or style.thin, dash=self.dash))
        if self.label:
            (x, y), anchor = self._label_point(style)
            out.append(S.text(x, y, self.label, style, anchor=anchor))
        return out

    def extent(self, cam: Projection, style: Style) -> List[Vec2]:
        out = [_flat(self.start), _flat(self.end)]
        if self.label:
            (x, y), _ = self._label_point(style)
            out += S.text_extent(x, y, self.label, style.font_size)
        return out


@dataclass
class Label2(Flat):
    at: Vec2 = (0.0, 0.0)
    text: str = ""
    offset: Vec2 = (0.0, 0.0)
    anchor: str = "middle"
    math: bool = True
    size: Optional[float] = None
    name: str = "label2"

    def _xy(self) -> Vec2:
        x, y = _flat(self.at)
        return (x + self.offset[0], y + self.offset[1])

    def draw(self, cam: Projection, style: Style) -> List[str]:
        x, y = self._xy()
        return [S.text(x, y, self.text, style, anchor=self.anchor, math=self.math, size=self.size)]

    def extent(self, cam: Projection, style: Style) -> List[Vec2]:
        x, y = self._xy()
        return S.text_extent(x, y, self.text, self.size or style.font_size)


@dataclass
class Dot2(Flat):
    at: Vec2 = (0.0, 0.0)
    radius: float = 2.2
    name: str = "dot2"

    def draw(self, cam: Projection, style: Style) -> List[str]:
        x, y = _flat(self.at)
        return [S.circle(x, y, self.radius, style.stroke)]

    def extent(self, cam: Projection, style: Style) -> List[Vec2]:
        x, y = _flat(self.at)
        return [(x - self.radius, y - self.radius), (x + self.radius, y + self.radius)]


def centre_line2(p0: Vec2, p1: Vec2, **kwargs) -> Poly2:
    """A dash-dot centre line, the drawing convention for an axis of symmetry."""
    kwargs.setdefault("width", 0.8)
    return Poly2(points=[p0, p1], dash="14 3 3 3", **kwargs)


@dataclass
class Capsule2(Flat):
    """Two circles joined by their common tangents — a link in a flat elevation or plan view.

    The joint circles are drawn complete over the body, which is how ISO 9787 Figure 4
    draws an arm in side view.
    """

    p0: Vec2 = (0.0, 0.0)
    r0: float = 1.0
    p1: Vec2 = (1.0, 0.0)
    r1: float = 1.0
    fill: Optional[str] = None
    joints: bool = True
    width: Optional[float] = None
    segments: int = 96
    name: str = "capsule2"

    def _samples(self) -> List[Vec2]:
        out = []
        for (cx, cy), r in ((self.p0, self.r0), (self.p1, self.r1)):
            for i in range(self.segments):
                t = 2.0 * math.pi * i / self.segments
                out.append((cx + r * math.cos(t), cy + r * math.sin(t)))
        return out

    def draw(self, cam: Projection, style: Style) -> List[str]:
        width = self.width or style.width
        out = [S.polygon(
            [_flat(p) for p in convex_hull(self._samples())],
            self.fill or style.surface, style.stroke, width,
        )]
        if self.joints:
            for (cx, cy), r in ((self.p0, self.r0), (self.p1, self.r1)):
                x, y = _flat((cx, cy))
                out.append(S.circle(x, y, r, None, style.stroke, width))
        return out

    def extent(self, cam: Projection, style: Style) -> List[Vec2]:
        return [_flat(p) for p in self._samples()]


def arc_path(center: Vec2, radius: float, start_deg: float, sweep_deg: float) -> str:
    """Path data for a circular arc, as cubic segments of at most 90 degrees each.

    Cubics are used rather than SVG's elliptical-arc command because they are exact for
    this purpose, render identically in every tool, and stay easy to drag around in a
    vector editor.
    """
    cx, cy = center
    steps = max(1, int(math.ceil(abs(sweep_deg) / 90.0)))
    delta = math.radians(sweep_deg) / steps
    k = 4.0 / 3.0 * math.tan(delta / 4.0)
    t = math.radians(start_deg)
    px, py = cx + radius * math.cos(t), cy + radius * math.sin(t)
    d = f"M {S.fmt(px)} {S.fmt(py)}"
    for _ in range(steps):
        t1 = t + delta
        qx, qy = cx + radius * math.cos(t1), cy + radius * math.sin(t1)
        c1 = (px - k * radius * math.sin(t), py + k * radius * math.cos(t))
        c2 = (qx + k * radius * math.sin(t1), qy - k * radius * math.cos(t1))
        d += (f" C {S.fmt(c1[0])} {S.fmt(c1[1])} {S.fmt(c2[0])} {S.fmt(c2[1])} "
              f"{S.fmt(qx)} {S.fmt(qy)}")
        t, px, py = t1, qx, qy
    return d


def arc2(center: Vec2, radius: float, start_deg: float, end_deg: float, **kwargs) -> Path2:
    """A circular arc in flat coordinates, swept anticlockwise from ``start_deg``."""
    sweep = (end_deg - start_deg) % 360.0 or 360.0
    cx, cy = center
    kwargs.setdefault("bbox", [(cx - radius, cy - radius), (cx + radius, cy + radius)])
    return Path2(d=arc_path(center, radius, start_deg, sweep), **kwargs)


def polar2(center: Vec2, radius: float, degrees: float) -> Vec2:
    """A point at an angle and radius from a flat centre — handy for annular envelopes."""
    return (center[0] + radius * math.cos(math.radians(degrees)),
            center[1] + radius * math.sin(math.radians(degrees)))
