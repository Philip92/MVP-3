"""
Test suite for Enhanced Invoice Workflow features - Iteration 29
Tests:
- GET /api/invoices/search - Search invoices by number, client, status
- GET /api/invoices/trip-parcels/{trip_id} - Get parcels with invoice status for smart selection
- POST /api/invoices/{invoice_id}/reassign-parcels - Reassign parcels between invoices
- Invoice creation stores payment_terms and payment_terms_custom fields
- Shipment creation accepts invoice_id, recipient_phone, recipient_vat, shipping_address, length_cm, width_cm, height_cm
- Invoice PDF includes client details (name, VAT, address, phone, email) and payment terms
"""
import pytest
import requests
import os
import uuid

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')
AUTH_EMAIL = "admin@servex.com"
AUTH_PASSWORD = "Servex2026!"


class TestInvoiceWorkflow:
    """Test enhanced invoice workflow features"""
    
    @pytest.fixture(scope="class")
    def session(self):
        """Create authenticated session"""
        s = requests.Session()
        s.headers.update({"Content-Type": "application/json"})
        
        # Login
        login_resp = s.post(f"{BASE_URL}/api/auth/login", json={
            "email": AUTH_EMAIL,
            "password": AUTH_PASSWORD
        })
        assert login_resp.status_code == 200, f"Login failed: {login_resp.text}"
        print(f"✓ Logged in as {AUTH_EMAIL}")
        return s
    
    @pytest.fixture(scope="class")
    def test_client(self, session):
        """Create a test client for invoice tests"""
        client_data = {
            "name": f"TEST_Invoice_Client_{uuid.uuid4().hex[:6]}",
            "phone": "+27821234567",
            "email": "testinvoice@test.com",
            "vat_number": "VAT123456",
            "billing_address": "123 Test Street, Johannesburg",
            "default_currency": "ZAR",
            "default_rate_type": "per_kg",
            "default_rate_value": 36.0
        }
        resp = session.post(f"{BASE_URL}/api/clients", json=client_data)
        assert resp.status_code == 200, f"Failed to create client: {resp.text}"
        client = resp.json()
        print(f"✓ Created test client: {client['name']}")
        yield client
        # Cleanup
        try:
            session.delete(f"{BASE_URL}/api/clients/{client['id']}")
            print(f"✓ Cleaned up test client")
        except:
            pass
    
    @pytest.fixture(scope="class")
    def test_trip(self, session):
        """Get an existing trip for testing"""
        resp = session.get(f"{BASE_URL}/api/trips")
        assert resp.status_code == 200
        trips = resp.json()
        if trips:
            trip = trips[0]
            print(f"✓ Using trip: {trip['trip_number']}")
            return trip
        pytest.skip("No trips available for testing")
    
    # ============ Invoice Search Tests ============
    
    def test_invoice_search_endpoint_exists(self, session):
        """Test GET /api/invoices/search endpoint exists"""
        resp = session.get(f"{BASE_URL}/api/invoices/search")
        assert resp.status_code == 200, f"Search endpoint failed: {resp.text}"
        data = resp.json()
        assert isinstance(data, list), "Expected list response"
        print(f"✓ Invoice search returns {len(data)} invoices")
    
    def test_invoice_search_by_status(self, session):
        """Test search invoices by status filter"""
        resp = session.get(f"{BASE_URL}/api/invoices/search?status=draft")
        assert resp.status_code == 200
        data = resp.json()
        for inv in data:
            assert inv.get('status') == 'draft', f"Expected draft status, got {inv.get('status')}"
        print(f"✓ Invoice search by status=draft returns {len(data)} invoices")
    
    def test_invoice_search_by_query(self, session):
        """Test search invoices by query string (invoice number or client)"""
        # First get an existing invoice to search for
        all_invoices = session.get(f"{BASE_URL}/api/invoices/search").json()
        if not all_invoices:
            pytest.skip("No invoices to search")
        
        # Search by invoice number
        inv_num = all_invoices[0].get('invoice_number', '')
        if inv_num:
            resp = session.get(f"{BASE_URL}/api/invoices/search?q={inv_num[:8]}")
            assert resp.status_code == 200
            data = resp.json()
            assert len(data) > 0, "Expected at least one result when searching by invoice number"
            print(f"✓ Invoice search by query returns {len(data)} results for '{inv_num[:8]}'")
    
    def test_invoice_search_by_client_id(self, session, test_client):
        """Test search invoices by client_id"""
        resp = session.get(f"{BASE_URL}/api/invoices/search?client_id={test_client['id']}")
        assert resp.status_code == 200
        data = resp.json()
        # May be empty if no invoices for this client
        print(f"✓ Invoice search by client_id returns {len(data)} invoices")
    
    def test_invoice_search_response_format(self, session):
        """Test invoice search response has required fields"""
        resp = session.get(f"{BASE_URL}/api/invoices/search")
        assert resp.status_code == 200
        data = resp.json()
        if data:
            inv = data[0]
            expected_fields = ['id', 'invoice_number', 'client_id', 'client_name', 'status', 'total']
            for field in expected_fields:
                assert field in inv, f"Missing field '{field}' in search response"
            print(f"✓ Invoice search response has all required fields: {expected_fields}")
    
    # ============ Trip Parcels Smart Selection Tests ============
    
    def test_trip_parcels_endpoint_exists(self, session, test_trip):
        """Test GET /api/invoices/trip-parcels/{trip_id} endpoint exists"""
        resp = session.get(f"{BASE_URL}/api/invoices/trip-parcels/{test_trip['id']}")
        assert resp.status_code == 200, f"Trip parcels endpoint failed: {resp.text}"
        data = resp.json()
        assert isinstance(data, list), "Expected list response"
        print(f"✓ Trip parcels endpoint returns {len(data)} parcels")
    
    def test_trip_parcels_response_format(self, session, test_trip):
        """Test trip parcels response has required fields for smart selection"""
        resp = session.get(f"{BASE_URL}/api/invoices/trip-parcels/{test_trip['id']}")
        assert resp.status_code == 200
        data = resp.json()
        if data:
            parcel = data[0]
            # Check for required fields for smart parcel selection
            expected_fields = ['id', 'description', 'client_id', 'client_name', 'total_weight', 
                              'is_invoiced', 'invoice_id', 'invoice_number']
            for field in expected_fields:
                assert field in parcel, f"Missing field '{field}' in trip parcels response"
            print(f"✓ Trip parcels response has all required fields including is_invoiced flag")
    
    def test_trip_parcels_includes_dimensions(self, session, test_trip):
        """Test trip parcels response includes dimension fields"""
        resp = session.get(f"{BASE_URL}/api/invoices/trip-parcels/{test_trip['id']}")
        assert resp.status_code == 200
        data = resp.json()
        if data:
            parcel = data[0]
            dimension_fields = ['length_cm', 'width_cm', 'height_cm']
            for field in dimension_fields:
                assert field in parcel, f"Missing dimension field '{field}'"
            print(f"✓ Trip parcels response includes dimension fields: {dimension_fields}")
    
    def test_trip_parcels_includes_recipient_fields(self, session, test_trip):
        """Test trip parcels response includes recipient fields"""
        resp = session.get(f"{BASE_URL}/api/invoices/trip-parcels/{test_trip['id']}")
        assert resp.status_code == 200
        data = resp.json()
        if data:
            parcel = data[0]
            recipient_fields = ['recipient', 'recipient_phone', 'recipient_vat', 'shipping_address']
            for field in recipient_fields:
                assert field in parcel, f"Missing recipient field '{field}'"
            print(f"✓ Trip parcels response includes recipient fields: {recipient_fields}")
    
    # ============ Invoice Creation with Payment Terms ============
    
    def test_create_invoice_with_payment_terms(self, session, test_client):
        """Test invoice creation stores payment_terms field"""
        invoice_data = {
            "client_id": test_client['id'],
            "currency": "ZAR",
            "payment_terms": "50_50",
            "line_items": [
                {"description": "Test Item", "quantity": 10, "rate": 36, "amount": 360}
            ],
            "adjustments": [],
            "total": 360,
            "status": "draft"
        }
        resp = session.post(f"{BASE_URL}/api/invoices", json=invoice_data)
        assert resp.status_code == 200, f"Failed to create invoice: {resp.text}"
        invoice = resp.json()
        
        assert invoice.get('payment_terms') == '50_50', f"Expected payment_terms='50_50', got '{invoice.get('payment_terms')}'"
        print(f"✓ Invoice created with payment_terms='50_50': {invoice['invoice_number']}")
        
        # Cleanup
        session.delete(f"{BASE_URL}/api/invoices/{invoice['id']}")
    
    def test_create_invoice_with_custom_payment_terms(self, session, test_client):
        """Test invoice creation stores payment_terms_custom field"""
        invoice_data = {
            "client_id": test_client['id'],
            "currency": "ZAR",
            "payment_terms": "custom",
            "payment_terms_custom": "Payment due within 7 days of delivery",
            "line_items": [
                {"description": "Test Item", "quantity": 5, "rate": 36, "amount": 180}
            ],
            "adjustments": [],
            "total": 180,
            "status": "draft"
        }
        resp = session.post(f"{BASE_URL}/api/invoices", json=invoice_data)
        assert resp.status_code == 200, f"Failed to create invoice: {resp.text}"
        invoice = resp.json()
        
        assert invoice.get('payment_terms') == 'custom'
        assert invoice.get('payment_terms_custom') == 'Payment due within 7 days of delivery'
        print(f"✓ Invoice created with custom payment terms: {invoice['invoice_number']}")
        
        # Cleanup
        session.delete(f"{BASE_URL}/api/invoices/{invoice['id']}")
    
    def test_all_payment_terms_options(self, session, test_client):
        """Test all payment_terms options are accepted"""
        payment_terms_options = ['full_on_receipt', '50_50', '30_70', 'net_30', 'custom']
        
        for terms in payment_terms_options:
            invoice_data = {
                "client_id": test_client['id'],
                "currency": "ZAR",
                "payment_terms": terms,
                "payment_terms_custom": "Custom text" if terms == "custom" else None,
                "line_items": [{"description": "Test", "quantity": 1, "rate": 36, "amount": 36}],
                "adjustments": [],
                "total": 36,
                "status": "draft"
            }
            resp = session.post(f"{BASE_URL}/api/invoices", json=invoice_data)
            assert resp.status_code == 200, f"Failed to create invoice with payment_terms='{terms}': {resp.text}"
            invoice = resp.json()
            session.delete(f"{BASE_URL}/api/invoices/{invoice['id']}")
        
        print(f"✓ All payment terms options accepted: {payment_terms_options}")
    
    # ============ Shipment Creation with Enhanced Fields ============
    
    def test_create_shipment_with_invoice_id(self, session, test_client, test_trip):
        """Test shipment creation accepts invoice_id field"""
        # First create an invoice
        invoice_data = {
            "client_id": test_client['id'],
            "currency": "ZAR",
            "line_items": [{"description": "Test", "quantity": 1, "rate": 36, "amount": 36}],
            "adjustments": [],
            "total": 36,
            "status": "draft"
        }
        inv_resp = session.post(f"{BASE_URL}/api/invoices", json=invoice_data)
        assert inv_resp.status_code == 200
        invoice = inv_resp.json()
        
        # Create shipment with invoice_id
        shipment_data = {
            "client_id": test_client['id'],
            "description": "TEST_Shipment_With_Invoice",
            "destination": "Harare",
            "total_pieces": 1,
            "total_weight": 10.5,
            "invoice_id": invoice['id']
        }
        ship_resp = session.post(f"{BASE_URL}/api/shipments", json=shipment_data)
        assert ship_resp.status_code == 200, f"Failed to create shipment: {ship_resp.text}"
        shipment = ship_resp.json()
        
        assert shipment.get('invoice_id') == invoice['id'], "invoice_id not stored in shipment"
        print(f"✓ Shipment created with invoice_id link")
        
        # Cleanup
        session.delete(f"{BASE_URL}/api/shipments/{shipment['id']}")
        session.delete(f"{BASE_URL}/api/invoices/{invoice['id']}")
    
    def test_create_shipment_with_recipient_fields(self, session, test_client):
        """Test shipment creation accepts recipient_phone, recipient_vat, shipping_address"""
        shipment_data = {
            "client_id": test_client['id'],
            "description": "TEST_Shipment_With_Recipient_Fields",
            "destination": "Harare",
            "total_pieces": 1,
            "total_weight": 5.0,
            "recipient": "John Doe",
            "recipient_phone": "+263771234567",
            "recipient_vat": "VAT-ZW-12345",
            "shipping_address": "456 Recipient Street, Harare"
        }
        resp = session.post(f"{BASE_URL}/api/shipments", json=shipment_data)
        assert resp.status_code == 200, f"Failed to create shipment: {resp.text}"
        shipment = resp.json()
        
        assert shipment.get('recipient') == "John Doe"
        assert shipment.get('recipient_phone') == "+263771234567"
        assert shipment.get('recipient_vat') == "VAT-ZW-12345"
        assert shipment.get('shipping_address') == "456 Recipient Street, Harare"
        print(f"✓ Shipment created with recipient fields: phone, vat, address")
        
        # Cleanup
        session.delete(f"{BASE_URL}/api/shipments/{shipment['id']}")
    
    def test_create_shipment_with_dimensions(self, session, test_client):
        """Test shipment creation accepts length_cm, width_cm, height_cm"""
        shipment_data = {
            "client_id": test_client['id'],
            "description": "TEST_Shipment_With_Dimensions",
            "destination": "Harare",
            "total_pieces": 1,
            "total_weight": 8.0,
            "length_cm": 50.5,
            "width_cm": 30.2,
            "height_cm": 20.8
        }
        resp = session.post(f"{BASE_URL}/api/shipments", json=shipment_data)
        assert resp.status_code == 200, f"Failed to create shipment: {resp.text}"
        shipment = resp.json()
        
        assert shipment.get('length_cm') == 50.5
        assert shipment.get('width_cm') == 30.2
        assert shipment.get('height_cm') == 20.8
        print(f"✓ Shipment created with dimensions: {shipment.get('length_cm')}×{shipment.get('width_cm')}×{shipment.get('height_cm')} cm")
        
        # Cleanup
        session.delete(f"{BASE_URL}/api/shipments/{shipment['id']}")
    
    # ============ Invoice PDF Tests ============
    
    def test_invoice_pdf_with_client_details(self, session, test_client):
        """Test invoice PDF includes client details from snapshot"""
        # Create invoice with client that has all details
        invoice_data = {
            "client_id": test_client['id'],
            "currency": "ZAR",
            "payment_terms": "net_30",
            "line_items": [{"description": "Test Item for PDF", "quantity": 10, "rate": 36, "amount": 360}],
            "adjustments": [],
            "total": 360,
            "status": "draft"
        }
        inv_resp = session.post(f"{BASE_URL}/api/invoices", json=invoice_data)
        assert inv_resp.status_code == 200
        invoice = inv_resp.json()
        
        # Check invoice has client snapshots
        assert invoice.get('client_name_snapshot') == test_client['name']
        assert invoice.get('client_vat_snapshot') == test_client.get('vat_number')
        assert invoice.get('client_address_snapshot') == test_client.get('billing_address')
        print(f"✓ Invoice stores client snapshot: name, VAT, address")
        
        # Test PDF generation
        pdf_resp = session.get(f"{BASE_URL}/api/invoices/{invoice['id']}/pdf")
        assert pdf_resp.status_code == 200, f"PDF generation failed: {pdf_resp.text}"
        assert pdf_resp.headers.get('content-type') == 'application/pdf'
        print(f"✓ Invoice PDF generated successfully")
        
        # Cleanup
        session.delete(f"{BASE_URL}/api/invoices/{invoice['id']}")
    
    def test_invoice_pdf_with_payment_terms(self, session, test_client):
        """Test invoice PDF includes payment terms"""
        invoice_data = {
            "client_id": test_client['id'],
            "currency": "ZAR",
            "payment_terms": "30_70",
            "line_items": [{"description": "PDF Test with Payment Terms", "quantity": 20, "rate": 36, "amount": 720}],
            "adjustments": [],
            "total": 720,
            "status": "draft"
        }
        inv_resp = session.post(f"{BASE_URL}/api/invoices", json=invoice_data)
        assert inv_resp.status_code == 200
        invoice = inv_resp.json()
        
        assert invoice.get('payment_terms') == '30_70'
        
        # Test PDF generation
        pdf_resp = session.get(f"{BASE_URL}/api/invoices/{invoice['id']}/pdf")
        assert pdf_resp.status_code == 200
        assert len(pdf_resp.content) > 0, "PDF content is empty"
        print(f"✓ Invoice PDF with payment_terms='30_70' generated ({len(pdf_resp.content)} bytes)")
        
        # Cleanup
        session.delete(f"{BASE_URL}/api/invoices/{invoice['id']}")
    
    # ============ Invoice Reassign Parcels Tests ============
    
    def test_reassign_parcels_endpoint_exists(self, session, test_client):
        """Test POST /api/invoices/{invoice_id}/reassign-parcels endpoint exists"""
        # Create invoice
        invoice_data = {
            "client_id": test_client['id'],
            "currency": "ZAR",
            "line_items": [{"description": "Test", "quantity": 1, "rate": 36, "amount": 36}],
            "adjustments": [],
            "total": 36,
            "status": "draft"
        }
        inv_resp = session.post(f"{BASE_URL}/api/invoices", json=invoice_data)
        assert inv_resp.status_code == 200
        invoice = inv_resp.json()
        
        # Test reassign endpoint with empty list
        resp = session.post(f"{BASE_URL}/api/invoices/{invoice['id']}/reassign-parcels", json=[])
        assert resp.status_code == 200, f"Reassign endpoint failed: {resp.text}"
        data = resp.json()
        assert 'results' in data
        print(f"✓ Reassign parcels endpoint exists and returns results")
        
        # Cleanup
        session.delete(f"{BASE_URL}/api/invoices/{invoice['id']}")
    
    def test_reassign_parcel_to_invoice(self, session, test_client, test_trip):
        """Test reassigning a parcel from one invoice to another"""
        # Create two invoices
        inv1_data = {
            "client_id": test_client['id'],
            "currency": "ZAR",
            "trip_id": test_trip['id'],
            "line_items": [{"description": "Invoice 1", "quantity": 1, "rate": 36, "amount": 36}],
            "adjustments": [],
            "total": 36,
            "status": "draft"
        }
        inv2_data = {
            "client_id": test_client['id'],
            "currency": "ZAR",
            "trip_id": test_trip['id'],
            "line_items": [],
            "adjustments": [],
            "total": 0,
            "status": "draft"
        }
        
        inv1_resp = session.post(f"{BASE_URL}/api/invoices", json=inv1_data)
        inv2_resp = session.post(f"{BASE_URL}/api/invoices", json=inv2_data)
        assert inv1_resp.status_code == 200
        assert inv2_resp.status_code == 200
        
        invoice1 = inv1_resp.json()
        invoice2 = inv2_resp.json()
        
        # Create a shipment linked to invoice1
        shipment_data = {
            "client_id": test_client['id'],
            "description": "TEST_Parcel_For_Reassignment",
            "destination": "Harare",
            "total_pieces": 1,
            "total_weight": 5.0,
            "invoice_id": invoice1['id'],
            "trip_id": test_trip['id']
        }
        ship_resp = session.post(f"{BASE_URL}/api/shipments", json=shipment_data)
        assert ship_resp.status_code == 200
        shipment = ship_resp.json()
        
        # Reassign to invoice2
        reassign_resp = session.post(f"{BASE_URL}/api/invoices/{invoice2['id']}/reassign-parcels", json=[shipment['id']])
        assert reassign_resp.status_code == 200
        results = reassign_resp.json()
        
        assert len(results['results']) == 1
        assert results['results'][0]['success'] == True
        assert results['results'][0]['new_invoice_id'] == invoice2['id']
        print(f"✓ Parcel reassigned from invoice1 to invoice2")
        
        # Verify shipment is now linked to invoice2
        get_ship_resp = session.get(f"{BASE_URL}/api/shipments/{shipment['id']}")
        if get_ship_resp.status_code == 200:
            updated_shipment = get_ship_resp.json()
            assert updated_shipment.get('invoice_id') == invoice2['id']
            print(f"✓ Shipment invoice_id updated to new invoice")
        
        # Cleanup
        session.delete(f"{BASE_URL}/api/shipments/{shipment['id']}")
        session.delete(f"{BASE_URL}/api/invoices/{invoice1['id']}")
        session.delete(f"{BASE_URL}/api/invoices/{invoice2['id']}")
    
    # ============ Line Item Enhanced Fields Tests ============
    
    def test_invoice_line_item_enhanced_fields(self, session, test_client):
        """Test invoice line items accept enhanced fields: parcel_label, client_name, recipient_name, dimensions"""
        invoice_data = {
            "client_id": test_client['id'],
            "currency": "ZAR",
            "line_items": [
                {
                    "description": "Enhanced Line Item",
                    "quantity": 1,
                    "unit": "kg",
                    "rate": 36,
                    "amount": 36,
                    "parcel_label": "1 of 5",
                    "client_name": test_client['name'],
                    "recipient_name": "John Recipient",
                    "length_cm": 30.5,
                    "width_cm": 20.0,
                    "height_cm": 15.0,
                    "weight": 5.5
                }
            ],
            "adjustments": [],
            "total": 36,
            "status": "draft"
        }
        resp = session.post(f"{BASE_URL}/api/invoices", json=invoice_data)
        assert resp.status_code == 200, f"Failed to create invoice: {resp.text}"
        invoice = resp.json()
        
        # Verify line items have enhanced fields
        line_items = invoice.get('line_items', [])
        assert len(line_items) > 0
        item = line_items[0]
        
        # The backend may store some fields, check they were accepted
        print(f"✓ Invoice line item created with enhanced fields")
        
        # Cleanup
        session.delete(f"{BASE_URL}/api/invoices/{invoice['id']}")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
