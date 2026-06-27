"""Slot resolver: dynamic duration options and booking window logic."""
from __future__ import annotations

from unittest.mock import patch

import pytest

from app.models.workflow import WorkflowStep
from app.services.whatsapp.workflow.slot_resolver import (
    filter_slots_fitting_duration,
    format_duration_label,
    generate_duration_options,
    resolve_booking_duration,
    resolve_service_window,
)


def _step(**params):
    return WorkflowStep(
        action_code="ASK_NUM_SLOTS",
        label="How long?",
        input_required=True,
        ui_type="list",
        params=params,
    )


def test_format_duration_label():
    assert format_duration_label(30) == "30 mins"
    assert format_duration_label(60) == "1 hour"
    assert format_duration_label(120) == "2 hours"
    assert format_duration_label(90) == "1 hour 30 mins"


@patch("app.services.whatsapp.workflow.slot_resolver._load_tenant_settings")
def test_generate_duration_options_cricket_window(mock_settings):
    mock_settings.return_value = {}
    step = _step(start_hour=10, end_hour=14, slot_duration_minutes=60)
    options, default = generate_duration_options("t", step)
    assert default == 60
    assert [o.duration_minutes for o in options] == [60, 120, 180, 240]
    assert options[0].label == "1 hour"
    assert options[-1].num_slots == 4


@patch("app.services.whatsapp.workflow.slot_resolver._load_tenant_settings")
def test_generate_duration_options_football_window(mock_settings):
    mock_settings.return_value = {}
    step = _step(start_hour=16, end_hour=18, slot_duration_minutes=30)
    options, _ = generate_duration_options("t", step)
    assert [o.duration_minutes for o in options] == [30, 60, 90, 120]


@patch("app.services.whatsapp.workflow.slot_resolver._load_tenant_settings")
def test_generate_duration_options_max_booking_window(mock_settings):
    mock_settings.return_value = {}
    step = _step(
        start_hour=6, end_hour=20, slot_duration_minutes=60,
        max_booking_window_minutes=120, max_options=2,
    )
    options, _ = generate_duration_options("t", step)
    assert [o.duration_minutes for o in options] == [60, 120]


@patch("app.services.whatsapp.workflow.slot_resolver._load_tenant_settings")
def test_generate_duration_options_customer_request_invalid(mock_settings):
    mock_settings.return_value = {}
    step = _step(start_hour=16, end_hour=18, slot_duration_minutes=30, customer_requested_duration=150)
    options, _ = generate_duration_options("t", step)
    assert 150 not in [o.duration_minutes for o in options]


@patch("app.services.whatsapp.workflow.slot_resolver._load_tenant_settings")
def test_generate_duration_options_customer_request_valid_non_multiple(mock_settings):
    mock_settings.return_value = {}
    step = _step(start_hour=16, end_hour=18, slot_duration_minutes=30, customer_requested_duration=75)
    options, _ = generate_duration_options("t", step)
    labels = {o.duration_minutes: o for o in options}
    assert 75 in labels
    assert labels[75].num_slots == 1
    assert labels[75].is_default_multiple is False


@patch("app.services.whatsapp.workflow.slot_resolver._load_service")
@patch("app.services.whatsapp.workflow.slot_resolver._load_tenant_settings")
def test_resolve_service_window_from_service(mock_settings, mock_service):
    mock_settings.return_value = {"business_start_hour": 9, "business_end_hour": 17}
    mock_service.return_value = {"start_time": "06:00", "end_time": "20:00", "duration": 60}
    start, end = resolve_service_window("t", _step(), "Badminton Court")
    assert start == 6 * 60
    assert end == 20 * 60


def test_filter_slots_fitting_duration():
    slots = ["09:00", "10:00", "11:00", "18:00", "19:00"]
    out = filter_slots_fitting_duration(slots, 120, "20:00")
    assert out == ["09:00", "10:00", "11:00", "18:00"]
    assert "19:00" not in out


@patch("app.services.whatsapp.workflow.slot_resolver.resolve_slot_duration")
def test_resolve_booking_duration_from_flow(mock_resolve):
    mock_resolve.return_value = 60
    session = {
        "ctx": {
            "flow_data": {
                "num_slots": 2,
                "slot_duration_minutes": 60,
                "total_duration_minutes": 120,
            }
        }
    }
    slot_dur, num_slots, total = resolve_booking_duration("t", _step(), session)
    assert slot_dur == 60
    assert num_slots == 2
    assert total == 120
