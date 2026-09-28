#!/usr/bin/env python3
"""Build the axis-marker scene, authored in the REP 103 body frame (x forward, y left, z up).

Four arms of deliberately different lengths, so a bounding box alone identifies
every axis and its sign:

    +x  1.00 m  red      forward
    +y  0.50 m  green    left
    +z  0.25 m  blue     up
    -x  0.10 m  grey     a stub, so the sign of x is unambiguous too

Same geometry as probe/coords/make_markers.py, so the two can be compared.

    blender --background --factory-startup --python demo/make_marker.py -- demo
"""
import os, sys
import bpy

W = 0.025  # half cross-section of every arm, 5 cm square
ARMS = [   # name, lo corner, hi corner, base color -- in the BODY frame
    ("arm_pos_x", (0.00, -W, -W), (1.00,  W,   W), (0.80, 0.10, 0.10)),
    ("arm_pos_y", (-W, 0.00, -W), ( W, 0.50,   W), (0.10, 0.70, 0.10)),
    ("arm_pos_z", (-W, -W, 0.00), ( W,  W,  0.25), (0.10, 0.20, 0.85)),
    ("arm_neg_x", (-0.10, -W, -W), (0.00, W,   W), (0.35, 0.35, 0.35)),
]

out = os.path.abspath(sys.argv[sys.argv.index("--") + 1] if "--" in sys.argv else ".")
bpy.ops.wm.read_factory_settings(use_empty=True)   # no default cube, camera or light
bpy.context.scene.unit_settings.scale_length = 1.0  # profile 5.1: metres, scale 1.0

for name, lo, hi, rgb in ARMS:
    ctr = [(lo[i] + hi[i]) / 2 for i in range(3)]
    bpy.ops.mesh.primitive_cube_add(size=1.0, location=ctr)
    ob = bpy.context.active_object
    ob.name = name
    ob.dimensions = [hi[i] - lo[i] for i in range(3)]
    bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)
    mat = bpy.data.materials.new(name)
    mat.use_nodes = True
    bsdf = mat.node_tree.nodes["Principled BSDF"]
    bsdf.inputs["Base Color"].default_value = (*rgb, 1.0)
    bsdf.inputs["Metallic"].default_value = 0.0    # not metal; see the export guide
    bsdf.inputs["Roughness"].default_value = 0.8
    ob.data.materials.append(mat)

# One object named for the part. The node name is the only name either consumer reads.
bpy.ops.object.select_all(action='SELECT')
bpy.context.view_layer.objects.active = bpy.data.objects["arm_pos_x"]
bpy.ops.object.join()
ob = bpy.context.active_object
ob.name = "marker"
ob.data.name = "marker"        # the datablock too, so no stray 'Cube' is left behind

blend = f"{out}/marker.blend"
bpy.ops.wm.save_as_mainfile(filepath=blend)
print("\n=== scene built ===")
print("  objects :", [o.name for o in bpy.data.objects])
print("  mesh    :", ob.data.name, "verts", len(ob.data.vertices), "materials", [m.name for m in ob.data.materials])
print("  uv maps :", [u.name for u in ob.data.uv_layers])
print("  loc/rot/scale:", tuple(ob.location), tuple(ob.rotation_euler), tuple(ob.scale))
print("  dims (body frame):", tuple(round(d, 4) for d in ob.dimensions))
print("  saved   :", blend)
