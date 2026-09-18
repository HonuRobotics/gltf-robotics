"""ISO 9787:2013 Figure 5 — Example of tool coordinate system.

A planar grasp-type gripper. The origin Ot is the tool centre point; +Xt runs in the
direction of the tool and +Yt lies on the moving plane of the fingers, which is what the
double-headed arrow is showing.

Run:  python3 figures/fig05_tool_frame.py
"""

import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))

from csi import *  # noqa: E402

HERE = pathlib.Path(__file__).resolve().parents[1]

# Fingers face each other across world X, which is also the direction they travel.
GAP = 0.95           # half the opening between the two fingers
FINGER_LENGTH = 2.3  # along world Y, the direction the arm comes from
FINGER_HEIGHT = 1.0

scene = Scene(
    camera=Camera(scale=96),
    style=Style(width=1.6),
    title="ISO 9787 Figure 5 - Example of tool coordinate system",
    description="Tool coordinate system on a planar grasp-type gripper.",
)


def finger(x: float, name: str) -> Poly:
    """One gripper plate: a rectangle in the plane x = const."""
    y0, y1 = -0.75, -0.75 + FINGER_LENGTH
    z0, z1 = -FINGER_HEIGHT / 2.0, FINGER_HEIGHT / 2.0
    return Poly(
        points=[(x, y0, z0), (x, y1, z0), (x, y1, z1), (x, y0, z1)],
        fill="#ffffff", name=name,
    )


scene.add(finger(-GAP, "finger-far"), finger(GAP, "finger-near"))

# The arm the gripper is mounted on, cut off by a break line.
scene.add(Box(center=(0.0, 2.05, 0.30), size=(0.55, 1.9, 0.55), name="arm-stub", z=-5.0))
scene.add(Poly(
    points=[(-0.275, 2.72, 0.575), (-0.09, 2.86, 0.575), (0.09, 2.74, 0.575),
            (0.275, 2.88, 0.575), (0.275, 2.74, 0.40), (0.275, 2.88, 0.22),
            (0.275, 2.74, 0.04)],
    closed=False, width=1.0, name="arm-break",
))

# The fingers travel along +/- Xt.
scene.add(
    Arrow(start=(0.0, -0.50, 0.62), end=(-0.55, -0.50, 0.62), width=1.3, name="travel-far"),
    Arrow(start=(0.0, -0.50, 0.62), end=(0.55, -0.50, 0.62), width=1.3, name="travel-near"),
)

# The tool coordinate system: +Xt down the tool, +Yt on the moving plane of the fingers.
scene.add(Frame(
    origin=(0.0, 0.0, 0.0), subscript="t", length=1.35,
    directions={"x": (0.0, 0.0, -1.0), "y": (1.0, 0.0, 0.0), "z": (0.0, -1.0, 0.0)},
    origin_offset=(-9.0, -11.0), origin_anchor="end",
    name="tool-frame",
))

if __name__ == "__main__":
    scene.save(str(HERE / "out" / "fig05_tool_frame.svg"))
