"""
Trip Detail Page API Tests
Tests for Trip Detail page with 5 tabs: Overview, Parcels, Clients & Invoicing, Expenses, History
Endpoints tested:
- GET /api/trips/{id}/summary (Overview tab)
- GET /api/trips/{id}/parcels (Parcels tab)
- GET /api/trips/{id}/clients-summary (Clients & Invoicing tab)
- GET /api/trips/{id}/expenses (Expenses tab)  
- POST /api/trips/{id}/expenses (Add expense)
- DELETE /api/trips/{id}/expenses/{expense_id} (Delete expense)
- GET /api/trips/{id}/history (History tab)
- POST /api/trips/{id}/close (Close trip - owner only)
- POST /api/trips/{id}/generate-invoices (Generate invoices)
- DELETE /api/trips/{id}/parcels/{parcel_id} (Remove parcel from trip)
"""

import pytest
import requests
import os
import uuid
from datetime import datetime

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', 'https://multi-warehouse-qa.preview.emergentagent.com')
SESSION_TOKEN = "demo_trips_session_1771084342772"
TRIP_ID = "trip-1"  # Trip S27 with parcels


class TestTripDetailOverview:
    """Test Overview tab - GET /api/trips/{id}/summary"""
    
    def test_trip_summary_success(self):
        """Trip summary returns complete data"""
        response = requests.get(
            f"{BASE_URL}/api/trips/{TRIP_ID}/summary",
            headers={"Authorization": f"Bearer {SESSION_TOKEN}"}
        )
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()
        
        # Check trip object exists
        assert "trip" in data, "Response should contain 'trip' object"
        assert "stats" in data, "Response should contain 'stats' object"
        
        # Check trip fields
        trip = data["trip"]
        assert "trip_number" in trip, "Trip should have trip_number"
        assert "status" in trip, "Trip should have status"
        assert "route" in trip, "Trip should have route"
        assert "departure_date" in trip, "Trip should have departure_date"
        
        # Check stats fields
        stats = data["stats"]
        required_stats = ["total_parcels", "total_weight", "total_clients", "invoiced_value", "loading_percentage"]
        for field in required_stats:
            assert field in stats, f"Stats should contain {field}"
        
        print(f"✓ Trip summary: {trip['trip_number']} - Status: {trip['status']}")
        print(f"✓ Stats: {stats['total_parcels']} parcels, {stats['total_weight']} kg")
    
    def test_trip_summary_includes_vehicle_driver(self):
        """Trip summary includes vehicle and driver info when assigned"""
        response = requests.get(
            f"{BASE_URL}/api/trips/{TRIP_ID}/summary",
            headers={"Authorization": f"Bearer {SESSION_TOKEN}"}
        )
        assert response.status_code == 200
        data = response.json()
        
        trip = data["trip"]
        # Vehicle and driver can be null but fields should exist
        assert "vehicle" in trip or trip.get("vehicle_id") is None, "Trip should have vehicle field or null vehicle_id"
        assert "driver" in trip or trip.get("driver_id") is None, "Trip should have driver field or null driver_id"
        
        print(f"✓ Vehicle: {trip.get('vehicle', 'Not assigned')}")
        print(f"✓ Driver: {trip.get('driver', 'Not assigned')}")
    
    def test_trip_summary_404_not_found(self):
        """Trip summary returns 404 for non-existent trip"""
        response = requests.get(
            f"{BASE_URL}/api/trips/non-existent-trip-id/summary",
            headers={"Authorization": f"Bearer {SESSION_TOKEN}"}
        )
        assert response.status_code == 404
        print("✓ Returns 404 for non-existent trip")
    
    def test_trip_summary_401_unauthorized(self):
        """Trip summary requires authentication"""
        response = requests.get(f"{BASE_URL}/api/trips/{TRIP_ID}/summary")
        assert response.status_code == 401
        print("✓ Returns 401 without authentication")


class TestTripDetailParcels:
    """Test Parcels tab - GET /api/trips/{id}/parcels and DELETE parcel"""
    
    def test_get_trip_parcels_all(self):
        """Get all parcels for a trip"""
        response = requests.get(
            f"{BASE_URL}/api/trips/{TRIP_ID}/parcels",
            headers={"Authorization": f"Bearer {SESSION_TOKEN}"}
        )
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()
        
        assert isinstance(data, list), "Response should be a list"
        if len(data) > 0:
            parcel = data[0]
            assert "id" in parcel, "Parcel should have id"
            assert "client_name" in parcel, "Parcel should have client_name"
            assert "status" in parcel, "Parcel should have status"
            assert "piece_count" in parcel, "Parcel should have piece_count"
            print(f"✓ Got {len(data)} parcels with client names")
        else:
            print("✓ No parcels on this trip (empty list)")
    
    def test_get_trip_parcels_filter_not_loaded(self):
        """Filter parcels by not_loaded status"""
        response = requests.get(
            f"{BASE_URL}/api/trips/{TRIP_ID}/parcels?status=not_loaded",
            headers={"Authorization": f"Bearer {SESSION_TOKEN}"}
        )
        assert response.status_code == 200
        data = response.json()
        
        # All returned parcels should be in warehouse or staged status
        for parcel in data:
            assert parcel["status"] in ["warehouse", "staged"], f"Expected warehouse/staged, got {parcel['status']}"
        
        print(f"✓ Filtered not_loaded: {len(data)} parcels")
    
    def test_get_trip_parcels_filter_loaded(self):
        """Filter parcels by loaded status"""
        response = requests.get(
            f"{BASE_URL}/api/trips/{TRIP_ID}/parcels?status=loaded",
            headers={"Authorization": f"Bearer {SESSION_TOKEN}"}
        )
        assert response.status_code == 200
        data = response.json()
        
        for parcel in data:
            assert parcel["status"] == "loaded", f"Expected loaded, got {parcel['status']}"
        
        print(f"✓ Filtered loaded: {len(data)} parcels")
    
    def test_get_trip_parcels_filter_delivered(self):
        """Filter parcels by delivered status"""
        response = requests.get(
            f"{BASE_URL}/api/trips/{TRIP_ID}/parcels?status=delivered",
            headers={"Authorization": f"Bearer {SESSION_TOKEN}"}
        )
        assert response.status_code == 200
        data = response.json()
        
        for parcel in data:
            assert parcel["status"] == "delivered", f"Expected delivered, got {parcel['status']}"
        
        print(f"✓ Filtered delivered: {len(data)} parcels")
    
    def test_remove_parcel_from_trip_404_not_found(self):
        """Remove parcel returns 404 for non-existent parcel"""
        response = requests.delete(
            f"{BASE_URL}/api/trips/{TRIP_ID}/parcels/non-existent-parcel-id",
            headers={"Authorization": f"Bearer {SESSION_TOKEN}"}
        )
        assert response.status_code == 404
        print("✓ Returns 404 for non-existent parcel")


class TestTripDetailClientsSummary:
    """Test Clients & Invoicing tab - GET /api/trips/{id}/clients-summary"""
    
    def test_get_clients_summary(self):
        """Get client summary for trip"""
        response = requests.get(
            f"{BASE_URL}/api/trips/{TRIP_ID}/clients-summary",
            headers={"Authorization": f"Bearer {SESSION_TOKEN}"}
        )
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()
        
        assert "clients" in data, "Response should have 'clients' array"
        assert "totals" in data, "Response should have 'totals' object"
        
        # Check totals structure
        totals = data["totals"]
        required_totals = ["total_clients", "total_parcels", "total_weight"]
        for field in required_totals:
            assert field in totals, f"Totals should contain {field}"
        
        # Check client structure if any clients
        if len(data["clients"]) > 0:
            client = data["clients"][0]
            assert "client_id" in client, "Client should have client_id"
            assert "client_name" in client, "Client should have client_name"
            assert "parcel_count" in client, "Client should have parcel_count"
            assert "total_weight" in client, "Client should have total_weight"
            assert "invoices" in client, "Client should have invoices array"
        
        print(f"✓ Got summary for {len(data['clients'])} clients")
        print(f"✓ Totals: {totals}")
    
    def test_clients_summary_404_not_found(self):
        """Clients summary returns 404 for non-existent trip"""
        response = requests.get(
            f"{BASE_URL}/api/trips/non-existent-trip/clients-summary",
            headers={"Authorization": f"Bearer {SESSION_TOKEN}"}
        )
        assert response.status_code == 404
        print("✓ Returns 404 for non-existent trip")


class TestTripDetailExpenses:
    """Test Expenses tab - GET/POST/DELETE expenses"""
    
    def test_get_trip_expenses(self):
        """Get all expenses for a trip"""
        response = requests.get(
            f"{BASE_URL}/api/trips/{TRIP_ID}/expenses",
            headers={"Authorization": f"Bearer {SESSION_TOKEN}"}
        )
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()
        
        assert isinstance(data, list), "Response should be a list"
        if len(data) > 0:
            expense = data[0]
            assert "id" in expense, "Expense should have id"
            assert "category" in expense, "Expense should have category"
            assert "amount" in expense, "Expense should have amount"
            assert "currency" in expense, "Expense should have currency"
        
        print(f"✓ Got {len(data)} expenses for trip")
    
    def test_add_expense_fuel(self):
        """Add a fuel expense to trip"""
        expense_data = {
            "category": "fuel",
            "amount": 1500.00,
            "currency": "ZAR",
            "expense_date": datetime.now().strftime("%Y-%m-%d"),
            "description": "TEST_ Diesel refuel at Shell station"
        }
        response = requests.post(
            f"{BASE_URL}/api/trips/{TRIP_ID}/expenses",
            json=expense_data,
            headers={"Authorization": f"Bearer {SESSION_TOKEN}"}
        )
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()
        
        assert "id" in data, "Response should contain expense id"
        assert data["category"] == "fuel"
        assert data["amount"] == 1500.00
        assert data["currency"] == "ZAR"
        
        # Store for cleanup
        TestTripDetailExpenses.created_expense_id = data["id"]
        print(f"✓ Created fuel expense: {data['id']}")
    
    def test_add_expense_tolls(self):
        """Add a tolls expense to trip"""
        expense_data = {
            "category": "tolls",
            "amount": 350.00,
            "currency": "ZAR",
            "expense_date": datetime.now().strftime("%Y-%m-%d"),
            "description": "TEST_ N1 toll fees"
        }
        response = requests.post(
            f"{BASE_URL}/api/trips/{TRIP_ID}/expenses",
            json=expense_data,
            headers={"Authorization": f"Bearer {SESSION_TOKEN}"}
        )
        assert response.status_code == 200
        data = response.json()
        
        assert data["category"] == "tolls"
        TestTripDetailExpenses.created_toll_expense_id = data["id"]
        print(f"✓ Created tolls expense: {data['id']}")
    
    def test_add_expense_border_fees(self):
        """Add border fees expense"""
        expense_data = {
            "category": "border_fees",
            "amount": 2500.00,
            "currency": "ZAR",
            "expense_date": datetime.now().strftime("%Y-%m-%d"),
            "description": "TEST_ Beitbridge border processing"
        }
        response = requests.post(
            f"{BASE_URL}/api/trips/{TRIP_ID}/expenses",
            json=expense_data,
            headers={"Authorization": f"Bearer {SESSION_TOKEN}"}
        )
        assert response.status_code == 200
        data = response.json()
        assert data["category"] == "border_fees"
        TestTripDetailExpenses.created_border_expense_id = data["id"]
        print(f"✓ Created border_fees expense: {data['id']}")
    
    def test_add_expense_repairs(self):
        """Add repairs expense"""
        expense_data = {
            "category": "repairs",
            "amount": 800.00,
            "currency": "ZAR",
            "expense_date": datetime.now().strftime("%Y-%m-%d"),
            "description": "TEST_ Tire puncture repair"
        }
        response = requests.post(
            f"{BASE_URL}/api/trips/{TRIP_ID}/expenses",
            json=expense_data,
            headers={"Authorization": f"Bearer {SESSION_TOKEN}"}
        )
        assert response.status_code == 200
        data = response.json()
        assert data["category"] == "repairs"
        TestTripDetailExpenses.created_repairs_expense_id = data["id"]
        print(f"✓ Created repairs expense: {data['id']}")
    
    def test_add_expense_food(self):
        """Add food expense"""
        expense_data = {
            "category": "food",
            "amount": 250.00,
            "currency": "ZAR",
            "expense_date": datetime.now().strftime("%Y-%m-%d"),
            "description": "TEST_ Driver meals"
        }
        response = requests.post(
            f"{BASE_URL}/api/trips/{TRIP_ID}/expenses",
            json=expense_data,
            headers={"Authorization": f"Bearer {SESSION_TOKEN}"}
        )
        assert response.status_code == 200
        data = response.json()
        assert data["category"] == "food"
        TestTripDetailExpenses.created_food_expense_id = data["id"]
        print(f"✓ Created food expense: {data['id']}")
    
    def test_add_expense_accommodation(self):
        """Add accommodation expense"""
        expense_data = {
            "category": "accommodation",
            "amount": 600.00,
            "currency": "ZAR",
            "expense_date": datetime.now().strftime("%Y-%m-%d"),
            "description": "TEST_ Overnight stay in Harare"
        }
        response = requests.post(
            f"{BASE_URL}/api/trips/{TRIP_ID}/expenses",
            json=expense_data,
            headers={"Authorization": f"Bearer {SESSION_TOKEN}"}
        )
        assert response.status_code == 200
        data = response.json()
        assert data["category"] == "accommodation"
        TestTripDetailExpenses.created_accommodation_expense_id = data["id"]
        print(f"✓ Created accommodation expense: {data['id']}")
    
    def test_add_expense_other(self):
        """Add other category expense"""
        expense_data = {
            "category": "other",
            "amount": 100.00,
            "currency": "ZAR",
            "expense_date": datetime.now().strftime("%Y-%m-%d"),
            "description": "TEST_ Miscellaneous supplies"
        }
        response = requests.post(
            f"{BASE_URL}/api/trips/{TRIP_ID}/expenses",
            json=expense_data,
            headers={"Authorization": f"Bearer {SESSION_TOKEN}"}
        )
        assert response.status_code == 200
        data = response.json()
        assert data["category"] == "other"
        TestTripDetailExpenses.created_other_expense_id = data["id"]
        print(f"✓ Created other expense: {data['id']}")
    
    def test_delete_expense(self):
        """Delete an expense"""
        # Use the fuel expense we created
        expense_id = getattr(TestTripDetailExpenses, 'created_expense_id', None)
        if not expense_id:
            pytest.skip("No expense created to delete")
        
        response = requests.delete(
            f"{BASE_URL}/api/trips/{TRIP_ID}/expenses/{expense_id}",
            headers={"Authorization": f"Bearer {SESSION_TOKEN}"}
        )
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        # Verify expense is deleted
        response = requests.get(
            f"{BASE_URL}/api/trips/{TRIP_ID}/expenses",
            headers={"Authorization": f"Bearer {SESSION_TOKEN}"}
        )
        expenses = response.json()
        expense_ids = [e["id"] for e in expenses]
        assert expense_id not in expense_ids, "Deleted expense should not be in list"
        
        print(f"✓ Deleted expense: {expense_id}")
    
    def test_delete_expense_404_not_found(self):
        """Delete non-existent expense returns 404"""
        response = requests.delete(
            f"{BASE_URL}/api/trips/{TRIP_ID}/expenses/non-existent-expense-id",
            headers={"Authorization": f"Bearer {SESSION_TOKEN}"}
        )
        assert response.status_code == 404
        print("✓ Returns 404 for non-existent expense")
    
    @pytest.fixture(autouse=True, scope="class")
    def cleanup_test_expenses(self, request):
        """Cleanup test expenses after all tests in class"""
        yield
        # Cleanup created expenses
        expense_ids = [
            getattr(TestTripDetailExpenses, 'created_toll_expense_id', None),
            getattr(TestTripDetailExpenses, 'created_border_expense_id', None),
            getattr(TestTripDetailExpenses, 'created_repairs_expense_id', None),
            getattr(TestTripDetailExpenses, 'created_food_expense_id', None),
            getattr(TestTripDetailExpenses, 'created_accommodation_expense_id', None),
            getattr(TestTripDetailExpenses, 'created_other_expense_id', None),
        ]
        for expense_id in expense_ids:
            if expense_id:
                requests.delete(
                    f"{BASE_URL}/api/trips/{TRIP_ID}/expenses/{expense_id}",
                    headers={"Authorization": f"Bearer {SESSION_TOKEN}"}
                )


class TestTripDetailHistory:
    """Test History tab - GET /api/trips/{id}/history"""
    
    def test_get_trip_history_all(self):
        """Get all history for a trip"""
        response = requests.get(
            f"{BASE_URL}/api/trips/{TRIP_ID}/history",
            headers={"Authorization": f"Bearer {SESSION_TOKEN}"}
        )
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()
        
        assert isinstance(data, list), "Response should be a list"
        if len(data) > 0:
            log = data[0]
            assert "action" in log, "Log should have action"
            assert "table_name" in log, "Log should have table_name"
            assert "user_name" in log, "Log should have user_name"
        
        print(f"✓ Got {len(data)} history records")
    
    def test_get_trip_history_filter_parcels(self):
        """Filter history by parcels"""
        response = requests.get(
            f"{BASE_URL}/api/trips/{TRIP_ID}/history?filter_type=parcels",
            headers={"Authorization": f"Bearer {SESSION_TOKEN}"}
        )
        assert response.status_code == 200
        data = response.json()
        
        # All returned logs should be related to shipments or trips
        for log in data:
            assert log["table_name"] in ["trips", "shipments"], f"Expected trips/shipments, got {log['table_name']}"
        
        print(f"✓ Filtered parcels history: {len(data)} records")
    
    def test_get_trip_history_filter_expenses(self):
        """Filter history by expenses"""
        response = requests.get(
            f"{BASE_URL}/api/trips/{TRIP_ID}/history?filter_type=expenses",
            headers={"Authorization": f"Bearer {SESSION_TOKEN}"}
        )
        assert response.status_code == 200
        data = response.json()
        print(f"✓ Filtered expenses history: {len(data)} records")
    
    def test_get_trip_history_filter_invoices(self):
        """Filter history by invoices"""
        response = requests.get(
            f"{BASE_URL}/api/trips/{TRIP_ID}/history?filter_type=invoices",
            headers={"Authorization": f"Bearer {SESSION_TOKEN}"}
        )
        assert response.status_code == 200
        data = response.json()
        print(f"✓ Filtered invoices history: {len(data)} records")
    
    def test_get_trip_history_filter_status(self):
        """Filter history by status changes"""
        response = requests.get(
            f"{BASE_URL}/api/trips/{TRIP_ID}/history?filter_type=status",
            headers={"Authorization": f"Bearer {SESSION_TOKEN}"}
        )
        assert response.status_code == 200
        data = response.json()
        print(f"✓ Filtered status history: {len(data)} records")
    
    def test_trip_history_404_not_found(self):
        """History returns 404 for non-existent trip"""
        response = requests.get(
            f"{BASE_URL}/api/trips/non-existent-trip/history",
            headers={"Authorization": f"Bearer {SESSION_TOKEN}"}
        )
        assert response.status_code == 404
        print("✓ Returns 404 for non-existent trip")


class TestTripCloseAndInvoices:
    """Test Close Trip and Generate Invoices functionality"""
    
    @classmethod
    def setup_class(cls):
        """Create a test trip for close/invoice testing"""
        trip_number = f"TEST_{uuid.uuid4().hex[:8].upper()}"
        trip_data = {
            "trip_number": trip_number,
            "route": ["Johannesburg", "Harare"],
            "departure_date": datetime.now().strftime("%Y-%m-%d")
        }
        response = requests.post(
            f"{BASE_URL}/api/trips",
            json=trip_data,
            headers={"Authorization": f"Bearer {SESSION_TOKEN}"}
        )
        if response.status_code == 200:
            cls.test_trip_id = response.json()["id"]
            cls.test_trip_number = trip_number
            print(f"✓ Created test trip: {trip_number}")
        else:
            cls.test_trip_id = None
            cls.test_trip_number = None
    
    def test_close_trip_owner_only(self):
        """Close trip works for owner"""
        if not TestTripCloseAndInvoices.test_trip_id:
            pytest.skip("No test trip created")
        
        response = requests.post(
            f"{BASE_URL}/api/trips/{TestTripCloseAndInvoices.test_trip_id}/close",
            headers={"Authorization": f"Bearer {SESSION_TOKEN}"}
        )
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()
        
        assert "message" in data, "Response should have message"
        assert "locked_at" in data, "Response should have locked_at"
        
        print(f"✓ Closed trip: {data['message']}")
    
    def test_close_trip_already_closed(self):
        """Cannot close an already closed trip"""
        if not TestTripCloseAndInvoices.test_trip_id:
            pytest.skip("No test trip created")
        
        response = requests.post(
            f"{BASE_URL}/api/trips/{TestTripCloseAndInvoices.test_trip_id}/close",
            headers={"Authorization": f"Bearer {SESSION_TOKEN}"}
        )
        assert response.status_code == 400, "Should return 400 for already closed trip"
        print("✓ Returns 400 for already closed trip")
    
    def test_close_trip_404_not_found(self):
        """Close trip returns 404 for non-existent trip"""
        response = requests.post(
            f"{BASE_URL}/api/trips/non-existent-trip/close",
            headers={"Authorization": f"Bearer {SESSION_TOKEN}"}
        )
        assert response.status_code == 404
        print("✓ Returns 404 for non-existent trip")
    
    def test_generate_invoices(self):
        """Generate invoices for trip"""
        response = requests.post(
            f"{BASE_URL}/api/trips/{TRIP_ID}/generate-invoices",
            headers={"Authorization": f"Bearer {SESSION_TOKEN}"}
        )
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()
        
        assert "message" in data, "Response should have message"
        assert "invoices" in data, "Response should have invoices array"
        
        print(f"✓ Generated invoices: {data['message']}")
    
    def test_generate_invoices_404_not_found(self):
        """Generate invoices returns 404 for non-existent trip"""
        response = requests.post(
            f"{BASE_URL}/api/trips/non-existent-trip/generate-invoices",
            headers={"Authorization": f"Bearer {SESSION_TOKEN}"}
        )
        assert response.status_code == 404
        print("✓ Returns 404 for non-existent trip")
    
    @classmethod
    def teardown_class(cls):
        """Cleanup test trip"""
        if cls.test_trip_id:
            # Owner can delete closed trips
            requests.delete(
                f"{BASE_URL}/api/trips/{cls.test_trip_id}",
                headers={"Authorization": f"Bearer {SESSION_TOKEN}"}
            )
            print(f"✓ Cleaned up test trip: {cls.test_trip_number}")


class TestRouteAndAssignmentUpdate:
    """Test Edit Route and Change Assignment functionality"""
    
    def test_update_route(self):
        """Update trip route"""
        update_data = {
            "route": ["Johannesburg", "Beitbridge", "Harare", "Lusaka"]
        }
        response = requests.put(
            f"{BASE_URL}/api/trips/{TRIP_ID}",
            json=update_data,
            headers={"Authorization": f"Bearer {SESSION_TOKEN}"}
        )
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()
        
        assert "route" in data, "Response should have route"
        assert len(data["route"]) == 4, f"Expected 4 stops, got {len(data['route'])}"
        
        print(f"✓ Updated route: {data['route']}")
        
        # Restore original route
        requests.put(
            f"{BASE_URL}/api/trips/{TRIP_ID}",
            json={"route": ["Johannesburg", "Beitbridge", "Harare"]},
            headers={"Authorization": f"Bearer {SESSION_TOKEN}"}
        )
    
    def test_update_vehicle_assignment(self):
        """Test update vehicle assignment (if vehicles exist)"""
        # Get available vehicles
        response = requests.get(
            f"{BASE_URL}/api/vehicles",
            headers={"Authorization": f"Bearer {SESSION_TOKEN}"}
        )
        if response.status_code != 200:
            pytest.skip("Cannot get vehicles")
        
        vehicles = response.json()
        if len(vehicles) == 0:
            pytest.skip("No vehicles available")
        
        # Update trip with vehicle
        update_data = {"vehicle_id": vehicles[0]["id"]}
        response = requests.put(
            f"{BASE_URL}/api/trips/{TRIP_ID}",
            json=update_data,
            headers={"Authorization": f"Bearer {SESSION_TOKEN}"}
        )
        assert response.status_code == 200
        print(f"✓ Updated vehicle assignment")
    
    def test_update_driver_assignment(self):
        """Test update driver assignment (if drivers exist)"""
        # Get available drivers
        response = requests.get(
            f"{BASE_URL}/api/drivers",
            headers={"Authorization": f"Bearer {SESSION_TOKEN}"}
        )
        if response.status_code != 200:
            pytest.skip("Cannot get drivers")
        
        drivers = response.json()
        if len(drivers) == 0:
            pytest.skip("No drivers available")
        
        # Update trip with driver
        update_data = {"driver_id": drivers[0]["id"]}
        response = requests.put(
            f"{BASE_URL}/api/trips/{TRIP_ID}",
            json=update_data,
            headers={"Authorization": f"Bearer {SESSION_TOKEN}"}
        )
        assert response.status_code == 200
        print(f"✓ Updated driver assignment")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
