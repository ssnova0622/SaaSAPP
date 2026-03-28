"""Workflow catalog + dispatcher meta (single source: _DISPATCHER_ACTIONS)."""
from unittest.mock import patch

from app.helpers.constants_action import BOOK_APPOINTMENT
from app.services.whatsapp.usecases.action_registry import (
    get_action_meta,
    get_all_workflow_actions,
    get_available_actions_for_tenant,
    list_dispatcher_actions_for_tenant,
)
from app.services.whatsapp.workflow.workflow_engine import WorkflowEngine


def test_get_action_meta_select_timeslot_maps_to_book_appointment():
    meta = get_action_meta("salon.select_timeslot")
    assert meta is not None
    assert meta["id"] == BOOK_APPOINTMENT


def test_get_action_meta_legacy_alias():
    m = get_action_meta("select_timeslot")
    assert m is not None
    assert m["id"] == BOOK_APPOINTMENT


def test_get_action_meta_unknown():
    assert get_action_meta("unknown.action") is None
    assert get_action_meta("") is None


def test_get_all_workflow_actions_dedupes_book_appointment():
    codes = [a.action_code for a in get_all_workflow_actions()]
    assert codes.count("book_appointment") == 1


def test_get_available_actions_salon_not_clinic_doctors():
    mock_settings = {"modules": ["salon"], "capabilities": ["salon.appointments"]}
    with patch("app.services.whatsapp.usecases.action_registry.get_tenant_service") as m:
        m.return_value.get_tenant_settings.return_value = mock_settings
        codes = {a.action_code for a in get_available_actions_for_tenant("t1")}
    assert "show_services" in codes
    assert "clinic.list_doctors" not in codes


def test_list_dispatcher_actions_for_tenant():
    mock_settings = {"modules": ["salon"], "capabilities": ["salon.appointments"]}
    with patch("app.services.whatsapp.usecases.action_registry.get_tenant_service") as m:
        m.return_value.get_tenant_settings.return_value = mock_settings
        ids = {x["id"] for x in list_dispatcher_actions_for_tenant("t1")}
    assert "show_services" in ids
    assert "store.track_order" not in ids


def test_list_whatsapp_menu_items_includes_workflow():
    from app.models.workflows import WorkflowDefinition

    mock_settings = {"modules": ["salon"], "capabilities": ["salon.appointments"]}
    mock_wf = [WorkflowDefinition(tenant="t1", workflow_id="wf1", name="Booking", steps=[])]
    with patch("app.services.whatsapp.workflow.workflow_engine.WorkflowEngine.list_workflows", return_value=mock_wf):
        with patch("app.services.whatsapp.usecases.action_registry.get_tenant_service") as m:
            m.return_value.get_tenant_settings.return_value = mock_settings
            items = WorkflowEngine.list_whatsapp_menu_items("t1")
    ids = [i["id"] for i in items]
    assert "workflow.wf1" in ids
    assert "show_services" in ids
