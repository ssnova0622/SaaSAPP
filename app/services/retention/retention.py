"""
Retention metrics API + cron entrypoints.

Implementation lives in :mod:`app.services.core.retention_service` (tenant-aware thresholds,
``customer_phone_number`` / legacy ``customer_phone`` grouping). This module re-exports the same
functions so routers and cron keep a stable import path.
"""
from __future__ import annotations

from app.services.core import retention_service as _core

aggregate_and_store_for_all_tenants = _core.aggregate_and_store_for_all_tenants
compute_segments_for_tenant = _core.compute_segments_for_tenant
get_summary = _core.get_summary
list_by_segment = _core.list_by_segment

__all__ = [
    "aggregate_and_store_for_all_tenants",
    "compute_segments_for_tenant",
    "get_summary",
    "list_by_segment",
]
