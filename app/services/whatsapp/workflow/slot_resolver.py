"""
Multi-tenant appointment slot resolver.

Priority order (always enforced):
  1. Professional slot time   — stylist/doctor/trainer configured slots
  2. Workflow default time    — step.params time_slots / start_hour / end_hour
  3. Service duration time      — service catalogue start_time/end_time + duration (no professional)
  4. Auto-adjust next time      — snap overflow selections to next valid slot in window

Used by WhatsApp SELECT_TIME and any future booking channels.
"""
from __future__ import annotations

import datetime as dt
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Set, Tuple

from app.core.container import get_tenant_service
from app.models.workflow import WorkflowStep


class SlotSource(str, Enum):
    PROFESSIONAL = "professional"
    WORKFLOW_DEFAULT = "workflow_default"
    SERVICE_DURATION = "service_duration"


@dataclass
class SlotResolutionResult:
    slots: List[str]
    source: SlotSource
    slot_duration_min: int
    professional: Optional[str] = None
    workflow_window: Tuple[Optional[str], Optional[str]] = (None, None)  # (start_hhmm, end_hhmm)


@dataclass
class SlotResolutionContext:
    tenant: str
    step: WorkflowStep
    session: Dict[str, Any]
    professional: Optional[str]
    service_name: Optional[str]
    date_str: str
    has_professional_step: bool
    slot_duration_min: int
    num_slots: int = 1
    total_duration_min: int = 0


# ---------------------------------------------------------------------------
# Time helpers
# ---------------------------------------------------------------------------

def _parse_hhmm(value: str) -> Optional[int]:
    """Parse 'HH:MM' → minutes from midnight, or None."""
    if not value or ":" not in str(value):
        return None
    try:
        parts = str(value).strip().split(":")
        return int(parts[0]) * 60 + int(parts[1])
    except (ValueError, IndexError):
        return None


def _fmt_hhmm(minutes: int) -> str:
    h, m = divmod(max(0, minutes), 60)
    return f"{h:02d}:{m:02d}"


def _load_tenant_settings(tenant: str) -> Dict[str, Any]:
    try:
        return get_tenant_service().get_tenant_settings(tenant) or {}
    except Exception:
        return {}


def _load_service(tenant: str, service_name: Optional[str]) -> Optional[Dict[str, Any]]:
    if not service_name:
        return None
    try:
        from app.services.storage_mongo import Storage
        target = service_name.strip().lower()
        for svc in Storage.list_services(tenant) or []:
            if str(svc.get("name") or "").strip().lower() == target:
                return svc
    except Exception:
        pass
    return None


def resolve_slot_duration(tenant: str, step: WorkflowStep, service_name: Optional[str] = None) -> int:
    """Duration in minutes: step param → service.duration → tenant default → 60."""
    params = dict(step.params or {})

    explicit = params.get("slot_duration_minutes") or params.get("slot_duration")
    if explicit:
        try:
            return max(1, int(explicit))
        except (ValueError, TypeError):
            pass

    svc = _load_service(tenant, service_name)
    if svc:
        dur = int(svc.get("duration") or 0)
        if dur > 0:
            return dur

    settings = _load_tenant_settings(tenant)
    tenant_dur = int((settings.get("appointments") or {}).get("slot_duration_minutes") or 0)
    if tenant_dur > 0:
        return tenant_dur

    return 60


def _flow_data(session: Dict[str, Any]) -> Dict[str, Any]:
    ctx = session.get("ctx") if isinstance(session, dict) else None
    if not isinstance(ctx, dict):
        return {}
    fd = ctx.get("flow_data")
    return fd if isinstance(fd, dict) else {}


def resolve_booking_duration(
    tenant: str,
    step: WorkflowStep,
    session: Dict[str, Any],
    service_name: Optional[str] = None,
) -> Tuple[int, int, int]:
    """
    Return (slot_duration_min, num_slots, total_duration_minutes).

  Priority: flow_data from ASK_NUM_SLOTS → step.params → service/tenant default.
    """
    flow = _flow_data(session)
    params = dict(step.params or {})
    default = resolve_slot_duration(tenant, step, service_name)

    slot_dur = int(flow.get("slot_duration_minutes") or 0) or default
    num_slots = int(flow.get("num_slots") or 0)
    total = int(flow.get("total_duration_minutes") or 0)

    if total > 0:
        return slot_dur, max(1, num_slots or 1), total
    if num_slots > 1:
        return slot_dur, num_slots, num_slots * slot_dur

    step_num = int(params.get("num_slots") or 1)
    if step_num > 1:
        return slot_dur, step_num, step_num * slot_dur
    return slot_dur, 1, slot_dur


def filter_slots_fitting_duration(
    slots: List[str],
    total_duration_min: int,
    window_end: Optional[str] = None,
) -> List[str]:
    """Drop start times where start + total_duration exceeds the bookable window end."""
    if not slots or total_duration_min <= 0:
        return slots
    end_m = _parse_hhmm(window_end) if window_end else None
    if end_m is None:
        return slots
    out: List[str] = []
    for t in slots:
        m = _parse_hhmm(t)
        if m is None:
            out.append(t)
            continue
        if m + total_duration_min <= end_m:
            out.append(t)
    return out


@dataclass
class DurationOption:
    """One bookable duration choice for ASK_NUM_SLOTS."""
    duration_minutes: int
    num_slots: int
    label: str
    is_default_multiple: bool = True


def format_duration_label(minutes: int) -> str:
    """Human-readable duration for WhatsApp menus."""
    minutes = max(1, int(minutes))
    if minutes < 60:
        return f"{minutes} mins"
    hours, rem = divmod(minutes, 60)
    if rem == 0:
        return "1 hour" if hours == 1 else f"{hours} hours"
    hour_part = "1 hour" if hours == 1 else f"{hours} hours"
    return f"{hour_part} {rem} mins"


def resolve_service_window(
    tenant: str,
    step: WorkflowStep,
    service_name: Optional[str],
) -> Tuple[int, int]:
    """Return (start_min, end_min) for the service / workflow bookable window."""
    params = dict(step.params or {})
    settings = _load_tenant_settings(tenant)
    svc = _load_service(tenant, service_name)

    start_min: Optional[int] = None
    end_min: Optional[int] = None

    if svc:
        st = str(svc.get("start_time") or "").strip()
        et = str(svc.get("end_time") or "").strip()
        if st:
            start_min = _parse_hhmm(st)
        if et:
            end_min = _parse_hhmm(et)

    if start_min is None or end_min is None:
        wf_start, wf_end = _workflow_window(params, settings)
        start_min = start_min if start_min is not None else wf_start
        end_min = end_min if end_min is not None else wf_end

    if end_min <= start_min:
        end_min = start_min + 60

    return start_min, end_min


def _cap_max_booking_window(params: Dict[str, Any], window_minutes: int) -> int:
    """Apply optional step-level cap on total bookable duration."""
    for key in ("max_booking_window_minutes", "max_duration_minutes", "max_booking_minutes"):
        raw = params.get(key)
        if raw is None:
            continue
        try:
            cap = max(1, int(raw))
            return min(window_minutes, cap)
        except (ValueError, TypeError):
            continue
    return window_minutes


def _parse_requested_duration(
    params: Dict[str, Any],
    flow: Optional[Dict[str, Any]] = None,
) -> Optional[int]:
    """Optional customer-requested duration from step params or prior flow answers."""
    for source in (flow or {}, params):
        for key in (
            "customer_requested_duration",
            "requested_duration",
            "duration_minutes",
        ):
            raw = source.get(key)
            if raw is None:
                continue
            try:
                val = int(raw)
                if val > 0:
                    return val
            except (ValueError, TypeError):
                continue
    return None


def generate_duration_options(
    tenant: str,
    step: WorkflowStep,
    service_name: Optional[str] = None,
    customer_requested_duration: Optional[int] = None,
    flow: Optional[Dict[str, Any]] = None,
) -> Tuple[List[DurationOption], int]:
    """
    Build ascending duration choices for ASK_NUM_SLOTS.

    Options are multiples of the service default duration that fit inside the
    service start/end window (capped by optional max_booking_window_minutes).
    """
    params = dict(step.params or {})
    default_duration = resolve_slot_duration(tenant, step, service_name)
    start_min, end_min = resolve_service_window(tenant, step, service_name)
    max_duration = _cap_max_booking_window(params, end_min - start_min)

    requested = customer_requested_duration
    if requested is None:
        requested = _parse_requested_duration(params, flow)

    durations: List[int] = []
    if default_duration > 0 and max_duration > 0:
        current = default_duration
        while current <= max_duration:
            durations.append(current)
            current += default_duration
    elif default_duration > 0:
        durations = [default_duration]

    if not durations and max_duration > 0:
        durations = [max_duration]
    elif default_duration > max_duration > 0:
        durations = [max_duration]

    if requested and requested > 0 and requested <= max_duration:
        if requested not in durations:
            durations.append(requested)

    durations = sorted({d for d in durations if d > 0})

    max_options = int(params.get("max_options") or 0)
    if max_options <= 0:
        # Deprecated alias — limits how many duration choices are shown, not slots booked.
        max_options = int(params.get("max_slots") or 0)
    if max_options > 0:
        durations = durations[:max_options]

    options: List[DurationOption] = []
    for dur in durations:
        if dur % default_duration == 0:
            options.append(DurationOption(
                duration_minutes=dur,
                num_slots=max(1, dur // default_duration),
                label=format_duration_label(dur),
                is_default_multiple=True,
            ))
        else:
            options.append(DurationOption(
                duration_minutes=dur,
                num_slots=1,
                label=format_duration_label(dur),
                is_default_multiple=False,
            ))

    return options, default_duration


# ---------------------------------------------------------------------------
# Slot generators
# ---------------------------------------------------------------------------

def _workflow_window(params: Dict[str, Any], settings: Dict[str, Any]) -> Tuple[int, int]:
    """Return (start_min, end_min) for workflow window."""
    appt = settings.get("appointments") or {}
    if not isinstance(appt, dict):
        appt = {}
    start_h = int(
        params.get("start_hour")
        or settings.get("business_start_hour")
        or appt.get("business_start_hour")
        or 9
    )
    end_h = int(
        params.get("end_hour")
        or settings.get("business_end_hour")
        or appt.get("business_end_hour")
        or 17
    )
    return start_h * 60, end_h * 60


def generate_workflow_default_slots(
    tenant: str,
    step: WorkflowStep,
    slot_duration_min: int,
) -> Tuple[List[str], Tuple[Optional[str], Optional[str]]]:
    """
    Priority-2: workflow step params.

    Sources (in order):
      1. step.params.time_slots (explicit list)
      2. start_hour / end_hour + slot_interval_minutes
      3. tenant business hours
    """
    params = dict(step.params or {})
    settings = _load_tenant_settings(tenant)

    explicit = params.get("time_slots") or []
    if isinstance(explicit, list) and explicit:
        slots = [str(t).strip() for t in explicit if str(t).strip()]
        window = (slots[0], slots[-1]) if slots else (None, None)
        return slots, window

    start_min, end_min = _workflow_window(params, settings)
    interval = int(params.get("slot_interval_minutes") or slot_duration_min)

    slots: List[str] = []
    current = start_min
    while current < end_min:
        slots.append(_fmt_hhmm(current))
        current += interval

    return slots, (_fmt_hhmm(start_min), _fmt_hhmm(end_min))


def generate_service_duration_slots(
    tenant: str,
    step: WorkflowStep,
    service_name: Optional[str],
    slot_duration_min: int,
) -> Tuple[List[str], Tuple[Optional[str], Optional[str]]]:
    """
    Priority-3: service catalogue start_time / end_time + duration interval.
    Used when workflow has NO professional step.
    """
    params = dict(step.params or {})

    # Explicit workflow list still wins within service mode
    explicit = params.get("time_slots") or []
    if isinstance(explicit, list) and explicit:
        slots = [str(t).strip() for t in explicit if str(t).strip()]
        return slots, (slots[0] if slots else None, slots[-1] if slots else None)

    start_min, end_min = resolve_service_window(tenant, step, service_name)
    interval = int(params.get("slot_interval_minutes") or slot_duration_min)

    slots: List[str] = []
    current = start_min
    while current < end_min:
        slots.append(_fmt_hhmm(current))
        current += interval

    if not slots:
        slots = ["09:00", "10:00", "11:00", "14:00", "15:00", "16:00"]

    return slots, (_fmt_hhmm(start_min), _fmt_hhmm(end_min))


def filter_slots_to_window(slots: List[str], window_start: Optional[str], window_end: Optional[str]) -> List[str]:
    """Keep only slots within [window_start, window_end)."""
    if not slots:
        return slots
    start_m = _parse_hhmm(window_start) if window_start else None
    end_m = _parse_hhmm(window_end) if window_end else None
    if start_m is None and end_m is None:
        return slots

    out: List[str] = []
    for t in slots:
        m = _parse_hhmm(t)
        if m is None:
            out.append(t)
            continue
        if start_m is not None and m < start_m:
            continue
        if end_m is not None and m >= end_m:
            continue
        out.append(t)
    return out


def intersect_with_workflow_list(prof_slots: List[str], workflow_slots: List[str]) -> List[str]:
    """
    Keep professional slots that appear in the workflow time list.
    If workflow list is empty, return all professional slots unchanged.
    """
    if not prof_slots:
        return []
    if not workflow_slots:
        return prof_slots
    wf_set: Set[str] = set(workflow_slots)
    matched = [s for s in prof_slots if s in wf_set]
    return matched


def auto_adjust_next_valid(
    selected: str,
    available_slots: List[str],
    window_end: Optional[str] = None,
) -> Optional[str]:
    """
    Priority-4: if *selected* exceeds the workflow window or is not bookable,
    return the next valid slot at or after *selected*, else None.
    """
    if not available_slots:
        return None

    sel_m = _parse_hhmm(selected)
    if sel_m is None:
        return available_slots[0] if available_slots else None

    end_m = _parse_hhmm(window_end) if window_end else None

    # Parse and sort available slots
    parsed: List[Tuple[int, str]] = []
    for t in available_slots:
        m = _parse_hhmm(t)
        if m is not None:
            parsed.append((m, t))
    parsed.sort(key=lambda x: x[0])

    for m, t in parsed:
        if end_m is not None and m >= end_m:
            break
        if m >= sel_m:
            return t

    # Selected past window — return last valid slot before end
    if end_m is not None:
        for m, t in reversed(parsed):
            if m < end_m:
                return t

    return parsed[-1][1] if parsed else None


def dedupe_sorted(slots: List[str]) -> List[str]:
    seen: Set[str] = set()
    parsed: List[Tuple[int, str]] = []
    for t in slots:
        if t in seen:
            continue
        m = _parse_hhmm(t)
        if m is not None:
            seen.add(t)
            parsed.append((m, t))
    parsed.sort(key=lambda x: x[0])
    return [t for _, t in parsed]


# ---------------------------------------------------------------------------
# Main resolver
# ---------------------------------------------------------------------------

async def resolve_available_slots(
    ctx: SlotResolutionContext,
    fetch_professional_slots,
) -> SlotResolutionResult:
    """
    Resolve bookable slot list following the 4-level priority rules.

    ``fetch_professional_slots`` is an async callable:
        (tenant, professional_name, date_str) -> List[str]
    """
    from app.services.whatsapp.helpers import constants as WMSG

    params = dict(ctx.step.params or {})
    settings = _load_tenant_settings(ctx.tenant)

    prof = ctx.professional
    is_real_prof = bool(
        prof
        and prof not in (WMSG.PROF_SENTINEL_NO_PROF, WMSG.LABEL_AUTO_ASSIGNED, "Auto-assigned")
    )

    workflow_slots, workflow_window = generate_workflow_default_slots(
        ctx.tenant, ctx.step, ctx.slot_duration_min
    )

    # ── No professional step → service-duration slots (priority 3) ──────────
    if not ctx.has_professional_step or not is_real_prof:
        service_slots, svc_window = generate_service_duration_slots(
            ctx.tenant, ctx.step, ctx.service_name, ctx.slot_duration_min
        )
        slots = dedupe_sorted(service_slots)
        slots = filter_slots_to_window(slots, svc_window[0], svc_window[1])
        return SlotResolutionResult(
            slots=slots,
            source=SlotSource.SERVICE_DURATION,
            slot_duration_min=ctx.slot_duration_min,
            professional=prof,
            workflow_window=svc_window,
        )

    # ── Professional step → priority 1 then 2 ───────────────────────────────
    prof_slots: List[str] = []
    if prof:
        try:
            prof_slots = await fetch_professional_slots(ctx.tenant, prof, ctx.date_str) or []
        except Exception:
            prof_slots = []

    prof_slots = dedupe_sorted(prof_slots)
    workflow_slots = dedupe_sorted(workflow_slots)

    if prof_slots:
        # Professional has slots — use them if they fit the workflow window/list
        in_list = intersect_with_workflow_list(prof_slots, workflow_slots)
        in_window = filter_slots_to_window(prof_slots, workflow_window[0], workflow_window[1])

        if workflow_slots and in_list:
            final_slots = in_list
            source = SlotSource.PROFESSIONAL
        elif in_window:
            final_slots = in_window
            source = SlotSource.PROFESSIONAL
        elif workflow_slots:
            # Professional times not in workflow list → fallback to workflow default
            final_slots = workflow_slots
            source = SlotSource.WORKFLOW_DEFAULT
        else:
            final_slots = prof_slots
            source = SlotSource.PROFESSIONAL

        return SlotResolutionResult(
            slots=final_slots,
            source=source,
            slot_duration_min=ctx.slot_duration_min,
            professional=prof,
            workflow_window=workflow_window,
        )

    # No professional slots → workflow default (priority 2)
    final = filter_slots_to_window(workflow_slots, workflow_window[0], workflow_window[1])
    return SlotResolutionResult(
        slots=final,
        source=SlotSource.WORKFLOW_DEFAULT,
        slot_duration_min=ctx.slot_duration_min,
        professional=prof,
        workflow_window=workflow_window,
    )


def build_resolution_context(
    tenant: str,
    step: WorkflowStep,
    session: Dict[str, Any],
    professional: Optional[str],
    service_name: Optional[str],
    date_str: str,
    has_professional_step: bool,
) -> SlotResolutionContext:
    slot_dur, num_slots, total_dur = resolve_booking_duration(
        tenant, step, session, service_name
    )
    return SlotResolutionContext(
        tenant=tenant,
        step=step,
        session=session,
        professional=professional,
        service_name=service_name,
        date_str=date_str,
        has_professional_step=has_professional_step,
        slot_duration_min=slot_dur,
        num_slots=num_slots,
        total_duration_min=total_dur,
    )
