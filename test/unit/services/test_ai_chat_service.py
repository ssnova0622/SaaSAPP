# test/unit/services/test_ai_chat_service.py
import pytest
from app_ref.services.ai.ai_chat_service import AIChatService
from app_ref.models.ai_chat import AIChatSessionCreate
from app_ref.repositories.ai_chat_repository import AIChatSessionRepository, AIChatMessageRepository

def test_create_session(mock_db):
    data = AIChatSessionCreate(tenant="t1", title="Help me", model_config_id="m1")
    res = AIChatService.create_session(data)
    assert res["title"] == "Help me"
    assert res["tenant"] == "t1"
    assert res["model_config_id"] == "m1"

def test_list_messages(mock_db):
    tenant = "t1"
    session_id = "s1"
    AIChatMessageRepository.create({
        "id": "m1", "tenant": tenant, "session_id": session_id,
        "role": "user", "content": "hello"
    })
    
    msgs = AIChatService.list_messages(tenant, session_id)
    assert len(msgs) == 1
    assert msgs[0]["content"] == "hello"
