# Honu glTF Asset Workflow

The [profile](profile.md) states what a delivered visual model must be. This document states the process that produces one: two parties, three steps, in order. Where the two would overlap, this document cites the profile and does not restate it. Requirements live there; who does what, and when, lives here.

The process begins with a commission, a vehicle or a batch of parts to be modeled, and ends when the integrator accepts the delivered files. Placing an accepted part in the simulation model, the macro and the RViz correction, is the consuming project's work and is out of scope here.

To write: a paragraph on why a written process is needed at all. The failures that motivated it were not modeling mistakes but handoff gaps: intent never stated, origins decided at the keyboard, both parties assuming the other had checked the file.

## Roles

The two parties are the ones the profile names in section 2.1: the modeler, who authors and delivers the visual model, and the integrator, who commissions it, checks it and integrates it as a robot component. Part, delivery and model carry their profile section 3 meanings.

Two words this document needs and the profile does not:

- commission: the unit of work a specification is written for, typically one vehicle or one batch of parts.
- specification: the visual model specification the integrator writes in step 1 for one commission, with one block per part. The word is used only in this sense here; the profile is never called the specification.

The datasheet is the published source a part's dimensions are cited from. The integrator chooses it in step 1 and measures against it in step 3.

## The three steps at a glance

| Step | Owner | Input | Output | Gate to the next step |
|---|---|---|---|---|
| 1. Specify | Integrator | Reference material, datasheets, the vehicle's datum decision | One specification per commission, one block per part | Every block complete and agreed with the modeler |
| 2. Model | Modeler | The specification and the profile | One `<part>.visual.glb` per part, manifest filled from the specification | The modeler's own checks pass |
| 3. Verify | Modeler, then integrator | The delivery and the specification | Acceptance, or a rejection naming what failed | All checks pass |

Rejection in step 3 sends the part back to step 2. It sends the commission back to step 1 only when the specification itself was wrong or silent on the point that failed. Nothing enters step 2 without an agreed specification, and nothing leaves step 3 without the integrator's acceptance.

## Step 1: Specify

The integrator writes the specification before any modeling starts. It is the only written statement of intent the process has, and it is what the visual checks in step 3 are judged against. Profile section 12's second question, whether the model is what was intended, can only be answered against something written down.

### What the specification contains

To write: expand each item to one sentence. Each item names the profile section and the manifest property it feeds, so the manifest in step 2 is copied from the specification rather than authored from memory.

Per commission:

- Sources: datasheets, drawings, vendor pages, and any CAD, scans or vendor models handed over (profile 4.1.4, `dc:relation`, `dc:source`)
- Licensing and texture redistribution terms (`dc:rights`)
- The base part, exactly one per vehicle, and the vehicle's datum decision (5.6.2, `gltfrp:partRole`)
- The authoring toolchain the modeler will use, against the pin in section 11
- Where the `.blend` and CAD will be archived (`xmpMM:DerivedFrom`)
- The default visual requirement for the commission, provisional while the budgets in 6.2 are open
- Dates for the three agreement moves below

Per part:

- Part name, lowercase snake_case, and role, base or component (4.1, 4.1.4)
- Reference images, with what each view shows and what matters in it
- Cited dimensions, each as a named quantity with its source, and the tolerance held, or an explicit statement that no published figure exists (`gltfrp:nominalDimension`, `gltfrp:dimensionTolerance`)
- The datum point: the single geometric feature the origin is referenced to (profile 5.6, `gltfrp:datumPoint`). Orientation is not specified per part; profile 5.2 fixes it for every delivery
- Datum targets where a physical realization exists (`gltfrp:datumTarget`)
- The feature that defines forward, and its sense, where the shape does not determine it (5.2)
- Visual requirement: what must read at the viewing distance, what may be simplified
- Materials per region, metal or non-metal, finish reference (7, 8)
- Cutouts and translucent regions, named (9)
- Priorities: what matters most on this part, in order
- Notes to the modeler

### Agreeing the specification

Three moves, all before modeling starts:

1. The written specification goes to the modeler.
2. A meeting walks through it against the reference images, so intent is clarified in conversation rather than inferred from text.
3. The integrator issues the final written part-by-part priorities, amended by what the meeting found.

To write: how a change to the specification after this point is handled. It is a change to the commission and is written down, not agreed in passing.

### Gate

Every part block has a name, a role, a datum specification that closes all six degrees of freedom, a cited dimension or an explicit "none published", and a visual requirement. The modeler has the final version in hand. A modeler who starts a part without a datum specification stops and asks; there is no default, and nothing downstream can recover the intent.

## Step 2: Model

### Build to the profile

Profile sections 5 to 10 are the rules the model is built to. The [Blender export guide](how-to/exporting-from-blender.md) is the tool-specific practice for meeting them, and the [walkthrough](walkthroughs/blender_mesh_coordinate_ex.md) shows one file going through end to end. The origin is placed by evaluating the datum specification against the geometry, never chosen from a menu (5.4).

### Export

To write: one paragraph. The toolchain pin (11), the exporter's `+Y Up` option off (5.2), clear location and rotation and apply scale before export (5.5), and the authoring source kept outside the simulation repository and cited from the manifest.

### Fill the manifest from the specification

Every `gltfrp:` and `dc:` value in the manifest (4.1.4) is copied from the specification block for that part. This is the mechanism that lets step 3 compare the delivery with what was asked for, and it is why the specification names the property beside each field.

### Gate

The modeler's own checks in step 3 pass. The delivery is one `<part>.visual.glb` per part, named per profile 4.1, plus whatever the commission asked to accompany it.

## Step 3: Verify

Profile section 12 asks four questions of a delivery: valid, intended, compliant, usable. They fail independently and no single tool answers more than one. The first two are the modeler's to answer before delivering, the last two the integrator's after. The split is stated here so that neither party assumes the other checked the thing.

### What the modeler checks

To write: one paragraph each.

- The Khronos glTF Validator: zero errors, warnings read.
- The Khronos Sample Viewer, against the specification's images and material notes. The viewer assumes glTF's Y-up convention and shows every conforming part on its side; read it for materials, textures, transparency and validity, and ignore the pose. Blender's viewport answers nothing, because it shows Blender's materials and not the exported file.
- `gltf-check`: no failures, every warning understood.
- `gltf-summary`: the origin line agrees with the datum specification. An origin on a mounting face reads 0.00 or 1.00 on that axis; 0.50 on all three axes is the bounding-box midpoint and almost always means the origin was inherited rather than specified.

The modeler delivers with a note that these four were done. The integrator does not repeat the first two.

### What the integrator checks

To write: one paragraph each.

- `gltf-check` again, output kept with the review.
- `glb_probe`: loads without error, every submesh has a material, submesh name equals the part name.
- Gazebo, in the parts world: scale against a known object, orientation, origin, no white-metal patches, no dark hull, cutouts actually cut, thin parts visible from both sides.
- RViz with the URDF: renders, upright, stays up. Passing in Gazebo is necessary and never sufficient; a normal map with no base color renders in Gazebo and terminates RViz.
- Extents against the datasheet, within the specified tolerance, and the manifest's cited dimension matching the specification.
- Origin and orientation by eye against the datum specification, naming what the origin sits on in the part's own terms.
- The specification's visual requirement and priorities, the one check with a written answer key.

### Who answers what

| Question | Asked by | Tool | Passes when |
|---|---|---|---|
| Valid | Modeler | Khronos Validator | Zero errors |
| Intended | Modeler | Sample Viewer, against the specification | Signed off by the modeler, pose ignored |
| Compliant | Modeler, then integrator | `gltf-check` | No failures, warnings reviewed, open items discussed |
| Usable | Integrator | `glb_probe`, Gazebo, RViz | Loads, renders upright, RViz stays up |
| Matches the specification | Integrator | `gltf-summary`, datasheet, eyes | Within tolerance, datum recognized, priorities met |

The last row is this workflow's own gate rather than a profile question. Not every failure is the modeler's to fix: a defect that turns out to be a consumer limitation becomes a target constraint recorded in the profile, not a rejection.

### Rejection and redelivery

A rejection names the question that failed and either the profile section or the specification field behind it, with the tool output attached. A disagreement is then with a rule or a field, not with a person.

A redelivery is a complete delivery under the same part name, with the manifest's date updated and the modeler's four checks redone. The integrator reruns every check, not only the one that failed, because a `.glb` is opaque in a diff and the previous run's output kept with the review is the only before-and-after comparison.

If the failure was the specification's, wrong or silent on the point, step 1 reopens and the block is amended before the modeler works again.

### Gate

All five rows pass. The integrator records the accepted delivery date and the checker output, and the part goes to the consuming project's [add-part procedure](https://honurobotics.github.io/bluerobotics_models/lyrical/how-to/add-part.html).

## After acceptance

Out of scope here. The consuming project owns placement, the part macro and the RViz correction.

## Not settled here

- Visual requirement tiers have no numbers until profile 6.2 closes.
- A component part's datum is a SHOULD (5.6.3), so a component block may leave it out; this document does not decide whether it should.
- Where the filled specification is archived is the consuming project's decision.
