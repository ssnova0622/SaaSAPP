# app/services/system_config_service.py
"""System-wide config (e.g. login OTP enabled). Persisted in MongoDB; only super_admin may write."""
from __future__ import annotations
from typing import Any, Optional

from app.services.db import get_db


def _col():
    return get_db().get_collection("system_config")


def get_system_config(key: str) -> Optional[Any]:
    doc = _col().find_one({"_id": key})
    if doc is None:
        return None
    return doc.get("value")


def set_system_config(key: str, value: Any) -> None:
    _col().update_one({"_id": key}, {"$set": {"value": value}}, upsert=True)


def is_login_otp_enabled() -> bool:
    return bool(get_system_config("login_otp_enabled"))
