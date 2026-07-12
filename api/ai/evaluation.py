"""Fail-closed оценка качества AI-моделей перед production promotion."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from math import isfinite
from typing import Any, Literal, cast

MANIFEST_SCHEMA_VERSION = "1.0"
REQUIRED_HUMAN_CONTROL_ARTIFACTS = (
    "approved_real_anonymized_fixture_set",
    "metric_thresholds",
    "owner_confirmation",
)
MetricDirection = Literal["minimum", "maximum"]


class ManifestValidationError(ValueError):
    """Манифест оценки не соответствует поддерживаемой схеме."""


@dataclass(frozen=True)
class FixtureDataset:
    classification: str
    approved: bool
    fixture_ids: tuple[str, ...]
    approval_reference: str | None


@dataclass(frozen=True)
class DeclaredMetric:
    name: str
    direction: MetricDirection
    threshold: float | None
    threshold_reference: str | None


@dataclass(frozen=True)
class OwnerConfirmation:
    confirmed: bool
    owner: str | None
    confirmation_reference: str | None


@dataclass(frozen=True)
class EvaluationManifest:
    schema_version: str
    dataset: FixtureDataset
    metrics: tuple[DeclaredMetric, ...]
    owner_confirmation: OwnerConfirmation | None

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> EvaluationManifest:
        schema_version = _required_text(value, "schema_version")
        if schema_version != MANIFEST_SCHEMA_VERSION:
            raise ManifestValidationError(f"Неподдерживаемая версия манифеста: {schema_version}")

        dataset = _dataset(_required_object(value, "dataset"))
        metrics_value = value.get("metrics", [])
        if not isinstance(metrics_value, list):
            raise ManifestValidationError("Поле metrics должно быть списком")
        owner_value = value.get("owner_confirmation")
        return cls(
            schema_version=schema_version,
            dataset=dataset,
            metrics=tuple(_metric(item) for item in metrics_value),
            owner_confirmation=_owner_confirmation(owner_value),
        )


@dataclass(frozen=True)
class MetricResult:
    name: str
    value: float | None
    threshold: float | None
    direction: MetricDirection
    passed: bool


@dataclass(frozen=True)
class EvaluationScorecard:
    metric_results: tuple[MetricResult, ...]
    promotion_allowed: bool
    blocking_reasons: tuple[str, ...]


class EvaluationScoreCalculator:
    """Сопоставляет измерения с метриками, объявленными в манифесте."""

    def __init__(self, manifest: EvaluationManifest) -> None:
        self._manifest = manifest

    def calculate(self, observed_scores: Mapping[str, float]) -> EvaluationScorecard:
        metric_results = tuple(
            _metric_result(metric, observed_scores.get(metric.name)) for metric in self._manifest.metrics
        )
        blocking_reasons = _blocking_reasons(self._manifest, metric_results)
        return EvaluationScorecard(
            metric_results=metric_results,
            promotion_allowed=not blocking_reasons,
            blocking_reasons=tuple(blocking_reasons),
        )


def _dataset(value: Mapping[str, Any]) -> FixtureDataset:
    fixture_ids = value.get("fixture_ids", [])
    if not isinstance(fixture_ids, list) or not all(_is_nonempty_text(item) for item in fixture_ids):
        raise ManifestValidationError("Поле fixture_ids должно быть списком непустых строк")
    return FixtureDataset(
        classification=_required_text(value, "classification"),
        approved=_required_bool(value, "approved"),
        fixture_ids=tuple(fixture_ids),
        approval_reference=_optional_text(value, "approval_reference"),
    )


def _metric(value: Any) -> DeclaredMetric:
    if not isinstance(value, Mapping):
        raise ManifestValidationError("Каждая метрика должна быть объектом")
    direction = _required_text(value, "direction")
    if direction not in ("minimum", "maximum"):
        raise ManifestValidationError("direction должен быть minimum или maximum")
    threshold = value.get("threshold")
    if (
        threshold is not None
        and (
            not isinstance(threshold, (int, float))
            or isinstance(threshold, bool)
            or not isfinite(threshold)
        )
    ):
        raise ManifestValidationError("threshold должен быть конечным числом или null")
    return DeclaredMetric(
        name=_required_text(value, "name"),
        direction=cast(MetricDirection, direction),
        threshold=float(threshold) if threshold is not None else None,
        threshold_reference=_optional_text(value, "threshold_reference"),
    )


def _owner_confirmation(value: Any) -> OwnerConfirmation | None:
    if value is None:
        return None
    if not isinstance(value, Mapping):
        raise ManifestValidationError("owner_confirmation должен быть объектом")
    return OwnerConfirmation(
        confirmed=_required_bool(value, "confirmed"),
        owner=_optional_text(value, "owner"),
        confirmation_reference=_optional_text(value, "confirmation_reference"),
    )


def _metric_result(metric: DeclaredMetric, value: Any) -> MetricResult:
    score = (
        float(value)
        if isinstance(value, (int, float)) and not isinstance(value, bool) and isfinite(value)
        else None
    )
    if score is None or metric.threshold is None:
        passed = False
    elif metric.direction == "minimum":
        passed = score >= metric.threshold
    else:
        passed = score <= metric.threshold
    return MetricResult(metric.name, score, metric.threshold, metric.direction, passed)


def _blocking_reasons(
    manifest: EvaluationManifest, metric_results: tuple[MetricResult, ...]
) -> list[str]:
    reasons: list[str] = []
    dataset = manifest.dataset
    if dataset.classification != "real_anonymized":
        reasons.append("dataset_is_not_real_anonymized")
    if not dataset.approved:
        reasons.append("dataset_not_approved")
    if not dataset.fixture_ids:
        reasons.append("dataset_has_no_fixtures")
    if not dataset.approval_reference:
        reasons.append("dataset_has_no_approval_reference")

    if not manifest.metrics:
        reasons.append("no_declared_metrics")
    for metric in manifest.metrics:
        if metric.threshold is None or not metric.threshold_reference:
            reasons.append(f"metric_has_no_approved_threshold:{metric.name}")

    confirmation = manifest.owner_confirmation
    if confirmation is None or not confirmation.confirmed:
        reasons.append("owner_confirmation_missing")
    elif not confirmation.owner or not confirmation.confirmation_reference:
        reasons.append("owner_confirmation_incomplete")

    for result in metric_results:
        if result.value is None:
            reasons.append(f"metric_not_observed:{result.name}")
        elif not result.passed:
            reasons.append(f"metric_threshold_not_met:{result.name}")
    return reasons


def _required_object(value: Mapping[str, Any], key: str) -> Mapping[str, Any]:
    result = value.get(key)
    if not isinstance(result, Mapping):
        raise ManifestValidationError(f"Поле {key} должно быть объектом")
    return result


def _required_bool(value: Mapping[str, Any], key: str) -> bool:
    result = value.get(key)
    if not isinstance(result, bool):
        raise ManifestValidationError(f"Поле {key} должно быть bool")
    return result


def _required_text(value: Mapping[str, Any], key: str) -> str:
    result = _optional_text(value, key)
    if result is None:
        raise ManifestValidationError(f"Поле {key} должно быть непустой строкой")
    return result


def _optional_text(value: Mapping[str, Any], key: str) -> str | None:
    result = value.get(key)
    if result is None:
        return None
    if not _is_nonempty_text(result):
        raise ManifestValidationError(f"Поле {key} должно быть непустой строкой или null")
    return result


def _is_nonempty_text(value: Any) -> bool:
    return isinstance(value, str) and bool(value.strip())
