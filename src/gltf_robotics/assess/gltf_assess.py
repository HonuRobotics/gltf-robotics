#!/usr/bin/env python3
"""Assess glTF assets from a list, without downloading them whole.

The point of this tool is bottom-up evidence for `model-spec.md`: that document
is a top-down statement of what a delivered model must be, and this is the other
half, a look at what glTF assets in the wild actually are. It reads a hand-edited
list of examples (`examples.yaml`), measures each one against the criteria in
`criteria.md`, and writes one report plus a corpus summary.

It is built around HTTP range requests, because the assets worth looking at are
large and almost nothing we want to know lives in the geometry. A `.glb` states
its JSON chunk length in bytes 12 to 16, so twenty bytes and then one more range
request yields the whole structure of the file -- nodes, meshes, materials,
extensions, triangle counts, texture slots and MIME types. Image dimensions come
from a further few kilobytes per image, read out of the PNG or JPEG header. Only
the measurements that genuinely need vertex data (UV range, texel density,
degenerate triangles) fetch any geometry, and those are skipped when the span
they need exceeds the per-asset byte budget. A 429 MB model costs about 100 KB
to assess.

    gltf_assess.py                     # assess everything, refresh ASSESSMENT.md
    gltf_assess.py --only fuel/        # just the ids with this prefix
    gltf_assess.py --refresh           # ignore the cache
    gltf_assess.py --json out.json     # the raw measurements

Every measurement is cached under `cache/`, keyed by source URI and by the
source's own length, so a re-run after adding an example measures only the new
one. That is what makes the list incremental, and what would make it cheap to
run from CI.
"""

import argparse
import fnmatch
import hashlib
import io
import json
import math
import os
import pathlib
import re
import struct
import subprocess
import sys
import time
import urllib.error
import urllib.parse
import urllib.request

import yaml

HERE = pathlib.Path(__file__).resolve().parent


def default_registry():
    """The repository's corpus, found by searching upward from this module.

    The tool installs as a package while its corpus -- criteria, registry,
    visual notes -- stays hand-edited in `assess/` at the repository root, so
    the two are no longer siblings. Returns None for an installed copy with no
    checkout around it, where --registry must be given explicitly.
    """
    for parent in [HERE, *HERE.parents]:
        candidate = parent / "assess" / "examples.yaml"
        if candidate.is_file():
            return candidate
    return None


# Set from the registry path in main(), so the report can read the files that
# live beside it without every function taking a root argument.
ROOT_HINT = [HERE]
USER_AGENT = "honu-gltf-assess/0.1 (+https://github.com/HonuRobotics/gltf-robotics)"
TIMEOUT = 60

GLB_MAGIC = b"glTF"
CHUNK_JSON = 0x4E4F534A
CHUNK_BIN = 0x004E4942

COMPONENT_SIZES = {5120: 1, 5121: 1, 5122: 2, 5123: 2, 5125: 4, 5126: 4}
COMPONENT_NAMES = {
    5120: "int8", 5121: "uint8", 5122: "int16",
    5123: "uint16", 5125: "uint32", 5126: "float32",
}
TYPE_COUNTS = {"SCALAR": 1, "VEC2": 2, "VEC3": 3, "VEC4": 4, "MAT2": 4, "MAT3": 9, "MAT4": 16}
PRIMITIVE_MODES = {
    0: "POINTS", 1: "LINES", 2: "LINE_LOOP", 3: "LINE_STRIP",
    4: "TRIANGLES", 5: "TRIANGLE_STRIP", 6: "TRIANGLE_FAN",
}

# The five texture slots glTF defines on a material, in the order a reviewer
# reads them. Matches glb_inventory.py so the two tools can be compared.
MAP_SLOTS = ("baseColor", "normal", "metallicRoughness", "occlusion", "emissive")

# How many primitives to read UVs from when they are too scattered to fetch in
# one go. One range request each, so this is a request budget as much as a byte
# one.
UV_SAMPLE = 48

# Below this, a file is fetched whole rather than in ranges: a dozen image
# headers and a UV window over a small file cost more requests, and sometimes
# more bytes, than the file itself. Above it, ranges are the whole point.
WHOLE_FILE_MAX = 2 << 20

# Image formats that reach the GPU in this project's consumers. Anything else
# loads as nothing at all -- see model-spec.md section 8.
LOADABLE_MIME = {"image/png", "image/jpeg"}

BLENDER_SUFFIX = re.compile(r"\.\d{3}$")
# Names an exporter invented rather than a modeler chose. A file full of these
# cannot be addressed by SDF <submesh> even where the mechanism works.
GENERIC_NAME = re.compile(
    r"^(mesh|node|object|cube|sphere|cylinder|cone|torus|plane|circle|line|curve|"
    r"bezier|empty|group|polysurface|solid|part|component|default)[._\- ]?\d*$",
    re.IGNORECASE,
)


# ---------------------------------------------------------------- fetching


class FetchError(Exception):
    pass


class Source:
    """A byte range reader over one asset, local or remote.

    Local files are read from disk; remote ones use HTTP range requests, and
    every range actually fetched is counted so the report can say what an
    assessment cost. `total` is the file length, which for a remote file comes
    from the Content-Range header of the first request rather than a HEAD, to
    keep it to one round trip.
    """

    def __init__(self, uri):
        self.uri = uri
        self.remote = uri.startswith(("http://", "https://"))
        self.fetched = 0
        self.requests = 0
        self._local = None
        self.total = None
        if not self.remote:
            path = pathlib.Path(uri).expanduser()
            self._local = path.read_bytes()
            self.total = len(self._local)

    def read(self, offset, length):
        if length <= 0:
            return b""
        if self._local is not None:
            return self._local[offset:offset + length]
        end = offset + length - 1
        req = urllib.request.Request(
            self.uri, headers={"Range": f"bytes={offset}-{end}", "User-Agent": USER_AGENT}
        )
        try:
            with urllib.request.urlopen(req, timeout=TIMEOUT) as resp:
                data = resp.read()
                self.requests += 1
                self.fetched += len(data)
                if self.total is None:
                    rng = resp.headers.get("Content-Range", "")
                    if "/" in rng:
                        self.total = int(rng.rsplit("/", 1)[1])
                    elif resp.status == 200:
                        # A server that ignored the range handed us everything.
                        self.total = len(data)
                        self._local = data
                        return data[offset:offset + length]
                return data
        except urllib.error.HTTPError as exc:
            raise FetchError(f"{exc.code} {exc.reason} on range {offset}-{end}") from exc
        except OSError as exc:
            raise FetchError(str(exc)) from exc

    def read_all(self):
        if self._local is not None:
            return self._local
        req = urllib.request.Request(self.uri, headers={"User-Agent": USER_AGENT})
        try:
            with urllib.request.urlopen(req, timeout=TIMEOUT) as resp:
                data = resp.read()
        except urllib.error.HTTPError as exc:
            raise FetchError(f"{exc.code} {exc.reason}") from exc
        except OSError as exc:
            raise FetchError(str(exc)) from exc
        self.requests += 1
        self.fetched += len(data)
        self.total = len(data)
        self._local = data
        return data


def fetch_text(url):
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(req, timeout=TIMEOUT) as resp:
        return resp.read()


# ---------------------------------------------------------------- parsing


def load_structure(source):
    """Return (gltf_json, bin_offset, bin_length) reading as little as possible.

    For a `.glb` that is two range requests and no geometry. For a `.gltf` the
    JSON is the whole file, so it is read in full; its buffers are separate
    resources handled by the resolver.
    """
    head = source.read(0, 20)
    if head[:4] == GLB_MAGIC:
        magic, version, _length = struct.unpack_from("<4sII", head, 0)
        if version != 2:
            raise FetchError(f"glTF container version {version}, expected 2")
        json_len, json_type = struct.unpack_from("<II", head, 12)
        if json_type != CHUNK_JSON:
            raise FetchError("first chunk of the container is not JSON")
        gltf = json.loads(source.read(20, json_len))
        bin_offset, bin_length = None, 0
        # The BIN chunk, if there is one, follows the JSON chunk's 4-byte pad.
        after = 12 + 8 + json_len + (-json_len % 4)
        if source.total is None or after + 8 <= source.total:
            header = source.read(after, 8)
            if len(header) == 8:
                chunk_len, chunk_type = struct.unpack("<II", header)
                if chunk_type == CHUNK_BIN:
                    bin_offset, bin_length = after + 8, chunk_len
        return gltf, bin_offset, bin_length
    raw = source.read_all()
    # A repository that stores its large assets in Git LFS serves a text pointer
    # from the raw endpoint, which is a fetching problem rather than a bad file.
    if raw[:40].startswith(b"version https://git-lfs"):
        size = next((line.split(b" ")[1] for line in raw.splitlines()
                     if line.startswith(b"size ")), b"?").decode()
        raise FetchError(
            f"Git LFS pointer, not the asset: {size} bytes are stored in LFS and the raw "
            "endpoint does not serve them"
        )
    return json.loads(raw), None, 0


class Resolver:
    """Reads bufferView bytes, wherever the buffer happens to live.

    A GLB keeps buffer 0 in its own BIN chunk, so a read is a range on the file
    itself. A `.gltf` keeps it in a side file named by a relative URI, and an
    image may be an external file too; both are resolved against the asset's own
    URI and fetched on demand. Missing side files are recorded rather than
    raised, because a delivery that references a file it did not ship is exactly
    the kind of finding this tool exists to report.
    """

    def __init__(self, gltf, source, bin_offset, budget):
        self.gltf = gltf
        self.source = source
        self.bin_offset = bin_offset
        self.budget = budget
        self.external = {}
        self.missing = []
        self.views = {}
        self.window = None

    def _resource(self, uri):
        if uri in self.external:
            return self.external[uri]
        if uri.startswith("data:"):
            import base64
            payload = uri.split(",", 1)[1]
            data = base64.b64decode(payload)
            self.external[uri] = data
            return data
        base = self.source.uri
        if self.source.remote:
            target = urllib.parse.urljoin(base, uri)
        else:
            target = str(pathlib.Path(base).parent / urllib.parse.unquote(uri))
        try:
            data = Source(target).read_all() if self.source.remote else pathlib.Path(target).read_bytes()
        except (FetchError, OSError) as exc:
            self.missing.append({"uri": uri, "resolved": target, "error": str(exc)})
            self.external[uri] = None
            return None
        self.source.fetched += len(data)
        self.source.requests += 1
        self.external[uri] = data
        return data

    def view_bytes(self, view_index, limit=None):
        """Bytes of one bufferView, or None if they are unreachable.

        Cached: primitives routinely share a bufferView, and each fetch of one
        is a range request over the network.
        """
        key = (view_index, limit)
        if key in self.views:
            return self.views[key]
        data = self._view_bytes(view_index, limit)
        self.views[key] = data
        return data

    def prefetch(self, view_indices):
        """Pull one contiguous span covering several bufferViews, in one request.

        A mesh split over three thousand nodes has its UVs in as many
        bufferViews, and fetching them one at a time is thousands of range
        requests for a couple of megabytes. They lie consecutively in the
        buffer, so one read of the span they occupy is the same bytes at one
        request. Returns False, and the caller falls back to reading them one by
        one, when the span is larger than the budget or the views are not all in
        the BIN chunk.
        """
        views = [self.gltf["bufferViews"][i] for i in view_indices]
        if not views or self.bin_offset is None:
            return False
        if any("uri" in self.gltf["buffers"][v["buffer"]] for v in views):
            return False
        start = min(v.get("byteOffset", 0) for v in views)
        end = max(v.get("byteOffset", 0) + v["byteLength"] for v in views)
        if end - start > self.budget:
            return False
        self.window = (start, self.source.read(self.bin_offset + start, end - start))
        return True

    def _view_bytes(self, view_index, limit=None):
        view = self.gltf["bufferViews"][view_index]
        buffer = self.gltf["buffers"][view["buffer"]]
        offset = view.get("byteOffset", 0)
        length = view["byteLength"] if limit is None else min(limit, view["byteLength"])
        if "uri" in buffer:
            data = self._resource(buffer["uri"])
            return None if data is None else data[offset:offset + length]
        if self.bin_offset is None:
            return None
        if self.window is not None:
            base, blob = self.window
            if base <= offset and offset + length <= base + len(blob):
                return blob[offset - base:offset - base + length]
        return self.source.read(self.bin_offset + offset, length)


def accessor_span(gltf, index):
    """(bufferView, start, length) of the bytes one accessor occupies."""
    acc = gltf["accessors"][index]
    if "bufferView" not in acc:
        return None
    view = gltf["bufferViews"][acc["bufferView"]]
    comps = TYPE_COUNTS[acc["type"]]
    size = COMPONENT_SIZES[acc["componentType"]] * comps
    stride = view.get("byteStride") or size
    start = acc.get("byteOffset", 0)
    return acc["bufferView"], start, (acc["count"] - 1) * stride + size


def read_accessor(gltf, resolver, index):
    """Accessor `index` as a list of tuples, or None if the bytes are missing."""
    import array
    acc = gltf["accessors"][index]
    comps = TYPE_COUNTS[acc["type"]]
    count = acc["count"]
    if "bufferView" not in acc:
        # No bytes behind it: zeros by the specification, unless an extension
        # such as Draco supplies the data, which the caller filters out first.
        return [(0,) * comps] * count
    view = gltf["bufferViews"][acc["bufferView"]]
    raw = resolver.view_bytes(acc["bufferView"])
    if raw is None:
        return None
    item = COMPONENT_SIZES[acc["componentType"]]
    size = item * comps
    stride = view.get("byteStride") or size
    start = acc.get("byteOffset", 0)
    typecode = {5120: "b", 5121: "B", 5122: "h", 5123: "H", 5125: "I", 5126: "f"}[
        acc["componentType"]
    ]
    if stride == size:
        flat = array.array(typecode)
        block = raw[start:start + count * size]
        if len(block) < count * size:
            return None
        flat.frombytes(block)
        return [tuple(flat[i * comps:(i + 1) * comps]) for i in range(count)]
    out = []
    for i in range(count):
        chunk = raw[start + i * stride:start + i * stride + size]
        if len(chunk) < size:
            return None
        values = array.array(typecode)
        values.frombytes(chunk)
        out.append(tuple(values))
    return out


def sniff_image(data):
    """(mime, width, height) from the first bytes of a PNG, JPEG, WebP or KTX2."""
    if data[:8] == b"\x89PNG\r\n\x1a\n" and data[12:16] == b"IHDR":
        w, h = struct.unpack_from(">II", data, 16)
        return "image/png", w, h
    if data[:2] == b"\xff\xd8":
        i = 2
        while i + 9 < len(data):
            if data[i] != 0xFF:
                i += 1
                continue
            marker = data[i + 1]
            if marker in (0xD8, 0x01) or 0xD0 <= marker <= 0xD7:
                i += 2
                continue
            seglen = struct.unpack_from(">H", data, i + 2)[0]
            if marker in (0xC0, 0xC1, 0xC2, 0xC3, 0xC5, 0xC6, 0xC7,
                          0xC9, 0xCA, 0xCB, 0xCD, 0xCE, 0xCF):
                h, w = struct.unpack_from(">HH", data, i + 5)
                return "image/jpeg", w, h
            i += 2 + seglen
        return "image/jpeg", None, None
    if data[:4] == b"RIFF" and data[8:12] == b"WEBP":
        return "image/webp", None, None
    if data[:12] == b"\xabKTX 20\xbb\r\n\x1a\n":
        w, h = struct.unpack_from("<II", data, 20)
        return "image/ktx2", w, h
    if data[:4] == b"DDS ":
        return "image/dds", None, None
    return None, None, None


# ---------------------------------------------------------------- measuring


def node_scale(node):
    """The uniform scale a node's own transform applies, if it applies one."""
    if "matrix" in node:
        m = node["matrix"]
        cols = [math.sqrt(m[i] ** 2 + m[i + 1] ** 2 + m[i + 2] ** 2) for i in (0, 4, 8)]
        return cols
    return list(node.get("scale", [1.0, 1.0, 1.0]))


def node_matrix(node):
    if "matrix" in node:
        m = node["matrix"]
        return [[m[0], m[4], m[8], m[12]],
                [m[1], m[5], m[9], m[13]],
                [m[2], m[6], m[10], m[14]],
                [m[3], m[7], m[11], m[15]]]
    out = [[1.0, 0, 0, 0], [0, 1.0, 0, 0], [0, 0, 1.0, 0], [0, 0, 0, 1.0]]
    if "rotation" in node:
        x, y, z, w = node["rotation"]
        r = [[1 - 2 * (y * y + z * z), 2 * (x * y - z * w), 2 * (x * z + y * w)],
             [2 * (x * y + z * w), 1 - 2 * (x * x + z * z), 2 * (y * z - x * w)],
             [2 * (x * z - y * w), 2 * (y * z + x * w), 1 - 2 * (x * x + y * y)]]
        for i in range(3):
            for j in range(3):
                out[i][j] = r[i][j]
    s = node.get("scale", [1, 1, 1])
    for i in range(3):
        for j in range(3):
            out[i][j] *= s[j]
    t = node.get("translation", [0, 0, 0])
    for i in range(3):
        out[i][3] = t[i]
    return out


def mat_mul(a, b):
    return [[sum(a[i][k] * b[k][j] for k in range(4)) for j in range(4)] for i in range(4)]


def transform_bounds(matrix, lo, hi):
    """World-space AABB of a local AABB under a 4x4 -- all eight corners."""
    out_lo = [float("inf")] * 3
    out_hi = [float("-inf")] * 3
    for cx in (lo[0], hi[0]):
        for cy in (lo[1], hi[1]):
            for cz in (lo[2], hi[2]):
                for i in range(3):
                    v = (matrix[i][0] * cx + matrix[i][1] * cy
                         + matrix[i][2] * cz + matrix[i][3])
                    out_lo[i] = min(out_lo[i], v)
                    out_hi[i] = max(out_hi[i], v)
    return out_lo, out_hi


def material_maps(gltf, index):
    """Every texture slot a material fills, as slot -> {image, uv, texture}."""
    material = gltf.get("materials", [])[index]
    pbr = material.get("pbrMetallicRoughness", {})
    slots = {
        "baseColor": pbr.get("baseColorTexture"),
        "metallicRoughness": pbr.get("metallicRoughnessTexture"),
        "normal": material.get("normalTexture"),
        "occlusion": material.get("occlusionTexture"),
        "emissive": material.get("emissiveTexture"),
    }
    out = {}
    for slot, info in slots.items():
        if info is None:
            continue
        texture = gltf.get("textures", [])[info["index"]]
        source = texture.get("source")
        if source is None:
            # KHR_texture_basisu and friends put the image somewhere else.
            for ext in texture.get("extensions", {}).values():
                if isinstance(ext, dict) and "source" in ext:
                    source = ext["source"]
        out[slot] = {
            "image": source,
            "uv": info.get("texCoord", 0),
            "transform": "KHR_texture_transform" in info.get("extensions", {}),
        }
    return out


def measure(entry, uri, budget_bytes):
    """Every measurement this tool makes about one asset, as a dict."""
    source = Source(uri)
    gltf, bin_offset, bin_length = load_structure(source)
    if source.total is not None and source.total <= WHOLE_FILE_MAX:
        source.read_all()
    resolver = Resolver(gltf, source, bin_offset, budget_bytes)

    nodes = gltf.get("nodes", [])
    meshes = gltf.get("meshes", [])
    materials = gltf.get("materials", [])
    images = gltf.get("images", [])
    asset = gltf.get("asset", {})

    m = {
        "id": entry["id"],
        "uri": uri,
        "measured": time.strftime("%Y-%m-%d"),
        "container": "glb" if bin_offset is not None or uri.endswith(".glb") else "gltf",
        "file_bytes": source.total,
        "generator": asset.get("generator", ""),
        "version": asset.get("version", ""),
        "min_version": asset.get("minVersion"),
        "copyright": asset.get("copyright", ""),
        "extensions_used": sorted(gltf.get("extensionsUsed", [])),
        "extensions_required": sorted(gltf.get("extensionsRequired", [])),
        "counts": {
            "scenes": len(gltf.get("scenes", [])),
            "nodes": len(nodes),
            "meshes": len(meshes),
            "materials": len(materials),
            "textures": len(gltf.get("textures", [])),
            "images": len(images),
            "samplers": len(gltf.get("samplers", [])),
            "cameras": len(gltf.get("cameras", [])),
            "animations": len(gltf.get("animations", [])),
            "skins": len(gltf.get("skins", [])),
            "buffers": len(gltf.get("buffers", [])),
        },
    }

    # --- scene and node structure
    scene_index = gltf.get("scene")
    roots = []
    if scene_index is not None and gltf.get("scenes"):
        roots = gltf["scenes"][scene_index].get("nodes", [])
    elif gltf.get("scenes"):
        roots = gltf["scenes"][0].get("nodes", [])
    m["default_scene"] = scene_index
    m["root_nodes"] = [nodes[i].get("name", "") for i in roots if i < len(nodes)]
    m["root_transforms"] = [
        {
            "name": nodes[i].get("name", ""),
            "rotation": "rotation" in nodes[i] or "matrix" in nodes[i],
            "translation": nodes[i].get("translation"),
            "scale": node_scale(nodes[i]),
        }
        for i in roots if i < len(nodes)
    ]

    names = [n.get("name", "") for n in nodes]
    seen = {}
    for name in names:
        if name:
            seen[name] = seen.get(name, 0) + 1
    m["duplicate_node_names"] = sorted(
        [n for n, c in seen.items() if c > 1], key=lambda n: -seen[n]
    )[:10]
    m["duplicate_node_name_count"] = sum(1 for c in seen.values() if c > 1)
    m["unnamed_nodes"] = sum(1 for n in names if not n)
    m["blender_suffix_nodes"] = sum(1 for n in names if BLENDER_SUFFIX.search(n))
    m["generic_nodes"] = sum(1 for n in names if GENERIC_NAME.match(n))
    m["node_names_sample"] = [n for n in names if n][:8]

    depth = {}

    def walk_depth(index, d, chain):
        if index in chain:
            return
        depth[index] = max(depth.get(index, 0), d)
        for child in nodes[index].get("children", []):
            walk_depth(child, d + 1, chain | {index})

    for root in roots:
        if root < len(nodes):
            walk_depth(root, 1, frozenset())
    m["max_node_depth"] = max(depth.values(), default=0)

    # A node may instance the same mesh many times; Gazebo emits one submesh per
    # primitive per instantiating node, so this is what the loader will build.
    instances = []

    def walk_mesh(index, parent, chain):
        if index in chain or index >= len(nodes):
            return
        node = nodes[index]
        world = mat_mul(parent, node_matrix(node))
        if "mesh" in node:
            instances.append((index, node["mesh"], world))
        for child in node.get("children", []):
            walk_mesh(child, world, chain | {index})

    identity = [[1.0 if i == j else 0.0 for j in range(4)] for i in range(4)]
    for root in roots:
        walk_mesh(root, identity, frozenset())
    m["mesh_instances"] = len(instances)
    m["orphan_meshes"] = len(meshes) - len({mi for _, mi, _ in instances})

    # --- geometry, from accessor metadata alone
    prims = []
    lo = [float("inf")] * 3
    hi = [float("-inf")] * 3
    for node_index, mesh_index, world in instances:
        for prim in meshes[mesh_index].get("primitives", []):
            attrs = prim.get("attributes", {})
            mode = prim.get("mode", 4)
            tris = None
            if "indices" in prim:
                count = gltf["accessors"][prim["indices"]]["count"]
                index_type = COMPONENT_NAMES[
                    gltf["accessors"][prim["indices"]]["componentType"]
                ]
            elif "POSITION" in attrs:
                count = gltf["accessors"][attrs["POSITION"]]["count"]
                index_type = "none"
            else:
                count, index_type = 0, "none"
            if mode == 4:
                tris = count // 3
            elif mode in (5, 6):
                tris = max(count - 2, 0)
            verts = (
                gltf["accessors"][attrs["POSITION"]]["count"] if "POSITION" in attrs else 0
            )
            pos_acc = gltf["accessors"][attrs["POSITION"]] if "POSITION" in attrs else {}
            if "min" in pos_acc and "max" in pos_acc:
                plo, phi = transform_bounds(world, pos_acc["min"], pos_acc["max"])
                lo = [min(a, b) for a, b in zip(lo, plo)]
                hi = [max(a, b) for a, b in zip(hi, phi)]
            prims.append({
                "node": nodes[node_index].get("name", ""),
                "mode": PRIMITIVE_MODES.get(mode, str(mode)),
                "triangles": tris,
                "vertices": verts,
                "index_type": index_type,
                "attributes": sorted(attrs),
                "material": prim.get("material"),
                "draco": "KHR_draco_mesh_compression" in prim.get("extensions", {}),
                "accessors": attrs,
                "indices": prim.get("indices"),
            })
    m["primitives"] = len(prims)
    m["triangles"] = sum(p["triangles"] or 0 for p in prims)
    m["vertices"] = sum(p["vertices"] for p in prims)
    m["modes"] = sorted({p["mode"] for p in prims})
    m["index_types"] = sorted({p["index_type"] for p in prims})
    m["attribute_sets"] = sorted({", ".join(p["attributes"]) for p in prims})
    m["has_tangent"] = sum(1 for p in prims if "TANGENT" in p["attributes"])
    m["has_color"] = sum(1 for p in prims if any(a.startswith("COLOR_") for a in p["attributes"]))
    m["uv_sets"] = max(
        (sum(1 for a in p["attributes"] if a.startswith("TEXCOORD_")) for p in prims),
        default=0,
    )
    m["prims_without_normal"] = sum(1 for p in prims if "NORMAL" not in p["attributes"])
    m["prims_without_uv"] = sum(1 for p in prims if "TEXCOORD_0" not in p["attributes"])
    m["prims_without_material"] = sum(1 for p in prims if p["material"] is None)
    m["draco_primitives"] = sum(1 for p in prims if p["draco"])
    m["extent_m"] = (
        [round(h - l, 4) for l, h in zip(lo, hi)] if hi[0] > float("-inf") else None
    )
    m["origin_offset_m"] = (
        [round((l + h) / 2, 4) for l, h in zip(lo, hi)] if hi[0] > float("-inf") else None
    )
    m["bbox_min_m"] = [round(v, 4) for v in lo] if hi[0] > float("-inf") else None
    m["bbox_max_m"] = [round(v, 4) for v in hi] if hi[0] > float("-inf") else None
    # Where the file's zero sits inside its own bounding box, per axis, as a
    # fraction: 0 is the low face, 1 the high face, 0.5 the middle. This is the
    # measurable half of the origin question in spec 5.4 -- it says the origin is
    # centered in two axes and on a face in the third, but not which face that
    # is in the part's own terms. A person in front of the rig says that.
    m["origin_fraction"] = (
        [
            round((0.0 - l) / (h - l), 4) if h - l > 1e-9 else None
            for l, h in zip(lo, hi)
        ]
        if hi[0] > float("-inf") else None
    )

    # Submeshes as gz-common would name them: one per primitive, carrying the
    # name of the node that instantiated it, never the mesh or material name.
    submesh_names = [p["node"] for p in prims]
    counts = {}
    for name in submesh_names:
        counts[name] = counts.get(name, 0) + 1
    m["ambiguous_submeshes"] = sum(c for c in counts.values() if c > 1)
    m["distinct_submesh_names"] = len(counts)

    # --- materials
    mat = {
        "metallic_trap": [], "specular_glossiness": 0, "double_sided": 0,
        "alpha_modes": {}, "textured_without_basecolor": [], "factor_only": 0,
        "normal_scale_not_1": 0, "occlusion_strength_not_1": 0,
        "basecolor_alpha_lt_1": 0, "unlit": 0, "names": [],
    }
    used_materials = sorted({p["material"] for p in prims if p["material"] is not None})
    for i, material in enumerate(materials):
        pbr = material.get("pbrMetallicRoughness", {})
        maps = material_maps(gltf, i)
        name = material.get("name", "")
        mat["names"].append(name)
        mode = material.get("alphaMode", "OPAQUE")
        mat["alpha_modes"][mode] = mat["alpha_modes"].get(mode, 0) + 1
        if material.get("doubleSided"):
            mat["double_sided"] += 1
        exts = material.get("extensions", {})
        if "KHR_materials_pbrSpecularGlossiness" in exts:
            mat["specular_glossiness"] += 1
        if "KHR_materials_unlit" in exts:
            mat["unlit"] += 1
        metallic = pbr.get("metallicFactor", 1.0)
        if metallic > 0.0 and "metallicRoughness" not in maps:
            mat["metallic_trap"].append({
                "index": i, "name": name, "factor": metallic,
                "declared": "metallicFactor" in pbr,
            })
        if maps and "baseColor" not in maps:
            mat["textured_without_basecolor"].append({
                "index": i, "name": name, "slots": sorted(maps),
            })
        if not maps:
            mat["factor_only"] += 1
        if material.get("normalTexture", {}).get("scale", 1.0) != 1.0:
            mat["normal_scale_not_1"] += 1
        if material.get("occlusionTexture", {}).get("strength", 1.0) != 1.0:
            mat["occlusion_strength_not_1"] += 1
        if pbr.get("baseColorFactor", [1, 1, 1, 1])[3] < 1.0:
            mat["basecolor_alpha_lt_1"] += 1
    mat["unused"] = len(materials) - len(used_materials)
    m["materials"] = mat

    # --- images: MIME and pixel size from the first bytes of each one
    image_records = []
    for i, image in enumerate(images):
        record = {"index": i, "name": image.get("name", ""), "declared_mime": image.get("mimeType"),
                  "external": "uri" in image and not image["uri"].startswith("data:")}
        data = None
        if "bufferView" in image:
            view = gltf["bufferViews"][image["bufferView"]]
            record["bytes"] = view["byteLength"]
            data = resolver.view_bytes(image["bufferView"], limit=min(65536, view["byteLength"]))
        elif "uri" in image:
            record["uri"] = image["uri"]
            data = resolver._resource(image["uri"])
            if data is not None:
                record["bytes"] = len(data)
        if data:
            mime, width, height = sniff_image(data[:65536])
            record.update({"mime": mime, "width": width, "height": height})
        else:
            record.update({"mime": image.get("mimeType"), "width": None, "height": None,
                           "unreadable": True})
        image_records.append(record)
    m["images"] = image_records
    m["texture_bytes"] = sum(r.get("bytes", 0) for r in image_records)
    m["decoded_bytes"] = sum(
        (r.get("width") or 0) * (r.get("height") or 0) * 4 for r in image_records
    )
    m["missing_resources"] = resolver.missing

    # Which slot each image serves, and the format in each slot.
    roles = {}
    slot_mimes = {slot: {} for slot in MAP_SLOTS}
    slot_sizes = {slot: set() for slot in MAP_SLOTS}
    texture_transform_used = False
    for p in prims:
        if p["material"] is None:
            continue
        for slot, ref in material_maps(gltf, p["material"]).items():
            texture_transform_used |= ref["transform"]
            idx = ref["image"]
            if idx is None or idx >= len(image_records):
                continue
            roles.setdefault(idx, slot)
            rec = image_records[idx]
            mime = rec.get("mime") or "unknown"
            slot_mimes[slot].setdefault(mime, set()).add(idx)
            if rec.get("width"):
                slot_sizes[slot].add((rec["width"], rec["height"]))
    for idx, rec in enumerate(image_records):
        rec["role"] = roles.get(idx, "unused")
    m["slot_mimes"] = {
        slot: {mime: len(idxs) for mime, idxs in mimes.items()}
        for slot, mimes in slot_mimes.items() if mimes
    }
    m["slot_sizes"] = {k: sorted(v) for k, v in slot_sizes.items() if v}
    m["texture_transform_on_slot"] = texture_transform_used
    m["max_texture_px"] = max(
        ((r.get("width") or 0, r.get("height") or 0) for r in image_records),
        default=(0, 0),
    )

    # --- UV range, the one measurement that needs vertex data
    #
    # Two things make this expensive on a large asset. The bytes themselves are
    # bounded by the budget, but they are also scattered: the warehouse model
    # holds its UVs in three thousand bufferViews spread over an 83 MB buffer,
    # so one request each is three thousand requests and one request for the
    # span is the whole file. Where they are packed closely enough, one read
    # covers them all; where they are not, the largest primitives are sampled
    # and the report says so. A sampled range is a lower bound on the real one,
    # which is the right direction: it can show a violation but never hide one.
    # A Draco primitive's accessors carry no bufferView, because the vertex data
    # lives inside the extension. Reading one yields zeros, which would be
    # reported as a UV range of 0 to 0 rather than as an unanswered question.
    with_uv = [p for p in prims if "TEXCOORD_0" in p["accessors"] and not p["draco"]]
    draco_uv = [p for p in prims if "TEXCOORD_0" in p["accessors"] and p["draco"]]
    spans = [accessor_span(gltf, p["accessors"]["TEXCOORD_0"]) for p in with_uv]
    spans = [s for s in spans if s]
    m["uv_range"] = None
    m["uv_range_note"] = None
    if not with_uv:
        m["uv_range_note"] = (
            "not measured: the geometry is Draco-compressed" if draco_uv else "no UVs"
        )
    else:
        needed = sum(s[2] for s in spans)
        sample = with_uv
        if needed > budget_bytes or not resolver.prefetch(sorted({s[0] for s in spans})):
            if len(with_uv) > UV_SAMPLE:
                sample = sorted(with_uv, key=lambda p: -p["vertices"])[:UV_SAMPLE]
                m["uv_range_note"] = f"sampled: the {len(sample)} largest of {len(with_uv)} primitives"
            elif needed > budget_bytes:
                sample = []
                m["uv_range_note"] = "not measured: over the byte budget"
        umin = vmin = float("inf")
        umax = vmax = float("-inf")
        for p in sample:
            uv = read_accessor(gltf, resolver, p["accessors"]["TEXCOORD_0"])
            if uv is None:
                m["uv_range_note"] = "not measured: vertex data unreachable"
                umax = float("-inf")
                break
            for u, v in uv:
                umin, umax = min(umin, u), max(umax, u)
                vmin, vmax = min(vmin, v), max(vmax, v)
        if umax > float("-inf"):
            m["uv_range"] = [round(umin, 3), round(umax, 3), round(vmin, 3), round(vmax, 3)]

    # --- samplers, which is how tiling outside [0,1] is declared
    wraps = {}
    for sampler in gltf.get("samplers", []):
        for key in ("wrapS", "wrapT"):
            mode = {33071: "CLAMP", 33648: "MIRROR", 10497: "REPEAT"}.get(
                sampler.get(key, 10497), str(sampler.get(key))
            )
            wraps[mode] = wraps.get(mode, 0) + 1
    m["sampler_wraps"] = wraps

    m["fetched_bytes"] = source.fetched
    m["requests"] = source.requests
    return m


# ---------------------------------------------------------------- checks

# Each check names the criterion it answers in criteria.md. These are not a pass
# or fail grade on someone else's asset -- they record where an example diverges
# from what model-spec.md requires of ours, which is the whole reason for
# looking at it.
def plural(n, word, suffix="s"):
    return f"{n} {word}" if n == 1 else f"{n} {word}{suffix}"


def observations(m):
    out = []

    def flag(criterion, level, text):
        out.append({"criterion": criterion, "level": level, "text": text})

    if m["container"] != "glb":
        flag("B1", "diverges", "delivered as .gltf with side files, not a self-contained .glb")
    if m["missing_resources"]:
        flag("B2", "broken", plural(len(m["missing_resources"]), "referenced file") + " do not resolve: "
             + ", ".join(r["uri"] for r in m["missing_resources"][:3]))
    if any(r.get("external") for r in m["images"]):
        n = sum(1 for r in m["images"] if r.get("external"))
        flag("B3", "diverges", plural(n, "image") + " are external files rather than embedded")
    if m["min_version"]:
        flag("A2", "diverges", f"asset.minVersion is set to {m['min_version']}")
    if not m["generator"]:
        flag("A3", "note", "no asset.generator, so the authoring tool is unrecorded")

    if m["extensions_required"]:
        flag("H1", "broken", "extensionsRequired is non-empty: "
             + ", ".join(m["extensions_required"]))
    if m["draco_primitives"]:
        flag("H2", "diverges",
             "Draco compression on " + plural(m["draco_primitives"], "primitive"))
    if m["texture_transform_on_slot"]:
        flag("H3", "diverges", "KHR_texture_transform is applied to a texture slot; "
             "Gazebo parses and ignores it, so those textures land in the wrong place")

    if m["counts"]["animations"]:
        flag("I1", "diverges", plural(m["counts"]["animations"], "animation"))
    if m["counts"]["skins"]:
        flag("I1", "diverges", plural(m["counts"]["skins"], "skin"))
    if m["counts"]["cameras"]:
        flag("I1", "note", plural(m["counts"]["cameras"], "camera"))

    if m["counts"]["scenes"] > 1:
        flag("C1", "diverges", f"{m['counts']['scenes']} scenes; a viewer picks one")
    if len(m["root_nodes"]) > 1:
        flag("C2", "diverges", f"{len(m['root_nodes'])} root nodes in the default scene")
    for root in m["root_transforms"]:
        if root["rotation"]:
            flag("C3", "diverges", f"root node '{root['name']}' carries a rotation or matrix")
        if any(abs(s - 1.0) > 1e-6 for s in root["scale"]):
            flag("C4", "diverges", f"root node '{root['name']}' carries a scale of "
                 + " x ".join(f"{s:g}" for s in root["scale"])
                 + ", so scale is in the transform rather than the mesh data")
    if m["ambiguous_submeshes"]:
        flag("C6", "note", f"{m['ambiguous_submeshes']} primitives share a node name, so an SDF "
             "`<submesh>` selection on those names takes the first and drops the rest")
    if m["duplicate_node_name_count"]:
        flag("C5", "note", plural(m["duplicate_node_name_count"], "node name") + " used more than once")
    if m["generic_nodes"]:
        flag("C7", "note", f"{m['generic_nodes']} of {m['counts']['nodes']} node names are "
             "exporter-generated (Cylinder002 and the like), so nothing in the file is addressable")

    if m["prims_without_material"]:
        flag("F1", "broken", plural(m["prims_without_material"], "primitive") + " with no material, rendering as white metal")
    trap = m["materials"]["metallic_trap"]
    if trap:
        undeclared = sum(1 for t in trap if not t["declared"])
        flag("F2", "diverges", plural(len(trap), "material") + " metallic with no metallic-roughness texture to override it "
             f"({undeclared} by leaving `metallicFactor` unset, so 1.0)")
    if m["materials"]["textured_without_basecolor"]:
        n = len(m["materials"]["textured_without_basecolor"])
        flag("F3", "broken", plural(n, "material") + " carrying a texture but no `baseColorTexture`; RViz terminates on such a material")
    if m["materials"]["specular_glossiness"]:
        flag("F4", "broken", plural(m["materials"]["specular_glossiness"], "material") + " using the specular-glossiness workflow")
    blend = m["materials"]["alpha_modes"].get("BLEND", 0)
    if blend:
        flag("F5", "note", plural(blend, "material") + " tagged `BLEND`, which Gazebo ignores and renders opaque")
    if m["materials"]["basecolor_alpha_lt_1"]:
        flag("F6", "note", plural(m["materials"]["basecolor_alpha_lt_1"], "material") + " with `baseColorFactor` alpha below 1; Ogre2 applies it twice")
    if m["materials"]["normal_scale_not_1"] or m["materials"]["occlusion_strength_not_1"]:
        flag("F7", "note", "normalTexture.scale or occlusionTexture.strength is not 1.0, "
             "and neither is read by this project's consumers")

    for slot in ("normal", "metallicRoughness", "occlusion"):
        mimes = m["slot_mimes"].get(slot, {})
        if mimes.get("image/jpeg"):
            flag("G1", "diverges", plural(mimes["image/jpeg"], f"{slot} map") + " in JPEG; chroma subsampling blends unrelated channels")
    bad = [r for r in m["images"] if r.get("mime") and r["mime"] not in LOADABLE_MIME]
    if bad:
        flag("G2", "broken", plural(len(bad), "image") + f" in {', '.join(sorted({r['mime'] for r in bad}))}, "
             "which this project's consumers cannot decode")
    if m["max_texture_px"][0] > 2048 or m["max_texture_px"][1] > 2048:
        flag("G3", "diverges", f"largest texture is {m['max_texture_px'][0]}x"
             f"{m['max_texture_px'][1]}, above the 2048 cap")
    if m["uv_range"] and (m["uv_range"][0] < -0.001 or m["uv_range"][1] > 1.001
                          or m["uv_range"][2] < -0.001 or m["uv_range"][3] > 1.001):
        flag("E4", "diverges", "UVs fall outside [0,1]: u "
             f"{m['uv_range'][0]} to {m['uv_range'][1]}, v {m['uv_range'][2]} to {m['uv_range'][3]}"
             + (f" ({m['uv_range_note']})" if m.get("uv_range_note") else ""))

    if m["uv_sets"] > 1:
        flag("E3", "note", f"{m['uv_sets']} UV sets")
    if m["prims_without_normal"]:
        flag("E2", "diverges", plural(m["prims_without_normal"], "primitive") + " with no `NORMAL`, so normals are generated on import")
    if m["prims_without_uv"]:
        flag("E2", "note", plural(m["prims_without_uv"], "primitive") + " with no `TEXCOORD_0`")
    if [mode for mode in m["modes"] if mode != "TRIANGLES"]:
        flag("E1", "diverges", "non-triangle primitives: "
             + ", ".join(mode for mode in m["modes"] if mode != "TRIANGLES"))

    if m["extent_m"]:
        big = max(m["extent_m"])
        if big > 100:
            flag("D1", "note", f"largest extent is {big:g} m, so the file is probably not "
                 "in meters or is a whole scene")
        elif big < 0.005:
            flag("D1", "note", f"largest extent is {big:g} m, which is too small to be "
                 "real-world scale")
    return out


# ---------------------------------------------------------------- recency


def github_parts(uri):
    """(repo, ref, path) for a raw.githubusercontent URL, or None."""
    parts = urllib.parse.urlparse(uri)
    if parts.netloc != "raw.githubusercontent.com":
        return None
    bits = urllib.parse.unquote(parts.path).lstrip("/").split("/")
    if len(bits) < 4:
        return None
    return f"{bits[0]}/{bits[1]}", bits[2], "/".join(bits[3:])


def fuel_parts(uri):
    """(owner, model) for a Fuel file URL, or None."""
    parts = urllib.parse.urlparse(uri)
    if parts.netloc != "fuel.gazebosim.org":
        return None
    bits = urllib.parse.unquote(parts.path).lstrip("/").split("/")
    if len(bits) < 4 or bits[1] != "" and bits[2] != "models":
        pass
    # /1.0/{owner}/models/{name}/tip/files/...
    if len(bits) >= 4 and bits[2] == "models":
        return bits[1], bits[3]
    return None


def last_modified(uri):
    """When the asset itself last changed, as an ISO date, or None.

    Three sources, because there is no general one. GitHub knows the last commit
    that touched the path, which is the real answer for a versioned asset. Fuel
    records a per-model modify date. A local file has an mtime, which says when
    it arrived here rather than when it was authored, and is labelled as such.
    Anything else falls back to the HTTP Last-Modified header, which for most
    CDNs is the time they cached it and so is not trusted.
    """
    gh = github_parts(uri)
    if gh:
        repo, ref, path = gh
        try:
            data = gh_json(
                f"https://api.github.com/repos/{repo}/commits"
                f"?path={urllib.parse.quote(path)}&sha={urllib.parse.quote(ref)}&per_page=1"
            )
            if data:
                return data[0]["commit"]["committer"]["date"][:10], "last commit touching the file"
        except Exception:
            return None, None
    fuel = fuel_parts(uri)
    if fuel:
        owner, name = fuel
        try:
            data = json.loads(fetch_text(
                f"https://fuel.gazebosim.org/1.0/{urllib.parse.quote(owner)}"
                f"/models/{urllib.parse.quote(name)}"
            ))
            stamp = data.get("modify_date") or data.get("upload_date")
            return (stamp[:10] if stamp else None), "Fuel model modify date"
        except Exception:
            return None, None
    if not uri.startswith(("http://", "https://")):
        try:
            when = pathlib.Path(uri).expanduser().stat().st_mtime
            return time.strftime("%Y-%m-%d", time.localtime(when)), "local file mtime"
        except OSError:
            return None, None
    return None, None


def age_years(stamp, today=None):
    if not stamp:
        return None
    then = time.strptime(stamp, "%Y-%m-%d")
    now = time.localtime() if today is None else today
    years = now.tm_year - then.tm_year
    if (now.tm_mon, now.tm_mday) < (then.tm_mon, then.tm_mday):
        years -= 1
    days = (time.mktime(now) - time.mktime(then)) / 86400.0
    return round(days / 365.25, 2)


def resolve_dates(assets, cache_dir, refresh=False):
    """Fill in each asset's last-modified date, cached beside the measurements.

    Kept out of `measure` deliberately: the date is a property of the repository
    rather than of the bytes, it moves without the asset changing, and looking it
    up separately means the existing measurement cache stays valid.
    """
    path = cache_dir / "dates.json"
    known = json.loads(path.read_text()) if path.exists() and not refresh else {}
    changed = False
    for asset in assets:
        uri = asset["uri"]
        if uri not in known:
            stamp, source = last_modified(uri)
            known[uri] = {"date": stamp, "source": source}
            changed = True
        asset["last_modified"] = known[uri]["date"]
        asset["date_source"] = known[uri]["source"]
    if changed:
        path.write_text(json.dumps(known, indent=1, sort_keys=True))
    return assets


# ---------------------------------------------------------------- registry


def gh_json(url):
    """GitHub API, through `gh` when it is authenticated, else unauthenticated."""
    try:
        out = subprocess.run(
            ["gh", "api", url.replace("https://api.github.com/", "")],
            capture_output=True, text=True, timeout=60,
        )
        if out.returncode == 0:
            return json.loads(out.stdout)
    except (OSError, subprocess.SubprocessError):
        pass
    return json.loads(fetch_text(url))


def short_ids(paths):
    """Short, unique labels for the files a library entry expanded to.

    A library is usually a directory per model holding a file with the same name
    in each -- seventeen copies of `base_visual.glb` -- so the basename alone is
    useless and the full path is noise. Drop the extension, drop every path
    component that is common to all of them, collapse a directory repeated by
    its own file name, and fall back to the whole relative path if that still
    collides.
    """
    rels = [pathlib.PurePosixPath(p).with_suffix("").parts for p in paths]
    if len(rels) == 1:
        return ["/".join(rels[0][-1:])]
    everywhere = set(rels[0]).intersection(*(set(r) for r in rels[1:]))
    out = []
    for parts in rels:
        kept = [c for c in parts if c not in everywhere] or list(parts[-1:])
        squashed = [c for i, c in enumerate(kept) if i == 0 or c != kept[i - 1]]
        out.append("/".join(squashed))
    if len(set(out)) != len(out):
        out = ["/".join(r) for r in rels]
    return out


def expand(entry, cfg):
    """One registry entry to a list of (id, uri) assets.

    Single models, and libraries: a Fuel model with no file named, a GitHub repo
    with a glob, or a local directory glob, each expand to every glTF asset they
    contain.
    """
    exts = (".glb", ".gltf")
    out = []
    if "url" in entry:
        out.append((entry["id"], entry["url"]))
    elif "fuel" in entry:
        owner, name = entry["fuel"].split("/", 1)
        base = (f"https://fuel.gazebosim.org/1.0/{urllib.parse.quote(owner)}"
                f"/models/{urllib.parse.quote(name)}/tip/files")
        if "file" in entry:
            out.append((entry["id"], f"{base}/{entry['file'].lstrip('/')}"))
        else:
            tree = json.loads(fetch_text(base))
            paths = []

            def walk(nodes, prefix=""):
                for node in nodes:
                    path = node["path"]
                    if node.get("children"):
                        walk(node["children"], path)
                    elif path.lower().endswith(exts):
                        paths.append(path.lstrip("/"))

            walk(tree.get("file_tree", []))
            paths.sort()
            labels = short_ids(paths)
            for path, label in zip(paths, labels):
                out.append((entry["id"] if len(paths) == 1 else f"{entry['id']}/{label}",
                            f"{base}/{path}"))
    elif "github" in entry:
        repo, _, ref = entry["github"].partition("@")
        ref = ref or "HEAD"
        tree = gh_json(
            f"https://api.github.com/repos/{repo}/git/trees/{ref}?recursive=1"
        )
        pattern = entry.get("glob", "**/*.glb")
        hits = [
            node["path"] for node in tree.get("tree", [])
            if node["type"] == "blob" and node["path"].lower().endswith(exts)
            and fnmatch.fnmatch(node["path"], pattern)
        ]
        hits.sort()
        limit = entry.get("limit")
        if limit:
            hits = hits[:limit]
        for path, label in zip(hits, short_ids(hits)):
            out.append((entry["id"] if len(hits) == 1 else f"{entry['id']}/{label}",
                        f"https://raw.githubusercontent.com/{repo}/{ref}/"
                        + urllib.parse.quote(path)))
    elif "path" in entry:
        raw = os.path.expanduser(entry["path"])
        base = pathlib.Path(raw)
        if any(ch in raw for ch in "*?["):
            anchor = pathlib.Path(raw.split("*")[0].split("?")[0]).parent
            hits = sorted(str(p) for p in anchor.glob(raw[len(str(anchor)) + 1:]))
        elif base.is_dir():
            hits = sorted(str(p) for p in base.rglob("*") if p.suffix.lower() in exts)
        else:
            hits = [str(base)]
        if len(hits) == 1:
            out.append((entry["id"], hits[0]))
        else:
            for path, label in zip(hits, short_ids(hits)):
                out.append((f"{entry['id']}/{label}", path))
    else:
        raise ValueError(f"{entry['id']}: no url, fuel, github or path")
    return out


def cache_path(cache_dir, uri):
    return cache_dir / (hashlib.sha1(uri.encode()).hexdigest()[:16] + ".json")


# ---------------------------------------------------------------- visual rig

# The marker is the one from `spike/coords/make_markers.py`, in the REP 103 body
# frame and with arms of deliberately different lengths, so that a bounding box
# alone identifies every axis and its sign:
#
#     +X  1.00 L  red      forward        -X  0.10 L  grey   (so the sign of X reads too)
#     +Y  0.50 L  green    left
#     +Z  0.25 L  blue     up
#
# Emitted here as SDF boxes rather than as the glTF marker, deliberately. The
# glTF marker exists to test what a loader does with a file; this rig needs a
# reference that is true in the world frame whatever the loader does with glTF.
MARKER_ARMS = [
    ("pos_x", 1.00, (1, 0, 0), (0.80, 0.10, 0.10)),
    ("pos_y", 0.50, (0, 1, 0), (0.10, 0.70, 0.10)),
    ("pos_z", 0.25, (0, 0, 1), (0.10, 0.20, 0.85)),
    ("neg_x", 0.10, (-1, 0, 0), (0.35, 0.35, 0.35)),
]


def marker_model(name, length, offset):
    """An axis marker as a static SDF model, arms scaled to the asset."""
    w = max(length * 0.05, 0.002)
    out = [f'    <model name="{name}">', f"      <static>true</static>",
           f'      <pose>{offset[0]:g} {offset[1]:g} {offset[2]:g} 0 0 0</pose>',
           '      <link name="link">']
    for arm, fraction, axis, color in MARKER_ARMS:
        span = length * fraction
        size = [w, w, w]
        pose = [0.0, 0.0, 0.0]
        for i, a in enumerate(axis):
            if a:
                size[i] = span
                pose[i] = a * span / 2.0
        r, g, b = color
        out += [
            f'        <visual name="{arm}">',
            f"          <pose>{pose[0]:g} {pose[1]:g} {pose[2]:g} 0 0 0</pose>",
            f"          <geometry><box><size>{size[0]:g} {size[1]:g} {size[2]:g}</size>"
            "</box></geometry>",
            f"          <material><ambient>{r} {g} {b} 1</ambient>"
            f"<diffuse>{r} {g} {b} 1</diffuse></material>",
            "        </visual>",
        ]
    out += ["      </link>", "    </model>"]
    return "\n".join(out)


def asset_model(name, uri, offset, visual_pose):
    return "\n".join([
        f'    <model name="{name}">',
        "      <static>true</static>",
        f"      <pose>{offset[0]:g} {offset[1]:g} {offset[2]:g} 0 0 0</pose>",
        '      <link name="link">',
        '        <visual name="visual">',
        f"          <pose>{visual_pose}</pose>",
        f"          <geometry><mesh><uri>{uri}</uri></mesh></geometry>",
        "        </visual>",
        "      </link>",
        "    </model>",
    ])


def write_rig(result, uri, rig_dir):
    """Write a Gazebo world and a URDF that put the asset beside an axis marker.

    Two copies of the asset, each on its own marker: the file as authored, and
    the file with the +90 degree rotation about X that `parts.xacro` applies for
    `gltf_up:=z`. Standing in front of the pair answers both questions at once --
    which way the file faces, and whether our convention is the one that makes it
    stand up.
    """
    rig_dir.mkdir(parents=True, exist_ok=True)
    local = rig_dir / pathlib.PurePosixPath(urllib.parse.urlparse(uri).path).name
    if uri.startswith(("http://", "https://")):
        if not local.exists():
            local.write_bytes(Source(uri).read_all())
    else:
        local = pathlib.Path(uri).expanduser().resolve()

    extent = result.get("extent_m") or [1.0, 1.0, 1.0]
    span = max(extent) or 1.0
    length = min(max(span * 0.75, 0.05), 2.0)
    gap = span * 1.6 + length

    world = rig_dir / "rig.sdf"
    world.write_text("\n".join([
        '<?xml version="1.0"?>',
        '<sdf version="1.9">',
        '  <world name="origin_rig">',
        '    <plugin filename="gz-sim-physics-system" '
        'name="gz::sim::systems::Physics"/>',
        '    <plugin filename="gz-sim-user-commands-system" '
        'name="gz::sim::systems::UserCommands"/>',
        '    <plugin filename="gz-sim-scene-broadcaster-system" '
        'name="gz::sim::systems::SceneBroadcaster"/>',
        '    <light type="directional" name="sun">',
        "      <diffuse>1 1 1 1</diffuse><specular>0.2 0.2 0.2 1</specular>",
        "      <direction>-0.4 0.3 -0.9</direction><cast_shadows>false</cast_shadows>",
        "    </light>",
        f"    <!-- {result['id']}: extent {fmt_extent(extent)} m, "
        f"{origin_reading(result) or 'origin unmeasured'} -->",
        marker_model("marker_as_authored", length, (0, 0, 0)),
        asset_model("as_authored", local.as_uri(), (0, 0, 0), "0 0 0 0 0 0"),
        marker_model("marker_as_we_load_it", length, (0, gap, 0)),
        asset_model("as_we_load_it", local.as_uri(), (0, gap, 0), "0 0 0 1.5708 0 0"),
        "  </world>",
        "</sdf>",
        "",
    ]))

    urdf = rig_dir / "rig.urdf"
    links = ['<?xml version="1.0"?>', '<robot name="origin_rig">',
             '  <link name="base_link"/>']
    for suffix, rpy, y in (("as_authored", "0 0 0", 0.0), ("as_we_load_it", "1.5708 0 0", gap)):
        links += [
            f'  <link name="{suffix}">',
            "    <visual>",
            f'      <origin xyz="0 0 0" rpy="{rpy}"/>',
            f'      <geometry><mesh filename="{local.as_uri()}"/></geometry>',
            "    </visual>",
            "  </link>",
            f'  <joint name="{suffix}_joint" type="fixed">',
            '    <parent link="base_link"/>',
            f'    <child link="{suffix}"/>',
            f'    <origin xyz="0 {y:g} 0" rpy="0 0 0"/>',
            "  </joint>",
        ]
    links += ["</robot>", ""]
    urdf.write_text("\n".join(links))
    return world, urdf, local


RIG_QUESTIONS = """
  up:       which file axis points up when the model looks upright
  forward:  which file axis the front of the part faces
  datum:    what the origin sits on, in the part's own terms
"""


def rig_instructions(result, world, urdf):
    """What to run, and what to answer, printed rather than done: both need a window."""
    drydock = "~/maritime_ws/tools/drydock/drydock join maritime bash -lc"
    return f"""
Rig for {result['id']}
  extent      {fmt_extent(result.get('extent_m'))} m
  measured    {origin_reading(result) or 'origin unmeasured'}
  marker      +X red, +Y green (half), +Z blue (quarter), -X grey stub, in the world frame
  two copies  at the origin as authored, and at +Y with our gltf_up:=z rotation applied

Gazebo:
  {drydock} 'gz sim -v2 {world}'

RViz, fixed frame base_link, add a RobotModel display on /robot_description:
  {drydock} 'ros2 run robot_state_publisher robot_state_publisher {urdf}'
  {drydock} 'rviz2'

Then record the answers in visual-notes.yaml:

  "{result['id']}":
    up:       # +X | -X | +Y | -Y | +Z | -Z
    forward:  #
    datum:    # what the origin sits on, in the part's own terms
    checked:  # {time.strftime('%Y-%m-%d')} <you>
    note:     #
"""

# ---------------------------------------------------------------- report


def fmt_bytes(n):
    if n is None:
        return "--"
    if n >= 1 << 20:
        return f"{n / (1 << 20):.1f} MB"
    return f"{n / 1024:.0f} KB"


def fmt_extent(extent):
    if not extent:
        return "--"
    return " x ".join(f"{v:.3g}" for v in extent)


def slot_summary(m):
    out = []
    for slot in MAP_SLOTS:
        mimes = m["slot_mimes"].get(slot)
        if not mimes:
            continue
        label = {"baseColor": "base", "metallicRoughness": "MR", "normal": "nrm",
                 "occlusion": "occ", "emissive": "emis"}[slot]
        kinds = "/".join(
            (k or "?").replace("image/", "").upper() for k in sorted(mimes)
        )
        out.append(f"{label} {kinds}")
    return ", ".join(out) or "none"



AXIS_NAMES = ("X", "Y", "Z")


def origin_reading(m):
    """The origin's place inside the geometry, in words.

    Three fractions are hard to read and easy to misread; "centered in X and Z,
    on the -Y face" is the sentence a convention is actually written in. Spec 5.4
    proposes "centered in plan, zero on the mounting plane", and this is what
    that looks like when it is true.
    """
    fractions = m.get("origin_fraction")
    if not fractions and m.get("bbox_min_m") and m.get("extent_m"):
        # Derived rather than stored, so a cached measurement taken before this
        # existed still reads correctly and nothing has to be fetched again.
        fractions = [
            round(-lo / size, 4) if size > 1e-9 else None
            for lo, size in zip(m["bbox_min_m"], m["extent_m"])
        ]
    if not fractions:
        return None
    parts = []
    for axis, f in zip(AXIS_NAMES, fractions):
        if f is None:
            parts.append(f"flat in {axis}")
        elif f < -0.001 or f > 1.001:
            parts.append(f"outside the geometry in {axis}")
        elif f < 0.02:
            parts.append(f"on the -{axis} face")
        elif f > 0.98:
            parts.append(f"on the +{axis} face")
        elif 0.45 <= f <= 0.55:
            parts.append(f"centered in {axis}")
        else:
            parts.append(f"{f:.0%} along {axis}")
    return ", ".join(parts)


def measured_line(r):
    """The measurements worth seeing per asset that the corpus tables cannot show.

    Everything measured is in `results.json`; this is the handful a reader wants
    while looking at one asset's divergences -- how deep the tree is, where the
    origin sits inside the geometry, what the textures cost decoded, and how much
    of the file was read to find out.
    """
    bits = [
        plural(r["counts"]["nodes"], "node") + f", depth {r['max_node_depth']}",
        plural(r["counts"]["materials"], "material")
        + (f" ({r['materials']['unused']} unused)" if r['materials']['unused'] else ""),
    ]
    reading = origin_reading(r)
    if reading:
        bits.append("origin " + reading)
    if r.get("uv_range"):
        bits.append(
            f"UV {r['uv_range'][0]} to {r['uv_range'][1]}, {r['uv_range'][2]} to {r['uv_range'][3]}"
            + (f" ({r['uv_range_note']})" if r.get("uv_range_note") else "")
        )
    elif r.get("uv_range_note") and r["uv_range_note"] != "no UVs":
        # Say so: an absent range reads like an unremarkable one.
        bits.append("UV " + r["uv_range_note"])
    if r.get("decoded_bytes"):
        bits.append(f"{r['decoded_bytes'] / (1 << 20):.0f} MB of texture decoded")
    bits.append(
        f"fetched {fmt_bytes(r['fetched_bytes'])} in {plural(r['requests'], 'request')}"
        if r.get("requests") else "read from disk"
    )
    return " &middot; ".join(bits)


LEVEL_MARK = {"broken": "**breaks**", "diverges": "diverges", "note": "note"}


def source_link(source):
    """A registry entry's origin, as a link where there is one to give."""
    kind, locator = source["kind"], source["locator"]
    select = f" `{source['select']}`" if source["select"] else ""
    if kind == "fuel":
        owner, _, name = locator.partition("/")
        url = (f"https://app.gazebosim.org/{urllib.parse.quote(owner)}"
               f"/fuel/models/{urllib.parse.quote(name)}")
        return f"Fuel [{locator}]({url}){select}"
    if kind == "github":
        repo, _, ref = locator.partition("@")
        return f"[{repo}]({'https://github.com/' + repo}) `{ref or 'HEAD'}`{select}"
    if kind == "url":
        parts = urllib.parse.urlparse(locator)
        name = pathlib.PurePosixPath(parts.path).name
        if parts.netloc == "raw.githubusercontent.com":
            owner, repo, *_ = parts.path.lstrip("/").split("/") + ["", ""]
            return (f"[{name}]({locator}) in "
                    f"[{owner}/{repo}](https://github.com/{owner}/{repo})")
        return f"[{name}]({locator}) on {parts.netloc}"
    if kind == "path":
        return f"local `{locator}`"
    return "--"


def sources_section(sources, results, registry):
    """Where the examples came from: one row per registry entry, grouped.

    The registry is the argument of the assessment -- which corpus was looked at,
    and why each piece of it is in -- so the report carries it rather than
    pointing at the YAML. Entry rows say what a block expanded to, so a library
    of seventeen models reads as one decision rather than seventeen.
    """
    if not sources:
        return ""
    by_id = {r["id"]: r for r in results}
    groups = registry.get("groups", {})
    order = list(groups) + [g for g in dict.fromkeys(s["group"] for s in sources)
                            if g not in groups]
    lines = []
    add = lines.append
    add("## Where the examples come from")
    add("")
    live = [s for s in sources if not s["skip"]]
    add(f"{len(live)} entries in [examples.yaml](examples.yaml), expanding to "
        f"{sum(len(s['assets']) for s in live)} assets. An entry is one decision to include "
        "something; a library entry expands to every glTF file it matches, so seventeen "
        "warehouse models are one decision and not seventeen.")
    add("")
    for group in order:
        here = [s for s in sources if s["group"] == group]
        if not here:
            continue
        meta = groups.get(group, {})
        add(f"### {meta.get('title', group)}")
        add("")
        if meta.get("note"):
            add(meta["note"])
            add("")
        add("| Entry | Source | Assets | Size | Why it is on the list |")
        add("|---|---|---:|---:|---|")
        for source in here:
            rows = [by_id[a] for a in source["assets"] if a in by_id]
            size = sum(r.get("file_bytes") or 0 for r in rows)
            failed = sum(1 for r in rows if r.get("error"))
            count = "parked" if source["skip"] else str(len(source["assets"]))
            if failed:
                count += f" ({failed} unreachable)"
            add(f"| `{source['entry']}` | {source_link(source)} | {count} | "
                f"{fmt_bytes(size) if rows else '--'} | {source['note']} |")
        add("")
    return "\n".join(lines)


def origin_section(results, registry, root):
    """Where each origin sits, measured, and what a person made of it.

    The measurement and the visual answer are different kinds of thing and are
    kept in different columns on purpose: one is derived from the file every run,
    the other is somebody's reading of a rendering, recorded by hand and dated.
    """
    notes_path = root / registry.get("visual_notes", "visual-notes.yaml")
    notes = {}
    if notes_path.exists():
        notes = yaml.safe_load(notes_path.read_text()) or {}

    lines = []
    add = lines.append
    add("## Origin and orientation")
    add("")
    add("Where the file's zero sits inside its own geometry is measured every run. Which face "
        "that is in the part's own terms -- the mounting plane, the bow, upright -- is not in "
        "the file at all, and is answered by standing in front of the asset next to an axis "
        "marker. The protocol is in [criteria.md](criteria.md); the answers are hand-recorded "
        f"in [{notes_path.name}]({notes_path.name}).")
    add("")

    readings = {}
    for r in results:
        reading = origin_reading(r)
        if reading:
            readings.setdefault(reading, []).append(r["id"])
    if readings:
        add("### Measured, across the corpus")
        add("")
        add("| Where the origin sits | Assets |")
        add("|---|---:|")
        for reading, ids in sorted(readings.items(), key=lambda kv: -len(kv[1])):
            add(f"| {reading} | {len(ids)} |")
        add("")

    recorded = [r for r in results if notes.get(r["id"])]
    add("### Read off the rig")
    add("")
    if recorded:
        add("| Asset | Measured | Up | Forward | Datum | Checked |")
        add("|---|---|---|---|---|---|")
        for r in sorted(recorded, key=lambda r: r["id"]):
            n = notes[r["id"]] or {}
            add(f"| `{r['id']}` | {origin_reading(r) or '--'} | {n.get('up') or '--'} | "
                f"{n.get('forward') or '--'} | {n.get('datum') or '--'} | "
                f"{n.get('checked') or '--'} |")
        add("")
    add(f"{len(recorded)} of {len(results)} inspected."
        + ("" if len(recorded) == len(results)
           else " Set up the next one with `./gltf_assess.py --rig <id>`, which writes a "
                "Gazebo world holding the asset as authored beside the same asset with our "
                "`gltf_up:=z` rotation applied, each on its own axis marker, and prints the "
                "commands to view it in Gazebo and in RViz."))
    add("")
    return "\n".join(lines)


def report(results, registry, generated, sources=(), max_age=None):
    groups = registry.get("groups", {})
    by_group = {}
    for r in results:
        by_group.setdefault(r.get("group", "other"), []).append(r)

    lines = []
    add = lines.append
    add("# glTF example assessment")
    add("")
    add(f"Generated by `gltf_assess.py` on {generated}. Do not hand-edit: the list of examples is "
        "[examples.yaml](examples.yaml), the criteria behind the columns are [criteria.md](criteria.md), "
        "and the prose findings live in "
        "[findings.md](findings.md).")
    add("")

    ok = [r for r in results if not r.get("error")]
    failed = [r for r in results if r.get("error")]
    fetched = sum(r.get("fetched_bytes", 0) for r in ok)
    total = sum(r.get("file_bytes") or 0 for r in ok)
    requests = sum(r.get("requests", 0) for r in ok)
    cost = (
        f"this assessment fetched {fmt_bytes(fetched)} of it, in {requests} requests"
        if requests else "every file was read from disk"
    )
    add(f"{len(ok)} assets assessed"
        + (f", {len(failed)} unreachable" if failed else "")
        + f". Their combined size is {fmt_bytes(total)}; {cost}.")
    add("")

    section = sources_section(sources, results, registry)
    if section:
        add(section)
        add("")

    # A group marked `control` is read asset by asset and kept out of the corpus
    # numbers: the question the summary answers is what the robotics community
    # ships, which is not the same question as what the standard's authors meant.
    controls = {g for g, meta in groups.items() if meta.get("control")}
    # Age is the second reason an asset is measured but not counted. A file
    # nobody has touched in years is evidence about what people used to do, and
    # the question here is what they do now. Nothing is dropped: the assets stay
    # measured, cached and listed, and the cut is stated with the dates.
    for r in ok:
        r["age_years"] = age_years(r.get("last_modified"))
    stale = [
        r for r in ok
        if max_age and r.get("age_years") is not None and r["age_years"] > max_age
    ]
    undated = [r for r in ok if max_age and r.get("age_years") is None]
    aged_out = {id(r) for r in stale}
    counted = [r for r in ok if r.get("group") not in controls and id(r) not in aged_out]
    excluded = [r for r in ok if r.get("group") in controls and id(r) not in aged_out]
    recent = [r for r in ok if id(r) not in aged_out]
    add("## Corpus at a glance")
    add("")
    if max_age:
        add(f"Assets last changed more than {max_age:g} years ago are left out of everything "
            f"below: {len(stale)} of {len(ok)} are, and they are listed with their dates at the "
            "end so the record is kept."
            + (f" {len(undated)} could not be dated and are kept in." if undated else ""))
        add("")
    if excluded:
        names = ", ".join(sorted(groups[g].get("title", g) for g in controls))
        add(f"Over {len(counted)} of the {len(recent)} assets in scope. The {len(excluded)} "
            f"remaining in {names} are excluded here and read individually below: they are a "
            "control on the tool and on the standard, not evidence about what the robotics "
            "community does.")
        add("")
    add(summary_tables(counted))
    add("")

    add(origin_section(counted, registry, ROOT_HINT[0]))
    add("")

    add("## Every asset")
    add("")
    add("| Asset | Container | Size | Tris | Nodes | Prims | Mats | Imgs | Texture slots | "
        "Extent m | Changed | Generator |")
    add("|---|---|---:|---:|---:|---:|---:|---:|---|---|---|---|")
    for r in sorted(recent, key=lambda r: r["id"]):
        gen = re.sub(r"\s*v?(\d+\.\d+)[\d.]*$", r" \1", r["generator"])[:38] or "--"
        add(f"| `{r['id']}` | {r['container']} | {fmt_bytes(r['file_bytes'])} | "
            f"{r['triangles']:,} | {r['counts']['nodes']:,} | {r['primitives']:,} | "
            f"{r['counts']['materials']} | {r['counts']['images']} | {slot_summary(r)} | "
            f"{fmt_extent(r['extent_m'])} | {r.get('last_modified') or '--'} | {gen} |")
    add("")

    if failed:
        add("### Unreachable")
        add("")
        for r in sorted(failed, key=lambda r: r["id"]):
            add(f"- `{r['id']}` -- {r['error']} ({r['uri']})")
        add("")

    if stale:
        add("## Left out as no longer recent")
        add("")
        add(f"Measured, cached and kept in `results.json`, and excluded from everything above "
            f"because the file has not changed in more than {max_age:g} years. Raise "
            "`max_age_years` in [examples.yaml](examples.yaml), or pass `--max-age`, to bring "
            "them back.")
        add("")
        add("| Asset | Changed | Age | How the date was found |")
        add("|---|---|---:|---|")
        for r in sorted(stale, key=lambda r: r.get("last_modified") or ""):
            add(f"| `{r['id']}` | {r.get('last_modified') or '--'} | "
                f"{r['age_years']:.1f} yr | {r.get('date_source') or '--'} |")
        add("")

    add("## Against model-spec.md, per asset")
    add("")
    add("What each example does that our own specification forbids, or that would break in "
        "Gazebo or RViz. These are observations about other people's assets, not defects: "
        "an entry here means the example and the spec disagree, and which of them is wrong is "
        "the question worth asking. Criterion ids are defined in [criteria.md](criteria.md).")
    add("")
    last_note = None
    for r in sorted(recent, key=lambda r: r["id"]):
        obs = r.get("observations", [])
        add(f"### `{r['id']}`")
        add("")
        note = r.get("note")
        if note and note != last_note:
            add(f"{note}")
            add("")
        last_note = note
        add(f"[source]({r['uri']}) &middot; " + measured_line(r))
        add("")
        if not obs:
            add("Nothing diverges from `model-spec.md` that this tool can see.")
            add("")
            continue
        add("| | Criterion | Observation |")
        add("|---|---|---|")
        for o in sorted(obs, key=lambda o: (o["level"] != "broken", o["criterion"])):
            add(f"| {LEVEL_MARK[o['level']]} | {o['criterion']} | {o['text']} |")
        add("")
    return "\n".join(lines)


def summary_tables(results):
    """The trends across the corpus -- the reason for assessing more than one."""
    if not results:
        return "_Nothing assessed._"
    n = len(results)
    lines = []
    add = lines.append

    def pct(count):
        return f"{count} of {n} ({100 * count / n:.0f}%)"

    add("### Packaging and toolchain")
    add("")
    add("| | |")
    add("|---|---|")
    add(f"| Self-contained `.glb` | {pct(sum(1 for r in results if r['container'] == 'glb'))} |")
    add(f"| `.gltf` with side files | {pct(sum(1 for r in results if r['container'] != 'glb'))} |")
    add(f"| External image files | {pct(sum(1 for r in results if any(i.get('external') for i in r['images'])))} |")
    add(f"| Referenced file missing | {pct(sum(1 for r in results if r['missing_resources']))} |")
    gens = {}
    for r in results:
        key = re.sub(r"\s*v?(\d+)\.(\d+)[\d.]*$", r" \1.\2", r["generator"]) or "(none)"
        gens[key] = gens.get(key, 0) + 1
    add(f"| Distinct generators | {len(gens)} |")
    add("")
    add("| Generator | Assets |")
    add("|---|---:|")
    for key, count in sorted(gens.items(), key=lambda kv: -kv[1]):
        add(f"| {key} | {count} |")
    add("")

    add("### Scope actually used")
    add("")
    add("| Feature | Assets |")
    add("|---|---|")
    add(f"| Animations | {pct(sum(1 for r in results if r['counts']['animations']))} |")
    add(f"| Skins | {pct(sum(1 for r in results if r['counts']['skins']))} |")
    add(f"| Cameras | {pct(sum(1 for r in results if r['counts']['cameras']))} |")
    add(f"| `TANGENT` on any primitive | {pct(sum(1 for r in results if r['has_tangent']))} |")
    add(f"| Vertex colors | {pct(sum(1 for r in results if r['has_color']))} |")
    add(f"| More than one UV set | {pct(sum(1 for r in results if r['uv_sets'] > 1))} |")
    add(f"| Non-triangle primitives | {pct(sum(1 for r in results if any(m != 'TRIANGLES' for m in r['modes'])))} |")
    add(f"| More than one scene | {pct(sum(1 for r in results if r['counts']['scenes'] > 1))} |")
    add(f"| More than one root node | {pct(sum(1 for r in results if len(r['root_nodes']) > 1))} |")
    add(f"| Draco compression | {pct(sum(1 for r in results if r['draco_primitives']))} |")
    add("")

    add("### Structure, against the rules in spec 5.5")
    add("")
    add("| | |")
    add("|---|---|")
    add(f"| Root node carries a rotation or matrix | "
        f"{pct(sum(1 for r in results if any(t['rotation'] for t in r['root_transforms'])))} |")
    add(f"| Root node carries a scale | "
        f"{pct(sum(1 for r in results if any(any(abs(s - 1.0) > 1e-6 for s in t['scale']) for t in r['root_transforms'])))} |")
    add(f"| Exactly one root node, named and unrotated | "
        f"{pct(sum(1 for r in results if len(r['root_nodes']) == 1 and r['root_nodes'][0] and not any(t['rotation'] for t in r['root_transforms'])))} |")
    add(f"| Primitives sharing a node name (ambiguous `<submesh>`) | "
        f"{pct(sum(1 for r in results if r['ambiguous_submeshes']))} |")
    add(f"| Any exporter-generated node name | "
        f"{pct(sum(1 for r in results if r['generic_nodes']))} |")
    add(f"| Primitive count equals material count | "
        f"{pct(sum(1 for r in results if r['primitives'] == r['counts']['materials']))} |")
    add(f"| Nodes, median | {sorted(r['counts']['nodes'] for r in results)[len(results) // 2]} |")
    add("")
    add("### Extensions")
    add("")
    exts = {}
    required = {}
    for r in results:
        for e in r["extensions_used"]:
            exts[e] = exts.get(e, 0) + 1
        for e in r["extensions_required"]:
            required[e] = required.get(e, 0) + 1
    if exts:
        add("| Extension | Used by | Declared required by |")
        add("|---|---:|---:|")
        for e, count in sorted(exts.items(), key=lambda kv: -kv[1]):
            add(f"| `{e}` | {count} | {required.get(e, 0)} |")
    else:
        add("_No extensions anywhere in the corpus._")
    add("")

    add("### Materials")
    add("")
    total_mats = sum(r["counts"]["materials"] for r in results)
    trap = sum(len(r["materials"]["metallic_trap"]) for r in results)
    add("| | |")
    add("|---|---|")
    add(f"| Materials in the corpus | {total_mats} |")
    add(f"| Metallic with no metallic-roughness map | {trap} materials, in "
        f"{pct(sum(1 for r in results if r['materials']['metallic_trap']))} |")
    add(f"| ... by leaving `metallicFactor` unset | "
        f"{sum(1 for r in results for t in r['materials']['metallic_trap'] if not t['declared'])} materials |")
    add(f"| Textured with no `baseColorTexture` (RViz aborts) | "
        f"{sum(len(r['materials']['textured_without_basecolor']) for r in results)} materials, in "
        f"{pct(sum(1 for r in results if r['materials']['textured_without_basecolor']))} |")
    add(f"| Primitives with no material at all | "
        f"{sum(r['prims_without_material'] for r in results)}, in "
        f"{pct(sum(1 for r in results if r['prims_without_material']))} |")
    add(f"| Factor-only materials (no textures) | "
        f"{sum(r['materials']['factor_only'] for r in results)} |")
    add(f"| `BLEND` materials (Gazebo renders opaque) | "
        f"{sum(r['materials']['alpha_modes'].get('BLEND', 0) for r in results)} |")
    add(f"| `MASK` materials | "
        f"{sum(r['materials']['alpha_modes'].get('MASK', 0) for r in results)} |")
    add(f"| Double-sided materials | {sum(r['materials']['double_sided'] for r in results)} |")
    add("")

    add("### Texture format by slot")
    add("")
    add("Counted by image, not by use: an atlas shared across three thousand primitives is "
        "one image. The role of an image is the first slot it is used in.")
    add("")
    add("| Slot | PNG | JPEG | Other | Assets using the slot |")
    add("|---|---:|---:|---|---:|")
    for slot in MAP_SLOTS:
        png = jpeg = 0
        other = {}
        users = 0
        for r in results:
            here = [i for i in r["images"] if i.get("role") == slot]
            if not here:
                continue
            users += 1
            for image in here:
                mime = image.get("mime") or "unknown"
                if mime == "image/png":
                    png += 1
                elif mime == "image/jpeg":
                    jpeg += 1
                else:
                    other[mime] = other.get(mime, 0) + 1
        if users:
            other_text = ", ".join(f"{k} {v}" for k, v in sorted(other.items())) or "--"
            add(f"| {slot} | {png} | {jpeg} | {other_text} | {users} |")
    unused = sum(1 for r in results for i in r["images"] if i.get("role") == "unused")
    if unused:
        add(f"| (in the file, used by nothing) | | | | {unused} images |")
    add("")

    add("### Size")
    add("")
    tris = sorted(r["triangles"] for r in results)
    sizes = sorted(r["file_bytes"] or 0 for r in results)
    px = sorted(max(r["max_texture_px"]) for r in results if max(r["max_texture_px"]))
    add("| | min | median | max |")
    add("|---|---:|---:|---:|")
    add(f"| Triangles | {tris[0]:,} | {tris[len(tris) // 2]:,} | {tris[-1]:,} |")
    add(f"| File size | {fmt_bytes(sizes[0])} | {fmt_bytes(sizes[len(sizes) // 2])} | "
        f"{fmt_bytes(sizes[-1])} |")
    if px:
        add(f"| Largest texture, px | {px[0]} | {px[len(px) // 2]} | {px[-1]} |")
    add(f"| Over the 2048 texture cap | {pct(sum(1 for r in results if max(r['max_texture_px']) > 2048))} | | |")
    return "\n".join(lines)


# ---------------------------------------------------------------- main


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--registry", type=pathlib.Path, default=default_registry(),
                        help="the corpus registry; found automatically in a checkout")
    parser.add_argument("--only", action="append", default=[],
                        help="assess only ids starting with this (repeatable)")
    parser.add_argument("--refresh", action="store_true", help="ignore cached measurements")
    parser.add_argument("--json", type=pathlib.Path, help="also write the raw measurements here")
    parser.add_argument("--budget-mb", type=float, default=None,
                        help="per-asset ceiling on geometry actually fetched")
    parser.add_argument("--list", action="store_true", help="expand the registry and stop")
    parser.add_argument("--rig", metavar="ID",
                        help="write the visual rig for one asset and print how to view it")
    parser.add_argument("--rig-dir", type=pathlib.Path, default=None)
    parser.add_argument("--max-age", type=float, default=None, metavar="YEARS",
                        help="assess only assets changed within this many years "
                             "(default: the registry's max_age_years)")
    args = parser.parse_args(argv)

    if args.registry is None:
        print("no assess/examples.yaml found; pass --registry", file=sys.stderr)
        return 2
    registry = yaml.safe_load(args.registry.read_text())
    root = args.registry.parent
    ROOT_HINT[0] = root
    cache_dir = root / registry.get("cache", "cache")
    cache_dir.mkdir(exist_ok=True)
    budget = int((args.budget_mb or registry.get("budget_mb", 24)) * (1 << 20))

    assets = []
    sources = []
    for entry in registry.get("assets", []):
        source = {
            "entry": entry["id"],
            "group": entry.get("group", "other"),
            "note": entry.get("note", ""),
            "skip": bool(entry.get("skip")),
            "kind": next((k for k in ("url", "fuel", "github", "path") if k in entry), "?"),
            "locator": next((entry[k] for k in ("url", "fuel", "github", "path") if k in entry), ""),
            "select": entry.get("glob") or entry.get("file") or "",
            "assets": [],
        }
        sources.append(source)
        if entry.get("skip"):
            continue
        try:
            for asset_id, uri in expand(entry, registry):
                assets.append({"id": asset_id, "uri": uri, "group": entry.get("group", "other"),
                               "note": entry.get("note", ""), "entry": entry["id"]})
                source["assets"].append(asset_id)
        except Exception as exc:  # a library that will not list is a finding, not a crash
            assets.append({"id": entry["id"], "uri": entry.get("url", str(entry)),
                           "group": entry.get("group", "other"), "note": entry.get("note", ""),
                           "entry": entry["id"],
                           "error": f"could not expand: {exc}"})
            source["assets"].append(entry["id"])
    resolve_dates(assets, cache_dir, refresh=args.refresh)
    by_uri = {a["uri"]: a for a in assets}
    selected = [
        a for a in assets
        if not args.only or any(a["id"].startswith(p) for p in args.only)
    ]

    if args.rig:
        match = [a for a in assets if a["id"] == args.rig] or \
                [a for a in assets if a["id"].startswith(args.rig)]
        if not match:
            print(f"no asset matches {args.rig!r}; --list shows the ids", file=sys.stderr)
            return 1
        if len(match) > 1:
            print("ambiguous, matches: " + ", ".join(a["id"] for a in match), file=sys.stderr)
            return 1
        asset = match[0]
        cached = cache_path(cache_dir, asset["uri"])
        result = json.loads(cached.read_text()) if cached.exists() else measure(
            asset, asset["uri"], budget)
        result["id"] = asset["id"]
        rig_dir = args.rig_dir or (root / "rig" / asset["id"].replace("/", "_"))
        world, urdf, local = write_rig(result, asset["uri"], rig_dir)
        print(rig_instructions(result, world, urdf))
        return 0

    if args.list:
        assets = selected
        for a in assets:
            print(f"{a['id']}\t{a['uri']}")
        return 0

    # --only narrows what is measured, never what is reported: an asset left out
    # is read from the cache, so the generated report always covers the whole
    # registry and a partial run cannot quietly truncate it.
    chosen = {a["id"] for a in selected}
    results = []
    for asset in assets:
        if asset["id"] not in chosen:
            cached = cache_path(cache_dir, asset["uri"])
            if not cached.exists():
                continue
            m = json.loads(cached.read_text())
            m.update({"group": asset["group"], "note": asset["note"], "id": asset["id"],
                      "entry": asset.get("entry", "")})
            m["last_modified"] = asset.get("last_modified")
            m["date_source"] = asset.get("date_source")
            if not m.get("error"):
                m["observations"] = observations(m)
            results.append(m)
            continue
        if asset.get("error"):
            results.append(asset)
            print(f"  !! {asset['id']}: {asset['error']}", file=sys.stderr)
            continue
        cached = cache_path(cache_dir, asset["uri"])
        stale = json.loads(cached.read_text()) if cached.exists() else None
        # A cached failure is remembered so that a partial run still reports the
        # asset, and retried whenever the asset is actually selected, so that a
        # transient network error does not become a permanent finding.
        if stale is not None and not stale.get("error") and not args.refresh:
            m = stale
            print(f"  -- {asset['id']} (cached)", file=sys.stderr)
        else:
            print(f"  .. {asset['id']}", file=sys.stderr, flush=True)
            try:
                m = measure(asset, asset["uri"], budget)
                cached.write_text(json.dumps(m, indent=1))
            except Exception as exc:
                m = {"id": asset["id"], "uri": asset["uri"], "error": f"{type(exc).__name__}: {exc}"}
                cached.write_text(json.dumps(m, indent=1))
                print(f"  !! {asset['id']}: {m['error']}", file=sys.stderr)
        m["group"] = asset["group"]
        m["note"] = asset["note"]
        m["id"] = asset["id"]
        m["entry"] = asset.get("entry", "")
        m["last_modified"] = asset.get("last_modified")
        m["date_source"] = asset.get("date_source")
        if not m.get("error"):
            m["observations"] = observations(m)
        results.append(m)

    out = root / registry.get("report", "ASSESSMENT.md")
    max_age = args.max_age if args.max_age is not None else registry.get("max_age_years")
    out.write_text(
        report(results, registry, time.strftime("%Y-%m-%d"), sources, max_age) + "\n"
    )
    print(f"wrote {out}", file=sys.stderr)
    if args.json:
        args.json.write_text(json.dumps(results, indent=1))
        print(f"wrote {args.json}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
