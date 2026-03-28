"""
Authentication service: credential verification, tenant checks, and JWT issuance.
Keeps auth router thin and centralizes login policy. Supports optional login OTP (pluggable).
"""
from __future__ import annotations
from datetime import datetime, timedelta, timezone
from typing import Any, Dict

import jwt

from settings import env
from app.services.storage_mongo import Storage


class AuthService:
    """Handles login verification and token issuance."""

    @staticmethod
    def verify_and_issue_token(email: str, password: str) -> Dict[str, Any]:
        """
        Verify credentials, enforce tenant-active policy. If login OTP is enabled (and user
        is not super_admin), return requires_otp + session_id instead of token; otherwise
        return JWT and user.
        """
        from fastapi import HTTPException
        from app.services.system_config_service import is_login_otp_enabled
        from app.services.otp.otp_service import create_otp_session
        from app.services.core.messaging_service import Messaging

        user = Storage.verify_user_password(email=email, password=password)
        if not user:
            raise HTTPException(status_code=401, detail="Invalid credentials")

        role = str((user or {}).get("role") or "admin").lower()
        tenant = (user or {}).get("tenant")
        if role in ("tenant_admin", "staff") and tenant:
            tdoc = Storage.get_tenant(tenant)
            if not tdoc:
                raise HTTPException(status_code=404, detail="Tenant not found")
            if not bool(tdoc.get("active", True)):
                raise HTTPException(status_code=403, detail="Tenant is inactive")

        # Super admin never requires OTP
        if role == "super_admin":
            return AuthService.issue_jwt(user)

        # When login OTP is enabled, require OTP for tenant_admin and staff
        if is_login_otp_enabled():
            phone = (user or {}).get("phone") or ""
            if not phone and tenant:
                tdoc_otp = Storage.get_tenant(tenant)
                if tdoc_otp:
                    phone = (tdoc_otp.get("owner_phone") or "").strip()
            if not phone:
                raise HTTPException(
                    status_code=403,
                    detail="Login OTP is required but no mobile number is on file. Contact your administrator.",
                )
            session_id, otp = create_otp_session(user)
            try:
                Messaging.send_sms(phone, f"Your login verification code is: {otp}. Valid for 5 minutes.", tenant=tenant)
            except Exception as e:
                from app.services.otp.otp_service import _otp_sessions_col
                _otp_sessions_col().delete_one({"_id": session_id})
                raise HTTPException(status_code=503, detail="Failed to send OTP. Please try again or contact support.") from e
            return {
                "requires_otp": True,
                "session_id": session_id,
                "message": "OTP sent to your registered mobile number.",
            }

        return AuthService.issue_jwt(user)

    @staticmethod
    def issue_jwt(user: Dict[str, Any]) -> Dict[str, Any]:
        """Build JWT and public user payload. Returns dict with access_token, expires_in, user."""
        secret = env.str("JWT_SECRET", "dev-secret-change-me")
        exp_minutes = env.int("JWT_EXP_MINUTES", 120)
        exp_dt = datetime.now(timezone.utc) + timedelta(minutes=exp_minutes)
        payload: Dict[str, Any] = {
            "sub": user.get("id") or user.get("email"),
            "email": user.get("email"),
            "role": user.get("role", "admin"),
            "tenant": user.get("tenant"),
            "caps": user.get("caps") or [],
            "exp": exp_dt,
            "iat": datetime.now(timezone.utc),
        }
        token = jwt.encode(payload, secret, algorithm="HS256")
        public_user = {
            "id": user.get("id"),
            "email": user.get("email"),
            "role": user.get("role"),
            "tenant": user.get("tenant"),
            "display_name": user.get("display_name"),
            "caps": user.get("caps") or [],
        }
        return {
            "access_token": token,
            "token_type": "bearer",
            "expires_in": exp_minutes * 60,
            "user": public_user,
        }
