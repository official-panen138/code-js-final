#!/usr/bin/env python3
"""
Backend API Testing for JavaScript Hosting Platform
Tests authentication, CRUD operations, and JS delivery endpoint
"""

import requests
import sys
import json
from datetime import datetime
from typing import Dict, List, Any

class JSHostAPITester:
    def __init__(self, base_url: str):
        self.base_url = base_url.rstrip('/')
        self.api_base = f"{self.base_url}/api"
        self.token = None
        self.user_id = None
        self.tests_run = 0
        self.tests_passed = 0
        self.project_id = None
        self.script_id = None
        self.whitelist_id = None
        
    def log_test(self, test_name: str, success: bool, details: str = ""):
        """Log test result"""
        self.tests_run += 1
        if success:
            self.tests_passed += 1
            print(f"✅ {test_name}")
        else:
            print(f"❌ {test_name} - {details}")
            
    def make_request(self, method: str, endpoint: str, data: Dict = None, expected_status: int = 200) -> tuple:
        """Make HTTP request with authentication"""
        url = f"{self.api_base}{endpoint}"
        headers = {'Content-Type': 'application/json'}
        
        if self.token:
            headers['Authorization'] = f'Bearer {self.token}'
            
        try:
            if method == 'GET':
                response = requests.get(url, headers=headers)
            elif method == 'POST':
                response = requests.post(url, json=data, headers=headers)
            elif method == 'PATCH':
                response = requests.patch(url, json=data, headers=headers)
            elif method == 'DELETE':
                response = requests.delete(url, headers=headers)
            else:
                return False, f"Unsupported method: {method}", None
                
            success = response.status_code == expected_status
            response_data = None
            
            try:
                response_data = response.json()
            except:
                response_data = response.text
                
            return success, response.status_code, response_data
            
        except Exception as e:
            return False, f"Request failed: {str(e)}", None
    
    def test_auth_register(self) -> bool:
        """Test user registration"""
        email = f"test_{datetime.now().strftime('%H%M%S')}@example.com"
        password = "test123456"
        
        success, status, data = self.make_request('POST', '/auth/register', {
            'email': email,
            'password': password
        })
        
        if success and 'token' in data and 'user' in data:
            self.token = data['token']
            self.user_id = data['user']['id']
            self.log_test("Auth Registration", True)
            return True
        else:
            self.log_test("Auth Registration", False, f"Status {status}, Response: {data}")
            return False
    
    def test_auth_login(self) -> bool:
        """Test user login with existing user"""
        success, status, data = self.make_request('POST', '/auth/login', {
            'email': 'test@example.com',
            'password': 'test123456'
        })
        
        if success and 'token' in data and 'user' in data:
            self.token = data['token']
            self.user_id = data['user']['id']
            self.log_test("Auth Login (Existing User)", True)
            return True
        else:
            self.log_test("Auth Login (Existing User)", False, f"Status {status}, Response: {data}")
            return False
    
    def test_auth_me(self) -> bool:
        """Test getting current user info"""
        success, status, data = self.make_request('GET', '/auth/me')
        
        if success and 'user' in data:
            self.log_test("Auth Me", True)
            return True
        else:
            self.log_test("Auth Me", False, f"Status {status}, Response: {data}")
            return False
    
    def test_categories_list(self) -> bool:
        """Test listing categories"""
        success, status, data = self.make_request('GET', '/categories')
        
        if success and 'categories' in data and len(data['categories']) >= 5:
            expected_categories = ['Website', 'Landing Page', 'AMP', 'Partner', 'Internal']
            found_names = [cat['name'] for cat in data['categories']]
            all_found = all(name in found_names for name in expected_categories)
            
            self.log_test("Categories List (5 seeded)", all_found)
            return all_found
        else:
            self.log_test("Categories List (5 seeded)", False, f"Status {status}, Response: {data}")
            return False
    
    def test_project_create(self) -> bool:
        """Test creating a project"""
        success, status, data = self.make_request('POST', '/projects', {
            'name': 'Test API Project',
            'category_id': 1,  # Website category
            'status': 'active'
        }, expected_status=200)
        
        if success and 'project' in data:
            project = data['project']
            self.project_id = project['id']
            self.log_test("Project Create", True)
            return True
        else:
            self.log_test("Project Create", False, f"Status {status}, Response: {data}")
            return False
    
    def test_project_list(self) -> bool:
        """Test listing projects"""
        success, status, data = self.make_request('GET', '/projects')
        
        if success and 'projects' in data:
            self.log_test("Project List", True)
            return True
        else:
            self.log_test("Project List", False, f"Status {status}, Response: {data}")
            return False
    
    def test_project_get(self) -> bool:
        """Test getting single project"""
        if not self.project_id:
            self.log_test("Project Get", False, "No project ID available")
            return False
            
        success, status, data = self.make_request('GET', f'/projects/{self.project_id}')
        
        if success and 'project' in data:
            self.log_test("Project Get", True)
            return True
        else:
            self.log_test("Project Get", False, f"Status {status}, Response: {data}")
            return False
    
    def test_project_update(self) -> bool:
        """Test updating project status"""
        if not self.project_id:
            self.log_test("Project Update", False, "No project ID available")
            return False
            
        success, status, data = self.make_request('PATCH', f'/projects/{self.project_id}', {
            'status': 'paused'
        })
        
        if success and 'project' in data and data['project']['status'] == 'paused':
            self.log_test("Project Update (Status)", True)
            return True
        else:
            self.log_test("Project Update (Status)", False, f"Status {status}, Response: {data}")
            return False
    
    def test_whitelist_add(self) -> bool:
        """Test adding domain to whitelist"""
        if not self.project_id:
            self.log_test("Whitelist Add", False, "No project ID available")
            return False
            
        success, status, data = self.make_request('POST', f'/projects/{self.project_id}/whitelist', {
            'domain_pattern': 'test-api.example.com'
        })
        
        if success and 'whitelist' in data:
            self.whitelist_id = data['whitelist']['id']
            self.log_test("Whitelist Add", True)
            return True
        else:
            self.log_test("Whitelist Add", False, f"Status {status}, Response: {data}")
            return False
    
    def test_whitelist_list(self) -> bool:
        """Test listing whitelist entries"""
        if not self.project_id:
            self.log_test("Whitelist List", False, "No project ID available")
            return False
            
        success, status, data = self.make_request('GET', f'/projects/{self.project_id}/whitelist')
        
        if success and 'whitelists' in data:
            self.log_test("Whitelist List", True)
            return True
        else:
            self.log_test("Whitelist List", False, f"Status {status}, Response: {data}")
            return False
    
    def test_script_create(self) -> bool:
        """Test creating a script"""
        if not self.project_id:
            self.log_test("Script Create", False, "No project ID available")
            return False
            
        success, status, data = self.make_request('POST', f'/projects/{self.project_id}/scripts', {
            'name': 'Test API Script',
            'js_code': 'console.log("API Test Script");',
            'status': 'active'
        })
        
        if success and 'script' in data:
            self.script_id = data['script']['id']
            self.log_test("Script Create", True)
            return True
        else:
            self.log_test("Script Create", False, f"Status {status}, Response: {data}")
            return False
    
    def test_script_list(self) -> bool:
        """Test listing scripts"""
        if not self.project_id:
            self.log_test("Script List", False, "No project ID available")
            return False
            
        success, status, data = self.make_request('GET', f'/projects/{self.project_id}/scripts')
        
        if success and 'scripts' in data:
            self.log_test("Script List", True)
            return True
        else:
            self.log_test("Script List", False, f"Status {status}, Response: {data}")
            return False
    
    def test_script_update(self) -> bool:
        """Test updating script status"""
        if not self.project_id or not self.script_id:
            self.log_test("Script Update", False, "Missing project or script ID")
            return False
            
        success, status, data = self.make_request('PATCH', f'/projects/{self.project_id}/scripts/{self.script_id}', {
            'status': 'disabled'
        })
        
        if success and 'script' in data and data['script']['status'] == 'disabled':
            self.log_test("Script Update (Status)", True)
            return True
        else:
            self.log_test("Script Update (Status)", False, f"Status {status}, Response: {data}")
            return False
    
    def test_dashboard_stats(self) -> bool:
        """Test dashboard stats endpoint"""
        success, status, data = self.make_request('GET', '/dashboard/stats')
        
        if success and 'stats' in data and 'recent_projects' in data:
            stats = data['stats']
            required_fields = ['total_projects', 'total_scripts', 'total_whitelists', 'total_requests']
            has_all_fields = all(field in stats for field in required_fields)
            
            self.log_test("Dashboard Stats", has_all_fields)
            return has_all_fields
        else:
            self.log_test("Dashboard Stats", False, f"Status {status}, Response: {data}")
            return False
    
    def test_js_delivery_denied(self) -> bool:
        """Test JS delivery returns noop for unauthorized domain"""
        if not self.project_id:
            self.log_test("JS Delivery (Denied)", False, "No project data available")
            return False
            
        # Try to get existing project slug (assume 'my-widget' exists)
        url = f"{self.api_base}/js/my-widget/tracker.js"
        
        try:
            # Request without proper Origin/Referer - should return noop
            response = requests.get(url, headers={'Origin': 'https://unauthorized-domain.com'})
            
            if response.status_code == 200 and response.headers.get('content-type', '').startswith('application/javascript'):
                content = response.text
                is_noop = 'noop' in content.lower() or 'unauthorized' in content.lower()
                self.log_test("JS Delivery (Denied - Unauthorized Domain)", is_noop)
                return is_noop
            else:
                self.log_test("JS Delivery (Denied - Unauthorized Domain)", False, f"Status {response.status_code}")
                return False
                
        except Exception as e:
            self.log_test("JS Delivery (Denied - Unauthorized Domain)", False, f"Request failed: {str(e)}")
            return False
    
    def test_js_delivery_allowed(self) -> bool:
        """Test JS delivery returns real JS for authorized domain"""
        # Try with existing test data
        url = f"{self.api_base}/js/my-widget/tracker.js"
        
        try:
            # Request with whitelisted domain
            response = requests.get(url, headers={'Origin': 'https://example.com'})
            
            if response.status_code == 200 and response.headers.get('content-type', '').startswith('application/javascript'):
                content = response.text
                # Should return real JS, not noop
                is_real_js = 'noop' not in content.lower() and 'unauthorized' not in content.lower() and len(content.strip()) > 20
                self.log_test("JS Delivery (Allowed - Whitelisted Domain)", is_real_js)
                return is_real_js
            else:
                self.log_test("JS Delivery (Allowed - Whitelisted Domain)", False, f"Status {response.status_code}")
                return False
                
        except Exception as e:
            self.log_test("JS Delivery (Allowed - Whitelisted Domain)", False, f"Request failed: {str(e)}")
            return False
    
    def test_domain_validation(self) -> bool:
        """Test domain validation rejects invalid patterns"""
        if not self.project_id:
            self.log_test("Domain Validation", False, "No project ID available")
            return False
        
        invalid_patterns = [
            'https://example.com',  # with protocol
            '*',                    # bare wildcard
            'localhost',            # localhost
            'a.*.com'              # invalid wildcard position
        ]
        
        rejected_count = 0
        for pattern in invalid_patterns:
            success, status, data = self.make_request('POST', f'/projects/{self.project_id}/whitelist', {
                'domain_pattern': pattern
            }, expected_status=400)  # Should return 400 for invalid patterns
            
            if status == 400:
                rejected_count += 1
        
        all_rejected = rejected_count == len(invalid_patterns)
        self.log_test("Domain Validation (Invalid Patterns Rejected)", all_rejected)
        return all_rejected
    
    def run_all_tests(self) -> Dict[str, Any]:
        """Run all API tests"""
        print(f"🧪 Starting JavaScript Hosting Platform API Tests")
        print(f"📍 Backend URL: {self.base_url}")
        print("=" * 60)
        
        # Authentication tests
        print("\n🔐 Authentication Tests")
        login_success = self.test_auth_login()
        if login_success:
            self.test_auth_me()
        
        # If login failed, try registration
        if not login_success:
            print("\n🆕 Trying registration (login failed)")
            reg_success = self.test_auth_register()
            if reg_success:
                self.test_auth_me()
        
        # Only proceed if we have authentication
        if not self.token:
            print("\n❌ Cannot proceed without authentication")
            return self.get_summary()
        
        # Categories
        print("\n📂 Categories Tests")
        self.test_categories_list()
        
        # Projects
        print("\n📋 Project CRUD Tests")
        self.test_project_create()
        self.test_project_list()
        self.test_project_get()
        self.test_project_update()
        
        # Whitelist
        print("\n🌐 Whitelist Tests")
        self.test_whitelist_add()
        self.test_whitelist_list()
        self.test_domain_validation()
        
        # Scripts
        print("\n📜 Script CRUD Tests")
        self.test_script_create()
        self.test_script_list()
        self.test_script_update()
        
        # Dashboard
        print("\n📊 Dashboard Tests")
        self.test_dashboard_stats()
        
        # JS Delivery
        print("\n🚀 JS Delivery Tests")
        self.test_js_delivery_denied()
        self.test_js_delivery_allowed()
        
        return self.get_summary()
    
    def get_summary(self) -> Dict[str, Any]:
        """Get test summary"""
        success_rate = (self.tests_passed / self.tests_run * 100) if self.tests_run > 0 else 0
        
        print("\n" + "=" * 60)
        print(f"📊 Test Summary: {self.tests_passed}/{self.tests_run} passed ({success_rate:.1f}%)")
        
        return {
            'tests_run': self.tests_run,
            'tests_passed': self.tests_passed,
            'success_rate': success_rate,
            'backend_working': success_rate > 80
        }

def main():
    """Main test runner"""
    backend_url = "https://js-hosting-platform.preview.emergentagent.com"
    
    tester = JSHostAPITester(backend_url)
    summary = tester.run_all_tests()
    
    # Return appropriate exit code
    return 0 if summary['backend_working'] else 1

if __name__ == "__main__":
    sys.exit(main())