# The glTF Robotics Profile

This "profile" is based on the glTF 2.0 specification and interprets and constrains the specification for use in 3D asset authoring for robotic simulation.

## 1. Introduction

### 1.1 Scope

This profile constrains the visual models authored for robotics simulation, currently mobile robots and specifically maritime robots.

It is being written for the `gz-maritime` project, against Gazebo and RViz and applied in the `bluerobotics_models` repository.  The aspiration is to generalize this, but at the current time we are prototyping the profile and workflow for this project and set of models. 

This profile builds upon [glTF 2.0](https://registry.khronos.org/glTF/specs/2.0/glTF-2.0.html) to make it actionable for 3D visual model integration in Gazebo for robotics. It stands in three relationships to that standard and the others referenced below, and every rule here is one of the three:

- **Narrowing.** Focusing and interpreting the standard's affordances for the specific needs of robotics simulation, to make it actionable in the context of developing 3D visual robotic assets. A file can be glTF-compliant and still be unusable in a robotics simulator.
- **Adding.** Requiring something the standard does not, to satisfy the constraints of the robotics simulation and visualization consumers of the assets (e.g., Gazebo, RViz). This is required because some consumers implement only part of glTF, so a glTF-compliant asset is not guaranteed to be importable. Added constraints name the downstream consumer that motivates them.
- **Departing.** Differing from what the standard says, which is done rarely and never silently. The forward axis in section 5.3 is the only current candidate.

This profile is only about the visual 3D asset model and does not cover Collision geometry, inertia properties, joints, etc. 

### 1.2 Closely related work (Informative)

This profile is not the first attempt to make glTF actionable for a particular consumer. Three efforts are close enough to compare against, and the comparison is useful in both directions: it shows which of our rules are obvious enough that others reached them independently, and which are ours alone and therefore carry more risk.

| Effort | What it profiles | Where we agree | Where we differ |
|---|---|---|---|
| [Drake mesh file formats](https://drake.mit.edu/doxygen_cxx/group__geometry__file__formats.html), Toyota Research Institute | glTF as consumed by one robotics simulator, stated as a supported-feature list rather than a specification | Animation and skinning ignored; vertex normals required; PBR as the reason to prefer glTF over OBJ | Drake does not support `.glb` at all, where we require it. Its published corpus is `.gltf` with external `.bin` and `.png`, and it recommends `KHR_texture_basisu`, which section 10 prohibits because Gazebo cannot read it |
| [REP 158](https://github.com/openrobotics/reps/blob/main/_posts/rep-0158%3A2006.md), ROS and Gazebo (Draft) | OpenUSD for simulation-asset interchange, with glTF 2.0 as one export target | PNG required for normal, metallic, roughness and packed ORM maps; JPEG permitted for base color and emissive without alpha; UVs packed into [0, 1]; the ROS right-handed convention | Its subject is USD and glTF is downstream of it, so its rules are written for an export pathway rather than for a delivered glTF file. It is also Draft and unratified |
| [Real-time Asset Creation Guidelines](https://github.com/KhronosGroup/3DC-Asset-Creation) v2.0.0, Khronos 3D Commerce | glTF for real-time product visualization on web, apps and XR | A single self-contained file is generally preferred; more than one UV map is discouraged; naming restricted to letters, digits, underscore and hyphen with no spaces; metalness should be black or white, gray only for anti-aliasing | It endorses UV tiling above 1 for repeating patterns, which section 6.1 forbids. Its target is photorealism at product scale, so it has no equivalent of a part frame, an origin convention or a collision companion |

Two things follow. The Khronos guidelines are the same exercise as this one in a different domain, and where they and this profile agree the rule is probably not controversial: the metalness rule in section 7 is the clearest case, arrived at there from art-pipeline experience and here from measuring what robotics assets actually ship. Where all three differ from us the disagreement is usually about the consumer, not about glTF, and section 10's prohibitions are the place that shows most plainly: an extension Drake recommends for performance is one Gazebo cannot read.

Nothing above is a survey. It is three efforts that publish enough detail to compare, and their existence is not evidence that a practice is settled.

## 2. Document conventions

### 2.1 Audience

This specification addresses two parties:

- **the modeler**, who authors and delivers a 3D visual asset
- **the integrator**, who integrates the asset as a functional robot component

Requirements are imposed only on the audience of the text stating them. Where the audience is not obvious from context, it is named.

### 2.2 Normative terminology

The key words MUST, MUST NOT, REQUIRED, SHALL, SHALL NOT, SHOULD, SHOULD NOT, RECOMMENDED, MAY and OPTIONAL are to be interpreted as described in [BCP 14](https://www.rfc-editor.org/info/bcp14), and only when they appear in capitals.

References to external documents are normative if this specification uses those keywords to refer to them or to their requirements.

### 2.3 Informative language

Some text is purely informative, giving background or explaining why a rule exists. A section whose title is suffixed "(Informative)" contains only informative language. All Notes, Implementation Notes and Examples are informative. Everything not so marked is normative.

### 2.4 Open issues

One kind of block marks everything not yet settled:

> **Open.** A question this draft does not answer. Where a proposal exists it is stated as the rule would read; where none does, the block names what has to be settled and, if known, what would settle it. Tracked as review decision N.

Three things become an Open issue, and they are not distinguished because acting on them is the same work: a question nobody has proposed an answer to; a proposal on the table that the team has not agreed to; and a rule this draft states in its simplest form, deliberately, where a more capable version is plausible later. The third kind is easy to lose, because it reads as settled -- the rule is normative and a delivery conforms to it today. It is recorded anyway, so that the reason for the simple version stays visible and the extension is a decision rather than a rediscovery.

A delivery cannot fail to conform on a point marked Open. Where a rule is normative today but expected to change, the rule governs and the block says what would reopen it.

The plan is to settle as many as possible before the first pilot of the modeling workflow. Some will stay open through it, and the pilot itself is expected to inform them. An item left open is a known gap, not an oversight.

Decision numbers refer to section 10 of [VISUAL_ASSET_PIPELINE_REVIEW.md](../reference/pipeline-review.md). Section 13 collects every Open block and is the to-do list for finishing this draft.

## 3. Terminology

The definitions below govern within this profile and supersede any other meaning these terms may carry elsewhere. Terms drawn from glTF keep their glTF meaning and are not redefined here.

part::
A single physical component, geometry only, no joints. The unit this profile delivers. A part is the smallest thing that can be given a name, a frame and a place in an assembly.

assembly::
Parts plus the joints between them. Out of scope: an assembly is expressed by the consuming project, in its own description format, and never in delivered geometry. Section 4.1 requires one part per delivered file for this reason.

model::
The visual geometry delivered for a part: the file `<part>.visual.glb` and its contents. Used in preference to "mesh" throughout, because whether a part is one glTF mesh, one node or several is undecided (section 5.5), and "mesh" would prejudge it.

submesh::
Not a glTF term. The unit Gazebo's loader produces from a file: one submesh per primitive, named after the node that instantiates the primitive's mesh. It is neither a node arrangement nor a second mesh, and a single mesh of four primitives becomes four submeshes. Section 6.3 states what follows from that.

delivery::
The set of files handed over for one part, together with whatever accompanies them under section 4.

part frame::
The coordinate frame in which a part's pose, attach point and any sub-frames are expressed. Defined by REP 103: x forward, y left, z up.

**Implementation Note.** "part" and "assembly" are this profile's own terms and no standard defines them. The closest published vocabulary is ISO 10303 (STEP), which distinguishes a part from an assembly in the same way for mechanical product data; the usage here is consistent with it but does not depend on it. The word "asset" is deliberately not used in normative text: in 3D work it spans meshes, textures, rigs, scenes and library entries at every scale, and glTF itself uses `asset` for the metadata object inside a file, so it cannot be used precisely.

## 4. Delivery

### 4.1 Files

A delivery MUST include a visual model named `<part>.visual.glb`, where `<part>` is the part name.

The part name MUST be lowercase snake_case: lowercase letters, digits and underscores, beginning with a letter. It MUST NOT contain spaces. It MUST match the name of the directory the delivery is placed in.

**Implementation Note.** This profile states the naming rule itself rather than citing a project's convention for it, because the dependency runs the other way: a consuming project may narrow or extend this profile, and this profile must stand without it. Where a project's own contract is stricter, the stricter rule governs there and this one remains the floor.

A delivery MUST describe exactly one part. A compound object -- a whole vehicle, or several parts carried as separate nodes in one file -- MUST NOT be delivered as a single glTF file.

**Implementation Note.** The reason is to start simple. One part, one model, one `.glb` is a mapping every tool in the pipeline can assume, and it keeps the assembly in one place rather than expressed twice.

> **Open: Future** Whether a compound delivery is worth supporting later. One file carrying a whole vehicle, with its components as separate nodes, could drive the assembly description from what the file already states rather than from a macro written alongside it. The rule above is the simple form and governs today; this records that it was chosen for simplicity and not because the alternative was ruled out. Settling it needs a case where the node structure states the assembly better than the macro does, and it bears on the node question in 5.5. Not yet on the review's decision list.

**Implementation Note.** This is not the same question as how many nodes one part may use, which section 5.5 leaves open. Section 5.5 requires a single root node named for the part but permits children, so a compound object could satisfy it by hanging its components under one root. That rule narrows the possibilities without closing them, and this one closes them. Nor is it mechanically checkable: nothing in a glTF file says how many parts it depicts, so `gltf-check` cannot enforce it and acceptance rests on the integrator recognising a delivery that is really an assembly.

> **Open.** Whether a delivery carries a manifest recording the source of the geometry, the source of its dimensions and the texture provenance. Proposed: yes, because it is cheap and answers questions the audit could not. Archiving the Blender source file is a separate and heavier commitment, storage, licensing of purchased textures and an implied ability to re-export, and is not proposed. Tracked as review decision 12. 

> **Open.** Whether every part must cite a published dimensional figure, and what to do for parts where none exists. Proposed: yes where one exists, because it is the one check that would have caught a defect the earlier audits missed. Tracked as review decision 13.

**Implementation Note.** Both of the questions above may be answered together by the datum specification in 5.6, which needs a manifest to live in and needs a cited expression of the part's nominal geometry to be written against.

### 4.2 Format

The model MUST be glTF 2.0 in the binary container, `.glb`. The `.gltf` form, with geometry in a side `.bin` and images as separate files, MUST NOT be delivered.

**Implementation Note.** Why the binary container, in order of weight:

- gz-common 7.3.0 drops the glTF root rotation for a `.gltf` file and keeps it for a `.glb`, because it compares an already-lowercased extension against the literal `"glTF"`. A `.gltf` delivery would load into Gazebo mis-oriented and report nothing.
- Gazebo decodes every external texture when the mesh loads, not when a texture is first needed. A `.gltf` delivery with eight maps therefore pays eight image decodes at load time even for a part that is off screen, and the cost is paid again for every model that references the file.
- One artifact cannot arrive incomplete. A directory of six files can, and the acceptance tooling reads a `.glb` with no search path at all.
- The legibility `.gltf` would give is already available from the container: `glb_inventory.py` reports per-image size, format and texel density, and `glb_probe` reports what the loader built.

What the rule gives up: with `.gltf` the images version independently in git, which matters because textures are the majority of the file size. 

The file MUST validate against the Khronos glTF Validator with zero errors. Validator warnings and infos MUST be reviewed but do not by themselves fail a delivery.

> **Open.** Whether the binary container stays the only permitted form. Two of the reasons above are defects rather than properties: the gz-common extension-comparison bug has an upstream fix, and eager texture decoding is an implementation choice. When the pinned container moves, both may be gone, and the remaining arguments are about delivery hygiene rather than correctness. Against relaxing it, Drake does not read `.glb` at all (1.2), so a `.gltf` allowance would widen the set of consumers a delivery can reach. Not yet on the review's decision list. % CLAUDE: Current decision - single file. KISS  Open for later consideration - consider using glb with references to textures for git and performance advantages

> **Open.** Whether textures are embedded in the container, delivered as external files, or either. The container decision above does not settle this: a `.glb` packs only its first buffer into the binary chunk, and an image may still carry a `uri` pointing at an external file. All deliveries to date embed, and the acceptance tooling reads a delivery with no search path. Against that, Drake does not support `.glb` at all (section 1.2), so a model meant to be consumed there cannot be delivered in the container this profile requires, whatever is done about textures. Packaging is therefore the first thing that breaks outside Gazebo and RViz. Tracked as review decision 16.

**Implementation Note.** Embedding gives one artifact that cannot arrive incomplete. External files version independently, so a texture can be re-authored without re-exporting geometry. The geometry remains an opaque binary either way.

### 4.3 Asset header

`asset.version` MUST be `"2.0"`.

`asset.minVersion` MUST NOT be present.

**Implementation Note.** The second rule is the one that earns its place: a stray `minVersion` written by some future exporter is a hard load failure in a consumer that would otherwise have been fine. There is no glTF 2.1 and none is planned. The Khronos registry carries 2.0 only, currently revision 2.0.1, and states that every update to it is a backwards-compatible patch; new capability arrives as extensions rather than as minor versions.

## 5. Coordinate system, units and frame

### 5.1 Units

All linear distances MUST be in meters, at real-world scale, as glTF requires.

The Blender scene unit scale MUST be 1.0, and object scale MUST be applied before export. A file whose scale is wrong is silently wrong: nothing downstream can detect it.

### 5.2 Up axis

The model MUST be Y-up, as glTF specifies.

**Implementation Note.** This is not a stylistic preference. Every consumer converts on the assumption that glTF is Y-up. RViz rotates a glTF mesh as it loads, and the part macro applies the matching rotation for Gazebo. A Z-up file renders correctly in one and wrong in the other.

**Implementation Note.** The RViz rotation is younger and narrower than it looks. It was added by `ros2/rviz` #1482, merged to `rolling` on 2025-06-16 and deliberately not backported, so Jazzy and Kilted do not have it. These models render correctly in RViz only on distributions downstream of that merge; on Jazzy every part appears rotated ninety degrees. This is a distribution floor for consumers of the library, not a defect in the file.

> **Open.** Whether this specification states that distribution floor as a requirement on the integrator, and where. Proposed: state it here and in the repository README, as the oldest ROS distribution on which the models render correctly in RViz. Not yet on the review's decision list.

### 5.3 Forward axis

> **Open.** Whether the delivered file faces +X, which is what authoring in the part frame produces and what every current delivery does, or +Z, which is the convention stated in glTF. Proposed: +X, stated as a deliberate departure from the glTF wording, because the frame is the interface with the part macro and moving would cost a re-export of every file and an extra rotation in two code paths. Tracked as review decision 2.

[REP 158](https://github.com/openrobotics/reps/blob/main/_posts/rep-0158%3A2006.md) requires "the strict ROS Right-Handed convention: X-forward, Y-left, Z-up", which is external support for +X. Its Z-up is stated about the USD stage and does not bear on the Y-up rule in section 5.2. See the reference for the rest.

**Implementation Note.** glTF says "the front side of a glTF asset faces +Z", but states it about the asset as a whole rather than any individual mesh, and states it without a normative keyword. No validator checks it.

Interim rule. Until this is decided, modelers SHOULD continue to author in the part frame, which yields a file facing +X, and MUST NOT re-orient a delivery to face +Z without agreement.

### 5.4 Origin

> **Open.** Where a part's origin sits within its geometry. Our documents state three rules, centroid, author's choice, and centroid near a sensible mounting point, and the library follows none of them. Measured, it is centered in plan and referenced to the mounting plane vertically on all but two parts. Proposed: adopt the measured convention, stated as "centered in plan, zero on the mounting plane, with the mounting face named in the part's macro comment", because it is what makes a part sit correctly at a slot, it matches fourteen of fifteen files already, and it is checkable by measurement once the face is named. Tracked as review decision 2.

**Implementation Note.** The proposal above states where the origin sits as a measured property of the geometry. Section 5.6 records a different approach, still open, which states instead which features the coordinate system is referenced to and lets the position follow.

**Implementation Note.** glTF has no concept of a mesh origin, pivot or reference point. The origin is simply the zero of the coordinate space, and geometry is placed relative to it by vertex positions and node transforms. Nothing in a file can declare where the origin is meant to be, and no validator can check it, which is why the rule must be stated here and in the part macro, and verified by measurement. The measurement reads the `POSITION` accessor bounds and composes the node's local transform; accessor bounds alone are wrong for the three files carrying a node translation.

### 5.5 Scenes and nodes

The delivered file MUST contain exactly one scene, and that scene MUST list only the root node.

**Implementation Note.** A file with no scene is a library of entities that a viewer cannot show, and a file with several leaves which one renders to the client. Neither is wanted here. Several current deliveries carry leftover empty scenes and `bluerov2_chassis` carries two, which this rule catches.

The delivered file MUST contain exactly one root node, and that node MUST NOT carry a `rotation` or a `matrix` transform. Transforms MUST be applied in Blender before export.

A `translation` on the root node SHOULD NOT be present. Where one is, it is applied by both consumers but composed differently, so the part does not land in the same place in each.

> **Open.** Whether a root translation is prohibited outright. Both consumers honor it, but they compose it against the up-axis correction in opposite orders -- Gazebo applies the correction outside the root transform, RViz inside it -- so a translation of 0.5 m along the file's Y puts the part 0.5 m up in Gazebo and 0.5 m to the side in RViz. `probe/coords/make_markers.py` writes `marker_roottrans` to demonstrate exactly this. An earlier draft of this section said a root translation "is permitted and is applied by both consumers", which is true of the first half and misleading about the second. The interim rule above is SHOULD NOT rather than MUST NOT because no current delivery carries one and the cost of prohibiting it is unknown; settling it needs the rendered comparison run and recorded. Not yet on the review's decision list.

The root node MUST be named `<part>`, with no Blender numeric suffix such as `.001` and no spaces. This is the only name in the file either consumer reads: Gazebo names each submesh after its node, never after the mesh or the material.

**Implementation Note.** The prohibition on rotation and matrix nodes is a tooling constraint, not a format one. glTF permits them and both consumers honor them. The project's `gltf_to_yup.py` refuses to convert a file containing them, because it does not conjugate rotations.

> **Open.** Whether a part may be delivered as more than one node, and what "one mesh" means when a part carries several primitives. Facts already established: a part with more than one material must have more than one primitive, so a one-primitive rule is a ban on multi-material parts; every primitive under one node becomes a Gazebo submesh carrying that node's name, so an SDF `<submesh>` cannot tell them apart; and an SDF `<material>` collapses every primitive to one material. What remains is whether any part needs submesh selection from SDF, and whether the rule should be stated on nodes rather than meshes. The mechanism behind those facts, and the proposal to rule submesh selection out, are in section 6.3. Tracked as review decision 15.

### 5.6 Datum specification

> **Open.** How a part's coordinate system is specified by *reference to its geometry* rather than as a set of coordinates. The approach being worked out borrows ASME Y14.5's datum vocabulary and carries the specification in the delivery manifest of 4.1: named datum features in an order of precedence, the degrees of freedom each constrains, and a separate declaration of which direction is forward and which is up. If it is adopted it replaces the proposed rule in 5.4 rather than sitting beside it, and it bears on 4.1 and 5.3 as well. Nothing here is settled. Not yet on the review's decision list.

**Implementation Note.** Placeholder, recorded so the work is tracked. The derivation is in [Coordinate systems](../reference/coordinate-systems.md) under "Specifying a coordinate system: datums and what 'referenced to' means". When this section is written it will have to state: which artifact expresses the nominal geometry a part is authored to, and what to do when there is no CAD; how a datum feature is designated, given that glTF is a delivery format with no annotation mechanism and cannot carry the specification itself; that the named datums together constrain all six degrees of freedom, since a partially constrained datum coordinate system is of no use to a delivery even though ASME permits one; how a direction the shape does not determine is declared rather than derived; and what `gltf-check` can verify.

## 6. Geometry

Every primitive MUST use triangle topology.

Every primitive MUST provide `POSITION`, `NORMAL` and `TEXCOORD_0`.

Normals MUST be authored, with hard edges where the part has them. A file delivered without normals will have them generated on import, discarding the author's intent.

The model SHOULD NOT contain degenerate, zero-area triangles.

`TANGENT` is OPTIONAL and is NOT REQUIRED.

**Implementation Note.** Exporting tangents is harmless and improves portability to other viewers, and the Khronos validator emits a portability warning when a normal-mapped primitive omits them. Neither of this project's consumers reads them: the loader has no tangent channel, and the renderer generates its own from the first UV set. What matters instead is a clean UV set on normal-mapped surfaces, since that is the input to that generation. Across the 54 glTF models in Fuel, exactly one primitive carries tangents.

### 6.1 UV sets

The model MUST carry `TEXCOORD_0`, with coordinates inside the range 0 to 1. A second UV set, `TEXCOORD_1`, MAY be present and then only to carry a baked ambient occlusion lightmap. No further UV set may be present.

[REP 158](https://github.com/openrobotics/reps/blob/main/_posts/rep-0158%3A2006.md) requires the same range and adds uniqueness: "Unique UVs must be packed into the [0, 1] space". It reserves coordinates outside that range for seamless tiling with repeat wrap modes, which this document does not permit. See the reference for the rest.

**Implementation Note.** Every texture except a lightmap is read from the first UV set. Coordinates are stored as half floats after loading, so precision degrades outside the 0 to 1 range.

**Implementation Note.** The two paragraphs above previously contradicted each other, requiring exactly one UV set and then permitting a second. `gltf-check` implements the rule as now written and fails a third set; it had been failing the permitted lightmap set as well.

> **Open.** Whether the 0-to-1 requirement survives. It is the most contested rule in this profile and the disagreement is not marginal: the Khronos Real-time Asset Creation Guidelines endorse tiling above 1 for repeating patterns (1.2), REP 158 reserves the range outside 0 to 1 for exactly that, and 19 of the 49 assets measured in the corpus do it, the Gazebo team's own files among them. The rule is kept for now because tiling defeats the texel-density measurement the acceptance tooling relies on, and because half-float storage degrades precision outside the range. Neither reason is about correctness, and a part needing a repeating material is the case that would settle it. Tracked as review decision 5.

### 6.2 Budgets

> **Open.** The triangle budget per part. The earlier draft proposed about 25,000; the current library ranges from 164 to 21,776. A single number is not defensible until each part states how much detail its role warrants, so the proposal is to record a visual requirement per part as one of a few named tiers, for example functional for the vehicles and the parts fitted to them, accessory for sensors and brackets, and scenery for items seen at distance, and then to set a triangle and texture budget per tier. Tracked as review decisions 5 and 18.

**Implementation Note.** Neither consumer imposes a triangle limit. Texture memory dominates the cost, not geometry.

### 6.3 Primitives and submeshes

**Implementation Note.** "Submesh" is a Gazebo word rather than a glTF one, and the mismatch is what makes it hard to picture. It is not a node arrangement and not a second mesh. Gazebo's loader walks the node hierarchy and emits one submesh for every primitive it meets, naming each after the node that instantiated that primitive's mesh, never after the mesh or the material. One node holding one mesh of four primitives therefore arrives as four submeshes all bearing that node's name, and two nodes arrive as the sum of their primitives, each batch carrying its own node's name. The submesh count is the primitive count; the names come from the nodes. The loader probe in section 2.1 of the review prints that list, and is the only way to see it without a renderer.

**Implementation Note.** A part has more than one primitive when it has more than one material, and in practice only then, because a primitive holds at most one `material` and glTF offers no other way to put two materials on one mesh. The specification gives one further reason, to limit the number of indices per draw call, which does not arise at these part sizes. So the primitive count of a well-formed part is its material count, and section 7 already requires every primitive to have a material.

**Implementation Note.** What follows from that. SDF can select one submesh from a file with `<mesh><submesh><name>`, and Gazebo resolves the name by returning the first submesh that matches it and then stopping. Primitives sharing a node are therefore indistinguishable: such a selection takes the first and drops the rest, with no error and no warning. Naming submeshes after their node rather than after themselves is a known upstream defect, `gz-common` pull request 659, open and unfinished since December 2024, so the collision cannot be designed around by naming things more carefully at this end. The neighboring override is in section 7: an SDF `<material>` replaces the material on every primitive with one, so per-primitive materials survive only while nothing declares one.

> **Open.** Whether this specification constrains primitives and rules out submesh selection. Proposed, as two rules: a primitive MUST exist only to carry a material distinct from its siblings, so that the primitive count equals the material count and nothing is split for any other reason; and a delivery MUST be usable as one whole mesh, with neither the part macro nor any world depending on `<mesh><submesh>` to select part of one. Both are free today, since nothing in the library splits a primitive gratuitously and nothing uses submesh selection, and together they keep the upstream naming defect permanently outside this project. The alternative, making selection work, needs one primitive per node and a naming rule for each, which is the multiple-node question in section 5.5. Not yet on the review's decision list.

## 7. Materials

The metallic-roughness workflow MUST be used. The specular-glossiness extension MUST NOT be used.

**Every primitive MUST have a material assigned.** A primitive without one renders as white metal, because that is the glTF default material, and there is no fallback to a neighboring material.

`metallicFactor` and the metalness channel together MUST reflect what the part is made of. Plastics, composites and painted surfaces MUST be non-metallic. Only genuinely metallic surfaces may be metallic.

**Implementation Note.** This is the most common and most damaging defect found in the current library. The glTF default for `metallicFactor` is 1.0, so a material whose metalness nobody set is fully metallic, and a metallic-roughness texture whose blue channel is white makes it metallic regardless of the factor. A plastic hull declared metallic renders dark under every light. Four of fifteen delivered files currently have this defect, and the same trap is live across Fuel.

Any material carrying a texture MUST also carry a `baseColorTexture`.

**Implementation Note.** This is a target constraint rather than a glTF rule. RViz iterates a material's texture properties and asks for the diffuse texture; on a material whose only texture is a normal map, that lookup fails and RViz terminates. The project works around existing files with a baked neutral base color, and a regression test guards against new ones.

A material property that is uniform across the surface SHOULD be delivered as a factor, not as a texture. A texture whose every texel is identical is a factor written the long way and costs a decode, a sampler and a file for nothing.

**Implementation Note.** All seven metallic-roughness textures in the current library are a single uniform color, six of them white, which is the metalness defect above seen from the other side: a constant-white blue channel tells the renderer the part is metal everywhere.

`normalTexture.scale` and `occlusionTexture.strength` MUST be 1.0. Both are ignored by this project's consumers, so a value baked into the file will not be applied.

Material names SHOULD name the component they cover, not a color. Material names are not read by either consumer and are hygiene only.

**Implementation Note.** The materials in the file are what renders. The generated part SDF declares no `<material>`, and if one were declared it would replace every embedded material with that one, so per-primitive materials survive only while nothing overrides them. This matches every glTF exemplar found outside the project, none of which declares a material in SDF.

> **Open.** Whether the workspace rule that PBR materials must be declared in the SDF applies to GLB parts at all. It was written for COLLADA, where the SDF is the only place a PBR material can live. For GLB it contradicts the rule above, the generated part SDF, and every glTF exemplar found. Proposed: restate the workspace rule as applying to COLLADA visuals only. Not yet on the review's decision list.

## 8. Textures

Embedded images MUST be PNG or JPEG. No other image format loads.

**Implementation Note.** KTX2, Basis and WebP are all reachable from the Blender export dialog and all fail. The part loads untextured, with an error naming an unsupported compressed image format.

Textures MUST be 2048 pixels or smaller on each side.

Any texture carrying alpha MUST be PNG.

Normal, metallic, roughness and packed ORM textures MUST be PNG, which [REP 158](https://github.com/openrobotics/reps/blob/main/_posts/rep-0158%3A2006.md) also requires. It permits JPEG for base color and emissive only where they carry no alpha, and excludes EXR, TIFF and other high dynamic range formats from material maps. See the reference for the rest.

**Implementation Note.** The rule follows from the transfer function glTF assigns to each slot. Base color and emissive are sRGB color, which is what JPEG was designed for. Normal, metallic-roughness and occlusion are linear data whose channels are unrelated scalars or the components of one vector, and JPEG's chroma subsampling blends channels that have nothing to do with each other. Measured on the BlueBoat normal map, JPEG at quality 95 with 4:4:4 subsampling leaves a mean error of 0.4 degrees and a 99.9th percentile above 6 degrees, concentrated at UV shell boundaries.

**Implementation Note.** Deliveries from anyone working in the normal way will arrive with JPEG normal maps: every normal map in the current library is JPEG, as are most in Fuel and in the Gazebo team's own demo assets. The Blender exporter inherits the format of the source image, so this is a texture-authoring decision, not an export setting. A JPEG normal map cannot be repaired by converting it to PNG, because the damage is already in the pixels; the remedy is to re-export from the source texture.

> **Open.** Whether base color and emissive textures may be JPEG, and the size cap per map type. Proposed: PNG by default for every map. JPEG is permitted for `baseColorTexture` and `emissiveTexture` only when all four hold: the material is `OPAQUE`, so no alpha is needed; the encoder is set to libjpeg quality 95 or better with 4:4:4 chroma subsampling, not a default; the JPEG is actually smaller than the PNG, which for flat maps it often is not; and the image is plugged into no other slot. Every JPEG in the current library is quality 75 at 4:2:0 and fails the second condition. For size, roughness and metalness maps SHOULD be smaller than the base color map, because they receive no mipmaps and shimmer at distance. Tracked as review decision 4.

**Implementation Note.** Base color and emissive are treated as sRGB; every other map is linear. 16-bit images are converted to 8 bits on upload and buy nothing. PNG and JPEG both decode to the same size in video memory, so the choice costs disk and transfer, never GPU memory.

A base color texture on an `OPAQUE` material SHOULD NOT carry an alpha channel. glTF ignores the channel on an opaque material, and a reader of the file cannot tell whether it was meant.

Occlusion, roughness and metalness MAY be packed into a single texture, with occlusion in red, roughness in green and metalness in blue, as glTF specifies.

Image names SHOULD identify what the map is, for example `Albedo-<component>` and `Normal-<component>`. This is the only signal a reviewer has for telling maps apart in a delivery.

## 9. Transparency

Transparency MUST be planned per material and MUST NOT be painted per pixel as a gradient.

For cutouts such as vents, perforations and mesh guards, the material MUST use `alphaMode: MASK` with `alphaCutoff` 0.5 and binary alpha in a PNG base color texture.

An opaque part MUST NOT be tagged `alphaMode: BLEND`.

**Implementation Note.** A base color texture needs an alpha channel in exactly one case: the opacity varies across the surface of one material, which is the cutout case above. Uniform translucency is a factor, not a channel. The BlueBoat chassis is a cutout region wearing the wrong clothes: 0.56 percent of its map is non-opaque and the whole hull is tagged `BLEND` for it, where `MASK` at cutoff 0.5 loses nothing.

> **Open.** How uniform translucency, such as an acrylic tube, is expressed, and whether `BLEND` is used at all given that this project's primary consumer ignores it. Proposed: give each translucent region its own material with the opacity in `baseColorFactor` alpha and the texture RGB only. Whether that material is tagged `BLEND` for the benefit of other viewers, or left `OPAQUE` so the file reads the same everywhere, is the part still to agree. Tracked as review decision 6.

**Implementation Note.** Gazebo honors `MASK` and ignores `BLEND` entirely, rendering the material opaque. Uniform opacity reaches it instead through the alpha of `baseColorFactor`, on any alpha mode, and is applied twice, so an alpha of 0.5 renders at about 0.25. `doubleSided` is honored only on a `MASK` material; every other surface is back-face culled, so thin geometry needs thickness.

## 10. Prohibited content

A delivered file MUST NOT contain:

- a non-empty `extensionsRequired` array
- animations, skins, cameras or lights
- Draco mesh compression
- KTX2 or Basis textures
- the `KHR_texture_transform` extension

**Implementation Note.** These are prohibited for different reasons, and the reasons matter if one is ever reconsidered. Draco decodes correctly in both consumers but defeats the project's own inspection tools. Texture transform is parsed and then ignored, so textures render in the wrong place. Animations are imported and force the bounding box to a unit cube, breaking culling. Cameras and lights are ignored harmlessly. An empty `extensionsRequired` is the single check that covers the general case, and it is worth being clear about what that check buys. The glTF specification requires a conforming reader to refuse a file outright when it requires an extension the reader does not implement, so one reading of this rule is that it saves us from a file that would fail to load. Measurement says otherwise: `Distribution_Warehouse`, which declares `KHR_texture_transform` in `extensionsRequired`, loads through gz-common without complaint, building 3,010 submeshes and 19 materials. Gazebo is not a conforming reader on this point. The rule therefore protects against a file that loads and is silently wrong, which is the worse failure and the one nobody notices. The Gazebo team's own demo assets declare `KHR_texture_transform` and `KHR_materials_specular`, so files from that workflow will fail this section and need re-export.

> **Open.** Which of these prohibitions are permanent. Two are not statements about the format: Draco decodes correctly in both consumers and is prohibited only because it defeats this project's own inspection tools, and KTX2 is prohibited because Gazebo cannot read it while Drake recommends it for performance (1.2). Both would be reconsidered if the tooling or the consumer changed, and compressed geometry and supercompressed textures are the two levers with real size savings behind them. Animations, cameras and lights are prohibited on their merits and are not expected to change. Not yet on the review's decision list.

## 11. Authoring toolchain

> **Open.** Whether the Blender and exporter versions are pinned as part of the project's version stack, and at which version. Proposed, from section 7 of the review: Blender 5.1 with `io_scene_gltf2` 5.1.20, an export preset shipped with this specification, and assimp 6.0.4 pinned in drydock alongside the Gazebo libraries, with versions tracked at patch level because the behavior that changed during the audit changed in a patch release. The modeler is outside our infrastructure, so the authoring half is a convention plus an acceptance check, not a technical constraint. Tracked as review decisions 8, 10 and 17.

Interim rule. Until that is decided, a delivery MUST record the exporter that produced it, which glTF does automatically in `asset.generator`, and the integrator SHOULD check it against previous deliveries.

**Implementation Note.** Every current delivery reports `Khronos glTF Blender I/O v5.1.20`, which corresponds to Blender 5.1. The generator string records the tool but not the settings, so two files from the same exporter can still differ in image format, tangents and compression. A version pin is therefore necessary but not sufficient, and the checks in section 12 constrain the outcome rather than the settings.

## 12. Conformance

A delivery conforms when all of the following hold. The first two are the modeler's responsibility, the third and fourth the integrator's.

1. **Valid.** Zero errors from the Khronos glTF Validator.
2. **Intended.** The model renders as the modeler intended in a conformant viewer. The Khronos glTF Sample Viewer is the reference. Blender's viewport is not, because it shows Blender's materials rather than the exported file.
3. **Compliant.** Every MUST in this specification is satisfied, checked mechanically where possible.
4. **Usable.** The part renders correctly in Gazebo and loads in RViz.

**Implementation Note.** These are four different questions and they fail independently. A file can be valid and not what the modeler meant. It can be both and still render wrong in Gazebo, which implements a subset of glTF and is actively changing. Passing in Gazebo is necessary and never sufficient, because a defect can be masked by something Gazebo ignores. External viewers such as Babylon and F3D are not a Gazebo proxy either; `glb_probe`, which prints what the loader built, is.

### 12.1 Checks (Informative)

The mechanical checks implied by this specification, and where they are described, are collected in the review document: file-level lint in section 2.2, the loader probe in section 2.1, the validator in section 2.6, the render checks in section 2.3, and the pass or fail table in section 2.5.

> **Open.** Whether the probe and the lint become a CI test alongside the existing base color guard, and where they live. Proposed: yes, because a floating assimp and Gazebo version can only be tolerated if the acceptance check is automated. Tracked as review decision 7.

> **Open.** Whether to commit a probe dump per part, so that a redelivered binary mesh produces a readable diff. Tracked as review decision 14.

## 13. Open questions (Informative)

Every Open block in this document, in order. Settled rules are not listed: they are the normative text. This table is the to-do list for finishing the draft.

Some entries are questions with no answer proposed, some are proposals awaiting agreement, and some are rules this draft states in their simplest form on purpose -- 4.1 on compound deliveries, 4.2 on the binary container and 10 on which prohibitions are permanent are all of the third kind. Section 2.4 explains why they are not distinguished here.

| Section | Question | Decision |
|---|---|---|
| 4.1 | Compound delivery supported later | none yet |
| 4.1 | Delivery manifest; Blender source archival | 12 |
| 4.1 | Cited dimensional source per part | 13 |
| 4.2 | Binary container as the only permitted form | none yet |
| 4.2 | Textures embedded or external | 16 |
| 5.2 | Stating the RViz distribution floor | none yet |
| 5.3 | Forward axis +X | 2 |
| 5.4 | Origin placement | 2 |
| 5.5 | Root translation prohibited outright | none yet |
| 5.5 | Multiple nodes, and what "one mesh" means | 15 |
| 5.6 | Datum specification for the part coordinate system | none yet |
| 6.1 | Whether the 0-to-1 UV requirement survives | 5 |
| 6.2 | Triangle budget, by visual requirement tier | 5, 18 |
| 6.3 | Primitive count, and ruling out submesh selection | none yet |
| 7 | PBR-in-SDF workspace rule for GLB parts | none yet |
| 8 | Base color format and per-map size caps | 4 |
| 9 | Uniform translucency and use of BLEND | 6 |
| 10 | Which prohibitions are permanent | none yet |
| 11 | Toolchain version pin | 8, 10, 17 |
| 12.1 | Probe and lint in CI | 7 |
| 12.1 | Committed probe dump per part | 14 |

Decision numbers refer to section 10 of [VISUAL_ASSET_PIPELINE_REVIEW.md](../reference/pipeline-review.md). Review decision 9, contributing the loader table upstream, is not a rule of this specification and is not listed. Items marked "none yet" were raised in the glTF reading notes after the review's list was written and should be added to it.

## 14. References (Informative)

The workflow this specification serves is built on published standards owned by other people, and defines project convention only where no standard reaches. This is deliberate. A project-local convention must be taught to every modeler, defended in every review and remembered by everyone who touches the pipeline. A standard is documented by someone else, understood by people not yet hired, and supported by software nobody here has to maintain.

| Standard | Title | Role here |
|---|---|---|
| [glTF 2.0](https://registry.khronos.org/glTF/specs/2.0/glTF-2.0.html), Khronos, registry revision 2.0.1 | glTF 2.0 Specification | The mesh format and its material model. Normative except where this profile narrows, adds to, or departs from it, each of which is marked. The Khronos registry text is cited rather than ISO/IEC 12113:2022, which froze the same content in 2022 and does not carry the extension registry |
| [REP 103](https://www.ros.org/reps/rep-0103.html), ROS | Standard Units of Measure and Coordinate Conventions | Coordinate conventions and units for the part frame |
| [BCP 14](https://www.rfc-editor.org/info/bcp14), IETF | Key words for use in RFCs to Indicate Requirement Levels: [RFC 2119](https://www.rfc-editor.org/rfc/rfc2119) as amended by [RFC 8174](https://www.rfc-editor.org/rfc/rfc8174) | The meaning of the requirement keywords in this document |
| [REP 158](https://github.com/openrobotics/reps/blob/main/_posts/rep-0158%3A2006.md), ROS and Gazebo (Draft) | OpenUSD Conventions for Simulation Asset Interoperability in Open Source Robotics | A strict OpenUSD profile for simulation assets. Its section 3 defines the export pathway to other formats, glTF 2.0 among them, and its geometry, material and texture rules are written for that pathway. Cited below wherever a rule here matches one of its requirements |

Three obligations follow from that design goal, and this document is bound by all of them. Where this specification departs from a standard, the departure is stated explicitly and the reason given, never left as a silent local habit. Where it adds a requirement the standard does not make, the rule says which consumer needs it, so that a reader can tell a limitation of our tools from a property of the format. And where a standard is silent, this specification says so plainly rather than implying an authority that does not exist.

**Implementation Note.** Gazebo's glTF support carries no roadmap commitment, and this document does not treat it as one. The published Gazebo roadmap has no glTF, GLB, PBR or mesh-format item. The direction is on record only in project management committee minutes: [2026-08-17](https://discourse.openrobotics.org/t/gazebo-pmc-meeting-minutes-2026-08-17/57494) discusses deprecating COLLADA in favor of glTF and GLB and leaves it unresolved, and [2026-06-15](https://discourse.openrobotics.org/t/gazebo-pmc-meeting-minutes-2026-06-15/55498) decided to move mesh loading to Assimp by default. Behavior is what `MeshManager.cc` does today, which routes `gltf`, `glb` and `fbx` to the Assimp loader while `dae`, `obj` and `stl` keep their custom ones. Rules below cite that behavior as intent or as fact accordingly, never a roadmap.
