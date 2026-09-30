# Honu glTF Asset Workflow

The [profile](profile.md) states what a delivered visual model must be. This document states the process that produces one for each part and takes it through conformance testing.

The process begins with a commission, a vehicle or a batch of parts to be modeled, and ends when each delivered part passes the profile's [conformance testing](profile.md#conformance-testing) and the integrator accepts it. What it produces is individual parts with the correct properties.

Turning accepted parts into a working simulation model is downstream work and out of scope here: declaring joints and actuators, adding sensors and plugins, buoyancy, the part macro and the RViz correction.

## Roles

The two parties are the modeler, who authors and delivers the visual model, and the integrator, who commissions it, checks it and integrates it as a robot component.

These and the other terms this document uses, among them part, delivery, commission and datasheet, are defined in the project [glossary](reference/glossary.md).

## Outline

| Step | Owner | Input | Output | Gate to the next step |
|---|---|---|---|---|
| 1. Commission | Integrator | Reference material, datasheets, the vehicle's datum decision | One commission per vehicle or batch of parts, one block per part | Every block complete and agreed with the modeler |
| 2. Model | Modeler | The commission and the profile | One `<part>.visual.glb` per part, manifest filled from the commission | The modeler's own checks pass |
| 3. Verify | Modeler, then integrator | The delivery and the commission | Acceptance, or a request for modification | All checks pass |

## Step 1: Commission [Integrator]

The integrator writes the commission before any modeling starts. It is the written statement of intent and is what the visual acceptance checks are judged against. Compliance with intent can only be verified when both parties share a clear understanding of the intent and of the design decisions behind it.

### Commission YAML file 

The commission is a YAML file, see [commission template](commission-template.yaml), which shows every field with an example. This meta data will be written into the `.glb` file later in the process.  

Half of the fields are the manifest wich will be written into the `.glb` file later in the process.  The other half are notes and links for the modeler.  

If any modifications are needed to keep the commission YAML file in alignment with the modeling deliverable, the written YAML file should be updated.  At delivery, the YAML commission and part geometry should agree.

## Step 2: Author 3D asset [Modeler]

### Build to the [Honu Asset Profile](./profile.md) and export

The profile inlcudes the rules the model is built to. 

The [Blender export guide](walkthroughs/exporting-from-blender.md) is the tool-specific practice for meeting them.

### Step 3: Fill the `.glb` manifest from the commission YAML [Integrator]

After export, one command writes [the manifest](profile.md#the-manifest) into the file:

```bash
gltf-manifest commission.yaml <part>.visual.glb
```

It finds the part's block in the commission by the file's name and copies the values in. It fills in the forward and up axes as `+X` and `+Z`, and the delivery date as today. Only the file's metadata changes; the geometry and textures are copied through untouched.

The command refuses a key it does not know, so a misspelled key is caught here. If the commission changes after delivery, the integrator reruns the command; no re-export is needed.

## Step 3: Verify

The profile's [Conformance testing](profile.md#conformance-testing) section asks four questions of a delivery

1. Valid? `gltf_validator` CLI tool 
2. Intended? [Khronos Sample Viewer](https://github.khronos.org/glTF-Sample-Viewer-Release/)  browser render
3. Compliant? `gltf-check` evaluates the `.glb` file against the [./profile.md]
4. Usable?



### Valid?

The Khronos glTF Validator answers whether the file is legal glTF. It is a single binary from the [glTF-Validator releases](https://github.com/KhronosGroup/glTF-Validator/releases). The delivery passes with zero errors. Warnings and infos are read and explained: a warning that a normal-mapped primitive has no tangents is expected, because neither consumer reads them ([Geometry](profile.md#geometry)). 

```bash
gltf_validator -o -a <part>.visual.glb
```

### Intended?
The [Khronos Sample Viewer](https://github.khronos.org/glTF-Sample-Viewer-Release/) answers whether the file looks as intended, judged by a person against the commission's images and material notes. The viewer assumes glTF's Y-up convention, so the default view is Y-up, X-right, Z-towards viewer.  Qualitative comparision between physcial robot and 3D asset materials, textures, etc. 

### Compliant?
`gltf-check` answers whether the file satisfies the profile and passes when thereare no failures, every warning is understood. It covers the container and header, extensions, scene and node structure, primitive attributes, materials, image format and size, transparency and the manifest. How to read its output is in the [checking walkthrough](walkthroughs/checking-a-delivery.md).

`gltf-summary` shows where the origin sits, and the origin line has to agree with the datum specification. An origin on a mounting face reads 0.00 or 1.00 on that axis; 0.50 on all three axes is the bounding-box midpoint and almost always means the origin was inherited and not specified.

The modeler delivers with a note that these four were done. The integrator does not repeat the first two.

### What the integrator checks

* `gltf-check` again, with the output kept with the review.
* `glb_probe` loads the file through the installed `gz-common`, exactly as Gazebo does, and prints the submeshes and materials the loader built. It is built and run inside drydock; the command is in the [probe README](https://github.com/HonuRobotics/gltf-robotics/tree/main/probe). The delivery passes when the output has no `[error]` lines, every submesh has a material, and the submesh name equals the part name.  It does not render, so it settles what a material is and not how it looks.
* Gazebo, standalone parts.   This step identifies Gazebo rendering issues that may or may not be consistent with glTF 2.0, e.g.,  white-metal patches mean a primitive with no material, a dark hull means metalness was left at its default. Other viewers do not predict any of this, because they honor `BLEND`, `doubleSided` and extensions that Gazebo ignores.
    * Origin and orientation by eye against the datum specification, naming what the origin sits on in the part's own terms.
    * The commission's visual requirement and priorities. 
* RViz with the URDF: the part renders, is upright and RViz stays up. Passing in Gazebo is necessary and never sufficient; a normal map with no base color renders in Gazebo and terminates RViz.




### When the checks run

The checks run when a delivery is reviewed.  These  are not CI tests: once a part is merged it has already been checked, and rerunning every check on every commit would slow every unrelated change. 

### Who answers what

| Question | Asked by | Tool | Passes when |
|---|---|---|---|
| Valid | Modeler | Khronos Validator | Zero errors |
| Intended | Modeler | Sample Viewer, against the commission | Signed off by the modeler, pose ignored |
| Compliant | Modeler, then integrator | `gltf-check` | No failures, warnings reviewed, open items discussed |
| Usable | Integrator | `glb_probe`, Gazebo, RViz | Loads, renders upright, RViz stays up |
| Matches the commission | Integrator | `gltf-check`, `gltf-summary`, datasheet, eyes | Within tolerance, datum recognized, priorities met |


## After acceptance

Out of scope here. The consuming project owns everything downstream of an accepted part: placement, the part macro, the RViz correction, joints and actuators, sensors, plugins and buoyancy.

## Not settled here

- Visual requirement tiers have no numbers until the profile's [Budgets](profile.md#budgets) section closes.
- A component part's datum is a SHOULD ([component part](profile.md#a-component-part)), so a component block may leave it out; this document does not decide whether it should.  The **component** profile is still a work in progress. 
- Whether the modeler delivers anything besides the visual model, such as collision geometry or a `model.sdf`. The profile covers the visual model only ([Scope](profile.md#scope)), so today that is whatever the commission asks for.  Yes - we'll sort that out later.


