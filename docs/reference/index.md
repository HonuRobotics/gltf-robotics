# Reference

Background the profile's rules rest on, and the material a reader needs to argue with them.

- [Glossary](glossary.md) — the vocabulary of the whole project, in one place.
- [Coordinate systems](coordinate-systems.md) — what ISO 9787, the ROS REPs and glTF each say about frames, where they disagree, and which one a delivered model is expressed in. Claims are marked firm, practice, open or corrected.
- [Gazebo and RViz loader behavior](loader-behavior.md) — what Gazebo and RViz build from a `.glb`, read out of the `gz-common` and `rviz_rendering` sources. A snapshot from 2026-09-04, not re-verified since.
- [Blender glTF export options](blender-export-options.md) — all 110 properties of the export operator with their defaults, read out by introspection, and which ones the profile settles.
- [PBR and glTF](pbr-and-gltf.md) — the metallic-roughness material model, and the difference between a property and a channel.
- [glTF background notes](gltf-background-notes.md) — reading notes and a reference collection, including the measured case for PNG over JPEG in the linear texture slots.

```{toctree}
:maxdepth: 2

glossary
coordinate-systems
loader-behavior
blender-export-options
pbr-and-gltf
gltf-background-notes
```
