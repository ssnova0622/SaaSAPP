"""Dispatcher ``run_action`` routes workflows, FSM starters, and registered steps."""
from __future__ import annotations

import asyncio
from unittest.mock import AsyncMock, patch

from app.services.whatsapp import action_executor_service as aes


def _run(coro):
    return asyncio.run(coro)


def test_run_action_starts_workflow() -> None:
    session = {"ctx": {}}

    async def fake_step(tenant, phone, sess):
        sess["ctx"]["step_idx"] = 1
        return "Pick a service:"

    with patch.object(aes, "get_session", return_value=session), patch.object(
        aes, "save_session"
    ), patch.object(aes.WorkflowEngine, "execute_next_step", side_effect=fake_step), patch.object(
        aes, "workflow_reply_or_welcome", side_effect=lambda t, r: r
    ):
        reply = _run(aes.run_action("acme", "workflow.booking", {"phone": "+100"}))

    assert reply == "Pick a service:"
    assert session["ctx"]["workflow_id"] == "booking"
    assert session["ctx"]["flow_data"] == {}


def test_run_action_starts_booking_workflow_when_available() -> None:
    session = {"ctx": {}}

    async def fake_step(tenant, phone, sess):
        return "Choose a service:"

    with patch.object(aes, "get_session", return_value=session), patch.object(
        aes, "save_session"
    ), patch.object(
        aes, "resolve_default_booking_workflow", return_value="salon_booking_flow"
    ), patch.object(aes.WorkflowEngine, "execute_next_step", side_effect=fake_step), patch.object(
        aes, "workflow_reply_or_welcome", side_effect=lambda t, r: r
    ):
        reply = _run(aes.run_action("acme", "book_appointment", {"phone": "+100"}))

    assert reply == "Choose a service:"
    assert session["ctx"]["workflow_id"] == "salon_booking_flow"


def test_run_action_starts_booking_fsm_when_no_workflow() -> None:
    with patch.object(aes, "get_session", return_value={"ctx": {"mode": "stale"}}), patch.object(
        aes, "save_session"
    ), patch.object(aes, "resolve_default_booking_workflow", return_value=None), patch(
        "app.services.whatsapp.usecases.salon.booking_flow.start_timeslot_flow",
        new_callable=AsyncMock,
        return_value="Choose a service:",
    ) as mock_start:
        reply = _run(aes.run_action("acme", "book_appointment", {"phone": "+100"}))

    assert reply == "Choose a service:"
    mock_start.assert_awaited_once()


def test_run_action_dispatches_registered_cancel() -> None:
    session = {"ctx": {}}
    with patch.object(aes, "get_session", return_value=session), patch.object(
        aes, "save_session"
    ), patch.object(aes, "execute_run", new_callable=AsyncMock, return_value="Cancel which?"), patch.object(
        aes, "is_registered", return_value=True
    ):
        reply = _run(aes.run_action("acme", "cancel_appointment", {"phone": "+100"}))

    assert reply == "Cancel which?"
