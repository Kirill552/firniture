import logging

import pytest
from httpx import ASGITransport, AsyncClient

from api.main import app

@pytest.mark.asyncio
async def test_product_analytics_events_route_validation(caplog: pytest.LogCaptureFixture) -> None:
    # Set logging level to capture observability.events logs
    logger = logging.getLogger("observability.events")
    logger.setLevel(logging.INFO)
    
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        # Scenario 1: Unknown event -> 422
        resp = await client.post(
            "/api/v1/product-analytics/events",
            json={"name": "unknown_event_name", "properties": {"order_id": "123"}}
        )
        assert resp.status_code == 422

        # Scenario 2: Valid event -> 202
        resp = await client.post(
            "/api/v1/product-analytics/events",
            json={"name": "landing_cta_clicked", "properties": {"entry_point": "hero"}}
        )
        assert resp.status_code == 202

        # Scenario 3: Redact check
        caplog.clear()
        resp = await client.post(
            "/api/v1/product-analytics/events",
            json={
                "name": "guest_analysis_completed",
                "properties": {
                    "order_id": "12345678-1234-1234-1234-123456789012",
                    "email": "test@example.com",
                    "factory_name": "My Factory",
                    "status": "success",
                    "width_mm": 1200
                }
            })
        # Check logs
        log_records = [
            r.message for r in caplog.records 
            if r.name == "observability.events" and "product.guest_analysis_completed" in r.message
        ]
        assert len(log_records) > 0
        
        log_message = log_records[0]
        
        # Verify that sensitive keys are redacted
        assert "test@example.com" not in log_message
        assert "My Factory" not in log_message
        # width_mm is also redacted as part of REDACTED_KEYS
        assert "1200" not in log_message
        assert "[REDACTED]" in log_message
        
        # Verify allowed properties are kept
        assert "success" in log_message
        assert "guest_analysis_completed" in log_message
