"""ISO 9787:2013 Figure 6 — Example of mobile platform coordinate system.

+Xp is the forward direction of the platform and +Zp is up, which is REP 103 exactly.
The world coordinate system stands beside it, unattached to anything.

The camera looks from the other quarter than Figure 3, so that forward reads to the
lower left, the way the standard draws it.

Run:  python3 figures/fig06_mobile_platform.py
"""

import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))

from csi import *  # noqa: E402

HERE = pathlib.Path(__file__).resolve().parents[1]

DECK_Z = 0.95                 # top of the platform, where Op sits
WHEEL_R, WHEEL_T = 0.42, 0.20
WHEEL_X, WHEEL_Y = 1.02, 0.80

scene = Scene(
    camera=Camera(azimuth=55.0, elevation=22.0, scale=118),
    title="ISO 9787 Figure 6 - Example of mobile platform coordinate system",
    description="Mobile platform coordinate system, with the world coordinate system alongside.",
)

# Wheels on the far side, then the body, then the wheels on the near side.
for sx in (-1, 1):
    scene.add(disc(
        (sx * WHEEL_X, -WHEEL_Y, WHEEL_R), (0.0, 1.0, 0.0), WHEEL_R, WHEEL_T,
        rim_fill="#d9d9d9", z=-1.0, name=f"wheel-far-{'front' if sx > 0 else 'rear'}",
    ))

scene.add(
    Box(center=(0.0, 0.0, 0.42), size=(1.7, 1.1, 0.5), name="chassis", z=0.0),
    Box(center=(0.0, 0.0, DECK_Z - 0.14), size=(2.6, 1.5, 0.28), name="deck", z=0.5),
)

for sx in (-1, 1):
    scene.add(disc(
        (sx * WHEEL_X, WHEEL_Y, WHEEL_R), (0.0, 1.0, 0.0), WHEEL_R, WHEEL_T,
        rim_fill="#d9d9d9", z=1.0, name=f"wheel-near-{'front' if sx > 0 else 'rear'}",
    ))

# Mobile platform coordinate system, on the deck.
scene.add(Frame(
    origin=(0.0, 0.0, DECK_Z), subscript="p", length=0.72, lengths={"x": 1.05, "z": 1.5},
    offsets={"x": (-2.0, -4.0), "y": (2.0, -4.0)},
    origin_offset=(-4.0, -14.0), origin_anchor="end",
    name="platform-frame",
))

# World coordinate system, standing free.
scene.add(Frame(
    origin=(3.3, -0.5, 0.55), subscript="0", length=1.15,
    origin_offset=(-6.0, -14.0), origin_anchor="end",
    name="world-frame",
))

if __name__ == "__main__":
    scene.save(str(HERE / "out" / "fig06_mobile_platform.svg"))
