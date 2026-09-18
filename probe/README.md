# Probes

Tools that answer what reading a glTF file cannot.

`gltf-check` and `gltf-assess` parse files. That is enough for most questions and it is why they need no GPU, but it leaves two classes of question open: what a consumer actually *builds* from a file, which is not always what the file says, and anything that requires looking at a rendered image.

| | |
|---|---|
| `glb_probe/` | loads a file through Gazebo's own `gz-common` loader and prints what it built — submesh names, material count, what survived. Built and run inside drydock, against the installed gz-common rather than a branch. |
| `coords/make_markers.py` | writes coordinate-frame probe assets from scratch, no dependencies. Each variant isolates one question about how a frame is expressed, so a rendered view answers it unambiguously. |
| `glb_community_probe.py` | the survey script behind the community-exemplars evidence. |

## glb_probe

```bash
~/maritime_ws/tools/drydock/drydock join maritime bash -lc \
  'cd /path/to/probe/glb_probe && cmake -S . -B build && cmake --build build && ./build/glb_probe FILE.glb'
```

It reports what `gz-common` produced, which is the only way to settle questions where the loader and the specification disagree. The standing example is `extensionsRequired`: a conforming reader must refuse a file that requires an extension it does not implement, while our reading of the Gazebo source predicts it parses the extension and ignores it. Those cannot both be true, and `OpenRobotics/Distribution_Warehouse` is the one asset that settles it.

## Coordinate markers

```bash
./coords/make_markers.py /tmp/markers
```

The marker is four box arms of deliberately different lengths in the REP 103 body frame — x forward 1.00 m red, y left 0.50 m green, z up 0.25 m blue, and a 0.10 m grey stub on -x. A bounding box alone therefore identifies every axis and its sign, so a mirrored or mis-rotated file is visibly wrong rather than plausibly right.

Each output isolates one question: whether a root-node rotation is honored and by whom, how Gazebo and RViz differ in composing a root transform (Gazebo pre-multiplies, RViz post-multiplies), and what a COLLADA `<up_axis>` declaration does against an identical buffer. The script's docstring lists them.

Output is regenerated, not committed. Answering these requires a window and a person; the conclusions live in the coordinate-systems reference.
