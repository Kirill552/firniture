import json
from pathlib import Path

import pytest

from api.ai.evaluation import (
    REQUIRED_HUMAN_CONTROL_ARTIFACTS,
    EvaluationManifest,
    EvaluationScoreCalculator,
    ManifestValidationError,
)


def test_allows_promotion_for_approved_real_dataset_that_meets_thresholds() -> None:
    manifest = EvaluationManifest.from_dict(
        {
            "schema_version": "1.0",
            "dataset": {
                "classification": "real_anonymized",
                "approved": True,
                "fixture_ids": ["cabinet-001"],
                "approval_reference": "governance/dataset-review-2026-07-12",
            },
            "metrics": [
                {
                    "name": "dimension_accuracy",
                    "direction": "minimum",
                    "threshold": 0.95,
                    "threshold_reference": "governance/thresholds-v1",
                }
            ],
            "owner_confirmation": {
                "confirmed": True,
                "owner": "ai-quality-owner",
                "confirmation_reference": "governance/owner-confirmation-2026-07-12",
            },
        }
    )

    scorecard = EvaluationScoreCalculator(manifest).calculate({"dimension_accuracy": 0.97})

    assert scorecard.promotion_allowed is True
    assert scorecard.metric_results[0].passed is True
    assert REQUIRED_HUMAN_CONTROL_ARTIFACTS == (
        "approved_real_anonymized_fixture_set",
        "metric_thresholds",
        "owner_confirmation",
    )


def test_pending_scaffolding_manifest_blocks_promotion_without_human_artifacts() -> None:
    manifest_path = Path(__file__).parents[1] / "fixtures" / "ai" / "manifest.json"
    manifest = EvaluationManifest.from_dict(json.loads(manifest_path.read_text(encoding="utf-8")))

    scorecard = EvaluationScoreCalculator(manifest).calculate({})

    assert scorecard.promotion_allowed is False
    assert set(scorecard.blocking_reasons) >= {
        "dataset_is_not_real_anonymized",
        "dataset_not_approved",
        "dataset_has_no_fixtures",
        "dataset_has_no_approval_reference",
        "metric_has_no_approved_threshold:dimension_accuracy",
        "owner_confirmation_missing",
        "metric_not_observed:dimension_accuracy",
    }


def test_synthetic_dataset_cannot_be_promoted_even_when_other_controls_are_present() -> None:
    manifest = EvaluationManifest.from_dict(
        {
            "schema_version": "1.0",
            "dataset": {
                "classification": "synthetic",
                "approved": True,
                "fixture_ids": ["synthetic-cabinet-001"],
                "approval_reference": "governance/dataset-review",
            },
            "metrics": [
                {
                    "name": "dimension_accuracy",
                    "direction": "minimum",
                    "threshold": 0.95,
                    "threshold_reference": "governance/thresholds-v1",
                }
            ],
            "owner_confirmation": {
                "confirmed": True,
                "owner": "ai-quality-owner",
                "confirmation_reference": "governance/owner-confirmation",
            },
        }
    )

    scorecard = EvaluationScoreCalculator(manifest).calculate({"dimension_accuracy": 1.0})

    assert scorecard.promotion_allowed is False
    assert scorecard.blocking_reasons == ("dataset_is_not_real_anonymized",)


def test_scorecard_blocks_promotion_when_declared_metric_misses_threshold() -> None:
    manifest = EvaluationManifest.from_dict(
        {
            "schema_version": "1.0",
            "dataset": {
                "classification": "real_anonymized",
                "approved": True,
                "fixture_ids": ["cabinet-001"],
                "approval_reference": "governance/dataset-review",
            },
            "metrics": [
                {
                    "name": "dimension_accuracy",
                    "direction": "minimum",
                    "threshold": 0.95,
                    "threshold_reference": "governance/thresholds-v1",
                }
            ],
            "owner_confirmation": {
                "confirmed": True,
                "owner": "ai-quality-owner",
                "confirmation_reference": "governance/owner-confirmation",
            },
        }
    )

    scorecard = EvaluationScoreCalculator(manifest).calculate({"dimension_accuracy": 0.94})

    assert scorecard.promotion_allowed is False
    assert scorecard.metric_results[0].passed is False
    assert scorecard.blocking_reasons == ("metric_threshold_not_met:dimension_accuracy",)



def test_scorecard_blocks_nonfinite_observed_score() -> None:
    manifest = EvaluationManifest.from_dict(
        {
            "schema_version": "1.0",
            "dataset": {
                "classification": "real_anonymized",
                "approved": True,
                "fixture_ids": ["cabinet-001"],
                "approval_reference": "governance/dataset-review",
            },
            "metrics": [
                {
                    "name": "dimension_accuracy",
                    "direction": "minimum",
                    "threshold": 0.95,
                    "threshold_reference": "governance/thresholds-v1",
                }
            ],
            "owner_confirmation": {
                "confirmed": True,
                "owner": "ai-quality-owner",
                "confirmation_reference": "governance/owner-confirmation",
            },
        }
    )

    scorecard = EvaluationScoreCalculator(manifest).calculate({"dimension_accuracy": float("inf")})

    assert scorecard.promotion_allowed is False
    assert scorecard.blocking_reasons == ("metric_not_observed:dimension_accuracy",)


def test_rejects_nonfinite_declared_threshold() -> None:
    with pytest.raises(ManifestValidationError, match="threshold должен быть конечным числом"):
        EvaluationManifest.from_dict(
            {
                "schema_version": "1.0",
                "dataset": {
                    "classification": "real_anonymized",
                    "approved": True,
                    "fixture_ids": ["cabinet-001"],
                },
                "metrics": [
                    {
                        "name": "dimension_accuracy",
                        "direction": "minimum",
                        "threshold": float("inf"),
                    }
                ],
            }
        )


def test_rejects_unsupported_manifest_schema_version() -> None:
    with pytest.raises(ManifestValidationError, match="Неподдерживаемая версия манифеста"):
        EvaluationManifest.from_dict(
            {
                "schema_version": "2.0",
                "dataset": {"classification": "real_anonymized", "fixture_ids": []},
                "metrics": [],
            }
        )
