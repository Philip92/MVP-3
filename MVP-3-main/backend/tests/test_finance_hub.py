"""
Finance Hub API Tests
Tests for the Finance Hub feature with 60/40 split view:
- GET /api/invoices-enhanced: List invoices with filters
- GET /api/invoices/{id}/full: Get complete invoice data
- POST /api/invoices: Create new invoice
- POST /api/invoices/{id}/finalize: Finalize invoice
- POST /api/invoices/{id}/record-payment: Record payment
- POST /api/invoices/{id}/log-whatsapp: Log WhatsApp send
- GET /api/trips-dropdown: Get trips for dropdown
- GET /api/trips/{id}/parcels-for-invoice: Get parcels for invoice
"""

import pytest
import requests
import os

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')
SESSION_TOKEN = "demo_trips_session_1771084342772"

# Test data references from context
TEST_INVOICES = {
    "sent_1": "c387cc73-0599-47c8-94a6-22dc9191578f",  # INV-2026-001
    "sent_2": "63085f5c-2752-45da-b5fa-f34ad67ca11f",  # INV-2026-002
    "draft": "bc660ff0-645a-4364-9d24-82c3a8282b33"    # INV-2026-0003
}

TEST_CLIENT_ID = "client-1"  # MTN South Africa
TEST_TRIP_ID = "trip-1"  # S27


@pytest.fixture
def auth_headers():
    """Headers with auth token"""
    return {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {SESSION_TOKEN}"
    }


class TestInvoicesEnhanced:
    """Tests for GET /api/invoices-enhanced endpoint"""
    
    def test_list_invoices_enhanced_success(self, auth_headers):
        """Test listing invoices with enhanced data"""
        response = requests.get(f"{BASE_URL}/api/invoices-enhanced", headers=auth_headers)
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert isinstance(data, list), "Response should be a list"
        assert len(data) >= 3, f"Expected at least 3 invoices, got {len(data)}"
        
        # Verify enhanced data structure
        for inv in data:
            assert "client_name" in inv, "Missing client_name in response"
            assert "display_status" in inv, "Missing display_status in response"
            assert "paid_amount" in inv, "Missing paid_amount in response"
            assert "outstanding" in inv, "Missing outstanding in response"
            assert "invoice_number" in inv, "Missing invoice_number"
            assert "total" in inv, "Missing total"
    
    def test_filter_by_status_draft(self, auth_headers):
        """Test filtering by status=draft"""
        response = requests.get(f"{BASE_URL}/api/invoices-enhanced?status=draft", headers=auth_headers)
        
        assert response.status_code == 200
        data = response.json()
        
        # All returned invoices should be draft
        for inv in data:
            assert inv["status"] == "draft" or inv["display_status"] == "draft"
    
    def test_filter_by_status_sent(self, auth_headers):
        """Test filtering by status=sent"""
        response = requests.get(f"{BASE_URL}/api/invoices-enhanced?status=sent", headers=auth_headers)
        
        assert response.status_code == 200
        data = response.json()
        
        for inv in data:
            assert inv["status"] == "sent"
    
    def test_filter_by_trip(self, auth_headers):
        """Test filtering by trip_id"""
        response = requests.get(f"{BASE_URL}/api/invoices-enhanced?trip_id={TEST_TRIP_ID}", headers=auth_headers)
        
        assert response.status_code == 200
        data = response.json()
        
        # All returned invoices should be for the specified trip
        for inv in data:
            assert inv.get("trip_id") == TEST_TRIP_ID
    
    def test_sort_by_newest(self, auth_headers):
        """Test sorting by newest first"""
        response = requests.get(f"{BASE_URL}/api/invoices-enhanced?sort_by=newest", headers=auth_headers)
        
        assert response.status_code == 200
        data = response.json()
        
        if len(data) > 1:
            # Verify dates are in descending order
            dates = [inv.get("created_at", "") for inv in data]
            assert dates == sorted(dates, reverse=True), "Invoices should be sorted newest first"
    
    def test_sort_by_amount_high(self, auth_headers):
        """Test sorting by amount (high to low)"""
        response = requests.get(f"{BASE_URL}/api/invoices-enhanced?sort_by=amount_high", headers=auth_headers)
        
        assert response.status_code == 200
        data = response.json()
        
        if len(data) > 1:
            amounts = [inv.get("total", 0) for inv in data]
            assert amounts == sorted(amounts, reverse=True), "Invoices should be sorted by amount descending"
    
    def test_unauthorized_access(self):
        """Test that endpoint requires authentication"""
        response = requests.get(f"{BASE_URL}/api/invoices-enhanced")
        
        assert response.status_code == 401


class TestInvoiceFull:
    """Tests for GET /api/invoices/{id}/full endpoint"""
    
    def test_get_invoice_full_success(self, auth_headers):
        """Test getting complete invoice data"""
        invoice_id = TEST_INVOICES["draft"]
        response = requests.get(f"{BASE_URL}/api/invoices/{invoice_id}/full", headers=auth_headers)
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        
        # Verify all required fields
        assert "id" in data
        assert "invoice_number" in data
        assert "status" in data
        assert "display_status" in data
        assert "client" in data, "Missing client data"
        assert "line_items" in data, "Missing line_items"
        assert "adjustments" in data, "Missing adjustments"
        assert "payments" in data, "Missing payments"
        assert "paid_amount" in data
        assert "outstanding" in data
    
    def test_get_sent_invoice_full(self, auth_headers):
        """Test getting sent invoice with all data"""
        invoice_id = TEST_INVOICES["sent_1"]
        response = requests.get(f"{BASE_URL}/api/invoices/{invoice_id}/full", headers=auth_headers)
        
        assert response.status_code == 200
        
        data = response.json()
        assert data["status"] == "sent"
        assert data["client"] is not None
    
    def test_invoice_full_404(self, auth_headers):
        """Test 404 for non-existent invoice"""
        response = requests.get(f"{BASE_URL}/api/invoices/non-existent-id/full", headers=auth_headers)
        
        assert response.status_code == 404
    
    def test_invoice_full_unauthorized(self):
        """Test that endpoint requires authentication"""
        invoice_id = TEST_INVOICES["draft"]
        response = requests.get(f"{BASE_URL}/api/invoices/{invoice_id}/full")
        
        assert response.status_code == 401


class TestCreateInvoice:
    """Tests for POST /api/invoices endpoint"""
    
    def test_create_invoice_success(self, auth_headers):
        """Test creating a new invoice"""
        payload = {
            "client_id": TEST_CLIENT_ID,
            "trip_id": TEST_TRIP_ID,
            "subtotal": 1000.00,
            "adjustments": 50.00,
            "currency": "ZAR"
        }
        
        response = requests.post(f"{BASE_URL}/api/invoices", json=payload, headers=auth_headers)
        
        assert response.status_code in [200, 201], f"Expected 200/201, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert "id" in data
        assert "invoice_number" in data
        assert data["status"] == "draft"
        assert data["client_id"] == TEST_CLIENT_ID
        
        # Verify invoice was created via GET
        get_response = requests.get(f"{BASE_URL}/api/invoices/{data['id']}/full", headers=auth_headers)
        assert get_response.status_code == 200
        
        # Clean up - delete the test invoice
        requests.delete(f"{BASE_URL}/api/invoices/{data['id']}", headers=auth_headers)
    
    def test_create_invoice_minimal(self, auth_headers):
        """Test creating invoice with minimal data"""
        payload = {
            "client_id": TEST_CLIENT_ID,
            "subtotal": 500.00
        }
        
        response = requests.post(f"{BASE_URL}/api/invoices", json=payload, headers=auth_headers)
        
        assert response.status_code in [200, 201]
        
        data = response.json()
        assert data["client_id"] == TEST_CLIENT_ID
        
        # Clean up
        requests.delete(f"{BASE_URL}/api/invoices/{data['id']}", headers=auth_headers)
    
    def test_create_invoice_invalid_client(self, auth_headers):
        """Test creating invoice with invalid client"""
        payload = {
            "client_id": "invalid-client-id",
            "subtotal": 100.00
        }
        
        response = requests.post(f"{BASE_URL}/api/invoices", json=payload, headers=auth_headers)
        
        # Should fail with 404 or 400
        assert response.status_code in [400, 404]


class TestFinalizeInvoice:
    """Tests for POST /api/invoices/{id}/finalize endpoint"""
    
    def test_finalize_draft_invoice(self, auth_headers):
        """Test finalizing a draft invoice"""
        # First create a new invoice
        payload = {
            "client_id": TEST_CLIENT_ID,
            "subtotal": 800.00,
            "currency": "ZAR"
        }
        create_response = requests.post(f"{BASE_URL}/api/invoices", json=payload, headers=auth_headers)
        assert create_response.status_code in [200, 201]
        
        invoice_id = create_response.json()["id"]
        
        # Finalize it
        finalize_response = requests.post(f"{BASE_URL}/api/invoices/{invoice_id}/finalize", headers=auth_headers)
        
        assert finalize_response.status_code == 200, f"Expected 200, got {finalize_response.status_code}: {finalize_response.text}"
        
        data = finalize_response.json()
        assert data["status"] == "sent"
        
        # Verify status change via GET
        get_response = requests.get(f"{BASE_URL}/api/invoices/{invoice_id}/full", headers=auth_headers)
        assert get_response.json()["status"] == "sent"
        
        # Clean up - cannot delete sent invoice as non-owner, leave it
    
    def test_finalize_sent_invoice_fails(self, auth_headers):
        """Test that finalizing an already sent invoice fails"""
        invoice_id = TEST_INVOICES["sent_1"]
        
        response = requests.post(f"{BASE_URL}/api/invoices/{invoice_id}/finalize", headers=auth_headers)
        
        assert response.status_code == 400
        assert "draft" in response.json()["detail"].lower()
    
    def test_finalize_404(self, auth_headers):
        """Test 404 for non-existent invoice"""
        response = requests.post(f"{BASE_URL}/api/invoices/non-existent-id/finalize", headers=auth_headers)
        
        assert response.status_code == 404


class TestRecordPayment:
    """Tests for POST /api/invoices/{id}/record-payment endpoint"""
    
    def test_record_payment_success(self, auth_headers):
        """Test recording a payment against a sent invoice"""
        invoice_id = TEST_INVOICES["sent_1"]
        
        # Get current invoice state
        get_response = requests.get(f"{BASE_URL}/api/invoices/{invoice_id}/full", headers=auth_headers)
        invoice = get_response.json()
        outstanding = invoice.get("outstanding", invoice["total"])
        
        # Record a partial payment
        payment_amount = min(100.00, outstanding - 1)  # Leave some outstanding
        
        if payment_amount <= 0:
            pytest.skip("Invoice already fully paid")
        
        payload = {
            "amount": payment_amount,
            "payment_date": "2026-02-14",
            "payment_method": "bank_transfer",
            "reference": "TEST-REF-001",
            "notes": "Test payment"
        }
        
        response = requests.post(f"{BASE_URL}/api/invoices/{invoice_id}/record-payment", json=payload, headers=auth_headers)
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert "payment_id" in data
        assert "new_paid_total" in data
        assert "outstanding" in data
    
    def test_record_payment_full(self, auth_headers):
        """Test recording full payment marks invoice as paid"""
        # Create a new invoice
        create_payload = {
            "client_id": TEST_CLIENT_ID,
            "subtotal": 500.00,
            "currency": "ZAR"
        }
        create_response = requests.post(f"{BASE_URL}/api/invoices", json=create_payload, headers=auth_headers)
        invoice_id = create_response.json()["id"]
        
        # Finalize it
        requests.post(f"{BASE_URL}/api/invoices/{invoice_id}/finalize", headers=auth_headers)
        
        # Get the invoice to check total
        get_response = requests.get(f"{BASE_URL}/api/invoices/{invoice_id}/full", headers=auth_headers)
        total = get_response.json()["total"]
        
        # Record full payment
        payment_payload = {
            "amount": total,
            "payment_date": "2026-02-14",
            "payment_method": "cash"
        }
        
        payment_response = requests.post(f"{BASE_URL}/api/invoices/{invoice_id}/record-payment", json=payment_payload, headers=auth_headers)
        
        assert payment_response.status_code == 200
        
        data = payment_response.json()
        assert data["fully_paid"] == True
        assert data["outstanding"] == 0
    
    def test_record_payment_invalid_amount(self, auth_headers):
        """Test recording payment with invalid amount"""
        invoice_id = TEST_INVOICES["sent_2"]
        
        payload = {
            "amount": -100.00,
            "payment_method": "cash"
        }
        
        response = requests.post(f"{BASE_URL}/api/invoices/{invoice_id}/record-payment", json=payload, headers=auth_headers)
        
        assert response.status_code == 400
    
    def test_record_payment_exceeds_outstanding(self, auth_headers):
        """Test recording payment that exceeds outstanding amount"""
        invoice_id = TEST_INVOICES["sent_1"]
        
        # Get current invoice
        get_response = requests.get(f"{BASE_URL}/api/invoices/{invoice_id}/full", headers=auth_headers)
        invoice = get_response.json()
        
        # Try to pay more than outstanding
        payload = {
            "amount": invoice["total"] + 10000,
            "payment_method": "bank_transfer"
        }
        
        response = requests.post(f"{BASE_URL}/api/invoices/{invoice_id}/record-payment", json=payload, headers=auth_headers)
        
        assert response.status_code == 400


class TestLogWhatsApp:
    """Tests for POST /api/invoices/{id}/log-whatsapp endpoint"""
    
    def test_log_whatsapp_success(self, auth_headers):
        """Test logging WhatsApp send"""
        invoice_id = TEST_INVOICES["sent_1"]
        
        payload = {
            "to_number": "+27123456789",
            "message": "Your invoice is ready for payment"
        }
        
        response = requests.post(f"{BASE_URL}/api/invoices/{invoice_id}/log-whatsapp", json=payload, headers=auth_headers)
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert "message" in data
        assert "log_id" in data
    
    def test_log_whatsapp_404(self, auth_headers):
        """Test 404 for non-existent invoice"""
        response = requests.post(
            f"{BASE_URL}/api/invoices/non-existent-id/log-whatsapp",
            json={"to_number": "+27123456789", "message": "Test"},
            headers=auth_headers
        )
        
        assert response.status_code == 404


class TestTripsDropdown:
    """Tests for GET /api/trips-dropdown endpoint"""
    
    def test_trips_dropdown_success(self, auth_headers):
        """Test getting trips for dropdown"""
        response = requests.get(f"{BASE_URL}/api/trips-dropdown", headers=auth_headers)
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert isinstance(data, list)
        
        # Verify structure
        for trip in data:
            assert "id" in trip
            assert "trip_number" in trip
            assert "status" in trip
    
    def test_trips_dropdown_unauthorized(self):
        """Test that endpoint requires authentication"""
        response = requests.get(f"{BASE_URL}/api/trips-dropdown")
        
        assert response.status_code == 401


class TestParcelsForInvoice:
    """Tests for GET /api/trips/{id}/parcels-for-invoice endpoint"""
    
    def test_parcels_for_invoice_success(self, auth_headers):
        """Test getting parcels from trip for invoice"""
        response = requests.get(f"{BASE_URL}/api/trips/{TEST_TRIP_ID}/parcels-for-invoice", headers=auth_headers)
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert isinstance(data, list)
        
        # Verify structure if parcels exist
        for parcel in data:
            assert "id" in parcel
            assert "client_name" in parcel
            assert "total_weight" in parcel
            assert "default_rate" in parcel
    
    def test_parcels_for_invoice_filter_by_client(self, auth_headers):
        """Test filtering parcels by client"""
        response = requests.get(
            f"{BASE_URL}/api/trips/{TEST_TRIP_ID}/parcels-for-invoice?client_id={TEST_CLIENT_ID}",
            headers=auth_headers
        )
        
        assert response.status_code == 200
        
        data = response.json()
        # All parcels should be for the specified client
        for parcel in data:
            assert parcel["client_id"] == TEST_CLIENT_ID
    
    def test_parcels_for_invoice_404(self, auth_headers):
        """Test 404 for non-existent trip"""
        response = requests.get(f"{BASE_URL}/api/trips/non-existent-trip/parcels-for-invoice", headers=auth_headers)
        
        # Should return 404 or empty list
        assert response.status_code in [200, 404]


class TestInvoiceAdjustments:
    """Tests for invoice adjustments endpoints"""
    
    def test_add_adjustment_to_draft(self, auth_headers):
        """Test adding adjustment to draft invoice"""
        invoice_id = TEST_INVOICES["draft"]
        
        payload = {
            "description": "Test discount",
            "amount": 100.00,
            "is_addition": False
        }
        
        response = requests.post(f"{BASE_URL}/api/invoices/{invoice_id}/adjustments", json=payload, headers=auth_headers)
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert "id" in data
        
        # Clean up
        requests.delete(f"{BASE_URL}/api/invoices/{invoice_id}/adjustments/{data['id']}", headers=auth_headers)
    
    def test_add_adjustment_to_sent_fails(self, auth_headers):
        """Test that adding adjustment to sent invoice fails"""
        invoice_id = TEST_INVOICES["sent_1"]
        
        payload = {
            "description": "Late fee",
            "amount": 50.00,
            "is_addition": True
        }
        
        response = requests.post(f"{BASE_URL}/api/invoices/{invoice_id}/adjustments", json=payload, headers=auth_headers)
        
        assert response.status_code == 400


class TestInvoiceLineItems:
    """Tests for invoice line items endpoints"""
    
    def test_add_line_item_to_draft(self, auth_headers):
        """Test adding line item to draft invoice"""
        invoice_id = TEST_INVOICES["draft"]
        
        payload = {
            "description": "Test freight item",
            "quantity": 1,
            "weight": 50.0,
            "rate": 36.0
        }
        
        response = requests.post(f"{BASE_URL}/api/invoices/{invoice_id}/items", json=payload, headers=auth_headers)
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert "id" in data
        assert data["amount"] == 50.0 * 36.0
        
        # Clean up
        requests.delete(f"{BASE_URL}/api/invoices/{invoice_id}/items/{data['id']}", headers=auth_headers)


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
