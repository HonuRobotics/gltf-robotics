# Exporting from Blender

Every delivery this project has received came out of `Khronos glTF Blender I/O`, and most of the defects found in them are export defaults rather than modelling mistakes. This page collects the ones that bite, each with what the export does and what to do instead.

None of it is a substitute for checking the result: run [`gltf-check`](checking-a-delivery.md) on the exported file, and open it in the Khronos Sample Viewer before delivering it. The viewer assumes glTF's convention and so does the file, so a correct export stands upright and faces the camera; the viewer answers orientation as well as materials, textures and transparency.

## Author in Blender's own convention, and let the exporter convert

Build the part the way Blender expects: front toward −Y, which is what the Front view (numpad 1) looks at, and up +Z. Leave the exporter's `+Y Up` option **on**, its default. The exporter maps Blender (x, y, z) to glTF (x, z, −y), so the file comes out in glTF's own convention, +Y up and +Z forward, which is what the profile's [Axes](../profile.md#axes) section requires.

The conversion to the robotics axes is the integrator's, not yours: Gazebo places the part with `<pose>0 0 0 1.5708 0 1.5708</pose>` on the visual, and the URDF visual carries `rpy="0 0 1.5708"` on Lyrical, where RViz rotates glTF on load, or `rpy="1.5708 0 1.5708"` on Jazzy and Kilted, where it does not. Do not rotate the part in Blender to compensate for either consumer. The [coordinate-systems reference](../reference/coordinate-systems.md#one-body-one-mesh-who-rotates-what) explains who rotates what.

## Clear location and rotation, apply scale, before exporting

The profile's [Scenes and nodes](../profile.md#scenes-and-nodes) section requires exactly one node carrying no translation, rotation, scale or matrix. Any object transform left unapplied in Blender is written as that node's TRS, and a node transform is a genuine hazard rather than cosmetic: Gazebo composes it outside its (absent) correction and RViz composes it inside its rotation, so the same file lands in two different places in the two consumers.

Getting there is not "apply all transforms", which is the instruction you will expect. Applying a location or a rotation holds the geometry still in the world and moves the origin relative to the part, which destroys the datum the profile's [Origin](../profile.md#origin---datum-coordinate-system-location) section requires; clearing them moves the geometry with the object and preserves it. Scale is the exception and must be applied, because clearing it changes the part's size. Set the scene unit scale to 1.0 as well. A file at the wrong scale is silently wrong — nothing downstream can detect it, and two assets in the wider corpus are millimetre files corrected by a URDF `scale` further down.

## Where the origin goes is not yours to choose

The part's coordinate system is specified before modelling starts, by naming the features it is referenced to — its datum. The profile's [Origin](../profile.md#origin---datum-coordinate-system-location) and [Datum specification](../profile.md#datum-specification) sections have the rule. Your job is to put the object origin where that specification puts it, so the origin arrives with the commission rather than being decided at the keyboard.

Four steps, in this order:

1. **Read the datum specification.** It names features of the part and says which degrees of freedom each one removes: a mounting face, a bore axis, a locating pin. Between them they fix all six, and that is what determines both the origin and the axis directions. If you were not given one, stop and ask — there is no default, and nothing downstream can recover the intent.
2. **Set the object origin to the datum origin.** Whatever it takes in Blender: snap the 3D cursor to a vertex, an edge midpoint or a face centre and use `Origin to 3D Cursor`, or place an empty and snap to that.
3. **Bring the object to the world origin**, with its datum axes aligned to the world axes: clear location and rotation, apply scale, as above. The datum now coincides with Blender's world origin, which is what makes node space, scene space and the part's coordinate system the same thing.
4. **Export** with `+Y Up` on, the default.

**Do not use Set Origin's centre options to decide the origin.** Blender offers four — the vertex mean, the bounding-box midpoint, the surface centroid and the volume centroid — and none of them is a datum. They are measurements of the mesh: they move when the mesh changes, they reference no feature, and a different one is a different answer. Two of them are also traps. The `Center` option defaults to `Median`, which is the arithmetic **mean** of the vertex coordinates and not a median at all; and which of the two it uses is silently taken from the viewport's Transform Pivot Point unless you override it in the operator panel. So the same menu click gives different results in different sessions.

A quick way to tell whether the origin ended up anywhere meaningful: run [`gltf-summary`](checking-a-delivery.md) on the export and read its `origin at` line. An origin on a mounting face reads `0.00` or `1.00` on the axis normal to that face. An origin reading `0.50` on all three axes is sitting at the midpoint of the bounding box, which is almost always a sign it was inherited rather than specified.

**Carrying a direction the shape does not determine.** Some parts have a forward that no feature implies — a symmetric housing that must nonetheless face a particular way. Add the feature: a plane whose normal is the forward direction, or an empty, and name it in the datum specification so it is part of the part's definition rather than something you remembered. The specification has to state which side of the plane is forward, because a plane alone gives an axis and not a sense.

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

The profile's [Textures](../profile.md#textures) section requires PNG for normal, metallic, roughness and packed ORM maps, and for anything carrying alpha. Base colour and emissive may be JPEG. Textures are capped at 2048 pixels on each side.

Be aware that the corpus disagrees with this rule more sharply than with any other in the profile: counted by image, normal maps in the wider corpus run 38 JPEG to 4 PNG. The rule is about what this project accepts, not a description of what arrives.

## Transparency is per material, not per pixel

Plan transparency per material. For cutouts — vents, perforations, mesh guards — use `alphaMode: MASK` with `alphaCutoff` 0.5 and binary alpha in a PNG base colour.

Do not tag an opaque part `BLEND`. Gazebo ignores `BLEND` and renders the material opaque, so the result looks fine there and is wrong everywhere else. One delivered chassis reached us exactly this way: 0.56% of its base colour map is a cutout region, and the whole hull had been tagged `BLEND` to handle it.

## Keep the authoring source, outside the simulation repository

A delivered `.glb` is an export, and an export is lossy in one direction that matters: you cannot get the modifier stack, the material node graph, the UV seams or the named datum features back out of it. So keep the `.blend`, and the CAD it came from if there was any.

It does not belong in the simulation repository — it is large, it is binary, it changes wholesale on every save, and nothing in the build reads it. Keep it wherever the project keeps things that must survive without being versioned alongside code, and cite it in the manifest's `xmpMM:DerivedFrom` so a delivered file says where its source went.

This is a practice rather than a rule. The profile's [manifest](../profile.md#the-manifest) section does not require the archive, because whether a file was kept is not a property of the file that arrived. What it does say is that if you keep one, the manifest should point at it, which costs nothing.

## Versions

The toolchain is pinned at patch level in the profile's [Authoring toolchain](../profile.md#authoring-toolchain) section: Blender 5.2.2 LTS with `io_scene_gltf2` 5.2.40, which writes `asset.generator` as `Khronos glTF Blender I/O v5.2.40`. Earlier deliveries report `v5.1.20`, which is Blender 5.1; they predate the pin and are not held to it.

The generator string records the tool and never the settings, so two files from the same exporter can still differ in image format, tangents and compression. That is why the checks constrain the outcome rather than the settings, and why `will_save_settings` is worth turning on — it puts the settings in the `.blend` where a re-export can reproduce them.
