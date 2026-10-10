# Blender export and materials: closing the open issues

A living plan. Steps are worked in order, checked off as they close, and rewritten as the work demands. Each step records its outcome (issue number, commit, test result, or decision and why) below its checkbox. Started 2026-10-07.

## Context

Ryan Lee (the modeller, GitHub `phfatmonkey`) ran the new glTF workflow on a test cube and then the BlueBoat chassis during the week of 2026-10-05. His findings are in the "Modeling workflow beta" email thread and, since 2026-10-06, in the shared Google Doc `3DVisualAssetWorkflowDiscussion` in the Honu Drive. He also sent the [mundobytes article](https://mundobytes.com/en/Blender-prepares-and-exports-models-to-GLTF-with-PBR-materials./) on Blender glTF PBR export (2026-10-02). A team call is being arranged for Friday 2026-10-09.

Every one of Ryan's observations has an answer in source read on 2026-10-07, and most point at gaps or contradictions in the docs. A survey of `main` found that no page explains how to author materials in Blender at all, and that the coordinate docs disagree with each other in four places.

Decisions taken so far:

- Each topic becomes a GitHub issue in this repository, so every question has a thread that records the finding, the decision and why. Ryan is not a collaborator, so he can comment but cannot be assigned. The Google Doc gets one closing note pointing at the issues.
- The coordinate rule (URDF `rpy` per distro and the Blender `+Y Up` statement) is Brian's to state definitively; propagation waits on that statement (step 1).
- Metalness policy is decided after a Gazebo test; the profile keeps its Open item with the finding attached.
- `KHR_materials_variants` is prohibited; one GLB per color variant.

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
- The docs disagree on the URDF rotation: `profile.md:184` says Lyrical `rpy="-1.5708 0 1.5708"` and `:185` says Jazzy/Kilted `TBD`; `coordinate-systems.md:566-579` ([Firm]), `exporting-from-blender.md:11`, `workflow.md:93` and `blender-export-options.md:122` say Lyrical `rpy="0 0 1.5708"` and Jazzy/Kilted `rpy="1.5708 0 1.5708"`. `coordinate_orientation_demo.md:288` still says the decision is `+Y Up` off and uses `rpy="-1.5708 0 0"` at L220, L227, L284; `workflow_blueboat.md:257` uses the old roll; `blender-export-options.md:66` still calls the toolchain pin 5.1 and Open. Step 1 resolves which statement is right before any of these are touched.

## Steps, in order

### Step 0. Make this plan a living document

- [x] File created at `plans/2026-10-blender-materials.md` and committed on `main`, 2026-10-07.

Each later step ends with this file updated and committed: the box checked, the issue number, commit, test result or decision and its reason recorded under it.

### Step 1. The coordinate statement

The rule, stated once: build in Blender's convention (front −Y, up +Z); export with `+Y Up` on, so the file is in glTF's convention (+Y up, +Z forward); the consumer rotates it onto the robotics axes with `<pose>0 0 0 1.5708 0 1.5708</pose>` on the Gazebo visual and `rpy="0 0 1.5708"` on the URDF visual for RViz on Lyrical and later, which rolls glTF files +90° about X itself. Earlier ROS distributions do not rotate and are not supported.

Evidence (2026-10-09): [S] gz-common `gz-common7_7.3.0` `AssimpLoader.cc` L849-853, L955-976 applies no up-axis conversion; [S] rviz `lyrical` `assimp_loader.cpp` L215-222 post-multiplies Rx(+90°) onto the root; [P] `glb_probe` in drydock returns the raw buffer bounds for `monkey.glb` (Y-up) and the Z-up export alike; [M] with R = Rz·Ry·Rx only the stated values give face +X, up +Z; on screen in `gz sim` 10.5.0 and `rviz_rendering` 15.2.5 by Brian, recorded in the [Coordinate orientation demo](../docs/walkthroughs/coordinate_orientation_demo.md). The earlier `rpy="-1.5708 0 1.5708"` in the profile was the right value for a Z-up file and came from the old `monkey.urdf`.

- [x] Statement recorded (above) and shown end to end in the demo, commit `ca1b5ad`.
- [x] Propagated: profile Axes table and Jazzy/Kilted note, stray "; " at L95, `step-4-verify-integrator` anchor; coordinate-systems [Open] on per-distro delivery closed as [Practice]; export guide; workflow; options reference (5.2.2 / 5.2.40 pin); BlueBoat walkthrough banner and a note under its recorded URDF; `examples/monkeys.sdf`. Commit on `main` after `ca1b5ad`.
- [~] `bluerobotics_models` is deferred (Brian, 2026-10-09). The chassis `model.sdf` pose and `part_visual` values are committed locally on `bsb/blueboat_gltf_workflow` as `1d725f0`, not pushed; the chassis `.glb` there is still the Z-up, X-forward export. The migration of `main` off `gltf_to_yup.py` is likewise parked. Pick both up when the repo comes back into scope.
- [ ] Comment on #2 (draft below), after Brian's say-so.

Draft comment for #2:

> Resolved on the docs side. The flag is right: export with `+Y Up` on. What was missing is the consumer rotation in the SDF. For a file in glTF's convention Gazebo applies nothing on load, so the visual needs `<pose>0 0 0 1.5708 0 1.5708</pose>` (roll 90° then yaw 90°); RViz on Lyrical rolls the mesh +90° about X itself, so the URDF visual needs only `rpy="0 0 1.5708"`. Read from gz-common 7.3.0 and rviz lyrical source, checked with the probe and the math, and seen on screen with the monkey on 2026-10-09; the [Coordinate orientation demo](https://github.com/HonuRobotics/gltf-robotics/blob/main/docs/walkthroughs/coordinate_orientation_demo.md) shows it end to end. The chassis `model.sdf` and `part_visual` on `bsb/blueboat_gltf_workflow` now carry these values (commit to follow). What is left is the file: the chassis `.glb` on that branch is still the Z-up export, so once your `+Y Up` export is pushed there it should load upright. Could you push it and check?

Not re-recorded this round: `docs/walkthroughs/blueboat_chassis.urdf` and the URDF snippet in the BlueBoat walkthrough keep the old `rpy="-1.5708 0 0"` as a record of the earlier convention, with a note.

### Step 2. Open the GitHub issues

Posted 2026-10-09. Each issue opens with the exchange from the Google Doc, quoted as written (or, for 6 to 8, the gap as found); solution and plan are added as comments. Issue numbers in this repository.

| # | Title | Source | Status |
|---|---|---|---|
| [#1](https://github.com/HonuRobotics/gltf-robotics/issues/1) | Metallic texture renders black in Gazebo | doc, email 2026-10-05 | open |
| [#2](https://github.com/HonuRobotics/gltf-robotics/issues/2) | Export with the Y-up flag loads on its side in Gazebo | doc | open |
| [#3](https://github.com/HonuRobotics/gltf-robotics/issues/3) | Transmission (glass) material does not show up in Gazebo | doc | open |
| [#4](https://github.com/HonuRobotics/gltf-robotics/issues/4) | Material variants: how to use them in Gazebo | doc | closed 2026-10-10: MUST NOT in the profile, `gltf-check` fails on it (31857aa) |
| [#5](https://github.com/HonuRobotics/gltf-robotics/issues/5) | Assembling a model from its parts | doc | open |
| [#6](https://github.com/HonuRobotics/gltf-robotics/issues/6) | Export guide has no section on authoring materials in Blender | docs survey | open |
| [#7](https://github.com/HonuRobotics/gltf-robotics/issues/7) | Apply Modifiers export option is still marked unsettled | options reference | open |
| [#8](https://github.com/HonuRobotics/gltf-robotics/issues/8) | Loader behavior page: upgrade four rows from source-read to observed | docs survey | open |

Topics from the survey that were not opened as issues and are folded into the steps below instead: the Images option passing WebP through (step 4), the coordinate disagreements (step 1), and the `KHR_materials_variants` prohibition (#4 and step 8).

- [x] Drafts written and reviewed (`plans/issues-draft.md`, deleted after posting).
- [x] Issues posted; numbers recorded above.
- [ ] Closing note for the Google Doc drafted (Brian pastes).
- [ ] Solution and plan posted as a comment on each of #1 to #5, after step 1.

### Step 3. Export guide: materials section (#6, #3)

[exporting-from-blender.md](../docs/walkthroughs/exporting-from-blender.md). Insert after "Name the object, not the mesh" a section "Wire the material the way the exporter reads it", in the page's voice (what the export does, what to do instead), one short paragraph per point:

- One Principled BSDF per material; the exporter reads the named sockets only (Base Color, Metallic, Roughness, Normal, Alpha, Emission).
- Roughness and metalness: one ORM image through Separate Color, or two grayscale images; the exporter packs G and B itself. Image Texture color space Non-Color. A uniform channel stays unlinked and becomes a factor.
- Occlusion: add `glTF Material Output` from the Add menu, ORM red through Separate Color into its Occlusion input; legacy name `glTF Settings`; enable the add-on preference if the entry is missing.
- Normal: Image Texture (Non-Color) → Normal Map (Tangent Space) → Normal; strength 1.0.
- Alpha: cutouts through Math Round (or Greater Than) into Alpha, which writes MASK at 0.5; opaque materials leave Alpha at 1.0 so no BLEND is written by accident; Backface Culling on except for MASK cutouts that must show both sides.
- Do not use Transmission, variants, Clearcoat, Sheen, IOR, Volume, Anisotropy; say which consumer does what with each, with the issue links.
- What it looks like in Gazebo: metal is dark, [Firm] with source, policy [Open] in #1.

Also: "Texture format is decided by the source image" gains the WebP case and the four option values; "Transparency is per material" gains one sentence on uniform translucency pointing at #3.

- [ ] Section written and committed.

### Step 4. Export options reference (#7, #4)

[blender-export-options.md](../docs/reference/blender-export-options.md).

- [ ] L66 stale 5.1 pin → 5.2.2 / 5.2.40.
- [ ] L167-178 Images rows: four values, no PNG option, WebP pass-through.
- [ ] L154-158 and worklist L226-234: `export_apply` stays open, record the shape-key warning and the test (#7).
- [ ] New note "Add-on preferences, not dialog options": `KHR_materials_variants_ui` (must be off) and `settings_node_ui` (must be on) live in Edit ▸ Preferences ▸ Add-ons and are not saved by `will_save_settings`.

### Step 5. Profile (#1, #3, #4)

[profile.md](../docs/profile.md).

- [ ] Axes rows per step 1.
- [ ] Materials: Implementation Note with the environment-map finding under L311-313, and an explicit Open on capping metalness, citing #1. Fold or remove the orphaned paragraph at L335.
- [ ] Transparency Open L373: add the transmission finding as an Implementation Note; the proposal stands; #3 decides the tag.
- [ ] Prohibited content L377-389: add `KHR_materials_variants` and `KHR_materials_transmission` with reasons. Update the Open questions tables L424-443.
- [ ] L393 typo "observe to be changning".

### Step 6. Loader behavior addendum (#1, #8)

- [ ] [loader-behavior.md](../docs/reference/loader-behavior.md): dated addendum (2026-10-07) under the consumers table with the environment-map finding and source lines, assimp has no `KHR_materials_variants`, and the P upgrades from Ryan's cube. Keep the snapshot framing.

### Step 7. Workflow

- [ ] [workflow.md](../docs/workflow.md): step "Author" points at the new materials section; step "Verify ▸ Intended?" says metal looks dark in Gazebo by design, judge color and roughness there and metal in the Sample Viewer.

### Step 8. Checker (#4)

- [ ] `src/gltf_robotics/check/rules.py`: add `KHR_materials_variants` and `KHR_materials_transmission` to `PROHIBITED_EXTENSIONS`.
- [ ] `tests/test_check.py`: two new cases using the fixture in `tests/conftest.py`. Confirm rule 8 already FAILs `image/webp`; add a test if not.

### Step 9. The chassis SDF (#2)

- [ ] `bluerobotics_models` branch `bsb/blueboat_gltf_workflow`: add `<pose>0 0 0 1.5708 0 1.5708</pose>` to the chassis visual in `bluerobotics_parts/models/blueboat_chassis/model.sdf`, or to the generator if `scripts/sdf_to_part.py` or `assembly.py` writes that file, then regenerate. Retire `scripts/gltf_to_yup.py`. Commit and link from #2.

### Step 10. Walkthrough addendum

- [ ] [workflow_blueboat.md](../docs/walkthroughs/workflow_blueboat.md): "Materials test (2026-10-05)" subsection summarising Ryan's cube results with explanations and issue links, and the SDF pose fix as the resolution of the on-its-side report.
- [ ] [coordinate_orientation_demo.md](../docs/walkthroughs/coordinate_orientation_demo.md): step 1 values and a banner if the rest cannot be re-recorded now.

## Tests that close the Open items

Recorded in the issue and in the doc that owns the item.

| Issue | Test | Result |
|---|---|---|
| #1 | Cube with three materials, metalness 0 / 0.5 / 1, roughness 0.3, in `gz sim` with and without `<sky>`; screenshots (GUI). Then read gz-sim `RenderUtil` for any env-map hook reaching `Ogre2Material::SetEnvironmentMap` on mesh materials. Decide cap vs truth; consider a gz-rendering upstream issue. | pending |
| #3 | Monkey at `baseColorFactor` alpha 0.5 tagged OPAQUE and BLEND, transmission 0.5; `glb_probe` for built Transparency, `gz sim` for the look, Sample Viewer for other viewers. | pending |
| WebP (step 4) | Export a material whose source image is WebP under AUTO; `gltf-check` must FAIL, `glb_probe` must report the unsupported-format error. | pending |
| #7 | Chassis export with a live Mirror or Bevel modifier, on and off; `gltf-summary` triangle count and `gltf-check` both ways. | pending |

## Verification

1. Docs build: `~/maritime_ws/tools/maritime-workspace/docs-build gltf-robotics` on the host; no new warnings; anchors `#materials`, `#prohibited-content`, `#transparency` resolve from the export guide.
2. Checker: `python3 -m pytest tests/test_check.py -q` passes with the new cases; `PYTHONPATH=src python3 -m gltf_robotics.check` on `examples/monkey.glb` and the chassis GLB shows no regressions.
3. Coordinates: `grep -rn "1.5708" docs/ examples/` lists one Gazebo pose and the two URDF values from step 1 only; `grep -rn "Y Up" docs/` finds the reversal only in historical notes.
4. SDF fix: inside drydock, `gz sdf -p` on the chassis `model.sdf` parses; the visual check in `gz sim` is Brian's.
5. Issues: `gh issue list` shows #1 to #8 with labels; #2 links the branch commit; #1 to #5 each carry a solution comment.
