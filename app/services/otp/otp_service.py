# app/services/otp_service.py
"""Login OTP: generate, store session, send via SMS, verify."""
from __future__ import annotations
import secrets
import logging
from datetime import datetime, timezone, timedelta
from typing import Any, Dict, Optional

from app.services.db import get_db

logger = logging.getLogger(__name__)

OTP_EXPIRY_MINUTES = 5
OTP_LENGTH = 6


def _otp_sessions_col():
    col = get_db().get_collection("otp_sessions")
    # TTL index: expire documents after expires_at (MongoDB will delete them)
    try:
        col.create_index([("expires_at", 1)], expireAfterSeconds=0)
    except Exception:
        pass
    return col


def _generate_otp() -> str:
    return "".join(secrets.choice("0123456789") for _ in range(OTP_LENGTH))


def create_otp_session(user: Dict[str, Any]) -> tuple[str, str]:
    """Create OTP session for user. Returns (session_id, otp). Sender should send OTP via SMS."""
    session_id = secrets.token_urlsafe(32)
    otp = _generate_otp()
    expires_at = datetime.now(timezone.utc) + timedelta(minutes=OTP_EXPIRY_MINUTES)
    doc = {
        "_id": session_id,
        "user_id": user.get("id"),
        "email": user.get("email"),
        "tenant": user.get("tenant"),
        "role": user.get("role"),
        "display_name": user.get("display_name"),
        "caps": user.get("caps") or [],
        "otp": otp,
        "expires_at": expires_at,
    }
    _otp_sessions_col().insert_one(doc)
    return session_id, otp


def verify_otp_and_consume(session_id: str, otp: str) -> Optional[Dict[str, Any]]:
    """Verify OTP and return user snapshot for JWT issuance; delete session on success."""
    col = _otp_sessions_col()
    doc = col.find_one({"_id": session_id})
    if not doc:
        return None
    if doc.get("otp") != otp.strip():
        return None
    expires_at = doc.get("expires_at")
    if expires_at and datetime.now(timezone.utc) > expires_at:
        col.delete_one({"_id": session_id})
        return None
    user = {
        "id": doc.get("user_id"),
        "email": doc.get("email"),
        "role": doc.get("role"),
        "tenant": doc.get("tenant"),
        "display_name": doc.get("display_name"),
        "caps": doc.get("caps") or [],
    }
    col.delete_one({"_id": session_id})
    return user
