"""SHOW_SERVICE_PRICES workflow action."""
from __future__ import annotations

import asyncio
from unittest.mock import patch

from app.helpers.constants_action import END, SHOW_SERVICE_PRICES
from app.models.workflows import WorkflowDefinition, WorkflowStep
from app.services.whatsapp.workflow import workflow_engine as we


def _run(coro):
    return asyncio.run(coro)


def test_show_service_prices_lists_active_services_with_prices(monkeypatch):
    monkeypatch.setattr(
        "app.services.whatsapp.usecases.salon.salon_actions.Storage.list_services",
        lambda tenant, active=True: [
            {"name": "Haircut (Women)", "price": 600, "duration": 45, "active": True},
            {"name": "Facial", "price": 800, "duration": 60, "active": True},
        ],
    )
    monkeypatch.setattr(
        "app.services.whatsapp.usecases.salon.salon_actions.get_tenant_service",
        lambda: type("T", (), {"get_tenant_settings": lambda self, t: {"currency": "INR"}})(),
    )

    wf = WorkflowDefinition(
        tenant="acme",
        workflow_id="price_list",
        name="Prices",
        steps=[
            WorkflowStep(action_code=SHOW_SERVICE_PRICES),
            WorkflowStep(action_code=END, label="Reply *hi* for the main menu."),
        ],
    )
    monkeypatch.setattr(we.WorkflowEngine, "get_workflow", lambda t, wid: wf if wid == "price_list" else None)

    session = {"ctx": {"workflow_id": "price_list", "step_idx": 0, "waiting_for_input": False}}
    reply = _run(we.WorkflowEngine.execute_next_step("acme", "+100", session))

    assert "Haircut (Women)" in reply
    assert "₹600" in reply
    assert "45 min" in reply
    assert "Facial" in reply
    assert "₹800" in reply
    assert "Reply *hi* for the main menu" in reply
    assert session["ctx"].get("flow_ended") is True


def test_show_service_prices_no_services(monkeypatch):
    monkeypatch.setattr(
        "app.services.whatsapp.usecases.salon.salon_actions.Storage.list_services",
        lambda tenant, active=True: [],
    )
    monkeypatch.setattr(
        "app.services.whatsapp.usecases.salon.salon_actions.wa",
        lambda tenant, key, **kw: "No services available." if key == "wa_salon_no_services" else key,
    )

    from app.services.whatsapp.usecases.salon.salon_actions import SalonActions
    from app.models.workflow import WorkflowStep

    reply = _run(
        SalonActions._run_show_service_prices("acme", "+1", {"ctx": {}}, WorkflowStep(action_code=SHOW_SERVICE_PRICES))
    )
    assert reply == "No services available."


def test_run_action_dispatches_show_service_prices(monkeypatch):
    from app.services.whatsapp import action_executor_service as aes

    async def fake_execute(*args, **kwargs):
        return "1) Cut – ₹600"

    session = {"ctx": {}}
    with patch.object(aes, "get_session", return_value=session), patch.object(
        aes, "save_session"
    ), patch.object(aes, "execute_run", side_effect=fake_execute), patch.object(
        aes, "is_registered", return_value=True
    ):
        reply = _run(aes.run_action("acme", "show_service_prices", {"phone": "+100"}))
    assert "₹600" in reply
