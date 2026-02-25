"""
Backend tests for Warehouse page data synchronization features - Iteration 36
Tests: Refresh functionality, Invoice/Invoice Status columns in warehouse/parcels and shipments endpoints
"""
import pytest
import requests
import os

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

@pytest.fixture(scope="module")
def auth_session():
    """Authenticate and return session with cookies"""
    session = requests.Session()
    response = session.post(f"{BASE_URL}/api/auth/login", json={
        "email": "admin@servex.com",
        "password": "Servex2026!"
    })
    assert response.status_code == 200, f"Login failed: {response.text}"
    return session

class TestWarehouseParcelsInvoiceData:
    """Test warehouse/parcels endpoint returns invoice_number and invoice_status"""
    
    def test_warehouse_parcels_includes_invoice_fields(self, auth_session):
        """Verify warehouse/parcels response includes invoice_number and invoice_status fields"""
        response = auth_session.get(f"{BASE_URL}/api/warehouse/parcels?page_size=10")
        assert response.status_code == 200
        
        data = response.json()
        assert "items" in data
        assert "total" in data
        
        if data["items"]:
            first_item = data["items"][0]
            # Verify invoice fields exist in response
            assert "invoice_number" in first_item, "Missing invoice_number field"
            assert "invoice_status" in first_item, "Missing invoice_status field"
            print(f"PASS: warehouse/parcels includes invoice_number and invoice_status")
            print(f"  Sample: invoice_number={first_item.get('invoice_number')}, invoice_status={first_item.get('invoice_status')}")
    
    def test_warehouse_parcels_invoice_number_format(self, auth_session):
        """Verify invoice_number has correct format (INV-YYYY-XXX)"""
        response = auth_session.get(f"{BASE_URL}/api/warehouse/parcels?page_size=50")
        assert response.status_code == 200
        
        data = response.json()
        invoiced_parcels = [p for p in data["items"] if p.get("invoice_number")]
        
        if invoiced_parcels:
            for parcel in invoiced_parcels[:5]:
                inv_num = parcel.get("invoice_number")
                # Should match format INV-2026-XXX
                assert inv_num.startswith("INV-"), f"Invalid invoice format: {inv_num}"
                parts = inv_num.split("-")
                assert len(parts) == 3, f"Invalid invoice format: {inv_num}"
            print(f"PASS: Found {len(invoiced_parcels)} parcels with valid invoice numbers")
        else:
            print("WARNING: No invoiced parcels found to test format")
    
    def test_warehouse_parcels_invoice_status_values(self, auth_session):
        """Verify invoice_status has valid values (draft, sent, paid, overdue)"""
        response = auth_session.get(f"{BASE_URL}/api/warehouse/parcels?page_size=50")
        assert response.status_code == 200
        
        data = response.json()
        valid_statuses = {"draft", "sent", "paid", "overdue", None}
        
        for parcel in data["items"]:
            status = parcel.get("invoice_status")
            assert status in valid_statuses, f"Invalid invoice_status: {status}"
        
        # Count status distribution
        status_counts = {}
        for parcel in data["items"]:
            status = parcel.get("invoice_status") or "None"
            status_counts[status] = status_counts.get(status, 0) + 1
        print(f"PASS: Invoice status distribution: {status_counts}")

class TestShipmentsInvoiceData:
    """Test shipments endpoint returns invoice_number and invoice_status"""
    
    def test_shipments_includes_invoice_fields(self, auth_session):
        """Verify shipments response includes invoice_number and invoice_status fields"""
        response = auth_session.get(f"{BASE_URL}/api/shipments?limit=10")
        assert response.status_code == 200
        
        data = response.json()
        assert isinstance(data, list)
        
        if data:
            first_item = data[0]
            assert "invoice_number" in first_item, "Missing invoice_number field"
            assert "invoice_status" in first_item, "Missing invoice_status field"
            print(f"PASS: shipments endpoint includes invoice_number and invoice_status")

class TestWarehouseParcelsRefresh:
    """Test cache buster parameter for refresh functionality"""
    
    def test_cache_buster_parameter_accepted(self, auth_session):
        """Verify _t cache buster parameter doesn't cause errors"""
        import time
        cache_buster = str(int(time.time() * 1000))
        response = auth_session.get(f"{BASE_URL}/api/warehouse/parcels?page_size=5&_t={cache_buster}")
        assert response.status_code == 200, f"Cache buster failed: {response.text}"
        print(f"PASS: Cache buster parameter accepted")
    
    def test_refresh_returns_fresh_data(self, auth_session):
        """Verify consecutive calls return consistent data structure"""
        import time
        
        # First call
        response1 = auth_session.get(f"{BASE_URL}/api/warehouse/parcels?page_size=5&_t={int(time.time()*1000)}")
        assert response1.status_code == 200
        data1 = response1.json()
        
        # Second call (simulating refresh)
        time.sleep(0.1)
        response2 = auth_session.get(f"{BASE_URL}/api/warehouse/parcels?page_size=5&_t={int(time.time()*1000)}")
        assert response2.status_code == 200
        data2 = response2.json()
        
        # Structure should be consistent
        assert set(data1.keys()) == set(data2.keys()), "Response structure changed between calls"
        assert data1["total"] == data2["total"], "Total count should be consistent"
        print(f"PASS: Refresh returns consistent data structure")

class TestInvoiceEnrichmentLogic:
    """Test invoice data enrichment from invoice collection"""
    
    def test_invoiced_parcel_has_invoice_data(self, auth_session):
        """Verify parcels with invoice_id get enriched with invoice details"""
        response = auth_session.get(f"{BASE_URL}/api/warehouse/parcels?page_size=100")
        assert response.status_code == 200
        
        data = response.json()
        
        # Find parcels with invoice_id and check they have invoice_number
        for parcel in data["items"]:
            if parcel.get("invoice_id"):
                assert parcel.get("invoice_number") is not None, \
                    f"Parcel {parcel['id']} has invoice_id but no invoice_number"
                assert parcel.get("invoice_status") is not None, \
                    f"Parcel {parcel['id']} has invoice_id but no invoice_status"
        
        invoiced_count = sum(1 for p in data["items"] if p.get("invoice_id"))
        print(f"PASS: All {invoiced_count} invoiced parcels have invoice_number and invoice_status")
    
    def test_non_invoiced_parcel_has_null_invoice_data(self, auth_session):
        """Verify parcels without invoice_id have null invoice_number and invoice_status"""
        response = auth_session.get(f"{BASE_URL}/api/warehouse/parcels?page_size=100")
        assert response.status_code == 200
        
        data = response.json()
        
        non_invoiced = [p for p in data["items"] if not p.get("invoice_id")]
        for parcel in non_invoiced:
            assert parcel.get("invoice_number") is None, \
                f"Non-invoiced parcel {parcel['id']} should have null invoice_number"
            assert parcel.get("invoice_status") is None, \
                f"Non-invoiced parcel {parcel['id']} should have null invoice_status"
        
        print(f"PASS: All {len(non_invoiced)} non-invoiced parcels have null invoice data")

if __name__ == "__main__":
    pytest.main([__file__, "-v"])
