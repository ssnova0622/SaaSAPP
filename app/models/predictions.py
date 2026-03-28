# app/models/predictions.py
from __future__ import annotations
from typing import Optional, List
from pydantic import BaseModel


class PredictRequest(BaseModel):
    tenant: str
    professional: Optional[str] = None
    top_k: int = 3


class PredictResponse(BaseModel):
    tenant: str
    professional: Optional[str]
    recommended: List[str]
    rationale: str
