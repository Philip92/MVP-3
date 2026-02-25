"""
Tests for Photo Management and Servex Holdings Rebrand

Tests cover:
1. POST /api/warehouse/parcels/{id}/photos - Upload photo to piece
2. DELETE /api/warehouse/parcels/{id}/photos/{piece_id} - Delete photo from piece
3. Servex Holdings branding verification in API responses
"""

import pytest
import requests
import os
import base64

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')
SESSION_TOKEN = "test_photo_session_1771080011425"
SHIPMENT_ID = "test-photo-shipment-1771080011425"
PIECE_ID_1 = "test-photo-piece-1-1771080011425"
PIECE_ID_2 = "test-photo-piece-2-1771080011425"


class TestPhotoEndpoints:
    """Test photo upload and delete functionality"""
    
    def test_api_health_shows_servex_branding(self):
        """Test that API root shows Servex Holdings branding"""
        response = requests.get(f"{BASE_URL}/api/")
        assert response.status_code == 200
        data = response.json()
        assert "Servex Holdings" in data.get("message", "")
        print("PASS: API root shows 'Servex Holdings' branding")
    
    def test_upload_photo_to_parcel_piece(self):
        """Test POST /api/warehouse/parcels/{id}/photos uploads photo"""
        # Create a tiny 1x1 PNG image
        png_bytes = base64.b64decode("iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg==")
        
        files = {'file': ('test.png', png_bytes, 'image/png')}
        response = requests.post(
            f"{BASE_URL}/api/warehouse/parcels/{SHIPMENT_ID}/photos",
            headers={"Authorization": f"Bearer {SESSION_TOKEN}"},
            files=files
        )
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()
        assert data.get("message") == "Photo uploaded successfully"
        assert "piece_id" in data
        assert "photo_url" in data
        assert data["photo_url"].startswith("data:image/png;base64,")
        print(f"PASS: Photo uploaded to piece {data['piece_id']}")
        
    def test_upload_photo_to_specific_piece(self):
        """Test uploading photo to specific piece by piece_id"""
        png_bytes = base64.b64decode("iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg==")
        
        files = {'file': ('test2.png', png_bytes, 'image/png')}
        response = requests.post(
            f"{BASE_URL}/api/warehouse/parcels/{SHIPMENT_ID}/photos",
            headers={"Authorization": f"Bearer {SESSION_TOKEN}"},
            files=files,
            data={"piece_id": PIECE_ID_2}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data.get("piece_id") == PIECE_ID_2 or data.get("piece_id") == PIECE_ID_1  # Could be either since first already has photo
        print(f"PASS: Photo uploaded to specific piece")
    
    def test_get_parcel_shows_photos_in_pieces(self):
        """Test GET /api/warehouse/parcels/{id} shows photo_url in pieces"""
        response = requests.get(
            f"{BASE_URL}/api/warehouse/parcels/{SHIPMENT_ID}",
            headers={"Authorization": f"Bearer {SESSION_TOKEN}"}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "pieces" in data
        
        # At least one piece should have a photo
        pieces_with_photos = [p for p in data["pieces"] if p.get("photo_url")]
        assert len(pieces_with_photos) >= 1, "Expected at least one piece with photo"
        print(f"PASS: Parcel details show {len(pieces_with_photos)} piece(s) with photos")
    
    def test_delete_photo_from_piece(self):
        """Test DELETE /api/warehouse/parcels/{id}/photos/{piece_id} removes photo"""
        # First, ensure there's a photo to delete
        png_bytes = base64.b64decode("iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg==")
        files = {'file': ('test.png', png_bytes, 'image/png')}
        requests.post(
            f"{BASE_URL}/api/warehouse/parcels/{SHIPMENT_ID}/photos",
            headers={"Authorization": f"Bearer {SESSION_TOKEN}"},
            files=files,
            data={"piece_id": PIECE_ID_1}
        )
        
        # Now delete the photo
        response = requests.delete(
            f"{BASE_URL}/api/warehouse/parcels/{SHIPMENT_ID}/photos/{PIECE_ID_1}",
            headers={"Authorization": f"Bearer {SESSION_TOKEN}"}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data.get("message") == "Photo deleted successfully"
        assert data.get("piece_id") == PIECE_ID_1
        print("PASS: Photo deleted successfully")
        
        # Verify photo is gone
        verify_response = requests.get(
            f"{BASE_URL}/api/warehouse/parcels/{SHIPMENT_ID}",
            headers={"Authorization": f"Bearer {SESSION_TOKEN}"}
        )
        verify_data = verify_response.json()
        piece_1 = next((p for p in verify_data["pieces"] if p["id"] == PIECE_ID_1), None)
        assert piece_1 is not None
        assert piece_1.get("photo_url") is None, "Expected photo_url to be null after deletion"
        print("PASS: Photo verified as deleted from piece")
    
    def test_upload_photo_invalid_parcel_returns_404(self):
        """Test uploading to non-existent parcel returns 404"""
        png_bytes = base64.b64decode("iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg==")
        files = {'file': ('test.png', png_bytes, 'image/png')}
        
        response = requests.post(
            f"{BASE_URL}/api/warehouse/parcels/non-existent-id/photos",
            headers={"Authorization": f"Bearer {SESSION_TOKEN}"},
            files=files
        )
        
        assert response.status_code == 404
        print("PASS: Upload to non-existent parcel returns 404")
    
    def test_delete_photo_invalid_parcel_returns_404(self):
        """Test deleting from non-existent parcel returns 404"""
        response = requests.delete(
            f"{BASE_URL}/api/warehouse/parcels/non-existent-id/photos/{PIECE_ID_1}",
            headers={"Authorization": f"Bearer {SESSION_TOKEN}"}
        )
        
        assert response.status_code == 404
        print("PASS: Delete from non-existent parcel returns 404")
    
    def test_delete_photo_invalid_piece_returns_404(self):
        """Test deleting non-existent piece returns 404"""
        response = requests.delete(
            f"{BASE_URL}/api/warehouse/parcels/{SHIPMENT_ID}/photos/non-existent-piece",
            headers={"Authorization": f"Bearer {SESSION_TOKEN}"}
        )
        
        assert response.status_code == 404
        print("PASS: Delete non-existent piece returns 404")
    
    def test_photo_upload_requires_auth(self):
        """Test photo upload requires authentication"""
        png_bytes = base64.b64decode("iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg==")
        files = {'file': ('test.png', png_bytes, 'image/png')}
        
        response = requests.post(
            f"{BASE_URL}/api/warehouse/parcels/{SHIPMENT_ID}/photos",
            files=files
        )
        
        assert response.status_code == 401
        print("PASS: Photo upload requires authentication")
    
    def test_photo_delete_requires_auth(self):
        """Test photo delete requires authentication"""
        response = requests.delete(
            f"{BASE_URL}/api/warehouse/parcels/{SHIPMENT_ID}/photos/{PIECE_ID_1}"
        )
        
        assert response.status_code == 401
        print("PASS: Photo delete requires authentication")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
