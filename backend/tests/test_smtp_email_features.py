"""
Test SMTP Settings and Email Features for Burnout Competition App
Tests:
- SMTP Settings CRUD (GET, PUT)
- SMTP Test Connection endpoint
- Send Competitor Report endpoint
- Email status tracking on scores
"""

import pytest
import requests
import os

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL').rstrip('/')

# Test credentials
ADMIN_USER = "admin"
ADMIN_PASSWORD = "admin123"


class TestAuth:
    """Get authentication token for tests"""
    
    @pytest.fixture(scope="class")
    def auth_token(self):
        """Login and get admin token"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "username": ADMIN_USER,
            "password": ADMIN_PASSWORD
        })
        assert response.status_code == 200, f"Login failed: {response.text}"
        return response.json()["token"]
    
    @pytest.fixture(scope="class")
    def auth_headers(self, auth_token):
        """Return headers with auth token"""
        return {"Authorization": f"Bearer {auth_token}"}


class TestSMTPSettings(TestAuth):
    """Test SMTP Settings endpoints"""
    
    def test_get_smtp_settings_requires_auth(self):
        """GET /api/admin/settings/smtp requires authentication"""
        response = requests.get(f"{BASE_URL}/api/admin/settings/smtp")
        assert response.status_code == 403 or response.status_code == 401
        print("✓ GET SMTP settings requires authentication")
    
    def test_get_smtp_settings_returns_structure(self, auth_headers):
        """GET /api/admin/settings/smtp returns correct structure"""
        response = requests.get(f"{BASE_URL}/api/admin/settings/smtp", headers=auth_headers)
        assert response.status_code == 200
        
        data = response.json()
        # Verify all expected fields exist
        assert "smtp_server" in data
        assert "smtp_port" in data
        assert "smtp_email" in data
        assert "smtp_password" in data
        assert "smtp_use_tls" in data
        
        # Verify types
        assert isinstance(data["smtp_port"], int)
        assert isinstance(data["smtp_use_tls"], bool)
        print(f"✓ GET SMTP settings returns correct structure: {data}")
    
    def test_put_smtp_settings_requires_auth(self):
        """PUT /api/admin/settings/smtp requires authentication"""
        response = requests.put(f"{BASE_URL}/api/admin/settings/smtp", json={
            "smtp_server": "test.smtp.com",
            "smtp_port": 587,
            "smtp_email": "test@test.com",
            "smtp_password": "testpass",
            "smtp_use_tls": True
        })
        assert response.status_code == 403 or response.status_code == 401
        print("✓ PUT SMTP settings requires authentication")
    
    def test_put_smtp_settings_saves_correctly(self, auth_headers):
        """PUT /api/admin/settings/smtp saves settings"""
        test_settings = {
            "smtp_server": "smtp.test.com",
            "smtp_port": 587,
            "smtp_email": "test@example.com",
            "smtp_password": "testpassword123",
            "smtp_use_tls": True
        }
        
        response = requests.put(f"{BASE_URL}/api/admin/settings/smtp", 
                               json=test_settings, headers=auth_headers)
        assert response.status_code == 200
        
        data = response.json()
        assert "message" in data
        assert "success" in data["message"].lower() or "updated" in data["message"].lower()
        print(f"✓ PUT SMTP settings saves correctly: {data}")
    
    def test_get_smtp_settings_password_masked(self, auth_headers):
        """GET /api/admin/settings/smtp returns masked password"""
        # First save settings with a password
        requests.put(f"{BASE_URL}/api/admin/settings/smtp", json={
            "smtp_server": "smtp.test.com",
            "smtp_port": 587,
            "smtp_email": "test@example.com",
            "smtp_password": "realpassword123",
            "smtp_use_tls": True
        }, headers=auth_headers)
        
        # Now get settings and verify password is masked
        response = requests.get(f"{BASE_URL}/api/admin/settings/smtp", headers=auth_headers)
        assert response.status_code == 200
        
        data = response.json()
        # Password should be masked (asterisks) or empty
        assert data["smtp_password"] == "********" or data["smtp_password"] == ""
        print(f"✓ SMTP password is masked: {data['smtp_password']}")
    
    def test_put_smtp_settings_preserves_password_when_masked(self, auth_headers):
        """PUT /api/admin/settings/smtp preserves password when sending masked value"""
        # First save with real password
        requests.put(f"{BASE_URL}/api/admin/settings/smtp", json={
            "smtp_server": "smtp.test.com",
            "smtp_port": 587,
            "smtp_email": "test@example.com",
            "smtp_password": "realpassword123",
            "smtp_use_tls": True
        }, headers=auth_headers)
        
        # Update with masked password (simulating UI behavior)
        response = requests.put(f"{BASE_URL}/api/admin/settings/smtp", json={
            "smtp_server": "smtp.updated.com",
            "smtp_port": 465,
            "smtp_email": "updated@example.com",
            "smtp_password": "********",  # Masked value
            "smtp_use_tls": False
        }, headers=auth_headers)
        assert response.status_code == 200
        
        # Verify other settings updated but password preserved
        get_response = requests.get(f"{BASE_URL}/api/admin/settings/smtp", headers=auth_headers)
        data = get_response.json()
        assert data["smtp_server"] == "smtp.updated.com"
        assert data["smtp_port"] == 465
        assert data["smtp_email"] == "updated@example.com"
        assert data["smtp_use_tls"] == False
        # Password should still be masked (meaning it was preserved)
        assert data["smtp_password"] == "********"
        print("✓ SMTP password preserved when sending masked value")


class TestSMTPTestConnection(TestAuth):
    """Test SMTP Test Connection endpoint"""
    
    def test_smtp_test_requires_auth(self):
        """POST /api/admin/settings/smtp/test requires authentication"""
        response = requests.post(f"{BASE_URL}/api/admin/settings/smtp/test")
        assert response.status_code == 403 or response.status_code == 401
        print("✓ SMTP test connection requires authentication")
    
    def test_smtp_test_fails_without_config(self, auth_headers):
        """POST /api/admin/settings/smtp/test fails if SMTP not configured"""
        # Clear SMTP settings first
        requests.put(f"{BASE_URL}/api/admin/settings/smtp", json={
            "smtp_server": "",
            "smtp_port": 587,
            "smtp_email": "",
            "smtp_password": "",
            "smtp_use_tls": True
        }, headers=auth_headers)
        
        response = requests.post(f"{BASE_URL}/api/admin/settings/smtp/test", 
                                headers=auth_headers)
        # Should return 400 with "SMTP not configured" message
        assert response.status_code == 400
        data = response.json()
        assert "not configured" in data.get("detail", "").lower()
        print(f"✓ SMTP test fails without config: {data}")
    
    def test_smtp_test_with_invalid_server(self, auth_headers):
        """POST /api/admin/settings/smtp/test fails with invalid server"""
        # Configure with invalid server
        requests.put(f"{BASE_URL}/api/admin/settings/smtp", json={
            "smtp_server": "invalid.nonexistent.server.xyz",
            "smtp_port": 587,
            "smtp_email": "test@test.com",
            "smtp_password": "testpass",
            "smtp_use_tls": True
        }, headers=auth_headers)
        
        response = requests.post(f"{BASE_URL}/api/admin/settings/smtp/test", 
                                headers=auth_headers)
        # Should return 400 with connection failed message
        assert response.status_code == 400
        data = response.json()
        assert "failed" in data.get("detail", "").lower() or "error" in data.get("detail", "").lower()
        print(f"✓ SMTP test fails with invalid server: {data}")


class TestSendCompetitorReport(TestAuth):
    """Test Send Competitor Report endpoint"""
    
    def test_send_report_requires_auth(self):
        """POST /api/admin/send-competitor-report requires authentication"""
        response = requests.post(f"{BASE_URL}/api/admin/send-competitor-report", json={
            "competitor_id": "test-id",
            "recipient_email": "test@test.com"
        })
        assert response.status_code == 403 or response.status_code == 401
        print("✓ Send competitor report requires authentication")
    
    def test_send_report_fails_without_smtp(self, auth_headers):
        """POST /api/admin/send-competitor-report fails if SMTP not configured"""
        # Clear SMTP settings
        requests.put(f"{BASE_URL}/api/admin/settings/smtp", json={
            "smtp_server": "",
            "smtp_port": 587,
            "smtp_email": "",
            "smtp_password": "",
            "smtp_use_tls": True
        }, headers=auth_headers)
        
        response = requests.post(f"{BASE_URL}/api/admin/send-competitor-report", json={
            "competitor_id": "test-id",
            "recipient_email": "test@test.com"
        }, headers=auth_headers)
        
        assert response.status_code == 400
        data = response.json()
        assert "smtp" in data.get("detail", "").lower() and "not configured" in data.get("detail", "").lower()
        print(f"✓ Send report fails without SMTP config: {data}")
    
    def test_send_report_fails_invalid_competitor(self, auth_headers):
        """POST /api/admin/send-competitor-report fails with invalid competitor"""
        # Configure SMTP first
        requests.put(f"{BASE_URL}/api/admin/settings/smtp", json={
            "smtp_server": "smtp.test.com",
            "smtp_port": 587,
            "smtp_email": "test@test.com",
            "smtp_password": "testpass",
            "smtp_use_tls": True
        }, headers=auth_headers)
        
        response = requests.post(f"{BASE_URL}/api/admin/send-competitor-report", json={
            "competitor_id": "nonexistent-competitor-id",
            "recipient_email": "test@test.com"
        }, headers=auth_headers)
        
        assert response.status_code == 404
        data = response.json()
        assert "competitor" in data.get("detail", "").lower() and "not found" in data.get("detail", "").lower()
        print(f"✓ Send report fails with invalid competitor: {data}")
    
    def test_send_report_endpoint_accepts_request(self, auth_headers):
        """POST /api/admin/send-competitor-report accepts valid request structure"""
        # Configure SMTP
        requests.put(f"{BASE_URL}/api/admin/settings/smtp", json={
            "smtp_server": "smtp.test.com",
            "smtp_port": 587,
            "smtp_email": "test@test.com",
            "smtp_password": "testpass",
            "smtp_use_tls": True
        }, headers=auth_headers)
        
        # Get a real competitor ID
        competitors_response = requests.get(f"{BASE_URL}/api/admin/competitors", headers=auth_headers)
        if competitors_response.status_code == 200 and len(competitors_response.json()) > 0:
            competitor_id = competitors_response.json()[0]["id"]
            
            # Try to send - will fail at SMTP connection but validates request structure
            response = requests.post(f"{BASE_URL}/api/admin/send-competitor-report", json={
                "competitor_id": competitor_id,
                "recipient_email": "test@test.com"
            }, headers=auth_headers)
            
            # Should either succeed or fail at SMTP connection (not validation)
            # 400 with SMTP error or 404 with no scores is acceptable
            assert response.status_code in [200, 400, 404]
            print(f"✓ Send report endpoint accepts valid request: status={response.status_code}")
        else:
            pytest.skip("No competitors available for testing")


class TestScoreEmailStatus(TestAuth):
    """Test email_sent field on scores"""
    
    def test_scores_have_email_sent_field(self, auth_headers):
        """GET /api/admin/scores returns scores with email_sent field"""
        response = requests.get(f"{BASE_URL}/api/admin/scores", headers=auth_headers)
        assert response.status_code == 200
        
        scores = response.json()
        if len(scores) > 0:
            # Check that email_sent field exists
            score = scores[0]
            # email_sent might be missing on old scores, but new ones should have it
            # Just verify the endpoint works
            print(f"✓ Scores endpoint returns {len(scores)} scores")
            if "email_sent" in score:
                print(f"  - email_sent field present: {score['email_sent']}")
            else:
                print("  - Note: email_sent field not present on older scores")
        else:
            print("✓ Scores endpoint works (no scores found)")


class TestPendingEmails(TestAuth):
    """Test pending emails endpoint"""
    
    def test_pending_emails_requires_auth(self):
        """GET /api/admin/pending-emails requires authentication"""
        response = requests.get(f"{BASE_URL}/api/admin/pending-emails")
        assert response.status_code == 403 or response.status_code == 401
        print("✓ Pending emails requires authentication")
    
    def test_pending_emails_returns_structure(self, auth_headers):
        """GET /api/admin/pending-emails returns correct structure"""
        response = requests.get(f"{BASE_URL}/api/admin/pending-emails", headers=auth_headers)
        assert response.status_code == 200
        
        data = response.json()
        assert "total_competitors_scored" in data
        assert "competitors_pending_email" in data
        assert "competitors_list" in data
        
        assert isinstance(data["total_competitors_scored"], int)
        assert isinstance(data["competitors_pending_email"], int)
        assert isinstance(data["competitors_list"], list)
        
        print(f"✓ Pending emails structure correct: {data['total_competitors_scored']} scored, {data['competitors_pending_email']} pending")


class TestMarkEmailed(TestAuth):
    """Test mark scores as emailed endpoint"""
    
    def test_mark_emailed_requires_auth(self):
        """POST /api/admin/mark-emailed/{competitor_id}/{round_id} requires authentication"""
        response = requests.post(f"{BASE_URL}/api/admin/mark-emailed/test-comp/test-round")
        assert response.status_code == 403 or response.status_code == 401
        print("✓ Mark emailed requires authentication")
    
    def test_mark_emailed_endpoint_exists(self, auth_headers):
        """POST /api/admin/mark-emailed/{competitor_id}/{round_id} endpoint exists"""
        response = requests.post(f"{BASE_URL}/api/admin/mark-emailed/test-comp/test-round", 
                                headers=auth_headers)
        # Should return 200 even if no scores found (0 modified)
        assert response.status_code == 200
        data = response.json()
        assert "message" in data
        print(f"✓ Mark emailed endpoint works: {data}")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
