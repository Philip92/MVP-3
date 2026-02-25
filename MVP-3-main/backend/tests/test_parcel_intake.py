"""
Backend tests for Parcel Intake feature
Tests: shipment creation, piece creation, client autocomplete, inline client creation
"""
import pytest
import requests
import os
import time

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

# Test session token will be created in setup
SESSION_TOKEN = None
TENANT_ID = None
USER_ID = None


@pytest.fixture(scope="module", autouse=True)
def setup_test_session():
    """Create test session in MongoDB for authenticated testing"""
    global SESSION_TOKEN, TENANT_ID, USER_ID
    
    import subprocess
    timestamp = str(int(time.time() * 1000))
    
    result = subprocess.run([
        'mongosh', '--quiet', '--eval', f'''
        use('test_database');
        var userId = 'test-parcel-user-{timestamp}';
        var tenantId = 'test-parcel-tenant-{timestamp}';
        var sessionToken = 'test_parcel_session_{timestamp}';
        
        db.tenants.insertOne({{
          id: tenantId,
          subdomain: 'testparcel{timestamp}',
          company_name: 'Test Parcel Company',
          primary_color: '#27AE60',
          created_at: new Date().toISOString()
        }});
        
        db.users.insertOne({{
          id: userId,
          tenant_id: tenantId,
          name: 'Test Parcel User',
          email: 'test.parcel.{timestamp}@example.com',
          role: 'owner',
          status: 'active',
          picture: 'https://via.placeholder.com/150',
          created_at: new Date().toISOString()
        }});
        
        db.user_sessions.insertOne({{
          user_id: userId,
          session_token: sessionToken,
          expires_at: new Date(Date.now() + 7*24*60*60*1000).toISOString(),
          created_at: new Date().toISOString()
        }});
        
        print('SESSION_TOKEN=' + sessionToken);
        print('USER_ID=' + userId);
        print('TENANT_ID=' + tenantId);
        '''
    ], capture_output=True, text=True)
    
    output = result.stdout
    for line in output.split('\n'):
        if line.startswith('SESSION_TOKEN='):
            SESSION_TOKEN = line.split('=')[1]
        elif line.startswith('USER_ID='):
            USER_ID = line.split('=')[1]
        elif line.startswith('TENANT_ID='):
            TENANT_ID = line.split('=')[1]
    
    assert SESSION_TOKEN, f"Failed to create test session: {output}"
    print(f"\nCreated test session: {SESSION_TOKEN}")
    
    yield
    
    # Cleanup
    subprocess.run([
        'mongosh', '--quiet', '--eval', f'''
        use('test_database');
        db.users.deleteMany({{email: /test\\.parcel\\.{timestamp}/}});
        db.user_sessions.deleteMany({{session_token: /test_parcel_session_{timestamp}/}});
        db.tenants.deleteMany({{subdomain: /testparcel{timestamp}/}});
        db.clients.deleteMany({{name: /TEST_/}});
        db.shipments.deleteMany({{description: /TEST_/}});
        '''
    ], capture_output=True, text=True)


@pytest.fixture
def api_client():
    """Authenticated requests session"""
    session = requests.Session()
    session.headers.update({
        "Content-Type": "application/json",
        "Authorization": f"Bearer {SESSION_TOKEN}"
    })
    return session


class TestClientAPIs:
    """Test client APIs used by Parcel Intake for autocomplete"""
    
    def test_list_clients_empty_initially(self, api_client):
        """GET /api/clients - Should return empty list for new tenant"""
        response = api_client.get(f"{BASE_URL}/api/clients")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        print(f"Clients list: {len(data)} items")
    
    def test_create_client_inline(self, api_client):
        """POST /api/clients - Create client inline for autocomplete"""
        client_data = {
            "name": "TEST_InlineClient",
            "phone": "+27111222333"
        }
        response = api_client.post(f"{BASE_URL}/api/clients", json=client_data)
        
        assert response.status_code == 200, f"Response: {response.text}"
        data = response.json()
        
        # Verify response structure
        assert "id" in data
        assert data["name"] == "TEST_InlineClient"
        assert data["phone"] == "+27111222333"
        assert data["status"] == "active"
        print(f"Created client: {data['id']}")
        
        # Verify persistence
        get_response = api_client.get(f"{BASE_URL}/api/clients/{data['id']}")
        assert get_response.status_code == 200
        fetched = get_response.json()
        assert fetched["name"] == "TEST_InlineClient"
    
    def test_create_client_with_full_details(self, api_client):
        """POST /api/clients - Create client with email and all fields"""
        client_data = {
            "name": "TEST_FullClient",
            "phone": "+27444555666",
            "email": "test@example.com",
            "whatsapp": "+27444555666"
        }
        response = api_client.post(f"{BASE_URL}/api/clients", json=client_data)
        
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "TEST_FullClient"
        assert data["email"] == "test@example.com"
    
    def test_list_clients_after_creation(self, api_client):
        """GET /api/clients - Should return created clients"""
        response = api_client.get(f"{BASE_URL}/api/clients")
        assert response.status_code == 200
        data = response.json()
        
        # Filter test clients
        test_clients = [c for c in data if c["name"].startswith("TEST_")]
        assert len(test_clients) >= 2, f"Expected at least 2 test clients, found {len(test_clients)}"
        print(f"Found {len(test_clients)} test clients")


class TestShipmentAPIs:
    """Test shipment creation APIs used by Parcel Intake"""
    
    @pytest.fixture
    def test_client(self, api_client):
        """Create a test client for shipment tests"""
        response = api_client.post(f"{BASE_URL}/api/clients", json={
            "name": "TEST_ShipmentClient",
            "phone": "+27777888999"
        })
        return response.json()
    
    def test_create_shipment_with_required_fields(self, api_client, test_client):
        """POST /api/shipments - Create shipment with required fields"""
        shipment_data = {
            "client_id": test_client["id"],
            "description": "TEST_Basic parcel shipment",
            "destination": "Kenya",
            "total_pieces": 1,
            "total_weight": 5.0
        }
        response = api_client.post(f"{BASE_URL}/api/shipments", json=shipment_data)
        
        assert response.status_code == 200, f"Response: {response.text}"
        data = response.json()
        
        # Verify response structure
        assert "id" in data
        assert data["description"] == "TEST_Basic parcel shipment"
        assert data["destination"] == "Kenya"
        assert data["total_pieces"] == 1
        assert data["total_weight"] == 5.0
        assert data["status"] == "warehouse"
        assert data["client_id"] == test_client["id"]
        print(f"Created shipment: {data['id']}")
        return data
    
    def test_create_shipment_with_cbm(self, api_client, test_client):
        """POST /api/shipments - Create shipment with CBM calculation"""
        shipment_data = {
            "client_id": test_client["id"],
            "description": "TEST_Shipment with dimensions",
            "destination": "Tanzania",
            "total_pieces": 2,
            "total_weight": 15.5,
            "total_cbm": 0.025
        }
        response = api_client.post(f"{BASE_URL}/api/shipments", json=shipment_data)
        
        assert response.status_code == 200
        data = response.json()
        assert data["total_cbm"] == 0.025
        assert data["total_pieces"] == 2
    
    def test_create_shipment_invalid_client(self, api_client):
        """POST /api/shipments - Should fail with non-existent client"""
        shipment_data = {
            "client_id": "non-existent-client-id",
            "description": "TEST_Invalid shipment",
            "destination": "Kenya",
            "total_pieces": 1,
            "total_weight": 5.0
        }
        response = api_client.post(f"{BASE_URL}/api/shipments", json=shipment_data)
        
        assert response.status_code == 404
        assert "Client not found" in response.json().get("detail", "")


class TestShipmentPieceAPIs:
    """Test shipment piece creation APIs"""
    
    @pytest.fixture
    def test_shipment(self, api_client):
        """Create test client and shipment for piece tests"""
        # Create client
        client_response = api_client.post(f"{BASE_URL}/api/clients", json={
            "name": "TEST_PieceClient",
            "phone": "+27999000111"
        })
        client = client_response.json()
        
        # Create shipment
        shipment_response = api_client.post(f"{BASE_URL}/api/shipments", json={
            "client_id": client["id"],
            "description": "TEST_Multi-piece shipment",
            "destination": "Zambia",
            "total_pieces": 3,
            "total_weight": 25.0
        })
        return shipment_response.json()
    
    def test_create_piece_with_dimensions(self, api_client, test_shipment):
        """POST /api/shipments/{id}/pieces - Create piece with dimensions"""
        piece_data = {
            "piece_number": 1,
            "weight": 8.0,
            "length_cm": 30,
            "width_cm": 25,
            "height_cm": 40
        }
        response = api_client.post(
            f"{BASE_URL}/api/shipments/{test_shipment['id']}/pieces",
            json=piece_data
        )
        
        assert response.status_code == 200, f"Response: {response.text}"
        data = response.json()
        
        # Verify response structure
        assert "id" in data
        assert "barcode" in data
        assert data["piece_number"] == 1
        assert data["weight"] == 8.0
        assert data["length_cm"] == 30.0
        assert data["width_cm"] == 25.0
        assert data["height_cm"] == 40.0
        assert data["shipment_id"] == test_shipment["id"]
        assert data["barcode"].startswith("TEMP-")  # No trip assigned
        print(f"Created piece with barcode: {data['barcode']}")
    
    def test_create_multiple_pieces(self, api_client, test_shipment):
        """POST /api/shipments/{id}/pieces - Create multiple pieces"""
        # Create piece 1
        response1 = api_client.post(
            f"{BASE_URL}/api/shipments/{test_shipment['id']}/pieces",
            json={"piece_number": 1, "weight": 10.0}
        )
        assert response1.status_code == 200
        
        # Create piece 2
        response2 = api_client.post(
            f"{BASE_URL}/api/shipments/{test_shipment['id']}/pieces",
            json={"piece_number": 2, "weight": 8.0, "length_cm": 20, "width_cm": 15, "height_cm": 30}
        )
        assert response2.status_code == 200
        
        # Create piece 3
        response3 = api_client.post(
            f"{BASE_URL}/api/shipments/{test_shipment['id']}/pieces",
            json={"piece_number": 3, "weight": 7.0}
        )
        assert response3.status_code == 200
        
        # Verify all pieces via GET
        shipment_response = api_client.get(f"{BASE_URL}/api/shipments/{test_shipment['id']}")
        assert shipment_response.status_code == 200
        shipment_data = shipment_response.json()
        
        # Should have 3 pieces + any from previous test
        pieces = shipment_data.get("pieces", [])
        piece_nums = [p["piece_number"] for p in pieces]
        assert 1 in piece_nums
        assert 2 in piece_nums
        assert 3 in piece_nums
        print(f"Shipment has {len(pieces)} pieces")
    
    def test_create_piece_invalid_shipment(self, api_client):
        """POST /api/shipments/{id}/pieces - Should fail with invalid shipment"""
        response = api_client.post(
            f"{BASE_URL}/api/shipments/non-existent-shipment/pieces",
            json={"piece_number": 1, "weight": 5.0}
        )
        
        assert response.status_code == 404
        assert "Shipment not found" in response.json().get("detail", "")
    
    def test_barcode_generation(self, api_client, test_shipment):
        """Verify barcode is generated for pieces"""
        response = api_client.post(
            f"{BASE_URL}/api/shipments/{test_shipment['id']}/pieces",
            json={"piece_number": 99, "weight": 1.0}
        )
        
        assert response.status_code == 200
        data = response.json()
        
        # Barcode should be TEMP-XXXXXX format (no trip)
        assert data["barcode"].startswith("TEMP-")
        assert len(data["barcode"]) == 11  # TEMP-XXXXXX


class TestShipmentCRUD:
    """Test full CRUD operations for shipments"""
    
    @pytest.fixture
    def test_client_and_shipment(self, api_client):
        """Create test client and shipment"""
        client = api_client.post(f"{BASE_URL}/api/clients", json={
            "name": "TEST_CRUDClient",
            "phone": "+27111222333"
        }).json()
        
        shipment = api_client.post(f"{BASE_URL}/api/shipments", json={
            "client_id": client["id"],
            "description": "TEST_CRUD shipment",
            "destination": "Zimbabwe",
            "total_pieces": 1,
            "total_weight": 10.0
        }).json()
        
        return {"client": client, "shipment": shipment}
    
    def test_get_shipment_by_id(self, api_client, test_client_and_shipment):
        """GET /api/shipments/{id} - Get single shipment"""
        shipment = test_client_and_shipment["shipment"]
        response = api_client.get(f"{BASE_URL}/api/shipments/{shipment['id']}")
        
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == shipment["id"]
        assert "pieces" in data  # Should include pieces array
    
    def test_list_shipments(self, api_client):
        """GET /api/shipments - List all shipments"""
        response = api_client.get(f"{BASE_URL}/api/shipments")
        
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        print(f"Found {len(data)} shipments")
    
    def test_list_shipments_by_status(self, api_client):
        """GET /api/shipments?status=warehouse - Filter by status"""
        response = api_client.get(f"{BASE_URL}/api/shipments?status=warehouse")
        
        assert response.status_code == 200
        data = response.json()
        for shipment in data:
            assert shipment["status"] == "warehouse"
    
    def test_update_shipment(self, api_client, test_client_and_shipment):
        """PUT /api/shipments/{id} - Update shipment"""
        shipment = test_client_and_shipment["shipment"]
        
        response = api_client.put(
            f"{BASE_URL}/api/shipments/{shipment['id']}",
            json={"description": "TEST_Updated description", "total_weight": 12.5}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["description"] == "TEST_Updated description"
        assert data["total_weight"] == 12.5
    
    def test_delete_shipment(self, api_client, test_client_and_shipment):
        """DELETE /api/shipments/{id} - Delete shipment"""
        shipment = test_client_and_shipment["shipment"]
        
        response = api_client.delete(f"{BASE_URL}/api/shipments/{shipment['id']}")
        
        assert response.status_code == 200
        assert "deleted" in response.json().get("message", "").lower()
        
        # Verify deletion
        get_response = api_client.get(f"{BASE_URL}/api/shipments/{shipment['id']}")
        assert get_response.status_code == 404


class TestAuthRequired:
    """Verify endpoints require authentication"""
    
    def test_clients_requires_auth(self):
        """GET /api/clients without auth should fail"""
        response = requests.get(f"{BASE_URL}/api/clients")
        assert response.status_code == 401
    
    def test_shipments_requires_auth(self):
        """POST /api/shipments without auth should fail"""
        response = requests.post(f"{BASE_URL}/api/shipments", json={
            "client_id": "test",
            "description": "test",
            "destination": "test",
            "total_pieces": 1,
            "total_weight": 1.0
        })
        assert response.status_code == 401
