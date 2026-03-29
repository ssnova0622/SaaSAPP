"""Retention metrics (segments from appointments); used by routers and cron."""

from .retention import (
    aggregate_and_store_for_all_tenants,
    compute_segments_for_tenant,
    get_summary,
    list_by_segment,
)

__all__ = [
    "aggregate_and_store_for_all_tenants",
    "compute_segments_for_tenant",
    "get_summary",
    "list_by_segment",
]
