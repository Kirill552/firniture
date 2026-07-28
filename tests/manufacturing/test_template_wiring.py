from api.manufacturing.spec_builder import CabinetInput, CabinetType, build_spec

def _hinge_ops(spec):
    return [
        operation
        for panel in spec.panels
        for operation in panel.operations
        if getattr(operation, "diameter_mm", 0) >= 20
    ]


def _input(**kwargs):
    return CabinetInput(
        cabinet_type=CabinetType.WALL,
        width_mm=600,
        height_mm=720,
        depth_mm=300,
        door_count=1,
        hinge_type="catalog-hinge",
        **kwargs,
    )


def test_inset_catalog_position_changes_grid_coordinates():
    overlay = build_spec(_input()).spec
    inset = build_spec(_input(
        hinge_position_type="петля вкладная",
        hinge_params={"cup_diameter_mm": 35},
    )).spec
    overlay_ops = _hinge_ops(overlay)
    inset_ops = _hinge_ops(inset)
    assert [(op.x_mm, op.y_mm) for op in overlay_ops] != [
        (op.x_mm, op.y_mm) for op in inset_ops
    ]


def test_mini_catalog_position_uses_26mm_cup():
    result = build_spec(_input(
        hinge_position_type="петля mini",
        hinge_params={"cup_diameter_mm": 26},
    ))
    assert {op.diameter_mm for op in _hinge_ops(result.spec)} == {26.0}
    assert result.provenance["hinges"]["template"] == "hinge_26mm_mini"
    assert result.provenance["hinges"]["source"] == "catalog"


def test_review_position_uses_default_template_and_marks_provenance():
    result = build_spec(_input(
        hinge_position_type="петля вкладная",
        hinge_params={"cup_diameter_mm": 35, "needs_review": True},
    ))
    assert result.provenance["hinges"]["template"] == "hinge_35mm_overlay"
    assert result.provenance["hinges"]["source"] == "default"
    assert result.provenance["hinges"]["needs_review"] is True


def test_explicit_template_without_catalog_params_keeps_default_behavior():
    result = build_spec(_input(hinge_template_id="hinge_35mm_inset"))
    assert result.provenance["hinges"]["template"] == "hinge_35mm_overlay"
