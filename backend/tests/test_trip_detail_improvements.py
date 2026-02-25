"""
Trip Detail Improvements API Tests
Tests for new Trip Detail page features:
- Documents tab: Upload/List/Delete trip documents
- Trip Actions: Duplicate trip
- Invoice Review Workflow: Mark reviewed, Approve and send
- Team Members: List for @mentions
"""

import pytest
import requests
import os
import uuid
from datetime import datetime

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', 'https://multi-warehouse-qa.preview.emergentagent.com')
TRIP_ID = "863a0a83-e73c-4701-874a-22886c22d306"  # Trip T001


@pytest.fixture(scope="module")
def session():
    """Create authenticated session"""
    s = requests.Session()
    # Login to get session
    login_response = s.post(
        f"{BASE_URL}/api/auth/login",
        json={"email": "admin@servex.com", "password": "Servex2026!"}
    )
    assert login_response.status_code == 200, f"Login failed: {login_response.text}"
    print(f"✓ Logged in as admin@servex.com")
    return s


class TestTripDocumentsEndpoint:
    """Test /api/trips/{trip_id}/documents endpoint"""
    
    def test_get_documents_empty(self, session):
        """Get documents for trip (may be empty)"""
        response = session.get(f"{BASE_URL}/api/trips/{TRIP_ID}/documents")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()
        assert isinstance(data, list), "Response should be a list"
        print(f"✓ GET /api/trips/{TRIP_ID}/documents - returned {len(data)} documents")
    
    def test_upload_document(self, session):
        """Upload a test document"""
        import base64
        # Create a simple test file content (base64 encoded)
        test_content = base64.b64encode(b"Test document content for TEST_trip_detail").decode('utf-8')
        
        doc_data = {
            "file_name": "TEST_document.txt",
            "file_type": "text/plain",
            "file_data": test_content,
            "category": "Other"
        }
        
        response = session.post(
            f"{BASE_URL}/api/trips/{TRIP_ID}/documents",
            json=doc_data
        )
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()
        assert "id" in data, "Response should contain document id"
        
        # Store for cleanup
        TestTripDocumentsEndpoint.uploaded_doc_id = data["id"]
        print(f"✓ POST /api/trips/{TRIP_ID}/documents - uploaded document: {data['id']}")
    
    def test_get_documents_after_upload(self, session):
        """Verify document appears in list after upload"""
        response = session.get(f"{BASE_URL}/api/trips/{TRIP_ID}/documents")
        assert response.status_code == 200
        data = response.json()
        
        # Check if our uploaded doc is in the list
        doc_ids = [d["id"] for d in data]
        uploaded_id = getattr(TestTripDocumentsEndpoint, 'uploaded_doc_id', None)
        if uploaded_id:
            assert uploaded_id in doc_ids, "Uploaded document should be in list"
            
            # Check document structure
            doc = next(d for d in data if d["id"] == uploaded_id)
            assert "file_name" in doc, "Document should have file_name"
            assert "file_type" in doc, "Document should have file_type"
            assert "category" in doc, "Document should have category"
            assert "uploaded_by" in doc or "uploader_name" in doc, "Document should have uploader info"
            assert "uploaded_at" in doc, "Document should have uploaded_at"
            
            print(f"✓ Document structure verified: {doc['file_name']}")
    
    def test_download_document(self, session):
        """Download uploaded document"""
        doc_id = getattr(TestTripDocumentsEndpoint, 'uploaded_doc_id', None)
        if not doc_id:
            pytest.skip("No document uploaded")
        
        response = session.get(f"{BASE_URL}/api/trips/{TRIP_ID}/documents/{doc_id}/download")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()
        
        assert "file_name" in data, "Download response should have file_name"
        assert "file_type" in data, "Download response should have file_type"
        assert "file_data" in data, "Download response should have file_data"
        
        print(f"✓ GET /api/trips/{TRIP_ID}/documents/{doc_id}/download - success")
    
    def test_delete_document(self, session):
        """Delete uploaded document"""
        doc_id = getattr(TestTripDocumentsEndpoint, 'uploaded_doc_id', None)
        if not doc_id:
            pytest.skip("No document uploaded")
        
        response = session.delete(f"{BASE_URL}/api/trips/{TRIP_ID}/documents/{doc_id}")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        # Verify document is deleted
        response = session.get(f"{BASE_URL}/api/trips/{TRIP_ID}/documents")
        data = response.json()
        doc_ids = [d["id"] for d in data]
        assert doc_id not in doc_ids, "Deleted document should not be in list"
        
        print(f"✓ DELETE /api/trips/{TRIP_ID}/documents/{doc_id} - success")
    
    def test_get_documents_404_for_invalid_trip(self, session):
        """Documents endpoint returns 404 for non-existent trip"""
        response = session.get(f"{BASE_URL}/api/trips/invalid-trip-id/documents")
        assert response.status_code == 404
        print("✓ Returns 404 for non-existent trip")


class TestTripDuplicateEndpoint:
    """Test /api/trips/{trip_id}/duplicate endpoint"""
    
    def test_duplicate_trip(self, session):
        """Duplicate a trip"""
        response = session.post(f"{BASE_URL}/api/trips/{TRIP_ID}/duplicate")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()
        
        assert "id" in data, "Response should contain new trip id"
        assert "trip_number" in data, "Response should contain new trip_number"
        assert data["trip_number"] != "T001", "New trip should have different trip_number"
        
        # Store for cleanup
        TestTripDuplicateEndpoint.duplicated_trip_id = data["id"]
        print(f"✓ POST /api/trips/{TRIP_ID}/duplicate - created {data['trip_number']}")
    
    def test_verify_duplicated_trip(self, session):
        """Verify duplicated trip exists"""
        trip_id = getattr(TestTripDuplicateEndpoint, 'duplicated_trip_id', None)
        if not trip_id:
            pytest.skip("No duplicated trip")
        
        response = session.get(f"{BASE_URL}/api/trips/{trip_id}/summary")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()
        
        assert "trip" in data, "Response should have trip object"
        assert data["trip"]["status"] == "planning", "Duplicated trip should be in planning status"
        
        print(f"✓ Verified duplicated trip exists with status: {data['trip']['status']}")
    
    def test_cleanup_duplicated_trip(self, session):
        """Cleanup duplicated trip"""
        trip_id = getattr(TestTripDuplicateEndpoint, 'duplicated_trip_id', None)
        if not trip_id:
            pytest.skip("No duplicated trip")
        
        response = session.delete(f"{BASE_URL}/api/trips/{trip_id}")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        print(f"✓ Cleaned up duplicated trip")
    
    def test_duplicate_trip_404_for_invalid_trip(self, session):
        """Duplicate endpoint returns 404 for non-existent trip"""
        response = session.post(f"{BASE_URL}/api/trips/invalid-trip-id/duplicate")
        assert response.status_code == 404
        print("✓ Returns 404 for non-existent trip")


class TestInvoiceReviewWorkflow:
    """Test invoice review workflow endpoints"""
    
    @pytest.fixture(autouse=True)
    def setup_invoice(self, session):
        """Create a test invoice for review testing"""
        # First check if we have any existing clients
        clients_response = session.get(f"{BASE_URL}/api/clients")
        if clients_response.status_code != 200:
            pytest.skip("Cannot get clients")
        
        clients = clients_response.json()
        if len(clients) == 0:
            pytest.skip("No clients available")
        
        client_id = clients[0]["id"]
        
        # Create a test invoice
        invoice_data = {
            "client_id": client_id,
            "trip_id": TRIP_ID,
            "line_items": [
                {
                    "description": "TEST_ freight charge",
                    "quantity": 1,
                    "unit": "kg",
                    "rate": 10,
                    "amount": 100
                }
            ],
            "adjustments": [],
            "status": "draft"
        }
        
        response = session.post(f"{BASE_URL}/api/invoices", json=invoice_data)
        if response.status_code == 200:
            self.__class__.test_invoice_id = response.json()["id"]
            print(f"✓ Created test invoice: {self.__class__.test_invoice_id}")
        else:
            self.__class__.test_invoice_id = None
        
        yield
        
        # Cleanup
        if hasattr(self.__class__, 'test_invoice_id') and self.__class__.test_invoice_id:
            session.delete(f"{BASE_URL}/api/invoices/{self.__class__.test_invoice_id}")
    
    def test_mark_invoice_reviewed(self, session):
        """Mark invoice as reviewed"""
        invoice_id = getattr(self.__class__, 'test_invoice_id', None)
        if not invoice_id:
            pytest.skip("No test invoice created")
        
        response = session.post(f"{BASE_URL}/api/invoices/{invoice_id}/mark-reviewed")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        # Verify invoice has reviewed_at set
        invoice_response = session.get(f"{BASE_URL}/api/invoices/{invoice_id}")
        if invoice_response.status_code == 200:
            invoice = invoice_response.json()
            assert invoice.get("reviewed_at") is not None, "Invoice should have reviewed_at timestamp"
            print(f"✓ POST /api/invoices/{invoice_id}/mark-reviewed - success")
    
    def test_approve_and_send_invoice(self, session):
        """Approve and send an invoice"""
        invoice_id = getattr(self.__class__, 'test_invoice_id', None)
        if not invoice_id:
            pytest.skip("No test invoice created")
        
        # First mark as reviewed if not already
        session.post(f"{BASE_URL}/api/invoices/{invoice_id}/mark-reviewed")
        
        response = session.post(f"{BASE_URL}/api/invoices/{invoice_id}/approve-and-send")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        # Verify invoice has approved_at set
        invoice_response = session.get(f"{BASE_URL}/api/invoices/{invoice_id}")
        if invoice_response.status_code == 200:
            invoice = invoice_response.json()
            assert invoice.get("approved_at") is not None, "Invoice should have approved_at timestamp"
            assert invoice.get("status") == "sent", "Invoice status should be 'sent'"
            print(f"✓ POST /api/invoices/{invoice_id}/approve-and-send - success")
    
    def test_mark_reviewed_404_for_invalid_invoice(self, session):
        """Mark reviewed returns 404 for non-existent invoice"""
        response = session.post(f"{BASE_URL}/api/invoices/invalid-invoice-id/mark-reviewed")
        assert response.status_code == 404
        print("✓ Returns 404 for non-existent invoice")
    
    def test_approve_and_send_404_for_invalid_invoice(self, session):
        """Approve and send returns 404 for non-existent invoice"""
        response = session.post(f"{BASE_URL}/api/invoices/invalid-invoice-id/approve-and-send")
        assert response.status_code == 404
        print("✓ Returns 404 for non-existent invoice")


class TestTeamMembersEndpoint:
    """Test /api/team-members endpoint"""
    
    def test_list_team_members(self, session):
        """List team members for @mentions"""
        response = session.get(f"{BASE_URL}/api/team-members")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()
        
        assert isinstance(data, list), "Response should be a list"
        
        if len(data) > 0:
            member = data[0]
            assert "id" in member, "Team member should have id"
            assert "name" in member, "Team member should have name"
            assert "email" in member, "Team member should have email"
            
            print(f"✓ GET /api/team-members - returned {len(data)} team members")
            print(f"  Sample member: {member['name']} ({member['email']})")
        else:
            print("✓ GET /api/team-members - returned empty list (no active users)")


class TestInvoiceComments:
    """Test invoice comments endpoint for @mentions"""
    
    @pytest.fixture(autouse=True)
    def setup_invoice(self, session):
        """Create a test invoice for comment testing"""
        clients_response = session.get(f"{BASE_URL}/api/clients")
        if clients_response.status_code != 200:
            pytest.skip("Cannot get clients")
        
        clients = clients_response.json()
        if len(clients) == 0:
            pytest.skip("No clients available")
        
        client_id = clients[0]["id"]
        
        invoice_data = {
            "client_id": client_id,
            "trip_id": TRIP_ID,
            "line_items": [{"description": "TEST_ comment test", "quantity": 1, "unit": "kg", "rate": 10, "amount": 100}],
            "adjustments": [],
            "status": "draft"
        }
        
        response = session.post(f"{BASE_URL}/api/invoices", json=invoice_data)
        if response.status_code == 200:
            self.__class__.test_invoice_id = response.json()["id"]
        else:
            self.__class__.test_invoice_id = None
        
        yield
        
        if hasattr(self.__class__, 'test_invoice_id') and self.__class__.test_invoice_id:
            session.delete(f"{BASE_URL}/api/invoices/{self.__class__.test_invoice_id}")
    
    def test_add_comment_to_invoice(self, session):
        """Add a comment to an invoice"""
        invoice_id = getattr(self.__class__, 'test_invoice_id', None)
        if not invoice_id:
            pytest.skip("No test invoice created")
        
        comment_data = {
            "content": "TEST_ This is a test comment for the invoice",
            "mentioned_user_ids": []
        }
        
        response = session.post(
            f"{BASE_URL}/api/invoices/{invoice_id}/comments",
            json=comment_data
        )
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()
        assert "id" in data, "Response should contain comment id"
        
        print(f"✓ POST /api/invoices/{invoice_id}/comments - success")
    
    def test_list_invoice_comments(self, session):
        """List comments on an invoice"""
        invoice_id = getattr(self.__class__, 'test_invoice_id', None)
        if not invoice_id:
            pytest.skip("No test invoice created")
        
        response = session.get(f"{BASE_URL}/api/invoices/{invoice_id}/comments")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()
        
        assert isinstance(data, list), "Response should be a list"
        print(f"✓ GET /api/invoices/{invoice_id}/comments - returned {len(data)} comments")
    
    def test_add_comment_with_mentions(self, session):
        """Add a comment with @mentions"""
        invoice_id = getattr(self.__class__, 'test_invoice_id', None)
        if not invoice_id:
            pytest.skip("No test invoice created")
        
        # Get team members to mention
        team_response = session.get(f"{BASE_URL}/api/team-members")
        if team_response.status_code != 200:
            pytest.skip("Cannot get team members")
        
        team_members = team_response.json()
        mention_ids = [m["id"] for m in team_members[:1]] if team_members else []
        
        comment_data = {
            "content": "TEST_ Mentioning team member for review @",
            "mentioned_user_ids": mention_ids
        }
        
        response = session.post(
            f"{BASE_URL}/api/invoices/{invoice_id}/comments",
            json=comment_data
        )
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        print(f"✓ Added comment with {len(mention_ids)} mentions")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
