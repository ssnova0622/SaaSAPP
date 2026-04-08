# test/unit/services/test_appointment_status_service.py
"""Tests for AppointmentStatusService.update_status: revenue, slots, no-show, customer sync."""
from __future__ import annotations

from datetime import datetime, timezone
from unittest.mock import MagicMock

import pytest

pytest.importorskip("mongomock")

from app.helpers.constants import (
    APPOINTMENT_STATUS_BOOKED,
    APPOINTMENT_STATUS_COMPLETED,
    APPOINTMENT_STATUS_NO_SHOW,
)
from app.services.salon.appointments import appointment_status_service as mod
from app.services.salon.appointments.appointment_status_service import AppointmentStatusService


@pytest.fixture
def tenant_ctx(monkeypatch):
    monkeypatch.setattr(
        mod.TenantService,
        "get_tenant_settings",
        staticmethod(
            lambda tenant: {
                "tz": "UTC",
                "tenant_country": "IN",
                "date_format": "%Y-%m-%d",
            }
        ),
    )
    monkeypatch.setattr(
        mod.TenantService,
        "_get_tenant_country_code",
        staticmethod(lambda tenant: "91"),
    )
    names = {}

    def _resolve(ids):
        return {i: names.get(i, f"user-{i}") for i in (ids or [])}

    monkeypatch.setattr(
        mod.UserService,
        "resolve_user_names",
        staticmethod(_resolve),
    )
    return names


def _base_appt(**over):
    start = datetime(2026, 3, 15, 10, 0, tzinfo=timezone.utc)
    doc = {
        "tenant": "t1",
        "id": "a1",
        "status": APPOINTMENT_STATUS_BOOKED,
        "price": 100.0,
        "customer_name": "Bob",
        "customer_phone_number": {"code": "+91", "number": "9876543210"},
        "professional": "Pro One",
        "professional_id": "p1",
        "time": "10:00",
        "start": start,
        "created_by": "u0",
    }
    doc.update(over)
    return doc


@pytest.mark.usefixtures("mock_db")
class TestUpdateAppointmentStatus:
    def test_raises_when_missing(self, tenant_ctx, mock_db):
        with pytest.raises(ValueError, match="Appointment not found"):
            AppointmentStatusService.update_status("t1", "missing", APPOINTMENT_STATUS_COMPLETED)

    def test_completed_increments_tenant_revenue(self, tenant_ctx, mock_db):
        mock_db.tenants.insert_one({"_id": "t1", "revenue": 0.0})
        mock_db.appointments.insert_one(_base_appt(status=APPOINTMENT_STATUS_BOOKED, price=50.0))
        out = AppointmentStatusService.update_status("t1", "a1", APPOINTMENT_STATUS_COMPLETED, user_id="u1")
        assert out["status"] == APPOINTMENT_STATUS_COMPLETED
        assert mock_db.tenants.find_one({"_id": "t1"})["revenue"] == 50.0

    def test_revert_completed_decrements_revenue(self, tenant_ctx, mock_db):
        mock_db.tenants.insert_one({"_id": "t1", "revenue": 200.0})
        mock_db.appointments.insert_one(_base_appt(status=APPOINTMENT_STATUS_COMPLETED, price=75.0))
        out = AppointmentStatusService.update_status("t1", "a1", APPOINTMENT_STATUS_BOOKED, user_id="u1")
        assert out["status"] == APPOINTMENT_STATUS_BOOKED
        assert mock_db.tenants.find_one({"_id": "t1"})["revenue"] == 125.0

    def test_no_revenue_double_count_when_already_completed(self, tenant_ctx, mock_db):
        mock_db.tenants.insert_one({"_id": "t1", "revenue": 100.0})
        mock_db.appointments.insert_one(_base_appt(status=APPOINTMENT_STATUS_COMPLETED, price=100.0))
        AppointmentStatusService.update_status("t1", "a1", APPOINTMENT_STATUS_COMPLETED, user_id="u1")
        assert mock_db.tenants.find_one({"_id": "t1"})["revenue"] == 100.0

    def test_no_show_frees_slot_and_increments_no_show(self, tenant_ctx, mock_db, monkeypatch):
        slot = MagicMock()
        inc = MagicMock(return_value=2)
        monkeypatch.setattr(mod.SalonSlotService, "set_slot_status", staticmethod(slot))
        monkeypatch.setattr(
            "app.services.salon.appointments.no_show_block_service.increment_no_show_count",
            inc,
        )
        mock_db.tenants.insert_one({"_id": "t1", "revenue": 0.0})
        mock_db.appointments.insert_one(_base_appt())
        AppointmentStatusService.update_status("t1", "a1", APPOINTMENT_STATUS_NO_SHOW, user_id="u1")
        slot.assert_called_once()
        inc.assert_called_once()
        assert mock_db.appointments.find_one({"id": "a1"})["status"] == APPOINTMENT_STATUS_NO_SHOW

    def test_no_show_without_slot_fields_skips_set_slot(self, tenant_ctx, mock_db, monkeypatch):
        slot = MagicMock()
        inc = MagicMock(return_value=1)
        monkeypatch.setattr(mod.SalonSlotService, "set_slot_status", staticmethod(slot))
        monkeypatch.setattr(
            "app.services.salon.appointments.no_show_block_service.increment_no_show_count",
            inc,
        )
        mock_db.tenants.insert_one({"_id": "t1", "revenue": 0.0})
        mock_db.appointments.insert_one(
            _base_appt(start=None, professional_id="", professional="", time="")
        )
        AppointmentStatusService.update_status("t1", "a1", APPOINTMENT_STATUS_NO_SHOW, user_id="u1")
        slot.assert_not_called()
        inc.assert_called_once()

    def test_no_show_without_phone_does_not_call_increment(self, tenant_ctx, mock_db, monkeypatch):
        slot = MagicMock()
        inc = MagicMock()
        monkeypatch.setattr(mod.SalonSlotService, "set_slot_status", staticmethod(slot))
        monkeypatch.setattr(
            "app.services.salon.appointments.no_show_block_service.increment_no_show_count",
            inc,
        )
        mock_db.tenants.insert_one({"_id": "t1", "revenue": 0.0})
        mock_db.appointments.insert_one(
            _base_appt(customer_phone_number=None, customer_phone="")
        )
        AppointmentStatusService.update_status("t1", "a1", APPOINTMENT_STATUS_NO_SHOW, user_id="u1")
        inc.assert_not_called()

    def test_booked_triggers_ensure_customer(self, tenant_ctx, mock_db, monkeypatch):
        ensure = MagicMock()
        monkeypatch.setattr(
            "app.services.core.customer_service.CustomerService.ensure_customer_if_absent",
            staticmethod(ensure),
        )
        mock_db.tenants.insert_one({"_id": "t1", "revenue": 0.0})
        mock_db.appointments.insert_one(_base_appt())
        AppointmentStatusService.update_status("t1", "a1", APPOINTMENT_STATUS_BOOKED, user_id="u1")
        ensure.assert_called_once()
        args, kwargs = ensure.call_args
        assert args[0] == "t1"
        assert args[2] == "+919876543210"

    def test_response_includes_customer_phone_e164(self, tenant_ctx, mock_db):
        mock_db.tenants.insert_one({"_id": "t1", "revenue": 0.0})
        mock_db.appointments.insert_one(_base_appt())
        out = AppointmentStatusService.update_status("t1", "a1", APPOINTMENT_STATUS_BOOKED, user_id="u1")
        assert out["customer_phone"] == "+919876543210"
        assert out["id"] == "a1"
        assert out["tenant"] == "t1"

    def test_no_start_date_label_none(self, tenant_ctx, mock_db):
        mock_db.tenants.insert_one({"_id": "t1", "revenue": 0.0})
        mock_db.appointments.insert_one(_base_appt(start=None))
        out = AppointmentStatusService.update_status("t1", "a1", APPOINTMENT_STATUS_BOOKED, user_id="u1")
        assert out.get("date") is None

    def test_no_show_invalid_tz_falls_back_to_default_timezone(self, tenant_ctx, mock_db, monkeypatch):
        monkeypatch.setattr(
            mod.TenantService,
            "get_tenant_settings",
            staticmethod(
                lambda tenant: {
                    "tz": "Invalid/Timezone",
                    "tenant_country": "IN",
                    "date_format": "%Y-%m-%d",
                }
            ),
        )
        slot = MagicMock()
        monkeypatch.setattr(mod.SalonSlotService, "set_slot_status", staticmethod(slot))
        monkeypatch.setattr(
            "app.services.salon.appointments.no_show_block_service.increment_no_show_count",
            MagicMock(return_value=1),
        )
        mock_db.tenants.insert_one({"_id": "t1", "revenue": 0.0})
        mock_db.appointments.insert_one(_base_appt())
        AppointmentStatusService.update_status("t1", "a1", APPOINTMENT_STATUS_NO_SHOW, user_id="u1")
        slot.assert_called_once()

    def test_no_show_warns_when_phone_normalizes_empty(self, tenant_ctx, mock_db, monkeypatch):
        slot = MagicMock()
        monkeypatch.setattr(mod.SalonSlotService, "set_slot_status", staticmethod(slot))
        inc = MagicMock()
        monkeypatch.setattr(
            "app.services.salon.appointments.no_show_block_service.increment_no_show_count",
            inc,
        )
        real_norm = mod.PhoneUtil.normalize_e164_input

        def norm_stub(phone, country_code_digits=None):
            if str(phone).strip() == "+919876543210":
                return ""
            return real_norm(phone, country_code_digits)

        monkeypatch.setattr(mod.PhoneUtil, "normalize_e164_input", staticmethod(norm_stub))
        mock_db.tenants.insert_one({"_id": "t1", "revenue": 0.0})
        mock_db.appointments.insert_one(_base_appt())
        AppointmentStatusService.update_status("t1", "a1", APPOINTMENT_STATUS_NO_SHOW, user_id="u1")
        inc.assert_not_called()

    def test_ensure_customer_failure_is_swallowed(self, tenant_ctx, mock_db, monkeypatch):
        def boom(*args, **kwargs):
            raise RuntimeError("db down")

        monkeypatch.setattr(
            "app.services.core.customer_service.CustomerService.ensure_customer_if_absent",
            staticmethod(boom),
        )
        mock_db.tenants.insert_one({"_id": "t1", "revenue": 0.0})
        mock_db.appointments.insert_one(_base_appt())
        out = AppointmentStatusService.update_status("t1", "a1", APPOINTMENT_STATUS_BOOKED, user_id="u1")
        assert out["status"] == APPOINTMENT_STATUS_BOOKED

    def test_no_show_increment_exception_is_logged_and_swallowed(
        self, tenant_ctx, mock_db, monkeypatch
    ):
        slot = MagicMock()
        monkeypatch.setattr(mod.SalonSlotService, "set_slot_status", staticmethod(slot))
        monkeypatch.setattr(
            "app.services.salon.appointments.no_show_block_service.increment_no_show_count",
            MagicMock(side_effect=RuntimeError("increment failed")),
        )
        mock_db.tenants.insert_one({"_id": "t1", "revenue": 0.0})
        mock_db.appointments.insert_one(_base_appt())
        out = AppointmentStatusService.update_status("t1", "a1", APPOINTMENT_STATUS_NO_SHOW, user_id="u1")
        assert out["status"] == APPOINTMENT_STATUS_NO_SHOW
