"""Booking/reschedule session ctx vs flow_data alignment (regression for workflow + FSM handoff)."""
import unittest

from app.services.whatsapp.usecases.salon.booking_ctx_utils import (
    clear_stale_booking_calendar_keys,
    sync_booking_ctx_from_flow_data,
)


class TestSalonBookingCtxSync(unittest.TestCase):
    def test_sync_fills_missing_top_level(self):
        ctx = {
            "mode": "select_date",
            "workflow_id": "wf1",
            "flow_data": {
                "date": "2025-03-26",
                "professional": "Dr. A",
                "service": "Cut",
                "selected_slot": "10:00",
                "available_slots": ["09:00", "10:00"],
                "professionals": ["Dr. A", "Dr. B"],
            },
        }
        sync_booking_ctx_from_flow_data(ctx)
        self.assertEqual(ctx["date"], "2025-03-26")
        self.assertEqual(ctx["professional"], "Dr. A")
        self.assertEqual(ctx["service"], "Cut")
        self.assertEqual(ctx["selected_slot"], "10:00")
        self.assertEqual(ctx["available_slots"], ["09:00", "10:00"])
        self.assertEqual(ctx["professionals"], ["Dr. A", "Dr. B"])

    def test_sync_respects_existing_top_level(self):
        ctx = {
            "date": "2025-03-20",
            "professional": "Keep me",
            "flow_data": {"date": "2025-03-26", "professional": "Dr. Other"},
        }
        sync_booking_ctx_from_flow_data(ctx)
        self.assertEqual(ctx["date"], "2025-03-20")
        self.assertEqual(ctx["professional"], "Keep me")

    def test_sync_no_flow_data(self):
        ctx = {"mode": "select_service", "date": "2025-01-01"}
        sync_booking_ctx_from_flow_data(ctx)
        self.assertEqual(ctx, {"mode": "select_service", "date": "2025-01-01"})

    def test_clear_stale_booking_calendar_keys_ctx_and_flow_data(self):
        ctx = {
            "mode": "select_date",
            "reschedule_id": "appt-1",
            "date": "2025-01-01",
            "time": "11:00",
            "selected_slot": "11:00",
            "available_slots": ["10:00"],
            "flow_data": {
                "date": "2025-01-02",
                "appointment_time": "14:00",
                "appointment_date": "2025-01-02",
            },
        }
        clear_stale_booking_calendar_keys(ctx)
        self.assertEqual(ctx["reschedule_id"], "appt-1")
        self.assertEqual(ctx["mode"], "select_date")
        self.assertNotIn("date", ctx)
        self.assertNotIn("time", ctx)
        fd = ctx["flow_data"]
        self.assertNotIn("date", fd)
        self.assertNotIn("appointment_time", fd)
        self.assertNotIn("appointment_date", fd)


if __name__ == "__main__":
    unittest.main()
