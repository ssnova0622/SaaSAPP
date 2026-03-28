"""Unit tests for tenant-configurable message templates."""
import pytest
from app.services.core.message_templates import get_message, get_defaults


@pytest.fixture
def patch_platform(monkeypatch):
    """Avoid MongoDB: fixed platform layer as if loaded from default_message."""
    merged = {
        "whatsapp_hello": "Hello!",
        "whatsapp_service_offline": "Service offline",
        "followup_confirm": "Hi {name}, your booking with {pro} at {time} is confirmed. - {tenant}",
    }

    def _merged():
        return dict(merged)

    def _bundle():
        return {"templates": dict(merged), "labels": {k: k.replace("_", " ") for k in merged}}

    monkeypatch.setattr(
        "app.services.core.default_message_service.get_default_templates_merged",
        _merged,
    )
    monkeypatch.setattr(
        "app.services.core.default_message_service.get_default_message_bundle",
        _bundle,
    )
    return merged


def test_get_defaults_returns_dict(patch_platform):
    defaults = get_defaults()
    assert isinstance(defaults, dict)
    assert "whatsapp_hello" in defaults
    assert "followup_confirm" in defaults
    assert defaults["whatsapp_hello"] == "Hello!"


def test_get_message_without_tenant_uses_platform(patch_platform, monkeypatch):
    import app.services.core.message_templates as msg_tpl

    class MockTenantService:
        def get_tenant_settings(self, tenant):
            return {}

    monkeypatch.setattr(msg_tpl, "get_tenant_service", lambda: MockTenantService())
    out = get_message("test-tenant", "whatsapp_hello")
    assert out == "Hello!"
    out2 = get_message("test-tenant", "whatsapp_service_offline")
    assert out2 == "Service offline"


def test_get_message_replaces_placeholders(patch_platform, monkeypatch):
    import app.services.core.message_templates as msg_tpl

    class MockTenantService:
        def get_tenant_settings(self, tenant):
            return {}

    monkeypatch.setattr(msg_tpl, "get_tenant_service", lambda: MockTenantService())
    out = get_message("t1", "followup_confirm", name="Jane", pro="Dr. Smith", time="10:00", tenant="Clinic")
    assert "Jane" in out
    assert "Dr. Smith" in out
    assert "10:00" in out
    assert "Clinic" in out


def test_get_message_tenant_override(patch_platform, monkeypatch):
    import app.services.core.message_templates as msg_tpl

    class MockTenantService:
        def get_tenant_settings(self, tenant):
            return {"message_templates": {"whatsapp_hello": "Hi there!"}}

    monkeypatch.setattr(msg_tpl, "get_tenant_service", lambda: MockTenantService())
    out = get_message("t1", "whatsapp_hello")
    assert out == "Hi there!"


def test_unknown_key_returns_empty(patch_platform, monkeypatch):
    import app.services.core.message_templates as msg_tpl

    class MockTenantService:
        def get_tenant_settings(self, tenant):
            return {}

    monkeypatch.setattr(msg_tpl, "get_tenant_service", lambda: MockTenantService())
    out = get_message("t1", "unknown_key_xyz")
    assert out == ""
