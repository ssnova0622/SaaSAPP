# app/helpers/money_format.py
"""Tenant-facing money strings for reports and PDFs (uses payment_config.currency)."""
from __future__ import annotations

from typing import Any, Dict, Optional


def format_money(amount: float, currency: str = "INR") -> str:
    """Format a numeric amount with a symbol or ISO code prefix. No locale dependency."""
    try:
        val = float(amount or 0.0)
    except (TypeError, ValueError):
        val = 0.0
    c = (currency or "INR").strip().upper() or "INR"
    s = f"{val:,.2f}"
    symbols = {
        "INR": "₹",
        "USD": "$",
        "EUR": "€",
        "GBP": "£",
        "AED": "AED ",
        "SAR": "SAR ",
        "SGD": "S$",
        "AUD": "A$",
        "NZD": "NZ$",
        "CAD": "CA$",
        "JPY": "¥",
        "CNY": "¥",
        "KRW": "₩",
        "CHF": "CHF ",
        "SEK": "SEK ",
        "NOK": "NOK ",
        "DKK": "DKK ",
        "ZAR": "R",
        "BRL": "R$",
        "MXN": "MX$",
    }
    sym = symbols.get(c)
    if sym:
        return f"{sym}{s}"
    return f"{c} {s}"


def tenant_currency(tenant_doc: Optional[Dict[str, Any]]) -> str:
    """Resolve ISO currency from tenant settings document."""
    if not tenant_doc:
        return "INR"
    pay = tenant_doc.get("payment_config") or {}
    cur = pay.get("currency") if isinstance(pay, dict) else None
    if isinstance(cur, str) and cur.strip():
        return cur.strip().upper()
    return "INR"
