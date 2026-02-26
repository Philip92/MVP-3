"""
Client routes for Servex Holdings backend.
Handles client CRUD operations and client rate management.
"""
from fastapi import APIRouter, HTTPException, Depends, UploadFile, File
from fastapi.responses import StreamingResponse
from typing import List, Optional
from datetime import datetime, timezone
import csv
import io
import uuid

from database import db
from dependencies import get_current_user, get_tenant_id
from models.schemas import Client, ClientCreate, ClientUpdate, ClientRate, ClientRateCreate, ClientRateBase
from models.enums import ClientStatus

router = APIRouter()

@router.get("/clients", response_model=List[Client])
async def list_clients(tenant_id: str = Depends(get_tenant_id)):
    """List all clients"""
    clients = await db.clients.find({"tenant_id": tenant_id}, {"_id": 0}).to_list(1000)
    return clients

@router.get("/clients-with-stats")
async def list_clients_with_stats(
    trip_id: Optional[str] = None,
    sort_by: Optional[str] = "name",
    sort_order: Optional[str] = "asc",
    tenant_id: str = Depends(get_tenant_id)
):
    """List all clients with financial stats (rate, amount owed, total spent)"""
    
    # If filtering by trip, get client IDs that have parcels in that trip
    client_ids_filter = None
    if trip_id:
        parcels = await db.shipments.find(
            {"tenant_id": tenant_id, "trip_id": trip_id},
            {"client_id": 1, "_id": 0}
        ).to_list(10000)
        client_ids_filter = list(set(p["client_id"] for p in parcels if p.get("client_id")))
        if not client_ids_filter:
            return []
    
    # Build query
    query = {"tenant_id": tenant_id}
    if client_ids_filter:
        query["id"] = {"$in": client_ids_filter}
    
    clients = await db.clients.find(query, {"_id": 0}).to_list(1000)
    
    # Enrich with financial data
    result = []
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    
    for client in clients:
        client_id = client["id"]
        
        # Get current rate from client_rates or fall back to client's default rate
        rates = await db.client_rates.find(
            {"client_id": client_id},
            {"_id": 0}
        ).to_list(100)
        
        current_rate = None
        rate_type = None
        if rates:
            effective_rates = []
            for rate in rates:
                effective_from = rate.get("effective_from", "")
                if effective_from:
                    effective_date = effective_from[:10] if len(effective_from) >= 10 else effective_from
                    if effective_date <= today:
                        effective_rates.append((effective_date, rate))
            if effective_rates:
                effective_rates.sort(key=lambda x: x[0], reverse=True)
                rate_obj = effective_rates[0][1]
                current_rate = rate_obj.get("rate_per_kg") or rate_obj.get("rate_value") or 0
                rate_type = rate_obj.get("rate_type", "per_kg")
        
        # Fall back to client's default rate if no rate entries
        if current_rate is None:
            current_rate = client.get("default_rate_value")
            rate_type = client.get("default_rate_type", "per_kg")
        
        # Get invoices for this client
        invoices = await db.invoices.find(
            {"tenant_id": tenant_id, "client_id": client_id},
            {"_id": 0, "id": 1, "total": 1, "status": 1}
        ).to_list(1000)
        
        # Calculate amount owed (unpaid invoices) and total spent (paid invoices)
        amount_owed = 0
        total_spent = 0
        
        for inv in invoices:
            inv_total = inv.get("total", 0) or 0
            inv_status = inv.get("status", "")
            
            if inv_status == "paid":
                total_spent += inv_total
            elif inv_status in ["sent", "overdue", "draft"]:
                # Get payments for this invoice to subtract from owed
                payments = await db.payments.find(
                    {"invoice_id": inv["id"]},
                    {"_id": 0, "amount": 1}
                ).to_list(100)
                paid_amount = sum(p.get("amount", 0) for p in payments)
                amount_owed += (inv_total - paid_amount)
        
        result.append({
            **client,
            "current_rate": current_rate,
            "rate_type": rate_type,
            "amount_owed": round(amount_owed, 2),
            "total_spent": round(total_spent, 2)
        })
    
    # Sort results
    reverse = sort_order == "desc"
    if sort_by == "name":
        result.sort(key=lambda x: x.get("name", "").lower(), reverse=reverse)
    elif sort_by == "amount_owed":
        result.sort(key=lambda x: x.get("amount_owed", 0), reverse=reverse)
    elif sort_by == "total_spent":
        result.sort(key=lambda x: x.get("total_spent", 0), reverse=reverse)
    elif sort_by == "rate":
        result.sort(key=lambda x: x.get("current_rate") or 0, reverse=reverse)
    elif sort_by == "created_at":
        result.sort(key=lambda x: x.get("created_at", ""), reverse=reverse)
    
    return result

@router.get("/clients/{client_id}")
async def get_client(client_id: str, tenant_id: str = Depends(get_tenant_id)):
    """Get single client with auto-calculated total_amount_spent"""
    client = await db.clients.find_one({"id": client_id, "tenant_id": tenant_id}, {"_id": 0})
    if not client:
        raise HTTPException(status_code=404, detail="Client not found")
    
    # Auto-calculate total_amount_spent from paid invoices
    pipeline = [
        {"$match": {"client_id": client_id, "tenant_id": tenant_id, "status": {"$in": ["paid", "partial"]}}},
        {"$group": {"_id": None, "total": {"$sum": "$paid_amount"}}}
    ]
    result = await db.invoices.aggregate(pipeline).to_list(1)
    total_spent = result[0]["total"] if result else 0.0
    
    # Update in DB
    await db.clients.update_one(
        {"id": client_id, "tenant_id": tenant_id},
        {"$set": {"total_amount_spent": total_spent}}
    )
    client["total_amount_spent"] = total_spent
    
    return client

@router.post("/clients", response_model=Client)
async def create_client(
    client_data: ClientCreate,
    tenant_id: str = Depends(get_tenant_id)
):
    """Create a new client"""
    # Get tenant default rate if not provided
    if not client_data.default_rate_value or client_data.default_rate_value == 36.0:
        tenant = await db.tenants.find_one({"id": tenant_id}, {"_id": 0})
        if tenant:
            client_dict = client_data.model_dump()
            client_dict["default_rate_value"] = tenant.get("default_rate_value", 36.0)
            client_dict["default_rate_type"] = tenant.get("default_rate_type", "per_kg")
            client = Client(**client_dict, tenant_id=tenant_id)
        else:
            client = Client(**client_data.model_dump(), tenant_id=tenant_id)
    else:
        client = Client(**client_data.model_dump(), tenant_id=tenant_id)
    
    doc = client.model_dump()
    doc['created_at'] = doc['created_at'].isoformat()
    await db.clients.insert_one(doc)
    
    return client

@router.put("/clients/{client_id}")
async def update_client(
    client_id: str,
    update_data: ClientUpdate,
    tenant_id: str = Depends(get_tenant_id)
):
    """Update client"""
    update_dict = {k: v for k, v in update_data.model_dump().items() if v is not None}
    
    if update_dict:
        result = await db.clients.update_one(
            {"id": client_id, "tenant_id": tenant_id},
            {"$set": update_dict}
        )
        if result.matched_count == 0:
            raise HTTPException(status_code=404, detail="Client not found")
    
    client = await db.clients.find_one({"id": client_id, "tenant_id": tenant_id}, {"_id": 0})
    return client

@router.delete("/clients/{client_id}")
async def delete_client(client_id: str, tenant_id: str = Depends(get_tenant_id)):
    """Delete client"""
    result = await db.clients.delete_one({"id": client_id, "tenant_id": tenant_id})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Client not found")
    return {"message": "Client deleted"}


# ============ CSV EXPORT/IMPORT ============

@router.get("/clients/export/csv")
async def export_clients_csv(tenant_id: str = Depends(get_tenant_id)):
    """Export all clients to CSV - extended format."""
    clients = await db.clients.find(
        {"tenant_id": tenant_id, "status": {"$ne": "merged"}},
        {"_id": 0}
    ).sort("name", 1).to_list(5000)
    
    output = io.StringIO()
    fields = [
        "name", "company_name", "phone", "email", "whatsapp",
        "physical_address", "billing_address", "vat_number",
        "credit_limit", "payment_terms_days", "default_currency",
        "default_rate_type", "default_rate_value",
        "position", "primary_place_of_business", "nature_of_relationship",
        "owner", "frequency_of_business", "estimated_value_per_trip"
    ]
    
    writer = csv.DictWriter(output, fieldnames=fields)
    writer.writeheader()
    
    for client in clients:
        row = {}
        for f in fields:
            val = client.get(f)
            if val is None:
                if f == "default_currency":
                    val = "ZAR"
                elif f == "nature_of_relationship":
                    val = "Customer"
                elif f in ("credit_limit", "payment_terms_days", "default_rate_value", "estimated_value_per_trip"):
                    val = 0
                else:
                    val = ""
            row[f] = val
        writer.writerow(row)
    
    output.seek(0)
    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=clients.csv"}
    )


@router.post("/clients/import/csv")
async def import_clients_csv(
    file: UploadFile = File(...),
    tenant_id: str = Depends(get_tenant_id)
):
    """Import clients from CSV - creates new or updates existing by name (Session E)"""
    content = await file.read()
    decoded = content.decode("utf-8")
    reader = csv.DictReader(io.StringIO(decoded))
    
    created = 0
    updated = 0
    errors = []
    
    for i, row in enumerate(reader):
        try:
            name = row.get("name", "").strip()
            if not name:
                errors.append(f"Row {i+1}: Missing name field")
                continue
            
            client_data = {
                "name": name,
                "company_name": row.get("company_name", "").strip() or None,
                "email": row.get("email", "").strip() or None,
                "phone": row.get("phone", "").strip() or None,
                "vat_number": row.get("vat_number", "").strip() or None,
                "default_currency": row.get("default_currency", "ZAR").strip() or "ZAR",
                "position": row.get("position", "").strip() or None,
                "primary_place_of_business": row.get("primary_place_of_business", "").strip() or None,
                "nature_of_relationship": row.get("nature_of_relationship", "Customer").strip() or "Customer",
                "owner": row.get("owner", "").strip() or None,
                "frequency_of_business": row.get("frequency_of_business", "").strip() or None,
                "updated_at": datetime.now(timezone.utc).isoformat()
            }
            
            # Handle numeric fields
            rate_val = row.get("default_rate_value", "").strip()
            if rate_val:
                try:
                    client_data["default_rate_value"] = float(rate_val)
                except ValueError:
                    pass
            
            est_val = row.get("estimated_value_per_trip", "").strip()
            if est_val:
                try:
                    client_data["estimated_value_per_trip"] = float(est_val)
                except ValueError:
                    pass
            
            # Check if client exists
            existing = await db.clients.find_one({"tenant_id": tenant_id, "name": name})
            
            if existing:
                await db.clients.update_one(
                    {"tenant_id": tenant_id, "name": name},
                    {"$set": client_data}
                )
                updated += 1
            else:
                client_data["id"] = str(uuid.uuid4())
                client_data["tenant_id"] = tenant_id
                client_data["status"] = "active"
                client_data["aliases"] = []
                client_data["total_amount_spent"] = 0.0
                client_data["created_at"] = datetime.now(timezone.utc).isoformat()
                await db.clients.insert_one(client_data)
                created += 1
        except Exception as e:
            errors.append(f"Row {i+1}: {str(e)}")
    
    return {
        "success": True,
        "created": created,
        "updated": updated,
        "errors": errors
    }

# ============ CLIENT RATES ROUTES ============

@router.get("/clients/{client_id}/rate")
async def get_client_current_rate(
    client_id: str,
    tenant_id: str = Depends(get_tenant_id)
):
    """Get the current/latest rate for a client"""
    # Verify client belongs to tenant
    client = await db.clients.find_one({"id": client_id, "tenant_id": tenant_id}, {"_id": 0})
    if not client:
        raise HTTPException(status_code=404, detail="Client not found")
    
    # Get all rates for this client and find the most recent effective one
    all_rates = await db.client_rates.find(
        {"client_id": client_id},
        {"_id": 0}
    ).to_list(100)
    
    if not all_rates:
        return {"client_id": client_id, "rate_per_kg": None, "message": "No rate set for this client"}
    
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    
    # Filter rates that are effective (effective_from <= today)
    # Handle both date-only and full ISO timestamp formats
    effective_rates = []
    for rate in all_rates:
        effective_from = rate.get("effective_from", "")
        if effective_from:
            # Extract just the date part (first 10 chars) for comparison
            effective_date = effective_from[:10] if len(effective_from) >= 10 else effective_from
            if effective_date <= today:
                effective_rates.append((effective_date, rate))
    
    if effective_rates:
        # Sort by effective_date descending and get the most recent
        effective_rates.sort(key=lambda x: x[0], reverse=True)
        rate = effective_rates[0][1]
        
        # Normalize the response - support both rate_value and rate_per_kg field names
        rate_per_kg = rate.get("rate_per_kg") or rate.get("rate_value") or 0
        
        return {
            **rate,
            "rate_per_kg": rate_per_kg  # Ensure rate_per_kg is always present
        }
    
    # No effective rate found
    return {"client_id": client_id, "rate_per_kg": None, "message": "No rate set for this client"}

@router.get("/clients/{client_id}/rates", response_model=List[ClientRate])
async def list_client_rates(
    client_id: str,
    tenant_id: str = Depends(get_tenant_id)
):
    """List rates for a client"""
    # Verify client belongs to tenant
    client = await db.clients.find_one({"id": client_id, "tenant_id": tenant_id}, {"_id": 0})
    if not client:
        raise HTTPException(status_code=404, detail="Client not found")
    
    rates = await db.client_rates.find({"client_id": client_id}, {"_id": 0}).to_list(100)
    return rates

@router.post("/clients/{client_id}/rates", response_model=ClientRate)
async def create_client_rate(
    client_id: str,
    rate_data: ClientRateBase,
    tenant_id: str = Depends(get_tenant_id),
    user: dict = Depends(get_current_user)
):
    """Create rate for a client"""
    # Verify client belongs to tenant
    client = await db.clients.find_one({"id": client_id, "tenant_id": tenant_id}, {"_id": 0})
    if not client:
        raise HTTPException(status_code=404, detail="Client not found")
    
    rate = ClientRate(
        **rate_data.model_dump(),
        client_id=client_id,
        created_by=user["id"]
    )
    
    if not rate.effective_from:
        rate.effective_from = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    
    doc = rate.model_dump()
    doc['created_at'] = doc['created_at'].isoformat()
    await db.client_rates.insert_one(doc)
    
    return rate


# SESSION G: Collection Workflow Endpoints

@router.get("/clients/{client_id}/outstanding-balance")
async def get_client_outstanding_balance(
    client_id: str,
    tenant_id: str = Depends(get_tenant_id)
):
    """Calculate total outstanding balance for a client (SESSION G)"""
    
    # Verify client exists
    client = await db.clients.find_one({"id": client_id, "tenant_id": tenant_id}, {"_id": 0})
    if not client:
        raise HTTPException(status_code=404, detail="Client not found")
    
    # Get unpaid/partial invoices
    invoices = await db.invoices.find({
        "tenant_id": tenant_id,
        "client_id": client_id,
        "status": {"$in": ["draft", "sent", "overdue", "partial"]}
    }, {"_id": 0}).to_list(1000)
    
    invoice_outstanding = sum(
        inv.get("total", 0) - inv.get("paid_amount", 0)
        for inv in invoices
    )
    
    # Get uninvoiced parcels ready for collection
    uninvoiced = await db.shipments.find({
        "tenant_id": tenant_id,
        "client_id": client_id,
        "$or": [
            {"invoice_id": None},
            {"invoice_id": {"$exists": False}}
        ],
        "status": {"$in": ["warehouse", "arrived"]}
    }, {"_id": 0}).to_list(1000)
    
    # Estimate uninvoiced value
    client_rate_doc = await db.client_rates.find_one({
        "client_id": client_id,
        "status": "active"
    }, {"_id": 0})
    
    rate_per_kg = client_rate_doc.get("rate_per_kg", 50) if client_rate_doc else 50
    
    uninvoiced_estimated = sum(
        (p.get("weight", 5) * rate_per_kg) for p in uninvoiced
    )
    
    return {
        "client_id": client_id,
        "client_name": client.get("name"),
        "invoice_outstanding": round(invoice_outstanding, 2),
        "uninvoiced_count": len(uninvoiced),
        "uninvoiced_estimated": round(uninvoiced_estimated, 2),
        "total_outstanding": round(invoice_outstanding + uninvoiced_estimated, 2),
        "has_outstanding": (invoice_outstanding + uninvoiced_estimated) > 0,
        "invoices": [
            {
                "id": inv["id"],
                "invoice_number": inv.get("invoice_number"),
                "total": inv.get("total"),
                "paid_amount": inv.get("paid_amount", 0),
                "outstanding": inv.get("total", 0) - inv.get("paid_amount", 0),
                "due_date": inv.get("due_date"),
                "status": inv.get("status")
            }
            for inv in invoices
        ],
        "uninvoiced_parcels": [
            {
                "id": p["id"],
                "barcode": p.get("barcode"),
                "description": p.get("description"),
                "weight": p.get("weight"),
                "status": p.get("status")
            }
            for p in uninvoiced[:20]
        ]
    }

