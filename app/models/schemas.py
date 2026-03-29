from __future__ import annotations
from typing import List, Optional, Union, Dict, Any
from pydantic import BaseModel, Field, field_validator, model_validator

from app.helpers.constants import SLOT_STATUS_AVAILABLE


class Slot(BaseModel):
    time: str
    status: str = Field(default=SLOT_STATUS_AVAILABLE, description="available|booked|blocked|completed")


class Professional(BaseModel):
    name: str
    professional_id: str = Field(default="", description="Stable id for API paths")
    employee_id: str = Field(default="", description="Unique employee / badge id per tenant")
    price: float
    slots: List[Slot] = Field(default_factory=list)
    active: bool = True
    availability_criteria: str = "daily"
    available_days: List[int] = Field(default_factory=list)
    services: List[str] = Field(default_factory=list)
    phone: Optional[str] = None
    degree: Optional[str] = None
    address: Optional[str] = None
    bio: Optional[str] = None


class ProfessionalBrief(BaseModel):
    """Minimal row for pickers."""

    professional_id: str
    name: str
    employee_id: str = Field(default="", description="Unique per tenant")


# --- Tenant creation schemas ---
class ProfessionalCreate(BaseModel):
    name: str
    employee_id: str = Field(..., description="Unique per tenant (HR / badge id)")
    price: float = 0.0
    slots: Union[List[str], List[Slot]] = Field(
        default_factory=list,
        description="Optional explicit slots; if empty, use work_start/work_end and slot_interval_minutes",
    )
    slot_interval_minutes: int = Field(default=30, ge=5, le=240)
    work_start: str = Field(default="09:00", pattern=r"^\d{2}:\d{2}$")
    work_end: str = Field(default="18:00", pattern=r"^\d{2}:\d{2}$")
    active: bool = True
    availability_criteria: str = "daily"
    available_days: List[int] = Field(default_factory=list)
    services: List[str] = Field(default_factory=list)
    phone: Optional[str] = None
    degree: Optional[str] = None
    address: Optional[str] = None
    bio: Optional[str] = None

    @field_validator("name", mode="before")
    @classmethod
    def normalize_name(cls, v: Any) -> str:
        if not isinstance(v, str):
            raise TypeError("name must be a string")
        s = v.strip()
        if not s:
            raise ValueError("name must not be empty")
        return s

    @field_validator("employee_id", mode="before")
    @classmethod
    def normalize_employee_id(cls, v: Any) -> str:
        if v is None or (isinstance(v, str) and not str(v).strip()):
            raise ValueError("employee_id is required")
        return str(v).strip()


class TenantCreate(BaseModel):
    tenant: str = Field(..., description="Tenant identifier")
    category: Optional[str] = Field(default="salon", description="Domain category e.g. salon|clinic|showroom")
    plan: Optional[str] = Field(default="pro", description="Subscription plan: basic | pro | enterprise | trial. Use 'trial' for 14-day Pro trial (auto-deactivated after 14 days).")
    professionals: Optional[List[ProfessionalCreate]] = Field(default=None)
    # Optional owner contact
    owner_email: Optional[str] = Field(default=None, description="Owner/admin email for notifications")
    owner_phone: Optional[str] = Field(default=None, description="Owner/admin phone for WhatsApp notifications")
    tz: Optional[str] = Field(default=None, description="IANA timezone, e.g. Asia/Kolkata")
    # WhatsApp/Twilio configuration to persist under whatsapp_config in tenants collection
    whatsapp_config: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Provider configuration, e.g., {provider:'twilio', account_sid:'...', auth_token:'...', from_number:'+1...'}",
    )
    # Bootstrap tenant admin credentials (required by business rule)
    admin_email: str = Field(..., description="Initial tenant admin email to create")
    admin_password: str = Field(..., min_length=8, description="Initial tenant admin password to create (min 8 chars)")
    admin_display_name: Optional[str] = Field(default=None, description="Display name for the tenant admin user")


class TenantCreateResponse(BaseModel):
    tenant: str
    category: str
    professionals: List[Professional] = Field(default_factory=list)
    appointments: int
    revenue: float

# --- Catalog/Inventory schemas ---
class CategoryIn(BaseModel):
    name: str
    active: bool = True


class CategoryOut(BaseModel):
    name: str
    active: bool = True


class ProductIn(BaseModel):
    sku: str = Field(..., description="Unique product SKU")
    name: str
    category: Optional[str] = None
    price: float = 0.0
    mrp: Optional[float] = None
    tax: Optional[float] = None
    unit: Optional[str] = Field(default=None, description="kg|pc|litre etc")
    unit_conversions: Optional[List[Dict[str, Any]]] = Field(
        default=None,
        description="List of conversions: {unit: 'gram', factor: 0.001} (relative to base unit)"
    )
    active: bool = True
    # Optional barcode/UPC/EAN for scanning
    barcode: Optional[str] = Field(default=None, description="Barcode/UPC/EAN for the product")
    # Optional product image URL (can also be a data URL for MVP)
    image_url: Optional[str] = Field(default=None, description="Public URL or data URI for product image")
    # Discount handling: either amount or percent. If both provided, amount takes precedence.
    discount_type: Optional[str] = Field(default=None, description="amount|percent")
    discount_value: Optional[float] = Field(default=None, description="If type=amount, absolute discount; if percent, 0-100")
    # Minimum selling price (MSP): floor for offers/cart. When margin set, backend computes from cost + margin.
    minimum_selling_price: Optional[float] = Field(default=None, description="Minimum selling price (MSP) floor")
    final_selling_price: Optional[float] = Field(default=None, description="Final selling price (Selling Price − Discount + VAT), stored on save")
    margin_type: Optional[str] = Field(default=None, description="percent|amount markup on cost for MSP")
    margin_value: Optional[float] = Field(default=None, description="Margin value for MSP calculation")
    # Optional list of variants (e.g., color/size). When present and non-empty, variants are the purchasable items.
    variants: Optional[list[dict]] = Field(
        default=None,
        description="List of variant objects: {variant_sku:string, attributes: {color?:string, size?:string, ...}, price?, mrp?, tax?, discount_type?, discount_value?, image_url?, active?}"
    )


class ProductOut(ProductIn):
    pass


# --- Appointments / Availability (Phase 1 foundation) ---
class AvailabilityItem(BaseModel):
    start: str = Field(description="Slot start time in ISO-8601 (tenant/professional timezone)")
    end: str = Field(description="Slot end time in ISO-8601 (tenant/professional timezone)")
    capacity: int = Field(ge=1, description="Total concurrent capacity for the slot")
    remaining: int = Field(ge=0, description="Remaining bookable capacity for the slot")
    bookable: bool = Field(description="True if remaining > 0 and within horizon/buffer rules")
    blocked: Optional[bool] = Field(default=None, description="True if slot is manually blocked")


class InventoryUpsert(BaseModel):
    sku: str
    available_qty: float = 0.0


class AppointmentIn(BaseModel):
    tenant: str = Field(..., description="Tenant identifier")
    customer_name: str
    customer_phone: str
    professional: str = Field(default="", description="Display name (optional if professional_id is set)")
    professional_id: Optional[str] = Field(default=None, description="Stable id from GET .../professionals/full")
    time: str
    date: Optional[str] = Field(default=None, description="YYYY-MM-DD")

    @model_validator(mode="after")
    def require_professional_ref(self):
        if not (self.professional_id or "").strip() and not (self.professional or "").strip():
            raise ValueError("Provide professional_id or professional")
        return self


class AppointmentOut(BaseModel):
    id: str
    tenant: str
    customer_name: str
    customer_phone: str
    professional: str
    professional_id: Optional[str] = None
    time: str
    date: Optional[str] = None
    price: float
    status: str
    created_by: Optional[str] = None
    updated_by: Optional[str] = None


class PredictRequest(BaseModel):
    tenant: str
    professional: Optional[str] = None
    top_k: int = 3


class PredictResponse(BaseModel):
    tenant: str
    professional: Optional[str]
    recommended: List[str]
    rationale: str


class AnalyticsResponse(BaseModel):
    tenant: str
    total_appointments: int
    cancellations: int
    revenue: float
