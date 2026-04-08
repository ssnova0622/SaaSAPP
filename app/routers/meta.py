"""Public reference data for admin UI (countries, etc.)."""
from __future__ import annotations

from fastapi import APIRouter, Depends

from app.helpers.countries_data import list_countries_response
from .deps import get_current_user

router = APIRouter(dependencies=[Depends(get_current_user)])


@router.get("/meta/countries")
def get_countries() -> dict:
    return {"items": list_countries_response()}
