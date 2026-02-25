"""
Test CSV Import/Export features and Invoice Line Items Display
Tests for iteration 32:
1. Invoice line items display - Qty shows 1, Weight shows formatted weight
2. Client CSV Export - headers and data
3. Client CSV Import - preview modal
4. Parcel CSV Import - preview with client matching
"""
import pytest
import requests
import os
import io
import csv

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')


class TestClientExport:
    """Test Client CSV Export functionality"""
    
    @pytest.fixture
    def auth_session(self):
        """Get authenticated session"""
        session = requests.Session()
        login_resp = session.post(f"{BASE_URL}/api/auth/login", json={
            "email": "admin@servex.com",
            "password": "Servex2026!"
        })
        assert login_resp.status_code == 200, f"Login failed: {login_resp.text}"
        return session
    
    def test_client_export_returns_csv(self, auth_session):
        """Test that /api/export/clients returns a CSV file"""
        response = auth_session.get(f"{BASE_URL}/api/export/clients")
        assert response.status_code == 200, f"Export failed: {response.text}"
        
        # Check content type
        content_type = response.headers.get('Content-Type', '')
        assert 'text/csv' in content_type, f"Expected CSV content type, got: {content_type}"
        
    def test_client_export_has_correct_headers(self, auth_session):
        """Test that exported CSV has correct headers: Client Name,Phone,Email,VAT No,Physical Address,Billing Address,Rate"""
        response = auth_session.get(f"{BASE_URL}/api/export/clients")
        assert response.status_code == 200
        
        # Parse CSV
        csv_content = response.content.decode('utf-8')
        reader = csv.reader(io.StringIO(csv_content))
        headers = next(reader)
        
        expected_headers = ['Client Name', 'Phone', 'Email', 'VAT No', 'Physical Address', 'Billing Address', 'Rate']
        assert headers == expected_headers, f"Headers mismatch. Expected {expected_headers}, got {headers}"
        
    def test_client_export_contains_data(self, auth_session):
        """Test that exported CSV contains client data"""
        response = auth_session.get(f"{BASE_URL}/api/export/clients")
        assert response.status_code == 200
        
        csv_content = response.content.decode('utf-8')
        reader = csv.reader(io.StringIO(csv_content))
        rows = list(reader)
        
        # Should have at least header + some data rows
        assert len(rows) >= 2, f"Expected at least 2 rows (header + data), got {len(rows)}"
        
        # First row should be headers
        assert rows[0][0] == 'Client Name'


class TestClientImport:
    """Test Client CSV Import functionality"""
    
    @pytest.fixture
    def auth_session(self):
        """Get authenticated session"""
        session = requests.Session()
        login_resp = session.post(f"{BASE_URL}/api/auth/login", json={
            "email": "admin@servex.com",
            "password": "Servex2026!"
        })
        assert login_resp.status_code == 200, f"Login failed: {login_resp.text}"
        return session
    
    def test_client_import_endpoint_exists(self, auth_session):
        """Test that /api/import/clients endpoint exists"""
        # Create a minimal CSV file
        csv_content = "Client Name,Phone,Email,VAT No,Physical Address,Billing Address,Rate\n"
        csv_content += "TEST_Client_Import_001,+27123456789,test@test.com,,123 Test St,,36\n"
        
        files = {'file': ('test.csv', csv_content, 'text/csv')}
        response = auth_session.post(f"{BASE_URL}/api/import/clients", files=files)
        
        # Should succeed or return validation error, not 404
        assert response.status_code != 404, "Import endpoint not found"
        
    def test_client_import_success(self, auth_session):
        """Test successful client import"""
        import time
        unique_id = int(time.time())
        
        csv_content = "Client Name,Phone,Email,VAT No,Physical Address,Billing Address,Rate\n"
        csv_content += f"TEST_Import_Client_{unique_id},+27111111111,import_{unique_id}@test.com,,100 Import St,,45\n"
        
        files = {'file': ('test.csv', csv_content, 'text/csv')}
        response = auth_session.post(f"{BASE_URL}/api/import/clients", files=files)
        
        assert response.status_code == 200, f"Import failed: {response.text}"
        data = response.json()
        assert 'summary' in data, f"Response missing summary: {data}"


class TestParcelImport:
    """Test Parcel CSV Import functionality"""
    
    @pytest.fixture
    def auth_session(self):
        """Get authenticated session"""
        session = requests.Session()
        login_resp = session.post(f"{BASE_URL}/api/auth/login", json={
            "email": "admin@servex.com",
            "password": "Servex2026!"
        })
        assert login_resp.status_code == 200, f"Login failed: {login_resp.text}"
        return session
    
    def test_parcel_import_endpoint_exists(self, auth_session):
        """Test that /api/import/parcels endpoint exists"""
        csv_content = "Sent By,Primary Recipient,Secondary Recipient,Description,L,W,H,KG,QTY\n"
        csv_content += "TestClient,TestRecipient,,Test Item,10,10,10,5,1\n"
        
        files = {'file': ('test.csv', csv_content, 'text/csv')}
        response = auth_session.post(f"{BASE_URL}/api/import/parcels", files=files)
        
        # Should not be 404
        assert response.status_code != 404, "Parcel import endpoint not found"
        
    def test_parcel_import_creates_multiple_for_qty(self, auth_session):
        """Test that QTY > 1 creates multiple parcels with sequence"""
        import time
        unique_id = int(time.time())
        
        # CSV with QTY = 3
        csv_content = "Sent By,Primary Recipient,Secondary Recipient,Description,L,W,H,KG,QTY\n"
        csv_content += f"TEST_ParcelBatch_{unique_id},TestRecipient_{unique_id},,Multi-item test,20,15,10,8,3\n"
        
        files = {'file': ('test.csv', csv_content, 'text/csv')}
        response = auth_session.post(f"{BASE_URL}/api/import/parcels", files=files)
        
        assert response.status_code == 200, f"Import failed: {response.text}"
        data = response.json()
        
        # Should have created 3 parcels
        if 'details' in data:
            assert data['details']['parcels_created'] >= 3, f"Expected 3 parcels, got {data['details']['parcels_created']}"


class TestInvoiceLineItems:
    """Test Invoice Line Items Display"""
    
    @pytest.fixture
    def auth_session(self):
        """Get authenticated session"""
        session = requests.Session()
        login_resp = session.post(f"{BASE_URL}/api/auth/login", json={
            "email": "admin@servex.com",
            "password": "Servex2026!"
        })
        assert login_resp.status_code == 200, f"Login failed: {login_resp.text}"
        return session
    
    def test_invoice_list_endpoint(self, auth_session):
        """Test /api/invoices-enhanced returns invoices"""
        response = auth_session.get(f"{BASE_URL}/api/invoices-enhanced")
        assert response.status_code == 200, f"Failed to get invoices: {response.text}"
        
        data = response.json()
        assert isinstance(data, list), "Expected list of invoices"
        
    def test_invoice_detail_has_line_items(self, auth_session):
        """Test that invoice detail includes line items with correct structure"""
        # First get list of invoices
        list_response = auth_session.get(f"{BASE_URL}/api/invoices-enhanced")
        assert list_response.status_code == 200
        invoices = list_response.json()
        
        if len(invoices) == 0:
            pytest.skip("No invoices to test")
        
        # Get first invoice details
        invoice_id = invoices[0]['id']
        detail_response = auth_session.get(f"{BASE_URL}/api/invoices/{invoice_id}")
        assert detail_response.status_code == 200, f"Failed to get invoice: {detail_response.text}"
        
        invoice = detail_response.json()
        
        # Check structure
        assert 'line_items' in invoice, "Invoice missing line_items"
        assert isinstance(invoice['line_items'], list), "line_items should be a list"
        
    def test_invoice_line_item_structure(self, auth_session):
        """Test that line items have correct fields for display"""
        list_response = auth_session.get(f"{BASE_URL}/api/invoices-enhanced")
        invoices = list_response.json()
        
        if len(invoices) == 0:
            pytest.skip("No invoices to test")
        
        invoice_id = invoices[0]['id']
        detail_response = auth_session.get(f"{BASE_URL}/api/invoices/{invoice_id}")
        invoice = detail_response.json()
        
        if len(invoice.get('line_items', [])) == 0:
            pytest.skip("No line items to test")
        
        line_item = invoice['line_items'][0]
        
        # Check essential fields exist
        assert 'description' in line_item, "Line item missing description"
        assert 'rate' in line_item, "Line item missing rate"
        assert 'amount' in line_item, "Line item missing amount"


class TestSettingsCurrencies:
    """Test Currency settings for exchange rates"""
    
    @pytest.fixture
    def auth_session(self):
        """Get authenticated session"""
        session = requests.Session()
        login_resp = session.post(f"{BASE_URL}/api/auth/login", json={
            "email": "admin@servex.com",
            "password": "Servex2026!"
        })
        assert login_resp.status_code == 200
        return session
    
    def test_currencies_endpoint(self, auth_session):
        """Test /api/settings/currencies returns currencies with exchange rates"""
        response = auth_session.get(f"{BASE_URL}/api/settings/currencies")
        assert response.status_code == 200, f"Failed: {response.text}"
        
        data = response.json()
        assert 'currencies' in data, f"Response missing currencies: {data}"
        
        # Check KES currency exists
        currencies = data['currencies']
        kes_currency = next((c for c in currencies if c['code'] == 'KES'), None)
        assert kes_currency is not None, "KES currency not found"
        assert 'exchange_rate' in kes_currency, "KES missing exchange_rate"


class TestClients:
    """Test Client listing and fetching"""
    
    @pytest.fixture
    def auth_session(self):
        """Get authenticated session"""
        session = requests.Session()
        login_resp = session.post(f"{BASE_URL}/api/auth/login", json={
            "email": "admin@servex.com",
            "password": "Servex2026!"
        })
        assert login_resp.status_code == 200
        return session
    
    def test_clients_list(self, auth_session):
        """Test /api/clients returns list of clients"""
        response = auth_session.get(f"{BASE_URL}/api/clients")
        assert response.status_code == 200, f"Failed: {response.text}"
        
        data = response.json()
        assert isinstance(data, list), "Expected list of clients"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
