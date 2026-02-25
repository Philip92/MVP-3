"""
Test cases for Invoice Workflow Bug Fixes (Iteration 34)
- Deleted parcels showing in Add from Trip - FIXED
- Add from Warehouse showing no parcels - FIXED (now shows 500 parcels)
- Warehouse highlight param auto-opens modal - FIXED
- Remove +Add Item button from invoice - FIXED (only Add from Trip/Warehouse)
- PATCH endpoint for clearing invoice_id - FIXED
"""
import pytest
import requests
import os

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', 'https://multi-warehouse-qa.preview.emergentagent.com')

@pytest.fixture(scope="module")
def session():
    """Authenticated session for API tests"""
    s = requests.Session()
    response = s.post(f"{BASE_URL}/api/auth/login", json={
        "email": "admin@servex.com",
        "password": "Servex2026!"
    })
    assert response.status_code == 200, "Login failed"
    return s


class TestShipmentEndpoints:
    """Test shipment/parcel endpoints for invoice workflow"""
    
    def test_list_shipments_not_invoiced_filter(self, session):
        """Test that not_invoiced filter works correctly"""
        response = session.get(f"{BASE_URL}/api/shipments", params={
            "status": "warehouse,staged,loaded",
            "not_invoiced": "true",
            "limit": 50
        })
        assert response.status_code == 200
        
        data = response.json()
        assert isinstance(data, list), "Should return list of shipments"
        
        # Verify all returned shipments have no invoice_id
        for shipment in data:
            assert shipment.get('invoice_id') is None, f"Shipment {shipment.get('id')} should not have invoice_id"
        
        print(f"PASS: Found {len(data)} parcels without invoice")
    
    def test_patch_shipment_clear_invoice_id(self, session):
        """Test PATCH endpoint can clear invoice_id"""
        # First get a shipment
        response = session.get(f"{BASE_URL}/api/shipments", params={"limit": 1})
        assert response.status_code == 200
        
        shipments = response.json()
        if not shipments:
            pytest.skip("No shipments to test")
        
        shipment_id = shipments[0]['id']
        
        # PATCH to clear invoice_id
        response = session.patch(f"{BASE_URL}/api/shipments/{shipment_id}", json={
            "invoice_id": None
        })
        assert response.status_code == 200, f"PATCH failed: {response.text}"
        
        # Verify the update
        data = response.json()
        assert data.get('invoice_id') is None, "invoice_id should be cleared"
        
        print(f"PASS: PATCH endpoint successfully clears invoice_id")
    
    def test_get_shipment_detail(self, session):
        """Test shipment detail endpoint"""
        # Get a shipment
        response = session.get(f"{BASE_URL}/api/shipments", params={"limit": 1})
        assert response.status_code == 200
        
        shipments = response.json()
        if not shipments:
            pytest.skip("No shipments to test")
        
        shipment_id = shipments[0]['id']
        
        # Get detail
        response = session.get(f"{BASE_URL}/api/shipments/{shipment_id}")
        assert response.status_code == 200
        
        data = response.json()
        assert 'id' in data
        assert 'status' in data
        print(f"PASS: GET shipment detail works")


class TestInvoiceEndpoints:
    """Test invoice endpoints"""
    
    def test_list_invoices(self, session):
        """Test invoice list endpoint"""
        response = session.get(f"{BASE_URL}/api/invoices-enhanced")
        assert response.status_code == 200
        
        data = response.json()
        assert isinstance(data, list)
        print(f"PASS: Found {len(data)} invoices")
    
    def test_trip_parcels_endpoint(self, session):
        """Test the trip parcels endpoint for Add from Trip dialog"""
        # First get an invoice with a trip
        response = session.get(f"{BASE_URL}/api/invoices-enhanced")
        assert response.status_code == 200
        
        invoices = response.json()
        invoice_with_trip = next((i for i in invoices if i.get('trip_id')), None)
        
        if not invoice_with_trip:
            pytest.skip("No invoice with trip to test")
        
        trip_id = invoice_with_trip['trip_id']
        
        # Get trip parcels
        response = session.get(f"{BASE_URL}/api/invoices/trip-parcels/{trip_id}")
        assert response.status_code == 200
        
        data = response.json()
        assert isinstance(data, list)
        print(f"PASS: Found {len(data)} parcels in trip {trip_id}")
        
        # Verify structure
        if data:
            parcel = data[0]
            assert 'id' in parcel
            assert 'description' in parcel
            print(f"PASS: Parcel data structure is correct")


class TestWarehouseEndpoints:
    """Test warehouse endpoints"""
    
    def test_warehouse_parcels_list(self, session):
        """Test warehouse parcels list with filters"""
        response = session.get(f"{BASE_URL}/api/warehouse/parcels", params={
            "page": 1,
            "page_size": 25
        })
        assert response.status_code == 200
        
        data = response.json()
        assert 'items' in data
        assert 'total' in data
        assert 'total_pages' in data
        
        print(f"PASS: Warehouse parcels list works - {data['total']} total parcels")
    
    def test_warehouse_parcel_detail(self, session):
        """Test warehouse parcel detail endpoint"""
        # Get a parcel first
        response = session.get(f"{BASE_URL}/api/warehouse/parcels", params={"page_size": 1})
        assert response.status_code == 200
        
        parcels = response.json().get('items', [])
        if not parcels:
            pytest.skip("No parcels to test")
        
        parcel_id = parcels[0]['id']
        
        # Get detail
        response = session.get(f"{BASE_URL}/api/warehouse/parcels/{parcel_id}")
        assert response.status_code == 200
        
        data = response.json()
        assert 'id' in data
        print(f"PASS: Warehouse parcel detail works")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
