"""
Test Warehouse Manager Backend Endpoints
Tests for GET /api/warehouse/parcels, GET /api/warehouse/filters, 
GET /api/warehouse/parcels/{id}, PUT /api/warehouse/parcels/bulk-status,
PUT /api/warehouse/parcels/bulk-assign-trip, DELETE /api/warehouse/parcels/bulk-delete
"""

import pytest
import requests
import os

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL').rstrip('/')
SESSION_TOKEN = os.environ.get('TEST_SESSION_TOKEN', '')

@pytest.fixture(scope="module")
def api_client():
    """Shared requests session with auth header"""
    session = requests.Session()
    session.headers.update({
        "Content-Type": "application/json",
        "Authorization": f"Bearer {SESSION_TOKEN}"
    })
    return session


class TestWarehouseFilters:
    """Test GET /api/warehouse/filters endpoint"""
    
    def test_get_filter_options(self, api_client):
        """Test that filter options endpoint returns expected structure"""
        response = api_client.get(f"{BASE_URL}/api/warehouse/filters")
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert "destinations" in data, "Response should have destinations"
        assert "clients" in data, "Response should have clients"
        assert "trips" in data, "Response should have trips"
        assert "statuses" in data, "Response should have statuses"
        
        # Verify statuses are correct
        assert "warehouse" in data["statuses"]
        assert "staged" in data["statuses"]
        assert "loaded" in data["statuses"]
        assert "in_transit" in data["statuses"]
        assert "delivered" in data["statuses"]
        
        # Clients should have id and name
        if len(data["clients"]) > 0:
            assert "id" in data["clients"][0]
            assert "name" in data["clients"][0]
        
        print(f"Filter options: {len(data['destinations'])} destinations, {len(data['clients'])} clients, {len(data['trips'])} trips")


class TestWarehouseParcels:
    """Test GET /api/warehouse/parcels endpoint - paginated list with filters"""
    
    def test_list_parcels_default(self, api_client):
        """Test listing parcels with default params"""
        response = api_client.get(f"{BASE_URL}/api/warehouse/parcels")
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert "items" in data, "Response should have items"
        assert "total" in data, "Response should have total count"
        assert "page" in data, "Response should have page"
        assert "page_size" in data, "Response should have page_size"
        assert "total_pages" in data, "Response should have total_pages"
        
        print(f"Listed {len(data['items'])} parcels, total: {data['total']}")
    
    def test_list_parcels_with_enriched_data(self, api_client):
        """Test that parcels have enriched data (client_name, trip_number, staff_name)"""
        response = api_client.get(f"{BASE_URL}/api/warehouse/parcels")
        
        assert response.status_code == 200
        
        data = response.json()
        if len(data["items"]) > 0:
            parcel = data["items"][0]
            assert "client_name" in parcel, "Parcel should have client_name"
            assert "staff_name" in parcel, "Parcel should have staff_name"
            assert "trip_number" in parcel or parcel.get("trip_id") is None, "Parcel should have trip_number if trip_id exists"
            print(f"First parcel: {parcel.get('id', '')[:8]}, client: {parcel.get('client_name')}")
    
    def test_list_parcels_pagination(self, api_client):
        """Test pagination works correctly"""
        # Get first page
        response1 = api_client.get(f"{BASE_URL}/api/warehouse/parcels?page=1&page_size=3")
        assert response1.status_code == 200
        data1 = response1.json()
        
        assert data1["page"] == 1
        assert data1["page_size"] == 3
        
        if data1["total"] > 3:
            # Get second page
            response2 = api_client.get(f"{BASE_URL}/api/warehouse/parcels?page=2&page_size=3")
            assert response2.status_code == 200
            data2 = response2.json()
            
            assert data2["page"] == 2
            
            # Items should be different
            ids1 = {item["id"] for item in data1["items"]}
            ids2 = {item["id"] for item in data2["items"]}
            assert len(ids1 & ids2) == 0, "Pagination returned duplicate items"
            print(f"Pagination works: page 1 has {len(data1['items'])} items, page 2 has {len(data2['items'])} items")
    
    def test_filter_by_status(self, api_client):
        """Test filtering by single status"""
        response = api_client.get(f"{BASE_URL}/api/warehouse/parcels?status=warehouse")
        
        assert response.status_code == 200
        data = response.json()
        
        # All items should have warehouse status
        for item in data["items"]:
            assert item["status"] == "warehouse", f"Expected status warehouse, got {item['status']}"
        
        print(f"Found {data['total']} parcels with status warehouse")
    
    def test_filter_by_multiple_statuses(self, api_client):
        """Test filtering by multiple statuses (comma-separated)"""
        response = api_client.get(f"{BASE_URL}/api/warehouse/parcels?status=warehouse,staged")
        
        assert response.status_code == 200
        data = response.json()
        
        # All items should have warehouse or staged status
        for item in data["items"]:
            assert item["status"] in ["warehouse", "staged"], f"Expected warehouse/staged, got {item['status']}"
        
        print(f"Found {data['total']} parcels with status warehouse or staged")
    
    def test_sort_by_weight(self, api_client):
        """Test sorting by weight descending"""
        response = api_client.get(f"{BASE_URL}/api/warehouse/parcels?sort_by=total_weight&sort_order=desc")
        
        assert response.status_code == 200
        data = response.json()
        
        if len(data["items"]) > 1:
            weights = [item["total_weight"] for item in data["items"]]
            assert weights == sorted(weights, reverse=True), "Items should be sorted by weight descending"
        
        print(f"Sort by weight works, first item: {data['items'][0]['total_weight'] if data['items'] else 'N/A'} kg")
    
    def test_search_filter(self, api_client):
        """Test search filter works on description/destination"""
        response = api_client.get(f"{BASE_URL}/api/warehouse/parcels?search=Test")
        
        assert response.status_code == 200
        data = response.json()
        
        print(f"Search 'Test' found {data['total']} parcels")


class TestWarehouseParcelDetail:
    """Test GET /api/warehouse/parcels/{id} endpoint"""
    
    def test_get_parcel_detail(self, api_client):
        """Test getting detailed parcel info"""
        # First get a parcel ID
        list_response = api_client.get(f"{BASE_URL}/api/warehouse/parcels?page_size=1")
        assert list_response.status_code == 200
        
        list_data = list_response.json()
        if len(list_data["items"]) == 0:
            pytest.skip("No parcels to test detail view")
        
        parcel_id = list_data["items"][0]["id"]
        
        # Get detail
        response = api_client.get(f"{BASE_URL}/api/warehouse/parcels/{parcel_id}")
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        
        data = response.json()
        assert "pieces" in data, "Detail should include pieces"
        assert "client" in data, "Detail should include client"
        assert "staff" in data, "Detail should include staff"
        
        # Basic parcel fields
        assert "id" in data
        assert "description" in data
        assert "destination" in data
        assert "total_pieces" in data
        assert "total_weight" in data
        assert "status" in data
        
        print(f"Detail for parcel {parcel_id[:8]}: {data.get('description')}, {len(data.get('pieces', []))} pieces")
    
    def test_get_parcel_not_found(self, api_client):
        """Test 404 for non-existent parcel"""
        response = api_client.get(f"{BASE_URL}/api/warehouse/parcels/nonexistent-id-12345")
        
        assert response.status_code == 404
        print("404 returned correctly for non-existent parcel")


class TestBulkStatusChange:
    """Test PUT /api/warehouse/parcels/bulk-status endpoint"""
    
    def test_bulk_status_change(self, api_client):
        """Test changing status for multiple parcels"""
        # Get some parcel IDs
        list_response = api_client.get(f"{BASE_URL}/api/warehouse/parcels?status=warehouse&page_size=2")
        assert list_response.status_code == 200
        
        list_data = list_response.json()
        if len(list_data["items"]) < 1:
            pytest.skip("No warehouse parcels to test bulk status change")
        
        parcel_ids = [item["id"] for item in list_data["items"]]
        
        # Change status to staged
        response = api_client.put(
            f"{BASE_URL}/api/warehouse/parcels/bulk-status",
            json={"parcel_ids": parcel_ids, "status": "staged"}
        )
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert "count" in data, "Response should have count"
        assert data["count"] == len(parcel_ids), f"Expected {len(parcel_ids)} updated, got {data['count']}"
        
        # Verify status changed
        for pid in parcel_ids:
            verify = api_client.get(f"{BASE_URL}/api/warehouse/parcels/{pid}")
            assert verify.status_code == 200
            assert verify.json()["status"] == "staged", f"Parcel {pid} status not updated"
        
        print(f"Successfully changed status for {data['count']} parcels")
        
        # Restore status back to warehouse
        api_client.put(
            f"{BASE_URL}/api/warehouse/parcels/bulk-status",
            json={"parcel_ids": parcel_ids, "status": "warehouse"}
        )
    
    def test_bulk_status_missing_params(self, api_client):
        """Test that bulk status fails with missing params"""
        response = api_client.put(
            f"{BASE_URL}/api/warehouse/parcels/bulk-status",
            json={"status": "staged"}  # Missing parcel_ids
        )
        
        assert response.status_code == 400
        print("400 returned correctly for missing parcel_ids")


class TestBulkAssignTrip:
    """Test PUT /api/warehouse/parcels/bulk-assign-trip endpoint"""
    
    def test_bulk_assign_to_trip(self, api_client):
        """Test assigning multiple parcels to a trip"""
        # Get unassigned parcels
        list_response = api_client.get(f"{BASE_URL}/api/warehouse/parcels?status=warehouse&page_size=2")
        assert list_response.status_code == 200
        
        list_data = list_response.json()
        # Filter to only unassigned ones
        unassigned = [item for item in list_data["items"] if item.get("trip_id") is None]
        
        if len(unassigned) < 1:
            pytest.skip("No unassigned warehouse parcels to test")
        
        parcel_ids = [item["id"] for item in unassigned[:2]]
        
        # Get a trip ID
        trip_response = api_client.get(f"{BASE_URL}/api/trips")
        assert trip_response.status_code == 200
        trips = trip_response.json()
        active_trips = [t for t in trips if t.get("status") not in ["closed", "delivered"]]
        
        if len(active_trips) == 0:
            pytest.skip("No active trips to assign parcels to")
        
        trip_id = active_trips[0]["id"]
        
        # Assign to trip
        response = api_client.put(
            f"{BASE_URL}/api/warehouse/parcels/bulk-assign-trip",
            json={"parcel_ids": parcel_ids, "trip_id": trip_id}
        )
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert "count" in data
        
        # Verify assignment and status change
        for pid in parcel_ids:
            verify = api_client.get(f"{BASE_URL}/api/warehouse/parcels/{pid}")
            assert verify.status_code == 200
            parcel = verify.json()
            assert parcel["trip_id"] == trip_id, f"Parcel {pid} not assigned to trip"
            assert parcel["status"] == "staged", f"Parcel {pid} status not changed to staged"
        
        print(f"Successfully assigned {data['count']} parcels to trip {trip_id[:8]}")
        
        # Unassign (restore)
        api_client.put(
            f"{BASE_URL}/api/warehouse/parcels/bulk-assign-trip",
            json={"parcel_ids": parcel_ids, "trip_id": None}
        )
    
    def test_bulk_unassign_from_trip(self, api_client):
        """Test unassigning parcels from trip (set trip_id to null)"""
        # Get assigned parcels
        list_response = api_client.get(f"{BASE_URL}/api/warehouse/parcels?status=staged&page_size=2")
        assert list_response.status_code == 200
        
        list_data = list_response.json()
        assigned = [item for item in list_data["items"] if item.get("trip_id") is not None]
        
        if len(assigned) < 1:
            pytest.skip("No assigned parcels to test unassign")
        
        parcel_ids = [item["id"] for item in assigned[:1]]
        original_trip = assigned[0].get("trip_id")
        
        # Unassign
        response = api_client.put(
            f"{BASE_URL}/api/warehouse/parcels/bulk-assign-trip",
            json={"parcel_ids": parcel_ids, "trip_id": None}
        )
        
        assert response.status_code == 200
        
        # Verify unassignment
        verify = api_client.get(f"{BASE_URL}/api/warehouse/parcels/{parcel_ids[0]}")
        assert verify.status_code == 200
        parcel = verify.json()
        assert parcel["trip_id"] is None, "Parcel trip_id should be null"
        assert parcel["status"] == "warehouse", "Parcel status should be warehouse"
        
        print(f"Successfully unassigned parcel {parcel_ids[0][:8]} from trip")
        
        # Restore if needed
        if original_trip:
            api_client.put(
                f"{BASE_URL}/api/warehouse/parcels/bulk-assign-trip",
                json={"parcel_ids": parcel_ids, "trip_id": original_trip}
            )
    
    def test_bulk_assign_trip_not_found(self, api_client):
        """Test assigning to non-existent trip returns 404"""
        # Get a parcel
        list_response = api_client.get(f"{BASE_URL}/api/warehouse/parcels?page_size=1")
        if list_response.status_code != 200 or len(list_response.json()["items"]) == 0:
            pytest.skip("No parcels available")
        
        parcel_id = list_response.json()["items"][0]["id"]
        
        response = api_client.put(
            f"{BASE_URL}/api/warehouse/parcels/bulk-assign-trip",
            json={"parcel_ids": [parcel_id], "trip_id": "nonexistent-trip-id-12345"}
        )
        
        assert response.status_code == 404
        print("404 returned correctly for non-existent trip")


class TestBulkDelete:
    """Test DELETE /api/warehouse/parcels/bulk-delete endpoint"""
    
    def test_bulk_delete(self, api_client):
        """Test deleting multiple parcels"""
        # Create test parcels to delete
        # First create a shipment
        client_response = api_client.get(f"{BASE_URL}/api/clients?page_size=1")
        if client_response.status_code != 200 or len(client_response.json()) == 0:
            pytest.skip("No clients to create test shipment")
        
        client_id = client_response.json()[0]["id"]
        
        # Create 2 test shipments for deletion
        test_ids = []
        for i in range(2):
            create_response = api_client.post(
                f"{BASE_URL}/api/shipments",
                json={
                    "client_id": client_id,
                    "description": f"TEST_DELETE_Parcel_{i}",
                    "destination": "TestDestination",
                    "total_pieces": 1,
                    "total_weight": 5.0
                }
            )
            if create_response.status_code == 200:
                test_ids.append(create_response.json()["id"])
        
        if len(test_ids) == 0:
            pytest.skip("Could not create test shipments")
        
        # Delete them
        response = api_client.delete(
            f"{BASE_URL}/api/warehouse/parcels/bulk-delete",
            json={"parcel_ids": test_ids}
        )
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert "count" in data
        assert data["count"] == len(test_ids), f"Expected {len(test_ids)} deleted, got {data['count']}"
        
        # Verify deletion
        for pid in test_ids:
            verify = api_client.get(f"{BASE_URL}/api/warehouse/parcels/{pid}")
            assert verify.status_code == 404, f"Parcel {pid} should be deleted"
        
        print(f"Successfully deleted {data['count']} parcels")
    
    def test_bulk_delete_missing_ids(self, api_client):
        """Test that bulk delete fails with missing parcel_ids"""
        response = api_client.delete(
            f"{BASE_URL}/api/warehouse/parcels/bulk-delete",
            json={}
        )
        
        assert response.status_code == 400
        print("400 returned correctly for missing parcel_ids")


class TestAuthentication:
    """Test that endpoints require authentication"""
    
    def test_warehouse_parcels_requires_auth(self):
        """Test that warehouse/parcels endpoint requires auth"""
        response = requests.get(f"{BASE_URL}/api/warehouse/parcels")
        assert response.status_code == 401
        print("401 returned correctly for unauthenticated request")
    
    def test_warehouse_filters_requires_auth(self):
        """Test that warehouse/filters endpoint requires auth"""
        response = requests.get(f"{BASE_URL}/api/warehouse/filters")
        assert response.status_code == 401
        print("401 returned correctly for unauthenticated request")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
