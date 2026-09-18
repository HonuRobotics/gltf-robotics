"""Small 3-D vector helpers and the 2-D convex hull used for solid silhouettes.

Points are plain ``(x, y, z)`` tuples of floats; nothing here needs numpy.
"""

from __future__ import annotations

import math
from typing import Iterable, List, Sequence, Tuple

Vec3 = Tuple[float, float, float]
Vec2 = Tuple[float, float]


def add(a: Vec3, b: Vec3) -> Vec3:
    return (a[0] + b[0], a[1] + b[1], a[2] + b[2])


def sub(a: Vec3, b: Vec3) -> Vec3:
    return (a[0] - b[0], a[1] - b[1], a[2] - b[2])


def mul(a: Vec3, s: float) -> Vec3:
    return (a[0] * s, a[1] * s, a[2] * s)


def dot(a: Vec3, b: Vec3) -> float:
    return a[0] * b[0] + a[1] * b[1] + a[2] * b[2]


def cross(a: Vec3, b: Vec3) -> Vec3:
    return (
        a[1] * b[2] - a[2] * b[1],
        a[2] * b[0] - a[0] * b[2],
        a[0] * b[1] - a[1] * b[0],
    )


def length(a: Vec3) -> float:
    return math.sqrt(dot(a, a))


def unit(a: Vec3) -> Vec3:
    n = length(a)
    if n == 0.0:
        raise ValueError("cannot normalise a zero-length vector")
    return mul(a, 1.0 / n)


def lerp(a: Vec3, b: Vec3, t: float) -> Vec3:
    return add(mul(a, 1.0 - t), mul(b, t))


def centroid(points: Sequence[Vec3]) -> Vec3:
    n = float(len(points))
    return (
        sum(p[0] for p in points) / n,
        sum(p[1] for p in points) / n,
        sum(p[2] for p in points) / n,
    )


def basis_for(normal: Vec3) -> Tuple[Vec3, Vec3]:
    """Return two orthonormal vectors spanning the plane perpendicular to ``normal``."""
    n = unit(normal)
    seed = (0.0, 0.0, 1.0) if abs(n[2]) < 0.9 else (1.0, 0.0, 0.0)
    e1 = unit(cross(seed, n))
    e2 = cross(n, e1)
    return e1, e2


def circle_points(center: Vec3, normal: Vec3, radius: float, segments: int = 64) -> List[Vec3]:
    """Sample a circle lying in the plane through ``center`` with the given ``normal``."""
    e1, e2 = basis_for(normal)
    pts = []
    for i in range(segments):
        t = 2.0 * math.pi * i / segments
        pts.append(add(center, add(mul(e1, radius * math.cos(t)), mul(e2, radius * math.sin(t)))))
    return pts


def convex_hull(points: Iterable[Vec2]) -> List[Vec2]:
    """Andrew's monotone chain hull. Returns CCW order in a y-up sense."""
    pts = sorted(set((round(x, 6), round(y, 6)) for x, y in points))
    if len(pts) <= 2:
        return pts

    def half(seq):
        out: List[Vec2] = []
        for p in seq:
            while len(out) >= 2:
                (x1, y1), (x2, y2) = out[-2], out[-1]
                if (x2 - x1) * (p[1] - y1) - (y2 - y1) * (p[0] - x1) <= 0:
                    out.pop()
                else:
                    break
            out.append(p)
        return out

    return half(pts)[:-1] + half(reversed(pts))[:-1]
