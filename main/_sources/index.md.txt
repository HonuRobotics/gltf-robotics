# glTF for robot simulation

Honu Robotics' glTF asset pipeline for Gazebo and RViz: the rules we author to, the workflow that produces a delivery, the tools that check it, and the measurements the rules rest on.

This is our pipeline, published openly with its evidence. It is not a standard, and not a bid to displace [REP 158](https://github.com/openrobotics/reps/blob/main/_posts/rep-0158%3A2006.md), which it cites wherever that document reaches. There is very little practice to defer to — three of 427 robot platforms in Gazebo Fuel are delivered as glTF — so where the field has no settled answer we have worked one out and said so. Every rule carries its status: decided, under discussion, or open.

## Where to start

- [The Profile](profile/index.md) — what a delivered model must be, rule by rule.
- [How-to guides](how-to/index.md) — authoring and exporting a model that satisfies it.
- [Reference](reference/index.md) — coordinate systems, and what Gazebo and RViz actually read from a `.glb`.
- [Evidence](evidence/index.md) — what other people's assets contain, measured rather than asserted.

## Checking a file

```bash
pip install git+https://github.com/HonuRobotics/gltf-robotics
gltf-check path/to/model.glb
```

It parses the glTF rather than rendering it, so it needs no Gazebo, no GPU and no ROS.

```{toctree}
:hidden:
:maxdepth: 3

The Profile <profile/index>
How-to guides <how-to/index>
Reference <reference/index>
Evidence <evidence/index>
Project <project/index>
```
