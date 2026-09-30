# Walkthroughs

Complete step-by-step examples and how-tos. Each one is run end to end, with the real output of each tool quoted, including where the result is surprising.

- [Minimum viable workflow](blender_mesh_coordinate_ex.md). One mesh from Blender to Gazebo and RViz, the simplest thing that exercises the whole pipeline, used to test the conventions and verify the tools against a file we made ourselves.
- [Exporting from Blender](exporting-from-blender.md). The export defaults that produce most of the defects we see, and what to do instead.
- [Checking a delivery](checking-a-delivery.md). The four conformance questions, what answers each, and how to read `gltf-check` output.
- [BlueBoat walkthrough](workflow_blueboat.md). The BlueBoat chassis taken through the workflow: commission, manifest, and the four conformance checks, with each tool's real output.

```{toctree}
:maxdepth: 2

blender_mesh_coordinate_ex
exporting-from-blender
checking-a-delivery
workflow_blueboat
```
