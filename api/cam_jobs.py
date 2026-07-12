"""
CAM job envelope — versioned idempotency, state transitions, pure domain.

No worker / route / ORM integration; pure domain models consumed by those layers.

Schema version tracks envelope format evolution; state machine enforces
legal transitions; idempotency guard deduplicates enqueue attempts.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import Enum
from typing import Any
from uuid import UUID, uuid4

# ──────────────────────────────────────────────────────────────────────
# Enums
# ──────────────────────────────────────────────────────────────────────


class JobKind(str, Enum):
    """Тип CAM задачи — определяет очередь и обработчик."""

    DXF = "dxf"
    GCODE = "gcode"
    DRILLING = "drilling"
    ZIP = "zip"


class JobState(str, Enum):
    """Состояние задачи в жизненном цикле.

    Базовый state machine:

        CREATED ──► PROCESSING ──► COMPLETED
          │              │
          ▼              ▼
        FAILED ◄─────────┘
          │
          ▼
        CREATED   (retry — возврат в начальное состояние)
    """

    CREATED = "created"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


# Допустимые переходы state → множество следующих состояний.
VALID_TRANSITIONS: dict[JobState, set[JobState]] = {
    JobState.CREATED: {JobState.PROCESSING, JobState.FAILED},
    JobState.PROCESSING: {JobState.COMPLETED, JobState.FAILED},
    JobState.COMPLETED: set(),  # терминальное
    JobState.FAILED: {JobState.CREATED},  # retry
}


class SchemaVersion(int, Enum):
    """Версия формата envelope — для безопасной эволюции."""

    V1 = 1


# ──────────────────────────────────────────────────────────────────────
# Errors
# ──────────────────────────────────────────────────────────────────────


class InvalidTransition(Exception):
    """Попытка нелегального перехода состояний."""

    def __init__(self, current: JobState, target: JobState) -> None:
        self.current = current
        self.target = target
        super().__init__(
            f"Transition {current.value!r} → {target.value!r} is not allowed"
        )


class DuplicateJob(Exception):
    """Попытка создать дубликат с тем же idempotency_key."""

    def __init__(self, idempotency_key: str, existing_id: UUID) -> None:
        self.idempotency_key = idempotency_key
        self.existing_id = existing_id
        super().__init__(
            f"Idempotency key {idempotency_key!r} already used "
            f"by job {existing_id}"
        )


class EnvelopeValidationError(Exception):
    """Невалидные данные envelope."""


# ──────────────────────────────────────────────────────────────────────
# Envelope
# ──────────────────────────────────────────────────────────────────────


@dataclass(frozen=True)
class CAMJobEnvelope:
    """Версионированный envelope для CAM задачи.

    frozen=True — immutable after creation; state changes produce new
    instances via ``transition_to``.
    """

    id: UUID = field(default_factory=uuid4)
    schema_version: SchemaVersion = SchemaVersion.V1
    job_kind: JobKind = JobKind.DXF
    state: JobState = JobState.CREATED
    idempotency_key: str | None = None
    order_id: UUID | None = None
    context: dict[str, Any] = field(default_factory=dict)
    attempt: int = 0
    max_retries: int = 3
    error: str | None = None
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    updated_at: datetime = field(default_factory=lambda: datetime.now(UTC))

    # ── state machine ──────────────────────────────────────────────

    def transition_to(self, target: JobState, *, error: str | None = None) -> CAMJobEnvelope:
        """Validate and perform state transition; return new instance.

        Raises ``InvalidTransition`` if the move is not in VALID_TRANSITIONS.
        """
        allowed = VALID_TRANSITIONS.get(self.state, set())
        if target not in allowed:
            raise InvalidTransition(self.state, target)
        return CAMJobEnvelope(
            id=self.id,
            schema_version=self.schema_version,
            job_kind=self.job_kind,
            state=target,
            idempotency_key=self.idempotency_key,
            order_id=self.order_id,
            context=self.context,
            attempt=self.attempt + 1 if target == JobState.PROCESSING else self.attempt,
            max_retries=self.max_retries,
            error=error,
            created_at=self.created_at,
            updated_at=datetime.now(UTC),
        )

    def is_terminal(self) -> bool:
        """True when the job can never transition again."""
        return self.state == JobState.COMPLETED

    def can_retry(self) -> bool:
        """True when the job has retries remaining and can go back to CREATED."""
        return (
            self.state == JobState.FAILED
            and self.attempt <= self.max_retries
        )

    # ── serialization ──────────────────────────────────────────────

    def to_dict(self) -> dict[str, Any]:
        """Serialize to JSON-safe dict."""
        return {
            "id": str(self.id),
            "schema_version": self.schema_version.value,
            "job_kind": self.job_kind.value,
            "state": self.state.value,
            "idempotency_key": self.idempotency_key,
            "order_id": str(self.order_id) if self.order_id else None,
            "context": self.context,
            "attempt": self.attempt,
            "max_retries": self.max_retries,
            "error": self.error,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> CAMJobEnvelope:
        """Deserialize from dict; raises EnvelopeValidationError on bad data."""
        try:
            return cls(
                id=UUID(data["id"]),
                schema_version=SchemaVersion(data["schema_version"]),
                job_kind=JobKind(data["job_kind"]),
                state=JobState(data["state"]),
                idempotency_key=data.get("idempotency_key"),
                order_id=UUID(data["order_id"]) if data.get("order_id") else None,
                context=data.get("context", {}),
                attempt=data.get("attempt", 0),
                max_retries=data.get("max_retries", 3),
                error=data.get("error"),
                created_at=datetime.fromisoformat(data["created_at"]),
                updated_at=datetime.fromisoformat(data["updated_at"]),
            )
        except (KeyError, ValueError, TypeError) as exc:
            raise EnvelopeValidationError(
                f"Cannot deserialize envelope: {exc}"
            ) from exc


# ──────────────────────────────────────────────────────────────────────
# Factory
# ──────────────────────────────────────────────────────────────────────


def create_envelope(
    job_kind: JobKind,
    *,
    order_id: UUID | None = None,
    idempotency_key: str | None = None,
    context: dict[str, Any] | None = None,
    max_retries: int = 3,
) -> CAMJobEnvelope:
    """Create a new CAMJobEnvelope in CREATED state."""
    return CAMJobEnvelope(
        job_kind=job_kind,
        order_id=order_id,
        idempotency_key=idempotency_key,
        context=context or {},
        max_retries=max_retries,
    )


# ──────────────────────────────────────────────────────────────────────
# Idempotency guard (in-memory; swap for Redis/DB in production layer)
# ──────────────────────────────────────────────────────────────────────


@dataclass
class IdempotencyRegistry:
    """Tracks (idempotency_key → job_id) to prevent duplicate jobs.

    This is an in-memory domain-level guard.  The integration layer
    (Redis / DB unique constraint) provides the real enforcement;
    this registry allows callers to short-circuit *before* hitting I/O.
    """

    _seen: dict[str, UUID] = field(default_factory=dict)

    def check_and_register(self, key: str, job_id: UUID) -> UUID | None:
        """Register *key* for *job_id*.

        Returns the previously registered UUID if the key was already used
        (caller must treat this as a duplicate).  Returns ``None`` on
        first use (key successfully registered).
        """
        existing = self._seen.get(key)
        if existing is not None:
            return existing
        self._seen[key] = job_id
        return None

    def lookup(self, key: str) -> UUID | None:
        """Return the job_id registered for *key*, or None."""
        return self._seen.get(key)

    def remove(self, key: str) -> bool:
        """Remove a key (e.g. on job finalization).  Returns True if found."""
        return self._seen.pop(key, None) is not None

    def __contains__(self, key: str) -> bool:
        return key in self._seen

    def __len__(self) -> int:
        return len(self._seen)


def enqueue_envelope(
    envelope: CAMJobEnvelope,
    registry: IdempotencyRegistry,
) -> CAMJobEnvelope:
    """Register an envelope's idempotency key; raise DuplicateJob on collision.

    Pure domain function — no I/O, no Redis.  The caller
    (worker layer) handles actual queue push *after* this succeeds.
    """
    if envelope.idempotency_key is None:
        return envelope  # no idempotency — pass through
    existing = registry.check_and_register(envelope.idempotency_key, envelope.id)
    if existing is not None:
        raise DuplicateJob(envelope.idempotency_key, existing)
    return envelope
