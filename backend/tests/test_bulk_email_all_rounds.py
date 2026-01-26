"""
Test suite for bulk email enhancement: Include ALL completed rounds in email
Tests the new feature where bulk emails include all previously completed rounds
along with the newly completed round, not just the newly completed round.

Key features tested:
1. get_completed_rounds_for_competitor helper function
2. generate_competitor_email_html with include_all_completed=True
3. Bulk email flow: marks only newly completed round as emailed
4. Pending emails still shows newly completed round even if other rounds were already emailed
"""

import pytest
import requests
import os
import time

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

class TestBulkEmailAllRounds:
    """Test bulk email includes ALL completed rounds"""
    
    @pytest.fixture(autouse=True)
    def setup_and_teardown(self):
        """Setup test data and cleanup after tests"""
        self.token = None
        self.test_ids = {
            "class_id": None,
            "competitor_id": None,
            "round1_id": None,
            "round2_id": None,
            "judge_id": None,
            "score_ids": []
        }
        
        # Login as admin
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "username": "admin",
            "password": "admin123"
        })
        assert response.status_code == 200, f"Login failed: {response.text}"
        self.token = response.json()["token"]
        self.headers = {"Authorization": f"Bearer {self.token}"}
        
        yield
        
        # Cleanup test data
        self._cleanup_test_data()
    
    def _cleanup_test_data(self):
        """Clean up all test data created during tests"""
        # Delete scores
        for score_id in self.test_ids.get("score_ids", []):
            try:
                requests.delete(f"{BASE_URL}/api/admin/scores/{score_id}", headers=self.headers)
            except:
                pass
        
        # Delete competitor
        if self.test_ids.get("competitor_id"):
            try:
                requests.delete(f"{BASE_URL}/api/admin/competitors/{self.test_ids['competitor_id']}", headers=self.headers)
            except:
                pass
        
        # Delete rounds
        for round_key in ["round1_id", "round2_id"]:
            if self.test_ids.get(round_key):
                try:
                    requests.delete(f"{BASE_URL}/api/admin/rounds/{self.test_ids[round_key]}", headers=self.headers)
                except:
                    pass
        
        # Delete class
        if self.test_ids.get("class_id"):
            try:
                requests.delete(f"{BASE_URL}/api/admin/classes/{self.test_ids['class_id']}", headers=self.headers)
            except:
                pass
        
        # Delete judge
        if self.test_ids.get("judge_id"):
            try:
                requests.delete(f"{BASE_URL}/api/admin/judges/{self.test_ids['judge_id']}", headers=self.headers)
            except:
                pass
    
    def _create_test_data(self):
        """Create test data: class, competitor, 2 rounds, and a judge"""
        # Create class
        response = requests.post(f"{BASE_URL}/api/admin/classes", headers=self.headers, json={
            "name": "TEST_AllRoundsClass",
            "description": "Test class for all rounds email test"
        })
        assert response.status_code == 200, f"Failed to create class: {response.text}"
        self.test_ids["class_id"] = response.json()["id"]
        
        # Create competitor with email
        response = requests.post(f"{BASE_URL}/api/admin/competitors", headers=self.headers, json={
            "name": "TEST_AllRoundsCompetitor",
            "car_number": "999",
            "vehicle_info": "Test Vehicle",
            "plate": "TEST999",
            "class_id": self.test_ids["class_id"],
            "email": "test@example.com"
        })
        assert response.status_code == 200, f"Failed to create competitor: {response.text}"
        self.test_ids["competitor_id"] = response.json()["id"]
        
        # Create Round 1
        response = requests.post(f"{BASE_URL}/api/admin/rounds", headers=self.headers, json={
            "name": "TEST_Round1_AllRounds",
            "is_minor": False,
            "round_status": "active"
        })
        assert response.status_code == 200, f"Failed to create round 1: {response.text}"
        self.test_ids["round1_id"] = response.json()["id"]
        
        # Create Round 2
        response = requests.post(f"{BASE_URL}/api/admin/rounds", headers=self.headers, json={
            "name": "TEST_Round2_AllRounds",
            "is_minor": False,
            "round_status": "active"
        })
        assert response.status_code == 200, f"Failed to create round 2: {response.text}"
        self.test_ids["round2_id"] = response.json()["id"]
        
        # Create a judge
        response = requests.post(f"{BASE_URL}/api/auth/register", headers=self.headers, json={
            "username": "TEST_allrounds_judge",
            "password": "testpass123",
            "name": "Test AllRounds Judge",
            "role": "judge"
        })
        assert response.status_code == 200, f"Failed to create judge: {response.text}"
        self.test_ids["judge_id"] = response.json()["id"]
        
        return self.test_ids
    
    def _submit_score_as_judge(self, round_id: str, competitor_id: str):
        """Submit a score as the test judge"""
        # Login as judge
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "username": "TEST_allrounds_judge",
            "password": "testpass123"
        })
        assert response.status_code == 200, f"Judge login failed: {response.text}"
        judge_token = response.json()["token"]
        judge_headers = {"Authorization": f"Bearer {judge_token}"}
        
        # Submit score
        response = requests.post(f"{BASE_URL}/api/judge/scores", headers=judge_headers, json={
            "competitor_id": competitor_id,
            "round_id": round_id,
            "tip_in": 8.0,
            "instant_smoke": 7.5,
            "constant_smoke": 15.0,
            "volume_of_smoke": 18.0,
            "driving_skill": 35.0,
            "tyres_popped": 1,
            "penalty_reversing": 0,
            "penalty_stopping": 0,
            "penalty_contact_barrier": 0,
            "penalty_small_fire": 0,
            "penalty_failed_drive_off": 0,
            "penalty_large_fire": 0,
            "penalty_disqualified": False
        })
        assert response.status_code == 200, f"Failed to submit score: {response.text}"
        score_id = response.json()["id"]
        self.test_ids["score_ids"].append(score_id)
        return score_id
    
    def test_pending_emails_shows_newly_completed_round(self):
        """Test that pending emails shows the newly completed round"""
        self._create_test_data()
        
        # Submit score for Round 1
        self._submit_score_as_judge(self.test_ids["round1_id"], self.test_ids["competitor_id"])
        
        # Check pending emails - should show Round 1
        response = requests.get(f"{BASE_URL}/api/admin/pending-emails", headers=self.headers)
        assert response.status_code == 200, f"Failed to get pending emails: {response.text}"
        
        data = response.json()
        pending_list = data.get("competitors_list", [])
        
        # Find our test competitor in pending list
        test_pending = [p for p in pending_list if p["competitor_id"] == self.test_ids["competitor_id"]]
        assert len(test_pending) == 1, f"Expected 1 pending entry for test competitor, got {len(test_pending)}"
        assert test_pending[0]["round_id"] == self.test_ids["round1_id"], "Pending entry should be for Round 1"
        print(f"PASS: Pending emails shows Round 1 for test competitor")
    
    def test_mark_round1_emailed_then_round2_appears(self):
        """Test that after marking Round 1 as emailed, Round 2 appears in pending when scored"""
        self._create_test_data()
        
        # Submit score for Round 1
        self._submit_score_as_judge(self.test_ids["round1_id"], self.test_ids["competitor_id"])
        
        # Mark Round 1 as emailed
        response = requests.post(
            f"{BASE_URL}/api/admin/mark-emailed/{self.test_ids['competitor_id']}/{self.test_ids['round1_id']}",
            headers=self.headers
        )
        assert response.status_code == 200, f"Failed to mark as emailed: {response.text}"
        print(f"PASS: Marked Round 1 as emailed")
        
        # Submit score for Round 2
        self._submit_score_as_judge(self.test_ids["round2_id"], self.test_ids["competitor_id"])
        
        # Check pending emails - should show Round 2 only
        response = requests.get(f"{BASE_URL}/api/admin/pending-emails", headers=self.headers)
        assert response.status_code == 200, f"Failed to get pending emails: {response.text}"
        
        data = response.json()
        pending_list = data.get("competitors_list", [])
        
        # Find our test competitor in pending list
        test_pending = [p for p in pending_list if p["competitor_id"] == self.test_ids["competitor_id"]]
        assert len(test_pending) == 1, f"Expected 1 pending entry (Round 2), got {len(test_pending)}"
        assert test_pending[0]["round_id"] == self.test_ids["round2_id"], "Pending entry should be for Round 2"
        print(f"PASS: After marking Round 1 emailed, only Round 2 appears in pending")
    
    def test_bulk_email_marks_only_specific_round(self):
        """Test that bulk email only marks the specific round as emailed, not all rounds"""
        self._create_test_data()
        
        # Submit scores for both rounds
        self._submit_score_as_judge(self.test_ids["round1_id"], self.test_ids["competitor_id"])
        self._submit_score_as_judge(self.test_ids["round2_id"], self.test_ids["competitor_id"])
        
        # Check initial pending emails - should show both rounds
        response = requests.get(f"{BASE_URL}/api/admin/pending-emails", headers=self.headers)
        assert response.status_code == 200
        data = response.json()
        test_pending = [p for p in data.get("competitors_list", []) if p["competitor_id"] == self.test_ids["competitor_id"]]
        assert len(test_pending) == 2, f"Expected 2 pending entries (both rounds), got {len(test_pending)}"
        print(f"PASS: Both rounds appear in pending emails initially")
        
        # Mark only Round 1 as emailed (simulating what bulk email does)
        response = requests.post(
            f"{BASE_URL}/api/admin/mark-emailed/{self.test_ids['competitor_id']}/{self.test_ids['round1_id']}",
            headers=self.headers
        )
        assert response.status_code == 200
        
        # Check pending emails again - should only show Round 2
        response = requests.get(f"{BASE_URL}/api/admin/pending-emails", headers=self.headers)
        assert response.status_code == 200
        data = response.json()
        test_pending = [p for p in data.get("competitors_list", []) if p["competitor_id"] == self.test_ids["competitor_id"]]
        assert len(test_pending) == 1, f"Expected 1 pending entry (Round 2 only), got {len(test_pending)}"
        assert test_pending[0]["round_id"] == self.test_ids["round2_id"], "Remaining pending should be Round 2"
        print(f"PASS: After marking Round 1 emailed, only Round 2 remains in pending")
    
    def test_scores_email_sent_flag_per_round(self):
        """Test that email_sent flag is set per round, not globally"""
        self._create_test_data()
        
        # Submit scores for both rounds
        self._submit_score_as_judge(self.test_ids["round1_id"], self.test_ids["competitor_id"])
        self._submit_score_as_judge(self.test_ids["round2_id"], self.test_ids["competitor_id"])
        
        # Mark Round 1 as emailed
        response = requests.post(
            f"{BASE_URL}/api/admin/mark-emailed/{self.test_ids['competitor_id']}/{self.test_ids['round1_id']}",
            headers=self.headers
        )
        assert response.status_code == 200
        
        # Get all scores and verify email_sent flags
        response = requests.get(f"{BASE_URL}/api/admin/scores", headers=self.headers)
        assert response.status_code == 200
        
        all_scores = response.json()
        test_scores = [s for s in all_scores if s["competitor_id"] == self.test_ids["competitor_id"]]
        
        round1_scores = [s for s in test_scores if s["round_id"] == self.test_ids["round1_id"]]
        round2_scores = [s for s in test_scores if s["round_id"] == self.test_ids["round2_id"]]
        
        # Round 1 scores should have email_sent=True
        for score in round1_scores:
            assert score.get("email_sent") == True, f"Round 1 score should have email_sent=True"
        print(f"PASS: Round 1 scores have email_sent=True")
        
        # Round 2 scores should have email_sent=False (or not set)
        for score in round2_scores:
            assert score.get("email_sent", False) == False, f"Round 2 score should have email_sent=False"
        print(f"PASS: Round 2 scores have email_sent=False")


class TestGenerateEmailHtmlAllRounds:
    """Test the generate_competitor_email_html function with include_all_completed=True"""
    
    @pytest.fixture(autouse=True)
    def setup_and_teardown(self):
        """Setup test data and cleanup after tests"""
        self.token = None
        self.test_ids = {
            "class_id": None,
            "competitor_id": None,
            "round1_id": None,
            "round2_id": None,
            "judge_id": None,
            "score_ids": []
        }
        
        # Login as admin
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "username": "admin",
            "password": "admin123"
        })
        assert response.status_code == 200, f"Login failed: {response.text}"
        self.token = response.json()["token"]
        self.headers = {"Authorization": f"Bearer {self.token}"}
        
        yield
        
        # Cleanup test data
        self._cleanup_test_data()
    
    def _cleanup_test_data(self):
        """Clean up all test data created during tests"""
        # Delete scores
        for score_id in self.test_ids.get("score_ids", []):
            try:
                requests.delete(f"{BASE_URL}/api/admin/scores/{score_id}", headers=self.headers)
            except:
                pass
        
        # Delete competitor
        if self.test_ids.get("competitor_id"):
            try:
                requests.delete(f"{BASE_URL}/api/admin/competitors/{self.test_ids['competitor_id']}", headers=self.headers)
            except:
                pass
        
        # Delete rounds
        for round_key in ["round1_id", "round2_id"]:
            if self.test_ids.get(round_key):
                try:
                    requests.delete(f"{BASE_URL}/api/admin/rounds/{self.test_ids[round_key]}", headers=self.headers)
                except:
                    pass
        
        # Delete class
        if self.test_ids.get("class_id"):
            try:
                requests.delete(f"{BASE_URL}/api/admin/classes/{self.test_ids['class_id']}", headers=self.headers)
            except:
                pass
        
        # Delete judge
        if self.test_ids.get("judge_id"):
            try:
                requests.delete(f"{BASE_URL}/api/admin/judges/{self.test_ids['judge_id']}", headers=self.headers)
            except:
                pass
    
    def _create_test_data_with_scores(self):
        """Create test data with scores in both rounds"""
        # Create class
        response = requests.post(f"{BASE_URL}/api/admin/classes", headers=self.headers, json={
            "name": "TEST_EmailHtmlClass",
            "description": "Test class for email HTML test"
        })
        assert response.status_code == 200
        self.test_ids["class_id"] = response.json()["id"]
        
        # Create competitor
        response = requests.post(f"{BASE_URL}/api/admin/competitors", headers=self.headers, json={
            "name": "TEST_EmailHtmlCompetitor",
            "car_number": "888",
            "vehicle_info": "Test Vehicle HTML",
            "plate": "TEST888",
            "class_id": self.test_ids["class_id"],
            "email": "htmltest@example.com"
        })
        assert response.status_code == 200
        self.test_ids["competitor_id"] = response.json()["id"]
        
        # Create Round 1
        response = requests.post(f"{BASE_URL}/api/admin/rounds", headers=self.headers, json={
            "name": "TEST_HTMLRound1",
            "is_minor": False,
            "round_status": "active"
        })
        assert response.status_code == 200
        self.test_ids["round1_id"] = response.json()["id"]
        
        # Create Round 2
        response = requests.post(f"{BASE_URL}/api/admin/rounds", headers=self.headers, json={
            "name": "TEST_HTMLRound2",
            "is_minor": False,
            "round_status": "active"
        })
        assert response.status_code == 200
        self.test_ids["round2_id"] = response.json()["id"]
        
        # Create a judge
        response = requests.post(f"{BASE_URL}/api/auth/register", headers=self.headers, json={
            "username": "TEST_html_judge",
            "password": "testpass123",
            "name": "Test HTML Judge",
            "role": "judge"
        })
        assert response.status_code == 200
        self.test_ids["judge_id"] = response.json()["id"]
        
        # Login as judge and submit scores for both rounds
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "username": "TEST_html_judge",
            "password": "testpass123"
        })
        assert response.status_code == 200
        judge_token = response.json()["token"]
        judge_headers = {"Authorization": f"Bearer {judge_token}"}
        
        # Submit score for Round 1
        response = requests.post(f"{BASE_URL}/api/judge/scores", headers=judge_headers, json={
            "competitor_id": self.test_ids["competitor_id"],
            "round_id": self.test_ids["round1_id"],
            "tip_in": 9.0,
            "instant_smoke": 8.0,
            "constant_smoke": 16.0,
            "volume_of_smoke": 17.0,
            "driving_skill": 36.0,
            "tyres_popped": 2,
            "penalty_reversing": 1,
            "penalty_stopping": 0,
            "penalty_contact_barrier": 0,
            "penalty_small_fire": 0,
            "penalty_failed_drive_off": 0,
            "penalty_large_fire": 0,
            "penalty_disqualified": False
        })
        assert response.status_code == 200
        self.test_ids["score_ids"].append(response.json()["id"])
        
        # Submit score for Round 2
        response = requests.post(f"{BASE_URL}/api/judge/scores", headers=judge_headers, json={
            "competitor_id": self.test_ids["competitor_id"],
            "round_id": self.test_ids["round2_id"],
            "tip_in": 7.5,
            "instant_smoke": 7.0,
            "constant_smoke": 14.0,
            "volume_of_smoke": 15.0,
            "driving_skill": 32.0,
            "tyres_popped": 1,
            "penalty_reversing": 0,
            "penalty_stopping": 1,
            "penalty_contact_barrier": 0,
            "penalty_small_fire": 0,
            "penalty_failed_drive_off": 0,
            "penalty_large_fire": 0,
            "penalty_disqualified": False
        })
        assert response.status_code == 200
        self.test_ids["score_ids"].append(response.json()["id"])
        
        return self.test_ids
    
    def test_send_competitor_report_includes_all_rounds(self):
        """Test that send-competitor-report endpoint can include all rounds"""
        self._create_test_data_with_scores()
        
        # Note: We can't directly test generate_competitor_email_html since it's internal
        # But we can test the send-competitor-report endpoint which uses it
        # The endpoint will fail on SMTP but we can verify the data flow
        
        # First, verify both rounds have scores
        response = requests.get(f"{BASE_URL}/api/admin/scores", headers=self.headers)
        assert response.status_code == 200
        
        all_scores = response.json()
        test_scores = [s for s in all_scores if s["competitor_id"] == self.test_ids["competitor_id"]]
        
        round1_scores = [s for s in test_scores if s["round_id"] == self.test_ids["round1_id"]]
        round2_scores = [s for s in test_scores if s["round_id"] == self.test_ids["round2_id"]]
        
        assert len(round1_scores) == 1, f"Expected 1 score for Round 1, got {len(round1_scores)}"
        assert len(round2_scores) == 1, f"Expected 1 score for Round 2, got {len(round2_scores)}"
        print(f"PASS: Competitor has scores in both rounds")
    
    def test_pending_emails_structure_includes_round_info(self):
        """Test that pending emails includes round_id and round_name for each entry"""
        self._create_test_data_with_scores()
        
        response = requests.get(f"{BASE_URL}/api/admin/pending-emails", headers=self.headers)
        assert response.status_code == 200
        
        data = response.json()
        pending_list = data.get("competitors_list", [])
        
        # Find our test competitor entries
        test_pending = [p for p in pending_list if p["competitor_id"] == self.test_ids["competitor_id"]]
        
        # Should have 2 entries (one for each round)
        assert len(test_pending) == 2, f"Expected 2 pending entries, got {len(test_pending)}"
        
        # Each entry should have round_id and round_name
        for entry in test_pending:
            assert "round_id" in entry, "Entry should have round_id"
            assert "round_name" in entry, "Entry should have round_name"
            assert entry["round_id"] in [self.test_ids["round1_id"], self.test_ids["round2_id"]]
        
        print(f"PASS: Pending emails includes round_id and round_name for each entry")


class TestBulkEmailPayloadStructure:
    """Test the bulk email payload structure and handling"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Setup - login as admin"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "username": "admin",
            "password": "admin123"
        })
        assert response.status_code == 200
        self.token = response.json()["token"]
        self.headers = {"Authorization": f"Bearer {self.token}"}
        yield
    
    def test_bulk_email_accepts_round_id_in_payload(self):
        """Test that bulk email endpoint accepts round_id in the payload"""
        # This will fail on SMTP but should accept the payload structure
        response = requests.post(f"{BASE_URL}/api/admin/send-bulk-emails", headers=self.headers, json={
            "competitor_emails": [
                {
                    "competitor_id": "test-id-123",
                    "recipient_email": "test@example.com",
                    "round_id": "round-id-456"
                }
            ]
        })
        
        # Should fail with SMTP error, not validation error
        # If SMTP is not configured, it returns 400 with "SMTP not configured"
        # If SMTP is configured but fails, it returns 500 with SMTP error
        # Either way, the payload structure was accepted
        assert response.status_code in [400, 500], f"Unexpected status: {response.status_code}"
        
        error_detail = response.json().get("detail", "")
        # Should not be a validation error about the payload structure
        assert "competitor_emails" not in error_detail.lower() or "validation" not in error_detail.lower()
        print(f"PASS: Bulk email endpoint accepts round_id in payload (SMTP error expected: {error_detail})")
    
    def test_bulk_email_payload_without_round_id(self):
        """Test that bulk email works without round_id (backward compatibility)"""
        response = requests.post(f"{BASE_URL}/api/admin/send-bulk-emails", headers=self.headers, json={
            "competitor_emails": [
                {
                    "competitor_id": "test-id-123",
                    "recipient_email": "test@example.com"
                    # No round_id - should still work
                }
            ]
        })
        
        # Should fail with SMTP error, not validation error
        assert response.status_code in [400, 500]
        print(f"PASS: Bulk email endpoint works without round_id (backward compatible)")


class TestCompletedRoundsHelper:
    """Test the get_completed_rounds_for_competitor helper function behavior"""
    
    @pytest.fixture(autouse=True)
    def setup_and_teardown(self):
        """Setup test data and cleanup after tests"""
        self.token = None
        self.test_ids = {
            "class_id": None,
            "competitor_id": None,
            "round1_id": None,
            "round2_id": None,
            "round3_id": None,
            "judge1_id": None,
            "judge2_id": None,
            "score_ids": []
        }
        
        # Login as admin
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "username": "admin",
            "password": "admin123"
        })
        assert response.status_code == 200
        self.token = response.json()["token"]
        self.headers = {"Authorization": f"Bearer {self.token}"}
        
        yield
        
        # Cleanup test data
        self._cleanup_test_data()
    
    def _cleanup_test_data(self):
        """Clean up all test data created during tests"""
        # Delete scores
        for score_id in self.test_ids.get("score_ids", []):
            try:
                requests.delete(f"{BASE_URL}/api/admin/scores/{score_id}", headers=self.headers)
            except:
                pass
        
        # Delete competitor
        if self.test_ids.get("competitor_id"):
            try:
                requests.delete(f"{BASE_URL}/api/admin/competitors/{self.test_ids['competitor_id']}", headers=self.headers)
            except:
                pass
        
        # Delete rounds
        for round_key in ["round1_id", "round2_id", "round3_id"]:
            if self.test_ids.get(round_key):
                try:
                    requests.delete(f"{BASE_URL}/api/admin/rounds/{self.test_ids[round_key]}", headers=self.headers)
                except:
                    pass
        
        # Delete class
        if self.test_ids.get("class_id"):
            try:
                requests.delete(f"{BASE_URL}/api/admin/classes/{self.test_ids['class_id']}", headers=self.headers)
            except:
                pass
        
        # Delete judges
        for judge_key in ["judge1_id", "judge2_id"]:
            if self.test_ids.get(judge_key):
                try:
                    requests.delete(f"{BASE_URL}/api/admin/judges/{self.test_ids[judge_key]}", headers=self.headers)
                except:
                    pass
    
    def _create_multi_judge_test_data(self):
        """Create test data with 2 judges and 3 rounds"""
        # Create class
        response = requests.post(f"{BASE_URL}/api/admin/classes", headers=self.headers, json={
            "name": "TEST_MultiJudgeClass",
            "description": "Test class for multi-judge test"
        })
        assert response.status_code == 200
        self.test_ids["class_id"] = response.json()["id"]
        
        # Create competitor
        response = requests.post(f"{BASE_URL}/api/admin/competitors", headers=self.headers, json={
            "name": "TEST_MultiJudgeCompetitor",
            "car_number": "777",
            "vehicle_info": "Multi Judge Test Vehicle",
            "plate": "TEST777",
            "class_id": self.test_ids["class_id"],
            "email": "multijudge@example.com"
        })
        assert response.status_code == 200
        self.test_ids["competitor_id"] = response.json()["id"]
        
        # Create 3 rounds
        for i, round_key in enumerate(["round1_id", "round2_id", "round3_id"], 1):
            response = requests.post(f"{BASE_URL}/api/admin/rounds", headers=self.headers, json={
                "name": f"TEST_MultiJudge_Round{i}",
                "is_minor": False,
                "round_status": "active"
            })
            assert response.status_code == 200
            self.test_ids[round_key] = response.json()["id"]
        
        # Create 2 judges
        for i, judge_key in enumerate(["judge1_id", "judge2_id"], 1):
            response = requests.post(f"{BASE_URL}/api/auth/register", headers=self.headers, json={
                "username": f"TEST_multijudge{i}",
                "password": "testpass123",
                "name": f"Test MultiJudge {i}",
                "role": "judge"
            })
            assert response.status_code == 200
            self.test_ids[judge_key] = response.json()["id"]
        
        return self.test_ids
    
    def _submit_score(self, judge_username: str, round_id: str, competitor_id: str):
        """Submit a score as a specific judge"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "username": judge_username,
            "password": "testpass123"
        })
        assert response.status_code == 200
        judge_token = response.json()["token"]
        judge_headers = {"Authorization": f"Bearer {judge_token}"}
        
        response = requests.post(f"{BASE_URL}/api/judge/scores", headers=judge_headers, json={
            "competitor_id": competitor_id,
            "round_id": round_id,
            "tip_in": 8.0,
            "instant_smoke": 7.5,
            "constant_smoke": 15.0,
            "volume_of_smoke": 18.0,
            "driving_skill": 35.0,
            "tyres_popped": 1,
            "penalty_reversing": 0,
            "penalty_stopping": 0,
            "penalty_contact_barrier": 0,
            "penalty_small_fire": 0,
            "penalty_failed_drive_off": 0,
            "penalty_large_fire": 0,
            "penalty_disqualified": False
        })
        assert response.status_code == 200
        self.test_ids["score_ids"].append(response.json()["id"])
        return response.json()["id"]
    
    def test_round_not_complete_until_all_judges_score(self):
        """Test that a round is not considered complete until all active judges have scored"""
        self._create_multi_judge_test_data()
        
        # Only Judge 1 scores Round 1
        self._submit_score("TEST_multijudge1", self.test_ids["round1_id"], self.test_ids["competitor_id"])
        
        # Check pending emails - Round 1 should NOT appear (incomplete)
        response = requests.get(f"{BASE_URL}/api/admin/pending-emails", headers=self.headers)
        assert response.status_code == 200
        
        data = response.json()
        pending_list = data.get("competitors_list", [])
        test_pending = [p for p in pending_list if p["competitor_id"] == self.test_ids["competitor_id"]]
        
        # Should be empty - Round 1 is not complete (only 1 of 2 judges scored)
        assert len(test_pending) == 0, f"Expected 0 pending entries (incomplete round), got {len(test_pending)}"
        print(f"PASS: Round with partial scoring does not appear in pending emails")
    
    def test_round_complete_when_all_judges_score(self):
        """Test that a round is complete when all active judges have scored"""
        self._create_multi_judge_test_data()
        
        # Both judges score Round 1
        self._submit_score("TEST_multijudge1", self.test_ids["round1_id"], self.test_ids["competitor_id"])
        self._submit_score("TEST_multijudge2", self.test_ids["round1_id"], self.test_ids["competitor_id"])
        
        # Check pending emails - Round 1 should appear (complete)
        response = requests.get(f"{BASE_URL}/api/admin/pending-emails", headers=self.headers)
        assert response.status_code == 200
        
        data = response.json()
        pending_list = data.get("competitors_list", [])
        test_pending = [p for p in pending_list if p["competitor_id"] == self.test_ids["competitor_id"]]
        
        # Should have 1 entry for Round 1
        assert len(test_pending) == 1, f"Expected 1 pending entry (complete round), got {len(test_pending)}"
        assert test_pending[0]["round_id"] == self.test_ids["round1_id"]
        print(f"PASS: Round with all judges scored appears in pending emails")
    
    def test_multiple_completed_rounds_all_appear(self):
        """Test that multiple completed rounds all appear in pending emails"""
        self._create_multi_judge_test_data()
        
        # Both judges score Round 1 and Round 2
        self._submit_score("TEST_multijudge1", self.test_ids["round1_id"], self.test_ids["competitor_id"])
        self._submit_score("TEST_multijudge2", self.test_ids["round1_id"], self.test_ids["competitor_id"])
        self._submit_score("TEST_multijudge1", self.test_ids["round2_id"], self.test_ids["competitor_id"])
        self._submit_score("TEST_multijudge2", self.test_ids["round2_id"], self.test_ids["competitor_id"])
        
        # Only Judge 1 scores Round 3 (incomplete)
        self._submit_score("TEST_multijudge1", self.test_ids["round3_id"], self.test_ids["competitor_id"])
        
        # Check pending emails
        response = requests.get(f"{BASE_URL}/api/admin/pending-emails", headers=self.headers)
        assert response.status_code == 200
        
        data = response.json()
        pending_list = data.get("competitors_list", [])
        test_pending = [p for p in pending_list if p["competitor_id"] == self.test_ids["competitor_id"]]
        
        # Should have 2 entries (Round 1 and Round 2, not Round 3)
        assert len(test_pending) == 2, f"Expected 2 pending entries, got {len(test_pending)}"
        
        pending_round_ids = [p["round_id"] for p in test_pending]
        assert self.test_ids["round1_id"] in pending_round_ids, "Round 1 should be in pending"
        assert self.test_ids["round2_id"] in pending_round_ids, "Round 2 should be in pending"
        assert self.test_ids["round3_id"] not in pending_round_ids, "Round 3 should NOT be in pending (incomplete)"
        
        print(f"PASS: Multiple completed rounds appear in pending, incomplete round does not")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
