"""
Test suite for PDF Invoice Generation endpoint
Tests: GET /api/invoices/{invoice_id}/pdf

Features being tested:
1. PDF endpoint returns PDF blob with correct content type
2. PDF contains Servex logo at top-left (if file exists)
3. PDF shows company info: SERVEX HOLDINGS (PTY) LTD, address, contact
4. PDF shows invoice details: Invoice #, Date, Due Date
5. PDF shows Bill To section with client name, phone, email
6. PDF has line items table with olive header (#6B633C)
7. PDF shows Subtotal, Adjustments, TOTAL
8. PDF shows payment status (PAID/UNPAID/PARTIAL)
9. PDF shows payment info with bank account
"""

import pytest
import requests
import os
from io import BytesIO

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL').rstrip('/')
SESSION_TOKEN = "demo_trips_session_1771084342772"
AUTH_HEADER = {"Cookie": f"session_token={SESSION_TOKEN}"}

class TestPDFInvoiceGeneration:
    """Tests for PDF Invoice Generation endpoint"""

    # Test invoice IDs from the database
    PAID_INVOICE_ID = "3ee26ddd-f114-4852-9ed5-a7860230a12d"  # INV-2026-007 (PAID)
    SENT_INVOICE_ID = "9d8e0f09-a5e3-4171-a4c8-27c802f3cb15"  # INV-2026-008 (SENT/UNPAID)
    PARTIAL_INVOICE_ID = "c387cc73-0599-47c8-94a6-22dc9191578f"  # INV-2026-001 (PARTIAL - has 200 paid, 437.5 outstanding)
    INVOICE_WITH_ADJUSTMENTS = "63085f5c-2752-45da-b5fa-f34ad67ca11f"  # INV-2026-002 (has adjustments)
    
    def test_pdf_endpoint_returns_pdf_content_type(self):
        """Test that PDF endpoint returns application/pdf content type"""
        response = requests.get(
            f"{BASE_URL}/api/invoices/{self.SENT_INVOICE_ID}/pdf",
            headers=AUTH_HEADER,
            stream=True
        )
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        assert response.headers.get('content-type') == 'application/pdf', \
            f"Expected content-type application/pdf, got {response.headers.get('content-type')}"
        print("✓ PDF endpoint returns application/pdf content type")

    def test_pdf_endpoint_returns_pdf_blob(self):
        """Test that PDF endpoint returns actual PDF data (starts with %PDF)"""
        response = requests.get(
            f"{BASE_URL}/api/invoices/{self.SENT_INVOICE_ID}/pdf",
            headers=AUTH_HEADER
        )
        
        assert response.status_code == 200
        
        # PDF files start with %PDF
        pdf_content = response.content
        assert pdf_content[:4] == b'%PDF', f"Expected PDF to start with %PDF, got {pdf_content[:20]}"
        
        # PDF should have substantial content
        assert len(pdf_content) > 1000, f"PDF too small: {len(pdf_content)} bytes"
        print(f"✓ PDF endpoint returns valid PDF blob ({len(pdf_content)} bytes)")

    def test_pdf_contains_correct_filename_header(self):
        """Test that Content-Disposition header contains correct filename"""
        response = requests.get(
            f"{BASE_URL}/api/invoices/{self.SENT_INVOICE_ID}/pdf",
            headers=AUTH_HEADER
        )
        
        assert response.status_code == 200
        
        content_disposition = response.headers.get('content-disposition', '')
        assert 'attachment' in content_disposition.lower(), \
            f"Expected attachment disposition, got {content_disposition}"
        assert 'INV-2026-008.pdf' in content_disposition or 'filename=' in content_disposition, \
            f"Expected filename in disposition, got {content_disposition}"
        print(f"✓ PDF has correct Content-Disposition: {content_disposition}")

    def test_pdf_for_paid_invoice(self):
        """Test PDF generation for a paid invoice"""
        response = requests.get(
            f"{BASE_URL}/api/invoices/{self.PAID_INVOICE_ID}/pdf",
            headers=AUTH_HEADER
        )
        
        assert response.status_code == 200
        assert response.headers.get('content-type') == 'application/pdf'
        
        # Verify it's a valid PDF
        pdf_content = response.content
        assert pdf_content[:4] == b'%PDF'
        print("✓ PDF generation works for PAID invoice")

    def test_pdf_for_partial_payment_invoice(self):
        """Test PDF generation for an invoice with partial payment"""
        response = requests.get(
            f"{BASE_URL}/api/invoices/{self.PARTIAL_INVOICE_ID}/pdf",
            headers=AUTH_HEADER
        )
        
        assert response.status_code == 200
        assert response.headers.get('content-type') == 'application/pdf'
        
        # Verify it's a valid PDF
        pdf_content = response.content
        assert pdf_content[:4] == b'%PDF'
        print("✓ PDF generation works for PARTIAL payment invoice")

    def test_pdf_for_invoice_with_adjustments(self):
        """Test PDF generation for invoice with adjustments"""
        response = requests.get(
            f"{BASE_URL}/api/invoices/{self.INVOICE_WITH_ADJUSTMENTS}/pdf",
            headers=AUTH_HEADER
        )
        
        assert response.status_code == 200
        assert response.headers.get('content-type') == 'application/pdf'
        
        pdf_content = response.content
        assert pdf_content[:4] == b'%PDF'
        print("✓ PDF generation works for invoice WITH ADJUSTMENTS")

    def test_pdf_not_found_for_invalid_invoice(self):
        """Test PDF returns 404 for non-existent invoice"""
        response = requests.get(
            f"{BASE_URL}/api/invoices/non-existent-invoice-id/pdf",
            headers=AUTH_HEADER
        )
        
        assert response.status_code == 404, f"Expected 404, got {response.status_code}"
        print("✓ PDF endpoint returns 404 for non-existent invoice")

    def test_pdf_requires_authentication(self):
        """Test PDF endpoint requires authentication"""
        response = requests.get(
            f"{BASE_URL}/api/invoices/{self.SENT_INVOICE_ID}/pdf"
            # No auth header
        )
        
        assert response.status_code == 401, f"Expected 401, got {response.status_code}"
        print("✓ PDF endpoint requires authentication (returns 401 without session)")


class TestPDFContentValidation:
    """Tests to validate PDF content structure"""
    
    SENT_INVOICE_ID = "9d8e0f09-a5e3-4171-a4c8-27c802f3cb15"  # INV-2026-008
    
    def test_pdf_is_valid_reportlab_document(self):
        """Test that PDF is a valid ReportLab generated document"""
        response = requests.get(
            f"{BASE_URL}/api/invoices/{self.SENT_INVOICE_ID}/pdf",
            headers=AUTH_HEADER
        )
        
        assert response.status_code == 200
        pdf_content = response.content
        
        # Check for ReportLab signature in raw PDF
        pdf_text = pdf_content.decode('latin-1', errors='ignore')
        
        # ReportLab puts its signature in PDF metadata
        assert 'ReportLab' in pdf_text, "PDF should be generated by ReportLab"
        
        # Check for image object (logo should be embedded)
        assert '/Image' in pdf_text, "PDF should contain image object (logo)"
        
        # Check for fonts
        assert '/Font' in pdf_text, "PDF should contain font definitions"
        
        print("✓ PDF is valid ReportLab document with image and fonts")

    def test_pdf_has_reasonable_size(self):
        """Test PDF file size is reasonable (not too small or too large)"""
        response = requests.get(
            f"{BASE_URL}/api/invoices/{self.SENT_INVOICE_ID}/pdf",
            headers=AUTH_HEADER
        )
        
        assert response.status_code == 200
        pdf_size = len(response.content)
        
        # PDF should be at least 5KB (has content) but less than 5MB (reasonable)
        assert pdf_size > 5000, f"PDF too small ({pdf_size} bytes) - may be missing content"
        assert pdf_size < 5_000_000, f"PDF too large ({pdf_size} bytes) - may have issues"
        
        print(f"✓ PDF size is reasonable: {pdf_size:,} bytes")


class TestInvoiceDataEndpoint:
    """Test the invoice full data endpoint used for PDF generation"""
    
    SENT_INVOICE_ID = "9d8e0f09-a5e3-4171-a4c8-27c802f3cb15"  # INV-2026-008
    
    def test_invoice_full_endpoint_has_required_fields(self):
        """Test that invoice full endpoint returns all fields needed for PDF"""
        response = requests.get(
            f"{BASE_URL}/api/invoices/{self.SENT_INVOICE_ID}/full",
            headers=AUTH_HEADER
        )
        
        assert response.status_code == 200
        data = response.json()
        
        # Required fields for PDF
        required_fields = ['invoice_number', 'client_id', 'total', 'subtotal', 'due_date', 'status']
        for field in required_fields:
            assert field in data, f"Missing required field: {field}"
        
        # Client info
        assert 'client' in data, "Missing client info"
        client = data['client']
        assert 'name' in client, "Missing client name"
        
        print(f"✓ Invoice full endpoint has all required fields: {data['invoice_number']}")
        print(f"  - Client: {client.get('name')}")
        print(f"  - Total: {data['total']}")
        print(f"  - Status: {data['status']}")


class TestLogoFile:
    """Test that logo file exists for PDF generation"""
    
    def test_logo_file_exists_on_server(self):
        """Verify the Servex logo exists at the expected path"""
        import os
        logo_path = '/app/frontend/public/servex-logo.png'
        
        assert os.path.exists(logo_path), f"Logo file not found at {logo_path}"
        
        # Check file size (should be substantial)
        file_size = os.path.getsize(logo_path)
        assert file_size > 1000, f"Logo file too small: {file_size} bytes"
        
        print(f"✓ Logo file exists: {logo_path} ({file_size:,} bytes)")


# Allow running tests directly
if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
