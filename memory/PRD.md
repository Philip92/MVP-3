# Servex Holdings - Logistics Management Platform

## Original Problem Statement
Bug fixes on existing Servex Holdings logistics management app:

**S1 - Sidebar + Logo Flicker on Navigation**  
**S2 - Finalized Invoices Not Locked in UI**  
**S3 - Add Parcels Search Not Returning Results**

## Architecture
- **Frontend**: React.js with React Router v6, Tailwind CSS, shadcn/ui components
- **Backend**: FastAPI (Python), multi-tenant architecture
- **Database**: MongoDB
- **Auth**: JWT-based cookie auth

### 2026-02-23 - Session Brief v2 (S4-S10)

#### S4: Status Cascade Fix
- **trip_routes.py**: When trip status changes to 'in_transit', bulk-updates all `loaded` parcels for that trip to `in_transit` status (before unassigning staged parcels)
- **invoice_routes.py, finance_routes.py**: Changed all `to_list(500)` → `to_list(2000)` to support larger datasets

#### S5: Save Draft Feedback
- **InvoiceEditor.jsx**: Toast now shows `Draft saved at HH:MM:SS` at `top-center`, duration 4000ms
- **InvoiceEditor.jsx**: Added `flashedInvoiceId` state - invoice card gets CSS class `invoice-saved-flash` for 2s green border pulse
- **App.css**: Added `@keyframes saveFlash` + `.invoice-saved-flash` CSS class

#### S6: Invoice List - Full Height + Search + Count
- **InvoiceEditor.jsx**: Added `invoiceListSearch` state; search input filters by invoice number OR client name
- **InvoiceEditor.jsx**: Shows `Showing X of Y invoices` count above the list
- **InvoiceEditor.jsx**: ScrollArea changed from `h-[500px]` to `h-[calc(100vh-280px)]`
- **InvoiceEditor.jsx**: Compact card layout (40px height), smaller filter dropdowns, smaller New button

#### S7: Loading Page Layout
- **LoadingStaging.jsx**: Helper text below barcode input hidden (`sr-only`)
- **LoadingStaging.jsx**: Colored stat bubble cards replaced with minimal inline text stats

#### S8: Scrollbar Styling
- **App.css**: `::-webkit-scrollbar { width: 8px }`, thumb `#C8BFA8` border-radius 4px, hover `#9E9478`

#### S9: Currency Toggle Exchange Rate Display
- **InvoiceEditor.jsx**: Added `(1 ZAR = X KES)` text next to ZAR/KES toggle in invoice form header

#### S10: Clients - Row Numbers + Company Name
- **schemas.py**: Added `company_name: Optional[str] = None` to `ClientBase` and `ClientUpdate`
- **Clients.jsx**: Row numbers (#) column added to table; subtitle shows `N of M clients` count
- **Clients.jsx**: Company Name optional field added to Add/Edit Client form (shown under client name in table if present)

### 2026-02-23 - Bug Fixes (S1, S2, S3)

#### S1: Sidebar Flicker Fix
- **App.js**: Restructured from per-route `<ProtectedRoute>` wrapping to single nested layout route: `<Route element={<ProtectedRoute><Layout /></ProtectedRoute>}>`
- **Layout.jsx**: Replaced `{children}` with `<Outlet />` from react-router-dom; Layout function no longer accepts children prop
- **All 13 page components**: Removed `<Layout>` wrapper (replaced with React Fragment `<>`) and removed `import { Layout }` statement

#### S2: Invoice Lock Fix
- **InvoiceEditor.jsx**: Added `isLocked = !!(invoiceData && invoiceData.status !== 'draft')` computed value
- **InvoiceEditor.jsx**: Added amber lock banner with "Request Edit Access" button when `isLocked`
- **InvoiceEditor.jsx**: All form fields now use `disabled={isLocked}` instead of `disabled={invoiceData?.status === 'paid'}`
- **InvoiceEditor.jsx**: Save Draft and Finalize Invoice buttons are HIDDEN (not just disabled) when `isLocked`
- **InvoiceEditor.jsx**: Download PDF and Record Payment remain visible for locked invoices

#### S3: Parcel Search Fix
- **backend/routes/shipment_routes.py**: Added batch client_name enrichment in `list_shipments()` - fetches all unique client IDs and adds `client_name` field to each shipment in the response
- **InvoiceEditor.jsx**: Null-safety guard `(p.client_name || '')` already present in search filter

## Key Pages/Files
- `frontend/src/App.js` - Route structure (nested layout)
- `frontend/src/components/Layout.jsx` - Sidebar/header with Outlet
- `frontend/src/components/InvoiceEditor.jsx` - Invoice form with lock logic
- `frontend/src/components/ProtectedRoute.jsx` - Auth guard
- `backend/routes/invoice_routes.py` - Invoice CRUD, finalize, payments
- `backend/routes/shipment_routes.py` - Shipments with client_name enrichment
- `frontend/src/pages/` - 13 page components (Dashboard, Clients, Finance, etc.)

## Core Features
- Multi-tenant logistics management
- Parcel intake, warehouse management, trip planning
- Invoice creation and management with lock state
- Role-based access control (owner/manager/warehouse/finance/driver)
- PDF invoice generation
- WhatsApp payment notification logging
- Fleet and team management
- Settings with CSV import/export

## Prioritized Backlog
- P0: (All fixed in this session)
- P1: Enhanced parcel search with destination filter support in backend
- P2: Unlock request workflow (backend endpoint + notification)
- P2: DialogContent aria-describedby accessibility improvements

## Test Accounts
- admin@servex.com / Servex2026! (owner role)

### 2026-02-23 - N-01, N-02, N-03

#### N-01: Dashboard KPI Cards
- **fleet_routes.py**: Enhanced `get_dashboard_stats` with `period` param (mtd/last_month/3m/all), financial stats (revenue_mtd, revenue_last_month, revenue_change_pct, accounts_receivable, overdue_amount, collection_rate), ops stats (in_transit, awaiting_collection, uninvoiced_parcels), 8-week revenue sparkline, truck_utilisation
- **Dashboard.jsx**: Complete redesign — 3 KPI rows (Revenue, Operations, Summary), period toggle (MTD/Last Mo./3M/All), ZAR/KES toggle, Recharts sparkline (stroke #2D6A4F), truck utilisation progress bars, recent shipments table, quick actions

#### N-02: Trip Worksheet Remodel
- **finance_routes.py**: `get_trip_worksheet` now returns per-invoice shipping_weight, cbm, effective_rate, paid_kes; fetches line items for dimension data; summary includes used_kg, remaining_kg, used_cbm, remaining_cbm, revenue_per_kg, revenue_per_ton
- **schemas.py**: Trip schema now has `capacity_kg` and `capacity_cbm` optional fields
- **invoice_routes.py**: Added `PATCH /invoices/{id}` endpoint for comment field (safe-field-only patch)
- **Finance.jsx**: Worksheets tab redesigned with 2 rows of stat tiles (capacity + revenue), full table (Sender|INV No|Recipient|KG|Ship KG|CBM|Rate|ZAR|KSH|Comment|Status|Outstanding), totals footer row, inline editable comment cells (InlineComment component auto-saves on blur)

#### N-03: Client Statements Matrix
- **finance_routes.py**: `get_client_statements` now returns `trip_amounts[trip_num] = {invoiced, outstanding, status}`, adds `total_invoiced` per client, 20 trip columns, `sort_by` and `show_paid` query params
- **Finance.jsx**: Statements tab redesigned as Excel-style frozen-column matrix table with per-trip INV/OUT sub-columns, sort dropdown, search, show-paid toggle, row expand for individual invoices

### 2026-02-23 - D-07: Comprehensive Seed Data & System Verification

#### Database Seeding
- **seed_data.py**: Created comprehensive seed script that generates:
  - 50 clients with realistic South African and Kenyan names, companies, contact info
  - 8 trips with various statuses (planning, loading, in_transit, delivered, closed)
  - 332 shipments distributed across trips with proper status cascading
  - 92 invoices with draft/sent/paid/overdue statuses
  - 282 invoice line items with weight, dimensions, rates
  - 38 payments for paid invoices
  - 50 additional warehouse parcels (unassigned to trips)

#### System Verification Complete
All major features verified working with seeded data:

**Dashboard KPIs:**
- ✅ Revenue (Period): R 57,665 with sparkline
- ✅ Accounts Receivable: R 164,938
- ✅ Overdue Amount: R 52,332 (red border when > 0)
- ✅ Collection Rate: 0%
- ✅ Operations metrics: Warehouse (138), In Transit (35), Awaiting Collection (50), Uninvoiced (173)
- ✅ Summary: Clients (50), Trips (8), Shipments (332), Delivered (79)
- ✅ Period toggle (MTD/Last Mo./3M/All) working
- ✅ ZAR/KES currency toggle working

**Finance Page:**
- ✅ Client Statements matrix with frozen columns, color-coded cells
- ✅ Trip Worksheets with capacity stats (KG/CBM), revenue stats, invoice table
- ✅ Overdue tab showing 4 overdue invoices
- ✅ Inline editable comments working
- ✅ Currency toggle with exchange rate display

**Loading/Unloading Page:**
- ✅ Trip selector with route display
- ✅ Progress bar (60% for trip SH-2025-006)
- ✅ Split-screen tables (Ready to Load / Loaded)
- ✅ Parcel sequencing display ("1 of 3")
- ✅ Invoice status badges
- ✅ Depart Trip button with loaded count

## Prioritized Backlog

### P0 (Critical) - COMPLETED
- ✅ D-07 Seed data and verification complete

### P1 (High)
- Admin invoice unlock verification (endpoint exists, needs UI testing with locked invoice)

### P2 (Medium)
- Remove unused `generate_trip_invoices` function from `trip_routes.py`
- Address `ClientStatus.merged` cleanup
- Fix shipping weight logic in `addSelectedParcels()`
- Implement "select-all across pages" in warehouse view
- Break down `Finance.jsx` into smaller components (large file, prone to errors)

## Test Accounts
- admin@servex.com / Servex2026! (owner role)

## Key API Endpoints
- `GET /api/dashboard/stats?period={mtd|last_month|3m|all}` - Dashboard KPIs
- `GET /api/finance/client-statements?sort_by={}&show_paid={}` - Client statements matrix
- `GET /api/finance/trip-worksheet/{trip_id}` - Trip worksheet data
- `GET /api/finance/overdue` - Overdue invoices list
- `PATCH /api/invoices/{id}` - Update invoice comment
- `POST /api/invoices/{id}/unlock-invoice-admin` - Admin unlock (exists, needs verification)
