"""Frames on a monohull USV — an example that is not from the standard.

The same three coordinate systems as usv_cat_frames.py on a single displacement hull:
a world coordinate system standing free, the platform frame on the deck, and a sensor
frame on the mast. REP 103 throughout — +X is the bow, +Y to port, +Z up.

Run:  python3 figures/usv_mono_frames.py
"""

import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))

from csi import *  # noqa: E402

HERE = pathlib.Path(__file__).resolve().parents[1]

BOW, STERN = 1.30, -0.98      # x of the stem and of the transom
DECK_Z = 0.62                 # deck at midship; the sheer rises forward to the stem
SENSOR = (0.30, 0.0, 1.18)

# The hull is drawn as panels between two lines running bow to stern: the sheer, where
# topside meets deck, and the chine, where topside meets bottom. Naming the two lines
# once keeps the deck, the topsides and the transom in step.
SHEER = [(STERN, 0.44, 0.58), (0.35, 0.44, DECK_Z), (BOW, 0.0, 0.76)]
CHINE = [(STERN, 0.24, 0.16), (0.40, 0.24, 0.12), (BOW, 0.0, 0.60)]


def mirror(points):
    """The starboard copy of a line given on the port side."""
    return [(x, -y, z) for x, y, z in points]


scene = Scene(
    camera=Camera(azimuth=55.0, elevation=22.0, scale=150),
    title="Frames on a monohull USV",
    description="World, platform and sensor coordinate systems on a monohull USV, REP 103.",
)

# Far topside, transom, deck, near topside — painted in that order.
scene.add(
    Poly(points=mirror(SHEER) + mirror(CHINE)[::-1], fill="#ffffff", name="topside-starboard"),
    Poly(points=[SHEER[0], mirror(SHEER)[0], mirror(CHINE)[0], CHINE[0]],
         fill="#ffffff", name="transom"),
    Poly(points=mirror(SHEER)[::-1] + SHEER[:-1], fill="#ffffff", name="deck"),
    Poly(points=SHEER + CHINE[::-1], fill="#ffffff", name="topside-port"),
)

scene.add(
    Box(center=(-0.25, 0.0, DECK_Z + 0.16), size=(0.62, 0.56, 0.32), z=1.0, name="cabin"),
    cylinder((0.30, 0.0, DECK_Z), (0.30, 0.0, 1.08), 0.045, z=1.1, name="mast"),
    Box(center=(0.30, 0.0, 1.14), size=(0.16, 0.30, 0.14), z=1.2, name="sensor"),
)

# Platform frame: +X is the bow, the convention REP 103 and ISO 9787 5.5 agree on.
scene.add(Frame(
    origin=(0.0, 0.0, DECK_Z), subscript="p", length=0.95, lengths={"z": 0.72},
    offsets={"x": (-6.0, 14.0), "y": (4.0, 12.0)},
    origin_offset=(-6.0, -13.0), origin_anchor="end", name="platform-frame",
))

# Sensor frame, mounted on the mast and rotated to look forward and down.
scene.add(Frame(
    origin=SENSOR, subscript="s", length=0.42,
    directions={"x": (0.94, 0.0, -0.34), "y": (0.0, 1.0, 0.0), "z": (0.34, 0.0, 0.94)},
    offsets={"y": (4.0, -8.0)},
    origin_offset=(-20.0, -2.0), origin_anchor="end", name="sensor-frame",
))

# World frame, standing free alongside.
scene.add(Frame(
    origin=(2.3, -0.4, 0.15), subscript="0", length=0.8,
    origin_offset=(-6.0, -12.0), origin_anchor="end", name="world-frame",
))

if __name__ == "__main__":
    scene.save(str(HERE / "out" / "usv_mono_frames.svg"))
