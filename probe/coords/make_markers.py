#!/usr/bin/env python3
"""Write coordinate-frame probe assets from scratch, with no dependencies.

The marker is four box arms of deliberately different lengths, authored in the REP 103 body frame (x forward, y left, z up):

    +x  1.00 m  red      forward
    +y  0.50 m  green    left
    +z  0.25 m  blue     up
    -x  0.10 m  grey     a stub, so the sign of x is unambiguous too

A bounding box alone therefore identifies every axis and its sign, and a mirrored or mis-rotated file is visibly wrong. Every variant below carries the same marker; they differ only in how the frame is expressed, so that each file isolates one question.

Outputs, in the directory given as argv[1] (default: alongside this script):

  marker_yup.gltf / .glb      buffer swizzled (x,y,z)->(x,z,-y), root node identity.  What Blender's default "+Y Up" export produces.
  marker_zup.gltf / .glb      buffer raw in the body frame, root node identity.        What Blender's export produces with "+Y Up" off.
  marker_rotnode.gltf / .glb  buffer raw (Z-up) and a root-node rotation of -90 deg about X, so the composed result equals marker_yup.  Is a node rotation honored, and by whom?
  marker_roottrans.gltf/.glb  marker_yup with a root-node translation (0, 0.5, 0) in file space.        Gazebo rolls it with the geometry; RViz does not (root post-multiply).
  marker_twonode.glb          marker_yup plus a child node "pointer" with its own mesh, translated and rotated.  Node composition and submesh naming.
  marker_zup_declZ.dae        Z-up buffer, <up_axis>Z_UP</up_axis>.   } identical buffers, different declarations:
  marker_zup_declY.dae        Z-up buffer, <up_axis>Y_UP</up_axis>.   } if a consumer's output is identical, it ignores the declaration.
  world_marker.sdf            gz sim world placing marker_yup.glb with an identity visual pose.
  world_marker_rolled.sdf     the same, with <pose>0 0 0 1.5708 0 0</pose> on the visual.
  marker.urdf                 one link, marker_yup.glb as its visual, identity origin.
"""
import base64, json, math, os, struct, sys

W = 0.025  # half cross-section of every arm, 5 cm square
ARMS = [  # name, lo corner, hi corner, base color (r,g,b) — in the BODY frame
    ("arm_pos_x", (0.0, -W, -W), (1.00,  W,  W), (0.80, 0.10, 0.10)),
    ("arm_pos_y", (-W, 0.0, -W), ( W, 0.50,  W), (0.10, 0.70, 0.10)),
    ("arm_pos_z", (-W, -W, 0.0), ( W,  W, 0.25), (0.10, 0.20, 0.85)),
    ("arm_neg_x", (-0.10, -W, -W), (0.0, W,  W), (0.35, 0.35, 0.35)),
]
POINTER = ("pointer", (0.0, -W, -W), (0.30, W, W), (0.90, 0.60, 0.10))  # a single box along its own local +X

# Face table: outward normal, and two in-plane axes u, v with u x v = n, so (c0,c1,c2),(c0,c2,c3) are counter-clockwise from outside.
FACES = [
    (( 1, 0, 0), (0, 1, 0), (0, 0, 1)),
    ((-1, 0, 0), (0, 0, 1), (0, 1, 0)),
    (( 0, 1, 0), (0, 0, 1), (1, 0, 0)),
    (( 0,-1, 0), (1, 0, 0), (0, 0, 1)),
    (( 0, 0, 1), (1, 0, 0), (0, 1, 0)),
    (( 0, 0,-1), (0, 1, 0), (1, 0, 0)),
]

def box(lo, hi):
    """Return (positions, normals, indices) for an axis-aligned box, flat-shaded, CCW winding viewed from outside."""
    c = [(lo[i] + hi[i]) / 2 for i in range(3)]
    h = [(hi[i] - lo[i]) / 2 for i in range(3)]
    P, N, I = [], [], []
    for n, u, v in FACES:
        hn = sum(abs(n[i]) * h[i] for i in range(3))
        hu = sum(abs(u[i]) * h[i] for i in range(3))
        hv = sum(abs(v[i]) * h[i] for i in range(3))
        fc = [c[i] + n[i] * hn for i in range(3)]
        base = len(P)
        for su, sv in ((-1, -1), (1, -1), (1, 1), (-1, 1)):
            P.append(tuple(fc[i] + su * u[i] * hu + sv * v[i] * hv for i in range(3)))
            N.append(tuple(float(x) for x in n))
        I += [base, base + 1, base + 2, base, base + 2, base + 3]
    return P, N, I

def swizzle_yup(p):
    """Blender's exporter: (x, y, z) -> (x, z, -y).  gltf2_blender_math.swizzle_yup_location."""
    return (p[0], p[2], -p[1])

def quat_axis(axis, deg):
    s = math.sin(math.radians(deg) / 2)
    return [axis[0] * s, axis[1] * s, axis[2] * s, math.cos(math.radians(deg) / 2)]

# ---------------------------------------------------------------- glTF writer
class Gltf:
    def __init__(self):
        self.bin = bytearray()
        self.j = {"asset": {"version": "2.0", "generator": "make_markers.py (hand-authored, no exporter)"},
                  "buffers": [], "bufferViews": [], "accessors": [], "materials": [], "meshes": [],
                  "nodes": [], "scenes": [{"nodes": []}], "scene": 0}

    def _view(self, data, target):
        while len(self.bin) % 4: self.bin += b"\0"
        off = len(self.bin); self.bin += data
        self.j["bufferViews"].append({"buffer": 0, "byteOffset": off, "byteLength": len(data), "target": target})
        return len(self.j["bufferViews"]) - 1

    def vec3(self, pts):
        data = b"".join(struct.pack("<3f", *p) for p in pts)
        v = self._view(data, 34962)
        self.j["accessors"].append({"bufferView": v, "componentType": 5126, "count": len(pts), "type": "VEC3",
                                    "min": [min(p[i] for p in pts) for i in range(3)],
                                    "max": [max(p[i] for p in pts) for i in range(3)]})
        return len(self.j["accessors"]) - 1

    def idx(self, ind):
        v = self._view(b"".join(struct.pack("<H", i) for i in ind), 34963)
        self.j["accessors"].append({"bufferView": v, "componentType": 5123, "count": len(ind), "type": "SCALAR"})
        return len(self.j["accessors"]) - 1

    def material(self, name, rgb):
        self.j["materials"].append({"name": name, "pbrMetallicRoughness": {"baseColorFactor": [*rgb, 1.0], "metallicFactor": 0.0, "roughnessFactor": 0.8}})
        return len(self.j["materials"]) - 1

    def mesh(self, name, arms, xform):
        prims = []
        for aname, lo, hi, rgb in arms:
            P, N, I = box(lo, hi)
            P = [xform(p) for p in P]; N = [xform(n) for n in N]
            prims.append({"attributes": {"POSITION": self.vec3(P), "NORMAL": self.vec3(N)}, "indices": self.idx(I),
                          "material": self.material(aname, rgb)})
        self.j["meshes"].append({"name": name, "primitives": prims})
        return len(self.j["meshes"]) - 1

    def node(self, name, mesh, root=True, **trs):
        n = {"name": name, "mesh": mesh}; n.update(trs)
        self.j["nodes"].append(n)
        i = len(self.j["nodes"]) - 1
        if root: self.j["scenes"][0]["nodes"].append(i)
        return i

    def write(self, stem):
        while len(self.bin) % 4: self.bin += b"\0"
        self.j["buffers"] = [{"byteLength": len(self.bin)}]
        # .gltf with an embedded data URI, so the file is self-contained
        jg = json.loads(json.dumps(self.j)); jg["buffers"][0]["uri"] = "data:application/octet-stream;base64," + base64.b64encode(self.bin).decode()
        with open(stem + ".gltf", "w") as f: json.dump(jg, f, indent=1)
        # .glb
        js = json.dumps(self.j).encode()
        while len(js) % 4: js += b" "
        glb = b"glTF" + struct.pack("<II", 2, 12 + 8 + len(js) + 8 + len(self.bin))
        glb += struct.pack("<I4s", len(js), b"JSON") + js + struct.pack("<I4s", len(self.bin), b"BIN\0") + bytes(self.bin)
        with open(stem + ".glb", "wb") as f: f.write(glb)

# ---------------------------------------------------------------- Collada writer
def write_dae(path, up_axis, xform):
    P, I = [], []
    for aname, lo, hi, rgb in ARMS:
        bp, bn, bi = box(lo, hi)
        base = len(P); P += [xform(p) for p in bp]; I += [base + i for i in bi]
    pos = " ".join("%.6g" % c for p in P for c in p)
    xml = f"""<?xml version="1.0" encoding="utf-8"?>
<COLLADA xmlns="http://www.collada.org/2005/11/COLLADASchema" version="1.4.1">
  <asset><unit name="meter" meter="1"/><up_axis>{up_axis}</up_axis></asset>
  <library_geometries>
    <geometry id="marker-geom" name="marker"><mesh>
      <source id="marker-pos"><float_array id="marker-pos-array" count="{len(P)*3}">{pos}</float_array>
        <technique_common><accessor source="#marker-pos-array" count="{len(P)}" stride="3">
          <param name="X" type="float"/><param name="Y" type="float"/><param name="Z" type="float"/></accessor></technique_common></source>
      <vertices id="marker-vtx"><input semantic="POSITION" source="#marker-pos"/></vertices>
      <triangles count="{len(I)//3}"><input semantic="VERTEX" source="#marker-vtx" offset="0"/><p>{" ".join(map(str, I))}</p></triangles>
    </mesh></geometry>
  </library_geometries>
  <library_visual_scenes><visual_scene id="scene"><node id="marker-node" name="marker"><instance_geometry url="#marker-geom"/></node></visual_scene></library_visual_scenes>
  <scene><instance_visual_scene url="#scene"/></scene>
</COLLADA>
"""
    with open(path, "w") as f: f.write(xml)

# ---------------------------------------------------------------- SDF / URDF
def write_sdf(path, mesh_uri, rpy):
    with open(path, "w") as f: f.write(f"""<?xml version="1.0"?>
<sdf version="1.9">
  <world name="marker_world">
    <light type="directional" name="sun"><pose>0 0 10 0 0 0</pose><direction>-0.5 0.1 -0.9</direction><diffuse>0.9 0.9 0.9 1</diffuse></light>
    <model name="ground"><static>true</static><link name="l"><visual name="v"><geometry><plane><normal>0 0 1</normal><size>4 4</size></plane></geometry>
      <material><ambient>0.85 0.85 0.85 1</ambient><diffuse>0.85 0.85 0.85 1</diffuse></material></visual></link></model>
    <!-- The marker, exactly as the file says, with the visual pose given here and nothing else. -->
    <model name="marker"><static>true</static><pose>0 0 0.6 0 0 0</pose>
      <link name="base_link"><visual name="marker_visual"><pose>0 0 0 {rpy}</pose>
        <geometry><mesh><uri>{mesh_uri}</uri></mesh></geometry></visual></link></model>
  </world>
</sdf>
""")

def write_urdf(path, mesh_uri):
    with open(path, "w") as f: f.write(f"""<?xml version="1.0"?>
<robot name="marker">
  <link name="base_link">
    <visual><origin xyz="0 0 0" rpy="0 0 0"/><geometry><mesh filename="{mesh_uri}"/></geometry></visual>
  </link>
</robot>
""")

# ---------------------------------------------------------------- main
def main():
    out = os.path.abspath(sys.argv[1] if len(sys.argv) > 1 else os.path.dirname(__file__))
    os.makedirs(out, exist_ok=True)
    ident = lambda p: p

    g = Gltf(); g.node("marker", g.mesh("marker_mesh", ARMS, swizzle_yup)); g.write(f"{out}/marker_yup")
    g = Gltf(); g.node("marker", g.mesh("marker_mesh", ARMS, ident)); g.write(f"{out}/marker_zup")
    g = Gltf(); g.node("marker", g.mesh("marker_mesh", ARMS, ident), rotation=quat_axis((1, 0, 0), -90)); g.write(f"{out}/marker_rotnode")
    # root node carrying only a translation, 0.5 m up the FILE's Y: the two consumers compose this differently
    g = Gltf(); g.node("marker", g.mesh("marker_mesh", ARMS, swizzle_yup), translation=[0.0, 0.5, 0.0]); g.write(f"{out}/marker_roottrans")

    g = Gltf()
    parent = g.node("marker", g.mesh("marker_mesh", ARMS, swizzle_yup))
    child = g.node("pointer", g.mesh("pointer_mesh", [POINTER], ident), root=False, translation=[0.0, 0.5, 0.0], rotation=quat_axis((0, 1, 0), 90))
    g.j["nodes"][parent]["children"] = [child]
    g.write(f"{out}/marker_twonode")
    os.remove(f"{out}/marker_twonode.gltf")

    write_dae(f"{out}/marker_zup_declZ.dae", "Z_UP", ident)
    write_dae(f"{out}/marker_zup_declY.dae", "Y_UP", ident)

    write_sdf(f"{out}/world_marker.sdf", f"file://{out}/marker_yup.glb", "0 0 0")
    write_sdf(f"{out}/world_marker_rolled.sdf", f"file://{out}/marker_yup.glb", "1.5708 0 0")
    write_urdf(f"{out}/marker.urdf", f"file://{out}/marker_yup.glb")
    write_sdf(f"{out}/world_roottrans_rolled.sdf", f"file://{out}/marker_roottrans.glb", "1.5708 0 0")
    write_urdf(f"{out}/marker_roottrans.urdf", f"file://{out}/marker_roottrans.glb")

    print("wrote to", out)
    for n in sorted(os.listdir(out)):
        if n.startswith(("marker", "world")): print("  ", n)

if __name__ == "__main__":
    main()
