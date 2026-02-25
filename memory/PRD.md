# Servex Holdings - Logistics Management Platform PRD

## Original Problem Statement
Implement 4 session documents (F1-Labels PDF, F2-Invoice PDF Type2, F3-Warehouse Excel Export, J1-Configurable Invoice Numbering), connect trip tiles to truck fleet data for KG/CBM capacity, add CSV upload format instructions to Settings, and ensure truck capacity fields exist in Fleet.

## Architecture
- **Frontend**: React.js + TailwindCSS + ShadCN UI
- **Backend**: FastAPI (Python) 
- **Database**: MongoDB
- **PDF Generation**: ReportLab + qrcode
- **Excel Export**: openpyxl

## What's Been Implemented (Feb 25, 2026)

### Session F1 - Labels PDF
- Backend: `generate_labels_pdf()` in pdf_service.py - A6 labels with QR codes, 14 fields per label
- Endpoints: `GET /trips/{id}/labels/pdf`, `POST /warehouse/labels/pdf`
- Frontend: Labels download button in TripDetail > Documents tab, Warehouse bulk print downloads actual PDF

### Session F2 - Invoice PDF Type 2
- Backend: `generate_invoice_pdf_type2()` in pdf_service.py - Servex branded template with red accents, logo
- Endpoint: `GET /invoices/{id}/pdf/type2`
- Frontend: PDF download dropdown in InvoiceEditor and Finance page with Type 1/Type 2 options

### Session F3 - Warehouse Excel Export
- Backend: `GET /warehouse/export/excel` - 24-column Digital Manifest format with filters
- Frontend: Export Excel button added to Warehouse header toolbar

### Session J1 - Invoice Number Format Builder
- Backend: InvoiceNumberService with configurable segments (STATIC, YEAR, MONTH, TRIP_SEQ, GLOBAL_SEQ)
- Endpoints: GET/PUT `/settings/invoice-number-format`, POST preview
- Frontend: Visual builder in Settings > Invoice Numbering tab with live preview

### Trip Capacity from Fleet
- trips-with-stats endpoint now pulls max_weight_kg and max_volume_cbm from vehicle data
- Trips page table shows Capacity and CBM columns
- Trip cards show capacity_kg and total_cbm in stats grid

### CSV Upload Instructions
- Settings > Data tab: Both Client and Parcel import tiles show CSV column order info in colored info boxes before clicking upload

## User Personas
- Admin/Owner: Full access to all features
- Operations Staff: Warehouse management, trip management
- Finance: Invoice creation, PDF generation, statements

## Prioritized Backlog
- P0: All 4 sessions implemented ✅
- P1: Trip capacity from fleet ✅, CSV upload info ✅
- P2: Invoice number format integration with actual invoice creation flow
- P2: Labels print directly to printer (PrintNode integration)
- P3: Statement PDF Type 2

## Next Tasks
1. Integrate invoice number format with actual invoice creation (use configurable format when generating invoice numbers)
2. Add bulk labels generation from warehouse with print preview
3. Add more export formats (CSV alongside Excel)
