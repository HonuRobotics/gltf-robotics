# Blender glTF Export Options

Every option the Blender glTF exporter offers, with its default. The dialog has 110 properties and no guide we have written names more than a handful, so the settings that matter are collected here first and the full enumeration follows as backing.

## Directive

Thirteen options out of 110. Everything not named below stays at its Blender default.

Confirm these. They are already Blender's defaults, so the work is checking rather than changing:

| UI label | Identifier | Value | Why |
|---|---|---|---|
| Format | `export_format` | GLB | the profile's [File format](../profile.md#file-format) section prohibits `.gltf` |
| At Collection Center | `at_collection_center` | False | it relocates the origin, which the profile's [Origin](../profile.md#origin---datum-coordinate-system-location) and [Datum specification](../profile.md#datum-specification) sections govern |
| UVs | `export_texcoords` | True | the profile's [Geometry](../profile.md#geometry) section requires `TEXCOORD_0` on every primitive |
| Normals | `export_normals` | True | the profile's [Geometry](../profile.md#geometry) section requires `NORMAL` |
| Materials | `export_materials` | EXPORT | the profile's [Materials](../profile.md#materials) section |
| Cameras | `export_cameras` | False | the profile's [Prohibited content](../profile.md#prohibited-content) section prohibits `cameras` |
| Punctual Lights | `export_lights` | False | the profile's [Prohibited content](../profile.md#prohibited-content) section prohibits `KHR_lights_punctual` |
| Draco | `export_draco_mesh_compression_enable` | False | the profile's [Prohibited content](../profile.md#prohibited-content) section prohibits `KHR_draco_mesh_compression` |

Change these. They are the only five that differ from the default:

| UI label | Identifier | Default | Set to | Why |
|---|---|---|---|---|
| +Y Up | `export_yup` | True | True | the profile's [Axes](../profile.md#axes) section requires the file in glTF's convention, +Y up and +Z forward; the default produces it from a part built in Blender's own convention |
| Limit to ▸ Selected Objects | `use_selection` | False | True | one part per delivery — the profile's [File](../profile.md#file) section |
| Animation | `export_animations` | True | False | the profile's [Prohibited content](../profile.md#prohibited-content) section prohibits `animations`, and no scene should rely on having no actions |
| Remember Export Settings | `will_save_settings` | False | True | the `.blend` then carries the settings it was exported with, so the delivery can be reproduced from its source |
| Copyright | `export_copyright` | `''` | `Copyright Honu Robotics` | |

Four decide where the geometry lands: `export_format`, `export_yup`, `at_collection_center` and `use_selection`. The rest is payload, prohibition or provenance.

Two are not settled, and the dialog default is what we use until they are: `export_apply` (Apply Modifiers) and `export_image_format` (`AUTO`, which is necessary and not sufficient — see the Data ▸ Material panel below).

### Four things that decide the result and are not in this dialog

No export option touches any of these. They are done in the scene, before the dialog opens.

| What | Where | Why |
|---|---|---|
| Clear location and rotation, apply scale | `Object ▸ Clear` and `Object ▸ Apply ▸ Scale` | the profile's [Scenes and nodes](../profile.md#scenes-and-nodes) section — the node must carry no transform at all. Apply is wrong for location and rotation: it moves the origin off the datum |
| Scene unit scale 1.0, object scale applied | Scene properties | the profile's [Units](../profile.md#units) section — a file at the wrong scale is silently wrong |
| `metallicFactor` | the material's Principled BSDF | the profile's [Materials](../profile.md#materials) section — the defect that recurs most in deliveries |
| The object's name | the object, not the mesh datablock | the profile's [Scenes and nodes](../profile.md#scenes-and-nodes) section — the only name either consumer reads |

## Provenance

Read out of the operator by introspection, not from documentation:

```bash
blender --background --factory-startup --python - <<'EOF'
import bpy
for p in bpy.ops.export_scene.gltf.get_rna_type().properties:
    print(p.identifier, p.type, getattr(p, "default", None))
EOF
```

| | |
|---|---|
| Blender | 5.2.2 LTS (hash `d13f752e3b9c`, built 2026-09-15) |
| Add-on | `io_scene_gltf2` 5.2.40 |
| `asset.generator` written | `Khronos glTF Blender I/O v5.2.40` |
| Properties | 110 |

Every current delivery reports `Khronos glTF Blender I/O v5.1.20`, which is Blender 5.1. This page is one minor version ahead of the deliveries. The profile's [Authoring toolchain](../profile.md#authoring-toolchain) section proposes pinning 5.1 and is Open; nothing here decides it.

## What no option does

There is no export option that applies object transforms. `export_apply` is Apply **Modifiers** — it evaluates the modifier stack, and it has nothing to do with an object's location, rotation or scale.

The profile's [Scenes and nodes](../profile.md#scenes-and-nodes) section requires the node to carry no `translation`, `rotation`, `scale` or `matrix`, and that is achieved in the scene before the export dialog is ever opened. An object left with a transform exports as a node carrying it, no matter how the dialog is set.

The operation is not `Object ▸ Apply ▸ All Transforms`, which is the one a reader expects. Applying a location or a rotation holds the geometry still in the world and moves the origin relative to the part, destroying the datum that the profile's [Origin](../profile.md#origin---datum-coordinate-system-location) section requires; clearing them moves the geometry with the object and preserves it. Scale is the exception and must be applied, because clearing it changes the part's size. Measured on 5.2.2 with an origin set 1 m off the geometry: applying moved it 5.42 m relative to the part, clearing moved it not at all.

## Top of the dialog

| UI label | Identifier | Default | Ours |
|---|---|---|---|
| Format | `export_format` | GLB | required GLB — the profile's [File format](../profile.md#file-format) section |
| Copyright | `export_copyright` | `''` | `Copyright Honu Robotics` |
| Remember Export Settings | `will_save_settings` | False | True — the `.blend` then carries the settings it was exported with |
| File path | `filepath` | `''` | naming is governed by the profile's [File](../profile.md#file) section: `<part>.visual.glb` |
| Check Existing | `check_existing` | True | default |
| Filter | `filter_glob` | `'*.glb'` | default |
| Caller id | `gltf_export_id` | `''` | default |
| Log Level | `export_loglevel` | −1 | default |
| Settings category | `ui_tab` | `'GENERAL'` | UI only |

`export_format`'s enum items are built dynamically, so headless introspection returns an empty list and a warning. The default is binary, which `filter_glob` confirms.

`will_save_settings` stores the export settings inside the `.blend`, so the source file records how it was exported and a re-export reproduces the delivery rather than approximating it. That is a partial answer to the shipped-preset proposal in the profile's [Authoring toolchain](../profile.md#authoring-toolchain) section: it does not distribute a preset, but it does make each source file self-describing, which is the part that matters when the modeler is outside our infrastructure. What it does not do is put the settings in the delivered `.glb` — `asset.generator` records the tool and never the settings, which is why the profile's [Authoring toolchain](../profile.md#authoring-toolchain) section calls a version pin necessary and not sufficient.

`export_copyright` writes `asset.copyright`, one of the few places a delivered file can carry provenance without an extension.

## Include

| UI label | Identifier | Default | Ours |
|---|---|---|---|
| Limit to ▸ Selected Objects | `use_selection` | False | True — the profile's [File](../profile.md#file) section is one part per delivery |
| Limit to ▸ Visible Objects | `use_visible` | False | default |
| Limit to ▸ Renderable Objects | `use_renderable` | False | default |
| Limit to ▸ Active Collection | `use_active_collection` | False | default |
| … with Nested Collections | `use_active_collection_with_nested` | True | default |
| Limit to ▸ Active Scene | `use_active_scene` | False | open — the profile's [Scenes and nodes](../profile.md#scenes-and-nodes) section requires exactly one scene, and six deliveries carried leftover empty ones |
| Collection by name | `collection` | `''` | default |
| At Collection Center | `at_collection_center` | False | required False — it would move the origin, which the profile's [Origin](../profile.md#origin---datum-coordinate-system-location) and [Datum specification](../profile.md#datum-specification) sections govern |
| Data ▸ Custom Properties | `export_extras` | False | open — the archive-the-source question in the profile's [manifest](../profile.md#the-manifest) section |
| Data ▸ Cameras | `export_cameras` | False | required False — the profile's [Prohibited content](../profile.md#prohibited-content) section prohibits `cameras` |
| Data ▸ Punctual Lights | `export_lights` | False | required False — the profile's [Prohibited content](../profile.md#prohibited-content) section prohibits `KHR_lights_punctual` |

`use_selection` is prescribed True rather than left at the default. The profile's [File](../profile.md#file) section is one part per delivery, and an export that takes whatever happens to be in the scene is the mechanism by which leftover objects and empty scenes reach a delivery. Requiring a selection makes the modeler state what the part is. The profile's [Scenes and nodes](../profile.md#scenes-and-nodes) section now requires exactly one node with no children, so a delivery cannot legitimately hold more than one object and this will not relax.

`at_collection_center` deserves attention. It is off by default and nothing in our guides mentions it, but switching it on relocates the origin of the exported result, which is the one thing the origin rules exist to control.

## Transform

| UI label | Identifier | Default | Ours |
|---|---|---|---|
| +Y Up | `export_yup` | True | required True, the default — the profile's [Axes](../profile.md#axes) section |

One option, and it is the whole of the coordinate conversion. On, it converts `(x, y, z)` to `(x, z, −y)` for vertices, normals and node TRS, producing the file the glTF specification describes: +Y up, and Blender's front, −Y, on +Z. That is what the profile's [Axes](../profile.md#axes) section requires, and the consumer then applies one fixed rotation onto the robotics axes: `<pose>0 0 0 1.5708 0 1.5708</pose>` in Gazebo, `rpy="0 0 1.5708"` in RViz on Lyrical. Off, Blender's Z-up axes pass through unchanged and every glTF viewer shows the part on its side. The [coordinate-systems reference](coordinate-systems.md#one-body-one-mesh-who-rotates-what) has the derivation.

Note what no check can do about it: `gltf-check` has no rule implementing the profile's [Axes](../profile.md#axes) section, because nothing in a file says which way its author meant up or forward. This setting is verifiable only by rendering: a part exported with it off lies on its side in the Sample Viewer.

## Data ▸ Scene Graph

| UI label | Identifier | Default | Ours |
|---|---|---|---|
| Flatten Object Hierarchy | `export_hierarchy_flatten_objs` | False | moot — the profile's [Scenes and nodes](../profile.md#scenes-and-nodes) section permits exactly one node with no children, so there is no hierarchy to flatten |
| Flatten Bone Hierarchy | `export_hierarchy_flatten_bones` | False | default — no armatures |
| Full Collection Hierarchy | `export_hierarchy_full_collections` | False | required False — it adds intermediate nodes |
| Remove Armature Object | `export_armature_object_remove` | False | default — no armatures |
| GPU Instances | `export_gpu_instances` | False | required False — `EXT_mesh_gpu_instancing`, and the profile's [Prohibited content](../profile.md#prohibited-content) section fails any `extensionsRequired` |

## Data ▸ Mesh

| UI label | Identifier | Default | Ours |
|---|---|---|---|
| Apply Modifiers | `export_apply` | False | open — see the note below |
| UVs | `export_texcoords` | True | required True — the profile's [Geometry](../profile.md#geometry) section requires `TEXCOORD_0` on every primitive |
| Normals | `export_normals` | True | required True — the profile's [Geometry](../profile.md#geometry) section requires `NORMAL` |
| Tangents | `export_tangents` | False | default False — neither consumer needs them |
| Vertex Colors | `export_vertex_color` | `'MATERIAL'` | open |
| … name | `export_vertex_color_name` | `'Color'` | default |
| … export all | `export_all_vertex_colors` | True | open — its own description says a fake `COLOR_0` may be created; see below |
| … active when no material | `export_active_vertex_color_when_no_material` | True | open |
| Attributes | `export_attributes` | False | required False — underscore-prefixed custom attributes are not in the profile |
| Loose Edges | `use_mesh_edges` | False | required False — the profile's [Geometry](../profile.md#geometry) section requires triangles |
| Loose Points | `use_mesh_vertices` | False | required False — same |
| Shared Accessors | `export_shared_accessors` | False | open — it changes accessor layout, which `glb_probe` reads |
| Geometry Nodes Instances | `export_gn_mesh` | False | open |

Two rows to settle by experiment.

`export_apply` is genuinely open. Leaving it off delivers the base mesh and ignores the modifier stack, which silently drops a bevel or a subdivision the modeler intended. Turning it on bakes modifiers and, per its own warning, prevents exporting shape keys — which we do not want anyway. The profile says nothing about modifiers.

`export_all_vertex_colors` defaults True and its description warns that "if no Vertex Color is used in the mesh materials, a fake `COLOR_0` will be created". A plain cube with no material exports with `POSITION`, `NORMAL` and `TEXCOORD_0` only, so the fake attribute does not appear in the simplest case. The condition that triggers it is not yet established.

Also worth recording: `export_texcoords` defaults True, and Blender's primitives carry a `UVMap`, so a normal Blender export satisfies the profile's [Geometry](../profile.md#geometry) section's `TEXCOORD_0` requirement without anyone thinking about it. Hand-authored files do not — `probe/coords/marker_yup.glb` fails rule 6 for exactly this reason.

## Data ▸ Material

| UI label | Identifier | Default | Ours |
|---|---|---|---|
| Materials | `export_materials` | `'EXPORT'` | required EXPORT — the profile's [Materials](../profile.md#materials) section |
| Images | `export_image_format` | `'AUTO'` | open — see below |
| Image quality | `export_image_quality` | 75 | open |
| JPEG quality | `export_jpeg_quality` | 75 | open |
| Create WebP | `export_image_add_webp` | False | required False — not in the profile |
| WebP fallback | `export_image_webp_fallback` | False | required False |
| Keep original textures | `export_keep_originals` | False | required False — its own warning says only one texture survives |
| Texture folder | `export_texture_dir` | `''` | n/a for GLB |
| Unused Images | `export_unused_images` | False | required False |
| Unused Textures | `export_unused_textures` | False | required False — its description says it needs a non-standard extension |
| Original PBR Specular | `export_original_specular` | False | default |

`export_image_format` is where the profile and the dialog do not line up. The profile's [Textures](../profile.md#textures) section requires PNG for normal, metallic, roughness and packed ORM maps and for anything carrying alpha. `AUTO` writes JPEG when the source image is JPEG, so the setting alone cannot deliver that — the fix is at the texture source, as the export guide says. Forcing `JPEG` is wrong for the linear slots, and `NONE` drops images entirely. So `AUTO` is correct and insufficient at the same time, which is worth stating rather than recording a tick.

Nothing in this panel controls `metallicFactor`. That is a material property in the scene, and it is the defect that recurs most in deliveries.

## Data ▸ Shape Keys, Skinning, Lighting

A static part has no shape keys, no armature and no lights, so all twelve options in these three panels stay at their defaults and none can affect the result.

| UI label | Identifier | Default | Ours |
|---|---|---|---|
| Shape Keys | `export_morph` | True | default — nothing to export |
| Skinning | `export_skins` | True | default — the profile's [Prohibited content](../profile.md#prohibited-content) section prohibits `skins`, but none exist without an armature |
| Lighting Mode | `export_import_convert_lighting_mode` | `'SPEC'` | default — applies to lights, which we do not export |

The nine remaining options are sub-settings of those three and are not enumerated here.

## Animation

There should be no animations. Change `export_animations` to False. Leaving it True is usually harmless because there are no animations to export, but better to be sure.

| UI label | Identifier | Default | Ours |
|---|---|---|---|
| Animation | `export_animations` | True | False — the profile's [Prohibited content](../profile.md#prohibited-content) section prohibits `animations` |

With `export_animations` off, the other 25 options in this group have no effect and are not enumerated here.

## Compression

All of it is prohibited by the profile's [Prohibited content](../profile.md#prohibited-content) section, one way or another, and all of it is off by default.

| UI label | Identifier | Default | Ours |
|---|---|---|---|
| Draco | `export_draco_mesh_compression_enable` | False | required False — the profile's [Prohibited content](../profile.md#prohibited-content) section prohibits `KHR_draco_mesh_compression` |
| Meshopt | `export_meshopt_compression_enable` | False | required False — it lands in `extensionsRequired`, which the profile's [Prohibited content](../profile.md#prohibited-content) section fails outright |
| gltfpack | `export_use_gltfpack` | False | required False — it converts textures to KTX2/BasisU, which is `KHR_texture_basisu`, prohibited |

The 19 quantization and quality sub-settings of those three are not enumerated here.

Draco is absent from this Blender install regardless: `libextern_draco.so` is not present, and the exporter says so at load. So the prohibition is currently enforced by the build as well as by the rule.

## What this enumeration suggests, and needs checking

A reading worth testing rather than adopting. Of the 110 options, four are changed from the default and nine are confirmed at it. Two of the four changes are provenance rather than geometry (`will_save_settings`, `export_copyright`) and one is belt and braces (`export_animations`, which produces nothing either way on a scene with no actions). That leaves `use_selection` as the only change that alters what a clean scene exports.

If that holds, then the defects in delivered files do not come from the export dialog. They come from the scene: transforms not applied, `metallicFactor` left to a node graph the exporter cannot read, `Cube.001` names, leftover empty scenes, JPEG source textures, `BLEND` on an opaque hull. None of those is a checkbox in this dialog, which is why the four items under [Four things that decide the result and are not in this dialog](#four-things-that-decide-the-result-and-are-not-in-this-dialog) carry more weight than the thirteen that are.

That sits awkwardly against the opening line of our [export guide](../walkthroughs/exporting-from-blender.md), which says most defects "are export defaults rather than modelling mistakes". Both can be true if "defaults" is read broadly enough to include Blender's material and naming defaults, and the guide's own examples are mostly of that kind. Worth resolving in wording once the rows below are settled.

## Open rows, as a worklist

- `export_apply` — do we want modifiers baked, and does the answer differ for a delivery versus a working file?
- `export_image_format` — the wording that makes clear `AUTO` is necessary and not sufficient.
- `export_all_vertex_colors` and the rest of the vertex-colour group — what actually triggers the fake `COLOR_0`, and does any rule care?
- `export_extras` — a candidate for the manifest question in the profile's [manifest](../profile.md#the-manifest) section.
- `use_active_scene` — whether it, rather than `use_selection` alone, is how "exactly one scene" in the profile's [Scenes and nodes](../profile.md#scenes-and-nodes) section gets enforced at export time.
- `export_shared_accessors` — whether it changes what `glb_probe` reports.
- `export_current_frame` — whether a static part is safe on the default.

Settled by this review and no longer open: `use_selection` (True), `will_save_settings` (True), `export_copyright` (`Copyright Honu Robotics`), `export_animations` (False).
