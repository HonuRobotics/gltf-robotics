"""Write a part's manifest into its `.glb`, from the commission.

The profile requires every delivery to carry a manifest, and the workflow says
every value in it is copied from the commission. This does the copying. The
commission is a YAML file with plain keys; the manifest inside the file is
`KHR_xmp_json_ld`, whose properties carry namespace prefixes. Nobody has to
type a prefix: KEYS below is the whole mapping.

Only the JSON chunk of the container is rewritten. The binary chunk, which
holds the geometry and the textures, is copied through byte for byte.
"""

import argparse
import datetime
import json
import os
import pathlib
import struct
import sys

import yaml

from .check.rules import parse_dimensions

GLB_MAGIC = b"glTF"
CHUNK_JSON = 0x4E4F534A
CHUNK_BIN = 0x004E4942
EXTENSION = "KHR_xmp_json_ld"

CONTEXT = {
    "dc": "http://purl.org/dc/elements/1.1/",
    "xmpMM": "http://ns.adobe.com/xap/1.0/mm/",
    "stRef": "http://ns.adobe.com/xap/1.0/sType/ResourceRef#",
    "gltfrp": "https://honurobotics.github.io/gltf-robotics/ns/profile/1.0/",
}

# Commission key -> manifest property, and what it records.
KEYS = {
    "partRole": ("gltfrp:partRole", "base or component"),
    "datumPoint": ("gltfrp:datumPoint", "the feature of the part the origin is referenced to"),
    "datumTarget": ("gltfrp:datumTarget", "the physical realization of the datum"),
    "nominalDimension": ("gltfrp:nominalDimension", "the cited dimension, with its name and unit"),
    "dimensionTolerance": ("gltfrp:dimensionTolerance", "meters; the band the extent is held to"),
    "source": ("dc:source", "where the geometry came from"),
    "creator": ("dc:creator", "who authored the model"),
    "date": ("dc:date", "when it was delivered; today unless stated"),
    "rights": ("dc:rights", "licensing and redistribution terms"),
    "dimensionSource": ("dc:relation", "the published source the dimensions are cited from"),
    "authoringSource": ("xmpMM:DerivedFrom", "the archived authoring file"),
}

# Keys of a part block that are for the modeler to read and are not written to the file.
NOTES = ("referenceImages", "forwardFeature", "visualRequirement", "materials", "openings",
         "priorities", "notes")

# Keys that may be stated once for the whole commission and apply to every part.
SHARED = ("creator", "rights", "source", "dimensionSource", "authoringSource", "date")

DEFAULTS = {}  # the axes are glTF's own and are no longer declared


class ManifestError(Exception):
    """The commission or the file cannot be used as given."""


def part_name(path):
    """The part name implied by the filename: `<part>.visual.glb` -> `<part>`."""
    name = pathlib.Path(path).name
    for suffix in (".visual.glb", ".glb"):
        if name.endswith(suffix):
            return name[: -len(suffix)]
    raise ManifestError(f"{name}: not a .glb file")


def load_commission(path):
    try:
        data = yaml.safe_load(pathlib.Path(path).read_text())
    except yaml.YAMLError as exc:
        raise ManifestError(f"{path} is not valid YAML. An unclosed quote is the usual cause.\n{exc}")
    if not isinstance(data, dict) or not isinstance(data.get("parts"), dict):
        raise ManifestError(f"{path}: a commission needs a 'parts' mapping, one block per part")
    return data


def values_for(commission, part):
    """The manifest values for one part, in commission keys."""
    parts = commission["parts"]
    if part not in parts:
        raise ManifestError(f"the commission has no block for '{part}'; it has: "
                            + ", ".join(sorted(parts)))
    block = parts[part] or {}
    unknown = sorted(k for k in block if k not in KEYS and k not in NOTES)
    if unknown:
        raise ManifestError(f"'{part}' has keys this tool does not know: {', '.join(unknown)}. "
                            "Run gltf-manifest --keys for the list.")

    values = dict(DEFAULTS)
    values.update({k: commission[k] for k in SHARED if commission.get(k) is not None})
    values.update({k: v for k, v in block.items() if k in KEYS and v is not None})
    values.setdefault("date", datetime.date.today().isoformat())

    role = values.get("partRole")
    if role not in ("base", "component"):
        raise ManifestError(f"'{part}': partRole must be base or component, not {role!r}")
    if role == "base" and not values.get("datumPoint"):
        raise ManifestError(f"'{part}' is the base part and names no datumPoint")
    cited = values.get("nominalDimension")
    if cited and not parse_dimensions(cited):
        raise ManifestError(f"'{part}': nominalDimension {cited!r} has no readable figure. "
                            "Write a number with its unit, m, cm or mm, for example "
                            "'length overall 1.146 m'.")
    return values


def packet_for(values):
    """The JSON-LD packet for one part."""
    packet = {"@context": {}, "@id": ""}
    for key, value in values.items():
        prop = KEYS[key][0]
        if key in ("creator", "date"):
            # Ordered lists in XMP, even when there is one entry.
            value = {"@list": [str(v) for v in (value if isinstance(value, list) else [value])]}
        elif key == "authoringSource":
            value = {"stRef:filePath": str(value)}
        elif isinstance(value, datetime.date):
            value = value.isoformat()
        packet[prop] = value
    used = {p.split(":")[0] for p in packet if ":" in p}
    if "xmpMM:DerivedFrom" in packet:
        used.add("stRef")
    packet["@context"] = {prefix: CONTEXT[prefix] for prefix in CONTEXT if prefix in used}
    return packet


def read_glb(path):
    """(gltf, bin_chunk_bytes or None) from a binary glTF container."""
    data = pathlib.Path(path).read_bytes()
    if data[:4] != GLB_MAGIC:
        raise ManifestError(f"{path}: not a binary glTF file")
    _magic, version, _length = struct.unpack_from("<4sII", data, 0)
    if version != 2:
        raise ManifestError(f"{path}: glTF container version {version}, expected 2")
    json_len, json_type = struct.unpack_from("<II", data, 12)
    if json_type != CHUNK_JSON:
        raise ManifestError(f"{path}: the first chunk of the container is not JSON")
    gltf = json.loads(data[20:20 + json_len])
    after = 20 + json_len
    binary = None
    if after + 8 <= len(data):
        bin_len, bin_type = struct.unpack_from("<II", data, after)
        if bin_type == CHUNK_BIN:
            binary = data[after + 8: after + 8 + bin_len]
    return gltf, binary


def write_glb(path, gltf, binary):
    js = json.dumps(gltf, separators=(",", ":"), ensure_ascii=False).encode()
    js += b" " * (-len(js) % 4)
    body = struct.pack("<II", len(js), CHUNK_JSON) + js
    if binary is not None:
        binary += b"\x00" * (-len(binary) % 4)
        body += struct.pack("<II", len(binary), CHUNK_BIN) + binary
    path = pathlib.Path(path)
    tmp = path.with_name(path.name + ".tmp")
    tmp.write_bytes(struct.pack("<4sII", GLB_MAGIC, 2, 12 + len(body)) + body)
    os.replace(tmp, path)


def attach(gltf, packet):
    """Put the packet on the asset object, replacing the one already there."""
    top = gltf.setdefault("extensions", {}).setdefault(EXTENSION, {})
    packets = top.setdefault("packets", [])
    ref = gltf.setdefault("asset", {}).setdefault("extensions", {}).setdefault(EXTENSION, {})
    index = ref.get("packet")
    if isinstance(index, int) and 0 <= index < len(packets):
        packets[index] = packet
    else:
        packets.append(packet)
        ref["packet"] = len(packets) - 1
    used = gltf.setdefault("extensionsUsed", [])
    if EXTENSION not in used:
        used.append(EXTENSION)


def stamp(commission_path, glb_path, output=None, part=None):
    """Write the manifest for one file. Returns the packet written."""
    commission = load_commission(commission_path)
    packet = packet_for(values_for(commission, part or part_name(glb_path)))
    gltf, binary = read_glb(glb_path)
    attach(gltf, packet)
    write_glb(output or glb_path, gltf, binary)
    return packet


def main(argv=None):
    parser = argparse.ArgumentParser(
        prog="gltf-manifest",
        description="Write a part's manifest into its .glb, from the commission.",
    )
    parser.add_argument("commission", nargs="?", type=pathlib.Path, help="the commission, a YAML file")
    parser.add_argument("files", nargs="*", type=pathlib.Path, help="<part>.visual.glb, one or more")
    parser.add_argument("-o", "--output", type=pathlib.Path,
                        help="write here and leave the input untouched; one file only")
    parser.add_argument("--part", help="the part's name, when the filename does not give it")
    parser.add_argument("--keys", action="store_true",
                        help="list the commission keys and the manifest property each one writes")
    args = parser.parse_args(argv)

    if args.keys:
        width = max(len(k) for k in KEYS)
        for key, (prop, what) in KEYS.items():
            print(f"  {key:<{width}}  {prop:<26} {what}")
        print("\nRead by the modeler and not written to the file: " + ", ".join(NOTES))
        return 0
    if args.commission is None or not args.files:
        parser.error("give the commission and at least one .glb file")
    if (args.output or args.part) and len(args.files) > 1:
        parser.error("--output and --part take one file")

    failed = False
    for path in args.files:
        try:
            packet = stamp(args.commission, path, args.output, args.part)
        except (ManifestError, OSError, yaml.YAMLError, json.JSONDecodeError) as exc:
            print(f"{path}: {exc}", file=sys.stderr)
            failed = True
            continue
        written = args.output or path
        print(f"{written}: manifest written, {len(packet) - 2} properties, "
              f"role {packet['gltfrp:partRole']}")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
