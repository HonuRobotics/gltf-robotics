"""The profile's mechanically decidable rules, one function each.

Every rule names the profile section it comes from, so a failure points at the
text that justifies it rather than at an opinion in this file. Sections the
profile marks Open are reported as advisory: the profile says a delivery cannot
fail to conform on an unsettled point, and this must not quietly harden one.
A rule that is normative today but recorded as Open because a more capable
version is plausible later still fails, because it is normative today.

What is deliberately not here: the four conformance questions in profile
section 12 fail independently, and only "compliant" is decidable by reading the
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
    material_maps,
    read_accessor,
    sniff_image,
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
FEATURE_KINDS = ("point", "line", "plane", "helix")
AXES = ("+X", "-X", "+Y", "-Y", "+Z", "-Z")
DOF = ("Tx", "Ty", "Tz", "Rx", "Ry", "Rz")
PROHIBITED_EXTENSIONS = {
    "KHR_draco_mesh_compression": "Draco mesh compression",
    "KHR_texture_basisu": "KTX2/Basis textures",
    "KHR_texture_transform": "KHR_texture_transform",
    "KHR_materials_pbrSpecularGlossiness": "the specular-glossiness workflow",
}


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

        Profile 4.1.4 puts the manifest in KHR_xmp_json_ld and attaches it to
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
    """Section 4.1: named `<part>.visual.glb`, part lowercase snake_case."""
    name = m.path.name
    if not name.endswith(".visual.glb"):
        return Finding("4.1", WARN, "filename is not <part>.visual.glb",
                       f"{name!r}; the delivery rule names the file after the part")
    part = m.part_name
    if not re.fullmatch(r"[a-z0-9]+(_[a-z0-9]+)*", part):
        return Finding("4.1", FAIL, "part name is not lowercase snake_case", repr(part))
    return Finding("4.1", PASS, f"named {name}")


def rule_4_2_container(m):
    """Section 4.2: binary container required, .gltf prohibited."""
    if not m.is_glb:
        return Finding("4.2", FAIL, "not the binary container",
                       "the .gltf form, with a side .bin and loose images, must not be delivered")
    return Finding("4.2", PASS, "binary .glb container")


def rule_4_3_asset_header(m):
    asset = m.gltf.get("asset", {})
    out = []
    if asset.get("version") != "2.0":
        out.append(Finding("4.3", FAIL, "asset.version is not \"2.0\"",
                           repr(asset.get("version"))))
    if "minVersion" in asset:
        # 4.3 relaxed this from MUST NOT to SHOULD NOT. It remains a real hazard --
        # a stray minVersion is a hard load failure in a consumer that would
        # otherwise have coped -- but there is no glTF 2.1 for it to be right about.
        out.append(Finding("4.3", WARN, "asset.minVersion is present",
                           repr(asset["minVersion"]) + ". A consumer that does not meet it "
                           "refuses the file outright, and there is no glTF 2.1 for it to "
                           "legitimately require."))
    return out or [Finding("4.3", PASS, "asset header is 2.0 with no minVersion")]


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
        out.append(Finding("5.5", FAIL, f"{len(scenes)} scenes, expected exactly 1"))

    if len(nodes) != 1:
        names = ", ".join(repr(n.get("name")) for n in nodes[:8])
        out.append(Finding("5.5", FAIL, f"{len(nodes)} nodes, expected exactly 1",
                           f"{names}. A part is one node: placement belongs to the SDF "
                           f"visual pose and the joint tree, not to the asset"))

    roots = m.root_nodes()
    if len(roots) != 1:
        names = ", ".join(repr(nodes[i].get("name")) for i in roots[:8])
        out.append(Finding("5.5", FAIL, f"{len(roots)} root nodes, expected exactly 1", names))

    if scenes and len(scenes) == 1:
        listed = scenes[0].get("nodes", [])
        if sorted(listed) != sorted(roots):
            out.append(Finding("5.5", FAIL, "the scene does not list exactly the root node",
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
        out.append(Finding("5.5", level, subject,
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

    return out or [Finding("5.5", PASS,
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
        out.append(Finding("6", FAIL, f"{plural(len(non_triangles), 'primitive is', 'primitives are')} not triangles",
                           "; ".join(non_triangles[:5])))
    if missing:
        out.append(Finding("6", FAIL, f"{plural(len(missing), 'primitive lacks', 'primitives lack')} a required attribute",
                           "; ".join(missing[:5])))
    return out or [Finding("6", PASS, "every primitive is triangles with POSITION, NORMAL, TEXCOORD_0")]


def rule_6_1_uv(m):
    out = []
    # Profile 6.1 permits TEXCOORD_1, and only for a baked occlusion lightmap.
    # Anything beyond that is a failure. Whether a present TEXCOORD_1 really
    # carries a lightmap cannot be read from the file: it depends on which slot
    # the material samples with it, which the material rules cover separately.
    sets = {a for _, _, p in m.primitives() for a in p.get("attributes", {})
            if a.startswith("TEXCOORD_")}
    extra = sorted(a for a in sets if a not in ("TEXCOORD_0", "TEXCOORD_1"))
    if extra:
        out.append(Finding("6.1", FAIL, "more than two UV sets",
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
            "6.1", FAIL, "UV coordinates outside [0, 1]",
            f"range {worst[0]:.3f} to {worst[1]:.3f}. The profile requires [0,1]; note that "
            "tiling against a REPEAT sampler is normal practice elsewhere and 19 of 49 assets "
            "in the corpus do it, so this is a deliberate narrowing, not a defect everyone agrees on"))
    return out or [Finding("6.1", PASS, f"{plural(len(sets), 'UV set')}, inside [0, 1]")]


def rule_6_3_primitives(m):
    """A primitive exists only to carry a material distinct from its siblings.

    glTF gives a primitive at most one `material`, so a part with several
    materials must have several primitives and there is no other reason to split
    one at these part sizes. Two primitives sharing a material therefore split
    the geometry for no reason a consumer can use, and they are not addressable
    separately: Gazebo names every submesh after the node that instantiated the
    mesh, so primitives under one node arrive with the same name and an SDF
    `<submesh>` selection takes the first and silently drops the rest.

    Section 5.5's one-node rule forecloses the alternative of one primitive per
    node, so this rule and that one are the same decision seen from two sides.
    """
    out = []
    for mi, mesh in enumerate(m.get("meshes")):
        prims = mesh.get("primitives", [])
        seen = {}
        for pi, prim in enumerate(prims):
            material = prim.get("material")
            if material is None:
                continue        # section 7 fails a primitive with no material
            seen.setdefault(material, []).append(pi)
        shared = {mat: idx for mat, idx in seen.items() if len(idx) > 1}
        if shared:
            names = m.get("materials")
            detail = "; ".join(
                f"mesh {mi} primitives {idx} all use material "
                f"{names[mat].get('name', mat) if mat < len(names) else mat!r}"
                for mat, idx in sorted(shared.items()))
            out.append(Finding("6.3", FAIL,
                               f"{plural(sum(len(i) for i in shared.values()), 'primitive')} "
                               f"share a material with a sibling",
                               f"{detail}. A primitive should exist only to carry a distinct "
                               f"material, and primitives under one node are indistinguishable "
                               f"to an SDF <submesh> selection"))
    total = sum(len(mesh.get("primitives", [])) for mesh in m.get("meshes"))
    return out or [Finding("6.3", PASS,
                           f"{plural(total, 'primitive')}, each carrying a distinct material")]


def rule_7_materials(m):
    out = []
    materials = m.get("materials")

    no_material = [f"mesh {mi} primitive {pi}" for mi, pi, p in m.primitives()
                   if "material" not in p]
    if no_material:
        out.append(Finding("7", FAIL, f"{plural(len(no_material), 'primitive has', 'primitives have')} no material",
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
            "7", FAIL, f"{plural(len(metal_trap), 'material is', 'materials are')} metallic with nothing to override it",
            "; ".join(metal_trap[:6]) + ". glTF's metallicFactor defaults to 1.0, so a material "
            "that says nothing says metal. Plastics and painted surfaces must be non-metallic."))
    if metal_unverified:
        out.append(Finding(
            "7", WARN,
            f"{plural(len(metal_unverified), 'material leaves', 'materials leave')} metallicFactor unset but carry an ORM map",
            "; ".join(metal_unverified[:6]) + ". The texture's blue channel multiplies against "
            "the factor, so a black metallic channel would still yield a non-metal. Settling it "
            "needs the decoded texel values, which this tool does not read. Do not assume it is "
            "fine: a solid white metallic channel is the usual export, and every map measured in "
            "this project's own library had B = 255, which makes the part fully metal. State the "
            "factor explicitly if the part is not metal."))
    if missing_base:
        out.append(Finding("7", FAIL, f"{plural(len(missing_base), 'textured material has', 'textured materials have')} no baseColorTexture",
                           "; ".join(missing_base[:5]) + " -- this is the shape that terminates RViz"))
    if scaled:
        out.append(Finding("7", FAIL, "normalTexture.scale / occlusionTexture.strength must be 1.0",
                           "; ".join(scaled[:5]) + " -- both are ignored by this project's consumers"))
    return out or [Finding("7", PASS, f"{len(materials)} materials, none metallic by default")]


def rule_8_textures(m):
    out = []
    images = m.get("images")
    if not images:
        return [Finding("8", SKIP, "no embedded images")]

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
        out.append(Finding("8", FAIL, "images must be PNG or JPEG", "; ".join(bad_format[:5])))
    if oversize:
        out.append(Finding("8", FAIL, f"{plural(len(oversize), 'texture exceeds', 'textures exceed')} 2048 px",
                           "; ".join(oversize[:5])))
    if undimensioned:
        out.append(Finding("8", WARN, f"{plural(len(undimensioned), 'image has', 'images have')} unreadable dimensions",
                           "; ".join(undimensioned[:5]) + " -- the size rule could not be checked"))
    if linear_jpeg:
        out.append(Finding(
            "8", FAIL, f"{plural(len(linear_jpeg), 'linear map is', 'linear maps are')} JPEG",
            "; ".join(linear_jpeg[:5]) + ". Chroma subsampling blends channels that are "
            "unrelated in a normal or ORM map. The remedy is a re-export from the source "
            "texture -- converting a JPEG to PNG preserves the damage."))
    return out or [Finding("8", PASS, f"{len(images)} images, PNG/JPEG, within 2048 px")]


def rule_9_transparency(m):
    out = []
    for i, mat in enumerate(m.get("materials")):
        name = mat.get("name", f"material {i}")
        mode = mat.get("alphaMode", "OPAQUE")
        if mode == "BLEND":
            out.append(Finding("9", FAIL, f"{name} uses alphaMode BLEND",
                               "Gazebo ignores BLEND and renders the material opaque; a cutout "
                               "belongs in MASK with binary alpha"))
        elif mode == "MASK":
            cutoff = mat.get("alphaCutoff", 0.5)
            if cutoff != 0.5:
                out.append(Finding("9", FAIL, f"{name} uses MASK with alphaCutoff {cutoff}",
                                   "the profile fixes the cutoff at 0.5"))
            maps = material_maps(m.gltf, i)
            base = maps.get("baseColor", {}).get("image")
            if base is not None:
                head = m.image_bytes(base)
                if head is not None and not png_has_alpha(head):
                    out.append(Finding("9", FAIL, f"{name} is MASK but its base colour has no alpha",
                                       "a MASK material needs binary alpha in a PNG base colour"))
    return out or [Finding("9", PASS, "no BLEND; any MASK is cutoff 0.5 with alpha")]


def rule_10_prohibited(m):
    out = []
    required = m.gltf.get("extensionsRequired", [])
    if required:
        out.append(Finding(
            "10", FAIL, "extensionsRequired is not empty", ", ".join(required) +
            ". A conforming reader must refuse a file outright when it requires an extension "
            "it does not implement. Gazebo does not: measured with glb_probe against "
            "jetty_demo's Distribution_Warehouse, which requires KHR_texture_transform, the "
            "loader built all 3010 submeshes and 19 materials rather than refusing. The risk "
            "is a file that loads and is quietly wrong, not one that fails loudly."))

    used = set(m.gltf.get("extensionsUsed", [])) | set(required)
    for ext, label in PROHIBITED_EXTENSIONS.items():
        if ext in used:
            out.append(Finding("10", FAIL, f"{label} is prohibited", ext))

    for key, label in (("animations", "animations"), ("skins", "skins"),
                       ("cameras", "cameras")):
        if m.get(key):
            out.append(Finding("10", FAIL, f"{label} are prohibited",
                               f"{len(m.get(key))} present"))
    lights = m.gltf.get("extensions", {}).get("KHR_lights_punctual", {}).get("lights", [])
    if lights:
        out.append(Finding("10", FAIL, "lights are prohibited", f"{len(lights)} present"))
    return out or [Finding("10", PASS, "no prohibited extensions or content")]


def rule_11_generator(m):
    generator = m.gltf.get("asset", {}).get("generator")
    if not generator:
        return Finding("11", FAIL, "asset.generator is absent",
                       "a delivery must record the exporter that produced it")
    return Finding("11", PASS, f"generator: {generator}")


REQUIRED_AXES = (("gltfrp:forward", "+X"), ("gltfrp:up", "+Z"))


def rule_5_2_axes(m):
    """Section 5.2: +X forward, +Y left, +Z up -- ISO 9787 and REP 103.

    Nothing in a glTF file records which way its author meant up or forward, so
    the geometry cannot settle this. What can be checked is the manifest's
    declaration under 4.1.4, and a declaration that disagrees with 5.2 is a
    straightforward failure: the rule is decided, not interim.

    An absent declaration is a WARN rather than a FAIL because it is the second
    kind of warning the legend describes -- a MUST the file alone cannot settle.
    Only a rendered view or the authoring source can.
    """
    packet = m.manifest() or {}
    declared = {key: packet.get(key) for key, _ in REQUIRED_AXES}
    if all(v is None for v in declared.values()):
        # Section 4.1.4 requires the declaration and reports its absence. Saying
        # so twice would make one omission look like two defects.
        return Finding("5.2", SKIP, "the axes are not declared, so there is nothing to compare",
                       "section 4.1.4 reports the missing declaration; nothing in the geometry "
                       "records an axis, so this rule can only check what a manifest states")
    wrong = [f"{key} is {declared[key]!r}, expected {want!r}"
             for key, want in REQUIRED_AXES if declared[key] != want]
    if wrong:
        return Finding("5.2", FAIL, "the manifest declares axes that section 5.2 prohibits",
                       "; ".join(wrong) + ". The profile follows ISO 9787 and REP 103 rather "
                       "than glTF, so a delivery is +X forward and +Z up. Export from Blender "
                       "with the '+Y Up' option off.")
    return Finding("5.2", PASS, "declared +X forward, +Z up")


def rule_5_1_scale(m):
    """Section 5.1 requires meters. A file cannot state its own units."""
    return Finding("5.1", ADVISORY, "scale is not checkable from the file",
                   "glTF says meters and nothing in the file confirms it. Two assets in the "
                   "corpus are millimetre files corrected downstream. What would catch a wrong "
                   "scale is a cited dimensional figure per part, which section 4.1.4 now records in "
                   "the manifest as gltfrp:nominalDimension with a tolerance.")


def _listvals(packet, key):
    """An XMP ordered or unordered array as a plain list.

    KHR_xmp_json_ld requires arrays to be wrapped in `@list` or `@set`, so the
    value is a dict with one of those keys rather than a bare array.
    """
    v = packet.get(key)
    if v is None:
        return None
    if isinstance(v, dict):
        return v.get("@list") or v.get("@set") or []
    return v if isinstance(v, list) else [v]


def rule_4_1_1_manifest(m):
    """Section 4.1.4: a delivery MUST carry a manifest declaring three properties.

    The three are `gltfrp:partRole`, `gltfrp:forward` and `gltfrp:up`, and each
    records something no measurement can recover: whether 5.6's datum rule
    applies, and the two axes that are this profile's departure from glTF. This
    rule owns whether they are *present*; section 5.2 owns whether the axis
    values are the ones it requires.
    """
    packet = m.manifest()
    if packet is None:
        used = set(m.gltf.get("extensionsUsed", []))
        if "KHR_xmp_json_ld" in used:
            return [Finding("4.1.4", FAIL, "KHR_xmp_json_ld is present but no packet reaches the asset",
                            "the manifest must be attached to the glTF asset object to describe the "
                            "whole delivery")]
        return [Finding("4.1.4", FAIL, "no manifest",
                        "a delivery must carry one in KHR_xmp_json_ld attached to the asset object, "
                        "declaring at least gltfrp:partRole, gltfrp:forward and gltfrp:up. "
                        "Provenance cannot be reconstructed afterwards.")]

    out = []
    for key, what in (("gltfrp:forward", "which axis the part faces"),
                      ("gltfrp:up", "which axis is up")):
        if packet.get(key) is None:
            out.append(Finding("4.1.4", FAIL, f"the manifest does not declare {key}",
                               f"one of the three required properties: {what}. Nothing in a glTF "
                               f"file records it, so an undeclared axis cannot be checked at all"))

    role = packet.get("gltfrp:partRole")
    if role is None:
        out.append(Finding("4.1.4", FAIL, "the manifest does not declare gltfrp:partRole",
                           "one of the three required properties; base or component"))
    elif role not in ("base", "component"):
        out.append(Finding("4.1.4", FAIL, f"gltfrp:partRole is {role!r}",
                           "must be base or component"))

    tool = packet.get("xmp:CreatorTool")
    generator = m.gltf.get("asset", {}).get("generator")
    if tool and generator and tool != generator:
        out.append(Finding("4.1.4", FAIL, "xmp:CreatorTool disagrees with asset.generator",
                           f"manifest says {tool!r}, the file says {generator!r}. This is what a "
                           "manifest copied from another part and never edited looks like."))

    missing = [k for k in ("dc:source", "dc:creator", "dc:date") if k not in packet]
    if missing:
        out.append(Finding("4.1.4", WARN, "the manifest omits recommended provenance",
                           ", ".join(missing)))
    return out or [Finding("4.1.4", PASS, f"manifest present, role {role}")]


def rule_5_6_datum(m):
    """Section 5.6: a base part MUST carry a complete datum specification."""
    packet = m.manifest()
    role = (packet or {}).get("gltfrp:partRole")

    if packet is None or role is None:
        return [Finding("5.6", SKIP, "no declared role, so no datum requirement applies")]

    features = _listvals(packet, "gltfrp:datumFeature")
    kinds = _listvals(packet, "gltfrp:datumFeatureKind")
    constrains = _listvals(packet, "gltfrp:datumConstrains")
    forward = packet.get("gltfrp:forward")
    up = packet.get("gltfrp:up")

    required = role == "base"
    level = FAIL if required else WARN

    if not features:
        return [Finding("5.6", level, f"a {role} part carries no datum specification",
                        "a base part must declare one; a component part should" if required
                        else "a component part should declare one, usually its mounting interface")]

    out = []
    if not (len(features) == len(kinds or []) == len(constrains or [])):
        out.append(Finding("5.6", FAIL, "the datum lists are not the same length",
                           f"{len(features)} features, {len(kinds or [])} kinds, "
                           f"{len(constrains or [])} constraint entries. The three lists are "
                           "positionally matched."))
        return out

    bad = [k for k in kinds if k not in FEATURE_KINDS]
    if bad:
        out.append(Finding("5.6", FAIL, "a datum feature is not a situation feature",
                           ", ".join(map(repr, bad)) + f". ISO 17450-1 closes the list to "
                           f"{', '.join(FEATURE_KINDS)}."))

    seen = []
    for entry in constrains:
        seen.extend(str(entry).replace(",", " ").split())
    unknown = sorted({d for d in seen if d not in DOF})
    if unknown:
        out.append(Finding("5.6", FAIL, "unrecognised degree of freedom",
                           ", ".join(map(repr, unknown)) + f". Expected from {', '.join(DOF)}."))
    dupes = sorted({d for d in seen if seen.count(d) > 1})
    if dupes:
        out.append(Finding("5.6", FAIL, "a degree of freedom is constrained more than once",
                           ", ".join(dupes)))
    absent = [d for d in DOF if d not in seen]
    if absent:
        out.append(Finding("5.6", level, "the datum specification is under-constrained",
                           f"{', '.join(absent)} unconstrained. The named features must constrain "
                           "all six degrees of freedom, or the coordinate system is not determined "
                           "and every consumer resolves the remainder differently."))

    for name, value in (("gltfrp:forward", forward), ("gltfrp:up", up)):
        if value is None:
            out.append(Finding("5.6", level, f"{name} is not declared",
                               "nothing in a glTF file records a forward or up axis, so an "
                               "undeclared one cannot be checked at all"))
        elif value not in AXES:
            out.append(Finding("5.6", FAIL, f"{name} is {value!r}",
                               f"expected one of {', '.join(AXES)}"))
    if forward and up and forward in AXES and up in AXES and forward[1] == up[1]:
        out.append(Finding("5.6", FAIL, "forward and up are the same axis",
                           f"forward {forward}, up {up}"))

    if "realizedPose" in packet or "gltfrp:realizedPose" in packet:
        out.append(Finding("5.6", FAIL, "the manifest records a realized pose",
                           "a realized pose is derived by measurement, never authored; recording "
                           "it beside the rule that derives it creates two sources of truth"))
    return out or [Finding("5.6", PASS,
                           f"{len(features)} datum features constraining all six DOF, "
                           f"forward {forward}, up {up}")]


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
