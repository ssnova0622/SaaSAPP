"""Unit tests for follow-ups service: scheduling and followup_prefs."""
import pytest
from datetime import datetime, timedelta
from unittest.mock import patch, MagicMock

from app.services.core.followups_service import (
    _followup_prefs_for_tenant,
    format_message,
    SCHEDULE_OFFSETS,
)


def test_followup_prefs_default_all_true(monkeypatch):
    """When tenant has no followup_prefs, all event types are enabled."""
    mock_get = MagicMock(return_value={})
    with patch("app.services.core.followups_service.get_tenant_service") as m:
        m.return_value.get_tenant_settings = mock_get
        prefs = _followup_prefs_for_tenant("t1")
    for ftype in SCHEDULE_OFFSETS:
        assert prefs.get(ftype, True) is True


def test_followup_prefs_tenant_disables_some(monkeypatch):
    """Tenant can disable specific event types via followup_prefs."""
    mock_get = MagicMock(return_value={"followup_prefs": {"reminder24": False, "post": False}})
    with patch("app.services.core.followups_service.get_tenant_service") as m:
        m.return_value.get_tenant_settings = mock_get
        prefs = _followup_prefs_for_tenant("t1")
    assert prefs.get("confirm", True) is True
    assert prefs.get("reminder24") is False
    assert prefs.get("reminder2", True) is True
    assert prefs.get("post") is False


def test_format_message_uses_placeholders(monkeypatch):
    """format_message(tenant, ftype, payload) returns template with placeholders filled."""
    import app.services.core.message_templates as msg_tpl
    mock_get = MagicMock(return_value={})
    with patch.object(msg_tpl, "get_tenant_service", lambda: MagicMock(get_tenant_settings=mock_get)):
        payload = {
            "customer_name": "Alice",
            "professional": "Dr. Smith",
            "time": "14:00",
            "tenant": "MyClinic",
        }
        out = format_message("t1", "confirm", payload)
    assert "Alice" in out
    assert "Dr. Smith" in out
    assert "14:00" in out
    assert "MyClinic" in out
