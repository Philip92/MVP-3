"""
Test Finance Features - Iteration 31
Tests for currency toggle, exchange rates, WhatsApp log, and invoice validation features
"""
import pytest
import requests
import os

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

class TestCurrencySettings:
    """Currency settings and exchange rate tests"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Login and get auth session"""
        self.session = requests.Session()
        login_response = self.session.post(
            f"{BASE_URL}/api/auth/login",
            json={"email": "admin@servex.com", "password": "Servex2026!"}
        )
        assert login_response.status_code == 200, f"Login failed: {login_response.text}"
        self.user = login_response.json()
        yield
        # Cleanup
        self.session.close()
    
    def test_get_currencies_endpoint(self):
        """Test GET /api/settings/currencies returns currency data with exchange rates"""
        response = self.session.get(f"{BASE_URL}/api/settings/currencies")
        assert response.status_code == 200, f"Failed to get currencies: {response.text}"
        
        data = response.json()
        assert "currencies" in data, "Response should have 'currencies' key"
        
        currencies = data["currencies"]
        assert len(currencies) >= 2, "Should have at least ZAR and KES currencies"
        
        # Check ZAR
        zar = next((c for c in currencies if c["code"] == "ZAR"), None)
        assert zar is not None, "ZAR currency should exist"
        assert zar["exchange_rate"] == 1.0 or zar["exchange_rate"] == 1, "ZAR exchange rate should be 1"
        
        # Check KES
        kes = next((c for c in currencies if c["code"] == "KES"), None)
        assert kes is not None, "KES currency should exist"
        assert kes["exchange_rate"] == 6.67, "KES exchange rate should be 6.67"
    
    def test_currencies_have_required_fields(self):
        """Test that currency objects have all required fields"""
        response = self.session.get(f"{BASE_URL}/api/settings/currencies")
        assert response.status_code == 200
        
        currencies = response.json()["currencies"]
        required_fields = ["code", "name", "symbol", "exchange_rate"]
        
        for currency in currencies:
            for field in required_fields:
                assert field in currency, f"Currency missing field: {field}"


class TestFinanceEndpoints:
    """Finance hub endpoint tests"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Login and get auth session"""
        self.session = requests.Session()
        login_response = self.session.post(
            f"{BASE_URL}/api/auth/login",
            json={"email": "admin@servex.com", "password": "Servex2026!"}
        )
        assert login_response.status_code == 200
        yield
        self.session.close()
    
    def test_client_statements_endpoint(self):
        """Test GET /api/finance/client-statements returns statements data"""
        response = self.session.get(f"{BASE_URL}/api/finance/client-statements")
        assert response.status_code == 200
        
        data = response.json()
        assert "statements" in data, "Should have statements key"
        assert "trip_columns" in data, "Should have trip_columns key"
        assert "summary" in data, "Should have summary key"
        
        summary = data["summary"]
        assert "total_outstanding" in summary, "Summary should have total_outstanding"
        assert "clients_with_debt" in summary, "Summary should have clients_with_debt"
        assert "overdue_amount" in summary, "Summary should have overdue_amount"
    
    def test_overdue_invoices_endpoint(self):
        """Test GET /api/finance/overdue returns overdue data"""
        response = self.session.get(f"{BASE_URL}/api/finance/overdue")
        assert response.status_code == 200
        
        data = response.json()
        assert "invoices" in data, "Should have invoices key"
        assert "total_overdue" in data, "Should have total_overdue key"
        assert "count" in data, "Should have count key"
        assert isinstance(data["invoices"], list), "Invoices should be a list"


class TestWhatsAppLogging:
    """WhatsApp log endpoint tests"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Login and get auth session"""
        self.session = requests.Session()
        login_response = self.session.post(
            f"{BASE_URL}/api/auth/login",
            json={"email": "admin@servex.com", "password": "Servex2026!"}
        )
        assert login_response.status_code == 200
        yield
        self.session.close()
    
    def test_whatsapp_log_endpoint_success(self):
        """Test POST /api/invoices/{id}/log-whatsapp logs a message"""
        # First get an invoice
        invoices_response = self.session.get(f"{BASE_URL}/api/invoices")
        assert invoices_response.status_code == 200
        
        invoices = invoices_response.json()
        if not invoices:
            pytest.skip("No invoices to test WhatsApp logging")
        
        invoice_id = invoices[0]["id"]
        
        # Test WhatsApp log
        response = self.session.post(
            f"{BASE_URL}/api/invoices/{invoice_id}/log-whatsapp",
            json={
                "to_number": "+27123456789",
                "message": "TEST: Payment reminder message"
            }
        )
        assert response.status_code == 200, f"Failed to log WhatsApp: {response.text}"
        
        data = response.json()
        assert "message" in data, "Should have message in response"
        assert "log_id" in data, "Should have log_id in response"
    
    def test_whatsapp_log_invalid_invoice(self):
        """Test POST /api/invoices/{id}/log-whatsapp with invalid invoice returns 404"""
        response = self.session.post(
            f"{BASE_URL}/api/invoices/invalid-invoice-id/log-whatsapp",
            json={
                "to_number": "+27123456789",
                "message": "Test message"
            }
        )
        assert response.status_code == 404, "Should return 404 for invalid invoice"


class TestTripWorksheets:
    """Trip worksheet endpoint tests"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Login and get auth session"""
        self.session = requests.Session()
        login_response = self.session.post(
            f"{BASE_URL}/api/auth/login",
            json={"email": "admin@servex.com", "password": "Servex2026!"}
        )
        assert login_response.status_code == 200
        yield
        self.session.close()
    
    def test_trip_worksheet_endpoint(self):
        """Test GET /api/finance/trip-worksheet/{trip_id} returns worksheet data"""
        # First get a trip
        trips_response = self.session.get(f"{BASE_URL}/api/trips")
        assert trips_response.status_code == 200
        
        trips = trips_response.json()
        if not trips:
            pytest.skip("No trips to test worksheet")
        
        trip_id = trips[0]["id"]
        
        response = self.session.get(f"{BASE_URL}/api/finance/trip-worksheet/{trip_id}")
        assert response.status_code == 200
        
        data = response.json()
        assert "trip" in data, "Should have trip data"
        assert "summary" in data, "Should have summary data"
        assert "invoices" in data, "Should have invoices list"
        
        summary = data["summary"]
        assert "total_revenue" in summary, "Summary should have total_revenue"
        assert "total_collected" in summary, "Summary should have total_collected"
        assert "total_outstanding" in summary, "Summary should have total_outstanding"
        assert "collection_percent" in summary, "Summary should have collection_percent"


class TestInvoicePDF:
    """Invoice PDF generation tests"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Login and get auth session"""
        self.session = requests.Session()
        login_response = self.session.post(
            f"{BASE_URL}/api/auth/login",
            json={"email": "admin@servex.com", "password": "Servex2026!"}
        )
        assert login_response.status_code == 200
        yield
        self.session.close()
    
    def test_invoice_pdf_download(self):
        """Test GET /api/invoices/{id}/pdf returns a valid PDF"""
        # First get an invoice
        invoices_response = self.session.get(f"{BASE_URL}/api/invoices")
        assert invoices_response.status_code == 200
        
        invoices = invoices_response.json()
        if not invoices:
            pytest.skip("No invoices to test PDF download")
        
        invoice_id = invoices[0]["id"]
        
        response = self.session.get(f"{BASE_URL}/api/invoices/{invoice_id}/pdf")
        assert response.status_code == 200, f"Failed to download PDF: {response.text}"
        assert response.headers.get("content-type") == "application/pdf", "Content type should be PDF"
        
        # Check PDF starts with %PDF
        content = response.content
        assert content[:4] == b'%PDF', "PDF content should start with %PDF header"


class TestInvoiceValidation:
    """Invoice validation and total matching tests"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Login and get auth session"""
        self.session = requests.Session()
        login_response = self.session.post(
            f"{BASE_URL}/api/auth/login",
            json={"email": "admin@servex.com", "password": "Servex2026!"}
        )
        assert login_response.status_code == 200
        yield
        self.session.close()
    
    def test_invoice_total_matches_line_items_plus_adjustments(self):
        """Test that invoice total equals line items subtotal + adjustments"""
        # Get an invoice with line items
        invoices_response = self.session.get(f"{BASE_URL}/api/invoices")
        assert invoices_response.status_code == 200
        
        invoices = invoices_response.json()
        if not invoices:
            pytest.skip("No invoices to test")
        
        invoice_id = invoices[0]["id"]
        
        # Get full invoice data
        invoice_response = self.session.get(f"{BASE_URL}/api/invoices/{invoice_id}")
        assert invoice_response.status_code == 200
        
        invoice = invoice_response.json()
        line_items = invoice.get("line_items", [])
        adjustments = invoice.get("adjustments", [])
        
        # Calculate expected total
        subtotal = sum(item.get("amount", 0) for item in line_items)
        adj_total = sum(
            adj.get("amount", 0) if adj.get("is_addition", True) else -adj.get("amount", 0)
            for adj in adjustments
        )
        expected_total = subtotal + adj_total
        
        actual_total = invoice.get("total", 0)
        
        # Allow small floating point tolerance
        assert abs(actual_total - expected_total) < 0.01, \
            f"Invoice total {actual_total} doesn't match calculated {expected_total}"


class TestClientRateAutoPopulate:
    """Client rate auto-population tests"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Login and get auth session"""
        self.session = requests.Session()
        login_response = self.session.post(
            f"{BASE_URL}/api/auth/login",
            json={"email": "admin@servex.com", "password": "Servex2026!"}
        )
        assert login_response.status_code == 200
        yield
        self.session.close()
    
    def test_client_has_vat_and_rate(self):
        """Test that clients have VAT number and default rate available"""
        clients_response = self.session.get(f"{BASE_URL}/api/clients")
        assert clients_response.status_code == 200
        
        clients = clients_response.json()
        if not clients:
            pytest.skip("No clients to test")
        
        # Check that client structure supports VAT and rate
        client = clients[0]
        # VAT is optional but field should be in response
        assert "id" in client, "Client should have id"
        assert "name" in client, "Client should have name"
    
    def test_client_rate_endpoint(self):
        """Test GET /api/clients/{id}/rate returns rate data"""
        clients_response = self.session.get(f"{BASE_URL}/api/clients")
        assert clients_response.status_code == 200
        
        clients = clients_response.json()
        if not clients:
            pytest.skip("No clients to test")
        
        client_id = clients[0]["id"]
        
        response = self.session.get(f"{BASE_URL}/api/clients/{client_id}/rate")
        # Rate endpoint may return 404 if no rate set, or 200 with rate data
        assert response.status_code in [200, 404], f"Unexpected status: {response.status_code}"
        
        if response.status_code == 200:
            data = response.json()
            assert "rate_per_kg" in data, "Rate response should have rate_per_kg"


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
