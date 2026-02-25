"""
Barcode service for Servex Holdings backend.
Handles barcode generation for shipments and invoice number generation.
"""
from typing import Optional
from datetime import datetime, timezone
import random
import string

from database import db


def generate_barcode(trip_number: Optional[str], shipment_seq: int, piece_number: int) -> str:
    """
    Generate barcode in format: [trip_number]-[shipment_seq]-[piece_number] or TEMP-[random]
    
    Args:
        trip_number: Trip number (e.g., "S27") or None for temp barcode
        shipment_seq: Shipment sequence number (zero-padded to 3 digits)
        piece_number: Piece number within shipment (zero-padded to 2 digits)
    
    Returns:
        Barcode string (e.g., "S27-001-01" or "TEMP-123456")
    """
    if trip_number:
        return f"{trip_number}-{shipment_seq:03d}-{piece_number:02d}"
    else:
        random_digits = ''.join(random.choices(string.digits, k=6))
        return f"TEMP-{random_digits}"


async def generate_invoice_number(tenant_id: str) -> str:
    """
    Generate invoice number in format: INV-YYYY-NNN
    
    Args:
        tenant_id: Tenant ID to scope invoice numbering
    
    Returns:
        Invoice number string (e.g., "INV-2026-001")
    """
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
