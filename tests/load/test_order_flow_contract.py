"""Offline contract tests for the deterministic order-flow workload definition."""

from __future__ import annotations

import json
import re
from pathlib import Path
from uuid import UUID

import pytest

SCRIPT_PATH = Path(__file__).with_name("order-flow.js")
EXPECTED_SCENARIOS = {
    "anonymous_upload",
    "authenticated_bom_edit",
    "ai_extraction",
    "cam_job",
    "artifact_download",
    "backlog",
}
EXPECTED_REQUESTS = {
    "anonymous_upload": ("POST", "/api/v1/orders/anonymous", "anonymous"),
    "authenticated_bom_edit": ("PATCH", "/api/v1/orders/{order_id}/bom", "required"),
    "ai_extraction": ("POST", "/api/v1/spec/extract-from-image", "anonymous"),
    "cam_job": ("POST", "/api/v1/cam/dxf", "required"),
    "artifact_download": ("GET", "/api/v1/cam/jobs/{job_id}/download", "required"),
    "backlog": ("GET", "/api/v1/cam/jobs?limit=50&offset=0", "required"),
}


def test_scenarios_target_the_declared_order_flow_operations() -> None:
    definition = _definition()
    for name, (method, endpoint, auth) in EXPECTED_REQUESTS.items():
        scenario = definition["scenarios"][name]
        assert (scenario["method"], scenario["endpoint"], scenario["auth"]) == (
            method,
            endpoint,
            auth,
        )


def _definition() -> dict:
    """Read the JSON contract without importing k6 or making network calls."""
    source = SCRIPT_PATH.read_text(encoding="utf-8")
    match = re.search(
        r"const WORKLOAD_DEFINITION_JSON = String\.raw`(?P<payload>.*?)`;",
        source,
        flags=re.DOTALL,
    )
    assert match, "order-flow.js must contain the embedded JSON workload contract"
    return json.loads(match.group("payload"))


def test_workload_script_is_local_k6_module() -> None:
    source = SCRIPT_PATH.read_text(encoding="utf-8")
    assert "from \"k6/http\"" in source
    assert "from \"k6\"" in source
    assert "from \"k6/execution\"" not in source
    assert "playwright" not in source.lower()
    assert "Math.random" not in source
    assert "Date.now" not in source
    assert "production" not in source.lower()


def test_definition_has_expected_scenarios_and_human_gate() -> None:
    definition = _definition()
    assert definition["version"] == 1
    assert set(definition["scenarios"]) == EXPECTED_SCENARIOS
    assert definition["human_gates"] == ["measured_capacity", "slo_approval"]
    assert definition["approval_status"] == "deferred"


def test_each_scenario_has_deterministic_arrival_config() -> None:
    definition = _definition()
    for name, scenario in definition["scenarios"].items():
        assert scenario["executor"] == "constant-arrival-rate", name
        assert isinstance(scenario["rate"], int) and scenario["rate"] > 0
        assert scenario["timeUnit"] == "1s"
        assert re.fullmatch(r"[1-9][0-9]*s", scenario["duration"]), name
        assert scenario["preAllocatedVUs"] > 0
        assert scenario["maxVUs"] >= scenario["preAllocatedVUs"]
        assert scenario["method"] in {"GET", "POST", "PATCH"}
        assert scenario["endpoint"].startswith("/api/v1/")
        assert scenario["auth"] in {"anonymous", "required"}


def test_thresholds_cover_every_scenario_without_claiming_measurements() -> None:
    definition = _definition()
    thresholds = definition["thresholds"]
    assert set(thresholds) == {
        "http_req_failed",
        *[f"http_req_duration{{scenario:{name}}}" for name in EXPECTED_SCENARIOS],
    }
    assert thresholds["http_req_failed"] == ["rate<0.01"]
    for name in EXPECTED_SCENARIOS:
        values = thresholds[f"http_req_duration{{scenario:{name}}}"]
        assert len(values) == 1
        assert re.fullmatch(r"p\(95\)<[1-9][0-9]*", values[0])
    assert "measured" not in json.dumps(thresholds).lower()


def test_fixtures_are_valid_and_payloads_are_static() -> None:
    definition = _definition()
    fixtures = definition["fixtures"]
    for field in ("order_id", "job_id"):
        UUID(fixtures[field])
    assert fixtures["image_base64"]
    assert fixtures["anonymous_order"]["customer_ref"] == "load-anonymous"
    assert fixtures["bom_patch"]["dimensions"]["width_mm"] == 600
    assert fixtures["cam_job"]["panels"]


@pytest.mark.parametrize("name", sorted(EXPECTED_SCENARIOS))
def test_script_exports_every_scenario_executor(name: str) -> None:
    source = SCRIPT_PATH.read_text(encoding="utf-8")
    assert re.search(rf"export function {name}\s*\(", source)
