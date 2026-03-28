# services/ai/modules/professionals.py
import datetime as dt
from typing import Dict, List, Any, Optional
from app.helpers.date_utils import resolve_date_window
from app.helpers.tools import to_float
from app.services.ai.helpers.config import AI_DEFAULTS


class ProfessionalsService:
    """
    Provides professional analytics:
    - Performance metrics
    - Slot availability
    - Slot recommendations
    """

    def __init__(self, appt_repo):
        """
        Args:
            appt_repo: AppointmentRepository
        """
        self.appt_repo = appt_repo

    # ----------------------------------------------------------------------
    # PROFESSIONAL PERFORMANCE
    # ----------------------------------------------------------------------

    def professional_performance(
            self,
            tenant: str,
            days: int = None,
            from_date: dt.date = None,
            to_date: dt.date = None,
    ) -> List[Dict[str, Any]]:
        """
        Return performance metrics per professional.
        """
        if not tenant:
            raise ValueError("tenant is required")

        cfg = AI_DEFAULTS["professionals"]

        window_start, window_end, _ = resolve_date_window(
            days or cfg["days"],
            from_date,
            to_date,
        )

        agg: Dict[str, Dict[str, Any]] = {}

        cursor = self.appt_repo.get_collection().find(
            {
                "tenant": tenant,
                "created_at": {"$gte": window_start, "$lte": window_end},
            },
            {"professional": 1, "status": 1, "price": 1},
        )

        for doc in cursor:
            professional = str(doc.get("professional") or "Unknown")
            status = str(doc.get("status") or "")
            price = to_float(doc.get("price"))

            row = agg.setdefault(
                professional,
                {
                    "professional": professional,
                    "appointments": 0,
                    "completed": 0,
                    "revenue": 0.0,
                    "canceled": 0,
                },
            )

            row["appointments"] += 1

            if status == "completed":
                row["completed"] += 1
                row["revenue"] += price
            elif status == "canceled":
                row["canceled"] += 1

        results = list(agg.values())

        for r in results:
            r["revenue"] = round(r["revenue"], 2)

        results.sort(key=lambda x: (-x["revenue"], -x["completed"]))

        return results

    # ----------------------------------------------------------------------
    # SLOT AVAILABILITY (ASYNC)
    # ----------------------------------------------------------------------

    async def list_available_slots_for_first_professional(
            self,
            tenant: str,
    ) -> List[Dict[str, Any]]:
        """
        Return available slots for the first professional.
        """
        from app.services.salon.professional_service import ProfessionalService
        from app.services.salon.slot_service import SlotService

        pros = ProfessionalService.get_professionals(tenant)
        if not pros:
            return []

        today = dt.date.today().isoformat()
        tomorrow = (dt.date.today() + dt.timedelta(days=1)).isoformat()

        return await SlotService.get_availability(
            tenant=tenant,
            professional=pros[0].name,
            from_date=today,
            to_date=tomorrow,
            channel="admin",
        )

    # ----------------------------------------------------------------------
    # SLOT TIMES FOR SPECIFIC PROFESSIONAL (ASYNC)
    # ----------------------------------------------------------------------

    async def list_times_for_professional_label(
            self,
            tenant: str,
            professional: str,
            limit: int = 10,
    ) -> List[str]:
        """
        Return bookable times for a specific professional.
        """
        from app.services.salon.slot_service import SlotService

        today = dt.date.today().isoformat()
        tomorrow = (dt.date.today() + dt.timedelta(days=1)).isoformat()

        items = await SlotService.get_availability(
            tenant=tenant,
            professional=professional,
            from_date=today,
            to_date=tomorrow,
            channel="admin",
        )

        return [i["time"] for i in items if i.get("bookable")][:limit]

    # ----------------------------------------------------------------------
    # SLOT RECOMMENDATIONS (ASYNC)
    # ----------------------------------------------------------------------

    async def recommend_slots(
            self,
            tenant: str,
            professional: Optional[str] = None,
            top: int = 3,
    ) -> List[Dict[str, Any]]:
        """
        Recommend top slots for a professional.
        """
        if professional:
            slots = await self.list_times_for_professional_label(
                tenant,
                professional,
                limit=top,
            )
            return [{"time": s, "score": 0.9} for s in slots]

        return []
