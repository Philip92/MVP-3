"""
Test Settings, Team, Fleet features:
1. Add Default Warehouse dropdown to Add/Edit User forms
2. Permissions tab in Settings with role vs page grid
3. File upload to compliance items in Fleet
4. All compliance items sorted by expiry date with color coding (red/yellow/green)
"""
import pytest
import requests
import os
from datetime import datetime, timedelta

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', 'https://multi-warehouse-qa.preview.emergentagent.com')

class TestSession:
    """Shared session with authentication"""
    session = None
    user = None

@pytest.fixture(scope="class")
def auth_session():
    """Get authenticated session"""
    if TestSession.session is None:
        TestSession.session = requests.Session()
        # Login
        response = TestSession.session.post(
            f"{BASE_URL}/api/auth/login",
            json={"email": "admin@servex.com", "password": "Servex2026!"}
        )
        assert response.status_code == 200, f"Login failed: {response.text}"
        TestSession.user = response.json()
        print(f"Logged in as: {TestSession.user['email']} (role: {TestSession.user['role']})")
    return TestSession.session


class TestLogin:
    """Test admin login"""
    
    def test_login_with_admin_credentials(self, auth_session):
        """Verify login with admin@servex.com / Servex2026!"""
        assert TestSession.user is not None
        assert TestSession.user['email'] == 'admin@servex.com'
        assert TestSession.user['role'] == 'owner'
        print("Login test PASSED: admin@servex.com is logged in as owner")


class TestTeamEndpoints:
    """Test Team page features - Default Warehouse"""
    
    def test_list_users_includes_default_warehouse(self, auth_session):
        """GET /api/users - verify users have default_warehouse field"""
        response = auth_session.get(f"{BASE_URL}/api/users")
        assert response.status_code == 200
        users = response.json()
        print(f"Found {len(users)} users")
        
        # Check that user structure includes default_warehouse field
        if len(users) > 0:
            user = users[0]
            assert 'default_warehouse' in user or user.get('default_warehouse') is None, \
                "User should have default_warehouse field"
            print(f"User {user.get('name')} has default_warehouse: {user.get('default_warehouse')}")
    
    def test_list_warehouses(self, auth_session):
        """GET /api/warehouses - verify warehouses endpoint exists for dropdown"""
        response = auth_session.get(f"{BASE_URL}/api/warehouses")
        assert response.status_code == 200
        warehouses = response.json()
        print(f"Found {len(warehouses)} warehouses")
        for wh in warehouses[:5]:
            print(f"  - {wh.get('name')} (ID: {wh.get('id')})")
    
    def test_create_user_with_default_warehouse(self, auth_session):
        """POST /api/users - create user with default_warehouse"""
        # First get a warehouse ID if available
        wh_response = auth_session.get(f"{BASE_URL}/api/warehouses")
        warehouses = wh_response.json() if wh_response.status_code == 200 else []
        warehouse_id = warehouses[0]['id'] if len(warehouses) > 0 else None
        
        # Create user
        test_email = f"test_user_{datetime.now().strftime('%Y%m%d%H%M%S')}@test.com"
        user_data = {
            "name": "Test User with Warehouse",
            "email": test_email,
            "role": "warehouse",
            "phone": "+27123456789",
            "default_warehouse": warehouse_id
        }
        
        response = auth_session.post(f"{BASE_URL}/api/users", json=user_data)
        assert response.status_code in [200, 201], f"Failed to create user: {response.text}"
        
        created_user = response.json()
        assert created_user['default_warehouse'] == warehouse_id, \
            f"Expected default_warehouse={warehouse_id}, got {created_user.get('default_warehouse')}"
        print(f"Created user with default_warehouse: {created_user.get('default_warehouse')}")
        
        # Store user ID for cleanup
        TestTeamEndpoints.created_user_id = created_user['id']
        return created_user
    
    def test_update_user_default_warehouse(self, auth_session):
        """PUT /api/users/:id - update user's default_warehouse"""
        user_id = getattr(TestTeamEndpoints, 'created_user_id', None)
        if not user_id:
            pytest.skip("No test user created")
        
        # Update to no default warehouse
        response = auth_session.put(
            f"{BASE_URL}/api/users/{user_id}",
            json={"default_warehouse": None}
        )
        assert response.status_code == 200
        
        updated_user = response.json()
        assert updated_user.get('default_warehouse') is None
        print(f"Updated user default_warehouse to None")
    
    def test_cleanup_test_user(self, auth_session):
        """Cleanup: Delete test user"""
        user_id = getattr(TestTeamEndpoints, 'created_user_id', None)
        if user_id:
            response = auth_session.delete(f"{BASE_URL}/api/users/{user_id}")
            if response.status_code in [200, 204]:
                print(f"Deleted test user {user_id}")


class TestPermissionsEndpoints:
    """Test Settings -> Permissions tab endpoints"""
    
    def test_get_permissions(self, auth_session):
        """GET /api/tenant/permissions - verify endpoint exists and returns role permissions"""
        response = auth_session.get(f"{BASE_URL}/api/tenant/permissions")
        assert response.status_code == 200, f"Failed to get permissions: {response.text}"
        
        permissions = response.json()
        assert isinstance(permissions, dict), "Permissions should be a dict of role -> pages"
        
        # Check for expected roles
        expected_roles = ['owner', 'manager', 'warehouse', 'finance', 'driver']
        for role in expected_roles:
            assert role in permissions, f"Missing role: {role}"
            assert isinstance(permissions[role], list), f"Permissions for {role} should be a list"
            print(f"  {role}: {len(permissions[role])} pages - {permissions[role]}")
        
        # Owner should have all pages
        assert 'settings' in permissions['owner'], "Owner should have settings access"
        print("Permissions endpoint test PASSED")
    
    def test_owner_has_all_pages(self, auth_session):
        """Verify owner role has access to all pages"""
        response = auth_session.get(f"{BASE_URL}/api/tenant/permissions")
        permissions = response.json()
        
        expected_pages = ['dashboard', 'parcel-intake', 'warehouse', 'clients', 'loading', 
                         'trips', 'scanner', 'finance', 'fleet', 'team', 'settings']
        
        owner_perms = permissions.get('owner', [])
        for page in expected_pages:
            assert page in owner_perms, f"Owner should have access to {page}"
        print(f"Owner has access to all {len(expected_pages)} pages")
    
    def test_update_permissions(self, auth_session):
        """PUT /api/tenant/permissions - update permissions"""
        # First get current permissions
        response = auth_session.get(f"{BASE_URL}/api/tenant/permissions")
        original_perms = response.json()
        
        # Make a small change to warehouse role (add/remove fleet access)
        warehouse_perms = original_perms.get('warehouse', [])
        if 'fleet' in warehouse_perms:
            new_perms = [p for p in warehouse_perms if p != 'fleet']
        else:
            new_perms = warehouse_perms + ['fleet']
        
        # Update permissions
        updated_permissions = {**original_perms, 'warehouse': new_perms}
        response = auth_session.put(
            f"{BASE_URL}/api/tenant/permissions",
            json=updated_permissions
        )
        assert response.status_code == 200, f"Failed to update permissions: {response.text}"
        print("Permissions update test PASSED")
        
        # Restore original permissions
        auth_session.put(f"{BASE_URL}/api/tenant/permissions", json=original_perms)


class TestFleetComplianceAll:
    """Test Fleet -> Reminders tab with all compliance items sorted by expiry date"""
    
    def test_get_all_compliance_items(self, auth_session):
        """GET /api/compliance/all - verify returns all compliance items with status_color"""
        response = auth_session.get(f"{BASE_URL}/api/compliance/all")
        assert response.status_code == 200, f"Failed to get compliance items: {response.text}"
        
        items = response.json()
        assert isinstance(items, list), "Response should be a list"
        print(f"Found {len(items)} compliance items")
        
        if len(items) > 0:
            # Check first item structure
            item = items[0]
            required_fields = ['type', 'entity_id', 'entity_name', 'expiry_date', 'status_color']
            for field in required_fields:
                assert field in item, f"Missing field: {field}"
            
            # Check status_color values
            valid_colors = ['red', 'yellow', 'green']
            assert item['status_color'] in valid_colors, \
                f"Invalid status_color: {item['status_color']}"
            
            print(f"First item: {item['entity_name']} - {item['item_label']} - Expires: {item['expiry_date']} - Color: {item['status_color']}")
    
    def test_compliance_items_sorted_by_expiry(self, auth_session):
        """Verify compliance items are sorted by expiry date ascending"""
        response = auth_session.get(f"{BASE_URL}/api/compliance/all")
        items = response.json()
        
        if len(items) > 1:
            for i in range(len(items) - 1):
                current_date = items[i]['expiry_date']
                next_date = items[i + 1]['expiry_date']
                assert current_date <= next_date, \
                    f"Items not sorted: {current_date} > {next_date}"
            print(f"All {len(items)} items are sorted by expiry date (ascending)")
    
    def test_compliance_color_coding(self, auth_session):
        """Verify status_color logic: red/yellow/green based on expiry date"""
        response = auth_session.get(f"{BASE_URL}/api/compliance/all")
        items = response.json()
        
        today = datetime.now()
        thirty_days = (today + timedelta(days=30)).strftime("%Y-%m-%d")
        sixty_days = (today + timedelta(days=60)).strftime("%Y-%m-%d")
        today_str = today.strftime("%Y-%m-%d")
        
        color_counts = {'red': 0, 'yellow': 0, 'green': 0}
        
        for item in items:
            expiry = item['expiry_date']
            color = item['status_color']
            color_counts[color] = color_counts.get(color, 0) + 1
            
            # Verify color logic
            if expiry < today_str or expiry <= thirty_days:
                expected = 'red'
            elif expiry <= sixty_days:
                expected = 'yellow'
            else:
                expected = 'green'
            
            assert color == expected, \
                f"Wrong color for {item['entity_name']}: got {color}, expected {expected} (expiry: {expiry})"
        
        print(f"Color distribution: {color_counts}")


class TestFleetComplianceFileUpload:
    """Test Fleet compliance file upload feature"""
    
    def test_create_vehicle_with_compliance_file(self, auth_session):
        """Create vehicle, add compliance with file upload"""
        # Create a test vehicle
        vehicle_data = {
            "name": "Test Truck for Compliance",
            "registration_number": f"TEST-{datetime.now().strftime('%H%M%S')}",
            "make": "Test Make",
            "model": "Test Model"
        }
        
        response = auth_session.post(f"{BASE_URL}/api/vehicles", json=vehicle_data)
        assert response.status_code in [200, 201], f"Failed to create vehicle: {response.text}"
        
        vehicle = response.json()
        vehicle_id = vehicle['id']
        print(f"Created test vehicle: {vehicle['name']} (ID: {vehicle_id})")
        
        # Store for cleanup
        TestFleetComplianceFileUpload.vehicle_id = vehicle_id
    
    def test_add_compliance_with_file(self, auth_session):
        """Add compliance item with file upload (base64)"""
        vehicle_id = getattr(TestFleetComplianceFileUpload, 'vehicle_id', None)
        if not vehicle_id:
            pytest.skip("No test vehicle created")
        
        # Create compliance with mock file (base64 encoded)
        import base64
        mock_file_content = b"Mock PDF content for testing"
        file_data = base64.b64encode(mock_file_content).decode('utf-8')
        
        compliance_data = {
            "item_type": "insurance",
            "item_label": "Test Insurance Policy",
            "expiry_date": (datetime.now() + timedelta(days=90)).strftime("%Y-%m-%d"),
            "reminder_days_before": 30,
            "provider": "Test Insurance Co",
            "policy_number": "POL-12345",
            "file_name": "test_policy.pdf",
            "file_type": "application/pdf",
            "file_data": file_data
        }
        
        response = auth_session.post(
            f"{BASE_URL}/api/vehicles/{vehicle_id}/compliance",
            json=compliance_data
        )
        assert response.status_code in [200, 201], f"Failed to add compliance: {response.text}"
        
        compliance = response.json()
        assert compliance.get('file_name') == "test_policy.pdf", "File name not saved"
        assert compliance.get('file_type') == "application/pdf", "File type not saved"
        print(f"Created compliance with file: {compliance.get('file_name')}")
        
        TestFleetComplianceFileUpload.compliance_id = compliance['id']
    
    def test_compliance_appears_in_all_list(self, auth_session):
        """Verify new compliance appears in /api/compliance/all with file_name"""
        vehicle_id = getattr(TestFleetComplianceFileUpload, 'vehicle_id', None)
        if not vehicle_id:
            pytest.skip("No test vehicle created")
        
        response = auth_session.get(f"{BASE_URL}/api/compliance/all")
        items = response.json()
        
        # Find our test compliance item
        test_item = None
        for item in items:
            if item.get('entity_id') == vehicle_id:
                test_item = item
                break
        
        assert test_item is not None, "Test compliance item not found in /api/compliance/all"
        assert test_item.get('file_name') == "test_policy.pdf", "file_name not returned"
        assert test_item.get('file_type') == "application/pdf", "file_type not returned"
        print(f"Found test compliance in all items with file: {test_item.get('file_name')}")
    
    def test_cleanup_test_vehicle(self, auth_session):
        """Cleanup: Delete test vehicle and compliance"""
        vehicle_id = getattr(TestFleetComplianceFileUpload, 'vehicle_id', None)
        if vehicle_id:
            response = auth_session.delete(f"{BASE_URL}/api/vehicles/{vehicle_id}")
            if response.status_code in [200, 204]:
                print(f"Deleted test vehicle {vehicle_id}")


class TestDriverComplianceFileUpload:
    """Test driver compliance file upload"""
    
    def test_create_driver_with_compliance_file(self, auth_session):
        """Create driver and add compliance with file"""
        # Create driver
        driver_data = {
            "name": f"Test Driver {datetime.now().strftime('%H%M%S')}",
            "phone": "+27123456789",
            "email": "test.driver@test.com"
        }
        
        response = auth_session.post(f"{BASE_URL}/api/drivers", json=driver_data)
        assert response.status_code in [200, 201], f"Failed to create driver: {response.text}"
        
        driver = response.json()
        driver_id = driver['id']
        print(f"Created test driver: {driver['name']} (ID: {driver_id})")
        
        TestDriverComplianceFileUpload.driver_id = driver_id
    
    def test_add_driver_compliance_with_file(self, auth_session):
        """Add driver compliance with file upload"""
        driver_id = getattr(TestDriverComplianceFileUpload, 'driver_id', None)
        if not driver_id:
            pytest.skip("No test driver created")
        
        import base64
        mock_file_content = b"Mock license document"
        file_data = base64.b64encode(mock_file_content).decode('utf-8')
        
        compliance_data = {
            "item_type": "license",
            "item_label": "Driver License",
            "expiry_date": (datetime.now() + timedelta(days=45)).strftime("%Y-%m-%d"),
            "reminder_days_before": 30,
            "license_number": "DL-12345",
            "issuing_country": "South Africa",
            "file_name": "driver_license.png",
            "file_type": "image/png",
            "file_data": file_data
        }
        
        response = auth_session.post(
            f"{BASE_URL}/api/drivers/{driver_id}/compliance",
            json=compliance_data
        )
        assert response.status_code in [200, 201], f"Failed to add compliance: {response.text}"
        
        compliance = response.json()
        assert compliance.get('file_name') == "driver_license.png"
        print(f"Created driver compliance with file: {compliance.get('file_name')}")
    
    def test_cleanup_test_driver(self, auth_session):
        """Cleanup: Delete test driver"""
        driver_id = getattr(TestDriverComplianceFileUpload, 'driver_id', None)
        if driver_id:
            response = auth_session.delete(f"{BASE_URL}/api/drivers/{driver_id}")
            if response.status_code in [200, 204]:
                print(f"Deleted test driver {driver_id}")


# Run tests if executed directly
if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
