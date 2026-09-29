# Gazebo and RViz loader behavior

What Gazebo and RViz build from a glTF file, read out of their source code and confirmed with `glb_probe` where marked.

This page is a snapshot taken on 2026-09-04 and has not been re-verified since. It is kept as information we may need to return to, not as a maintained reference. The versions in the first table are the ones the snapshot was read against; [profile section 11](../profile.md) is the current pin, and the loader is under active change, so check a claim against the installed version before relying on it.

Evidence tags used below:

| Tag | Evidence |
|---|---|
| S | Read in the source of the version listed |
| P | Observed by running `glb_probe` against our files inside the drydock container |
| U | Not verified |

> **Open.** Whether to contribute the material table below to Gazebo, on the open documentation issue that asked for it, and whether to file an issue for the `SceneManager` material-override TODO. Both are small, and neither is a rule of the profile.

## The consumers

Read out of the drydock container on 2026-09-04. Nothing in this project pins them: the Gazebo libraries are whatever the `ros-lyrical-gz-*-vendor` packages (the Jetty line) resolve to on Ubuntu 26.04, and assimp is the Ubuntu package. An `apt upgrade` or an image rebuild can move any row, and every S-tagged claim below is tied to these numbers.

**Is any of this stable?** No, and the Gazebo project's written record is unambiguous about it. glTF loading arrived in Gazebo Garden in 2022 and has been under continuous correction since. The metallic-roughness maps were being written out rotated ninety degrees. Every PBR texture was treated as color data, so meshes rendered visibly too dark. Embedded JPEG textures failed to load at all, with an error message about texture settings that named nothing relevant. The root node transform was dropped, then restored for glTF only. Occlusion was disabled because the renderer could not use it, then re-enabled from a different channel. Nine changes to the loader alone merged between July and September 2026, and the rotation and default-material behavior changed again between the version installed here and the next patch release, which is the table below. A recollection that an older Gazebo handled GLB very differently is not a false memory. It is what this history predicts.

**How much resolution does the tracking need?** Patch level. The change that moved under us during this audit was 7.3.0 to 7.3.1, so tracking at the minor version would not have caught it, and a pin that names anything coarser than the patch would not be worth writing. The same applies to assimp, which is the component actually doing the parsing and is versioned independently of everything else here. Profile section 11 pins the stack at patch level for this reason.

| Component | Version | Role |
|---|---|---|
| gz-sim | 10.5.0 | Chooses whether the SDF material or the mesh's own materials are used |
| gz-rendering | 10.0.2 | Builds the Ogre-Next mesh and material from what gz-common loaded |
| gz-common | 7.3.0 | The loader: `AssimpLoader.cc` (external library, version not pinned, so could introduce instability), `Image.cc` (stb_image), `Material.cc`, `Pbr.cc`, `SubMesh.cc` |
| Ogre-Next | 2.3.3 | The renderer: HLMS PBS datablocks, tangent generation at mesh import |
| assimp | 6.0.4 (Ubuntu, linked against Draco) | Parses glTF for both Gazebo and RViz |
| rviz_rendering | 15.2.5 (Ogre 1.9) | RViz mesh loader: `mesh_loader_helpers/assimp_loader.cpp` |
| Blender glTF I/O | 5.1.20 | The exporter that wrote every delivered file |

Sources read: branches `gz-common7`, `gz-rendering10`, `gz-sim10`, assimp tag `v6.0.4`, ogre-next `v2-3` and rviz `rolling`. Nothing below is from memory of older versions. gz-common 7 decodes images with stb_image, not FreeImage, which changes what "supported image format" means compared with older Gazebo.

One caveat on that. The gz-common source read here is the `gz-common7` branch tip, which is ahead of the installed 7.3.0: releases 7.3.1 (2026-08-18) and 7.4.0 (2026-08-24) exist upstream, plus merges not yet released. Two of those changes are in `AssimpLoader.cc` and are compared against the 7.3.0 tag here:

| Behavior | 7.3.0, the installed version | 7.3.1 and later, the branch read | Effect on us |
|---|---|---|---|
| glTF root node rotation | `useIdentityRotation = (extension != "glb" && extension != "glTF")`. The extension is lowercased before the comparison, so `"glTF"` never matches and a `.gltf` file loses its root rotation. `.glb` matches and keeps it. | The literal is corrected to `"gltf"`, so both keep it (gz-common PR 858) | None. We deliver `.glb` only, which took the same path before and after. It is a small argument for requiring GLB over `.gltf` on this version. |
| assimp's own default material | No filter exists. Every assimp material becomes a gz `Material`. | `IsDefaultMaterial` skips a material named `DefaultMaterial` carrying exactly two properties (gz-common PR 858) | None. A glTF primitive without a material gets a fully populated synthesized material, which fails that two-property test, so it survives on both. Probe-confirmed on 7.3.0 (the Gazebo path below, step 6). |
Gazebo has not implemented the whole of glTF, it is openly still working on the parts it does implement, and the project publishes almost nothing saying which parts those are. Expecting it to agree with the specification was never a safe assumption, and the table above is the compact demonstration: one file, one specification, two adjacent patch releases, different behavior. A file is correct because it validates and matches its intent. Gazebo tells us what will ship today, on this version, which is a different and more perishable question.

Where the branch and the installed version could differ, a P-tagged observation wins over an S-tagged one, because the probe links against the installed library and the source is the branch. Every S claim on this page was checked for such a gap; these two are the only ones found, and neither changes a conclusion.

## The Gazebo path, step by step

1. The gz-sim server never loads a visual mesh. Visuals are loaded by whichever process renders: the GUI, or a rendering sensor. Collision meshes are loaded by the physics side through the same gz-common loader. [S]
2. `MeshManager` dispatches on the lowercased extension: `stl` to the STL loader, `dae` to the Collada loader, `obj` to the OBJ loader, and `gltf`, `glb`, `fbx` to `AssimpLoader`. The two `.dae` files still in the tree (`ping360`, `bluerov2_heavy_chassis`) therefore go through a different loader with different material semantics; they are outside the profile until converted. [S]
3. `AssimpLoader::Load` imports with `JoinIdenticalVertices`, `RemoveRedundantMaterials`, `SortByPType`, `FlipUVs`, `PopulateArmatureData`, `Triangulate` and `GenNormals`. Not requested: `CalcTangentSpace` (tangents are never computed here), `FindDegenerates` (degenerate triangles survive), `GenUVCoords`. Assimp assertion failures and exceptions are caught and reported as a load failure, not a crash. [S]
4. Root transform: for `glb` the root node transform is kept as exported; for other formats its rotation is dropped, and on the installed 7.3.0 that wrongly includes `.gltf` (see the table above). Every node's translation, rotation, scale or matrix is multiplied down the tree and baked into the vertices. Node transforms are therefore honored, not ignored. [S, P: the T200 files carry a 2.8 mm translation node and the probe's bounding box shifts by exactly that.]
5. Each assimp mesh, which is one glTF primitive, becomes one gz `SubMesh` named after the glTF node that carries it, not after the glTF mesh. Seven primitives on one node become seven submeshes with the same name. [S, P: `bluerov2_chassis` yields seven submeshes all named `Frame.001`.] Vertices, normals (authored ones kept; generated only when absent), every UV set, and 32-bit indices are copied. Tangents and vertex colors are not stored: `SubMesh` has no tangent channel and the factory has a `TODO: diffuse colors`. [S]
6. Materials: `CreateMaterial` builds a gz `Material` plus `Pbr` for every assimp material (on 7.3.1 and later, every one that is not assimp's own two-property default). The table in the next section lists what it reads. A glTF primitive with no material gets assimp's synthesized glTF default (white, metallic 1, roughness 1, opaque), which is fully populated and so survives that filter on either version; Gazebo renders it as dull white metal. [S, P: `material[6]` on the chassis.]
7. gz-rendering's `Ogre2MeshFactory` builds an Ogre v1 mesh (positions, normals, all UV sets as float2, a dummy UV set if there is none, 32-bit indices) and then calls `importV1(v1Mesh, halfPos=false, halfTexCoords=true, qTangents=true)`. Ogre-Next's `importV1` with `qTangents=true` generates tangents from UV set 0 whenever the mesh lacks them, which for us is always. UVs are stored as 16-bit half floats. [S]
8. `BaseMaterial::CopyFrom` copies, in order: ambient, diffuse (RGBA), specular, emissive, shininess, transparency, alpha-from-texture (enabled, threshold, two-sided), render order, base color texture, then the PBR set: normal, roughness and metalness maps, roughness and metalness factors, environment map, emissive map, light map with its UV set. Ogre-Next combines factor and map for metalness and roughness; the factor is a multiplier on the map as in glTF. [S for the copy order; U for the exact shader combination, which is documented behavior of Ogre-Next's PBS but not re-read in shader source for this audit.]
9. Textures are uploaded from memory as RGBA8; base color and emissive as sRGB, normal, roughness and metalness as linear (Ogre-Next's `suggestUsingSRGB`). Normal maps are reduced to a two-channel signed format, so only R and G are used and the blue channel is reconstructed. Mipmaps are generated for the base color and normal maps only; roughness and metalness maps get none. Sampler wrap is always repeat; the glTF sampler is not read. 16-bit PNGs decode but are converted to 8-bit on upload. [S]
10. Transparency: Ogre2's `UpdateTransparency` computes `opacity = (1 - transparency) * diffuse.alpha`; anything below 1.0 moves the material to the transparent render queue. `SetAlphaFromTexture` (MASK) switches on alpha test with the cutoff, a transparent-alpha blend block, and two-sided lighting, which in Ogre-Next also disables back-face culling. Nothing else touches the cull mode, whose default is `CULL_CLOCKWISE`: back faces of OPAQUE and BLEND materials are culled regardless of `doubleSided`. [S, P: `twoSided 0` on every delivered material although all are exported `doubleSided: true`.]
11. gz-sim `SceneManager`: if the SDF `<visual>` carries a `<material>`, that one material is loaded and set on the whole geometry, replacing every embedded material. If it does not, the submesh materials from the file are used, with the visual's `<transparency>` multiplied in. The generated part SDF never emits `<material>`, so embedded materials are what renders. This also means an SDF-side material can only ever be a single material per visual: per-primitive materials are lost the moment one is declared. [S]

## What the loader reads from a glTF material

| glTF field | assimp property | gz-common result | Renders as |
|---|---|---|---|
| `baseColorFactor` RGB | `COLOR_DIFFUSE` | `Diffuse` | Multiplies the base color texture (alpha, see next row) |
| `baseColorFactor` alpha | `COLOR_DIFFUSE` alpha and `OPACITY` | `Diffuse.A = a` and `Transparency = 1 - a` | Opacity `a * a` in Ogre2, on every alpha mode, because both terms carry it [S; visual confirmation pending, U] |
| `baseColorTexture` | `aiTextureType_DIFFUSE` | base color image (UV set 0 assumed) | sRGB albedo with mipmaps |
| `alphaMode: MASK`, `alphaCutoff`, `doubleSided` | `GLTF_ALPHAMODE`, `GLTF_ALPHACUTOFF`, `TWOSIDED` | `SetAlphaFromTexture(true, cutoff, twoSided)` | Alpha test at cutoff, no back-face culling. Only read when a base color texture exists |
| `alphaMode: BLEND` | `GLTF_ALPHAMODE` | nothing (`BLEND not supported yet` in source) | Opaque, texture alpha ignored |
| `doubleSided` on OPAQUE or BLEND | `TWOSIDED` | not read | Back faces culled |
| `metallicFactor`, `roughnessFactor` | `METALLIC_FACTOR`, `ROUGHNESS_FACTOR` | `Pbr::Metalness`, `Pbr::Roughness`; metalness also becomes the Phong specular color | Multipliers on the maps |
| `metallicRoughnessTexture` | `GLTF_PBRMETALLICROUGHNESS_METALLICROUGHNESS_TEXTURE` | split into a metalness map (B) and a roughness map (G), 8-bit single channel | Linear, no mipmaps |
| `occlusionTexture` on UV set 0 | `aiTextureType_LIGHTMAP`, uv index 0 | R channel extracted into a light map on set 0 | Ambient occlusion |
| `occlusionTexture` on UV set 1 or higher | `aiTextureType_LIGHTMAP`, uv index n | whole image as light map on set n | Baked lightmap on its own UVs |
| `normalTexture` | `aiTextureType_NORMALS` | normal map, tangent space | R and G only; `scale` ignored |
| `emissiveFactor`, `emissiveTexture` | `COLOR_EMISSIVE`, `aiTextureType_EMISSIVE` | `Emissive`, emissive map | sRGB emissive, 0 to 1 |
| `KHR_materials_emissive_strength` | `EMISSIVE_INTENSITY` | not read | No HDR emissive |
| `KHR_materials_transmission` | `TRANSMISSION_FACTOR` | `Transparency = factor` | Transparent, so not ignored |
| `KHR_texture_transform` | `UVTRANSFORM` | not read | Textures render untransformed, i.e. misplaced |
| `KHR_materials_pbrSpecularGlossiness` | diffuse and specular colors, `aiTextureType_SPECULAR` | diffuse color, specular map name only | No roughness or metalness maps; not a working import |
| `KHR_materials_specular` | `COLOR_SPECULAR`, `SPECULAR_FACTOR`, specular textures | specular color and a specular map name | Effectively ignored under the metal workflow |
| `KHR_materials_clearcoat`, `sheen`, `ior`, `volume`, `anisotropy`, `unlit` | read by assimp | not read | Ignored |
| `KHR_draco_mesh_compression` | decoded by assimp (Ubuntu build links Draco) | plain geometry | Works in both consumers |
| `KHR_texture_basisu`, `EXT_texture_webp` | parsed by assimp | `Unable to load embedded texture. Unsupported compressed image format` | Untextured, with an error on the console |
| Embedded PNG or JPEG | `aiTexture` with format hint | decoded with stb_image | Works. Only these two hints are accepted |
| `samplers` | read by assimp | not read | Always repeat, linear |
| `COLOR_0` vertex colors | read by assimp | not copied | Ignored |
| `TANGENT` | read by assimp | not copied | Ogre-Next regenerates from UV0 |
| `animations`, `skins` | read | skeleton and animation built | Bounding box forced to a unit cube when an animation exists, so a stray animation breaks culling |
| `cameras`, `KHR_lights_punctual` | read by assimp | not read | Ignored |

## The RViz path

`rviz_rendering::AssimpLoader` imports with `SortByPType`, `GenNormals`, `Triangulate`, `GenUVCoords`, `FlipUVs`, then for `.gltf`, `.glb` and `.vrm` multiplies the root node by a +90 degree rotation about X, taking glTF Y-up to ROS Z-up. Materials are Ogre 1.9 fixed-function: diffuse, ambient, specular, emissive colors, shininess, opacity from `baseColorFactor` alpha, and exactly one texture, looked up as `aiTextureType_DIFFUSE`. Metalness, roughness, normal, occlusion and emissive maps do not exist in RViz. [S]

The lookup loop is the known trap: it iterates every material property and, on any `$tex.file` entry, asks for the diffuse texture. A material whose only texture is a normal map has such an entry, the diffuse lookup fails, the resulting path resolves to the mesh directory, and the resource retriever's exception terminates RViz. That is why `gltf_bake_basecolor.py` and the guard in `test/test_parts.py` exist in `bluerobotics_models` (commit `01b05f9`), and why profile section 7 requires that a material with any texture also has a base color texture. [S, and the repo's own regression test]
