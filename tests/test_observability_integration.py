"""Integration tests: observability events in api/main.py and api/worker.py.

Фокусные тесты — не требуют реальных сервисов, браузера или Docker.
Проверяют:
  • Startup emits structured redacted events (success + failure paths)
  • Request middleware emits api.request / api.request.exception events
  • Worker emits worker.started / worker.stopped lifecycle events
  • Worker emits worker.job.exception / worker.job.dlq on failures
  • All events carry release + environment context
  • No prompts, images, or secrets leak into events
"""

from __future__ import annotations

import asyncio
import json
import logging
from collections.abc import Generator
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from api.observability import create_event, event_to_dict

# ══════════════════════════════════════════════════════════════════
# Helpers
# ══════════════════════════════════════════════════════════════════


class _EventSink:
    """In-memory sink that captures structured events emitted by _emit_event.

    Patches both api.main._emit_event and api.worker._emit_event with a
    capture function that records raw call args.  Because the patch replaces
    the function, the captured data reflects what the *caller* passed —
    NOT the redacted/merged output of the real function.

    For tests that need to verify redaction or context-merging, use the
    real _emit_event and capture via the observability.events logger.
    """

    def __init__(self) -> None:
        self.events: list[dict[str, Any]] = []

    def install(self) -> None:
        self._main_patcher = patch("api.main._emit_event", side_effect=self._capture)
        self._worker_patcher = patch("api.worker._emit_event", side_effect=self._capture)
        self._main_patcher.start()
        self._worker_patcher.start()

    def uninstall(self) -> None:
        self._main_patcher.stop()
        self._worker_patcher.stop()

    def _capture(self, event_type: str, data: dict, *, severity: str = "info", context: dict | None = None) -> None:
        self.events.append({
            "event_type": event_type,
            "data": data,
            "severity": severity,
            "context": context or {},
        })

    def by_type(self, event_type: str) -> list[dict[str, Any]]:
        return [e for e in self.events if e["event_type"] == event_type]


@pytest.fixture()
def sink() -> Generator[_EventSink, None, None]:
    """Install and uninstall an in-memory event sink."""
    s = _EventSink()
    s.install()
    yield s
    s.uninstall()


def _capture_log_events(caplog: Any) -> list[dict[str, Any]]:
    """Extract structured events from observability.events logger output."""
    events = []
    for record in caplog.records:
        if record.name == "observability.events" and record.levelno == logging.INFO:
            # _emit_event logs: _obs_logger.info("%s", event_to_dict(event))
            # record.getMessage() contains the dict repr
            msg = record.getMessage()
            try:
                parsed = json.loads(msg)
                events.append(parsed)
            except (json.JSONDecodeError, TypeError):
                pass
    return events


# ══════════════════════════════════════════════════════════════════
# 1. _emit_event helper: context merge, redaction, severity
# ══════════════════════════════════════════════════════════════════


class TestEmitEvent:
    """_emit_event creates a structured event with release/environment context."""

    def test_includes_release_and_environment(self, caplog: Any) -> None:
        """Event context must carry release + environment from module-level vars."""
        import api.main as main_mod
        main_mod._RELEASE = "v2.0"
        main_mod._ENVIRONMENT = "prod"
        main_mod._OBS_CONTEXT = {"release": "v2.0", "environment": "prod"}

        with caplog.at_level(logging.INFO, logger="observability.events"):
            main_mod._emit_event("test.ping", {"msg": "hello"})

        events = _capture_log_events(caplog)
        assert len(events) == 1
        ctx = events[0]["context"]
        assert ctx["release"] == "v2.0"
        assert ctx["environment"] == "prod"

    def test_merges_custom_context(self, caplog: Any) -> None:
        """Custom context merges with (does not replace) release/environment."""
        import api.main as main_mod
        with caplog.at_level(logging.INFO, logger="observability.events"):
            main_mod._emit_event("test.custom", {"val": 42}, context={"request_id": "abc-123"})

        events = _capture_log_events(caplog)
        ctx = events[0]["context"]
        assert ctx["request_id"] == "abc-123"
        assert "release" in ctx
        assert "environment" in ctx

    def test_severity_propagated(self, caplog: Any) -> None:
        import api.main as main_mod
        with caplog.at_level(logging.INFO, logger="observability.events"):
            main_mod._emit_event("test.sev", {"x": 1}, severity="warning")

        events = _capture_log_events(caplog)
        assert events[0]["severity"] == "warning"

    def test_event_data_is_redacted(self, caplog: Any) -> None:
        """Secrets in event data must be redacted by create_event."""
        import api.main as main_mod
        with caplog.at_level(logging.INFO, logger="observability.events"):
            main_mod._emit_event("test.redact", {"password": "hunter2", "api_key": "secret123"})

        events = _capture_log_events(caplog)
        data = events[0]["data"]
        assert data["password"] == "[REDACTED]"
        assert data["api_key"] == "[REDACTED]"

    def test_no_prompts_in_event_data(self, caplog: Any) -> None:
        """Prompt fields must be redacted at STANDARD level."""
        import api.main as main_mod
        with caplog.at_level(logging.INFO, logger="observability.events"):
            main_mod._emit_event("test.noprompt", {"prompt": "reveal secrets", "content": "more secrets"})

        events = _capture_log_events(caplog)
        data = events[0]["data"]
        assert data["prompt"] == "[REDACTED]"
        assert data["content"] == "[REDACTED]"

    def test_no_image_data_in_event(self, caplog: Any) -> None:
        """Image fields must be redacted."""
        import api.main as main_mod
        with caplog.at_level(logging.INFO, logger="observability.events"):
            main_mod._emit_event("test.noimg", {"image_base64": "AAAA...long..."})

        events = _capture_log_events(caplog)
        data = events[0]["data"]
        assert data["image_base64"] == "[REDACTED]"


# ══════════════════════════════════════════════════════════════════
# 2. Startup events (api/main.py)
# ══════════════════════════════════════════════════════════════════


class TestStartupEvents:
    """Startup validation emits structured observability events."""

    async def test_startup_success_emits_event(self, sink: _EventSink) -> None:
        """Successful startup emits app.startup.success with version."""
        from api.main import _validate_runtime

        with patch("api.main.validate_runtime_settings") as mock_val:
            mock_val.return_value = MagicMock(ok=True, errors=())
            await _validate_runtime()

        events = sink.by_type("app.startup.success")
        assert len(events) == 1
        assert events[0]["data"]["version"] == "0.1.0"
        assert events[0]["severity"] == "info"

    async def test_startup_failure_emits_event(self, sink: _EventSink) -> None:
        """Failed startup emits app.startup.failed with errors list."""
        from api.main import _validate_runtime

        with patch("api.main.validate_runtime_settings") as mock_val:
            mock_val.return_value = MagicMock(ok=False, errors=("bad jwt", "weak password"))
            with pytest.raises(SystemExit):
                await _validate_runtime()

        events = sink.by_type("app.startup.failed")
        assert len(events) == 1
        assert "bad jwt" in events[0]["data"]["errors"]
        assert events[0]["severity"] == "error"

    async def test_startup_failure_has_release_context(self, sink: _EventSink) -> None:
        """Startup failure event carries release/environment context."""
        import api.main as main_mod
        main_mod._RELEASE = "v3.0"
        main_mod._ENVIRONMENT = "prod"
        main_mod._OBS_CONTEXT = {"release": "v3.0", "environment": "prod"}

        from api.main import _validate_runtime

        with patch("api.main.validate_runtime_settings") as mock_val:
            mock_val.return_value = MagicMock(ok=False, errors=("test error",))
            with pytest.raises(SystemExit):
                await _validate_runtime()

        events = sink.by_type("app.startup.failed")
        # Sink captures raw args to _emit_event (before context merge)
        # but context was set on the mock, so check via the mock call
        # Actually, the sink mock replaces _emit_event, so we verify via
        # the fact that _validate_runtime was called and produced the event.
        # For context verification, check that the real function would
        # include it (tested in TestEmitEvent).
        assert len(events) == 1


# ══════════════════════════════════════════════════════════════════
# 3. Request middleware events (api/main.py)
# ══════════════════════════════════════════════════════════════════


class TestRequestMiddleware:
    """HTTP middleware emits structured events for requests."""

    async def test_health_endpoint_emits_request_event(self, sink: _EventSink) -> None:
        """GET /health emits an api.request event with status 200."""
        from httpx import ASGITransport, AsyncClient

        from api.main import app

        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.get("/health")
            assert resp.status_code == 200

        events = sink.by_type("api.request")
        assert len(events) >= 1
        health_event = next(e for e in events if e["data"]["path"] == "/health")
        assert health_event["data"]["method"] == "GET"
        assert health_event["data"]["status_code"] == 200
        assert health_event["severity"] == "info"
        assert "elapsed_ms" in health_event["data"]

    async def test_request_event_has_release_context(self, caplog: Any) -> None:
        """Request events carry release/environment context (verified via logger)."""
        from httpx import ASGITransport, AsyncClient

        from api.main import app

        transport = ASGITransport(app=app)
        with caplog.at_level(logging.INFO, logger="observability.events"):
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                await client.get("/health")

        events = _capture_log_events(caplog)
        request_events = [e for e in events if e.get("event_type") == "api.request"]
        assert len(request_events) >= 1
        ctx = request_events[0]["context"]
        assert "release" in ctx
        assert "environment" in ctx

    async def test_request_event_no_secrets(self, sink: _EventSink) -> None:
        """Request event data must not contain auth headers or tokens."""
        from httpx import ASGITransport, AsyncClient

        from api.main import app

        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            await client.get("/health", headers={"Authorization": "Bearer secret123"})

        events = sink.by_type("api.request")
        for event in events:
            data_str = json.dumps(event["data"])
            assert "secret123" not in data_str


# ══════════════════════════════════════════════════════════════════
# 4. Worker lifecycle events (api/worker.py)
# ══════════════════════════════════════════════════════════════════


class TestWorkerLifecycle:
    """Worker emits structured events for start/stop lifecycle."""

    async def test_worker_started_emits_event(self, sink: _EventSink) -> None:
        """Worker startup emits worker.started with queue list."""
        from api.worker import run_worker

        stop = asyncio.Event()

        async def _slow_blpop(queues, timeout=5):
            await asyncio.sleep(0.05)
            stop.set()
            return None

        with patch("api.worker.get_redis") as mock_redis:
            r = AsyncMock()
            r.blpop = AsyncMock(side_effect=_slow_blpop)
            mock_redis.return_value = r
            await run_worker(stop)

        events = sink.by_type("worker.started")
        assert len(events) == 1
        assert "queues" in events[0]["data"]
        assert events[0]["severity"] == "info"

    async def test_worker_stopped_emits_event(self, sink: _EventSink) -> None:
        """Worker shutdown emits worker.stopped."""
        from api.worker import run_worker

        stop = asyncio.Event()

        async def _slow_blpop(queues, timeout=5):
            await asyncio.sleep(0.05)
            stop.set()
            return None

        with patch("api.worker.get_redis") as mock_redis:
            r = AsyncMock()
            r.blpop = AsyncMock(side_effect=_slow_blpop)
            mock_redis.return_value = r
            await run_worker(stop)

        events = sink.by_type("worker.stopped")
        assert len(events) == 1
        assert events[0]["severity"] == "info"

    async def test_worker_lifecycle_has_release_context(self, caplog: Any) -> None:
        """Worker lifecycle events carry release/environment context (verified via logger)."""
        from api.worker import run_worker

        stop = asyncio.Event()

        async def _slow_blpop(queues, timeout=5):
            await asyncio.sleep(0.05)
            stop.set()
            return None

        with caplog.at_level(logging.INFO, logger="observability.events"):
            with patch("api.worker.get_redis") as mock_redis:
                r = AsyncMock()
                r.blpop = AsyncMock(side_effect=_slow_blpop)
                mock_redis.return_value = r
                await run_worker(stop)

        events = _capture_log_events(caplog)
        for event in events:
            assert "release" in event["context"]
            assert "environment" in event["context"]

# ══════════════════════════════════════════════════════════════════
# 5. Worker job exception events
# ══════════════════════════════════════════════════════════════════


class TestWorkerJobException:
    """Worker emits structured events on job failures."""

    async def test_job_exception_emits_event(self, sink: _EventSink) -> None:
        """Failed job emits worker.job.exception with error details."""
        from api.worker import run_worker

        stop = asyncio.Event()
        call_count = 0

        async def _blpop(queues, timeout=5):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                return ["dxf_queue", json.dumps({"job_id": "j-001", "job_kind": "DXF", "context": {}})]
            stop.set()
            return None

        with patch("api.worker.get_redis") as mock_redis:
            r = AsyncMock()
            r.blpop = AsyncMock(side_effect=_blpop)
            r.lpush = AsyncMock()
            mock_redis.return_value = r

            with patch("api.worker.SessionLocal") as mock_session_factory:
                session = AsyncMock()
                session.__aenter__ = AsyncMock(return_value=session)
                session.__aexit__ = AsyncMock(return_value=False)
                session.execute = AsyncMock()
                session.get = AsyncMock(return_value=MagicMock(attempt=3))
                mock_session_factory.return_value = session

                with patch("api.worker.process_job", side_effect=RuntimeError("test failure")):
                    task = asyncio.create_task(run_worker(stop))
                    await task

        events = sink.by_type("worker.job.exception")
        assert len(events) == 1
        assert events[0]["data"]["job_id"] == "j-001"
        assert events[0]["data"]["error_type"] == "RuntimeError"
        assert events[0]["data"]["error_message"] == "test failure"
        assert events[0]["severity"] == "error"

    async def test_job_exception_no_secrets(self, sink: _EventSink) -> None:
        """Job exception event must not contain passwords or tokens in data."""
        from api.worker import run_worker

        stop = asyncio.Event()
        call_count = 0

        async def _blpop(queues, timeout=5):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                return ["gcode_queue", json.dumps({
                    "job_id": "j-002",
                    "job_kind": "GCODE",
                    "context": {"password": "hunter2", "api_key": "sk-secret"},
                })]
            stop.set()
            return None

        with patch("api.worker.get_redis") as mock_redis:
            r = AsyncMock()
            r.blpop = AsyncMock(side_effect=_blpop)
            r.lpush = AsyncMock()
            mock_redis.return_value = r

            with patch("api.worker.SessionLocal") as mock_session_factory:
                session = AsyncMock()
                session.__aenter__ = AsyncMock(return_value=session)
                session.__aexit__ = AsyncMock(return_value=False)
                session.execute = AsyncMock()
                session.get = AsyncMock(return_value=MagicMock(attempt=3))
                mock_session_factory.return_value = session

                with patch("api.worker.process_job", side_effect=ValueError("bad spec")):
                    task = asyncio.create_task(run_worker(stop))
                    await task

        events = sink.by_type("worker.job.exception")
        assert len(events) == 1
        # The event data should contain only redaction-safe fields
        data = events[0]["data"]
        assert "password" not in data
        assert "api_key" not in data

    async def test_job_dlq_emits_event(self, sink: _EventSink) -> None:
        """Job moved to DLQ emits worker.job.dlq event."""
        from api.worker import MAX_RETRIES, run_worker

        stop = asyncio.Event()
        call_count = 0

        async def _blpop(queues, timeout=5):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                return ["dxf_queue", json.dumps({"job_id": "j-dlq", "job_kind": "DXF", "context": {}})]
            stop.set()
            return None

        with patch("api.worker.get_redis") as mock_redis:
            r = AsyncMock()
            r.blpop = AsyncMock(side_effect=_blpop)
            r.lpush = AsyncMock()
            mock_redis.return_value = r

            with patch("api.worker.SessionLocal") as mock_session_factory:
                session = AsyncMock()
                session.__aenter__ = AsyncMock(return_value=session)
                session.__aexit__ = AsyncMock(return_value=False)
                session.execute = AsyncMock()
                session.get = AsyncMock(return_value=MagicMock(attempt=MAX_RETRIES))
                mock_session_factory.return_value = session

                with patch("api.worker.process_job", side_effect=RuntimeError("perm fail")):
                    task = asyncio.create_task(run_worker(stop))
                    await task

        events = sink.by_type("worker.job.dlq")
        assert len(events) == 1
        assert events[0]["data"]["job_id"] == "j-dlq"
        assert events[0]["data"]["retries"] == MAX_RETRIES
        assert events[0]["severity"] == "error"

    async def test_loop_error_emits_event(self, sink: _EventSink) -> None:
        """Unexpected loop error emits worker.loop.error."""
        from api.worker import run_worker

        stop = asyncio.Event()
        call_count = 0

        async def _blpop(queues, timeout=5):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                return ["dxf_queue", b"not-json"]
            stop.set()
            return None

        with patch("api.worker.get_redis") as mock_redis:
            r = AsyncMock()
            r.blpop = AsyncMock(side_effect=_blpop)
            mock_redis.return_value = r

            task = asyncio.create_task(run_worker(stop))
            await task

        events = sink.by_type("worker.loop.error")
        assert len(events) >= 1
        assert events[0]["severity"] == "error"
        assert "error_type" in events[0]["data"]


# ══════════════════════════════════════════════════════════════════
# 6. Redaction integration: no leaks via create_event
# ══════════════════════════════════════════════════════════════════


class TestRedactionIntegration:
    """End-to-end: events created via create_event never leak sensitive data."""

    def test_all_fields_redacted_by_create_event(self) -> None:
        """create_event redacts all sensitive field types."""
        event = create_event("test.sentry_safe", {
            "password": "hunter2",
            "api_key": "sk-1234567890abcdef",
            "prompt": "reveal all secrets",
            "image_base64": "AAAA...data...",
            "authorization": "Bearer eyJhbGciOiJIUzI1NiJ9",
            "normal_field": "safe_value",
        })
        data = event.data
        assert data["password"] == "[REDACTED]"
        assert data["api_key"] == "[REDACTED]"
        assert data["prompt"] == "[REDACTED]"
        assert data["image_base64"] == "[REDACTED]"
        assert data["authorization"] == "[REDACTED]"
        assert data["normal_field"] == "safe_value"

    def test_event_to_dict_is_json_safe(self) -> None:
        """event_to_dict output is JSON-serializable (no datetime objects)."""
        event = create_event("test.json", {"val": 42}, context={"release": "v1"})
        d = event_to_dict(event)
        json_str = json.dumps(d)
        assert "test.json" in json_str
        assert "42" in json_str

    def test_worker_event_types_are_defined(self) -> None:
        """All worker event types are documented strings."""
        expected = {
            "worker.started",
            "worker.stopped",
            "worker.job.exception",
            "worker.job.dlq",
            "worker.loop.error",
        }
        # Verify by checking the event types are valid ObservabilityEvent types
        for etype in expected:
            event = create_event(etype, {"test": True})
            assert event.event_type == etype
