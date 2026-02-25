"""
Authentication routes for Servex Holdings backend.
Handles user authentication with email/password login.
"""
from fastapi import APIRouter, Request, Response, HTTPException, Depends
from pydantic import BaseModel, EmailStr
from typing import List, Optional
from pydantic import BaseModel as PydanticBaseModel
from datetime import datetime, timezone, timedelta
import os
import uuid
import bcrypt
import logging

from database import db
from dependencies import get_current_user, get_tenant_id
from models.schemas import (
    User, UserCreate, UserUpdate, UserBase, AuthUser, Tenant
)

router = APIRouter()
logger = logging.getLogger(__name__)

# ============ AUTH MODELS ============

class LoginRequest(BaseModel):
    email: EmailStr
    password: str

class RegisterRequest(BaseModel):
    email: EmailStr
    password: str
    name: str
    company_name: Optional[str] = None

# ============ HELPER FUNCTIONS ============

def hash_password(password: str) -> str:
    """Hash a password using bcrypt"""
    salt = bcrypt.gensalt()
    return bcrypt.hashpw(password.encode('utf-8'), salt).decode('utf-8')

def verify_password(password: str, hashed: str) -> bool:
    """Verify a password against its hash"""
    return bcrypt.checkpw(password.encode('utf-8'), hashed.encode('utf-8'))

def generate_session_token() -> str:
    """Generate a unique session token"""
    return f"sess_{uuid.uuid4().hex}"

# ============ AUTH ROUTES ============

@router.post("/auth/login")
async def login(request: LoginRequest, response: Response):
    """Login with email and password"""
    logger.info(f"Login attempt for email: {request.email}")
    
    # Find user by email
    user = await db.users.find_one({"email": request.email}, {"_id": 0})
    
    if not user:
        logger.warning(f"Login failed: User not found for email {request.email}")
        raise HTTPException(status_code=401, detail="Invalid email or password")
    
    # Check password
    if not user.get("password_hash"):
        logger.warning(f"Login failed: No password set for user {request.email}")
        raise HTTPException(status_code=401, detail="Invalid email or password")
    
    if not verify_password(request.password, user["password_hash"]):
        logger.warning(f"Login failed: Invalid password for email {request.email}")
        raise HTTPException(status_code=401, detail="Invalid email or password")
    
    # Check if user is active
    if user.get("status") != "active":
        raise HTTPException(status_code=401, detail="Account is not active")
    
    # Generate session token
    session_token = generate_session_token()
    
    # Store session
    session_doc = {
        "user_id": user["id"],
        "session_token": session_token,
        "expires_at": (datetime.now(timezone.utc) + timedelta(days=7)).isoformat(),
        "created_at": datetime.now(timezone.utc).isoformat()
    }
    await db.user_sessions.insert_one(session_doc)
    
    # Update last login
    await db.users.update_one(
        {"id": user["id"]},
        {"$set": {"last_login": datetime.now(timezone.utc).isoformat()}}
    )
    
    # Get tenant info
    tenant_doc = await db.tenants.find_one({"id": user.get("tenant_id")}, {"_id": 0})
    tenant_name = tenant_doc.get("company_name") if tenant_doc else None
    
    # Set cookie
    response.set_cookie(
        key="session_token",
        value=session_token,
        httponly=True,
        secure=True,
        samesite="none",
        path="/",
        max_age=7 * 24 * 60 * 60
    )
    
    logger.info(f"Login successful for email: {request.email}")
    
    return {
        "id": user["id"],
        "email": user["email"],
        "name": user["name"],
        "picture": user.get("picture"),
        "tenant_id": user.get("tenant_id"),
        "tenant_name": tenant_name,
        "role": user.get("role", "owner"),
        "default_warehouse": user.get("default_warehouse")
    }

@router.post("/auth/register")
async def register(request: RegisterRequest, response: Response):
    """Register a new user with email and password"""
    logger.info(f"Registration attempt for email: {request.email}")
    
    # Check if user already exists
    existing_user = await db.users.find_one({"email": request.email})
    if existing_user:
        raise HTTPException(status_code=400, detail="Email already registered")
    
    # Create tenant
    tenant_id = str(uuid.uuid4())
    subdomain = request.email.split("@")[0].lower().replace(".", "")[:20]
    
    # Check if subdomain exists
    existing_tenant = await db.tenants.find_one({"subdomain": subdomain})
    if existing_tenant:
        import random
        subdomain = f"{subdomain}{random.randint(100, 999)}"
    
    tenant_doc = {
        "id": tenant_id,
        "subdomain": subdomain,
        "company_name": request.company_name or f"{request.name}'s Company",
        "logo_url": None,
        "primary_color": "#6B633C",
        "created_at": datetime.now(timezone.utc).isoformat()
    }
    await db.tenants.insert_one(tenant_doc)
    
    # Create user
    user_id = str(uuid.uuid4())
    password_hash = hash_password(request.password)
    
    user_doc = {
        "id": user_id,
        "tenant_id": tenant_id,
        "name": request.name,
        "email": request.email,
        "password_hash": password_hash,
        "role": "owner",
        "phone": None,
        "status": "active",
        "picture": None,
        "last_login": datetime.now(timezone.utc).isoformat(),
        "created_at": datetime.now(timezone.utc).isoformat()
    }
    await db.users.insert_one(user_doc)
    
    # Generate session token
    session_token = generate_session_token()
    
    # Store session
    session_doc = {
        "user_id": user_id,
        "session_token": session_token,
        "expires_at": (datetime.now(timezone.utc) + timedelta(days=7)).isoformat(),
        "created_at": datetime.now(timezone.utc).isoformat()
    }
    await db.user_sessions.insert_one(session_doc)
    
    # Set cookie
    response.set_cookie(
        key="session_token",
        value=session_token,
        httponly=True,
        secure=True,
        samesite="none",
        path="/",
        max_age=7 * 24 * 60 * 60
    )
    
    logger.info(f"Registration successful for email: {request.email}")
    
    return {
        "id": user_id,
        "email": request.email,
        "name": request.name,
        "picture": None,
        "tenant_id": tenant_id,
        "tenant_name": tenant_doc["company_name"],
        "role": "owner"
    }

@router.get("/auth/me", response_model=AuthUser)
async def get_current_user_info(user: dict = Depends(get_current_user)):
    """Get current authenticated user with all security fields"""
    tenant_doc = await db.tenants.find_one({"id": user.get("tenant_id")}, {"_id": 0})
    tenant_name = tenant_doc.get("company_name") if tenant_doc else None
    
    return {
        "id": user["id"],
        "email": user["email"],
        "name": user["name"],
        "picture": user.get("picture"),
        "tenant_id": user.get("tenant_id"),
        "tenant_name": tenant_name,
        "role": user.get("role"),
        "role_title": user.get("role_title"),
        "role_template": user.get("role_template"),
        "default_warehouse": user.get("default_warehouse"),
        "allowed_warehouses": user.get("allowed_warehouses"),
        "custom_permissions": user.get("custom_permissions")
    }

@router.put("/auth/me/default-warehouse")
async def update_default_warehouse(
    data: dict,
    current_user: dict = Depends(get_current_user)
):
    """Update current user's default warehouse"""
    warehouse_id = data.get("warehouse_id")
    
    await db.users.update_one(
        {"id": current_user["id"]},
        {"$set": {"default_warehouse": warehouse_id}}
    )
    
    return {"message": "Default warehouse updated", "default_warehouse": warehouse_id}

@router.post("/auth/logout")
async def logout(request: Request, response: Response):
    """Logout and clear session"""
    session_token = request.cookies.get("session_token")
    
    if session_token:
        await db.user_sessions.delete_one({"session_token": session_token})
    
    response.delete_cookie(key="session_token", path="/")
    return {"message": "Logged out successfully"}

# ============ TENANT ROUTES ============

@router.get("/tenant", response_model=Tenant)
async def get_current_tenant(tenant_id: str = Depends(get_tenant_id)):
    """Get current tenant info"""
    tenant = await db.tenants.find_one({"id": tenant_id}, {"_id": 0})
    if not tenant:
        raise HTTPException(status_code=404, detail="Tenant not found")
    return tenant

@router.put("/tenant")
async def update_tenant(
    update_data: dict,
    tenant_id: str = Depends(get_tenant_id),
    current_user: dict = Depends(get_current_user)
):
    """Update tenant info (owner only)"""
    if current_user.get("role") != "owner":
        raise HTTPException(status_code=403, detail="Only owners can update tenant info")
    
    allowed_fields = ["company_name", "logo_url", "primary_color", "default_currency", 
                      "address", "phone", "email", "volumetric_divisor", "default_rate_type",
                      "default_rate_value", "fuel_surcharge_percentage", "role_permissions"]
    update_dict = {k: v for k, v in update_data.items() if k in allowed_fields}
    
    if update_dict:
        await db.tenants.update_one({"id": tenant_id}, {"$set": update_dict})
    
    tenant = await db.tenants.find_one({"id": tenant_id}, {"_id": 0})
    return tenant

@router.get("/tenant/permissions")
async def get_tenant_permissions(tenant_id: str = Depends(get_tenant_id)):
    """Get role-based page permissions for tenant"""
    tenant = await db.tenants.find_one({"id": tenant_id}, {"_id": 0, "role_permissions": 1})
    
    # Default permissions if not set (removed scanner)
    default_permissions = {
        "owner": ["dashboard", "parcel-intake", "warehouse", "clients", "loading", "trips", "finance", "fleet", "team", "settings"],
        "manager": ["dashboard", "parcel-intake", "warehouse", "clients", "loading", "trips", "finance", "fleet", "team"],
        "warehouse": ["dashboard", "parcel-intake", "warehouse", "loading"],
        "finance": ["dashboard", "clients", "finance"],
        "driver": ["dashboard", "trips"]
    }
    
    return tenant.get("role_permissions", default_permissions) if tenant else default_permissions

@router.put("/tenant/permissions")
async def update_tenant_permissions(
    permissions: dict,
    tenant_id: str = Depends(get_tenant_id),
    current_user: dict = Depends(get_current_user)
):
    """Update role-based page permissions (owner only)"""
    if current_user.get("role") != "owner":
        raise HTTPException(status_code=403, detail="Only owners can update permissions")
    
    await db.tenants.update_one(
        {"id": tenant_id},
        {"$set": {"role_permissions": permissions}}
    )
    
    return {"message": "Permissions updated"}

# ============ CURRENCY MANAGEMENT ============

@router.get("/tenant/currencies")
async def get_tenant_currencies(tenant_id: str = Depends(get_tenant_id)):
    """Get currency settings for tenant"""
    tenant = await db.tenants.find_one({"id": tenant_id}, {"_id": 0})
    
    # Default currencies if not set
    default_currencies = {
        "base_currency": "ZAR",
        "exchange_rates": [
            {"code": "ZAR", "name": "South African Rand", "rate_to_base": 1.0},
            {"code": "KES", "name": "Kenyan Shilling", "rate_to_base": 0.14},
            {"code": "USD", "name": "US Dollar", "rate_to_base": 18.5},
            {"code": "GBP", "name": "British Pound", "rate_to_base": 23.2},
            {"code": "EUR", "name": "Euro", "rate_to_base": 20.1}
        ]
    }
    
    # Check if tenant has exchange_rates set (not None AND not empty)
    tenant_rates = tenant.get("exchange_rates") if tenant else None
    has_rates = tenant_rates is not None and len(tenant_rates) > 0
    
    return {
        "base_currency": tenant.get("base_currency", default_currencies["base_currency"]) if tenant else default_currencies["base_currency"],
        "exchange_rates": tenant_rates if has_rates else default_currencies["exchange_rates"]
    }

@router.put("/tenant/currencies")
async def update_tenant_currencies(
    currency_data: dict,
    tenant_id: str = Depends(get_tenant_id),
    current_user: dict = Depends(get_current_user)
):
    """Update currency settings (owner only)"""
    if current_user.get("role") != "owner":
        raise HTTPException(status_code=403, detail="Only owners can update currencies")
    
    update_dict = {}
    if "base_currency" in currency_data:
        update_dict["base_currency"] = currency_data["base_currency"]
    if "exchange_rates" in currency_data:
        update_dict["exchange_rates"] = currency_data["exchange_rates"]
    
    if update_dict:
        await db.tenants.update_one({"id": tenant_id}, {"$set": update_dict})
    
    return {"message": "Currencies updated"}

@router.post("/tenant/currencies/add")
async def add_currency(
    currency: dict,
    tenant_id: str = Depends(get_tenant_id),
    current_user: dict = Depends(get_current_user)
):
    """Add a new currency"""
    if current_user.get("role") != "owner":
        raise HTTPException(status_code=403, detail="Only owners can add currencies")
    
    # Get current currencies
    tenant = await db.tenants.find_one({"id": tenant_id}, {"_id": 0})
    exchange_rates = tenant.get("exchange_rates", []) if tenant else []
    
    # Check if currency already exists
    if any(r["code"] == currency["code"] for r in exchange_rates):
        raise HTTPException(status_code=400, detail=f"Currency {currency['code']} already exists")
    
    # Add new currency
    exchange_rates.append({
        "code": currency["code"],
        "name": currency["name"],
        "rate_to_base": float(currency.get("rate_to_base", 1.0))
    })
    
    await db.tenants.update_one({"id": tenant_id}, {"$set": {"exchange_rates": exchange_rates}})
    
    return {"message": f"Currency {currency['code']} added", "exchange_rates": exchange_rates}

@router.delete("/tenant/currencies/{code}")
async def delete_currency(
    code: str,
    tenant_id: str = Depends(get_tenant_id),
    current_user: dict = Depends(get_current_user)
):
    """Delete a currency (cannot delete base currency)"""
    if current_user.get("role") != "owner":
        raise HTTPException(status_code=403, detail="Only owners can delete currencies")
    
    tenant = await db.tenants.find_one({"id": tenant_id}, {"_id": 0})
    base_currency = tenant.get("base_currency", "ZAR") if tenant else "ZAR"
    
    if code == base_currency:
        raise HTTPException(status_code=400, detail="Cannot delete base currency")
    
    exchange_rates = tenant.get("exchange_rates", []) if tenant else []
    exchange_rates = [r for r in exchange_rates if r["code"] != code]
    
    await db.tenants.update_one({"id": tenant_id}, {"$set": {"exchange_rates": exchange_rates}})
    
    return {"message": f"Currency {code} deleted"}

# ============ USER MANAGEMENT ROUTES ============

@router.get("/users", response_model=List[User])
async def list_users(tenant_id: str = Depends(get_tenant_id)):
    """List all users in tenant"""
    users = await db.users.find({"tenant_id": tenant_id}, {"_id": 0, "password_hash": 0}).to_list(1000)
    return users

class UserCreateWithPassword(BaseModel):
    """User creation model with password and security fields"""
    name: str
    email: EmailStr
    role: str = "warehouse"
    phone: Optional[str] = None
    password: Optional[str] = None  # Admin-set password
    role_title: Optional[str] = None  # Custom job title
    role_template: Optional[str] = "Warehouse"  # Owner/Manager/Warehouse/Finance/Driver
    custom_permissions: Optional[dict] = None  # Custom permissions JSON
    default_warehouse: Optional[str] = None
    allowed_warehouses: Optional[List[str]] = None  # Warehouse access restrictions

@router.post("/users", response_model=User)
async def create_user(
    user_data: UserCreateWithPassword,
    tenant_id: str = Depends(get_tenant_id),
    current_user: dict = Depends(get_current_user)
):
    """Create a new user in tenant with security fields"""
    if current_user.get("role") not in ["owner", "manager"]:
        raise HTTPException(status_code=403, detail="Insufficient permissions")
    
    # Check if email already exists
    existing = await db.users.find_one(
        {"email": user_data.email, "tenant_id": tenant_id}
    )
    if existing:
        raise HTTPException(status_code=400, detail="Email already exists in this tenant")
    
    user_id = str(uuid.uuid4())
    
    # Use admin-set password or generate temporary
    if user_data.password:
        password_hash = hash_password(user_data.password)
    else:
        temp_password = f"Temp{uuid.uuid4().hex[:8]}!"
        password_hash = hash_password(temp_password)
    
    doc = {
        "id": user_id,
        "tenant_id": tenant_id,
        "name": user_data.name,
        "email": user_data.email,
        "password_hash": password_hash,
        "role": user_data.role,
        "phone": user_data.phone,
        "status": "active",
        "picture": None,
        "role_title": user_data.role_title,
        "role_template": user_data.role_template,
        "custom_permissions": user_data.custom_permissions,
        "default_warehouse": user_data.default_warehouse,
        "allowed_warehouses": user_data.allowed_warehouses,
        "created_at": datetime.now(timezone.utc).isoformat()
    }
    await db.users.insert_one(doc)
    
    logger.info(f"Created user {user_data.email} with role {user_data.role}")
    
    # Return user without password_hash
    doc.pop("password_hash", None)
    return doc

class UserUpdateWithPassword(BaseModel):
    """User update model with password and security fields"""
    name: Optional[str] = None
    role: Optional[str] = None
    phone: Optional[str] = None
    status: Optional[str] = None
    password: Optional[str] = None  # New password (will be hashed)
    role_title: Optional[str] = None
    role_template: Optional[str] = None
    custom_permissions: Optional[dict] = None
    default_warehouse: Optional[str] = None
    allowed_warehouses: Optional[List[str]] = None

@router.put("/users/{user_id}")
async def update_user(
    user_id: str,
    update_data: UserUpdateWithPassword,
    tenant_id: str = Depends(get_tenant_id),
    current_user: dict = Depends(get_current_user)
):
    """Update a user including password and security fields"""
    # Check permissions
    if current_user.get("role") not in ["owner", "manager"] and current_user.get("id") != user_id:
        raise HTTPException(status_code=403, detail="Insufficient permissions")
    
    user = await db.users.find_one({"id": user_id, "tenant_id": tenant_id})
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    update_dict = {k: v for k, v in update_data.model_dump(exclude_unset=True).items()}
    
    # Handle password update - hash if provided
    if "password" in update_dict and update_dict["password"]:
        update_dict["password_hash"] = hash_password(update_dict["password"])
        del update_dict["password"]
        logger.info(f"Password updated for user {user_id}")
    elif "password" in update_dict:
        del update_dict["password"]  # Remove empty password field
    
    # Handle enum values
    if "role" in update_dict and hasattr(update_dict["role"], 'value'):
        update_dict["role"] = update_dict["role"].value
    if "status" in update_dict and hasattr(update_dict["status"], 'value'):
        update_dict["status"] = update_dict["status"].value
    
    if update_dict:
        await db.users.update_one({"id": user_id}, {"$set": update_dict})
    
    updated_user = await db.users.find_one({"id": user_id}, {"_id": 0, "password_hash": 0})
    return updated_user

@router.delete("/users/{user_id}")
async def delete_user(
    user_id: str,
    tenant_id: str = Depends(get_tenant_id),
    current_user: dict = Depends(get_current_user)
):
    """Delete a user (owner only)"""
    if current_user.get("role") != "owner":
        raise HTTPException(status_code=403, detail="Only owners can delete users")
    
    if current_user.get("id") == user_id:
        raise HTTPException(status_code=400, detail="Cannot delete yourself")
    
    result = await db.users.delete_one({"id": user_id, "tenant_id": tenant_id})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="User not found")
    
    # Also delete user sessions
    await db.user_sessions.delete_many({"user_id": user_id})
    
    return {"message": "User deleted successfully"}
