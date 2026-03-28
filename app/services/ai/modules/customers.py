# services/ai/modules/customers.py
import datetime as dt
from typing import Dict, List, Any
from app.helpers.date_utils import resolve_date_window, utcnow
from app.services.ai.helpers.config import AI_DEFAULTS


class CustomersService:
    """
    Provides customer analytics:
    - New vs returning customers timeseries
    """

    def __init__(self, customer_repo, order_repo):
        """
        Args:
            customer_repo: CustomerRepository
            order_repo: OrderRepository
        """
        self.customer_repo = customer_repo
        self.order_repo = order_repo

    # ----------------------------------------------------------------------
    # CUSTOMERS TIMESERIES
    # ----------------------------------------------------------------------

    def customers_timeseries(
            self,
            tenant: str,
            days: int = None,
            from_date: dt.date = None,
            to_date: dt.date = None,
    ) -> List[Dict[str, Any]]:
        """
        Return daily new vs returning customers.
        """
        if not tenant:
            raise ValueError("tenant is required")

        cfg = AI_DEFAULTS["customers"]

        # Resolve date window
        window_start, window_end, days_diff = resolve_date_window(
            days or cfg["days"],
            from_date,
            to_date,
        )

        # Build map of phone → first_seen_date
        first_seen: Dict[str, dt.datetime] = {}

        try:
            for c in self.customer_repo.get_collection().find(
                    {"tenant": tenant},
                    {"phone": 1, "created_at": 1},
            ):
                phone = str(c.get("phone") or "").strip()
                if not phone:
                    continue
                first_seen[phone] = c.get("created_at") or utcnow()
        except Exception:
            first_seen = {}

        # Aggregate per day
        buckets: Dict[str, Dict[str, int]] = {}

        cursor = self.order_repo.get_collection().find(
            {
                "tenant": tenant,
                "created_at": {"$gte": window_start, "$lte": window_end},
            },
            {"created_at": 1, "customer": 1},
        )

        for doc in cursor:
            created = doc.get("created_at") or utcnow()
            key = created.date().isoformat()

            bucket = buckets.setdefault(
                key,
                {"new_customers": 0, "returning_customers": 0},
            )

            cust = doc.get("customer") or {}
            phone = str(
                cust.get("phone") or cust.get("customer_phone") or ""
            ).strip()

            if phone and phone in first_seen:
                if first_seen[phone].date() == created.date():
                    bucket["new_customers"] += 1
                else:
                    bucket["returning_customers"] += 1
            else:
                bucket["new_customers"] += 1

        # Build output timeseries
        out: List[Dict[str, Any]] = []
        end_date = to_date or utcnow().date()

        for i in range(days_diff, -1, -1):
            d = (end_date - dt.timedelta(days=i)).isoformat()
            b = buckets.get(d) or {
                "new_customers": 0,
                "returning_customers": 0,
            }

            out.append({
                "date": d,
                "new_customers": int(b["new_customers"]),
                "returning_customers": int(b["returning_customers"]),
            })

        return out
