"""
WhatsApp Template routes for Servex Holdings backend (SESSION H).
Handles template CRUD and default template creation.
"""
from fastapi import APIRouter, HTTPException, Depends
from typing import List, Optional
from datetime import datetime, timezone
import uuid

from database import db
from dependencies import get_current_user, get_tenant_id

router = APIRouter()

# Default templates
DEFAULT_TEMPLATES = {
    "invoice_sent": {
        "name": "Invoice Sent",
        "category": "invoices",
        "message": """Hi {{client_name}},

Your invoice {{invoice_number}} for {{amount}} is now available.

Due date: {{due_date}}

Please review and let us know if you have any questions.

Thank you!
{{company_name}}""",
        "placeholders": ["client_name", "invoice_number", "amount", "due_date", "company_name"],
        "description": "Sent when a new invoice is created"
    },
    "invoice_overdue": {
        "name": "Invoice Overdue",
        "category": "invoices",
        "message": """Hi {{client_name}},

Your invoice {{invoice_number}} for {{amount}} is now {{days_overdue}} days overdue.

Original due date: {{due_date}}
Outstanding amount: {{outstanding_amount}}

Please arrange payment at your earliest convenience.

{{company_name}}""",
        "placeholders": ["client_name", "invoice_number", "amount", "days_overdue", "due_date", "outstanding_amount", "company_name"],
        "description": "Sent when an invoice becomes overdue"
    },
    "statement_ready": {
        "name": "Statement Ready",
        "category": "statements",
        "message": """Hi {{client_name}},

Your account statement for {{period}} is ready for review.

Total outstanding: {{total_outstanding}}
Invoices: {{invoice_count}}

Please let us know if you need any clarification.

{{company_name}}""",
        "placeholders": ["client_name", "period", "total_outstanding", "invoice_count", "company_name"],
        "description": "Sent with monthly statements"
    },
    "collection_ready": {
        "name": "Collection Ready",
        "category": "collection",
        "message": """Hi {{client_name}},

Your {{parcel_count}} parcel(s) have arrived and are ready for collection at {{warehouse_name}}.

Collection hours: Mon-Fri 8am-5pm

{{company_name}}""",
        "placeholders": ["client_name", "parcel_count", "warehouse_name", "company_name"],
        "description": "Sent when parcels are ready for collection"
    }
}

@router.get("/templates/whatsapp")
async def get_whatsapp_templates(
    tenant_id: str = Depends(get_tenant_id)
):
    """Get all WhatsApp templates for tenant (SESSION H)"""
    templates = await db.whatsapp_templates.find({
        "tenant_id": tenant_id
    }, {"_id": 0}).to_list(100)
    
    # If no templates exist, create defaults
    if not templates:
        templates = await create_default_templates(tenant_id)
    
    return {"templates": templates}


@router.get("/templates/whatsapp/{template_id}")
async def get_whatsapp_template(
    template_id: str,
    tenant_id: str = Depends(get_tenant_id)
):
    """Get single template (SESSION H)"""
    template = await db.whatsapp_templates.find_one({
        "id": template_id,
        "tenant_id": tenant_id
    }, {"_id": 0})
    
    if not template:
        raise HTTPException(404, "Template not found")
    
    return template


@router.put("/templates/whatsapp/{template_id}")
async def update_whatsapp_template(
    template_id: str,
    data: dict,
    tenant_id: str = Depends(get_tenant_id),
    user: dict = Depends(get_current_user)
):
    """Update template message (SESSION H)"""
    message = data.get("message", "")
    result = await db.whatsapp_templates.update_one(
        {"id": template_id, "tenant_id": tenant_id},
        {
            "$set": {
                "message": message,
                "updated_at": datetime.now(timezone.utc).isoformat(),
                "updated_by": user["id"]
            }
        }
    )
    
    if result.matched_count == 0:
        raise HTTPException(404, "Template not found")
    
    return {"message": "Template updated"}


@router.post("/templates/whatsapp/{template_id}/reset")
async def reset_template_to_default(
    template_id: str,
    tenant_id: str = Depends(get_tenant_id)
):
    """Reset template to default message (SESSION H)"""
    template = await db.whatsapp_templates.find_one({
        "id": template_id,
        "tenant_id": tenant_id
    }, {"_id": 0})
    
    if not template:
        raise HTTPException(404, "Template not found")
    
    default_message = DEFAULT_TEMPLATES.get(template["template_key"], {}).get("message", "")
    
    await db.whatsapp_templates.update_one(
        {"id": template_id},
        {"$set": {"message": default_message}}
    )
    
    return {"message": "Template reset to default"}


async def create_default_templates(tenant_id: str):
    """Create default templates for new tenant (SESSION H)"""
    templates = []
    
    for key, data in DEFAULT_TEMPLATES.items():
        template = {
            "id": str(uuid.uuid4()),
            "tenant_id": tenant_id,
            "template_key": key,
            **data,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "updated_at": datetime.now(timezone.utc).isoformat()
        }
        await db.whatsapp_templates.insert_one(template)
        templates.append(template)
    
    return templates
