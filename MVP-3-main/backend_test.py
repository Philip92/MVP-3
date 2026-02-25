#!/usr/bin/env python3
"""
Comprehensive Backend API Test Suite for Servex Holdings Logistics Management App
Tests all major endpoints with authentication and data validation
"""

import requests
import json
import sys
from datetime import datetime
import os
from typing import Dict, Any, Optional

# Configuration
BASE_URL = "https://multi-warehouse-qa.preview.emergentagent.com/api"
LOGIN_EMAIL = "admin@servex.com"
LOGIN_PASSWORD = "Servex2026!"

class ServexAPITester:
    def __init__(self):
        self.base_url = BASE_URL
        self.session = requests.Session()
        self.auth_user = None
        self.test_results = []
        
    def log_test(self, test_name: str, success: bool, message: str = "", data: Any = None):
        """Log test result"""
        result = {
            "test": test_name,
            "success": success,
            "message": message,
            "data": data if success else None,
            "timestamp": datetime.now().isoformat()
        }
        self.test_results.append(result)
        status = "✅ PASS" if success else "❌ FAIL"
        print(f"{status}: {test_name} - {message}")
        return success
    
    def make_request(self, method: str, endpoint: str, data: dict = None, params: dict = None) -> dict:
        """Make authenticated request to API"""
        url = f"{self.base_url}{endpoint}"
        
        try:
            if method.upper() == "GET":
                response = self.session.get(url, params=params, timeout=30)
            elif method.upper() == "POST":
                response = self.session.post(url, json=data, timeout=30)
            elif method.upper() == "PUT":
                response = self.session.put(url, json=data, timeout=30)
            elif method.upper() == "DELETE":
                response = self.session.delete(url, timeout=30)
            else:
                raise ValueError(f"Unsupported HTTP method: {method}")
            
            # Handle different response types
            content_type = response.headers.get('content-type', '').lower()
            
            if 'application/json' in content_type:
                # JSON response
                response_data = response.json() if response.content else {}
            elif 'application/pdf' in content_type or 'text/csv' in content_type:
                # Binary/text response (PDF, CSV)
                response_data = {
                    "content_length": len(response.content),
                    "content_type": content_type,
                    "has_content": len(response.content) > 0
                }
            else:
                # Plain text or other
                response_data = response.text if response.content else ""
            
            # Return structured response
            return {
                "status_code": response.status_code,
                "success": response.status_code < 400,
                "data": response_data,
                "headers": dict(response.headers)
            }
        except requests.RequestException as e:
            return {
                "status_code": 0,
                "success": False,
                "data": {"error": str(e)},
                "headers": {}
            }
        except Exception as e:
            return {
                "status_code": 0,
                "success": False,
                "data": {"error": f"Unexpected error: {str(e)}"},
                "headers": {}
            }

    def test_authentication(self):
        """Test login and user authentication"""
        print("\n=== Testing Authentication ===")
        
        # Test login
        login_data = {
            "email": LOGIN_EMAIL,
            "password": LOGIN_PASSWORD
        }
        
        response = self.make_request("POST", "/auth/login", login_data)
        
        if not response["success"]:
            return self.log_test("AUTH_LOGIN", False, f"Login failed: {response.get('data', {}).get('detail', 'Unknown error')}")
        
        self.auth_user = response["data"]
        success = self.log_test("AUTH_LOGIN", True, f"Login successful for {self.auth_user.get('email')}", self.auth_user)
        
        if not success:
            return False
        
        # Test get current user info
        me_response = self.make_request("GET", "/auth/me")
        
        if not me_response["success"]:
            return self.log_test("AUTH_ME", False, f"Get user info failed: {me_response.get('data', {}).get('detail', 'Unknown error')}")
        
        user_info = me_response["data"]
        return self.log_test("AUTH_ME", True, f"User info retrieved: {user_info.get('name', 'N/A')}", user_info)

    def test_dashboard_stats(self):
        """Test dashboard statistics endpoints"""
        print("\n=== Testing Dashboard Stats ===")
        
        # Test MTD stats
        response = self.make_request("GET", "/dashboard/stats", params={"period": "mtd"})
        
        if not response["success"]:
            return self.log_test("DASHBOARD_MTD", False, f"Dashboard MTD failed: {response.get('data', {}).get('detail', 'Unknown error')}")
        
        stats = response["data"]
        success = self.log_test("DASHBOARD_MTD", True, f"MTD Stats - Clients: {stats.get('total_clients', 0)}, Shipments: {stats.get('total_shipments', 0)}, Revenue: {stats.get('financial', {}).get('revenue_mtd', 0)}", stats)
        
        # Test ALL period stats
        all_response = self.make_request("GET", "/dashboard/stats", params={"period": "all"})
        
        if not all_response["success"]:
            return self.log_test("DASHBOARD_ALL", False, f"Dashboard ALL failed: {all_response.get('data', {}).get('detail', 'Unknown error')}")
        
        all_stats = all_response["data"]
        return self.log_test("DASHBOARD_ALL", True, f"ALL Stats - Clients: {all_stats.get('total_clients', 0)}, Shipments: {all_stats.get('total_shipments', 0)}", all_stats) and success

    def test_clients_api(self):
        """Test client management endpoints"""
        print("\n=== Testing Client APIs ===")
        
        # Test list clients
        response = self.make_request("GET", "/clients")
        
        if not response["success"]:
            return self.log_test("CLIENTS_LIST", False, f"List clients failed: {response.get('data', {}).get('detail', 'Unknown error')}")
        
        clients = response["data"]
        if not isinstance(clients, list) or len(clients) == 0:
            return self.log_test("CLIENTS_LIST", False, f"Expected client list, got: {len(clients) if isinstance(clients, list) else 'non-list'} clients")
        
        success = self.log_test("CLIENTS_LIST", True, f"Retrieved {len(clients)} clients", {"count": len(clients), "first_client": clients[0].get('name') if clients else None})
        
        # Test get single client with total_amount_spent (NEW ENDPOINT)
        if clients:
            first_client_id = clients[0]["id"]
            client_response = self.make_request("GET", f"/clients/{first_client_id}")
            
            if not client_response["success"]:
                success = self.log_test("CLIENTS_GET", False, f"Get single client failed: {client_response.get('data', {}).get('detail', 'Unknown error')}") and success
            else:
                client = client_response["data"]
                # Check if total_amount_spent field is present
                has_total_spent = "total_amount_spent" in client
                total_spent_value = client.get("total_amount_spent", 0)
                success = self.log_test("CLIENTS_GET", True, f"Retrieved client: {client.get('name')} - Total spent: {total_spent_value} (field present: {has_total_spent})", client) and success
        
        # Test CSV Export (NEW ENDPOINT)
        csv_response = self.make_request("GET", "/clients/export/csv")
        
        if not csv_response["success"]:
            success = self.log_test("CLIENTS_CSV_EXPORT", False, f"CSV export failed: {csv_response.get('data', {}).get('detail', 'Unknown error')}") and success
        else:
            # Check if response is CSV format
            content_type = csv_response.get("headers", {}).get("content-type", "")
            content_disposition = csv_response.get("headers", {}).get("content-disposition", "")
            is_csv = "text/csv" in content_type or "filename=clients.csv" in content_disposition
            success = self.log_test("CLIENTS_CSV_EXPORT", True, f"CSV export successful - Content-Type: {content_type}, Has CSV data: {is_csv}", {"content_type": content_type, "has_csv_data": is_csv}) and success
        
        # Test create client
        test_client_data = {
            "name": f"Test Client {datetime.now().strftime('%H%M%S')}",
            "email": f"testclient{datetime.now().strftime('%H%M%S')}@example.com",
            "phone": "+27123456789",
            "address": "123 Test Street, Test City",
            "status": "active",
            "default_rate_value": 50.0,
            "default_rate_type": "per_kg"
        }
        
        create_response = self.make_request("POST", "/clients", test_client_data)
        
        if not create_response["success"]:
            success = self.log_test("CLIENTS_CREATE", False, f"Create client failed: {create_response.get('data', {}).get('detail', 'Unknown error')}") and success
        else:
            new_client = create_response["data"]
            success = self.log_test("CLIENTS_CREATE", True, f"Created client: {new_client.get('name')}", new_client) and success
            
            # Test update client
            update_data = {
                "name": f"Updated Test Client {datetime.now().strftime('%H%M%S')}",
                "phone": "+27987654321"
            }
            
            update_response = self.make_request("PUT", f"/clients/{new_client['id']}", update_data)
            
            if not update_response["success"]:
                success = self.log_test("CLIENTS_UPDATE", False, f"Update client failed: {update_response.get('data', {}).get('detail', 'Unknown error')}") and success
            else:
                updated_client = update_response["data"]
                success = self.log_test("CLIENTS_UPDATE", True, f"Updated client: {updated_client.get('name')}", updated_client) and success
        
        return success

    def test_warehouse_api(self):
        """Test warehouse and parcel management endpoints"""
        print("\n=== Testing Warehouse APIs ===")
        
        # Test list warehouse parcels (shipments)
        response = self.make_request("GET", "/warehouse/parcels", params={"page": 1, "page_size": 10})
        
        if not response["success"]:
            return self.log_test("WAREHOUSE_PARCELS", False, f"List parcels failed: {response.get('data', {}).get('detail', 'Unknown error')}")
        
        parcels_data = response["data"]
        if not isinstance(parcels_data, dict) or "items" not in parcels_data:
            return self.log_test("WAREHOUSE_PARCELS", False, f"Expected paginated parcels data, got: {type(parcels_data)}")
        
        parcels = parcels_data["items"]
        total = parcels_data.get("total", 0)
        success = self.log_test("WAREHOUSE_PARCELS", True, f"Retrieved {len(parcels)} parcels (total: {total})", {"count": len(parcels), "total": total})
        
        # Test warehouse parcels with status filter
        filter_response = self.make_request("GET", "/warehouse/parcels", params={"status": "warehouse", "page": 1, "page_size": 5})
        
        if not filter_response["success"]:
            success = self.log_test("WAREHOUSE_FILTER", False, f"Filter parcels failed: {filter_response.get('data', {}).get('detail', 'Unknown error')}") and success
        else:
            filtered_data = filter_response["data"]
            success = self.log_test("WAREHOUSE_FILTER", True, f"Filtered parcels: {len(filtered_data.get('items', []))} warehouse parcels", filtered_data) and success
        
        # Test warehouse filter options
        filters_response = self.make_request("GET", "/warehouse/filters")
        
        if not filters_response["success"]:
            success = self.log_test("WAREHOUSE_FILTERS", False, f"Get filters failed: {filters_response.get('data', {}).get('detail', 'Unknown error')}") and success
        else:
            filters = filters_response["data"]
            success = self.log_test("WAREHOUSE_FILTERS", True, f"Retrieved filter options - destinations: {len(filters.get('destinations', []))}, clients: {len(filters.get('clients', []))}", filters) and success
        
        return success

    def test_trips_api(self):
        """Test trip management endpoints"""
        print("\n=== Testing Trip APIs ===")
        
        # Test list trips
        response = self.make_request("GET", "/trips")
        
        if not response["success"]:
            return self.log_test("TRIPS_LIST", False, f"List trips failed: {response.get('data', {}).get('detail', 'Unknown error')}")
        
        trips = response["data"]
        if not isinstance(trips, list):
            return self.log_test("TRIPS_LIST", False, f"Expected trip list, got: {type(trips)}")
        
        success = self.log_test("TRIPS_LIST", True, f"Retrieved {len(trips)} trips", {"count": len(trips), "first_trip": trips[0].get('trip_number') if trips else None})
        
        # Test get single trip if trips exist
        if trips:
            first_trip_id = trips[0]["id"]
            trip_response = self.make_request("GET", f"/trips/{first_trip_id}")
            
            if not trip_response["success"]:
                success = self.log_test("TRIPS_GET", False, f"Get single trip failed: {trip_response.get('data', {}).get('detail', 'Unknown error')}") and success
            else:
                trip = trip_response["data"]
                success = self.log_test("TRIPS_GET", True, f"Retrieved trip: {trip.get('trip_number')} - Status: {trip.get('status')}", trip) and success
        
        return success

    def test_invoices_api(self):
        """Test invoice management endpoints"""
        print("\n=== Testing Invoice APIs ===")
        
        # Test list invoices
        response = self.make_request("GET", "/invoices")
        
        if not response["success"]:
            return self.log_test("INVOICES_LIST", False, f"List invoices failed: {response.get('data', {}).get('detail', 'Unknown error')}")
        
        invoices_data = response["data"]
        
        # Handle both list and paginated response formats
        if isinstance(invoices_data, dict) and "items" in invoices_data:
            invoices = invoices_data["items"]
            total = invoices_data.get("total", len(invoices))
        elif isinstance(invoices_data, list):
            invoices = invoices_data
            total = len(invoices)
        else:
            return self.log_test("INVOICES_LIST", False, f"Unexpected invoice data format: {type(invoices_data)}")
        
        success = self.log_test("INVOICES_LIST", True, f"Retrieved {len(invoices)} invoices (total: {total})", {"count": len(invoices), "total": total})
        
        # Test get single invoice if invoices exist
        if invoices:
            first_invoice_id = invoices[0]["id"]
            invoice_response = self.make_request("GET", f"/invoices/{first_invoice_id}")
            
            if not invoice_response["success"]:
                success = self.log_test("INVOICES_GET", False, f"Get single invoice failed: {invoice_response.get('data', {}).get('detail', 'Unknown error')}") and success
            else:
                invoice = invoice_response["data"]
                success = self.log_test("INVOICES_GET", True, f"Retrieved invoice: {invoice.get('invoice_number')} - Status: {invoice.get('status')}, Total: {invoice.get('total')}", invoice) and success
        
        return success

    def test_finance_api(self):
        """Test finance management endpoints"""
        print("\n=== Testing Finance APIs ===")
        
        # Test client statements
        response = self.make_request("GET", "/finance/client-statements")
        
        if not response["success"]:
            return self.log_test("FINANCE_STATEMENTS", False, f"Client statements failed: {response.get('data', {}).get('detail', 'Unknown error')}")
        
        statements = response["data"]
        if not isinstance(statements, dict) or "statements" not in statements:
            return self.log_test("FINANCE_STATEMENTS", False, f"Expected statements object, got: {type(statements)}")
        
        client_statements = statements["statements"]
        summary = statements.get("summary", {})
        success = self.log_test("FINANCE_STATEMENTS", True, f"Retrieved {len(client_statements)} client statements - Total outstanding: {summary.get('total_outstanding', 0)}", statements)
        
        # Test overdue invoices
        overdue_response = self.make_request("GET", "/finance/overdue")
        
        if not overdue_response["success"]:
            success = self.log_test("FINANCE_OVERDUE", False, f"Overdue invoices failed: {overdue_response.get('data', {}).get('detail', 'Unknown error')}") and success
        else:
            overdue = overdue_response["data"]
            overdue_invoices = overdue.get("invoices", [])
            total_overdue = overdue.get("total_overdue", 0)
            success = self.log_test("FINANCE_OVERDUE", True, f"Retrieved {len(overdue_invoices)} overdue invoices - Total overdue: {total_overdue}", overdue) and success
        
        # Test trip worksheet (if trips exist)
        trips_response = self.make_request("GET", "/trips")
        if trips_response["success"] and trips_response["data"]:
            first_trip_id = trips_response["data"][0]["id"]
            worksheet_response = self.make_request("GET", f"/finance/trip-worksheet/{first_trip_id}")
            
            if not worksheet_response["success"]:
                success = self.log_test("FINANCE_WORKSHEET", False, f"Trip worksheet failed: {worksheet_response.get('data', {}).get('detail', 'Unknown error')}") and success
            else:
                worksheet = worksheet_response["data"]
                trip_info = worksheet.get("trip", {})
                summary = worksheet.get("summary", {})
                success = self.log_test("FINANCE_WORKSHEET", True, f"Trip worksheet for {trip_info.get('trip_number')} - Revenue: {summary.get('total_revenue', 0)}", worksheet) and success
        
        return success

    def test_shipments_api(self):
        """Test shipment endpoints"""
        print("\n=== Testing Shipment APIs ===")
        
        # Test list shipments
        response = self.make_request("GET", "/shipments")
        
        if not response["success"]:
            return self.log_test("SHIPMENTS_LIST", False, f"List shipments failed: {response.get('data', {}).get('detail', 'Unknown error')}")
        
        shipments_data = response["data"]
        
        # Handle both list and paginated response formats
        if isinstance(shipments_data, dict) and "items" in shipments_data:
            shipments = shipments_data["items"]
            total = shipments_data.get("total", len(shipments))
        elif isinstance(shipments_data, list):
            shipments = shipments_data
            total = len(shipments)
        else:
            return self.log_test("SHIPMENTS_LIST", False, f"Unexpected shipment data format: {type(shipments_data)}")
        
        return self.log_test("SHIPMENTS_LIST", True, f"Retrieved {len(shipments)} shipments (total: {total})", {"count": len(shipments), "total": total})

    def test_whatsapp_templates_api(self):
        """Test WhatsApp template endpoints"""
        print("\n=== Testing WhatsApp Template APIs ===")
        
        # Test get WhatsApp templates
        response = self.make_request("GET", "/templates/whatsapp")
        
        if not response["success"]:
            return self.log_test("TEMPLATES_WHATSAPP", False, f"WhatsApp templates failed: {response.get('data', {}).get('detail', 'Unknown error')}")
        
        templates_data = response["data"]
        if isinstance(templates_data, dict) and "templates" in templates_data:
            templates = templates_data["templates"]
            return self.log_test("TEMPLATES_WHATSAPP", True, f"Retrieved {len(templates)} WhatsApp templates", {"count": len(templates), "templates": templates})
        else:
            return self.log_test("TEMPLATES_WHATSAPP", False, f"Expected templates object with 'templates' key, got: {type(templates_data)}")

    def test_collection_workflow_api(self):
        """Test NEW collection workflow endpoints"""
        print("\n=== Testing Collection Workflow (NEW) ===")
        
        # First, get parcels with "arrived" status
        arrived_response = self.make_request("GET", "/warehouse/parcels", params={"status": "arrived", "page": 1, "page_size": 5})
        
        if not arrived_response["success"]:
            return self.log_test("COLLECTION_GET_ARRIVED", False, f"Failed to get arrived parcels: {arrived_response.get('data', {}).get('detail', 'Unknown error')}")
        
        arrived_data = arrived_response["data"]
        arrived_parcels = arrived_data.get("items", [])
        
        if not arrived_parcels:
            return self.log_test("COLLECTION_GET_ARRIVED", False, "No parcels with 'arrived' status found for testing collection workflow")
        
        success = self.log_test("COLLECTION_GET_ARRIVED", True, f"Found {len(arrived_parcels)} arrived parcels", {"count": len(arrived_parcels)})
        
        # Test collection check for the first arrived parcel
        test_parcel_id = arrived_parcels[0]["id"]
        parcel_desc = arrived_parcels[0].get("description", "Unknown")
        
        check_response = self.make_request("GET", f"/warehouse/parcels/{test_parcel_id}/collection-check")
        
        if not check_response["success"]:
            success = self.log_test("COLLECTION_CHECK", False, f"Collection check failed: {check_response.get('data', {}).get('detail', 'Unknown error')}") and success
        else:
            check_data = check_response["data"]
            can_collect = check_data.get("can_collect", False)
            warning = check_data.get("warning", "none")
            payment_status = check_data.get("payment_status", "unknown")
            success = self.log_test("COLLECTION_CHECK", True, f"Collection check for parcel {parcel_desc} - Can collect: {can_collect}, Payment: {payment_status}, Warning: {warning}", check_data) and success
        
        # Test collect parcel
        collect_data = {"confirmation_note": "Testing collection workflow from backend test"}
        collect_response = self.make_request("POST", f"/warehouse/parcels/{test_parcel_id}/collect", collect_data)
        
        if not collect_response["success"]:
            success = self.log_test("COLLECTION_COLLECT", False, f"Parcel collection failed: {collect_response.get('data', {}).get('detail', 'Unknown error')}") and success
        else:
            collect_result = collect_response["data"]
            collected_success = collect_result.get("success", False)
            admin_notified = collect_result.get("admin_notified", False)
            success = self.log_test("COLLECTION_COLLECT", True, f"Parcel {parcel_desc} collected successfully - Admin notified: {admin_notified}", collect_result) and success
        
        return success

    def test_finance_pdf_api(self):
        """Test NEW finance PDF endpoints"""
        print("\n=== Testing Finance PDF APIs (NEW) ===")
        
        # Get a client for testing PDF generation
        clients_response = self.make_request("GET", "/clients")
        
        if not clients_response["success"] or not clients_response["data"]:
            return self.log_test("FINANCE_PDF_GET_CLIENT", False, "No clients found for PDF testing")
        
        clients = clients_response["data"]
        test_client_id = clients[0]["id"]
        client_name = clients[0].get("name", "Unknown")
        
        success = self.log_test("FINANCE_PDF_GET_CLIENT", True, f"Using client {client_name} for PDF testing", {"client_id": test_client_id})
        
        # Test client statement PDF generation
        pdf_response = self.make_request("GET", f"/finance/client-statement/{test_client_id}/pdf")
        
        if not pdf_response["success"]:
            success = self.log_test("FINANCE_CLIENT_STATEMENT_PDF", False, f"Client statement PDF failed: {pdf_response.get('data', {}).get('detail', 'Unknown error')}") and success
        else:
            # Check if response is PDF format
            content_type = pdf_response.get("headers", {}).get("content-type", "")
            content_disposition = pdf_response.get("headers", {}).get("content-disposition", "")
            is_pdf = "application/pdf" in content_type or ".pdf" in content_disposition
            success = self.log_test("FINANCE_CLIENT_STATEMENT_PDF", True, f"Client statement PDF generated for {client_name} - Content-Type: {content_type}, Is PDF: {is_pdf}", {"content_type": content_type, "is_pdf": is_pdf}) and success
        
        return success

    def run_all_tests(self):
        """Run comprehensive test suite"""
        print("🚀 Starting Servex Holdings Backend API Test Suite")
        print(f"Testing against: {self.base_url}")
        print(f"Login credentials: {LOGIN_EMAIL}")
        
        # Authentication must pass first
        if not self.test_authentication():
            print("\n❌ Authentication failed - stopping tests")
            return False
        
        # Run all API tests
        test_methods = [
            self.test_dashboard_stats,
            self.test_clients_api,
            self.test_warehouse_api,
            self.test_trips_api,
            self.test_invoices_api,
            self.test_finance_api,
            self.test_shipments_api,
            self.test_whatsapp_templates_api,
            self.test_collection_workflow_api,  # NEW
            self.test_finance_pdf_api  # NEW
        ]
        
        all_passed = True
        for test_method in test_methods:
            try:
                result = test_method()
                all_passed = all_passed and result
            except Exception as e:
                test_name = test_method.__name__.replace("test_", "").upper()
                self.log_test(test_name, False, f"Test method failed with exception: {str(e)}")
                all_passed = False
        
        # Print summary
        self.print_summary()
        return all_passed

    def print_summary(self):
        """Print test results summary"""
        passed = sum(1 for r in self.test_results if r["success"])
        total = len(self.test_results)
        failed = total - passed
        
        print(f"\n{'='*60}")
        print(f"🧪 TEST SUMMARY")
        print(f"{'='*60}")
        print(f"✅ PASSED: {passed}")
        print(f"❌ FAILED: {failed}")
        print(f"📊 TOTAL:  {total}")
        print(f"📈 SUCCESS RATE: {(passed/total*100):.1f}%")
        
        if failed > 0:
            print(f"\n❌ FAILED TESTS:")
            for result in self.test_results:
                if not result["success"]:
                    print(f"   • {result['test']}: {result['message']}")
        
        print(f"{'='*60}")

def main():
    """Main test execution"""
    tester = ServexAPITester()
    
    try:
        success = tester.run_all_tests()
        exit_code = 0 if success else 1
    except KeyboardInterrupt:
        print("\n⚠️  Tests interrupted by user")
        exit_code = 1
    except Exception as e:
        print(f"\n💥 Test suite failed with exception: {str(e)}")
        exit_code = 1
    
    sys.exit(exit_code)

if __name__ == "__main__":
    main()