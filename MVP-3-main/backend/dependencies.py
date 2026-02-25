"""
Shared dependencies for Servex Holdings backend.
Contains dependency functions used across multiple routes.
"""
from fastapi import HTTPException, Request, Depends
from datetime import datetime, timezone
from typing import Optional, List

from database import db


async def get_current_user(request: Request) -> dict:
    """
    Get current user from session token (cookie or header).
    
    Args:
        request: FastAPI Request object
    
    Returns:
        User document dict
    
    Raises:
        HTTPException: 401 if not authenticated or session invalid/expired
    """
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
    """
    Extract tenant_id from current user.
    
    Args:
        user: Current user dict from get_current_user dependency
    
    Returns:
        Tenant ID string
    
    Raises:
        HTTPException: 403 if user not associated with a tenant
    """
    tenant_id = user.get("tenant_id")
    if not tenant_id:
        raise HTTPException(status_code=403, detail="User not associated with a tenant")
    return tenant_id


def get_user_allowed_warehouses(user: dict) -> Optional[List[str]]:
    """
    Get list of warehouse IDs the user is allowed to access.
    
    Returns:
        - None if user has access to all warehouses (owner/manager or no restrictions)
        - List of warehouse IDs if user has restrictions
    """
    # Owners and managers typically have full access
    if user.get("role") in ["owner", "manager"]:
        return None  # No restrictions
    
    allowed = user.get("allowed_warehouses")
    
    # If allowed_warehouses is not set or empty, return None (no restrictions)
    if not allowed or len(allowed) == 0:
        return None
    
    return allowed


def build_warehouse_filter(user: dict, warehouse_field: str = "warehouse_id") -> dict:
    """
    Build a MongoDB query filter based on user's allowed warehouses.
    
    Args:
        user: Current user dict
        warehouse_field: The field name to filter on (default: "warehouse_id")
    
    Returns:
        Empty dict if no restrictions, otherwise a filter dict
    """
    allowed = get_user_allowed_warehouses(user)
    
    if allowed is None:
        return {}  # No warehouse restrictions
    
    # User is restricted to specific warehouses
    return {warehouse_field: {"$in": allowed}}


async def check_warehouse_access(
    user: dict, 
    warehouse_id: Optional[str],
    raise_exception: bool = True
) -> bool:
    """
    Check if user has access to a specific warehouse.
    
    Args:
        user: Current user dict
        warehouse_id: The warehouse ID to check
        raise_exception: If True, raises 403 on denial; otherwise returns False
    
    Returns:
        True if access allowed, False otherwise
    
    Raises:
        HTTPException: 403 if access denied and raise_exception is True
    """
    allowed = get_user_allowed_warehouses(user)
    
    # No restrictions - user has access to all
    if allowed is None:
        return True
    
    # Check if warehouse is in allowed list
    if warehouse_id and warehouse_id in allowed:
        return True
    
    # Also allow if warehouse_id is None (unassigned parcels) and user has at least one warehouse
    # This is a business decision - can be made stricter if needed
    
    if raise_exception:
        raise HTTPException(
            status_code=403, 
            detail="Access denied: You do not have permission to access this warehouse"
        )
    
    return False


async def check_permission(
    user: dict,
    page: Optional[str] = None,
    action: Optional[str] = None,
    raise_exception: bool = True
) -> bool:
    """
    Check if user has permission to access a page or perform an action.
    
    Uses custom_permissions if set, otherwise falls back to role_template defaults.
    
    Args:
        user: Current user dict
        page: Page identifier (e.g., "finance", "dashboard")
        action: Action identifier (e.g., "edit_rates", "delete_invoices")
        raise_exception: If True, raises 403 on denial
    
    Returns:
        True if permission granted, False otherwise
    """
    # Owners have full access
    if user.get("role") == "owner":
        return True
    
    # Get custom permissions if set
    custom_permissions = user.get("custom_permissions")
    
    if custom_permissions:
        # Check custom permissions
        if page:
            pages = custom_permissions.get("pages", {})
            if not pages.get(page, False):
                if raise_exception:
                    raise HTTPException(
                        status_code=403,
                        detail=f"Access denied: You do not have permission to access {page}"
                    )
                return False
        
        if action:
            actions = custom_permissions.get("actions", {})
            if not actions.get(action, False):
                if raise_exception:
                    raise HTTPException(
                        status_code=403,
                        detail=f"Access denied: You do not have permission to {action}"
                    )
                return False
        
        return True
    
    # Fall back to role-based defaults
    role = user.get("role", "warehouse")
    
    # Default page permissions by role
    default_page_permissions = {
        "manager": ["dashboard", "parcel-intake", "warehouse", "clients", "loading", "trips", "finance", "fleet", "team"],
        "warehouse": ["dashboard", "parcel-intake", "warehouse", "loading"],
        "finance": ["dashboard", "clients", "finance"],
        "driver": ["dashboard", "trips"]
    }
    
    # Default action permissions by role
    default_action_permissions = {
        "manager": ["edit_rates", "view_all_warehouses", "export_data"],
        "warehouse": [],
        "finance": ["edit_rates", "view_all_warehouses"],
        "driver": []
    }
    
    if page:
        allowed_pages = default_page_permissions.get(role, [])
        if page not in allowed_pages:
            if raise_exception:
                raise HTTPException(
                    status_code=403,
                    detail=f"Access denied: Your role ({role}) does not have permission to access {page}"
                )
            return False
    
    if action:
        allowed_actions = default_action_permissions.get(role, [])
        if action not in allowed_actions:
            if raise_exception:
                raise HTTPException(
                    status_code=403,
                    detail=f"Access denied: Your role ({role}) does not have permission to {action}"
                )
            return False
    
    return True
