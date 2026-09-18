# What the examples say

The prose half of the assessment. [ASSESSMENT.md](ASSESSMENT.md) is generated and says what each asset contains; this says what that means, and it is written by hand. [criteria.md](criteria.md) says what is being asked and why.

The first section is the Fuel survey of 2026-09-12, moved here from the annotated glTF specification in `tools/glTF`, where it had outgrown a reading note. It is the starting point of this list rather than a result of the tool: every asset it names is now an entry in [examples.yaml](examples.yaml), measured mechanically and repeatably instead of by hand.

---

## Fuel, surveyed whole (2026-09-12)

Surveyed the whole library through the Fuel REST API rather than the web UI, because neither mesh format nor articulation is a searchable field there. `GET /1.0/models?per_page=100` walks all 3,371 records; `/1.0/{owner}/models/{name}/tip/files` gives each model's file tree; `/tip/files/model.sdf` gives the SDF. For the glTF assets themselves, an HTTP Range request for the first twenty bytes of a `.glb` yields the JSON chunk length, and a second range request yields the chunk -- so every glTF file in Fuel can be inspected without downloading a byte of geometry. That matters here: the 54 glTF files total 534 MB, of which one model is 429 MB. It is also the trick `gltf_assess.py` is built on.

The sharp version of the result is that glTF is nearly absent from Fuel, and entirely absent from the part of Fuel we would want to learn from.

Excluding the 1,033 GoogleResearch scanned objects -- shoes, bottles, toys, uniformly OBJ plus MTL plus JPEG, one mesh each -- leaves 2,333 models with retrievable file trees:

| Contains | models |
|---|---|
| `.dae` | 1,404 |
| `.obj` | 350 |
| `.stl` | 300 |
| `.gltf` or `.glb` | 54 |

Narrowing to things that are robots in our sense -- at least one `<sensor>` or an actuation/control plugin, which catches quadrotors whose only joints spin propellers and free-flyers with thrusters and no joints at all -- gives 427 models. Three of them use glTF. By upload year there were none before 2024 and exactly one per year since, against 21 to 75 COLLADA platforms per year throughout. All 33 `<actor>` skins in the library are COLLADA.

So there is no community practice for glTF robots to copy, and no second opinion to check ours against. That is a finding rather than a dead end, since it removes "but everyone else does it this way" as an argument in either direction, but it does mean the spec is doing original work and should say so.

The three that qualify:

| Model | Container | Links | Joints | Triangles | Note |
|---|---|---|---|---|---|
| `Open-RMF/Caddy` | `.gltf` + `.bin` | 11 | 8 | 7,714 | The only single-file-plus-`<submesh>` precedent in Fuel |
| `proque/atmos` | GLB | 9 | 0 | 195,403 | Thrusters, IMU, barometer, navsat; factor-only materials |
| `proque/atmos_dual` | GLB | 13 | 4 | 1,463,312 | Mixes one GLB with four DAE meshes; absolute versioned URL as the mesh URI |

`Open-RMF/Caddy` is worth reading in full, because it is the one model in Fuel that answers the question behind spec section 6.3 -- does anything downstream ever need to select a sub-entity out of the file. It carries the whole vehicle in `polaris.gltf` and each link picks its own part out by node name:

```xml
<mesh>
  <uri>model://Caddy/meshes/polaris.gltf</uri>
  <submesh><name>Front_Wheel_Left</name><center>true</center></submesh>
</mesh>
```

Eleven visuals, one URI, eleven `<submesh>` selections, `<center>true</center>` on every moving part so its geometry is recentered on its joint origin and `<center>false</center>` on the chassis. Three defects in it are as instructive as the pattern. The file declares an external `"uri": "Ranger_Diffuse.png"` that is not in the upload -- fetching it returns 404 -- so the only articulated glTF robot in Fuel renders untextured, which is a direct argument for self-contained GLB over `.gltf` plus loose files. Node names are duplicated between each parent transform node and its mesh child, so `Steering_Wheel` matches two nodes and `<submesh>` resolution is ambiguous. And a 0.0255 scale factor is baked into every node transform rather than into the mesh data.

What the other 51 glTF files tell us, all of them props, scenes or test uploads. Seven of the 54 are byte-identical re-uploads of someone else's asset, so there are 47 distinct files.

- Container: 53 GLB to 1 `.gltf` plus `.bin`, and the one non-GLB is the broken one.
- Tooling: 50 of 54 from the Blender glTF exporter, versions 3.3 through 5.1. Two from Sketchfab, one from Unity. No pipeline diversity to learn from.
- Scope actually used: zero animations, zero skins, zero cameras, across every file. Every primitive is mode 4. Exactly one primitive in the entire corpus carries `TANGENT`, which agrees with what `glb_probe` found about our own loader.
- Texture format: 5,429 JPEG images against 95 PNG. Forty-four of the 54 carry normal maps and 37 carry packed metallic-roughness maps, overwhelmingly as JPEG. This contradicts spec decision 4 and REP-158 head-on. It does not overturn either -- a corpus of warehouse props is not evidence about correctness -- but it does say that assets delivered to us by anyone working in the normal way will arrive with JPEG normal maps, so the spec needs to state the rule and the remedy rather than assume the toolchain produces PNG.
- The metalness default trap is live: 128 materials across 9 models leave `metallicFactor` unset, so 1.0, with no metallic-roughness texture to override it. `dhyutin/trial` is 8 of 8; `proque/atmos` is 80 of 404. The same defect we found in four of fifteen delivered parts.
- Extensions: `KHR_materials_specular` in 29 models, `KHR_materials_ior` in 13, `KHR_materials_transmission` in 9, `KHR_texture_transform` in 6, `KHR_materials_unlit` in 2. Five models put `KHR_texture_transform` in `extensionsRequired` rather than `extensionsUsed`, which a spec-compliant reader must refuse to load outright. Those five are a ready-made conformance probe for what Gazebo actually does -- `OpenRobotics/Distribution_Warehouse` is the convenient one.

The two assets worth keeping as reference material:

- `OpenRobotics/Forklift` -- the best-authored glTF asset in Fuel. Self-contained GLB, 15,492 triangles, embedded albedo, normal and packed metalness-roughness maps, and roughly 30 hand-placed primitive colliders in the SDF against the single visual mesh. That collision discipline is worth as much as the material work. Its normal map is JPEG.
- `OpenRobotics/Ionic Mascot` -- the factor-only case: 12 materials, no textures at all, explicit `metallicFactor: 0` on the non-metals. Also a counter-example on naming, with 148 nodes called `Cylinder002`, `Line001`, `Torus008`. Nothing in that file could be addressed by `<submesh>`.

One caution about reading Fuel for SDF convention rather than for assets. Across the 427 robot platforms, 67% use primitive-only collision, 64% declare `<material>` in the SDF, 30% still reference the Gazebo Classic `gazebo.material` script, and only 8% use `<submesh>` at all -- the dominant pattern is one mesh file per link, as in `bosdyn_spot` with 27 separate meshes. Of the 65 platforms declaring `<pbr>` in the SDF, every one pairs it with COLLADA and none with glTF. The two material approaches in the library are cleanly separated, and nobody does both, which is the one thing worth reconciling against the "PBR must be declared in the SDF" rule in the workspace `CLAUDE.md`.

### The question left open when this moved

The section it came from ended with one unanswered question: which popular projects, measurable by GitHub analytics, use glTF assets in Gazebo. It was answered separately, by code search rather than by analytics, in [community-exemplars.md](../docs/evidence/community-exemplars.md), and the cohort it names is what group `ros` of [examples.yaml](examples.yaml) is drawn from. What that document could not do is say what those assets contain, one criterion at a time, in a form that stays true when they change. That is what this directory is for.

---

## The assessed corpus (2026-09-16)

> Stale as of the same day. The numbers below were counted over all 49 assets. The report has since been narrowed twice -- the Khronos control files are out of the corpus summary, and so is anything not changed in the last three years -- so its figures are over 42 assets and will not match these. This section needs a pass once the corpus definition settles. The conclusions are unaffected; the counts are not.


Forty-nine assets, listed in [examples.yaml](examples.yaml) and measured into [ASSESSMENT.md](ASSESSMENT.md): the Gazebo team's own demo assets, the six Fuel models worth reading closely, the robots shipped as glTF by projects outside the Gazebo team, two Khronos reference files as a control, and two more Khronos files packaged with Draco and KTX2 as a deliberate probe of the prohibitions in spec sections 8 and 10. It is a sample rather than a population, and it is weighted -- seventeen of the forty-nine are jetty_demo, which is one team and one workflow, not seventeen independent opinions. The two probes are ours, not practice, and are called out wherever they move a number. Read the percentages with that in mind.

### Robot assets are untextured; textured assets are not robots

Seventeen of the forty-nine carry no images at all, and the split follows what the asset is rather than who made it. The untextured files are the robot parts: every ROSbot link, every SO-ARM101 part, JPL's Ingenuity, the Skydio 2, the vanttec hull. The textured files are environment props and scenes: forklifts, pallet racks, warehouses, drums. Factor-only materials are 519 of the 601 in the corpus.

That is the most uncomfortable finding for us, because our own parts are textured robot parts and almost nobody else is making those. The assets that look like ours in content -- a vehicle, a sensor, a bracket -- look nothing like ours in material work, and the assets that look like ours in material work are warehouse scenery. It is the same conclusion the Fuel survey reached, arrived at from a different direction: the specification is doing original work.

The mechanism is visible in the generator strings. The untextured robot files come from `trimesh`, `THREE.GLTFExporter` and `assimp`, which are CAD and format-conversion pipelines; the textured ones come from the Blender exporter, which is an art pipeline. Thirty-eight of the forty-nine come out of Blender, so this is not pipeline diversity so much as two uses of one tool plus a handful of converters.

### The [0,1] UV rule is the one nobody follows

Nineteen of the forty-nine put UV coordinates outside [0,1], including one of the two Khronos reference assets. The Gazebo team's own files run u to about 2.0 across seven models, `thor_table` runs v from -499 to 501, and `fuel/atmos` covers -7.4 to 8.4 in both axes. This is deliberate tiling against a REPEAT sampler, not an authoring accident: it is how a surface gets a repeating material without a large map.

`model-spec.md` section 6.1 requires [0,1] and REP-158 requires it too, reserving anything outside for "seamless tiling with repeat wrap modes" -- which is exactly what these files are doing. So the rule is not wrong, but it is narrower than it reads, and it forbids a technique in normal use by the team that maintains our primary consumer. Worth stating in the spec as a deliberate cost, with the reason (half-float UV storage after load, and the texel-density measurement it makes possible) rather than as a rule everyone would agree with.

### Nobody uses alpha, and four fifths of materials ask for two-sided rendering

Across 601 materials there is not one `MASK` and not one `BLEND`. Every material in the corpus is `OPAQUE`. Section 9 of the spec, and review decision 6 with it, is legislating for a case that this corpus never exercises -- which is either a reason to keep the rule cheap, or a warning that we are the ones who will find the bugs.

Meanwhile 462 of those 601 materials are `doubleSided`. Gazebo honors `doubleSided` only on a `MASK` material, and there are none, so four fifths of the materials in this corpus are asking for two-sided rendering and being back-face culled instead. Nobody appears to have noticed, which suggests the geometry has thickness anyway and the flag is a Blender default rather than an intent. It also means the spec's advice that thin geometry needs thickness is the right advice, and that it is being followed accidentally.

### The metalness trap is not ours, it is glTF's

132 materials across 13 of the 49 assets are metallic with no metallic-roughness texture to override the factor, and 106 of those got there by leaving `metallicFactor` unset, where the glTF default is 1.0. `fuel/atmos` is 80 materials; JPL's Ingenuity parts are 12, 6 and 6, straight out of `THREE.GLTFExporter`; ARIAC's battery cells are 4 each.

This is the same defect found in four of fifteen of our own delivered parts, and it is the clearest case in the whole assessment of a rule that earns its place. It is not a modeler being careless. It is a format default that means "metal" when the author said nothing, reached through exporters that say nothing by default.

### Two assets would break RViz, and only one of them is somebody else's

`simple_warehouse/thor_table` has two materials -- `Aluminum_Brushed` and `Stainless_Steel_Glossy` -- carrying a normal map and a metallic-roughness map and no base color texture. That is precisely the shape that terminates RViz, which iterates a material's texture properties and asks for the diffuse one. The same file has two primitives with no material at all, which render as white metal.

The other two such materials are in `ABeautifulGame`, the Khronos Draco and KTX2 probe, which says the shape is not exotic. Two assets in forty-nine is a low rate, and the rule is still worth having: the community file it appears in is by the Gazebo rendering maintainer, in the workflow we are being told to copy, and the defect is invisible in Gazebo and fatal in RViz. That is exactly the class of thing a specification is for.

### The `extensionsRequired` probe is real and it is one file

`Distribution_Warehouse` -- the same asset in Fuel and in jetty_demo, byte for byte -- declares `KHR_texture_transform` in `extensionsRequired`, not in `extensionsUsed`, and applies the transform to texture slots. A conforming reader must refuse to load the file outright. Our own audit says Gazebo parses the extension and then ignores it, which predicts that the textures land in the wrong place rather than that the file fails.

Both predictions cannot be right, and this is the one asset that settles it. The two Draco and KTX2 probes sit beside it as the easier half of the same question: those extensions are genuinely unimplemented rather than parsed and dropped, so a consumer has no way to be quietly wrong about them.

**Settled, 2026-09-18.** Run through `glb_probe` against the installed gz-common, `Distribution_Warehouse` loads. The probe reports 3,010 submeshes, 19 materials and a bounding box of roughly 62 by 74 by 13 metres, with no error and no refusal, from a file whose `extensionsRequired` is `["KHR_texture_transform"]`. So the glTF specification's requirement -- that a conforming reader refuse a file requiring an extension it does not implement -- is not what Gazebo does, and the reading of the code in the review was right.

That changes what section 10's prohibition is for. It is not protecting us from a file that will fail to load; it is protecting us from one that loads and is quietly wrong, which is the worse case and the harder one to notice. The rule stands and its reason should be restated in those terms.

Two things the probe does not settle. Whether the textures actually land in the wrong place needs a rendered view, since the loader reports what it built and not what it looks like; the prediction is that the transform is dropped and the textures are misplaced. And the same file carries two UV sets and 3,010 root nodes, so it violates several other sections independently -- it is a probe of one rule, not a representative delivery.

### Texture format: the corpus is JPEG and the standards are PNG

Counted by image rather than by use, normal maps are 38 JPEG to 4 PNG, and metallic-roughness maps 39 JPEG to 6 PNG. Base color is 45 JPEG to 13 PNG, which is the one slot where JPEG is defensible. The 10 to 13 KTX2 images in each slot are all from the Khronos probe and are nobody's practice.

This is the sharpest spec-versus-practice disagreement in the assessment, and it is not close. `model-spec.md` section 8 and REP-158 both require PNG for linear data; the corpus, including every asset the Gazebo team ships, uses JPEG. Nothing here changes the physics -- chroma subsampling really does blend channels that have nothing to do with each other -- but it does settle how the rule should be written. It is a rule about what we accept, not a description of what arrives, and the spec already says so. What it should add is that the remedy is a re-export from the source texture, because converting a JPEG normal map to PNG preserves the damage.

Seven assets exceed the 2048 texture cap, all at 4096, and all in the Gazebo and warehouse cohort. There is no size discipline anywhere in the corpus: one warehouse is 85 MB in a single visual.

### Structure: the rules in section 5.5 are broken by export default

Nineteen of forty-nine carry a rotation or matrix on the root node, which is the Blender Y-up conversion node nobody removes, and twenty-two carry a root scale. Only twenty-one -- fewer than half -- have the shape our spec requires: exactly one root node, named, with no rotation.

Two structural findings cut the other way, in favor of rules we have. The primitive count equals the material count in 41 of 49 assets, which is the rule proposed in spec section 6.3, free of charge. And nothing in the corpus uses more than one scene, has an animation, a skin, a camera or vertex colors, or a non-triangle primitive, and only two assets carry tangents. Leaving aside the two probes, which were chosen to violate it, the prohibitions in section 10 cost the corpus nothing at all.

Fifteen of forty-nine have primitives sharing a node name, so an SDF `<submesh>` selection on those names would take the first and silently drop the rest. That is the upstream naming defect, live in a third of the corpus.

### Scale is not reliably meters, and one asset is visibly wrong

`rosbot/body` measures 214 x 166 x 199, `tri/skydio_2` 133 x 161 x 30: both are millimeter files corrected downstream by a URDF `scale`, which husarion does deliberately and documents. glTF says meters, and neither file is at meters.

`jetty/Picking_Bin` looked like a third case at 8 x 18 x 9 meters on 36 triangles, and is not: its `model.sdf` places hand-authored colliders 8 x 17.3 x 9 meters around it, so the file is internally consistent and it is the name that misleads. That is the more useful lesson. An extent measurement catches a file that disagrees with itself, and this one does not; what would catch a wrong scale is a cited dimensional figure per part, which is exactly the open question in spec section 4.1.

### What it cost

The whole corpus is 309 MB of asset and was assessed by fetching 75 MB of it, in 467 requests. Nothing was downloaded whole except the files small enough that downloading them was cheaper than three range requests. That is what makes the list extensible: adding the forty-eighth asset costs one asset.

---

## What this should change in `model-spec.md`

In rough order of how much the evidence moves:

1. Section 6.1, the [0,1] UV rule. The corpus says it forbids a technique in normal use, including by the Gazebo team. Keep it, but state the cost and the reason rather than implying consensus.
2. Section 10, the `extensionsRequired` prohibition. Run `Distribution_Warehouse` through `glb_probe` before the rule is finalized; the prediction in the review and the prediction in the glTF spec disagree, and one file settles it.
3. Section 9, transparency. The corpus has no `MASK` and no `BLEND` at all, and 79 percent `doubleSided` that Gazebo ignores. Decision 6 can be taken on our own terms; there is no practice to defer to.
4. Section 8, texture format. Unchanged in substance, sharper in framing: state that conforming deliveries will be the exception, and that the remedy is a re-export rather than a conversion.
5. Section 6.3, one primitive per material. Now measured at 41 of 49 in the wild, so the proposed rule is free.
6. Section 5.1, scale. Two files in the corpus are in millimeters by design and one appears to be wrong by a factor of a hundred. A measured extent check belongs in the acceptance tooling.
7. Section 5.5, the single unrotated root node. Fewer than half the corpus complies, and the failures are export defaults rather than decisions. The rule stands; the note should say that a delivery arriving without it is normal and is fixed at export, not in review.

## Open threads

- The `<submesh>` question can be closed with evidence now: nothing in the corpus except `Open-RMF/Caddy` uses submesh selection, and a third of the corpus could not support it if it tried.
- Nothing here reads the SDF or URDF beside the asset, which is where `<material>`, `<pbr>`, `<submesh>` and the collider conventions live. That is criteria B5, B6 and I2, and it is the largest gap in the assessment as it stands.
- Our own parts are on the list and parked. Turning them on would say how far we sit from the corpus, as against how far we sit from the spec, which `glb_inventory.py` already measures.
