"""SVG emission: number formatting, elements, and ISO-style italic-with-subscript type."""

from __future__ import annotations

import re
from typing import Iterable, List, Optional

from .geom import Vec2


def fmt(value: float) -> str:
    s = f"{value:.2f}".rstrip("0").rstrip(".")
    return "0" if s in ("-0", "") else s


def pts(points: Iterable[Vec2]) -> str:
    return " ".join(f"{fmt(x)},{fmt(y)}" for x, y in points)


def esc(text: str) -> str:
    return text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def attrs(**kwargs) -> str:
    out = []
    for key, value in kwargs.items():
        if value is None:
            continue
        name = key.rstrip("_").replace("__", ":").replace("_", "-")
        out.append(f'{name}="{value}"')
    return " ".join(out)


def polygon(points, fill, stroke, width, dash=None, closed=True, **extra) -> str:
    tag = "polygon" if closed else "polyline"
    return f"<{tag} points=\"{pts(points)}\" " + attrs(
        fill=fill or "none",
        stroke=stroke,
        stroke_width=fmt(width),
        stroke_dasharray=dash,
        stroke_linejoin="round",
        **extra,
    ) + "/>"


def line(p0: Vec2, p1: Vec2, stroke, width, dash=None, **extra) -> str:
    return "<line " + attrs(
        x1=fmt(p0[0]), y1=fmt(p0[1]), x2=fmt(p1[0]), y2=fmt(p1[1]),
        stroke=stroke, stroke_width=fmt(width), stroke_dasharray=dash,
        stroke_linecap="round", **extra,
    ) + "/>"


def ellipse(cx, cy, rx, ry, rot, fill, stroke, width, **extra) -> str:
    transform = None if abs(rot) < 1e-6 else f"rotate({fmt(rot)} {fmt(cx)} {fmt(cy)})"
    return "<ellipse " + attrs(
        cx=fmt(cx), cy=fmt(cy), rx=fmt(rx), ry=fmt(ry), transform=transform,
        fill=fill or "none", stroke=stroke, stroke_width=fmt(width), **extra,
    ) + "/>"


def circle(cx, cy, r, fill, stroke=None, width=0.0, **extra) -> str:
    return "<circle " + attrs(
        cx=fmt(cx), cy=fmt(cy), r=fmt(r), fill=fill or "none",
        stroke=stroke, stroke_width=fmt(width) if stroke else None, **extra,
    ) + "/>"


def path(d: str, fill, stroke, width, dash=None, **extra) -> str:
    return "<path " + attrs(
        d=d, fill=fill or "none", stroke=stroke, stroke_width=fmt(width),
        stroke_dasharray=dash, stroke_linejoin="round", **extra,
    ) + "/>"


_MATH = re.compile(r"^([^_]+)(?:_(?:\{(.*)\}|(.+)))?$")


def math_spans(text: str) -> str:
    """Render ``"X_0"``, ``"O_m"``, ``"C_{w1}"`` as an italic letter with an upright subscript.

    Anything that does not look like a symbol with a subscript is passed through italic,
    which is what ISO uses for a bare axis or point name.
    """
    match = _MATH.match(text)
    if not match:
        return f'<tspan font-style="italic">{esc(text)}</tspan>'
    base, braced, bare = match.groups()
    sub = braced if braced is not None else bare
    out = f'<tspan font-style="italic">{esc(base)}</tspan>'
    if sub:
        out += f'<tspan font-size="72%" dy="0.26em">{esc(sub)}</tspan>'
    return out


def text(
    x: float,
    y: float,
    content: str,
    style,
    anchor: str = "middle",
    math: bool = True,
    size: Optional[float] = None,
    fill: Optional[str] = None,
    **extra,
) -> str:
    body = math_spans(content) if math else esc(content)
    return (
        "<text " + attrs(
            x=fmt(x), y=fmt(y), font_family=style.font_family,
            font_size=fmt(size or style.font_size), fill=fill or style.stroke,
            text_anchor=anchor, dominant_baseline="central", **extra,
        ) + f">{body}</text>"
    )


def text_extent(x: float, y: float, content: str, size: float) -> List[Vec2]:
    """A rough box for a label, used only to size the drawing's viewBox."""
    width = 0.62 * size * max(1, len(content))
    return [(x - width, y - size), (x + width, y + size)]
