# Blender glTF Export Options

Every option the Blender glTF exporter offers, with its default, so the correct settings for this project can be worked out one at a time rather than assumed. The export dialog has 110 properties and names only a handful of them in any guide we have written.

The `Ours` column is the point of the page. It is filled in where the profile already settles the question and left open where it does not, so the open rows are a worklist rather than a silence.

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

Every current delivery reports `Khronos glTF Blender I/O v5.1.20`, which is Blender 5.1. This page is one minor version ahead of the deliveries. Profile section 11 proposes pinning 5.1 and is Open; nothing here decides it.

## What no option does

There is no export option that applies object transforms. `export_apply` is Apply **Modifiers** — it evaluates the modifier stack, and it has nothing to do with an object's location, rotation or scale.

Profile section 5.5 requires the root node to carry no rotation and no matrix, and that is achieved in the scene, with `Object ▸ Apply ▸ All Transforms`, before the export dialog is ever opened. An object left with a rotation exports as a node with a rotation no matter how the dialog is set. Our own [export guide](../how-to/exporting-from-blender.md) says "Apply transforms before exporting" under a heading that invites this confusion, and the distinction belongs there too.

## The four options that decide coordinates

Out of 110, these are the ones that touch where the geometry lands:

| Option | Identifier | Default | Ours |
|---|---|---|---|
| +Y Up | `export_yup` | True | required True — profile 5.2 |
| Format | `export_format` | GLB | required GLB — profile 4.2 prohibits `.gltf` |
| Apply Modifiers | `export_apply` | False | open — see below |
| Limit to ▸ Selected Objects | `use_selection` | False | practice True when the scene holds more than the part | % CLAUDE: I think we want to prescribe that this is true.

Everything else in the dialog is payload, compression or animation.

## Top of the dialog

| UI label | Identifier | Default | Ours |
|---|---|---|---|
| Format | `export_format` | GLB | required GLB — profile 4.2 |
| Copyright | `export_copyright` | `''` | open — a candidate for the manifest question in profile 4.1.1 | % CLAUDE: Copyright Honu Robotics ad default
| Remember Export Settings | `will_save_settings` | False | open — True would make a `.blend` carry its own settings, which is one answer to the preset proposal in profile 11 |  % CLAUDE: Set true so that the .blend artifacts (source) will inlcude the settings used to export, which helps in 
| File path | `filepath` | `''` | naming is governed by profile 4.1: `<part>.visual.glb` |
| Check Existing | `check_existing` | True | default |
| Filter | `filter_glob` | `'*.glb'` | default |
| Caller id | `gltf_export_id` | `''` | default |
| Log Level | `export_loglevel` | −1 | default |
| Settings category | `ui_tab` | `'GENERAL'` | UI only |

`export_format`'s enum items are built dynamically, so headless introspection returns an empty list and a warning. The default is binary, which `filter_glob` confirms.

## Include

| UI label | Identifier | Default | Ours |
|---|---|---|---|
| Limit to ▸ Selected Objects | `use_selection` | False | practice True — profile 4.1 is one part per delivery | % CLAUDE: Set to true for now - may relax later, but 
| Limit to ▸ Visible Objects | `use_visible` | False | default |
| Limit to ▸ Renderable Objects | `use_renderable` | False | default |
| Limit to ▸ Active Collection | `use_active_collection` | False | default |
| … with Nested Collections | `use_active_collection_with_nested` | True | default |
| Limit to ▸ Active Scene | `use_active_scene` | False | open — profile 5.5 requires exactly one scene, and six deliveries carried leftover empty ones |
| Collection by name | `collection` | `''` | default |
| At Collection Center | `at_collection_center` | False | required False — it would move the origin, which profile 5.4 and 5.6 govern |
| Data ▸ Custom Properties | `export_extras` | False | open — the archive-the-source question in profile 4.1.1 |
| Data ▸ Cameras | `export_cameras` | False | required False — profile 10 prohibits `cameras` |
| Data ▸ Punctual Lights | `export_lights` | False | required False — profile 10 prohibits `KHR_lights_punctual` |

`at_collection_center` deserves attention. It is off by default and nothing in our guides mentions it, but switching it on relocates the origin of the exported result, which is the one thing the origin rules exist to control.

## Transform

| UI label | Identifier | Default | Ours |
|---|---|---|---|
| +Y Up | `export_yup` | True | required True — profile 5.2 |

One option, and it is the whole of the coordinate conversion. On, it swizzles `(x, y, z) → (x, z, −y)` for vertices and for node TRS. Off, Blender's Z-up axes pass through unchanged and the file is wrong for every consumer that assumes glTF is Y-up.

Note what no check can do about it: `gltf-check` has no rule implementing profile 5.2's Y-up MUST, because nothing in a file says which way its author meant up. This setting is verifiable only by rendering.

## Data ▸ Scene Graph

| UI label | Identifier | Default | Ours |
|---|---|---|---|
| Flatten Object Hierarchy | `export_hierarchy_flatten_objs` | False | open — profile 5.5's multi-node question, review decision 15 |
| Flatten Bone Hierarchy | `export_hierarchy_flatten_bones` | False | default — no armatures |
| Full Collection Hierarchy | `export_hierarchy_full_collections` | False | required False — it adds intermediate nodes |
| Remove Armature Object | `export_armature_object_remove` | False | default — no armatures |
| GPU Instances | `export_gpu_instances` | False | required False — `EXT_mesh_gpu_instancing`, and profile 10 fails any `extensionsRequired` |

## Data ▸ Mesh

| UI label | Identifier | Default | Ours |
|---|---|---|---|
| Apply Modifiers | `export_apply` | False | open — see the note below |
| UVs | `export_texcoords` | True | required True — profile 6 requires `TEXCOORD_0` on every primitive |
| Normals | `export_normals` | True | required True — profile 6 requires `NORMAL` |
| Tangents | `export_tangents` | False | default False — neither consumer needs them |
| Vertex Colors | `export_vertex_color` | `'MATERIAL'` | open |
| … name | `export_vertex_color_name` | `'Color'` | default |
| … export all | `export_all_vertex_colors` | True | open — its own description says a fake `COLOR_0` may be created; see below |
| … active when no material | `export_active_vertex_color_when_no_material` | True | open |
| Attributes | `export_attributes` | False | required False — underscore-prefixed custom attributes are not in the profile |
| Loose Edges | `use_mesh_edges` | False | required False — profile 6 requires triangles |
| Loose Points | `use_mesh_vertices` | False | required False — same |
| Shared Accessors | `export_shared_accessors` | False | open — it changes accessor layout, which `glb_probe` reads |
| Geometry Nodes Instances | `export_gn_mesh` | False | open |

Two rows to settle by experiment.

`export_apply` is genuinely open. Leaving it off delivers the base mesh and ignores the modifier stack, which silently drops a bevel or a subdivision the modeler intended. Turning it on bakes modifiers and, per its own warning, prevents exporting shape keys — which we do not want anyway. The profile says nothing about modifiers.

`export_all_vertex_colors` defaults True and its description warns that "if no Vertex Color is used in the mesh materials, a fake `COLOR_0` will be created". A plain cube with no material exports with `POSITION`, `NORMAL` and `TEXCOORD_0` only, so the fake attribute does not appear in the simplest case. The condition that triggers it is not yet established.

Also worth recording: `export_texcoords` defaults True, and Blender's primitives carry a `UVMap`, so a normal Blender export satisfies profile 6's `TEXCOORD_0` requirement without anyone thinking about it. Hand-authored files do not — `probe/coords/marker_yup.glb` fails rule 6 for exactly this reason.

## Data ▸ Material

| UI label | Identifier | Default | Ours |
|---|---|---|---|
| Materials | `export_materials` | `'EXPORT'` | required EXPORT — profile 7 |
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

`export_image_format` is where the profile and the dialog do not line up. Profile section 8 requires PNG for normal, metallic, roughness and packed ORM maps and for anything carrying alpha. `AUTO` writes JPEG when the source image is JPEG, so the setting alone cannot deliver that — the fix is at the texture source, as the export guide says. Forcing `JPEG` is wrong for the linear slots, and `NONE` drops images entirely. So `AUTO` is correct and insufficient at the same time, which is worth stating rather than recording a tick.

Nothing in this panel controls `metallicFactor`. That is a material property in the scene, and it is the defect that recurs most in deliveries.

## Data ▸ Shape Keys, Skinning, Lighting

| UI label | Identifier | Default | Ours |
|---|---|---|---|
| Shape Keys | `export_morph` | True | harmless — no shape keys in a static part |
| … Normals | `export_morph_normal` | True | harmless |
| … Tangents | `export_morph_tangent` | False | harmless |
| … Sparse Accessor | `export_try_sparse_sk` | True | harmless |
| … omit if empty | `export_try_omit_sparse_sk` | False | harmless |
| Skinning | `export_skins` | True | harmless — profile 10 prohibits `skins`, but none exist without an armature |
| … bone influences | `export_influence_nb` | 4 | n/a |
| … all influences | `export_all_influences` | False | n/a |
| Deformation bones only | `export_def_bones` | False | n/a |
| Add Leaf Bones | `export_leaf_bone` | False | n/a |
| Rest position armature | `export_rest_position_armature` | True | n/a |
| Lighting Mode | `export_import_convert_lighting_mode` | `'SPEC'` | default — applies to lights, which we do not export |

## Animation

There shoudl be no animations.  Change `export_animations` to False. (Leaving it True is usually harmless becaue there are no anmations, but better to be sure)
| UI label | Identifier | Default | Ours |
|---|---|---|---|
| Animation | `export_animations` | True | False — harmless either way for a static part |

By removing `export_animations` we can safely ignore the rest.

## Compression

All of it is prohibited by profile section 10, one way or another, and all of it is off by default.

| UI label | Identifier | Default | Ours |
|---|---|---|---|
| Draco | `export_draco_mesh_compression_enable` | False | required False — profile 10 prohibits `KHR_draco_mesh_compression` |

Remainder is omitted for brevity. 

## What this enumeration suggests, and needs checking

A reading worth testing rather than adopting. Of the 110 options, exactly one has to be confirmed rather than changed (`export_yup`, already True), one is governed by the profile and matches the default (`export_format`), and the rest are either payload for features we do not use or prohibitions that are already off.

If that holds, then the defects in delivered files do not come from the export dialog. They come from the scene: transforms not applied, `metallicFactor` left to a node graph the exporter cannot read, `Cube.001` names, leftover empty scenes, JPEG source textures, `BLEND` on an opaque hull. None of those is a checkbox in this dialog.

That sits awkwardly against the opening line of our [export guide](../how-to/exporting-from-blender.md), which says most defects "are export defaults rather than modelling mistakes". Both can be true if "defaults" is read broadly enough to include Blender's material and naming defaults, and the guide's own examples are mostly of that kind. Worth resolving in wording once the rows below are settled.

## Open rows, as a worklist

- `export_apply` — do we want modifiers baked, and does the answer differ for a delivery versus a working file?
- `export_all_vertex_colors` and the rest of the vertex-colour group — what actually triggers the fake `COLOR_0`, and does any rule care?
- `export_extras` and `export_copyright` — both are candidates for the manifest question in profile 4.1.1.
- `will_save_settings` — a per-`.blend` alternative to the shipped export preset proposed in profile 11.
- `use_selection` and `use_active_scene` — the mechanism for "one part, one scene" in profile 4.1 and 5.5.
- `export_shared_accessors` — whether it changes what `glb_probe` reports.
- `export_current_frame` — whether a static part is safe on the default.
- `export_image_format` — the wording that makes clear `AUTO` is necessary and not sufficient.
