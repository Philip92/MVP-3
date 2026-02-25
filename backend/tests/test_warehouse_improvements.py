"""
Test Warehouse Improvements - Search by Client Name, Auth/Me Default Warehouse, Warehouses Endpoint
Tests for new features:
1. Search by client name in /api/warehouse/parcels?search=
2. /api/auth/me returns default_warehouse field
3. /api/warehouses endpoint returns warehouse list
"""

import pytest
import requests
import os

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

class TestSearchByClientName:
    """Test that warehouse search API supports client name searches"""
    
    @pytest.fixture(scope="class")
    def authenticated_session(self):
        """Get authenticated session"""
        session = requests.Session()
        session.headers.update({"Content-Type": "application/json"})
        
        # Login
        login_response = session.post(
            f"{BASE_URL}/api/auth/login",
            json={"email": "admin@servex.com", "password": "Servex2026!"}
        )
        
        if login_response.status_code != 200:
            pytest.skip(f"Login failed: {login_response.status_code}")
        
        return session
    
    def test_search_api_accepts_search_param(self, authenticated_session):
        """Test that search parameter is accepted by API"""
        response = authenticated_session.get(
            f"{BASE_URL}/api/warehouse/parcels?search=TestClient"
        )
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert "items" in data, "Response should have items"
        assert "total" in data, "Response should have total"
        
        print(f"✅ Search API works - found {data['total']} results for 'TestClient'")
    
    def test_search_handles_empty_query(self, authenticated_session):
        """Test that empty search returns all parcels"""
        response = authenticated_session.get(
            f"{BASE_URL}/api/warehouse/parcels?search="
        )
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        
        data = response.json()
        assert "items" in data
        print(f"✅ Empty search returns {data['total']} parcels")
    
    def test_search_with_special_characters(self, authenticated_session):
        """Test search handles special characters safely"""
        response = authenticated_session.get(
            f"{BASE_URL}/api/warehouse/parcels?search=Test%20%26%20Co"
        )
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        print("✅ Search handles special characters safely")


class TestAuthMeDefaultWarehouse:
    """Test that /api/auth/me returns default_warehouse field"""
    
    @pytest.fixture(scope="class")
    def authenticated_session(self):
        """Get authenticated session"""
        session = requests.Session()
        session.headers.update({"Content-Type": "application/json"})
        
        # Login
        login_response = session.post(
            f"{BASE_URL}/api/auth/login",
            json={"email": "admin@servex.com", "password": "Servex2026!"}
        )
        
        if login_response.status_code != 200:
            pytest.skip(f"Login failed: {login_response.status_code}")
        
        return session
    
    def test_auth_me_returns_default_warehouse(self, authenticated_session):
        """Test that /api/auth/me includes default_warehouse field"""
        response = authenticated_session.get(f"{BASE_URL}/api/auth/me")
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        
        # Check required fields exist
        assert "id" in data, "Response should have id"
        assert "email" in data, "Response should have email"
        assert "name" in data, "Response should have name"
        
        # Check default_warehouse field exists (can be null)
        assert "default_warehouse" in data, "Response should have default_warehouse field"
        
        print(f"✅ /api/auth/me returns user with default_warehouse: {data.get('default_warehouse')}")
    
    def test_login_returns_default_warehouse(self, authenticated_session):
        """Test that login response includes default_warehouse"""
        # Make fresh login request to check response
        login_response = authenticated_session.post(
            f"{BASE_URL}/api/auth/login",
            json={"email": "admin@servex.com", "password": "Servex2026!"}
        )
        
        assert login_response.status_code == 200
        
        data = login_response.json()
        assert "default_warehouse" in data, "Login response should include default_warehouse"
        
        print(f"✅ Login returns default_warehouse: {data.get('default_warehouse')}")


class TestWarehousesEndpoint:
    """Test /api/warehouses endpoint"""
    
    @pytest.fixture(scope="class")
    def authenticated_session(self):
        """Get authenticated session"""
        session = requests.Session()
        session.headers.update({"Content-Type": "application/json"})
        
        # Login
        login_response = session.post(
            f"{BASE_URL}/api/auth/login",
            json={"email": "admin@servex.com", "password": "Servex2026!"}
        )
        
        if login_response.status_code != 200:
            pytest.skip(f"Login failed: {login_response.status_code}")
        
        return session
    
    def test_warehouses_endpoint_exists(self, authenticated_session):
        """Test that /api/warehouses endpoint exists and returns list"""
        response = authenticated_session.get(f"{BASE_URL}/api/warehouses")
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert isinstance(data, list), "Response should be a list"
        
        print(f"✅ /api/warehouses returns list with {len(data)} warehouses")
    
    def test_warehouses_response_structure(self, authenticated_session):
        """Test warehouse objects have expected structure"""
        response = authenticated_session.get(f"{BASE_URL}/api/warehouses")
        
        assert response.status_code == 200
        
        data = response.json()
        
        if len(data) > 0:
            warehouse = data[0]
            assert "id" in warehouse, "Warehouse should have id"
            assert "name" in warehouse or "id" in warehouse, "Warehouse should have name or id"
            print(f"✅ Warehouse structure verified: {list(warehouse.keys())}")
        else:
            print("⚠️ No warehouses to verify structure (empty list)")


class TestTripFilterSupport:
    """Test trip filter including unassigned option"""
    
    @pytest.fixture(scope="class")
    def authenticated_session(self):
        """Get authenticated session"""
        session = requests.Session()
        session.headers.update({"Content-Type": "application/json"})
        
        # Login
        login_response = session.post(
            f"{BASE_URL}/api/auth/login",
            json={"email": "admin@servex.com", "password": "Servex2026!"}
        )
        
        if login_response.status_code != 200:
            pytest.skip(f"Login failed: {login_response.status_code}")
        
        return session
    
    def test_filter_by_trip_unassigned(self, authenticated_session):
        """Test filtering parcels by unassigned trip"""
        response = authenticated_session.get(
            f"{BASE_URL}/api/warehouse/parcels?trip_id=unassigned"
        )
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert "items" in data
        
        # Verify all items have trip_id = null
        for item in data["items"]:
            assert item.get("trip_id") is None, f"Expected unassigned, got trip_id: {item.get('trip_id')}"
        
        print(f"✅ Trip filter 'unassigned' works - found {data['total']} unassigned parcels")
    
    def test_filter_by_all_trips(self, authenticated_session):
        """Test that 'all' trip filter returns all parcels"""
        response = authenticated_session.get(
            f"{BASE_URL}/api/warehouse/parcels"
        )
        
        assert response.status_code == 200
        
        data = response.json()
        print(f"✅ Default (all trips) returns {data['total']} parcels")


class TestWarehouseFiltersEndpoint:
    """Test /api/warehouse/filters endpoint"""
    
    @pytest.fixture(scope="class")
    def authenticated_session(self):
        """Get authenticated session"""
        session = requests.Session()
        session.headers.update({"Content-Type": "application/json"})
        
        # Login
        login_response = session.post(
            f"{BASE_URL}/api/auth/login",
            json={"email": "admin@servex.com", "password": "Servex2026!"}
        )
        
        if login_response.status_code != 200:
            pytest.skip(f"Login failed: {login_response.status_code}")
        
        return session
    
    def test_filters_returns_trips(self, authenticated_session):
        """Test that filters endpoint returns trips for dropdown"""
        response = authenticated_session.get(f"{BASE_URL}/api/warehouse/filters")
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        
        data = response.json()
        assert "trips" in data, "Filters should include trips"
        
        print(f"✅ Filters endpoint returns {len(data['trips'])} active trips")
    
    def test_filters_returns_clients(self, authenticated_session):
        """Test that filters endpoint returns clients for search by name"""
        response = authenticated_session.get(f"{BASE_URL}/api/warehouse/filters")
        
        assert response.status_code == 200
        
        data = response.json()
        assert "clients" in data, "Filters should include clients"
        
        # If clients exist, verify structure
        if len(data["clients"]) > 0:
            client = data["clients"][0]
            assert "id" in client, "Client should have id"
            assert "name" in client, "Client should have name"
            print(f"✅ Filters returns {len(data['clients'])} clients with name field")
        else:
            print("⚠️ No clients in filters (empty)")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
