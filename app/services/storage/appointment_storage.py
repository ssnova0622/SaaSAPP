"""MongoDB storage for appointments. Composed into Storage; uses cls.get_tenant_settings, cls.get_professional, cls._generate_prof_short, cls._get_tenant_country_code, cls.count_appointments_overlapping from the composed Storage."""
from __future__ import annotations

import datetime as dt
import logging
import re
from typing import Any, Dict, List, Optional

from pymongo import ReturnDocument
from zoneinfo import ZoneInfo

from app.helpers.constants import (
    APPOINTMENT_STATUS_CANCELED,
    APPOINTMENT_STATUS_NEEDS_RESCHEDULE,
    DEFAULT_TIMEZONE,
    SLOT_STATUS_AVAILABLE,
)
from app.helpers.date_utils import utcnow
from app.helpers.phone_utils import normalize_phone
from app.services.db import collections, get_db
from app.services.storage.models import Appointment, Professional, Slot

logger = logging.getLogger(__name__)


class AppointmentStorage:
    """
    Appointment-related storage methods. Expects to be composed with mixins that provide:
    get_tenant_settings, get_professional, _generate_prof_short, _get_tenant_country_code.
    """

    @classmethod
    def list_appointments(
        cls,
        tenant: str,
        professional: Optional[str] = None,
        date_str: Optional[str] = None,
        search_type: Optional[str] = None,
        search_value: Optional[str] = None,
        status: Optional[str] = None,
    ) -> List[Appointment]:
        _tenants, pros_col, appts_col = collections()
        appts: List[Appointment] = []
        query: Dict[str, Any] = {"tenant": tenant}
        if professional:
            query["professional"] = professional

        if status:
            query["status"] = status

        if date_str:
            settings = cls.get_tenant_settings(tenant) or {}
            tz_name = settings.get("tz") or DEFAULT_TIMEZONE
            try:
                tz = ZoneInfo(tz_name)
            except Exception:
                tz = ZoneInfo(DEFAULT_TIMEZONE)

            try:
                day = dt.date.fromisoformat(date_str)
                start_local = dt.datetime.combine(day, dt.time(0, 0, 0)).replace(tzinfo=tz)
                end_local = start_local + dt.timedelta(days=1)
                query["start"] = {"$gte": start_local, "$lt": end_local}
            except Exception:
                pass

        if search_type and search_value:
            val = str(search_value).strip()
            if search_type == "phone":
                cc = cls._get_tenant_country_code(tenant)
                val = normalize_phone(val, country_code=cc)

            if search_type == "phone" and val.startswith("+"):
                digits = val[1:]
                escaped_val = "^\\s*\\+?" + re.escape(digits) + "\\s*$"
                try:
                    num_val = int(digits)
                    query["$or"] = [
                        {"customer_phone": {"$regex": escaped_val, "$options": "i"}},
                        {"customer_phone": num_val},
                        {"customer_phone": val},
                    ]
                except Exception as e:
                    logger.debug("Appointment phone query fallback: %s", e)
                    query["customer_phone"] = {"$regex": escaped_val, "$options": "i"}
            else:
                escaped_val = re.escape(val)
                if search_type == "phone":
                    query["customer_phone"] = {"$regex": escaped_val, "$options": "i"}
                elif search_type == "name":
                    query["customer_name"] = {"$regex": escaped_val, "$options": "i"}
                elif search_type == "token":
                    query["id"] = {"$regex": escaped_val, "$options": "i"}

        for doc in appts_col.find(query).sort("created_at", -1):
            appts.append(
                Appointment(
                    id=doc["id"],
                    customer_name=doc.get("customer_name", ""),
                    customer_phone=doc.get("customer_phone", ""),
                    professional=doc.get("professional", ""),
                    time=doc.get("time", ""),
                    price=float(doc.get("price", 0.0)),
                    status=doc.get("status", "booked"),
                    service=doc.get("service"),
                    created_at=doc.get("created_at", utcnow()),
                    created_by=doc.get("created_by"),
                    updated_at=doc.get("updated_at"),
                    updated_by=doc.get("updated_by"),
                    start=doc.get("start"),
                    end=doc.get("end"),
                )
            )

        if (not status or status == "blocked") and date_str:
            prof_query: Dict[str, Any] = {"tenant": tenant}
            if professional:
                prof_query["name"] = professional

            for prof_doc in pros_col.find(prof_query):
                overrides = prof_doc.get("date_overrides") or {}
                day_slots = overrides.get(date_str) or []
                for s in day_slots:
                    if s.get("status") == "blocked":
                        already_in_appts = any(
                            a.professional == prof_doc["name"] and a.time == s["time"] for a in appts
                        )
                        if not already_in_appts:
                            appts.append(
                                Appointment(
                                    id=f"BLOCKED-{prof_doc['name']}-{s['time']}",
                                    customer_name="BLOCKED",
                                    customer_phone="NA",
                                    professional=prof_doc["name"],
                                    time=s["time"],
                                    price=0.0,
                                    status="blocked",
                                    created_at=utcnow(),
                                    start=None,
                                    end=None,
                                )
                            )
        return appts

    @classmethod
    def create_appointment(
        cls,
        tenant: str,
        customer_name: str,
        customer_phone: str,
        professional: str,
        time: str,
        service: Optional[str] = None,
        source: str = "WA",
        date_str: Optional[str] = None,
        user_id: Optional[str] = None,
    ) -> Appointment:
        tenants_col, pros_col, appts_col = collections()

        settings = cls.get_tenant_settings(tenant) or {}
        appt_settings = (settings.get("appointments") or {}) if isinstance(settings, dict) else {}
        slot_duration = int(appt_settings.get("slot_duration_minutes", 30) or 30)
        tz_name = str(appt_settings.get("timezone") or settings.get("tz") or DEFAULT_TIMEZONE)
        try:
            tz = ZoneInfo(tz_name)
        except Exception:
            tz = ZoneInfo(DEFAULT_TIMEZONE)

        if date_str:
            try:
                d = dt.date.fromisoformat(date_str)
            except Exception:
                raise ValueError("Invalid date_str. Use YYYY-MM-DD.")
        else:
            d = dt.datetime.now(tz).date()

        try:
            hh, mm = [int(x) for x in time.split(":", 1)]
            start_local = dt.datetime(d.year, d.month, d.day, hh, mm, tzinfo=tz)
            end_local = start_local + dt.timedelta(minutes=slot_duration)
        except Exception:
            raise ValueError("Invalid time format. Use HH:MM.")

        prof_doc = pros_col.find_one(
            {"tenant": tenant, "name": professional},
            {"active": 1, "price": 1, "capacity": 1, "_id": 0},
        )
        if not prof_doc:
            raise ValueError("Professional not found")
        if not bool(prof_doc.get("active", True)):
            raise ValueError("Professional is inactive")

        is_today = d == dt.datetime.now(tz).date()

        if is_today:
            updated_prof = pros_col.find_one_and_update(
                {
                    "tenant": tenant,
                    "name": professional,
                    "slots": {"$elemMatch": {"time": time, "status": SLOT_STATUS_AVAILABLE}},
                },
                {"$set": {"slots.$.status": "booked"}},
                return_document=ReturnDocument.AFTER,
            )

            if not updated_prof:
                current_prof = pros_col.find_one(
                    {"tenant": tenant, "name": professional},
                    {"slots": 1},
                )
                target_slot = next(
                    (s for s in current_prof.get("slots", []) if s.get("time") == time), None
                )
                if target_slot and target_slot.get("status") == "blocked":
                    raise ValueError("Slot is blocked and cannot be booked")

                already_booked = pros_col.find_one(
                    {
                        "tenant": tenant,
                        "name": professional,
                        "slots": {"$elemMatch": {"time": time, "status": "booked"}},
                    }
                )
                if already_booked:
                    raise ValueError("Slot already booked")

                if source == "WA":
                    updated_prof = pros_col.find_one_and_update(
                        {"tenant": tenant, "name": professional},
                        {"$push": {"slots": {"time": time, "status": "booked"}}},
                        return_document=ReturnDocument.AFTER,
                    )
        else:
            updated_prof = prof_doc

        cap = int(prof_doc.get("capacity", 1) or 1)

        if date_str:
            prof_doc_full = pros_col.find_one(
                {"tenant": tenant, "name": professional}, {"date_overrides": 1}
            )
            overrides = (prof_doc_full.get("date_overrides") or {}) if prof_doc_full else {}
            day_slots = overrides.get(date_str) or []
            target_slot = next((s for s in day_slots if s.get("time") == time), None)
            if target_slot and target_slot.get("status") == "blocked":
                raise ValueError("Slot is blocked and cannot be booked")

        overlaps = cls.count_appointments_overlapping(
            tenant=tenant,
            professional=professional,
            start_iso=start_local.isoformat(),
            end_iso=end_local.isoformat(),
        )
        if overlaps >= cap:
            raise ValueError("Slot already booked (capacity reached)")

        prof_short = str(prof_doc.get("short_name") or "").upper()
        if not prof_short:
            prof_short = cls._generate_prof_short(tenant, professional)

        db = get_db()
        counters = db.get_collection("counters")
        today_str = d.strftime("%Y%m%d")
        counter_key = f"appt_counter:{tenant}:{professional}:{today_str}"
        try:
            res = counters.find_one_and_update(
                {"_id": counter_key},
                {"$inc": {"val": 1}},
                upsert=True,
                return_document=ReturnDocument.AFTER,
            )
            counter_val = res.get("val", 1)
        except Exception:
            import random
            counter_val = random.randint(1000, 9999)

        appt_id = f"{source}-{prof_short}-{counter_val:04d}"

        price = float(prof_doc.get("price", 0.0))
        cc = cls._get_tenant_country_code(tenant)
        customer_phone = normalize_phone(customer_phone, country_code=cc)
        appt = Appointment(
            id=appt_id,
            customer_name=customer_name,
            customer_phone=customer_phone,
            professional=professional,
            service=service,
            time=time,
            price=price,
            start=start_local,
            end=end_local,
            created_by=user_id,
        )
        appts_col.insert_one(
            {
                "tenant": tenant,
                "id": appt.id,
                "customer_name": appt.customer_name,
                "customer_phone": appt.customer_phone,
                "professional": appt.professional,
                "service": appt.service,
                "time": appt.time,
                "price": appt.price,
                "status": appt.status,
                "created_at": appt.created_at,
                "created_by": appt.created_by,
                "start": appt.start,
                "end": appt.end,
            }
        )
        if appt.status == "completed":
            tenants_col.update_one({"_id": tenant}, {"$inc": {"revenue": appt.price}})
        return appt

    @classmethod
    def update_appointment_status(
        cls,
        tenant: str,
        appt_id: str,
        status: str,
        user_id: Optional[str] = None,
    ) -> Appointment:
        tenants_col, pros_col, appts_col = collections()
        doc = appts_col.find_one({"tenant": tenant, "id": appt_id})
        if not doc:
            raise ValueError("Appointment not found")

        update_payload = {
            "status": status,
            "updated_at": utcnow(),
            "updated_by": user_id,
        }
        appts_col.update_one({"tenant": tenant, "id": appt_id}, {"$set": update_payload})

        old_status = doc.get("status")
        price = float(doc.get("price") or 0.0)

        if old_status != "completed" and status == "completed":
            tenants_col.update_one({"_id": tenant}, {"$inc": {"revenue": price}})
        elif old_status == "completed" and status != "completed":
            tenants_col.update_one({"_id": tenant}, {"$inc": {"revenue": -price}})

        updated = appts_col.find_one({"tenant": tenant, "id": appt_id})
        return Appointment(
            id=updated["id"],
            customer_name=updated.get("customer_name", ""),
            customer_phone=updated.get("customer_phone", ""),
            professional=updated.get("professional", ""),
            time=updated.get("time", ""),
            price=float(updated.get("price", 0.0)),
            status=updated.get("status", status),
            created_at=updated.get("created_at", utcnow()),
            created_by=updated.get("created_by"),
            updated_at=updated.get("updated_at"),
            updated_by=updated.get("updated_by"),
            start=updated.get("start"),
            end=updated.get("end"),
        )

    @classmethod
    def cancel_appointment(
        cls,
        tenant: str,
        appt_id: str,
        reason: str = "canceled",
        user_id: Optional[str] = None,
        date: Optional[dt.date] = None,
    ) -> Appointment:
        tenants_col, pros_col, appts_col = collections()

        query = {"tenant": tenant, "id": appt_id}
        if date:
            start_of_day = dt.datetime.combine(date, dt.time.min)
            end_of_day = dt.datetime.combine(date, dt.time.max)
            query["start"] = {"$gte": start_of_day, "$lte": end_of_day}

        doc = appts_col.find_one(query)
        if not doc:
            raise ValueError("Appointment not found")

        status = (
            APPOINTMENT_STATUS_CANCELED
            if reason == APPOINTMENT_STATUS_CANCELED
            else APPOINTMENT_STATUS_NEEDS_RESCHEDULE
        )

        update_payload = {
            "status": status,
            "updated_at": utcnow(),
            "updated_by": user_id,
        }

        appts_col.update_one({"_id": doc["_id"]}, {"$set": update_payload})

        tenant_doc = tenants_col.find_one({"_id": tenant}, {"tz": 1})
        tz_name = (tenant_doc or {}).get("tz") or DEFAULT_TIMEZONE
        try:
            tz = ZoneInfo(tz_name)
        except Exception:
            tz = ZoneInfo(DEFAULT_TIMEZONE)

        if status == "canceled":
            cls._set_slot_status(
                tenant,
                doc.get("professional"),
                doc.get("time"),
                SLOT_STATUS_AVAILABLE,
                date=doc.get("start").astimezone(tz).date() if doc.get("start") else None,
                user_id=user_id,
            )
        else:
            cls._set_slot_status(
                tenant,
                doc.get("professional"),
                doc.get("time"),
                "blocked",
                date=doc.get("start").astimezone(tz).date() if doc.get("start") else None,
                user_id=user_id,
            )

        if doc.get("status") == "completed":
            price = float(doc.get("price") or 0.0)
            tenants_col.update_one({"_id": tenant}, {"$inc": {"revenue": -price}})

        updated = appts_col.find_one({"tenant": tenant, "id": appt_id})
        return Appointment(
            id=updated["id"],
            customer_name=updated.get("customer_name", ""),
            customer_phone=updated.get("customer_phone", ""),
            professional=updated.get("professional", ""),
            time=updated.get("time", ""),
            price=float(updated.get("price", 0.0)),
            status=updated.get("status", status),
            created_at=updated.get("created_at", utcnow()),
            created_by=updated.get("created_by"),
            updated_at=updated.get("updated_at"),
            updated_by=updated.get("updated_by"),
        )

    @classmethod
    def _set_slot_status(
        cls,
        tenant: str,
        professional: str,
        time: str,
        status: str,
        date: Optional[dt.date] = None,
        user_id: Optional[str] = None,
    ) -> None:
        tenants_col, pros_col, appts_col = collections()
        tenant_doc = tenants_col.find_one({"_id": tenant}, {"tz": 1})
        tz_name = (tenant_doc or {}).get("tz") or DEFAULT_TIMEZONE
        try:
            tz = ZoneInfo(tz_name)
        except Exception:
            tz = ZoneInfo(DEFAULT_TIMEZONE)

        now_local = dt.datetime.now(tz)
        target_date = date or now_local.date()
        target_date_str = target_date.isoformat()

        update_payload: Dict[str, Any] = {
            "updated_at": utcnow(),
            "updated_by": user_id,
        }

        if target_date == now_local.date():
            pros_col.update_one(
                {"tenant": tenant, "name": professional, "slots.time": time},
                {"$set": {"slots.$.status": status, **update_payload}},
            )

        prof_doc = pros_col.find_one({"tenant": tenant, "name": professional})
        if not prof_doc:
            return

        overrides = prof_doc.get("date_overrides") or {}
        day_slots = overrides.get(target_date_str)

        if day_slots is None:
            global_slots = prof_doc.get("slots") or []
            day_slots = [dict(s) for s in global_slots]

        found = False
        for s in day_slots:
            if s.get("time") == time:
                s["status"] = status
                found = True
                break

        if not found:
            day_slots.append({"time": time, "status": status})

        pros_col.update_one(
            {"tenant": tenant, "name": professional},
            {"$set": {f"date_overrides.{target_date_str}": day_slots, **update_payload}},
        )

    @classmethod
    def _set_slot_status_if_today(
        cls,
        tenant: str,
        professional: str,
        time: str,
        status: str,
        date: Optional[dt.date] = None,
    ) -> None:
        cls._set_slot_status(tenant, professional, time, status, date=date)

    @classmethod
    def _free_slot_if_today(cls, tenant: str, appt_doc: Dict[str, Any]) -> None:
        tenants_col, pros_col, appts_col = collections()
        tenant_doc = tenants_col.find_one({"_id": tenant}, {"tz": 1})
        tz_name = (tenant_doc or {}).get("tz") or DEFAULT_TIMEZONE
        try:
            tz = ZoneInfo(tz_name)
        except Exception:
            tz = ZoneInfo(DEFAULT_TIMEZONE)

        now_local = dt.datetime.now(tz)
        is_today = (
            appt_doc.get("start")
            and appt_doc.get("start").astimezone(tz).date() == now_local.date()
        )

        if is_today:
            pros_col.update_one(
                {
                    "tenant": tenant,
                    "name": appt_doc.get("professional"),
                    "slots.time": appt_doc.get("time"),
                },
                {"$set": {"slots.$.status": SLOT_STATUS_AVAILABLE}},
            )

    @classmethod
    def reschedule_appointment(
        cls,
        tenant: str,
        appt_id: str,
        new_time: str,
        new_date_str: Optional[str] = None,
        user_id: Optional[str] = None,
        old_date: Optional[dt.date] = None,
        mark_old_as_available: bool = False,
    ) -> Appointment:
        tenants_col, pros_col, appts_col = collections()

        query = {"tenant": tenant, "id": appt_id}
        if old_date:
            start_of_day = dt.datetime.combine(old_date, dt.time.min)
            end_of_day = dt.datetime.combine(old_date, dt.time.max)
            query["start"] = {"$gte": start_of_day, "$lte": end_of_day}

        doc = appts_col.find_one(query)
        if not doc:
            raise ValueError("Appointment not found")

        tenant_doc = tenants_col.find_one({"_id": tenant}, {"tz": 1})
        tz_name = (tenant_doc or {}).get("tz") or DEFAULT_TIMEZONE
        try:
            tz = ZoneInfo(tz_name)
        except Exception:
            tz = ZoneInfo(DEFAULT_TIMEZONE)

        old_status = SLOT_STATUS_AVAILABLE if mark_old_as_available else "blocked"
        cls._set_slot_status(
            tenant,
            doc.get("professional"),
            doc.get("time"),
            old_status,
            date=doc.get("start").astimezone(tz).date() if doc.get("start") else None,
            user_id=user_id,
        )

        settings = cls.get_tenant_settings(tenant) or {}
        appt_settings = (settings.get("appointments") or {}) if isinstance(settings, dict) else {}
        slot_duration = int(appt_settings.get("slot_duration_minutes", 30) or 30)
        tz_name = str(appt_settings.get("timezone") or settings.get("tz") or DEFAULT_TIMEZONE)
        try:
            tz = ZoneInfo(tz_name)
        except Exception:
            tz = ZoneInfo(DEFAULT_TIMEZONE)

        if new_date_str:
            try:
                d = dt.date.fromisoformat(new_date_str)
            except Exception:
                raise ValueError("Invalid date_str. Use YYYY-MM-DD.")
        else:
            d = dt.datetime.now(tz).date()

        try:
            hh, mm = [int(x) for x in new_time.split(":", 1)]
            start_local = dt.datetime(d.year, d.month, d.day, hh, mm, tzinfo=tz)
            end_local = start_local + dt.timedelta(minutes=slot_duration)
        except Exception:
            raise ValueError("Invalid time format. Use HH:MM.")

        professional = doc.get("professional")
        prof_doc = pros_col.find_one(
            {"tenant": tenant, "name": professional}, {"active": 1, "capacity": 1}
        )
        if not prof_doc:
            raise ValueError("Professional not found")

        cap = int(prof_doc.get("capacity", 1) or 1)

        prof_doc_full = pros_col.find_one(
            {"tenant": tenant, "name": professional}, {"date_overrides": 1}
        )
        overrides = (prof_doc_full.get("date_overrides") or {}) if prof_doc_full else {}
        target_date_str = d.isoformat()
        day_slots = overrides.get(target_date_str) or []
        target_slot = next((s for s in day_slots if s.get("time") == new_time), None)
        if target_slot and target_slot.get("status") == "blocked":
            raise ValueError("Slot is blocked and cannot be booked")

        overlaps = cls.count_appointments_overlapping(
            tenant=tenant,
            professional=professional,
            start_iso=start_local.isoformat(),
            end_iso=end_local.isoformat(),
            exclude_appt_id=appt_id,
        )
        if overlaps >= cap:
            raise ValueError("New slot already booked (capacity reached)")

        is_today = d == dt.datetime.now(tz).date()
        if is_today:
            res_upd = pros_col.update_one(
                {
                    "tenant": tenant,
                    "name": professional,
                    "slots": {"$elemMatch": {"time": new_time, "status": SLOT_STATUS_AVAILABLE}},
                },
                {"$set": {"slots.$.status": "booked"}},
            )
            if res_upd.modified_count == 0:
                prof_now = pros_col.find_one({"tenant": tenant, "name": professional})
                target_slot = next(
                    (s for s in prof_now.get("slots", []) if s.get("time") == new_time), None
                )
                if target_slot and target_slot.get("status") == "blocked":
                    raise ValueError("Slot is blocked and cannot be booked")

        res = appts_col.find_one_and_update(
            {"_id": doc["_id"]},
            {
                "$set": {
                    "time": new_time,
                    "start": start_local,
                    "end": end_local,
                    "status": "booked",
                    "rescheduled_at": utcnow(),
                    "updated_at": utcnow(),
                    "updated_by": user_id,
                },
                "$push": {
                    "history": {
                        "action": "rescheduled",
                        "old_time": doc.get("time"),
                        "old_start": doc.get("start"),
                        "new_time": new_time,
                        "new_start": start_local,
                        "at": utcnow(),
                        "by": user_id,
                    }
                },
            },
            return_document=ReturnDocument.BEFORE,
        )

        if res and res.get("status") == "completed":
            price = float(res.get("price") or 0.0)
            tenants_col.update_one({"_id": tenant}, {"$inc": {"revenue": -price}})

        res = appts_col.find_one({"tenant": tenant, "id": appt_id})

        return Appointment(
            id=res["id"],
            customer_name=res.get("customer_name", ""),
            customer_phone=res.get("customer_phone", ""),
            professional=res.get("professional", ""),
            time=res.get("time", ""),
            price=float(res.get("price", 0.0)),
            status=res.get("status", "booked"),
            created_at=res.get("created_at", utcnow()),
            created_by=res.get("created_by"),
            updated_at=res.get("updated_at"),
            updated_by=res.get("updated_by"),
            start=res.get("start"),
            end=res.get("end"),
        )

    @classmethod
    def count_appointments_overlapping(
        cls,
        tenant: str,
        professional: str,
        start_iso: str,
        end_iso: str,
        exclude_appt_id: Optional[str] = None,
    ) -> int:
        """Count non-canceled appointments overlapping [start, end) for a professional.

        Overlap condition: appt.start < end AND appt.end > start
        """
        if not tenant or not professional:
            return 0
        try:
            start_dt = dt.datetime.fromisoformat(start_iso.replace("Z", "+00:00"))
            end_dt = dt.datetime.fromisoformat(end_iso.replace("Z", "+00:00"))
        except Exception:
            return 0
        db = get_db()
        col = db.get_collection("appointments")
        q = {
            "tenant": tenant,
            "professional": professional,
            "status": {"$ne": "canceled"},
            "start": {"$lt": end_dt},
            "end": {"$gt": start_dt},
        }
        if exclude_appt_id:
            q["id"] = {"$ne": exclude_appt_id}
        try:
            return int(col.count_documents(q))
        except Exception:
            return 0
