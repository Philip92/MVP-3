"""
Backend tests for Parcel Intake Bug Fix Verification
Tests the specific bugs that were fixed:
1. Shipment creation now works (was failing with NameError for create_audit_log)
2. Multiple parcels can be saved at once without duplicates
3. Photo uploads to parcels work correctly

Bug Fix: Added missing imports in /app/backend/routes/shipment_routes.py line 11:
- create_audit_log from models.schemas
- AuditAction from models.enums
"""
import pytest
import requests
import os
import time

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

# Session variables
SESSION_TOKEN = None
TENANT_ID = None
USER_ID = None
CLIENT_ID = None


@pytest.fixture(scope="module", autouse=True)
def setup_test_session():
    """Create test session and client for testing"""
    global SESSION_TOKEN, TENANT_ID, USER_ID, CLIENT_ID
    
    import subprocess
    timestamp = str(int(time.time() * 1000))
    
    result = subprocess.run([
        'mongosh', '--quiet', '--eval', f'''
        use('test_database');
        var userId = 'bugfix-user-{timestamp}';
        var tenantId = 'bugfix-tenant-{timestamp}';
        var sessionToken = 'bugfix_session_{timestamp}';
        var clientId = 'bugfix-client-{timestamp}';
        
        // Create tenant
        db.tenants.insertOne({{
          id: tenantId,
          subdomain: 'bugfixtest{timestamp}',
          company_name: 'Bug Fix Test Company',
          primary_color: '#6B633C',
          created_at: new Date().toISOString()
        }});
        
        // Create user
        db.users.insertOne({{
          id: userId,
          tenant_id: tenantId,
          name: 'Bug Fix Test User',
          email: 'bugfix.test.{timestamp}@example.com',
          role: 'owner',
          status: 'active',
          created_at: new Date().toISOString()
        }});
        
        // Create session
        db.user_sessions.insertOne({{
          user_id: userId,
          session_token: sessionToken,
          expires_at: new Date(Date.now() + 7*24*60*60*1000).toISOString(),
          created_at: new Date().toISOString()
        }});
        
        // Create test client
        db.clients.insertOne({{
          id: clientId,
          tenant_id: tenantId,
          name: 'BUGFIX_TestClient',
          phone: '+27123456789',
          status: 'active',
          created_at: new Date().toISOString()
        }});
        
        print('SESSION_TOKEN=' + sessionToken);
        print('USER_ID=' + userId);
        print('TENANT_ID=' + tenantId);
        print('CLIENT_ID=' + clientId);
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
        elif line.startswith('CLIENT_ID='):
            CLIENT_ID = line.split('=')[1]
    
    assert SESSION_TOKEN, f"Failed to create test session: {output}"
    print(f"\nCreated test session: {SESSION_TOKEN}")
    print(f"Created test client: {CLIENT_ID}")
    
    yield
    
    # Cleanup
    subprocess.run([
        'mongosh', '--quiet', '--eval', f'''
        use('test_database');
        db.users.deleteMany({{email: /bugfix\\.test\\.{timestamp}/}});
        db.user_sessions.deleteMany({{session_token: /bugfix_session_{timestamp}/}});
        db.tenants.deleteMany({{subdomain: /bugfixtest{timestamp}/}});
        db.clients.deleteMany({{name: /BUGFIX_/}});
        db.shipments.deleteMany({{description: /BUGFIX_/}});
        db.shipment_pieces.deleteMany({{shipment_id: /bugfix/}});
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


class TestShipmentCreationBugFix:
    """
    Test that shipment creation works after the bug fix.
    Bug: NameError: name 'create_audit_log' is not defined
    Fix: Added create_audit_log to imports from models.schemas
    """
    
    def test_create_single_shipment_success(self, api_client):
        """POST /api/shipments - Create single shipment (tests audit_log fix)"""
        shipment_data = {
            "client_id": CLIENT_ID,
            "description": "BUGFIX_SingleShipment",
            "destination": "Harare",
            "total_pieces": 1,
            "total_weight": 5.0
        }
        response = api_client.post(f"{BASE_URL}/api/shipments", json=shipment_data)
        
        # The bug would cause 500 error with NameError
        assert response.status_code == 200, f"Shipment creation failed: {response.text}"
        
        data = response.json()
        assert "id" in data, "Response should contain shipment ID"
        assert data["description"] == "BUGFIX_SingleShipment"
        assert data["status"] == "warehouse"
        assert data["client_id"] == CLIENT_ID
        
        print(f"✓ Shipment created successfully: {data['id']}")
        
        # Cleanup
        api_client.delete(f"{BASE_URL}/api/shipments/{data['id']}")
    
    def test_create_shipment_with_trip_assignment(self, api_client):
        """POST /api/shipments with trip_id - Tests status='staged' path"""
        # First create a trip
        trip_data = {
            "origin": "Johannesburg",
            "route": ["Johannesburg", "Harare"],
            "departure_date": "2026-02-20"
        }
        trip_response = api_client.post(f"{BASE_URL}/api/trips", json=trip_data)
        
        if trip_response.status_code != 200:
            pytest.skip("Could not create trip for test")
        
        trip_id = trip_response.json()["id"]
        
        # Create shipment assigned to trip
        shipment_data = {
            "client_id": CLIENT_ID,
            "description": "BUGFIX_TripAssigned",
            "destination": "Harare",
            "total_pieces": 1,
            "total_weight": 10.0,
            "trip_id": trip_id
        }
        response = api_client.post(f"{BASE_URL}/api/shipments", json=shipment_data)
        
        assert response.status_code == 200, f"Shipment creation failed: {response.text}"
        
        data = response.json()
        assert data["trip_id"] == trip_id
        assert data["status"] == "staged", "Shipment with trip should be 'staged'"
        
        print(f"✓ Shipment with trip assignment created: {data['id']}")
        
        # Cleanup
        api_client.delete(f"{BASE_URL}/api/shipments/{data['id']}")
        api_client.delete(f"{BASE_URL}/api/trips/{trip_id}")


class TestMultipleParcelSave:
    """
    Test that multiple parcels can be saved without duplicates.
    Bug: Only first parcel was being saved, rest failed
    """
    
    def test_create_multiple_shipments_no_duplicates(self, api_client):
        """Create 3 shipments and verify no duplicates"""
        created_ids = []
        
        for i in range(3):
            shipment_data = {
                "client_id": CLIENT_ID,
                "description": f"BUGFIX_MultiParcel{i+1}",
                "destination": "Lusaka",
                "total_pieces": 1,
                "total_weight": float(i + 1)
            }
            response = api_client.post(f"{BASE_URL}/api/shipments", json=shipment_data)
            
            assert response.status_code == 200, f"Shipment {i+1} creation failed: {response.text}"
            
            data = response.json()
            created_ids.append(data["id"])
            print(f"✓ Created parcel {i+1}: {data['id']}")
        
        # Verify all 3 are unique
        assert len(created_ids) == 3, "Should have created 3 shipments"
        assert len(set(created_ids)) == 3, "All shipment IDs should be unique (no duplicates)"
        
        # Verify all exist in database
        for ship_id in created_ids:
            get_response = api_client.get(f"{BASE_URL}/api/shipments/{ship_id}")
            assert get_response.status_code == 200, f"Shipment {ship_id} not found in database"
        
        print(f"✓ All 3 parcels saved without duplicates")
        
        # Cleanup
        for ship_id in created_ids:
            api_client.delete(f"{BASE_URL}/api/shipments/{ship_id}")


class TestPieceCreation:
    """Test piece creation with barcode generation"""
    
    def test_create_piece_with_dimensions(self, api_client):
        """POST /api/shipments/{id}/pieces - Create piece with dimensions"""
        # Create shipment first
        shipment_data = {
            "client_id": CLIENT_ID,
            "description": "BUGFIX_PieceTest",
            "destination": "Maputo",
            "total_pieces": 1,
            "total_weight": 5.0
        }
        ship_response = api_client.post(f"{BASE_URL}/api/shipments", json=shipment_data)
        assert ship_response.status_code == 200
        shipment_id = ship_response.json()["id"]
        
        # Create piece
        piece_data = {
            "piece_number": 1,
            "weight": 5.0,
            "length_cm": 30,
            "width_cm": 20,
            "height_cm": 15
        }
        piece_response = api_client.post(
            f"{BASE_URL}/api/shipments/{shipment_id}/pieces",
            json=piece_data
        )
        
        assert piece_response.status_code == 200, f"Piece creation failed: {piece_response.text}"
        
        piece = piece_response.json()
        assert "id" in piece
        assert "barcode" in piece
        assert piece["barcode"].startswith("TEMP-"), "Barcode should start with TEMP- when no trip"
        assert piece["weight"] == 5.0
        assert piece["length_cm"] == 30.0
        
        print(f"✓ Piece created with barcode: {piece['barcode']}")
        
        # Cleanup
        api_client.delete(f"{BASE_URL}/api/shipments/{shipment_id}")


class TestPhotoUpload:
    """Test photo upload to parcel pieces"""
    
    def test_upload_photo_to_parcel(self, api_client):
        """POST /api/warehouse/parcels/{id}/photos - Upload photo"""
        # Create shipment
        shipment_data = {
            "client_id": CLIENT_ID,
            "description": "BUGFIX_PhotoTest",
            "destination": "Gaborone",
            "total_pieces": 1,
            "total_weight": 3.0
        }
        ship_response = api_client.post(f"{BASE_URL}/api/shipments", json=shipment_data)
        assert ship_response.status_code == 200
        shipment_id = ship_response.json()["id"]
        
        # Create piece
        piece_response = api_client.post(
            f"{BASE_URL}/api/shipments/{shipment_id}/pieces",
            json={"piece_number": 1, "weight": 3.0}
        )
        assert piece_response.status_code == 200
        piece_id = piece_response.json()["id"]
        
        # Upload photo (base64 encoded 1x1 red pixel PNG)
        import base64
        photo_data = base64.b64decode('iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8z8DwHwAFBQIAX8jx0gAAAABJRU5ErkJggg==')
        
        # Create multipart form data
        session = requests.Session()
        session.headers.update({"Authorization": f"Bearer {SESSION_TOKEN}"})
        
        files = {'file': ('test.png', photo_data, 'image/png')}
        photo_response = session.post(
            f"{BASE_URL}/api/warehouse/parcels/{shipment_id}/photos",
            files=files
        )
        
        assert photo_response.status_code == 200, f"Photo upload failed: {photo_response.text}"
        
        photo_result = photo_response.json()
        assert photo_result["message"] == "Photo uploaded successfully"
        assert photo_result["piece_id"] == piece_id
        assert "photo_url" in photo_result
        assert photo_result["photo_url"].startswith("data:image/png;base64,")
        
        print(f"✓ Photo uploaded successfully to piece: {piece_id}")
        
        # Verify photo is stored
        detail_response = api_client.get(f"{BASE_URL}/api/warehouse/parcels/{shipment_id}")
        assert detail_response.status_code == 200
        detail = detail_response.json()
        
        pieces = detail.get("pieces", [])
        assert len(pieces) == 1
        assert pieces[0]["photo_url"] is not None
        assert pieces[0]["photo_url"].startswith("data:image")
        
        print(f"✓ Photo verified in parcel detail")
        
        # Cleanup
        api_client.delete(f"{BASE_URL}/api/shipments/{shipment_id}")


class TestAuditLogCreation:
    """Verify audit logs are created for shipment operations"""
    
    def test_shipment_creates_audit_log(self, api_client):
        """Verify audit log is created when shipment is created"""
        import subprocess
        
        # Create shipment
        shipment_data = {
            "client_id": CLIENT_ID,
            "description": "BUGFIX_AuditLogTest",
            "destination": "Windhoek",
            "total_pieces": 1,
            "total_weight": 7.0
        }
        response = api_client.post(f"{BASE_URL}/api/shipments", json=shipment_data)
        assert response.status_code == 200
        shipment_id = response.json()["id"]
        
        # Check audit log was created
        result = subprocess.run([
            'mongosh', '--quiet', '--eval', f'''
            use('test_database');
            var logs = db.audit_logs.find({{
                record_id: "{shipment_id}",
                table_name: "shipments",
                action: "create"
            }}).toArray();
            print("AUDIT_LOG_COUNT=" + logs.length);
            '''
        ], capture_output=True, text=True)
        
        audit_count = 0
        for line in result.stdout.split('\n'):
            if line.startswith('AUDIT_LOG_COUNT='):
                audit_count = int(line.split('=')[1])
        
        assert audit_count >= 1, f"Expected audit log to be created, found {audit_count}"
        print(f"✓ Audit log created for shipment: {shipment_id}")
        
        # Cleanup
        api_client.delete(f"{BASE_URL}/api/shipments/{shipment_id}")


class TestIntegrationFlow:
    """End-to-end integration test simulating Parcel Intake page flow"""
    
    def test_full_parcel_intake_flow(self, api_client):
        """
        Simulate the full Parcel Intake page flow:
        1. Select client (already have CLIENT_ID)
        2. Fill 2 parcels with details
        3. Save all parcels
        4. Verify in warehouse
        """
        print("\n=== Starting Full Parcel Intake Flow Test ===")
        
        # Step 1: Create 2 parcels (simulating Save All)
        parcels = [
            {
                "client_id": CLIENT_ID,
                "description": "BUGFIX_FlowTest1 - Electronics",
                "destination": "Harare",
                "total_pieces": 1,
                "total_weight": 5.5,
                "sender": "Test Sender 1"
            },
            {
                "client_id": CLIENT_ID,
                "description": "BUGFIX_FlowTest2 - Clothing",
                "destination": "Harare",
                "total_pieces": 2,
                "total_weight": 3.0,
                "sender": "Test Sender 2"
            }
        ]
        
        created_shipments = []
        for i, parcel in enumerate(parcels):
            response = api_client.post(f"{BASE_URL}/api/shipments", json=parcel)
            assert response.status_code == 200, f"Failed to create parcel {i+1}: {response.text}"
            
            shipment = response.json()
            created_shipments.append(shipment)
            
            # Create piece for each shipment
            piece_response = api_client.post(
                f"{BASE_URL}/api/shipments/{shipment['id']}/pieces",
                json={
                    "piece_number": 1,
                    "weight": parcel["total_weight"],
                    "length_cm": 30,
                    "width_cm": 20,
                    "height_cm": 10
                }
            )
            assert piece_response.status_code == 200
            print(f"✓ Created parcel {i+1}: {shipment['id']}")
        
        # Step 2: Verify both appear in warehouse
        warehouse_response = api_client.get(
            f"{BASE_URL}/api/warehouse/parcels?search=BUGFIX_FlowTest"
        )
        assert warehouse_response.status_code == 200
        
        warehouse_data = warehouse_response.json()
        assert warehouse_data["total"] == 2, f"Expected 2 parcels in warehouse, found {warehouse_data['total']}"
        
        # Verify descriptions
        descriptions = [item["description"] for item in warehouse_data["items"]]
        assert "BUGFIX_FlowTest1 - Electronics" in descriptions
        assert "BUGFIX_FlowTest2 - Clothing" in descriptions
        
        print(f"✓ Both parcels verified in warehouse")
        
        # Cleanup
        for shipment in created_shipments:
            api_client.delete(f"{BASE_URL}/api/shipments/{shipment['id']}")
        
        print("=== Full Parcel Intake Flow Test Complete ===\n")
