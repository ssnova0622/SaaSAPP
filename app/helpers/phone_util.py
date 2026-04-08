"""
Single phone helper for the application. Canonical stored shape:
  phone_number: {"code": "+91", "number": "9898989898"}

Never persist a parallel string `phone` / `mobile_number` key — use `number` only.
"""
from __future__ import annotations

import re
from typing import Any, Dict, List, Optional

from app.helpers.countries_data import COUNTRIES, DEFAULT_TENANT_COUNTRY_ISO2, dial_digits_for_iso

_DIAL_PREFIXES_SORTED: Optional[List[str]] = None


class PhoneUtil:
    """Normalize, validate, and convert phone data. Default country: India (+91)."""

    DEFAULT_CODE = "+91"
    DEFAULT_DIAL_DIGITS = "91"

    # ------------------------------------------------------------------
    # Internals
    # ------------------------------------------------------------------
    @classmethod
    def _dial_prefixes_longest_first(cls) -> List[str]:
        global _DIAL_PREFIXES_SORTED
        if _DIAL_PREFIXES_SORTED is None:
            _DIAL_PREFIXES_SORTED = sorted({c["dial"] for c in COUNTRIES}, key=len, reverse=True)
        return _DIAL_PREFIXES_SORTED

    @classmethod
    def digits(cls, s: str) -> str:
        return re.sub(r"\D", "", s or "")

    # ------------------------------------------------------------------
    # Canonical dict: always code + number (national digits only)
    # ------------------------------------------------------------------
    @classmethod
    def normalize_phone_number(cls, raw: Any) -> Optional[Dict[str, str]]:
        """Accept legacy shapes (mobile_number key, string E.164) → canonical dict or None."""
        if raw is None:
            return None
        if isinstance(raw, str) and not str(raw).strip():
            return None
        if isinstance(raw, dict):
            code = str(raw.get("code") or "").strip()
            num = raw.get("number")
            if num is None and raw.get("mobile_number") is not None:
                num = raw.get("mobile_number")
            num = cls.digits(str(num or ""))
            cc = cls.digits(code.replace("+", ""))
            if not cc or not num:
                return None
            return {"code": f"+{cc}", "number": num}
        return None

    @classmethod
    def validate(cls, pn: Dict[str, Any]) -> None:
        c = cls.normalize_phone_number(pn)
        if not c:
            raise ValueError("Invalid phone_number: need code and number")
        num = c["number"]
        cc = cls.digits(c["code"])
        if len(num) < 4 or len(num) > 15:
            raise ValueError("Phone national number must be 4–15 digits")
        if len(cc) < 1 or len(cc) > 6:
            raise ValueError("Invalid country calling code")

    @classmethod
    def to_e164(cls, pn: Any) -> str:
        c = cls.normalize_phone_number(pn)
        if not c:
            return ""
        cc = cls.digits(c["code"])
        return f"+{cc}{c['number']}"

    @classmethod
    def normalize_e164_input(cls, phone: str, country_code_digits: Optional[str] = None) -> str:
        """Build E.164. Leading '+' → international as-is (digits only). Else prepend tenant dial digits."""
        if not phone:
            return ""
        p = str(phone).strip()
        if p.lower().startswith("whatsapp:"):
            p = p[9:].strip()
        explicit = p.startswith("+")
        digits = cls.digits(p)
        if not digits:
            return ""
        if explicit:
            return f"+{digits}" if len(digits) >= 7 else digits
        cc = (country_code_digits or cls.DEFAULT_DIAL_DIGITS).replace("+", "").strip()
        if cc:
            if len(digits) >= 11 and digits.startswith("0"):
                digits = digits.lstrip("0") or digits
            if not digits.startswith(cc):
                digits = cc + digits
        return f"+{digits}" if len(digits) >= 7 else digits

    @classmethod
    def from_raw(cls, raw: str, tenant_dial_digits: str) -> Dict[str, str]:
        """Parse free-text / national / E.164 into canonical phone_number."""
        td = (tenant_dial_digits or cls.DEFAULT_DIAL_DIGITS).replace("+", "").strip()
        e164 = cls.normalize_e164_input(raw, td)
        digits = cls.digits(e164)
        if len(digits) < 7:
            raise ValueError("Invalid phone number")
        for prefix in cls._dial_prefixes_longest_first():
            if digits.startswith(prefix) and len(digits) > len(prefix):
                national = digits[len(prefix) :]
                if len(national) < 4:
                    continue
                out = {"code": f"+{prefix}", "number": national}
                cls.validate(out)
                return out
        if td and digits.startswith(td) and len(digits) > len(td):
            out = {"code": f"+{td}", "number": digits[len(td) :]}
            cls.validate(out)
            return out
        raise ValueError("Could not determine country code for this phone number")

    @classmethod
    def prepare_storage(cls, raw: Optional[str], tenant_dial_digits: str) -> Optional[Dict[str, str]]:
        if raw is None or not str(raw).strip():
            return None
        return cls.from_raw(str(raw).strip(), tenant_dial_digits)

    @classmethod
    def promo_normalize(cls, phone: str) -> str:
        p = (phone or "").strip().replace(" ", "").replace("-", "")
        if p.startswith("whatsapp:+"):
            p = p[len("whatsapp:+") :]
            p = "+" + p
        return p

    @classmethod
    def tenant_default_dial_digits(cls, tenant_iso: Optional[str]) -> str:
        return dial_digits_for_iso(tenant_iso or DEFAULT_TENANT_COUNTRY_ISO2)

    # ------------------------------------------------------------------
    # Mongo / API document shaping (no extra persisted string field)
    # ------------------------------------------------------------------
    @classmethod
    def customer_filter(cls, tenant: str, pn: Dict[str, str]) -> Dict[str, Any]:
        c = cls.normalize_phone_number(pn)
        if not c:
            raise ValueError("phone_number required")
        return {
            "tenant": tenant,
            "phone_number.code": c["code"],
            "phone_number.number": c["number"],
        }

    @classmethod
    def enrich_document(
        cls,
        doc: Dict[str, Any],
        *,
        phone_field: str = "phone_number",
        tenant_dial_digits: str,
        legacy_plain_field: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Ensure canonical phone_number only; strip legacy string fields from copy (for API)."""
        out = dict(doc)
        legacy_plain_field = legacy_plain_field or (
            "phone" if phone_field == "phone_number" else None
        )
        if legacy_plain_field and legacy_plain_field in out:
            out.pop(legacy_plain_field, None)
        pn = cls.normalize_phone_number(out.get(phone_field))
        if not pn and legacy_plain_field:
            leg = doc.get(legacy_plain_field)
            if leg:
                try:
                    pn = cls.from_raw(str(leg), tenant_dial_digits)
                except Exception:
                    pn = None
        if pn:
            out[phone_field] = pn
        elif phone_field in out:
            out.pop(phone_field, None)
        return out

    @classmethod
    def export_e164(cls, doc_or_pn: Any, tenant_dial_digits: str = "91") -> str:
        if isinstance(doc_or_pn, dict) and "code" in doc_or_pn:
            return cls.to_e164(doc_or_pn)
        if isinstance(doc_or_pn, dict):
            return cls.to_e164(doc_or_pn.get("phone_number") or doc_or_pn.get("customer_phone_number"))
        if doc_or_pn:
            return cls.normalize_e164_input(str(doc_or_pn), tenant_dial_digits)
        return ""

    @classmethod
    def appointment_customer_e164(cls, doc: Dict[str, Any], tenant_dial_digits: str = DEFAULT_DIAL_DIGITS) -> str:
        """E.164 for an appointment doc: prefer customer_phone_number, else legacy customer_phone."""
        e = cls.to_e164(doc.get("customer_phone_number"))
        if e:
            return e
        leg = doc.get("customer_phone")
        if leg:
            td = (tenant_dial_digits or cls.DEFAULT_DIAL_DIGITS).replace("+", "").strip()
            return cls.normalize_e164_input(str(leg), td)
        return ""

    @classmethod
    def customer_match_query(cls, tenant: str, phone_e164: str, tenant_dial: str) -> Dict[str, Any]:
        """Match a customer by canonical phone_number or legacy flat `phone` (E.164)."""
        raw = str(phone_e164 or "").strip()
        if not raw:
            return {"tenant": tenant, "_id": None}
        td = (tenant_dial or cls.DEFAULT_DIAL_DIGITS).replace("+", "").strip()
        parts: List[Dict[str, Any]] = [{"tenant": tenant, "phone": raw}]
        try:
            pn = cls.from_raw(raw, td)
        except ValueError:
            pn = cls.prepare_storage(raw, td)
        if pn:
            parts.append(
                {
                    "tenant": tenant,
                    "phone_number.code": pn["code"],
                    "phone_number.number": pn["number"],
                }
            )
        return {"$or": parts} if len(parts) > 1 else parts[0]

    @classmethod
    def appointment_phone_search_query(
        cls, tenant: str, search_raw: str, tenant_dial: Optional[str]
    ) -> Dict[str, Any]:
        """
        Mongo fragment: match appointment customer phone (legacy string or customer_phone_number).
        search_raw is user input; tenant_dial is digits only (e.g. 91).
        """
        td = (tenant_dial or cls.DEFAULT_DIAL_DIGITS).replace("+", "").strip()
        val = cls.normalize_e164_input(str(search_raw or "").strip(), td)
        clauses: List[Dict[str, Any]] = []
        if val.startswith("+") and len(val) > 1:
            digits = val[1:]
            escaped = "^\\s*\\+?" + re.escape(digits) + "\\s*$"
            try:
                num_val = int(digits)
                clauses.extend(
                    [
                        {"customer_phone": {"$regex": escaped, "$options": "i"}},
                        {"customer_phone": num_val},
                        {"customer_phone": val},
                    ]
                )
            except ValueError:
                clauses.append({"customer_phone": {"$regex": escaped, "$options": "i"}})
            pn = None
            try:
                pn = cls.from_raw(str(search_raw).strip(), td)
            except ValueError:
                try:
                    pn = cls.from_raw(val, td)
                except ValueError:
                    pass
            if pn:
                clauses.append(
                    {
                        "customer_phone_number.code": pn["code"],
                        "customer_phone_number.number": pn["number"],
                    }
                )
        else:
            esc = re.escape(val)
            clauses.append({"customer_phone": {"$regex": esc, "$options": "i"}})
            clauses.append({"customer_phone": val})
            clauses.append({"customer_phone": str(search_raw).strip()})
            try:
                pn2 = cls.from_raw(str(search_raw).strip(), td)
            except ValueError:
                pn2 = None
            if pn2:
                clauses.append(
                    {
                        "customer_phone_number.code": pn2["code"],
                        "customer_phone_number.number": pn2["number"],
                    }
                )
        return {"$or": clauses} if len(clauses) > 1 else clauses[0]
