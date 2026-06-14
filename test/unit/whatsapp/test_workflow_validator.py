"""Workflow definition validation and booking workflow resolution."""
from __future__ import annotations

from unittest.mock import patch

import pytest

from app.helpers.constants_action import END, SHOW_SERVICES
from app.models.workflows import WorkflowDefinition, WorkflowStep
from app.services.whatsapp.workflow.workflow_resolver import resolve_default_booking_workflow
from app.services.whatsapp.workflow.workflow_validator import (
    WorkflowValidationError,
    assert_workflow_valid,
    validate_workflow_definition,
)


def _salon_settings():
    return {
        "modules": ["salon"],
        "capabilities": ["salon.appointments"],
        "enabled_action_ids": [],
    }


def test_validate_workflow_requires_end_step():
    wf = WorkflowDefinition(
        tenant="t1",
        workflow_id="bad_flow",
        name="Bad",
        steps=[WorkflowStep(action_code=SHOW_SERVICES, label="Pick")],
    )
    with patch("app.services.whatsapp.usecases.action_registry.get_tenant_service") as mock_ts:
        mock_ts.return_value.get_tenant_settings.return_value = _salon_settings()
        errors = validate_workflow_definition("t1", wf)
    assert any("END" in e for e in errors)


def test_validate_workflow_rejects_unknown_action():
    wf = WorkflowDefinition(
        tenant="t1",
        workflow_id="bad_flow",
        name="Bad",
        steps=[
            WorkflowStep(action_code="NOT_A_REAL_ACTION", label="Nope"),
            WorkflowStep(action_code=END, label="Done"),
        ],
    )
    with patch("app.services.whatsapp.usecases.action_registry.get_tenant_service") as mock_ts:
        mock_ts.return_value.get_tenant_settings.return_value = _salon_settings()
        errors = validate_workflow_definition("t1", wf)
    assert any("unknown action" in e.lower() for e in errors)


def test_validate_workflow_accepts_salon_booking_flow():
    wf = WorkflowDefinition(
        tenant="t1",
        workflow_id="salon_booking_flow",
        name="Booking",
        requires_caps=["appointments"],
        steps=[
            WorkflowStep(action_code=SHOW_SERVICES, label="Pick"),
            WorkflowStep(action_code=END, label="Done"),
        ],
    )
    with patch("app.services.whatsapp.usecases.action_registry.get_tenant_service") as mock_ts:
        mock_ts.return_value.get_tenant_settings.return_value = _salon_settings()
        errors = validate_workflow_definition("t1", wf)
    assert errors == []


def test_assert_workflow_valid_raises():
    wf = WorkflowDefinition(tenant="t1", workflow_id="", name="X", steps=[])
    with pytest.raises(WorkflowValidationError):
        assert_workflow_valid("t1", wf)


def test_resolve_default_booking_workflow_prefers_conventional_id():
    wfs = [
        WorkflowDefinition(
            tenant="t1",
            workflow_id="other_flow",
            name="Other",
            steps=[WorkflowStep(action_code=END, label="x")],
        ),
        WorkflowDefinition(
            tenant="t1",
            workflow_id="salon_booking_flow",
            name="Booking",
            steps=[WorkflowStep(action_code=SHOW_SERVICES, label="x"), WorkflowStep(action_code=END, label="y")],
        ),
    ]
    with patch(
        "app.services.whatsapp.workflow.workflow_resolver.list_workflows",
        return_value=wfs,
    ):
        assert resolve_default_booking_workflow("t1") == "salon_booking_flow"


def test_resolve_default_booking_workflow_none_when_empty():
    with patch(
        "app.services.whatsapp.workflow.workflow_resolver.list_workflows",
        return_value=[],
    ):
        assert resolve_default_booking_workflow("t1") is None
