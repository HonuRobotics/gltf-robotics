"""ISO 9787:2013 Figure 4 — Examples of robot working space.

Two orthographic views of the same robot: an elevation over a plan. Both are drawn flat,
in drawing units with y up, because a plan and an elevation want graph paper rather than
a camera. Cw is the centre of the working space, the point +X1 is defined to pass through.

Run:  python3 figures/fig04_working_space.py
"""

import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))

from csi import *  # noqa: E402
from csi.shapes import arc_path  # noqa: E402

HERE = pathlib.Path(__file__).resolve().parents[1]

# --- elevation ------------------------------------------------------------------------
SHOULDER = (0.0, 200.0)
WRIST = (250.0, 262.0)
CW_ELEVATION = (302.0, 150.0)

# --- plan ------------------------------------------------------------------------------
PLAN = (0.0, -470.0)                 # centre of the plan view
R_OUTER, R_INNER = 215.0, 118.0      # working space envelope
GAP_OUTER, GAP_INNER = 26.0, 13.0    # half-angles of the unreachable wedge, at each radius

scene = Scene(
    style=Style(width=1.8, thin=1.2, font_size=26.0, arrow_length=16.0, arrow_width=6.0),
    title="ISO 9787 Figure 4 - Examples of robot working space",
    description="Elevation and plan of a robot working space, with the base coordinate system.",
)

# ===== elevation view =================================================================
scene.add(
    centre_line2((0.0, -14.0), (0.0, SHOULDER[1] + 40.0), z=10.0, name="column-centre"),
    centre_line2((-38.0, 191.0), (292.0, 272.0), z=10.0, name="arm-centre"),
    centre_line2((-62.0, SHOULDER[1]), (48.0, SHOULDER[1]), z=10.0, name="shoulder-axis"),
    centre_line2((WRIST[0], WRIST[1] - 42.0), (WRIST[0], WRIST[1] + 42.0), z=10.0, name="wrist-axis"),
)
scene.add(
    Capsule2(p0=(0.0, 62.0), r0=30.0, p1=SHOULDER, r1=32.0, name="column"),
    Capsule2(p0=SHOULDER, r0=32.0, p1=WRIST, r1=22.0, name="upper-arm"),
    rect2(WRIST[0] + 18.0, WRIST[1] - 6.0, 30.0, 14.0, fill="#ffffff", name="wrist-flange"),
    rect2(WRIST[0] + 48.0, WRIST[1] - 14.0, 8.0, 30.0, fill="#ffffff", name="tool"),
    rect2(-58.0, 0.0, 116.0, 46.0, fill="#ffffff", name="pedestal"),
)

# The working space: a free outline, broken on the side where it runs into the robot.
BLOB = (
    "M 236 248 C 270 262 322 258 342 236 C 366 210 360 150 352 118 "
    "C 344 84 322 46 298 42 C 278 38 266 58 258 74 "
    # the break line, drawn as a run of small waves
    "C 250 92 240 96 246 112 C 252 128 230 128 236 144 "
    "C 242 160 220 162 228 178 C 236 194 216 200 224 216 C 230 230 226 240 236 248 Z"
)
scene.add(Path2(d=BLOB, bbox=[(216.0, 38.0), (366.0, 262.0)], name="working-space"))
scene.add(
    Circle2(center=CW_ELEVATION, radius=4.0, width=1.2, name="cw-elevation"),
    Label2(at=CW_ELEVATION, text="C_w", offset=(-6.0, -26.0), name="cw-elevation-label"),
)

scene.add(
    Arrow2(start=(0.0, 0.0), end=(238.0, 0.0), label="X_1", name="x1-elevation"),
    Arrow2(start=(0.0, SHOULDER[1] + 30.0), end=(0.0, 352.0), label="Z_1",
           label_offset=(2.0, 0.0), label_anchor="middle", name="z1-elevation"),
    Dot2(at=(0.0, 0.0), radius=3.6, name="o1-elevation"),
    Label2(at=(0.0, 0.0), text="Y_1", offset=(16.0, -22.0), anchor="start",
           name="y1-elevation"),
)

# ===== plan view ======================================================================
scene.add(
    centre_line2((PLAN[0] - R_OUTER - 60.0, PLAN[1]), (PLAN[0] + R_OUTER + 60.0, PLAN[1]),
                 z=10.0, name="plan-centre-h"),
    centre_line2((PLAN[0], PLAN[1] - R_OUTER - 60.0), (PLAN[0], PLAN[1] + R_OUTER + 60.0),
                 z=10.0, name="plan-centre-v"),
)

# Working space envelope: an annulus with a wedge the arm cannot reach.
scene.add(
    Path2(d=arc_path(PLAN, R_OUTER, 180.0 + GAP_OUTER, 360.0 - 2.0 * GAP_OUTER),
          bbox=[(PLAN[0] - R_OUTER, PLAN[1] - R_OUTER), (PLAN[0] + R_OUTER, PLAN[1] + R_OUTER)],
          name="envelope-outer"),
    Circle2(center=PLAN, radius=R_INNER, name="envelope-inner"),
    Poly2(points=[polar2(PLAN, R_OUTER, 180.0 - GAP_OUTER), polar2(PLAN, R_INNER, 180.0 - GAP_INNER)],
          name="envelope-gap-upper"),
    Poly2(points=[polar2(PLAN, R_OUTER, 180.0 + GAP_OUTER), polar2(PLAN, R_INNER, 180.0 + GAP_INNER)],
          name="envelope-gap-lower"),
)

# The robot itself, seen from above: base, arm, tool.
scene.add(
    rect2(PLAN[0] - 62.0, PLAN[1] - 68.0, 124.0, 124.0, fill="#ffffff", name="plan-base"),
    rect2(PLAN[0] - 40.0, PLAN[1] - 26.0, 62.0, 52.0, fill="#ffffff", name="plan-shoulder"),
    rect2(PLAN[0] - 28.0, PLAN[1] - 14.0, 190.0, 28.0, fill="#ffffff", name="plan-arm"),
    rect2(PLAN[0] + 150.0, PLAN[1] - 18.0, 44.0, 36.0, fill="#ffffff", name="plan-wrist"),
    rect2(PLAN[0] + 194.0, PLAN[1] - 12.0, 10.0, 24.0, fill="#ffffff", name="plan-tool"),
    Dot2(at=PLAN, radius=3.6, name="o1-plan"),
)
scene.add(
    Circle2(center=(PLAN[0] + R_OUTER, PLAN[1]), radius=4.0, width=1.2, name="cw-plan"),
    Label2(at=(PLAN[0] + R_OUTER, PLAN[1]), text="C_w", offset=(-16.0, -34.0), name="cw-plan-label"),
    Label2(at=PLAN, text="Z_1", offset=(-52.0, 46.0), name="z1-plan"),
    Arrow2(start=(PLAN[0], PLAN[1] + R_OUTER + 12.0), end=(PLAN[0], PLAN[1] + R_OUTER + 56.0),
           label="Y_1", label_offset=(12.0, 6.0), label_anchor="start", name="y1-plan"),
    Arrow2(start=(PLAN[0] + R_OUTER + 40.0, PLAN[1]), end=(PLAN[0] + R_OUTER + 110.0, PLAN[1]),
           label="X_1", name="x1-plan"),
)

if __name__ == "__main__":
    scene.save(str(HERE / "out" / "fig04_working_space.svg"))
