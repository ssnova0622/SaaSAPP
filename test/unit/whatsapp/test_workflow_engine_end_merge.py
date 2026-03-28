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
