# app/models/ai.py
from __future__ import annotations
from typing import List, Dict, Any, Optional
from pydantic import BaseModel


class LowStockResponse(BaseModel):
    items: List[Dict[str, Any]]
    days: int
    lead_time: int
    safety_days: int


class TopSellersResponse(BaseModel):
    items: List[Dict[str, Any]]
    days: int


class PredictionsSummaryResponse(BaseModel):
    summary: Dict[str, Any]


class SalesForecastResponse(BaseModel):
    forecast: List[Dict[str, Any]]


class CartRecoveryResponse(BaseModel):
    items: List[Dict[str, Any]]
    window_hours: int
    top: int


class SlotRecommendationResponse(BaseModel):
    recommended: List[Any]
    rationale: List[Any]
    all_available: List[str]


class NoShowScore(BaseModel):
    appointment_id: str
    customer_id: Optional[str]
    time: Optional[str]
    professional: Optional[str]
    score: float
    rationale: str


class NoShowScoresResponse(BaseModel):
    items: List[NoShowScore]
    window_days: int


class RescheduleProposal(BaseModel):
    appointment_id: str
    current_time: Optional[str]
    options: List[str]


class RescheduleResponse(BaseModel):
    proposals: List[RescheduleProposal]


class PersonalizedServicesResponse(BaseModel):
    items: List[Dict[str, Any]]
    customer_id: Optional[str]


class WorkloadBalanceResponse(BaseModel):
    weights: Dict[str, float]
    date: Optional[str]


class PricingQuoteResponse(BaseModel):
    service_id: str
    base_price: float
    suggested_price: float
    rationale: str


class FollowupQueueResponse(BaseModel):
    queued: int


class TreatmentInsightsResponse(BaseModel):
    days: int
    top_treatments: List[Dict[str, Any]]
    repeat_rate: float


class AiInsightsSummaryResponse(BaseModel):
    tenant: str
    days: int
    utilization: float
    no_show_risk: float
    revenue_at_risk: float
    top_services: List[Dict[str, Any]]
    staff_load: Dict[str, Any]


class VoiceIngestResponse(BaseModel):
    status: str
    id: Optional[str]
