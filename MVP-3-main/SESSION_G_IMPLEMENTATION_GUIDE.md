# SESSION G: Collection Workflow Implementation Guide

## Overview
Implement collection warnings and collection mode for handling unpaid parcel pickups.

---

## 🎯 Requirements (38 credits total)

### 1. **Unpaid Collection Warnings** (15 credits)
- Display warning when client tries to collect unpaid parcels
- Show total unpaid amount + list of uninvoiced/unpaid parcels
- Block collection until payment or admin override

### 2. **Collection Mode on Warehouse Page** (18 credits)
- Toggle between "Normal Mode" and "Collection Mode"
- Collection Mode shows:
  - Client search/scanner
  - Outstanding balance prominently
  - List of parcels ready for collection
  - "Mark as Collected" batch action
  - Admin override for unpaid collections

### 3. **Admin Notifications** (5 credits)
- Notify admin when unpaid collection attempted
- Notify admin when override used
- Log all collection events

---

## 📁 Files to Modify

### Backend:
1. `/app/backend/routes/shipment_routes.py`
   - Add `GET /shipments/ready-for-collection?client_id={id}` endpoint
   - Add `POST /shipments/mark-collected` batch endpoint
   - Add unpaid balance check logic

2. `/app/backend/routes/client_routes.py`
   - Add `GET /clients/{id}/outstanding-balance` endpoint
   - Returns: total unpaid invoices + uninvoiced parcels value

3. `/app/backend/routes/notification_routes.py`
   - Add `POST /notifications/collection-warning` endpoint
   - Store notification in MongoDB

### Frontend:
1. `/app/frontend/src/pages/Warehouse.jsx`
   - Add "Collection Mode" toggle button in header
   - Add Collection Mode UI (separate from normal warehouse view)
   - Add client scanner/search in Collection Mode
   - Add outstanding balance display
   - Add batch collection confirmation dialog

2. `/app/frontend/src/components/CollectionModePanel.jsx` (NEW)
   - Dedicated component for Collection Mode interface
   - Client lookup
   - Parcel list with checkboxes
   - Payment status indicator
   - Admin override button (role-based)

---

## 🛠 Implementation Steps

### **STEP 1: Backend - Outstanding Balance Endpoint**
```python
# In /app/backend/routes/client_routes.py

@router.get("/clients/{client_id}/outstanding-balance")
async def get_client_outstanding_balance(
    client_id: str,
    tenant_id: str = Depends(get_tenant_id)
):
    """Calculate total outstanding balance for a client"""
    
    # Get unpaid/partial invoices
    invoices = await db.invoices.find({
        "tenant_id": tenant_id,
        "client_id": client_id,
        "status": {"$in": ["draft", "sent", "overdue", "partial"]}
    }).to_list(1000)
    
    invoice_outstanding = sum(
        inv.get("total", 0) - inv.get("paid_amount", 0)
        for inv in invoices
    )
    
    # Get uninvoiced parcels
    uninvoiced = await db.shipments.find({
        "tenant_id": tenant_id,
        "client_id": client_id,
        "$or": [
            {"invoice_id": None},
            {"invoice_id": {"$exists": False}}
        ],
        "status": {"$in": ["warehouse", "arrived"]}
    }).to_list(1000)
    
    # Estimate uninvoiced value (use client's average rate if available)
    # For now, use weight * default rate
    uninvoiced_estimated = len(uninvoiced) * 500  # R500 average per parcel
    
    return {
        "client_id": client_id,
        "invoice_outstanding": round(invoice_outstanding, 2),
        "uninvoiced_count": len(uninvoiced),
        "uninvoiced_estimated": uninvoiced_estimated,
        "total_outstanding": round(invoice_outstanding + uninvoiced_estimated, 2),
        "invoices": [
            {
                "id": inv["id"],
                "invoice_number": inv.get("invoice_number"),
                "total": inv.get("total"),
                "paid_amount": inv.get("paid_amount", 0),
                "outstanding": inv.get("total", 0) - inv.get("paid_amount", 0),
                "due_date": inv.get("due_date")
            }
            for inv in invoices
        ],
        "uninvoiced_parcels": [
            {
                "id": p["id"],
                "barcode": p.get("barcode"),
                "description": p.get("description")
            }
            for p in uninvoiced[:10]  # First 10 only
        ]
    }
```

### **STEP 2: Backend - Ready for Collection Endpoint**
```python
# In /app/backend/routes/shipment_routes.py

@router.get("/shipments/ready-for-collection")
async def get_ready_for_collection(
    client_id: str,
    tenant_id: str = Depends(get_tenant_id)
):
    """Get all parcels ready for collection by client"""
    parcels = await db.shipments.find({
        "tenant_id": tenant_id,
        "client_id": client_id,
        "status": "arrived"  # Status indicating parcel is at destination warehouse
    }).to_list(500)
    
    return {
        "count": len(parcels),
        "parcels": [
            {
                "id": p["id"],
                "barcode": p.get("barcode"),
                "description": p.get("description"),
                "weight": p.get("weight"),
                "arrived_at": p.get("updated_at"),
                "invoice_id": p.get("invoice_id"),
                "is_paid": p.get("is_paid", False)
            }
            for p in parcels
        ]
    }
```

### **STEP 3: Frontend - Collection Mode Toggle**
```jsx
// In /app/frontend/src/pages/Warehouse.jsx

const [collectionMode, setCollectionMode] = useState(false);

// Add to header section
<div className="flex gap-2">
  <Button
    variant={collectionMode ? "default" : "outline"}
    onClick={() => setCollectionMode(!collectionMode)}
    className={collectionMode ? "bg-green-600 hover:bg-green-700" : ""}
  >
    <UserCheck className="h-4 w-4 mr-2" />
    {collectionMode ? "Collection Mode ON" : "Enable Collection Mode"}
  </Button>
</div>

// Conditional rendering
{collectionMode ? (
  <CollectionModePanel />
) : (
  // ... existing warehouse table ...
)}
```

### **STEP 4: Frontend - Collection Mode Component**
```jsx
// Create new file: /app/frontend/src/components/CollectionModePanel.jsx

import { useState, useEffect } from 'react';
import { Button } from './ui/button';
import { Input } from './ui/input';
import { Badge } from './ui/badge';
import { Card, CardContent, CardHeader, CardTitle } from './ui/card';
import { Checkbox } from './ui/checkbox';
import { AlertTriangle, Check } from 'lucide-react';

export default function CollectionModePanel() {
  const [clientSearch, setClientSearch] = useState('');
  const [selectedClient, setSelectedClient] = useState(null);
  const [outstandingBalance, setOutstandingBalance] = useState(null);
  const [parcelsForCollection, setParcelsForCollection] = useState([]);
  const [selectedParcels, setSelectedParcels] = useState([]);
  const [showWarning, setShowWarning] = useState(false);

  const handleClientSearch = async () => {
    // Fetch client by name/phone
    // Fetch outstanding balance
    // Fetch ready parcels
  };

  const handleMarkCollected = async () => {
    if (outstandingBalance?.total_outstanding > 0) {
      setShowWarning(true);
      return;
    }
    // Mark parcels as collected
  };

  const handleAdminOverride = async () => {
    // Require admin password/confirmation
    // Log override action
    // Proceed with collection
  };

  return (
    <div className="space-y-4">
      {/* Client Search */}
      <Card>
        <CardHeader>
          <CardTitle>Client Lookup</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="flex gap-2">
            <Input
              placeholder="Search by name, phone, or scan barcode"
              value={clientSearch}
              onChange={(e) => setClientSearch(e.target.value)}
              onKeyDown={(e) => e.key === 'Enter' && handleClientSearch()}
            />
            <Button onClick={handleClientSearch}>Search</Button>
          </div>
        </CardContent>
      </Card>

      {/* Outstanding Balance Warning */}
      {selectedClient && outstandingBalance && (
        <Card className={outstandingBalance.total_outstanding > 0 ? "border-orange-400" : "border-green-400"}>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              {outstandingBalance.total_outstanding > 0 ? (
                <>
                  <AlertTriangle className="h-5 w-5 text-orange-500" />
                  Outstanding Balance
                </>
              ) : (
                <>
                  <Check className="h-5 w-5 text-green-500" />
                  Account Clear
                </>
              )}
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">
              R {outstandingBalance.total_outstanding.toLocaleString()}
            </div>
            <div className="text-sm text-muted-foreground mt-1">
              {outstandingBalance.uninvoiced_count} uninvoiced parcels + {outstandingBalance.invoices?.length || 0} unpaid invoices
            </div>
          </CardContent>
        </Card>
      )}

      {/* Parcels for Collection */}
      {parcelsForCollection.length > 0 && (
        <Card>
          <CardHeader>
            <CardTitle>Parcels Ready for Collection ({parcelsForCollection.length})</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="space-y-2">
              {parcelsForCollection.map(parcel => (
                <div key={parcel.id} className="flex items-center gap-3 p-2 border rounded">
                  <Checkbox
                    checked={selectedParcels.includes(parcel.id)}
                    onCheckedChange={(checked) => {
                      if (checked) {
                        setSelectedParcels([...selectedParcels, parcel.id]);
                      } else {
                        setSelectedParcels(selectedParcels.filter(id => id !== parcel.id));
                      }
                    }}
                  />
                  <div className="flex-1">
                    <div className="font-medium">{parcel.barcode}</div>
                    <div className="text-sm text-muted-foreground">{parcel.description}</div>
                  </div>
                  <Badge variant={parcel.is_paid ? "success" : "warning"}>
                    {parcel.is_paid ? "Paid" : "Unpaid"}
                  </Badge>
                </div>
              ))}
            </div>
            
            <div className="flex gap-2 mt-4">
              <Button
                onClick={handleMarkCollected}
                disabled={selectedParcels.length === 0}
                className="flex-1"
              >
                Mark {selectedParcels.length} as Collected
              </Button>
              {showWarning && (
                <Button
                  variant="destructive"
                  onClick={handleAdminOverride}
                >
                  Admin Override
                </Button>
              )}
            </div>
          </CardContent>
        </Card>
      )}
    </div>
  );
}
```

---

## 🧪 Testing Checklist

- [ ] Outstanding balance calculates correctly (invoices + uninvoiced)
- [ ] Collection Mode toggle works
- [ ] Client search returns correct parcels
- [ ] Warning shows when balance > 0
- [ ] Admin override requires authentication
- [ ] Notifications sent on unpaid collection attempt
- [ ] Batch mark as collected updates status
- [ ] Collection events logged in audit log

---

## 📊 Database Changes

Add to shipments:
```javascript
{
  collected_at: ISOString,
  collected_by: user_id,
  collection_override: boolean,
  collection_override_reason: string
}
```

Add notifications collection:
```javascript
{
  id: uuid,
  type: "collection_warning" | "collection_override",
  client_id: string,
  user_id: string,
  message: string,
  metadata: {
    parcel_count: number,
    outstanding_amount: number
  },
  created_at: ISOString,
  read: boolean
}
```

---

**Estimated Implementation Time**: 6-8 hours
**Priority**: HIGH (Customer satisfaction impact)
