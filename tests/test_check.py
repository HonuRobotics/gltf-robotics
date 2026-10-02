"""Each mutation must fail its own rule, and no other.

That second half is the point. A checker that fires on everything is no more
useful than one that fires on nothing, so every test asserts both the expected
failure and the absence of collateral ones.
"""

import pytest

from gltf_robotics.check.rules import FAIL, WARN, check_file


def failures(path):
    return {f.section for f in check_file(path) if f.level == FAIL}


def warnings(path):
    return {f.section for f in check_file(path) if f.level == WARN}


def summaries(path, level=FAIL):
    return [f.summary for f in check_file(path) if f.level == level]


def test_baseline_conforms(write_model):
    """The baseline must be clean, or every other test is meaningless."""
    path = write_model()
    assert failures(path) == set()
    assert warnings(path) == set()


# ------------------------------------------------------- delivery

def test_part_name_must_be_snake_case(write_model):
    path = write_model(name="TestPart.visual.glb")
    assert "File naming" in failures(path)


def test_filename_without_visual_suffix_warns(write_model):
    path = write_model(name="test_part.glb")
    assert "File naming" in warnings(path)
    assert failures(path) == set()


def test_min_version_warns(write_model):
    """Asset header relaxed this to SHOULD NOT, so it reviews rather than fails."""
    path = write_model(lambda g: g["asset"].update(minVersion="2.0"))
    assert failures(path) == set()
    assert "Asset header" in warnings(path)


def test_generator_must_be_recorded(write_model):
    path = write_model(lambda g: g["asset"].pop("generator"))
    assert failures(path) == {"Authoring toolchain"}


# ------------------------------------- coordinate systems, nodes

def test_old_axis_declarations_are_accepted_silently(write_model):
    """The file follows glTF's convention now, so the old attestation is harmless."""
    from conftest import manifest
    path = write_model(lambda g: g["extensions"]["KHR_xmp_json_ld"].update(
        packets=[manifest(**{"gltfrp:forward": "+X", "gltfrp:up": "+Z"})]))
    assert failures(path) == set()
    assert not any("forward" in f.summary or "gltfrp:up" in f.summary for f in check_file(path))


def test_two_scenes(write_model):
    path = write_model(lambda g: g["scenes"].append({"nodes": [0]}))
    assert failures(path) == {"Scenes and nodes"}


@pytest.mark.parametrize("key, value", [
    ("translation", [0.0, 0.5, 0.0]),
    ("rotation", [-0.7071068, 0.0, 0.0, 0.7071068]),
    ("scale", [2.0, 2.0, 2.0]),
    ("matrix", [1, 0, 0, 0, 0, 1, 0, 0, 0, 0, 1, 0, 0, 0, 0, 1]),
])
def test_any_node_transform_fails(write_model, key, value):
    """All four keys, so node space and scene space cannot come apart."""
    path = write_model(lambda g: g["nodes"][0].update({key: value}))
    assert failures(path) == {"Scenes and nodes"}
    assert any(key in f.detail for f in check_file(path) if f.level == FAIL)


@pytest.mark.parametrize("key, identity", [
    ("translation", [0.0, 0.0, 0.0]),
    ("rotation", [0.0, 0.0, 0.0, 1.0]),
    ("scale", [1.0, 1.0, 1.0]),
    ("matrix", [1, 0, 0, 0, 0, 1, 0, 0, 0, 0, 1, 0, 0, 0, 0, 1]),
])
def test_a_stated_identity_transform_still_fails(write_model, key, identity):
    """The rule is on presence, not value.

    glTF omits a component equal to its default, so an absent key and an
    identity value are the same geometry from two different exporters. A value
    test would pass a file that `gltf_to_yup.py` refuses, and it would leave the
    checker disagreeing with the profile, which prohibits the key.
    """
    path = write_model(lambda g: g["nodes"][0].update({key: identity}))
    assert failures(path) == {"Scenes and nodes"}


def test_several_transform_keys_are_reported_together(write_model):
    path = write_model(lambda g: g["nodes"][0].update(
        translation=[0.0, 0.5, 0.0], scale=[2.0, 2.0, 2.0]))
    assert failures(path) == {"Scenes and nodes"}
    detail = " ".join(f.detail for f in check_file(path) if f.level == FAIL)
    assert "translation" in detail and "scale" in detail


def test_root_node_blender_numeric_suffix(write_model):
    path = write_model(lambda g: g["nodes"][0].update(name="test_part.001"))
    assert failures(path) == {"Scenes and nodes"}


def test_two_root_nodes(write_model):
    def mutate(g):
        g["nodes"].append({"name": "second", "mesh": 0})
        g["scenes"][0]["nodes"] = [0, 1]
    path = write_model(mutate)
    assert failures(path) == {"Scenes and nodes"}


def test_a_child_node_fails(write_model):
    """One node, no hierarchy: Gazebo bakes child transforms in, so structure is lost."""
    def mutate(g):
        g["nodes"][0]["children"] = [1]
        g["nodes"].append({"name": "tip", "mesh": 0})
    path = write_model(mutate)
    assert failures(path) == {"Scenes and nodes"}
    detail = " ".join(f.detail for f in check_file(path) if f.level == FAIL)
    assert "child" in detail


def test_a_second_node_fails_even_unparented(write_model):
    """Two nodes is two nodes, whether or not the scene lists both."""
    path = write_model(lambda g: g["nodes"].append({"name": "spare", "mesh": 0}))
    assert failures(path) == {"Scenes and nodes"}
    assert any("2 nodes, expected exactly 1" in s for s in summaries(path))


# ----------------------------------------------------- geometry

def test_non_triangle_primitive(write_model):
    path = write_model(lambda g: g["meshes"][0]["primitives"][0].update(mode=5))
    assert failures(path) == {"Geometry"}


def test_missing_normals(write_model):
    path = write_model(lambda g: g["meshes"][0]["primitives"][0]["attributes"].pop("NORMAL"))
    assert failures(path) == {"Geometry"}


def test_second_uv_set_is_permitted_for_a_lightmap(write_model):
    """The profile's UV sets section permits TEXCOORD_1, and only for a baked occlusion lightmap."""
    path = write_model(
        lambda g: g["meshes"][0]["primitives"][0]["attributes"].update(TEXCOORD_1=2))
    assert failures(path) == set()


def test_third_uv_set_fails(write_model):
    path = write_model(
        lambda g: g["meshes"][0]["primitives"][0]["attributes"].update(
            TEXCOORD_1=2, TEXCOORD_2=2))
    assert failures(path) == {"UV sets"}


def test_uv_outside_unit_range(write_model):
    path = write_model(lambda g: g["accessors"][2].update(min=[0.0, 0.0], max=[2.0, 1.0]))
    assert failures(path) == {"UV sets"}


def _extra_primitive(g, material=0):
    """A second primitive on the same mesh, reusing the baseline's buffer views."""
    first = g["meshes"][0]["primitives"][0]
    g["meshes"][0]["primitives"].append(dict(first, material=material))


def test_two_primitives_sharing_a_material_fail(write_model):
    """A primitive exists to carry a distinct material; sharing one splits for no reason."""
    path = write_model(_extra_primitive)
    assert failures(path) == {"Primitives"}
    detail = " ".join(f.detail for f in check_file(path) if f.level == FAIL)
    assert "Housing" in detail


def test_two_primitives_with_distinct_materials_pass(write_model):
    """The legitimate reason to have two: glTF gives a primitive at most one material."""
    def mutate(g):
        g["materials"].append(dict(g["materials"][0], name="Trim"))
        _extra_primitive(g, material=1)

    path = write_model(mutate)
    assert failures(path) == set()


# ---------------------------------------------------- materials

def test_primitive_without_material(write_model):
    path = write_model(lambda g: g["meshes"][0]["primitives"][0].pop("material"))
    assert failures(path) == {"Materials"}
    assert any("white metal" in f.detail for f in check_file(path))


def test_metalness_trap_with_no_texture_to_override(write_model):
    """metallicFactor unset means 1.0: a material that says nothing says metal."""
    path = write_model(
        lambda g: g["materials"][0]["pbrMetallicRoughness"].pop("metallicFactor"))
    assert failures(path) == {"Materials"}


def test_unset_metalness_with_orm_texture_is_only_a_warning(write_model):
    """The texture multiplies against the factor, so this is not decidable here."""
    def mutate(g):
        g["materials"][0]["pbrMetallicRoughness"].pop("metallicFactor")
        g["materials"][0]["pbrMetallicRoughness"]["metallicRoughnessTexture"] = {"index": 0}
    path = write_model(mutate)
    assert failures(path) == set()
    assert warnings(path) == {"Materials"}


def test_textured_material_without_base_colour(write_model):
    """The shape that terminates RViz: maps present, no diffuse to hand back."""
    def mutate(g):
        pbr = g["materials"][0]["pbrMetallicRoughness"]
        pbr.pop("baseColorTexture")
        g["materials"][0]["normalTexture"] = {"index": 0}
    path = write_model(mutate)
    # Only the profile's Materials section. The map reused here is the baseline's PNG, so the texture
    # format rule is satisfied and must stay quiet.
    assert failures(path) == {"Materials"}
    assert any("RViz" in f.detail for f in check_file(path))


def test_normal_texture_scale_must_be_one(write_model):
    def mutate(g):
        g["materials"][0]["normalTexture"] = {"index": 0, "scale": 0.5}
    path = write_model(mutate)
    assert "Materials" in failures(path)


# ----------------------------------------------------- textures

def test_texture_over_2048(write_model):
    from conftest import pad4, png
    def buffer_mutate(g, buf):
        big = png(4096, 4)
        head = buf[: g["bufferViews"][4]["byteOffset"]]
        g["bufferViews"][4]["byteLength"] = len(big)
        return pad4(head + big)
    path = write_model(buffer_mutate=buffer_mutate)
    assert failures(path) == {"Textures"}


# ------------------------------------------------- transparency

def test_blend_is_prohibited(write_model):
    path = write_model(lambda g: g["materials"][0].update(alphaMode="BLEND"))
    assert failures(path) == {"Transparency"}


def test_mask_requires_cutoff_half(write_model):
    def mutate(g):
        g["materials"][0].update(alphaMode="MASK", alphaCutoff=0.1)
    path = write_model(mutate)
    assert "Transparency" in failures(path)


def test_mask_requires_alpha_in_the_base_colour(write_model):
    """The baseline's PNG is colour type 2, so MASK alone has nothing to threshold."""
    path = write_model(lambda g: g["materials"][0].update(alphaMode="MASK"))
    assert failures(path) == {"Transparency"}
    assert any("binary alpha" in f.detail for f in check_file(path))


# --------------------------------------------- prohibited content

@pytest.mark.parametrize("extension", [
    "KHR_draco_mesh_compression",
    "KHR_texture_basisu",
    "KHR_texture_transform",
    "KHR_materials_pbrSpecularGlossiness",
])
def test_prohibited_extensions(write_model, extension):
    path = write_model(lambda g: g.update(extensionsUsed=[extension]))
    assert failures(path) == {"Prohibited content"}


def test_extensions_required_is_prohibited_even_when_allowed_elsewhere(write_model):
    """The general case: a required extension a reader must refuse the file over."""
    path = write_model(lambda g: g.update(extensionsRequired=["KHR_materials_specular"],
                                          extensionsUsed=["KHR_materials_specular"]))
    assert failures(path) == {"Prohibited content"}


@pytest.mark.parametrize("key", ["animations", "skins", "cameras"])
def test_prohibited_content(write_model, key):
    path = write_model(lambda g: g.update(**{key: [{}]}))
    assert failures(path) == {"Prohibited content"}


# --------------------------------------------------------------- advisories

def test_undecided_rules_never_fail(write_model):
    """The profile's Open issues section: a delivery cannot fail on a point marked Open."""
    from gltf_robotics.check.rules import ADVISORY
    findings = check_file(write_model())
    advisory = {f.section for f in findings if f.level == ADVISORY}
    # Units alone: scale cannot be read from a glTF file at all. The axes are
    # decided now, so an undeclared axis is a WARN -- a MUST the file cannot
    # settle -- rather than an Open point, and Datum specification is a real rule now that the
    # datum specification has a home.
    assert advisory == {"Units"}
    assert not any(f.failed for f in findings if f.section in advisory)


# ---------------------------------------------------- manifest, datum

def _packet(g):
    return g["extensions"]["KHR_xmp_json_ld"]["packets"][0]


# ------------------------------------ units: the extent against the cited dimension
# The baseline is a square 1 m on a side in the XY plane, so its extents are 1, 1, 0.

def _cite(text, tolerance=0.005):
    def mutate(g):
        _packet(g)["gltfrp:nominalDimension"] = text
        if tolerance is not None:
            _packet(g)["gltfrp:dimensionTolerance"] = tolerance
    return mutate


def _units(path):
    return [f for f in check_file(path) if f.section == "Units"]


def test_a_cited_dimension_that_matches_an_extent_passes(write_model):
    from gltf_robotics.check.rules import PASS
    (finding,) = _units(write_model(_cite("length overall 1.002 m")))
    assert finding.level == PASS
    assert "X extent" in finding.summary


def test_a_cited_dimension_outside_tolerance_fails(write_model):
    (finding,) = _units(write_model(_cite("length overall 1.2 m")))
    assert finding.level == FAIL
    assert "X 1 m" in finding.detail and "0.2" in finding.detail


def test_a_file_in_millimeters_is_named_as_such(write_model):
    def mutate(g):
        _cite("length overall 1 m")(g)
        g["accessors"][0]["min"] = [-500.0, -500.0, 0.0]
        g["accessors"][0]["max"] = [500.0, 500.0, 0.0]
    (finding,) = _units(write_model(mutate))
    assert finding.level == FAIL
    assert "millimeters" in finding.detail


def test_a_cited_dimension_in_millimeters_is_converted(write_model):
    from gltf_robotics.check.rules import PASS
    (finding,) = _units(write_model(_cite("length overall 1000 mm")))
    assert finding.level == PASS


def test_a_cited_dimension_without_a_tolerance_warns(write_model):
    (finding,) = _units(write_model(_cite("length overall 1 m", tolerance=None)))
    assert finding.level == WARN
    assert "tolerance" in finding.summary


def test_a_cited_dimension_with_no_figure_warns(write_model):
    (finding,) = _units(write_model(_cite("about a meter long")))
    assert finding.level == WARN
    assert "readable figure" in finding.summary


def test_every_cited_figure_is_checked(write_model):
    from gltf_robotics.check.rules import PASS
    findings = _units(write_model(_cite("length overall 1 m; height 0.3 m")))
    assert [f.level for f in findings] == [PASS, FAIL]
    assert "height" in findings[1].summary


def test_no_cited_dimension_stays_open(write_model):
    from gltf_robotics.check.rules import ADVISORY
    (finding,) = _units(write_model())
    assert finding.level == ADVISORY


def test_a_missing_manifest_fails(write_model):
    """Required by the profile's manifest section: provenance cannot be reconstructed later.

    It was a SHOULD while the argument against was that no existing delivery
    carried one. That argument is withdrawn -- the existing files are not trusted
    and no rule is calibrated to them.
    """
    def mutate(g):
        g["asset"].pop("extensions")
        g.pop("extensions")
        g.pop("extensionsUsed")
    path = write_model(mutate)
    assert "The manifest" in failures(path)


@pytest.mark.parametrize("key", ["gltfrp:partRole"])
def test_each_required_manifest_property_fails_when_absent(write_model, key):
    """The one property that records what no measurement can recover."""
    from conftest import manifest
    packet = manifest()
    packet.pop(key)
    path = write_model(lambda g: g["extensions"]["KHR_xmp_json_ld"].update(packets=[packet]))
    assert "The manifest" in failures(path)
    assert any(key in f.summary for f in check_file(path) if f.level == FAIL)


def test_manifest_without_a_role_fails(write_model):
    path = write_model(lambda g: _packet(g).pop("gltfrp:partRole"))
    assert "The manifest" in failures(path)


def test_creator_tool_must_match_asset_generator(write_model):
    """The copied-from-a-sibling-part failure, made mechanical."""
    path = write_model(lambda g: _packet(g).update({"xmp:CreatorTool": "Some Other Exporter"}))
    assert "The manifest" in failures(path)


def test_realized_pose_must_not_be_authored(write_model):
    """Datum specification: a derived quantity recorded beside its rule is two sources of truth."""
    path = write_model(
        lambda g: _packet(g).update({"gltfrp:realizedPose": {"@list": [0, 0, 0, 0, 0, 0]}}))
    assert "Datum specification" in failures(path)


# ------------------------------------------------------------ the CLI output

from gltf_robotics.check import cli  # noqa: E402


def test_verdict_agrees_with_exit_code(write_model, capsys):
    """The text verdict, the JSON flag and the exit code must give one answer.

    The profile's Conformance testing section defines compliant as every MUST satisfied, so a file carrying
    only SHOULD violations is compliant unless --strict says to count them.
    """
    clean = write_model()
    assert cli.verdict(check_file(clean)).endswith("-> compliant")

    warn_only = write_model(name="test_part.glb")
    text = cli.verdict(check_file(warn_only))
    assert "-> compliant; 1 WARN to review" in text and "File naming" in text
    assert "not compliant under --strict" in cli.verdict(check_file(warn_only), strict=True)
    assert cli.main([str(warn_only)]) == 0
    assert cli.main(["--strict", str(warn_only)]) == 1

    failing = write_model(lambda g: g["asset"].pop("generator"))
    assert "-> not compliant: a MUST is violated in Authoring toolchain" in cli.verdict(check_file(failing))
    assert cli.main([str(failing)]) == 1
    capsys.readouterr()


def test_tally_uses_the_same_words_as_the_marks(write_model):
    text = cli.verdict(check_file(write_model(name="test_part.glb")))
    tally = text.splitlines()[0]
    assert "checks:" in tally
    for word in ("passed", "to review", "undecided", "not applicable", "ok", "note"):
        assert word not in tally
    assert "PASS" in tally and "WARN" in tally


def test_every_section_has_a_title(write_model):
    """A rule added without a TITLES entry would print a bare section name."""
    out = cli.render(write_model(), check_file(write_model()), verbose=False, quiet=False)
    headers = [line for line in out.splitlines() if line.startswith("  ") and line[2:].split(":")[0] in cli.TITLES]
    assert headers
    for line in headers:
        assert line.split(":", 1)[1].strip(), f"untitled section: {line!r}"
    assert {f.section for f in check_file(write_model())} <= set(cli.TITLES)


def test_legend_prints_once_per_run(write_model, capsys):
    a, b = write_model(), write_model(name="other_part.visual.glb")
    cli.main([str(a), str(b)])
    out = capsys.readouterr().out
    assert out.count("marks:") == 1
    assert out.count("-> compliant") == 2
    for mark, _ in cli.LEGEND:
        assert f"  {mark}  " in out


def test_base_part_without_a_datum_point_fails(write_model):
    def mutate(g):
        p = _packet(g)
        p["gltfrp:partRole"] = "base"
        p.pop("gltfrp:datumPoint")
    path = write_model(mutate)
    assert "Datum specification" in failures(path)


def test_component_without_a_datum_point_only_warns(write_model):
    path = write_model(lambda g: _packet(g).pop("gltfrp:datumPoint"))
    assert failures(path) == set()
    assert "Datum specification" in warnings(path)


def test_derived_datum_point_fails(write_model):
    """A computed property references nothing and moves with the geometry."""
    path = write_model(
        lambda g: _packet(g).update({"gltfrp:datumPoint": "the center of mass"}))
    assert "Datum specification" in failures(path)


def test_naming_a_source_does_not_excuse_a_derived_datum_point(write_model):
    """The profile has no exception: the datum point is a feature of the part."""
    def mutate(g):
        p = _packet(g)
        p["gltfrp:datumPoint"] = "the center of mass"
        p["gltfrp:datumDerivedFrom"] = "hull CAD rev C, empty configuration"
    path = write_model(mutate)
    assert "Datum specification" in failures(path)


def test_superseded_datum_properties_warn(write_model):
    """The ordered-list form Datum specification used to define is no longer part of the profile."""
    path = write_model(lambda g: _packet(g).update(
        {"gltfrp:datumFeature": {"@list": ["mounting face"]}}))
    assert "Datum specification" in warnings(path)
