"""
Data management routes for Servex Holdings backend.
Handles data reset, CSV import, and data export operations.
"""
from fastapi import APIRouter, HTTPException, Depends, UploadFile, File
from typing import List, Optional
from datetime import datetime, timezone
import csv
import io
import uuid

from database import db
from dependencies import get_current_user, get_tenant_id
from services.barcode_service import generate_barcode

router = APIRouter()

# ============ DATA RESET ============

@router.post("/data/reset")
async def reset_tenant_data(
    tenant_id: str = Depends(get_tenant_id),
    user: dict = Depends(get_current_user)
):
    """
    Delete all operational data for the current tenant.
    Preserves: users, tenant settings, warehouses
    """
    # Verify user is owner
    if user.get("role") != "owner":
        raise HTTPException(status_code=403, detail="Only owners can reset data")
    
    # Count before deletion for summary
    counts = {
        "clients": await db.clients.count_documents({"tenant_id": tenant_id}),
        "shipments": await db.shipments.count_documents({"tenant_id": tenant_id}),
        "shipment_pieces": await db.shipment_pieces.count_documents({}),  # Will filter by shipment
        "trips": await db.trips.count_documents({"tenant_id": tenant_id}),
        "invoices": await db.invoices.count_documents({"tenant_id": tenant_id}),
        "payments": await db.payments.count_documents({"tenant_id": tenant_id}),
        "expenses": await db.expenses.count_documents({"tenant_id": tenant_id}),
        "notifications": await db.notifications.count_documents({"tenant_id": tenant_id}),
    }
    
    # Get shipment IDs to delete pieces
    shipment_ids = await db.shipments.distinct("id", {"tenant_id": tenant_id})
    
    # Delete in order (respecting foreign key-like relationships)
    await db.notifications.delete_many({"tenant_id": tenant_id})
    await db.payments.delete_many({"tenant_id": tenant_id})
    await db.expenses.delete_many({"tenant_id": tenant_id})
    await db.invoice_line_items.delete_many({"tenant_id": tenant_id})
    await db.invoice_adjustments.delete_many({"tenant_id": tenant_id})
    await db.invoices.delete_many({"tenant_id": tenant_id})
    await db.shipment_pieces.delete_many({"shipment_id": {"$in": shipment_ids}})
    await db.shipments.delete_many({"tenant_id": tenant_id})
    await db.trips.delete_many({"tenant_id": tenant_id})
    await db.clients.delete_many({"tenant_id": tenant_id})
    await db.client_rates.delete_many({"tenant_id": tenant_id})
    
    # Also delete recipients if collection exists
    try:
        await db.recipients.delete_many({"tenant_id": tenant_id})
    except Exception:
        pass
    
    return {
        "message": "Data reset complete",
        "deleted": {
            "clients": counts["clients"],
            "parcels": counts["shipments"],
            "trips": counts["trips"],
            "invoices": counts["invoices"],
            "payments": counts["payments"],
            "expenses": counts["expenses"],
            "notifications": counts["notifications"]
        },
        "summary": f"{counts['clients']} clients deleted, {counts['trips']} trips deleted, {counts['shipments']} parcels deleted"
    }

# ============ CSV IMPORT ============

@router.post("/import/parcels")
async def import_parcels_from_csv(
    file: UploadFile = File(...),
    warehouse_id: Optional[str] = None,
    tenant_id: str = Depends(get_tenant_id),
    user: dict = Depends(get_current_user)
):
    """
    Import parcels from CSV file.
    Expected columns: Sent By, Primary Recipient, Secondary Recipient, Description, QTY, KG, L, W, H
    If warehouse_id is provided, all parcels go to that warehouse.
    Otherwise, parcels alternate between available warehouses.
    """
    if not file.filename.endswith('.csv'):
        raise HTTPException(status_code=400, detail="File must be a CSV")
    
    # Read CSV content
    content = await file.read()
    text_content = content.decode('utf-8')
    
    # Parse CSV
    reader = csv.DictReader(io.StringIO(text_content))
    
    # Get tenant settings for default rate
    tenant = await db.tenants.find_one({"id": tenant_id}, {"_id": 0})
    default_rate_value = tenant.get("default_rate_value", 36.0) if tenant else 36.0
    default_rate_type = tenant.get("default_rate_type", "per_kg") if tenant else "per_kg"
    
    # Get warehouses
    warehouses = await db.warehouses.find(
        {"tenant_id": tenant_id, "status": "active"},
        {"_id": 0}
    ).to_list(100)
    
    # If specific warehouse provided, use only that one
    target_warehouse = None
    if warehouse_id:
        target_warehouse = next((w for w in warehouses if w["id"] == warehouse_id), None)
        if not target_warehouse:
            raise HTTPException(status_code=400, detail="Warehouse not found")
    elif len(warehouses) < 1:
        raise HTTPException(status_code=400, detail="No active warehouses found")
    
    warehouse_a = warehouses[0] if len(warehouses) > 0 else None
    warehouse_b = warehouses[1] if len(warehouses) > 1 else warehouse_a
    
    # Track stats
    stats = {
        "total_rows": 0,
        "skipped_zero_weight": 0,
        "skipped_missing_description": 0,
        "parcels_created": 0,
        "clients_created": 0,
        "clients_matched": 0,
        "warehouse_a_count": 0,
        "warehouse_b_count": 0,
        "total_weight": 0.0
    }
    
    # Client cache
    client_cache = {}
    
    # Process each row
    row_index = 0
    for row in reader:
        stats["total_rows"] += 1
        
        # Get weight - skip if 0
        try:
            weight = float(row.get('KG', 0) or 0)
        except ValueError:
            weight = 0
        
        if weight == 0:
            stats["skipped_zero_weight"] += 1
            continue
        
        # Get dimensions
        try:
            length = float(row.get('L', 0) or 0)
            width = float(row.get('W', 0) or 0)
            height = float(row.get('H', 0) or 0)
        except ValueError:
            length = width = height = 0
        
        # Get quantity
        try:
            qty = int(row.get('QTY', 1) or 1)
        except ValueError:
            qty = 1
        
        # Get client name from "Sent By"
        client_name = (row.get('Sent By', '') or '').strip()
        if not client_name:
            continue
        
        # Find or create client
        client_key = client_name.lower()
        if client_key in client_cache:
            client = client_cache[client_key]
            stats["clients_matched"] += 1
        else:
            # Check if client exists (case-insensitive)
            existing_client = await db.clients.find_one(
                {"tenant_id": tenant_id, "name": {"$regex": f"^{client_name}$", "$options": "i"}},
                {"_id": 0}
            )
            
            if existing_client:
                client = existing_client
                stats["clients_matched"] += 1
            else:
                # Create new client with default rate from tenant settings
                client = {
                    "id": str(uuid.uuid4()),
                    "tenant_id": tenant_id,
                    "name": client_name,
                    "phone": None,
                    "email": None,
                    "whatsapp": None,
                    "physical_address": None,
                    "default_currency": "ZAR",
                    "default_rate_type": default_rate_type,
                    "default_rate_value": default_rate_value,
                    "credit_limit": 0,
                    "payment_terms_days": 30,
                    "status": "active",
                    "created_at": datetime.now(timezone.utc).isoformat()
                }
                await db.clients.insert_one(client)
                stats["clients_created"] += 1
            
            client_cache[client_key] = client
        
        # Get sender from Secondary Recipient or fall back to Sent By
        sender = (row.get('Secondary Recipient', '') or '').strip() or client_name
        description = (row.get('Description', '') or '').strip()
        
        # Skip if description is empty
        if not description:
            stats["skipped_missing_description"] += 1
            continue
        
        # Calculate volumetric weight
        volumetric_weight = (length * width * height) / 5000 if (length and width and height) else 0
        chargeable_weight = max(weight, volumetric_weight)
        
        # Create parcels based on quantity
        for i in range(qty):
            row_index += 1
            
            # Use target warehouse if specified, otherwise alternate
            if target_warehouse:
                warehouse = target_warehouse
                stats["warehouse_a_count"] += 1  # Count all as warehouse_a when specific
            elif row_index % 2 == 1:
                warehouse = warehouse_a
                stats["warehouse_a_count"] += 1
            else:
                warehouse = warehouse_b
                stats["warehouse_b_count"] += 1
            
            # Create shipment with parcel sequence for QTY > 1
            shipment_id = str(uuid.uuid4())
            shipment = {
                "id": shipment_id,
                "tenant_id": tenant_id,
                "client_id": client["id"],
                "trip_id": None,  # Not assigned to any trip
                "recipient": row.get('Primary Recipient', '') or client_name,
                "sender": sender,
                "description": description,
                "quantity": 1,  # Each parcel is individual
                "total_weight": weight,
                "total_cbm": None,
                "total_pieces": 1,
                "destination": "TBD",
                "status": "warehouse",
                "warehouse_id": warehouse["id"],
                "length_cm": length,
                "width_cm": width,
                "height_cm": height,
                "volumetric_weight": round(volumetric_weight, 2),
                "chargeable_weight": round(chargeable_weight, 2),
                # Parcel sequence numbering (e.g., 1 of 5, 2 of 5...)
                "parcel_sequence": i + 1 if qty > 1 else None,
                "total_in_sequence": qty if qty > 1 else None,
                "created_by": user["id"],
                "created_at": datetime.now(timezone.utc).isoformat()
            }
            await db.shipments.insert_one(shipment)
            
            # Create piece with barcode
            barcode = generate_barcode(None, stats["parcels_created"] + 1, 1)
            piece = {
                "id": str(uuid.uuid4()),
                "shipment_id": shipment_id,
                "piece_number": 1,
                "weight": weight,
                "length_cm": length,
                "width_cm": width,
                "height_cm": height,
                "barcode": barcode,
                "photo_url": None,
                "loaded_at": None
            }
            await db.shipment_pieces.insert_one(piece)
            
            stats["parcels_created"] += 1
            stats["total_weight"] += weight
    
    # Build summary message
    if target_warehouse:
        summary = f"Imported {stats['parcels_created']} parcels for {stats['clients_created'] + stats['clients_matched']} clients to {target_warehouse['name']}. Total weight: {round(stats['total_weight'], 2)} kg"
    else:
        summary = f"Imported {stats['parcels_created']} parcels for {stats['clients_created'] + stats['clients_matched']} clients. {stats['warehouse_a_count']} parcels to {warehouse_a['name']}, {stats['warehouse_b_count']} parcels to {warehouse_b['name'] if warehouse_b else 'N/A'}. Total weight: {round(stats['total_weight'], 2)} kg"
    
    return {
        "message": "CSV import complete",
        "summary": summary,
        "details": stats,
        "warehouses": {
            "warehouse_a": warehouse_a["name"] if warehouse_a else None,
            "warehouse_b": warehouse_b["name"] if warehouse_b else None,
            "target_warehouse": target_warehouse["name"] if target_warehouse else None
        }
    }


# ============ CLIENT CSV IMPORT/EXPORT ============

@router.post("/import/clients")
async def import_clients_from_csv(
    file: UploadFile = File(...),
    tenant_id: str = Depends(get_tenant_id),
    user: dict = Depends(get_current_user)
):
    """
    Import clients from CSV file.
    Expected columns: Client Name, Phone, Email, VAT No, Physical Address, Billing Address, Rate
    """
    if not file.filename.endswith('.csv'):
        raise HTTPException(status_code=400, detail="File must be a CSV")
    
    # Read CSV content
    content = await file.read()
    text_content = content.decode('utf-8')
    
    # Get tenant settings for default rate
    tenant = await db.tenants.find_one({"id": tenant_id}, {"_id": 0})
    default_rate_value = tenant.get("default_rate_value", 36.0) if tenant else 36.0
    default_rate_type = tenant.get("default_rate_type", "per_kg") if tenant else "per_kg"
    
    # Parse CSV - try to detect headers
    lines = text_content.strip().split('\n')
    if not lines:
        raise HTTPException(status_code=400, detail="Empty CSV file")
    
    # Check for headers
    first_line = lines[0].lower()
    has_headers = 'client name' in first_line or 'name' in first_line
    
    if has_headers:
        reader = csv.DictReader(io.StringIO(text_content))
    else:
        # No headers - use positional columns
        reader = csv.reader(io.StringIO(text_content))
    
    # Track stats
    stats = {
        "imported": 0,
        "skipped": 0,
        "duplicates": 0
    }
    
    # Get existing client names for duplicate detection
    existing_clients = await db.clients.find(
        {"tenant_id": tenant_id},
        {"_id": 0, "name": 1}
    ).to_list(10000)
    existing_names = {c["name"].lower() for c in existing_clients}
    
    now = datetime.now(timezone.utc).isoformat()
    
    for row in reader:
        if has_headers:
            # Dict reader
            name = (row.get('Client Name') or row.get('client name') or row.get('name') or row.get('Name') or '').strip()
            phone = (row.get('Phone') or row.get('phone') or '').strip()
            email = (row.get('Email') or row.get('email') or '').strip()
            vat_number = (row.get('VAT No') or row.get('vat_number') or row.get('VAT') or '').strip()
            physical_address = (row.get('Physical Address') or row.get('physical_address') or row.get('Address') or '').strip()
            billing_address = (row.get('Billing Address') or row.get('billing_address') or '').strip() or physical_address
            rate_str = (row.get('Rate') or row.get('rate') or '').strip()
        else:
            # List reader - positional
            parts = [p.strip().replace('"', '').replace("'", "") for p in row]
            name = parts[0] if len(parts) > 0 else ''
            phone = parts[1] if len(parts) > 1 else ''
            email = parts[2] if len(parts) > 2 else ''
            vat_number = parts[3] if len(parts) > 3 else ''
            physical_address = parts[4] if len(parts) > 4 else ''
            billing_address = parts[5] if len(parts) > 5 else physical_address
            rate_str = parts[6] if len(parts) > 6 else ''
        
        # Skip empty names
        if not name:
            stats["skipped"] += 1
            continue
        
        # Check for duplicates
        if name.lower() in existing_names:
            stats["duplicates"] += 1
            continue
        
        # Parse rate
        try:
            rate_value = float(rate_str) if rate_str else default_rate_value
        except ValueError:
            rate_value = default_rate_value
        
        # Create client
        client_id = str(uuid.uuid4())
        client = {
            "id": client_id,
            "tenant_id": tenant_id,
            "name": name,
            "phone": phone,
            "whatsapp": phone,  # Use phone as WhatsApp by default
            "email": email,
            "vat_number": vat_number,
            "physical_address": physical_address,
            "billing_address": billing_address,
            "default_currency": "ZAR",
            "default_rate_type": default_rate_type,
            "default_rate_value": rate_value,
            "status": "active",
            "aliases": [],  # Empty aliases list
            "created_at": now,
            "created_by": user["id"]
        }
        
        await db.clients.insert_one(client)
        existing_names.add(name.lower())
        stats["imported"] += 1
    
    summary = f"Imported {stats['imported']} clients successfully."
    if stats["skipped"] > 0:
        summary += f" {stats['skipped']} rows skipped (missing name)."
    if stats["duplicates"] > 0:
        summary += f" {stats['duplicates']} duplicates skipped."
    
    return {
        "message": "Client import complete",
        "summary": summary,
        "details": stats
    }


@router.get("/export/clients")
async def export_clients_to_csv(
    tenant_id: str = Depends(get_tenant_id),
    user: dict = Depends(get_current_user)
):
    """
    Export all clients to CSV format.
    """
    from fastapi.responses import StreamingResponse
    
    # Get all active clients
    clients = await db.clients.find(
        {"tenant_id": tenant_id, "status": {"$ne": "merged"}},
        {"_id": 0}
    ).to_list(10000)
    
    # Build CSV content
    output = io.StringIO()
    writer = csv.writer(output)
    
    # Write headers
    writer.writerow(['Client Name', 'Phone', 'Email', 'VAT No', 'Physical Address', 'Billing Address', 'Rate'])
    
    # Write client rows
    for client in clients:
        writer.writerow([
            client.get('name', ''),
            client.get('phone', ''),
            client.get('email', ''),
            client.get('vat_number', ''),
            client.get('physical_address', ''),
            client.get('billing_address', ''),
            client.get('default_rate_value', 36.0)
        ])
    
    # Return as streaming response
    output.seek(0)
    
    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename=Servex_Clients_Export_{datetime.now().strftime('%Y-%m-%d')}.csv"}
    )



# ============ DATA MIGRATION ============

@router.post("/data/fix-invoice-line-items")
async def fix_invoice_line_items(
    tenant_id: str = Depends(get_tenant_id),
    user: dict = Depends(get_current_user)
):
    """
    Migration endpoint to fix existing invoice line items.
    Fixes issues where:
    - 'quantity' was storing weight values instead of actual quantity
    - 'weight' field was null
    - dimensions were not populated
    
    For each line item with shipment_id, fetches the actual parcel data
    and updates the line item with correct values.
    """
    if user.get("role") != "owner":
        raise HTTPException(status_code=403, detail="Only owners can run migrations")
    
    # Get all line items for this tenant's invoices
    invoices = await db.invoices.find(
        {"tenant_id": tenant_id},
        {"_id": 0, "id": 1, "trip_id": 1}
    ).to_list(10000)
    
    invoice_map = {inv["id"]: inv for inv in invoices}
    invoice_ids = [inv["id"] for inv in invoices]
    
    line_items = await db.invoice_line_items.find(
        {"invoice_id": {"$in": invoice_ids}},
        {"_id": 0}
    ).to_list(10000)
    
    # Get all shipments for matching
    all_trip_ids = list(set(inv.get("trip_id") for inv in invoices if inv.get("trip_id")))
    all_shipments = await db.shipments.find(
        {"trip_id": {"$in": all_trip_ids}},
        {"_id": 0}
    ).to_list(10000)
    
    # Create lookup maps
    shipment_by_id = {s["id"]: s for s in all_shipments}
    
    # Create a map of shipments by (trip_id, description, weight) for fuzzy matching
    shipment_by_desc_weight = {}
    for s in all_shipments:
        key = (s.get("trip_id"), s.get("description", "").lower().strip(), round(s.get("total_weight", 0), 1))
        shipment_by_desc_weight[key] = s
    
    # Fix each line item
    fixed_count = 0
    for li in line_items:
        shipment_id = li.get("shipment_id")
        invoice_id = li.get("invoice_id")
        update_fields = {}
        shipment = None
        
        # First try to find by shipment_id
        if shipment_id and shipment_id in shipment_by_id:
            shipment = shipment_by_id[shipment_id]
        
        # If no shipment_id, try to match by description and weight
        if not shipment and invoice_id in invoice_map:
            invoice = invoice_map[invoice_id]
            trip_id = invoice.get("trip_id")
            if trip_id:
                # Try to match by description and the quantity value (which might be weight)
                desc = (li.get("description") or "").lower().strip()
                weight_guess = round(li.get("quantity", 0), 1)  # Old data stores weight in quantity
                key = (trip_id, desc, weight_guess)
                if key in shipment_by_desc_weight:
                    shipment = shipment_by_desc_weight[key]
        
        if shipment:
            # Update from shipment data
            if shipment.get("total_weight") is not None:
                update_fields["weight"] = shipment.get("total_weight")
            
            # Fix quantity field
            update_fields["quantity"] = shipment.get("quantity", 1) or 1
            
            # Fix dimensions
            if shipment.get("length_cm") is not None:
                update_fields["length_cm"] = shipment.get("length_cm")
            if shipment.get("width_cm") is not None:
                update_fields["width_cm"] = shipment.get("width_cm")
            if shipment.get("height_cm") is not None:
                update_fields["height_cm"] = shipment.get("height_cm")
            
            # Fix shipment_id if missing
            if not li.get("shipment_id"):
                update_fields["shipment_id"] = shipment.get("id")
            
            # Fix recipient name if missing
            if not li.get("recipient_name") and shipment.get("recipient"):
                update_fields["recipient_name"] = shipment.get("recipient")
        
        if update_fields:
            await db.invoice_line_items.update_one(
                {"id": li["id"]},
                {"$set": update_fields}
            )
            fixed_count += 1
    
    return {
        "message": "Line items migration complete",
        "total_line_items": len(line_items),
        "fixed_count": fixed_count
    }
