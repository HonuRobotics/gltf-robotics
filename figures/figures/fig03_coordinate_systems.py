"""ISO 9787:2013 Figure 3 — Examples of coordinate systems.

A world coordinate system standing free, and an articulated robot carrying its base
coordinate system (O1) and its mechanical interface coordinate system (Om).

Run:  python3 figures/fig03_coordinate_systems.py
"""

import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))

from csi import *  # noqa: E402

HERE = pathlib.Path(__file__).resolve().parents[1]

# --- the arm, as a chain of joint centres -------------------------------------------
# The arm works in the world YZ plane, so every joint axis is parallel to world X.
SHOULDER = (0.0, -0.15, 0.85)
ELBOW = (0.0, -0.75, 2.05)
WRIST = (0.0, 0.95, 2.70)
FLANGE = (0.0, 1.28, 2.82)          # centre of the mechanical interface, Om
JOINT_AXIS = (1.0, 0.0, 0.0)

# --- the mechanical interface triad --------------------------------------------------
# A right-handed set chosen so the flange sits at a working angle: +Zm away from the
# interface, +Xm up and outboard. Replace these three with your own flange orientation.
XM = (0.588, -0.158, 0.793)
YM = (-0.259, -0.966, 0.0)
ZM = (0.766, -0.205, -0.609)

scene = Scene(
    camera=Camera(scale=86),
    title="ISO 9787 Figure 3 - Examples of coordinate systems",
    description="World, base and mechanical interface coordinate systems on an articulated robot.",
)

# --- robot ---------------------------------------------------------------------------
scene.add(
    link(SHOULDER, 0.30, ELBOW, 0.27, JOINT_AXIS, 0.42, name="upper-arm"),
    link(ELBOW, 0.27, WRIST, 0.21, JOINT_AXIS, 0.38, name="forearm"),
    cylinder(WRIST, FLANGE, 0.15, name="wrist"),
    cylinder((0.0, -0.15, 0.35), SHOULDER, 0.26, name="column"),
)
scene.add(Box(center=(0.0, 0.0, 0.28), size=(1.5, 2.1, 0.55), name="pedestal", z=5.0))

# --- base coordinate system, referenced to the base mounting surface ------------------
scene.add(Frame(
    origin=(0.0, 0.0, 0.0), subscript="1", length=1.6,
    lengths={"y": 2.45, "z": 3.55},
    offsets={"x": (2.0, 4.0), "y": (2.0, -2.0)},
    origin_offset=(-6.0, 12.0), origin_anchor="end",
    name="base-frame",
))
# The base Z axis is drawn from below the mounting surface, as ISO draws it.
scene.add(Poly(points=[(0.0, 0.0, -0.22), (0.0, 0.0, 0.0)], closed=False,
               width=0.9, name="base-z-stub"))

# --- mechanical interface coordinate system ------------------------------------------
scene.add(Frame(
    origin=FLANGE, subscript="m", length=0.95,
    directions={"x": XM, "y": YM, "z": ZM},
    lengths={"y": 0.72}, offsets={"y": (-1.0, 3.0)},
    origin_offset=(14.0, -6.0), origin_anchor="start",
    name="interface-frame",
))

# --- world coordinate system, standing free to the left ------------------------------
scene.add(Frame(
    origin=(-0.35, -4.6, 0.75), subscript="0", length=1.35,
    origin_offset=(-14.0, 6.0), origin_anchor="end",
    name="world-frame",
))

if __name__ == "__main__":
    scene.save(str(HERE / "out" / "fig03_coordinate_systems.svg"))
