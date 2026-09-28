"""Tests for `gltf-summary`.

It describes rather than judges, so these check that what it reports matches the
file, not that it reaches a verdict. The one behaviour worth pinning hard is the
composed bounding box: a node transform changes where geometry lands, and that
is invisible in the accessor bounds the file publishes.
"""

from gltf_robotics.summary import fmt, main, origin_placement, render, summarize


def test_describes_the_baseline(write_model):
    s = summarize(write_model())

    assert s["container"] == ".glb"
    assert s["version"] == "2.0"
    assert s["has_manifest"] is True
    assert len(s["scenes"]) == 1
    assert s["default_scene"] == 0

    assert len(s["nodes"]) == 1
    node = s["nodes"][0]
    assert node["name"] == "test_part"
    assert node["is_root"] is True
    assert node["transform_keys"] == []

    assert len(s["primitives"]) == 1
    prim = s["primitives"][0]
    assert prim["attributes"] == ["NORMAL", "POSITION", "TEXCOORD_0"]
    assert prim["material"] == "Housing"
    assert prim["mode"] == 4
    # The square is 1 x 1 in XY and flat in Z, so no transform means no change.
    assert prim["local_bbox"] == prim["world_bbox"]

    assert s["extent"] == ([-0.5, -0.5, 0.0], [0.5, 0.5, 0.0])


def test_origin_is_centred_on_the_baseline(write_model):
    s = summarize(write_model())
    x, y, z = s["origin_placement"]
    assert x == 0.5 and y == 0.5
    assert z is None, "a flat axis has no placement to report"


def test_a_root_translation_moves_the_geometry(write_model):
    """The accessor bounds do not change; where the part lands does."""
    path = write_model(lambda g: g["nodes"][0].update(translation=[0.0, 5.0, 0.0]))
    s = summarize(path)

    assert s["nodes"][0]["transform_keys"] == ["translation"]
    prim = s["primitives"][0]
    assert prim["local_bbox"] == ([-0.5, -0.5, 0.0], [0.5, 0.5, 0.0])
    assert prim["world_bbox"][0][1] == 4.5
    assert prim["world_bbox"][1][1] == 5.5

    # And the origin is now nowhere near the geometry, which is the point.
    assert s["origin_placement"][1] == -4.5
    assert "OUTSIDE the geometry" in render(s)


def test_a_child_node_is_composed_through_its_parent(write_model):
    def mutate(g):
        g["nodes"][0]["children"] = [1]
        g["nodes"][0]["translation"] = [1.0, 0.0, 0.0]
        g["nodes"].append({"name": "tip", "mesh": 0, "translation": [2.0, 0.0, 0.0]})

    s = summarize(write_model(mutate))
    assert [n["is_root"] for n in s["nodes"]] == [True, False]
    parent, child = s["primitives"]
    assert parent["world_bbox"][1][0] == 1.5          # 0.5 shifted by 1
    assert child["world_bbox"][1][0] == 3.5           # 0.5 shifted by 1 + 2


def test_an_absent_metallic_factor_is_reported_as_the_glTF_default(write_model):
    path = write_model(lambda g: g["materials"][0]["pbrMetallicRoughness"].pop("metallicFactor"))
    s = summarize(path)
    assert s["materials"][0]["metallicFactor"] is None
    assert "absent, so glTF's default of 1.0 applies" in render(s)


def test_an_empty_export_is_visible(write_model):
    """The failure mode that prompted this tool: a valid file with no geometry."""
    def mutate(g):
        g["scenes"] = [{"name": "Scene"}]
        g["nodes"] = []
        g["meshes"] = []

    s = summarize(write_model(mutate))
    assert s["nodes"] == []
    assert s["primitives"] == []
    assert s["extent"] is None
    assert s["origin_placement"] is None
    render(s)  # must not raise on a file with nothing in it


def test_fmt_snaps_float_noise_to_zero():
    assert fmt([5.551e-18, 1.0, -0.0]) == "[0, 1, 0]"


def test_origin_placement_handles_a_flat_axis():
    assert origin_placement([-1.0, 0.0, -2.0], [3.0, 0.0, 2.0]) == [0.25, None, 0.5]


def test_cli_succeeds_on_a_file_and_fails_on_a_missing_one(write_model, capsys):
    assert main([str(write_model())]) == 0
    assert "test_part" in capsys.readouterr().out
    assert main(["no/such/file.glb"]) == 1


def test_cli_json_is_machine_readable(write_model, capsys):
    import json

    assert main([str(write_model()), "--json"]) == 0
    payload = json.loads(capsys.readouterr().out)
    assert len(payload) == 1
    assert payload[0]["primitives"][0]["material"] == "Housing"


def test_the_geometry_block_says_whether_a_transform_was_involved(write_model):
    """The 'derived' heading confused a reader when nothing was actually derived."""
    plain = render(summarize(write_model()))
    assert "unchanged from the vertex min/max above" in plain
    assert "node transform" not in plain.split("geometry in")[1]

    moved = render(summarize(
        write_model(lambda g: g["nodes"][0].update(translation=[0.0, 5.0, 0.0]))))
    assert "before any node transform" in moved
    assert "after the node transform above" in moved
    assert "unchanged from the vertex min/max above" not in moved


def test_no_material_is_reported_without_editorial(write_model):
    """What an absent material renders as is gltf-check's section 7, not this tool's."""
    def mutate(g):
        g["meshes"][0]["primitives"][0].pop("material")
        g["materials"] = []

    out = render(summarize(write_model(mutate)))
    assert "materials: none" in out
    assert "white metal" not in out


def test_an_unused_material_still_counts_as_present(write_model):
    """'materials: none' describes the materials array, not what the primitives use."""
    s = summarize(write_model(lambda g: g["meshes"][0]["primitives"][0].pop("material")))
    assert s["primitives"][0]["material"] is None
    assert [m["name"] for m in s["materials"]] == ["Housing"]
    out = render(s)
    assert "material: none" in out        # the primitive
    assert "materials: 1 total" in out    # the array


def test_reports_the_midpoint_and_the_vertex_mean_separately(write_model):
    """Two different points, and the fixture is asymmetric enough to tell them apart."""
    def mutate(g):
        # Three of the four corners stay; one is pulled out to +x, so the extreme
        # moves twice as far as the average does.
        g["accessors"][0]["max"] = [1.5, 0.5, 0.0]

    def buffer_mutate(g, buf):
        import struct
        verts = [(-0.5, -0.5, 0.0), (1.5, -0.5, 0.0), (-0.5, 0.5, 0.0), (0.5, 0.5, 0.0)]
        return struct.pack("<12f", *[c for v in verts for c in v]) + buf[48:]

    s = summarize(write_model(mutate, buffer_mutate=buffer_mutate))
    prim = s["primitives"][0]
    assert prim["vertex_count"] == 4
    assert prim["midpoint"] == [0.5, 0.0, 0.0]          # (-0.5 + 1.5) / 2
    assert prim["vertex_mean"][0] == 0.25               # (-0.5 + 1.5 - 0.5 + 0.5) / 4
    assert prim["midpoint"] != prim["vertex_mean"]

    out = render(s)
    assert "bbox midpoint" in out
    assert "vertex mean" in out
    assert "vertex min/max" in out


def test_both_origin_readings_appear_only_when_they_can_differ(write_model):
    """A reader hit a real contradiction: bbox midpoint nonzero, yet origin at 0.50.

    The two were measured in different spaces four lines apart with no labels. With
    a node transform the report must give both and say which is which; without one
    there is nothing to disambiguate and a second line would be noise.
    """
    identity = render(summarize(write_model()))
    assert identity.count("  geometry in ") == 1
    assert "NODE space, which is also SCENE space here" in identity
    assert "-> node space and scene space coincide" in identity

    s = summarize(write_model(lambda g: g["nodes"][0].update(translation=[0.0, 5.0, 0.0])))
    moved = render(s)
    assert moved.count("  geometry in ") == 2
    assert "geometry in NODE space --" in moved
    assert "geometry in SCENE space --" in moved
    assert "exactly one node with no transform" in moved

    # The node's transform is printed with its values, because it is what accounts
    # for the difference between the two blocks.
    assert "translation [0, 5, 0]" in moved

    # The node reading is the untransformed one; the scene reading is not.
    assert s["local_origin_placement"][1] == 0.5
    assert s["origin_placement"][1] == -4.5


def test_every_transform_component_is_printed_even_when_it_is_the_default(write_model):
    """glTF omits a component equal to its default, and 5.5 constrains presence.

    So the report states all three either way, and says which the file actually
    carried -- an absent `rotation` and an identity `rotation` are the same
    geometry and a different verdict under 5.5.
    """
    plain = render(summarize(write_model()))
    for line in ("translation [0, 0, 0]", "rotation    [0, 0, 0, 1]", "scale       [1, 1, 1]"):
        assert line in plain
    assert plain.count("absent, so glTF's default applies") == 3
    assert "stated in the file" not in plain

    moved = render(summarize(
        write_model(lambda g: g["nodes"][0].update(rotation=[0.0, 0.0, 0.0, 1.0]))))
    assert "rotation    [0, 0, 0, 1]" in moved
    assert "stated in the file" in moved, "an identity rotation is still a stated one"


def test_a_matrix_node_reports_the_matrix_instead_of_trs(write_model):
    ident = [1, 0, 0, 0, 0, 1, 0, 0, 0, 0, 1, 0, 2, 0, 0, 1]
    out = render(summarize(write_model(lambda g: g["nodes"][0].update(matrix=ident))))
    assert "matrix" in out
    assert "it replaces translation, rotation and scale" in out
    assert "translation [" not in out
