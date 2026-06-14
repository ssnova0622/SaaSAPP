"""
End-to-end workflow booking tests: WorkflowEngine + salon handlers + inbound pipeline.

Mocks DB/services only; exercises real step handlers and session flow_data routing.
"""
from __future__ import annotations

import asyncio
from typing import Any, Dict, List
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.helpers.constants_action import CONFIRM_BOOKING, END, SELECT_TIME, SHOW_PROFESSIONALS, SHOW_SERVICES
from app.models.workflows import WorkflowDefinition, WorkflowStep
from app.services.whatsapp.pipeline.inbound_pipeline import handle_incoming
from app.services.whatsapp.workflow.workflow_engine import WorkflowEngine


def _run(coro):
    return asyncio.run(coro)


TENANT = "acme"
PHONE = "+15551234567"
SERVICES = ["Haircut", "Color"]
PROS = ["Alex", "Jordan"]
SLOTS = ["09:00", "10:00", "11:00"]


@pytest.fixture
def session_store(monkeypatch):
    store: Dict[tuple, Dict[str, Any]] = {}

    def fake_get(tenant: str, phone: str) -> Dict[str, Any]:
        key = (tenant, phone)
        if key not in store:
            store[key] = {"ctx": {}, "last_node": "root"}
        return store[key]

    def fake_save(tenant: str, phone: str, session: Dict[str, Any], ttl_minutes: int = 30) -> None:
        store[(tenant, phone)] = session

    for mod in (
        "app.services.whatsapp.session_flow_service",
        "app.services.whatsapp.pipeline.inbound_pipeline",
        "app.services.whatsapp.action_executor_service",
    ):
        monkeypatch.setattr(f"{mod}.get_session", fake_get)
        monkeypatch.setattr(f"{mod}.save_session", fake_save)

    return store


@pytest.fixture
def mock_salon_backend(monkeypatch):
    class _Tenant:
        def get_tenant_settings(self, tenant: str) -> dict:
            return {"category": "salon", "timezone": "UTC", "business_name": "Test Salon"}

        def _get_tenant_country_code(self, tenant: str) -> str:
            return "1"

    class _Prof:
        def __init__(self, name: str):
            self.name = name
            self.services = list(SERVICES)
            self.availability_criteria = "daily"
            self.available_days = []
            self.date_overrides = {}
            self.slots = [{"time": t, "status": "available"} for t in SLOTS]

    class _ProfSvc:
        @staticmethod
        def get_professionals(tenant: str) -> List[_Prof]:
            return [_Prof(n) for n in PROS]

        @staticmethod
        def filter_professionals(tenant: str, date_str=None, service=None) -> List[str]:
            return list(PROS)

    async def fake_slots(tenant, professional_name=None, limit=6, date_str=None):
        return list(SLOTS)

    monkeypatch.setattr(
        "app.services.whatsapp.usecases.salon.salon_actions.Storage.list_services",
        lambda tenant: [{"name": s, "active": True} for s in SERVICES],
    )
    monkeypatch.setattr(
        "app.services.salon.professional_service.ProfessionalService.filter_professionals",
        _ProfSvc.filter_professionals,
    )
    monkeypatch.setattr(
        "app.services.whatsapp.usecases.salon.salon_actions.get_professional_service",
        lambda: _ProfSvc(),
    )
    monkeypatch.setattr(
        "app.services.whatsapp.usecases.salon.salon_actions.get_tenant_service",
        lambda: _Tenant(),
    )
    monkeypatch.setattr(
        "app.services.whatsapp.usecases.core.core_actions.get_tenant_service",
        lambda: _Tenant(),
    )
    monkeypatch.setattr(
        "app.services.whatsapp.usecases.salon.salon_actions.SalonActions.get_available_slots",
        fake_slots,
    )
    monkeypatch.setattr(
        "app.services.whatsapp.usecases.salon.booking_flow.get_available_slots",
        fake_slots,
    )
    monkeypatch.setattr(
        "app.services.whatsapp.usecases.salon.booking_flow.list_professionals",
        lambda tenant, date_str=None, service=None: list(PROS),
    )
    monkeypatch.setattr(
        "app.services.whatsapp.workflow.workflow_engine.get_tenant_service",
        lambda: _Tenant(),
    )


def _wf_services_time_confirm() -> WorkflowDefinition:
    return WorkflowDefinition(
        tenant=TENANT,
        workflow_id="book_svc_time",
        name="Service then time",
        steps=[
            WorkflowStep(action_code=SHOW_SERVICES, label="Pick a service:"),
            WorkflowStep(action_code=SELECT_TIME, label="Pick a time:"),
            WorkflowStep(action_code=CONFIRM_BOOKING, label="Confirm?"),
            WorkflowStep(action_code=END, label="Booked!"),
        ],
    )


def _wf_pro_time_confirm() -> WorkflowDefinition:
    return WorkflowDefinition(
        tenant=TENANT,
        workflow_id="book_pro_time",
        name="Professional then time",
        steps=[
            WorkflowStep(action_code=SHOW_PROFESSIONALS, label="Pick staff:"),
            WorkflowStep(action_code=SELECT_TIME, label="Pick a time:"),
            WorkflowStep(action_code=CONFIRM_BOOKING, label="Confirm?"),
            WorkflowStep(action_code=END, label="Done!"),
        ],
    )


def _menu_tree() -> dict:
    return {
        "root": "root",
        "nodes": [
            {
                "id": "root",
                "type": "submenu",
                "title": "Welcome",
                "prompt": "Choose:",
                "options": [
                    {"key": "1", "label": "Book", "next": "workflow.book_svc_time"},
                    {"key": "2", "label": "Cancel", "next": "workflow.cancel"},
                    {"key": "3", "label": "Reschedule", "next": "workflow.reschedule"},
                ],
            }
        ],
    }


def _patch_workflow(monkeypatch, wf: WorkflowDefinition) -> None:
    monkeypatch.setattr(
        WorkflowEngine,
        "get_workflow",
        staticmethod(lambda t, wid: wf if wid == wf.workflow_id else None),
    )


def _patch_menu(monkeypatch) -> None:
    tree = _menu_tree()
    mdoc = {"tree": tree, "status": "published", "menu_id": "welcome_message"}

    monkeypatch.setattr(
        "app.services.whatsapp.pipeline.inbound_pipeline.get_whatsapp_service",
        lambda: MagicMock(
            get_whatsapp_menu=lambda *a, **k: mdoc,
            list_whatsapp_menus=lambda *a, **k: [mdoc],
        ),
    )
    monkeypatch.setattr(
        "app.services.whatsapp.pipeline.inbound_pipeline.get_tenant_service",
        lambda: MagicMock(get_tenant_settings=lambda t: {"capabilities": ["salon.appointments"]}),
    )
    monkeypatch.setattr(
        "app.services.whatsapp.pipeline.inbound_pipeline._use_nl",
        lambda t: False,
    )
    monkeypatch.setattr(
        "app.services.whatsapp.pipeline.inbound_pipeline.evaluate_triggers",
        lambda *a, **k: None,
    )
    monkeypatch.setattr(
        "app.services.whatsapp.pipeline.inbound_pipeline.send_submenu_reply",
        lambda *a, **k: "Main menu",
    )


async def _drive_workflow(session: dict, wf: WorkflowDefinition, inputs: List[str]) -> List[str]:
    replies: List[str] = []
    session["ctx"] = {"workflow_id": wf.workflow_id, "step_idx": 0, "waiting_for_input": False, "flow_data": {}}
    r0 = await WorkflowEngine.execute_next_step(TENANT, PHONE, session)
    replies.append(r0 or "")
    for ui in inputs:
        r = await WorkflowEngine.execute_next_step(TENANT, PHONE, session, user_input=ui)
        replies.append(r or "")
    return replies


def test_workflow_services_then_time(session_store, mock_salon_backend, monkeypatch):
    wf = _wf_services_time_confirm()
    _patch_workflow(monkeypatch, wf)

    session = {"ctx": {}, "last_node": "root"}
    replies = _run(_drive_workflow(session, wf, ["1", "2", "1", "1"]))

    assert any("Haircut" in r for r in replies)
    assert any("09:00" in r or "10:00" in r for r in replies)
    assert any("Confirm" in r or "Yes" in r for r in replies)
    fd = session["ctx"].get("flow_data") or {}
    assert fd.get("service") == "Haircut"
    assert fd.get("selected_slot") == "10:00"


def test_workflow_professionals_then_time(session_store, mock_salon_backend, monkeypatch):
    wf = _wf_pro_time_confirm()
    _patch_workflow(monkeypatch, wf)

    session = {"ctx": {}, "last_node": "root"}
    replies = _run(_drive_workflow(session, wf, ["2", "1", "1", "1"]))

    fd = session["ctx"].get("flow_data") or {}
    assert fd.get("professional") == "Jordan"
    assert fd.get("selected_slot") == "09:00"
    assert any("09:00" in r for r in replies)


def test_workflow_digit_not_consumed_when_not_waiting(session_store, mock_salon_backend, monkeypatch):
    """Stray digit while not waiting must not commit as a service pick."""
    wf = _wf_services_time_confirm()
    _patch_workflow(monkeypatch, wf)

    session = {
        "ctx": {
            "workflow_id": wf.workflow_id,
            "step_idx": 0,
            "waiting_for_input": False,
            "flow_data": {},
        }
    }
    reply = _run(WorkflowEngine.execute_next_step(TENANT, PHONE, session, user_input="3"))
    assert "Haircut" in reply or "Color" in reply
    assert session["ctx"].get("flow_data", {}).get("service") is None


def test_inbound_workflow_digit_not_root_menu(session_store, mock_salon_backend, monkeypatch):
    """While workflow active, '3' selects professional #3 — not root Reschedule."""
    wf = _wf_pro_time_confirm()
    _patch_workflow(monkeypatch, wf)
    _patch_menu(monkeypatch)

    session_store[(TENANT, PHONE)] = {
        "ctx": {
            "workflow_id": wf.workflow_id,
            "step_idx": 0,
            "waiting_for_input": True,
            "flow_data": {"professionals": PROS},
        },
        "last_node": "root",
    }

    with patch(
        "app.services.whatsapp.pipeline.inbound_pipeline.handle_timeslot_fsm",
        new_callable=AsyncMock,
        return_value="FSM_SHOULD_NOT_RUN",
    ):
        out = _run(handle_incoming(TENANT, PHONE, "3", locale="en"))

    assert out["node"] == "workflow"
    assert "FSM_SHOULD_NOT_RUN" not in out["reply"]
    session = session_store[(TENANT, PHONE)]
    fd = session["ctx"].get("flow_data") or {}
    assert fd.get("professional") == "Alex"


def test_inbound_workflow_service_time_confirm_path(session_store, mock_salon_backend, monkeypatch):
    wf = _wf_services_time_confirm()
    _patch_workflow(monkeypatch, wf)
    _patch_menu(monkeypatch)

    with patch(
        "app.services.whatsapp.pipeline.inbound_pipeline.handle_timeslot_fsm",
        new_callable=AsyncMock,
        return_value=None,
    ), patch(
        "app.services.whatsapp.usecases.salon.salon_actions.SalonActions._run_finalize_booking",
        new_callable=AsyncMock,
        return_value="Booking confirmed!",
    ):
        session_store[(TENANT, PHONE)] = {"ctx": {}, "last_node": "root"}

        # Start workflow from menu option 1
        r1 = _run(handle_incoming(TENANT, PHONE, "1", locale="en", client_node="root"))
        assert "Haircut" in r1["reply"] or "service" in r1["reply"].lower()

        session = session_store[(TENANT, PHONE)]
        assert session["ctx"].get("workflow_id") == wf.workflow_id
        assert session["ctx"].get("waiting_for_input") is True

        r2 = _run(handle_incoming(TENANT, PHONE, "1", locale="en"))
        assert r2["node"] == "workflow"
        assert "09:00" in r2["reply"] or "10:00" in r2["reply"]

        r3 = _run(handle_incoming(TENANT, PHONE, "1", locale="en"))
        assert "Confirm" in r3["reply"] or "Yes" in r3["reply"]
        assert "Booked" not in r3["reply"]

        r4 = _run(handle_incoming(TENANT, PHONE, "1", locale="en"))
        fd = session["ctx"].get("flow_data") or {}
        assert fd.get("service") == "Haircut"
        assert fd.get("selected_slot") == "09:00"
