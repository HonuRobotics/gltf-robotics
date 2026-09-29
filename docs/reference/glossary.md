# Glossary

The vocabulary of the whole project: the profile, the workflow, the reference pages and the tools. A term means the same thing wherever it appears.

Within the [profile](../profile.md) these definitions govern and supersede any other meaning the terms may carry elsewhere. Terms drawn from glTF keep their glTF meaning and are not redefined here.

## Terms

### assembly

A collection of parts and the joints between them. Out of scope: an assembly is expressed by the consuming project in its own description format, never in delivered geometry.

"Part" and "assembly" are this project's own terms and no standard defines them. The closest published vocabulary is ISO 10303 (STEP), which distinguishes a part from an assembly the same way for mechanical product data; the usage here is consistent with it but does not depend on it.

### asset

Avoided in normative text. In 3D work the word spans meshes, textures, rigs, scenes and library entries at every scale, and glTF itself uses `asset` for the metadata object inside a file, so it cannot be used precisely. Where the profile means the delivered file it says *visual model*; where it means the glTF object it writes `asset` in code font.

### base part

The part that establishes a vehicle's reference coordinate system. There is exactly one per vehicle, and its manifest declares `gltfrp:partRole` as `base`. The profile's [What the manifest carries](../profile.md#what-the-manifest-carries) section requires more of it than of a component part.

### commission

The document the integrator writes in step 1 of the workflow, stating what is to be modeled: one vehicle or one batch of parts, with one block per part. It is the written statement of intent that a delivery is checked against. As a verb, to commission is to write and agree that document.

### component part

A part that attaches to a vehicle's reference coordinate system and does not establish it. Its manifest declares `gltfrp:partRole` as `component`. See the profile's [component part](../profile.md#a-component-part) section.

### consumer

A program that loads a delivered visual model. For this project the consumers are Gazebo and RViz.

### coordinate system

Used throughout in preference to *frame* and to *space*. All three are in use elsewhere (REP 103 says frame, ISO 9787 says coordinate system, graphics says space) and they are treated here as naming the same thing. Where an external document is quoted its own word is kept. What each coordinate system here is called in ISO 9787, in REP 103 and in glTF is tabulated in the [coordinate systems reference](coordinate-systems.md#our-coordinate-system-names).

### datasheet

The published source a part's dimensions are cited from. The integrator chooses it in step 1 of the workflow and measures against it in step 3.

### datum

A situation feature of the part that the coordinate system is referenced to. The profile's [Datum specification](../profile.md#datum-specification) section states which features may serve and requires that those named together fix all six degrees of freedom. A datum is named before modeling starts; it is not measured from the geometry afterwards.

### datum coordinate system

What a datum specification evaluates to against a particular piece of geometry. In a conforming delivery it is the same thing as the part coordinate system, the origin, node space and scene space. The profile narrows all of them to one. The profile's [Origin](../profile.md#origin---datum-coordinate-system-location) section says so normatively.

One coordinate system, several names. glTF distinguishes *node space*, the coordinate system a node's vertices are expressed in, from *scene space*, what node space becomes once node transforms are composed down from the root. The profile's [Scenes and nodes](../profile.md#scenes-and-nodes) section requires exactly one node carrying no transform, which collapses the distinction: node space, scene space, the part coordinate system, the datum coordinate system and the origin are all the same thing in a conforming delivery. Narrowing them to one is a deliberate act of the profile, and it is why the terms are listed here as equivalents and not distinguished.

### datum point

The single geometric point feature of a part that fixes the location of its coordinate system, stated before authoring begins and recorded in the manifest. See the profile's [datum point](../profile.md#the-datum-point) section.

### delivery

A single `.glb` file carrying a single part. See the profile's [Delivery](../profile.md#delivery) section.

### integrator

The party who commissions a visual model, checks it and integrates it as a robot component.

### manifest

The metadata a delivery carries about itself, expressed as `KHR_xmp_json_ld` and attached to the glTF `asset` object. It is written from the commission by `gltf-manifest`. See the profile's [manifest](../profile.md#the-manifest) section.

### modeler

The party who authors and delivers a visual model.

### origin

The location and orientation of the datum coordinate system relative to the visual geometry. Not a point chosen at the keyboard and not a measured property of the mesh: it is what the profile's [datum specification](../profile.md#datum-specification) evaluates to.

### part

A single physical component, geometry only, no joints. The unit the profile delivers. A part has a coordinate system and a place in an assembly.

### part coordinate system

The coordinate system in which a part's geometry is expressed. Its axes are fixed by the profile's [Axes](../profile.md#axes) section (+X forward, +Y left, +Z up, per ISO 9787 §5.5 and REP 103) and its origin by the profile's [Origin](../profile.md#origin---datum-coordinate-system-location) section.

### submesh

Gazebo's word and SDF's, not a glTF term and not an assimp one. Gazebo's loader turns every glTF primitive into one submesh, and SDF's `<mesh><submesh>` element selects one by name. The project's documents say *primitive* and use this word only when they mean Gazebo's object or the SDF element. See the profile's [Primitives](../profile.md#primitives) section.

### visual model

The visual geometry delivered for a part: the file `<part>.visual.glb` and its contents.
