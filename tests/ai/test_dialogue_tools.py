from types import MappingProxyType

import pytest

from api.ai.dialogue import (
    DialogueLimits,
    DialogueProposal,
    ToolCall,
    ToolError,
    ToolErrorCode,
    ToolResult,
)


def test_tool_call_decodes_explicit_json_and_freezes_arguments() -> None:
    call = ToolCall.from_json('{"name":"find_hardware","arguments":{"query":"петля"}}')

    assert call == ToolCall(name="find_hardware", arguments={"query": "петля"})
    assert isinstance(call.arguments, MappingProxyType)
    with pytest.raises(TypeError):
        call.arguments["query"] = "направляющая"  # type: ignore[index]


def test_invalid_json_and_missing_arguments_return_structured_errors() -> None:
    invalid_json = ToolCall.from_json("{")
    missing_arguments = ToolCall.from_json('{"name":"find_hardware"}')

    assert invalid_json == ToolError(
        code=ToolErrorCode.INVALID_JSON,
        message="Аргументы инструмента должны быть корректным JSON-объектом",
    )
    assert missing_arguments == ToolError(
        code=ToolErrorCode.MISSING_ARGUMENTS,
        message="Для вызова инструмента требуется объект arguments",
    )


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        pytest.param(
            '{"arguments":{}}',
            ToolError(
                code=ToolErrorCode.MISSING_NAME,
                message="Для вызова инструмента требуется непустое имя",
            ),
            id="missing-name",
        ),
        pytest.param(
            '{"name":"","arguments":{}}',
            ToolError(
                code=ToolErrorCode.MISSING_NAME,
                message="Для вызова инструмента требуется непустое имя",
            ),
            id="empty-name",
        ),
        pytest.param(
            '{"name":"find_hardware","arguments":[]}',
            ToolError(
                code=ToolErrorCode.INVALID_ARGUMENTS,
                message="Поле arguments должно быть JSON-объектом",
            ),
            id="array-arguments",
        ),
        pytest.param(
            '{"name":"find_hardware","arguments":{"value":NaN}}',
            ToolError(
                code=ToolErrorCode.INVALID_ARGUMENTS,
                message="Поле arguments должно содержать только JSON-значения",
            ),
            id="nan-argument",
        ),
        pytest.param(
            '{"name":"find_hardware","arguments":{"value":Infinity}}',
            ToolError(
                code=ToolErrorCode.INVALID_ARGUMENTS,
                message="Поле arguments должно содержать только JSON-значения",
            ),
            id="positive-infinity-argument",
        ),
        pytest.param(
            '{"name":"find_hardware","arguments":{"value":-Infinity}}',
            ToolError(
                code=ToolErrorCode.INVALID_ARGUMENTS,
                message="Поле arguments должно содержать только JSON-значения",
            ),
            id="negative-infinity-argument",
        ),
    ],
)
def test_malformed_tool_calls_return_structured_errors(
    raw: str, expected: ToolError
) -> None:
    assert ToolCall.from_json(raw) == expected


def test_tool_contracts_do_not_accept_raw_json_payloads() -> None:
    with pytest.raises(ValueError, match="arguments"):
        ToolCall(name="find_hardware", arguments='{"query":"петля"}')  # type: ignore[arg-type]
    with pytest.raises(ValueError, match="payload"):
        ToolResult(name="find_hardware", payload='{"items":[]}')  # type: ignore[arg-type]


def test_dialogue_limits_are_positive_integer_bounds_with_safe_defaults() -> None:
    assert DialogueLimits() == DialogueLimits(
        max_iterations=1,
        max_parallel_calls=1,
        max_history_items=1,
        max_output_tokens=1,
        max_result_bytes=1,
    )

    with pytest.raises(ValueError, match="max_iterations"):
        DialogueLimits(max_iterations=0)
    with pytest.raises(ValueError, match="max_result_bytes"):
        DialogueLimits(max_result_bytes=float("inf"))  # type: ignore[arg-type]


def test_proposal_is_only_an_immutable_patch_without_persistence_state() -> None:
    source_patch = {"dimensions.width_mm": 600}

    proposal = DialogueProposal(patch=source_patch)
    source_patch["dimensions.width_mm"] = 800

    assert proposal.patch == {"dimensions.width_mm": 600}
    assert isinstance(proposal.patch, MappingProxyType)
    assert not hasattr(proposal, "save")
    assert not hasattr(proposal, "persist")
