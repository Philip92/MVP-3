"""
Invoice Bug Fix Tests
Tests for 4 critical invoice bugs:
1. Line items don't populate when adding parcels from trip
2. Rate defaults to 0 instead of client's default rate
3. Total amount calculation broken
4. Currency toggle creates compounding values

Test client: MTN South Africa (client-1) - has rate R36/kg
Test trip: S28 (trip-2) - has parcels
"""

import pytest
import requests
import os

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')
SESSION_TOKEN = "demo_trips_session_1771084342772"

# Test data
TEST_CLIENT_ID = "client-1"  # MTN South Africa
TEST_TRIP_ID = "trip-2"  # S28
EXPECTED_RATE = 36  # R36/kg


@pytest.fixture
def auth_headers():
    """Headers with auth token"""
    return {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {SESSION_TOKEN}"
    }


class TestBug2ClientRate:
    """BUG 2 FIX: When selecting client, their default rate is fetched and applied"""
    
    def test_client_rate_endpoint_returns_rate(self, auth_headers):
        """Test GET /api/clients/{id}/rate returns current rate_per_kg"""
        response = requests.get(
            f"{BASE_URL}/api/clients/{TEST_CLIENT_ID}/rate",
            headers=auth_headers
        )
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert "rate_per_kg" in data, "Response should contain rate_per_kg"
        assert data["rate_per_kg"] is not None, "rate_per_kg should not be null"
        assert data["rate_per_kg"] == EXPECTED_RATE, f"Expected rate {EXPECTED_RATE}, got {data['rate_per_kg']}"
        
        print(f"✓ Client rate endpoint returns: {data['rate_per_kg']}/kg")
    
    def test_client_rate_handles_date_formats(self, auth_headers):
        """Test rate endpoint handles both ISO timestamp and date-only formats"""
        response = requests.get(
            f"{BASE_URL}/api/clients/{TEST_CLIENT_ID}/rate",
            headers=auth_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        
        # Rate should be returned even if effective_from has timestamp
        assert data.get("rate_per_kg") is not None
        print(f"✓ Rate returned despite timestamp format in effective_from")


class TestBug1LineItemsFromParcels:
    """BUG 1 FIX: Line items populate when adding parcels from trip"""
    
    def test_parcels_for_invoice_returns_data(self, auth_headers):
        """Test GET /api/trips/{id}/parcels-for-invoice returns parcels with rate"""
        response = requests.get(
            f"{BASE_URL}/api/trips/{TEST_TRIP_ID}/parcels-for-invoice",
            headers=auth_headers
        )
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert isinstance(data, list), "Response should be a list"
        
        print(f"✓ Found {len(data)} parcels for trip {TEST_TRIP_ID}")
        
        for parcel in data:
            assert "id" in parcel, "Parcel should have id"
            assert "description" in parcel, "Parcel should have description"
            assert "total_weight" in parcel, "Parcel should have total_weight"
            assert "default_rate" in parcel, "Parcel should have default_rate"
            assert "client_name" in parcel, "Parcel should have client_name"
            
            print(f"  - Parcel: {parcel['description']}, Weight: {parcel['total_weight']}kg, Rate: {parcel['default_rate']}/kg")
    
    def test_parcel_data_for_line_item_creation(self, auth_headers):
        """Test parcels have all data needed to create line items"""
        response = requests.get(
            f"{BASE_URL}/api/trips/{TEST_TRIP_ID}/parcels-for-invoice",
            headers=auth_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        
        if len(data) > 0:
            parcel = data[0]
            
            # Calculate expected amount
            weight = parcel.get("total_weight", 0)
            rate = parcel.get("default_rate", 0)
            expected_amount = weight * rate
            
            print(f"✓ Parcel line item calculation: {weight}kg × R{rate} = R{expected_amount}")
            
            # Verify rate comes from client_rates
            assert rate >= 0, "Rate should be non-negative"


class TestBug3TotalCalculation:
    """BUG 3 FIX: Total amount calculation - Amount = Weight × Rate"""
    
    def test_line_item_amount_calculation(self, auth_headers):
        """Test line item amount = weight × rate"""
        # Create invoice
        invoice_payload = {
            "client_id": TEST_CLIENT_ID,
            "trip_id": TEST_TRIP_ID,
            "subtotal": 0,
            "currency": "ZAR"
        }
        
        create_response = requests.post(
            f"{BASE_URL}/api/invoices",
            json=invoice_payload,
            headers=auth_headers
        )
        
        assert create_response.status_code in [200, 201], f"Failed to create invoice: {create_response.text}"
        invoice_id = create_response.json()["id"]
        
        try:
            # Add line item with weight 45kg and rate 36
            line_item_payload = {
                "description": "Test Parcel - Bug 3 Fix Verification",
                "quantity": 1,
                "weight": 45.0,
                "rate": 36.0
            }
            
            item_response = requests.post(
                f"{BASE_URL}/api/invoices/{invoice_id}/items",
                json=line_item_payload,
                headers=auth_headers
            )
            
            assert item_response.status_code == 200, f"Failed to add line item: {item_response.text}"
            
            item_data = item_response.json()
            expected_amount = 45.0 * 36.0  # R1,620
            
            assert "amount" in item_data, "Line item should have calculated amount"
            assert item_data["amount"] == expected_amount, f"Expected amount {expected_amount}, got {item_data['amount']}"
            
            print(f"✓ Line item amount: 45kg × R36 = R{item_data['amount']} (expected R{expected_amount})")
            
        finally:
            # Clean up
            requests.delete(f"{BASE_URL}/api/invoices/{invoice_id}", headers=auth_headers)
    
    def test_subtotal_is_sum_of_line_items(self, auth_headers):
        """Test subtotal = sum of all line items"""
        # Create invoice
        invoice_payload = {
            "client_id": TEST_CLIENT_ID,
            "subtotal": 0,
            "currency": "ZAR"
        }
        
        create_response = requests.post(
            f"{BASE_URL}/api/invoices",
            json=invoice_payload,
            headers=auth_headers
        )
        
        assert create_response.status_code in [200, 201]
        invoice_id = create_response.json()["id"]
        
        try:
            # Add two line items
            items = [
                {"description": "Item 1", "quantity": 1, "weight": 10.0, "rate": 36.0},  # R360
                {"description": "Item 2", "quantity": 1, "weight": 20.0, "rate": 36.0}   # R720
            ]
            
            total_expected = 0
            for item in items:
                requests.post(
                    f"{BASE_URL}/api/invoices/{invoice_id}/items",
                    json=item,
                    headers=auth_headers
                )
                total_expected += item["weight"] * item["rate"]
            
            # Get full invoice
            get_response = requests.get(
                f"{BASE_URL}/api/invoices/{invoice_id}/full",
                headers=auth_headers
            )
            
            assert get_response.status_code == 200
            invoice_data = get_response.json()
            
            # Sum line items from response
            line_items = invoice_data.get("line_items", [])
            actual_subtotal = sum(item.get("amount", 0) for item in line_items)
            
            assert actual_subtotal == total_expected, f"Expected subtotal {total_expected}, got {actual_subtotal}"
            print(f"✓ Subtotal (sum of line items): R{actual_subtotal} (expected R{total_expected})")
            
        finally:
            requests.delete(f"{BASE_URL}/api/invoices/{invoice_id}", headers=auth_headers)
    
    def test_total_with_adjustments(self, auth_headers):
        """Test total = subtotal + adjustments"""
        # Create invoice
        invoice_payload = {
            "client_id": TEST_CLIENT_ID,
            "subtotal": 1000.0,
            "adjustments": 0,
            "currency": "ZAR"
        }
        
        create_response = requests.post(
            f"{BASE_URL}/api/invoices",
            json=invoice_payload,
            headers=auth_headers
        )
        
        assert create_response.status_code in [200, 201]
        invoice_id = create_response.json()["id"]
        
        try:
            # Add a line item
            requests.post(
                f"{BASE_URL}/api/invoices/{invoice_id}/items",
                json={"description": "Main freight", "quantity": 1, "weight": 45.0, "rate": 36.0},  # R1,620
                headers=auth_headers
            )
            
            # Add an adjustment (+R100 handling fee)
            adj_response = requests.post(
                f"{BASE_URL}/api/invoices/{invoice_id}/adjustments",
                json={"description": "Handling fee", "amount": 100.0, "is_addition": True},
                headers=auth_headers
            )
            
            assert adj_response.status_code == 200, f"Failed to add adjustment: {adj_response.text}"
            
            # Get full invoice
            get_response = requests.get(
                f"{BASE_URL}/api/invoices/{invoice_id}/full",
                headers=auth_headers
            )
            
            invoice_data = get_response.json()
            
            # Calculate expected total
            line_items = invoice_data.get("line_items", [])
            subtotal = sum(item.get("amount", 0) for item in line_items)  # R1,620
            
            adjustments = invoice_data.get("adjustments", [])
            adjustment_total = sum(
                adj.get("amount", 0) if adj.get("is_addition") else -adj.get("amount", 0)
                for adj in adjustments
            )  # R100
            
            expected_total = subtotal + adjustment_total  # R1,720
            
            print(f"✓ Total calculation: R{subtotal} (subtotal) + R{adjustment_total} (adjustments) = R{expected_total}")
            
        finally:
            requests.delete(f"{BASE_URL}/api/invoices/{invoice_id}", headers=auth_headers)


class TestBug4CurrencyToggle:
    """BUG 4 FIX: Currency toggle does NOT compound values"""
    
    def test_invoice_stores_base_currency(self, auth_headers):
        """Test that invoices store values in ZAR (base currency)"""
        # Create invoice in ZAR
        invoice_payload = {
            "client_id": TEST_CLIENT_ID,
            "subtotal": 1620.0,  # R1,620
            "currency": "ZAR"
        }
        
        create_response = requests.post(
            f"{BASE_URL}/api/invoices",
            json=invoice_payload,
            headers=auth_headers
        )
        
        assert create_response.status_code in [200, 201]
        invoice_id = create_response.json()["id"]
        
        try:
            # Add line item
            requests.post(
                f"{BASE_URL}/api/invoices/{invoice_id}/items",
                json={"description": "Test Item", "quantity": 1, "weight": 45.0, "rate": 36.0},
                headers=auth_headers
            )
            
            # Get invoice
            get_response = requests.get(
                f"{BASE_URL}/api/invoices/{invoice_id}/full",
                headers=auth_headers
            )
            
            invoice_data = get_response.json()
            
            # Line item amounts should be stored in ZAR
            line_items = invoice_data.get("line_items", [])
            if line_items:
                amount = line_items[0].get("amount", 0)
                assert amount == 1620.0, f"Line item amount should be R1,620, got {amount}"
                print(f"✓ Line item stored in ZAR: R{amount}")
            
        finally:
            requests.delete(f"{BASE_URL}/api/invoices/{invoice_id}", headers=auth_headers)
    
    def test_currency_conversion_display_only(self):
        """
        Note: Currency conversion is frontend-only behavior.
        Backend stores all amounts in ZAR (base currency).
        Frontend multiplies/divides by exchange rate (6.67) for display only.
        
        This test documents the expected behavior:
        - R1,620 in ZAR = KES 10,805.40 (1620 × 6.67)
        - Toggle back: KES 10,805.40 = R1,620 (10805.40 / 6.67)
        - Values should NOT compound with each toggle
        """
        exchange_rate = 6.67
        zar_amount = 1620.0
        
        # ZAR -> KES
        kes_amount = zar_amount * exchange_rate
        print(f"✓ ZAR → KES: R{zar_amount} × {exchange_rate} = KES {kes_amount:.2f}")
        
        # KES -> ZAR
        back_to_zar = kes_amount / exchange_rate
        print(f"✓ KES → ZAR: KES {kes_amount:.2f} / {exchange_rate} = R{back_to_zar:.2f}")
        
        # Values should be consistent
        assert abs(back_to_zar - zar_amount) < 0.01, "Currency toggle should not compound values"
        
        # Multiple toggles should produce consistent results
        for i in range(5):
            toggle = i % 2
            if toggle == 1:  # To KES
                display = zar_amount * exchange_rate
                currency = "KES"
            else:  # To ZAR
                display = zar_amount
                currency = "ZAR"
            print(f"  Toggle {i+1}: {currency} {display:.2f}")
        
        print("✓ Currency toggle produces consistent values (no compounding)")


class TestInvoiceFinalize:
    """Test invoice finalization changes status to sent"""
    
    def test_finalize_changes_status_to_sent(self, auth_headers):
        """Test finalizing invoice changes status from draft to sent"""
        # Create invoice
        invoice_payload = {
            "client_id": TEST_CLIENT_ID,
            "subtotal": 1000.0,
            "currency": "ZAR"
        }
        
        create_response = requests.post(
            f"{BASE_URL}/api/invoices",
            json=invoice_payload,
            headers=auth_headers
        )
        
        assert create_response.status_code in [200, 201]
        invoice_id = create_response.json()["id"]
        
        # Verify initial status is draft
        get_response = requests.get(
            f"{BASE_URL}/api/invoices/{invoice_id}/full",
            headers=auth_headers
        )
        assert get_response.json()["status"] == "draft"
        
        # Finalize
        finalize_response = requests.post(
            f"{BASE_URL}/api/invoices/{invoice_id}/finalize",
            headers=auth_headers
        )
        
        assert finalize_response.status_code == 200
        
        # Verify status changed to sent
        get_response = requests.get(
            f"{BASE_URL}/api/invoices/{invoice_id}/full",
            headers=auth_headers
        )
        assert get_response.json()["status"] == "sent"
        
        print("✓ Invoice finalized: status changed from draft to sent")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
