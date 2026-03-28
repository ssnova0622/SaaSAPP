"""
Integration-style tests for salon booking FSM: in-memory session + container mocks.

These are not full E2E tests; they guard core transitions without Mongo or real WhatsApp.
"""
from __future__ import annotations

import asyncio
from types import SimpleNamespace
from typing import Any, Dict
import pytest

import app.services.whatsapp.usecases.salon.booking_flow as booking_flow
import app.services.whatsapp.usecases.salon.booking_timeslot_start as booking_timeslot_start
from app.services.whatsapp.helpers import constants as WMSG


def _run(coro):
    return asyncio.run(coro)


def _patch_booking_session_backends(monkeypatch, fake_get_session, fake_save_session) -> None:
    """Patch both modules: ``handle_timeslot_fsm`` uses ``booking_flow`` bindings; ``start_timeslot_flow`` uses ``booking_timeslot_start``."""
    monkeypatch.setattr(booking_flow, "get_session", fake_get_session)
    monkeypatch.setattr(booking_flow, "save_session", fake_save_session)
    monkeypatch.setattr(booking_timeslot_start, "get_session", fake_get_session)
    monkeypatch.setattr(booking_timeslot_start, "save_session", fake_save_session)


@pytest.fixture
def memory_session(monkeypatch):
    store: Dict[tuple, Dict[str, Any]] = {}

    def fake_get_session(tenant: str, phone: str) -> Dict[str, Any]:
        key = (tenant, phone)
        if key not in store:
            store[key] = {"ctx": {}}
        return store[key]

    def fake_save_session(tenant: str, phone: str, session: Dict[str, Any], ttl_minutes: int = 30) -> None:
        store[(tenant, phone)] = session

    _patch_booking_session_backends(monkeypatch, fake_get_session, fake_save_session)
    return store


def _patch_timeslot_flow_services(monkeypatch, tenant, salon, appt) -> None:
    monkeypatch.setattr(booking_flow, "get_tenant_service", lambda: tenant)
    monkeypatch.setattr(booking_timeslot_start, "get_tenant_service", lambda: tenant)
    monkeypatch.setattr(booking_timeslot_start, "get_salon_services", lambda: salon)
    monkeypatch.setattr(booking_timeslot_start, "get_appointment_service", lambda: appt)


@pytest.fixture
def mock_booking_container(monkeypatch, memory_session):
    """Minimal tenant, salon, appointments for ``start_timeslot_flow`` / date branch."""

    class _Tenant:
        def get_tenant_settings(self, tenant: str) -> dict:
            return {"category": WMSG.BIZ_CATEGORY_SALON, "timezone": "UTC"}

        def _get_tenant_country_code(self, tenant: str) -> str:
            return "1"

    class _Salon:
        def list_services(self, tenant: str) -> list:
            return [{"name": "Haircut", "active": True}]

    class _Appt:
        async def list_appointments(self, *args, **kwargs):
            return []

    _patch_timeslot_flow_services(monkeypatch, _Tenant(), _Salon(), _Appt())


def test_fsm_menu_keyword_clears_ctx(memory_session, monkeypatch):
    memory_session[("acme", "+100")] = {
        "ctx": {
            "mode": "select_service",
            "available_services": ["A", "B"],
        }
    }

    out = _run(booking_flow.handle_timeslot_fsm("acme", "+100", "menu"))
    assert out is None
    assert memory_session[("acme", "+100")]["ctx"] == {}


def test_fsm_invalid_service_choice_returns_prompt(memory_session, monkeypatch):
    memory_session[("acme", "+100")] = {
        "ctx": {
            "mode": "select_service",
            "available_services": ["Cut", "Color"],
        }
    }

    out = _run(booking_flow.handle_timeslot_fsm("acme", "+100", "99"))
    assert out == WMSG.MSG_PLEASE_CHOOSE_SERVICE


def test_start_timeslot_flow_lists_db_service(mock_booking_container, memory_session):
    reply = _run(booking_flow.start_timeslot_flow("acme", "+100"))
    assert "Haircut" in reply
    assert "1)" in reply


def test_fsm_service_then_today_reaches_slot_prompt(mock_booking_container, memory_session, monkeypatch):
    """Service → date (today) → pick staff → see slot times."""
    async def fake_slots(*args, **kwargs):
        return ["10:00", "11:00"]

    monkeypatch.setattr(booking_flow, "get_available_slots", fake_slots)

    class _Prof:
        name = "Alex"
        services = ["Haircut"]
        availability_criteria = "daily"
        available_days = []
        date_overrides = {}

        @property
        def slots(self):
            return [
                SimpleNamespace(status="available", time="10:00"),
                SimpleNamespace(status="available", time="11:00"),
            ]

    class _ProfSvc:
        def get_professionals(self, tenant: str):
            return [_Prof()]

    monkeypatch.setattr(booking_flow, "get_professional_service", lambda: _ProfSvc())

    first = _run(booking_flow.start_timeslot_flow("acme", "+100"))
    assert "Haircut" in first

    second = _run(booking_flow.handle_timeslot_fsm("acme", "+100", "1"))
    assert WMSG.MSG_DATE_ROW_TODAY.split("(")[0].strip() in second or "1)" in second

    third = _run(booking_flow.handle_timeslot_fsm("acme", "+100", "1"))
    assert WMSG.MSG_DO_YOU_PREFER_STAFF in third
    assert "Alex" in third

    fourth = _run(booking_flow.handle_timeslot_fsm("acme", "+100", "1"))
    assert "10:00" in fourth or "11:00" in fourth
