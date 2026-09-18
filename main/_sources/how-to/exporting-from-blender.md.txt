# Exporting from Blender

Every delivery this project has received came out of `Khronos glTF Blender I/O`, and most of the defects found in them are export defaults rather than modelling mistakes. This page collects the ones that bite, each with what the export does and what to do instead.

None of it is a substitute for checking the result: run [`gltf-check`](checking-a-delivery.md) on the exported file, and open it in the Khronos Sample Viewer before delivering it.

## Author in the ROS frame, and let the exporter convert

Blender is Z-up and right-handed, the same convention as REP 103, so a part is modelled x forward, y left, z up — exactly the part frame the macro uses. The exporter then applies its fixed Y-up conversion, mapping (x, y, z) to (x, z, −y).

The consequence is that every delivered file has up on +Y and forward on +X. The +Y is glTF's requirement. The +X is a consequence of authoring in the robot's convention rather than a decision anyone recorded, and it differs from glTF's own statement that an asset faces +Z. Profile section 5.3 is the interim rule: keep authoring in the part frame, and do not re-orient a delivery to face +Z without agreement.

Do not rotate the part to "fix" its orientation for Gazebo. That correction happens downstream.

## Apply transforms before exporting

Profile section 5.5 requires exactly one root node carrying no rotation and no matrix. The exporter writes a Y-up conversion node when transforms are left unapplied, and that node is a genuine hazard rather than cosmetic: Gazebo pre-multiplies it and RViz post-multiplies it, so the same file lands differently in the two consumers.

Set the scene unit scale to 1.0 and apply object scale as well. A file at the wrong scale is silently wrong — nothing downstream can detect it, and two assets in the wider corpus are millimetre files corrected by a URDF `scale` further down.

## Name the object, not the mesh

Gazebo names each submesh after the node that instantiates the mesh — never after the mesh datablock and never after the material. The node name comes from the Blender object name, so renaming the mesh datablock changes nothing anyone sees.

Clear Blender's numeric suffixes. `Cube.001` and `blueboat_chassis.visual.001` are both real examples from delivered files, and the suffix travels into the node name. The root node must be named for the part, with no suffix and no spaces.

Check for leftover scenes too. Six delivered files carried empty extra scenes inherited from the Blender file; the profile requires exactly one.

## Metalness is the defect that keeps recurring

glTF's `metallicFactor` defaults to 1.0, and so does Blender's. A material where nobody set it is a material that says "metal", and a plastic hull renders as dark metal.

A metallic-roughness texture does not rescue it by existing. The effective metalness is the factor multiplied by the texture's blue channel, so only a dark blue channel brings it down. Every metallic-roughness map measured in this project's library is a solid colour with B = 255, which means the factor was doing the deciding all along — and in four of fifteen parts the factor was unset.

Two fixes, either is fine: set `metallicFactor` to 0 for anything not genuinely metallic, or author a black metallic channel and carry roughness as a factor rather than a map. Prefer stating the factor, because it is readable without decoding an image.

## Texture format is decided by the source image

Under its default Automatic image setting the exporter writes JPEG when the source image is JPEG. So a preset change alone will not get PNG normal maps out of a project whose source textures are JPEG — the fix is at the texture source.

This matters because chroma subsampling blends channels that are unrelated in a normal or ORM map, and converting an existing JPEG to PNG preserves the damage rather than undoing it. A re-export from the original texture is the remedy.

Profile section 8 requires PNG for normal, metallic, roughness and packed ORM maps, and for anything carrying alpha. Base colour and emissive may be JPEG. Textures are capped at 2048 pixels on each side.

Be aware that the corpus disagrees with this rule more sharply than with any other in the profile: counted by image, normal maps in the wider corpus run 38 JPEG to 4 PNG. The rule is about what this project accepts, not a description of what arrives.

## Transparency is per material, not per pixel

Plan transparency per material. For cutouts — vents, perforations, mesh guards — use `alphaMode: MASK` with `alphaCutoff` 0.5 and binary alpha in a PNG base colour.

Do not tag an opaque part `BLEND`. Gazebo ignores `BLEND` and renders the material opaque, so the result looks fine there and is wrong everywhere else. One delivered chassis reached us exactly this way: 0.56% of its base colour map is a cutout region, and the whole hull had been tagged `BLEND` to handle it.

## Versions

Every current delivery reports `Khronos glTF Blender I/O v5.1.20`, which corresponds to Blender 5.1. Whether those versions get pinned is still open — profile section 11 has the proposal. The generator string records the tool but not the settings, so two files from the same exporter can still differ in image format, tangents and compression. That is why the checks constrain the outcome rather than the settings.
