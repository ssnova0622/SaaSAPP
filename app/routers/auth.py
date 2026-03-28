from __future__ import annotations
from typing import Optional, Dict, Any

from fastapi import APIRouter, Response, Depends
from pydantic import BaseModel

from settings import env
from app.services.auth.auth_service import AuthService
from .deps import get_current_user, ensure_super_admin
from app.services.otp.otp_service import verify_otp_and_consume
from app.services.system_config_service import set_system_config, is_login_otp_enabled

router = APIRouter()


class LoginRequest(BaseModel):
    email: str
    password: str


class LoginResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int
    user: Dict[str, Any]


class RequiresOtpResponse(BaseModel):
    requires_otp: bool = True
    session_id: str
    message: str


@router.post("/auth/login")
def login(body: LoginRequest, response: Response):
    """Login. Returns JWT or requires_otp + session_id when OTP is enabled for non–super_admin."""
    token_resp = AuthService.verify_and_issue_token(email=body.email, password=body.password)
    if token_resp.get("requires_otp"):
        return token_resp
    # Set HttpOnly cookie so subsequent requests (e.g. Swagger UI) can use session auth
    response.set_cookie(
        key="access_token",
        value=token_resp["access_token"],
        max_age=token_resp["expires_in"],
        httponly=True,
        secure=env.bool("COOKIE_SECURE", False),
        samesite=env.str("COOKIE_SAMESITE", "lax").lower(),
    )
    return LoginResponse(**token_resp)


class VerifyOtpRequest(BaseModel):
    session_id: str
    otp: str


@router.post("/auth/verify-otp", response_model=LoginResponse)
def verify_otp(body: VerifyOtpRequest, response: Response):
    """Verify OTP and complete login. Returns JWT on success."""
    from fastapi import HTTPException
    user = verify_otp_and_consume(body.session_id, body.otp)
    if not user:
        raise HTTPException(status_code=401, detail="Invalid or expired OTP. Please try logging in again.")
    token_resp = AuthService.issue_jwt(user)
    response.set_cookie(
        key="access_token",
        value=token_resp["access_token"],
        max_age=token_resp["expires_in"],
        httponly=True,
        secure=env.bool("COOKIE_SECURE", False),
        samesite=env.str("COOKIE_SAMESITE", "lax").lower(),
    )
    return LoginResponse(**token_resp)


class MeResponse(BaseModel):
    id: Optional[str] = None
    email: Optional[str] = None
    role: str
    tenant: Optional[str] = None
    display_name: Optional[str] = None
    caps: Optional[list] = None


@router.get("/auth/me", response_model=MeResponse)
def me(user: Dict[str, Any] = Depends(get_current_user)):
    return MeResponse(
        id=user.get("sub"),
        email=user.get("email"),  # may be missing if token was minted without
        role=user.get("role", "admin"),
        tenant=user.get("tenant"),
        display_name=user.get("display_name"),
        caps=user.get("caps"),
    )


# ---------- System config: login OTP (super_admin only) ----------


@router.get("/auth/system/login-otp")
def get_login_otp_enabled(_: bool = Depends(ensure_super_admin)):
    """Return whether login OTP is enabled for non–super_admin users. Super Admin only."""
    return {"login_otp_enabled": is_login_otp_enabled()}


class LoginOtpConfigBody(BaseModel):
    login_otp_enabled: bool


@router.patch("/auth/system/login-otp")
def set_login_otp_enabled(body: LoginOtpConfigBody, _: bool = Depends(ensure_super_admin)):
    """Enable or disable login OTP for tenant_admin and staff. Super Admin only. Super Admin login is never subject to OTP."""
    set_system_config("login_otp_enabled", body.login_otp_enabled)
    return {"login_otp_enabled": is_login_otp_enabled()}
