"""Контракт системного промпта диалога технолога."""

from api.routers import TECHNOLOGIST_SYSTEM_PROMPT


def test_technologist_prompt_keeps_markers_and_tool_names() -> None:
    prompt = TECHNOLOGIST_SYSTEM_PROMPT

    for marker in ("[BUTTONS]", "[COMPLETE]", "[SPEC_JSON]", "[PARAM_UPDATE]"):
        assert marker in prompt

    for tool_name in (
        "calculate_panels",
        "find_hardware",
        "calculate_hardware_qty",
        "get_hardware_details",
        "check_hardware_compatibility",
    ):
        assert tool_name in prompt


def test_technologist_prompt_prioritizes_estimate_and_workshop_rules() -> None:
    prompt = TECHNOLOGIST_SYSTEM_PROMPT

    assert "Быстрая прикидка — режим по умолчанию" in prompt
    assert "Целая кухня из многих модулей" in prompt
    assert "Съёмную полку сужают на 1,5 мм с каждой стороны" in prompt
    assert "Типовой зазор фасада — 4 мм" in prompt
    assert "множитель наценки" in prompt
