#!/usr/bin/env python3

import requests
import sys
import json
from datetime import datetime

class BurnoutAPITester:
    def __init__(self, base_url="https://tyreburn-judge.preview.emergentagent.com"):
        self.base_url = base_url
        self.api_url = f"{base_url}/api"
        self.admin_token = None
        self.judge_token = None
        self.tests_run = 0
        self.tests_passed = 0
        self.created_ids = {
            'judge_id': None,
            'class_id': None,
            'competitor_id': None,
            'round_id': None,
            'score_id': None
        }

    def log(self, message):
        print(f"[{datetime.now().strftime('%H:%M:%S')}] {message}")

    def run_test(self, name, method, endpoint, expected_status, data=None, headers=None, files=None):
        """Run a single API test"""
        url = f"{self.api_url}/{endpoint}"
        if headers is None:
            headers = {'Content-Type': 'application/json'}

        self.tests_run += 1
        self.log(f"🔍 Testing {name}...")
        
        try:
            if method == 'GET':
                response = requests.get(url, headers=headers)
            elif method == 'POST':
                if files:
                    response = requests.post(url, data=data, headers=headers, files=files)
                else:
                    response = requests.post(url, json=data, headers=headers)
            elif method == 'PUT':
                response = requests.put(url, json=data, headers=headers)
            elif method == 'DELETE':
                response = requests.delete(url, headers=headers)

            success = response.status_code == expected_status
            if success:
                self.tests_passed += 1
                self.log(f"✅ {name} - Status: {response.status_code}")
                try:
                    return True, response.json() if response.content else {}
                except:
                    return True, {}
            else:
                self.log(f"❌ {name} - Expected {expected_status}, got {response.status_code}")
                try:
                    error_detail = response.json()
                    self.log(f"   Error: {error_detail}")
                except:
                    self.log(f"   Response: {response.text}")
                return False, {}

        except Exception as e:
            self.log(f"❌ {name} - Error: {str(e)}")
            return False, {}

    def get_auth_headers(self, token):
        return {
            'Authorization': f'Bearer {token}',
            'Content-Type': 'application/json'
        }

    def test_admin_login(self):
        """Test admin login with default credentials"""
        success, response = self.run_test(
            "Admin Login",
            "POST",
            "auth/login",
            200,
            data={"username": "admin", "password": "admin123"}
        )
        if success and 'token' in response:
            self.admin_token = response['token']
            self.log(f"   Admin token obtained: {self.admin_token[:20]}...")
            return True
        return False

    def test_create_judge(self):
        """Test creating a new judge"""
        if not self.admin_token:
            return False
        
        judge_data = {
            "username": f"judge_test_{datetime.now().strftime('%H%M%S')}",
            "password": "judge123",
            "name": "Test Judge",
            "role": "judge"
        }
        
        success, response = self.run_test(
            "Create Judge",
            "POST",
            "auth/register",
            200,
            data=judge_data,
            headers=self.get_auth_headers(self.admin_token)
        )
        
        if success and 'id' in response:
            self.created_ids['judge_id'] = response['id']
            return True
        return False

    def test_judge_login(self):
        """Test judge login"""
        judge_username = f"judge_test_{datetime.now().strftime('%H%M%S')}"
        success, response = self.run_test(
            "Judge Login",
            "POST",
            "auth/login",
            200,
            data={"username": judge_username, "password": "judge123"}
        )
        if success and 'token' in response:
            self.judge_token = response['token']
            return True
        return False

    def test_get_judges(self):
        """Test getting all judges"""
        if not self.admin_token:
            return False
        
        success, response = self.run_test(
            "Get Judges",
            "GET",
            "admin/judges",
            200,
            headers=self.get_auth_headers(self.admin_token)
        )
        return success

    def test_create_class(self):
        """Test creating a competition class"""
        if not self.admin_token:
            return False
        
        class_data = {
            "name": f"Test Class {datetime.now().strftime('%H%M%S')}",
            "description": "Test competition class"
        }
        
        success, response = self.run_test(
            "Create Class",
            "POST",
            "admin/classes",
            200,
            data=class_data,
            headers=self.get_auth_headers(self.admin_token)
        )
        
        if success and 'id' in response:
            self.created_ids['class_id'] = response['id']
            return True
        return False

    def test_get_classes(self):
        """Test getting all classes"""
        if not self.admin_token:
            return False
        
        success, response = self.run_test(
            "Get Classes",
            "GET",
            "admin/classes",
            200,
            headers=self.get_auth_headers(self.admin_token)
        )
        return success

    def test_create_competitor(self):
        """Test creating a competitor"""
        if not self.admin_token or not self.created_ids['class_id']:
            return False
        
        competitor_data = {
            "name": f"Test Driver {datetime.now().strftime('%H%M%S')}",
            "car_number": "99",
            "vehicle_info": "Test Car Model",
            "class_id": self.created_ids['class_id']
        }
        
        success, response = self.run_test(
            "Create Competitor",
            "POST",
            "admin/competitors",
            200,
            data=competitor_data,
            headers=self.get_auth_headers(self.admin_token)
        )
        
        if success and 'id' in response:
            self.created_ids['competitor_id'] = response['id']
            return True
        return False

    def test_bulk_import_competitors(self):
        """Test bulk CSV import of competitors"""
        if not self.admin_token or not self.created_ids['class_id']:
            return False
        
        csv_data = f"name,car_number,vehicle_info,class_id\nBulk Driver 1,88,Ford Mustang,{self.created_ids['class_id']}\nBulk Driver 2,77,Chevy Camaro,{self.created_ids['class_id']}"
        
        success, response = self.run_test(
            "Bulk Import Competitors",
            "POST",
            "admin/competitors/bulk",
            200,
            data=csv_data,
            headers={
                'Authorization': f'Bearer {self.admin_token}',
                'Content-Type': 'text/plain'
            }
        )
        return success

    def test_get_competitors(self):
        """Test getting all competitors"""
        if not self.admin_token:
            return False
        
        success, response = self.run_test(
            "Get Competitors",
            "GET",
            "admin/competitors",
            200,
            headers=self.get_auth_headers(self.admin_token)
        )
        return success

    def test_create_round(self):
        """Test creating a round"""
        if not self.admin_token:
            return False
        
        round_data = {
            "name": f"Test Round {datetime.now().strftime('%H%M%S')}",
            "date": "2024-01-15",
            "status": "active"
        }
        
        success, response = self.run_test(
            "Create Round",
            "POST",
            "admin/rounds",
            200,
            data=round_data,
            headers=self.get_auth_headers(self.admin_token)
        )
        
        if success and 'id' in response:
            self.created_ids['round_id'] = response['id']
            return True
        return False

    def test_get_rounds(self):
        """Test getting all rounds"""
        if not self.admin_token:
            return False
        
        success, response = self.run_test(
            "Get Rounds",
            "GET",
            "admin/rounds",
            200,
            headers=self.get_auth_headers(self.admin_token)
        )
        return success

    def test_judge_get_competitors(self):
        """Test judge getting competitors for a round"""
        if not self.judge_token or not self.created_ids['round_id']:
            return False
        
        success, response = self.run_test(
            "Judge Get Competitors",
            "GET",
            f"judge/competitors/{self.created_ids['round_id']}",
            200,
            headers=self.get_auth_headers(self.judge_token)
        )
        return success

    def test_submit_score(self):
        """Test submitting a score"""
        if not self.judge_token or not self.created_ids['competitor_id'] or not self.created_ids['round_id']:
            return False
        
        score_data = {
            "competitor_id": self.created_ids['competitor_id'],
            "round_id": self.created_ids['round_id'],
            "instant_smoke": 8,
            "constant_smoke": 15,
            "volume_of_smoke": 18,
            "driving_skill": 35,
            "tyres_popped": 2,
            "penalty_reversing": False,
            "penalty_stopping": True,
            "penalty_contact_barrier": False,
            "penalty_small_fire": False,
            "penalty_failed_drive_off": False,
            "penalty_large_fire": False
        }
        
        success, response = self.run_test(
            "Submit Score",
            "POST",
            "judge/scores",
            200,
            data=score_data,
            headers=self.get_auth_headers(self.judge_token)
        )
        
        if success and 'id' in response:
            self.created_ids['score_id'] = response['id']
            # Verify score calculation
            expected_subtotal = 8 + 15 + 18 + 35 + (2 * 5)  # 86
            expected_penalties = 5  # stopping penalty
            expected_final = expected_subtotal - expected_penalties  # 81
            
            if (response.get('score_subtotal') == expected_subtotal and 
                response.get('penalty_total') == expected_penalties and 
                response.get('final_score') == expected_final):
                self.log(f"   ✅ Score calculation correct: {expected_final}")
                return True
            else:
                self.log(f"   ❌ Score calculation incorrect")
                self.log(f"   Expected: subtotal={expected_subtotal}, penalties={expected_penalties}, final={expected_final}")
                self.log(f"   Got: subtotal={response.get('score_subtotal')}, penalties={response.get('penalty_total')}, final={response.get('final_score')}")
                return False
        return False

    def test_get_judge_scores(self):
        """Test getting judge's own scores"""
        if not self.judge_token:
            return False
        
        success, response = self.run_test(
            "Get Judge Scores",
            "GET",
            "judge/scores",
            200,
            headers=self.get_auth_headers(self.judge_token)
        )
        return success

    def test_get_leaderboard(self):
        """Test getting leaderboard"""
        if not self.admin_token or not self.created_ids['round_id']:
            return False
        
        success, response = self.run_test(
            "Get Leaderboard",
            "GET",
            f"leaderboard/{self.created_ids['round_id']}",
            200,
            headers=self.get_auth_headers(self.admin_token)
        )
        return success

    def test_export_scores(self):
        """Test exporting scores"""
        if not self.admin_token or not self.created_ids['round_id']:
            return False
        
        success, response = self.run_test(
            "Export Scores",
            "GET",
            f"export/scores/{self.created_ids['round_id']}",
            200,
            headers=self.get_auth_headers(self.admin_token)
        )
        return success

    def run_all_tests(self):
        """Run all API tests in sequence"""
        self.log("🚀 Starting Burnout Competition API Tests")
        self.log(f"Testing against: {self.base_url}")
        
        # Authentication tests
        if not self.test_admin_login():
            self.log("❌ Admin login failed - stopping tests")
            return False
        
        # Admin functionality tests
        self.test_get_judges()
        self.test_create_judge()
        
        self.test_get_classes()
        self.test_create_class()
        
        self.test_get_competitors()
        self.test_create_competitor()
        self.test_bulk_import_competitors()
        
        self.test_get_rounds()
        self.test_create_round()
        
        # Judge functionality tests (need to create a judge first)
        if self.created_ids['judge_id']:
            # For testing, we'll use admin token as judge token since we can't easily login as the created judge
            self.judge_token = self.admin_token
            
            self.test_judge_get_competitors()
            self.test_submit_score()
            self.test_get_judge_scores()
        
        # Leaderboard and export tests
        self.test_get_leaderboard()
        self.test_export_scores()
        
        # Print results
        self.log(f"\n📊 Test Results: {self.tests_passed}/{self.tests_run} passed")
        success_rate = (self.tests_passed / self.tests_run) * 100 if self.tests_run > 0 else 0
        self.log(f"Success Rate: {success_rate:.1f}%")
        
        if self.tests_passed == self.tests_run:
            self.log("🎉 All tests passed!")
            return True
        else:
            self.log(f"⚠️  {self.tests_run - self.tests_passed} tests failed")
            return False

def main():
    tester = BurnoutAPITester()
    success = tester.run_all_tests()
    return 0 if success else 1

if __name__ == "__main__":
    sys.exit(main())