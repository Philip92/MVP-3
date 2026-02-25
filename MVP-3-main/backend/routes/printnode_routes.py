"""
PrintNode integration routes for Servex Holdings backend.
Handles printer configuration, print job submission, and status checks.
"""
from fastapi import APIRouter, HTTPException, Depends
from typing import Optional
from datetime import datetime, timezone
import httpx
import uuid
import base64

from database import db
from dependencies import get_current_user, get_tenant_id

router = APIRouter()

PRINTNODE_API_URL = "https://api.printnode.com"


async def get_printnode_config(tenant_id: str):
    """Get PrintNode configuration for a tenant."""
    config = await db.printnode_config.find_one({"tenant_id": tenant_id}, {"_id": 0})
    return config


async def get_printnode_client(tenant_id: str):
    """Get an authenticated httpx client for PrintNode API."""
    config = await get_printnode_config(tenant_id)
    if not config or not config.get("api_key"):
        raise HTTPException(status_code=400, detail="PrintNode API key not configured. Go to Settings > PrintNode to add your key.")
    
    return config["api_key"]


# ============ CONFIGURATION ============

@router.get("/printnode/config")
async def get_config(tenant_id: str = Depends(get_tenant_id)):
    """Get PrintNode configuration (API key masked)."""
    config = await get_printnode_config(tenant_id)
    if not config:
        return {"configured": False, "api_key_set": False, "default_printer_id": None}
    
    return {
        "configured": True,
        "api_key_set": bool(config.get("api_key")),
        "api_key_preview": config["api_key"][:8] + "..." if config.get("api_key") else None,
        "default_printer_id": config.get("default_printer_id"),
        "default_printer_name": config.get("default_printer_name"),
        "updated_at": config.get("updated_at")
    }


@router.post("/printnode/config")
async def save_config(
    data: dict,
    tenant_id: str = Depends(get_tenant_id),
    user: dict = Depends(get_current_user)
):
    """Save PrintNode API key and default printer configuration."""
    api_key = data.get("api_key", "").strip()
    default_printer_id = data.get("default_printer_id")
    default_printer_name = data.get("default_printer_name")
    
    if not api_key:
        raise HTTPException(status_code=400, detail="API key is required")
    
    # Validate the API key by testing it
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{PRINTNODE_API_URL}/whoami",
                auth=(api_key, "")
            )
            if response.status_code != 200:
                raise HTTPException(
                    status_code=400, 
                    detail=f"Invalid PrintNode API key. Status: {response.status_code}"
                )
            account_info = response.json()
    except httpx.ConnectError:
        raise HTTPException(status_code=503, detail="Cannot connect to PrintNode API. Check your internet connection.")
    
    config = {
        "tenant_id": tenant_id,
        "api_key": api_key,
        "default_printer_id": default_printer_id,
        "default_printer_name": default_printer_name,
        "account_email": account_info.get("email"),
        "account_name": f"{account_info.get('firstname', '')} {account_info.get('lastname', '')}".strip(),
        "updated_at": datetime.now(timezone.utc).isoformat(),
        "updated_by": user["id"]
    }
    
    await db.printnode_config.update_one(
        {"tenant_id": tenant_id},
        {"$set": config},
        upsert=True
    )
    
    return {
        "success": True,
        "message": "PrintNode configured successfully",
        "account_name": config["account_name"],
        "account_email": config["account_email"]
    }


@router.delete("/printnode/config")
async def delete_config(
    tenant_id: str = Depends(get_tenant_id),
    user: dict = Depends(get_current_user)
):
    """Remove PrintNode configuration."""
    await db.printnode_config.delete_one({"tenant_id": tenant_id})
    return {"success": True, "message": "PrintNode configuration removed"}


# ============ PRINTERS ============

@router.get("/printnode/printers")
async def list_printers(tenant_id: str = Depends(get_tenant_id)):
    """List all available printers from PrintNode account."""
    api_key = await get_printnode_client(tenant_id)
    
    async with httpx.AsyncClient() as client:
        response = await client.get(
            f"{PRINTNODE_API_URL}/printers",
            auth=(api_key, "")
        )
        
        if response.status_code != 200:
            raise HTTPException(status_code=response.status_code, detail="Failed to fetch printers")
        
        printers = response.json()
    
    return {
        "printers": [
            {
                "id": p.get("id"),
                "name": p.get("name"),
                "description": p.get("description"),
                "state": p.get("state"),
                "computer_name": p.get("computer", {}).get("name"),
                "computer_id": p.get("computer", {}).get("id")
            }
            for p in printers
        ]
    }


@router.post("/printnode/default-printer")
async def set_default_printer(
    data: dict,
    tenant_id: str = Depends(get_tenant_id),
    user: dict = Depends(get_current_user)
):
    """Set the default printer."""
    printer_id = data.get("printer_id")
    printer_name = data.get("printer_name", "")
    
    await db.printnode_config.update_one(
        {"tenant_id": tenant_id},
        {"$set": {
            "default_printer_id": printer_id,
            "default_printer_name": printer_name,
            "updated_at": datetime.now(timezone.utc).isoformat()
        }}
    )
    
    return {"success": True, "message": f"Default printer set to {printer_name}"}


# ============ PRINT JOBS ============

@router.post("/printnode/print")
async def submit_print_job(
    data: dict,
    tenant_id: str = Depends(get_tenant_id),
    user: dict = Depends(get_current_user)
):
    """Submit a print job to PrintNode.
    
    Body:
    - printer_id (optional, uses default if not set)
    - title: Job title
    - content_type: "pdf_base64" | "raw_uri" | "pdf_uri"
    - content: Base64 encoded PDF data or URI
    - source: Where the print request originated (e.g., "warehouse_label", "invoice")
    - copies: Number of copies (default 1)
    """
    api_key = await get_printnode_client(tenant_id)
    config = await get_printnode_config(tenant_id)
    
    printer_id = data.get("printer_id") or config.get("default_printer_id")
    if not printer_id:
        raise HTTPException(status_code=400, detail="No printer specified and no default printer set")
    
    title = data.get("title", "Servex Print Job")
    content_type = data.get("content_type", "pdf_base64")
    content = data.get("content", "")
    copies = data.get("copies", 1)
    source = data.get("source", "manual")
    
    if not content:
        raise HTTPException(status_code=400, detail="No content provided for printing")
    
    # Map content type to PrintNode format
    pn_content_type = "pdf_base64"
    if content_type == "raw_uri":
        pn_content_type = "raw_uri"
    elif content_type == "pdf_uri":
        pn_content_type = "pdf_uri"
    
    printjob_payload = {
        "printerId": int(printer_id),
        "title": title,
        "contentType": pn_content_type,
        "content": content,
        "source": f"servex-{source}",
        "qty": copies
    }
    
    async with httpx.AsyncClient() as client:
        response = await client.post(
            f"{PRINTNODE_API_URL}/printjobs",
            json=printjob_payload,
            auth=(api_key, "")
        )
        
        if response.status_code not in [200, 201]:
            error_detail = response.text
            raise HTTPException(
                status_code=response.status_code, 
                detail=f"PrintNode error: {error_detail}"
            )
        
        job_id = response.json()
    
    # Log the print job
    await db.print_jobs.insert_one({
        "id": str(uuid.uuid4()),
        "tenant_id": tenant_id,
        "printnode_job_id": job_id,
        "printer_id": str(printer_id),
        "title": title,
        "source": source,
        "copies": copies,
        "status": "submitted",
        "created_by": user["id"],
        "created_at": datetime.now(timezone.utc).isoformat()
    })
    
    return {
        "success": True,
        "job_id": job_id,
        "message": f"Print job submitted to printer"
    }


@router.get("/printnode/jobs")
async def list_print_jobs(
    limit: int = 20,
    tenant_id: str = Depends(get_tenant_id)
):
    """List recent print jobs."""
    jobs = await db.print_jobs.find(
        {"tenant_id": tenant_id},
        {"_id": 0}
    ).sort("created_at", -1).limit(limit).to_list(limit)
    
    return {"jobs": jobs}
