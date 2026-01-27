"""
Test Score Deviation Validation Feature
- GET /api/admin/settings/score-deviation - returns threshold (default 5)
- PUT /api/admin/settings/score-deviation - updates the threshold
- GET /api/admin/scoring-errors - returns score_deviation errors with score_id, judge_name, deviation_amount
- POST /api/admin/scores/{score_id}/acknowledge-deviation - marks score as acknowledged
- POST /api/admin/scores/{score_id}/unacknowledge-deviation - removes acknowledgment
- Verify acknowledged scores no longer appear in scoring errors
- Verify deviation threshold change affects which scores are flagged
"""

import pytest
import requests
import os
import uuid

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

class TestScoreDeviationFeature:
    """Test score deviation validation feature"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Setup - login and get token"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "username": "admin",
            "password": "admin123"
        })
        assert response.status_code == 200, f"Login failed: {response.text}"
        self.token = response.json()["token"]
        self.headers = {"Authorization": f"Bearer {self.token}"}
        yield
        # Cleanup - reset threshold to default
        requests.put(f"{BASE_URL}/api/admin/settings/score-deviation?threshold=5", headers=self.headers)
    
    def test_get_score_deviation_settings_returns_threshold(self):
        """Test GET /api/admin/settings/score-deviation returns threshold"""
        response = requests.get(f"{BASE_URL}/api/admin/settings/score-deviation", headers=self.headers)
        
        assert response.status_code == 200
        data = response.json()
        assert "threshold" in data
        assert isinstance(data["threshold"], (int, float))
        assert data["threshold"] >= 0
        print(f"Current threshold: {data['threshold']}")
    
    def test_update_score_deviation_threshold(self):
        """Test PUT /api/admin/settings/score-deviation updates the threshold"""
        # Update threshold to 15
        response = requests.put(
            f"{BASE_URL}/api/admin/settings/score-deviation?threshold=15",
            headers=self.headers
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["threshold"] == 15
        assert "message" in data
        
        # Verify the change persisted
        get_response = requests.get(f"{BASE_URL}/api/admin/settings/score-deviation", headers=self.headers)
        assert get_response.status_code == 200
        assert get_response.json()["threshold"] == 15
        print("Threshold updated to 15 and verified")
    
    def test_update_threshold_rejects_negative(self):
        """Test PUT /api/admin/settings/score-deviation rejects negative threshold"""
        response = requests.put(
            f"{BASE_URL}/api/admin/settings/score-deviation?threshold=-5",
            headers=self.headers
        )
        
        assert response.status_code == 400
        print("Negative threshold correctly rejected")
    
    def test_scoring_errors_returns_deviation_errors(self):
        """Test GET /api/admin/scoring-errors returns score_deviation errors with required fields"""
        response = requests.get(f"{BASE_URL}/api/admin/scoring-errors", headers=self.headers)
        
        assert response.status_code == 200
        errors = response.json()
        assert isinstance(errors, list)
        
        # Check for score_deviation errors
        deviation_errors = [e for e in errors if e.get("error_type") == "score_deviation"]
        
        if deviation_errors:
            for error in deviation_errors:
                # Verify required fields for score_deviation errors
                assert "score_id" in error, "score_deviation error missing score_id"
                assert "judge_name" in error, "score_deviation error missing judge_name"
                assert "deviation_amount" in error, "score_deviation error missing deviation_amount"
                assert error["score_id"] is not None, "score_id should not be None for deviation errors"
                assert error["judge_name"] is not None, "judge_name should not be None for deviation errors"
                assert error["deviation_amount"] is not None, "deviation_amount should not be None for deviation errors"
                assert isinstance(error["deviation_amount"], (int, float))
                print(f"Found deviation error: {error['judge_name']} - {error['deviation_amount']} pts")
        else:
            print("No score_deviation errors found (may need test data with deviations)")
    
    def test_acknowledge_deviation_removes_from_errors(self):
        """Test POST /api/admin/scores/{score_id}/acknowledge-deviation marks score as acknowledged"""
        # First get scoring errors to find a deviation error
        errors_response = requests.get(f"{BASE_URL}/api/admin/scoring-errors", headers=self.headers)
        assert errors_response.status_code == 200
        errors = errors_response.json()
        
        deviation_errors = [e for e in errors if e.get("error_type") == "score_deviation" and e.get("score_id")]
        
        if not deviation_errors:
            pytest.skip("No score_deviation errors with score_id found to test acknowledgment")
        
        # Acknowledge the first deviation error
        score_id = deviation_errors[0]["score_id"]
        judge_name = deviation_errors[0]["judge_name"]
        
        ack_response = requests.post(
            f"{BASE_URL}/api/admin/scores/{score_id}/acknowledge-deviation",
            headers=self.headers
        )
        
        assert ack_response.status_code == 200
        assert "message" in ack_response.json()
        print(f"Acknowledged deviation for score {score_id} ({judge_name})")
        
        # Verify the acknowledged score no longer appears in errors
        errors_after = requests.get(f"{BASE_URL}/api/admin/scoring-errors", headers=self.headers)
        assert errors_after.status_code == 200
        
        remaining_deviation_errors = [
            e for e in errors_after.json() 
            if e.get("error_type") == "score_deviation" and e.get("score_id") == score_id
        ]
        
        assert len(remaining_deviation_errors) == 0, "Acknowledged score should not appear in errors"
        print(f"Verified: Acknowledged score {score_id} no longer in errors")
        
        # Cleanup - unacknowledge the score
        requests.post(f"{BASE_URL}/api/admin/scores/{score_id}/unacknowledge-deviation", headers=self.headers)
    
    def test_unacknowledge_deviation_restores_to_errors(self):
        """Test POST /api/admin/scores/{score_id}/unacknowledge-deviation removes acknowledgment"""
        # First get scoring errors to find a deviation error
        errors_response = requests.get(f"{BASE_URL}/api/admin/scoring-errors", headers=self.headers)
        assert errors_response.status_code == 200
        errors = errors_response.json()
        
        deviation_errors = [e for e in errors if e.get("error_type") == "score_deviation" and e.get("score_id")]
        
        if not deviation_errors:
            pytest.skip("No score_deviation errors with score_id found to test")
        
        score_id = deviation_errors[0]["score_id"]
        
        # Acknowledge first
        requests.post(f"{BASE_URL}/api/admin/scores/{score_id}/acknowledge-deviation", headers=self.headers)
        
        # Then unacknowledge
        unack_response = requests.post(
            f"{BASE_URL}/api/admin/scores/{score_id}/unacknowledge-deviation",
            headers=self.headers
        )
        
        assert unack_response.status_code == 200
        assert "message" in unack_response.json()
        
        # Verify the score reappears in errors
        errors_after = requests.get(f"{BASE_URL}/api/admin/scoring-errors", headers=self.headers)
        assert errors_after.status_code == 200
        
        restored_errors = [
            e for e in errors_after.json() 
            if e.get("error_type") == "score_deviation" and e.get("score_id") == score_id
        ]
        
        assert len(restored_errors) == 1, "Unacknowledged score should reappear in errors"
        print(f"Verified: Unacknowledged score {score_id} restored to errors")
    
    def test_threshold_change_affects_flagged_scores(self):
        """Test that changing threshold affects which scores are flagged"""
        # Get current errors with default threshold
        errors_before = requests.get(f"{BASE_URL}/api/admin/scoring-errors", headers=self.headers)
        assert errors_before.status_code == 200
        deviation_count_before = len([e for e in errors_before.json() if e.get("error_type") == "score_deviation"])
        
        # Set a very high threshold (should reduce or eliminate deviation errors)
        requests.put(f"{BASE_URL}/api/admin/settings/score-deviation?threshold=100", headers=self.headers)
        
        errors_after_high = requests.get(f"{BASE_URL}/api/admin/scoring-errors", headers=self.headers)
        assert errors_after_high.status_code == 200
        deviation_count_high = len([e for e in errors_after_high.json() if e.get("error_type") == "score_deviation"])
        
        # With threshold=100, there should be fewer or no deviation errors
        assert deviation_count_high <= deviation_count_before, "Higher threshold should reduce deviation errors"
        print(f"Deviation errors: {deviation_count_before} (threshold=5) -> {deviation_count_high} (threshold=100)")
        
        # Set a very low threshold (should increase deviation errors)
        requests.put(f"{BASE_URL}/api/admin/settings/score-deviation?threshold=1", headers=self.headers)
        
        errors_after_low = requests.get(f"{BASE_URL}/api/admin/scoring-errors", headers=self.headers)
        assert errors_after_low.status_code == 200
        deviation_count_low = len([e for e in errors_after_low.json() if e.get("error_type") == "score_deviation"])
        
        # With threshold=1, there should be more deviation errors than with threshold=100
        assert deviation_count_low >= deviation_count_high, "Lower threshold should increase deviation errors"
        print(f"Deviation errors: {deviation_count_high} (threshold=100) -> {deviation_count_low} (threshold=1)")
        
        # Reset to default
        requests.put(f"{BASE_URL}/api/admin/settings/score-deviation?threshold=5", headers=self.headers)
    
    def test_acknowledge_nonexistent_score_returns_404(self):
        """Test acknowledging a non-existent score returns 404"""
        fake_score_id = str(uuid.uuid4())
        
        response = requests.post(
            f"{BASE_URL}/api/admin/scores/{fake_score_id}/acknowledge-deviation",
            headers=self.headers
        )
        
        assert response.status_code == 404
        print(f"Correctly returned 404 for non-existent score {fake_score_id}")
    
    def test_scoring_errors_structure(self):
        """Test that scoring errors have correct structure for all error types"""
        response = requests.get(f"{BASE_URL}/api/admin/scoring-errors", headers=self.headers)
        
        assert response.status_code == 200
        errors = response.json()
        
        for error in errors:
            # All errors should have these base fields
            assert "round_id" in error
            assert "round_name" in error
            assert "competitor_id" in error
            assert "competitor_name" in error
            assert "car_number" in error
            assert "error_type" in error
            assert "details" in error
            assert "judge_count" in error
            assert "expected_count" in error
            
            # score_deviation specific fields
            if error["error_type"] == "score_deviation":
                assert error.get("score_id") is not None
                assert error.get("judge_name") is not None
                assert error.get("deviation_amount") is not None
        
        print(f"Verified structure of {len(errors)} scoring errors")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
