# gltf-check report

gltf-robotics 0.1.0

Each test is marked as one of:

- **PASS** the rule is satisfied
- **FAIL** a MUST in the profile is violated; the delivery is not compliant
- **WARN** a SHOULD is violated, or a MUST the file alone cannot settle; review before delivering
- **OPEN** the profile has not settled this point (the profile's Open issues section); nothing to fix, something to discuss
- **SKIP** nothing in the file for the rule to examine

This answers only the 'compliant' question of the profile's Conformance testing section: does the file satisfy the rules that can be decided by reading it. Valid (Khronos validator), intended (reference viewer) and usable (glb_probe, Gazebo, RViz) are separate checks.

## Summary

Test                | blueboat_chassis_visual.glb | m200_weedless_prop_cw_visual.glb | m200_weedless_prop_ccw_visual.glb
--------------------|-----------------------------|----------------------------------|----------------------------------
File naming         | PASS                        | PASS                             | PASS
File format         | PASS                        | PASS                             | PASS
The manifest        | PASS                        | PASS                             | PASS
Asset header        | PASS                        | PASS                             | PASS
Units               | PASS                        | PASS                             | PASS
Scenes and nodes    | WARN                        | WARN                             | WARN
Datum specification | PASS                        | PASS                             | PASS
Geometry            | PASS                        | PASS                             | PASS
UV sets             | PASS                        | PASS                             | PASS
Primitives          | PASS                        | PASS                             | PASS
Materials           | WARN                        | WARN                             | WARN
Textures            | PASS                        | PASS                             | PASS
Transparency        | PASS                        | PASS                             | PASS
Prohibited content  | PASS                        | PASS                             | PASS
Authoring toolchain | PASS                        | PASS                             | PASS
Verdict             | compliant                   | compliant                        | compliant

## blueboat_chassis_visual.glb

**compliant; 2 WARN to review before delivering (Scenes and nodes, Materials)**

15 checks: 2 WARN, 13 PASS

### Tests

Result | Test name           | Test description                                                                    | Notes
-------|---------------------|-------------------------------------------------------------------------------------|--------------------------------------------------------------------------------------------------------------------------------------------
PASS   | File naming         | named <part>_visual.glb, with <part> in lowercase snake_case                        | named blueboat_chassis_visual.glb
PASS   | File format         | delivered as binary .glb rather than .gltf                                          | binary .glb container
PASS   | The manifest        | carries a KHR_xmp_json_ld manifest, and its contents agree with the file            | manifest present, role base
PASS   | Asset header        | asset header declares glTF 2.0 and no minVersion                                    | asset header is 2.0 with no minVersion
PASS   | Units               | in meters at real-world scale, checked against the cited dimension                  | length overall 1.2 m matches the Z extent 1.192 m
WARN   | Scenes and nodes    | exactly one scene and one named node, with no children and no transform             | the root node is not named after the part
PASS   | Datum specification | names the datum point its origin is referenced to                                   | datum point: Intersection of three planes on the geometry mid-point as explained and illustrated in docs/vehicles/blueboat/configuration.md
PASS   | Geometry            | every primitive is triangles carrying POSITION, NORMAL and TEXCOORD_0               | every primitive is triangles with POSITION, NORMAL, TEXCOORD_0
PASS   | UV sets             | UV coordinates present, and inside the range 0 to 1                                 | 1 UV set, inside [0, 1]
PASS   | Primitives          | a primitive exists only to carry a material distinct from its siblings              | 1 primitive, each carrying a distinct material
WARN   | Materials           | every primitive has a material, with metalness stated rather than defaulted         | 1 material leaves metallicFactor unset but carry an ORM map
PASS   | Textures            | textures are PNG in the linear slots and at most 2048 px on a side                  | 3 images, PNG/JPEG, within 2048 px
PASS   | Transparency        | transparency declared per material: MASK for cutouts, never BLEND on an opaque part | no BLEND; any MASK is cutoff 0.5 with alpha
PASS   | Prohibited content  | no prohibited extension, animation, skin, camera or light                           | no prohibited extensions or content
PASS   | Authoring toolchain | records the exporter that produced it                                               | generator: Khronos glTF Blender I/O v5.2.40

### Notes

- **WARN** Scenes and nodes: 'blueboat_chassis.visual'. the filename implies 'blueboat_chassis'
- **WARN** Materials: Gazebo Compliant glTF Material (metallicFactor unset, so 1.0, metallicRoughness texture present). The texture's blue channel multiplies against the factor, so a black metallic channel would still yield a non-metal. Settling it needs the decoded texel values, which this tool does not read. Do not assume it is fine: a solid white metallic channel is the usual export, and every map measured in this project's own library had B = 255, which makes the part fully metal. State the factor explicitly if the part is not metal.

### Structure

```text
* scene[0] 'blueboat_chassis'
   └─ node[0] 'blueboat_chassis.visual'
      └─ mesh[0] 'Cube'
         └─ primitive[0] -> material[0] 'Gazebo Compliant glTF Material'

* the scene the file opens
```

## m200_weedless_prop_cw_visual.glb

**compliant; 2 WARN to review before delivering (Scenes and nodes, Materials)**

15 checks: 2 WARN, 13 PASS

### Tests

Result | Test name           | Test description                                                                    | Notes
-------|---------------------|-------------------------------------------------------------------------------------|---------------------------------------------------------------
PASS   | File naming         | named <part>_visual.glb, with <part> in lowercase snake_case                        | named m200_weedless_prop_cw_visual.glb
PASS   | File format         | delivered as binary .glb rather than .gltf                                          | binary .glb container
PASS   | The manifest        | carries a KHR_xmp_json_ld manifest, and its contents agree with the file            | manifest present, role component
PASS   | Asset header        | asset header declares glTF 2.0 and no minVersion                                    | asset header is 2.0 with no minVersion
PASS   | Units               | in meters at real-world scale, checked against the cited dimension                  | diameter 0.112 m matches the Y extent 0.1103 m
WARN   | Scenes and nodes    | exactly one scene and one named node, with no children and no transform             | the root node is not named after the part
PASS   | Datum specification | names the datum point its origin is referenced to                                   | datum point: center of the hub's mating face, on the spin axis
PASS   | Geometry            | every primitive is triangles carrying POSITION, NORMAL and TEXCOORD_0               | every primitive is triangles with POSITION, NORMAL, TEXCOORD_0
PASS   | UV sets             | UV coordinates present, and inside the range 0 to 1                                 | 1 UV set, inside [0, 1]
PASS   | Primitives          | a primitive exists only to carry a material distinct from its siblings              | 1 primitive, each carrying a distinct material
WARN   | Materials           | every primitive has a material, with metalness stated rather than defaulted         | 1 material leaves metallicFactor unset but carry an ORM map
PASS   | Textures            | textures are PNG in the linear slots and at most 2048 px on a side                  | 3 images, PNG/JPEG, within 2048 px
PASS   | Transparency        | transparency declared per material: MASK for cutouts, never BLEND on an opaque part | no BLEND; any MASK is cutoff 0.5 with alpha
PASS   | Prohibited content  | no prohibited extension, animation, skin, camera or light                           | no prohibited extensions or content
PASS   | Authoring toolchain | records the exporter that produced it                                               | generator: Khronos glTF Blender I/O v5.2.40

### Notes

- **WARN** Scenes and nodes: 'm200_weedless_prop_cw.visual'. the filename implies 'm200_weedless_prop_cw'
- **WARN** Materials: Prop-CW-Mat (metallicFactor unset, so 1.0, metallicRoughness texture present). The texture's blue channel multiplies against the factor, so a black metallic channel would still yield a non-metal. Settling it needs the decoded texel values, which this tool does not read. Do not assume it is fine: a solid white metallic channel is the usual export, and every map measured in this project's own library had B = 255, which makes the part fully metal. State the factor explicitly if the part is not metal.

### Structure

```text
* scene[0] 'm200_weedless_prop_cw'
   └─ node[0] 'm200_weedless_prop_cw.visual'
      └─ mesh[0] 'Cylinder.007'
         └─ primitive[0] -> material[0] 'Prop-CW-Mat'

* the scene the file opens
```

## m200_weedless_prop_ccw_visual.glb

**compliant; 2 WARN to review before delivering (Scenes and nodes, Materials)**

15 checks: 2 WARN, 13 PASS

### Tests

Result | Test name           | Test description                                                                    | Notes
-------|---------------------|-------------------------------------------------------------------------------------|---------------------------------------------------------------
PASS   | File naming         | named <part>_visual.glb, with <part> in lowercase snake_case                        | named m200_weedless_prop_ccw_visual.glb
PASS   | File format         | delivered as binary .glb rather than .gltf                                          | binary .glb container
PASS   | The manifest        | carries a KHR_xmp_json_ld manifest, and its contents agree with the file            | manifest present, role component
PASS   | Asset header        | asset header declares glTF 2.0 and no minVersion                                    | asset header is 2.0 with no minVersion
PASS   | Units               | in meters at real-world scale, checked against the cited dimension                  | diameter 0.112 m matches the Y extent 0.1107 m
WARN   | Scenes and nodes    | exactly one scene and one named node, with no children and no transform             | the root node is not named after the part
PASS   | Datum specification | names the datum point its origin is referenced to                                   | datum point: center of the hub's mating face, on the spin axis
PASS   | Geometry            | every primitive is triangles carrying POSITION, NORMAL and TEXCOORD_0               | every primitive is triangles with POSITION, NORMAL, TEXCOORD_0
PASS   | UV sets             | UV coordinates present, and inside the range 0 to 1                                 | 1 UV set, inside [0, 1]
PASS   | Primitives          | a primitive exists only to carry a material distinct from its siblings              | 1 primitive, each carrying a distinct material
WARN   | Materials           | every primitive has a material, with metalness stated rather than defaulted         | 1 material leaves metallicFactor unset but carry an ORM map
PASS   | Textures            | textures are PNG in the linear slots and at most 2048 px on a side                  | 3 images, PNG/JPEG, within 2048 px
PASS   | Transparency        | transparency declared per material: MASK for cutouts, never BLEND on an opaque part | no BLEND; any MASK is cutoff 0.5 with alpha
PASS   | Prohibited content  | no prohibited extension, animation, skin, camera or light                           | no prohibited extensions or content
PASS   | Authoring toolchain | records the exporter that produced it                                               | generator: Khronos glTF Blender I/O v5.2.40

### Notes

- **WARN** Scenes and nodes: 'm200_weedless_prop_ccw.visual'. the filename implies 'm200_weedless_prop_ccw'
- **WARN** Materials: Prop-CCW-Mat (metallicFactor unset, so 1.0, metallicRoughness texture present). The texture's blue channel multiplies against the factor, so a black metallic channel would still yield a non-metal. Settling it needs the decoded texel values, which this tool does not read. Do not assume it is fine: a solid white metallic channel is the usual export, and every map measured in this project's own library had B = 255, which makes the part fully metal. State the factor explicitly if the part is not metal.

### Structure

```text
* scene[0] 'm200_weedless_prop_ccw'
   └─ node[0] 'm200_weedless_prop_ccw.visual'
      └─ mesh[0] 'Cylinder.004'
         └─ primitive[0] -> material[0] 'Prop-CCW-Mat'

* the scene the file opens
```

