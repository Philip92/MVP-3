"""
Main application entry point for Servex Holdings backend.
Configures FastAPI app and wires up all route modules.
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import logging
import bcrypt
import uuid
from datetime import datetime, timezone

from config import APP_TITLE, APP_VERSION
from database import db
from routes import (
    auth_routes,
    client_routes,
    shipment_routes,
    trip_routes,
    invoice_routes,
    finance_routes,
    fleet_routes,
    warehouse_routes,
    team_routes,
    data_routes,
    recipient_routes,
    notes_routes,
    template_routes,
    printnode_routes,
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

async def create_default_admin():
    """Create default admin account if it doesn't exist"""
    admin_email = "admin@servex.com"
    admin_password = "Servex2026!"
    
    # Check if admin exists
    existing_admin = await db.users.find_one({"email": admin_email})
    if existing_admin:
        logger.info(f"Default admin account already exists: {admin_email}")
        return
    
    # Create tenant for admin
    tenant_id = str(uuid.uuid4())
    tenant_doc = {
        "id": tenant_id,
        "subdomain": "servex-admin",
        "company_name": "Servex Holdings",
        "logo_url": None,
        "primary_color": "#6B633C",
        "created_at": datetime.now(timezone.utc).isoformat()
    }
    await db.tenants.insert_one(tenant_doc)
    
    # Hash password
    salt = bcrypt.gensalt()
    password_hash = bcrypt.hashpw(admin_password.encode('utf-8'), salt).decode('utf-8')
    
    # Create admin user
    user_id = str(uuid.uuid4())
    user_doc = {
        "id": user_id,
        "tenant_id": tenant_id,
        "name": "Admin User",
        "email": admin_email,
        "password_hash": password_hash,
        "role": "owner",
        "phone": None,
        "status": "active",
        "picture": None,
        "created_at": datetime.now(timezone.utc).isoformat()
    }
    await db.users.insert_one(user_doc)
    
    logger.info(f"Created default admin account: {admin_email}")

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan handler"""
    # Startup
    logger.info("Starting up Servex Holdings API...")
    await create_default_admin()
    yield
    # Shutdown
    logger.info("Shutting down Servex Holdings API...")

# Create FastAPI app
app = FastAPI(title=APP_TITLE, version=APP_VERSION, lifespan=lifespan)

# CORS middleware (configure as needed)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure properly for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include all route modules with /api prefix
app.include_router(auth_routes.router, prefix="/api", tags=["Authentication"])
app.include_router(client_routes.router, prefix="/api", tags=["Clients"])
app.include_router(shipment_routes.router, prefix="/api", tags=["Shipments"])
app.include_router(trip_routes.router, prefix="/api", tags=["Trips"])
app.include_router(invoice_routes.router, prefix="/api", tags=["Invoices"])
app.include_router(finance_routes.router, prefix="/api", tags=["Finance"])
app.include_router(fleet_routes.router, prefix="/api", tags=["Fleet"])
app.include_router(warehouse_routes.router, prefix="/api", tags=["Warehouse"])
app.include_router(team_routes.router, prefix="/api", tags=["Team"])
app.include_router(data_routes.router, prefix="/api", tags=["Data"])
app.include_router(recipient_routes.router, prefix="/api", tags=["Recipients"])
app.include_router(notes_routes.router, prefix="/api", tags=["Notes"])

app.include_router(template_routes.router, prefix="/api", tags=["Templates"])
app.include_router(printnode_routes.router, prefix="/api", tags=["PrintNode"])

# Health check endpoint
@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy", "version": APP_VERSION}

# Root endpoint
@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "message": "Servex Holdings Logistics API",
        "version": APP_VERSION,
        "docs": "/docs"
    }

# Note: In production, uvicorn is started by supervisor with --port 8001
# This block is only used for local development
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8001)
