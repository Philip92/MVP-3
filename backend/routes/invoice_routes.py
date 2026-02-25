"""
Invoice routes for Servex Holdings backend.
Handles invoice CRUD, line items, payments, and PDF generation.
"""
from fastapi import APIRouter, HTTPException, Depends, Request
from fastapi.responses import StreamingResponse
from typing import List, Optional
from datetime import datetime, timezone
from io import BytesIO
import uuid

from database import db
from dependencies import get_current_user, get_tenant_id, build_warehouse_filter, check_permission
from models.schemas import Invoice, InvoiceCreate, InvoiceUpdate, InvoiceLineItem, InvoiceLineItemCreate, InvoiceAdjustmentInput, Payment, PaymentCreate, InvoiceCreateEnhanced, InvoiceUpdateEnhanced, create_audit_log
from models.enums import InvoiceStatus, PaymentMethod, AuditAction
from services.barcode_service import generate_invoice_number
from utils.helpers import calculate_due_date

from services.pdf_service import generate_invoice_pdf
router = APIRouter()

@router.get("/invoices")
async def list_invoices(
    status: Optional[str] = None,
    client_id: Optional[str] = None,
    tenant_id: str = Depends(get_tenant_id),
    user: dict = Depends(get_current_user)
):
    """List all invoices with overdue status check.
    
    SECURITY: For users with warehouse restrictions, only show invoices
    that contain parcels from their allowed warehouses.
    """
    query = {"tenant_id": tenant_id}
    if status and status != "all":
        query["status"] = status
    if client_id:
        query["client_id"] = client_id
    
    # SECURITY: Apply warehouse-based filtering
    warehouse_filter = build_warehouse_filter(user)
    if warehouse_filter:
        # Find invoice IDs that have line items with parcels from user's allowed warehouses
        allowed_warehouses = user.get("allowed_warehouses", [])
        # Get shipment IDs from allowed warehouses
        allowed_shipments = await db.shipments.distinct(
            "id",
            {"tenant_id": tenant_id, "warehouse_id": {"$in": allowed_warehouses}}
        )
        # Get invoice IDs that have these shipments
        allowed_invoice_ids = await db.invoice_line_items.distinct(
            "invoice_id",
            {"shipment_id": {"$in": allowed_shipments}}
        )
        # Also include invoices where shipments directly link to invoice
        direct_invoice_ids = await db.shipments.distinct(
            "invoice_id",
            {"tenant_id": tenant_id, "warehouse_id": {"$in": allowed_warehouses}, "invoice_id": {"$ne": None}}
        )
        all_allowed_invoices = list(set(allowed_invoice_ids + direct_invoice_ids))
        query["id"] = {"$in": all_allowed_invoices}
    
    invoices = await db.invoices.find(query, {"_id": 0}).sort("created_at", -1).to_list(2000)
    
    if not invoices:
        return invoices
    
    # Batch fetch all unique client IDs to avoid N+1 query
    client_ids = list(set(inv.get("client_id") for inv in invoices if inv.get("client_id")))
    clients_cursor = await db.clients.find(
        {"id": {"$in": client_ids}},
        {"_id": 0, "id": 1, "name": 1}
    ).to_list(len(client_ids))
    clients_map = {c["id"]: c["name"] for c in clients_cursor}
    
    # Check for overdue invoices and update status
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    for invoice in invoices:
        if invoice["status"] not in ["paid", "overdue"] and invoice.get("due_date", "") < today:
            # Update to overdue
            await db.invoices.update_one(
                {"id": invoice["id"]},
                {"$set": {"status": "overdue"}}
            )
            invoice["status"] = "overdue"
        
        # Enrich with client name from cached map
        invoice["client_name"] = clients_map.get(invoice.get("client_id"), "Unknown")
    
    return invoices


@router.get("/invoices/search")
async def search_invoices(
    q: Optional[str] = None,
    client_id: Optional[str] = None,
    status: Optional[str] = None,
    tenant_id: str = Depends(get_tenant_id)
):
    """
    Search invoices by number or client name for quick assignment.
    IMPORTANT: This route must be defined BEFORE /invoices/{invoice_id} to avoid 'search' being matched as an ID.
    """
    query = {"tenant_id": tenant_id}
    
    if status:
        query["status"] = status
    
    if client_id:
        query["client_id"] = client_id
    
    invoices = await db.invoices.find(query, {"_id": 0}).to_list(100)
    
    # Get clients for name matching
    client_ids = list(set(inv.get("client_id") for inv in invoices if inv.get("client_id")))
    clients = await db.clients.find({"id": {"$in": client_ids}}, {"_id": 0}).to_list(100)
    client_map = {c["id"]: c for c in clients}
    
    # Filter by search query
    results = []
    for inv in invoices:
        client = client_map.get(inv.get("client_id"), {})
        client_name = client.get("name", "")
        
        # Check if query matches
        if q:
            q_lower = q.lower()
            if q_lower not in inv.get("invoice_number", "").lower() and q_lower not in client_name.lower():
                continue
        
        results.append({
            "id": inv["id"],
            "invoice_number": inv.get("invoice_number"),
            "client_id": inv.get("client_id"),
            "client_name": client_name,
            "status": inv.get("status"),
            "total": inv.get("total", 0),
            "created_at": inv.get("created_at")
        })
    
    return results[:20]  # Limit to 20 results


@router.get("/invoices/{invoice_id}")
async def get_invoice(invoice_id: str, tenant_id: str = Depends(get_tenant_id)):
    """Get single invoice with line items, adjustments and payments"""
    invoice = await db.invoices.find_one(
        {"id": invoice_id, "tenant_id": tenant_id},
        {"_id": 0}
    )
    if not invoice:
        raise HTTPException(status_code=404, detail="Invoice not found")
    
    # Get line items
    line_items = await db.invoice_line_items.find(
        {"invoice_id": invoice_id},
        {"_id": 0}
    ).to_list(100)
    
    # Get adjustments
    adjustments = await db.invoice_adjustments.find(
        {"invoice_id": invoice_id},
        {"_id": 0}
    ).to_list(100)
    
    # Get payments
    payments = await db.payments.find(
        {"invoice_id": invoice_id, "tenant_id": tenant_id},
        {"_id": 0}
    ).sort("payment_date", -1).to_list(100)
    
    total_paid = sum(p["amount"] for p in payments)
    
    # Get client info
    client = await db.clients.find_one({"id": invoice["client_id"]}, {"_id": 0})
    
    # Check overdue
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    if invoice["status"] not in ["paid", "overdue"] and invoice["due_date"] < today:
        await db.invoices.update_one(
            {"id": invoice_id},
            {"$set": {"status": "overdue"}}
        )
        invoice["status"] = "overdue"
    
    return {
        **invoice,
        "line_items": line_items,
        "adjustments": adjustments,
        "payments": payments,
        "total_paid": total_paid,
        "balance_due": invoice["total"] - total_paid,
        "client": client
    }

@router.post("/invoices")
async def create_invoice(
    request: Request,
    invoice_data: InvoiceCreateEnhanced,
    tenant_id: str = Depends(get_tenant_id),
    user: dict = Depends(get_current_user)
):
    """Create a new invoice with line items and adjustments"""
    # Verify client exists
    client = await db.clients.find_one(
        {"id": invoice_data.client_id, "tenant_id": tenant_id},
        {"_id": 0}
    )
    if not client:
        raise HTTPException(status_code=404, detail="Client not found")
    
    # Generate invoice number
    invoice_number = await generate_invoice_number(tenant_id)
    
    # Calculate subtotal from line items
    subtotal = sum(item.amount for item in invoice_data.line_items)
    
    # Calculate adjustments total (positive for additions, negative for discounts)
    adjustments_total = sum(
        adj.amount if adj.is_addition else -adj.amount 
        for adj in invoice_data.adjustments
    )
    
    # Calculate total
    total = invoice_data.total if invoice_data.total else (subtotal + adjustments_total)
    
    # Calculate due date - use provided or default
    if invoice_data.due_date:
        due_date = invoice_data.due_date
    else:
        due_date = calculate_due_date(client.get("payment_terms_days", 30))
    
    # Create invoice with frozen client details for historical accuracy
    invoice_id = str(uuid.uuid4())
    invoice_doc = {
        "id": invoice_id,
        "tenant_id": tenant_id,
        "client_id": invoice_data.client_id,
        "trip_id": invoice_data.trip_id,
        "invoice_number": invoice_number,
        "currency": invoice_data.currency,
        "subtotal": subtotal,
        "adjustments": adjustments_total,
        "total": total,
        "status": invoice_data.status or "draft",
        "due_date": due_date,
        "issue_date": invoice_data.issue_date or datetime.now(timezone.utc).strftime("%Y-%m-%d"),
        "created_at": datetime.now(timezone.utc).isoformat(),
        "sent_at": None,
        "sent_by": None,
        "paid_at": None,
        # Payment terms
        "payment_terms": invoice_data.payment_terms,
        "payment_terms_custom": invoice_data.payment_terms_custom,
        # Frozen client details at invoice creation
        "client_name_snapshot": client.get("name"),
        "client_address_snapshot": client.get("billing_address") or client.get("physical_address"),
        "client_vat_snapshot": client.get("vat_number"),
        "client_phone_snapshot": client.get("phone"),
        "client_email_snapshot": client.get("email")
    }
    
    await db.invoices.insert_one(invoice_doc)
    
    # Remove MongoDB's _id from the response
    invoice_doc.pop('_id', None)
    
    # Create line items and update shipments to link to this invoice
    for item in invoice_data.line_items:
        line_item_doc = {
            "id": str(uuid.uuid4()),
            "invoice_id": invoice_id,
            "description": item.description,
            "quantity": item.quantity,
            "unit": item.unit,
            "rate": item.rate,
            "amount": item.amount,
            "shipment_id": item.shipment_id,
            "parcel_label": item.parcel_label,
            "client_name": item.client_name,
            "recipient_name": item.recipient_name,
            "length_cm": item.length_cm,
            "width_cm": item.width_cm,
            "height_cm": item.height_cm,
            "weight": item.weight
        }
        await db.invoice_line_items.insert_one(line_item_doc)
        
        # Update shipment with invoice_id if shipment_id is provided
        if item.shipment_id:
            await db.shipments.update_one(
                {"id": item.shipment_id},
                {"$set": {"invoice_id": invoice_id}}
            )
    
    # Create adjustments
    for adj in invoice_data.adjustments:
        adj_doc = {
            "id": str(uuid.uuid4()),
            "invoice_id": invoice_id,
            "description": adj.description,
            "amount": adj.amount,
            "is_addition": adj.is_addition
        }
        await db.invoice_adjustments.insert_one(adj_doc)
    
    # Audit log
    await create_audit_log(
        tenant_id=tenant_id,
        user_id=user["id"],
        action=AuditAction.create,
        table_name="invoices",
        record_id=invoice_id,
        new_value=invoice_doc,
        ip_address=request.client.host if request.client else None
    )
    
    # Build line items response
    line_items_response = []
    for item in invoice_data.line_items:
        line_items_response.append({
            "description": item.description,
            "quantity": item.quantity,
            "unit": item.unit,
            "rate": item.rate,
            "amount": item.amount
        })
    
    # Build adjustments response
    adjustments_response = []
    for adj in invoice_data.adjustments:
        adjustments_response.append({
            "description": adj.description,
            "amount": adj.amount,
            "is_addition": adj.is_addition
        })
    
    # Return the created invoice with line items
    return {
        **invoice_doc,
        "line_items": line_items_response,
        "adjustments": adjustments_response
    }

@router.put("/invoices/{invoice_id}")
async def update_invoice(
    request: Request,
    invoice_id: str,
    update_data: InvoiceUpdateEnhanced,
    tenant_id: str = Depends(get_tenant_id),
    user: dict = Depends(get_current_user)
):
    """Update invoice with line items and adjustments"""
    invoice = await db.invoices.find_one(
        {"id": invoice_id, "tenant_id": tenant_id}
    )
    if not invoice:
        raise HTTPException(status_code=404, detail="Invoice not found")
    
    old_invoice = dict(invoice)
    
    # Build update dict from non-None values (excluding line_items and adjustments)
    update_dict = {}
    if update_data.client_id is not None:
        update_dict["client_id"] = update_data.client_id
    if update_data.trip_id is not None:
        update_dict["trip_id"] = update_data.trip_id
    if update_data.currency is not None:
        update_dict["currency"] = update_data.currency
    if update_data.issue_date is not None:
        update_dict["issue_date"] = update_data.issue_date
    if update_data.due_date is not None:
        update_dict["due_date"] = update_data.due_date
    if update_data.status is not None:
        update_dict["status"] = update_data.status
    
    # Handle line items update
    if update_data.line_items is not None:
        # Delete existing line items
        await db.invoice_line_items.delete_many({"invoice_id": invoice_id})
        
        # Create new line items with dimension data from shipments
        subtotal = 0
        for item in update_data.line_items:
            # If shipment_id exists, fetch dimensions from shipment
            length_cm = item.length_cm
            width_cm = item.width_cm
            height_cm = item.height_cm
            weight = item.weight
            
            if item.shipment_id and (not length_cm or not weight):
                shipment = await db.shipments.find_one(
                    {"id": item.shipment_id},
                    {"_id": 0, "length_cm": 1, "width_cm": 1, "height_cm": 1, "total_weight": 1}
                )
                if shipment:
                    length_cm = length_cm or shipment.get("length_cm")
                    width_cm = width_cm or shipment.get("width_cm")
                    height_cm = height_cm or shipment.get("height_cm")
                    weight = weight or shipment.get("total_weight")
            
            line_item_doc = {
                "id": str(uuid.uuid4()),
                "invoice_id": invoice_id,
                "description": item.description,
                "quantity": item.quantity,
                "unit": item.unit,
                "rate": item.rate,
                "amount": item.amount,
                "shipment_id": item.shipment_id,
                "length_cm": length_cm,
                "width_cm": width_cm,
                "height_cm": height_cm,
                "weight": weight,
                "parcel_label": item.parcel_label,
                "client_name": item.client_name,
                "recipient_name": item.recipient_name
            }
            await db.invoice_line_items.insert_one(line_item_doc)
            subtotal += item.amount
        
        update_dict["subtotal"] = subtotal
    
    # Handle adjustments update
    adjustments_total = 0
    if update_data.adjustments is not None:
        # Delete existing adjustments
        await db.invoice_adjustments.delete_many({"invoice_id": invoice_id})
        
        # Create new adjustments
        for adj in update_data.adjustments:
            adj_doc = {
                "id": str(uuid.uuid4()),
                "invoice_id": invoice_id,
                "description": adj.description,
                "amount": adj.amount,
                "is_addition": adj.is_addition
            }
            await db.invoice_adjustments.insert_one(adj_doc)
            adjustments_total += adj.amount if adj.is_addition else -adj.amount
        
        update_dict["adjustments"] = adjustments_total
    
    # Update total if provided or recalculate
    if update_data.total is not None:
        update_dict["total"] = update_data.total
    elif "subtotal" in update_dict or "adjustments" in update_dict:
        subtotal = update_dict.get("subtotal", invoice.get("subtotal", 0))
        adjustments = update_dict.get("adjustments", invoice.get("adjustments", 0))
        update_dict["total"] = subtotal + adjustments
    
    # Determine action type
    action = AuditAction.status_change if "status" in update_dict else AuditAction.update
    
    # Handle status changes
    if update_dict.get("status") == "sent" and invoice["status"] == "draft":
        update_dict["sent_at"] = datetime.now(timezone.utc).isoformat()
        update_dict["sent_by"] = user["id"]
    elif update_dict.get("status") == "paid" and invoice["status"] != "paid":
        update_dict["paid_at"] = datetime.now(timezone.utc).isoformat()
    
    if update_dict:
        await db.invoices.update_one(
            {"id": invoice_id, "tenant_id": tenant_id},
            {"$set": update_dict}
        )
    
    # Get updated invoice with line items and adjustments
    new_invoice = await db.invoices.find_one({"id": invoice_id, "tenant_id": tenant_id}, {"_id": 0})
    line_items = await db.invoice_line_items.find({"invoice_id": invoice_id}, {"_id": 0}).to_list(100)
    adjustments = await db.invoice_adjustments.find({"invoice_id": invoice_id}, {"_id": 0}).to_list(100)
    
    # Audit log
    await create_audit_log(
        tenant_id=tenant_id,
        user_id=user["id"],
        action=action,
        table_name="invoices",
        record_id=invoice_id,
        old_value=old_invoice,
        new_value=new_invoice,
        ip_address=request.client.host if request.client else None
    )
    
    return {
        **new_invoice,
        "line_items": line_items,
        "adjustments": adjustments
    }

@router.delete("/invoices/{invoice_id}")
async def delete_invoice(
    request: Request,
    invoice_id: str,
    tenant_id: str = Depends(get_tenant_id),
    user: dict = Depends(get_current_user)
):
    """Delete invoice (only drafts or by owner)"""
    invoice = await db.invoices.find_one(
        {"id": invoice_id, "tenant_id": tenant_id}
    )
    if not invoice:
        raise HTTPException(status_code=404, detail="Invoice not found")
    
    old_invoice = dict(invoice)
    
    if invoice["status"] != "draft" and user.get("role") != "owner":
        raise HTTPException(status_code=403, detail="Only owner can delete non-draft invoices")
    
    # Delete line items
    await db.invoice_line_items.delete_many({"invoice_id": invoice_id})
    
    # Delete adjustments
    await db.invoice_adjustments.delete_many({"invoice_id": invoice_id})
    
    # Delete invoice
    await db.invoices.delete_one({"id": invoice_id, "tenant_id": tenant_id})
    
    # Audit log
    await create_audit_log(
        tenant_id=tenant_id,
        user_id=user["id"],
        action=AuditAction.delete,
        table_name="invoices",
        record_id=invoice_id,
        old_value=old_invoice,
        ip_address=request.client.host if request.client else None
    )
    
    return {"message": "Invoice deleted"}

# ============ INVOICE LINE ITEMS ROUTES ============

@router.get("/invoices/{invoice_id}/items")
async def list_invoice_items(
    invoice_id: str,
    tenant_id: str = Depends(get_tenant_id)
):
    """List invoice line items"""
    invoice = await db.invoices.find_one(
        {"id": invoice_id, "tenant_id": tenant_id},
        {"_id": 0}
    )
    if not invoice:
        raise HTTPException(status_code=404, detail="Invoice not found")
    
    items = await db.invoice_line_items.find(
        {"invoice_id": invoice_id},
        {"_id": 0}
    ).to_list(100)
    
    return items

@router.post("/invoices/{invoice_id}/items")
async def add_invoice_item(
    invoice_id: str,
    item_data: InvoiceLineItemCreate,
    tenant_id: str = Depends(get_tenant_id)
):
    """Add line item to invoice"""
    invoice = await db.invoices.find_one(
        {"id": invoice_id, "tenant_id": tenant_id},
        {"_id": 0}
    )
    if not invoice:
        raise HTTPException(status_code=404, detail="Invoice not found")
    
    if invoice["status"] != "draft":
        raise HTTPException(status_code=400, detail="Can only add items to draft invoices")
    
    # Calculate amount
    if item_data.weight:
        amount = item_data.weight * item_data.rate
    else:
        amount = item_data.quantity * item_data.rate
    
    item = InvoiceLineItem(
        **item_data.model_dump(),
        invoice_id=invoice_id,
        amount=amount
    )
    
    doc = item.model_dump()
    await db.invoice_line_items.insert_one(doc)
    
    # Update invoice subtotal
    all_items = await db.invoice_line_items.find(
        {"invoice_id": invoice_id},
        {"_id": 0, "amount": 1}
    ).to_list(100)
    
    new_subtotal = sum(i["amount"] for i in all_items)
    new_total = new_subtotal + invoice["adjustments"]
    
    await db.invoices.update_one(
        {"id": invoice_id},
        {"$set": {"subtotal": new_subtotal, "total": new_total}}
    )
    
    return item

@router.delete("/invoices/{invoice_id}/items/{item_id}")
async def delete_invoice_item(
    invoice_id: str,
    item_id: str,
    tenant_id: str = Depends(get_tenant_id)
):
    """Delete line item from invoice"""
    invoice = await db.invoices.find_one(
        {"id": invoice_id, "tenant_id": tenant_id},
        {"_id": 0}
    )
    if not invoice:
        raise HTTPException(status_code=404, detail="Invoice not found")
    
    if invoice["status"] != "draft":
        raise HTTPException(status_code=400, detail="Can only remove items from draft invoices")
    
    result = await db.invoice_line_items.delete_one(
        {"id": item_id, "invoice_id": invoice_id}
    )
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Item not found")
    
    # Recalculate subtotal
    all_items = await db.invoice_line_items.find(
        {"invoice_id": invoice_id},
        {"_id": 0, "amount": 1}
    ).to_list(100)
    
    new_subtotal = sum(i["amount"] for i in all_items)
    new_total = new_subtotal + invoice["adjustments"]
    
    await db.invoices.update_one(
        {"id": invoice_id},
        {"$set": {"subtotal": new_subtotal, "total": new_total}}
    )
    
    return {"message": "Item deleted"}

# ============ PAYMENT ROUTES ============

@router.get("/payments")
async def list_payments(
    client_id: Optional[str] = None,
    tenant_id: str = Depends(get_tenant_id)
):
    """List all payments"""
    query = {"tenant_id": tenant_id}
    if client_id:
        query["client_id"] = client_id
    
    payments = await db.payments.find(query, {"_id": 0}).sort("payment_date", -1).to_list(2000)
    
    # Enrich with client and invoice info
    for payment in payments:
        client = await db.clients.find_one({"id": payment["client_id"]}, {"_id": 0, "name": 1})
        payment["client_name"] = client["name"] if client else "Unknown"
        
        if payment.get("invoice_id"):
            invoice = await db.invoices.find_one(
                {"id": payment["invoice_id"]},
                {"_id": 0, "invoice_number": 1}
            )
            payment["invoice_number"] = invoice["invoice_number"] if invoice else None
    
    return payments

@router.post("/payments")
async def create_payment(
    request: Request,
    payment_data: PaymentCreate,
    tenant_id: str = Depends(get_tenant_id),
    user: dict = Depends(get_current_user)
):
    """Record a payment"""
    # Verify client exists
    client = await db.clients.find_one(
        {"id": payment_data.client_id, "tenant_id": tenant_id},
        {"_id": 0}
    )
    if not client:
        raise HTTPException(status_code=404, detail="Client not found")
    
    # Verify invoice if provided
    if payment_data.invoice_id:
        invoice = await db.invoices.find_one(
            {"id": payment_data.invoice_id, "tenant_id": tenant_id},
            {"_id": 0}
        )
        if not invoice:
            raise HTTPException(status_code=404, detail="Invoice not found")
    
    payment = Payment(
        **payment_data.model_dump(),
        tenant_id=tenant_id,
        created_by=user["id"]
    )
    
    doc = payment.model_dump()
    doc['created_at'] = doc['created_at'].isoformat()
    await db.payments.insert_one(doc)
    
    # Audit log
    await create_audit_log(
        tenant_id=tenant_id,
        user_id=user["id"],
        action=AuditAction.create,
        table_name="payments",
        record_id=payment.id,
        new_value=doc,
        ip_address=request.client.host if request.client else None
    )
    
    # Check if invoice is fully paid
    if payment_data.invoice_id:
        invoice = await db.invoices.find_one(
            {"id": payment_data.invoice_id},
            {"_id": 0}
        )
        payments = await db.payments.find(
            {"invoice_id": payment_data.invoice_id},
            {"_id": 0, "amount": 1}
        ).to_list(100)
        
        total_paid = sum(p["amount"] for p in payments)
        
        if total_paid >= invoice["total"]:
            await db.invoices.update_one(
                {"id": payment_data.invoice_id},
                {"$set": {"status": "paid", "paid_at": datetime.now(timezone.utc).isoformat()}}
            )
    
    return payment

@router.delete("/payments/{payment_id}")
async def delete_payment(
    request: Request,
    payment_id: str,
    tenant_id: str = Depends(get_tenant_id),
    user: dict = Depends(get_current_user)
):
    """Delete a payment (owner/finance only)"""
    if user.get("role") not in ["owner", "finance"]:
        raise HTTPException(status_code=403, detail="Only owner/finance can delete payments")
    
    payment = await db.payments.find_one(
        {"id": payment_id, "tenant_id": tenant_id}
    )
    if not payment:
        raise HTTPException(status_code=404, detail="Payment not found")
    
    old_payment = dict(payment)
    invoice_id = payment.get("invoice_id")
    
    await db.payments.delete_one({"id": payment_id, "tenant_id": tenant_id})
    
    # Audit log
    await create_audit_log(
        tenant_id=tenant_id,
        user_id=user["id"],
        action=AuditAction.delete,
        table_name="payments",
        record_id=payment_id,
        old_value=old_payment,
        ip_address=request.client.host if request.client else None
    )
    
    # Recheck invoice paid status
    if invoice_id:
        invoice = await db.invoices.find_one({"id": invoice_id}, {"_id": 0})
        if invoice and invoice["status"] == "paid":
            payments = await db.payments.find(
                {"invoice_id": invoice_id},
                {"_id": 0, "amount": 1}
            ).to_list(100)
            
            total_paid = sum(p["amount"] for p in payments)
            
            if total_paid < invoice["total"]:
                # Revert to sent or overdue
                today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
                new_status = "overdue" if invoice["due_date"] < today else "sent"
                await db.invoices.update_one(
                    {"id": invoice_id},
                    {"$set": {"status": new_status, "paid_at": None}}
                )
    
    return {"message": "Payment deleted"}

@router.get("/invoices-enhanced")
async def list_invoices_enhanced(
    trip_id: Optional[str] = None,
    status: Optional[str] = None,
    sort_by: Optional[str] = "newest",
    tenant_id: str = Depends(get_tenant_id)
):
    """List invoices with enhanced data for Finance Hub"""
    query = {"tenant_id": tenant_id}
    
    if trip_id and trip_id != "all":
        query["trip_id"] = trip_id
    
    if status and status != "all":
        query["status"] = status
    
    # Determine sort
    sort_field = "created_at"
    sort_order = -1
    if sort_by == "oldest":
        sort_order = 1
    elif sort_by == "amount_high":
        sort_field = "total"
        sort_order = -1
    elif sort_by == "amount_low":
        sort_field = "total"
        sort_order = 1
    
    invoices = await db.invoices.find(query, {"_id": 0}).sort(sort_field, sort_order).to_list(2000)
    
    # Enrich with client names and trip numbers
    result = []
    for inv in invoices:
        client = await db.clients.find_one({"id": inv.get("client_id")}, {"_id": 0, "name": 1, "phone": 1, "whatsapp": 1})
        trip = None
        if inv.get("trip_id"):
            trip = await db.trips.find_one({"id": inv["trip_id"]}, {"_id": 0, "trip_number": 1})
        
        # Get payment info
        payments = await db.payments.find({"invoice_id": inv["id"]}, {"_id": 0, "amount": 1}).to_list(100)
        paid_amount = sum(p.get("amount", 0) for p in payments)
        
        # Check overdue
        today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        display_status = inv["status"]
        if display_status not in ["paid", "overdue"] and inv["due_date"] < today:
            display_status = "overdue"
        
        result.append({
            **inv,
            "display_status": display_status,
            "client_name": client.get("name") if client else "Unknown",
            "client_phone": client.get("phone") if client else None,
            "client_whatsapp": client.get("whatsapp") if client else None,
            "trip_number": trip.get("trip_number") if trip else None,
            "paid_amount": paid_amount,
            "outstanding": inv["total"] - paid_amount
        })
    
    return result

@router.get("/invoices/{invoice_id}/full")
async def get_invoice_full(
    invoice_id: str,
    tenant_id: str = Depends(get_tenant_id)
):
    """Get complete invoice with all related data"""
    invoice = await db.invoices.find_one({"id": invoice_id, "tenant_id": tenant_id}, {"_id": 0})
    if not invoice:
        raise HTTPException(status_code=404, detail="Invoice not found")
    
    # Get client
    client = await db.clients.find_one({"id": invoice.get("client_id")}, {"_id": 0})
    
    # Get client rate
    client_rate = await db.client_rates.find_one(
        {"client_id": invoice.get("client_id")},
        {"_id": 0}
    )
    
    # Get trip
    trip = None
    if invoice.get("trip_id"):
        trip = await db.trips.find_one({"id": invoice["trip_id"]}, {"_id": 0})
    
    # Get line items
    line_items = await db.invoice_line_items.find(
        {"invoice_id": invoice_id},
        {"_id": 0}
    ).to_list(100)
    
    # Get adjustments
    adjustments = await db.invoice_adjustments.find(
        {"invoice_id": invoice_id},
        {"_id": 0}
    ).to_list(100)
    
    # Get payments
    payments = await db.payments.find(
        {"invoice_id": invoice_id},
        {"_id": 0}
    ).to_list(100)
    
    paid_amount = sum(p.get("amount", 0) for p in payments)
    
    # Check overdue
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    display_status = invoice["status"]
    if display_status not in ["paid", "overdue"] and invoice["due_date"] < today:
        display_status = "overdue"
    
    return {
        **invoice,
        "display_status": display_status,
        "client": client,
        "client_rate": client_rate,
        "trip": trip,
        "line_items": line_items,
        "adjustments": adjustments,
        "payments": payments,
        "paid_amount": paid_amount,
        "outstanding": invoice["total"] - paid_amount
    }


async def recalculate_invoice_totals(invoice_id: str):
    """Helper function to recalculate invoice subtotal, adjustments and total"""
    # Get all line items
    line_items = await db.invoice_line_items.find(
        {"invoice_id": invoice_id},
        {"_id": 0}
    ).to_list(100)
    
    subtotal = sum(item.get("amount", 0) for item in line_items)
    
    # Get all adjustments
    adjustments = await db.invoice_adjustments.find(
        {"invoice_id": invoice_id},
        {"_id": 0}
    ).to_list(100)
    
    adjustments_total = sum(
        adj.get("amount", 0) if adj.get("is_addition", True) else -adj.get("amount", 0)
        for adj in adjustments
    )
    
    total = subtotal + adjustments_total
    
    # Update invoice
    await db.invoices.update_one(
        {"id": invoice_id},
        {"$set": {
            "subtotal": subtotal,
            "adjustments": adjustments_total,
            "total": total
        }}
    )


@router.post("/invoices/{invoice_id}/adjustments")
async def add_invoice_adjustment(
    invoice_id: str,
    data: dict,
    tenant_id: str = Depends(get_tenant_id),
    user: dict = Depends(get_current_user)
):
    """Add an adjustment to an invoice"""
    invoice = await db.invoices.find_one({"id": invoice_id, "tenant_id": tenant_id}, {"_id": 0})
    if not invoice:
        raise HTTPException(status_code=404, detail="Invoice not found")
    
    if invoice["status"] not in ["draft"]:
        raise HTTPException(status_code=400, detail="Can only add adjustments to draft invoices")
    
    adjustment = {
        "id": str(uuid.uuid4()),
        "invoice_id": invoice_id,
        "description": data.get("description", ""),
        "amount": data.get("amount", 0),
        "is_addition": data.get("is_addition", True),
        "created_at": datetime.now(timezone.utc).isoformat()
    }
    
    await db.invoice_adjustments.insert_one(adjustment)
    
    # Recalculate invoice totals
    await recalculate_invoice_totals(invoice_id)
    
    return {"id": adjustment["id"], "message": "Adjustment added"}

@router.delete("/invoices/{invoice_id}/adjustments/{adjustment_id}")
async def delete_invoice_adjustment(
    invoice_id: str,
    adjustment_id: str,
    tenant_id: str = Depends(get_tenant_id)
):
    """Delete an adjustment from an invoice"""
    invoice = await db.invoices.find_one({"id": invoice_id, "tenant_id": tenant_id}, {"_id": 0})
    if not invoice:
        raise HTTPException(status_code=404, detail="Invoice not found")
    
    if invoice["status"] not in ["draft"]:
        raise HTTPException(status_code=400, detail="Can only modify draft invoices")
    
    result = await db.invoice_adjustments.delete_one({"id": adjustment_id, "invoice_id": invoice_id})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Adjustment not found")
    
    await recalculate_invoice_totals(invoice_id)
    
    return {"message": "Adjustment deleted"}

@router.post("/invoices/{invoice_id}/finalize")
async def finalize_invoice(
    invoice_id: str,
    request: Request,
    tenant_id: str = Depends(get_tenant_id),
    user: dict = Depends(get_current_user)
):
    """Finalize and send invoice"""
    invoice = await db.invoices.find_one({"id": invoice_id, "tenant_id": tenant_id}, {"_id": 0})
    if not invoice:
        raise HTTPException(status_code=404, detail="Invoice not found")
    
    if invoice["status"] != "draft":
        raise HTTPException(status_code=400, detail="Only draft invoices can be finalized")
    
    old_value = dict(invoice)
    now = datetime.now(timezone.utc)
    
    await db.invoices.update_one(
        {"id": invoice_id},
        {"$set": {
            "status": "sent",
            "sent_at": now.isoformat(),
            "sent_by": user["id"]
        }}
    )
    
    await create_audit_log(
        tenant_id=tenant_id,
        user_id=user["id"],
        action=AuditAction.update,
        table_name="invoices",
        record_id=invoice_id,
        old_value=old_value,
        new_value={"status": "sent"},
        ip_address=request.client.host if request.client else None
    )
    
    return {"message": "Invoice finalized and sent", "status": "sent"}

@router.post("/invoices/{invoice_id}/record-payment")
async def record_invoice_payment(
    invoice_id: str,
    data: dict,
    request: Request,
    tenant_id: str = Depends(get_tenant_id),
    user: dict = Depends(get_current_user)
):
    """Record a payment against an invoice"""
    invoice = await db.invoices.find_one({"id": invoice_id, "tenant_id": tenant_id}, {"_id": 0})
    if not invoice:
        raise HTTPException(status_code=404, detail="Invoice not found")
    
    if invoice["status"] == "paid":
        raise HTTPException(status_code=400, detail="Invoice is already fully paid")
    
    # Get existing payments
    existing_payments = await db.payments.find({"invoice_id": invoice_id}, {"_id": 0, "amount": 1}).to_list(100)
    paid_so_far = sum(p.get("amount", 0) for p in existing_payments)
    outstanding = invoice["total"] - paid_so_far
    
    amount = data.get("amount", 0)
    if amount <= 0:
        raise HTTPException(status_code=400, detail="Payment amount must be positive")
    
    if amount > outstanding:
        raise HTTPException(status_code=400, detail=f"Payment exceeds outstanding amount of {outstanding}")
    
    # Create payment
    payment = {
        "id": str(uuid.uuid4()),
        "tenant_id": tenant_id,
        "client_id": invoice["client_id"],
        "invoice_id": invoice_id,
        "amount": amount,
        "payment_date": data.get("payment_date", datetime.now(timezone.utc).strftime("%Y-%m-%d")),
        "payment_method": data.get("payment_method", "bank_transfer"),
        "reference": data.get("reference"),
        "notes": data.get("notes"),
        "created_by": user["id"],
        "created_at": datetime.now(timezone.utc).isoformat()
    }
    
    await db.payments.insert_one(payment)
    
    # Check if fully paid
    new_paid_total = paid_so_far + amount
    if new_paid_total >= invoice["total"]:
        await db.invoices.update_one(
            {"id": invoice_id},
            {"$set": {"status": "paid", "paid_at": datetime.now(timezone.utc).isoformat()}}
        )
    
    await create_audit_log(
        tenant_id=tenant_id,
        user_id=user["id"],
        action=AuditAction.create,
        table_name="payments",
        record_id=payment["id"],
        new_value=payment,
        ip_address=request.client.host if request.client else None
    )
    
    return {
        "payment_id": payment["id"],
        "new_paid_total": new_paid_total,
        "outstanding": invoice["total"] - new_paid_total,
        "fully_paid": new_paid_total >= invoice["total"]
    }

@router.post("/invoices/{invoice_id}/log-whatsapp")
async def log_whatsapp_send(
    invoice_id: str,
    data: dict,
    tenant_id: str = Depends(get_tenant_id),
    user: dict = Depends(get_current_user)
):
    """Log WhatsApp message send for an invoice"""
    invoice = await db.invoices.find_one({"id": invoice_id, "tenant_id": tenant_id}, {"_id": 0})
    if not invoice:
        raise HTTPException(status_code=404, detail="Invoice not found")
    
    client = await db.clients.find_one({"id": invoice["client_id"]}, {"_id": 0})
    
    log_entry = {
        "id": str(uuid.uuid4()),
        "tenant_id": tenant_id,
        "invoice_id": invoice_id,
        "to_number": client.get("whatsapp") or client.get("phone") if client else data.get("to_number"),
        "message": data.get("message", ""),
        "sent_by": user["id"],
        "sent_at": datetime.now(timezone.utc).isoformat(),
        "status": "sent"
    }
    
    await db.whatsapp_logs.insert_one(log_entry)
    
    return {"message": "WhatsApp log recorded", "log_id": log_entry["id"]}

@router.get("/invoices/{invoice_id}/pdf")
async def download_invoice_pdf(
    invoice_id: str,
    tenant_id: str = Depends(get_tenant_id)
):
    """Generate and download invoice PDF"""
    return await generate_invoice_pdf(invoice_id, tenant_id)


# ============ INVOICE REVIEW WORKFLOW ROUTES ============

@router.post("/invoices/{invoice_id}/mark-reviewed")
async def mark_invoice_reviewed(
    invoice_id: str,
    tenant_id: str = Depends(get_tenant_id),
    user: dict = Depends(get_current_user)
):
    """Mark an invoice as reviewed"""
    invoice = await db.invoices.find_one({"id": invoice_id, "tenant_id": tenant_id}, {"_id": 0})
    if not invoice:
        raise HTTPException(status_code=404, detail="Invoice not found")
    
    await db.invoices.update_one(
        {"id": invoice_id},
        {"$set": {
            "reviewed_by": user["id"],
            "reviewed_at": datetime.now(timezone.utc).isoformat()
        }}
    )
    
    return {"message": "Invoice marked as reviewed"}

@router.post("/invoices/{invoice_id}/approve-and-send")
async def approve_and_send_invoice(
    invoice_id: str,
    tenant_id: str = Depends(get_tenant_id),
    user: dict = Depends(get_current_user)
):
    """Approve and send an invoice (owner/manager only)"""
    if user.get("role") not in ["owner", "manager"]:
        raise HTTPException(status_code=403, detail="Only owners and managers can approve invoices")
    
    invoice = await db.invoices.find_one({"id": invoice_id, "tenant_id": tenant_id}, {"_id": 0})
    if not invoice:
        raise HTTPException(status_code=404, detail="Invoice not found")
    
    await db.invoices.update_one(
        {"id": invoice_id},
        {"$set": {
            "approved_by": user["id"],
            "approved_at": datetime.now(timezone.utc).isoformat(),
            "status": "sent",
            "sent_at": datetime.now(timezone.utc).isoformat(),
            "sent_by": user["id"]
        }}
    )
    
    return {"message": "Invoice approved and sent"}


# ============ SMART PARCEL SELECTION ROUTES ============

@router.get("/invoices/trip-parcels/{trip_id}")
async def get_trip_parcels_for_invoicing(
    trip_id: str,
    tenant_id: str = Depends(get_tenant_id)
):
    """
    Get parcels for a trip with invoice information for smart selection.
    Returns parcels with their current invoice status (if any).
    """
    # Get all shipments for this trip
    shipments = await db.shipments.find(
        {"trip_id": trip_id, "tenant_id": tenant_id},
        {"_id": 0}
    ).to_list(1000)
    
    # Get clients for enrichment
    client_ids = list(set(s.get("client_id") for s in shipments if s.get("client_id")))
    clients = await db.clients.find({"id": {"$in": client_ids}}, {"_id": 0}).to_list(1000)
    client_map = {c["id"]: c for c in clients}
    
    # Get invoice info for shipments that have invoice_id
    invoice_ids = list(set(s.get("invoice_id") for s in shipments if s.get("invoice_id")))
    invoices = {}
    if invoice_ids:
        invoice_docs = await db.invoices.find(
            {"id": {"$in": invoice_ids}},
            {"_id": 0, "id": 1, "invoice_number": 1, "status": 1}
        ).to_list(1000)
        invoices = {inv["id"]: inv for inv in invoice_docs}
    
    # Also check invoice_line_items for legacy linkage
    shipment_ids = [s["id"] for s in shipments]
    line_items = await db.invoice_line_items.find(
        {"shipment_id": {"$in": shipment_ids}},
        {"_id": 0, "shipment_id": 1, "invoice_id": 1}
    ).to_list(1000)
    
    # Get invoice info for line items
    line_item_invoice_ids = list(set(li["invoice_id"] for li in line_items if li.get("invoice_id")))
    if line_item_invoice_ids:
        more_invoices = await db.invoices.find(
            {"id": {"$in": line_item_invoice_ids}},
            {"_id": 0, "id": 1, "invoice_number": 1, "status": 1}
        ).to_list(1000)
        for inv in more_invoices:
            if inv["id"] not in invoices:
                invoices[inv["id"]] = inv
    
    # Create shipment to invoice map from line items
    shipment_invoice_map = {}
    for li in line_items:
        if li.get("shipment_id") and li.get("invoice_id"):
            shipment_invoice_map[li["shipment_id"]] = li["invoice_id"]
    
    # Enrich shipments with invoice info
    result = []
    for s in shipments:
        client = client_map.get(s.get("client_id"), {})
        
        # Check for invoice (direct or via line items)
        invoice_id = s.get("invoice_id") or shipment_invoice_map.get(s["id"])
        invoice = invoices.get(invoice_id) if invoice_id else None
        
        # Build display label for parcel sequence
        parcel_label = ""
        if s.get("parcel_sequence") and s.get("total_in_sequence"):
            parcel_label = f"{s['parcel_sequence']} of {s['total_in_sequence']}"
        
        result.append({
            "id": s["id"],
            "description": s.get("description", ""),
            "destination": s.get("destination", ""),
            "total_weight": s.get("total_weight", 0),
            "total_pieces": s.get("total_pieces", 1),
            "quantity": s.get("quantity", 1),
            "client_id": s.get("client_id"),
            "client_name": client.get("name", "Unknown"),
            "recipient": s.get("recipient"),
            "recipient_phone": s.get("recipient_phone"),
            "recipient_vat": s.get("recipient_vat"),
            "shipping_address": s.get("shipping_address"),
            "length_cm": s.get("length_cm"),
            "width_cm": s.get("width_cm"),
            "height_cm": s.get("height_cm"),
            "parcel_label": parcel_label,
            "parcel_sequence": s.get("parcel_sequence"),
            "total_in_sequence": s.get("total_in_sequence"),
            "is_invoiced": invoice is not None,
            "invoice_id": invoice_id,
            "invoice_number": invoice.get("invoice_number") if invoice else None,
            "invoice_status": invoice.get("status") if invoice else None
        })
    
    return result


@router.post("/invoices/{invoice_id}/reassign-parcels")
async def reassign_parcels_to_invoice(
    invoice_id: str,
    parcel_ids: List[str],
    tenant_id: str = Depends(get_tenant_id),
    user: dict = Depends(get_current_user)
):
    """
    Reassign parcels from their current invoice to this invoice.
    Removes from old invoice and adds to new one.
    """
    # Verify invoice exists
    invoice = await db.invoices.find_one(
        {"id": invoice_id, "tenant_id": tenant_id},
        {"_id": 0}
    )
    if not invoice:
        raise HTTPException(status_code=404, detail="Invoice not found")
    
    # Get client rate for calculating line item amounts
    client = await db.clients.find_one({"id": invoice.get("client_id")}, {"_id": 0})
    default_rate = client.get("default_rate_value", 36.0) if client else 36.0
    
    results = []
    for parcel_id in parcel_ids:
        shipment = await db.shipments.find_one(
            {"id": parcel_id, "tenant_id": tenant_id},
            {"_id": 0}
        )
        if not shipment:
            results.append({"parcel_id": parcel_id, "success": False, "error": "Parcel not found"})
            continue
        
        old_invoice_id = shipment.get("invoice_id")
        
        # Remove from old invoice line items
        if old_invoice_id:
            await db.invoice_line_items.delete_many({
                "invoice_id": old_invoice_id,
                "shipment_id": parcel_id
            })
            # Recalculate old invoice totals
            await recalculate_invoice_totals(old_invoice_id)
        
        # Also remove any existing line items for this shipment in any invoice
        await db.invoice_line_items.delete_many({"shipment_id": parcel_id})
        
        # Update shipment with new invoice_id
        await db.shipments.update_one(
            {"id": parcel_id},
            {"$set": {"invoice_id": invoice_id}}
        )
        
        # Build parcel label
        parcel_label = ""
        if shipment.get("parcel_sequence") and shipment.get("total_in_sequence"):
            parcel_label = f"{shipment['parcel_sequence']} of {shipment['total_in_sequence']}"
        
        # Create new line item
        weight = shipment.get("total_weight", 0)
        amount = weight * default_rate
        
        line_item_doc = {
            "id": str(uuid.uuid4()),
            "invoice_id": invoice_id,
            "description": shipment.get("description", ""),
            "quantity": shipment.get("total_weight", 0),
            "unit": "kg",
            "rate": default_rate,
            "amount": amount,
            "shipment_id": parcel_id,
            "parcel_label": parcel_label,
            "client_name": client.get("name") if client else None,
            "recipient_name": shipment.get("recipient"),
            "length_cm": shipment.get("length_cm"),
            "width_cm": shipment.get("width_cm"),
            "height_cm": shipment.get("height_cm"),
            "weight": weight
        }
        await db.invoice_line_items.insert_one(line_item_doc)
        
        results.append({
            "parcel_id": parcel_id,
            "success": True,
            "old_invoice_id": old_invoice_id,
            "new_invoice_id": invoice_id
        })
    
    # Recalculate new invoice totals
    await recalculate_invoice_totals(invoice_id)
    
    return {"results": results}


@router.patch("/invoices/{invoice_id}/unlock")
async def unlock_invoice(
    invoice_id: str,
    tenant_id: str = Depends(get_tenant_id),
    user: dict = Depends(get_current_user)
):
    """Unlock a finalized invoice (set back to draft). Owner/manager only."""
    if user.get("role") not in ["owner", "manager"]:
        raise HTTPException(status_code=403, detail="Only owners and managers can unlock invoices")
    result = await db.invoices.update_one(
        {"id": invoice_id, "tenant_id": tenant_id},
        {"$set": {"status": "draft", "updated_at": datetime.now(timezone.utc).isoformat()}}
    )
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Invoice not found")
    return {"success": True}

# ============ INVOICE PATCH (comment / minor fields) ============

@router.patch("/invoices/{invoice_id}")
async def patch_invoice(
    invoice_id: str,
    data: dict,
    tenant_id: str = Depends(get_tenant_id),
    user: dict = Depends(get_current_user)
):
    """Patch specific invoice fields (e.g. comment). Only allows safe fields."""
    ALLOWED = {"comment"}
    update = {k: v for k, v in data.items() if k in ALLOWED}
    if not update:
        raise HTTPException(status_code=400, detail="No patchable fields provided")
    update["updated_at"] = datetime.now(timezone.utc).isoformat()
    result = await db.invoices.update_one(
        {"id": invoice_id, "tenant_id": tenant_id},
        {"$set": update}
    )
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Invoice not found")
    return {"success": True}

# ============ INVOICE COMMENTS/MENTIONS ROUTES ============

@router.get("/invoices/{invoice_id}/comments")
async def list_invoice_comments(
    invoice_id: str,
    tenant_id: str = Depends(get_tenant_id)
):
    """List all comments on an invoice"""
    comments = await db.invoice_comments.find(
        {"invoice_id": invoice_id, "tenant_id": tenant_id},
        {"_id": 0}
    ).sort("created_at", -1).to_list(100)
    
    # Enrich with user names
    result = []
    for comment in comments:
        user = await db.users.find_one({"id": comment.get("created_by")}, {"name": 1, "_id": 0})
        result.append({
            **comment,
            "user_name": user.get("name") if user else "Unknown"
        })
    
    return result

@router.post("/invoices/{invoice_id}/comments")
async def add_invoice_comment(
    invoice_id: str,
    comment_data: dict,
    tenant_id: str = Depends(get_tenant_id),
    user: dict = Depends(get_current_user)
):
    """Add a comment to an invoice with optional @mentions"""
    invoice = await db.invoices.find_one({"id": invoice_id, "tenant_id": tenant_id}, {"_id": 0})
    if not invoice:
        raise HTTPException(status_code=404, detail="Invoice not found")
    
    comment_id = str(uuid.uuid4())
    comment = {
        "id": comment_id,
        "invoice_id": invoice_id,
        "tenant_id": tenant_id,
        "content": comment_data.get("content", ""),
        "mentioned_user_ids": comment_data.get("mentioned_user_ids", []),
        "created_by": user["id"],
        "created_at": datetime.now(timezone.utc).isoformat()
    }
    
    await db.invoice_comments.insert_one(comment)
    
    # Create notifications for mentioned users
    for mentioned_user_id in comment_data.get("mentioned_user_ids", []):
        notification = {
            "id": str(uuid.uuid4()),
            "tenant_id": tenant_id,
            "user_id": mentioned_user_id,
            "message": f"{user.get('name', 'Someone')} mentioned you in a comment on invoice {invoice.get('invoice_number', '')}",
            "link": f"/invoices/{invoice_id}",
            "type": "mention",
            "created_by": user["id"],
            "read": False,
            "created_at": datetime.now(timezone.utc).isoformat()
        }
        await db.notifications.insert_one(notification)
    
    return {"id": comment_id, "message": "Comment added"}

# ============ NOTIFICATION ROUTES ============

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

@router.post("/notifications/{notification_id}/read")
async def mark_notification_read(
    notification_id: str,
    tenant_id: str = Depends(get_tenant_id),
    user: dict = Depends(get_current_user)
):
    """Mark a notification as read"""
    result = await db.notifications.update_one(
        {"id": notification_id, "user_id": user["id"]},
        {"$set": {"read": True}}
    )
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Notification not found")
    
    return {"message": "Notification marked as read"}

@router.get("/notifications/unread-count")
async def get_unread_notification_count(
    tenant_id: str = Depends(get_tenant_id),
    user: dict = Depends(get_current_user)
):
    """Get count of unread notifications"""
    count = await db.notifications.count_documents({
        "tenant_id": tenant_id,
        "user_id": user["id"],
        "read": False
    })
    return {"count": count}

# ============ TEAM MEMBERS FOR MENTIONS ============

@router.get("/team-members")
async def list_team_members(
    tenant_id: str = Depends(get_tenant_id)
):
    """List team members for @mention functionality"""
    members = await db.users.find(
        {"tenant_id": tenant_id, "status": "active"},
        {"_id": 0, "id": 1, "name": 1, "email": 1, "role": 1}
    ).to_list(100)
    
    return members



# ============ INVOICE PDF TYPE 2 ============

@router.get("/invoices/{invoice_id}/pdf/type2")
async def download_invoice_pdf_type2(
    invoice_id: str,
    tenant_id: str = Depends(get_tenant_id)
):
    """Download Invoice PDF - TYPE 2 (Servex branded template)."""
    from services.pdf_service import generate_invoice_pdf_type2

    pdf_buffer = await generate_invoice_pdf_type2(invoice_id, tenant_id)

    invoice = await db.invoices.find_one({"id": invoice_id, "tenant_id": tenant_id}, {"_id": 0, "invoice_number": 1})
    invoice_number = invoice.get("invoice_number", invoice_id) if invoice else invoice_id

    return StreamingResponse(
        pdf_buffer,
        media_type="application/pdf",
        headers={"Content-Disposition": f"attachment; filename=invoice_{invoice_number}_type2.pdf"}
    )
