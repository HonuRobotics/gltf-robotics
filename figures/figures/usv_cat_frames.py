"""Frames on a catamaran USV — an example that is not from the standard.

This is the one to copy when starting a new drawing. It uses the same vocabulary as the
ISO reproductions — hulls built from a Solid, a deck, a mast, and three coordinate
systems — and it follows REP 103 rather than ISO 9787, so +X is the bow, +Y to port and
+Z up. Its two companions draw the same three frames on a monohull and on an ROV.

Run:  python3 figures/usv_cat_frames.py
"""

import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))

from csi import *  # noqa: E402

HERE = pathlib.Path(__file__).resolve().parents[1]

HULL_Y = 0.52          # half the beam, centre to centre of the two pontoons
DECK_Z = 0.56
SENSOR = (0.15, 0.0, 1.12)

scene = Scene(
    camera=Camera(azimuth=55.0, elevation=22.0, scale=150),
    title="Frames on a catamaran USV",
    description="World, platform and sensor coordinate systems on a catamaran USV, REP 103.",
)


def pontoon(y: float, name: str) -> Solid:
    """A round hull with a pointed bow: two circles and the bow tip, hulled together."""
    axis = (1.0, 0.0, 0.0)
    return Solid(
        circles=[((-1.05, y, 0.24), (-1.0, 0.0, 0.0), 0.22),
                 ((0.70, y, 0.24), axis, 0.22)],
        points=[(1.32, y, 0.30)],
        z=-1.0 if y < 0 else 1.0, name=name,
    )


scene.add(pontoon(-HULL_Y, "pontoon-starboard"))
scene.add(
    Box(center=(0.0, 0.0, DECK_Z - 0.06), size=(1.75, 1.35, 0.12), name="deck", z=0.0),
    cylinder((0.15, 0.0, DECK_Z), (0.15, 0.0, 1.02), 0.045, z=0.5, name="mast"),
    Box(center=(0.15, 0.0, 1.08), size=(0.16, 0.30, 0.14), name="sensor", z=0.6),
)
scene.add(pontoon(HULL_Y, "pontoon-port"))

# Platform frame: +X is the bow, the convention REP 103 and ISO 9787 5.5 agree on.
scene.add(Frame(
    origin=(0.0, 0.0, DECK_Z), subscript="p", length=0.95, lengths={"z": 0.75},
    offsets={"x": (-4.0, 6.0), "y": (2.0, 2.0)},
    origin_offset=(-6.0, -13.0), origin_anchor="end", name="platform-frame",
))

# Sensor frame, mounted on the mast and rotated to look forward and down.
scene.add(Frame(
    origin=SENSOR, subscript="s", length=0.42,
    directions={"x": (0.94, 0.0, -0.34), "y": (0.0, 1.0, 0.0), "z": (0.34, 0.0, 0.94)},
    offsets={"y": (4.0, -8.0)},
    origin_offset=(-17.0, -5.0), origin_anchor="end", name="sensor-frame",
))

# World frame, standing free alongside.
scene.add(Frame(
    origin=(2.3, -0.4, 0.15), subscript="0", length=0.8,
    origin_offset=(-6.0, -12.0), origin_anchor="end", name="world-frame",
))

if __name__ == "__main__":
    scene.save(str(HERE / "out" / "usv_cat_frames.svg"))
