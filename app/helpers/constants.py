# app/helpers/constants.py
"""
Application-wide constants (timezone, date formats, appointment/slot statuses).
Use these instead of hardcoding. For capability/role constants see constants_capabilities, constants_roles.
"""
from __future__ import annotations

# -----------------------------------------------------------------------------
# Timezone & locale
# -----------------------------------------------------------------------------
DEFAULT_TIMEZONE = "Asia/Kolkata"
DEFAULT_DISPLAY_DATE_FORMAT = "DD/MM/YYYY"
ISO_DATE_FORMAT = "YYYY-MM-DD"
DISPLAY_DATE_FORMAT_STRFTIME = {
    "DD/MM/YYYY": "%d/%m/%Y",
    "DD-MM-YYYY": "%d-%m-%Y",
    "MM/DD/YYYY": "%m/%d/%Y",
    "YYYY-MM-DD": "%Y-%m-%d",
}

# -----------------------------------------------------------------------------
# Appointment statuses
# -----------------------------------------------------------------------------
APPOINTMENT_STATUS_BOOKED = "booked"
APPOINTMENT_STATUS_CANCELED = "canceled"
APPOINTMENT_STATUS_COMPLETED = "completed"
APPOINTMENT_STATUS_NEEDS_RESCHEDULE = "needs_reschedule"
APPOINTMENT_STATUS_NO_SHOW = "no_show"
APPOINTMENT_STATUS_BLOCKED = "blocked"

# -----------------------------------------------------------------------------
# Slot statuses
# -----------------------------------------------------------------------------
SLOT_STATUS_AVAILABLE = "available"
SLOT_STATUS_BLOCKED = "blocked"
SLOT_STATUS_BOOKED = "booked"
SLOT_STATUS_COMPLETED = "completed"

BOOKED = "booked"

# -----------------------------------------------------------------------------
# User statuses
# -----------------------------------------------------------------------------
USER_STATUS_ACTIVE = "active"
USER_STATUS_DISABLED = "disabled"

# -----------------------------------------------------------------------------
# Workflow / generic active flag (for workflow.active, tenant.active, etc.)
# -----------------------------------------------------------------------------
STATUS_ACTIVE = "active"
STATUS_INACTIVE = "inactive"


FLOW_MODE_SELECT_SERVICE = "select_service"
FLOW_MODE_SELECT_DATE = "select_date"
FLOW_MODE_SELECT_PROF_NEW = "select_prof_new"
FLOW_MODE_SELECT_SLOT = "select_slot"
FLOW_MODE_CONFIRM_BOOKING = "confirm_booking"
FLOW_MODE_ASK_NAME = "ask_name"
FLOW_MODE_RETURNING_CHOICE = "returning_choice"
FLOW_MODE_WAIT_REMINDER = "wait_reminder"
FLOW_MODE_CANCEL_SELECTION = "cancel_selection"

FLOW_MODES_EXPECTING_INPUT = (
    FLOW_MODE_SELECT_SERVICE,
    FLOW_MODE_SELECT_DATE,
    FLOW_MODE_SELECT_PROF_NEW,
    FLOW_MODE_SELECT_SLOT,
    FLOW_MODE_CONFIRM_BOOKING,
    FLOW_MODE_ASK_NAME,
    FLOW_MODE_RETURNING_CHOICE,
    FLOW_MODE_WAIT_REMINDER,
    FLOW_MODE_CANCEL_SELECTION,
)

