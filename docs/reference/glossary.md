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

The part that establishes a vehicle's reference coordinate system. There is exactly one per vehicle, and its manifest declares `gltfrp:partRole` as `base`. Profile section 5.6.2 requires more of it than of a component part.

### commission

The unit of work a specification is written for, typically one vehicle or one batch of parts.

### component part

A part that attaches to a vehicle's reference coordinate system and does not establish it. Its manifest declares `gltfrp:partRole` as `component`. Profile section 5.6.3.

### consumer

A program that loads a delivered visual model. For this project the consumers are Gazebo and RViz.

### coordinate system

Used throughout in preference to *frame* and to *space*. All three are in use elsewhere (REP 103 says frame, ISO 9787 says coordinate system, graphics says space) and they are treated here as naming the same thing. Where an external document is quoted its own word is kept. What each coordinate system here is called in ISO 9787, in REP 103 and in glTF is tabulated in the [coordinate systems reference](coordinate-systems.md#our-coordinate-system-names).

### datasheet

The published source a part's dimensions are cited from. The integrator chooses it in step 1 of the workflow and measures against it in step 3.

### datum

A situation feature of the part that the coordinate system is referenced to. Profile section 5.6 states which features may serve and requires that those named together fix all six degrees of freedom. A datum is named before modeling starts; it is not measured from the geometry afterwards.

### datum coordinate system

What a datum specification evaluates to against a particular piece of geometry. In a conforming delivery it is the same thing as the part coordinate system, the origin, node space and scene space. The profile narrows all of them to one. Profile section 5.4 says so normatively.

One coordinate system, several names. glTF distinguishes *node space*, the coordinate system a node's vertices are expressed in, from *scene space*, what node space becomes once node transforms are composed down from the root. Profile section 5.5 requires exactly one node carrying no transform, which collapses the distinction: node space, scene space, the part coordinate system, the datum coordinate system and the origin are all the same thing in a conforming delivery. Narrowing them to one is a deliberate act of the profile, and it is why the terms are listed here as equivalents and not distinguished.

### datum point

The single geometric point feature of a part that fixes the location of its coordinate system, stated before authoring begins and recorded in the manifest. Profile section 5.6.1.

### delivery

A single `.glb` file carrying a single part. Profile section 4.

### integrator

The party who commissions a visual model, checks it and integrates it as a robot component.

### manifest

The metadata a delivery carries about itself, expressed as `KHR_xmp_json_ld` and attached to the glTF `asset` object. Profile section 4.1.4.

### modeler

The party who authors and delivers a visual model.

### origin

The location and orientation of the datum coordinate system relative to the visual geometry. Not a point chosen at the keyboard and not a measured property of the mesh: it is what the datum specification of profile section 5.6 evaluates to.

### part

A single physical component, geometry only, no joints. The unit the profile delivers. A part has a coordinate system and a place in an assembly.

### part coordinate system

The coordinate system in which a part's geometry is expressed. Its axes are fixed by profile section 5.2 (+X forward, +Y left, +Z up, per ISO 9787 §5.5 and REP 103) and its origin by profile section 5.4.

### specification

The visual model specification the integrator writes in step 1 of the workflow for one commission, with one block per part. The word is used only in this sense in the workflow, which never calls the profile the specification.

### submesh

A Gazebo word, not a glTF one. Gazebo's loader emits one submesh for every primitive it meets and names each after the node that instantiated that primitive's mesh. Profile section 6.3.

### visual model

The visual geometry delivered for a part: the file `<part>.visual.glb` and its contents.
