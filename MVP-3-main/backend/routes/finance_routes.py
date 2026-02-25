"""
Finance routes for Servex Holdings backend.
Handles finance hub operations: client statements, trip worksheets, overdue tracking.
"""
from fastapi import APIRouter, HTTPException, Depends
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime, timezone, timedelta
from io import BytesIO
import uuid

from database import db
from dependencies import get_current_user, get_tenant_id, check_permission
from models.enums import InvoiceStatus

router = APIRouter()

# ============ SETTINGS - CURRENCIES ============

@router.get("/settings/currencies")
async def get_currencies(tenant_id: str = Depends(get_tenant_id)):
    """Get currency settings including exchange rates"""
    # Try to get from tenant settings, fallback to defaults
    settings = await db.settings.find_one({"tenant_id": tenant_id}, {"_id": 0})
    
    if settings and settings.get("currencies"):
        return {"currencies": settings["currencies"]}
    
    # Return default currencies
    return {
        "currencies": [
            {"code": "ZAR", "name": "South African Rand", "symbol": "R", "exchange_rate": 1.0},
            {"code": "KES", "name": "Kenyan Shilling", "symbol": "KES", "exchange_rate": 6.67}
        ]
    }

@router.put("/settings/currencies")
async def update_currencies(
    data: dict,
    tenant_id: str = Depends(get_tenant_id),
    user: dict = Depends(get_current_user)
):
    """Update currency exchange rates"""
    currencies = data.get("currencies", [])
    
    await db.settings.update_one(
        {"tenant_id": tenant_id},
        {"$set": {"currencies": currencies, "updated_at": datetime.now(timezone.utc).isoformat()}},
        upsert=True
    )
    
    return {"message": "Currencies updated", "currencies": currencies}

@router.get("/finance/client-statements")
async def get_client_statements(
    tenant_id: str = Depends(get_tenant_id),
    user: dict = Depends(get_current_user),
    sort_by: str = "outstanding_desc",
    show_paid: bool = True
):
    """
    Get all clients with their outstanding amounts grouped by trip.
    Returns data matching the Excel statement summary format.
    """
    await check_permission(user, page="finance")
    clients = await db.clients.find({"tenant_id": tenant_id}).to_list(1000)

    trips = await db.trips.find(
        {"tenant_id": tenant_id}
    ).sort("created_at", -1).limit(20).to_list(20)
    trip_numbers = [t.get("trip_number", f"T{i}") for i, t in enumerate(trips)]
    trip_ids = {t.get("id"): t.get("trip_number") for t in trips}

    # Get all invoices (include paid if show_paid)
    status_filter = ["draft", "sent", "overdue", "partial", "paid"] if show_paid else ["draft", "sent", "overdue", "partial", "paid"]
    invoices = await db.invoices.find({
        "tenant_id": tenant_id,
    }).to_list(5000)

    # Build client statements
    client_statements = []
    total_outstanding = 0
    total_overdue = 0

    for client in clients:
        client_id = client.get("id")
        client_invoices = [inv for inv in invoices if inv.get("client_id") == client_id]

        if not client_invoices:
            continue

        client_total_invoiced = sum(inv.get("total", 0) for inv in client_invoices)
        client_total_outstanding = sum(
            max(0, inv.get("total", 0) - inv.get("paid_amount", 0))
            for inv in client_invoices
            if inv.get("status") not in ["draft"]
        )

        if client_total_outstanding <= 0 and not show_paid:
            continue

        # Group by trip with richer info
        trip_amounts = {}
        for inv in client_invoices:
            if inv.get("status") == "draft":
                continue
            trip_id = inv.get("trip_id")
            trip_num = trip_ids.get(trip_id, "Other") if trip_id else "Other"
            invoiced = inv.get("total", 0)
            outstanding = max(0, invoiced - inv.get("paid_amount", 0))
            status = inv.get("status", "sent")
            if trip_num not in trip_amounts:
                trip_amounts[trip_num] = {"invoiced": 0, "outstanding": 0, "status": "paid"}
            trip_amounts[trip_num]["invoiced"] = round(trip_amounts[trip_num]["invoiced"] + invoiced, 2)
            trip_amounts[trip_num]["outstanding"] = round(trip_amounts[trip_num]["outstanding"] + outstanding, 2)
            # Escalate status
            cur = trip_amounts[trip_num]["status"]
            if status == "overdue":
                trip_amounts[trip_num]["status"] = "overdue"
            elif status in ["sent", "partial"] and cur != "overdue":
                trip_amounts[trip_num]["status"] = "unpaid" if outstanding > 0 else "partial"
            elif outstanding > 0 and outstanding < invoiced and cur == "paid":
                trip_amounts[trip_num]["status"] = "partial"

        client_overdue = sum(
            max(0, inv.get("total", 0) - inv.get("paid_amount", 0))
            for inv in client_invoices if inv.get("status") == "overdue"
        )

        total_outstanding += client_total_outstanding
        total_overdue += client_overdue

        client_statements.append({
            "client_id": client_id,
            "client_name": client.get("name", "Unknown"),
            "client_email": client.get("email"),
            "client_phone": client.get("phone"),
            "total_invoiced": round(client_total_invoiced, 2),
            "total_outstanding": round(client_total_outstanding, 2),
            "trip_amounts": trip_amounts,
            "invoice_count": len(client_invoices),
            "has_overdue": client_overdue > 0
        })

    # Sort
    sort_map = {
        "outstanding_desc": lambda x: -x["total_outstanding"],
        "outstanding_asc": lambda x: x["total_outstanding"],
        "name_asc": lambda x: x["client_name"].lower(),
        "name_desc": lambda x: x["client_name"].lower(),
    }
    reverse = sort_by == "name_desc"
    key_fn = sort_map.get(sort_by, lambda x: -x["total_outstanding"])
    client_statements.sort(key=key_fn, reverse=(sort_by == "name_desc"))

    return {
        "statements": client_statements,
        "trip_columns": trip_numbers[:20],
        "summary": {
            "total_outstanding": round(total_outstanding, 2),
            "clients_with_debt": len([s for s in client_statements if s["total_outstanding"] > 0]),
            "overdue_amount": round(total_overdue, 2)
        }
    }

@router.get("/finance/client-statements/{client_id}/invoices")
async def get_client_statement_invoices(client_id: str, tenant_id: str = Depends(get_tenant_id)):
    """Get all unpaid/partial invoices for a specific client"""
    invoices = await db.invoices.find({
        "tenant_id": tenant_id,
        "client_id": client_id,
        "status": {"$in": ["draft", "sent", "overdue"]}
    }).sort("created_at", -1).to_list(1000)
    
    # Get trip info for each invoice
    trip_ids = list(set(inv.get("trip_id") for inv in invoices if inv.get("trip_id")))
    trips = await db.trips.find({"id": {"$in": trip_ids}}).to_list(1000)
    trip_map = {t.get("id"): t for t in trips}
    
    result = []
    for inv in invoices:
        trip = trip_map.get(inv.get("trip_id"), {})
        outstanding = inv.get("total", 0) - inv.get("paid_amount", 0)
        result.append({
            "id": inv.get("id"),
            "invoice_number": inv.get("invoice_number"),
            "trip_number": trip.get("trip_number", "-"),
            "total": inv.get("total", 0),
            "paid_amount": inv.get("paid_amount", 0),
            "outstanding": outstanding,
            "due_date": inv.get("due_date"),
            "status": inv.get("status"),
            "created_at": inv.get("created_at")
        })
    
    return result


# ============ FINANCE - TRIP WORKSHEETS ============

@router.get("/finance/trip-worksheet/{trip_id}")
async def get_trip_worksheet(trip_id: str, tenant_id: str = Depends(get_tenant_id)):
    """Get invoice breakdown for a specific trip with weight, CBM, and rate calculations."""
    trip = await db.trips.find_one({"id": trip_id, "tenant_id": tenant_id})
    if not trip:
        raise HTTPException(status_code=404, detail="Trip not found")

    invoices = await db.invoices.find({"tenant_id": tenant_id, "trip_id": trip_id}).to_list(1000)
    client_ids = list(set(inv.get("client_id") for inv in invoices if inv.get("client_id")))
    clients = await db.clients.find({"id": {"$in": client_ids}}).to_list(1000)
    client_map = {c.get("id"): c for c in clients}

    # Fetch KES exchange rate
    settings = await db.settings.find_one({"tenant_id": tenant_id}, {"_id": 0})
    kes_rate = 6.67
    if settings and settings.get("currencies"):
        for cur in settings["currencies"]:
            if cur.get("code") == "KES":
                kes_rate = cur.get("exchange_rate", 6.67)

    # Get capacity from vehicle if assigned, otherwise from trip defaults
    capacity_kg = 0
    capacity_cbm = 0
    vehicle_info = None
    
    vehicle_id = trip.get("vehicle_id")
    if vehicle_id:
        vehicle = await db.vehicles.find_one({"id": vehicle_id, "tenant_id": tenant_id}, {"_id": 0})
        if vehicle:
            capacity_kg = vehicle.get("max_weight_kg") or vehicle.get("capacity_kg") or 0
            capacity_cbm = vehicle.get("max_volume_cbm") or vehicle.get("capacity_cbm") or 0
            vehicle_info = {
                "id": vehicle.get("id"),
                "name": vehicle.get("name", ""),
                "registration": vehicle.get("registration", ""),
                "type": vehicle.get("vehicle_type", "")
            }
    
    # Fallback to trip-level capacity if no vehicle
    if capacity_kg == 0:
        capacity_kg = trip.get("capacity_kg") or 0
    if capacity_cbm == 0:
        capacity_cbm = trip.get("capacity_cbm") or 0

    invoice_list = []
    total_revenue = 0
    total_collected = 0
    total_outstanding = 0
    total_weight_kg = 0
    total_shipping_kg = 0
    total_cbm = 0
    invoices_paid = 0

    for inv in invoices:
        client = client_map.get(inv.get("client_id"), {})
        total = inv.get("total", 0)
        paid = inv.get("paid_amount", 0)
        outstanding = total - paid

        # Fetch line items for dimension data
        line_items = await db.invoice_line_items.find(
            {"invoice_id": inv.get("id")}, {"_id": 0}
        ).to_list(200)

        inv_weight = 0
        inv_shipping_weight = 0
        inv_cbm = 0
        volumetric_div = 5000  # cm³/kg divisor

        for item in line_items:
            w = item.get("weight_kg") or item.get("actual_weight", 0) or 0
            l = item.get("length_cm") or 0
            wd = item.get("width_cm") or 0
            h = item.get("height_cm") or 0
            vol_kg = (l * wd * h) / volumetric_div if (l and wd and h) else 0
            cbm = (l * wd * h) / 1000000 if (l and wd and h) else 0
            ship_kg = max(w, vol_kg)
            inv_weight += w
            inv_shipping_weight += ship_kg
            inv_cbm += cbm

        # Fallback: use client weight from shipments
        if inv_weight == 0:
            shipments_for_inv = await db.shipments.find(
                {"invoice_id": inv.get("id")}, {"_id": 0, "total_weight": 1}
            ).to_list(200)
            if not shipments_for_inv:
                shipments_for_inv = await db.shipments.find(
                    {"client_id": inv.get("client_id"), "trip_id": trip_id},
                    {"_id": 0, "total_weight": 1}
                ).to_list(200)
            inv_weight = sum(s.get("total_weight", 0) or 0 for s in shipments_for_inv)
            inv_shipping_weight = inv_weight

        effective_rate = round(total / inv_shipping_weight, 2) if inv_shipping_weight > 0 else 0
        paid_kes = round(paid * kes_rate, 2)

        total_revenue += total
        total_collected += paid
        total_outstanding += outstanding
        total_weight_kg += inv_weight
        total_shipping_kg += inv_shipping_weight
        total_cbm += inv_cbm

        if inv.get("status") == "paid":
            invoices_paid += 1

        # Determine display status
        status = inv.get("status", "draft")
        if status == "sent" and inv.get("due_date"):
            try:
                due_str = inv["due_date"]
                due = datetime.fromisoformat(due_str.replace("Z", "+00:00")) if "T" in str(due_str) else datetime.fromisoformat(str(due_str)).replace(tzinfo=timezone.utc)
                if due.tzinfo is None:
                    due = due.replace(tzinfo=timezone.utc)
                if due < datetime.now(timezone.utc):
                    status = "overdue"
            except Exception:
                pass

        invoice_list.append({
            "id": inv.get("id"),
            "invoice_number": inv.get("invoice_number"),
            "client_id": inv.get("client_id"),
            "client_name": client.get("name", "Unknown"),
            "client_email": client.get("email"),
            "recipient": inv.get("recipient") or client.get("name", "-"),
            "weight_kg": round(inv_weight, 2),
            "shipping_weight": round(inv_shipping_weight, 2),
            "cbm": round(inv_cbm, 4),
            "effective_rate": effective_rate,
            "total_amount": round(total, 2),
            "paid_amount": round(paid, 2),
            "paid_kes": paid_kes,
            "outstanding": round(outstanding, 2),
            "status": status,
            "comment": inv.get("comment", ""),
            "due_date": inv.get("due_date"),
            "created_at": inv.get("created_at")
        })

    invoice_list.sort(key=lambda x: x["client_name"].lower())

    remaining_kg = max(0, capacity_kg - total_shipping_kg) if capacity_kg else 0
    remaining_cbm = max(0, capacity_cbm - total_cbm) if capacity_cbm else 0
    revenue_per_kg = round(total_revenue / total_shipping_kg, 2) if total_shipping_kg > 0 else 0
    revenue_per_ton = round(total_revenue / (total_shipping_kg / 1000), 2) if total_shipping_kg > 0 else 0
    max_revenue_estimate = round(capacity_kg * revenue_per_kg, 2) if capacity_kg and revenue_per_kg else 0

    return {
        "trip": {
            "id": trip.get("id"),
            "trip_number": trip.get("trip_number"),
            "status": trip.get("status"),
            "route": trip.get("route", []),
            "departure_date": trip.get("departure_date"),
            "capacity_kg": capacity_kg,
            "capacity_cbm": capacity_cbm,
            "vehicle": vehicle_info
        },
        "summary": {
            "total_revenue": round(total_revenue, 2),
            "total_collected": round(total_collected, 2),
            "total_outstanding": round(total_outstanding, 2),
            "collection_percent": round((total_collected / total_revenue * 100) if total_revenue > 0 else 0, 1),
            "invoices_paid": invoices_paid,
            "invoices_total": len(invoices),
            "used_kg": round(total_shipping_kg, 2),
            "remaining_kg": round(remaining_kg, 2),
            "used_cbm": round(total_cbm, 4),
            "remaining_cbm": round(remaining_cbm, 4),
            "revenue_per_kg": revenue_per_kg,
            "revenue_per_ton": revenue_per_ton,
            "max_revenue_estimate": max_revenue_estimate
        },
        "invoices": invoice_list
    }


@router.get("/finance/trip-worksheet/{trip_id}/pdf")
async def get_trip_worksheet_pdf(trip_id: str, tenant_id: str = Depends(get_tenant_id)):
    """
    Generate PDF worksheet for a trip with invoice breakdown.
    """
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.units import mm
    from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
    from reportlab.lib.enums import TA_RIGHT, TA_CENTER, TA_LEFT
    
    # Get trip
    trip = await db.trips.find_one({"id": trip_id, "tenant_id": tenant_id})
    if not trip:
        raise HTTPException(status_code=404, detail="Trip not found")
    
    # Get all invoices for this trip
    invoices = await db.invoices.find({
        "tenant_id": tenant_id,
        "trip_id": trip_id
    }, {"_id": 0}).to_list(1000)
    
    # Get clients
    client_ids = list(set(inv.get("client_id") for inv in invoices if inv.get("client_id")))
    clients = await db.clients.find({"id": {"$in": client_ids}}, {"_id": 0}).to_list(1000)
    client_map = {c.get("id"): c for c in clients}
    
    # Get shipments for weight info
    shipments = await db.shipments.find({"trip_id": trip_id}, {"_id": 0}).to_list(1000)
    client_weights = {}
    for s in shipments:
        cid = s.get("client_id")
        if cid:
            client_weights[cid] = client_weights.get(cid, 0) + (s.get("total_weight", 0) or 0)
    
    # Calculate totals
    total_revenue = sum(inv.get("total", 0) for inv in invoices)
    total_paid = sum(inv.get("paid_amount", 0) for inv in invoices)
    total_outstanding = total_revenue - total_paid
    
    # Create PDF
    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4, leftMargin=15*mm, rightMargin=15*mm, topMargin=15*mm, bottomMargin=15*mm)
    
    # Define colors
    olive = colors.HexColor('#6B633C')
    dark_gray = colors.HexColor('#3C3F42')
    light_gray = colors.HexColor('#F5F5F5')
    
    # Styles - use unique names to avoid conflicts with getSampleStyleSheet()
    styles = getSampleStyleSheet()
    styles.add(ParagraphStyle(name='WorksheetTitle', fontSize=18, fontName='Helvetica-Bold', textColor=olive, alignment=TA_CENTER))
    styles.add(ParagraphStyle(name='WorksheetSubtitle', fontSize=12, fontName='Helvetica', textColor=dark_gray, alignment=TA_CENTER))
    styles.add(ParagraphStyle(name='WorksheetSectionTitle', fontSize=11, fontName='Helvetica-Bold', textColor=dark_gray))
    
    elements = []
    
    # Title
    trip_number = trip.get("trip_number", "Unknown")
    elements.append(Paragraph(f"Trip Worksheet: {trip_number}", styles['WorksheetTitle']))
    elements.append(Spacer(1, 3*mm))
    
    # Trip info
    route = " → ".join(trip.get("route", []))
    departure = trip.get("departure_date", "")
    elements.append(Paragraph(f"Route: {route}", styles['WorksheetSubtitle']))
    elements.append(Paragraph(f"Departure: {departure} | Status: {trip.get('status', 'unknown').title()}", styles['WorksheetSubtitle']))
    elements.append(Spacer(1, 8*mm))
    
    # Summary section
    elements.append(Paragraph("Summary", styles['WorksheetSectionTitle']))
    elements.append(Spacer(1, 3*mm))
    
    summary_data = [
        ['Total Revenue', 'Total Collected', 'Outstanding', 'Invoices'],
        [f"R {total_revenue:,.2f}", f"R {total_paid:,.2f}", f"R {total_outstanding:,.2f}", f"{len(invoices)}"]
    ]
    summary_table = Table(summary_data, colWidths=[45*mm, 45*mm, 45*mm, 35*mm])
    summary_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), olive),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 10),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.lightgrey),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
        ('TOPPADDING', (0, 0), (-1, -1), 6),
    ]))
    elements.append(summary_table)
    elements.append(Spacer(1, 8*mm))
    
    # Invoice details
    elements.append(Paragraph("Invoice Details", styles['WorksheetSectionTitle']))
    elements.append(Spacer(1, 3*mm))
    
    # Invoice table header
    table_data = [['Invoice #', 'Client', 'Weight (kg)', 'Total', 'Paid', 'Outstanding', 'Status']]
    
    # Sort invoices by client name
    sorted_invoices = sorted(invoices, key=lambda x: client_map.get(x.get("client_id"), {}).get("name", "").lower())
    
    for inv in sorted_invoices:
        client = client_map.get(inv.get("client_id"), {})
        weight = client_weights.get(inv.get("client_id"), 0)
        total = inv.get("total", 0)
        paid = inv.get("paid_amount", 0)
        outstanding = total - paid
        status = inv.get("status", "draft").title()
        
        table_data.append([
            inv.get("invoice_number", "-"),
            client.get("name", "Unknown")[:25],
            f"{weight:.1f}",
            f"R {total:,.2f}",
            f"R {paid:,.2f}",
            f"R {outstanding:,.2f}",
            status
        ])
    
    if len(table_data) == 1:
        table_data.append(['-', 'No invoices found', '-', '-', '-', '-', '-'])
    
    invoice_table = Table(table_data, colWidths=[25*mm, 45*mm, 20*mm, 28*mm, 28*mm, 28*mm, 18*mm])
    invoice_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), olive),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 9),
        ('ALIGN', (2, 0), (-1, -1), 'RIGHT'),
        ('ALIGN', (0, 0), (1, -1), 'LEFT'),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.lightgrey),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
        ('TOPPADDING', (0, 0), (-1, -1), 5),
    ]))
    
    # Alternating row colors
    for i in range(1, len(table_data)):
        if i % 2 == 0:
            invoice_table.setStyle(TableStyle([('BACKGROUND', (0, i), (-1, i), light_gray)]))
    
    elements.append(invoice_table)
    elements.append(Spacer(1, 10*mm))
    
    # Footer
    elements.append(Paragraph(f"Generated on {datetime.now().strftime('%Y-%m-%d %H:%M')} | Servex Holdings", 
                              ParagraphStyle(name='Footer', fontSize=8, textColor=colors.gray, alignment=TA_CENTER)))
    
    # Build PDF
    doc.build(elements)
    buffer.seek(0)
    
    filename = f"Worksheet-{trip_number}.pdf"
    return StreamingResponse(
        buffer,
        media_type="application/pdf",
        headers={"Content-Disposition": f"attachment; filename={filename}"}
    )


# ============ FINANCE - OVERDUE INVOICES ============

@router.get("/finance/overdue")
async def get_overdue_invoices(
    tenant_id: str = Depends(get_tenant_id),
    trip_id: Optional[str] = None,
    sort_by: Optional[str] = "amount_desc",
    sort_order: Optional[str] = "desc"
):
    """Get all overdue invoices sorted by days overdue or amount or client name"""
    now = datetime.now(timezone.utc)
    
    # Build query
    query = {
        "tenant_id": tenant_id,
        "status": {"$in": ["draft", "sent", "overdue"]},
        "due_date": {"$lt": now.isoformat()}
    }
    
    # Add trip filter if provided
    if trip_id:
        query["trip_id"] = trip_id
    
    # Get invoices where due_date < now and status is not paid
    invoices = await db.invoices.find(query).to_list(1000)
    
    # Get clients - use id field instead of _id
    client_ids = list(set(inv.get("client_id") for inv in invoices if inv.get("client_id")))
    clients = await db.clients.find({"id": {"$in": client_ids}}).to_list(1000)
    client_map = {c.get("id"): c for c in clients}
    
    # Get trips - use id field instead of _id
    trip_ids = list(set(inv.get("trip_id") for inv in invoices if inv.get("trip_id")))
    trips = await db.trips.find({"id": {"$in": trip_ids}}).to_list(1000)
    trip_map = {t.get("id"): t for t in trips}
    
    result = []
    for inv in invoices:
        client = client_map.get(inv.get("client_id"), {})
        trip = trip_map.get(inv.get("trip_id"), {})
        
        outstanding = inv.get("total", 0) - inv.get("paid_amount", 0)
        if outstanding <= 0:
            continue
        
        # Calculate days overdue
        due_date = inv.get("due_date")
        if isinstance(due_date, str):
            # Handle ISO format with or without timezone
            try:
                if 'T' in due_date:
                    due = datetime.fromisoformat(due_date.replace("Z", "+00:00"))
                else:
                    # Date-only format like "2025-12-31"
                    due = datetime.fromisoformat(due_date).replace(tzinfo=timezone.utc)
            except (ValueError, TypeError, AttributeError):
                due = None
            if due and due.tzinfo is None:
                due = due.replace(tzinfo=timezone.utc)
        elif due_date:
            due = due_date
            if due.tzinfo is None:
                due = due.replace(tzinfo=timezone.utc)
        else:
            due = None
        
        days_overdue = (now - due).days if due else 0
        
        result.append({
            "id": inv.get("id"),
            "invoice_number": inv.get("invoice_number"),
            "client_id": inv.get("client_id"),
            "client_name": client.get("name", "Unknown"),
            "client_email": client.get("email"),
            "client_whatsapp": client.get("whatsapp") or client.get("phone"),
            "trip_number": trip.get("trip_number", "-"),
            "due_date": due_date,
            "days_overdue": days_overdue,
            "total": inv.get("total", 0),
            "paid_amount": inv.get("paid_amount", 0),
            "outstanding": outstanding
        })
    
    # Sort based on sort_by parameter
    if sort_by == "amount_desc":
        result.sort(key=lambda x: x["outstanding"], reverse=True)
    elif sort_by == "amount_asc":
        result.sort(key=lambda x: x["outstanding"])
    elif sort_by == "client_asc":
        result.sort(key=lambda x: x["client_name"].lower())
    elif sort_by == "client_desc":
        result.sort(key=lambda x: x["client_name"].lower(), reverse=True)
    else:
        # Default: sort by days overdue (most overdue first)
        result.sort(key=lambda x: x["days_overdue"], reverse=True)
    
    return {
        "invoices": result,
        "total_overdue": sum(i["outstanding"] for i in result),
        "count": len(result)
    }


# ============ FINANCE - EMAIL INVOICE ============

class EmailInvoiceRequest(BaseModel):
    to: str
    subject: str
    body: str
    attach_pdf: bool = True

@router.post("/invoices/{invoice_id}/send-email")
async def send_invoice_email(
    invoice_id: str,
    request: EmailInvoiceRequest,
    tenant_id: str = Depends(get_tenant_id),
    current_user: dict = Depends(get_current_user)
):
    """
    Send invoice via email with PDF attachment.
    NOTE: This is a placeholder - actual email sending requires SMTP configuration.
    """
    # Get invoice - use id field instead of _id
    invoice = await db.invoices.find_one({"id": invoice_id, "tenant_id": tenant_id})
    if not invoice:
        raise HTTPException(status_code=404, detail="Invoice not found")
    
    # Log the email attempt (even if we can't actually send)
    email_log = {
        "id": str(uuid.uuid4()),
        "tenant_id": tenant_id,
        "invoice_id": invoice_id,
        "to_email": request.to,
        "subject": request.subject,
        "body": request.body,
        "sent_by": current_user.get("id"),
        "sent_at": datetime.now(timezone.utc).isoformat(),
        "status": "logged"  # Would be "sent" with actual SMTP
    }
    
    # In production, this would use SendGrid or SMTP
    # For now, we just log it
    await db.email_logs.insert_one(email_log)
    
    # Update invoice with email sent info
    await db.invoices.update_one(
        {"id": invoice_id},
        {"$set": {
            "email_sent_at": datetime.now(timezone.utc).isoformat(),
            "email_sent_to": request.to
        }}
    )
    
    # Create audit log
    await db.audit_logs.insert_one({
        "id": str(uuid.uuid4()),
        "tenant_id": tenant_id,
        "user_id": current_user.get("id"),
        "action": "email_sent",
        "table_name": "invoices",
        "record_id": invoice_id,
        "old_value": None,
        "new_value": {"to": request.to, "subject": request.subject},
        "created_at": datetime.now(timezone.utc).isoformat()
    })
    
    return {"message": "Email sent successfully (MOCKED)", "to": request.to}

# ============ CLIENT DEBT & STATEMENTS ============

@router.get("/client-debt-summary")
async def get_client_debt_summary(tenant_id: str = Depends(get_tenant_id)):
    """Get summary of all clients with outstanding debt"""
    # Aggregate unpaid/partially paid invoices by client
    pipeline = [
        {
            "$match": {
                "tenant_id": tenant_id,
                "status": {"$in": ["sent", "overdue", "partially_paid"]}
            }
        },
        {
            "$group": {
                "_id": "$client_id",
                "total_outstanding": {"$sum": "$balance_due"},
                "invoice_count": {"$sum": 1},
                "oldest_invoice_date": {"$min": "$issue_date"}
            }
        }
    ]
    
    results = await db.invoices.aggregate(pipeline).to_list(1000)
    
    # Enrich with client details
    client_debts = []
    for item in results:
        if not item["_id"]:
            continue
            
        client = await db.clients.find_one({"id": item["_id"]}, {"_id": 0})
        if client:
            client_debts.append({
                "client_id": item["_id"],
                "client_name": client.get("name"),
                "client_email": client.get("email"),
                "client_phone": client.get("phone"),
                "total_outstanding": round(item["total_outstanding"], 2),
                "invoice_count": item["invoice_count"],
                "oldest_invoice_date": item["oldest_invoice_date"]
            })
    
    # Sort by outstanding amount descending
    client_debts.sort(key=lambda x: x["total_outstanding"], reverse=True)
    
    return client_debts

@router.get("/client-statement/{client_id}")
async def get_client_statement(
    client_id: str,
    tenant_id: str = Depends(get_tenant_id)
):
    """Get statement of unpaid invoices for a client"""
    # Get client details
    client = await db.clients.find_one({"id": client_id, "tenant_id": tenant_id}, {"_id": 0})
    if not client:
        raise HTTPException(status_code=404, detail="Client not found")
    
    # Get unpaid invoices
    invoices = await db.invoices.find(
        {
            "tenant_id": tenant_id,
            "client_id": client_id,
            "status": {"$in": ["sent", "overdue", "partially_paid"]}
        },
        {"_id": 0}
    ).sort("issue_date", 1).to_list(2000)
    
    # Calculate totals
    total_outstanding = sum(inv.get("balance_due", 0) for inv in invoices)
    
    return {
        "client": client,
        "invoices": invoices,
        "total_outstanding": round(total_outstanding, 2),
        "statement_date": datetime.now(timezone.utc).isoformat()
    }


@router.get("/finance/client-statement/{client_id}/pdf")
async def get_client_statement_pdf(
    client_id: str,
    tenant_id: str = Depends(get_tenant_id)
):
    """Generate a PDF client statement showing all invoices and payments (Session I M-03)"""
    from services.pdf_service import generate_client_statement_pdf
    return await generate_client_statement_pdf(client_id, tenant_id)

class WhatsAppReminderRequest(BaseModel):
    client_ids: List[str]
    message_template: Optional[str] = None

@router.post("/send-payment-reminders")
async def send_payment_reminders(
    request: WhatsAppReminderRequest,
    tenant_id: str = Depends(get_tenant_id),
    current_user: dict = Depends(get_current_user)
):
    """Send WhatsApp payment reminders to selected clients"""
    reminders_sent = []
    
    for client_id in request.client_ids:
        # Get client details
        client = await db.clients.find_one({"id": client_id, "tenant_id": tenant_id}, {"_id": 0})
        if not client or not client.get("phone"):
            continue
        
        # Get outstanding amount
        pipeline = [
            {
                "$match": {
                    "tenant_id": tenant_id,
                    "client_id": client_id,
                    "status": {"$in": ["sent", "overdue", "partially_paid"]}
                }
            },
            {
                "$group": {
                    "_id": None,
                    "total": {"$sum": "$balance_due"},
                    "count": {"$sum": 1}
                }
            }
        ]
        
        result = await db.invoices.aggregate(pipeline).to_list(1)
        if not result:
            continue
        
        outstanding = result[0]["total"]
        invoice_count = result[0]["count"]
        
        # Default message if not provided
        message = request.message_template or f"Hi {client.get('name')}, you have {invoice_count} outstanding invoice(s) totaling R {outstanding:.2f}. Please remit payment at your earliest convenience. Thank you."
        
        # Log the reminder (actual WhatsApp sending would use Twilio API)
        reminder_log = {
            "id": str(uuid.uuid4()),
            "tenant_id": tenant_id,
            "client_id": client_id,
            "phone": client.get("phone"),
            "message": message,
            "outstanding_amount": outstanding,
            "invoice_count": invoice_count,
            "sent_by": current_user.get("id"),
            "sent_at": datetime.now(timezone.utc).isoformat(),
            "status": "logged"  # Would be "sent" with actual WhatsApp API
        }
        
        await db.whatsapp_logs.insert_one(reminder_log)
        
        reminders_sent.append({
            "client_id": client_id,
            "client_name": client.get("name"),
            "phone": client.get("phone"),
            "amount": outstanding
        })
    
    return {
        "message": f"Reminders logged for {len(reminders_sent)} client(s) (MOCKED)",
        "reminders": reminders_sent
    }

# ============ SETTINGS - BANKING DETAILS ============

class BankAccount(BaseModel):
    currency: str
    bank_name: str
    account_name: str
    account_number: str
    branch_code: Optional[str] = None
    swift_code: Optional[str] = None

class BankingDetailsRequest(BaseModel):
    accounts: List[BankAccount]

@router.get("/settings/banking-details")
async def get_banking_details(tenant_id: str = Depends(get_tenant_id)):
    """Get banking details for all currencies"""
    try:
        settings = await db.settings.find_one({"tenant_id": tenant_id}, {"_id": 0})
        
        if settings and settings.get("banking_details"):
            return {"accounts": settings["banking_details"]}
        
        # Return default accounts
        return {
            "accounts": [
                {
                    "currency": "ZAR",
                    "bank_name": "FNB (First National Bank)",
                    "account_name": "Servex Holdings",
                    "account_number": "62XXXXXXXXXX",
                    "branch_code": "250655",
                    "swift_code": "FIRNZAJJ"
                },
                {
                    "currency": "KES",
                    "bank_name": "Equity Bank Kenya",
                    "account_name": "Servex Holdings Ltd",
                    "account_number": "01XXXXXXXXXX",
                    "branch_code": "068",
                    "swift_code": "EQBLKENA"
                }
            ]
        }
    except Exception as e:
        # Return default accounts on any error
        return {
            "accounts": [
                {
                    "currency": "ZAR",
                    "bank_name": "",
                    "account_name": "",
                    "account_number": "",
                    "branch_code": "",
                    "swift_code": ""
                },
                {
                    "currency": "KES",
                    "bank_name": "",
                    "account_name": "",
                    "account_number": "",
                    "branch_code": "",
                    "swift_code": ""
                }
            ]
        }

@router.put("/settings/banking-details")
async def update_banking_details(
    request: BankingDetailsRequest,
    tenant_id: str = Depends(get_tenant_id),
    current_user: dict = Depends(get_current_user)
):
    """Update banking details"""
    await db.settings.update_one(
        {"tenant_id": tenant_id},
        {
            "$set": {
                "banking_details": [acc.dict() for acc in request.accounts],
                "updated_at": datetime.now(timezone.utc).isoformat(),
                "updated_by": current_user.get("id")
            }
        },
        upsert=True
    )
    
    return {"message": "Banking details updated successfully"}
