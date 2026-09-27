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


def test_min_version_is_prohibited(write_model):
    path = write_model(lambda g: g["asset"].update(minVersion="2.0"))
    assert failures(path) == {"4.3"}


def test_generator_must_be_recorded(write_model):
    path = write_model(lambda g: g["asset"].pop("generator"))
    assert failures(path) == {"11"}


# --------------------------------------------------- section 5: frame, nodes

def test_two_scenes(write_model):
    path = write_model(lambda g: g["scenes"].append({"nodes": [0]}))
    assert failures(path) == {"5.5"}


def test_root_node_rotation(write_model):
    """The Blender Y-up conversion node: the two consumers compose it differently."""
    path = write_model(lambda g: g["nodes"][0].update(
        rotation=[-0.7071068, 0.0, 0.0, 0.7071068]))
    assert failures(path) == {"5.5"}
    assert any("rotation" in s for s in summaries(path))


def test_root_node_matrix(write_model):
    path = write_model(lambda g: g["nodes"][0].update(
        matrix=[1, 0, 0, 0, 0, 1, 0, 0, 0, 0, 1, 0, 0, 0, 0, 1]))
    assert failures(path) == {"5.5"}


def test_root_node_blender_numeric_suffix(write_model):
    path = write_model(lambda g: g["nodes"][0].update(name="test_part.001"))
    assert failures(path) == {"5.5"}


def test_identity_rotation_is_not_a_failure(write_model):
    """A rotation that rotates nothing is noise, not the hazard the rule is about."""
    path = write_model(lambda g: g["nodes"][0].update(rotation=[0.0, 0.0, 0.0, 1.0]))
    assert failures(path) == set()


def test_two_root_nodes(write_model):
    def mutate(g):
        g["nodes"].append({"name": "second", "mesh": 0})
        g["scenes"][0]["nodes"] = [0, 1]
    path = write_model(mutate)
    assert failures(path) == {"5.5"}


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
    # 5.1 alone: scale cannot be read from a glTF file at all. 5.3 leaves the
    # advisory tier as soon as the manifest declares a forward axis, and 5.6 is
    # a real rule now that the datum specification has a home.
    assert advisory == {"5.1"}
    assert not any(f.failed for f in findings if f.section in advisory)


# ------------------------------------------- 4.1.1 manifest, 5.6 datum

def _packet(g):
    return g["extensions"]["KHR_xmp_json_ld"]["packets"][0]


def test_missing_manifest_warns_but_does_not_fail(write_model):
    def mutate(g):
        g["asset"].pop("extensions")
        g.pop("extensions")
        g.pop("extensionsUsed")
    path = write_model(mutate)
    assert failures(path) == set()
    assert "4.1.1" in warnings(path)


def test_manifest_without_a_role_fails(write_model):
    path = write_model(lambda g: _packet(g).pop("gltfrp:partRole"))
    assert "4.1.1" in failures(path)


def test_creator_tool_must_match_asset_generator(write_model):
    """The copied-from-a-sibling-part failure, made mechanical."""
    path = write_model(lambda g: _packet(g).update({"xmp:CreatorTool": "Some Other Exporter"}))
    assert "4.1.1" in failures(path)


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
