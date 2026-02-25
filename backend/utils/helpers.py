"""
Utility helper functions for Servex Holdings backend.
Contains shared helper functions for audit logging, notifications, and date calculations.
"""
from typing import Optional
from datetime import datetime, timezone, timedelta

from database import db
from models.enums import AuditAction, NotificationType
from models.schemas import AuditLog, Notification


def calculate_due_date(payment_terms_days: int) -> str:
    """
    Calculate due date from today + payment terms.
    
    Args:
        payment_terms_days: Number of days until payment is due
    
    Returns:
        Due date string in format YYYY-MM-DD
    """
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
    """
    Create an audit log entry for any CRUD operation.
    
    Args:
        tenant_id: Tenant ID
        user_id: User who performed the action
        action: Type of action (create, update, delete, status_change)
        table_name: Name of the collection/table
        record_id: ID of the affected record
        old_value: Previous value (for updates/deletes)
        new_value: New value (for creates/updates)
        ip_address: IP address of the user
    """
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
    """
    Create a notification for a user.
    
    Args:
        tenant_id: Tenant ID
        user_id: User to notify
        notification_type: Type of notification
        title: Notification title
        message: Notification message
        link_url: Optional URL to link to
    
    Returns:
        Notification object
    """
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
