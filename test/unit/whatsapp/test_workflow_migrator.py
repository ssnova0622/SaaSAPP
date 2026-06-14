"""Workflow migrator: legacy step repair and audit."""
from app.helpers.constants_action import END, SHOW_SERVICES
from app.models.workflows import WorkflowDefinition, WorkflowStep
from app.services.whatsapp.workflow.workflow_migrator import repair_workflow_steps


def test_repair_legacy_store_steps():
    steps = [
        {"action_code": "SHOW_CATEGORIES", "label": "Categories"},
        {"action_code": "SHOW_PRODUCTS", "label": "Products"},
        {"action_code": "VIEW_CART", "label": "Cart"},
        {"action_code": "CHECKOUT", "label": "Checkout"},
    ]
    repaired, notes = repair_workflow_steps(steps)
    codes = [s["action_code"] for s in repaired]
    assert "BROWSE_CATALOG" in codes
    assert "SHOW_CATEGORIES" not in codes
    assert codes[-1] == "END"
    assert any("Replaced" in n for n in notes)
    assert any("Appended missing END" in n for n in notes)


def test_repair_support_flow_collect_order_id():
    steps = [
        {"action_code": "COLLECT_ORDER_ID", "label": "Order id"},
        {"action_code": "SHOW_ORDER_DETAIL", "label": "Details"},
    ]
    repaired, notes = repair_workflow_steps(steps)
    codes = [s["action_code"] for s in repaired]
    assert codes == ["TRACK_ORDER", "END"]
    assert len(notes) >= 2


def test_repair_keeps_valid_salon_flow():
    steps = [
        WorkflowStep(action_code=SHOW_SERVICES, label="Pick"),
        WorkflowStep(action_code=END, label="Done"),
    ]
    repaired, notes = repair_workflow_steps(steps)
    assert len(repaired) == 2
    assert notes == []


def test_repair_appends_end_when_missing():
    steps = [{"action_code": SHOW_SERVICES, "label": "Pick"}]
    repaired, notes = repair_workflow_steps(steps)
    assert repaired[-1]["action_code"] == "END"
    assert any("Appended" in n for n in notes)
