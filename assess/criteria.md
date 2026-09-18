# What we assess in a glTF example

This is the draft of the assessment itself: the list of things worth knowing about a glTF asset that somebody else wrote. It is the input to `gltf_assess.py`, which implements the mechanical part of it, and the counterpart to [model-spec.md](../docs/profile/profile.md), which states top-down what a delivered model must be. This list is bottom-up. It asks what assets in the wild actually are, so that every rule in the spec can be checked against practice rather than against argument alone.

The two differ in what a row means. A rule in the spec is a requirement, and a delivery either meets it or does not. A criterion here is a question, and an example either answers it or does not. Where an example diverges from the spec, that is a disagreement to resolve, not a defect in somebody else's file: several of the spec's open decisions exist precisely because the corpus disagrees with the draft rule.

## How to read it

Criteria are grouped A to J and numbered within a group. The ids are stable and are what the generated [ASSESSMENT.md](ASSESSMENT.md) cites, so a finding in the report can be traced back to the question it answers.

The last column says where an answer comes from, which is also a statement about cost:

| | |
|---|---|
| tool | `gltf_assess.py`, from the JSON chunk and a few kilobytes of image header. Costs nothing and runs on the host. Every such measurement is in `results.json`; `ASSESSMENT.md` surfaces the subset a reader needs to see. |
| tool+geo | The same tool, but it must read vertex data, so it is subject to the per-asset byte budget and is skipped on very large assets. |
| planned | Agreed as worth measuring, not yet implemented. |
| probe | `glb_probe` inside drydock, which reports what gz-common's loader actually built rather than what the file says. The only Gazebo proxy we trust. |
| rig | Needs a person in front of the visual rig, which `--rig` sets up: the asset beside an axis marker in Gazebo and in RViz. See the protocol under group D. |
| render | Needs a window: Gazebo, RViz or the Khronos sample viewer. Cannot be automated from here. |
| judgement | A person looking at the file and deciding. |

The `Why` column names the section of `model-spec.md` the criterion bears on, where there is one. Criteria with no spec section are the ones where the corpus may tell us something the spec does not yet have an opinion about.

---

## A. Provenance and header

Who made the file, with what, and what it claims to be. Cheap, and it explains most of what follows: almost every divergence in the corpus is an exporter default nobody changed.

| id | What we measure | Why we want to know | From |
|---|---|---|---|
| A1 | `asset.version` | Anything but `2.0` is not a file we can read. Spec 4.3. | tool |
| A2 | `asset.minVersion` present | A hard load failure in a consumer that would otherwise have coped. Spec 4.3 turns on how often this appears in practice. | tool |
| A3 | `asset.generator` | The single best predictor of every material and texture defect. Spec 11 proposes pinning a toolchain; this says how much variety is out there. | tool |
| A4 | `asset.copyright`, and the license beside the file | Whether an asset can be used as a reference, or only read. | judgement |
| A5 | Where it came from, and who maintains it | An asset from the Gazebo team is evidence about Gazebo; an asset from a props marketplace is not. | judgement |

## B. Packaging and delivery

The one decision that is settled in our spec and contested everywhere else.

| id | What we measure | Why we want to know | From |
|---|---|---|---|
| B1 | Container: self-contained `.glb`, or `.gltf` with side files | Spec 4.2 requires `.glb`. Drake refuses `.glb` outright and TRI and JPL both ship `.gltf` plus `.bin`, so this is the live disagreement. | tool |
| B2 | Referenced files that do not resolve | The failure mode `.glb` exists to prevent. Fuel's only articulated glTF robot ships a 404 texture. | tool |
| B3 | Images embedded or external | Spec 4.2 leaves this open (decision 16). Worth knowing whether anybody mixes the two. | tool |
| B4 | File size, and the geometry-to-texture split | Textures are 59 percent of our own bytes. Whether that ratio holds elsewhere decides whether external images would actually buy anything. | tool |
| B5 | Number of files per model, and per link | The per-link-mesh versus one-file-plus-`<submesh>` question in spec 5.5 and 6.3. Fuel is 92 percent one file per link. | planned |
| B6 | Whether an SDF or URDF ships beside the asset, and what it declares | Whether `<material>`, `<pbr>` or `<submesh>` appear at all. Directly against the workspace `<pbr>`-in-SDF rule. | planned |

## C. Scene and node structure

What the file is, as a tree. This is the group that decides whether anything downstream can address part of a file.

| id | What we measure | Why we want to know | From |
|---|---|---|---|
| C1 | Scene count and which is default | Spec 5.5 requires exactly one. Leftover empty scenes are a common export artifact. | tool |
| C2 | Root node count | Spec 5.5 requires exactly one. | tool |
| C3 | Root node carries `rotation` or `matrix` | Spec 5.5 forbids it, for a tooling reason rather than a format one: `gltf_to_yup.py` will not convert such a file. | tool |
| C4 | Root node carries a `scale` | Scale in the transform rather than in the mesh data. Fuel's Caddy bakes 0.0255 into every node. Silently wrong in anything that reads accessor bounds. | tool |
| C5 | Node count, depth, and duplicate names | Depth and duplication are what make `<submesh>` selection ambiguous. | tool |
| C6 | Primitives sharing a node name | Gazebo names a submesh after its node, so these are indistinguishable to SDF: the selection takes the first and silently drops the rest. Spec 6.3. | tool |
| C7 | Node names that an exporter invented (`Cylinder002`) | Whether anything in the file is addressable at all. Fuel's Ionic Mascot has 148 such nodes. | tool |
| C8 | Mesh instancing: one mesh used by several nodes | Changes what the loader builds, and what a triangle count means. | tool |
| C9 | Meshes reachable from no scene | Dead weight that still costs bytes. | tool |

## D. Coordinates, units and scale

| id | What we measure | Why we want to know | From |
|---|---|---|---|
| D1 | Overall extent in meters | Whether the file is at real-world scale. Spec 5.1. A model in millimeters corrected by a URDF `scale` is a real pattern, not a mistake: husarion does it deliberately. | tool |
| D2 | Where the origin sits inside the bounding box, per axis, as a fraction | Spec 5.4 is open on where a part's origin should sit. Reported as a reading -- "centered in X, centered in Y, on the -Z face" -- because that is the form a convention is written in. | tool |
| D3 | Which file axis is up | glTF says Y-up and every consumer assumes it. A Z-up file renders correctly in one consumer and wrong in the other, and no measurement can tell them apart: both are a box of triangles. Spec 5.2. | rig |
| D4 | Which file axis the part faces | Spec 5.3 is the one candidate departure from glTF. Whether anybody in the corpus faces +Z would settle it, and only a person who recognizes the front of a forklift can say. | rig |
| D5 | Scale baked into node transforms rather than vertices | See C4; recorded separately because it is a units question as well as a structural one. | tool |
| D6 | What the origin sits on, in the part's own terms | The other half of D2, and the half that matters: "on the -Z face" is only useful once somebody says that face is the wheel contact plane. Spec 5.4's proposed convention is stated in these terms. | rig |
| D7 | Whether our `gltf_up:=z` rotation makes the part stand up | The rule in `parts.xacro` is a bet about what arrives. The rig applies it beside the untouched file, so the bet is visible rather than assumed. | rig |

### Determining the origin and orientation by eye

D3, D4, D6 and D7 cannot be measured, and it is worth being precise about why. A glTF file records vertex positions and node transforms and nothing else. There is no up axis in it, no forward axis, no mounting face, no pivot. The specification's "Y-up" and "the front faces +Z" are conventions about what an author should have meant, checked by nobody and enforceable by nothing. So the file cannot be asked. A person who recognizes a forklift can answer all four questions in about a minute, and that minute is the whole protocol.

What the tool contributes first is the arithmetic, so that the minute is spent on the part that needs a person. It composes every node transform, takes the bounds of the composed geometry, and reports where zero sits between them on each axis. `jetty/Forklift` comes out "centered in X, 28% along Y, on the -Z face", which already rules out most readings: whatever is up, it is not X; the origin is on a face in Z and a quarter of the way along in Y. Cross-checked against `glb_probe`, which is gz-common's own loader, the two agree to four decimal places, so the arithmetic is not the uncertain part.

#### The rig

    ./gltf_assess.py --rig jetty/Forklift

writes a Gazebo world and a URDF into `rig/<asset>/`, fetching the asset itself if it is remote, and prints the commands to view them. The world holds four things:

- the asset at the world origin, exactly as authored, with no rotation applied
- an axis marker at that same origin
- the asset again, offset along +Y, with the `+90` degree rotation about X that `parts.xacro` applies for `gltf_up:=z`
- a second marker at that offset

The marker is the one from `spike/coords/make_markers.py`, in the REP 103 body frame, with arms of deliberately different lengths so that no view of it is ambiguous: +X red at full length, +Y green at half, +Z blue at a quarter, and a short grey stub on -X so the sign of X reads as well as its direction. It is emitted as SDF boxes rather than as the glTF marker, because the reference has to be true in the world frame whatever the loader does with glTF -- which is the thing under test.

Two copies rather than one, because the interesting answer is usually comparative. The left-hand copy says what the file is. The right-hand copy says whether our convention is the one that makes it stand up. A file that is already Y-up appears upright on the left and lying on its side on the right; a Z-up file does the opposite. That is a glance, not a measurement.

#### The procedure

1. Run the rig command and read the three lines it prints: extent, the measured origin reading, and the marker legend.
2. Open the Gazebo world. Look down each marker arm in turn. Decide which file axis points up, and which the front of the part faces. If the part has no front -- a drum, a pallet, a bin -- say so and leave forward empty rather than inventing one.
3. Name what the origin sits on in the part's own terms: the wheel contact plane, the base of the mast, the mounting flange, the centroid. This is the answer spec 5.4 is asking for, and it is the one nothing else in the assessment can produce.
4. Open the same rig in RViz. The two consumers do not agree: the Y-up rotation that RViz applies to a glTF mesh merged to `rolling` on 2025-06-16 and was not backported, so a part that stands up in Gazebo may be ninety degrees off in RViz depending on the distribution. Note the distribution you looked at.
5. Record the answers in `visual-notes.yaml`, in the file's own axes rather than in ROS axes, because the file is what is being described. Date it and sign it. An entry with a date and no answers is a useful record too: it says somebody looked and could not tell.

#### What a finished answer looks like

    "jetty/Forklift":
      up: +Z
      forward: -Y
      datum: ground, at the wheel contact patch; centered across the width
      checked: 2026-09-17 bsb
      note: mast folded; the 28% along Y is the rear axle, not the tail

The report folds these back in beside the measurement, and says how many assets remain uninspected, so the protocol has visible progress rather than being a thing we mean to do.

#### Doing it in bulk

The corpus table of measured readings is the cheap way to choose what to look at. Twenty-two of the assets in scope share one reading, so inspecting three of them establishes what that reading means and the rest inherit it by argument rather than by eye. Spend the looking on the assets whose reading is its own -- an origin outside the geometry, an origin at 81% along an axis -- because those are either a convention nobody else uses or a defect, and only a person can tell which.

## E. Geometry

| id | What we measure | Why we want to know | From |
|---|---|---|---|
| E1 | Primitive modes | Spec 6 requires triangles. Everything in Fuel is mode 4, so the rule may be free. | tool |
| E2 | Attributes present: `POSITION`, `NORMAL`, `TEXCOORD_0`, `TANGENT`, `COLOR_n`, joints and weights | Spec 6. Missing normals are generated on import and discard the author's intent. Tangents are never read by our consumers; exactly one primitive in Fuel carries them. | tool |
| E3 | UV set count | Spec 6.1 allows a second set only for a baked occlusion lightmap. | tool |
| E4 | UV range, and whether coordinates leave [0,1] | Spec 6.1 and REP-158 both require [0,1]. Outside that range, tiling depends on sampler wrap modes. | tool+geo |
| E5 | UV shell fill: the fraction of the map the shells land on | Texture memory paid for and not used. `glb_inventory.py` already reports this for our own files. | planned |
| E6 | Triangle and vertex counts | Spec 6.2 has no defensible budget yet. The corpus ranges over four orders of magnitude, which is itself the finding. | tool |
| E7 | Index component type | A `uint32` index buffer on a small mesh is waste; `uint16` on a large one is a correctness question. | tool |
| E8 | Degenerate, zero-area triangles | Spec 6 says they should not be there. | planned |
| E9 | Primitive count against material count | Spec 6.3 proposes that a primitive exists only to carry a distinct material. Whether the corpus splits primitives for other reasons tells us if the rule is free. | tool |

## F. Materials

The group with the highest defect rate in every corpus looked at so far, including our own.

| id | What we measure | Why we want to know | From |
|---|---|---|---|
| F1 | Primitives with no material | Render as white metal, with no fallback. Spec 7. | tool |
| F2 | Materials metallic with no metallic-roughness texture to override it, split by whether `metallicFactor` was declared at all | The single most damaging defect we have found, in our own library and in Fuel. The glTF default is 1.0, so silence means metal. Spec 7. | tool |
| F3 | Materials carrying a texture but no `baseColorTexture` | RViz terminates on one. A target constraint rather than a glTF rule. Spec 7. | tool |
| F4 | Specular-glossiness workflow | Prohibited by spec 7, and long deprecated by Khronos. | tool |
| F5 | `alphaMode` distribution | Gazebo honors `MASK` and ignores `BLEND` entirely, rendering it opaque. Spec 9. | tool |
| F6 | `baseColorFactor` alpha below 1 | How uniform translucency actually reaches Gazebo -- and it is applied twice, so 0.5 renders at about 0.25. Spec 9, decision 6. | tool |
| F7 | `doubleSided` | Honored only on a `MASK` material; everything else is back-face culled, so thin geometry needs thickness. | tool |
| F8 | `normalTexture.scale`, `occlusionTexture.strength` | Spec 7 requires 1.0 because neither consumer reads them, so a baked value is a silent difference between viewers. | tool |
| F9 | Whether uniform properties are delivered as factors or as uniform textures | A texture whose every texel is identical is a factor written the long way. All seven of our own metallic-roughness maps are uniform. Spec 7. | planned |
| F10 | Material names | Hygiene only -- neither consumer reads them -- but a name like `Material.003` says what the authoring process was. | tool |
| F11 | Unused materials | Export residue. | tool |

## G. Textures

| id | What we measure | Why we want to know | From |
|---|---|---|---|
| G1 | Image format per map slot | Spec 8 and REP-158 both require PNG for normal, metallic-roughness and occlusion. The corpus overwhelmingly ships JPEG. This is the sharpest spec-versus-practice disagreement we have. | tool |
| G2 | Formats that do not load: KTX2, Basis, WebP, DDS | The part loads untextured with an error naming an unsupported format. TRI ships 48 KTX2 textures. Spec 8. | tool |
| G3 | Pixel dimensions per map | Spec 8 caps at 2048. Nobody else appears to have a cap. | tool |
| G4 | Texel density, in texels per millimeter of surface | Pixel count alone does not say whether a map is over- or under-sampled. `glb_inventory.py` computes this for our own files. | planned |
| G5 | Decoded texture memory | What the GPU actually spends, which the encoded byte count in the file does not tell you. | tool |
| G6 | ORM packing: occlusion, roughness and metalness in one image | Spec 8 permits it, and it is the efficient form. How common is it? | planned |
| G7 | Alpha channel on an `OPAQUE` material's base color | glTF ignores it, and a reader cannot tell whether it was meant. Spec 8. | planned |
| G8 | Sampler wrap modes | REPEAT plus UVs outside [0,1] is deliberate tiling; REPEAT with UVs inside is just the default nobody changed. | tool |
| G9 | Image names | The only signal a reviewer has for telling maps apart. Spec 8. | tool |

## H. Extensions

| id | What we measure | Why we want to know | From |
|---|---|---|---|
| H1 | `extensionsRequired`, and what is in it | Spec 10 forbids a non-empty array. A conforming reader must refuse such a file outright; five models in Fuel do this by accident. What Gazebo actually does with one is worth probing. | tool |
| H2 | Draco compression | Decodes correctly in both consumers but defeats our own inspection tools. Spec 10. | tool |
| H3 | `KHR_texture_transform` | Parsed and then ignored by Gazebo, so the textures are sampled from the wrong region of the map. Prohibited by spec 10, and used casually by the Gazebo team's own assets, which is a contradiction worth resolving. | tool |
| H4 | `extensionsUsed` as a whole | Which extensions a normal authoring workflow emits without being asked. `KHR_materials_specular` and `KHR_materials_ior` appear in a third of Fuel. | tool |
| H5 | What Gazebo does with each extension found | Ignoring an extension is not the same as failing on it, and the spec's prohibitions assume one or the other. | probe |

## I. Content that is out of scope for a visual part

| id | What we measure | Why we want to know | From |
|---|---|---|---|
| I1 | Animations, skins, cameras, lights | Spec 10 prohibits all four, for different reasons: animations force the bounding box to a unit cube and break culling, cameras and lights are ignored harmlessly. Zero in all 54 glTF files in Fuel. | tool |
| I2 | Whether collision geometry travels in the same file | Nobody in the corpus does this except rmf_site, which emits a separate collision GLB. Bears on spec 4.1. | judgement |

## J. What the consumer will actually do with it

The end of the assessment, and the part that cannot be read out of the file. Spec 12 is explicit that valid, intended, compliant and usable are four different questions that fail independently.

| id | What we measure | Why we want to know | From |
|---|---|---|---|
| J1 | Khronos glTF Validator: errors, warnings, infos | The only external authority. Spec 4.2 requires zero errors. | planned |
| J2 | The submesh list gz-common builds, with names | The names are the file's only addressable interface, and they come from nodes rather than meshes. | probe |
| J3 | Whether the part renders correctly in Gazebo | Necessary and never sufficient: a defect can be masked by something Gazebo ignores. | render |
| J4 | Whether it loads in RViz, on which distribution | The Y-up rotation merged to rolling on 2025-06-16 and was not backported, so Jazzy and Kilted render every glTF part rotated. Spec 5.2. | render |
| J5 | How it looks in the Khronos sample viewer | The reference for what the author meant, which Blender's viewport is not. | render |
| J6 | What the assessment cost: bytes fetched, requests made | Whether this list can be run over a library rather than over a handful of files. | tool |

---

## What this list deliberately does not assess

- Artistic quality. Whether a model looks right is a judgement, and one we would make in a viewer rather than in a table.
- Collision geometry. Out of scope for `model-spec.md` today, and the corpus keeps it in SDF rather than in the asset.
- Physics, sensors and plugins. They live in SDF, not in the glTF, and belong to a different assessment.
- Whether an asset is good for its own purpose. A warehouse prop is not trying to be a robot part, and criticizing it for that would teach us nothing.

## Open questions on the list itself

1. Should an example carry a verdict, or only measurements? The report currently flags divergence from `model-spec.md` and stops short of saying who is right. That is deliberate for now, but a column recording our conclusion about each disagreement would be the thing that feeds back into the spec.
2. How is a library summarized? Seventeen jetty models are one workflow and one set of decisions, not seventeen independent data points. The corpus tables currently weight every asset equally, which overstates whoever shipped the most files.
3. Group B wants the SDF or URDF beside the asset, not just the asset. That is a different fetch and a different parser, and it is where several of the most useful criteria live (B5, B6, I2).
4. Which of the `planned` rows are worth the code? E5, E8, G4 and G6 all need vertex or pixel data and would push the byte budget up considerably.
5. Does this list ever grade our own files? It is written as an outside view, and `glb_inventory.py` covers the inside one, but the two overlap enough that one tool might eventually do both.
