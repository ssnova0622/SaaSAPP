# test/integration/test_whatsapp_api.py
import pytest
from fastapi.testclient import TestClient
from app_ref.main import app
from app_ref.services.auth.user_service import UserService
from app_ref.services.tenant.tenant_service import TenantService
from app_ref.models.auth import UserCreate
from app_ref.models.tenant import TenantCreate

client = TestClient(app)

@pytest.fixture
def auth_header(mock_db):
    TenantService.create_tenant(TenantCreate(name="T1", code="t1"))
    from app_ref.repositories.tenant_repository import TenantRepository
    TenantRepository.update_by_code("t1", {"status": "active"})
    
    UserService.create_user(UserCreate(
        email="admin@t1.com", password="pwd", full_name="Admin", tenant="t1"
    ))
    token, _ = UserService.login("admin@t1.com", "pwd")
    return {"Authorization": f"Bearer {token}", "X-Tenant": "t1"}

def test_list_templates_api(auth_header, mock_db):
    response = client.get("/tenants/t1/whatsapp/templates", headers=auth_header)
    assert response.status_code == 200
    assert isinstance(response.json(), list)

def test_whatsapp_dashboard_api(auth_header, mock_db):
    response = client.get("/tenants/t1/whatsapp/dashboard", headers=auth_header)
    assert response.status_code == 200


def test_create_menu_full(auth_header, mock_db):
    """Create one menu with steps in one request; only one top-level entry should exist."""
    response = client.post(
        "/tenants/t1/whatsapp/menus/full",
        headers=auth_header,
        json={
            "trigger_keyword": "book",
            "options": [
                {"key": "1", "label": "Book appointment", "reply_type": "dynamic", "action_type": "book_appointment"},
                {"key": "2", "label": "Cancel", "reply_type": "text", "text_body": "Reply with your booking ID to cancel."},
            ],
        },
    )
    assert response.status_code == 200
    data = response.json()
    assert "menu" in data
    assert data["menu"]["trigger_keyword"] == "book"
    assert data["menu"]["reply_type"] == "menu"
    assert data["menu"].get("parent_menu_id") is None
    assert len(data["menu"]["menu_options"]) == 2
    assert "steps" in data
    assert len(data["steps"]) == 2
    menu_id = data["menu"]["id"]

    list_resp = client.get("/tenants/t1/whatsapp/menus", headers=auth_header)
    assert list_resp.status_code == 200
    all_menus = list_resp.json()
    top_level = [m for m in all_menus if m.get("parent_menu_id") is None and m.get("reply_type") == "menu"]
    assert len(top_level) >= 1
    triggers = [m["trigger_keyword"] for m in top_level]
    assert "book" in triggers

    update_resp = client.put(
        f"/tenants/t1/whatsapp/menus/{menu_id}/full",
        headers=auth_header,
        json={
            "trigger_keyword": "book",
            "options": [
                {"key": "1", "label": "Book appointment", "reply_type": "dynamic", "action_type": "book_appointment"},
                {"key": "2", "label": "Cancel", "reply_type": "text", "text_body": "Updated cancel message."},
                {"key": "3", "label": "Help", "reply_type": "text", "text_body": "Contact support."},
            ],
        },
    )
    assert update_resp.status_code == 200
    upd = update_resp.json()
    assert upd["menu"]["trigger_keyword"] == "book"
    assert len(upd["steps"]) == 3

    del_resp = client.delete(f"/tenants/t1/whatsapp/menus/{menu_id}", headers=auth_header)
    assert del_resp.status_code == 200
    list_after = client.get("/tenants/t1/whatsapp/menus", headers=auth_header)
    all_after = list_after.json()
    top_after = [m for m in all_after if m.get("parent_menu_id") is None and m.get("reply_type") == "menu"]
    assert "book" not in [m["trigger_keyword"] for m in top_after]


def test_create_menu_full_idempotent(auth_header, mock_db):
    """Creating the same trigger twice must not create two top-level menus."""
    payload = {
        "trigger_keyword": "hi",
        "options": [{"key": "1", "label": "Option 1", "reply_type": "text", "text_body": "Hello"}],
    }
    r1 = client.post("/tenants/t1/whatsapp/menus/full", headers=auth_header, json=payload)
    assert r1.status_code == 200
    r2 = client.post("/tenants/t1/whatsapp/menus/full", headers=auth_header, json=payload)
    assert r2.status_code == 200
    list_resp = client.get("/tenants/t1/whatsapp/menus", headers=auth_header)
    all_menus = list_resp.json()
    top_level = [m for m in all_menus if m.get("parent_menu_id") is None and m.get("reply_type") == "menu"]
    hi_menus = [m for m in top_level if (m.get("trigger_keyword") or "").strip().lower() == "hi"]
    assert len(hi_menus) == 1, "expected exactly one top-level menu for trigger 'hi', got %s" % len(hi_menus)


def test_simulate_menu_option_with_current_menu_id(auth_header, mock_db):
    """When current_menu_id is set, simulate '1' should return the step reply, not fallback."""
    create = client.post(
        "/tenants/t1/whatsapp/menus/full",
        headers=auth_header,
        json={
            "trigger_keyword": "hi",
            "options": [
                {"key": "1", "label": "Book", "reply_type": "text", "text_body": "You chose Book."},
                {"key": "2", "label": "Cancel", "reply_type": "text", "text_body": "You chose Cancel."},
            ],
        },
    )
    assert create.status_code == 200
    menu_id = create.json()["menu"]["id"]
    sim_hi = client.post("/tenants/t1/whatsapp/simulate", headers=auth_header, json={"message": "hi"})
    assert sim_hi.status_code == 200
    assert "Please choose an option" in (sim_hi.json().get("reply") or "")
    sim_1 = client.post(
        "/tenants/t1/whatsapp/simulate",
        headers=auth_header,
        json={"message": "1", "current_menu_id": menu_id},
    )
    assert sim_1.status_code == 200
    data = sim_1.json()
    assert data.get("matched") is True
    assert "You chose Book" in (data.get("reply") or ""), "expected step reply, got %s" % data.get("reply")


def test_conversation_flow_hi_then_1_persisted_session(auth_header, mock_db):
    """Full flow: conversation/process with 'hi' then '1' – session must persist so second call gets option reply."""
    create = client.post(
        "/tenants/t1/whatsapp/menus/full",
        headers=auth_header,
        json={
            "trigger_keyword": "hi",
            "options": [
                {"key": "1", "label": "Book", "reply_type": "text", "text_body": "You chose Book."},
                {"key": "2", "label": "Cancel", "reply_type": "text", "text_body": "You chose Cancel."},
            ],
        },
    )
    assert create.status_code == 200
    phone = "9876543210"
    r1 = client.post(
        "/tenants/t1/whatsapp/conversation/process",
        headers=auth_header,
        json={"from_phone": phone, "message": "hi"},
    )
    assert r1.status_code == 200
    data1 = r1.json()
    assert "Please choose an option" in (data1.get("reply") or "")
    assert data1.get("session_updated") is True
    r2 = client.post(
        "/tenants/t1/whatsapp/conversation/process",
        headers=auth_header,
        json={"from_phone": phone, "message": "1"},
    )
    assert r2.status_code == 200
    data2 = r2.json()
    assert "You chose Book" in (data2.get("reply") or ""), "expected option 1 reply, got %s" % data2.get("reply")
