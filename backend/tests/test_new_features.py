"""
Test suite for new Burnout Competition features:
1. Disqualified penalty (zeros score)
2. Email tracking (email_sent field, pending emails count)
3. Admin edit scores
"""
import pytest
import requests
import os

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

class TestAuth:
    """Authentication tests"""
    
    @pytest.fixture(scope="class")
    def admin_token(self):
        """Get admin authentication token"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "username": "admin",
            "password": "admin123"
        })
        assert response.status_code == 200, f"Admin login failed: {response.text}"
        return response.json()["token"]
    
    @pytest.fixture(scope="class")
    def auth_headers(self, admin_token):
        """Get auth headers for admin"""
        return {"Authorization": f"Bearer {admin_token}"}


class TestDisqualifiedPenalty(TestAuth):
    """Test disqualified penalty feature - zeros score"""
    
    def test_score_model_has_penalty_disqualified_field(self, auth_headers):
        """Verify new scores have penalty_disqualified field - older scores may not have it"""
        # Submit a new score to verify the field is present
        rounds_response = requests.get(f"{BASE_URL}/api/admin/rounds", headers=auth_headers)
        competitors_response = requests.get(f"{BASE_URL}/api/admin/competitors", headers=auth_headers)
        
        rounds = rounds_response.json()
        competitors = competitors_response.json()
        
        if len(rounds) == 0 or len(competitors) == 0:
            pytest.skip("No rounds or competitors available")
        
        # Submit a test score
        score_data = {
            "competitor_id": competitors[0]["id"],
            "round_id": rounds[0]["id"],
            "tip_in": 5,
            "instant_smoke": 5,
            "constant_smoke": 10,
            "volume_of_smoke": 10,
            "driving_skill": 20,
            "tyres_popped": 0,
            "penalty_reversing": 0,
            "penalty_stopping": 0,
            "penalty_contact_barrier": 0,
            "penalty_small_fire": 0,
            "penalty_failed_drive_off": 0,
            "penalty_large_fire": 0,
            "penalty_disqualified": False
        }
        
        response = requests.post(f"{BASE_URL}/api/judge/scores", json=score_data, headers=auth_headers)
        assert response.status_code == 200
        
        score = response.json()
        assert "penalty_disqualified" in score
        assert score["penalty_disqualified"] == False
        print(f"✓ New scores have penalty_disqualified field")
        
        # Clean up
        requests.delete(f"{BASE_URL}/api/admin/scores/{score['id']}", headers=auth_headers)
    
    def test_submit_score_with_disqualified_zeros_final_score(self, auth_headers):
        """Test that submitting a score with penalty_disqualified=true results in final_score=0"""
        # First get a round and competitor
        rounds_response = requests.get(f"{BASE_URL}/api/admin/rounds", headers=auth_headers)
        assert rounds_response.status_code == 200
        rounds = rounds_response.json()
        
        competitors_response = requests.get(f"{BASE_URL}/api/admin/competitors", headers=auth_headers)
        assert competitors_response.status_code == 200
        competitors = competitors_response.json()
        
        if len(rounds) == 0 or len(competitors) == 0:
            pytest.skip("No rounds or competitors available for testing")
        
        # Submit a score with disqualified=true
        score_data = {
            "competitor_id": competitors[0]["id"],
            "round_id": rounds[0]["id"],
            "tip_in": 5,
            "instant_smoke": 8,
            "constant_smoke": 15,
            "volume_of_smoke": 18,
            "driving_skill": 35,
            "tyres_popped": 1,
            "penalty_reversing": 0,
            "penalty_stopping": 0,
            "penalty_contact_barrier": 0,
            "penalty_small_fire": 0,
            "penalty_failed_drive_off": 0,
            "penalty_large_fire": 0,
            "penalty_disqualified": True
        }
        
        response = requests.post(f"{BASE_URL}/api/judge/scores", json=score_data, headers=auth_headers)
        assert response.status_code == 200, f"Failed to submit score: {response.text}"
        
        score = response.json()
        assert score["final_score"] == 0, f"Expected final_score=0 for disqualified, got {score['final_score']}"
        assert score["penalty_disqualified"] == True
        print(f"✓ Disqualified score has final_score=0")
        
        # Clean up - delete the test score
        requests.delete(f"{BASE_URL}/api/admin/scores/{score['id']}", headers=auth_headers)
    
    def test_admin_edit_score_with_disqualified(self, auth_headers):
        """Test admin can edit a score to set disqualified and it zeros the score"""
        # Get existing scores
        response = requests.get(f"{BASE_URL}/api/admin/scores", headers=auth_headers)
        assert response.status_code == 200
        scores = response.json()
        
        if len(scores) == 0:
            pytest.skip("No scores available for testing")
        
        # Find a score that is not disqualified
        test_score = None
        for score in scores:
            if not score.get("penalty_disqualified", False):
                test_score = score
                break
        
        if not test_score:
            pytest.skip("No non-disqualified scores available")
        
        original_final_score = test_score["final_score"]
        
        # Edit to set disqualified
        edit_response = requests.put(
            f"{BASE_URL}/api/admin/scores/{test_score['id']}", 
            json={"penalty_disqualified": True},
            headers=auth_headers
        )
        assert edit_response.status_code == 200, f"Failed to edit score: {edit_response.text}"
        
        edited_score = edit_response.json()
        assert edited_score["final_score"] == 0, f"Expected final_score=0 after disqualification, got {edited_score['final_score']}"
        assert edited_score["penalty_disqualified"] == True
        print(f"✓ Admin edit with disqualified zeros the score")
        
        # Revert the change
        requests.put(
            f"{BASE_URL}/api/admin/scores/{test_score['id']}", 
            json={"penalty_disqualified": False},
            headers=auth_headers
        )


class TestEmailTracking(TestAuth):
    """Test email tracking feature"""
    
    def test_score_model_has_email_sent_field(self, auth_headers):
        """Verify scores have email_sent field"""
        response = requests.get(f"{BASE_URL}/api/admin/scores", headers=auth_headers)
        assert response.status_code == 200
        scores = response.json()
        if len(scores) > 0:
            # email_sent should be present (default false)
            assert "email_sent" in scores[0] or scores[0].get("email_sent") is not None
            print(f"✓ Score model has email_sent field")
    
    def test_pending_emails_endpoint_exists(self, auth_headers):
        """Test GET /api/admin/pending-emails endpoint exists and returns correct structure"""
        response = requests.get(f"{BASE_URL}/api/admin/pending-emails", headers=auth_headers)
        assert response.status_code == 200, f"Pending emails endpoint failed: {response.text}"
        
        data = response.json()
        assert "total_competitors_scored" in data
        assert "competitors_pending_email" in data
        assert "competitors_list" in data
        assert isinstance(data["competitors_list"], list)
        print(f"✓ Pending emails endpoint returns correct structure")
        print(f"  - Total scored: {data['total_competitors_scored']}")
        print(f"  - Pending email: {data['competitors_pending_email']}")
    
    def test_pending_emails_requires_auth(self):
        """Test pending emails endpoint requires authentication"""
        response = requests.get(f"{BASE_URL}/api/admin/pending-emails")
        assert response.status_code in [401, 403], "Pending emails should require auth"
        print(f"✓ Pending emails endpoint requires authentication")
    
    def test_pending_emails_list_structure(self, auth_headers):
        """Test pending emails list has correct structure"""
        response = requests.get(f"{BASE_URL}/api/admin/pending-emails", headers=auth_headers)
        assert response.status_code == 200
        
        data = response.json()
        if len(data["competitors_list"]) > 0:
            item = data["competitors_list"][0]
            assert "competitor_id" in item
            assert "competitor_name" in item
            assert "car_number" in item
            assert "round_id" in item
            assert "round_name" in item
            print(f"✓ Pending emails list has correct structure")
    
    def test_mark_emailed_endpoint(self, auth_headers):
        """Test POST /api/admin/mark-emailed/{competitor_id}/{round_id} endpoint"""
        # Get pending emails first
        pending_response = requests.get(f"{BASE_URL}/api/admin/pending-emails", headers=auth_headers)
        assert pending_response.status_code == 200
        
        pending_data = pending_response.json()
        if len(pending_data["competitors_list"]) == 0:
            pytest.skip("No pending emails to test with")
        
        # Mark first one as emailed
        item = pending_data["competitors_list"][0]
        mark_response = requests.post(
            f"{BASE_URL}/api/admin/mark-emailed/{item['competitor_id']}/{item['round_id']}",
            headers=auth_headers
        )
        assert mark_response.status_code == 200, f"Mark emailed failed: {mark_response.text}"
        
        result = mark_response.json()
        assert "message" in result
        print(f"✓ Mark emailed endpoint works: {result['message']}")


class TestAdminEditScore(TestAuth):
    """Test admin edit score feature"""
    
    def test_admin_edit_score_endpoint_exists(self, auth_headers):
        """Test PUT /api/admin/scores/{id} endpoint exists"""
        # Get a score to edit
        response = requests.get(f"{BASE_URL}/api/admin/scores", headers=auth_headers)
        assert response.status_code == 200
        scores = response.json()
        
        if len(scores) == 0:
            pytest.skip("No scores available for testing")
        
        test_score = scores[0]
        
        # Try to edit with same values (no change)
        edit_response = requests.put(
            f"{BASE_URL}/api/admin/scores/{test_score['id']}", 
            json={"tip_in": test_score.get("tip_in", 0)},
            headers=auth_headers
        )
        assert edit_response.status_code == 200, f"Admin edit score endpoint failed: {edit_response.text}"
        print(f"✓ Admin edit score endpoint exists and works")
    
    def test_admin_edit_score_recalculates_totals(self, auth_headers):
        """Test that editing a score recalculates subtotal, penalty_total, and final_score"""
        # Get a score to edit
        response = requests.get(f"{BASE_URL}/api/admin/scores", headers=auth_headers)
        assert response.status_code == 200
        scores = response.json()
        
        if len(scores) == 0:
            pytest.skip("No scores available for testing")
        
        # Find a non-disqualified score
        test_score = None
        for score in scores:
            if not score.get("penalty_disqualified", False):
                test_score = score
                break
        
        if not test_score:
            pytest.skip("No non-disqualified scores available")
        
        original_tip_in = test_score.get("tip_in", 0)
        
        # Edit tip_in to a different value
        new_tip_in = 5 if original_tip_in != 5 else 3
        edit_response = requests.put(
            f"{BASE_URL}/api/admin/scores/{test_score['id']}", 
            json={"tip_in": new_tip_in},
            headers=auth_headers
        )
        assert edit_response.status_code == 200
        
        edited_score = edit_response.json()
        
        # Verify score_subtotal was recalculated
        expected_subtotal = (
            new_tip_in +
            edited_score.get("instant_smoke", 0) +
            edited_score.get("constant_smoke", 0) +
            edited_score.get("volume_of_smoke", 0) +
            edited_score.get("driving_skill", 0) +
            (edited_score.get("tyres_popped", 0) * 5)
        )
        assert edited_score["score_subtotal"] == expected_subtotal, f"Score subtotal not recalculated correctly"
        print(f"✓ Admin edit recalculates score_subtotal correctly")
        
        # Revert the change
        requests.put(
            f"{BASE_URL}/api/admin/scores/{test_score['id']}", 
            json={"tip_in": original_tip_in},
            headers=auth_headers
        )
    
    def test_admin_edit_score_requires_auth(self):
        """Test admin edit score requires authentication"""
        response = requests.put(
            f"{BASE_URL}/api/admin/scores/fake-id", 
            json={"tip_in": 5}
        )
        assert response.status_code in [401, 403], "Admin edit score should require auth"
        print(f"✓ Admin edit score requires authentication")
    
    def test_admin_edit_score_404_for_invalid_id(self, auth_headers):
        """Test admin edit score returns 404 for invalid score ID"""
        response = requests.put(
            f"{BASE_URL}/api/admin/scores/invalid-score-id-12345", 
            json={"tip_in": 5},
            headers=auth_headers
        )
        assert response.status_code == 404, f"Expected 404 for invalid score ID, got {response.status_code}"
        print(f"✓ Admin edit score returns 404 for invalid ID")
    
    def test_admin_edit_score_sets_edited_at(self, auth_headers):
        """Test that editing a score sets the edited_at timestamp"""
        # Get a score to edit
        response = requests.get(f"{BASE_URL}/api/admin/scores", headers=auth_headers)
        assert response.status_code == 200
        scores = response.json()
        
        if len(scores) == 0:
            pytest.skip("No scores available for testing")
        
        test_score = scores[0]
        original_tip_in = test_score.get("tip_in", 0)
        
        # Edit the score
        new_tip_in = original_tip_in + 0.5 if original_tip_in < 10 else original_tip_in - 0.5
        edit_response = requests.put(
            f"{BASE_URL}/api/admin/scores/{test_score['id']}", 
            json={"tip_in": new_tip_in},
            headers=auth_headers
        )
        assert edit_response.status_code == 200
        
        edited_score = edit_response.json()
        assert edited_score.get("edited_at") is not None, "edited_at should be set after edit"
        print(f"✓ Admin edit sets edited_at timestamp")
        
        # Revert
        requests.put(
            f"{BASE_URL}/api/admin/scores/{test_score['id']}", 
            json={"tip_in": original_tip_in},
            headers=auth_headers
        )


class TestScoringErrorsDetection(TestAuth):
    """Test scoring errors detection feature"""
    
    def test_scoring_errors_endpoint_exists(self, auth_headers):
        """Test GET /api/admin/scoring-errors endpoint exists"""
        response = requests.get(f"{BASE_URL}/api/admin/scoring-errors", headers=auth_headers)
        assert response.status_code == 200, f"Scoring errors endpoint failed: {response.text}"
        
        errors = response.json()
        assert isinstance(errors, list)
        print(f"✓ Scoring errors endpoint exists and returns list")
        print(f"  - Found {len(errors)} scoring errors")
    
    def test_scoring_errors_structure(self, auth_headers):
        """Test scoring errors have correct structure"""
        response = requests.get(f"{BASE_URL}/api/admin/scoring-errors", headers=auth_headers)
        assert response.status_code == 200
        
        errors = response.json()
        if len(errors) > 0:
            error = errors[0]
            required_fields = ["round_id", "round_name", "competitor_id", "competitor_name", 
                            "car_number", "error_type", "details", "judge_count", "expected_count"]
            for field in required_fields:
                assert field in error, f"Missing field: {field}"
            print(f"✓ Scoring errors have correct structure")


class TestScoreSubmissionWithAllFields(TestAuth):
    """Test score submission includes all new fields"""
    
    def test_score_submission_accepts_all_fields(self, auth_headers):
        """Test that score submission accepts all fields including penalty_disqualified"""
        # Get round and competitor
        rounds_response = requests.get(f"{BASE_URL}/api/admin/rounds", headers=auth_headers)
        competitors_response = requests.get(f"{BASE_URL}/api/admin/competitors", headers=auth_headers)
        
        rounds = rounds_response.json()
        competitors = competitors_response.json()
        
        if len(rounds) == 0 or len(competitors) == 0:
            pytest.skip("No rounds or competitors available")
        
        # Submit score with all fields
        score_data = {
            "competitor_id": competitors[0]["id"],
            "round_id": rounds[0]["id"],
            "tip_in": 7.5,
            "instant_smoke": 8.5,
            "constant_smoke": 16,
            "volume_of_smoke": 17,
            "driving_skill": 32,
            "tyres_popped": 0,
            "penalty_reversing": 1,
            "penalty_stopping": 0,
            "penalty_contact_barrier": 0,
            "penalty_small_fire": 0,
            "penalty_failed_drive_off": 0,
            "penalty_large_fire": 0,
            "penalty_disqualified": False
        }
        
        response = requests.post(f"{BASE_URL}/api/judge/scores", json=score_data, headers=auth_headers)
        assert response.status_code == 200, f"Score submission failed: {response.text}"
        
        score = response.json()
        
        # Verify all fields are present in response
        assert score["tip_in"] == 7.5
        assert score["instant_smoke"] == 8.5
        assert score["penalty_disqualified"] == False
        assert score["email_sent"] == False  # Default value
        
        # Verify calculations
        expected_subtotal = 7.5 + 8.5 + 16 + 17 + 32 + 0  # tip_in + instant + constant + volume + driving + tyres*5
        assert score["score_subtotal"] == expected_subtotal
        
        expected_penalty = 1 * 5  # 1 reversing penalty
        assert score["penalty_total"] == expected_penalty
        
        expected_final = expected_subtotal - expected_penalty
        assert score["final_score"] == expected_final
        
        print(f"✓ Score submission accepts all fields and calculates correctly")
        print(f"  - Subtotal: {score['score_subtotal']}")
        print(f"  - Penalties: {score['penalty_total']}")
        print(f"  - Final: {score['final_score']}")
        
        # Clean up
        requests.delete(f"{BASE_URL}/api/admin/scores/{score['id']}", headers=auth_headers)


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
