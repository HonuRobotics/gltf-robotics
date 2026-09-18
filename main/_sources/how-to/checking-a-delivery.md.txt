# Checking a delivery

Four questions decide whether a delivery is good, they fail independently, and no single tool answers more than one of them. Profile section 12 states them; this page says what to actually run.

| | Question | How |
|---|---|---|
| Valid | Is it legal glTF? | The [Khronos glTF Validator](https://github.khronos.org/glTF-Validator/). Zero errors required. |
| Intended | Does it look like what the modeler meant? | The [Khronos Sample Viewer](https://github.khronos.org/glTF-Sample-Viewer-Release/), by a person. It runs the validator inline, so one drag and drop answers this and the row above together. |
| Compliant | Does it satisfy the profile? | `gltf-check`. |
| Usable | Does it render in Gazebo and load in RViz? | Open it. For what the loader built rather than what it looks like, `probe/glb_probe`. |

Passing in Gazebo is necessary and never sufficient: Gazebo ignores several things a file can get wrong, so a defect can be invisible there and fatal elsewhere. The clearest case is a material carrying a normal map and no base colour, which renders in Gazebo and terminates RViz.

Blender's viewport answers none of these. It shows Blender's materials, not the exported file, and the export is a translation in which metallic factor, image format, alpha mode and tangents can all change.

## Running the checker

```bash
pip install git+https://github.com/HonuRobotics/gltf-robotics
gltf-check path/to/part.visual.glb
```

It parses the file rather than rendering it, so it needs no Gazebo, no GPU and no ROS. Point it at several files at once, add `-v` to see the rules that passed, `--json` for machine-readable output, and `--strict` to treat SHOULD violations as failures.

## Reading the output

Findings come in three kinds, and the difference matters.

`FAIL` is a MUST in the profile. The delivery does not conform. Each one names the section that justifies it, so a disagreement is a disagreement with a specific rule and its stated reason, not with the tool.

`warn` is a SHOULD, or a MUST the tool cannot fully settle. The second kind is worth understanding rather than skimming: reading a file cannot decide everything. A material that leaves `metallicFactor` unset but carries a metallic-roughness texture is the standing example — the texture's blue channel multiplies against the factor, so a black channel would still give a non-metal, and only the decoded texels say which it is. Do not read that warning as "probably fine". A solid white metallic channel is the usual export, and every map measured in this project's own library had B = 255.

`note` is a rule the profile has not decided, or one nothing in the file can answer. Profile section 2.4 is explicit that a delivery cannot fail to conform on a point marked Discuss or Open, so these never fail a run. Scale and forward axis are both here: glTF says metres and nothing in the file confirms it, and no glTF file records a forward axis at all. The protocol for answering those by eye is in [`probe/`](https://github.com/HonuRobotics/gltf-robotics/tree/main/probe).

## What a clean run does not mean

A clean run is one of the four answers above, not the answer. It says the file satisfies the rules that can be decided by reading it. It says nothing about whether the part looks right, whether it is the correct size, which way it faces, or what Gazebo's loader will build from it.
