"""What is in a glTF file, described rather than judged.

`gltf-check` answers whether a file conforms to the profile, and says nothing
about a file that conforms. `gltf-assess` measures a registry of remote assets.
Neither answers the question you have in front of an unfamiliar local file:
what is actually in here, and is it what the exporter was supposed to produce.

So this prints structure and geometry with no verdicts attached. Nothing here
reports a violation, because a walkthrough needs to show what a correct file
looks like as often as it needs to catch a wrong one. The one thing it does
draw attention to is where the origin sits inside the bounding box, since that
is invisible in every viewer and is the first thing a coordinate question turns
on.

Parsing, resolution and the transform maths are all reused: `Model` and the
node-walking helpers from the checker, and `transform_bounds` from the assessor.
"""

import argparse
import json
import pathlib
import sys

from .assess.gltf_assess import plural, read_accessor, transform_bounds
from .check.rules import Model, union, world_matrices

TRS_KEYS = ("translation", "rotation", "scale", "matrix")
# Present in a file means present in the delivery; the checker decides whether that is allowed.
NOTABLE = ("animations", "skins", "cameras")


def vertex_mean(model, accessor_index):
    """The average of a POSITION accessor's vertices, in the node's own space.

    This is the one figure here that requires reading the buffer rather than the
    accessor's declared bounds, and it is worth the read because it is the number
    Blender's Set Origin actually uses. Blender's `center='MEDIAN'` -- the default
    on every Set Origin operation -- is this mean, not a median and not the
    midpoint of the bounding box, so a mesh whose origin was set that way has its
    mean at the origin and its midpoint somewhere else.

    Two cautions. An average over vertices weights tessellation rather than area,
    so subdividing one region moves it; it is not the centroid of the surface or of
    the volume. And it is not numerically the same mean the authoring tool saw: the
    exporter splits vertices at UV seams and shading boundaries, so a 507-vertex
    Suzanne arrives as 1966 vertices with the duplicates weighted twice. Blender's
    own mean of her is (0, -0.3266, 0.0681) where the file's is (0, -0.314, 0.0614).
    So this explains what the authoring tool did without reproducing its arithmetic.
    """
    data = read_accessor(model.gltf, model.resolver, accessor_index)
    if not data:
        return None
    n = len(data)
    return [sum(v[i] for v in data) / n for i in range(3)]


def origin_placement(lo, hi):
    """Where the origin sits inside an AABB, per axis, as a fraction of the extent.

    0.5 puts the origin at the midpoint of the bounding box, 0.0 on the minimum
    face, and anything outside 0 to 1 means the origin is outside the geometry
    entirely -- which is legal and sometimes intended, but never an accident
    worth leaving unremarked.
    """
    out = []
    for i in range(3):
        span = hi[i] - lo[i]
        out.append(None if span == 0 else (0.0 - lo[i]) / span)
    return out


def summarize(path):
    model = Model(path)
    gltf = model.gltf
    asset = gltf.get("asset", {})
    matrices = world_matrices(model)
    nodes = model.get("nodes")

    prims, boxes = [], []
    for index, matrix in sorted(matrices.items()):
        mesh_index = nodes[index].get("mesh")
        if mesh_index is None:
            continue
        mesh = model.get("meshes")[mesh_index]
        for pi, prim in enumerate(mesh.get("primitives", [])):
            pos = prim.get("attributes", {}).get("POSITION")
            local = world = None
            if pos is not None:
                accessor = model.get("accessors")[pos]
                if accessor.get("min") and accessor.get("max"):
                    local = (accessor["min"], accessor["max"])
                    world = transform_bounds(matrix, *local)
                    boxes.append(world)
            material = prim.get("material")
            prims.append({
                "node": nodes[index].get("name"),
                "node_index": index,
                "mesh": mesh.get("name"),
                "mesh_index": mesh_index,
                "primitive": pi,
                "mode": prim.get("mode", 4),
                "attributes": sorted(prim.get("attributes", {})),
                "material": (model.get("materials")[material].get("name")
                             if material is not None else None),
                "local_bbox": local,
                "world_bbox": world,
                "midpoint": ([(local[0][i] + local[1][i]) / 2 for i in range(3)]
                             if local else None),
                "vertex_mean": vertex_mean(model, pos) if pos is not None else None,
                "vertex_count": (model.get("accessors")[pos].get("count")
                                 if pos is not None else None),
            })

    materials = []
    for material in model.get("materials"):
        pbr = material.get("pbrMetallicRoughness", {})
        materials.append({
            "name": material.get("name"),
            "metallicFactor": pbr.get("metallicFactor"),
            "roughnessFactor": pbr.get("roughnessFactor"),
            "alphaMode": material.get("alphaMode", "OPAQUE"),
            "doubleSided": material.get("doubleSided", False),
            "textures": (sorted(k for k in pbr if k.endswith("Texture"))
                         + sorted(k for k in material if k.endswith("Texture"))),
        })

    extent = union(boxes)
    # The same union taken before any node transform, so the report can say where
    # the NODE origin sits as well as where the SCENE origin does. The two differ
    # exactly when a node carries a transform, and that difference is the finding.
    local_extent = union([p["local_bbox"] for p in prims])
    return {
        "file": str(path),
        "bytes": pathlib.Path(path).stat().st_size,
        "container": ".glb" if model.is_glb else ".gltf",
        "version": asset.get("version"),
        "generator": asset.get("generator"),
        "copyright": asset.get("copyright"),
        "extensionsUsed": gltf.get("extensionsUsed") or [],
        "extensionsRequired": gltf.get("extensionsRequired") or [],
        "has_manifest": model.manifest() is not None,
        "scenes": [{"name": s.get("name"), "nodes": s.get("nodes", [])}
                   for s in model.get("scenes")],
        "default_scene": gltf.get("scene"),
        "nodes": [{"index": i, "name": nodes[i].get("name"),
                   "transform_keys": [k for k in TRS_KEYS if k in nodes[i]],
                   "transform": {k: nodes[i][k] for k in TRS_KEYS if k in nodes[i]},
                   "mesh": nodes[i].get("mesh"),
                   "children": nodes[i].get("children", []),
                   "is_root": i in model.root_nodes()}
                  for i in range(len(nodes))],
        "primitives": prims,
        "materials": materials,
        "images": [{"mimeType": im.get("mimeType"), "name": im.get("name"),
                    "embedded": "bufferView" in im} for im in model.get("images")],
        "extent": extent,
        "origin_placement": origin_placement(*extent) if extent else None,
        "local_extent": local_extent,
        "local_origin_placement": (origin_placement(*local_extent)
                                   if local_extent else None),
        "notable": {k: len(gltf.get(k, [])) for k in NOTABLE if gltf.get(k)},
        "lights": len(gltf.get("extensions", {})
                      .get("KHR_lights_punctual", {}).get("lights", [])),
    }


def fmt(values, places=4, eps=1e-9):
    """Format a vector, snapping float noise to zero.

    Composing a rotation through a matrix turns an exact 0 into 5.551e-18, which
    is correct and unreadable. Anything below eps is reported as 0.
    """
    return "[" + ", ".join(f"{0.0 if abs(v) < eps else v:.{places}g}" for v in values) + "]"


TRS_DEFAULTS = (("translation", [0.0, 0.0, 0.0], ""),
                ("rotation", [0.0, 0.0, 0.0, 1.0], " (identity)"),
                ("scale", [1.0, 1.0, 1.0], ""))


def transform_lines(transform, indent="        "):
    """Every component of a node's transform, whether the file states it or not.

    This is the map from node space to scene space, so when the two geometry
    blocks below disagree these are the numbers that account for it. All three
    are printed even when they are identity, because a reader checking a file
    against the profile's Scenes and nodes section should not have to infer a component's value from its
    absence from the report.

    Stated and defaulted are still distinguished, because 5.5 prohibits all four
    keys and constrains
    presence rather than value: it prohibits a `rotation` key on the root node
    even when that rotation is identity, and glTF omits any component equal to
    its default, so an absent key and an identity value are the same geometry
    written by two different exporters.
    """
    if "matrix" in transform:
        return [f"{indent}matrix      {fmt(transform['matrix'], places=6)}",
                f"{indent}            stated, column-major; it replaces"
                f" translation, rotation and scale"]
    out = []
    for key, default, note in TRS_DEFAULTS:
        stated = key in transform
        state = ("stated in the file" if stated
                 else f"absent, so glTF's default applies{note}")
        out.append(f"{indent}{key:<11} {fmt(transform.get(key, default)):<26}"
                   f" {state}")
    if not transform:
        out.append(f"{indent}            -> node space and scene space coincide")
    return out


def geometry_block(space, lo, hi, placement, provenance):
    """One box, extent and origin placement, all stated in one named space."""
    return [
        f"  geometry in {space}",
        f"    bounding box  {fmt(lo)} -> {fmt(hi)}",
        f"                  {provenance}",
        f"    extent        {fmt([hi[i] - lo[i] for i in range(3)])}"
        f"   = max - min of that box",
        f"    origin at     {', '.join(place_words(placement))}"
        f"   = (0 - min) / extent, per axis",
        "                  0 = minimum face, "
        "0.5 = midpoint of the bounding box, 1 = maximum face",
    ]


def place_words(placement):
    """Per-axis origin placement as text, calling out an origin outside the box."""
    out = []
    for axis, f in zip("xyz", placement):
        if f is None:
            out.append(f"{axis} n/a (flat)")
        elif f < 0 or f > 1:
            out.append(f"{axis} {f:.2f} OUTSIDE the geometry")
        else:
            out.append(f"{axis} {f:.2f}")
    return out


GLOSSARY = """
Reading the output

  Counts versus indices. A bare number after a label is a count: "nodes: 1 total"
  means the file holds one node. A number in square brackets is an index into the
  glTF array of that name: "node [0]" is the first entry of the `nodes` array, and
  "-> mesh [0]" means that node instantiates the first entry of `meshes`. glTF
  refers to everything by array index, so the two kinds of number sit side by side
  throughout the format.

  Node space and scene space. Every coordinate in a glTF file belongs to one or the
  other, and the report says which above each block rather than leaving you to work
  it out. Node space is what the accessor's vertices are written in, and its zero is
  the node origin -- in Blender terms, the object origin, which is what Set Origin
  moves. Scene space is what you get after composing each node's transform down from
  the root, and its zero is what a consumer treats as the link origin: Gazebo bakes
  those transforms into the vertices at load, so scene space is the only one it ever
  shows you. A bounding box, an extent and an origin placement are each different
  numbers in the two spaces, so where a node carries a transform the report gives
  both blocks. Every node's transform is printed beneath it, component by component
  and whether the file states it or not, so the difference can be accounted for. Where no node carries a transform the two spaces coincide and one
  block is given, which is what the profile's Scenes and nodes section is asking for.

  Scene, node, mesh, primitive. A scene lists the root nodes a viewer should draw.
  A node is a coordinate system with an optional transform; it may instantiate one
  mesh and may have children. A mesh is a named bag of primitives. A primitive is
  one draw call -- one set of vertex attributes, one index buffer, one material.
  A part with three materials therefore has at least three primitives, all inside
  a single mesh, under a single node. So "primitives: 1" counts draw calls, not
  meshes; the mesh count is on its own line.

  Declared versus computed. "vertex min/max" is the `min` and `max` that the file's
  POSITION accessor states, copied out verbatim -- glTF requires them, so no vertex
  is read to obtain them. "bbox midpoint" is their average. Everything under
  "geometry" is computed from those same two numbers per axis: the extent is the
  union across every primitive after each node's transform is composed down from
  the root, and the origin placement is where (0, 0, 0) falls inside that union.

  Three points, all different. "bbox midpoint" is fixed by the two extreme vertices
  per axis. "vertex mean" is the average over every vertex, which is the one figure
  here that requires reading the buffer -- and it is what Blender's Set Origin uses
  under the name "median point", though it is neither a median nor the midpoint. A
  mesh whose origin was set that way has its mean at the origin and its midpoint
  somewhere else. Neither is the centroid of the surface or of the volume, and the
  mean weights tessellation, so subdividing one region moves it.

  Origin placement. Reported per axis as a fraction of the extent: 0.0 sits on the
  minimum face, 0.5 at the midpoint of the bounding box, 1.0 on the maximum face.
  Outside 0 to 1 means the origin lies outside the geometry altogether -- legal,
  occasionally intended, and worth knowing because no viewer shows it.

  What 0.5 does not mean. The midpoint of the bounding box is fixed by two vertices
  per axis, the extreme ones, and every other vertex is discarded. It is therefore
  not the centroid, not the centre of mass, and not the geometric median, and one
  stray vertex moves it where it would barely move any of those. Blender's Suzanne
  is the standing example: her bounding box is symmetric about her object origin,
  so this reads 0.50 on all three axes, while her vertex mean sits about a third of
  a unit away in depth. The midpoint is reported because it is the only one of the
  four that glTF's accessor bounds allow without reading the vertex buffer.
"""


def render(s):
    out = [f"{s['file']}  ({s['bytes']} bytes, {s['container']})"]
    out.append(f"  glTF {s['version']}   exported by: {s['generator']}")
    if s["copyright"]:
        out.append(f"  copyright: {s['copyright']}")
    if s["extensionsUsed"] or s["extensionsRequired"]:
        out.append(f"  extensions: used {s['extensionsUsed']}"
                   f"  required {s['extensionsRequired']}")
    out.append(f"  manifest: "
               f"{'KHR_xmp_json_ld present' if s['has_manifest'] else 'none'}")
    out.append("")

    # ---- structure, as the file declares it
    scene = "none" if s["default_scene"] is None else f"[{s['default_scene']}]"
    out.append(f"  scenes: {len(s['scenes'])} total; the file opens scene {scene}")
    for i, sc in enumerate(s["scenes"]):
        listed = sc["nodes"]
        out.append(f"    scene [{i}] {sc['name']!r} lists "
                   f"{plural(len(listed), 'root node')}:"
                   f" {listed if listed else 'none -- the scene is empty'}")

    roots = [n for n in s["nodes"] if n["is_root"]]
    out.append(f"  nodes: {len(s['nodes'])} total, "
               f"{len(roots)} root, {len(s['nodes']) - len(roots)} child")
    for n in s["nodes"]:
        tag = "root " if n["is_root"] else "child"
        mesh = "" if n["mesh"] is None else f"  -> mesh [{n['mesh']}]"
        kids = f"  children {n['children']}" if n["children"] else ""
        out.append(f"    node [{n['index']}] {n['name']!r}  {tag}{mesh}{kids}")
        out.extend(transform_lines(n["transform"]))

    meshes = {}
    for p in s["primitives"]:
        meshes.setdefault((p["mesh_index"], p["mesh"]), []).append(p)
    out.append(f"  meshes: {len(meshes)} instantiated, holding "
               f"{plural(len(s['primitives']), 'primitive')} in total")
    for (mi, name), prims in sorted(meshes.items()):
        out.append(f"    mesh [{mi}] {name!r}  -- {plural(len(prims), 'primitive')}")
        for p in prims:
            mode = "" if p["mode"] == 4 else f"   MODE {p['mode']} (not triangles)"
            attrs = " + ".join(p["attributes"])
            out.append(f"      primitive [{p['primitive']}]  {attrs}"
                       f"   material: {p['material'] or 'none'}{mode}")
            if p["local_bbox"]:
                out.append(f"        -- in NODE space, where the node origin is zero")
                out.append(f"        vertex min/max   {fmt(p['local_bbox'][0])}"
                           f" -> {fmt(p['local_bbox'][1])}"
                           f"   declared by the accessor")
                out.append(f"        bbox midpoint    {fmt(p['midpoint'])}")
                if p["vertex_mean"] is not None:
                    out.append(f"        vertex mean      {fmt(p['vertex_mean'])}"
                               f"   over {p['vertex_count']} vertices, split at UV"
                               f" seams, so not the authoring tool's count")
                if p["world_bbox"] != p["local_bbox"]:
                    out.append(f"        -- in SCENE space, after node "
                               f"[{p['node_index']}]'s transform")
                    out.append(f"        vertex min/max   {fmt(p['world_bbox'][0])}"
                               f" -> {fmt(p['world_bbox'][1])}")
    out.append("")

    # ---- geometry, derived from the vertex min/max above, in dependency order:
    # the box first, the extent from the box, the origin from both. Given once per
    # coordinate system, because every one of these numbers is space-dependent and
    # reporting them unlabelled in two spaces is how a reader gets a contradiction.
    if s["extent"]:
        moved = any(p["world_bbox"] != p["local_bbox"] for p in s["primitives"])
        n = plural(len(s["primitives"]), "primitive")
        if moved:
            out.extend(geometry_block(
                "NODE space -- the coordinate system the accessor's vertices are in,"
                " and the one the modeller set",
                *s["local_extent"], s["local_origin_placement"],
                f"union over {n}, before any node transform"))
            out.append("")
            out.extend(geometry_block(
                "SCENE space -- what a consumer sees; Gazebo composes node"
                " transforms and bakes them into the vertices",
                *s["extent"], s["origin_placement"],
                f"union over {n}, after the node transform above"))
            out.append("")
            out.append("  the two blocks differ only because a node carries a "
                       "transform; the profile's Scenes and nodes section requires")
            out.append("  exactly one node with no transform, so that they cannot")
        else:
            out.extend(geometry_block(
                "NODE space, which is also SCENE space here -- no node carries a"
                " transform",
                *s["extent"], s["origin_placement"],
                f"union over {n}, unchanged from the vertex min/max above"))
    else:
        out.append("  geometry: none -- no primitive declares bounds")
    out.append("")

    if s["materials"]:
        out.append(f"  materials: {len(s['materials'])} total")
        for i, m in enumerate(s["materials"]):
            metal = ("absent, so glTF's default of 1.0 applies"
                     if m["metallicFactor"] is None else m["metallicFactor"])
            out.append(f"    material [{i}] {m['name']!r}  metallic {metal}  "
                       f"roughness {m['roughnessFactor']}  {m['alphaMode']}"
                       f"{'  doubleSided' if m['doubleSided'] else ''}")
            if m["textures"]:
                out.append(f"       textures: {', '.join(m['textures'])}")
    else:
        # No editorial: what an absent material renders as is gltf-check's the profile's Materials section.
        out.append("  materials: none")

    if s["images"]:
        out.append(f"  images: {len(s['images'])} total  "
                   f"{[im['mimeType'] for im in s['images']]}")
    if s["notable"] or s["lights"]:
        extra = dict(s["notable"])
        if s["lights"]:
            extra["lights"] = s["lights"]
        out.append(f"  also present: {extra}")
    return "\n".join(out)


def main(argv=None):
    parser = argparse.ArgumentParser(
        prog="gltf-summary",
        description="Describe what is in a glTF file: structure, geometry, materials. "
                    "No verdicts -- use gltf-check for those.")
    parser.add_argument("files", nargs="+", type=pathlib.Path)
    parser.add_argument("--json", action="store_true", help="machine-readable output")
    parser.add_argument("--explain", action="store_true",
                        help="append how to read the output: counts versus indices, "
                             "the node/mesh/primitive relationship, and which numbers "
                             "are declared in the file rather than computed here")
    args = parser.parse_args(argv)

    payload, failed = [], False
    for path in args.files:
        try:
            s = summarize(path)
        except Exception as exc:
            print(f"{path}: {type(exc).__name__}: {exc}", file=sys.stderr)
            failed = True
            continue
        payload.append(s)
        if not args.json:
            print(render(s))
            print()
    if args.json:
        print(json.dumps(payload, indent=1))
    elif args.explain:
        print(GLOSSARY)
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
