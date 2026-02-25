"""
Enum classes for Servex Holdings backend.
Defines all status types, categories, and classifications used throughout the system.
"""
from enum import Enum


class UserRole(str, Enum):
    owner = "owner"
    manager = "manager"
    warehouse = "warehouse"
    finance = "finance"
    driver = "driver"


class UserStatus(str, Enum):
    active = "active"
    invited = "invited"
    suspended = "suspended"


class ClientStatus(str, Enum):
    active = "active"
    inactive = "inactive"
    merged = "merged"


class RateType(str, Enum):
    per_kg = "per_kg"
    per_cbm = "per_cbm"
    flat_rate = "flat_rate"
    custom = "custom"


class ShipmentStatus(str, Enum):
    warehouse = "warehouse"
    staged = "staged"
    loaded = "loaded"
    in_transit = "in_transit"
    arrived = "arrived"
    delivered = "delivered"
    collected = "collected"


class TripStatus(str, Enum):
    planning = "planning"
    loading = "loading"
    in_transit = "in_transit"
    delivered = "delivered"
    closed = "closed"


class ExpenseCategory(str, Enum):
    fuel = "fuel"
    tolls = "tolls"
    border_fees = "border_fees"
    repairs = "repairs"
    food = "food"
    accommodation = "accommodation"
    other = "other"


class InvoiceStatus(str, Enum):
    draft = "draft"
    sent = "sent"
    paid = "paid"
    overdue = "overdue"


class PaymentMethod(str, Enum):
    cash = "cash"
    bank_transfer = "bank_transfer"
    mobile_money = "mobile_money"
    other = "other"


class VehicleStatus(str, Enum):
    available = "available"
    in_transit = "in_transit"
    repair = "repair"
    inactive = "inactive"


class VehicleComplianceType(str, Enum):
    license_disk = "license_disk"
    insurance = "insurance"
    roadworthy = "roadworthy"
    service = "service"
    custom = "custom"


class DriverStatus(str, Enum):
    available = "available"
    on_trip = "on_trip"
    on_leave = "on_leave"
    inactive = "inactive"


class DriverComplianceType(str, Enum):
    license = "license"
    work_permit = "work_permit"
    medical = "medical"
    prdp = "prdp"
    custom = "custom"


class AuditAction(str, Enum):
    create = "create"
    update = "update"
    delete = "delete"
    status_change = "status_change"


class NotificationType(str, Enum):
    mention = "mention"
    compliance = "compliance"
    system_event = "system_event"
    payment = "payment"
    invoice = "invoice"


class WhatsAppStatus(str, Enum):
    sent = "sent"
    delivered = "delivered"
    read = "read"
    failed = "failed"
