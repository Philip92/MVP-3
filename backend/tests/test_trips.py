"""
Backend tests for Trip Manager feature
Tests the /api/trips-with-stats, /api/trips/next-number, and /api/trips/{id}/summary endpoints
"""
import pytest
import requests
import os
import time

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')
SESSION_TOKEN = "demo_trips_session_1771084342772"  # Created for demo-tenant-123


class TestTripsWithStats:
    """Tests for /api/trips-with-stats endpoint - main Trip Manager listing"""
    
    def test_trips_with_stats_returns_list(self):
        """Test that trips-with-stats returns a list of trips with stats"""
        response = requests.get(
            f"{BASE_URL}/api/trips-with-stats",
            headers={"Authorization": f"Bearer {SESSION_TOKEN}"}
        )
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert isinstance(data, list), "Response should be a list"
        assert len(data) >= 5, f"Expected at least 5 trips, got {len(data)}"
    
    def test_trips_with_stats_includes_required_fields(self):
        """Test that each trip has required fields: trip_number, status, stats"""
        response = requests.get(
            f"{BASE_URL}/api/trips-with-stats",
            headers={"Authorization": f"Bearer {SESSION_TOKEN}"}
        )
        data = response.json()
        
        for trip in data:
            assert "id" in trip, "Trip should have id"
            assert "trip_number" in trip, "Trip should have trip_number"
            assert "status" in trip, "Trip should have status"
            assert "stats" in trip, "Trip should have stats"
            
            stats = trip["stats"]
            assert "total_parcels" in stats, "Stats should have total_parcels"
            assert "total_weight" in stats, "Stats should have total_weight"
            assert "total_clients" in stats, "Stats should have total_clients"
            assert "loading_percentage" in stats, "Stats should have loading_percentage"
    
    def test_trips_with_stats_filter_by_status_planning(self):
        """Test filtering trips by planning status"""
        response = requests.get(
            f"{BASE_URL}/api/trips-with-stats?status=planning",
            headers={"Authorization": f"Bearer {SESSION_TOKEN}"}
        )
        assert response.status_code == 200
        
        data = response.json()
        assert len(data) >= 2, f"Expected at least 2 planning trips, got {len(data)}"
        
        for trip in data:
            assert trip["status"] == "planning", f"Expected planning status, got {trip['status']}"
    
    def test_trips_with_stats_filter_by_status_loading(self):
        """Test filtering trips by loading status"""
        response = requests.get(
            f"{BASE_URL}/api/trips-with-stats?status=loading",
            headers={"Authorization": f"Bearer {SESSION_TOKEN}"}
        )
        assert response.status_code == 200
        
        data = response.json()
        assert len(data) >= 2, f"Expected at least 2 loading trips, got {len(data)}"
        
        for trip in data:
            assert trip["status"] == "loading", f"Expected loading status, got {trip['status']}"
    
    def test_trips_with_stats_filter_by_status_in_transit(self):
        """Test filtering trips by in_transit status"""
        response = requests.get(
            f"{BASE_URL}/api/trips-with-stats?status=in_transit",
            headers={"Authorization": f"Bearer {SESSION_TOKEN}"}
        )
        assert response.status_code == 200
        
        data = response.json()
        assert len(data) >= 1, f"Expected at least 1 in_transit trip, got {len(data)}"
        
        for trip in data:
            assert trip["status"] == "in_transit", f"Expected in_transit status, got {trip['status']}"
    
    def test_trips_with_stats_filter_by_status_closed(self):
        """Test filtering trips by closed status"""
        response = requests.get(
            f"{BASE_URL}/api/trips-with-stats?status=closed",
            headers={"Authorization": f"Bearer {SESSION_TOKEN}"}
        )
        assert response.status_code == 200
        
        data = response.json()
        assert len(data) >= 1, f"Expected at least 1 closed trip, got {len(data)}"
        
        for trip in data:
            assert trip["status"] == "closed", f"Expected closed status, got {trip['status']}"
    
    def test_trips_with_stats_includes_route_array(self):
        """Test that trips include route as an array of stops"""
        response = requests.get(
            f"{BASE_URL}/api/trips-with-stats",
            headers={"Authorization": f"Bearer {SESSION_TOKEN}"}
        )
        data = response.json()
        
        # Find a trip with route (S27 has Johannesburg -> Beitbridge -> Nairobi)
        trip_s27 = next((t for t in data if t["trip_number"] == "S27"), None)
        assert trip_s27 is not None, "S27 trip should exist"
        assert "route" in trip_s27, "Trip should have route"
        assert isinstance(trip_s27["route"], list), "Route should be a list"
        assert len(trip_s27["route"]) > 0, "Route should have at least one stop"
    
    def test_trips_with_stats_requires_authentication(self):
        """Test that authentication is required"""
        response = requests.get(f"{BASE_URL}/api/trips-with-stats")
        assert response.status_code == 401, f"Expected 401 without auth, got {response.status_code}"


class TestTripsNextNumber:
    """Tests for /api/trips/next-number endpoint - auto-generation of trip numbers"""
    
    def test_next_number_returns_s32(self):
        """Test that next trip number is S32 (after S27-S31)"""
        response = requests.get(
            f"{BASE_URL}/api/trips/next-number",
            headers={"Authorization": f"Bearer {SESSION_TOKEN}"}
        )
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert "next_trip_number" in data, "Response should have next_trip_number"
        assert data["next_trip_number"] == "S32", f"Expected S32, got {data['next_trip_number']}"
    
    def test_next_number_format(self):
        """Test that next trip number follows S{number} format"""
        response = requests.get(
            f"{BASE_URL}/api/trips/next-number",
            headers={"Authorization": f"Bearer {SESSION_TOKEN}"}
        )
        data = response.json()
        
        trip_number = data["next_trip_number"]
        assert trip_number.startswith("S"), f"Trip number should start with S, got {trip_number}"
        assert trip_number[1:].isdigit(), f"Trip number suffix should be numeric, got {trip_number}"
    
    def test_next_number_requires_authentication(self):
        """Test that authentication is required"""
        response = requests.get(f"{BASE_URL}/api/trips/next-number")
        assert response.status_code == 401, f"Expected 401 without auth, got {response.status_code}"


class TestTripSummary:
    """Tests for /api/trips/{trip_id}/summary endpoint - Trip Detail page"""
    
    def test_trip_summary_returns_complete_data(self):
        """Test that trip summary returns trip, stats, and metadata"""
        response = requests.get(
            f"{BASE_URL}/api/trips/trip-1/summary",
            headers={"Authorization": f"Bearer {SESSION_TOKEN}"}
        )
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert "trip" in data, "Response should have trip"
        assert "stats" in data, "Response should have stats"
        assert "created_by" in data, "Response should have created_by"
        assert "created_at" in data, "Response should have created_at"
    
    def test_trip_summary_trip_fields(self):
        """Test that trip object has all required fields"""
        response = requests.get(
            f"{BASE_URL}/api/trips/trip-1/summary",
            headers={"Authorization": f"Bearer {SESSION_TOKEN}"}
        )
        data = response.json()
        
        trip = data["trip"]
        assert trip["trip_number"] == "S27", "Trip number should be S27"
        assert "status" in trip, "Trip should have status"
        assert "route" in trip, "Trip should have route"
        assert "departure_date" in trip, "Trip should have departure_date"
        assert "vehicle" in trip, "Trip should have vehicle (even if null)"
        assert "driver" in trip, "Trip should have driver (even if null)"
    
    def test_trip_summary_stats_fields(self):
        """Test that stats object has all required fields"""
        response = requests.get(
            f"{BASE_URL}/api/trips/trip-1/summary",
            headers={"Authorization": f"Bearer {SESSION_TOKEN}"}
        )
        data = response.json()
        
        stats = data["stats"]
        assert "total_parcels" in stats, "Stats should have total_parcels"
        assert "total_pieces" in stats, "Stats should have total_pieces"
        assert "total_weight" in stats, "Stats should have total_weight"
        assert "total_clients" in stats, "Stats should have total_clients"
        assert "invoiced_value" in stats, "Stats should have invoiced_value"
        assert "loaded_parcels" in stats, "Stats should have loaded_parcels"
        assert "loading_percentage" in stats, "Stats should have loading_percentage"
    
    def test_trip_summary_404_for_nonexistent_trip(self):
        """Test that 404 is returned for non-existent trip"""
        response = requests.get(
            f"{BASE_URL}/api/trips/nonexistent-trip-id/summary",
            headers={"Authorization": f"Bearer {SESSION_TOKEN}"}
        )
        assert response.status_code == 404, f"Expected 404, got {response.status_code}"
    
    def test_trip_summary_requires_authentication(self):
        """Test that authentication is required"""
        response = requests.get(f"{BASE_URL}/api/trips/trip-1/summary")
        assert response.status_code == 401, f"Expected 401 without auth, got {response.status_code}"


class TestTripCRUD:
    """Tests for Trip CRUD operations (create, update, delete)"""
    
    def test_create_trip_success(self):
        """Test creating a new trip"""
        trip_data = {
            "trip_number": f"TEST-{int(time.time())}",
            "route": ["Johannesburg", "Harare"],
            "departure_date": "2026-02-20",
            "notes": "Test trip for CRUD"
        }
        
        response = requests.post(
            f"{BASE_URL}/api/trips",
            headers={"Authorization": f"Bearer {SESSION_TOKEN}"},
            json=trip_data
        )
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert data["trip_number"] == trip_data["trip_number"]
        assert data["route"] == trip_data["route"]
        assert data["status"] == "planning"  # Default status
        
        # Clean up - delete the trip
        requests.delete(
            f"{BASE_URL}/api/trips/{data['id']}",
            headers={"Authorization": f"Bearer {SESSION_TOKEN}"}
        )
    
    def test_create_trip_validates_route(self):
        """Test that empty route is allowed (optional)"""
        trip_data = {
            "trip_number": f"TEST-EMPTY-{int(time.time())}",
            "route": [],  # Empty route
            "departure_date": "2026-02-20"
        }
        
        response = requests.post(
            f"{BASE_URL}/api/trips",
            headers={"Authorization": f"Bearer {SESSION_TOKEN}"},
            json=trip_data
        )
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        # Clean up
        data = response.json()
        requests.delete(
            f"{BASE_URL}/api/trips/{data['id']}",
            headers={"Authorization": f"Bearer {SESSION_TOKEN}"}
        )
    
    def test_create_trip_duplicate_number_fails(self):
        """Test that duplicate trip number fails"""
        response = requests.post(
            f"{BASE_URL}/api/trips",
            headers={"Authorization": f"Bearer {SESSION_TOKEN}"},
            json={
                "trip_number": "S27",  # Already exists
                "route": ["Test"],
                "departure_date": "2026-02-20"
            }
        )
        assert response.status_code == 400, f"Expected 400 for duplicate, got {response.status_code}"


class TestTripsVehicleDriverInfo:
    """Tests for vehicle and driver info in trip responses"""
    
    def test_trips_with_stats_includes_vehicle_info(self):
        """Test that trips include vehicle info when assigned"""
        response = requests.get(
            f"{BASE_URL}/api/trips-with-stats",
            headers={"Authorization": f"Bearer {SESSION_TOKEN}"}
        )
        data = response.json()
        
        for trip in data:
            # Vehicle field should be present (even if null)
            assert "vehicle" in trip, "Trip should have vehicle field"
    
    def test_trips_with_stats_includes_driver_info(self):
        """Test that trips include driver info when assigned"""
        response = requests.get(
            f"{BASE_URL}/api/trips-with-stats",
            headers={"Authorization": f"Bearer {SESSION_TOKEN}"}
        )
        data = response.json()
        
        for trip in data:
            # Driver field should be present (even if null)
            assert "driver" in trip, "Trip should have driver field"


# Run tests
if __name__ == "__main__":
    pytest.main([__file__, "-v"])
