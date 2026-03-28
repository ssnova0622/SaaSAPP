# app/services/core/ai_facade.py
"""
AI/analytics facade: single entry point for AI endpoints. Delegates to Storage for
events, predictions, insights. Routers use get_ai_service() instead of Storage directly.
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional

from app.services.storage_mongo import Storage


class AIService:
    """Facade over Storage for AI/analytics. Use via get_ai_service() from container."""

    @staticmethod
    def insert_event(tenant: str, data: Dict[str, Any]) -> Dict[str, Any]:
        return Storage.insert_event(tenant=tenant, data=data)

    @staticmethod
    def predictions_summary(tenant: str, days: int = 30) -> Dict[str, Any]:
        return Storage.predictions_summary(tenant=tenant, days=days)

    @staticmethod
    def sales_forecast(tenant: str, days: int = 30, horizon: int = 14) -> Dict[str, Any]:
        return Storage.sales_forecast(tenant=tenant, days=days, horizon=horizon)

    @staticmethod
    def cart_recovery(tenant: str, window_hours: int = 24, top: int = 10) -> Dict[str, Any]:
        return Storage.cart_recovery(tenant=tenant, window_hours=window_hours, top=top)

    @staticmethod
    def list_upcoming_appointments(tenant: str, window_days: int = 7) -> Any:
        return Storage.list_upcoming_appointments(tenant=tenant, window_days=window_days)

    @staticmethod
    def count_customer_noshows(tenant: str, customer_id: Optional[str] = None) -> int:
        return Storage.count_customer_noshows(tenant=tenant, customer_id=customer_id)

    @staticmethod
    def top_services(tenant: str, days: int = 30, top: int = 5) -> Any:
        return Storage.top_services(tenant=tenant, days=days, top=top)

    @staticmethod
    def get_service_base_price(tenant: str, service_id: str) -> Optional[float]:
        return Storage.get_service_base_price(tenant=tenant, service_id=service_id)

    @staticmethod
    def treatment_insights(tenant: str, days: int = 90) -> Dict[str, Any]:
        return Storage.treatment_insights(tenant=tenant, days=days)

    @staticmethod
    def ai_insights_summary(tenant: str, days: int = 28) -> Dict[str, Any]:
        return Storage.ai_insights_summary(tenant=tenant, days=days)
