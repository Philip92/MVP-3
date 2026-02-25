"""
Notes routes for Servex Holdings backend.
Handles notes/comments with team member mentions across all entities.
"""
from fastapi import APIRouter, HTTPException, Depends
from typing import List, Optional
from pydantic import BaseModel
from datetime import datetime, timezone
import uuid
import re

from database import db
from dependencies import get_current_user, get_tenant_id

router = APIRouter()

# ============ MODELS ============

class NoteCreate(BaseModel):
    entity_type: str  # 'shipment', 'client', 'trip', 'invoice', 'vehicle', 'driver'
    entity_id: str
    content: str
    mentioned_users: Optional[List[str]] = []  # List of user IDs

class NoteUpdate(BaseModel):
    content: Optional[str] = None

# ============ ROUTES ============

@router.get("/notes")
async def list_notes(
    entity_type: str,
    entity_id: str,
    tenant_id: str = Depends(get_tenant_id)
):
    """List all notes for a specific entity"""
    notes = await db.notes.find(
        {"tenant_id": tenant_id, "entity_type": entity_type, "entity_id": entity_id},
        {"_id": 0}
    ).sort("created_at", -1).to_list(100)
    
    # Enrich with user info
    for note in notes:
        author = await db.users.find_one({"id": note["author_id"]}, {"_id": 0, "name": 1, "email": 1})
        note["author_name"] = author.get("name", "Unknown") if author else "Unknown"
        
        # Get mentioned user names
        if note.get("mentioned_users"):
            mentioned = await db.users.find(
                {"id": {"$in": note["mentioned_users"]}},
                {"_id": 0, "id": 1, "name": 1}
            ).to_list(100)
            note["mentioned_user_names"] = {u["id"]: u["name"] for u in mentioned}
    
    return notes

@router.post("/notes")
async def create_note(
    note_data: NoteCreate,
    tenant_id: str = Depends(get_tenant_id),
    user: dict = Depends(get_current_user)
):
    """Create a new note with optional team member mentions"""
    
    # Extract @mentions from content
    mention_pattern = r'@(\w+(?:\s+\w+)?)'
    mentioned_names = re.findall(mention_pattern, note_data.content)
    
    # Find user IDs for mentioned names
    mentioned_user_ids = list(note_data.mentioned_users) if note_data.mentioned_users else []
    
    if mentioned_names:
        for name in mentioned_names:
            mentioned_user = await db.users.find_one(
                {"tenant_id": tenant_id, "name": {"$regex": f"^{name}$", "$options": "i"}},
                {"_id": 0, "id": 1}
            )
            if mentioned_user and mentioned_user["id"] not in mentioned_user_ids:
                mentioned_user_ids.append(mentioned_user["id"])
    
    note = {
        "id": str(uuid.uuid4()),
        "tenant_id": tenant_id,
        "entity_type": note_data.entity_type,
        "entity_id": note_data.entity_id,
        "content": note_data.content,
        "author_id": user["id"],
        "mentioned_users": mentioned_user_ids,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "updated_at": None
    }
    
    await db.notes.insert_one(note)
    
    # Create notifications for mentioned users
    for mentioned_id in mentioned_user_ids:
        if mentioned_id != user["id"]:  # Don't notify self
            notification = {
                "id": str(uuid.uuid4()),
                "tenant_id": tenant_id,
                "user_id": mentioned_id,
                "type": "mention",
                "title": f"{user.get('name', 'Someone')} mentioned you",
                "message": f"in a note on {note_data.entity_type}: {note_data.content[:100]}...",
                "entity_type": note_data.entity_type,
                "entity_id": note_data.entity_id,
                "read": False,
                "created_at": datetime.now(timezone.utc).isoformat()
            }
            await db.notifications.insert_one(notification)
    
    # Return with author name
    note["author_name"] = user.get("name", "Unknown")
    if "_id" in note:
        del note["_id"]
    return note

@router.put("/notes/{note_id}")
async def update_note(
    note_id: str,
    note_data: NoteUpdate,
    tenant_id: str = Depends(get_tenant_id),
    user: dict = Depends(get_current_user)
):
    """Update a note (only author can edit)"""
    existing = await db.notes.find_one(
        {"id": note_id, "tenant_id": tenant_id}
    )
    if not existing:
        raise HTTPException(status_code=404, detail="Note not found")
    
    if existing["author_id"] != user["id"] and user.get("role") != "owner":
        raise HTTPException(status_code=403, detail="Only the author or owner can edit this note")
    
    update_dict = {}
    if note_data.content:
        update_dict["content"] = note_data.content
        update_dict["updated_at"] = datetime.now(timezone.utc).isoformat()
    
    if update_dict:
        await db.notes.update_one(
            {"id": note_id, "tenant_id": tenant_id},
            {"$set": update_dict}
        )
    
    note = await db.notes.find_one({"id": note_id, "tenant_id": tenant_id}, {"_id": 0})
    return note

@router.delete("/notes/{note_id}")
async def delete_note(
    note_id: str,
    tenant_id: str = Depends(get_tenant_id),
    user: dict = Depends(get_current_user)
):
    """Delete a note (only author or owner can delete)"""
    existing = await db.notes.find_one(
        {"id": note_id, "tenant_id": tenant_id}
    )
    if not existing:
        raise HTTPException(status_code=404, detail="Note not found")
    
    if existing["author_id"] != user["id"] and user.get("role") != "owner":
        raise HTTPException(status_code=403, detail="Only the author or owner can delete this note")
    
    await db.notes.delete_one({"id": note_id, "tenant_id": tenant_id})
    return {"message": "Note deleted successfully"}

# ============ NOTIFICATIONS ============

@router.get("/notifications")
async def list_notifications(
    unread_only: bool = False,
    tenant_id: str = Depends(get_tenant_id),
    user: dict = Depends(get_current_user)
):
    """List notifications for current user"""
    query = {"tenant_id": tenant_id, "user_id": user["id"]}
    if unread_only:
        query["read"] = False
    
    notifications = await db.notifications.find(
        query, {"_id": 0}
    ).sort("created_at", -1).to_list(50)
    
    return notifications

@router.put("/notifications/{notification_id}/read")
async def mark_notification_read(
    notification_id: str,
    tenant_id: str = Depends(get_tenant_id),
    user: dict = Depends(get_current_user)
):
    """Mark a notification as read"""
    await db.notifications.update_one(
        {"id": notification_id, "tenant_id": tenant_id, "user_id": user["id"]},
        {"$set": {"read": True}}
    )
    return {"message": "Notification marked as read"}

@router.put("/notifications/read-all")
async def mark_all_notifications_read(
    tenant_id: str = Depends(get_tenant_id),
    user: dict = Depends(get_current_user)
):
    """Mark all notifications as read for current user"""
    await db.notifications.update_many(
        {"tenant_id": tenant_id, "user_id": user["id"], "read": False},
        {"$set": {"read": True}}
    )
    return {"message": "All notifications marked as read"}

@router.get("/notifications/count")
async def get_unread_count(
    tenant_id: str = Depends(get_tenant_id),
    user: dict = Depends(get_current_user)
):
    """Get count of unread notifications"""
    count = await db.notifications.count_documents(
        {"tenant_id": tenant_id, "user_id": user["id"], "read": False}
    )
    return {"unread_count": count}
