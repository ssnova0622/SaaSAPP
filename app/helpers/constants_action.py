from __future__ import annotations

# Core
OPEN_TICKET = "open_ticket"
OPEN_URL = "open_url"
API_CALL = "api_call"
ASK_NAME = "ask_name"
SUBMIT_FEEDBACK = "submit_feedback"
COLLECT_PATIENT_INFO_ALIAS="collect_patient_info"
COLLECT_DETAILS="collect_details"

# Salon
SELECT_TIMESLOT = "select_timeslot"
BOOK_EXPRESS = "book_express"
BOOK_APPOINTMENT = "book_appointment"
CANCEL_APPOINTMENT = "cancel_appointment"
RESCHEDULE_APPOINTMENT = "reschedule_appointment"
SHOW_SERVICES = "show_services"
SHOW_SERVICE_PRICES = "show_service_prices"
SHOW_PROFESSIONALS = "show_professionals"
SUGGEST_PROFESSIONAL = "suggest_professional"
PROFESSIONAL_DETAILS = "professional_details"
TEST_API = "test_api"
BOOKING_SUMMARY = "booking_summary"
CONFIRM_PROMPT ="confirm_prompt"
CONFIRM_BOOKING = "confirm_booking"
FINALIZE_BOOKING = "finalize_booking"
SELECT_DATE="select_date"
SELECT_TIME="select_time"
AUTO_ASSIGN_TIME="auto_assign_time"
# Silently pre-selects a professional configured in step.params["professional"]
# (no user interaction). Use in workflows where the staff member is fixed or
# when the tenant does not expose professional selection to customers.
PRESET_PROFESSIONAL = "preset_professional"
# Asks how long to book (duration options derived from service window + default duration).
# Stores num_slots + slot_duration_minutes (+ total_duration_minutes) in flow_data.
# SELECT_TIME uses these to compute end_time.
# Optional step.params: max_booking_window_minutes, max_options, customer_requested_duration
ASK_NUM_SLOTS = "ask_num_slots"
END= "end"

# Clinic
CHECK_DOCTOR = "check_doctor"
LIST_DOCTORS = "list_doctors"
BOOK_DOCTOR = "book_doctor"

# AI (workflow)
AI_FREE_TEXT = "ai_free_text"

# Store
BROWSE_CATALOG = "browse_catalog"
CHECK_PRODUCT = "check_product"
CHECK_PRICE = "check_price"
TRACK_ORDER = "track_order"
VIEW_OFFERS = "view_offers"
VIEW_PRODUCTS = "view_products"
