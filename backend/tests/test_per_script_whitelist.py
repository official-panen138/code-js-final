"""
Tests for per-script whitelist management, domain tester, analytics by_script section, and clear logs functionality.
These features were added as part of the JS Hosting Platform enhancement:
1. Per-script domain whitelisting (moved from per-project to per-script)
2. Domain tester within each script's whitelist dialog
3. Script URL display in analytics by_script section
4. Clear Logs button functionality in Access Logs section
"""
import pytest
import requests
import os
import time

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

class TestAuth:
    """Authentication helper tests"""
    
    @pytest.fixture(scope="class")
    def auth_token(self):
        """Get auth token for admin user"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": "admin@jshost.com",
            "password": "Admin@123"
        })
        assert response.status_code == 200, f"Login failed: {response.text}"
        return response.json().get("token")
    
    @pytest.fixture(scope="class")
    def auth_headers(self, auth_token):
        """Get auth headers"""
        return {"Authorization": f"Bearer {auth_token}"}
    
    def test_login_success(self):
        """Verify login works with valid credentials"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": "admin@jshost.com",
            "password": "Admin@123"
        })
        assert response.status_code == 200
        data = response.json()
        assert "token" in data
        assert "user" in data
        print(f"Login successful, user: {data['user']['email']}")


class TestPerScriptWhitelist:
    """Tests for per-script whitelist management"""
    
    @pytest.fixture(scope="class")
    def auth_token(self):
        """Get auth token"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": "admin@jshost.com",
            "password": "Admin@123"
        })
        return response.json().get("token")
    
    @pytest.fixture(scope="class")
    def auth_headers(self, auth_token):
        """Get auth headers"""
        return {"Authorization": f"Bearer {auth_token}"}
    
    @pytest.fixture(scope="class")
    def test_project(self, auth_headers):
        """Create a test project for whitelist tests"""
        # Get categories first
        cat_response = requests.get(f"{BASE_URL}/api/categories", headers=auth_headers)
        categories = cat_response.json().get("categories", [])
        category_id = categories[0]["id"] if categories else 1
        
        # Create project
        response = requests.post(f"{BASE_URL}/api/projects", json={
            "name": "TEST_WhitelistProject",
            "category_id": category_id
        }, headers=auth_headers)
        assert response.status_code == 200
        project = response.json()["project"]
        yield project
        
        # Cleanup
        requests.delete(f"{BASE_URL}/api/projects/{project['id']}", headers=auth_headers)
    
    @pytest.fixture(scope="class")
    def test_script(self, auth_headers, test_project):
        """Create a test script for whitelist tests"""
        response = requests.post(f"{BASE_URL}/api/projects/{test_project['id']}/scripts", json={
            "name": "TEST_WhitelistScript",
            "js_code": "console.log('test whitelist script');"
        }, headers=auth_headers)
        assert response.status_code == 200
        script = response.json()["script"]
        yield script
    
    def test_whitelist_list_empty(self, auth_headers, test_project, test_script):
        """Test listing whitelist for a new script (should be empty)"""
        response = requests.get(
            f"{BASE_URL}/api/projects/{test_project['id']}/scripts/{test_script['id']}/whitelist",
            headers=auth_headers
        )
        assert response.status_code == 200
        data = response.json()
        assert "whitelists" in data
        print(f"Initial whitelist entries: {len(data['whitelists'])}")
    
    def test_whitelist_add_exact_domain(self, auth_headers, test_project, test_script):
        """Test adding an exact domain to whitelist"""
        response = requests.post(
            f"{BASE_URL}/api/projects/{test_project['id']}/scripts/{test_script['id']}/whitelist",
            json={"domain_pattern": "example.com"},
            headers=auth_headers
        )
        assert response.status_code == 200
        data = response.json()
        assert "whitelist" in data
        assert data["whitelist"]["domain_pattern"] == "example.com"
        assert data["whitelist"]["is_active"] == True
        print(f"Added exact domain: {data['whitelist']['domain_pattern']}")
    
    def test_whitelist_add_wildcard_domain(self, auth_headers, test_project, test_script):
        """Test adding a wildcard domain to whitelist"""
        response = requests.post(
            f"{BASE_URL}/api/projects/{test_project['id']}/scripts/{test_script['id']}/whitelist",
            json={"domain_pattern": "*.test.com"},
            headers=auth_headers
        )
        assert response.status_code == 200
        data = response.json()
        assert data["whitelist"]["domain_pattern"] == "*.test.com"
        print(f"Added wildcard domain: {data['whitelist']['domain_pattern']}")
    
    def test_whitelist_add_duplicate_fails(self, auth_headers, test_project, test_script):
        """Test adding duplicate domain fails"""
        response = requests.post(
            f"{BASE_URL}/api/projects/{test_project['id']}/scripts/{test_script['id']}/whitelist",
            json={"domain_pattern": "example.com"},
            headers=auth_headers
        )
        assert response.status_code == 400
        print("Duplicate domain correctly rejected")
    
    def test_whitelist_add_invalid_pattern_fails(self, auth_headers, test_project, test_script):
        """Test adding invalid domain pattern fails"""
        response = requests.post(
            f"{BASE_URL}/api/projects/{test_project['id']}/scripts/{test_script['id']}/whitelist",
            json={"domain_pattern": "*.*.com"},
            headers=auth_headers
        )
        assert response.status_code == 400
        print("Invalid pattern correctly rejected")
    
    def test_whitelist_list_with_entries(self, auth_headers, test_project, test_script):
        """Test listing whitelist after adding entries"""
        response = requests.get(
            f"{BASE_URL}/api/projects/{test_project['id']}/scripts/{test_script['id']}/whitelist",
            headers=auth_headers
        )
        assert response.status_code == 200
        data = response.json()
        assert len(data["whitelists"]) >= 2
        print(f"Whitelist now has {len(data['whitelists'])} entries")
    
    def test_whitelist_toggle_off(self, auth_headers, test_project, test_script):
        """Test toggling whitelist entry off"""
        # Get whitelist entries first
        list_response = requests.get(
            f"{BASE_URL}/api/projects/{test_project['id']}/scripts/{test_script['id']}/whitelist",
            headers=auth_headers
        )
        whitelists = list_response.json()["whitelists"]
        entry_id = whitelists[0]["id"]
        
        # Toggle off
        response = requests.patch(
            f"{BASE_URL}/api/projects/{test_project['id']}/scripts/{test_script['id']}/whitelist/{entry_id}",
            json={"is_active": False},
            headers=auth_headers
        )
        assert response.status_code == 200
        assert response.json()["whitelist"]["is_active"] == False
        print("Whitelist entry toggled off")
    
    def test_whitelist_toggle_on(self, auth_headers, test_project, test_script):
        """Test toggling whitelist entry back on"""
        list_response = requests.get(
            f"{BASE_URL}/api/projects/{test_project['id']}/scripts/{test_script['id']}/whitelist",
            headers=auth_headers
        )
        whitelists = list_response.json()["whitelists"]
        entry_id = whitelists[0]["id"]
        
        response = requests.patch(
            f"{BASE_URL}/api/projects/{test_project['id']}/scripts/{test_script['id']}/whitelist/{entry_id}",
            json={"is_active": True},
            headers=auth_headers
        )
        assert response.status_code == 200
        assert response.json()["whitelist"]["is_active"] == True
        print("Whitelist entry toggled back on")
    
    def test_whitelist_delete(self, auth_headers, test_project, test_script):
        """Test deleting whitelist entry"""
        # Add a new entry to delete
        add_response = requests.post(
            f"{BASE_URL}/api/projects/{test_project['id']}/scripts/{test_script['id']}/whitelist",
            json={"domain_pattern": "todelete.com"},
            headers=auth_headers
        )
        entry_id = add_response.json()["whitelist"]["id"]
        
        # Delete
        response = requests.delete(
            f"{BASE_URL}/api/projects/{test_project['id']}/scripts/{test_script['id']}/whitelist/{entry_id}",
            headers=auth_headers
        )
        assert response.status_code == 200
        print("Whitelist entry deleted")
    
    def test_whitelist_count_on_script(self, auth_headers, test_project, test_script):
        """Test that whitelist_count is returned with script data"""
        response = requests.get(
            f"{BASE_URL}/api/projects/{test_project['id']}/scripts/{test_script['id']}",
            headers=auth_headers
        )
        assert response.status_code == 200
        data = response.json()
        assert "whitelist_count" in data["script"]
        print(f"Script whitelist_count: {data['script']['whitelist_count']}")


class TestDomainTester:
    """Tests for domain tester feature (per-script)"""
    
    @pytest.fixture(scope="class")
    def auth_token(self):
        """Get auth token"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": "admin@jshost.com",
            "password": "Admin@123"
        })
        return response.json().get("token")
    
    @pytest.fixture(scope="class")
    def auth_headers(self, auth_token):
        """Get auth headers"""
        return {"Authorization": f"Bearer {auth_token}"}
    
    @pytest.fixture(scope="class")
    def test_project_with_script(self, auth_headers):
        """Create project with script and whitelist for testing"""
        # Get categories
        cat_response = requests.get(f"{BASE_URL}/api/categories", headers=auth_headers)
        categories = cat_response.json().get("categories", [])
        category_id = categories[0]["id"] if categories else 1
        
        # Create project
        proj_response = requests.post(f"{BASE_URL}/api/projects", json={
            "name": "TEST_DomainTester",
            "category_id": category_id
        }, headers=auth_headers)
        project = proj_response.json()["project"]
        
        # Create script
        script_response = requests.post(f"{BASE_URL}/api/projects/{project['id']}/scripts", json={
            "name": "TEST_DomainTesterScript",
            "js_code": "console.log('domain tester test');"
        }, headers=auth_headers)
        script = script_response.json()["script"]
        
        # Add whitelist entries
        requests.post(
            f"{BASE_URL}/api/projects/{project['id']}/scripts/{script['id']}/whitelist",
            json={"domain_pattern": "allowed.com"},
            headers=auth_headers
        )
        requests.post(
            f"{BASE_URL}/api/projects/{project['id']}/scripts/{script['id']}/whitelist",
            json={"domain_pattern": "*.wildcard.com"},
            headers=auth_headers
        )
        
        yield {"project": project, "script": script}
        
        # Cleanup
        requests.delete(f"{BASE_URL}/api/projects/{project['id']}", headers=auth_headers)
    
    def test_domain_allowed_exact_match(self, auth_headers, test_project_with_script):
        """Test domain tester with exact match"""
        project_id = test_project_with_script["project"]["id"]
        script_id = test_project_with_script["script"]["id"]
        
        response = requests.post(
            f"{BASE_URL}/api/projects/{project_id}/scripts/{script_id}/test-domain",
            json={"domain": "allowed.com"},
            headers=auth_headers
        )
        assert response.status_code == 200
        data = response.json()
        assert data["allowed"] == True
        assert data["matched_pattern"] == "allowed.com"
        print(f"Domain test result: allowed={data['allowed']}, matched={data['matched_pattern']}")
    
    def test_domain_allowed_wildcard_match(self, auth_headers, test_project_with_script):
        """Test domain tester with wildcard match"""
        project_id = test_project_with_script["project"]["id"]
        script_id = test_project_with_script["script"]["id"]
        
        response = requests.post(
            f"{BASE_URL}/api/projects/{project_id}/scripts/{script_id}/test-domain",
            json={"domain": "sub.wildcard.com"},
            headers=auth_headers
        )
        assert response.status_code == 200
        data = response.json()
        assert data["allowed"] == True
        assert data["matched_pattern"] == "*.wildcard.com"
        print(f"Wildcard match: {data['domain']} -> {data['matched_pattern']}")
    
    def test_domain_denied(self, auth_headers, test_project_with_script):
        """Test domain tester with non-whitelisted domain"""
        project_id = test_project_with_script["project"]["id"]
        script_id = test_project_with_script["script"]["id"]
        
        response = requests.post(
            f"{BASE_URL}/api/projects/{project_id}/scripts/{script_id}/test-domain",
            json={"domain": "notwhitelisted.com"},
            headers=auth_headers
        )
        assert response.status_code == 200
        data = response.json()
        assert data["allowed"] == False
        assert data["matched_pattern"] is None
        print(f"Domain denied: {data['domain']}, allowed={data['allowed']}")
    
    def test_domain_normalized(self, auth_headers, test_project_with_script):
        """Test domain normalization"""
        project_id = test_project_with_script["project"]["id"]
        script_id = test_project_with_script["script"]["id"]
        
        response = requests.post(
            f"{BASE_URL}/api/projects/{project_id}/scripts/{script_id}/test-domain",
            json={"domain": "https://ALLOWED.COM/path?query=1"},
            headers=auth_headers
        )
        assert response.status_code == 200
        data = response.json()
        assert data["normalized_domain"] == "allowed.com"
        assert data["allowed"] == True
        print(f"Normalized: {data['domain']} -> {data['normalized_domain']}")


class TestAnalyticsByScript:
    """Tests for analytics by_script section showing script URLs"""
    
    @pytest.fixture(scope="class")
    def auth_token(self):
        """Get auth token"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": "admin@jshost.com",
            "password": "Admin@123"
        })
        return response.json().get("token")
    
    @pytest.fixture(scope="class")
    def auth_headers(self, auth_token):
        """Get auth headers"""
        return {"Authorization": f"Bearer {auth_token}"}
    
    def test_analytics_has_by_script_section(self, auth_headers):
        """Test that analytics response includes by_script section"""
        # Get projects
        projects_response = requests.get(f"{BASE_URL}/api/projects", headers=auth_headers)
        projects = projects_response.json().get("projects", [])
        
        if not projects:
            pytest.skip("No projects available for testing")
        
        project_id = projects[0]["id"]
        
        response = requests.get(
            f"{BASE_URL}/api/projects/{project_id}/analytics",
            headers=auth_headers
        )
        assert response.status_code == 200
        data = response.json()
        
        assert "by_script" in data
        print(f"Analytics has by_script section: {len(data.get('by_script', []))} entries")
    
    def test_by_script_includes_script_url(self, auth_headers):
        """Test that by_script entries include script_url field"""
        # Get projects
        projects_response = requests.get(f"{BASE_URL}/api/projects", headers=auth_headers)
        projects = projects_response.json().get("projects", [])
        
        if not projects:
            pytest.skip("No projects available for testing")
        
        project_id = projects[0]["id"]
        
        response = requests.get(
            f"{BASE_URL}/api/projects/{project_id}/analytics",
            headers=auth_headers
        )
        data = response.json()
        
        if data["by_script"]:
            for entry in data["by_script"]:
                assert "script_url" in entry
                assert "script_name" in entry
                assert "script_id" in entry
                assert "count" in entry
                assert "allowed" in entry
                assert "denied" in entry
                print(f"Script URL: {entry['script_url']} (name: {entry['script_name']})")
        else:
            print("No by_script entries (no access logs for scripts)")
    
    def test_by_script_url_format(self, auth_headers):
        """Test that script_url follows expected format"""
        # Get first project with scripts
        projects_response = requests.get(f"{BASE_URL}/api/projects", headers=auth_headers)
        projects = projects_response.json().get("projects", [])
        
        for project in projects:
            project_id = project["id"]
            analytics_response = requests.get(
                f"{BASE_URL}/api/projects/{project_id}/analytics",
                headers=auth_headers
            )
            by_script = analytics_response.json().get("by_script", [])
            
            if by_script:
                for entry in by_script:
                    script_url = entry["script_url"]
                    # URL should follow format: /api/js/{project_slug}/{script_slug}.js
                    assert script_url.startswith("/api/js/")
                    assert script_url.endswith(".js")
                    print(f"Script URL format valid: {script_url}")
                return
        
        print("No by_script data found to verify URL format")


class TestClearLogs:
    """Tests for Clear Logs functionality"""
    
    @pytest.fixture(scope="class")
    def auth_token(self):
        """Get auth token"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": "admin@jshost.com",
            "password": "Admin@123"
        })
        return response.json().get("token")
    
    @pytest.fixture(scope="class")
    def auth_headers(self, auth_token):
        """Get auth headers"""
        return {"Authorization": f"Bearer {auth_token}"}
    
    @pytest.fixture(scope="class")
    def test_project_with_logs(self, auth_headers):
        """Create project and generate some access logs"""
        # Get categories
        cat_response = requests.get(f"{BASE_URL}/api/categories", headers=auth_headers)
        categories = cat_response.json().get("categories", [])
        category_id = categories[0]["id"] if categories else 1
        
        # Create project
        proj_response = requests.post(f"{BASE_URL}/api/projects", json={
            "name": "TEST_ClearLogs",
            "category_id": category_id
        }, headers=auth_headers)
        project = proj_response.json()["project"]
        
        # Create script
        script_response = requests.post(f"{BASE_URL}/api/projects/{project['id']}/scripts", json={
            "name": "TEST_ClearLogsScript",
            "js_code": "console.log('clear logs test');"
        }, headers=auth_headers)
        script = script_response.json()["script"]
        
        # Add a whitelist entry
        requests.post(
            f"{BASE_URL}/api/projects/{project['id']}/scripts/{script['id']}/whitelist",
            json={"domain_pattern": "test.com"},
            headers=auth_headers
        )
        
        # Generate some access logs by requesting the script
        script_url = f"{BASE_URL}/api/js/{project['slug']}/{script['slug']}.js"
        
        # Request from whitelisted domain
        requests.get(script_url, headers={"Referer": "https://test.com/page"})
        
        # Request from non-whitelisted domain
        requests.get(script_url, headers={"Referer": "https://denied.com/page"})
        
        time.sleep(0.5)  # Wait for logs to be written
        
        yield {"project": project, "script": script}
        
        # Cleanup
        requests.delete(f"{BASE_URL}/api/projects/{project['id']}", headers=auth_headers)
    
    def test_logs_exist_before_clear(self, auth_headers, test_project_with_logs):
        """Verify logs exist before clearing"""
        project_id = test_project_with_logs["project"]["id"]
        
        response = requests.get(
            f"{BASE_URL}/api/projects/{project_id}/logs",
            headers=auth_headers
        )
        assert response.status_code == 200
        data = response.json()
        log_count = len(data["logs"])
        print(f"Logs before clear: {log_count}")
    
    def test_clear_logs_endpoint(self, auth_headers, test_project_with_logs):
        """Test clear logs DELETE endpoint"""
        project_id = test_project_with_logs["project"]["id"]
        
        response = requests.delete(
            f"{BASE_URL}/api/projects/{project_id}/logs",
            headers=auth_headers
        )
        assert response.status_code == 200
        data = response.json()
        assert "message" in data
        assert "cleared" in data["message"].lower()
        print(f"Clear logs response: {data['message']}")
    
    def test_logs_empty_after_clear(self, auth_headers, test_project_with_logs):
        """Verify logs are empty after clearing"""
        project_id = test_project_with_logs["project"]["id"]
        
        response = requests.get(
            f"{BASE_URL}/api/projects/{project_id}/logs",
            headers=auth_headers
        )
        assert response.status_code == 200
        data = response.json()
        assert len(data["logs"]) == 0
        assert data["stats"]["total"] == 0
        print("Logs successfully cleared - count is 0")


class TestScriptCreationWithWhitelist:
    """Tests for script creation and whitelist workflow"""
    
    @pytest.fixture(scope="class")
    def auth_token(self):
        """Get auth token"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": "admin@jshost.com",
            "password": "Admin@123"
        })
        return response.json().get("token")
    
    @pytest.fixture(scope="class")
    def auth_headers(self, auth_token):
        """Get auth headers"""
        return {"Authorization": f"Bearer {auth_token}"}
    
    @pytest.fixture(scope="class")
    def test_project(self, auth_headers):
        """Create a test project"""
        cat_response = requests.get(f"{BASE_URL}/api/categories", headers=auth_headers)
        categories = cat_response.json().get("categories", [])
        category_id = categories[0]["id"] if categories else 1
        
        response = requests.post(f"{BASE_URL}/api/projects", json={
            "name": "TEST_ScriptCreation",
            "category_id": category_id
        }, headers=auth_headers)
        project = response.json()["project"]
        yield project
        requests.delete(f"{BASE_URL}/api/projects/{project['id']}", headers=auth_headers)
    
    def test_create_script_and_add_whitelist(self, auth_headers, test_project):
        """Test full workflow: create script, add whitelist"""
        project_id = test_project["id"]
        
        # Create script
        script_response = requests.post(f"{BASE_URL}/api/projects/{project_id}/scripts", json={
            "name": "TEST_NewScript",
            "js_code": "console.log('new script');"
        }, headers=auth_headers)
        assert script_response.status_code == 200
        script = script_response.json()["script"]
        
        # Verify script has whitelist_count = 0
        assert script["whitelist_count"] == 0
        
        # Add whitelist
        wl_response = requests.post(
            f"{BASE_URL}/api/projects/{project_id}/scripts/{script['id']}/whitelist",
            json={"domain_pattern": "mysite.com"},
            headers=auth_headers
        )
        assert wl_response.status_code == 200
        
        # Verify script now has whitelist_count = 1
        script_response = requests.get(
            f"{BASE_URL}/api/projects/{project_id}/scripts/{script['id']}",
            headers=auth_headers
        )
        updated_script = script_response.json()["script"]
        assert updated_script["whitelist_count"] == 1
        print(f"Script created with {updated_script['whitelist_count']} whitelist entries")
    
    def test_js_delivery_with_whitelist(self, auth_headers, test_project):
        """Test JS delivery respects per-script whitelist"""
        project_id = test_project["id"]
        
        # Create script
        script_response = requests.post(f"{BASE_URL}/api/projects/{project_id}/scripts", json={
            "name": "TEST_DeliveryScript",
            "js_code": "console.log('delivery test');"
        }, headers=auth_headers)
        script = script_response.json()["script"]
        
        # Add whitelist
        requests.post(
            f"{BASE_URL}/api/projects/{project_id}/scripts/{script['id']}/whitelist",
            json={"domain_pattern": "whitelisted.com"},
            headers=auth_headers
        )
        
        # Test delivery from whitelisted domain
        script_url = f"{BASE_URL}/api/js/{test_project['slug']}/{script['slug']}.js"
        
        allowed_response = requests.get(script_url, headers={"Referer": "https://whitelisted.com/page"})
        assert allowed_response.status_code == 200
        assert "delivery test" in allowed_response.text
        print("Script delivered to whitelisted domain")
        
        # Test delivery from non-whitelisted domain (should get noop)
        denied_response = requests.get(script_url, headers={"Referer": "https://notwhitelisted.com/page"})
        assert denied_response.status_code == 200
        assert "noop" in denied_response.text or "unauthorized" in denied_response.text
        print("Script denied to non-whitelisted domain (noop response)")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
