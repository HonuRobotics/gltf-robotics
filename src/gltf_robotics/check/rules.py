"""The profile's mechanically decidable rules, one function each.

Every rule names the profile section it comes from, so a failure points at the
text that justifies it rather than at an opinion in this file. Sections the
profile marks Discuss or Open are reported as advisory: the profile says a
delivery cannot fail to conform on an unsettled point, and this must not
quietly harden one.

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
        out.append(Finding("4.3", FAIL, "asset.minVersion is present",
                           repr(asset["minVersion"])))
    return out or [Finding("4.3", PASS, "asset header is 2.0 with no minVersion")]


def rule_5_5_scenes_and_nodes(m):
    out = []
    scenes = m.get("scenes")
    if len(scenes) != 1:
        out.append(Finding("5.5", FAIL, f"{len(scenes)} scenes, expected exactly 1"))

    roots = m.root_nodes()
    if len(roots) != 1:
        names = ", ".join(repr(m.get("nodes")[i].get("name")) for i in roots[:8])
        out.append(Finding("5.5", FAIL, f"{len(roots)} root nodes, expected exactly 1", names))

    if scenes and len(scenes) == 1:
        listed = scenes[0].get("nodes", [])
        if sorted(listed) != sorted(roots):
            out.append(Finding("5.5", FAIL, "the scene does not list exactly the root node",
                               f"scene lists {listed}, roots are {roots}"))

    for i in roots:
        node = m.get("nodes")[i]
        if "matrix" in node:
            out.append(Finding("5.5", FAIL, "the root node carries a matrix transform",
                               "apply transforms in Blender before export"))
        elif "rotation" in node:
            rot = node["rotation"]
            if abs(rot[0]) > 1e-6 or abs(rot[1]) > 1e-6 or abs(rot[2]) > 1e-6:
                out.append(Finding("5.5", FAIL, "the root node carries a rotation",
                                   f"{rot}; this is the Blender Y-up conversion node, "
                                   "and the two consumers compose it differently"))
        name = node.get("name")
        if name is None:
            out.append(Finding("5.5", FAIL, "the root node is unnamed",
                               "Gazebo names each submesh after its node"))
        else:
            if re.search(r"\.\d{3}$", name):
                out.append(Finding("5.5", FAIL, "the root node has a Blender numeric suffix",
                                   repr(name)))
            elif " " in name:
                out.append(Finding("5.5", FAIL, "the root node name contains a space",
                                   repr(name)))
            elif name != m.part_name:
                out.append(Finding("5.5", WARN, "the root node is not named after the part",
                                   f"node {name!r}, file implies {m.part_name!r}"))
    return out or [Finding("5.5", PASS, "one scene, one named root node, no root transform")]


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
        out.append(Finding("6", FAIL, f"{len(non_triangles)} primitives are not triangles",
                           "; ".join(non_triangles[:5])))
    if missing:
        out.append(Finding("6", FAIL, f"{len(missing)} primitives lack a required attribute",
                           "; ".join(missing[:5])))
    return out or [Finding("6", PASS, "every primitive is triangles with POSITION, NORMAL, TEXCOORD_0")]


def rule_6_1_uv(m):
    out = []
    extra = sorted({a for _, _, p in m.primitives() for a in p.get("attributes", {})
                    if a.startswith("TEXCOORD_") and a != "TEXCOORD_0"})
    if extra:
        out.append(Finding("6.1", FAIL, "more than one UV set", ", ".join(extra)))

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
    return out or [Finding("6.1", PASS, "one UV set, inside [0, 1]")]


def rule_7_materials(m):
    out = []
    materials = m.get("materials")

    no_material = [f"mesh {mi} primitive {pi}" for mi, pi, p in m.primitives()
                   if "material" not in p]
    if no_material:
        out.append(Finding("7", FAIL, f"{len(no_material)} primitives have no material",
                           "; ".join(no_material[:5]) + " -- these render as white metal"))

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
            "7", FAIL, f"{len(metal_trap)} materials are metallic with nothing to override it",
            "; ".join(metal_trap[:6]) + ". glTF's metallicFactor defaults to 1.0, so a material "
            "that says nothing says metal. Plastics and painted surfaces must be non-metallic."))
    if metal_unverified:
        out.append(Finding(
            "7", WARN,
            f"{len(metal_unverified)} materials leave metallicFactor unset but carry an ORM map",
            "; ".join(metal_unverified[:6]) + ". The texture's blue channel multiplies against "
            "the factor, so a black metallic channel would still yield a non-metal. Settling it "
            "needs the decoded texel values, which this tool does not read. Do not assume it is "
            "fine: a solid white metallic channel is the usual export, and every map measured in "
            "this project's own library had B = 255, which makes the part fully metal. State the "
            "factor explicitly if the part is not metal."))
    if missing_base:
        out.append(Finding("7", FAIL, f"{len(missing_base)} textured materials have no baseColorTexture",
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
        out.append(Finding("8", FAIL, f"{len(oversize)} textures exceed 2048 px",
                           "; ".join(oversize[:5])))
    if undimensioned:
        out.append(Finding("8", WARN, f"{len(undimensioned)} images have unreadable dimensions",
                           "; ".join(undimensioned[:5]) + " -- the size rule could not be checked"))
    if linear_jpeg:
        out.append(Finding(
            "8", FAIL, f"{len(linear_jpeg)} linear maps are JPEG",
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
            ". A conforming reader must refuse a file requiring an extension it does not "
            "implement. What Gazebo actually does here is unverified -- see probe/."))

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


def rule_5_3_forward_axis(m):
    """Section 5.3 is an interim rule, and the profile has not decided it."""
    return Finding("5.3", ADVISORY, "forward axis is not decided",
                   "the profile's interim rule is to author in the part frame, yielding a file "
                   "facing +X. Nothing in a glTF file records a forward axis, so this cannot be "
                   "checked by reading it -- see probe/coords for the visual protocol.")


def rule_5_1_scale(m):
    """Section 5.1 requires meters. A file cannot state its own units."""
    return Finding("5.1", ADVISORY, "scale is not checkable from the file",
                   "glTF says meters and nothing in the file confirms it. Two assets in the "
                   "corpus are millimetre files corrected downstream. What would catch a wrong "
                   "scale is a cited dimensional figure per part, which is profile section 4.1's "
                   "open question.")


RULES = [
    rule_4_1_filename,
    rule_4_2_container,
    rule_4_3_asset_header,
    rule_5_1_scale,
    rule_5_3_forward_axis,
    rule_5_5_scenes_and_nodes,
    rule_6_geometry,
    rule_6_1_uv,
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
