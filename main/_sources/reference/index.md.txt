# Reference

Background the profile's rules rest on, and the material a reader needs to argue with them.

- [Coordinate systems](coordinate-systems.md) — what ISO 9787, the ROS REPs and glTF each say about frames, where they disagree, and which one a delivered model is expressed in. Claims are marked firm, practice, open or corrected.
- [Pipeline review](pipeline-review.md) — what Gazebo and RViz actually build from a `.glb`, read out of the `gz-common` and `rviz_rendering` sources rather than from documentation. The profile reasons against this.
- [PBR and glTF](pbr-and-gltf.md) — the metallic-roughness material model, and the difference between a property and a channel.
- [glTF background notes](gltf-background-notes.md) — reading notes and a reference collection, including the measured case for PNG over JPEG in the linear texture slots.

```{toctree}
:maxdepth: 2

coordinate-systems
pipeline-review
pbr-and-gltf
gltf-background-notes
```
