"""
PDF generation service for Servex Holdings backend.
Handles invoice PDF generation using ReportLab.
"""
from io import BytesIO
from datetime import datetime
from pathlib import Path
from fastapi import HTTPException
from fastapi.responses import StreamingResponse
from reportlab.lib.pagesizes import letter, A4
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch, mm
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, Image
from reportlab.lib.enums import TA_CENTER, TA_RIGHT, TA_LEFT

from database import db


def format_weight(weight, decimals=4):
    """Format weight with specified decimal places"""
    if weight is None:
        return "-"
    return f"{float(weight):.{decimals}f}"


def format_dimension(dim, decimals=3):
    """Format dimension with specified decimal places"""
    if dim is None:
        return "-"
    return f"{float(dim):.{decimals}f}"


def format_dimensions(length, width, height, decimals=3):
    """Format L×W×H dimensions"""
    if not length and not width and not height:
        return "-"
    len_str = format_dimension(length, decimals) if length else "0"
    wid_str = format_dimension(width, decimals) if width else "0"
    hei_str = format_dimension(height, decimals) if height else "0"
    return f"{len_str} × {wid_str} × {hei_str}"


def format_currency(amount, currency="ZAR"):
    """Format currency amount"""
    if amount is None:
        return "-"
    symbols = {"ZAR": "R", "KES": "KES", "USD": "$", "EUR": "€", "GBP": "£"}
    symbol = symbols.get(currency, currency)
    return f"{symbol} {float(amount):,.2f}"


def get_payment_terms_display(payment_terms, payment_terms_custom, total):
    """Get payment terms display text with calculated amounts"""
    if not payment_terms:
        return None
    
    terms_map = {
        "full_on_receipt": "Full payment due on receipt",
        "net_30": "Net 30 days",
        "custom": payment_terms_custom or "Custom terms"
    }
    
    if payment_terms == "50_50":
        half = total / 2
        return f"50% upfront, 50% on delivery\n• Due on receipt: {format_currency(half)}\n• Due on delivery: {format_currency(half)}"
    elif payment_terms == "30_70":
        upfront = total * 0.3
        delivery = total * 0.7
        return f"30% upfront, 70% on delivery\n• Due on receipt: {format_currency(upfront)}\n• Due on delivery: {format_currency(delivery)}"
    
    return terms_map.get(payment_terms, payment_terms)


async def generate_invoice_pdf(
    invoice_id: str,
    tenant_id: str
):
    """Generate Servex Holdings TYPE 2 invoice PDF - exact template match."""
    # --- Fetch data ---
    invoice = await db.invoices.find_one({"id": invoice_id, "tenant_id": tenant_id}, {"_id": 0})
    if not invoice:
        raise HTTPException(status_code=404, detail="Invoice not found")

    client = await db.clients.find_one({"id": invoice.get("client_id")}, {"_id": 0})
    client_name = invoice.get("client_name_snapshot") or (client.get("name") if client else "Unknown")
    client_phone = invoice.get("client_phone_snapshot") or (client.get("phone") if client else "")
    recipient_phone = ""

    line_items = await db.invoice_line_items.find({"invoice_id": invoice_id}, {"_id": 0}).to_list(200)
    shipment_ids = [li.get("shipment_id") for li in line_items if li.get("shipment_id")]
    shipments = {}
    if shipment_ids:
        for s in await db.shipments.find({"id": {"$in": shipment_ids}}, {"_id": 0}).to_list(200):
            shipments[s["id"]] = s

    # Get recipient phone from first shipment
    first_li = line_items[0] if line_items else {}
    first_ship = shipments.get(first_li.get("shipment_id", ""), {}) if first_li else {}
    recipient_phone = first_ship.get("recipient_phone", "")
    destination = first_ship.get("destination") or "Nairobi Kenya"

    payments = await db.payments.find({"invoice_id": invoice_id}, {"_id": 0}).to_list(100)
    paid_amount = sum(p.get("amount", 0) for p in payments)

    # KES rate
    settings = await db.settings.find_one({"tenant_id": tenant_id})
    kes_rate = 7.5
    if settings and settings.get("currencies"):
        for cur in settings["currencies"]:
            if cur.get("code") == "KES":
                kes_rate = cur.get("exchange_rate", 7.5)

    currency = invoice.get("currency", "ZAR")
    total = invoice.get("total", 0)
    subtotal = invoice.get("subtotal", total)
    adj_total = invoice.get("adjustments", 0)
    outstanding = total - paid_amount
    invoice_number = invoice.get('invoice_number', '')

    # --- Format date ---
    issue_date_str = invoice.get('issue_date') or str(invoice.get('created_at', ''))[:10]
    try:
        issue_dt = datetime.fromisoformat(issue_date_str.replace('Z', '+00:00'))
        issue_date_fmt = issue_dt.strftime('%d/%m/%Y')
    except Exception:
        issue_date_fmt = issue_date_str

    # --- Colors ---
    dark_red = colors.HexColor('#CC0000')
    black = colors.black
    white = colors.white
    light_gray = colors.HexColor('#F5F5F5')
    header_bg = colors.HexColor('#2D2D2D')

    # --- Build PDF ---
    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4, leftMargin=12*mm, rightMargin=12*mm, topMargin=12*mm, bottomMargin=10*mm)

    # Styles
    def S(name, **kw):
        return ParagraphStyle(name=name, **kw)

    p_normal = S('p_normal', fontSize=9, fontName='Helvetica', leading=12)
    p_bold = S('p_bold', fontSize=9, fontName='Helvetica-Bold', leading=12)
    p_small = S('p_small', fontSize=8, fontName='Helvetica', leading=10)
    p_small_bold = S('p_small_bold', fontSize=8, fontName='Helvetica-Bold', leading=10)
    p_red = S('p_red', fontSize=9, fontName='Helvetica-Bold', textColor=dark_red, leading=12)
    p_red_right = S('p_red_right', fontSize=11, fontName='Helvetica-Bold', textColor=dark_red, alignment=TA_RIGHT, leading=14)
    p_right = S('p_right', fontSize=9, fontName='Helvetica', alignment=TA_RIGHT, leading=12)
    p_right_bold = S('p_right_bold', fontSize=9, fontName='Helvetica-Bold', alignment=TA_RIGHT, leading=12)
    p_center = S('p_center', fontSize=8, fontName='Helvetica', alignment=TA_CENTER, leading=10)
    p_center_bold = S('p_center_bold', fontSize=9, fontName='Helvetica-Bold', alignment=TA_CENTER, leading=12)
    p_disclaimer = S('p_disclaimer', fontSize=6.5, fontName='Helvetica', leading=8, textColor=colors.HexColor('#444444'))
    p_title = S('p_title', fontSize=14, fontName='Helvetica-Bold', leading=18)

    elements = []
    pw = 186 * mm  # page width minus margins

    # ============================================================
    # 1. HEADER: Logo left | Tagline + Invoice Info right
    # ============================================================
    logo_path = Path(__file__).parent.parent / 'frontend' / 'public' / 'servex-logo.png'
    if logo_path.exists():
        try:
            from PIL import Image as PILImage
            pil = PILImage.open(logo_path)
            asp = pil.height / pil.width
            logo_img = Image(str(logo_path), width=45*mm, height=45*mm*asp)
        except Exception:
            logo_img = Paragraph("<b>Servex Holdings (PTY) Ltd</b>", p_title)
    else:
        logo_img = Paragraph("<b>Servex Holdings (PTY) Ltd</b>", p_title)

    right_header = []
    right_header.append(Paragraph("Logistics Services to Kenya and South Africa", p_red_right))
    right_header.append(Spacer(1, 3*mm))
    right_header.append(Paragraph(f"<b>INVOICE NO:</b> {invoice_number}", p_right_bold))
    right_header.append(Paragraph(f"<b>Date:</b> {issue_date_fmt}", p_right))

    h1 = Table([[logo_img, right_header]], colWidths=[70*mm, pw - 70*mm])
    h1.setStyle(TableStyle([
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('ALIGN', (1, 0), (1, 0), 'RIGHT'),
    ]))
    elements.append(h1)
    elements.append(Spacer(1, 4*mm))

    # ============================================================
    # 2. SENDER / RECIPIENT SECTION (bordered grid)
    # ============================================================
    grid_data = [
        [Paragraph(f"<b>Date:</b>  {issue_date_fmt}", p_small), Paragraph("", p_small)],
        [Paragraph(f"<b>Sender:</b>  {client_name}", p_small), Paragraph(f"<b>Contact no:</b>  {client_phone}", p_small)],
        [Paragraph(f"<b>Contact no:</b>  {recipient_phone}", p_small), Paragraph(f"<b>Destination:</b>  {destination}", p_small)],
    ]
    grid_t = Table(grid_data, colWidths=[pw/2, pw/2])
    grid_t.setStyle(TableStyle([
        ('BOX', (0, 0), (-1, -1), 0.8, black),
        ('INNERGRID', (0, 0), (-1, -1), 0.4, colors.HexColor('#CCCCCC')),
        ('SPAN', (0, 0), (1, 0)),
        ('TOPPADDING', (0, 0), (-1, -1), 4),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
        ('LEFTPADDING', (0, 0), (-1, -1), 6),
    ]))
    elements.append(grid_t)
    elements.append(Spacer(1, 3*mm))

    # ============================================================
    # 3. PAYMENT TERMS (red text)
    # ============================================================
    elements.append(Paragraph(
        f"<font color='#CC0000'><b>Payment Terms:</b> Full payment due upon invoice receipt. "
        f"Use invoice number {invoice_number} as payment reference.</font>",
        S('pt', fontSize=9, fontName='Helvetica-Bold', textColor=dark_red, leading=12)
    ))
    elements.append(Spacer(1, 3*mm))

    # ============================================================
    # 4. ITEMIZED TABLE
    # ============================================================
    tbl_headers = ['Item no', 'Recipient', 'Description', 'QTY', 'KG', 'L', 'W', 'H', 'V', 'Shipping\nWeight', 'Amount']
    tbl_data = [tbl_headers]
    total_qty = 0
    total_kg = 0.0
    total_ship_wt = 0.0
    total_amount = 0.0

    for idx, li in enumerate(line_items, 1):
        ship = shipments.get(li.get("shipment_id", ""), {})
        l_cm = float(li.get("length_cm") or ship.get("length_cm") or 0)
        w_cm = float(li.get("width_cm") or ship.get("width_cm") or 0)
        h_cm = float(li.get("height_cm") or ship.get("height_cm") or 0)
        qty = int(li.get("quantity") or 1)
        kg = float(li.get("weight_kg") or li.get("actual_weight") or 0)
        vol = round(l_cm * w_cm * h_cm / 1000000, 4) if (l_cm and w_cm and h_cm) else 0
        ship_wt = max(kg, l_cm * w_cm * h_cm / 5000) if (l_cm and w_cm and h_cm) else kg
        amount = float(li.get("amount") or 0)
        recip = li.get("recipient_name") or ship.get("recipient") or ""
        desc = li.get("description") or ""

        total_qty += qty
        total_kg += kg
        total_ship_wt += ship_wt
        total_amount += amount

        tbl_data.append([
            str(idx),
            recip[:18],
            desc[:28],
            str(qty),
            f"{kg:.2f}" if kg else "",
            f"{l_cm:.0f}" if l_cm else "",
            f"{w_cm:.0f}" if w_cm else "",
            f"{h_cm:.0f}" if h_cm else "",
            f"{vol:.4f}" if vol else "",
            f"{ship_wt:.2f}" if ship_wt else "",
            f"R {amount:,.2f}" if amount else ""
        ])

    # Totals row
    tbl_data.append([
        "*", "", "TOTALS",
        str(total_qty),
        f"{total_kg:.2f}",
        "", "", "", "",
        f"{total_ship_wt:.2f}",
        f"R {total_amount:,.2f}"
    ])

    col_w = [9*mm, 24*mm, 34*mm, 9*mm, 13*mm, 9*mm, 9*mm, 9*mm, 14*mm, 17*mm, 22*mm]
    items_t = Table(tbl_data, colWidths=col_w, repeatRows=1)
    ts = TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), header_bg),
        ('TEXTCOLOR', (0, 0), (-1, 0), white),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 7),
        ('FONTSIZE', (0, 1), (-1, -1), 7),
        ('ALIGN', (3, 0), (-1, -1), 'RIGHT'),
        ('ALIGN', (0, 0), (2, -1), 'LEFT'),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 3),
        ('TOPPADDING', (0, 0), (-1, -1), 3),
        ('LEFTPADDING', (0, 0), (-1, -1), 2),
        ('RIGHTPADDING', (0, 0), (-1, -1), 2),
        ('GRID', (0, 0), (-1, -1), 0.4, colors.HexColor('#DDDDDD')),
        ('LINEBELOW', (0, 0), (-1, 0), 1.5, black),
        # Totals row styling
        ('FONTNAME', (0, -1), (-1, -1), 'Helvetica-Bold'),
        ('BACKGROUND', (0, -1), (-1, -1), light_gray),
        ('LINEABOVE', (0, -1), (-1, -1), 1, black),
        # Red asterisk color
        ('TEXTCOLOR', (0, -1), (0, -1), dark_red),
    ])
    # Alternate row shading
    for i in range(1, len(tbl_data) - 1):
        if i % 2 == 0:
            ts.add('BACKGROUND', (0, i), (-1, i), light_gray)
    items_t.setStyle(ts)
    elements.append(items_t)
    elements.append(Spacer(1, 5*mm))

    # ============================================================
    # 5. PAYMENT INFORMATION + TOTALS (two columns)
    # ============================================================
    payment_info_text = (
        "<b>Payment Information:</b><br/>"
        "<b>FNB Business Account</b><br/>"
        f"Account name: Servex Holdings Pty Ltd<br/>"
        f"Account number: 63112859666<br/>"
        f"Branch: Bryanston<br/>"
        f"Payment Reference: Invoice {invoice_number}<br/>"
        f"Swift code: FIRNZAJJ"
    )

    # Totals sub-table
    totals_rows = [
        [Paragraph("Subtotal:", p_small_bold), Paragraph(f"R {subtotal:,.2f}", p_right)],
        [Paragraph("Other:", p_small_bold), Paragraph(f"R {adj_total:,.2f}", p_right)],
        [Paragraph("<b>Total Amount:</b>", p_bold), Paragraph(f"<b>R {total:,.2f}</b>", p_right_bold)],
    ]
    if paid_amount > 0:
        totals_rows.append([Paragraph("Paid:", p_small_bold), Paragraph(f"R {paid_amount:,.2f}", p_right)])
        totals_rows.append([Paragraph("<b>Outstanding:</b>", p_bold), Paragraph(f"<b>R {outstanding:,.2f}</b>", p_right_bold)])

    totals_t = Table(totals_rows, colWidths=[30*mm, 30*mm])
    totals_t.setStyle(TableStyle([
        ('ALIGN', (1, 0), (1, -1), 'RIGHT'),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 3),
        ('TOPPADDING', (0, 0), (-1, -1), 3),
        ('LINEABOVE', (0, 2), (-1, 2), 1, black),
    ]))

    footer_t = Table([
        [Paragraph(payment_info_text, p_small), totals_t]
    ], colWidths=[pw - 70*mm, 70*mm])
    footer_t.setStyle(TableStyle([
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('LEFTPADDING', (0, 0), (0, 0), 4),
        ('TOPPADDING', (0, 0), (-1, -1), 4),
    ]))
    elements.append(footer_t)
    elements.append(Spacer(1, 5*mm))

    # ============================================================
    # 6. COLLECTION LOCATIONS
    # ============================================================
    elements.append(Paragraph("<b>Collection Location:</b>", p_bold))
    elements.append(Spacer(1, 2*mm))

    sa_loc = (
        "<b>South Africa:</b><br/>"
        "Unit 19 Eastborough Business Park<br/>"
        "15 Olympia Street, Eastgate<br/>"
        "Johannesburg 2090, South Africa<br/>"
        "Email: info@servexholdings.com<br/>"
        "Contact no: +27 79 645 6281"
    )
    ke_loc = (
        "<b>Kenya:</b><br/>"
        "Godown 3, Libra House<br/>"
        "Mombasa Road, Nairobi, Kenya<br/>"
        "Email: info@servexholdings.com<br/>"
        "Contact no: +254 706 675 432"
    )

    loc_t = Table([
        [Paragraph(sa_loc, p_small), Paragraph(ke_loc, p_small)]
    ], colWidths=[pw/2, pw/2])
    loc_t.setStyle(TableStyle([
        ('BOX', (0, 0), (-1, -1), 0.5, colors.HexColor('#CCCCCC')),
        ('INNERGRID', (0, 0), (-1, -1), 0.3, colors.HexColor('#CCCCCC')),
        ('TOPPADDING', (0, 0), (-1, -1), 5),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
        ('LEFTPADDING', (0, 0), (-1, -1), 6),
    ]))
    elements.append(loc_t)
    elements.append(Spacer(1, 3*mm))

    # ============================================================
    # 7. OPERATING HOURS
    # ============================================================
    elements.append(Paragraph("<b>Operating hours:</b> Weekdays 9 - 5pm", p_center_bold))
    elements.append(Spacer(1, 4*mm))

    # ============================================================
    # 8. FOOTER DISCLAIMER
    # ============================================================
    elements.append(Paragraph(
        "Servex Holdings (Pty) Ltd accepts no liability for delays due to customs, weather, or government action. "
        "Liability is limited to the declared value of goods and excludes indirect or consequential losses. "
        "Shipping rates are based on the greater of volumetric or actual weight, multiplied by quantity (QTY). "
        "Uncollected items after seven (7) days incur storage fees of KSH 100/kg per day. "
        f"Payments in Kenyan Shillings (KSH) use an exchange rate of {kes_rate} KSH to 1 ZAR. "
        "For full terms, visit www.servexholdings.com.",
        p_disclaimer
    ))

    # --- Build ---
    doc.build(elements)
    buffer.seek(0)

    filename = f"Invoice-{invoice_number or invoice_id}.pdf"
    return StreamingResponse(
        buffer,
        media_type="application/pdf",
        headers={"Content-Disposition": f"attachment; filename={filename}"}
    )


async def generate_client_statement_pdf(client_id: str, tenant_id: str):
    """Generate a client statement PDF showing all invoices and payments (Session I M-03)"""
    
    client = await db.clients.find_one({"id": client_id, "tenant_id": tenant_id}, {"_id": 0})
    if not client:
        raise HTTPException(status_code=404, detail="Client not found")
    
    invoices = await db.invoices.find(
        {"client_id": client_id, "tenant_id": tenant_id},
        {"_id": 0}
    ).sort("created_at", -1).to_list(1000)
    
    payments = await db.payments.find(
        {"client_id": client_id, "tenant_id": tenant_id},
        {"_id": 0}
    ).sort("payment_date", -1).to_list(1000)
    
    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4, topMargin=30*mm, bottomMargin=20*mm, leftMargin=15*mm, rightMargin=15*mm)
    
    styles = getSampleStyleSheet()
    
    title_style = ParagraphStyle('StatementTitle', parent=styles['Heading1'], fontSize=18, textColor=colors.HexColor('#6B633C'), spaceAfter=6)
    subtitle_style = ParagraphStyle('Subtitle', parent=styles['Normal'], fontSize=10, textColor=colors.gray, spaceAfter=12)
    section_style = ParagraphStyle('Section', parent=styles['Heading2'], fontSize=13, textColor=colors.HexColor('#3C3F42'), spaceBefore=14, spaceAfter=6)
    normal_style = ParagraphStyle('NormalText', parent=styles['Normal'], fontSize=9, leading=12)
    
    elements = []
    
    # Header
    elements.append(Paragraph("SERVEX HOLDINGS", title_style))
    elements.append(Paragraph(f"Client Statement - {client.get('name', 'Unknown')}", subtitle_style))
    elements.append(Paragraph(f"Generated: {datetime.now().strftime('%d %B %Y')}", normal_style))
    elements.append(Spacer(1, 12))
    
    # Client details
    elements.append(Paragraph("Client Details", section_style))
    client_info = [
        ["Name:", client.get("name", "-"), "Company:", client.get("company_name", "-")],
        ["Phone:", client.get("phone", "-"), "Email:", client.get("email", "-")],
        ["Currency:", client.get("default_currency", "ZAR"), "Rate:", f"R {client.get('default_rate_value', 0)}/kg"],
    ]
    info_table = Table(client_info, colWidths=[60, 150, 60, 150])
    info_table.setStyle(TableStyle([
        ('FONTSIZE', (0, 0), (-1, -1), 8),
        ('TEXTCOLOR', (0, 0), (0, -1), colors.gray),
        ('TEXTCOLOR', (2, 0), (2, -1), colors.gray),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
    ]))
    elements.append(info_table)
    elements.append(Spacer(1, 12))
    
    # Invoices table
    elements.append(Paragraph("Invoices", section_style))
    
    total_invoiced = sum(inv.get("total", 0) for inv in invoices)
    total_paid = sum(inv.get("paid_amount", 0) for inv in invoices)
    total_outstanding = total_invoiced - total_paid
    
    if invoices:
        inv_data = [["Invoice #", "Date", "Status", "Total", "Paid", "Outstanding"]]
        for inv in invoices:
            outstanding = inv.get("total", 0) - inv.get("paid_amount", 0)
            inv_data.append([
                inv.get("invoice_number", "-"),
                inv.get("issue_date", "-")[:10] if inv.get("issue_date") else "-",
                inv.get("status", "-").upper(),
                format_currency(inv.get("total", 0)),
                format_currency(inv.get("paid_amount", 0)),
                format_currency(outstanding),
            ])
        
        # Summary row
        inv_data.append(["", "", "TOTAL", format_currency(total_invoiced), format_currency(total_paid), format_currency(total_outstanding)])
        
        inv_table = Table(inv_data, colWidths=[80, 65, 55, 75, 75, 75])
        inv_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#6B633C')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
            ('FONTSIZE', (0, 0), (-1, -1), 8),
            ('ALIGN', (3, 0), (-1, -1), 'RIGHT'),
            ('GRID', (0, 0), (-1, -2), 0.5, colors.lightgrey),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
            ('TOPPADDING', (0, 0), (-1, -1), 4),
            ('BACKGROUND', (0, -1), (-1, -1), colors.HexColor('#f5f5f0')),
            ('FONTNAME', (0, -1), (-1, -1), 'Helvetica-Bold'),
            ('LINEABOVE', (0, -1), (-1, -1), 1, colors.HexColor('#6B633C')),
        ]))
        elements.append(inv_table)
    else:
        elements.append(Paragraph("No invoices found.", normal_style))
    
    elements.append(Spacer(1, 12))
    
    # Payments table
    elements.append(Paragraph("Payments", section_style))
    if payments:
        pay_data = [["Date", "Method", "Reference", "Invoice", "Amount"]]
        for pay in payments:
            # Find invoice number
            inv_num = "-"
            if pay.get("invoice_id"):
                inv = next((i for i in invoices if i.get("id") == pay["invoice_id"]), None)
                if inv:
                    inv_num = inv.get("invoice_number", "-")
            pay_data.append([
                pay.get("payment_date", "-")[:10] if pay.get("payment_date") else "-",
                (pay.get("payment_method", "-") or "-").replace("_", " ").title(),
                pay.get("reference", "-") or "-",
                inv_num,
                format_currency(pay.get("amount", 0)),
            ])
        
        pay_table = Table(pay_data, colWidths=[70, 85, 85, 85, 75])
        pay_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#6B633C')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
            ('FONTSIZE', (0, 0), (-1, -1), 8),
            ('ALIGN', (4, 0), (4, -1), 'RIGHT'),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.lightgrey),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
            ('TOPPADDING', (0, 0), (-1, -1), 4),
        ]))
        elements.append(pay_table)
    else:
        elements.append(Paragraph("No payments recorded.", normal_style))
    
    elements.append(Spacer(1, 20))
    
    # Summary
    elements.append(Paragraph("Account Summary", section_style))
    summary_data = [
        ["Total Invoiced:", format_currency(total_invoiced)],
        ["Total Paid:", format_currency(total_paid)],
        ["Outstanding Balance:", format_currency(total_outstanding)],
    ]
    summary_table = Table(summary_data, colWidths=[120, 100])
    summary_table.setStyle(TableStyle([
        ('FONTSIZE', (0, 0), (-1, -1), 10),
        ('TEXTCOLOR', (0, 0), (0, -1), colors.gray),
        ('ALIGN', (1, 0), (1, -1), 'RIGHT'),
        ('FONTNAME', (0, -1), (-1, -1), 'Helvetica-Bold'),
        ('TEXTCOLOR', (1, -1), (1, -1), colors.HexColor('#DC2626') if total_outstanding > 0 else colors.HexColor('#059669')),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
    ]))
    elements.append(summary_table)
    
    doc.build(elements)
    buffer.seek(0)
    
    filename = f"Statement-{client.get('name', 'Client').replace(' ', '_')}.pdf"
    return StreamingResponse(
        buffer,
        media_type="application/pdf",
        headers={"Content-Disposition": f"attachment; filename={filename}"}
    )



# ============ LABELS PDF GENERATION ============

async def generate_labels_pdf(shipment_ids: list, tenant_id: str):
    """
    Generate A6 parcel labels PDF - one label per page.
    Each label contains 14 fields + QR code + barcode.
    """
    from reportlab.lib.pagesizes import A6
    from reportlab.lib.units import mm
    from reportlab.pdfgen import canvas
    from reportlab.lib import colors
    from io import BytesIO
    import qrcode

    shipments = await db.shipments.find({
        "id": {"$in": shipment_ids},
        "tenant_id": tenant_id
    }, {"_id": 0}).to_list(None)

    if not shipments:
        raise HTTPException(404, "No shipments found")

    client_ids = list(set(s.get("client_id") for s in shipments if s.get("client_id")))
    clients = await db.clients.find({"id": {"$in": client_ids}}, {"_id": 0, "id": 1, "name": 1}).to_list(None)
    client_map = {c["id"]: c["name"] for c in clients}

    for s in shipments:
        s["client_name"] = client_map.get(s.get("client_id"), "Unknown")

    # Get trip info for trip numbers
    trip_ids = list(set(s.get("trip_id") for s in shipments if s.get("trip_id")))
    trips = await db.trips.find({"id": {"$in": trip_ids}}, {"_id": 0, "id": 1, "trip_number": 1}).to_list(None)
    trip_map = {t["id"]: t.get("trip_number", "N/A") for t in trips}

    # Get warehouse names
    warehouse_ids = list(set(s.get("warehouse_id") for s in shipments if s.get("warehouse_id")))
    warehouses = await db.warehouses.find({"id": {"$in": warehouse_ids}}, {"_id": 0, "id": 1, "name": 1}).to_list(None)
    warehouse_map = {w["id"]: w.get("name", "") for w in warehouses}

    buffer = BytesIO()
    c = canvas.Canvas(buffer, pagesize=A6)
    width, height = A6

    for shipment in shipments:
        trip_number = trip_map.get(shipment.get("trip_id"), "N/A")
        warehouse_name = warehouse_map.get(shipment.get("warehouse_id"), "")

        # Generate QR code
        qr = qrcode.QRCode(version=1, box_size=3, border=1)
        qr.add_data(shipment.get("barcode", shipment.get("id", "")))
        qr.make(fit=True)
        qr_img = qr.make_image(fill_color="black", back_color="white")

        qr_buffer = BytesIO()
        qr_img.save(qr_buffer, format='PNG')
        qr_buffer.seek(0)

        from reportlab.lib.utils import ImageReader
        qr_reader = ImageReader(qr_buffer)

        # Draw border
        c.setStrokeColor(colors.black)
        c.setLineWidth(1)
        c.rect(5*mm, 5*mm, width - 10*mm, height - 10*mm)

        # Header
        c.setFont("Helvetica-Bold", 14)
        c.drawCentredString(width / 2, height - 15*mm, "SERVEX HOLDINGS")
        c.setFont("Helvetica", 8)
        c.drawCentredString(width / 2, height - 20*mm, "Logistics Services to Kenya and South Africa")

        # Line separator
        c.line(10*mm, height - 25*mm, width - 10*mm, height - 25*mm)

        # 14 fields in two columns
        y_pos = height - 35*mm
        line_height = 6*mm
        left_x = 10*mm
        right_x = width / 2 + 5*mm

        # Calculate CBM
        l_cm = shipment.get("length_cm", 0) or 0
        w_cm = shipment.get("width_cm", 0) or 0
        h_cm = shipment.get("height_cm", 0) or 0
        cbm = round(shipment.get("total_cbm", 0) or (l_cm * w_cm * h_cm / 1000000), 4)
        shipping_weight = max(shipment.get("total_weight", 0) or 0, (l_cm * w_cm * h_cm) / 5000)

        # Left column (7 fields)
        fields_left = [
            ("Parcel ID:", str(shipment.get("id", ""))[:12]),
            ("Client:", str(shipment.get("client_name", ""))[:20]),
            ("Recipient:", str(shipment.get("recipient", ""))[:20]),
            ("Destination:", str(shipment.get("destination", ""))),
            ("Weight:", f"{shipment.get('total_weight', 0) or 0} kg"),
            ("Pieces:", str(shipment.get("total_pieces", 1))),
            ("Trip:", trip_number)
        ]

        for label, value in fields_left:
            c.setFont("Helvetica-Bold", 7)
            c.drawString(left_x, y_pos, label)
            c.setFont("Helvetica", 7)
            c.drawString(left_x + 20*mm, y_pos, str(value))
            y_pos -= line_height

        # Right column (7 fields)
        y_pos = height - 35*mm
        fields_right = [
            ("Invoice #:", str(shipment.get("invoice_number", "N/A"))),
            ("Status:", str(shipment.get("status", "")).upper()),
            ("CBM:", f"{cbm:.4f}"),
            ("LxWxH:", f"{l_cm}x{w_cm}x{h_cm}"),
            ("Ship Wt:", f"{shipping_weight:.1f} kg"),
            ("Warehouse:", warehouse_name),
            ("Date:", str(shipment.get("created_at", ""))[:10])
        ]

        for label, value in fields_right:
            c.setFont("Helvetica-Bold", 7)
            c.drawString(right_x, y_pos, label)
            c.setFont("Helvetica", 7)
            c.drawString(right_x + 18*mm, y_pos, str(value))
            y_pos -= line_height

        # QR code at bottom
        c.drawImage(qr_reader, 10*mm, 10*mm, 30*mm, 30*mm, preserveAspectRatio=True)

        # Barcode text below QR
        c.setFont("Helvetica-Bold", 10)
        c.drawString(45*mm, 15*mm, shipment.get("barcode", shipment.get("id", "")[:16]))

        c.showPage()

    c.save()
    buffer.seek(0)
    return buffer


# ============ INVOICE PDF TYPE 2 ============

async def generate_invoice_pdf_type2(invoice_id: str, tenant_id: str):
    """
    TYPE 2 Invoice PDF - Servex branded template with red accents.
    """
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.units import mm
    from reportlab.lib import colors
    from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, Image as RLImage
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.enums import TA_LEFT, TA_RIGHT, TA_CENTER
    from io import BytesIO
    import os

    invoice = await db.invoices.find_one({"id": invoice_id, "tenant_id": tenant_id}, {"_id": 0})
    if not invoice:
        raise HTTPException(404, "Invoice not found")

    client = await db.clients.find_one({"id": invoice["client_id"], "tenant_id": tenant_id}, {"_id": 0})
    if not client:
        raise HTTPException(404, "Client not found")

    line_items = await db.invoice_line_items.find(
        {"invoice_id": invoice_id},
        {"_id": 0}
    ).to_list(None)

    # Get banking details
    settings = await db.settings.find_one({"tenant_id": tenant_id}, {"_id": 0})
    banking = []
    if settings and settings.get("banking_details"):
        banking = settings["banking_details"]

    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4, topMargin=15*mm, bottomMargin=15*mm, leftMargin=15*mm, rightMargin=15*mm)
    story = []
    styles = getSampleStyleSheet()
    page_width = A4[0] - 30*mm

    servex_red = colors.HexColor('#8B0000')

    title_style = ParagraphStyle('ServexTitle', parent=styles['Heading1'], fontSize=20, textColor=servex_red, alignment=TA_CENTER, spaceAfter=10)
    red_style = ParagraphStyle('RedText', parent=styles['Normal'], fontSize=10, textColor=servex_red, alignment=TA_RIGHT, fontName='Helvetica-Bold')
    small_style = ParagraphStyle('SmallText', parent=styles['Normal'], fontSize=8, leading=10)
    disclaimer_style = ParagraphStyle('Disclaimer', parent=styles['Normal'], fontSize=7, textColor=colors.grey, alignment=TA_CENTER)

    # Header: Logo (left) and Tagline (right)
    logo_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "servex_logo.png")
    if os.path.exists(logo_path):
        try:
            logo = RLImage(logo_path, width=50*mm, height=50*mm)
        except Exception:
            logo = Paragraph("<b>SERVEX HOLDINGS</b>", title_style)
    else:
        logo = Paragraph("<b>SERVEX HOLDINGS</b>", title_style)

    tagline = Paragraph("Logistics Services to Kenya<br/>and South Africa", red_style)

    header_table = Table([[logo, tagline]], colWidths=[page_width * 0.55, page_width * 0.45])
    header_table.setStyle(TableStyle([
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('ALIGN', (0, 0), (0, 0), 'LEFT'),
        ('ALIGN', (1, 0), (1, 0), 'RIGHT'),
    ]))
    story.append(header_table)
    story.append(Spacer(1, 5*mm))

    # Invoice title
    story.append(Paragraph(f"INVOICE {invoice.get('invoice_number', 'N/A')}", title_style))
    story.append(Spacer(1, 5*mm))

    # Header grid (3 columns)
    company_lines = [
        "<b>Servex Holdings (PTY) Ltd</b>",
        "Email: info@servexholdings.info",
        "Phone: +27 11 123 4567",
    ]
    client_lines = [
        "<b>Bill To:</b>",
        client.get("name", ""),
        client.get("company_name", "") or "",
        client.get("email", "") or "",
        f"VAT: {client.get('vat_number', 'N/A')}",
    ]
    invoice_lines = [
        f"<b>Invoice #:</b> {invoice.get('invoice_number', '')}",
        f"<b>Date:</b> {str(invoice.get('issue_date', invoice.get('created_at', '')))[:10]}",
        f"<b>Due Date:</b> {str(invoice.get('due_date', ''))[:10]}",
        f"<b>Status:</b> {invoice.get('status', 'draft').upper()}",
    ]

    max_rows = max(len(company_lines), len(client_lines), len(invoice_lines))
    grid_data = [
        [
            Paragraph("<b>From:</b>", styles['Normal']),
            Paragraph("<b>To:</b>", styles['Normal']),
            Paragraph("<b>Invoice Details:</b>", styles['Normal'])
        ]
    ]

    for i in range(max_rows):
        row = [
            Paragraph(company_lines[i] if i < len(company_lines) else "", small_style),
            Paragraph(client_lines[i] if i < len(client_lines) else "", small_style),
            Paragraph(invoice_lines[i] if i < len(invoice_lines) else "", small_style),
        ]
        grid_data.append(row)

    col_w = page_width / 3
    grid_table = Table(grid_data, colWidths=[col_w, col_w, col_w])
    grid_table.setStyle(TableStyle([
        ('GRID', (0, 0), (-1, -1), 1, colors.black),
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#F0F0F0')),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 8),
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('LEFTPADDING', (0, 0), (-1, -1), 5),
        ('RIGHTPADDING', (0, 0), (-1, -1), 5),
        ('TOPPADDING', (0, 0), (-1, -1), 3),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 3),
    ]))
    story.append(grid_table)
    story.append(Spacer(1, 8*mm))

    # Line items table
    items_header = ["#", "Description", "L", "W", "H", "Vol", "Act.Wt", "Ship.Wt", "Rate", "Amount"]
    items_data = [[Paragraph(f"<b>{h}</b>", small_style) for h in items_header]]

    for idx, item in enumerate(line_items, start=1):
        length = item.get("length_cm", 0) or 0
        width_val = item.get("width_cm", 0) or 0
        height_val = item.get("height_cm", 0) or 0
        vol_weight = round((length * width_val * height_val) / 5000, 1) if (length and width_val and height_val) else 0
        actual_weight = item.get("weight", 0) or 0
        ship_weight = max(actual_weight, vol_weight)

        items_data.append([
            str(idx),
            Paragraph(str(item.get("description", ""))[:35], small_style),
            str(length),
            str(width_val),
            str(height_val),
            f"{vol_weight:.1f}",
            f"{actual_weight:.1f}",
            f"{ship_weight:.1f}",
            f"{item.get('rate', 0):.2f}",
            f"R {item.get('amount', 0):.2f}",
        ])

    subtotal = invoice.get('subtotal', invoice.get('total', 0))
    vat_rate = 15
    vat_amount = round(subtotal * vat_rate / 100, 2)
    total = invoice.get('total', subtotal + vat_amount)

    items_data.append(["", "", "", "", "", "", "", "", Paragraph("<b>Subtotal:</b>", small_style), Paragraph(f"<b>R {subtotal:.2f}</b>", small_style)])
    items_data.append(["", "", "", "", "", "", "", "", Paragraph(f"<b>VAT ({vat_rate}%):</b>", small_style), Paragraph(f"<b>R {vat_amount:.2f}</b>", small_style)])
    items_data.append(["", "", "", "", "", "", "", "", Paragraph("<b>TOTAL:</b>", small_style), Paragraph(f"<b>R {total:.2f}</b>", small_style)])

    item_col_widths = [8*mm, page_width - 133*mm, 12*mm, 12*mm, 12*mm, 14*mm, 16*mm, 16*mm, 18*mm, 25*mm]
    items_table = Table(items_data, colWidths=item_col_widths)
    items_table.setStyle(TableStyle([
        ('GRID', (0, 0), (-1, -4), 0.5, colors.grey),
        ('LINEABOVE', (0, -3), (-1, -3), 1, colors.black),
        ('BACKGROUND', (0, 0), (-1, 0), servex_red),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('FONTSIZE', (0, 0), (-1, -1), 7),
        ('ALIGN', (2, 0), (-1, -1), 'CENTER'),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
    ]))
    story.append(items_table)
    story.append(Spacer(1, 8*mm))

    # Payment details
    payment_lines = ["<b>Payment Details:</b>"]
    if banking:
        for acc in banking:
            if isinstance(acc, dict):
                payment_lines.append(f"<b>{acc.get('currency', '')}:</b> {acc.get('bank_name', '')} | Acc: {acc.get('account_number', '')} | Branch: {acc.get('branch_code', '')} | Swift: {acc.get('swift_code', '')}")
    else:
        payment_lines.append("Bank: First National Bank | Acc: Servex Holdings (PTY) Ltd | Acc #: 62 1234 5678 9 | Branch: 250 655 | Swift: FIRNZAJJ")
    payment_lines.append(f"Reference: {invoice.get('invoice_number', '')}")

    payment_text = "<br/>".join(payment_lines)
    story.append(Paragraph(payment_text, small_style))
    story.append(Spacer(1, 5*mm))

    # Collection locations
    collection_text = """<b>Collection Locations:</b><br/>
    <b>Johannesburg:</b> 123 Main Road, Johannesburg, South Africa | Tel: +27 11 123 4567<br/>
    <b>Nairobi:</b> 456 Kenyatta Avenue, Nairobi, Kenya | Tel: +254 20 123 4567"""
    story.append(Paragraph(collection_text, small_style))
    story.append(Spacer(1, 5*mm))

    # Disclaimer
    story.append(Paragraph("All goods remain the property of Servex Holdings until payment is received in full. Terms and conditions apply.", disclaimer_style))

    # Red bottom bar
    story.append(Spacer(1, 5*mm))
    bottom_bar = Table([[""]], colWidths=[page_width])
    bottom_bar.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, -1), servex_red),
        ('TOPPADDING', (0, 0), (-1, -1), 2*mm),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 2*mm),
    ]))
    story.append(bottom_bar)

    doc.build(story)
    buffer.seek(0)
    return buffer
