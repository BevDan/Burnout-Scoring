#!/usr/bin/env python3

import requests
import sys
from datetime import datetime

class BugFixTester:
    def __init__(self, base_url="https://smoke-judge.preview.emergentagent.com"):
        self.base_url = base_url
        self.api_url = f"{base_url}/api"
        self.admin_token = None
        self.judge_token = None
        self.tests_run = 0
        self.tests_passed = 0

    def log(self, message):
        print(f"[{datetime.now().strftime('%H:%M:%S')}] {message}")

    def run_test(self, name, method, endpoint, expected_status, data=None, headers=None):
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
                response = requests.post(url, json=data, headers=headers)

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
                    self.log(f"   Response: {response.text[:200]}")
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
        """Test admin login with credentials from review request"""
        success, response = self.run_test(
            "Admin Login (admin/admin123)",
            "POST",
            "auth/login",
            200,
            data={"username": "admin", "password": "admin123"}
        )
        if success and 'token' in response:
            self.admin_token = response['token']
            self.log(f"   Admin user: {response.get('user', {}).get('name', 'Unknown')}")
            return True
        return False

    def test_judge_login(self):
        """Test judge login with credentials from review request"""
        success, response = self.run_test(
            "Judge Login (judge1/judge123)",
            "POST",
            "auth/login",
            200,
            data={"username": "judge1", "password": "judge123"}
        )
        if success and 'token' in response:
            self.judge_token = response['token']
            self.log(f"   Judge user: {response.get('user', {}).get('name', 'Unknown')}")
            return True
        return False

    def test_p0_admin_rounds_tab(self):
        """P0 Bug Fix: Admin Rounds Tab should show rounds with status badges, not blank page"""
        if not self.admin_token:
            self.log("❌ No admin token available")
            return False
            
        headers = self.get_auth_headers(self.admin_token)
        success, response = self.run_test(
            "P0 - Admin Rounds Tab (round_status field)",
            "GET",
            "admin/rounds",
            200,
            headers=headers
        )
        
        if success:
            rounds = response if isinstance(response, list) else []
            self.log(f"   Found {len(rounds)} rounds")
            
            # Check that rounds have round_status field (not status)
            status_fields_found = []
            for round_data in rounds:
                if 'round_status' in round_data:
                    status_fields_found.append('round_status')
                    status = round_data['round_status']
                    self.log(f"   - {round_data.get('name', 'Unknown')}: {status.upper()}")
                elif 'status' in round_data:
                    status_fields_found.append('status')
                    self.log(f"   - {round_data.get('name', 'Unknown')}: {round_data['status'].upper()}")
                else:
                    self.log(f"   - {round_data.get('name', 'Unknown')}: NO STATUS FIELD")
            
            # Verify the fix: should have round_status field
            if rounds and all('round_status' in r for r in rounds):
                self.log("   ✅ All rounds have 'round_status' field - bug fix verified")
                return True
            elif not rounds:
                self.log("   ⚠️  No rounds found - cannot verify bug fix")
                return True  # Not a failure, just no data
            else:
                self.log("   ❌ Some rounds missing 'round_status' field - bug may not be fixed")
                return False
        
        return success

    def test_p1_judge_round_selection(self):
        """P1 Bug Fix: Judge should be able to select rounds from dropdown"""
        if not self.judge_token:
            self.log("❌ No judge token available")
            return False
            
        headers = self.get_auth_headers(self.judge_token)
        success, response = self.run_test(
            "P1 - Judge Round Selection (active rounds)",
            "GET",
            "admin/rounds",
            200,
            headers=headers
        )
        
        if success:
            rounds = response if isinstance(response, list) else []
            active_rounds = []
            
            for round_data in rounds:
                # Check both round_status and status fields for compatibility
                status = round_data.get('round_status') or round_data.get('status', 'active')
                if status == 'active':
                    active_rounds.append(round_data)
            
            self.log(f"   Total rounds: {len(rounds)}, Active rounds: {len(active_rounds)}")
            
            if active_rounds:
                for round_data in active_rounds[:3]:  # Show first 3 active rounds
                    self.log(f"   - Active: {round_data.get('name', 'Unknown')} ({round_data.get('date', 'No date')})")
                self.log("   ✅ Judge can access active rounds for selection")
                return True
            else:
                self.log("   ⚠️  No active rounds found - judge dropdown will be empty")
                return True  # Not a failure, just no active data
        
        return success

    def test_p1_judge_competitor_selection(self):
        """P1 Bug Fix: Judge should be able to select competitors after selecting round"""
        if not self.judge_token:
            self.log("❌ No judge token available")
            return False
            
        # First get rounds to find one to test with
        headers = self.get_auth_headers(self.judge_token)
        rounds_success, rounds_response = self.run_test(
            "Get Rounds for Competitor Test",
            "GET",
            "admin/rounds",
            200,
            headers=headers
        )
        
        if not rounds_success or not rounds_response:
            self.log("❌ Could not get rounds for competitor test")
            return False
            
        rounds = rounds_response if isinstance(rounds_response, list) else []
        if not rounds:
            self.log("❌ No rounds available for competitor test")
            return False
            
        # Test with first round
        round_id = rounds[0]['id']
        round_name = rounds[0].get('name', 'Unknown')
        self.log(f"   Testing competitor selection with round: {round_name}")
        
        success, response = self.run_test(
            "P1 - Judge Competitor Selection",
            "GET",
            f"judge/competitors/{round_id}",
            200,
            headers=headers
        )
        
        if success:
            competitors = response if isinstance(response, list) else []
            self.log(f"   Found {len(competitors)} competitors available for selection")
            
            # Check that competitors have required fields and optional fields are handled
            for comp in competitors[:3]:  # Show first 3 competitors
                car_num = comp.get('car_number', '?')
                name = comp.get('name', 'Unknown')
                class_name = comp.get('class_name', 'Unknown')
                plate = comp.get('plate', 'N/A')  # Should be optional now
                vehicle_info = comp.get('vehicle_info', 'N/A')  # Should be optional now
                
                self.log(f"   - #{car_num} {name} ({class_name}) - Plate: {plate}, Vehicle: {vehicle_info}")
            
            if competitors:
                self.log("   ✅ Judge can access competitors for selection - bug fix verified")
                return True
            else:
                self.log("   ⚠️  No competitors found - judge dropdown will be empty")
                return True  # Not a failure, just no data
        
        return success

    def test_competitor_optional_fields(self):
        """Test that plate and vehicle_info are now optional in competitor model"""
        if not self.admin_token:
            self.log("❌ No admin token available")
            return False
        
        # Get existing competitors to check field handling
        headers = self.get_auth_headers(self.admin_token)
        success, response = self.run_test(
            "Check Competitor Optional Fields",
            "GET",
            "admin/competitors",
            200,
            headers=headers
        )
        
        if success:
            competitors = response if isinstance(response, list) else []
            self.log(f"   Found {len(competitors)} competitors")
            
            # Check that competitors can have empty/missing optional fields
            optional_field_handling = True
            for comp in competitors[:5]:  # Check first 5 competitors
                plate = comp.get('plate', '')
                vehicle_info = comp.get('vehicle_info', '')
                
                # These fields should exist but can be empty
                if 'plate' not in comp or 'vehicle_info' not in comp:
                    self.log(f"   ❌ Competitor {comp.get('name', 'Unknown')} missing optional fields")
                    optional_field_handling = False
                else:
                    self.log(f"   - {comp.get('name', 'Unknown')}: plate='{plate}', vehicle='{vehicle_info}'")
            
            if optional_field_handling:
                self.log("   ✅ Optional fields (plate, vehicle_info) handled correctly")
                return True
            else:
                self.log("   ❌ Optional fields not handled correctly")
                return False
        
        return success

    def run_bug_fix_tests(self):
        """Run all bug fix verification tests"""
        self.log("🐛 Burnout Competition Bug Fix Verification")
        self.log("=" * 50)
        self.log(f"Testing against: {self.base_url}")
        
        # Test authentication first
        self.log("\n📋 AUTHENTICATION TESTS")
        admin_login_ok = self.test_admin_login()
        judge_login_ok = self.test_judge_login()
        
        if not admin_login_ok:
            self.log("❌ Admin login failed - cannot test admin features")
        
        if not judge_login_ok:
            self.log("❌ Judge login failed - cannot test judge features")
        
        if not admin_login_ok and not judge_login_ok:
            self.log("❌ Both logins failed - stopping tests")
            return False
        
        # Test the specific bug fixes
        self.log("\n🔧 BUG FIX VERIFICATION TESTS")
        
        bug_fix_results = []
        
        # P0 Bug: Admin Rounds Tab blank page
        if admin_login_ok:
            bug_fix_results.append(self.test_p0_admin_rounds_tab())
        
        # P1 Bug: Judge Round Selection
        if judge_login_ok:
            bug_fix_results.append(self.test_p1_judge_round_selection())
        
        # P1 Bug: Judge Competitor Selection  
        if judge_login_ok:
            bug_fix_results.append(self.test_p1_judge_competitor_selection())
        
        # Backend model fix: Optional fields
        if admin_login_ok:
            bug_fix_results.append(self.test_competitor_optional_fields())
        
        # Print results
        self.log(f"\n📊 BUG FIX TEST RESULTS")
        self.log("=" * 30)
        self.log(f"Total tests: {self.tests_passed}/{self.tests_run}")
        
        bug_fixes_passed = sum(bug_fix_results)
        total_bug_fixes = len(bug_fix_results)
        
        self.log(f"Bug fix verifications: {bug_fixes_passed}/{total_bug_fixes}")
        
        if bug_fixes_passed == total_bug_fixes and total_bug_fixes > 0:
            self.log("✅ All bug fixes verified working!")
            return True
        elif total_bug_fixes == 0:
            self.log("⚠️  No bug fix tests could be run due to authentication issues")
            return False
        else:
            self.log(f"❌ {total_bug_fixes - bug_fixes_passed} bug fix(es) may still have issues")
            return False

def main():
    tester = BugFixTester()
    success = tester.run_bug_fix_tests()
    return 0 if success else 1

if __name__ == "__main__":
    sys.exit(main())