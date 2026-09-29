# Honu glTF Asset Workflow

The [profile](profile.md) states what a delivered visual model must be. This document states the process that produces and integrates the asset.

The process begins with a commission, a vehicle or a batch of parts to be modeled, and ends when the integrator accepts the delivered files. Placing an accepted part in the simulation model, the macro and the RViz correction, is the consuming project's work and is out of scope here.

## Roles

The two parties are the modeler, who authors and delivers the visual model, and the integrator, who commissions it, checks it and integrates it as a robot component.

These and the other terms this document uses, among them part, delivery, commission and datasheet, are defined in the project [glossary](reference/glossary.md).

## Outline

| Step | Owner | Input | Output | Gate to the next step |
|---|---|---|---|---|
| 1. Commission | Integrator | Reference material, datasheets, the vehicle's datum decision | One commission per vehicle or batch of parts, one block per part | Every block complete and agreed with the modeler |
| 2. Model | Modeler | The commission and the profile | One `<part>.visual.glb` per part, manifest filled from the commission | The modeler's own checks pass |
| 3. Verify | Modeler, then integrator | The delivery and the commission | Acceptance, or a request for modification | All checks pass |

## Step 1: Commission

The integrator writes the commission before any modeling starts. It is the written statement of intent and is what the visual checks in step 3 are judged against. Compliance with intent can only be verified when both parties share a clear understanding of the intent and of the design decisions behind it.

### What the commission contains

To write: expand each item to one sentence. Each item names the profile rule and the manifest property it feeds, so the manifest in step 2 is copied from the commission.

For the whole commission:

- Sources: datasheets, drawings, vendor pages, and any CAD, scans or vendor models handed over ([the manifest](profile.md#the-manifest), `dc:relation`, `dc:source`)
- Licensing and texture redistribution terms (`dc:rights`). For Honu Robotics' own work the usual entry is "Copyright 2026 Honu Robotics. Licensed under the Apache License, Version 2.0." A purchased texture adds its own redistribution terms
- The base part, exactly one per vehicle, and the vehicle's datum decision ([what the manifest carries](profile.md#what-the-manifest-carries), `gltfrp:partRole`)
- The authoring toolchain the modeler will use, checked against the versions pinned in the profile's [authoring toolchain](profile.md#authoring-toolchain) section
- Whether the `.blend` and CAD will be archived, and if so where (`xmpMM:DerivedFrom`)

For each part:

- Part name, following the profile's [file naming](profile.md#file-naming) rule
- Reference images, with what each view shows and what matters in it
- Cited dimensions, each as a named quantity with its source, and the tolerance held, or an explicit statement that no published figure exists (`gltfrp:nominalDimension`, `gltfrp:dimensionTolerance`)
- The datum point: the single geometric feature the origin of the part coordinate system is referenced to ([datum specification](profile.md#datum-specification), `gltfrp:datumPoint`). Orientation is not specified per part; the profile's [axes](profile.md#axes) rule fixes it for every delivery, following ISO 9787 and REP 103 and not glTF's own convention
- Datum targets where a physical realization exists (`gltfrp:datumTarget`)
- The feature that defines forward, and its sense, where the shape does not determine it ([forward axis](profile.md#forward-axis))
- Visual requirement: how much detail the part needs. State the distance it is normally viewed from, which features must be recognizable at that distance, and which may be simplified or left out
- Materials: for each visible region, what it is made of, whether that is metal or non-metal, and a photo or a named finish to match ([materials](profile.md#materials), [textures](profile.md#textures)). Metal or non-metal is stated because glTF treats a material as metal unless told otherwise
- Openings and see-through regions, each listed by name: vents, perforations and mesh guards that are cut out, and windows, lenses or tubes that are translucent ([transparency](profile.md#transparency))
- Priorities: what matters most on this part, in order
- Notes to the modeler

### Agreeing the commission

Three moves, all before modeling starts:

1. The written commission goes to the modeler.
2. A meeting walks through it against the reference images, so intent is clarified in conversation rather than inferred from text.
3. The integrator issues the final written part-by-part priorities, amended by what the meeting found.

To write: how a change to the commission after this point is handled. It is written down, not agreed in passing.

### Gate

Every part block has a name, a datum point, a cited dimension or an explicit "none published", and a visual requirement. The modeler has the final version in hand. A modeler who starts a part without a datum point stops and asks; there is no default, and nothing downstream can recover the intent.

## Step 2: Model

### Build to the profile

The profile's sections from [Coordinate systems and units](profile.md#coordinate-systems-and-units) to [Prohibited content](profile.md#prohibited-content) are the rules the model is built to. The [Blender export guide](walkthroughs/exporting-from-blender.md) is the tool-specific practice for meeting them, and the [walkthrough](walkthroughs/blender_mesh_coordinate_ex.md) shows one file going through end to end. The origin is placed by evaluating the datum specification against the geometry, never chosen from a menu ([Origin](profile.md#origin)).

### Export

To write: one paragraph. The toolchain pin ([Authoring toolchain](profile.md#authoring-toolchain)), the exporter's `+Y Up` option off ([Axes](profile.md#axes)), clear location and rotation and apply scale before export ([Scenes and nodes](profile.md#scenes-and-nodes)), and the authoring source kept outside the simulation repository and cited from the manifest.

### Fill the manifest from the commission

Every `gltfrp:` and `dc:` value in [the manifest](profile.md#the-manifest) is copied from the commission block for that part. This is the mechanism that lets step 3 compare the delivery with what was asked for, and it is why the commission names the property beside each field.

### Gate

The modeler's own checks in step 3 pass. The delivery is one `<part>.visual.glb` per part, named per the profile's [File naming](profile.md#file-naming) section, plus whatever the commission asked to accompany it.

## Step 3: Verify

The profile's [Conformance](profile.md#conformance) section asks four questions of a delivery: valid, intended, compliant, usable. They fail independently and no single tool answers more than one. The first two are the modeler's to answer before delivering, the last two the integrator's after. The split is stated here so that neither party assumes the other checked the thing.

### What the modeler checks

The Khronos glTF Validator answers whether the file is legal glTF. It is a single binary from the [glTF-Validator releases](https://github.com/KhronosGroup/glTF-Validator/releases), and the Sample Viewer runs the same validator inline. The delivery passes with zero errors. Warnings and infos are read and explained: a warning that a normal-mapped primitive has no tangents is expected, because neither consumer reads them ([Geometry](profile.md#geometry)). A clean run says nothing about whether the materials are right, since the validator cannot know that a plastic hull reads as metal.

```bash
gltf_validator -o -a <part>.visual.glb
```

The [Khronos Sample Viewer](https://github.khronos.org/glTF-Sample-Viewer-Release/) answers whether the file looks as intended, judged by a person against the commission's images and material notes. The viewer assumes glTF's Y-up convention and shows every conforming part on its side; read it for materials, textures, transparency and validity, and ignore the pose. Blender's viewport answers nothing, because it shows Blender's materials and not the exported file. Other viewers, such as Babylon, three.js and F3D, are useful for inspecting names and material assignment and are not the reference.

`gltf-check` answers whether the file satisfies the profile: no failures, every warning understood. It reads the file and does not render it, so it needs no Gazebo and no GPU. It covers the container and header, extensions, scene and node structure, primitive attributes, materials, image format and size, transparency and the manifest. How to read its output is in the [checking walkthrough](walkthroughs/checking-a-delivery.md).

`gltf-summary` shows where the origin sits, and the origin line has to agree with the datum specification. An origin on a mounting face reads 0.00 or 1.00 on that axis; 0.50 on all three axes is the bounding-box midpoint and almost always means the origin was inherited and not specified.

The modeler delivers with a note that these four were done. The integrator does not repeat the first two.

### What the integrator checks

`gltf-check` again, with the output kept with the review.

`glb_probe` loads the file through the installed `gz-common`, exactly as Gazebo does, and prints the submeshes and materials the loader built. It is built and run inside drydock; the command is in the [probe README](https://github.com/HonuRobotics/gltf-robotics/tree/main/probe). The delivery passes when the output has no `[error]` lines, every submesh has a material, and the submesh name equals the part name. It is the only stand-in for Gazebo that needs no GPU. It does not render, so it settles what a material is and not how it looks.

Gazebo, in the parts world: scale against a known object, orientation and origin, then the material defects by name. White-metal patches mean a primitive with no material, a dark hull means metalness was left at its default, cutouts have to be cut, and thin parts have to be visible from both sides. Other viewers do not predict any of this, because they honor `BLEND`, `doubleSided` and extensions that Gazebo ignores.

RViz with the URDF: the part renders, is upright and RViz stays up. Passing in Gazebo is necessary and never sufficient; a normal map with no base color renders in Gazebo and terminates RViz.

Extents against the datasheet, within the specified tolerance, and the manifest's cited dimension matching the commission.

Origin and orientation by eye against the datum specification, naming what the origin sits on in the part's own terms.

The commission's visual requirement and priorities, the one check with a written answer key.

### When the checks run

The checks run when a delivery is reviewed, which is the moment it can be rejected. They are not CI tests: once a part is merged it has already been checked, and rerunning every check on every commit would slow every unrelated change. The consuming project's base color guard stays in its tests, because it is cheap and it catches a defect that terminates RViz. No probe output is committed per part; the checker output kept with the review is the record.

### Who answers what

| Question | Asked by | Tool | Passes when |
|---|---|---|---|
| Valid | Modeler | Khronos Validator | Zero errors |
| Intended | Modeler | Sample Viewer, against the commission | Signed off by the modeler, pose ignored |
| Compliant | Modeler, then integrator | `gltf-check` | No failures, warnings reviewed, open items discussed |
| Usable | Integrator | `glb_probe`, Gazebo, RViz | Loads, renders upright, RViz stays up |
| Matches the commission | Integrator | `gltf-summary`, datasheet, eyes | Within tolerance, datum recognized, priorities met |

The last row is this workflow's own gate rather than a profile question. Not every failure is the modeler's to fix: a defect that turns out to be a consumer limitation becomes a target constraint recorded in the profile, not a rejection.

### Rejection and redelivery

A rejection names the question that failed and either the profile section or the commission field behind it, with the tool output attached. A disagreement is then with a rule or a field, not with a person.

A redelivery is a complete delivery under the same part name, with the manifest's date updated and the modeler's four checks redone. The integrator reruns every check, not only the one that failed, because a `.glb` is opaque in a diff and the previous run's output kept with the review is the only before-and-after comparison.

If the failure was the commission's, wrong or silent on the point, step 1 reopens and the block is amended before the modeler works again.

### Gate

All five rows pass. The integrator records the accepted delivery date and the checker output, and the part goes to the consuming project's [add-part procedure](https://honurobotics.github.io/bluerobotics_models/lyrical/how-to/add-part.html).

## After acceptance

Out of scope here. The consuming project owns placement, the part macro and the RViz correction.

## Not settled here

- Visual requirement tiers have no numbers until the profile's [Budgets](profile.md#budgets) section closes.
- A component part's datum is a SHOULD ([component part](profile.md#a-component-part)), so a component block may leave it out; this document does not decide whether it should.
- Where the filled commission is archived is the consuming project's decision.
- Whether the modeler delivers anything besides the visual model, such as collision geometry or a `model.sdf`. The profile covers the visual model only ([Scope](profile.md#scope)), so today that is whatever the commission asks for.

Open in the step 3 checks:

- Which release of the Khronos validator is used. The profile's [Authoring toolchain](profile.md#authoring-toolchain) section does not pin it.
- Whether a metallic-roughness texture's metallic channel matches the material. Settling it needs the decoded texels, which `gltf-check` does not read, so it warns and a person decides.
- Triangle budgets have no check until the profile's [Budgets](profile.md#budgets) section closes, and per-map texture size caps have none until the profile's [Textures](profile.md#textures) section closes. `gltf-check` enforces only the 2048 px ceiling.
- Extents are compared with the datasheet by hand. Nothing yet compares the measured extent with the manifest's `gltfrp:nominalDimension` and tolerance.
- A headless render of the parts world, so a redelivery can be compared before and after without a GUI session. Not built.
