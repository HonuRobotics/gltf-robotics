"""Frames on an ROV — an example that is not from the standard.

The vehicle is deliberately a plain box: an ROV's body frame is referenced to the
vehicle, not to any feature of its shape, so the drawing has nothing to say about the
fairing. The same three coordinate systems as the two USV examples, REP 103 throughout —
+X forward, +Y to port, +Z up — with the camera frame taking the place of the mast
sensor, looking forward along the vehicle.

Run:  python3 figures/rov_frames.py
"""

import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))

from csi import *  # noqa: E402

HERE = pathlib.Path(__file__).resolve().parents[1]

BODY = (1.30, 0.86, 0.62)      # length, beam, height of the box
CENTRE = (0.0, 0.0, 0.55)      # centre of the box, and the origin of the body frame
CAMERA = (BODY[0] / 2.0, 0.26, 0.40)     # low on the forward face, off the centreline
LENS = (CAMERA[0] + 0.18, CAMERA[1], CAMERA[2])

scene = Scene(
    camera=Camera(azimuth=55.0, elevation=22.0, scale=150),
    title="Frames on an ROV",
    description="World, body and camera coordinate systems on an ROV, REP 103.",
)

scene.add(Box(center=CENTRE, size=BODY, name="body"))

# The camera, on the forward face and looking out along +X.
scene.add(cylinder(CAMERA, LENS, 0.10, name="camera-barrel"))

# Body frame, at the centre of the vehicle rather than on any surface of it.
scene.add(Frame(
    origin=CENTRE, subscript="b", length=1.00, lengths={"x": 1.38, "z": 0.85},
    offsets={"x": (-4.0, -8.0), "y": (2.0, 2.0)},
    origin_offset=(-7.0, -12.0), origin_anchor="end", name="body-frame",
))

# Camera frame, in the optical convention REP 103 gives for cameras: +Zc out of the lens,
# +Xc to the right of the image, +Yc down it. It is a rotation of the body frame, which is
# the whole reason a vehicle carries both.
scene.add(Frame(
    origin=LENS, subscript="c", length=0.46, lengths={"x": 0.38},
    directions={"x": (0.0, -1.0, 0.0), "y": (0.0, 0.0, -1.0), "z": (1.0, 0.0, 0.0)},
    offsets={"x": (0.0, -8.0), "y": (2.0, 6.0), "z": (-4.0, 10.0)},
    origin_offset=(8.0, -14.0), origin_anchor="start", name="camera-frame",
))

# World frame, standing free alongside.
scene.add(Frame(
    origin=(2.0, -0.5, 0.15), subscript="0", length=0.8,
    origin_offset=(-6.0, -12.0), origin_anchor="end", name="world-frame",
))

if __name__ == "__main__":
    scene.save(str(HERE / "out" / "rov_frames.svg"))
