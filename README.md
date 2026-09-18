# glTF for robot simulation

Honu Robotics' glTF asset pipeline for Gazebo and RViz: the rules we author to, the workflow that produces a delivery, the tools that check it, and the measurements the rules rest on.

Documentation: <https://honurobotics.github.io/gltf-robotics/>

## What this is, and what it is not

This is our pipeline, published openly with its evidence. It is not a standard, and it is not a bid to displace [REP 158](https://github.com/openrobotics/reps/blob/main/_posts/rep-0158%3A2006.md), which it cites wherever that document reaches.

The distinction matters because there is very little practice to defer to. A survey of the whole Gazebo Fuel library found three robot platforms delivered as glTF out of 427, and a survey of public repositories found a cohort small enough to name. Where the field has no settled answer we have had to work one out, and saying so plainly is more useful than implying a consensus that does not exist. Every rule here is marked with its status — decided, under discussion, or open — so a reader can tell our conclusions from our questions.

What we do have is measurement. Forty-seven assets from Khronos, the Gazebo team, Fuel and other robotics projects, read criterion by criterion; loader behavior taken from the gz-common and RViz sources rather than from documentation; and a pipeline that actually runs. That is the part worth publishing, and it is the part designed to stay true: the assessment is re-run, not rewritten, so an upstream asset that changes is noticed rather than quietly making a claim here false.

If you author glTF for Gazebo or RViz, the profile and the how-to guides should save you the fortnight we spent finding out what those two renderers really read. If you disagree with a rule, the evidence it rests on is in the same repository and you can check it.

## Layout

| | |
|---|---|
| `docs/profile/` | the glTF Robotics Profile — what a delivered model must be, rule by rule |
| `docs/how-to/` | the authoring workflow: export settings, delivery, review |
| `docs/reference/` | coordinate systems, loader behavior, glTF background |
| `docs/evidence/` | what the corpus says, and the generated assessment behind it |
| `assess/` | the corpus: criteria, the asset registry, the hand-written findings |
| `probe/` | tools that answer what reading a file cannot — `glb_probe` loads one through Gazebo's own loader |
| `exemplar/` | a worked model that satisfies the profile, and fixtures that deliberately do not |
| `figures/` | the ISO 9787 coordinate-frame illustrations, generated from Python scene scripts |

## Install

```bash
pip install -e .
```

Two commands:

```bash
gltf-check path/to/model.glb     # does this file satisfy the profile?
gltf-assess                      # re-measure the corpus, rewrite the assessment
```

`gltf-check` is the one worth pointing at your own files. It needs nothing but Python — it parses the glTF rather than rendering it.

## License

Apache-2.0. See [LICENSE](LICENSE) and [NOTICE](NOTICE).
