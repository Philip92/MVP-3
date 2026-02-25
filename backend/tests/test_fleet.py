"""
Fleet Management API Tests - Phase 4
Tests vehicles, drivers, compliance items, and reminders aggregation
"""
import pytest
import requests
import os
from datetime import datetime, timedelta

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', 'https://multi-warehouse-qa.preview.emergentagent.com').rstrip('/')
SESSION_TOKEN = os.environ.get('TEST_SESSION_TOKEN', 'test_fleet_session_1771018872390')

# Shared session for authenticated requests
@pytest.fixture(scope="module")
def auth_session():
    """Session with authentication token"""
    session = requests.Session()
    session.headers.update({
        "Content-Type": "application/json",
        "Authorization": f"Bearer {SESSION_TOKEN}"
    })
    session.cookies.set("session_token", SESSION_TOKEN)
    return session


class TestHealthAndAuth:
    """Basic health and authentication tests"""
    
    def test_api_health(self, auth_session):
        """Test API is running"""
        response = auth_session.get(f"{BASE_URL}/api/")
        assert response.status_code == 200
        print("API health check passed")
    
    def test_auth_me(self, auth_session):
        """Test authentication is working"""
        response = auth_session.get(f"{BASE_URL}/api/auth/me")
        assert response.status_code == 200
        data = response.json()
        assert "id" in data
        assert "tenant_id" in data
        print(f"Authenticated as: {data.get('name')} (tenant: {data.get('tenant_name')})")


class TestVehiclesCRUD:
    """Vehicle CRUD operations"""
    
    vehicle_id = None
    
    def test_create_vehicle(self, auth_session):
        """POST /api/vehicles - Create vehicle"""
        payload = {
            "name": "TEST_MAN TGM Box Truck",
            "registration_number": "TEST-CA-123-456",
            "vin": "WDB9061331N123456",
            "make": "MAN",
            "model": "TGM",
            "year": 2022,
            "max_weight_kg": 12000,
            "max_volume_cbm": 45.5
        }
        response = auth_session.post(f"{BASE_URL}/api/vehicles", json=payload)
        assert response.status_code == 200, f"Create vehicle failed: {response.text}"
        
        data = response.json()
        assert "id" in data
        assert data["name"] == "TEST_MAN TGM Box Truck"
        assert data["registration_number"] == "TEST-CA-123-456"
        assert data["make"] == "MAN"
        assert data["status"] == "available"  # Default status
        
        TestVehiclesCRUD.vehicle_id = data["id"]
        print(f"Created vehicle: {data['id']}")
    
    def test_list_vehicles(self, auth_session):
        """GET /api/vehicles - List all vehicles"""
        response = auth_session.get(f"{BASE_URL}/api/vehicles")
        assert response.status_code == 200
        
        data = response.json()
        assert isinstance(data, list)
        # Our test vehicle should be in the list
        test_vehicles = [v for v in data if v.get("registration_number") == "TEST-CA-123-456"]
        assert len(test_vehicles) >= 1, "Created vehicle not found in list"
        
        # Verify compliance_issues field is included
        for v in data:
            assert "compliance_issues" in v
        print(f"Listed {len(data)} vehicles, found test vehicle")
    
    def test_get_vehicle(self, auth_session):
        """GET /api/vehicles/{id} - Get vehicle with compliance"""
        assert TestVehiclesCRUD.vehicle_id, "No vehicle ID from create test"
        
        response = auth_session.get(f"{BASE_URL}/api/vehicles/{TestVehiclesCRUD.vehicle_id}")
        assert response.status_code == 200
        
        data = response.json()
        assert data["id"] == TestVehiclesCRUD.vehicle_id
        assert data["name"] == "TEST_MAN TGM Box Truck"
        assert "compliance" in data  # Compliance items array included
        assert isinstance(data["compliance"], list)
        print(f"Got vehicle details with {len(data['compliance'])} compliance items")
    
    def test_update_vehicle(self, auth_session):
        """PUT /api/vehicles/{id} - Update vehicle"""
        assert TestVehiclesCRUD.vehicle_id, "No vehicle ID from create test"
        
        payload = {
            "status": "repair",
            "max_weight_kg": 14000
        }
        response = auth_session.put(f"{BASE_URL}/api/vehicles/{TestVehiclesCRUD.vehicle_id}", json=payload)
        assert response.status_code == 200
        
        data = response.json()
        assert data["status"] == "repair"
        assert data["max_weight_kg"] == 14000
        # Unchanged fields preserved
        assert data["name"] == "TEST_MAN TGM Box Truck"
        print(f"Updated vehicle status to: {data['status']}")
    
    def test_get_vehicle_not_found(self, auth_session):
        """GET /api/vehicles/{id} - 404 for non-existent vehicle"""
        response = auth_session.get(f"{BASE_URL}/api/vehicles/non-existent-id")
        assert response.status_code == 404
        print("Correctly returned 404 for non-existent vehicle")


class TestVehicleCompliance:
    """Vehicle compliance item operations"""
    
    compliance_id = None
    
    def test_add_compliance_to_vehicle(self, auth_session):
        """POST /api/vehicles/{id}/compliance - Add compliance item"""
        assert TestVehiclesCRUD.vehicle_id, "No vehicle ID from create test"
        
        # Add insurance expiring in 30 days
        future_date = (datetime.now() + timedelta(days=30)).strftime("%Y-%m-%d")
        payload = {
            "item_type": "insurance",
            "expiry_date": future_date,
            "reminder_days_before": 14,
            "provider": "TEST_Hollard Insurance",
            "policy_number": "POL-123456"
        }
        response = auth_session.post(
            f"{BASE_URL}/api/vehicles/{TestVehiclesCRUD.vehicle_id}/compliance",
            json=payload
        )
        assert response.status_code == 200, f"Add compliance failed: {response.text}"
        
        data = response.json()
        assert "id" in data
        assert data["item_type"] == "insurance"
        assert data["expiry_date"] == future_date
        assert data["provider"] == "TEST_Hollard Insurance"
        
        TestVehicleCompliance.compliance_id = data["id"]
        print(f"Added compliance item: {data['id']} (expires: {future_date})")
    
    def test_add_overdue_compliance(self, auth_session):
        """Add an overdue compliance item to test reminders"""
        assert TestVehiclesCRUD.vehicle_id, "No vehicle ID from create test"
        
        # Add license_disk that expired yesterday
        past_date = (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d")
        payload = {
            "item_type": "license_disk",
            "expiry_date": past_date,
            "reminder_days_before": 30
        }
        response = auth_session.post(
            f"{BASE_URL}/api/vehicles/{TestVehiclesCRUD.vehicle_id}/compliance",
            json=payload
        )
        assert response.status_code == 200
        print(f"Added overdue compliance item (expired: {past_date})")
    
    def test_get_vehicle_with_compliance(self, auth_session):
        """Verify vehicle details include compliance items"""
        assert TestVehiclesCRUD.vehicle_id, "No vehicle ID from create test"
        
        response = auth_session.get(f"{BASE_URL}/api/vehicles/{TestVehiclesCRUD.vehicle_id}")
        assert response.status_code == 200
        
        data = response.json()
        assert len(data["compliance"]) >= 2
        
        # Check compliance items have expected fields
        for item in data["compliance"]:
            assert "id" in item
            assert "item_type" in item
            assert "expiry_date" in item
        print(f"Vehicle has {len(data['compliance'])} compliance items")
    
    def test_delete_compliance_item(self, auth_session):
        """DELETE /api/vehicles/{id}/compliance/{id} - Delete compliance"""
        assert TestVehiclesCRUD.vehicle_id, "No vehicle ID"
        assert TestVehicleCompliance.compliance_id, "No compliance ID"
        
        response = auth_session.delete(
            f"{BASE_URL}/api/vehicles/{TestVehiclesCRUD.vehicle_id}/compliance/{TestVehicleCompliance.compliance_id}"
        )
        assert response.status_code == 200
        
        data = response.json()
        assert data["message"] == "Compliance item deleted"
        print(f"Deleted compliance item: {TestVehicleCompliance.compliance_id}")


class TestDriversCRUD:
    """Driver CRUD operations"""
    
    driver_id = None
    
    def test_create_driver(self, auth_session):
        """POST /api/drivers - Create driver"""
        payload = {
            "name": "TEST_John Moyo",
            "phone": "+27123456789",
            "email": "john.moyo@test.com",
            "id_passport_number": "8801015001088",
            "nationality": "South African"
        }
        response = auth_session.post(f"{BASE_URL}/api/drivers", json=payload)
        assert response.status_code == 200, f"Create driver failed: {response.text}"
        
        data = response.json()
        assert "id" in data
        assert data["name"] == "TEST_John Moyo"
        assert data["phone"] == "+27123456789"
        assert data["status"] == "available"  # Default status
        
        TestDriversCRUD.driver_id = data["id"]
        print(f"Created driver: {data['id']}")
    
    def test_list_drivers(self, auth_session):
        """GET /api/drivers - List all drivers"""
        response = auth_session.get(f"{BASE_URL}/api/drivers")
        assert response.status_code == 200
        
        data = response.json()
        assert isinstance(data, list)
        
        # Our test driver should be in the list
        test_drivers = [d for d in data if d.get("phone") == "+27123456789"]
        assert len(test_drivers) >= 1, "Created driver not found in list"
        
        # Verify compliance_issues field is included
        for d in data:
            assert "compliance_issues" in d
        print(f"Listed {len(data)} drivers, found test driver")
    
    def test_get_driver(self, auth_session):
        """GET /api/drivers/{id} - Get driver with compliance"""
        assert TestDriversCRUD.driver_id, "No driver ID from create test"
        
        response = auth_session.get(f"{BASE_URL}/api/drivers/{TestDriversCRUD.driver_id}")
        assert response.status_code == 200
        
        data = response.json()
        assert data["id"] == TestDriversCRUD.driver_id
        assert data["name"] == "TEST_John Moyo"
        assert "compliance" in data
        assert isinstance(data["compliance"], list)
        print(f"Got driver details with {len(data['compliance'])} compliance items")
    
    def test_update_driver(self, auth_session):
        """PUT /api/drivers/{id} - Update driver"""
        assert TestDriversCRUD.driver_id, "No driver ID from create test"
        
        payload = {
            "status": "on_trip",
            "phone": "+27987654321"
        }
        response = auth_session.put(f"{BASE_URL}/api/drivers/{TestDriversCRUD.driver_id}", json=payload)
        assert response.status_code == 200
        
        data = response.json()
        assert data["status"] == "on_trip"
        assert data["phone"] == "+27987654321"
        # Unchanged fields preserved
        assert data["name"] == "TEST_John Moyo"
        print(f"Updated driver status to: {data['status']}")
    
    def test_get_driver_not_found(self, auth_session):
        """GET /api/drivers/{id} - 404 for non-existent driver"""
        response = auth_session.get(f"{BASE_URL}/api/drivers/non-existent-id")
        assert response.status_code == 404
        print("Correctly returned 404 for non-existent driver")


class TestDriverCompliance:
    """Driver compliance item operations"""
    
    compliance_id = None
    
    def test_add_compliance_to_driver(self, auth_session):
        """POST /api/drivers/{id}/compliance - Add compliance item"""
        assert TestDriversCRUD.driver_id, "No driver ID from create test"
        
        # Add license expiring in 60 days
        future_date = (datetime.now() + timedelta(days=60)).strftime("%Y-%m-%d")
        payload = {
            "item_type": "license",
            "expiry_date": future_date,
            "reminder_days_before": 30,
            "license_number": "TEST-DL-2023-12345",
            "issuing_country": "South Africa"
        }
        response = auth_session.post(
            f"{BASE_URL}/api/drivers/{TestDriversCRUD.driver_id}/compliance",
            json=payload
        )
        assert response.status_code == 200, f"Add compliance failed: {response.text}"
        
        data = response.json()
        assert "id" in data
        assert data["item_type"] == "license"
        assert data["license_number"] == "TEST-DL-2023-12345"
        
        TestDriverCompliance.compliance_id = data["id"]
        print(f"Added driver compliance: {data['id']} (expires: {future_date})")
    
    def test_add_expiring_soon_compliance(self, auth_session):
        """Add compliance expiring this week"""
        assert TestDriversCRUD.driver_id, "No driver ID"
        
        # Work permit expiring in 3 days
        soon_date = (datetime.now() + timedelta(days=3)).strftime("%Y-%m-%d")
        payload = {
            "item_type": "work_permit",
            "expiry_date": soon_date,
            "reminder_days_before": 14,
            "issuing_country": "Zimbabwe"
        }
        response = auth_session.post(
            f"{BASE_URL}/api/drivers/{TestDriversCRUD.driver_id}/compliance",
            json=payload
        )
        assert response.status_code == 200
        print(f"Added driver compliance expiring soon: {soon_date}")
    
    def test_delete_driver_compliance(self, auth_session):
        """DELETE /api/drivers/{id}/compliance/{id} - Delete compliance"""
        assert TestDriversCRUD.driver_id, "No driver ID"
        assert TestDriverCompliance.compliance_id, "No compliance ID"
        
        response = auth_session.delete(
            f"{BASE_URL}/api/drivers/{TestDriversCRUD.driver_id}/compliance/{TestDriverCompliance.compliance_id}"
        )
        assert response.status_code == 200
        
        data = response.json()
        assert data["message"] == "Compliance item deleted"
        print(f"Deleted driver compliance: {TestDriverCompliance.compliance_id}")


class TestRemindersAggregation:
    """Compliance reminders aggregation view"""
    
    def test_get_reminders(self, auth_session):
        """GET /api/reminders - Get compliance reminders grouped by urgency"""
        response = auth_session.get(f"{BASE_URL}/api/reminders")
        assert response.status_code == 200
        
        data = response.json()
        
        # Check structure
        assert "reminders" in data
        assert "summary" in data
        
        # Check reminders categories
        reminders = data["reminders"]
        assert "overdue" in reminders
        assert "due_this_week" in reminders
        assert "due_this_month" in reminders
        assert "upcoming" in reminders
        
        # Check summary
        summary = data["summary"]
        assert "overdue" in summary
        assert "due_this_week" in summary
        assert "due_this_month" in summary
        assert "total" in summary
        
        # Based on our test data:
        # - We added an overdue vehicle compliance (license_disk expired yesterday)
        # - We added a driver compliance expiring in 3 days (due_this_week)
        print(f"Reminders summary: overdue={summary['overdue']}, "
              f"due_this_week={summary['due_this_week']}, "
              f"due_this_month={summary['due_this_month']}, "
              f"total={summary['total']}")
        
        # Verify reminder item structure
        for category in ["overdue", "due_this_week", "due_this_month"]:
            for item in reminders[category]:
                assert "type" in item  # 'vehicle' or 'driver'
                assert "entity_id" in item
                assert "entity_name" in item
                assert "item_type" in item
                assert "item_label" in item
                assert "expiry_date" in item
        
        print("Reminders aggregation structure validated")


class TestCleanup:
    """Cleanup test data"""
    
    def test_delete_vehicle(self, auth_session):
        """DELETE /api/vehicles/{id} - Delete vehicle and compliance"""
        if not TestVehiclesCRUD.vehicle_id:
            pytest.skip("No vehicle to delete")
        
        response = auth_session.delete(f"{BASE_URL}/api/vehicles/{TestVehiclesCRUD.vehicle_id}")
        assert response.status_code == 200
        
        data = response.json()
        assert data["message"] == "Vehicle deleted"
        
        # Verify vehicle is gone
        get_response = auth_session.get(f"{BASE_URL}/api/vehicles/{TestVehiclesCRUD.vehicle_id}")
        assert get_response.status_code == 404
        print(f"Deleted vehicle and verified removal")
    
    def test_delete_driver(self, auth_session):
        """DELETE /api/drivers/{id} - Delete driver and compliance"""
        if not TestDriversCRUD.driver_id:
            pytest.skip("No driver to delete")
        
        response = auth_session.delete(f"{BASE_URL}/api/drivers/{TestDriversCRUD.driver_id}")
        assert response.status_code == 200
        
        data = response.json()
        assert data["message"] == "Driver deleted"
        
        # Verify driver is gone
        get_response = auth_session.get(f"{BASE_URL}/api/drivers/{TestDriversCRUD.driver_id}")
        assert get_response.status_code == 404
        print(f"Deleted driver and verified removal")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
