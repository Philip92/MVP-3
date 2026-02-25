"""
Recipient routes for Servex Holdings backend.
Handles recipient CRUD operations for parcel intake.
"""
from fastapi import APIRouter, HTTPException, Depends
from typing import List, Optional
from pydantic import BaseModel, EmailStr
from datetime import datetime, timezone
import uuid

from database import db
from dependencies import get_current_user, get_tenant_id

router = APIRouter()

# ============ MODELS ============

class RecipientCreate(BaseModel):
    name: str
    phone: Optional[str] = None
    whatsapp: Optional[str] = None
    email: Optional[str] = None
    vat_number: Optional[str] = None
    shipping_address: Optional[str] = None

class RecipientUpdate(BaseModel):
    name: Optional[str] = None
    phone: Optional[str] = None
    whatsapp: Optional[str] = None
    email: Optional[str] = None
    vat_number: Optional[str] = None
    shipping_address: Optional[str] = None

# ============ ROUTES ============

@router.get("/recipients")
async def list_recipients(
    search: Optional[str] = None,
    tenant_id: str = Depends(get_tenant_id)
):
    """List all recipients for tenant"""
    query = {"tenant_id": tenant_id}
    
    if search:
        query["$or"] = [
            {"name": {"$regex": search, "$options": "i"}},
            {"phone": {"$regex": search, "$options": "i"}},
            {"email": {"$regex": search, "$options": "i"}}
        ]
    
    recipients = await db.recipients.find(query, {"_id": 0}).to_list(1000)
    return recipients

@router.post("/recipients")
async def create_recipient(
    recipient_data: RecipientCreate,
    tenant_id: str = Depends(get_tenant_id),
    user: dict = Depends(get_current_user)
):
    """Create a new recipient"""
    recipient = {
        "id": str(uuid.uuid4()),
        "tenant_id": tenant_id,
        "name": recipient_data.name,
        "phone": recipient_data.phone,
        "whatsapp": recipient_data.whatsapp,
        "email": recipient_data.email,
        "vat_number": recipient_data.vat_number,
        "shipping_address": recipient_data.shipping_address,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "created_by": user["id"]
    }
    
    await db.recipients.insert_one(recipient)
    
    # Return without _id
    return {k: v for k, v in recipient.items() if k != "_id"}

@router.get("/recipients/{recipient_id}")
async def get_recipient(
    recipient_id: str,
    tenant_id: str = Depends(get_tenant_id)
):
    """Get a specific recipient"""
    recipient = await db.recipients.find_one(
        {"id": recipient_id, "tenant_id": tenant_id},
        {"_id": 0}
    )
    if not recipient:
        raise HTTPException(status_code=404, detail="Recipient not found")
    return recipient

@router.put("/recipients/{recipient_id}")
async def update_recipient(
    recipient_id: str,
    recipient_data: RecipientUpdate,
    tenant_id: str = Depends(get_tenant_id),
    user: dict = Depends(get_current_user)
):
    """Update a recipient"""
    existing = await db.recipients.find_one(
        {"id": recipient_id, "tenant_id": tenant_id}
    )
    if not existing:
        raise HTTPException(status_code=404, detail="Recipient not found")
    
    update_dict = {k: v for k, v in recipient_data.model_dump().items() if v is not None}
    
    if update_dict:
        await db.recipients.update_one(
            {"id": recipient_id, "tenant_id": tenant_id},
            {"$set": update_dict}
        )
    
    recipient = await db.recipients.find_one(
        {"id": recipient_id, "tenant_id": tenant_id},
        {"_id": 0}
    )
    return recipient

@router.delete("/recipients/{recipient_id}")
async def delete_recipient(
    recipient_id: str,
    tenant_id: str = Depends(get_tenant_id),
    user: dict = Depends(get_current_user)
):
    """Delete a recipient"""
    existing = await db.recipients.find_one(
        {"id": recipient_id, "tenant_id": tenant_id}
    )
    if not existing:
        raise HTTPException(status_code=404, detail="Recipient not found")
    
    await db.recipients.delete_one({"id": recipient_id, "tenant_id": tenant_id})
    return {"message": "Recipient deleted successfully"}
