# Towards a first release of gltf-robotics

A living plan. Steps are worked in order, checked off as they close, and rewritten as the work demands. Each step records its outcome (issue number, commit, test result, or decision and why) below its checkbox. Started 2026-10-07.

## Context

Ryan Lee (the modeller, GitHub `phfatmonkey`) ran the new glTF workflow on a test cube and then the BlueBoat chassis during the week of 2026-10-05. His findings are in the "Modeling workflow beta" email thread and, since 2026-10-06, in the shared Google Doc `3DVisualAssetWorkflowDiscussion` in the Honu Drive. He also sent the [mundobytes article](https://mundobytes.com/en/Blender-prepares-and-exports-models-to-GLTF-with-PBR-materials./) on Blender glTF PBR export (2026-10-02). A team call is being arranged for Friday 2026-10-09.

On 2026-10-11 the plan turned from closing issues to piloting the profile and workflow on Ryan's new BlueBoat chassis and propeller models (Plan Step 9); the existing BlueBoat walkthrough is retired (Plan Step 10).

Every one of Ryan's observations has an answer in source read on 2026-10-07, and most point at gaps or contradictions in the docs. A survey of `main` found that no page explains how to author materials in Blender at all, and that the coordinate docs disagree with each other in four places.

Decisions taken so far:

- Each topic becomes a GitHub issue in this repository, so every question has a thread that records the finding, the decision and why. Ryan is not a collaborator, so he can comment but cannot be assigned. The Google Doc gets one closing note pointing at the issues.
- The coordinate rule (URDF `rpy` per distro and the Blender `+Y Up` statement) is Brian's to state definitively; propagation waits on that statement (Plan Step 1).
- Metalness policy is decided after a Gazebo test; the profile keeps its Open item with the finding attached.
- `KHR_materials_variants` is prohibited; one GLB per color variant.
- The profile is the interface and tool-agnostic; the Blender export guide is an informative reference implementation in Blender 5.2.2, one of many configurations that meet it (2026-10-11). Blender statements in the profile became Implementation Notes.
- One Blender page, not two: the options reference (`docs/reference/blender-export-options.md`) is merged into the export guide and deleted (2026-10-11). The guide carries the fourteen-option table, the Images values and the introspection command; the 110-row enumeration lives in git history and the command reproduces it.
- Material authoring in Blender is in scope after all (Issue #6, reversed 2026-10-11): the export guide teaches how to wire a material so the exporter reads it, as part of the informative reference implementation, alongside Ryan's .blend examples. Plan Step 3 stands.
- `export_apply` is on in the reference configuration; the profile neither requires nor forbids it (Issue #7, Ryan's recommendation, 2026-10-11).

## What was established on 2026-10-07

Tags follow the coordinate-systems reference: [Firm] read in source or spec, [Practice] a project decision, [Open] needs a test, [Corrected] reverses an earlier statement.

### Blender exporter

Read from the installed `io_scene_gltf2` 5.2.40 under `/snap/blender/7803/5.2/scripts/addons_core/io_scene_gltf2/`.

- [Firm] Metallic and Roughness are read from the Principled BSDF sockets of those names. If either socket has an image behind it, the exporter writes a `metallicRoughnessTexture`; if the two come from different images it packs them itself, roughness into G and metallic into B (`blender/exp/material/pbr_metallic_roughness.py:200-221`, channel assignment `image.py:355-361`). A `Separate Color` node on a shared ORM image is recognised (`search_node_tree.py:1046`). No script is needed to pack channels.
- [Firm] Occlusion is read from the `Occlusion` input of a node group named `glTF Material Output` (`blender/com/material_helpers.py:21`); the legacy name `glTF Settings` is still accepted (`:11`). It is added from the node editor's Add menu (`gltf2_blender_ui.py:19-43`); the menu entry exists only if the add-on preference `settings_node_ui` is on. The R channel is used and may share the ORM image.
- [Firm] Alpha mode is inferred from the node tree, not from a material setting: constant alpha 1 is OPAQUE; a `Math: Round` node, or `X > cutoff` / `1 − (X < cutoff)`, is MASK with that cutoff (Round gives 0.5); anything else is BLEND (`search_node_tree.py:509-641`). Ryan's rounding is the recognised pattern.
- [Firm] `doubleSided` is written true unless Backface Culling is on (`materials.py:275-285`). Gazebo honours it only on MASK.
- [Firm] The Images option has four values: `AUTO`, `JPEG`, `WEBP`, `NONE`; there is no "force PNG". `AUTO` writes "PNGs as PNGs, JPEGs as JPEGs, WebPs as WebPs. For other formats, use PNG" (`__init__.py:353-365`). A WebP source becomes an embedded WebP that Gazebo cannot load; the docs describe AUTO without that case.
- [Firm] `Apply Modifiers` defaults off and warns it prevents exporting shape keys (`__init__.py:679-684`).
- [Firm] `KHR_materials_variants` is exported only when the add-on preference `KHR_materials_variants_ui` is on, default off (`__init__.py:2214-2215`, `blender/exp/primitives.py:336-398`).

### Consumers

Read from gz-rendering `gz-rendering10` and assimp `v6.0.4`, plus the 2026-09-04 audit in [loader-behavior](../docs/reference/loader-behavior.md).

- [Firm] `Ogre2Material` sets `HlmsPbsDatablock::MetallicWorkflow` and applies a reflection texture only through `SetEnvironmentMap`; nothing applies one by default. `Ogre2Scene::SetSkyEnabled` builds a `Default/skybox` material and sets it as the background material only. An embedded material with metalness 1 has nothing to reflect and renders black except for direct highlights. This is why Ryan's metal is black. [Open] whether any scene-level hook can hand a reflection map to embedded materials; the SDF `<material><pbr><metal><environment_map>` route is closed because an SDF material replaces every embedded one.
- [Firm] assimp 6.0.4 reads `KHR_materials_transmission` and gz-common maps `transmissionFactor` to `Transparency`. Factor 1.0 is fully transparent, which reads as "doesn't show up". RViz does not read it. [Open] confirm with a 0.5 test.
- [Firm] `KHR_materials_variants` does not appear in assimp 6.0.4's glTF2 asset header, so neither consumer reads it; the first material assigned renders.
- [Firm] MASK honoured, BLEND ignored, occlusion from R on UV0, normal maps R and G only: already in loader-behavior as S, now observed by Ryan on the GPU, which upgrades them to P.

### Coordinates and the SDF Ryan loaded

- [Firm] `bluerobotics_parts/models/blueboat_chassis/model.sdf` on `bluerobotics_models` branch `bsb/blueboat_gltf_workflow` (HEAD `782cdde`, 2026-09-29) has no `<pose>` on the visual. It predates the 2026-10-02 switch to glTF-native files. A `+Y Up` export is correct and lands on its side in that SDF because the consumer rotation is missing, not because the flag is wrong.
- The docs disagree on the URDF rotation: `profile.md:184` says Lyrical `rpy="-1.5708 0 1.5708"` and `:185` says Jazzy/Kilted `TBD`; `coordinate-systems.md:566-579` ([Firm]), `exporting-from-blender.md:11`, `workflow.md:93` and `blender-export-options.md:122` say Lyrical `rpy="0 0 1.5708"` and Jazzy/Kilted `rpy="1.5708 0 1.5708"`. `coordinate_orientation_demo.md:288` still says the decision is `+Y Up` off and uses `rpy="-1.5708 0 0"` at L220, L227, L284; `workflow_blueboat.md:257` uses the old roll; `blender-export-options.md:66` still calls the toolchain pin 5.1 and Open. Plan Step 1 resolves which statement is right before any of these are touched.

## Steps, in order

### Step 0. Make this plan a living document

- [x] File created at `plans/2026-10-blender-materials.md` (renamed `2026-10-blender-export-and-model-pilot.md` on 2026-10-11) and committed on `main`, 2026-10-07.

Each later step ends with this file updated and committed: the box checked, the issue number, commit, test result or decision and its reason recorded under it.

### Step 1. The coordinate statement

The rule, stated once: build in Blender's convention (front −Y, up +Z); export with `+Y Up` on, so the file is in glTF's convention (+Y up, +Z forward); the consumer rotates it onto the robotics axes with `<pose>0 0 0 1.5708 0 1.5708</pose>` on the Gazebo visual and `rpy="0 0 1.5708"` on the URDF visual for RViz on Lyrical and later, which rolls glTF files +90° about X itself. Earlier ROS distributions do not rotate and are not supported.

Evidence (2026-10-09): [S] gz-common `gz-common7_7.3.0` `AssimpLoader.cc` L849-853, L955-976 applies no up-axis conversion; [S] rviz `lyrical` `assimp_loader.cpp` L215-222 post-multiplies Rx(+90°) onto the root; [P] `glb_probe` in drydock returns the raw buffer bounds for `monkey.glb` (Y-up) and the Z-up export alike; [M] with R = Rz·Ry·Rx only the stated values give face +X, up +Z; on screen in `gz sim` 10.5.0 and `rviz_rendering` 15.2.5 by Brian, recorded in the [Coordinate orientation demo](../docs/walkthroughs/coordinate_orientation_demo.md). The earlier `rpy="-1.5708 0 1.5708"` in the profile was the right value for a Z-up file and came from the old `monkey.urdf`.

- [x] Statement recorded (above) and shown end to end in the demo, commit `ca1b5ad`.
- [x] Propagated: profile Axes table and Jazzy/Kilted note, stray "; " at L95, `step-4-verify-integrator` anchor; coordinate-systems [Open] on per-distro delivery closed as [Practice]; export guide; workflow; options reference (5.2.2 / 5.2.40 pin); BlueBoat walkthrough banner and a note under its recorded URDF; `examples/monkeys.sdf`. Commit on `main` after `ca1b5ad`.
- [x] Superseded 2026-10-11: the chassis and propeller come back as new models from Ryan, piloted in Plan Step 9. Formerly: `bluerobotics_models` is deferred (Brian, 2026-10-09). The chassis `model.sdf` pose and `part_visual` values are committed locally on `bsb/blueboat_gltf_workflow` as `1d725f0`, not pushed; the chassis `.glb` there is still the Z-up, X-forward export. The migration of `main` off `gltf_to_yup.py` is likewise parked. Pick both up when the repo comes back into scope. As of 2026-10-11 `1d725f0` is not in `src/bluerobotics_models`; only `origin/bsb/blueboat_gltf_workflow` exists.
- [x] #2 closed 2026-10-10 after [Brian's comment](https://github.com/HonuRobotics/gltf-robotics/issues/2#issuecomment-6098473150) linking the coordinate orientation demo; Ryan agreed.

No BlueBoat walkthrough is re-recorded: it is retired (Plan Step 10), and the pilot on Ryan's models replaces it.

### Step 2. Open the GitHub issues

Posted 2026-10-09. Each issue opens with the exchange from the Google Doc, quoted as written (or, for 6 to 8, the gap as found); solution and plan are added as comments. Issue numbers in this repository.

| # | Title | Source | Status |
|---|---|---|---|
| [#1](https://github.com/HonuRobotics/gltf-robotics/issues/1) | Metallic texture renders black in Gazebo | doc, email 2026-10-05 | open: the scene needs a skybox or environment map (Ryan); verify and document in the pilot, Plan Step 9 |
| [#2](https://github.com/HonuRobotics/gltf-robotics/issues/2) | Export with the Y-up flag loads on its side in Gazebo | doc | closed 2026-10-10 (Plan Step 1) |
| [#3](https://github.com/HonuRobotics/gltf-robotics/issues/3) | Transmission (glass) material does not show up in Gazebo | doc | open, back burner: looking for an existence proof among community models, else future work |
| [#4](https://github.com/HonuRobotics/gltf-robotics/issues/4) | Material variants: how to use them in Gazebo | doc | closed 2026-10-10: MUST NOT in the profile, `gltf-check` fails on it (31857aa) |
| [#5](https://github.com/HonuRobotics/gltf-robotics/issues/5) | Assembling a model from its parts | doc | open: in the pilot, Plan Step 9 |
| [#6](https://github.com/HonuRobotics/gltf-robotics/issues/6) | Export guide has no section on authoring materials in Blender | docs survey | open: Ryan's PR, Plan Step 3 |
| [#7](https://github.com/HonuRobotics/gltf-robotics/issues/7) | Apply Modifiers export option is still marked unsettled | options reference | decided 2026-10-11, settled by `c5c0f28`; close when Ryan concurs |
| [#8](https://github.com/HonuRobotics/gltf-robotics/issues/8) | Loader behavior page: upgrade four rows from source-read to observed | docs survey | closed 2026-10-10: rendered tag and dated observations added |

The plan tracks these issues; each one's plan lives in its comments. Topics from the survey that were not opened as issues were folded into Plan Steps 1, 4 and 8.

- [x] Drafts written and reviewed (`plans/issues-draft.md`, deleted after posting).
- [x] Issues posted; numbers recorded above.
- [x] A plan comment on each open issue: Issue #1, Issue #3 ([2026-10-12](https://github.com/HonuRobotics/gltf-robotics/issues/3#issuecomment-6115969328)), Issue #5, Issue #6, Issue #7.

### Step 3. Export guide: materials section (Issue #6)

The first draft is in [exporting-from-blender.md](../docs/walkthroughs/exporting-from-blender.md): metalness, texture format (with the four Images values and WebP), and transparency (MASK at 0.5, no `BLEND` on opaque parts). What is missing is the wiring itself, and per Brian's comment on Issue #6 it comes from Ryan's PR: his material `.blend` files plus the guide changes. Revisited in the pilot, Plan Step 9.

- [ ] Ryan's PR: material `.blend` examples and the guide's materials section.
- [ ] Reviewed against this checklist: the Principled BSDF sockets the exporter reads; ORM through Separate Color, Non-Color; occlusion through the `glTF Material Output` node group and the add-on preference `settings_node_ui`; the normal map chain; the alpha nodes that write MASK and Backface Culling for `doubleSided`; what not to use (Transmission, variants, Clearcoat and the rest); metal looks dark in Gazebo without a skybox (Issue #1).

### Step 4. Export settings (Issue #7, Issue #4) — done

Formerly the options reference, now merged into [exporting-from-blender.md](../docs/walkthroughs/exporting-from-blender.md).

- [x] Stale 5.1 pin: gone with the page.
- [x] Images: four values, no PNG option, WebP pass-through, in the guide's texture-format section.
- [x] `export_apply` settled True as the reference configuration's choice, page framed as informative, `required` relabeled as *fixed by the profile*; export guide gains "Turn on Apply Modifiers" (Issue #7).
- [x] Moved to Plan Step 3: the materials section notes the add-on preferences `KHR_materials_variants_ui` (off) and `settings_node_ui` (on), which live in Edit ▸ Preferences ▸ Add-ons and are not saved by `will_save_settings`.
- [x] Open option rows moved to [Parked](#parked).

### Step 5. Profile (Issue #4) — done

[profile.md](../docs/profile.md).

- [x] Axes rows per Plan Step 1 (`d548653`).
- [x] `KHR_materials_variants` prohibited (`31857aa`).
- [x] Typo "observe to be changning".
- Profile changes for Issue #1 (environment map) and Issue #3 (transmission) are tracked in those issues.

### Step 6. Loader behavior addendum (Issue #8) — done

- [x] Rendered observations from Ryan's cube, and the P upgrades (`0dfbb57`). The environment-map finding is tracked in Issue #1.

### Step 7. Workflow

- [ ] [workflow.md](../docs/workflow.md): step "Author" points at the new materials section; step "Verify ▸ Intended?" says metal looks dark in Gazebo by design, judge color and roughness there and metal in the Sample Viewer.

### Step 8. Checker

- [x] `KHR_materials_variants` in `PROHIBITED_EXTENSIONS`, with a test (`31857aa`). `KHR_materials_transmission` is tracked in Issue #3.
- [ ] `tests/test_check.py`: confirm rule 8 FAILs an `image/webp` texture; add the test if not.

### Step 9. Pilot on Ryan's BlueBoat models

Brian to Ryan, 2026-10-11: put the profile, workflow and tools to work on the BlueBoat models, and refine the models and the docs together as we go.

- [ ] Ryan opens a PR to `bluerobotics_models` with new BlueBoat chassis and propeller models.
- [ ] Brian reviews. `bluerobotics_models` and the gltf-robotics docs (profile, workflow, export guide, tools) are revised together; each doc change is recorded here with its reason.
- [ ] The chassis visual carries `<pose>0 0 0 1.5708 0 1.5708</pose>`, in `model.sdf` or its generator, and `scripts/gltf_to_yup.py` is retired.
- [ ] BlueROV2 chassis and propellers.
- [ ] Holybro UAV models ([holybro_models](https://github.com/HonuRobotics/holybro_models)).
- [ ] If time and budget allow: the Blue Robotics accessories.

### Step 10. Retire the BlueBoat walkthrough

- [x] Deleted `docs/walkthroughs/workflow_blueboat.md` with the files only it used (`blueboat_chassis.sdf`, `blueboat_chassis.urdf`, four `images/blueboat_*.png`) and its walkthroughs index entry (2026-10-11). It recorded the old chassis run with the old roll; the pilot may produce a new walkthrough later.
- [x] Coordinate orientation demo updated (`ca1b5ad`).

## Tests that close the Open items

Recorded in the issue and in the doc that owns the item.

| Issue | Test | Result |
|---|---|---|
| Issue #1, Issue #3 | Tracked in the issues; their plans are in the comments. | — |
| WebP (Plan Step 8) | Export a material whose source image is WebP under AUTO; `gltf-check` must FAIL, `glb_probe` must report the unsupported-format error. | pending |
| Issue #7 | Confirms the reasons, not the decision; run on Ryan's chassis when the Plan Step 9 PR arrives. Chassis export with a live Mirror and Bevel, plus Smooth by Angle shading and a Subdivision with viewport and render levels differing, on and off; `gltf-summary` triangle count and `gltf-check` both ways, Sample Viewer for shading. Add Smooth by Angle to the docs only if confirmed. | pending |

## Verification

1. Docs build: `~/maritime_ws/tools/maritime-workspace/docs-build gltf-robotics` on the host; no new warnings; anchors `#materials`, `#prohibited-content`, `#transparency` resolve from the export guide.
2. Checker: `python3 -m pytest tests/test_check.py -q` passes with the new cases; `PYTHONPATH=src python3 -m gltf_robotics.check` on `examples/monkey.glb` and the chassis GLB shows no regressions.
3. Coordinates: `grep -rn "1.5708" docs/ examples/` lists one Gazebo pose and the two URDF values from Plan Step 1 only; `grep -rn "Y Up" docs/` finds the reversal only in historical notes.
4. Pilot: inside drydock, `gz sdf -p` parses each piloted `model.sdf`; the visual check in `gz sim` is Brian's.
5. Issues: Issues #2, #4 and #8 closed; Issue #7 closes when Ryan concurs; Issue #6 with Plan Step 3; Issues #1 and #5 in the pilot; Issue #3 on the back burner.

## Parked

Export options carried over from the deleted options reference, to settle or drop before a first release: `export_all_vertex_colors` (what triggers the fake `COLOR_0`), `export_extras` (manifest), `use_active_scene` (exactly one scene), `export_shared_accessors` (`glb_probe`), `export_current_frame`.
