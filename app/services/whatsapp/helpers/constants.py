"""
WhatsApp-only constants: node ids, labels, prompts, messages, FSM keywords.
Use these instead of hardcoded strings in WhatsApp services.
Do not put other modules' constants or shared capability names here; those live in app.constants.
"""
from __future__ import annotations

# ----- Node / flow identifiers -----
NODE_ROOT = "root"
NODE_FSM = "fsm"
NODE_WORKFLOW = "workflow"
NODE_ERROR = "error"
WORKFLOW_PREFIX = "workflow."

# ----- Default / fallback labels -----
LABEL_NA = "N/A"
LABEL_OPTION = "Option"
LABEL_APPOINTMENT = "appointment"

# ----- Menu / submenu prompts -----
PROMPT_CHOOSE_OPTION = "Please choose an option."
PROMPT_CHOOSE_OPTION_FROM_MENU = "Please choose an option from the menu."
PROMPT_CHOOSE = "Please choose:"
REPLY_WITH_NUMBER = "Reply with a number."

# ----- Inbound / flow messages -----
MSG_TYPE_MENU_FOR_OPTIONS = "Type *menu* for options."
MSG_MENU_ERROR = "Menu error."
MSG_NO_PUBLISHED_MENU = (
    "No published WhatsApp menu found for this tenant. "
    "Please create and publish a menu in the Menu Editor first."
)
MSG_INVALID_SELECTION_RESTART = (
    "Invalid selection for the current step. Please try again or type 'menu' to restart."
)
MSG_THANK_YOU_FEEDBACK = "Thank you for your feedback! You can leave a review here: [Review Link]"
MSG_SOMETHING_WENT_WRONG = "Something went wrong. Type 'menu' to restart."

# ----- Booking / FSM -----
LABEL_AUTO_ASSIGNED = "Auto-assigned"
# Sentinel stored in flow_data when no professionals are configured for the tenant.
# SELECT_TIME detects this and shows business-hours slots instead of professional slots.
PROF_SENTINEL_NO_PROF = "__no_professional__"
BOOKING_SLOT_SKIP_ANYTIME = "Anytime"
BOOKING_NAME_INPUT_SKIP = "skip"
BOOKING_API_USER_ID = "WhatsApp"
BIZ_CATEGORY_SALON = "salon"
BIZ_CATEGORY_CLINIC = "clinic"
BIZ_CATEGORY_CAR_SHOWROOM = "car showroom"
FSM_BACK_KEYWORD = "back"
BOOKING_SERVICES_FALLBACK_SALON = ("Haircut", "Facial", "Nails", "Spa", "Hair Color")
BOOKING_SERVICES_FALLBACK_CLINIC = ("Consultation", "Dental Cleaning", "Skin Treatment")
BOOKING_SERVICES_FALLBACK_SHOWROOM = ("Test Drive", "Car Viewing", "Service Appointment")
MSG_SPECIALIST_LINE = "👤 Specialist: {prof}\n"
MSG_BOOKING_ERR_BLOCKED_SUBSTR = "Booking blocked"
MSG_BOOKING_ERR_NO_SHOW_SUBSTR = "too many no-shows"

MSG_SESSION_ERROR = "Session error. Please start again."
MSG_BOOKING_NOT_AVAILABLE = "Booking flow is not available."
MSG_BOOKING_FAILED_TRY_DATE = "Could not book: {err_msg}. Let's try another date."
MSG_BOOKING_SERVICE_PROMPT = "{prefix}Great! What service would you like to book?"
MSG_NEEDS_RESCHEDULE_INTRO = "You have an appointment ({appt_id}) that needs to be rescheduled.\n\n"
MSG_BOOKING_BLOCKED_NO_SHOWS = (
    "Sorry, booking from this number is currently not allowed due to repeated no-shows. "
    "Please contact the salon directly to resolve this."
)
MSG_PLEASE_CHOOSE_SERVICE = "Please choose a valid service by number."
MSG_PLEASE_CHOOSE_PROFESSIONAL = "Please choose a valid professional:"
MSG_PLEASE_CHOOSE_OPTION_SLOT = (
    "Please choose a valid option (1–{max}), or enter a preferred time (e.g. 6:30 PM, evening, after 4 evening, afternoon):"
)
MSG_DO_YOU_PREFER_STAFF = "Do you prefer a specific staff member?"
MSG_NO_AUTO_ASSIGN = "No, auto-assign best available"
MSG_WELCOME_BACK_BOOKING = "Welcome back, {name}! Is this booking for you or someone else?\n1) For me ({name})\n2) For someone else"
MSG_GOT_IT_CUSTOMER_NAME = "Got it. May I have the customer's name for this appointment?"
MSG_PLEASE_CHOOSE_FOR_ME = "Please choose:\n1) For me\n2) For someone else"
MSG_PERFECT_MAY_HAVE_NAME = "Perfect! May I have your name to confirm your appointment?"
MSG_OKAY_BOOKING_CANCELLED = "Okay, booking cancelled."
MSG_PLEASE_CONFIRM_BOOKING = "Please confirm your booking:\n1) Yes\n2) No"
MSG_OKAY_NOT_CANCELED = "Okay, I have not canceled your appointment."
MSG_OKAY_NOT_RESCHEDULED = "Okay, I have not rescheduled your appointment."
MSG_PLEASE_CONFIRM_CANCEL = "Please confirm:\n1) Yes, cancel\n2) No, keep it"
MSG_PLEASE_CONFIRM_RESCHEDULE = "Please confirm:\n1) Yes, reschedule\n2) No"
MSG_REPLY_NUMBER_CHOOSE_SLOT = "Reply with a number to choose a slot, or enter a preferred time (e.g. 6:30 PM, evening)."
MSG_REPLY_NUMBER_OR_ANOTHER_TIME = "Reply with a number to choose, or enter another time."
MSG_SEE_YOU_THEN = "See you then! 😊\nType *menu* when you need something."

# ----- Cancel / reschedule -----
MSG_APPOINTMENT_NOT_FOUND = "Appointment {id} not found."
MSG_INVALID_SELECTION_NUMBER = "Invalid selection. Please choose a number between 1 and {max} or say 'all'."
MSG_INVALID_SELECTION_RESCHEDULE = "Invalid selection. Please choose a number between 1 and {max}."
MSG_ARE_YOU_SURE_CANCEL = "Are you sure you want to cancel your appointment with {prof} at {time} on {date}?\n1) Yes\n2) No"
MSG_ARE_YOU_SURE_RESCHEDULE = "Are you sure you want to reschedule your appointment with {prof} at {time} on {date}?\n1) Yes\n2) No"
MSG_APPOINTMENT_CANCELED = "Appointment {id} {details} has been canceled."
MSG_ERROR_CANCELING = "Error canceling {id}: {err}"

# ----- Date / slot -----
MSG_INVALID_DATE_FORMAT = "Invalid date format. Please reply with 1, 2, or a date in format {fmt}."
MSG_DATE_IN_PAST = "The date {date} is in the past. Please choose a date today or in the future."
MSG_NO_PROFESSIONALS_DATE = "No professionals available on {date} for {service}. Please choose another date."
MSG_NO_SLOTS_ANY_PROFESSIONAL = "No slots available on {date} for any professional. Please choose another date."
MSG_NO_SLOTS_FOR_PROFESSIONAL = "No slots available for {prof} on {date}. Please choose another professional:"
MSG_NO_SLOTS_PROFESSIONAL_NOW = "No slots available for {prof} right now. Please choose another professional."
MSG_NO_SLOTS_NEAR_TIME = "No slots available near {time}. Please choose from the list below or enter another time:"
MSG_SLOTS_NEAR = "Slots near {time}:"
MSG_AVAILABLE_TIME_SLOTS = "Available time slots with {prof}:"
MSG_AVAILABLE_TIME_SLOTS_ON = "Available time slots with {prof} on {date}:"
MSG_CHOOSE_NEW_DATE = "Choose a new date for your appointment with {prof} (same professional):"
MSG_PLEASE_CHOOSE_DATE = "Please choose a date for your {service}:"
MSG_REQUESTED_SERVICE_FALLBACK = "the requested service"
MSG_DATE_ROW_TODAY = "1) Today ({display})"
MSG_DATE_ROW_TOMORROW = "2) Tomorrow ({display})"
MSG_DATE_ROW_OTHER = "3) Other date (Reply with {fmt})"
MSG_NO_SLOTS_PRO_OR_DATE = (
    "No slots available for {prof} on {date}. Please choose another professional or date."
)
MSG_REPLY_CHOOSE_SLOT_MULTILINE = (
    "\nReply with a number to choose a slot, or enter a preferred time (e.g. 6:30 PM, evening)."
)
MSG_RECOMMENDED_TIMES = "Recommended times: {times}"
MSG_RESCHEDULE_CONFIRM_FALLBACK = (
    "Confirm reschedule to {date} at {time} with {professional}?\n1) Yes\n2) No"
)
MSG_YOUR_SPECIALIST_FALLBACK = "your specialist"

# ----- Multi-appointment cancel / reschedule lists -----
MSG_MULTIPLE_APPOINTMENTS_CANCEL = "You have multiple appointments. Which one would you like to cancel?"
MSG_MULTIPLE_APPOINTMENTS_RESCHEDULE = "You have multiple appointments. Which one would you like to reschedule?"
MSG_APPOINTMENT_LIST_LINE = "{i}) {appt_id} - {prof} at {time} on {date}"
MSG_SUFFIX_REPLY_NUMBER_OR_ALL = "\nReply with a number or *all*."
MSG_SUFFIX_REPLY_NUMBER_OR_ALL_QUOTE = "\nReply with a number or 'all'."
MSG_SUFFIX_REPLY_NUMBER = "\nReply with a number."
MSG_CANCELLATION_RESULTS_HEADER = "Cancellation results:\n"
MSG_REPLY_CANCEL_LIST_OR_ALL = (
    "Please reply with a number from the list above, or say *all* to cancel every listed appointment."
)
MSG_REPLY_RESCHEDULE_LIST = "Please reply with a number from the rescheduling list above."
MSG_PHONE_NUMBER_REQUIRED = "Phone number required."
MSG_NO_ACTIVE_BOOKINGS_CANCEL = "No active bookings found to cancel."
MSG_NO_ACTIVE_BOOKINGS_RESCHEDULE = "No active bookings found to reschedule."
MSG_COULD_NOT_RESUME_CANCELLATION = "Could not resume cancellation. Please start again."
MSG_COULD_NOT_RESUME_RESCHEDULING = "Could not resume rescheduling. Please start again."
MSG_INVALID_SELECTION_STAR_ALL_RANGE = "Invalid selection. Choose 1–{max} or type *all*."
MSG_APPOINTMENT_NOT_FOUND_SHORT = "Appointment not found."
MSG_APPOINTMENT_ALREADY_STATUS = "Appointment {id} is already {status}."
MSG_ERROR_FINDING_APPOINTMENT = "Error finding appointment {id}."
LABEL_CUSTOMER_DEFAULT = "Customer"
LABEL_ITEM = "Item"
LABEL_OFFER = "Offer"

# ----- Appointment API user_id (non-display; avoids scattered literals) -----
APPOINTMENT_CANCEL_USER_ID_FSM = "AI-Bot"
APPOINTMENT_CANCEL_USER_ID_WORKFLOW = "whatsapp-workflow"

# ----- Shared appointment detail snippet (lists / ctx) -----
MSG_APPOINTMENT_COMPACT_DETAIL = "{prof} at {time} on {date}"

MSG_CANCEL_OK_EMOJI = "{id} ✅"
MSG_CANCEL_FAIL_EMOJI = "{id} ❌"
MSG_CANCEL_OK_PLAIN = "{id} ✓"
MSG_CANCEL_FAIL_PLAIN = "{id} ✘"
MSG_APPOINTMENT_DETAIL_WITH = "with {appt_details} for {cust_name}"
MSG_APPOINTMENT_DETAIL_FALLBACK = "with {prof} at {time_s} on {date_str} for {cust_name}"
MSG_BOOKING_CONFIRM_FALLBACK = (
    "Your appointment is confirmed, {customer_name}! 🎉\n"
    "📅 Date: {date}\n"
    "⏰ Time: {time}\n"
    "{service_line}"
    "📍 Location: {location}\n"
    "{specialist_line}"
)
MSG_BOOKING_SERVICE_LINE = "🏷️ Service: {service}\n"
MSG_DEFAULT_CUSTOMER_NAME = "WhatsApp User"
MSG_BUSINESS_ADDRESS_FALLBACK = "[Business Address]"
MSG_SALON_NO_PRO_MATCH = "I couldn't find any professionals matching your request."
MSG_SALON_NO_PRO_DETAILS = "I couldn't find details for that professional."
MSG_SALON_PRO_RECOMMEND_HEADER = "Here are some professionals I recommend:"
MSG_SALON_PRO_DETAIL_BLOCK = "Professional: {name}\nPrice: ₹{price}{slots}"
MSG_SALON_BOOK_APPOINTMENT_PROMPT = "Would you like to book an appointment?"
MSG_SALON_BOOKING_WITH_CUSTOM_SUFFIX = "{booking_msg}\n\n{custom}"
MSG_SALON_SUGGEST_PRO_BULLET = "- {name} (Price: ₹{price})"
MSG_SALON_BOOK_WITH_NAME_HINT = "\nYou can book with them by saying 'book with [name]'."
MSG_SALON_PRO_SLOTS_TODAY = "\nAvailable today: {slots}"
MSG_SALON_PRO_NO_SLOTS_TODAY = "\nNo slots available today."
MSG_STORE_PRODUCT_QUERY = (
    "What product are you looking for? Reply with the product name or keyword (e.g. milk, shampoo)."
)
MSG_STORE_PRODUCT_NOT_IN_CATALOG = "I couldn't find that product in our catalog."
MSG_PRO_PRODUCT_PROMPT = (
    "What product are you looking for? You can say e.g. 'cheap running shoes' or 'birthday cake'."
)
MSG_PRO_DELIVERY_INFO = (
    "Orders typically ship within 2-3 business days. Type your order number or *track* for status. "
    "Type *menu* for more options."
)
MSG_PRO_BUSINESS_HOURS = "Our business hours: Mon–Sat 9 AM–6 PM. Type *menu* for more."
MSG_PRO_CONTACT_SUPPORT = "Please contact support. Type *menu* for options."
MSG_PRO_HELP_GENERIC = (
    "How can we help? You can ask about *hours*, *contact*, or *refund policy*. "
    "Type *menu* for options."
)
MSG_PRO_NO_CATALOG_MATCH = (
    "We don't have a match for '{query}' right now. Type *menu* to browse or ask for something else."
)
MSG_PRO_OPTIONS_HEADER = "Here are some options:"
MSG_PRO_REFUND_DEFAULT = (
    "Our refund policy: You may request a refund within 30 days of purchase. "
    "Contact support for details. Type *menu* for more options."
)
MSG_PRO_DELIVERY_ETA_DAYS = (
    "Orders typically ship within {days} business days. Type *track* with your order number for status."
)
MSG_PRO_CONTACT_OWNER = "Contact us: {owner}. Type *menu* for more."
MSG_TIER_NL_FALLBACK = (
    "I didn't quite get that. You can ask about *refund*, *delivery*, *order status*, or *products*. "
    "Or type *menu* for options."
)
MSG_API_CALL_CONFIG_MISSING = "API call configuration missing: url"
MSG_API_ERROR = "API Error: {err}"
MSG_ACTION_EXECUTOR_NONE = "NONE"
MSG_CORE_API_EXAMPLE_URL = "https://example.com"

# ----- Workflow -----
WORKFLOW_COMPLETE_SENTINEL = "Workflow complete. Type 'menu' to start over."
WORKFLOW_END_MAIN_MENU = "__WORKFLOW_END_MAIN_MENU__"
MSG_THANK_YOU_TYPE_MAIN_MENU = "Thank you! Type anything to return to the main menu."

# ----- FSM exit / menu keywords -----
FSM_EXIT_KEYWORDS = ("exit", "quit", "stop", "cancel", "menu", "hi", "hello", "hey", "options", "start")
FSM_WAIT_REMINDER_KEYWORDS = ("menu", "hi", "hello", "options", "start", "hey")
FSM_CANCEL_ALL_KEYWORD = "all"

# ----- Action / store (WhatsApp copy / prompts) -----
MSG_OPTION_NOT_AVAILABLE = "This option is not available for your account."
MSG_NO_ACTIVE_OFFERS = "No active offers at the moment. Please check back later."
MSG_NO_PRODUCTS = "No products available at the moment. Please check back later."
MSG_NO_PRODUCTS_FOR_QUERY = "No products found for '{query}'. Try a different keyword or type *products* to browse all."
MSG_PLEASE_SHARE_ORDER_ID = "Please share your Order ID to track status (e.g. ORD-XXXXXXXX). Reply with your order number."
MSG_TICKET_CREATED = "Ticket created: {ticket_id}. Our team will contact you shortly."
MSG_STORE_FOUND_COUNT = "Found {n} product(s):"
MSG_STORE_PRICES_HEADER = "Prices for matching items:"
MSG_STORE_ORDER_HEADER = "📦 *Order {oid}*"
MSG_STORE_ORDER_STATUS_LINE = "Status: *{status}*"
MSG_STORE_ORDER_TOTAL_LINE = "Total: ₹{amount}"
MSG_STORE_ORDER_NOT_FOUND = "Order *{oid}* not found. Please check the ID and try again."
MSG_STORE_CATALOG_LINK_INTRO = "Browse our catalog — tap the link below to open in your browser:"
MSG_STORE_MOST_POPULAR_HEADER = "Most popular products:"
MSG_STORE_WHICH_PRODUCT_PRICE = "Which product's price do you need? Reply with a name or keyword."
MSG_STORE_OFFER_BROCHURE_CAPTION = "Offer brochure"
MSG_STORE_BROWSE_HEADER = "Our Products:"
MSG_STORE_OFFERS_SECTION_HEADER = "🛍️ *Current Offers*"
MSG_STORE_OFFERS_AI_FALLBACK_HEADER = "Current Offers:"
# ENV_DEFAULT_PUBLIC_APP_URL = "http://localhost:5173"
ENV_DEFAULT_PUBLIC_APP_URL = "https://4358-2001-8f8-1a3d-4925-9493-7676-9b2e-2df6.ngrok-free.app"
ORDER_STATUS_FALLBACK_PLACED = "placed"
ORDER_ID_PLACEHOLDER = "N/A"


