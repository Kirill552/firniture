from etl_pipeline.param_extraction import extract_parameters


def test_extracts_cup_and_angle_from_table_rows():
    result = extract_parameters("", [["Диаметр чашки", "35", "Угол открывания", "110°"]])
    assert result["cup_diameter_mm"] == "35"
    assert result["opening_angle_deg"] == "110"


def test_mount_type_comes_from_section_heading():
    result = extract_parameters("", [], "Мебельные петли накладные")
    assert result["mount_type"] == "накладная"


def test_rejects_impossible_cup():
    result = extract_parameters("", [["чашка", "40 мм"]])
    assert "cup_diameter_mm" not in result


def test_rejects_impossible_angle():
    result = extract_parameters("", [["угол открывания", "2600"]])
    assert "opening_angle_deg" not in result
