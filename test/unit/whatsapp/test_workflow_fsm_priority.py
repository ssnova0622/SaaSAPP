"""Workflow session must win over legacy FSM and root menu digit routing."""
from __future__ import annotations

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.services.whatsapp.pipeline.inbound_pipeline import (
    _session_has_active_workflow,
    _stage_active_workflow,
    _stage_menu_navigation,
    _stage_run_fsm,
)


def _run(coro):
    return asyncio.run(coro)


def test_session_has_active_workflow() -> None:
    assert _session_has_active_workflow({"ctx": {"workflow_id": "book_flow"}}) is True
    assert _session_has_active_workflow({"ctx": {"mode": "select_slot"}}) is False
    assert _session_has_active_workflow({"ctx": {}}) is False


def test_fsm_skipped_when_workflow_active() -> None:
    ctx = {
        "tenant": "acme",
        "phone": "+100",
        "user_input": "3",
        "tree": {},
        "fsm_reply": "should-not-be-set",
    }
    session = {"ctx": {"workflow_id": "book", "step_idx": 1, "waiting_for_input": True}}

    with patch(
        "app.services.whatsapp.pipeline.inbound_pipeline.get_session",
        return_value=session,
    ), patch(
        "app.services.whatsapp.pipeline.inbound_pipeline.handle_timeslot_fsm",
        new_callable=AsyncMock,
    ) as mock_fsm:
        _run(_stage_run_fsm(ctx))
        mock_fsm.assert_not_called()
        assert ctx["fsm_reply"] is None


def test_active_workflow_advances_with_user_input() -> None:
    ctx = {
        "tenant": "acme",
        "phone": "+100",
        "user_input": "2",
        "tree": {"root": "root"},
        "root_id": "root",
        "locale": "en",
        "fsm_reply": None,
    }
    session = {
        "ctx": {
            "workflow_id": "svc_time",
            "step_idx": 1,
            "waiting_for_input": True,
            "flow_data": {"available_slots": ["09:00", "10:00"]},
        }
    }

    with patch(
        "app.services.whatsapp.pipeline.inbound_pipeline.get_session",
        return_value=session,
    ), patch(
        "app.services.whatsapp.pipeline.inbound_pipeline.save_session",
    ) as mock_save, patch(
        "app.services.whatsapp.pipeline.inbound_pipeline.WorkflowEngine.execute_next_step",
        new_callable=AsyncMock,
        return_value="Confirm booking?",
    ) as mock_exec, patch(
        "app.services.whatsapp.pipeline.inbound_pipeline.workflow_reply_or_welcome",
        side_effect=lambda t, r: r,
    ):
        out = _run(_stage_active_workflow(ctx))

    assert out is not None
    assert out["node"] == "workflow"
    assert out["reply"] == "Confirm booking?"
    mock_exec.assert_awaited_once_with("acme", "+100", session, user_input="2")
    mock_save.assert_called_once()


def test_menu_navigation_delegates_to_workflow_not_root_option() -> None:
    """Digit '3' must not trigger root menu option 3 while a workflow is active."""
    ctx = {
        "tenant": "acme",
        "phone": "+100",
        "user_input": "3",
        "tree": {
            "root": "root",
            "nodes": {
                "root": {
                    "type": "submenu",
                    "options": [
                        {"key": "1", "next": "workflow.book"},
                        {"key": "2", "next": "cancel"},
                        {"key": "3", "next": "reschedule"},
                    ],
                }
            },
        },
        "root_id": "root",
        "locale": "en",
        "client_node": None,
    }
    session = {
        "last_node": "root",
        "ctx": {
            "workflow_id": "book",
            "step_idx": 0,
            "waiting_for_input": True,
            "flow_data": {"professionals": ["A", "B", "C"]},
        },
    }

    with patch(
        "app.services.whatsapp.pipeline.inbound_pipeline.get_session",
        return_value=session,
    ), patch(
        "app.services.whatsapp.pipeline.inbound_pipeline.find_node",
        return_value=ctx["tree"]["nodes"]["root"],
    ), patch(
        "app.services.whatsapp.pipeline.inbound_pipeline.save_session",
    ), patch(
        "app.services.whatsapp.pipeline.inbound_pipeline.WorkflowEngine.execute_next_step",
        new_callable=AsyncMock,
        return_value="Pick a time slot:",
    ) as mock_exec, patch(
        "app.services.whatsapp.pipeline.inbound_pipeline.workflow_reply_or_welcome",
        side_effect=lambda t, r: r,
    ):
        out = _run(_stage_menu_navigation(ctx))

    assert out is not None
    assert out["node"] == "workflow"
    assert "time" in out["reply"].lower()
    mock_exec.assert_awaited_once()
