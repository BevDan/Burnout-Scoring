"""
Backend tests for Settings endpoints (Logo upload, Website settings)
Tests the new printable reports feature settings
"""
import pytest
import requests
import os
import base64

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

class TestSettingsEndpoints:
    """Test settings endpoints for logo and website configuration"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Setup - get auth token for admin"""
        self.session = requests.Session()
        self.session.headers.update({"Content-Type": "application/json"})
        
        # Login as admin
        response = self.session.post(f"{BASE_URL}/api/auth/login", json={
            "username": "admin",
            "password": "admin123"
        })
        assert response.status_code == 200, f"Admin login failed: {response.text}"
        self.token = response.json()["token"]
        self.auth_headers = {"Authorization": f"Bearer {self.token}"}
    
    # ============ Logo Endpoints Tests ============
    
    def test_get_logo_no_logo(self):
        """Test GET /api/admin/settings/logo when no logo exists"""
        # First delete any existing logo
        self.session.delete(f"{BASE_URL}/api/admin/settings/logo", headers=self.auth_headers)
        
        # Now get logo - should return null
        response = self.session.get(f"{BASE_URL}/api/admin/settings/logo")
        assert response.status_code == 200
        data = response.json()
        assert "logo" in data
        # Logo can be None or null when not set
    
    def test_upload_logo_png(self):
        """Test POST /api/admin/settings/logo with PNG image"""
        # Create a simple 1x1 PNG image (smallest valid PNG)
        png_data = base64.b64decode(
            "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg=="
        )
        
        files = {'file': ('test_logo.png', png_data, 'image/png')}
        # Don't use session headers for multipart - set auth header separately
        response = requests.post(
            f"{BASE_URL}/api/admin/settings/logo",
            files=files,
            headers={"Authorization": f"Bearer {self.token}"}
        )
        
        assert response.status_code == 200, f"Logo upload failed: {response.text}"
        data = response.json()
        assert data["message"] == "Logo uploaded successfully"
        assert data["filename"] == "test_logo.png"
    
    def test_get_logo_after_upload(self):
        """Test GET /api/admin/settings/logo returns uploaded logo"""
        # First upload a logo
        png_data = base64.b64decode(
            "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg=="
        )
        files = {'file': ('test_logo.png', png_data, 'image/png')}
        upload_response = requests.post(
            f"{BASE_URL}/api/admin/settings/logo",
            files=files,
            headers={"Authorization": f"Bearer {self.token}"}
        )
        assert upload_response.status_code == 200, f"Upload failed: {upload_response.text}"
        
        # Now get the logo
        response = self.session.get(f"{BASE_URL}/api/admin/settings/logo")
        assert response.status_code == 200
        data = response.json()
        assert data["logo"] is not None
        assert data["logo"].startswith("data:image/png;base64,")
        assert "filename" in data
    
    def test_upload_logo_jpeg(self):
        """Test POST /api/admin/settings/logo with JPEG image"""
        # Minimal valid JPEG
        jpeg_data = base64.b64decode(
            "/9j/4AAQSkZJRgABAQEASABIAAD/2wBDAAgGBgcGBQgHBwcJCQgKDBQNDAsLDBkSEw8UHRofHh0aHBwgJC4nICIsIxwcKDcpLDAxNDQ0Hyc5PTgyPC4zNDL/2wBDAQkJCQwLDBgNDRgyIRwhMjIyMjIyMjIyMjIyMjIyMjIyMjIyMjIyMjIyMjIyMjIyMjIyMjIyMjIyMjIyMjIyMjL/wAARCAABAAEDASIAAhEBAxEB/8QAFQABAQAAAAAAAAAAAAAAAAAAAAn/xAAUEAEAAAAAAAAAAAAAAAAAAAAA/8QAFQEBAQAAAAAAAAAAAAAAAAAAAAX/xAAUEQEAAAAAAAAAAAAAAAAAAAAA/9oADAMBEQCEAwEPwAB//9k="
        )
        
        files = {'file': ('test_logo.jpg', jpeg_data, 'image/jpeg')}
        response = requests.post(
            f"{BASE_URL}/api/admin/settings/logo",
            files=files,
            headers={"Authorization": f"Bearer {self.token}"}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["message"] == "Logo uploaded successfully"
    
    def test_upload_logo_invalid_type(self):
        """Test POST /api/admin/settings/logo rejects invalid file types"""
        # Try to upload a text file
        files = {'file': ('test.txt', b'This is not an image', 'text/plain')}
        response = requests.post(
            f"{BASE_URL}/api/admin/settings/logo",
            files=files,
            headers={"Authorization": f"Bearer {self.token}"}
        )
        
        assert response.status_code == 400
        data = response.json()
        assert "Only PNG, JPG, and WebP images are allowed" in data["detail"]
    
    def test_delete_logo(self):
        """Test DELETE /api/admin/settings/logo"""
        # First upload a logo
        png_data = base64.b64decode(
            "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg=="
        )
        files = {'file': ('test_logo.png', png_data, 'image/png')}
        requests.post(
            f"{BASE_URL}/api/admin/settings/logo",
            files=files,
            headers={"Authorization": f"Bearer {self.token}"}
        )
        
        # Delete the logo
        response = self.session.delete(
            f"{BASE_URL}/api/admin/settings/logo",
            headers=self.auth_headers
        )
        assert response.status_code == 200
        data = response.json()
        assert data["message"] == "Logo deleted successfully"
        
        # Verify logo is gone
        get_response = self.session.get(f"{BASE_URL}/api/admin/settings/logo")
        assert get_response.status_code == 200
        get_data = get_response.json()
        assert get_data["logo"] is None
    
    def test_upload_logo_requires_auth(self):
        """Test POST /api/admin/settings/logo requires authentication"""
        png_data = base64.b64decode(
            "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg=="
        )
        files = {'file': ('test_logo.png', png_data, 'image/png')}
        
        # Try without auth
        response = requests.post(
            f"{BASE_URL}/api/admin/settings/logo",
            files=files
        )
        assert response.status_code in [401, 403]
    
    def test_delete_logo_requires_auth(self):
        """Test DELETE /api/admin/settings/logo requires authentication"""
        response = requests.delete(f"{BASE_URL}/api/admin/settings/logo")
        assert response.status_code in [401, 403]
    
    # ============ Website Settings Tests ============
    
    def test_get_website_settings_empty(self):
        """Test GET /api/admin/settings/website returns empty defaults"""
        response = self.session.get(f"{BASE_URL}/api/admin/settings/website")
        assert response.status_code == 200
        data = response.json()
        assert "website_url" in data
        assert "organization_name" in data
    
    def test_update_website_settings(self):
        """Test PUT /api/admin/settings/website updates settings"""
        response = self.session.put(
            f"{BASE_URL}/api/admin/settings/website?website_url=testsite.com&organization_name=Test%20Org",
            headers=self.auth_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["message"] == "Settings updated successfully"
        
        # Verify settings were saved
        get_response = self.session.get(f"{BASE_URL}/api/admin/settings/website")
        assert get_response.status_code == 200
        get_data = get_response.json()
        assert get_data["website_url"] == "testsite.com"
        assert get_data["organization_name"] == "Test Org"
    
    def test_update_website_settings_partial(self):
        """Test PUT /api/admin/settings/website with only website_url"""
        response = self.session.put(
            f"{BASE_URL}/api/admin/settings/website?website_url=newsite.com",
            headers=self.auth_headers
        )
        
        assert response.status_code == 200
        
        # Verify
        get_response = self.session.get(f"{BASE_URL}/api/admin/settings/website")
        get_data = get_response.json()
        assert get_data["website_url"] == "newsite.com"
    
    def test_update_website_settings_requires_admin(self):
        """Test PUT /api/admin/settings/website requires admin role"""
        # Try without auth
        response = requests.put(
            f"{BASE_URL}/api/admin/settings/website?website_url=test.com"
        )
        assert response.status_code in [401, 403]
    
    def test_website_settings_persistence(self):
        """Test website settings persist across requests"""
        # Set settings
        self.session.put(
            f"{BASE_URL}/api/admin/settings/website?website_url=persistent.com&organization_name=Persistent%20Org",
            headers=self.auth_headers
        )
        
        # Create new session and verify
        new_session = requests.Session()
        response = new_session.get(f"{BASE_URL}/api/admin/settings/website")
        assert response.status_code == 200
        data = response.json()
        assert data["website_url"] == "persistent.com"
        assert data["organization_name"] == "Persistent Org"


class TestLeaderboardEndpoints:
    """Test leaderboard endpoints used by print reports"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Setup - get auth token"""
        self.session = requests.Session()
        
        # Login as admin
        response = self.session.post(f"{BASE_URL}/api/auth/login", json={
            "username": "admin",
            "password": "admin123"
        })
        assert response.status_code == 200
        self.token = response.json()["token"]
        self.auth_headers = {"Authorization": f"Bearer {self.token}"}
    
    def test_get_rounds(self):
        """Test GET /api/admin/rounds returns rounds list"""
        response = self.session.get(
            f"{BASE_URL}/api/admin/rounds",
            headers=self.auth_headers
        )
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
    
    def test_get_classes(self):
        """Test GET /api/admin/classes returns classes list"""
        response = self.session.get(
            f"{BASE_URL}/api/admin/classes",
            headers=self.auth_headers
        )
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
    
    def test_get_events(self):
        """Test GET /api/admin/events returns events list"""
        response = self.session.get(
            f"{BASE_URL}/api/admin/events",
            headers=self.auth_headers
        )
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
    
    def test_get_minor_rounds_leaderboard(self):
        """Test GET /api/leaderboard/minor-rounds/cumulative"""
        response = self.session.get(
            f"{BASE_URL}/api/leaderboard/minor-rounds/cumulative",
            headers=self.auth_headers
        )
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
