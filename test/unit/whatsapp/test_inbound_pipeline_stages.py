"""Guardrail: inbound pipeline stage order matches ``ARCHITECTURE.md`` (do not reorder lightly)."""
from __future__ import annotations

from app.services.whatsapp.pipeline.inbound_pipeline import INBOUND_PIPELINE_STAGES


def test_inbound_pipeline_stage_order() -> None:
    names = tuple(f.__name__ for f in INBOUND_PIPELINE_STAGES)
    assert names == (
        "_stage_flow_ended_menu",
        "_stage_triggers",
        "_stage_store_waiting_input",
        "_stage_rebook_feedback",
        "_stage_exact_action_id",
        "_stage_run_fsm",
        "_stage_active_workflow",
        "_stage_return_fsm",
        "_stage_menu_inactive_goodbye",
        "_stage_nl_intent_high_confidence",
        "_stage_no_menu_error",
        "_stage_menu_navigation",
    )
