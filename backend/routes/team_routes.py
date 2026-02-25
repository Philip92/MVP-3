"""
Team and notification routes for Servex Holdings backend.
Handles notifications and team collaboration features.
"""
from fastapi import APIRouter, HTTPException, Depends
from typing import List, Optional
from datetime import datetime, timezone

from database import db
from dependencies import get_current_user, get_tenant_id
from models.schemas import Notification, NotificationCreate, WhatsAppLogCreate
from models.enums import NotificationType, WhatsAppStatus

router = APIRouter()

@router.get("/notifications")
async def list_notifications(
    unread_only: bool = False,
    tenant_id: str = Depends(get_tenant_id),
    user: dict = Depends(get_current_user)
):
    """Get notifications for the current user"""
    query = {"tenant_id": tenant_id, "user_id": user["id"]}
    if unread_only:
        query["read_at"] = None
    
    notifications = []
    cursor = db.notifications.find(query, {"_id": 0}).sort("created_at", -1).limit(50)
    async for notification in cursor:
        notifications.append(notification)
    
    return notifications

@router.get("/notifications/count")
async def get_unread_notification_count(
    tenant_id: str = Depends(get_tenant_id),
    user: dict = Depends(get_current_user)
):
    """Get count of unread notifications"""
    count = await db.notifications.count_documents({
        "tenant_id": tenant_id,
        "user_id": user["id"],
        "read_at": None
    })
    return {"unread_count": count}

@router.post("/notifications")
async def create_notification_endpoint(
    notification_data: NotificationCreate,
    tenant_id: str = Depends(get_tenant_id)
):
    """Create a new notification"""
    notification = Notification(
        tenant_id=tenant_id,
        **notification_data.model_dump()
    )
    await db.notifications.insert_one(notification.model_dump())
    return {"id": notification.id, "message": "Notification created"}

@router.put("/notifications/{notification_id}/read")
async def mark_notification_read(
    notification_id: str,
    tenant_id: str = Depends(get_tenant_id),
    user: dict = Depends(get_current_user)
):
    """Mark a notification as read"""
    result = await db.notifications.update_one(
        {"id": notification_id, "tenant_id": tenant_id, "user_id": user["id"]},
        {"$set": {"read_at": datetime.now(timezone.utc)}}
    )
    if result.modified_count == 0:
        raise HTTPException(status_code=404, detail="Notification not found")
    return {"message": "Notification marked as read"}

@router.put("/notifications/read-all")
async def mark_all_notifications_read(
    tenant_id: str = Depends(get_tenant_id),
    user: dict = Depends(get_current_user)
):
    """Mark all notifications as read for current user"""
    result = await db.notifications.update_many(
        {"tenant_id": tenant_id, "user_id": user["id"], "read_at": None},
        {"$set": {"read_at": datetime.now(timezone.utc)}}
    )
    return {"message": f"Marked {result.modified_count} notifications as read"}

@router.put("/notifications/{notification_id}/resolve")
async def resolve_notification(
    notification_id: str,
    tenant_id: str = Depends(get_tenant_id),
    user: dict = Depends(get_current_user)
):
    """Mark a notification as resolved"""
    result = await db.notifications.update_one(
        {"id": notification_id, "tenant_id": tenant_id, "user_id": user["id"]},
        {"$set": {"resolved_at": datetime.now(timezone.utc), "read_at": datetime.now(timezone.utc)}}
    )
    if result.modified_count == 0:
        raise HTTPException(status_code=404, detail="Notification not found")
    return {"message": "Notification resolved"}

# ============ WHATSAPP LOG ENDPOINTS ============

@router.get("/whatsapp-logs")
async def list_whatsapp_logs(
    invoice_id: Optional[str] = None,
    tenant_id: str = Depends(get_tenant_id)
):
    """Get WhatsApp message logs"""
    query = {"tenant_id": tenant_id}
    if invoice_id:
        query["invoice_id"] = invoice_id
    
    logs = []
    cursor = db.whatsapp_logs.find(query, {"_id": 0}).sort("sent_at", -1).limit(100)
    async for log in cursor:
        logs.append(log)
    
    return logs

@router.post("/whatsapp-logs")
async def create_whatsapp_log(
    log_data: WhatsAppLogCreate,
    tenant_id: str = Depends(get_tenant_id),
    user: dict = Depends(get_current_user)
):
    """Create a new WhatsApp log entry"""
    log = WhatsAppLog(
        tenant_id=tenant_id,
        sent_by=user["id"],
        **log_data.model_dump()
    )
    await db.whatsapp_logs.insert_one(log.model_dump())
    return {"id": log.id, "message": "WhatsApp log created"}

@router.put("/whatsapp-logs/{log_id}/status")
async def update_whatsapp_status(
    log_id: str,
    status: WhatsAppStatus,
    tenant_id: str = Depends(get_tenant_id)
):
    """Update WhatsApp message status (webhook callback)"""
    update_data = {"status": status.value}
    if status == WhatsAppStatus.delivered:
        update_data["delivered_at"] = datetime.now(timezone.utc)
    elif status == WhatsAppStatus.read:
        update_data["read_at"] = datetime.now(timezone.utc)
    
    result = await db.whatsapp_logs.update_one(
        {"id": log_id, "tenant_id": tenant_id},
        {"$set": update_data}
    )
    if result.modified_count == 0:
        raise HTTPException(status_code=404, detail="WhatsApp log not found")
    return {"message": "Status updated"}
