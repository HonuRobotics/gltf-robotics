"""ISO 9787:2013 Figure 7 — Coordinate systems in object handling.

All seven coordinate systems of Clause 5 in one scene, with the thin lines that carry
each one back to the one it is referenced to. Drawn in the oblique projection the
standard uses here, so +Y lies across the page and +Z up it.

Run:  python3 figures/fig07_object_handling.py
"""

import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))

from csi import *  # noqa: E402

HERE = pathlib.Path(__file__).resolve().parents[1]

SHADE = "#d9d9d9"      # a cut face, where the drawing breaks off the rest of the machine

# --- the seven origins ----------------------------------------------------------------
O_WORLD = (2.6, -4.4, 0.0)
O_BASE = (1.3, -2.7, 0.40)
O_INTERFACE = (0.15, 0.35, 2.30)
O_TOOL = (0.15, 0.35, 1.30)
O_TASK = (2.45, 0.0, 0.45)
O_OBJECT = (2.0, 1.20, 1.05)
O_CAMERA = (-0.9, 3.5, 2.30)

# A mounting frame and a tool frame both look down their own +Z into the work.
DOWN_X, DOWN_Y, DOWN_Z = (1.0, 0.0, 0.0), (0.0, -1.0, 0.0), (0.0, 0.0, -1.0)

# The camera is tilted, so its frame is given outright.
XC, YC, ZC = (0.0, 1.0, 0.0), (0.423, 0.0, 0.906), (0.906, 0.0, -0.423)

scene = Scene(
    camera=Oblique(receding=40.0, foreshortening=0.62, scale=92),
    style=Style(width=1.5),
    title="ISO 9787 Figure 7 - Coordinate systems in object handling",
    description="World, base, mechanical interface, tool, task, object and camera coordinate systems.",
)

# --- 2  the robot base ----------------------------------------------------------------
scene.add(
    Box(center=(1.3, -2.7, 0.20), size=(1.4, 1.9, 0.40), name="pedestal"),
    cylinder((1.3, -2.7, 0.40), (1.3, -2.7, 1.30), 0.34, rim_fill=SHADE, name="base-column"),
)

# --- 3, 9  the mechanical interface and the gripper it carries -------------------------
scene.add(
    cylinder(O_INTERFACE, (0.15, 0.35, 3.25), 0.30, rim_fill=SHADE, name="wrist"),
    Box(center=(0.15, 0.35, 2.02), size=(0.80, 1.00, 0.56), name="gripper-body"),
    Box(center=(0.15, -0.05, 1.45), size=(0.50, 0.20, 0.58), name="finger-left"),
    Box(center=(0.15, 0.75, 1.45), size=(0.50, 0.20, 0.58), name="finger-right"),
)

# --- 5, 6  the task surface and the object on it ---------------------------------------
scene.add(
    Box(center=(1.30, 1.60, 0.35), size=(2.30, 3.20, 0.20), name="task-surface"),
    Box(center=(1.55, 1.75, 0.75), size=(0.90, 1.10, 0.60), name="object"),
)

# --- 7  the camera ---------------------------------------------------------------------
CAMERA_BODY = add(O_CAMERA, mul(ZC, -0.78))
scene.add(
    Box(center=CAMERA_BODY, size=(0.60, 0.68, 0.62), axes=(XC, YC, ZC), name="camera-body"),
    cylinder(add(CAMERA_BODY, mul(ZC, 0.20)), add(CAMERA_BODY, mul(ZC, 0.62)), 0.17,
             name="camera-lens"),
)

# --- the chain: each coordinate system is referenced to the one before it ---------------
scene.add(
    Leader(points=[O_WORLD, O_BASE], name="world-to-base"),
    Leader(points=[O_BASE, O_TOOL], name="base-to-tool"),
    Leader(points=[O_TOOL, O_OBJECT], name="tool-to-object"),
    Leader(points=[O_WORLD, O_TASK], name="world-to-task"),
)

# --- the coordinate systems ------------------------------------------------------------
scene.add(
    Frame(origin=O_WORLD, subscript="0", length=0.95,
          origin_offset=(-10.0, 4.0), origin_anchor="end", name="world-frame"),
    Frame(origin=O_BASE, subscript="1", length=0.95, lengths={"z": 1.55},
          origin_offset=(-11.0, 2.0), origin_anchor="end", name="base-frame"),
    Frame(origin=O_INTERFACE, subscript="m", length=0.55, lengths={"z": 0.62},
          directions={"x": DOWN_X, "y": DOWN_Y, "z": DOWN_Z},
          offsets={"z": (12.0, 6.0)}, origin_offset=(6.0, -12.0), origin_anchor="start",
          name="interface-frame"),
    Frame(origin=O_TOOL, subscript="t", length=0.55, lengths={"z": 0.42},
          directions={"x": DOWN_X, "y": DOWN_Y, "z": DOWN_Z},
          offsets={"z": (13.0, 4.0)}, origin_offset=(-4.0, -13.0), origin_anchor="end",
          name="tool-frame"),
    Frame(origin=O_TASK, subscript="k", length=0.85, lengths={"y": 1.55},
          origin_offset=(-6.0, 13.0), origin_anchor="end", name="task-frame"),
    Frame(origin=O_OBJECT, subscript="j", length=0.62, lengths={"z": 0.62},
          offsets={"z": (-11.0, -2.0)}, origin_offset=(2.0, -13.0), origin_anchor="start",
          name="object-frame"),
    Frame(origin=O_CAMERA, subscript="c", length=0.85,
          directions={"x": XC, "y": YC, "z": ZC},
          origin_offset=(-12.0, 14.0), origin_anchor="end", name="camera-frame"),
)

# --- key numerals ----------------------------------------------------------------------
KEY = [
    ("1", O_WORLD, (26.0, 24.0), "world coordinate system"),
    ("2", (1.3, -2.7, 1.45), (-14.0, -14.0), "base coordinate system"),
    ("3", (0.15, 0.35, 3.30), (-6.0, -18.0), "mechanical interface coordinate system"),
    ("4", O_TOOL, (-62.0, 34.0), "tool coordinate system"),
    ("5", O_TASK, (28.0, 30.0), "task coordinate system"),
    ("6", O_OBJECT, (38.0, -28.0), "object coordinate system"),
    ("7", CAMERA_BODY, (-10.0, -46.0), "camera coordinate system"),
    ("8", O_TOOL, (30.0, 2.0), "TCP"),
    ("9", (0.15, -0.15, 1.74), (-30.0, 16.0), "gripper"),
]
for numeral, at, offset, _ in KEY:
    scene.add(Label(at=at, text=numeral, offset=offset, math=False,
                    size=scene.style.font_size * 1.5, name=f"key-{numeral}"))

# --- the key itself, set below the drawing ----------------------------------------------
left, _, _, bottom = scene.bounds()
line_height = scene.style.font_size * 1.55
scene.add(Label2(at=(left, -(bottom + line_height * 1.6)), text="Key", math=False,
                 anchor="start", name="key-heading"))
for index, (numeral, _, _, caption) in enumerate(KEY):
    y = -(bottom + line_height * (2.9 + index))
    scene.add(
        Label2(at=(left, y), text=numeral, math=False, anchor="start", name=f"key-n{numeral}"),
        Label2(at=(left + 34.0, y), text=caption, math=False, anchor="start",
               name=f"key-t{numeral}"),
    )

if __name__ == "__main__":
    scene.save(str(HERE / "out" / "fig07_object_handling.svg"))
