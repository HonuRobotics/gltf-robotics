# coordinate-system-illustrations

A small drawing kit for standalone, editable line drawings of coordinate systems — the kind ISO 9787:2013 uses in its Figures 3 to 7. White solids with black outlines, coordinate triads drawn as three arrows from a named origin, and italic labels with subscripts. Output is plain SVG with no external dependencies, so a drawing drops into Sphinx, a Markdown note, a slide or a PR comment, and can be opened in Inkscape afterwards.

The five ISO figures are reproduced here as scene scripts, both as a check that the kit can do the job and as a starting point to copy. [`refs/ISO+9787-2013.pdf`](../../refs/ISO+9787-2013.pdf) holds the originals to compare against. The drawings are reproductions for our own use, not copies of the standard's artwork.

## Quick start

```bash
cd tools/coordinate-system-illustrations
python3 figures/fig06_mobile_platform.py     # writes out/fig06_mobile_platform.svg
make                                         # regenerates every figure
make png                                     # PNG previews alongside, for eyeballing
```

Nothing to install: pure Python 3, standard library only. `make png` is the one step that needs Inkscape, and only for previews.

## What is here

| path | what it is |
|---|---|
| `csi/` | the library — projection, shapes, style, SVG emission |
| `figures/fig03…fig07*.py` | the five ISO 9787 figures, one scene script each |
| `figures/usv_cat_frames.py` | a worked example that is not from the standard — a catamaran USV, the one to copy to start |
| `figures/usv_mono_frames.py` | the same three frames on a monohull, whose hull is drawn from panels rather than solids |
| `figures/rov_frames.py` | the same again on an ROV, plus a camera frame in the optical convention |
| `out/` | generated SVGs (and PNGs from `make png`, which are disposable) |

## How a figure is written

A figure is a Python script that builds a `Scene` and saves it. The scene holds a camera, a style, and a list of shapes:

```python
from csi import *

scene = Scene(camera=Camera(scale=90))
scene.add(Box(center=(0, 0, 0.15), size=(1.4, 1.0, 0.3), name="pedestal"))
scene.add(cylinder((0, 0, 0.3), (0, 0, 1.0), 0.18, name="column"))
scene.add(Frame(origin=(0, 0, 0), subscript="1", length=1.2, lengths={"z": 1.6}))
scene.save("out/example.svg")
```

World coordinates are right-handed with +Z up, matching ISO 9787 and REP 103. Units are yours; `Camera(scale=…)` sets drawing units per world unit, and the page sizes itself to whatever was drawn, so there is no viewBox to keep in step.

There is no hidden-line removal. Solids are filled opaque white and painted far to near, which is how these drawings read anyway — a nearer block simply hides what is behind it. Where the automatic ordering is wrong, or where a solid needs to sit in front of one it does not overlap in depth, pass `z=` to pin it: larger paints later. Frames, arrows, labels and leaders default to painting over everything, as annotation should.

## The vocabulary

Solids, in world coordinates:

| shape | for |
|---|---|
| `Box(center, size, axes=None)` | a block; `axes` tilts it, for a camera body or a canted sensor |
| `cylinder(p0, p1, radius)` | a column, a wrist, a lens barrel |
| `link(p0, r0, p1, r1, axis, thickness)` | an arm segment: two joint cylinders and a tapered body between them |
| `disc(center, normal, radius, thickness)` | a wheel, a flange |
| `Solid(circles=…, points=…)` | the general case — the silhouette is the hull of any set of 3-D circles and points, which is exact for a convex body and is what the four above are built from |
| `Poly(points, fill=…)` | a flat plate or panel given as a 3-D polygon |

Annotation, also in world coordinates but painted on top:

| shape | for |
|---|---|
| `Frame(origin, subscript, length, …)` | a whole coordinate system: three arrows, an origin dot, four labels |
| `Arrow(start, end, label=…)` | a single arrow — a motion, a direction, one loose axis |
| `Label(at, text, offset=…)` | text pinned to a world point and nudged in drawing units |
| `Leader(points, head=False)` | the thin line from a key numeral, or from one frame to the one it is referenced to |

Flat 2-D linework, in drawing units with y up, for plan and elevation views: `Poly2`, `rect2`, `Circle2`, `Capsule2`, `arc2`, `Path2`, `Arrow2`, `Label2`, `Dot2`, `centre_line2`, and `polar2` for laying out points around a centre. These ignore the camera, which is what makes a two-view drawing such as Figure 4 straightforward.

## Coordinate systems, the way ISO draws them

`Frame` takes a `subscript` and labels all four names from it: `subscript="0"` gives *O*₀, *X*₀, *Y*₀, *Z*₀. Point the axes anywhere with `directions` — a mechanical interface or a sensor frame is rarely axis-aligned — stretch one axis with `lengths`, and nudge a label clear of the geometry with `offsets` (drawing units, y down):

```python
Frame(
    origin=(0.15, 0.35, 2.30), subscript="m", length=0.55,
    directions={"x": (1, 0, 0), "y": (0, -1, 0), "z": (0, 0, -1)},
    lengths={"z": 0.62}, offsets={"z": (12, 6)},
    origin_offset=(6, -12), origin_anchor="start",
)
```

Label text uses `_` for a subscript: `X_1`, `O_m`, `C_w`, `Z_{p1}`. The base is set italic and the subscript upright, as in the standard. Pass `math=False` for plain text such as a key numeral or caption.

## Projections

`Camera(azimuth, elevation, scale)` is axonometric. The default (−60°, 20°) reproduces ISO Figures 3 and 5: +Z up the page, +Y to the upper right, +X to the lower right. Figure 6 uses (55°, 22°) instead, which is what puts the platform's forward direction to the lower left the way the standard draws it — spinning the azimuth is usually a better fix for a crowded drawing than moving the geometry.

`Oblique(receding, foreshortening, scale)` puts +Y across the page and +Z up it, and lets +X recede at an angle. True lengths survive on the two axes lying in the page. ISO Figure 7 is drawn this way, so `fig07` uses it.

`look_along("-x" | "-y" | "-z")` gives a flat elevation or plan when the drawing wants one.

## Adapting a figure

Copy one of the three vehicle examples — `figures/usv_cat_frames.py` is the simplest — and edit it. The pattern throughout is to name the interesting points once at the top of the file — joint centres, origins, deck heights — and build everything from those names, so moving a frame means changing one line rather than hunting through coordinates. Each shape takes a `name=`, which becomes the id of its group in the SVG; that is what makes the output navigable in Inkscape and in a diff.

Two habits worth keeping. Nudge labels with `offsets` in drawing units rather than by moving the geometry, so the drawing stays a true projection of the thing it depicts. And change `Style` rather than individual shapes when the whole figure needs a heavier pen or bigger type — Figure 4 is drawn in much larger units than the others and does exactly that.

## Editing the SVG directly

The output is plain, indented SVG: one `<g id="…">` per shape, ellipses written as `<ellipse>` rather than polygon soup, arcs as cubic segments with ordinary nodes, and text as `<text>` with real tspans. Moving a label or restyling a line in Inkscape works fine. Anything structural is better done in the scene script and regenerated, since a hand edit is lost the next time the script runs.

## Limits worth knowing

Occlusion is per-object, so two solids that interpenetrate will not cut each other correctly; split them or order them with `z=`. Curves are silhouettes only — there is no shading, and a cylinder's far rim is omitted rather than dashed. Text extents are estimated when the page is sized, so a very long label can sit closer to the edge than the margin suggests.
