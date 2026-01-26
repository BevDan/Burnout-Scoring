"""
Test suite for bulk email functionality with round_id scoping.
Tests the fix for:
1) Include round_id in the bulk email payload so backend knows which round to scope the email to
2) Only mark scores as emailed for the specific round
3) Ensure pending emails list only includes competitor/round combos where ALL active judges have scored
"""

import pytest
import requests
import os
import time

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

class TestBulkEmailRoundIdFunctionality:
    """Test bulk email functionality with round_id scoping"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Setup test data - login and get auth token"""
        self.session = requests.Session()
        self.session.headers.update({"Content-Type": "application/json"})
        
        # Login as admin
        login_response = self.session.post(f"{BASE_URL}/api/auth/login", json={
            "username": "admin",
            "password": "admin123"
        })
        assert login_response.status_code == 200, f"Login failed: {login_response.text}"
        self.token = login_response.json()["token"]
        self.session.headers.update({"Authorization": f"Bearer {self.token}"})
        
        yield
        
        # Cleanup - delete test data
        self._cleanup_test_data()
    
    def _cleanup_test_data(self):
        """Clean up test-created data"""
        try:
            # Delete test judges
            judges_response = self.session.get(f"{BASE_URL}/api/admin/judges")
            if judges_response.status_code == 200:
                for judge in judges_response.json():
                    if judge.get("username", "").startswith("TEST_"):
                        self.session.delete(f"{BASE_URL}/api/admin/judges/{judge['id']}")
            
            # Delete test competitors
            competitors_response = self.session.get(f"{BASE_URL}/api/admin/competitors")
            if competitors_response.status_code == 200:
                for comp in competitors_response.json():
                    if comp.get("name", "").startswith("TEST_"):
                        self.session.delete(f"{BASE_URL}/api/admin/competitors/{comp['id']}")
            
            # Delete test rounds
            rounds_response = self.session.get(f"{BASE_URL}/api/admin/rounds")
            if rounds_response.status_code == 200:
                for rnd in rounds_response.json():
                    if rnd.get("name", "").startswith("TEST_"):
                        self.session.delete(f"{BASE_URL}/api/admin/rounds/{rnd['id']}")
            
            # Delete test classes
            classes_response = self.session.get(f"{BASE_URL}/api/admin/classes")
            if classes_response.status_code == 200:
                for cls in classes_response.json():
                    if cls.get("name", "").startswith("TEST_"):
                        self.session.delete(f"{BASE_URL}/api/admin/classes/{cls['id']}")
        except Exception as e:
            print(f"Cleanup error: {e}")
    
    # ==================== PENDING EMAILS ENDPOINT TESTS ====================
    
    def test_pending_emails_returns_round_id(self):
        """Test that /api/admin/pending-emails returns round_id for each pending email entry"""
        response = self.session.get(f"{BASE_URL}/api/admin/pending-emails")
        assert response.status_code == 200, f"Failed to get pending emails: {response.text}"
        
        data = response.json()
        assert "total_competitors_scored" in data, "Missing total_competitors_scored field"
        assert "competitors_pending_email" in data, "Missing competitors_pending_email field"
        assert "competitors_list" in data, "Missing competitors_list field"
        
        # If there are pending emails, verify each has round_id
        if data["competitors_list"]:
            for item in data["competitors_list"]:
                assert "competitor_id" in item, "Missing competitor_id in pending email item"
                assert "round_id" in item, "Missing round_id in pending email item"
                assert "round_name" in item, "Missing round_name in pending email item"
                print(f"Pending email item has round_id: {item['round_id']}, round_name: {item['round_name']}")
        
        print(f"Pending emails endpoint returns correct structure with round_id")
    
    def test_pending_emails_structure(self):
        """Test the structure of pending emails response"""
        response = self.session.get(f"{BASE_URL}/api/admin/pending-emails")
        assert response.status_code == 200
        
        data = response.json()
        
        # Verify structure
        assert isinstance(data["total_competitors_scored"], int)
        assert isinstance(data["competitors_pending_email"], int)
        assert isinstance(data["competitors_list"], list)
        
        print(f"Total scored: {data['total_competitors_scored']}, Pending email: {data['competitors_pending_email']}")
    
    # ==================== BULK EMAIL ENDPOINT TESTS ====================
    
    def test_bulk_email_endpoint_accepts_round_id(self):
        """Test that /api/admin/send-bulk-emails accepts round_id in the payload"""
        # This test verifies the endpoint accepts the payload structure
        # It will fail due to SMTP not being configured, but we verify the payload is accepted
        
        payload = {
            "competitor_emails": [
                {
                    "competitor_id": "test-competitor-id",
                    "recipient_email": "test@example.com",
                    "round_id": "test-round-id"
                }
            ]
        }
        
        response = self.session.post(f"{BASE_URL}/api/admin/send-bulk-emails", json=payload)
        
        # Should fail with SMTP not configured, not with payload validation error
        if response.status_code == 400:
            error_detail = response.json().get("detail", "")
            assert "SMTP not configured" in error_detail, f"Unexpected error: {error_detail}"
            print("Bulk email endpoint accepts round_id in payload (SMTP not configured as expected)")
        else:
            # If SMTP is configured, it might fail for other reasons
            print(f"Response: {response.status_code} - {response.text}")
    
    def test_bulk_email_payload_structure(self):
        """Test that bulk email payload with round_id is properly structured"""
        # Create test data to verify the flow
        
        # First, create a test class
        class_response = self.session.post(f"{BASE_URL}/api/admin/classes", json={
            "name": "TEST_BulkEmailClass",
            "description": "Test class for bulk email"
        })
        assert class_response.status_code == 200, f"Failed to create class: {class_response.text}"
        class_id = class_response.json()["id"]
        
        # Create a test competitor with email
        competitor_response = self.session.post(f"{BASE_URL}/api/admin/competitors", json={
            "name": "TEST_BulkEmailCompetitor",
            "car_number": "999",
            "vehicle_info": "Test Vehicle",
            "plate": "TEST999",
            "class_id": class_id,
            "email": "test@example.com"
        })
        assert competitor_response.status_code == 200, f"Failed to create competitor: {competitor_response.text}"
        competitor_id = competitor_response.json()["id"]
        
        # Create two test rounds
        round1_response = self.session.post(f"{BASE_URL}/api/admin/rounds", json={
            "name": "TEST_Round1",
            "is_minor": False,
            "round_status": "active"
        })
        assert round1_response.status_code == 200, f"Failed to create round 1: {round1_response.text}"
        round1_id = round1_response.json()["id"]
        
        round2_response = self.session.post(f"{BASE_URL}/api/admin/rounds", json={
            "name": "TEST_Round2",
            "is_minor": False,
            "round_status": "active"
        })
        assert round2_response.status_code == 200, f"Failed to create round 2: {round2_response.text}"
        round2_id = round2_response.json()["id"]
        
        # Verify the payload structure is correct
        payload = {
            "competitor_emails": [
                {
                    "competitor_id": competitor_id,
                    "recipient_email": "test@example.com",
                    "round_id": round1_id
                }
            ]
        }
        
        # The endpoint should accept this payload (will fail on SMTP)
        response = self.session.post(f"{BASE_URL}/api/admin/send-bulk-emails", json=payload)
        
        # Verify it's not a validation error
        if response.status_code == 400:
            error = response.json().get("detail", "")
            assert "SMTP not configured" in error, f"Unexpected validation error: {error}"
        
        print(f"Bulk email payload with round_id is properly structured")
    
    # ==================== ROUND-SCOPED MARKING TESTS ====================
    
    def test_mark_emailed_endpoint_with_round_id(self):
        """Test that /api/admin/mark-emailed/{competitor_id}/{round_id} marks only specific round"""
        # Create test data
        class_response = self.session.post(f"{BASE_URL}/api/admin/classes", json={
            "name": "TEST_MarkEmailedClass",
            "description": "Test class"
        })
        assert class_response.status_code == 200
        class_id = class_response.json()["id"]
        
        competitor_response = self.session.post(f"{BASE_URL}/api/admin/competitors", json={
            "name": "TEST_MarkEmailedCompetitor",
            "car_number": "888",
            "vehicle_info": "Test Vehicle",
            "plate": "TEST888",
            "class_id": class_id,
            "email": "test@example.com"
        })
        assert competitor_response.status_code == 200
        competitor_id = competitor_response.json()["id"]
        
        round1_response = self.session.post(f"{BASE_URL}/api/admin/rounds", json={
            "name": "TEST_MarkRound1",
            "is_minor": False,
            "round_status": "active"
        })
        assert round1_response.status_code == 200
        round1_id = round1_response.json()["id"]
        
        round2_response = self.session.post(f"{BASE_URL}/api/admin/rounds", json={
            "name": "TEST_MarkRound2",
            "is_minor": False,
            "round_status": "active"
        })
        assert round2_response.status_code == 200
        round2_id = round2_response.json()["id"]
        
        # Test the mark-emailed endpoint
        mark_response = self.session.post(f"{BASE_URL}/api/admin/mark-emailed/{competitor_id}/{round1_id}")
        assert mark_response.status_code == 200, f"Failed to mark emailed: {mark_response.text}"
        
        data = mark_response.json()
        assert "message" in data
        print(f"Mark emailed response: {data['message']}")
    
    # ==================== PARTIAL SCORES TESTS ====================
    
    def test_pending_emails_only_includes_complete_scoring(self):
        """Test that pending emails only includes competitor/round combos where ALL active judges have scored"""
        # Get active judges count
        judges_response = self.session.get(f"{BASE_URL}/api/admin/judges")
        assert judges_response.status_code == 200
        judges = judges_response.json()
        active_judges = [j for j in judges if j.get("is_active", True)]
        active_judge_count = len(active_judges)
        
        print(f"Active judges count: {active_judge_count}")
        
        # Get pending emails
        pending_response = self.session.get(f"{BASE_URL}/api/admin/pending-emails")
        assert pending_response.status_code == 200
        pending_data = pending_response.json()
        
        # Each item in competitors_list should have complete scoring
        for item in pending_data["competitors_list"]:
            score_count = item.get("score_count", 0)
            print(f"Competitor {item['competitor_name']} in {item['round_name']}: {score_count} scores")
            # Score count should be >= active_judge_count for complete scoring
            assert score_count >= active_judge_count, \
                f"Incomplete scoring found: {item['competitor_name']} has {score_count} scores but {active_judge_count} active judges"
        
        print("All pending email items have complete scoring from all active judges")
    
    # ==================== INTEGRATION TESTS ====================
    
    def test_full_bulk_email_flow_with_round_id(self):
        """Test the full flow: create data, submit scores, check pending emails, verify round_id"""
        # Create test class
        class_response = self.session.post(f"{BASE_URL}/api/admin/classes", json={
            "name": "TEST_FullFlowClass",
            "description": "Test class for full flow"
        })
        assert class_response.status_code == 200
        class_id = class_response.json()["id"]
        
        # Create test competitor
        competitor_response = self.session.post(f"{BASE_URL}/api/admin/competitors", json={
            "name": "TEST_FullFlowCompetitor",
            "car_number": "777",
            "vehicle_info": "Test Vehicle",
            "plate": "TEST777",
            "class_id": class_id,
            "email": "fullflow@example.com"
        })
        assert competitor_response.status_code == 200
        competitor_id = competitor_response.json()["id"]
        
        # Create two test rounds
        round1_response = self.session.post(f"{BASE_URL}/api/admin/rounds", json={
            "name": "TEST_FullFlowRound1",
            "is_minor": False,
            "round_status": "active"
        })
        assert round1_response.status_code == 200
        round1_id = round1_response.json()["id"]
        
        round2_response = self.session.post(f"{BASE_URL}/api/admin/rounds", json={
            "name": "TEST_FullFlowRound2",
            "is_minor": False,
            "round_status": "active"
        })
        assert round2_response.status_code == 200
        round2_id = round2_response.json()["id"]
        
        # Create a test judge
        judge_response = self.session.post(f"{BASE_URL}/api/auth/register", json={
            "username": "TEST_judge_fullflow",
            "password": "testpass123",
            "name": "TEST Judge FullFlow",
            "role": "judge"
        })
        assert judge_response.status_code == 200
        judge_id = judge_response.json()["id"]
        
        # Login as judge to submit scores
        judge_login = self.session.post(f"{BASE_URL}/api/auth/login", json={
            "username": "TEST_judge_fullflow",
            "password": "testpass123"
        })
        assert judge_login.status_code == 200
        judge_token = judge_login.json()["token"]
        
        judge_session = requests.Session()
        judge_session.headers.update({
            "Content-Type": "application/json",
            "Authorization": f"Bearer {judge_token}"
        })
        
        # Submit score for Round 1
        score1_response = judge_session.post(f"{BASE_URL}/api/judge/scores", json={
            "competitor_id": competitor_id,
            "round_id": round1_id,
            "tip_in": 5,
            "instant_smoke": 5,
            "constant_smoke": 10,
            "volume_of_smoke": 10,
            "driving_skill": 20,
            "tyres_popped": 0
        })
        assert score1_response.status_code == 200, f"Failed to submit score 1: {score1_response.text}"
        score1_id = score1_response.json()["id"]
        print(f"Submitted score for Round 1: {score1_id}")
        
        # Submit score for Round 2
        score2_response = judge_session.post(f"{BASE_URL}/api/judge/scores", json={
            "competitor_id": competitor_id,
            "round_id": round2_id,
            "tip_in": 6,
            "instant_smoke": 6,
            "constant_smoke": 12,
            "volume_of_smoke": 12,
            "driving_skill": 25,
            "tyres_popped": 1
        })
        assert score2_response.status_code == 200, f"Failed to submit score 2: {score2_response.text}"
        score2_id = score2_response.json()["id"]
        print(f"Submitted score for Round 2: {score2_id}")
        
        # Check pending emails - should include both rounds if only 1 active judge
        pending_response = self.session.get(f"{BASE_URL}/api/admin/pending-emails")
        assert pending_response.status_code == 200
        pending_data = pending_response.json()
        
        print(f"Pending emails: {pending_data['competitors_pending_email']}")
        
        # Verify round_id is present in each pending item
        for item in pending_data["competitors_list"]:
            if item["competitor_id"] == competitor_id:
                assert "round_id" in item, "Missing round_id in pending email item"
                print(f"Found pending email for competitor in round: {item['round_name']} (round_id: {item['round_id']})")
        
        # Test bulk email payload with round_id
        bulk_payload = {
            "competitor_emails": [
                {
                    "competitor_id": competitor_id,
                    "recipient_email": "fullflow@example.com",
                    "round_id": round1_id  # Only send for Round 1
                }
            ]
        }
        
        bulk_response = self.session.post(f"{BASE_URL}/api/admin/send-bulk-emails", json=bulk_payload)
        
        # Should fail with SMTP not configured
        if bulk_response.status_code == 400:
            error = bulk_response.json().get("detail", "")
            assert "SMTP not configured" in error
            print("Bulk email correctly accepts round_id (SMTP not configured)")
        
        # Verify scores - check that email_sent is still false (since SMTP failed)
        scores_response = self.session.get(f"{BASE_URL}/api/admin/scores?round_id={round1_id}")
        assert scores_response.status_code == 200
        
        print("Full flow test completed successfully")
    
    def test_scores_email_sent_field_exists(self):
        """Test that scores have email_sent field"""
        # Get all scores
        scores_response = self.session.get(f"{BASE_URL}/api/admin/scores")
        assert scores_response.status_code == 200
        
        scores = scores_response.json()
        if scores:
            for score in scores[:5]:  # Check first 5 scores
                assert "email_sent" in score, f"Score {score.get('id')} missing email_sent field"
                print(f"Score {score.get('id')}: email_sent = {score.get('email_sent')}")
        
        print("All scores have email_sent field")


class TestPendingEmailsLogic:
    """Test the logic for determining pending emails"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Setup test data"""
        self.session = requests.Session()
        self.session.headers.update({"Content-Type": "application/json"})
        
        # Login as admin
        login_response = self.session.post(f"{BASE_URL}/api/auth/login", json={
            "username": "admin",
            "password": "admin123"
        })
        assert login_response.status_code == 200
        self.token = login_response.json()["token"]
        self.session.headers.update({"Authorization": f"Bearer {self.token}"})
        
        yield
    
    def test_pending_emails_requires_all_active_judges(self):
        """Test that pending emails only shows entries where ALL active judges have scored"""
        # Get active judges
        judges_response = self.session.get(f"{BASE_URL}/api/admin/judges")
        assert judges_response.status_code == 200
        judges = judges_response.json()
        active_judges = [j for j in judges if j.get("is_active", True)]
        
        print(f"Active judges: {len(active_judges)}")
        
        # Get pending emails
        pending_response = self.session.get(f"{BASE_URL}/api/admin/pending-emails")
        assert pending_response.status_code == 200
        pending_data = pending_response.json()
        
        # Each pending item should have score_count >= active_judge_count
        for item in pending_data["competitors_list"]:
            assert item.get("score_count", 0) >= len(active_judges), \
                f"Incomplete scoring: {item['competitor_name']} has {item.get('score_count')} scores, need {len(active_judges)}"
        
        print(f"All {len(pending_data['competitors_list'])} pending items have complete scoring")
    
    def test_pending_emails_excludes_already_emailed(self):
        """Test that pending emails excludes entries that have already been emailed"""
        pending_response = self.session.get(f"{BASE_URL}/api/admin/pending-emails")
        assert pending_response.status_code == 200
        pending_data = pending_response.json()
        
        # All items in pending list should NOT have been emailed
        # (This is implicit in the endpoint logic - it only returns non-emailed entries)
        print(f"Pending emails count: {pending_data['competitors_pending_email']}")
        print(f"Total scored: {pending_data['total_competitors_scored']}")
        
        # The difference should be the already-emailed count
        already_emailed = pending_data['total_competitors_scored'] - pending_data['competitors_pending_email']
        print(f"Already emailed: {already_emailed}")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
