# Honu Robotics' glTF asset framework

Honu Robotics' glTF asset framework for Gazebo and RViz. This is a beta release: two documents are ready for review, and the rest of the site is planned work still in development.

## Ready for beta review

- [Honu glTF Asset Profile](profile.md). Normative rules for 3D visual robotic assets, narrowing, extending and clarifying glTF 2.0 for robotics and aligned to ISO and ROS REP conventions.
- [Honu glTF Asset Workflow](workflow.md). The step-by-step process of asset commissioning, authoring and integration, and who does what.

## In development, not ready for review

These items are work in progress

Supporting documentation:

- [Walkthroughs](walkthroughs/index.md). Complete step-by-step examples and how-tos: one mesh from Blender to Gazebo and RViz, exporting from Blender, and checking a delivery.
- [Assessments](assessments/index.md). Measurements of what glTF assets published by other projects contain. They show what is in the field and are not a basis for the profile's rules. Audits of our own deliveries are planned.
- [Reference](reference/index.md). Coordinate systems, Blender's glTF export options, PBR materials and notes on glTF itself.  These are notes and artifacts from working through issues and conventions.  

Tools and utilities, with their source code in the repository:

- [Command-line tools](https://github.com/HonuRobotics/gltf-robotics/tree/main/src/gltf_robotics). `gltf-check` tests a file against the profile's rules, `gltf-summary` describes what a file contains, and `gltf-assess` measures a list of assets published elsewhere.
- [Probes](https://github.com/HonuRobotics/gltf-robotics/tree/main/probe). `glb_probe` loads a file through Gazebo's own loader and reports what was built, and a marker generator writes test assets for coordinate-system questions.
- [Figures](https://github.com/HonuRobotics/gltf-robotics/tree/main/figures). The drawing kit and scene scripts that generate the coordinate-system illustrations.

Models:

- [Examples](https://github.com/HonuRobotics/gltf-robotics/tree/main/examples). The files behind the walkthroughs.
- [Exemplar](https://github.com/HonuRobotics/gltf-robotics/tree/main/exemplar). Planned as a reference model that satisfies the profile. At present it holds only a minimal glTF file used to explain the file structure.
- [Demo](https://github.com/HonuRobotics/gltf-robotics/tree/main/demo). A Blender script that builds an axis-marker scene in the robotics coordinate convention.

```{toctree}
:hidden:
:maxdepth: 3

Profile <profile>
Workflow <workflow>
Walkthroughs <walkthroughs/index>
Assessments <assessments/index>
Reference <reference/index>
```
