"""
Интеграционные тесты домена CAM job envelope.

Проверяет:
- Создание envelope с корректными默认值
- State machine переходы (valid и invalid)
- Идемпотентность и duplicate guard
- Сериализация / десериализация (to_dict ↔ from_dict)
- Retry логику и terminal state
- Фабричные функции

Нет worker / route / ORM / Redis зависимостей — чистый домен.
"""
from __future__ import annotations

from uuid import uuid4

import pytest

from api.cam_jobs import (
    CAMJobEnvelope,
    DuplicateJob,
    EnvelopeValidationError,
    IdempotencyRegistry,
    InvalidTransition,
    JobKind,
    JobState,
    SchemaVersion,
    create_envelope,
    enqueue_envelope,
)

# ──────────────────────────────────────────────────────────────────────
# Fixtures
# ──────────────────────────────────────────────────────────────────────


@pytest.fixture
def registry() -> IdempotencyRegistry:
    return IdempotencyRegistry()


@pytest.fixture
def sample_envelope() -> CAMJobEnvelope:
    return create_envelope(
        JobKind.DXF,
        order_id=uuid4(),
        context={"product_config_id": "pc-1"},
    )


# ──────────────────────────────────────────────────────────────────────
# 1. Создание envelope
# ──────────────────────────────────────────────────────────────────────


class TestEnvelopeCreation:
    """Envelope создаётся с корректными默认值 и переданными параметрами."""

    def test_default_state_is_created(self):
        env = create_envelope(JobKind.GCODE)
        assert env.state == JobState.CREATED
        assert env.job_kind == JobKind.GCODE
        assert env.attempt == 0
        assert env.max_retries == 3
        assert env.error is None

    def test_uuid_is_unique(self):
        env1 = create_envelope(JobKind.DXF)
        env2 = create_envelope(JobKind.DXF)
        assert env1.id != env2.id

    def test_schema_version_is_v1(self):
        env = create_envelope(JobKind.ZIP)
        assert env.schema_version == SchemaVersion.V1

    def test_context_preserved(self):
        ctx = {"panels": [1, 2, 3], "material": "ЛДСП"}
        env = create_envelope(JobKind.DXF, context=ctx)
        assert env.context == ctx

    def test_order_id_preserved(self):
        oid = uuid4()
        env = create_envelope(JobKind.DXF, order_id=oid)
        assert env.order_id == oid

    def test_idempotency_key_preserved(self):
        env = create_envelope(JobKind.DXF, idempotency_key="key-abc")
        assert env.idempotency_key == "key-abc"

    def test_created_at_is_utc(self):
        env = create_envelope(JobKind.DXF)
        assert env.created_at.tzinfo is not None

    def test_frozen_dataclass(self):
        """Envelope immutable — direct attribute assignment raises."""
        env = create_envelope(JobKind.DXF)
        with pytest.raises(AttributeError):
            env.state = JobState.COMPLETED  # type: ignore[misc]


# ──────────────────────────────────────────────────────────────────────
# 2. State machine
# ──────────────────────────────────────────────────────────────────────


class TestStateMachine:
    """Все legal и illegal переходы проверены."""

    def test_created_to_processing(self):
        env = create_envelope(JobKind.DXF)
        env2 = env.transition_to(JobState.PROCESSING)
        assert env2.state == JobState.PROCESSING
        assert env2.attempt == 1

    def test_processing_to_completed(self):
        env = create_envelope(JobKind.DXF)
        env2 = env.transition_to(JobState.PROCESSING)
        env3 = env2.transition_to(JobState.COMPLETED)
        assert env3.state == JobState.COMPLETED
        assert env3.attempt == 1  # completed не инкрементит

    def test_processing_to_failed(self):
        env = create_envelope(JobKind.GCODE)
        env2 = env.transition_to(JobState.PROCESSING)
        env3 = env2.transition_to(JobState.FAILED, error="timeout")
        assert env3.state == JobState.FAILED
        assert env3.error == "timeout"
        assert env3.attempt == 1  # FAILED не инкрементит

    def test_created_to_failed(self):
        """REJECTED — задача не прошла валидацию."""
        env = create_envelope(JobKind.DXF)
        env2 = env.transition_to(JobState.FAILED, error="invalid input")
        assert env2.state == JobState.FAILED
        assert env2.attempt == 0  # FAILED не инкрементит

    def test_failed_to_created_retry(self):
        """FAILED → CREATED — retry."""
        env = create_envelope(JobKind.DXF, max_retries=3)
        env2 = env.transition_to(JobState.PROCESSING)
        env3 = env2.transition_to(JobState.FAILED, error="oops")
        env4 = env3.transition_to(JobState.CREATED)
        assert env4.state == JobState.CREATED
        assert env4.attempt == 1  # PROCESSING инкрементил (1), FAILED нет

    def test_completed_is_terminal(self):
        env = create_envelope(JobKind.DXF)
        env2 = env.transition_to(JobState.PROCESSING)
        env3 = env2.transition_to(JobState.COMPLETED)
        with pytest.raises(InvalidTransition):
            env3.transition_to(JobState.FAILED)

    def test_invalid_transition_created_to_completed(self):
        env = create_envelope(JobKind.DXF)
        with pytest.raises(InvalidTransition) as exc_info:
            env.transition_to(JobState.COMPLETED)
        assert exc_info.value.current == JobState.CREATED
        assert exc_info.value.target == JobState.COMPLETED

    def test_invalid_transition_completed_to_created(self):
        env = create_envelope(JobKind.DXF)
        env2 = env.transition_to(JobState.PROCESSING)
        env3 = env2.transition_to(JobState.COMPLETED)
        with pytest.raises(InvalidTransition):
            env3.transition_to(JobState.CREATED)

    def test_attempt_increments_on_processing(self):
        env = create_envelope(JobKind.DXF)
        assert env.attempt == 0
        env2 = env.transition_to(JobState.PROCESSING)
        assert env2.attempt == 1
        env3 = env2.transition_to(JobState.FAILED, error="err")
        assert env3.attempt == 1  # FAILED не инкрементит
        env4 = env3.transition_to(JobState.CREATED)
        assert env4.attempt == 1  # retry не инкрементит
        env5 = env4.transition_to(JobState.PROCESSING)
        assert env5.attempt == 2

    def test_full_happy_path(self):
        """CREATED → PROCESSING → COMPLETED."""
        env = create_envelope(JobKind.ZIP)
        env = env.transition_to(JobState.PROCESSING)
        env = env.transition_to(JobState.COMPLETED)
        assert env.is_terminal()
        assert not env.can_retry()


# ──────────────────────────────────────────────────────────────────────
# 3. Retry логика
# ──────────────────────────────────────────────────────────────────────


class TestRetryLogic:
    """can_retry зависит от attempt и max_retries."""

    def test_can_retry_within_limit(self):
        env = create_envelope(JobKind.DXF, max_retries=2)
        env = env.transition_to(JobState.PROCESSING)
        env = env.transition_to(JobState.FAILED, error="err")
        assert env.can_retry()

    def test_cannot_retry_exceeded_limit(self):
        env = create_envelope(JobKind.DXF, max_retries=1)
        env = env.transition_to(JobState.PROCESSING)
        env = env.transition_to(JobState.FAILED, error="err1")
        assert env.can_retry()  # attempt=1, max=1 → still ok
        env = env.transition_to(JobState.CREATED)
        env = env.transition_to(JobState.PROCESSING)
        env = env.transition_to(JobState.FAILED, error="err2")
        assert not env.can_retry()  # attempt=2, max=1 → exceeded

    def test_cannot_retry_on_completed(self):
        env = create_envelope(JobKind.DXF)
        env = env.transition_to(JobState.PROCESSING)
        env = env.transition_to(JobState.COMPLETED)
        assert not env.can_retry()

    def test_can_retry_on_created_state(self):
        env = create_envelope(JobKind.DXF)
        assert not env.can_retry()  # CREATED is not FAILED

    def test_is_terminal_only_on_completed(self):
        for state in JobState:
            env = CAMJobEnvelope(state=state)
            assert env.is_terminal() == (state == JobState.COMPLETED)


# ──────────────────────────────────────────────────────────────────────
# 4. Идемпотентность
# ──────────────────────────────────────────────────────────────────────


class TestIdempotency:
    """IdempotencyRegistry + enqueue_envelope guard."""

    def test_first_registration_succeeds(self, registry):
        jid = uuid4()
        existing = registry.check_and_register("key-1", jid)
        assert existing is None

    def test_duplicate_registration_returns_existing_id(self, registry):
        jid1, jid2 = uuid4(), uuid4()
        registry.check_and_register("key-1", jid1)
        existing = registry.check_and_register("key-1", jid2)
        assert existing == jid1

    def test_lookup(self, registry):
        jid = uuid4()
        registry.check_and_register("key-1", jid)
        assert registry.lookup("key-1") == jid
        assert registry.lookup("nonexistent") is None

    def test_remove(self, registry):
        jid = uuid4()
        registry.check_and_register("key-1", jid)
        assert registry.remove("key-1") is True
        assert registry.remove("key-1") is False
        assert "key-1" not in registry

    def test_len_and_contains(self, registry):
        assert len(registry) == 0
        registry.check_and_register("k1", uuid4())
        assert len(registry) == 1
        assert "k1" in registry
        assert "k2" not in registry

    def test_enqueue_envelope_passes_without_key(self, registry):
        env = create_envelope(JobKind.DXF)
        result = enqueue_envelope(env, registry)
        assert result is env  # no idempotency_key → pass-through

    def test_enqueue_envelope_registers_key(self, registry):
        env = create_envelope(JobKind.DXF, idempotency_key="ik-1")
        result = enqueue_envelope(env, registry)
        assert result is env
        assert registry.lookup("ik-1") == env.id

    def test_enqueue_envelope_raises_on_duplicate(self, registry):
        env1 = create_envelope(JobKind.DXF, idempotency_key="ik-1")
        enqueue_envelope(env1, registry)
        env2 = create_envelope(JobKind.DXF, idempotency_key="ik-1")
        with pytest.raises(DuplicateJob) as exc_info:
            enqueue_envelope(env2, registry)
        assert exc_info.value.existing_id == env1.id
        assert exc_info.value.idempotency_key == "ik-1"

    def test_different_keys_do_not_collide(self, registry):
        env1 = create_envelope(JobKind.DXF, idempotency_key="ik-a")
        env2 = create_envelope(JobKind.DXF, idempotency_key="ik-b")
        enqueue_envelope(env1, registry)
        enqueue_envelope(env2, registry)  # no collision
        assert len(registry) == 2


# ──────────────────────────────────────────────────────────────────────
# 5. Сериализация
# ──────────────────────────────────────────────────────────────────────


class TestSerialization:
    """to_dict ↔ from_dict round-trip, versioned schema."""

    def test_round_trip(self):
        oid = uuid4()
        env = create_envelope(
            JobKind.GCODE,
            order_id=oid,
            idempotency_key="ik-rt",
            context={"machine": "Biesse"},
        )
        env2 = env.transition_to(JobState.PROCESSING)
        d = env2.to_dict()
        env3 = CAMJobEnvelope.from_dict(d)
        assert env3.id == env2.id
        assert env3.job_kind == JobKind.GCODE
        assert env3.state == JobState.PROCESSING
        assert env3.order_id == oid
        assert env3.idempotency_key == "ik-rt"
        assert env3.context == {"machine": "Biesse"}
        assert env3.attempt == 1

    def test_to_dict_keys(self):
        env = create_envelope(JobKind.DXF)
        d = env.to_dict()
        expected_keys = {
            "id", "schema_version", "job_kind", "state",
            "idempotency_key", "order_id", "context",
            "attempt", "max_retries", "error",
            "created_at", "updated_at",
        }
        assert set(d.keys()) == expected_keys

    def test_from_dict_missing_field_raises(self):
        with pytest.raises(EnvelopeValidationError):
            CAMJobEnvelope.from_dict({"id": str(uuid4())})  # missing job_kind

    def test_from_dict_invalid_enum_raises(self):
        d = create_envelope(JobKind.DXF).to_dict()
        d["state"] = "bogus"
        with pytest.raises(EnvelopeValidationError):
            CAMJobEnvelope.from_dict(d)

    def test_schema_version_in_dict(self):
        env = create_envelope(JobKind.DXF)
        d = env.to_dict()
        assert d["schema_version"] == 1

    def test_none_order_id_serializes(self):
        env = create_envelope(JobKind.DXF)
        d = env.to_dict()
        assert d["order_id"] is None
        env2 = CAMJobEnvelope.from_dict(d)
        assert env2.order_id is None

    def test_error_preserved_through_serialization(self):
        env = create_envelope(JobKind.DXF)
        env2 = env.transition_to(JobState.PROCESSING)
        env3 = env2.transition_to(JobState.FAILED, error="OOM")
        d = env3.to_dict()
        env4 = CAMJobEnvelope.from_dict(d)
        assert env4.error == "OOM"


# ──────────────────────────────────────────────────────────────────────
# 6. Envelope фабрика + полный lifecycle
# ──────────────────────────────────────────────────────────────────────


class TestFactoryAndLifecycle:
    """create_envelope → enqueue → transitions → terminal."""

    def test_full_dxf_lifecycle(self, registry):
        env = create_envelope(
            JobKind.DXF,
            order_id=uuid4(),
            idempotency_key="dxf-job-1",
            context={"panels": 5},
        )
        enqueue_envelope(env, registry)
        assert "dxf-job-1" in registry

        env = env.transition_to(JobState.PROCESSING)
        assert env.attempt == 1

        env = env.transition_to(JobState.COMPLETED)
        assert env.is_terminal()
        assert env.attempt == 1

    def test_full_gcode_retry_lifecycle(self, registry):
        env = create_envelope(
            JobKind.GCODE,
            idempotency_key="gcode-1",
            max_retries=2,
        )
        enqueue_envelope(env, registry)

        # Attempt 1 — fail
        env = env.transition_to(JobState.PROCESSING)
        env = env.transition_to(JobState.FAILED, error="timeout")
        assert env.can_retry()

        # Retry
        env = env.transition_to(JobState.CREATED)
        env = env.transition_to(JobState.PROCESSING)
        env = env.transition_to(JobState.COMPLETED)
        assert env.is_terminal()

    def test_drilling_lifecycle(self):
        env = create_envelope(JobKind.DRILLING, context={"holes": 12})
        env = env.transition_to(JobState.PROCESSING)
        env = env.transition_to(JobState.COMPLETED)
        assert env.job_kind == JobKind.DRILLING
        assert env.context["holes"] == 12
        assert env.is_terminal()

    def test_zip_lifecycle(self):
        env = create_envelope(JobKind.ZIP, context={"job_ids": ["j1", "j2"]})
        env = env.transition_to(JobState.PROCESSING)
        env = env.transition_to(JobState.COMPLETED)
        assert env.context["job_ids"] == ["j1", "j2"]
        assert env.is_terminal()
