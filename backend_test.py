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
        self.created_category_id = None
        self.created_role_id = None
        
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
    
    def test_categories_all(self) -> bool:
        """Test GET /api/categories/all with project counts"""
        success, status, data = self.make_request('GET', '/categories/all')
        
        if success and 'categories' in data:
            categories = data['categories']
            has_project_count = all('project_count' in cat for cat in categories)
            website_cat = next((cat for cat in categories if cat['name'] == 'Website'), None)
            
            if has_project_count and website_cat:
                self.log_test("Categories All (with project counts)", True)
                print(f"    Website category has {website_cat['project_count']} projects")
                return True
        
        self.log_test("Categories All (with project counts)", False, f"Status {status}, Response: {data}")
        return False
    
    def test_category_create(self) -> bool:
        """Test POST /api/categories"""
        test_name = f"Test Category {datetime.now().strftime('%H%M%S')}"
        success, status, data = self.make_request('POST', '/categories', {
            'name': test_name,
            'description': 'Test category for API testing'
        })
        
        if success and 'category' in data:
            self.created_category_id = data['category']['id']
            self.log_test("Category Create", True)
            print(f"    Created category ID: {self.created_category_id}")
            return True
        else:
            self.log_test("Category Create", False, f"Status {status}, Response: {data}")
            return False
    
    def test_category_update(self) -> bool:
        """Test PATCH /api/categories/{id}"""
        if not hasattr(self, 'created_category_id') or not self.created_category_id:
            self.log_test("Category Update", False, "No created category ID available")
            return False
            
        updated_name = f"Updated Category {datetime.now().strftime('%H%M%S')}"
        success, status, data = self.make_request('PATCH', f'/categories/{self.created_category_id}', {
            'name': updated_name,
            'description': 'Updated description'
        })
        
        if success and 'category' in data and data['category']['name'] == updated_name:
            self.log_test("Category Update", True)
            return True
        else:
            self.log_test("Category Update", False, f"Status {status}, Response: {data}")
            return False
    
    def test_category_delete_unused(self) -> bool:
        """Test DELETE /api/categories/{id} for unused category"""
        if not hasattr(self, 'created_category_id') or not self.created_category_id:
            self.log_test("Category Delete (unused)", False, "No created category ID available")
            return False
            
        success, status, data = self.make_request('DELETE', f'/categories/{self.created_category_id}', expected_status=200)
        
        if success:
            self.log_test("Category Delete (unused)", True)
            return True
        else:
            self.log_test("Category Delete (unused)", False, f"Status {status}, Response: {data}")
            return False
    
    def test_category_delete_in_use(self) -> bool:
        """Test DELETE /api/categories/{id} for in-use category (should fail with 400)"""
        # Try to delete Website category which should have projects
        success, status, data = self.make_request('DELETE', '/categories/1', expected_status=400)
        
        if status == 400:
            self.log_test("Category Delete (in-use, should fail)", True)
            print(f"    Expected 400 error: {data.get('detail', 'No detail')}")
            return True
        else:
            self.log_test("Category Delete (in-use, should fail)", False, f"Expected 400, got {status}")
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
    
    def test_domain_tester_endpoint(self) -> bool:
        """Test new domain tester endpoint"""
        if not self.project_id:
            self.log_test("Domain Tester Endpoint", False, "No project ID available")
            return False
            
        # Test allowed domain (should match our test-api.example.com whitelist entry)
        success, status, data = self.make_request('POST', f'/projects/{self.project_id}/test-domain', {
            'domain': 'test-api.example.com'
        })
        
        if success and 'allowed' in data and 'normalized_domain' in data:
            allowed_correct = data['allowed'] == True
            normalized_correct = data['normalized_domain'] == 'test-api.example.com'
            
            # Test denied domain
            success2, status2, data2 = self.make_request('POST', f'/projects/{self.project_id}/test-domain', {
                'domain': 'https://denied.com/path'
            })
            
            if success2 and 'allowed' in data2 and 'normalized_domain' in data2:
                denied_correct = data2['allowed'] == False
                normalized_denied = data2['normalized_domain'] == 'denied.com'
                
                all_tests_passed = allowed_correct and normalized_correct and denied_correct and normalized_denied
                self.log_test("Domain Tester Endpoint", all_tests_passed)
                return all_tests_passed
            else:
                self.log_test("Domain Tester Endpoint", False, f"Second test failed: Status {status2}, Response: {data2}")
                return False
        else:
            self.log_test("Domain Tester Endpoint", False, f"Status {status}, Response: {data}")
            return False
    
    def test_analytics_endpoint(self) -> bool:
        """Test new analytics endpoint"""
        if not self.project_id:
            self.log_test("Analytics Endpoint", False, "No project ID available")
            return False
            
        success, status, data = self.make_request('GET', f'/projects/{self.project_id}/analytics')
        
        if success and 'summary' in data and 'daily' in data and 'top_domains' in data:
            # Check summary structure
            summary = data['summary']
            required_fields = ['total', 'allowed', 'denied']
            has_summary_fields = all(field in summary for field in required_fields)
            
            # Check data types
            daily_is_list = isinstance(data['daily'], list)
            top_domains_is_list = isinstance(data['top_domains'], list)
            
            all_correct = has_summary_fields and daily_is_list and top_domains_is_list
            self.log_test("Analytics Endpoint", all_correct)
            return all_correct
        else:
            self.log_test("Analytics Endpoint", False, f"Status {status}, Response: {data}")
            return False

    def test_menus_endpoint(self) -> bool:
        """Test GET /api/menus endpoint"""
        success, status, data = self.make_request('GET', '/menus')
        
        if success and 'menus' in data:
            menus = data['menus']
            expected_keys = ['dashboard', 'projects', 'settings', 'user_management']
            found_keys = [menu['key'] for menu in menus]
            has_all_keys = all(key in found_keys for key in expected_keys)
            
            self.log_test("Menus Endpoint", has_all_keys)
            print(f"    Found menu keys: {found_keys}")
            return has_all_keys
        else:
            self.log_test("Menus Endpoint", False, f"Status {status}, Response: {data}")
            return False

    def test_roles_list(self) -> bool:
        """Test GET /api/roles endpoint"""
        success, status, data = self.make_request('GET', '/roles')
        
        if success and 'roles' in data and 'available_menus' in data:
            roles = data['roles']
            has_admin = any(role['name'] == 'admin' for role in roles)
            has_user = any(role['name'] == 'user' for role in roles)
            has_user_count = all('user_count' in role for role in roles)
            
            all_checks = has_admin and has_user and has_user_count
            self.log_test("Roles List", all_checks)
            print(f"    Found {len(roles)} roles: {[r['name'] for r in roles]}")
            return all_checks
        else:
            self.log_test("Roles List", False, f"Status {status}, Response: {data}")
            return False

    def test_role_create(self) -> bool:
        """Test POST /api/roles endpoint"""
        test_role_name = f"test_role_{datetime.now().strftime('%H%M%S')}"
        
        success, status, data = self.make_request('POST', '/roles', {
            'name': test_role_name,
            'description': 'Test role for API testing',
            'permissions': ['dashboard', 'projects']
        })
        
        if success and 'role' in data:
            self.created_role_id = data['role']['id']
            self.log_test("Role Create", True)
            print(f"    Created role ID: {self.created_role_id}")
            return True
        else:
            self.log_test("Role Create", False, f"Status {status}, Response: {data}")
            return False

    def test_role_update(self) -> bool:
        """Test PATCH /api/roles/{id} endpoint"""
        if not hasattr(self, 'created_role_id') or not self.created_role_id:
            self.log_test("Role Update", False, "No created role ID available")
            return False
            
        success, status, data = self.make_request('PATCH', f'/roles/{self.created_role_id}', {
            'description': 'Updated test role description',
            'permissions': ['dashboard', 'projects', 'settings']
        })
        
        if success and 'role' in data:
            updated_perms = data['role'].get('permissions', [])
            has_settings = 'settings' in updated_perms
            self.log_test("Role Update", has_settings)
            return has_settings
        else:
            self.log_test("Role Update", False, f"Status {status}, Response: {data}")
            return False

    def test_role_delete_unused(self) -> bool:
        """Test DELETE /api/roles/{id} for unused role"""
        if not hasattr(self, 'created_role_id') or not self.created_role_id:
            self.log_test("Role Delete (unused)", False, "No created role ID available")
            return False
            
        success, status, data = self.make_request('DELETE', f'/roles/{self.created_role_id}', expected_status=200)
        
        if success:
            self.log_test("Role Delete (unused)", True)
            return True
        else:
            self.log_test("Role Delete (unused)", False, f"Status {status}, Response: {data}")
            return False

    def test_role_delete_system_role(self) -> bool:
        """Test DELETE /api/roles/{id} for system role (should fail)"""
        # Try to delete admin role (system role, should fail with 400)
        success, status, data = self.make_request('DELETE', '/roles/1', expected_status=400)
        
        if status == 400:
            self.log_test("Role Delete (system role, should fail)", True)
            print(f"    Expected 400 error: {data.get('detail', 'No detail')}")
            return True
        else:
            self.log_test("Role Delete (system role, should fail)", False, f"Expected 400, got {status}")
            return False

    def test_users_list(self) -> bool:
        """Test GET /api/users endpoint"""
        success, status, data = self.make_request('GET', '/users')
        
        if success and 'users' in data and 'roles' in data:
            users = data['users']
            roles = data['roles']
            has_users = len(users) > 0
            has_roles = len(roles) > 0
            
            all_checks = has_users and has_roles
            self.log_test("Users List", all_checks)
            print(f"    Found {len(users)} users, {len(roles)} roles")
            return all_checks
        else:
            self.log_test("Users List", False, f"Status {status}, Response: {data}")
            return False

    def test_user_update_role(self) -> bool:
        """Test PATCH /api/users/{id} endpoint for role update"""
        if not self.user_id:
            self.log_test("User Update Role", False, "No user ID available")
            return False
            
        # Get current user info first
        success, status, data = self.make_request('GET', '/auth/me')
        if not success:
            self.log_test("User Update Role", False, "Could not get current user info")
            return False
            
        current_role = data['user']['role']
        new_role = 'admin' if current_role == 'user' else 'user'
        
        success, status, data = self.make_request('PATCH', f'/users/{self.user_id}', {
            'role': new_role
        })
        
        if success and 'user' in data:
            updated_role = data['user']['role']
            role_updated = updated_role == new_role
            self.log_test("User Update Role", role_updated)
            print(f"    Role updated from {current_role} to {updated_role}")
            return role_updated
        else:
            self.log_test("User Update Role", False, f"Status {status}, Response: {data}")
            return False

    def test_user_update_status(self) -> bool:
        """Test PATCH /api/users/{id} endpoint for status update"""
        if not self.user_id:
            self.log_test("User Update Status", False, "No user ID available")
            return False
            
        # Try to deactivate self (should fail)
        success, status, data = self.make_request('PATCH', f'/users/{self.user_id}', {
            'is_active': False
        }, expected_status=400)
        
        if status == 400:
            self.log_test("User Update Status (self-deactivate, should fail)", True)
            print(f"    Expected 400 error: {data.get('detail', 'No detail')}")
            return True
        else:
            self.log_test("User Update Status (self-deactivate, should fail)", False, f"Expected 400, got {status}")
            return False
    
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
        self.test_categories_all()
        self.test_category_create()
        self.test_category_update()
        self.test_category_delete_unused()
        self.test_category_delete_in_use()
        
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
        
        # NEW: Domain Tester
        print("\n🔍 Domain Tester Tests")
        self.test_domain_tester_endpoint()
        
        # Scripts
        print("\n📜 Script CRUD Tests")
        self.test_script_create()
        self.test_script_list()
        self.test_script_update()
        
        # Dashboard
        print("\n📊 Dashboard Tests")
        self.test_dashboard_stats()
        
        # NEW: Analytics
        print("\n📈 Analytics Tests")
        self.test_analytics_endpoint()
        
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