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


# ------------------------------------------------------- section 4: delivery

def test_part_name_must_be_snake_case(write_model):
    path = write_model(name="TestPart.visual.glb")
    assert "4.1" in failures(path)


def test_filename_without_visual_suffix_warns(write_model):
    path = write_model(name="test_part.glb")
    assert "4.1" in warnings(path)
    assert failures(path) == set()


def test_min_version_warns(write_model):
    """4.3 relaxed this to SHOULD NOT, so it reviews rather than fails."""
    path = write_model(lambda g: g["asset"].update(minVersion="2.0"))
    assert failures(path) == set()
    assert "4.3" in warnings(path)


def test_generator_must_be_recorded(write_model):
    path = write_model(lambda g: g["asset"].pop("generator"))
    assert failures(path) == {"11"}


# ------------------------------------- section 5: coordinate systems, nodes

def test_declared_axes_must_match_the_profile(write_model):
    """5.2 is a decided MUST, so a manifest declaring glTF's convention fails."""
    from conftest import manifest
    path = write_model(lambda g: g["extensions"]["KHR_xmp_json_ld"].update(
        packets=[manifest(**{"gltfrp:up": "+Y"})]))
    assert "5.2" in failures(path)
    detail = " ".join(f.detail for f in check_file(path) if f.level == FAIL)
    assert "+Z" in detail


def test_undeclared_axes_are_reported_once_by_4_1_1_not_twice(write_model):
    """One omission, one defect. 4.1.4 owns presence; 5.2 owns the values."""
    from conftest import manifest
    packet = manifest()
    packet.pop("gltfrp:forward")
    packet.pop("gltfrp:up")
    path = write_model(lambda g: g["extensions"]["KHR_xmp_json_ld"].update(packets=[packet]))
    assert "4.1.4" in failures(path)
    assert "5.2" not in failures(path)
    assert "5.2" not in warnings(path)


def test_two_scenes(write_model):
    path = write_model(lambda g: g["scenes"].append({"nodes": [0]}))
    assert failures(path) == {"5.5"}


@pytest.mark.parametrize("key, value", [
    ("translation", [0.0, 0.5, 0.0]),
    ("rotation", [-0.7071068, 0.0, 0.0, 0.7071068]),
    ("scale", [2.0, 2.0, 2.0]),
    ("matrix", [1, 0, 0, 0, 0, 1, 0, 0, 0, 0, 1, 0, 0, 0, 0, 1]),
])
def test_any_node_transform_fails(write_model, key, value):
    """All four keys, so node space and scene space cannot come apart."""
    path = write_model(lambda g: g["nodes"][0].update({key: value}))
    assert failures(path) == {"5.5"}
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
    assert failures(path) == {"5.5"}


def test_several_transform_keys_are_reported_together(write_model):
    path = write_model(lambda g: g["nodes"][0].update(
        translation=[0.0, 0.5, 0.0], scale=[2.0, 2.0, 2.0]))
    assert failures(path) == {"5.5"}
    detail = " ".join(f.detail for f in check_file(path) if f.level == FAIL)
    assert "translation" in detail and "scale" in detail


def test_root_node_blender_numeric_suffix(write_model):
    path = write_model(lambda g: g["nodes"][0].update(name="test_part.001"))
    assert failures(path) == {"5.5"}


def test_two_root_nodes(write_model):
    def mutate(g):
        g["nodes"].append({"name": "second", "mesh": 0})
        g["scenes"][0]["nodes"] = [0, 1]
    path = write_model(mutate)
    assert failures(path) == {"5.5"}


def test_a_child_node_fails(write_model):
    """One node, no hierarchy: Gazebo bakes child transforms in, so structure is lost."""
    def mutate(g):
        g["nodes"][0]["children"] = [1]
        g["nodes"].append({"name": "tip", "mesh": 0})
    path = write_model(mutate)
    assert failures(path) == {"5.5"}
    detail = " ".join(f.detail for f in check_file(path) if f.level == FAIL)
    assert "child" in detail


def test_a_second_node_fails_even_unparented(write_model):
    """Two nodes is two nodes, whether or not the scene lists both."""
    path = write_model(lambda g: g["nodes"].append({"name": "spare", "mesh": 0}))
    assert failures(path) == {"5.5"}
    assert any("2 nodes, expected exactly 1" in s for s in summaries(path))


# ----------------------------------------------------- section 6: geometry

def test_non_triangle_primitive(write_model):
    path = write_model(lambda g: g["meshes"][0]["primitives"][0].update(mode=5))
    assert failures(path) == {"6"}


def test_missing_normals(write_model):
    path = write_model(lambda g: g["meshes"][0]["primitives"][0]["attributes"].pop("NORMAL"))
    assert failures(path) == {"6"}


def test_second_uv_set_is_permitted_for_a_lightmap(write_model):
    """Profile 6.1 permits TEXCOORD_1, and only for a baked occlusion lightmap."""
    path = write_model(
        lambda g: g["meshes"][0]["primitives"][0]["attributes"].update(TEXCOORD_1=2))
    assert failures(path) == set()


def test_third_uv_set_fails(write_model):
    path = write_model(
        lambda g: g["meshes"][0]["primitives"][0]["attributes"].update(
            TEXCOORD_1=2, TEXCOORD_2=2))
    assert failures(path) == {"6.1"}


def test_uv_outside_unit_range(write_model):
    path = write_model(lambda g: g["accessors"][2].update(min=[0.0, 0.0], max=[2.0, 1.0]))
    assert failures(path) == {"6.1"}


def _extra_primitive(g, material=0):
    """A second primitive on the same mesh, reusing the baseline's buffer views."""
    first = g["meshes"][0]["primitives"][0]
    g["meshes"][0]["primitives"].append(dict(first, material=material))


def test_two_primitives_sharing_a_material_fail(write_model):
    """A primitive exists to carry a distinct material; sharing one splits for no reason."""
    path = write_model(_extra_primitive)
    assert failures(path) == {"6.3"}
    detail = " ".join(f.detail for f in check_file(path) if f.level == FAIL)
    assert "Housing" in detail


def test_two_primitives_with_distinct_materials_pass(write_model):
    """The legitimate reason to have two: glTF gives a primitive at most one material."""
    def mutate(g):
        g["materials"].append(dict(g["materials"][0], name="Trim"))
        _extra_primitive(g, material=1)

    path = write_model(mutate)
    assert failures(path) == set()


# ---------------------------------------------------- section 7: materials

def test_primitive_without_material(write_model):
    path = write_model(lambda g: g["meshes"][0]["primitives"][0].pop("material"))
    assert failures(path) == {"7"}
    assert any("white metal" in f.detail for f in check_file(path))


def test_metalness_trap_with_no_texture_to_override(write_model):
    """metallicFactor unset means 1.0: a material that says nothing says metal."""
    path = write_model(
        lambda g: g["materials"][0]["pbrMetallicRoughness"].pop("metallicFactor"))
    assert failures(path) == {"7"}


def test_unset_metalness_with_orm_texture_is_only_a_warning(write_model):
    """The texture multiplies against the factor, so this is not decidable here."""
    def mutate(g):
        g["materials"][0]["pbrMetallicRoughness"].pop("metallicFactor")
        g["materials"][0]["pbrMetallicRoughness"]["metallicRoughnessTexture"] = {"index": 0}
    path = write_model(mutate)
    assert failures(path) == set()
    assert warnings(path) == {"7"}


def test_textured_material_without_base_colour(write_model):
    """The shape that terminates RViz: maps present, no diffuse to hand back."""
    def mutate(g):
        pbr = g["materials"][0]["pbrMetallicRoughness"]
        pbr.pop("baseColorTexture")
        g["materials"][0]["normalTexture"] = {"index": 0}
    path = write_model(mutate)
    # Only section 7. The map reused here is the baseline's PNG, so the texture
    # format rule is satisfied and must stay quiet.
    assert failures(path) == {"7"}
    assert any("RViz" in f.detail for f in check_file(path))


def test_normal_texture_scale_must_be_one(write_model):
    def mutate(g):
        g["materials"][0]["normalTexture"] = {"index": 0, "scale": 0.5}
    path = write_model(mutate)
    assert "7" in failures(path)


# ----------------------------------------------------- section 8: textures

def test_texture_over_2048(write_model):
    from conftest import pad4, png
    def buffer_mutate(g, buf):
        big = png(4096, 4)
        head = buf[: g["bufferViews"][4]["byteOffset"]]
        g["bufferViews"][4]["byteLength"] = len(big)
        return pad4(head + big)
    path = write_model(buffer_mutate=buffer_mutate)
    assert failures(path) == {"8"}


# ------------------------------------------------- section 9: transparency

def test_blend_is_prohibited(write_model):
    path = write_model(lambda g: g["materials"][0].update(alphaMode="BLEND"))
    assert failures(path) == {"9"}


def test_mask_requires_cutoff_half(write_model):
    def mutate(g):
        g["materials"][0].update(alphaMode="MASK", alphaCutoff=0.1)
    path = write_model(mutate)
    assert "9" in failures(path)


def test_mask_requires_alpha_in_the_base_colour(write_model):
    """The baseline's PNG is colour type 2, so MASK alone has nothing to threshold."""
    path = write_model(lambda g: g["materials"][0].update(alphaMode="MASK"))
    assert failures(path) == {"9"}
    assert any("binary alpha" in f.detail for f in check_file(path))


# --------------------------------------------- section 10: prohibited content

@pytest.mark.parametrize("extension", [
    "KHR_draco_mesh_compression",
    "KHR_texture_basisu",
    "KHR_texture_transform",
    "KHR_materials_pbrSpecularGlossiness",
])
def test_prohibited_extensions(write_model, extension):
    path = write_model(lambda g: g.update(extensionsUsed=[extension]))
    assert failures(path) == {"10"}


def test_extensions_required_is_prohibited_even_when_allowed_elsewhere(write_model):
    """The general case: a required extension a reader must refuse the file over."""
    path = write_model(lambda g: g.update(extensionsRequired=["KHR_materials_specular"],
                                          extensionsUsed=["KHR_materials_specular"]))
    assert failures(path) == {"10"}


@pytest.mark.parametrize("key", ["animations", "skins", "cameras"])
def test_prohibited_content(write_model, key):
    path = write_model(lambda g: g.update(**{key: [{}]}))
    assert failures(path) == {"10"}


# --------------------------------------------------------------- advisories

def test_undecided_rules_never_fail(write_model):
    """Profile section 2.4: a delivery cannot fail on a point marked Open."""
    from gltf_robotics.check.rules import ADVISORY
    findings = check_file(write_model())
    advisory = {f.section for f in findings if f.level == ADVISORY}
    # 5.1 alone: scale cannot be read from a glTF file at all. 5.2's axes are
    # decided now, so an undeclared axis is a WARN -- a MUST the file cannot
    # settle -- rather than an Open point, and 5.6 is a real rule now that the
    # datum specification has a home.
    assert advisory == {"5.1"}
    assert not any(f.failed for f in findings if f.section in advisory)


# ------------------------------------------- 4.1.4 manifest, 5.6 datum

def _packet(g):
    return g["extensions"]["KHR_xmp_json_ld"]["packets"][0]


def test_a_missing_manifest_fails(write_model):
    """Required since review decision 13: provenance cannot be reconstructed later.

    It was a SHOULD while the argument against was that no existing delivery
    carried one. That argument is withdrawn -- the existing files are not trusted
    and no rule is calibrated to them.
    """
    def mutate(g):
        g["asset"].pop("extensions")
        g.pop("extensions")
        g.pop("extensionsUsed")
    path = write_model(mutate)
    assert "4.1.4" in failures(path)
    # 5.2 has nothing to compare against and must not double-report the omission.
    assert "5.2" not in failures(path)


@pytest.mark.parametrize("key", ["gltfrp:partRole", "gltfrp:forward", "gltfrp:up"])
def test_each_required_manifest_property_fails_when_absent(write_model, key):
    """The three that record what no measurement can recover."""
    from conftest import manifest
    packet = manifest()
    packet.pop(key)
    path = write_model(lambda g: g["extensions"]["KHR_xmp_json_ld"].update(packets=[packet]))
    assert "4.1.4" in failures(path)
    assert any(key in f.summary for f in check_file(path) if f.level == FAIL)


def test_manifest_without_a_role_fails(write_model):
    path = write_model(lambda g: _packet(g).pop("gltfrp:partRole"))
    assert "4.1.4" in failures(path)


def test_creator_tool_must_match_asset_generator(write_model):
    """The copied-from-a-sibling-part failure, made mechanical."""
    path = write_model(lambda g: _packet(g).update({"xmp:CreatorTool": "Some Other Exporter"}))
    assert "4.1.4" in failures(path)


def test_base_part_without_a_datum_fails(write_model):
    def mutate(g):
        p = _packet(g)
        p["gltfrp:partRole"] = "base"
        for k in ("gltfrp:datumFeature", "gltfrp:datumFeatureKind", "gltfrp:datumConstrains"):
            p.pop(k)
    path = write_model(mutate)
    assert "5.6" in failures(path)


def test_component_without_a_datum_only_warns(write_model):
    def mutate(g):
        p = _packet(g)
        for k in ("gltfrp:datumFeature", "gltfrp:datumFeatureKind", "gltfrp:datumConstrains"):
            p.pop(k)
    path = write_model(mutate)
    assert failures(path) == set()
    assert "5.6" in warnings(path)


def test_under_constrained_base_datum_fails(write_model):
    """Five of six degrees of freedom is not a coordinate system."""
    def mutate(g):
        p = _packet(g)
        p["gltfrp:partRole"] = "base"
        p["gltfrp:datumConstrains"] = {"@list": ["Tz Rx Ry", "Tx Ty", ""]}
    path = write_model(mutate)
    assert "5.6" in failures(path)
    assert any("under-constrained" in f.summary for f in check_file(path))


def test_doubly_constrained_datum_fails(write_model):
    def mutate(g):
        p = _packet(g)
        p["gltfrp:datumConstrains"] = {"@list": ["Tz Rx Ry", "Tx Ty Tz", "Rz"]}
    path = write_model(mutate)
    assert "5.6" in failures(path)


def test_feature_kind_must_be_a_situation_feature(write_model):
    """ISO 17450-1 closes the list to point, line, plane, helix."""
    path = write_model(
        lambda g: _packet(g).update({"gltfrp:datumFeatureKind": {"@list": ["silhouette", "line", "point"]}}))
    assert "5.6" in failures(path)


def test_mismatched_datum_list_lengths_fail(write_model):
    path = write_model(
        lambda g: _packet(g).update({"gltfrp:datumFeatureKind": {"@list": ["plane", "line"]}}))
    assert "5.6" in failures(path)


def test_forward_and_up_must_differ(write_model):
    path = write_model(lambda g: _packet(g).update({"gltfrp:up": "-X"}))
    assert "5.6" in failures(path)


def test_realized_pose_must_not_be_authored(write_model):
    """5.6: a derived quantity recorded beside its rule is two sources of truth."""
    path = write_model(
        lambda g: _packet(g).update({"gltfrp:realizedPose": {"@list": [0, 0, 0, 0, 0, 0]}}))
    assert "5.6" in failures(path)


# ------------------------------------------------------------ the CLI output

from gltf_robotics.check import cli  # noqa: E402


def test_verdict_agrees_with_exit_code(write_model, capsys):
    """The text verdict, the JSON flag and the exit code must give one answer.

    Profile 12.3 defines compliant as every MUST satisfied, so a file carrying
    only SHOULD violations is compliant unless --strict says to count them.
    """
    clean = write_model()
    assert cli.verdict(check_file(clean)).endswith("-> compliant")

    warn_only = write_model(name="test_part.glb")
    text = cli.verdict(check_file(warn_only))
    assert "-> compliant; 1 WARN to review" in text and "§4.1" in text
    assert "not compliant under --strict" in cli.verdict(check_file(warn_only), strict=True)
    assert cli.main([str(warn_only)]) == 0
    assert cli.main(["--strict", str(warn_only)]) == 1

    failing = write_model(lambda g: g["asset"].pop("generator"))
    assert "-> not compliant: a MUST is violated in §11" in cli.verdict(check_file(failing))
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
    """A rule added without a TITLES entry would print a bare section number."""
    out = cli.render(write_model(), check_file(write_model()), verbose=False, quiet=False)
    headers = [line for line in out.splitlines() if line.startswith("  §")]
    assert headers
    for line in headers:
        assert len(line.split(maxsplit=1)) == 2, f"untitled section: {line!r}"
    assert {f.section for f in check_file(write_model())} <= set(cli.TITLES)


def test_legend_prints_once_per_run(write_model, capsys):
    a, b = write_model(), write_model(name="other_part.visual.glb")
    cli.main([str(a), str(b)])
    out = capsys.readouterr().out
    assert out.count("marks:") == 1
    assert out.count("-> compliant") == 2
    for mark, _ in cli.LEGEND:
        assert f"  {mark}  " in out
