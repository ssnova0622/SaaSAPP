"""Menu escape from active workflow/FSM (simulator *Menu* chip must not hit SELECT_TIME)."""
from __future__ import annotations

import asyncio
from unittest.mock import patch

from app.services.whatsapp.pipeline.inbound_pipeline import _stage_escape_to_main_menu


def _run(coro):
    return asyncio.run(coro)


def test_menu_keyword_resets_active_workflow() -> None:
    ctx = {
        "tenant": "acme",
        "phone": "+100",
        "user_input": "menu",
        "tree": {"root": "root", "nodes": [{"id": "root", "type": "submenu", "title": "Hi", "options": []}]},
        "root_id": "root",
        "locale": "en",
    }
    session = {
        "ctx": {
            "workflow_id": "book",
            "step_idx": 1,
            "waiting_for_input": True,
            "flow_data": {},
        }
    }

    with patch(
        "app.services.whatsapp.pipeline.inbound_pipeline.get_session",
        return_value=session,
    ), patch(
        "app.services.whatsapp.pipeline.inbound_pipeline.reset_session_to_root",
    ) as mock_reset, patch(
        "app.services.whatsapp.pipeline.inbound_pipeline.find_node",
        return_value=ctx["tree"]["nodes"][0],
    ), patch(
        "app.services.whatsapp.pipeline.inbound_pipeline._menu_reply",
        return_value="Welcome\n1) Book",
    ):
        out = _run(_stage_escape_to_main_menu(ctx))

    assert out is not None
    assert "Welcome" in out["reply"]
    mock_reset.assert_called_once()
