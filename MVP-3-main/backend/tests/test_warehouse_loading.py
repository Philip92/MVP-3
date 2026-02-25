"""
Backend tests for warehouse management, loading/unloading workflows, and parcel tracking.
Tests iteration 30 features:
- Parcel verification endpoint (PUT /api/shipments/{id}/verify)
- Bulk collect endpoint (PUT /api/warehouse/parcels/bulk-collect)  
- Warehouse filters with client dropdown
- Trip status progression
- Loading/Unloading workflows
"""
import pytest
import requests
import os
import uuid

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', 'https://multi-warehouse-qa.preview.emergentagent.com').rstrip('/')

# Test credentials
TEST_EMAIL = "admin@servex.com"
TEST_PASSWORD = "Servex2026!"


class TestWarehouseLoadingFeatures:
    """Comprehensive tests for new warehouse and loading features"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Setup session and create test data"""
        self.session = requests.Session()
        self.session.headers.update({"Content-Type": "application/json"})
        
        # Login
        login_response = self.session.post(f"{BASE_URL}/api/auth/login", json={
            "email": TEST_EMAIL,
            "password": TEST_PASSWORD
        })
        
        if login_response.status_code != 200:
            pytest.skip(f"Failed to login: {login_response.status_code}")
        
        self.user = login_response.json()
        self.created_ids = {"clients": [], "trips": [], "shipments": []}
        yield
        
        # Cleanup after each test
        for shipment_id in self.created_ids["shipments"]:
            try:
                self.session.delete(f"{BASE_URL}/api/shipments/{shipment_id}")
            except:
                pass
        for trip_id in self.created_ids["trips"]:
            try:
                self.session.delete(f"{BASE_URL}/api/trips/{trip_id}")
            except:
                pass
        for client_id in self.created_ids["clients"]:
            try:
                self.session.delete(f"{BASE_URL}/api/clients/{client_id}")
            except:
                pass
    
    # ============ AUTHENTICATION ============
    
    def test_01_login_success(self):
        """Test successful login"""
        session = requests.Session()
        response = session.post(f"{BASE_URL}/api/auth/login", json={
            "email": TEST_EMAIL,
            "password": TEST_PASSWORD
        })
        assert response.status_code == 200
        data = response.json()
        assert "id" in data
        assert "email" in data
        print(f"✓ Login successful for {TEST_EMAIL}")
    
    # ============ SHIPMENT VERIFICATION ============
    
    def test_02_verify_shipment_endpoint_exists(self):
        """Test shipment verification endpoint works"""
        # Create test client
        client = self._create_test_client()
        
        # Create test shipment
        shipment = self._create_test_shipment(client["id"])
        
        # Verify the shipment
        response = self.session.put(
            f"{BASE_URL}/api/shipments/{shipment['id']}/verify",
            json={"verified": True}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "message" in data
        print(f"✓ Verify shipment endpoint working - {data['message']}")
    
    def test_03_unverify_shipment(self):
        """Test removing verification from shipment"""
        client = self._create_test_client()
        shipment = self._create_test_shipment(client["id"])
        
        # First verify
        self.session.put(f"{BASE_URL}/api/shipments/{shipment['id']}/verify", json={"verified": True})
        
        # Then unverify
        response = self.session.put(
            f"{BASE_URL}/api/shipments/{shipment['id']}/verify",
            json={"verified": False}
        )
        
        assert response.status_code == 200
        print("✓ Unverify shipment working")
    
    def test_04_verify_nonexistent_shipment_404(self):
        """Test verifying non-existent shipment returns 404"""
        fake_id = str(uuid.uuid4())
        response = self.session.put(
            f"{BASE_URL}/api/shipments/{fake_id}/verify",
            json={"verified": True}
        )
        assert response.status_code == 404
        print("✓ Verify non-existent shipment returns 404")
    
    # ============ BULK COLLECT ============
    
    def test_05_bulk_collect_arrived_parcels(self):
        """Test marking arrived parcels as collected"""
        client = self._create_test_client()
        trip = self._create_test_trip()
        
        # Create a shipment with 'arrived' status
        shipment_data = {
            "client_id": client["id"],
            "description": "TEST_Arrived parcel for collection",
            "destination": "Nairobi",
            "total_weight": 5.0,
            "quantity": 1,
            "trip_id": trip["id"],
            "status": "arrived"
        }
        response = self.session.post(f"{BASE_URL}/api/shipments", json=shipment_data)
        assert response.status_code in [200, 201]
        shipment = response.json()
        self.created_ids["shipments"].append(shipment["id"])
        
        # Bulk collect
        response = self.session.put(
            f"{BASE_URL}/api/warehouse/parcels/bulk-collect",
            json={"parcel_ids": [shipment["id"]]}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "message" in data
        print(f"✓ Bulk collect arrived parcels - {data['message']}")
    
    def test_06_bulk_collect_empty_list_fails(self):
        """Test bulk collect with empty parcel list fails"""
        response = self.session.put(
            f"{BASE_URL}/api/warehouse/parcels/bulk-collect",
            json={"parcel_ids": []}
        )
        assert response.status_code == 400
        print("✓ Bulk collect empty list returns 400")
    
    def test_07_bulk_collect_non_arrived_skipped(self):
        """Test that non-arrived parcels are skipped or rejected"""
        client = self._create_test_client()
        
        # Create shipment in 'warehouse' status (not arrived)
        shipment = self._create_test_shipment(client["id"], status="warehouse")
        
        response = self.session.put(
            f"{BASE_URL}/api/warehouse/parcels/bulk-collect",
            json={"parcel_ids": [shipment["id"]]}
        )
        
        # Should either fail or return 0 collected
        if response.status_code == 400:
            print("✓ Bulk collect rejects non-arrived parcels (400)")
        elif response.status_code == 200:
            data = response.json()
            assert data.get("count", 0) == 0
            print(f"✓ Bulk collect skips non-arrived parcels - {data['message']}")
    
    # ============ WAREHOUSE FILTERS ============
    
    def test_08_warehouse_filters_include_clients(self):
        """Test warehouse filters endpoint includes clients list"""
        response = self.session.get(f"{BASE_URL}/api/warehouse/filters")
        assert response.status_code == 200
        
        data = response.json()
        assert "clients" in data
        assert "destinations" in data
        assert "trips" in data
        assert "statuses" in data
        
        # Clients should have id and name
        if data["clients"]:
            assert "id" in data["clients"][0]
            assert "name" in data["clients"][0]
        
        print(f"✓ Warehouse filters returned {len(data['clients'])} clients, {len(data['destinations'])} destinations")
    
    def test_09_warehouse_parcels_client_filter(self):
        """Test filtering warehouse parcels by client ID"""
        # Get existing clients
        response = self.session.get(f"{BASE_URL}/api/clients")
        assert response.status_code == 200
        clients = response.json()
        
        if not clients:
            pytest.skip("No clients available for testing")
        
        client_id = clients[0]["id"]
        
        # Filter parcels by this client
        response = self.session.get(
            f"{BASE_URL}/api/warehouse/parcels",
            params={"client_id": client_id}
        )
        assert response.status_code == 200
        
        data = response.json()
        assert "items" in data
        assert "total" in data
        print(f"✓ Client filter returned {len(data['items'])} parcels")
    
    # ============ TRIP STATUS PROGRESSION ============
    
    def test_10_trip_status_to_loading(self):
        """Test changing trip status to loading"""
        trip = self._create_test_trip()
        
        response = self.session.put(
            f"{BASE_URL}/api/trips/{trip['id']}",
            json={"status": "loading"}
        )
        assert response.status_code == 200
        
        data = response.json()
        assert data.get("status") == "loading"
        print(f"✓ Trip status changed to loading")
    
    def test_11_trip_status_to_in_transit(self):
        """Test changing trip status to in_transit"""
        trip = self._create_test_trip()
        
        # First set to loading
        self.session.put(f"{BASE_URL}/api/trips/{trip['id']}", json={"status": "loading"})
        
        # Then to in_transit
        response = self.session.put(
            f"{BASE_URL}/api/trips/{trip['id']}",
            json={"status": "in_transit"}
        )
        assert response.status_code == 200
        
        data = response.json()
        assert data.get("status") == "in_transit"
        print(f"✓ Trip status changed to in_transit")
    
    def test_12_trip_status_to_delivered(self):
        """Test changing trip status to delivered"""
        trip = self._create_test_trip()
        
        response = self.session.put(
            f"{BASE_URL}/api/trips/{trip['id']}",
            json={"status": "delivered"}
        )
        assert response.status_code == 200
        
        data = response.json()
        assert data.get("status") == "delivered"
        print(f"✓ Trip status changed to delivered")
    
    # ============ BULK STATUS CHANGE ============
    
    def test_13_bulk_status_change(self):
        """Test bulk status change for parcels"""
        client = self._create_test_client()
        shipment = self._create_test_shipment(client["id"])
        
        response = self.session.put(
            f"{BASE_URL}/api/warehouse/parcels/bulk-status",
            json={
                "parcel_ids": [shipment["id"]],
                "status": "staged"
            }
        )
        assert response.status_code == 200
        
        data = response.json()
        assert "message" in data
        assert data.get("count", 0) >= 1
        print(f"✓ Bulk status change - {data['message']}")
    
    # ============ LOADING/UNLOADING WORKFLOWS ============
    
    def test_14_list_shipments_by_status(self):
        """Test listing shipments filtered by status"""
        response = self.session.get(
            f"{BASE_URL}/api/shipments",
            params={"status": "staged"}
        )
        assert response.status_code == 200
        
        data = response.json()
        assert isinstance(data, list)
        print(f"✓ Listed {len(data)} staged shipments")
    
    def test_15_list_shipments_by_trip(self):
        """Test listing shipments filtered by trip"""
        trip = self._create_test_trip()
        
        response = self.session.get(
            f"{BASE_URL}/api/shipments",
            params={"trip_id": trip["id"]}
        )
        assert response.status_code == 200
        
        data = response.json()
        assert isinstance(data, list)
        print(f"✓ Listed {len(data)} shipments for trip")
    
    def test_16_trip_parcels_for_invoice(self):
        """Test trip parcels endpoint for invoice modal"""
        trip = self._create_test_trip()
        
        response = self.session.get(f"{BASE_URL}/api/invoices/trip-parcels/{trip['id']}")
        
        # Should return 200 with list (even if empty)
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        print(f"✓ Trip parcels for invoice - returned {len(data)} parcels")
    
    # ============ HELPER METHODS ============
    
    def _create_test_client(self):
        """Helper to create a test client"""
        client_data = {
            "name": f"TEST_Client_{uuid.uuid4().hex[:8]}",
            "phone": "+27123456789",
            "default_currency": "ZAR",
            "default_rate_type": "per_kg",
            "default_rate_value": 36.0,
            "status": "active"
        }
        response = self.session.post(f"{BASE_URL}/api/clients", json=client_data)
        assert response.status_code in [200, 201], f"Failed to create client: {response.text}"
        client = response.json()
        self.created_ids["clients"].append(client["id"])
        return client
    
    def _create_test_trip(self):
        """Helper to create a test trip"""
        trip_data = {
            "trip_number": f"TEST-{uuid.uuid4().hex[:6].upper()}",
            "route": ["Johannesburg", "Nairobi"],
            "departure_date": "2026-01-20"
        }
        response = self.session.post(f"{BASE_URL}/api/trips", json=trip_data)
        assert response.status_code in [200, 201], f"Failed to create trip: {response.text}"
        trip = response.json()
        self.created_ids["trips"].append(trip["id"])
        return trip
    
    def _create_test_shipment(self, client_id, trip_id=None, status="warehouse"):
        """Helper to create a test shipment"""
        shipment_data = {
            "client_id": client_id,
            "description": f"TEST_Shipment_{uuid.uuid4().hex[:8]}",
            "destination": "Nairobi",
            "total_weight": 10.0,
            "quantity": 1,
            "status": status
        }
        if trip_id:
            shipment_data["trip_id"] = trip_id
            shipment_data["status"] = "staged"
        
        response = self.session.post(f"{BASE_URL}/api/shipments", json=shipment_data)
        assert response.status_code in [200, 201], f"Failed to create shipment: {response.text}"
        shipment = response.json()
        self.created_ids["shipments"].append(shipment["id"])
        return shipment
