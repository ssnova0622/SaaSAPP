# app/helpers/phone_utils.py
import re
from typing import Optional


def normalize_phone(phone: str, country_code: Optional[str] = None) -> str:
    """Standardize phone: strip non-digits (keep leading +), optionally prepend country_code, ensure + prefix."""
    if not phone:
        return ""
    p = str(phone).strip()
    digits = re.sub(r"\D", "", p)
    if not digits:
        return ""
    if country_code:
        cc = str(country_code).replace("+", "")
        if not digits.startswith(cc):
            if len(digits) <= 11:
                if len(digits) == 11 and digits.startswith("0"):
                    digits = digits[1:]
                digits = cc + digits
    if len(digits) >= 7:
        return f"+{digits}"
    return digits


def normalize_promo_phone(phone: str) -> str:
    p = (phone or "").strip().replace(" ", "").replace("-", "")
    if p.startswith("whatsapp:+"):
        p = p[len("whatsapp:+"):]
        p = "+" + p
    return p
