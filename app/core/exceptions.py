"""Centralized application exceptions and HTTP mapping for consistent error handling."""
from __future__ import annotations

from typing import Any, Dict, Optional


class AppError(Exception):
    """Base exception for application errors; can be mapped to HTTP responses."""

    def __init__(
            self,
            message: str,
            status_code: int = 500,
            detail: Optional[Dict[str, Any]] = None,
    ):
        super().__init__(message)
        self.message = message
        self.status_code = status_code
        self.detail = detail or {}

    def to_dict(self) -> Dict[str, Any]:
        return {"detail": self.message, **self.detail}


class NotFoundError(AppError):
    """Resource not found (404)."""

    def __init__(self, message: str = "Resource not found", detail: Optional[Dict[str, Any]] = None):
        super().__init__(message, status_code=404, detail=detail)


class DuplicateError(AppError):
    """Duplicate resource / conflict (409 or 400)."""

    def __init__(self, message: str, status_code: int = 409, detail: Optional[Dict[str, Any]] = None):
        super().__init__(message, status_code=status_code, detail=detail)


class ValidationError(AppError):
    """Validation error (400)."""

    def __init__(self, message: str, detail: Optional[Dict[str, Any]] = None):
        super().__init__(message, status_code=400, detail=detail)
