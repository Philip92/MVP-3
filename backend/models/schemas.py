"""
Pydantic model schemas for Servex Holdings backend.
Defines all data validation models used in API requests and responses.
"""
from pydantic import BaseModel, Field, ConfigDict, EmailStr
from typing import List, Optional
from datetime import datetime, timezone, timedelta
from fastapi import Request, HTTPException, Depends
import uuid

from models.enums import (
    UserRole, UserStatus, ClientStatus, RateType, ShipmentStatus,
    TripStatus, ExpenseCategory, InvoiceStatus, PaymentMethod,
    VehicleStatus, VehicleComplianceType, DriverStatus, DriverComplianceType,
    AuditAction, NotificationType, WhatsAppStatus
)
from database import db

# ============ MODELS ============

# Tenant Models
class TenantBase(BaseModel):
    subdomain: str
    company_name: str
    logo_url: Optional[str] = None
    primary_color: str = "#27AE60"
    default_currency: str = "ZAR"
    default_rate_type: str = "per_kg"
    default_rate_value: float = 36.0
    volumetric_divisor: int = 5000
    fuel_surcharge_percentage: float = 0
    address: Optional[str] = None
    phone: Optional[str] = None
    email: Optional[str] = None

class TenantCreate(TenantBase):
    pass

class Tenant(TenantBase):
    model_config = ConfigDict(extra="allow")  # Allow extra fields
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

# User Models
class UserBase(BaseModel):
    name: str
    email: EmailStr
    role: UserRole = UserRole.owner
    phone: Optional[str] = None
    role_title: Optional[str] = None  # Custom job title
    role_template: Optional[str] = "Owner"  # Owner/Manager/Warehouse/Finance/Driver

class UserCreate(UserBase):
    tenant_id: str
    password: Optional[str] = None  # Admin-set password

class UserUpdate(BaseModel):
    name: Optional[str] = None
    role: Optional[UserRole] = None
    phone: Optional[str] = None
    status: Optional[UserStatus] = None
    default_warehouse: Optional[str] = None
    role_title: Optional[str] = None
    role_template: Optional[str] = None
    custom_permissions: Optional[dict] = None
    allowed_warehouses: Optional[List[str]] = None
    password: Optional[str] = None

class User(UserBase):
    model_config = ConfigDict(extra="ignore")
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    tenant_id: str
    status: UserStatus = UserStatus.active
    last_login: Optional[datetime] = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    picture: Optional[str] = None
    default_warehouse: Optional[str] = None
    allowed_warehouses: Optional[List[str]] = None  # Warehouse access restriction
    custom_permissions: Optional[dict] = None  # JSON permissions object
    password_hash: Optional[str] = None  # Hashed password

# Client Models
class ClientBase(BaseModel):
    name: str
    company_name: Optional[str] = None
    phone: Optional[str] = None
    email: Optional[str] = None
    whatsapp: Optional[str] = None
    physical_address: Optional[str] = None
    billing_address: Optional[str] = None
    vat_number: Optional[str] = None
    credit_limit: float = 0.0
    payment_terms_days: int = 30
    default_currency: str = "ZAR"
    default_rate_type: str = "per_kg"
    default_rate_value: float = 36.0
    # Session E: Extended fields
    position: Optional[str] = None
    primary_place_of_business: Optional[str] = None
    nature_of_relationship: Optional[str] = None
    owner: Optional[str] = None
    frequency_of_business: Optional[str] = None
    estimated_value_per_trip: Optional[float] = None
    total_amount_spent: Optional[float] = None

class ClientCreate(ClientBase):
    pass

class ClientUpdate(BaseModel):
    name: Optional[str] = None
    company_name: Optional[str] = None
    phone: Optional[str] = None
    email: Optional[str] = None
    whatsapp: Optional[str] = None
    physical_address: Optional[str] = None
    billing_address: Optional[str] = None
    vat_number: Optional[str] = None
    credit_limit: Optional[float] = None
    payment_terms_days: Optional[int] = None
    default_currency: Optional[str] = None
    default_rate_type: Optional[str] = None
    default_rate_value: Optional[float] = None
    status: Optional[ClientStatus] = None
    # Session E: Extended fields
    position: Optional[str] = None
    primary_place_of_business: Optional[str] = None
    nature_of_relationship: Optional[str] = None
    owner: Optional[str] = None
    frequency_of_business: Optional[str] = None
    estimated_value_per_trip: Optional[float] = None

class Client(ClientBase):
    model_config = ConfigDict(extra="ignore")
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    tenant_id: str
    status: ClientStatus = ClientStatus.active
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

# Client Rate Models
class ClientRateBase(BaseModel):
    rate_type: RateType
    rate_value: float
    effective_from: Optional[str] = None
    notes: Optional[str] = None

class ClientRateCreate(ClientRateBase):
    client_id: str

class ClientRate(ClientRateBase):
    model_config = ConfigDict(extra="ignore")
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    client_id: str
    created_by: str
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

# Shipment Models
class ShipmentBase(BaseModel):
    description: str
    destination: str
    total_pieces: int = 1
    total_weight: float
    total_cbm: Optional[float] = None

class ShipmentCreate(ShipmentBase):
    client_id: str
    trip_id: Optional[str] = None
    invoice_id: Optional[str] = None
    status: Optional[ShipmentStatus] = None
    recipient: Optional[str] = None
    recipient_phone: Optional[str] = None
    recipient_vat: Optional[str] = None
    shipping_address: Optional[str] = None
    sender: Optional[str] = None  # Sub-client or secondary sender
    quantity: Optional[int] = 1
    warehouse_id: Optional[str] = None
    length_cm: Optional[float] = None
    width_cm: Optional[float] = None
    height_cm: Optional[float] = None

class ShipmentUpdate(BaseModel):
    description: Optional[str] = None
    destination: Optional[str] = None
    total_pieces: Optional[int] = None
    total_weight: Optional[float] = None
    total_cbm: Optional[float] = None
    status: Optional[ShipmentStatus] = None
    trip_id: Optional[str] = None
    warehouse_id: Optional[str] = None

class Shipment(ShipmentBase):
    model_config = ConfigDict(extra="ignore")
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    tenant_id: str
    client_id: str
    trip_id: Optional[str] = None
    invoice_id: Optional[str] = None  # Direct link to invoice
    recipient: Optional[str] = None
    recipient_phone: Optional[str] = None
    recipient_vat: Optional[str] = None
    shipping_address: Optional[str] = None
    sender: Optional[str] = None  # Sub-client or secondary sender
    quantity: int = 1
    status: ShipmentStatus = ShipmentStatus.warehouse
    created_by: str
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    warehouse_id: Optional[str] = None
    # Parcel sequencing for batch creation (Qty > 1)
    parcel_sequence: Optional[int] = None  # e.g., 1 for "1 of 10"
    total_in_sequence: Optional[int] = None  # e.g., 10 for "1 of 10"
    # Dimensions (stored for invoice display)
    length_cm: Optional[float] = None
    width_cm: Optional[float] = None
    height_cm: Optional[float] = None
    # Verification fields
    verified: bool = False
    verified_by: Optional[str] = None
    verified_at: Optional[datetime] = None
    # Collection fields
    collected: bool = False
    collected_by: Optional[str] = None
    collected_at: Optional[datetime] = None
    # Classification category (customs code grouping)
    category: Optional[str] = None  # e.g., "electronics", "apparel", "machinery"

# Shipment Piece Models
class ShipmentPieceBase(BaseModel):
    piece_number: int
    weight: float
    length_cm: Optional[float] = None
    width_cm: Optional[float] = None
    height_cm: Optional[float] = None
    photo_url: Optional[str] = None

class ShipmentPieceCreate(ShipmentPieceBase):
    shipment_id: str

class ShipmentPiece(ShipmentPieceBase):
    model_config = ConfigDict(extra="ignore")
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    shipment_id: str
    barcode: str
    loaded_at: Optional[datetime] = None

# Trip Models
class TripBase(BaseModel):
    trip_number: str
    route: List[str] = []  # JSON array of stops e.g. ["Johannesburg", "Beitbridge", "Harare"]
    departure_date: str  # Required
    vehicle_id: Optional[str] = None
    driver_id: Optional[str] = None
    destination_warehouse_id: Optional[str] = None  # Destination warehouse for arriving parcels
    notes: Optional[str] = None
    capacity_kg: Optional[float] = None
    capacity_cbm: Optional[float] = None

class TripCreate(TripBase):
    pass

class TripUpdate(BaseModel):
    trip_number: Optional[str] = None
    route: Optional[List[str]] = None
    departure_date: Optional[str] = None
    vehicle_id: Optional[str] = None
    driver_id: Optional[str] = None
    destination_warehouse_id: Optional[str] = None
    notes: Optional[str] = None
    status: Optional[TripStatus] = None
    actual_departure: Optional[str] = None
    actual_arrival: Optional[str] = None
    capacity_kg: Optional[float] = None
    capacity_cbm: Optional[float] = None

class Trip(TripBase):
    model_config = ConfigDict(extra="ignore")
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    tenant_id: str
    status: TripStatus = TripStatus.planning
    locked_at: Optional[datetime] = None
    actual_departure: Optional[str] = None  # When trip actually departed
    actual_arrival: Optional[str] = None    # When trip actually arrived
    destination_warehouse_id: Optional[str] = None  # Destination warehouse for arriving parcels
    created_by: str
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

# Trip Expense Models
class TripExpenseBase(BaseModel):
    category: ExpenseCategory
    amount: float
    currency: str = "ZAR"
    expense_date: str  # Required
    description: Optional[str] = None
    receipt_url: Optional[str] = None
    # Session I M-01: Expense Attachments
    attachment: Optional[str] = None  # Base64 encoded file
    attachment_filename: Optional[str] = None
    attachment_type: Optional[str] = None  # image/pdf

class TripExpenseCreate(TripExpenseBase):
    pass

class TripExpenseUpdate(BaseModel):
    category: Optional[ExpenseCategory] = None
    amount: Optional[float] = None
    currency: Optional[str] = None
    expense_date: Optional[str] = None
    description: Optional[str] = None
    receipt_url: Optional[str] = None
    attachment: Optional[str] = None
    attachment_filename: Optional[str] = None
    attachment_type: Optional[str] = None

class TripExpense(TripExpenseBase):
    model_config = ConfigDict(extra="ignore")
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    trip_id: str
    created_by: str
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

# ============ FINANCIAL MODELS ============

# Invoice Models
class InvoiceBase(BaseModel):
    trip_id: Optional[str] = None
    client_id: str
    subtotal: float
    adjustments: float = 0
    currency: str = "ZAR"

class InvoiceCreate(InvoiceBase):
    pass

# Enhanced invoice creation model that supports line_items and adjustments arrays from frontend
class InvoiceLineItemInput(BaseModel):
    id: Optional[str] = None
    description: str
    quantity: float = 1
    unit: str = "kg"
    rate: float = 0
    amount: float = 0
    shipment_id: Optional[str] = None
    # Additional fields for enhanced display
    parcel_label: Optional[str] = None  # e.g., "1 of 10"
    client_name: Optional[str] = None
    recipient_name: Optional[str] = None
    length_cm: Optional[float] = None
    width_cm: Optional[float] = None
    height_cm: Optional[float] = None
    weight: Optional[float] = None

class InvoiceAdjustmentInput(BaseModel):
    id: Optional[str] = None
    description: str
    amount: float = 0
    is_addition: bool = False

class InvoiceCreateEnhanced(BaseModel):
    client_id: str
    trip_id: Optional[str] = None
    currency: str = "ZAR"
    issue_date: Optional[str] = None
    due_date: Optional[str] = None
    payment_terms: Optional[str] = None  # "full_on_receipt", "50_50", "30_70", "net_30", "custom"
    payment_terms_custom: Optional[str] = None
    line_items: List[InvoiceLineItemInput] = []
    adjustments: List[InvoiceAdjustmentInput] = []
    total: float = 0
    status: Optional[str] = "draft"

class InvoiceUpdateEnhanced(BaseModel):
    client_id: Optional[str] = None
    trip_id: Optional[str] = None
    currency: Optional[str] = None
    issue_date: Optional[str] = None
    due_date: Optional[str] = None
    payment_terms: Optional[str] = None
    payment_terms_custom: Optional[str] = None
    line_items: Optional[List[InvoiceLineItemInput]] = None
    adjustments: Optional[List[InvoiceAdjustmentInput]] = None
    total: Optional[float] = None
    status: Optional[str] = None

class InvoiceUpdate(BaseModel):
    status: Optional[InvoiceStatus] = None
    subtotal: Optional[float] = None
    adjustments: Optional[float] = None
    currency: Optional[str] = None

class Invoice(InvoiceBase):
    model_config = ConfigDict(extra="ignore")
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    tenant_id: str
    invoice_number: str
    status: InvoiceStatus = InvoiceStatus.draft
    total: float = 0
    sent_at: Optional[datetime] = None
    sent_by: Optional[str] = None
    paid_at: Optional[datetime] = None
    due_date: str
    issue_date: Optional[str] = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    # Payment terms
    payment_terms: Optional[str] = None  # e.g., "full_on_receipt", "50_50", "30_70", "net_30", or custom text
    payment_terms_custom: Optional[str] = None  # Custom terms text
    # Review workflow fields
    reviewed_by: Optional[str] = None
    reviewed_at: Optional[datetime] = None
    approved_by: Optional[str] = None
    approved_at: Optional[datetime] = None
    # Frozen client details at invoice creation for historical accuracy
    client_name_snapshot: Optional[str] = None
    client_address_snapshot: Optional[str] = None
    client_vat_snapshot: Optional[str] = None
    client_phone_snapshot: Optional[str] = None
    client_email_snapshot: Optional[str] = None

# Trip Document Models
class TripDocumentBase(BaseModel):
    trip_id: str
    file_name: str
    file_type: str
    category: str  # Driver Doc, Border Permit, Receipt, Other

class TripDocumentCreate(TripDocumentBase):
    file_data: str  # base64 encoded

class TripDocument(TripDocumentBase):
    model_config = ConfigDict(extra="ignore")
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    file_data: str
    uploaded_by: str
    uploaded_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

# Notification Models
class NotificationBase(BaseModel):
    user_id: str
    message: str
    link: Optional[str] = None
    type: str = "mention"  # mention, system, alert

class NotificationCreate(NotificationBase):
    pass

class Notification(NotificationBase):
    model_config = ConfigDict(extra="ignore")
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    tenant_id: str
    created_by: str
    read: bool = False
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

# Invoice Comment Models
class InvoiceCommentBase(BaseModel):
    invoice_id: str
    content: str
    mentioned_user_ids: List[str] = []

class InvoiceCommentCreate(InvoiceCommentBase):
    pass

class InvoiceComment(InvoiceCommentBase):
    model_config = ConfigDict(extra="ignore")
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    tenant_id: str
    created_by: str
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

# Invoice Line Item Models
class InvoiceLineItemBase(BaseModel):
    shipment_id: Optional[str] = None
    description: str
    quantity: int = 1
    weight: Optional[float] = None
    rate: float

class InvoiceLineItemCreate(InvoiceLineItemBase):
    pass

class InvoiceLineItem(InvoiceLineItemBase):
    model_config = ConfigDict(extra="ignore")
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    invoice_id: str
    amount: float = 0

# Payment Models
class PaymentBase(BaseModel):
    client_id: str
    invoice_id: Optional[str] = None
    amount: float
    payment_date: str
    payment_method: PaymentMethod
    reference: Optional[str] = None
    notes: Optional[str] = None

class PaymentCreate(PaymentBase):
    pass

class Payment(PaymentBase):
    model_config = ConfigDict(extra="ignore")
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    tenant_id: str
    created_by: str
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

# ============ FLEET MANAGEMENT MODELS ============

# Vehicle Models
class VehicleBase(BaseModel):
    name: str
    registration_number: str
    vin: Optional[str] = None
    make: Optional[str] = None
    model: Optional[str] = None
    year: Optional[int] = None
    max_weight_kg: Optional[float] = None
    max_volume_cbm: Optional[float] = None

class VehicleCreate(VehicleBase):
    pass

class VehicleUpdate(BaseModel):
    name: Optional[str] = None
    registration_number: Optional[str] = None
    vin: Optional[str] = None
    make: Optional[str] = None
    model: Optional[str] = None
    year: Optional[int] = None
    max_weight_kg: Optional[float] = None
    max_volume_cbm: Optional[float] = None
    status: Optional[VehicleStatus] = None

class Vehicle(VehicleBase):
    model_config = ConfigDict(extra="ignore")
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    tenant_id: str
    status: VehicleStatus = VehicleStatus.available
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

# Vehicle Compliance Models
class VehicleComplianceBase(BaseModel):
    item_type: VehicleComplianceType
    item_label: Optional[str] = None
    expiry_date: str
    reminder_days_before: int = 30
    notify_channels: List[str] = ["bell"]
    provider: Optional[str] = None
    policy_number: Optional[str] = None
    file_name: Optional[str] = None
    file_type: Optional[str] = None
    file_data: Optional[str] = None  # base64 encoded

class VehicleComplianceCreate(VehicleComplianceBase):
    pass

class VehicleCompliance(VehicleComplianceBase):
    model_config = ConfigDict(extra="ignore")
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    vehicle_id: str
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

# Driver Models
class DriverBase(BaseModel):
    name: str
    phone: str
    email: Optional[str] = None
    id_passport_number: Optional[str] = None
    nationality: Optional[str] = None

class DriverCreate(DriverBase):
    pass

class DriverUpdate(BaseModel):
    name: Optional[str] = None
    phone: Optional[str] = None
    email: Optional[str] = None
    id_passport_number: Optional[str] = None
    nationality: Optional[str] = None
    status: Optional[DriverStatus] = None

class Driver(DriverBase):
    model_config = ConfigDict(extra="ignore")
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    tenant_id: str
    status: DriverStatus = DriverStatus.available
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

# Driver Compliance Models
class DriverComplianceBase(BaseModel):
    item_type: DriverComplianceType
    item_label: Optional[str] = None
    expiry_date: str
    reminder_days_before: int = 30
    notify_channels: List[str] = ["bell"]
    license_number: Optional[str] = None
    issuing_country: Optional[str] = None
    file_name: Optional[str] = None
    file_type: Optional[str] = None
    file_data: Optional[str] = None  # base64 encoded

class DriverComplianceCreate(DriverComplianceBase):
    pass

class DriverCompliance(DriverComplianceBase):
    model_config = ConfigDict(extra="ignore")
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    driver_id: str
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

# Audit Log Models
class AuditLog(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    tenant_id: str
    user_id: str
    action: AuditAction
    table_name: str
    record_id: str
    old_value: Optional[dict] = None
    new_value: Optional[dict] = None
    ip_address: Optional[str] = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

# Notification Models
class NotificationCreate(BaseModel):
    user_id: str
    type: NotificationType
    title: str
    message: str
    link_url: Optional[str] = None

class Notification(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    tenant_id: str
    user_id: str
    type: NotificationType
    title: str
    message: str
    link_url: Optional[str] = None
    read_at: Optional[datetime] = None
    resolved_at: Optional[datetime] = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

# WhatsApp Log Models
class WhatsAppLogCreate(BaseModel):
    to_number: str
    message: str
    template_name: Optional[str] = None
    invoice_id: Optional[str] = None

class WhatsAppLog(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    tenant_id: str
    to_number: str
    message: str
    template_name: Optional[str] = None
    invoice_id: Optional[str] = None
    sent_by: str
    sent_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    status: WhatsAppStatus = WhatsAppStatus.sent
    delivered_at: Optional[datetime] = None
    read_at: Optional[datetime] = None

# Auth Response
class AuthUser(BaseModel):
    id: str
    email: str
    name: str
    picture: Optional[str] = None
    tenant_id: Optional[str] = None
    tenant_name: Optional[str] = None
    role: Optional[str] = None
    role_title: Optional[str] = None
    role_template: Optional[str] = None
    default_warehouse: Optional[str] = None
    allowed_warehouses: Optional[List[str]] = None
    custom_permissions: Optional[dict] = None

# ============ HELPER FUNCTIONS ============

def generate_barcode(trip_number: Optional[str], shipment_seq: int, piece_number: int) -> str:
    """Generate barcode in format: [trip_number]-[shipment_seq]-[piece_number] or TEMP-[random]"""
    if trip_number:
        return f"{trip_number}-{shipment_seq:03d}-{piece_number:02d}"
    else:
        random_digits = ''.join(random.choices(string.digits, k=6))
        return f"TEMP-{random_digits}"

async def generate_invoice_number(tenant_id: str) -> str:
    """Generate invoice number in format: INV-YYYY-NNN"""
    current_year = datetime.now(timezone.utc).year
    
    # Find the highest invoice number for this tenant this year
    pattern = f"INV-{current_year}-"
    last_invoice = await db.invoices.find_one(
        {"tenant_id": tenant_id, "invoice_number": {"$regex": f"^{pattern}"}},
        {"_id": 0, "invoice_number": 1},
        sort=[("invoice_number", -1)]
    )
    
    if last_invoice:
        # Extract the sequence number and increment
        last_num = int(last_invoice["invoice_number"].split("-")[-1])
        next_num = last_num + 1
    else:
        next_num = 1
    
    return f"INV-{current_year}-{next_num:03d}"

def calculate_due_date(payment_terms_days: int) -> str:
    """Calculate due date from today + payment terms"""
    due = datetime.now(timezone.utc) + timedelta(days=payment_terms_days)
    return due.strftime("%Y-%m-%d")

async def create_audit_log(
    tenant_id: str,
    user_id: str,
    action: AuditAction,
    table_name: str,
    record_id: str,
    old_value: Optional[dict] = None,
    new_value: Optional[dict] = None,
    ip_address: Optional[str] = None
):
    """Create an audit log entry for any CRUD operation"""
    # Clean MongoDB ObjectIds from values
    def clean_for_json(obj):
        if obj is None:
            return None
        cleaned = {}
        for k, v in obj.items():
            if k == "_id":
                continue
            if isinstance(v, datetime):
                cleaned[k] = v.isoformat()
            else:
                cleaned[k] = v
        return cleaned
    
    audit_entry = AuditLog(
        tenant_id=tenant_id,
        user_id=user_id,
        action=action,
        table_name=table_name,
        record_id=record_id,
        old_value=clean_for_json(old_value),
        new_value=clean_for_json(new_value),
        ip_address=ip_address
    )
    await db.audit_logs.insert_one(audit_entry.model_dump())

async def create_notification(
    tenant_id: str,
    user_id: str,
    notification_type: NotificationType,
    title: str,
    message: str,
    link_url: Optional[str] = None
):
    """Create a notification for a user"""
    notification = Notification(
        tenant_id=tenant_id,
        user_id=user_id,
        type=notification_type,
        title=title,
        message=message,
        link_url=link_url
    )
    await db.notifications.insert_one(notification.model_dump())
    return notification

async def get_current_user(request: Request) -> dict:
    """Get current user from session token (cookie or header)"""
    # Try cookie first
    session_token = request.cookies.get("session_token")
    
    # Fallback to Authorization header
    if not session_token:
        auth_header = request.headers.get("Authorization")
        if auth_header and auth_header.startswith("Bearer "):
            session_token = auth_header.split(" ")[1]
    
    if not session_token:
        raise HTTPException(status_code=401, detail="Not authenticated")
    
    # Find session
    session_doc = await db.user_sessions.find_one(
        {"session_token": session_token},
        {"_id": 0}
    )
    
    if not session_doc:
        raise HTTPException(status_code=401, detail="Invalid session")
    
    # Check expiry
    expires_at = session_doc.get("expires_at")
    if isinstance(expires_at, str):
        expires_at = datetime.fromisoformat(expires_at.replace('Z', '+00:00'))
    if expires_at.tzinfo is None:
        expires_at = expires_at.replace(tzinfo=timezone.utc)
    if expires_at < datetime.now(timezone.utc):
        raise HTTPException(status_code=401, detail="Session expired")
    
    # Find user
    user_doc = await db.users.find_one(
        {"id": session_doc["user_id"]},
        {"_id": 0}
    )
    
    if not user_doc:
        raise HTTPException(status_code=401, detail="User not found")
    
    return user_doc

async def get_tenant_id(user: dict = Depends(get_current_user)) -> str:
    """Extract tenant_id from current user"""
    tenant_id = user.get("tenant_id")
    if not tenant_id:
        raise HTTPException(status_code=403, detail="User not associated with a tenant")
    return tenant_id
