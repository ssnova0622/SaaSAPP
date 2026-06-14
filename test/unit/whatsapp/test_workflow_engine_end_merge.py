"""Workflow engine: merge END step output with prior informational step in one turn."""
from __future__ import annotations

import asyncio

import pytest

from app.models.workflows import WorkflowDefinition, WorkflowStep
from app.services.whatsapp.workflow import workflow_engine as we


def _run(coro):
    return asyncio.run(coro)


def test_informational_step_then_end_no_wait(monkeypatch):
    wf = WorkflowDefinition(
        tenant="acme",
        workflow_id="svc_end",
        name="Services then end",
        steps=[
            WorkflowStep(action_code="SHOW_SERVICES"),
            WorkflowStep(action_code="END", label="Thanks for browsing!"),
        ],
    )
    monkeypatch.setattr(we.WorkflowEngine, "get_workflow", lambda t, wid: wf if wid == "svc_end" else None)

    calls: list[str] = []

    async def fake_execute_run(action_code, tenant, phone, session, step):
        calls.append(action_code)
        ac = (action_code or "").lower()
        if "show_services" in ac:
            return "1) Haircut\n2) Color"
        if ac == "end" or ac.endswith(".end"):
            return (step.label or "").strip() or "done"
        return None

    monkeypatch.setattr(we, "execute_run", fake_execute_run)

    session: dict = {"ctx": {"workflow_id": "svc_end", "step_idx": 0, "waiting_for_input": False}}
    reply = _run(we.WorkflowEngine.execute_next_step("acme", "+100", session))

    assert "Haircut" in reply
    assert "Thanks for browsing" in reply
    assert session["ctx"].get("workflow_id") is None
    assert session["ctx"].get("waiting_for_input") is not True
    assert session["ctx"].get("flow_ended") is True
    assert len(calls) == 2


def test_show_services_then_select_date_still_waits(monkeypatch):
    wf = WorkflowDefinition(
        tenant="acme",
        workflow_id="svc_date",
        name="Services then date",
        steps=[
            WorkflowStep(action_code="SHOW_SERVICES"),
            WorkflowStep(action_code="SELECT_DATE"),
        ],
    )
    monkeypatch.setattr(we.WorkflowEngine, "get_workflow", lambda t, wid: wf if wid == "svc_date" else None)

    async def fake_execute_run(action_code, tenant, phone, session, step):
        if "show_services" in (action_code or "").lower():
            return "Pick a service:"
        return "date?"

    monkeypatch.setattr(we, "execute_run", fake_execute_run)

    session = {"ctx": {"workflow_id": "svc_date", "step_idx": 0, "waiting_for_input": False}}
    reply = _run(we.WorkflowEngine.execute_next_step("acme", "+100", session))

    assert reply == "Pick a service:"
    assert session["ctx"].get("waiting_for_input") is True
    assert session["ctx"].get("workflow_id") == "svc_date"
    assert session["ctx"].get("step_idx") == 0


def test_confirm_yes_appends_end_message(monkeypatch):
    """After user confirms, END closing text must appear in the same turn."""
    from app.helpers.constants_action import CONFIRM_BOOKING, END

    wf = WorkflowDefinition(
        tenant="acme",
        workflow_id="confirm_end",
        name="Confirm then end",
        steps=[
            WorkflowStep(action_code=CONFIRM_BOOKING),
            WorkflowStep(action_code=END, label="Thanks — your booking is complete!"),
        ],
    )
    monkeypatch.setattr(we.WorkflowEngine, "get_workflow", lambda t, wid: wf if wid == "confirm_end" else None)

    async def fake_execute_run(action_code, tenant, phone, session, step):
        ac = (action_code or "").lower()
        ctx = session.setdefault("ctx", {})
        flow = ctx.setdefault("flow_data", {})
        if "confirm" in ac:
            pend = "confirm_booking_user_input_pending"
            if flow.get(pend) is not None:
                ctx["_wa_skip_input_wait_once"] = True
                return "Booking confirmed!"
            return "Confirm?\n1) Yes\n2) No"
        if ac == "end" or ac.endswith(".end"):
            return (step.label or "").strip()
        return None

    monkeypatch.setattr(we, "execute_run", fake_execute_run)

    session = {"ctx": {"workflow_id": "confirm_end", "step_idx": 0, "waiting_for_input": False}}
    _run(we.WorkflowEngine.execute_next_step("acme", "+100", session))
    session["ctx"]["waiting_for_input"] = True
    reply = _run(we.WorkflowEngine.execute_next_step("acme", "+100", session, user_input="1"))

    assert "Booking confirmed" in reply
    assert "Thanks — your booking is complete" in reply
    assert session["ctx"].get("flow_ended") is True
    assert session["ctx"].get("workflow_id") is None


def test_confirm_yes_with_empty_booking_msg_still_shows_end(monkeypatch):
    """END must show even when finalize returns no booking text."""
    from app.helpers.constants_action import CONFIRM_BOOKING, END

    wf = WorkflowDefinition(
        tenant="acme",
        workflow_id="confirm_end2",
        name="Confirm then end",
        steps=[
            WorkflowStep(action_code=CONFIRM_BOOKING),
            WorkflowStep(action_code=END, label="All done!"),
        ],
    )
    monkeypatch.setattr(we.WorkflowEngine, "get_workflow", lambda t, wid: wf if wid == "confirm_end2" else None)

    async def fake_execute_run(action_code, tenant, phone, session, step):
        ac = (action_code or "").lower()
        ctx = session.setdefault("ctx", {})
        flow = ctx.setdefault("flow_data", {})
        if "confirm" in ac:
            if flow.get("confirm_booking_user_input_pending") is not None:
                ctx["_wa_skip_input_wait_once"] = True
                return None
            return "Confirm?"
        if ac == "end":
            return (step.label or "").strip()
        return None

    monkeypatch.setattr(we, "execute_run", fake_execute_run)

    session = {"ctx": {"workflow_id": "confirm_end2", "step_idx": 0, "waiting_for_input": True}}
    reply = _run(we.WorkflowEngine.execute_next_step("acme", "+100", session, user_input="yes"))

    assert "All done!" in reply
    assert session["ctx"].get("flow_ended") is True


def test_confirm_then_end_waits_for_yes_no(monkeypatch):
    """CONFIRM_BOOKING → END must wait for user confirmation (not merge END immediately)."""
    from app.helpers.constants_action import CONFIRM_BOOKING, END

    wf = WorkflowDefinition(
        tenant="acme",
        workflow_id="confirm_end",
        name="Confirm then end",
        steps=[
            WorkflowStep(action_code=CONFIRM_BOOKING),
            WorkflowStep(action_code=END, label="Thanks!"),
        ],
    )
    monkeypatch.setattr(we.WorkflowEngine, "get_workflow", lambda t, wid: wf if wid == "confirm_end" else None)

    async def fake_execute_run(action_code, tenant, phone, session, step):
        ac = (action_code or "").lower()
        if "confirm" in ac:
            return "Confirm booking?\n1) Yes\n2) No"
        if ac == "end" or ac.endswith(".end"):
            return (step.label or "").strip()
        return None

    monkeypatch.setattr(we, "execute_run", fake_execute_run)

    session = {"ctx": {"workflow_id": "confirm_end", "step_idx": 0, "waiting_for_input": False}}
    reply = _run(we.WorkflowEngine.execute_next_step("acme", "+100", session))

    assert "Confirm booking" in reply
    assert "Thanks" not in reply
    assert session["ctx"].get("waiting_for_input") is True
    assert session["ctx"].get("workflow_id") == "confirm_end"
    assert session["ctx"].get("step_idx") == 0
