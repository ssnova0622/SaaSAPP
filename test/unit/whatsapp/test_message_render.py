"""Tests for WhatsApp message rendering and custom actions."""
import pytest
from fastapi import HTTPException

from app.services.whatsapp.message_render_service import (
    render_message_template,
    sanitize_message_text,
    validate_placeholders,
)
from app.services.whatsapp.custom_action_service import (
    validate_custom_action_payload,
    custom_action_runtime_id,
)


def test_render_placeholders():
    out = render_message_template(
        "Hello {{name}} at {{business_name}}",
        {"name": "Ali", "business_name": "FitZone"},
        sanitize=False,
    )
    assert out == "Hello Ali at FitZone"


def test_validate_placeholders_rejects_unknown():
    assert validate_placeholders("Hi {{evil_key}}") is not None


def test_sanitize_blocks_script():
    with pytest.raises(ValueError):
        sanitize_message_text("<script>alert(1)</script>")


def test_custom_action_runtime_id():
    assert custom_action_runtime_id("welcome_hours") == "custom.welcome_hours"


def test_validate_custom_action_static_text():
    payload = validate_custom_action_payload(
        "tenant_demo",
        {
            "action_id": "hours",
            "name": "Hours",
            "action_type": "static_text",
            "text": "Open at {{business_name}}",
        },
    )
    assert payload["action_id"] == "hours"


def test_validate_custom_action_bad_id():
    with pytest.raises(HTTPException):
        validate_custom_action_payload(
            "tenant_demo",
            {"action_id": "BAD ID", "name": "x", "action_type": "static_text", "text": "hi"},
        )
