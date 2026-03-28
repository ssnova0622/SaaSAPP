# app/services/core/user_service.py
from __future__ import annotations

# ============================================================
# Imports
# ============================================================

from typing import Any, Dict, List, Optional
from pymongo import ReturnDocument

from app.helpers.date_utils import utcnow
from app.services.core.tenant_service import TenantService
from app.repositories.user_repository import UserRepository
from app.modules.registry import ids_map, is_capability
from app.helpers.constants import USER_STATUS_ACTIVE

import hashlib
import os
import re

user_repo = UserRepository()


# ============================================================
# DB Helpers
# ============================================================

def _users_col():
    from app.services.db import users_collection
    return users_collection()


# ============================================================
# Password Helpers
# ============================================================

def _hash_password(password: str) -> str:
    """
    PBKDF2-HMAC-SHA256 with random salt.
    Returns: hex_digest:salt_hex
    """
    salt = os.urandom(16)
    digest = hashlib.pbkdf2_hmac(
        "sha256",
        password.encode("utf-8"),
        salt,
        100000
    ).hex()
    return f"{digest}:{salt.hex()}"


def _verify_password(password: str, password_hash: str) -> bool:
    """
    Supports:
    - New format: digest:salt
    - Old format: sha256$salt$digest
    """
    if ":" in password_hash:
        # New format
        digest, salt_hex = password_hash.split(":")
        salt = bytes.fromhex(salt_hex)
        check = hashlib.pbkdf2_hmac(
            "sha256",
            password.encode("utf-8"),
            salt,
            100000
        ).hex()
        return digest == check

    # Old format: sha256$salt$digest
    if password_hash.startswith("sha256$"):
        parts = password_hash.split("$")
        if len(parts) != 3:
            return False
        _, salt_hex, digest = parts
        salt = bytes.fromhex(salt_hex)
        check = hashlib.sha256(salt + password.encode("utf-8")).hexdigest()
        return digest == check

    return False


# ============================================================
# UserService
# ============================================================

class UserService:

    # --------------------------------------------------------
    # Listing
    # --------------------------------------------------------

    @staticmethod
    def list_users(
            tenant: Optional[str] = None,
            role: Optional[str] = None,
            search: Optional[str] = None,
            page: int = 1,
            size: int = 50
    ) -> Dict[str, Any]:

        users = user_repo.list_by_tenant(tenant, role)

        # In-memory search filter
        if search:
            pattern = re.compile(re.escape(search), re.IGNORECASE)
            users = [
                u for u in users
                if pattern.search(u.email) or pattern.search(u.display_name)
            ]

        total = len(users)
        start = (page - 1) * size
        end = start + size

        items = [
            u.dict(exclude={"password_hash"})
            for u in users[start:end]
        ]

        return {
            "items": items,
            "total": total,
            "page": page,
            "size": size,
            "pages": (total + size - 1) // size,
        }

    # --------------------------------------------------------
    # Creation
    # --------------------------------------------------------

    @staticmethod
    def create_user(
            email: str,
            password: str,
            role: str,
            tenant: Optional[str] = None,
            display_name: str = "",
            phone: Optional[str] = None,
            caps: List[str] = None
    ) -> Dict[str, Any]:

        if user_repo.find_by_email(email):
            raise ValueError("User already exists")

        from app.models.users import User

        now = utcnow()
        caps = caps or []

        user = User(
            id=str(now.timestamp()),
            email=email.lower().strip(),
            password_hash=_hash_password(password),
            role=role,
            tenant=tenant,
            display_name=display_name,
            phone=(phone or "").strip() or None,
            caps=caps,
            status=USER_STATUS_ACTIVE,
            created_at=now,
            updated_at=now,
        )

        try:
            user_repo.insert_one(user)
        except Exception as e:
            from pymongo.errors import DuplicateKeyError
            if isinstance(e, DuplicateKeyError):
                raise ValueError("A user with this email already exists. Email must be unique across the application.")
            raise
        return user.dict(exclude={"password_hash"})

    # --------------------------------------------------------
    # Retrieval
    # --------------------------------------------------------

    @staticmethod
    def get_user_by_email(email: str) -> Optional[Dict[str, Any]]:
        user = user_repo.find_by_email(email)
        return user.dict() if user else None

    @staticmethod
    def get_user_by_id(user_id: str) -> Optional[Dict[str, Any]]:
        user = user_repo.find_by_id(user_id)
        return user.dict(exclude={"password_hash"}) if user else None

    # --------------------------------------------------------
    # Update
    # --------------------------------------------------------

    @staticmethod
    def update_user(user_id: str, patch: Dict[str, Any]) -> Dict[str, Any]:
        col = _users_col()

        allowed = {"display_name", "role", "caps", "status", "tenant"}
        payload = {k: v for k, v in patch.items() if k in allowed}

        if "password" in patch:
            payload["password_hash"] = _hash_password(patch["password"])

        payload["updated_at"] = utcnow()

        doc = col.find_one_and_update(
            {"id": user_id},
            {"$set": payload},
            return_document=ReturnDocument.AFTER
        )

        if not doc:
            raise ValueError("User not found")

        out = dict(doc)
        out.pop("_id", None)
        out.pop("password_hash", None)
        return out

    # --------------------------------------------------------
    # Authentication
    # --------------------------------------------------------

    @staticmethod
    def verify_user_password(email: str, password: str) -> Optional[Dict[str, Any]]:
        user = user_repo.find_by_email(email)
        if not user:
            return None
        if _verify_password(password, user.password_hash):
            return user.dict(exclude={"password_hash"})
        return None

    # --------------------------------------------------------
    # Utilities
    # --------------------------------------------------------

    @staticmethod
    def resolve_user_names(user_ids: List[str]) -> Dict[str, str]:
        """Resolve user IDs (email or MongoDB _id string) to display names."""
        if not user_ids:
            return {}

        from bson import ObjectId
        col = _users_col()
        emails = []
        object_ids = []
        for uid in set(user_ids):
            if not uid:
                continue
            uid_str = str(uid).strip()
            if "@" in uid_str:
                emails.append(uid_str.lower())
            else:
                try:
                    object_ids.append(ObjectId(uid_str))
                except Exception:
                    emails.append(uid_str)

        query = {"$or": []}
        if emails:
            query["$or"].append({"email": {"$in": emails}})
        if object_ids:
            query["$or"].append({"_id": {"$in": object_ids}})
        if not query["$or"]:
            return {}

        mapping = {}
        for doc in col.find(query, {"_id": 1, "email": 1, "display_name": 1}):
            name = doc.get("display_name") or doc.get("email")
            if doc.get("email"):
                mapping[doc["email"]] = name
            mapping[str(doc["_id"])] = name
        return mapping

    @staticmethod
    def sanitize_caps_for_tenant(tenant: str, caps: Optional[List[str]]) -> List[str]:
        """
        Ensures user capabilities are valid AND allowed for the tenant.
        """
        if not caps:
            return []

        capability_ids = ids_map()
        tenant_cfg = TenantService.get_tenant_settings(tenant) or {}
        tenant_caps = {str(c).lower() for c in (tenant_cfg.get("capabilities") or [])}

        out = []
        for c in caps:
            cid = str(c).lower().strip()
            if cid in capability_ids and is_capability(cid) and cid in tenant_caps:
                out.append(cid)

        return sorted(set(out))
