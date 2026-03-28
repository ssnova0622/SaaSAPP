"""Appointment slot recommendation and NL parsing (AIPredictor). Lived in app.services.ai.py; re-homed here so app.services.ai package can export it.

Intent detection uses tenant ai_config.intent_keywords when tenant is passed: no hardcoding.
Tenants can add phrases (e.g. "where is my amount" for refund_policy) via PUT /tenants/{tenant} with
body.ai_config.intent_keywords = { "refund_policy": ["where is my amount"], ... }. Phrases are merged
with defaults. When no intent matches, flow falls back to menu (Enterprise/Basic behaviour).
"""
from __future__ import annotations
import datetime as dt
import re
from zoneinfo import ZoneInfo
from typing import List, Optional, Tuple, Any, Dict

from app.helpers.constants import SLOT_STATUS_AVAILABLE
from app.services.storage_mongo import Storage
from app.core.container import get_tenant_service


class AIPredictor:
    """
    Intelligent predictor for recommending appointment slots.
    Strategy:
      - Context-Aware: Prioritizes slots near the current time or preferred logical blocks.
      - History-Driven: Boosts slots matching the customer's historical booking patterns.
      - Gap-Reduction: Minimizes "swiss cheese" schedules by favoring slots adjacent to existing bookings.
      - Load-Balancing: Uses inverse popularity for general recommendations.
    """

    def recommend(
            self,
            tenant: str,
            professional: Optional[str] = None,
            customer_phone: Optional[str] = None,
            top_k: int = 3
    ) -> Tuple[List[str], str]:
        pros = Storage.get_professionals(tenant)
        if professional:
            pros = [p for p in pros if p.name == professional]
        if not pros:
            return [], "No professionals found for tenant"

        settings = get_tenant_service().get_tenant_settings(tenant) or {}
        tz_name = settings.get("tz") or DEFAULT_TIMEZONE
        try:
            tz = ZoneInfo(tz_name)
        except Exception:
            tz = ZoneInfo("UTC")

        now_local = dt.datetime.now(tz)
        today_str = now_local.date().isoformat()

        # 1. Gather historical preference
        history_pref = {}
        if customer_phone:
            history_pref = self._get_customer_history_pref(tenant, customer_phone)

        # 2. Gather slot popularity (for load balancing)
        popularity = self._slot_popularity(tenant)

        # 3. Gather daily adjacency (for gap reduction)
        booked_times = self._get_today_booked_times(tenant, professional, now_local.date())

        candidates: List[Tuple[str, float]] = []

        for p in pros:
            overrides = getattr(p, "date_overrides", {}) or {}
            day_overrides = overrides.get(today_str) or []
            blocked_times = {s["time"] for s in day_overrides if s.get("status") == "blocked"}

            for s in p.slots:
                if s.status != SLOT_STATUS_AVAILABLE or s.time in blocked_times:
                    continue

                score = 0.0
                score -= popularity.get(s.time, 0) * 0.1
                if s.time.endswith(":30"):
                    score += 0.5
                try:
                    sh, sm = map(int, s.time.split(":"))
                    diff_hours = (sh + sm / 60.0) - (now_local.hour + now_local.minute / 60.0)
                    if 0 < diff_hours <= 4:
                        score += 2.0
                    elif diff_hours > 4:
                        score += 1.0
                    elif diff_hours < 0:
                        score -= 1.0
                except Exception:
                    pass
                if s.time in history_pref:
                    score += history_pref[s.time] * 5.0
                if s.time in booked_times:
                    score += 3.0
                candidates.append((s.time, score))

        if not candidates:
            return [], "No available slots"

        best: dict[str, float] = {}
        for t, sc in candidates:
            if t not in best or sc > best[t]:
                best[t] = sc
        ranked = sorted(best.items(), key=lambda x: (-x[1], x[0]))
        recs = [t for t, _ in ranked[: max(1, top_k)]]

        rationale = "Recommended based on your history, current time, and optimized scheduling."
        if not history_pref and not booked_times:
            rationale = "Recommended based on availability and spreading load."
        elif history_pref and recs and recs[0] in history_pref:
            rationale = f"Based on your preference for {recs[0]}, we found these available slots."
        return recs, rationale

    def detect_intent(self, text: str, tenant: Optional[str] = None) -> Tuple[Optional[str], float]:
        """Detect intent from user text. Sources (in order): 1) MongoDB ai_knowledge_base (global + tenant), 2) tenant ai_config, 3) code fallback."""
        if not text:
            return None, 0.0
        t = text.lower().strip()
        if t.isdigit():
            return None, 0.0
        if tenant:
            config = self._get_intent_config_from_db_or_settings(tenant)
            if config:
                intent = self._match_intent_from_config(t, config)
                if intent:
                    return intent, 0.85
        return self._detect_intent_fallback(t)

    def _get_intent_config_from_db_or_settings(self, tenant: str) -> Optional[Dict[str, Any]]:
        """Load intent_keywords: 1) MongoDB ai_knowledge_base (global + tenant), 2) tenant ai_config (intent_keywords), else None."""
        try:
            from app.services.ai.knowledge_storage import get_intent_keywords_for_tenant
            keywords, order = get_intent_keywords_for_tenant(tenant)
            if keywords:
                return {"intent_keywords": keywords, "intent_keywords_order": order}
        except Exception:
            pass
        try:
            from app.services.ai.config_schema import get_effective_ai_config
            settings = get_tenant_service().get_tenant_settings(tenant) or {}
            return get_effective_ai_config(settings)
        except Exception:
            return None

    def _match_intent_from_config(self, t: str, config: Dict[str, Any]) -> Optional[str]:
        """Match text against config intent_keywords in configured order. First match wins."""
        keywords = config.get("intent_keywords") or {}
        order = config.get("intent_keywords_order") or list(keywords.keys())
        for intent in order:
            phrases = keywords.get(intent)
            if not isinstance(phrases, list):
                continue
            for phrase in phrases:
                if phrase and str(phrase).lower().strip() in t:
                    return intent
        return None

    def _detect_intent_fallback(self, t: str) -> Tuple[Optional[str], float]:
        """Fallback when no tenant or config missing: use built-in keyword lists (same as before)."""
        if any(kw in t for kw in ["book", "appointment", "schedule", "timing", "slot", "reserve"]):
            if "cancel" in t:
                return "cancel_appointment", 0.9
            if "reschedule" in t or "change" in t or "move" in t:
                return "reschedule_appointment", 0.9
            return "book_appointment", 0.8
        if any(kw in t for kw in ["cancel", "delete", "remove", "stop"]):
            return "cancel_appointment", 0.85
        if any(kw in t for kw in ["reschedule", "change time", "new time", "different time"]):
            return "reschedule_appointment", 0.85
        if any(kw in t for kw in
               ["professional", "doctor", "stylist", "expert", "who is", "tell me about", "check doctor"]):
            if any(kw in t for kw in ["suggest", "recommend", "best", "available"]):
                return "suggest_professional", 0.8
            return "professional_details", 0.8
        if any(kw in t for kw in ["price", "cost", "how much", "buy", "product", "catalog", "item", "service"]):
            return "check_price", 0.8
        if any(kw in t for kw in ["offer", "discount", "promo", "deal", "coupon", "sale"]):
            return "show_offers", 0.8
        if any(kw in t for kw in
               ["refund", "return policy", "return money", "money back", "cancel order", "where is my amount"]):
            return "refund_policy", 0.85
        if any(kw in t for kw in
               ["delivery time", "how long", "expect order", "when expect", "when order", "arrive", "shipping time",
                "delivery days"]):
            return "delivery_eta", 0.8
        if any(kw in t for kw in ["order", "track", "status", "where is my", "shipped", "dispatch"]):
            return "order_status", 0.8
        if any(kw in t for kw in
               ["show", "need", "want", "looking for", "recommend", "suggest", "find", "get me", "cheap", "affordable",
                "best", "cake", "shoes", "product", "item"]):
            return "product_recommendation", 0.8
        if any(kw in t for kw in ["hour", "open", "close", "contact", "phone", "address", "policy", "faq", "help"]):
            return "faq", 0.75
        return None, 0.0

    def parse_preferred_time(self, text: str) -> Optional[Tuple[int, int]]:
        if not text or not text.strip():
            return None
        t = text.strip().lower()
        if re.search(r"\b(after|post)\s*lunch\b", t):
            return (13, 0)
        if "before noon" in t:
            return (11, 0)
        if re.search(r"sometime?\s*(in\s+)?(the\s+)?afternoon", t):
            return (14, 0)
        if re.search(r"sometime?\s*(in\s+)?(the\s+)?evening", t):
            return (18, 0)
        if re.search(r"sometime?\s*(in\s+)?(the\s+)?morning", t):
            return (9, 0)
        m = re.search(r"before\s+(\d{1,2})\s*(am|pm)?", t)
        if m:
            h = int(m.group(1))
            if m.group(2) == "pm" and h != 12:
                h += 12
            elif m.group(2) == "am" and h == 12:
                h = 0
            elif not m.group(2) and 1 <= h <= 11:
                h += 12
            if 0 <= h <= 23:
                return (max(0, h - 1), 0)
        m = re.search(r"post\s+(\d{1,2})\s*(am|pm)?", t)
        if m:
            h = int(m.group(1))
            if m.group(2) == "pm" and h != 12:
                h += 12
            elif m.group(2) == "am" and h == 12:
                h = 0
            elif not m.group(2) and 1 <= h <= 11:
                h += 12
            if 0 <= h <= 23:
                return (h, 0)
        m = re.search(r"(\d{1,2})\s+or\s+(\d{1,2})\s*(pm|am)?", t)
        if m:
            h = int(m.group(1))
            if m.group(3) == "pm" and h != 12:
                h += 12
            elif m.group(3) == "am" and h == 12:
                h = 0
            elif m.group(3) != "am" and 1 <= h <= 11:
                h += 12
            if 0 <= h <= 23:
                return (h, 0)
        m = re.search(r"(\d{1,2})\s*(pm|am)\b", t)
        if m:
            h, mi = int(m.group(1)), 0
            if m.group(2) == "pm" and h != 12:
                h += 12
            elif m.group(2) == "am" and h == 12:
                h = 0
            if 0 <= h <= 23:
                return (h, mi)
        m = re.search(r"\b(around|about|like|need|want|prefer|by)\s*(\d{1,2})\b", t)
        if m:
            h = int(m.group(2))
            if 1 <= h <= 11:
                h += 12
            elif h == 12:
                h = 12
            if 0 <= h <= 23:
                return (h, 0)
        return None

    def extract_entities(self, text: str, intent: str) -> dict[str, Any]:
        entities = {}
        t = text.strip()
        tl = t.lower()
        appt_match = re.search(r"([A-Z]{2}-[A-Z]{2,4}-\d{4})", t, re.IGNORECASE)
        if appt_match:
            entities["appointment_id"] = appt_match.group(1).upper()
        phone_match = re.search(r"(\+?\d{10,15})", t)
        if phone_match:
            entities["phone"] = phone_match.group(1)
        time_match = re.search(r"(\d{1,2}:\d{2})", t)
        if time_match:
            entities["time"] = time_match.group(1)
        date_match = re.search(r"(\d{4}-\d{2}-\d{2})", t)
        if date_match:
            entities["date"] = date_match.group(1)
        elif "today" in tl:
            entities["date_marker"] = "today"
        elif "tomorrow" in tl:
            entities["date_marker"] = "tomorrow"
        services = ["haircut", "facial", "nails", "spa", "hair color", "consultation", "dental cleaning",
                    "skin treatment", "test drive", "car viewing", "service appointment"]
        for s in services:
            if s in tl:
                entities["service"] = s
                break
        prof_keywords = ["with", "dr", "dr.", "doctor", "stylist", "professional", "by", "for"]
        for kw in prof_keywords:
            if f" {kw} " in f" {tl} ":
                parts = tl.split(f" {kw} ")
                if len(parts) > 1:
                    name_candidate = parts[1].strip().split(" ")
                    if name_candidate:
                        entities["professional_name"] = name_candidate[0].capitalize()
                        if len(name_candidate) > 1:
                            entities["professional_name"] += " " + name_candidate[1].capitalize()
                break
        # Order ID for order_status / track_order: ORD-xxx, digits, or "order 1234"
        if intent == "order_status":
            ord_match = re.search(r"(?:order\s*#?\s*|#)([A-Za-z0-9\-]+)", t, re.IGNORECASE)
            if ord_match:
                entities["order_id"] = ord_match.group(1).strip()
            else:
                num_match = re.search(r"\b(\d{4,})\b", t)
                if num_match:
                    entities["order_id"] = num_match.group(1)
        return entities

    def search_catalog(self, tenant: str, query: str) -> List[dict[str, Any]]:
        if not query:
            return []
        clean_q = query.lower()
        for kw in ["price", "of", "how", "much", "is", "cost", "for"]:
            clean_q = clean_q.replace(kw, "")
        clean_q = clean_q.strip()
        res = Storage.list_products(tenant, search=clean_q, active=True, page=1, size=5)
        return res.get("items") or []

    def search_professionals(self, tenant: str, query: str) -> List[dict[str, Any]]:
        clean_q = query.lower()
        for kw in ["suggest", "recommend", "best", "stylist", "doctor", "expert", "who", "is", "details", "about"]:
            clean_q = clean_q.replace(kw, "")
        clean_q = clean_q.strip()
        pros = Storage.list_professionals_full(tenant, active=True)
        results = []
        for p in pros:
            name = str(p.get("name") or "").lower()
            if not clean_q or clean_q in name:
                results.append(p)
        if not results and not clean_q:
            return pros[:3]
        return results[:3]

    def _get_customer_history_pref(self, tenant: str, phone: str) -> dict[str, int]:
        pref = {}
        appts = Storage.list_appointments(tenant, search_type="phone", search_value=phone)
        for a in appts:
            if a.status == "booked":
                pref[a.time] = pref.get(a.time, 0) + 1
        return pref

    def _get_today_booked_times(self, tenant: str, professional: Optional[str], day: dt.date) -> set[str]:
        adj = set()
        appts = Storage.list_appointments(tenant, professional=professional, date_str=day.isoformat())
        for a in appts:
            if a.status != "booked":
                continue
            try:
                h, m = map(int, a.time.split(":"))
                t_dt = dt.datetime(2000, 1, 1, h, m)
                prev_t = (t_dt - dt.timedelta(minutes=30)).strftime("%H:%M")
                next_t = (t_dt + dt.timedelta(minutes=30)).strftime("%H:%M")
                adj.add(prev_t)
                adj.add(next_t)
            except Exception:
                continue
        return adj

    def _slot_popularity(self, tenant: str) -> dict[str, int]:
        pop: dict[str, int] = {}
        for appt in Storage.list_appointments(tenant):
            if appt.status == "booked":
                pop[appt.time] = pop.get(appt.time, 0) + 1
        return pop
