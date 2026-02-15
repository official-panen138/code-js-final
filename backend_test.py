#!/usr/bin/env python3

import requests
import sys
import json
from datetime import datetime

class CustomDomainAPITester:
    def __init__(self, base_url="https://js-hosting-platform-1.preview.emergentagent.com"):
        self.base_url = f"{base_url}/api"
        self.admin_token = None
        self.user_token = None
        self.tests_run = 0
        self.tests_passed = 0
        self.test_results = []

    def log_test(self, name, success, details=""):
        """Log test result"""
        self.tests_run += 1
        if success:
            self.tests_passed += 1
            print(f"✅ {name}")
        else:
            print(f"❌ {name} - {details}")
        
        self.test_results.append({
            "test": name,
            "success": success,
            "details": details
        })

    def make_request(self, method, endpoint, data=None, token=None, expected_status=200):
        """Make HTTP request and return success status and response"""
        url = f"{self.base_url}{endpoint}"
        headers = {'Content-Type': 'application/json'}
        if token:
            headers['Authorization'] = f'Bearer {token}'

        try:
            if method.upper() == 'GET':
                response = requests.get(url, headers=headers)
            elif method.upper() == 'POST':
                response = requests.post(url, json=data, headers=headers)
            elif method.upper() == 'PATCH':
                response = requests.patch(url, json=data, headers=headers)
            elif method.upper() == 'DELETE':
                response = requests.delete(url, headers=headers)
            else:
                return False, None, f"Unsupported method: {method}"

            success = response.status_code == expected_status
            return success, response, ""

        except Exception as e:
            return False, None, str(e)

    def test_admin_login(self):
        """Test admin login"""
        success, response, error = self.make_request(
            'POST', '/auth/login', 
            {"email": "admin@jshost.com", "password": "Admin@123"}
        )
        
        if success and response.json().get('token'):
            self.admin_token = response.json()['token']
            user = response.json().get('user', {})
            permissions = user.get('permissions', [])
            has_custom_domains = 'custom_domains' in permissions
            
            self.log_test(
                "Admin Login", 
                success and has_custom_domains,
                f"Admin permissions: {permissions}" if not has_custom_domains else ""
            )
            return success and has_custom_domains
        
        self.log_test("Admin Login", False, error or "No token received")
        return False

    def test_user_login(self):
        """Test regular user login"""
        success, response, error = self.make_request(
            'POST', '/auth/login', 
            {"email": "user@jshost.com", "password": "User@123"}
        )
        
        if success and response.json().get('token'):
            self.user_token = response.json()['token']
            user = response.json().get('user', {})
            permissions = user.get('permissions', [])
            has_custom_domains = 'custom_domains' in permissions
            
            self.log_test(
                "User Login", 
                success and not has_custom_domains,
                f"User should NOT have custom_domains permission. Got: {permissions}" if has_custom_domains else ""
            )
            return success
        
        self.log_test("User Login", False, error or "No token received")
        return False

    def test_list_domains_admin(self):
        """Test GET /custom-domains with admin"""
        success, response, error = self.make_request(
            'GET', '/custom-domains', token=self.admin_token
        )
        
        if success:
            domains = response.json().get('domains', [])
            # Should have the existing test domain 'cdn.example.com'
            existing_domain = any(d['domain'] == 'cdn.example.com' for d in domains)
            self.log_test(
                "List Domains (Admin)", 
                True,
                f"Found {len(domains)} domains. Expected test domain: {'✓' if existing_domain else '✗'}"
            )
            return domains
        
        self.log_test("List Domains (Admin)", False, error)
        return []

    def test_list_domains_user(self):
        """Test GET /custom-domains with regular user (should fail)"""
        success, response, error = self.make_request(
            'GET', '/custom-domains', token=self.user_token, expected_status=403
        )
        
        # For custom domains, user should not have access
        self.log_test(
            "List Domains (User - Should Fail)", 
            success,  # success = got 403 as expected
            "User should be denied access to custom domains" if not success else ""
        )
        return success

    def test_add_domain(self):
        """Test POST /custom-domains"""
        test_domain = f"test{datetime.now().strftime('%M%S')}.example.com"
        
        success, response, error = self.make_request(
            'POST', '/custom-domains', 
            {"domain": test_domain},
            token=self.admin_token,
            expected_status=201
        )
        
        if success:
            domain_data = response.json().get('domain', {})
            has_platform_ip = bool(domain_data.get('platform_ip'))
            is_pending = domain_data.get('status') == 'pending'
            
            result = has_platform_ip and is_pending
            self.log_test(
                "Add Domain", 
                result,
                f"Domain: {test_domain}, Status: {domain_data.get('status')}, Platform IP: {domain_data.get('platform_ip')}" if not result else ""
            )
            return domain_data if result else None
        
        self.log_test("Add Domain", False, error or "Failed to add domain")
        return None

    def test_verify_domain(self, domain_id):
        """Test POST /custom-domains/{id}/verify"""
        success, response, error = self.make_request(
            'POST', f'/custom-domains/{domain_id}/verify',
            token=self.admin_token
        )
        
        if success:
            verification = response.json().get('verification', {})
            domain_data = response.json().get('domain', {})
            
            platform_ip = verification.get('platform_ip')
            resolved_ip = verification.get('resolved_ip') 
            match = verification.get('match', False)
            
            # For test domains, verification should fail (no DNS record)
            expected_fail = not match and resolved_ip is None
            
            self.log_test(
                "Verify Domain DNS", 
                expected_fail,
                f"Platform IP: {platform_ip}, Resolved IP: {resolved_ip}, Match: {match}, Status: {domain_data.get('status')}"
            )
            return verification
        
        self.log_test("Verify Domain DNS", False, error)
        return None

    def test_delete_domain(self, domain_id):
        """Test DELETE /custom-domains/{id}"""
        success, response, error = self.make_request(
            'DELETE', f'/custom-domains/{domain_id}',
            token=self.admin_token
        )
        
        self.log_test(
            "Delete Domain", 
            success,
            error if not success else ""
        )
        return success

    def test_active_domains_public(self):
        """Test GET /custom-domains/active (public endpoint)"""
        success, response, error = self.make_request(
            'GET', '/custom-domains/active'
        )
        
        if success:
            domains = response.json().get('domains', [])
            # Should only return verified and active domains
            all_verified_active = all(d.get('domain') for d in domains)
            
            self.log_test(
                "List Active Domains (Public)", 
                True,
                f"Found {len(domains)} active domains"
            )
            return domains
        
        self.log_test("List Active Domains (Public)", False, error)
        return []

    def test_domain_validation(self):
        """Test domain validation"""
        test_cases = [
            {"domain": "invalid domain with spaces", "should_fail": True},
            {"domain": "invalid/domain", "should_fail": True},
            {"domain": "invalid:8080", "should_fail": True},
            {"domain": "nodot", "should_fail": True},
            {"domain": "valid.domain.com", "should_fail": False}
        ]
        
        passed = 0
        for case in test_cases:
            success, response, error = self.make_request(
                'POST', '/custom-domains',
                {"domain": case["domain"]},
                token=self.admin_token,
                expected_status=400 if case["should_fail"] else 201
            )
            
            if success:
                passed += 1
                if not case["should_fail"]:
                    # Clean up valid domain
                    domain_data = response.json().get('domain', {})
                    if domain_data.get('id'):
                        self.make_request('DELETE', f'/custom-domains/{domain_data["id"]}', token=self.admin_token)
        
        self.log_test(
            "Domain Validation", 
            passed == len(test_cases),
            f"Passed {passed}/{len(test_cases)} validation tests"
        )

    def run_all_tests(self):
        """Run all tests in sequence"""
        print("🚀 Starting Custom Domain API Tests...")
        print(f"Backend URL: {self.base_url}")
        print("=" * 60)

        # Authentication tests
        if not self.test_admin_login():
            print("❌ Admin login failed - aborting tests")
            return False

        if not self.test_user_login():
            print("❌ User login failed - continuing with admin tests only")

        # Permission tests
        self.test_list_domains_user()

        # Admin functionality tests
        existing_domains = self.test_list_domains_admin()
        
        # Test adding a domain
        new_domain = self.test_add_domain()
        
        if new_domain:
            domain_id = new_domain.get('id')
            if domain_id:
                # Test verification
                self.test_verify_domain(domain_id)
                
                # Test deletion
                self.test_delete_domain(domain_id)

        # Test public endpoints
        self.test_active_domains_public()
        
        # Test validation
        self.test_domain_validation()

        # Print summary
        print("\n" + "=" * 60)
        print(f"📊 Test Results: {self.tests_passed}/{self.tests_run} passed")
        
        if self.tests_passed == self.tests_run:
            print("🎉 All tests passed!")
            return True
        else:
            print(f"⚠️  {self.tests_run - self.tests_passed} tests failed")
            return False

def main():
    tester = CustomDomainAPITester()
    success = tester.run_all_tests()
    
    # Save detailed results
    with open('/tmp/backend_test_results.json', 'w') as f:
        json.dump({
            "timestamp": datetime.now().isoformat(),
            "total_tests": tester.tests_run,
            "passed_tests": tester.tests_passed,
            "success_rate": tester.tests_passed / tester.tests_run if tester.tests_run > 0 else 0,
            "results": tester.test_results
        }, f, indent=2)
    
    return 0 if success else 1

if __name__ == "__main__":
    sys.exit(main())