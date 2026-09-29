# Checking a delivery

Four questions decide whether a delivery is good, they fail independently, and no single tool answers more than one of them. The profile's [Conformance testing](../profile.md#conformance-testing) section states them; this page says what to actually run.

| | Question | How |
|---|---|---|
| Valid | Is it legal glTF? | The [Khronos glTF Validator](https://github.khronos.org/glTF-Validator/). Zero errors required. |
| Intended | Does it look like what the modeler meant? | The [Khronos Sample Viewer](https://github.khronos.org/glTF-Sample-Viewer-Release/), by a person. It runs the validator inline, so one drag and drop answers this and the row above together. **It cannot answer orientation** — see below. |
| Compliant | Does it satisfy the profile? | `gltf-check`. |
| Usable | Does it render in Gazebo and load in RViz? | Open it. For what the loader built rather than what it looks like, `probe/glb_probe`. |

Passing in Gazebo is necessary and never sufficient: Gazebo ignores several things a file can get wrong, so a defect can be invisible there and fatal elsewhere. The clearest case is a material carrying a normal map and no base colour, which renders in Gazebo and terminates RViz.

Blender's viewport answers none of these. It shows Blender's materials, not the exported file, and the export is a translation in which metallic factor, image format, alpha mode and tangents can all change.

The reference viewer cannot answer orientation either, and this is a deliberate cost rather than a gap. The profile's [Axes](../profile.md#axes) section delivers files +X forward and +Z up, following ISO 9787 and REP 103, where glTF's own convention is Y-up. Every third-party viewer assumes glTF's, so every conforming part appears rotated ninety degrees in the Sample Viewer and in any browser viewer. Read those views for materials, textures, transparency and validity, and ignore the pose. Orientation is settled by the manifest declaration that `gltf-check` verifies, and by opening the part in Gazebo.

## Running the checker

```bash
pip install git+https://github.com/HonuRobotics/gltf-robotics
gltf-check path/to/part.visual.glb
```

It parses the file rather than rendering it, so it needs no Gazebo, no GPU and no ROS. Point it at several files at once. The output is a checklist in profile order — one block per section stating what was tested, then the verdict — and it lists the checks that passed as well, since a report of problems alone cannot tell you whether the thing you cared about was examined. Add `-q` to drop the sections with nothing to report, `-v` to see the explanatory detail on passing checks too, `--json` for machine-readable output, and `--strict` to treat SHOULD violations as failures.

`gltf-summary` answers a different question: not whether a file conforms, but what is in it. Structure, geometry, materials, and where the origin sits inside the bounding box — the last of which no viewer shows you. It reaches no verdicts, so it is the tool for an unfamiliar file or for confirming that a correct one really is correct. `--explain` appends a glossary of the output.

## Reading the output

Every run opens with a legend, then one block per profile section: the section name, what the rule tests, a mark, a one-line finding, and for anything but a pass the reason behind it. The marks are five words, used identically beside each finding and in the closing tally.

`PASS` is a rule satisfied. Listed rather than hidden, because the question "was that examined?" needs an answer as much as "did it fail?".

`FAIL` is a MUST in the profile. The delivery is not compliant. Each one names the section that justifies it, so a disagreement is a disagreement with a specific rule and its stated reason, not with the tool.

`WARN` is a SHOULD, or a MUST the tool cannot fully settle. The second kind is worth understanding rather than skimming: reading a file cannot decide everything. A material that leaves `metallicFactor` unset but carries a metallic-roughness texture is the standing example — the texture's blue channel multiplies against the factor, so a black channel would still give a non-metal, and only the decoded texels say which it is. Do not read that warning as "probably fine". A solid white metallic channel is the usual export, and every map measured in this project's own library had B = 255.

`OPEN` is a rule the profile has not decided, or one nothing in the file can answer. The profile's [Open issues](../profile.md#open-issues) section is explicit that a delivery cannot fail to conform on a point marked Open, so these never fail a run: they are something to discuss, not something to fix. Scale and forward axis are both here: glTF says metres and nothing in the file confirms it, and no glTF file records a forward axis at all. The protocol for answering those by eye is in [`probe/`](https://github.com/HonuRobotics/gltf-robotics/tree/main/probe).

`SKIP` is a rule with nothing to examine — the texture rules on a file with no images, the datum rule on a file that declares no part role.

The last two lines are the tally and the verdict. The verdict says *compliant* rather than *conforms* on purpose: compliant is the profile's [Conformance testing](../profile.md#conformance-testing) section's third question, every MUST satisfied, and it is the only one of the four this tool answers. A file with only `WARN` findings is therefore compliant, with things to review before delivering; `--strict` counts them as failures instead. The exit code and the `--json` output follow the same rule as the text, so a script and a reader never disagree about a file.

## What a clean run does not mean

A clean run is one of the four answers above, not the answer. It says the file satisfies the rules that can be decided by reading it. It says nothing about whether the part looks right, whether it is the correct size, which way it faces, or what Gazebo's loader will build from it.
