"""gltf-manifest: the commission goes into the file, and nothing else changes."""

import pathlib

import pytest
import yaml

from gltf_robotics import manifest
from gltf_robotics.check.rules import FAIL, check_file

TEMPLATE = pathlib.Path(__file__).resolve().parents[1] / "docs" / "commission-template.yaml"


def strip(g):
    """The baseline model with its manifest removed, as an exporter delivers it."""
    g["asset"].pop("extensions")
    g.pop("extensions")
    g.pop("extensionsUsed")


@pytest.fixture
def commission(tmp_path):
    def _write(**part):
        block = {"partRole": "component", "datumPoint": "center of the mounting face",
                 "source": "test"}
        block.update(part)
        path = tmp_path / "commission.yaml"
        path.write_text(yaml.safe_dump({"creator": "tests", "parts": {"test_part": block}}))
        return path
    return _write


def failures(path):
    return {f.section for f in check_file(path) if f.level == FAIL}


def test_a_stamped_file_passes_the_manifest_rules(write_model, commission):
    path = write_model(strip)
    assert "The manifest" in failures(path)
    manifest.stamp(commission(), path)
    assert not failures(path)


def test_axes_are_filled_in(write_model, commission):
    path = write_model(strip)
    packet = manifest.stamp(commission(), path)
    assert packet["gltfrp:forward"] == "+X" and packet["gltfrp:up"] == "+Z"


def test_the_binary_chunk_is_untouched(write_model, commission):
    path = write_model(strip)
    _gltf, before = manifest.read_glb(path)
    manifest.stamp(commission(), path)
    _gltf, after = manifest.read_glb(path)
    assert before == after


def test_stamping_twice_leaves_one_packet(write_model, commission):
    path = write_model(strip)
    manifest.stamp(commission(), path)
    manifest.stamp(commission(datumPoint="center of the bore"), path)
    gltf, _binary = manifest.read_glb(path)
    packets = gltf["extensions"]["KHR_xmp_json_ld"]["packets"]
    assert len(packets) == 1
    assert packets[0]["gltfrp:datumPoint"] == "center of the bore"
    assert gltf["extensionsUsed"].count("KHR_xmp_json_ld") == 1


def test_a_misspelled_key_is_refused(write_model, commission):
    path = write_model(strip)
    with pytest.raises(manifest.ManifestError, match="datumPiont"):
        manifest.stamp(commission(datumPiont="oops"), path)


def test_a_base_part_needs_a_datum_point(write_model, commission):
    path = write_model(strip)
    with pytest.raises(manifest.ManifestError, match="datumPoint"):
        manifest.stamp(commission(partRole="base", datumPoint=None), path)


def test_a_part_missing_from_the_commission_is_refused(write_model, commission):
    path = write_model(strip, name="other_part.visual.glb")
    with pytest.raises(manifest.ManifestError, match="other_part"):
        manifest.stamp(commission(), path)


def test_notes_for_the_modeler_stay_out_of_the_file(write_model, commission):
    path = write_model(strip)
    packet = manifest.stamp(commission(materials="non-metal, matte black"), path)
    assert not any("materials" in key for key in packet)


def test_the_template_is_a_usable_commission():
    data = manifest.load_commission(TEMPLATE)
    for part in data["parts"]:
        packet = manifest.packet_for(manifest.values_for(data, part))
        assert packet["gltfrp:partRole"] in ("base", "component")
