"""A conforming baseline model, and the machinery to break it one rule at a time.

Fixtures are built rather than committed. A binary fixture in the tree tells a
reader nothing about which rule it is meant to violate, and a generator says it
in one line of Python.

The baseline satisfies every mechanically decidable rule in the profile, so any
finding a mutated copy produces is attributable to the mutation.
"""

import copy
import json
import pathlib
import struct
import zlib

import pytest


def png(width, height, rgba=False, alpha=255):
    """A minimal valid PNG, colour type 6 (RGBA) or 2 (RGB)."""
    ctype = 6 if rgba else 2
    depth, channels = 8, (4 if rgba else 3)
    raw = b""
    for _ in range(height):
        row = b"\x00"  # filter type 0
        for _ in range(width):
            row += bytes([120, 130, 140] + ([alpha] if rgba else []))
        raw += row

    def chunk(tag, payload):
        return (struct.pack(">I", len(payload)) + tag + payload
                + struct.pack(">I", zlib.crc32(tag + payload) & 0xFFFFFFFF))

    ihdr = struct.pack(">IIBBBBB", width, height, depth, ctype, 0, 0, 0)
    return (b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", ihdr)
            + chunk(b"IDAT", zlib.compress(raw)) + chunk(b"IEND", b""))


def pad4(data, fill=b"\x00"):
    return data + fill * (-len(data) % 4)


def pack_glb(gltf, buffer):
    js = pad4(json.dumps(gltf, separators=(",", ":")).encode(), b" ")
    bin_ = pad4(buffer)
    return (struct.pack("<4sII", b"glTF", 2, 12 + 8 + len(js) + 8 + len(bin_))
            + struct.pack("<II", len(js), 0x4E4F534A) + js
            + struct.pack("<II", len(bin_), 0x004E4942) + bin_)


def baseline():
    """(gltf, buffer) for a model that satisfies the profile.

    One square in the XY plane: four vertices, two triangles, one material with
    a PNG base colour, one UV set inside [0,1], one named root node with no
    transform, one scene listing it.
    """
    positions = [(-0.5, -0.5, 0.0), (0.5, -0.5, 0.0), (-0.5, 0.5, 0.0), (0.5, 0.5, 0.0)]
    normals = [(0.0, 0.0, 1.0)] * 4
    uvs = [(0.0, 1.0), (1.0, 1.0), (0.0, 0.0), (1.0, 0.0)]
    indices = [0, 1, 2, 1, 3, 2]

    blocks, buffer = [], b""
    for data, fmt in ((positions, "<3f"), (normals, "<3f"), (uvs, "<2f")):
        payload = b"".join(struct.pack(fmt, *v) for v in data)
        blocks.append((len(buffer), len(payload)))
        buffer = pad4(buffer + payload)
    payload = b"".join(struct.pack("<H", i) for i in indices)
    blocks.append((len(buffer), len(payload)))
    buffer = pad4(buffer + payload)
    image = png(64, 64)
    blocks.append((len(buffer), len(image)))
    buffer = pad4(buffer + image)

    gltf = {
        "asset": {"version": "2.0", "generator": "gltf-robotics test fixtures"},
        "scene": 0,
        "scenes": [{"nodes": [0]}],
        "nodes": [{"name": "test_part", "mesh": 0}],
        "meshes": [{"name": "test_part_mesh", "primitives": [{
            "attributes": {"POSITION": 0, "NORMAL": 1, "TEXCOORD_0": 2},
            "indices": 3, "material": 0, "mode": 4}]}],
        "materials": [{
            "name": "Housing",
            "alphaMode": "OPAQUE",
            "pbrMetallicRoughness": {
                "baseColorTexture": {"index": 0},
                "metallicFactor": 0.0,
                "roughnessFactor": 0.6,
            },
        }],
        "textures": [{"source": 0, "sampler": 0}],
        "samplers": [{}],
        "images": [{"name": "Albedo-Housing", "bufferView": 4, "mimeType": "image/png"}],
        "accessors": [
            {"bufferView": 0, "componentType": 5126, "count": 4, "type": "VEC3",
             "min": [-0.5, -0.5, 0.0], "max": [0.5, 0.5, 0.0]},
            {"bufferView": 1, "componentType": 5126, "count": 4, "type": "VEC3"},
            {"bufferView": 2, "componentType": 5126, "count": 4, "type": "VEC2",
             "min": [0.0, 0.0], "max": [1.0, 1.0]},
            {"bufferView": 3, "componentType": 5123, "count": 6, "type": "SCALAR"},
        ],
        "bufferViews": [{"buffer": 0, "byteOffset": off, "byteLength": ln}
                        for off, ln in blocks],
        "buffers": [{"byteLength": len(buffer)}],
    }
    return gltf, buffer


@pytest.fixture
def write_model(tmp_path):
    """write_model(mutate=None, name="test_part.visual.glb") -> path to a .glb."""

    def _write(mutate=None, name="test_part.visual.glb", buffer_mutate=None):
        gltf, buffer = baseline()
        gltf = copy.deepcopy(gltf)
        if mutate is not None:
            mutate(gltf)
        if buffer_mutate is not None:
            buffer = buffer_mutate(gltf, buffer)
        path = pathlib.Path(tmp_path) / name
        path.write_bytes(pack_glb(gltf, buffer))
        return path

    return _write
