"""
Bulk demo data for Glamour Studio (Salon).
Covers: appointments, professionals, customers, services, staff,
products with images, promotions (WA / email / SMS), multi-step
booking workflow, and rich WhatsApp triggers.
"""
import datetime as dt
from typing import Any

from app.modules.plans import get_plan_defaults
from app.helpers.constants import DEFAULT_TIMEZONE

NOW = dt.datetime.now(dt.timezone.utc).replace(tzinfo=None)


def _pn(e164: str, code: str = "+91") -> dict:
    """Build phone_number struct required by the customer unique index."""
    return {"code": code, "number": e164[len(code):]}


def _menu(tenant_id: str, menu_id: str, name: str, tree: dict) -> dict:
    """Build a whatsapp_menus document ready to insert."""
    return {
        "tenant": tenant_id,
        "menu_id": menu_id,
        "name": name,
        "status": "published",
        "version": 1,
        "tree": tree,
        "locales": {},
        "updated_at": NOW,
        "is_mock": True,
    }


def _prof_id(tenant: str, name: str, short_name: str) -> str:
    """Mirror ProfessionalService.build_professional_id for seed data."""
    import re

    def slug(s: str, max_len: int) -> str:
        s = s.lower().strip()
        s = re.sub(r"[^a-z0-9]+", "_", s).strip("_")
        return s[:max_len]

    sh = re.sub(r"[^a-z0-9_]", "", short_name.lower())[:20]
    return f"{slug(tenant, 48)}__{slug(name, 64)}__{sh}"

# ── free Unsplash CDN images (no API key needed) ──────────────────────────────
_IMG = {
    "shampoo":     "https://images.unsplash.com/photo-1556228453-efd6c1ff04f6?auto=format&fit=crop&w=400&q=80",
    "conditioner": "https://images.unsplash.com/photo-1611080626919-7cf5a9dbab12?auto=format&fit=crop&w=400&q=80",
    "face_cream":  "https://images.unsplash.com/photo-1556228720-195a672e8a03?auto=format&fit=crop&w=400&q=80",
    "hair_serum":  "https://images.unsplash.com/photo-1631730359585-38a4935cbec4?auto=format&fit=crop&w=400&q=80",
    "nail_polish": "https://images.unsplash.com/photo-1604654894610-df63bc536371?auto=format&fit=crop&w=400&q=80",
    "hair_mask":   "https://images.unsplash.com/photo-1559056199-641a0ac8b55e?auto=format&fit=crop&w=400&q=80",
    "salon_bg":    "https://images.unsplash.com/photo-1522337360788-8b13dee7a37e?auto=format&fit=crop&w=800&q=80",
}


def get_tenant_id() -> str:
    return "ss_business_salon_1"


def get_modules_capabilities() -> tuple[list[str], list[str]]:
    defaults = get_plan_defaults("pro")
    return defaults["modules"], defaults["capabilities"]


def get_seed_data(tenant_id: str) -> dict[str, Any]:
    modules, capabilities = get_modules_capabilities()
    return {
        "tenant_doc": {
            "_id": tenant_id,
            "plan": "pro",
            "category": "salon",
            "business_name": "Glamour Studio",
            "display_name": "Glamour Studio",
            "owner_email": "owner@glamourstudio.demo",
            "owner_phone": "+919876500001",
            "tz": DEFAULT_TIMEZONE,
            "modules": modules,
            "capabilities": capabilities,
            "active": True,
            "address": "12 Velachery Main Rd, Chennai – 600042",
            "location": "https://maps.google.com/?q=Glamour+Studio+Chennai",
            "whatsapp_config": {},
            "payment_config": {"provider": "dummy", "currency": "INR", "test_mode": True},
            "delivery_config": {},
            "smtp_config": {},
            "date_format": "DD-MM-YYYY",
            "currency": "INR",
            "ai_config": {
                "no_show_block_threshold": 3,
                "no_show_reminder_threshold": 0.5,
                "no_show_high_risk_threshold": 0.7,
                "no_show_reminder_lead_hours": 24,
            },
            "appointments": {"slot_duration_minutes": 30, "timezone": DEFAULT_TIMEZONE},
            "is_mock": True,
        },
        # ── Customers ────────────────────────────────────────────────────────
        "customers": [
            {
                "tenant": tenant_id,
                "phone": f"+9198765000{i:02d}",
                "phone_number": _pn(f"+9198765000{i:02d}"),
                "name": name,
                "email": f"c{i}@glamourstudio.demo",
                "tags": tags,
                "active": True,
                "no_show_count": ns,
                "visit_count": visits,
                "created_at": NOW - dt.timedelta(days=visits * 12),
                "is_mock": True,
            }
            for i, (name, ns, visits, tags) in enumerate([
                ("Priya Sharma",    0, 8,  ["vip", "bridal"]),
                ("Anita Reddy",     0, 5,  ["regular"]),
                ("Meera Krishnan",  1, 3,  ["regular"]),
                ("Sneha Patel",     0, 6,  ["regular"]),
                ("Kavitha Nair",    2, 4,  ["at-risk"]),
                ("Lakshmi Iyer",    0, 10, ["vip"]),
                ("Divya Menon",     4, 2,  ["at-risk"]),
                ("Rekha Pillai",    0, 7,  ["regular"]),
                ("Pooja Gupta",     1, 4,  ["regular"]),
                ("Shruti Singh",    0, 9,  ["vip"]),
                ("Neha Kapoor",     3, 1,  ["at-risk"]),
                ("Anjali Verma",    0, 6,  ["regular"]),
                ("Ritu Malhotra",   0, 3,  ["new"]),
                ("Sonal Mehta",     2, 5,  ["regular"]),
                ("Preeti Joshi",    0, 2,  ["new"]),
                ("Swati Bhanot",    0, 4,  ["regular"]),
                ("Geeta Rao",       1, 3,  ["regular"]),
                ("Hema Sundar",     0, 7,  ["vip"]),
            ], start=1)
        ],
        # ── Professionals ────────────────────────────────────────────────────
        "professionals": [
            {
                "tenant": tenant_id,
                "professional_id": _prof_id(tenant_id, name, short),
                "employee_id": eid,
                "name": name,
                "short_name": short,
                "price": price,
                "specialization": spec,
                "slots": [{"time": t, "status": "available"} for t in
                          ["09:00","09:30","10:00","10:30","11:00","11:30",
                           "14:00","14:30","15:00","15:30","16:00","16:30","17:00"]],
                "active": True,
                "created_at": NOW,
                "is_mock": True,
            }
            for name, short, eid, price, spec in [
                ("Riya Sharma",          "Riya",  "GS-E001", 600.0,  "Hair Cutting & Styling"),
                ("Sana Khan",            "Sana",  "GS-E002", 750.0,  "Hair Coloring & Highlights"),
                ("Nidhi Agarwal",        "Nidhi", "GS-E003", 1200.0, "Color Specialist"),
                ("Aisha Banu",           "Aisha", "GS-E004", 2500.0, "Bridal & Makeup Expert"),
                ("Rekha Venkataraman",   "Rekha", "GS-E005", 800.0,  "Skincare & Facials"),
            ]
        ],
        # ── Services ─────────────────────────────────────────────────────────
        "services": [
            {"tenant": tenant_id, "name": n, "description": d, "price": p, "duration": dur,
             "active": True, "created_at": NOW, "is_mock": True}
            for n, d, p, dur in [
                ("Haircut (Women)",    "Precision cut, wash & style",              600,  45),
                ("Haircut (Men)",      "Fade / scissor cut & finish",              400,  30),
                ("Hair Color – Full",  "Full head ammonia-free color",            1200,  90),
                ("Highlights",         "Balayage / foil highlights",              1800, 120),
                ("Blow Dry & Style",   "Wash, blow dry and set",                   350,  30),
                ("Deep Conditioning",  "Keratin-enriched treatment",               700,  60),
                ("Bridal Package",     "Full bridal hair + makeup",               2500, 180),
                ("Classic Facial",     "Cleanse, tone, moisturize",                800,  60),
                ("De-Tan Facial",      "Tan removal + skin brightening",           950,  60),
                ("Manicure",           "Nail shaping, cuticle care & polish",      400,  45),
                ("Pedicure",           "Foot scrub, massage & polish",             500,  60),
                ("Threading (Eyebrow)","Eyebrow threading & shaping",               80,  10),
            ]
        ],
        # ── Staff ────────────────────────────────────────────────────────────
        "staff": [
            {
                "tenant": tenant_id, "id": f"staff_{tenant_id}_{i}",
                "name": name, "role": role, "phone": f"+919876601{i:03d}",
                "email": f"staff{i}@glamourstudio.demo",
                "skills": skills, "active": True,
                "created_at": NOW, "updated_at": NOW, "is_mock": True,
            }
            for i, (name, role, skills) in enumerate([
                ("Meena Rajan",   "receptionist", ["booking", "billing"]),
                ("Sridhar K",     "receptionist", ["booking", "customer_service"]),
                ("Padma Suresh",  "assistant",    ["hair_wash", "preparation"]),
                ("Ravi Kumar",    "cashier",      ["billing", "inventory"]),
            ], start=1)
        ],
        # ── Appointments ─────────────────────────────────────────────────────
        "appointments": _salon_appointments(tenant_id),
        # ── Store categories & products with images ───────────────────────────
        "categories": [
            {"tenant": tenant_id, "name": "Hair Care",  "active": True, "is_mock": True},
            {"tenant": tenant_id, "name": "Skincare",   "active": True, "is_mock": True},
            {"tenant": tenant_id, "name": "Nail Care",  "active": True, "is_mock": True},
        ],
        "products": [
            {
                "tenant": tenant_id, "sku": sku, "name": name, "category": cat,
                "price": price, "mrp": mrp, "active": True, "unit": "pcs",
                "description": desc,
                "image_urls": imgs, "image_url": imgs[0],
                "is_mock": True,
            }
            for sku, name, cat, price, mrp, desc, imgs in [
                ("SALON-001", "Argan Oil Shampoo 300ml", "Hair Care", 450, 520,
                 "Sulfate-free shampoo with Moroccan argan oil. Adds shine and reduces frizz. Suitable for color-treated hair.",
                 [_IMG["shampoo"]]),
                ("SALON-002", "Keratin Conditioner 250ml", "Hair Care", 380, 450,
                 "Deep-repair conditioner with keratin protein. Detangles and strengthens every strand from root to tip.",
                 [_IMG["conditioner"]]),
                ("SALON-003", "Vitamin C Face Cream 50g", "Skincare", 620, 720,
                 "Brightening face cream with Vitamin C + hyaluronic acid. Reduces dark spots and evens skin tone.",
                 [_IMG["face_cream"]]),
                ("SALON-004", "Hair Growth Serum 30ml", "Hair Care", 850, 999,
                 "Clinically tested serum with biotin and peptides. Stimulates hair follicles and reduces hair fall.",
                 [_IMG["hair_serum"], _IMG["shampoo"]]),
                ("SALON-005", "Nourishing Hair Mask 200g", "Hair Care", 520, 599,
                 "Intensive overnight mask with coconut oil and shea butter. Restores moisture to dry, damaged hair.",
                 [_IMG["hair_mask"]]),
                ("SALON-006", "Gel Nail Polish Set (6 pcs)", "Nail Care", 699, 799,
                 "Long-lasting gel nail colors. Chip-resistant formula lasts up to 3 weeks. No lamp required.",
                 [_IMG["nail_polish"]]),
                ("SALON-007", "SPF 50 Sunscreen 75ml", "Skincare", 399, 449,
                 "Lightweight non-greasy sunscreen with broad-spectrum UV protection. PA+++ rating.",
                 [_IMG["face_cream"]]),
            ]
        ],
        "inventory": [
            {"tenant": tenant_id, "sku": f"SALON-00{i}", "available_qty": qty, "is_mock": True}
            for i, qty in enumerate([45, 60, 38, 20, 55, 80, 70], start=1)
        ],
        # ── Promotions (WhatsApp / email / SMS) ───────────────────────────────
        "promotions": [
            {
                "tenant": tenant_id,
                "name": "Welcome – 20% Off First Visit",
                "channel": "both",
                "message": "💇‍♀️ Welcome to Glamour Studio!\n\nEnjoy *20% off* your first service. Book now and look your best!\n\n📍 12 Velachery Main Rd, Chennai\n📞 +91 98765 00001",
                "audience": {"type": "all"},
                "status": "active",
                "offer_code": "FIRST20",
                "created_at": NOW, "updated_at": NOW, "is_mock": True,
            },
            {
                "tenant": tenant_id,
                "name": "Bridal Season Special",
                "channel": "whatsapp",
                "message": "✨ Bridal Season is HERE at Glamour Studio!\n\nBook our *Complete Bridal Package* — Hair + Makeup + Nail at ₹3,999 (save ₹1,000).\n\nSlots filling fast. Book today!",
                "interactive_type": "cta_url",
                "cta_entries": [{"id": "cta_1", "display_text": "Book Bridal Package", "url": "https://wa.me/+919876500001?text=Bridal+Package"}],
                "cta_append_urls_to_body": True,
                "audience": {"type": "all"},
                "status": "draft",
                "created_at": NOW, "updated_at": NOW, "is_mock": True,
            },
            {
                "tenant": tenant_id,
                "name": "Weekend Hair Color Offer – SMS",
                "channel": "sms",
                "message": "Glamour Studio: Get 15% OFF on Hair Color this weekend only! Book: +91 98765 00001. Offer code: COLOR15. Valid Sat-Sun.",
                "audience": {"type": "all"},
                "status": "draft",
                "offer_code": "COLOR15",
                "created_at": NOW, "updated_at": NOW, "is_mock": True,
            },
            {
                "tenant": tenant_id,
                "name": "Loyalty Reward – VIP Customers",
                "channel": "sms+whatsapp",
                "message": "🌟 You're a VIP at Glamour Studio!\n\nAs our loyal customer, enjoy a *complimentary deep conditioning* on your next visit. Show this message at the counter.\n\nValid this month only!",
                "audience": {"type": "tags", "tags": ["vip"]},
                "status": "draft",
                "created_at": NOW, "updated_at": NOW, "is_mock": True,
            },
        ],
        # ── WhatsApp Triggers ─────────────────────────────────────────────────
        "whatsapp_triggers": [
            {"tenant": tenant_id, "trigger_id": "welcome_hi",
             "match": {"type": "exact", "value": "hi"},
             "action": {"kind": "static_text", "text": "👋 Welcome to *Glamour Studio*!\n\nReply with:\n1️⃣ Book appointment\n2️⃣ Our services & prices\n3️⃣ Location & hours\n4️⃣ Cancel / reschedule\n5️⃣ Talk to us"},
             "enabled": True, "priority": 10, "is_mock": True},
            {"tenant": tenant_id, "trigger_id": "welcome_hello",
             "match": {"type": "exact", "value": "hello"},
             "action": {"kind": "static_text", "text": "👋 Hello! Welcome to *Glamour Studio*.\n\nReply *hi* to see our menu, or *book* to schedule your appointment right away."},
             "enabled": True, "priority": 9, "is_mock": True},
            {"tenant": tenant_id, "trigger_id": "trigger_book",
             "match": {"type": "exact", "value": "book"},
             "action": {"kind": "workflow", "workflow_id": "salon_booking_flow"},
             "enabled": True, "priority": 8, "is_mock": True},
            {"tenant": tenant_id, "trigger_id": "trigger_cancel",
             "match": {"type": "exact", "value": "cancel"},
             "action": {"kind": "static_text", "text": "To cancel your appointment please call us at +91 98765 00001 or WhatsApp 'CANCEL <your name>' and we'll handle it right away. 📅"},
             "enabled": True, "priority": 7, "is_mock": True},
            {"tenant": tenant_id, "trigger_id": "trigger_location",
             "match": {"type": "contains", "value": "location"},
             "action": {"kind": "static_text", "text": "📍 *Glamour Studio*\n12 Velachery Main Rd, Chennai – 600042\n\n🕐 Mon–Sat: 9 AM – 7 PM\n🕐 Sunday: 10 AM – 5 PM\n\nGoogle Maps: https://maps.google.com/?q=Glamour+Studio+Chennai"},
             "enabled": True, "priority": 6, "is_mock": True},
            {"tenant": tenant_id, "trigger_id": "trigger_prices",
             "match": {"type": "contains", "value": "price"},
             "action": {"kind": "invoke_action", "action_id": "show_service_prices"},
             "enabled": True, "priority": 5, "is_mock": True},
        ],
        # ── Workflows ─────────────────────────────────────────────────────────
        "workflows": [
            {
                "tenant": tenant_id,
                "workflow_id": "salon_booking_flow",
                "name": "Salon Appointment Booking",
                "active": True,
                "requires_caps": ["appointments"],
                "steps": [
                    {"action_code": "SHOW_SERVICES",    "label": "Please choose a service:",       "input_required": True,  "ui_type": "list", "params": {}},
                    {"action_code": "SELECT_DATE",       "label": "Select your preferred date:",    "input_required": True,  "ui_type": "list", "params": {}},
                    {"action_code": "SELECT_TIME",       "label": "Choose an available time slot:", "input_required": True,  "ui_type": "list", "params": {}},
                    {"action_code": "CONFIRM_BOOKING",   "label": "Confirm your booking",           "input_required": False, "ui_type": "list", "params": {}},
                    {"action_code": "END",               "label": "✅ Your appointment is confirmed! We'll send you a reminder 24 hours before. Reply *hi* to return to the main menu.", "input_required": False, "ui_type": "list", "params": {}},
                ],
                "created_at": NOW, "updated_at": NOW, "is_mock": True,
            },
            {
                "tenant": tenant_id,
                "workflow_id": "salon_reschedule_flow",
                "name": "Reschedule / Cancel Appointment",
                "active": True,
                "requires_caps": ["appointments"],
                "steps": [
                    {"action_code": "SELECT_DATE",    "label": "Choose a new date:", "input_required": True,  "ui_type": "list", "params": {}},
                    {"action_code": "SELECT_TIME",    "label": "Choose a new time:", "input_required": True,  "ui_type": "list", "params": {}},
                    {"action_code": "CONFIRM_BOOKING","label": "Confirm reschedule", "input_required": False, "ui_type": "list", "params": {}},
                    {"action_code": "END",            "label": "✅ Your appointment has been rescheduled! See you then. 💇‍♀️", "input_required": False, "ui_type": "list", "params": {}},
                ],
                "created_at": NOW, "updated_at": NOW, "is_mock": True,
            },
            {
                "tenant": tenant_id,
                "workflow_id": "salon_professional_flow",
                "name": "Book with Specific Stylist",
                "description": "Choose your stylist → service → date → confirm.",
                "active": True,
                "requires_caps": ["appointments"],
                "steps": [
                    {"action_code": "SHOW_PROFESSIONALS", "label": "Choose your preferred stylist:", "input_required": True,  "ui_type": "list", "params": {}},
                    {"action_code": "SHOW_SERVICES",      "label": "Select a service:",              "input_required": True,  "ui_type": "list", "params": {}},
                    {"action_code": "SELECT_DATE",        "label": "Select your preferred date:",    "input_required": True,  "ui_type": "list", "params": {}},
                    {"action_code": "CONFIRM_BOOKING",    "label": "Confirm your booking",           "input_required": False, "ui_type": "list", "params": {}},
                    {"action_code": "END",                "label": "✅ Booked with your chosen stylist! See you soon 💇‍♀️", "input_required": False, "ui_type": "list", "params": {}},
                ],
                "created_at": NOW, "updated_at": NOW, "is_mock": True,
            },
            {
                "tenant": tenant_id,
                "workflow_id": "salon_quick_flow",
                "name": "Quick Booking (Auto-Slot)",
                "description": "Pick a service — date and slot auto-assigned to next available.",
                "active": True,
                "requires_caps": ["appointments"],
                "steps": [
                    {"action_code": "SHOW_SERVICES",   "label": "Pick a service — we'll find the next available slot:", "input_required": True,  "ui_type": "list", "params": {}},
                    {"action_code": "CONFIRM_BOOKING", "label": "Confirm your appointment",                              "input_required": False, "ui_type": "list", "params": {}},
                    {"action_code": "END",             "label": "✅ Done! We've booked your next available slot. Reply *hi* anytime. 💇", "input_required": False, "ui_type": "list", "params": {}},
                ],
                "created_at": NOW, "updated_at": NOW, "is_mock": True,
            },
            {
                "tenant": tenant_id,
                "workflow_id": "salon_price_list_flow",
                "name": "Services & Price List",
                "description": "Live price list from tenant services catalog.",
                "active": True,
                "requires_caps": ["appointments"],
                "steps": [
                    {"action_code": "SHOW_SERVICE_PRICES", "label": "💇‍♀️ *Our Services & Prices*", "input_required": False, "ui_type": "list", "params": {}},
                    {"action_code": "END", "label": "Reply *hi* for the main menu or *book* to schedule an appointment.", "input_required": False, "ui_type": "list", "params": {}},
                ],
                "created_at": NOW, "updated_at": NOW, "is_mock": True,
            },
        ],
        # ── WhatsApp Menus ────────────────────────────────────────────────────
        "whatsapp_menus": [
            _menu(tenant_id, "welcome_message", "Glamour Studio – Main Menu", {
                "root": "main",
                "nodes": [
                    {
                        "id": "main",
                        "type": "submenu",
                        "title": "Welcome to *Glamour Studio* ✨",
                        "prompt": "How can we help you today?",
                        "options": [
                            {"key": "1", "label": "Book Appointment",       "next": "workflow.salon_booking_flow"},
                            {"key": "2", "label": "Book with Stylist",      "next": "workflow.salon_professional_flow"},
                            {"key": "3", "label": "Quick Booking",          "next": "workflow.salon_quick_flow"},
                            {"key": "4", "label": "Services & Prices",      "next": "workflow.salon_price_list_flow"},
                            {"key": "5", "label": "Location & Hours",       "next": "location_info"},
                            {"key": "6", "label": "Cancel / Reschedule",    "next": "cancel_info"},
                            {"key": "7", "label": "Talk to Us",             "next": "contact_info"},
                        ],
                    },
                    {
                        "id": "services_info",
                        "type": "action",
                        "action_type": "static_text",
                        "text": (
                            "💇‍♀️ *Our Services & Prices*\n\n"
                            "• Haircut (Women) – ₹600\n"
                            "• Haircut (Men) – ₹400\n"
                            "• Hair Color (Full) – ₹1,200\n"
                            "• Highlights – ₹1,800\n"
                            "• Bridal Package – ₹2,500\n"
                            "• Classic Facial – ₹800\n"
                            "• Manicure & Pedicure – ₹700\n"
                            "• Blow Dry & Style – ₹350\n\n"
                            "Reply *hi* to return to the main menu."
                        ),
                    },
                    {
                        "id": "location_info",
                        "type": "action",
                        "action_type": "static_text",
                        "text": (
                            "📍 *Glamour Studio*\n"
                            "12 Velachery Main Rd, Chennai – 600042\n\n"
                            "🕐 Mon–Sat: 9 AM – 7 PM\n"
                            "🕐 Sunday: 10 AM – 5 PM\n\n"
                            "📞 +91 98765 00001\n"
                            "🗺 https://maps.google.com/?q=Glamour+Studio+Chennai\n\n"
                            "Reply *hi* for main menu."
                        ),
                    },
                    {
                        "id": "cancel_info",
                        "type": "action",
                        "action_type": "static_text",
                        "text": (
                            "❌ *Cancel / Reschedule*\n\n"
                            "To cancel or reschedule your appointment:\n"
                            "• Reply with: CANCEL <your name>\n"
                            "• Or call us: +91 98765 00001\n\n"
                            "Our team will confirm within 30 minutes.\n\n"
                            "Reply *hi* for main menu."
                        ),
                    },
                    {
                        "id": "contact_info",
                        "type": "action",
                        "action_type": "static_text",
                        "text": (
                            "💬 *Get in Touch*\n\n"
                            "📞 Phone: +91 98765 00001\n"
                            "📧 Email: hello@glamourstudio.demo\n"
                            "📷 Instagram: @GlamourStudioChennai\n\n"
                            "We typically reply within 1 hour.\n\n"
                            "Reply *hi* for main menu."
                        ),
                    },
                ],
                "edges": [],
            }),
        ],
    }


def _salon_appointments(tenant_id: str) -> list[dict]:
    appts = []
    base = NOW.replace(hour=9, minute=0, second=0, microsecond=0)
    customers = [
        ("Priya Sharma",   "+919876500001"),
        ("Anita Reddy",    "+919876500002"),
        ("Meera Krishnan", "+919876500003"),
        ("Sneha Patel",    "+919876500004"),
        ("Kavitha Nair",   "+919876500005"),
        ("Lakshmi Iyer",   "+919876500006"),
        ("Divya Menon",    "+919876500007"),
        ("Rekha Pillai",   "+919876500008"),
        ("Shruti Singh",   "+919876500010"),
        ("Hema Sundar",    "+919876500018"),
    ]
    pros = ["Riya Sharma", "Sana Khan", "Nidhi Agarwal", "Aisha Banu", "Rekha Venkataraman"]
    services = [
        ("Haircut (Women)", 600.0, 45),
        ("Hair Color – Full", 1200.0, 90),
        ("Highlights", 1800.0, 120),
        ("Classic Facial", 800.0, 60),
        ("Blow Dry & Style", 350.0, 30),
        ("Deep Conditioning", 700.0, 60),
    ]
    slots = [("09:00", "completed"), ("10:00", "completed"), ("11:00", "no_show"),
             ("14:00", "booked"),    ("15:00", "booked"),    ("16:00", "completed")]
    for day in range(-14, 14):
        d = base + dt.timedelta(days=day)
        for slot_idx, (t, status) in enumerate(slots):
            if day < 0 and status == "booked":
                status = "completed"
            if day >= 0 and status == "completed":
                status = "booked"
            svc_name, svc_price, svc_dur = services[slot_idx % len(services)]
            start = d.replace(hour=int(t.split(":")[0]), minute=int(t.split(":")[1]))
            end = start + dt.timedelta(minutes=svc_dur)
            i = (day + 14) * len(slots) + slot_idx
            cname, cphone = customers[i % len(customers)]
            appts.append({
                "tenant": tenant_id,
                "id": f"GS-{2000 + i}",
                "customer_name": cname,
                "customer_phone": cphone,
                "professional": pros[slot_idx % len(pros)],
                "service": svc_name,
                "time": t,
                "price": svc_price,
                "status": status,
                "notes": "VIP customer" if cname in ("Priya Sharma", "Lakshmi Iyer", "Shruti Singh") else "",
                "created_at": NOW - dt.timedelta(days=abs(day) + 1),
                "start": start,
                "end": end,
                "created_by": "seed",
                "is_mock": True,
            })
    return appts
