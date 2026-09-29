"""The profile's mechanically decidable rules, one function each.

Every rule names the profile section it comes from, so a failure points at the
text that justifies it rather than at an opinion in this file. Sections the
profile marks Open are reported as advisory: the profile says a delivery cannot
fail to conform on an unsettled point, and this must not quietly harden one.
A rule that is normative today but recorded as Open because a more capable
version is plausible later still fails, because it is normative today.

What is deliberately not here: the four conformance questions in profile
the profile's Conformance testing section fail independently, and only "compliant" is decidable by reading the
file. Validity belongs to the Khronos validator, intent to a human at a
reference viewer, and usability to Gazebo and RViz -- for which `probe/` exists.
A clean run here is one of four answers, not the answer.
"""

import dataclasses
import json
import pathlib
import re
import struct

from ..assess.gltf_assess import (
    Resolver,
    Source,
    load_structure,
    mat_mul,
    material_maps,
    node_matrix,
    read_accessor,
    sniff_image,
    transform_bounds,
)

# Rule outcome levels. FAIL and WARN come from the profile's own MUST/SHOULD;
# ADVISORY is used where the profile has not decided, and never fails a run.
FAIL = "fail"
WARN = "warn"
ADVISORY = "advisory"
PASS = "pass"
SKIP = "skip"

LINEAR_SLOTS = ("normal", "metallicRoughness", "occlusion")
NS = "https://honurobotics.github.io/gltf-robotics/ns/profile/1.0/"
AXES = ("+X", "-X", "+Y", "-Y", "+Z", "-Z")
PROHIBITED_EXTENSIONS = {
    "KHR_draco_mesh_compression": "Draco mesh compression",
    "KHR_texture_basisu": "KTX2/Basis textures",
    "KHR_texture_transform": "KHR_texture_transform",
    "KHR_materials_pbrSpecularGlossiness": "the specular-glossiness workflow",
}
IDENTITY = [[1.0, 0, 0, 0], [0, 1.0, 0, 0], [0, 0, 1.0, 0], [0, 0, 0, 1.0]]
# Units a cited dimension may be written in, as meters per unit.
UNITS = {"m": 1.0, "cm": 0.01, "mm": 0.001}
# What a wrong scale usually is: the ratio of the file's extent to the cited figure.
SCALE_SUSPECTS = ((1000.0, "millimeters"), (100.0, "centimeters"), (39.37, "inches"))


@dataclasses.dataclass
class Finding:
    """One rule's verdict on one file."""

    section: str
    level: str
    summary: str
    detail: str = ""

    @property
    def failed(self):
        return self.level == FAIL


class Model:
    """A parsed glTF, with the bytes reachable but not yet read."""

    def __init__(self, path):
        self.path = pathlib.Path(path)
        self.source = Source(str(self.path))
        self.gltf, bin_offset, _bin_length = load_structure(self.source)
        self.resolver = Resolver(self.gltf, self.source, bin_offset, budget=1 << 30)
        self.is_glb = self.path.suffix.lower() == ".glb"

    def get(self, key):
        return self.gltf.get(key, [])

    @property
    def part_name(self):
        """The part name implied by the filename: `<part>.visual.glb` -> `<part>`."""
        name = self.path.name
        for suffix in (".visual.glb", ".visual.gltf", ".glb", ".gltf"):
            if name.endswith(suffix):
                return name[: -len(suffix)]
        return self.path.stem

    def root_nodes(self):
        nodes = self.get("nodes")
        child = {c for n in nodes for c in n.get("children", [])}
        return [i for i in range(len(nodes)) if i not in child]

    def primitives(self):
        """(mesh_index, primitive_index, primitive) for every primitive."""
        for mi, mesh in enumerate(self.get("meshes")):
            for pi, prim in enumerate(mesh.get("primitives", [])):
                yield mi, pi, prim

    def manifest(self):
        """The XMP packet the asset object points at, or None.

        The profile's manifest section puts the manifest in KHR_xmp_json_ld and attaches it to
        the glTF `asset` object. The extension keeps packets in a top-level
        array and references them by index, so this follows that indirection.
        """
        top = self.gltf.get("extensions", {}).get("KHR_xmp_json_ld")
        if not top:
            return None
        packets = top.get("packets") or []
        ref = self.gltf.get("asset", {}).get("extensions", {}).get("KHR_xmp_json_ld")
        if ref is None:
            return None
        i = ref.get("packet")
        if not isinstance(i, int) or not 0 <= i < len(packets):
            return None
        return packets[i]

    def image_bytes(self, index, limit=1 << 16):
        """The head of an embedded image.

        Large enough to reach a JPEG's SOF marker, which carries the dimensions
        and can sit well past the first kilobyte. A PNG's IHDR is in the first
        26 bytes, but sizing for the worst case costs one range read either way.
        """
        image = self.get("images")[index]
        if "bufferView" not in image:
            return None
        return self.resolver.view_bytes(image["bufferView"], limit=limit)

    def extent(self):
        """(lo, hi) of everything the file places, or None.

        From the bounds each POSITION accessor declares, composed through the
        node transforms. glTF requires those bounds, so this reads no geometry.
        """
        nodes, meshes, accessors = self.get("nodes"), self.get("meshes"), self.get("accessors")
        boxes = []
        for index, matrix in world_matrices(self).items():
            mesh_index = nodes[index].get("mesh")
            if mesh_index is None or not 0 <= mesh_index < len(meshes):
                continue
            for prim in meshes[mesh_index].get("primitives", []):
                pos = prim.get("attributes", {}).get("POSITION")
                if pos is None or not 0 <= pos < len(accessors):
                    continue
                lo, hi = accessors[pos].get("min"), accessors[pos].get("max")
                if lo and hi:
                    boxes.append(transform_bounds(matrix, lo, hi))
        return union(boxes)


def world_matrices(model):
    """Node index -> its composed 4x4, walking down from every root."""
    nodes = model.get("nodes")
    out = {}

    def walk(i, parent, seen):
        if i in seen or not 0 <= i < len(nodes):
            return
        matrix = mat_mul(parent, node_matrix(nodes[i]))
        out[i] = matrix
        for child in nodes[i].get("children", []):
            walk(child, matrix, seen | {i})

    for root in model.root_nodes():
        walk(root, IDENTITY, frozenset())
    return out


def union(boxes):
    """The AABB enclosing several (lo, hi) pairs, or None."""
    boxes = [b for b in boxes if b]
    if not boxes:
        return None
    lo = [min(b[0][i] for b in boxes) for i in range(3)]
    hi = [max(b[1][i] for b in boxes) for i in range(3)]
    return lo, hi


def parse_dimensions(text):
    """[(label, meters)] for every figure with a unit in a cited dimension.

    "length overall 1.146 m; beam 0.93 m" gives two. The label is whatever
    precedes the figure, kept so a finding can say which dimension it means.
    """
    out = []
    pattern = re.compile(r"([-+]?\d+(?:\.\d+)?)\s*(mm|cm|m)\b")
    for piece in re.split(r"[;,]", str(text)):
        match = pattern.search(piece)
        if match:
            label = piece[:match.start()].strip() or "cited dimension"
            out.append((label, float(match.group(1)) * UNITS[match.group(2)]))
    return out


def plural(n, singular, plural_form=None):
    """'1 primitive has' / '3 primitives have' without a stray 's'."""
    return f"{n} {singular}" if n == 1 else f"{n} {plural_form or singular + 's'}"


def png_has_alpha(head):
    """True when a PNG's IHDR declares a colour type carrying alpha.

    Colour type is byte 25: 4 is grey+alpha and 6 is RGBA. A tRNS chunk can also
    introduce transparency on types 0, 2 and 3, which this does not detect --
    the profile's concern is a delivered alpha channel, and exporters write one
    as type 4 or 6.
    """
    if len(head) < 26 or head[:8] != b"\x89PNG\r\n\x1a\n":
        return False
    return head[25] in (4, 6)


# --------------------------------------------------------------- the rules

def rule_4_1_filename(m):
    """The profile's File section: named `<part>.visual.glb`, part lowercase snake_case."""
    name = m.path.name
    if not name.endswith(".visual.glb"):
        return Finding("File naming", WARN, "filename is not <part>.visual.glb",
                       f"{name!r}; the delivery rule names the file after the part")
    part = m.part_name
    if not re.fullmatch(r"[a-z0-9]+(_[a-z0-9]+)*", part):
        return Finding("File naming", FAIL, "part name is not lowercase snake_case", repr(part))
    return Finding("File naming", PASS, f"named {name}")


def rule_4_2_container(m):
    """The profile's File format section: binary container required, .gltf prohibited."""
    if not m.is_glb:
        return Finding("File format", FAIL, "not the binary container",
                       "the .gltf form, with a side .bin and loose images, must not be delivered")
    return Finding("File format", PASS, "binary .glb container")


def rule_4_3_asset_header(m):
    asset = m.gltf.get("asset", {})
    out = []
    if asset.get("version") != "2.0":
        out.append(Finding("Asset header", FAIL, "asset.version is not \"2.0\"",
                           repr(asset.get("version"))))
    if "minVersion" in asset:
        # Asset header relaxed this from MUST NOT to SHOULD NOT. It remains a real hazard --
        # a stray minVersion is a hard load failure in a consumer that would
        # otherwise have coped -- but there is no glTF 2.1 for it to be right about.
        out.append(Finding("Asset header", WARN, "asset.minVersion is present",
                           repr(asset["minVersion"]) + ". A consumer that does not meet it "
                           "refuses the file outright, and there is no glTF 2.1 for it to "
                           "legitimately require."))
    return out or [Finding("Asset header", PASS, "asset header is 2.0 with no minVersion")]


def rule_5_5_scenes_and_nodes(m):
    """One scene, one node, no transform: exactly one coordinate system in the file.

    A node transform makes node space and scene space differ, and the two
    consumers compose the difference in opposite orders -- Gazebo applies the
    up-axis correction outside the root transform, RViz post-multiplies it
    inside -- so the same file lands in two different places. One node with no
    transform removes the possibility rather than documenting it.

    The transform test is on presence, not value. glTF omits any component equal
    to its default, so an absent key and an identity value are the same geometry
    written by two different exporters, and a rule about values would let a
    stated identity through while `gltf_to_yup.py` still refuses the file.
    """
    out = []
    scenes = m.get("scenes")
    nodes = m.get("nodes")
    if len(scenes) != 1:
        out.append(Finding("Scenes and nodes", FAIL, f"{len(scenes)} scenes, expected exactly 1"))

    if len(nodes) != 1:
        names = ", ".join(repr(n.get("name")) for n in nodes[:8])
        out.append(Finding("Scenes and nodes", FAIL, f"{len(nodes)} nodes, expected exactly 1",
                           f"{names}. A part is one node: placement belongs to the SDF "
                           f"visual pose and the joint tree, not to the asset"))

    roots = m.root_nodes()
    if len(roots) != 1:
        names = ", ".join(repr(nodes[i].get("name")) for i in roots[:8])
        out.append(Finding("Scenes and nodes", FAIL, f"{len(roots)} root nodes, expected exactly 1", names))

    if scenes and len(scenes) == 1:
        listed = scenes[0].get("nodes", [])
        if sorted(listed) != sorted(roots):
            out.append(Finding("Scenes and nodes", FAIL, "the scene does not list exactly the root node",
                               f"scene lists {listed}, roots are {roots}"))

    # One finding per class rather than per node: a scene with thousands of
    # roots would otherwise bury every other rule's verdict under its own.
    parents, transformed, unnamed, suffixed, spaced, misnamed = [], [], [], [], [], []
    for i, node in enumerate(nodes):
        name = node.get("name")
        label = repr(name) if name else f"node {i}"
        if node.get("children"):
            parents.append(f"{label} -> {node['children']}")
        keys = [k for k in ("translation", "rotation", "scale", "matrix") if k in node]
        if keys:
            transformed.append(f"{label} carries {', '.join(keys)}")
        if i not in roots:
            continue        # the name rules are about the part's own node
        if name is None:
            unnamed.append(label)
        elif re.search(r"\.\d{3}$", name):
            suffixed.append(label)
        elif " " in name:
            spaced.append(label)
        elif name != m.part_name:
            misnamed.append(label)

    def summarise(items, level, singular, plural, detail="", subject_noun="root nodes",
                  singular_noun="the root node"):
        if not items:
            return
        shown = ", ".join(items[:6]) + (f", and {len(items) - 6} more" if len(items) > 6 else "")
        subject = (f"{len(items)} {subject_noun} {plural}" if len(items) > 1
                   else f"{singular_noun} {singular}")
        out.append(Finding("Scenes and nodes", level, subject,
                           f"{shown}{'. ' + detail if detail else ''}"))

    summarise(parents, FAIL, "has child nodes", "have child nodes",
              "a delivery is one node with no hierarchy; Gazebo composes child transforms "
              "and bakes them into the vertices, so the structure is unrecoverable anyway",
              subject_noun="nodes", singular_noun="a node")
    summarise(transformed, FAIL, "carries a transform", "carry a transform",
              "translation, rotation, scale and matrix must all be absent, so that node "
              "space and scene space coincide. Clear location and rotation in Blender, and "
              "apply scale",
              subject_noun="nodes", singular_noun="the node")
    summarise(unnamed, FAIL, "is unnamed", "are unnamed",
              "Gazebo names each submesh after its node")
    summarise(suffixed, FAIL, "has a Blender numeric suffix", "have a Blender numeric suffix")
    summarise(spaced, FAIL, "has a space in the name", "have a space in the name")
    summarise(misnamed, WARN, "is not named after the part", "are not named after the part",
              f"the filename implies {m.part_name!r}")

    return out or [Finding("Scenes and nodes", PASS,
                           "one scene, one named node, no children, no transform")]


def rule_6_geometry(m):
    out = []
    non_triangles, missing = [], []
    for mi, pi, prim in m.primitives():
        if prim.get("mode", 4) != 4:
            non_triangles.append(f"mesh {mi} primitive {pi} mode {prim.get('mode')}")
        absent = [a for a in ("POSITION", "NORMAL", "TEXCOORD_0")
                  if a not in prim.get("attributes", {})]
        if absent:
            missing.append(f"mesh {mi} primitive {pi}: no {', '.join(absent)}")
    if non_triangles:
        out.append(Finding("Geometry", FAIL, f"{plural(len(non_triangles), 'primitive is', 'primitives are')} not triangles",
                           "; ".join(non_triangles[:5])))
    if missing:
        out.append(Finding("Geometry", FAIL, f"{plural(len(missing), 'primitive lacks', 'primitives lack')} a required attribute",
                           "; ".join(missing[:5])))
    return out or [Finding("Geometry", PASS, "every primitive is triangles with POSITION, NORMAL, TEXCOORD_0")]


def rule_6_1_uv(m):
    out = []
    # The profile's UV sets section permits TEXCOORD_1, and only for a baked occlusion lightmap.
    # Anything beyond that is a failure. Whether a present TEXCOORD_1 really
    # carries a lightmap cannot be read from the file: it depends on which slot
    # the material samples with it, which the material rules cover separately.
    sets = {a for _, _, p in m.primitives() for a in p.get("attributes", {})
            if a.startswith("TEXCOORD_")}
    extra = sorted(a for a in sets if a not in ("TEXCOORD_0", "TEXCOORD_1"))
    if extra:
        out.append(Finding("UV sets", FAIL, "more than two UV sets",
                           ", ".join(extra) + ". Only TEXCOORD_0, and TEXCOORD_1 for a "
                           "baked occlusion lightmap, are permitted"))

    worst = None
    for mi, pi, prim in m.primitives():
        idx = prim.get("attributes", {}).get("TEXCOORD_0")
        if idx is None:
            continue
        acc = m.gltf["accessors"][idx]
        lo, hi = acc.get("min"), acc.get("max")
        if not lo or not hi:
            try:
                uvs = read_accessor(m.gltf, m.resolver, idx)
            except Exception:
                continue
            if not uvs:
                continue
            lo = [min(v[0] for v in uvs), min(v[1] for v in uvs)]
            hi = [max(v[0] for v in uvs), max(v[1] for v in uvs)]
        span = (min(lo), max(hi))
        if worst is None or span[0] < worst[0] or span[1] > worst[1]:
            worst = span
    if worst and (worst[0] < -1e-4 or worst[1] > 1 + 1e-4):
        out.append(Finding(
            "UV sets", FAIL, "UV coordinates outside [0, 1]",
            f"range {worst[0]:.3f} to {worst[1]:.3f}. The profile requires [0,1]; note that "
            "tiling against a REPEAT sampler is normal practice elsewhere and 19 of 49 assets "
            "in the corpus do it, so this is a deliberate narrowing, not a defect everyone agrees on"))
    return out or [Finding("UV sets", PASS, f"{plural(len(sets), 'UV set')}, inside [0, 1]")]


def rule_6_3_primitives(m):
    """A primitive exists only to carry a material distinct from its siblings.

    glTF gives a primitive at most one `material`, so a part with several
    materials must have several primitives and there is no other reason to split
    one at these part sizes. Two primitives sharing a material therefore split
    the geometry for no reason a consumer can use, and they are not addressable
    separately: Gazebo names every submesh after the node that instantiated the
    mesh, so primitives under one node arrive with the same name and an SDF
    `<submesh>` selection takes the first and silently drops the rest.

    The profile's Scenes and nodes section's one-node rule forecloses the alternative of one primitive per
    node, so this rule and that one are the same decision seen from two sides.
    """
    out = []
    for mi, mesh in enumerate(m.get("meshes")):
        prims = mesh.get("primitives", [])
        seen = {}
        for pi, prim in enumerate(prims):
            material = prim.get("material")
            if material is None:
                continue        # the profile's Materials section fails a primitive with no material
            seen.setdefault(material, []).append(pi)
        shared = {mat: idx for mat, idx in seen.items() if len(idx) > 1}
        if shared:
            names = m.get("materials")
            detail = "; ".join(
                f"mesh {mi} primitives {idx} all use material "
                f"{names[mat].get('name', mat) if mat < len(names) else mat!r}"
                for mat, idx in sorted(shared.items()))
            out.append(Finding("Primitives", FAIL,
                               f"{plural(sum(len(i) for i in shared.values()), 'primitive')} "
                               f"share a material with a sibling",
                               f"{detail}. A primitive should exist only to carry a distinct "
                               f"material, and primitives under one node are indistinguishable "
                               f"to an SDF <submesh> selection"))
    total = sum(len(mesh.get("primitives", [])) for mesh in m.get("meshes"))
    return out or [Finding("Primitives", PASS,
                           f"{plural(total, 'primitive')}, each carrying a distinct material")]


def rule_7_materials(m):
    out = []
    materials = m.get("materials")

    no_material = [f"mesh {mi} primitive {pi}" for mi, pi, p in m.primitives()
                   if "material" not in p]
    if no_material:
        out.append(Finding("Materials", FAIL, f"{plural(len(no_material), 'primitive has', 'primitives have')} no material",
                           "; ".join(no_material[:5]) + " -- glTF's metallicFactor defaults to 1.0, "
                           "so a primitive with no material renders as white metal"))

    metal_trap, metal_unverified, missing_base, scaled = [], [], [], []
    for i, mat in enumerate(materials):
        name = mat.get("name", f"material {i}")
        pbr = mat.get("pbrMetallicRoughness", {})
        maps = material_maps(m.gltf, i)
        metallic = pbr.get("metallicFactor", 1.0)
        declared = "metallicFactor" in pbr
        if metallic > 0.0:
            how = f"metallicFactor {metallic}" if declared else "metallicFactor unset, so 1.0"
            if "metallicRoughness" not in maps:
                # Nothing can bring it back down: the material is metal.
                metal_trap.append(f"{name} ({how})")
            elif not declared:
                # A metallic-roughness texture multiplies against the factor, so
                # a blue channel of zero still yields a non-metal. Whether it
                # does cannot be known without decoding the image, which this
                # tool deliberately does not do -- so this warns rather than
                # fails. Do not read the warning as "probably fine": a solid
                # white metallic channel is the common export, and where this
                # project decoded its own maps it found B = 255 throughout, so
                # the unset factor really did make those parts metal.
                metal_unverified.append(f"{name} ({how}, metallicRoughness texture present)")
        if maps and "baseColor" not in maps:
            missing_base.append(f"{name} ({', '.join(sorted(maps))})")
        if mat.get("normalTexture", {}).get("scale", 1.0) != 1.0:
            scaled.append(f"{name} normalTexture.scale={mat['normalTexture']['scale']}")
        if mat.get("occlusionTexture", {}).get("strength", 1.0) != 1.0:
            scaled.append(f"{name} occlusionTexture.strength={mat['occlusionTexture']['strength']}")

    if metal_trap:
        out.append(Finding(
            "Materials", FAIL, f"{plural(len(metal_trap), 'material is', 'materials are')} metallic with nothing to override it",
            "; ".join(metal_trap[:6]) + ". glTF's metallicFactor defaults to 1.0, so a material "
            "that says nothing says metal. Plastics and painted surfaces must be non-metallic."))
    if metal_unverified:
        out.append(Finding(
            "Materials", WARN,
            f"{plural(len(metal_unverified), 'material leaves', 'materials leave')} metallicFactor unset but carry an ORM map",
            "; ".join(metal_unverified[:6]) + ". The texture's blue channel multiplies against "
            "the factor, so a black metallic channel would still yield a non-metal. Settling it "
            "needs the decoded texel values, which this tool does not read. Do not assume it is "
            "fine: a solid white metallic channel is the usual export, and every map measured in "
            "this project's own library had B = 255, which makes the part fully metal. State the "
            "factor explicitly if the part is not metal."))
    if missing_base:
        out.append(Finding("Materials", FAIL, f"{plural(len(missing_base), 'textured material has', 'textured materials have')} no baseColorTexture",
                           "; ".join(missing_base[:5]) + " -- this is the shape that terminates RViz"))
    if scaled:
        out.append(Finding("Materials", FAIL, "normalTexture.scale / occlusionTexture.strength must be 1.0",
                           "; ".join(scaled[:5]) + " -- both are ignored by this project's consumers"))
    return out or [Finding("Materials", PASS, f"{len(materials)} materials, none metallic by default")]


def rule_8_textures(m):
    out = []
    images = m.get("images")
    if not images:
        return [Finding("Textures", SKIP, "no embedded images")]

    linear_png = {}
    for mi in range(len(m.get("materials"))):
        for slot, info in material_maps(m.gltf, mi).items():
            if info["image"] is not None and slot in LINEAR_SLOTS:
                linear_png.setdefault(info["image"], set()).add(slot)

    bad_format, oversize, linear_jpeg, undimensioned = [], [], [], []
    for i, image in enumerate(images):
        name = image.get("name", f"image {i}")
        head = m.image_bytes(i)
        if head is None:
            continue
        mime, w, h = sniff_image(head)
        if mime is None:
            bad_format.append(f"{name}: unrecognised format")
            continue
        if mime not in ("image/png", "image/jpeg"):
            bad_format.append(f"{name}: {mime}")
            continue
        if w is None or h is None:
            undimensioned.append(f"{name}: {mime}, dimensions not found in the header")
        elif max(w, h) > 2048:
            oversize.append(f"{name}: {w}x{h}")
        if mime == "image/jpeg" and i in linear_png:
            linear_jpeg.append(f"{name}: JPEG in {'/'.join(sorted(linear_png[i]))}")

    if bad_format:
        out.append(Finding("Textures", FAIL, "images must be PNG or JPEG", "; ".join(bad_format[:5])))
    if oversize:
        out.append(Finding("Textures", FAIL, f"{plural(len(oversize), 'texture exceeds', 'textures exceed')} 2048 px",
                           "; ".join(oversize[:5])))
    if undimensioned:
        out.append(Finding("Textures", WARN, f"{plural(len(undimensioned), 'image has', 'images have')} unreadable dimensions",
                           "; ".join(undimensioned[:5]) + " -- the size rule could not be checked"))
    if linear_jpeg:
        out.append(Finding(
            "Textures", FAIL, f"{plural(len(linear_jpeg), 'linear map is', 'linear maps are')} JPEG",
            "; ".join(linear_jpeg[:5]) + ". Chroma subsampling blends channels that are "
            "unrelated in a normal or ORM map. The remedy is a re-export from the source "
            "texture -- converting a JPEG to PNG preserves the damage."))
    return out or [Finding("Textures", PASS, f"{len(images)} images, PNG/JPEG, within 2048 px")]


def rule_9_transparency(m):
    out = []
    for i, mat in enumerate(m.get("materials")):
        name = mat.get("name", f"material {i}")
        mode = mat.get("alphaMode", "OPAQUE")
        if mode == "BLEND":
            out.append(Finding("Transparency", FAIL, f"{name} uses alphaMode BLEND",
                               "Gazebo ignores BLEND and renders the material opaque; a cutout "
                               "belongs in MASK with binary alpha"))
        elif mode == "MASK":
            cutoff = mat.get("alphaCutoff", 0.5)
            if cutoff != 0.5:
                out.append(Finding("Transparency", FAIL, f"{name} uses MASK with alphaCutoff {cutoff}",
                                   "the profile fixes the cutoff at 0.5"))
            maps = material_maps(m.gltf, i)
            base = maps.get("baseColor", {}).get("image")
            if base is not None:
                head = m.image_bytes(base)
                if head is not None and not png_has_alpha(head):
                    out.append(Finding("Transparency", FAIL, f"{name} is MASK but its base colour has no alpha",
                                       "a MASK material needs binary alpha in a PNG base colour"))
    return out or [Finding("Transparency", PASS, "no BLEND; any MASK is cutoff 0.5 with alpha")]


def rule_10_prohibited(m):
    out = []
    required = m.gltf.get("extensionsRequired", [])
    if required:
        out.append(Finding(
            "Prohibited content", FAIL, "extensionsRequired is not empty", ", ".join(required) +
            ". A conforming reader must refuse a file outright when it requires an extension "
            "it does not implement. Gazebo does not: measured with glb_probe against "
            "jetty_demo's Distribution_Warehouse, which requires KHR_texture_transform, the "
            "loader built all 3010 submeshes and 19 materials rather than refusing. The risk "
            "is a file that loads and is quietly wrong, not one that fails loudly."))

    used = set(m.gltf.get("extensionsUsed", [])) | set(required)
    for ext, label in PROHIBITED_EXTENSIONS.items():
        if ext in used:
            out.append(Finding("Prohibited content", FAIL, f"{label} is prohibited", ext))

    for key, label in (("animations", "animations"), ("skins", "skins"),
                       ("cameras", "cameras")):
        if m.get(key):
            out.append(Finding("Prohibited content", FAIL, f"{label} are prohibited",
                               f"{len(m.get(key))} present"))
    lights = m.gltf.get("extensions", {}).get("KHR_lights_punctual", {}).get("lights", [])
    if lights:
        out.append(Finding("Prohibited content", FAIL, "lights are prohibited", f"{len(lights)} present"))
    return out or [Finding("Prohibited content", PASS, "no prohibited extensions or content")]


def rule_11_generator(m):
    generator = m.gltf.get("asset", {}).get("generator")
    if not generator:
        return Finding("Authoring toolchain", FAIL, "asset.generator is absent",
                       "a delivery must record the exporter that produced it")
    return Finding("Authoring toolchain", PASS, f"generator: {generator}")


REQUIRED_AXES = (("gltfrp:forward", "+X"), ("gltfrp:up", "+Z"))


def rule_5_2_axes(m):
    """The profile's Axes section: +X forward, +Y left, +Z up -- ISO 9787 and REP 103.

    Nothing in a glTF file records which way its author meant up or forward, so
    the geometry cannot settle this. What can be checked is the manifest's
    declaration under the manifest section, and a declaration that disagrees with Axes is a
    straightforward failure: the rule is decided, not interim.

    An absent declaration is a WARN rather than a FAIL because it is the second
    kind of warning the legend describes -- a MUST the file alone cannot settle.
    Only a rendered view or the authoring source can.
    """
    packet = m.manifest() or {}
    declared = {key: packet.get(key) for key, _ in REQUIRED_AXES}
    if all(v is None for v in declared.values()):
        # The profile's manifest section requires the declaration and reports its absence. Saying
        # so twice would make one omission look like two defects.
        return Finding("Axes", SKIP, "the axes are not declared, so there is nothing to compare",
                       "the profile's manifest section reports the missing declaration; nothing in the geometry "
                       "records an axis, so this rule can only check what a manifest states")
    wrong = [f"{key} is {declared[key]!r}, expected {want!r}"
             for key, want in REQUIRED_AXES if declared[key] != want]
    if wrong:
        return Finding("Axes", FAIL, "the manifest declares axes that the profile's Axes section prohibits",
                       "; ".join(wrong) + ". The profile follows ISO 9787 and REP 103 rather "
                       "than glTF, so a delivery is +X forward and +Z up. Export from Blender "
                       "with the '+Y Up' option off.")
    return Finding("Axes", PASS, "declared +X forward, +Z up")


def rule_5_1_scale(m):
    """The profile's Units section requires meters at real-world scale.

    A file cannot state its own units, so the only check is against a figure
    from outside it: the dimension the manifest cites. Each cited figure has to
    match one of the three axis extents within the manifest's own tolerance.
    Which axis is not prescribed; the finding says which one matched.
    """
    packet = m.manifest() or {}
    cited = packet.get("gltfrp:nominalDimension")
    if not cited:
        return Finding("Units", ADVISORY, "scale cannot be checked: the manifest cites no dimension",
                       "glTF says meters and nothing in the file confirms it. A cited figure in "
                       "gltfrp:nominalDimension, with gltfrp:dimensionTolerance, is what this "
                       "rule compares the geometry against.")
    box = m.extent()
    if box is None:
        return Finding("Units", SKIP, "no geometry bounds to measure")
    figures = parse_dimensions(cited)
    if not figures:
        return Finding("Units", WARN, "the cited dimension has no readable figure",
                       f"{cited!r}. Expected a number with its unit, m, cm or mm, for example "
                       "'length overall 1.146 m'.")

    extents = [box[1][i] - box[0][i] for i in range(3)]
    measured = ", ".join(f"{axis} {value:.4g} m" for axis, value in zip("XYZ", extents))
    tolerance = packet.get("gltfrp:dimensionTolerance")
    try:
        tolerance = None if tolerance is None else float(tolerance)
    except (TypeError, ValueError):
        tolerance = None

    out = []
    for label, figure in figures:
        nearest = min(range(3), key=lambda i: abs(extents[i] - figure))
        difference = abs(extents[nearest] - figure)
        axis = "XYZ"[nearest]
        what = f"{label} {figure:.4g} m"
        if tolerance is None:
            out.append(Finding(
                "Units", WARN, f"{what} has no tolerance to be held to",
                f"nearest extent is {axis} {extents[nearest]:.4g} m, a difference of "
                f"{difference:.3g} m. Extents: {measured}. State gltfrp:dimensionTolerance."))
        elif difference <= tolerance:
            out.append(Finding(
                "Units", PASS, f"{what} matches the {axis} extent {extents[nearest]:.4g} m",
                f"difference {difference:.3g} m, tolerance {tolerance:.3g} m. Extents: {measured}"))
        else:
            hint = ""
            for ratio, unit in SCALE_SUSPECTS:
                if figure > 0 and any(abs(e / figure - ratio) <= 0.02 * ratio for e in extents):
                    hint = f" An extent is about {ratio:g} times the figure: the file looks like {unit}."
                    break
            out.append(Finding(
                "Units", FAIL, f"{what} matches no extent",
                f"extents: {measured}. The nearest is {axis}, off by {difference:.3g} m against "
                f"a tolerance of {tolerance:.3g} m.{hint}"))
    return out


def rule_4_1_1_manifest(m):
    """The profile's manifest section: a delivery MUST carry a manifest declaring three properties.

    The three are `gltfrp:partRole`, `gltfrp:forward` and `gltfrp:up`, and each
    records something no measurement can recover: whether Datum specification's datum rule
    applies, and the two axes that are this profile's departure from glTF. This
    rule owns whether they are *present*; the profile's Axes section owns whether the axis
    values are the ones it requires.
    """
    packet = m.manifest()
    if packet is None:
        used = set(m.gltf.get("extensionsUsed", []))
        if "KHR_xmp_json_ld" in used:
            return [Finding("The manifest", FAIL, "KHR_xmp_json_ld is present but no packet reaches the asset",
                            "the manifest must be attached to the glTF asset object to describe the "
                            "whole delivery")]
        return [Finding("The manifest", FAIL, "no manifest",
                        "a delivery must carry one in KHR_xmp_json_ld attached to the asset object, "
                        "declaring at least gltfrp:partRole, gltfrp:forward and gltfrp:up. "
                        "Provenance cannot be reconstructed afterwards.")]

    out = []
    for key, what in (("gltfrp:forward", "which axis the part faces"),
                      ("gltfrp:up", "which axis is up")):
        if packet.get(key) is None:
            out.append(Finding("The manifest", FAIL, f"the manifest does not declare {key}",
                               f"one of the three required properties: {what}. Nothing in a glTF "
                               f"file records it, so an undeclared axis cannot be checked at all"))

    role = packet.get("gltfrp:partRole")
    if role is None:
        out.append(Finding("The manifest", FAIL, "the manifest does not declare gltfrp:partRole",
                           "one of the three required properties; base or component"))
    elif role not in ("base", "component"):
        out.append(Finding("The manifest", FAIL, f"gltfrp:partRole is {role!r}",
                           "must be base or component"))

    tool = packet.get("xmp:CreatorTool")
    generator = m.gltf.get("asset", {}).get("generator")
    if tool and generator and tool != generator:
        out.append(Finding("The manifest", FAIL, "xmp:CreatorTool disagrees with asset.generator",
                           f"manifest says {tool!r}, the file says {generator!r}. This is what a "
                           "manifest copied from another part and never edited looks like."))

    missing = [k for k in ("dc:source", "dc:creator", "dc:date") if k not in packet]
    if missing:
        out.append(Finding("The manifest", WARN, "the manifest omits recommended provenance",
                           ", ".join(missing)))
    return out or [Finding("The manifest", PASS, f"manifest present, role {role}")]


def rule_5_6_datum(m):
    """The profile's Datum specification section: the datum is one point; orientation comes from Axes.

    The ordered-list-and-six-degrees-of-freedom machinery this rule used to
    implement is gone. The profile's Axes section fixes all three rotations for every delivery,
    and a point fixes all three translations, so one named point is a complete
    specification and there is no bookkeeping left to check.
    """
    packet = m.manifest()
    role = (packet or {}).get("gltfrp:partRole")
    if packet is None or role is None:
        return [Finding("Datum specification", SKIP, "no declared role, so no datum requirement applies")]

    out = []
    point = packet.get("gltfrp:datumPoint")
    if not point:
        out.append(Finding(
            "Datum specification", FAIL if role == "base" else WARN,
            f"a {role} part names no datum point",
            "The profile requires a base part to name the point its origin is referenced to, and "
            "recommends it for a component. Without one the origin is a number with no meaning: "
            "nothing distinguishes a deliberate placement from wherever the tool left it."))

    # A derived quantity is not a feature of the part, whatever it is derived from.
    derived_words = ("centroid", "center of mass", "centre of mass", "bounding box",
                     "bounding-box", "silhouette", "median", "average", "mean")
    if point and any(w in str(point).lower() for w in derived_words):
        out.append(Finding(
            "Datum specification", FAIL, "the datum point looks derived",
            f"{point!r}. The datum point must be a geometric feature of the part. A computed "
            "property references nothing, moves when the geometry changes, and a different "
            "tool computes a different one."))

    # Stale properties from the ordered-list form, which Datum specification no longer defines.
    stale = [k for k in ("gltfrp:datumFeature", "gltfrp:datumFeatureKind",
                         "gltfrp:datumConstrains", "gltfrp:datumDerivedFrom") if k in packet]
    if stale:
        out.append(Finding("Datum specification", WARN, "the manifest uses the superseded datum properties",
                           ", ".join(stale) + ". The profile now names a single gltfrp:datumPoint; "
                           "orientation comes from the profile's Axes section and is not part of the datum."))

    if "gltfrp:realizedPose" in packet or "realizedPose" in packet:
        out.append(Finding("Datum specification", FAIL, "the manifest records a realized pose",
                           "a realized pose is derived by measurement, never authored; recording "
                           "it beside the rule that derives it creates two sources of truth"))
    return out or [Finding("Datum specification", PASS, f"datum point: {point}")]


RULES = [
    rule_4_1_filename,
    rule_4_2_container,
    rule_4_3_asset_header,
    rule_4_1_1_manifest,
    rule_5_1_scale,
    rule_5_2_axes,
    rule_5_5_scenes_and_nodes,
    rule_5_6_datum,
    rule_6_geometry,
    rule_6_1_uv,
    rule_6_3_primitives,
    rule_7_materials,
    rule_8_textures,
    rule_9_transparency,
    rule_10_prohibited,
    rule_11_generator,
]


def check_file(path):
    """Every rule's verdict on one file, in profile-section order."""
    model = Model(path)
    findings = []
    for rule in RULES:
        result = rule(model)
        findings.extend(result if isinstance(result, list) else [result])
    return findings
