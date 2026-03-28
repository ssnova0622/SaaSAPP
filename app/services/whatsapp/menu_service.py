# app/services/whatsapp/menu_service.py
from __future__ import annotations

import re
from typing import Optional, List


class WhatsAppMenuService:
    """
    Clean, predictable menu utilities for WhatsApp flows.

    Responsibilities:
    - Convert user input into numeric menu choices
    - Render numbered menus consistently
    """

    # ---------------------------------------------------------
    # HMAC Validation
    # ---------------------------------------------------------

    @staticmethod
    def hmac_valid(secret: str, body: bytes, signature: Optional[str]) -> bool:
        """
        Validate incoming webhook signature using HMAC-SHA256.
        """
        if not signature:
            return False

        import hmac
        import hashlib

        expected = hmac.new(
            secret.encode("utf-8"),
            body,
            hashlib.sha256
        ).hexdigest()

        return hmac.compare_digest(expected, signature)

    # ---------------------------------------------------------
    # Choice parsing
    # ---------------------------------------------------------

    @staticmethod
    def choice_to_index(text: str) -> Optional[int]:
        """Parse leading digit from user reply (delegates to usecases.utils)."""
        from app.services.whatsapp.usecases.utils import choice_to_index as _choice_to_index

        return _choice_to_index(text)

    # ---------------------------------------------------------
    # Menu rendering
    # ---------------------------------------------------------

    @staticmethod
    def render_menu(
        title: str,
        items: List[str],
        include_numbers: bool = True,
        footer: Optional[str] = None,
    ) -> str:
        """
        Render a clean WhatsApp menu:
            Title
            1) Item A
            2) Item B
            ...
            Footer (optional)
        """
        lines = [title]

        if include_numbers:
            for i, item in enumerate(items, start=1):
                lines.append(f"{i}) {item}")
        else:
            lines.extend(items)

        if footer:
            lines.append(footer)

        return "\n".join(lines)
