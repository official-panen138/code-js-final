"""
Test Analytics Logs Tab Features
- GET /api/projects/{project_id}/analytics/logs - Returns individual log entries with IDs
- DELETE /api/projects/{project_id}/logs/{log_id} - Deletes single log entry
- Analytics summary stats (Total, Allowed, Denied)
- Individual log entries structure
"""
import pytest
import requests
import os

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

class TestAnalyticsLogsFeature:
    """Tests for the Analytics Logs Tab with per-row delete functionality"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Login and get token before each test"""
        self.session = requests.Session()
        login_response = self.session.post(f"{BASE_URL}/api/auth/login", json={
            "email": "admin@jshost.com",
            "password": "Admin@123"
        })
        assert login_response.status_code == 200, f"Login failed: {login_response.text}"
        self.token = login_response.json()["token"]
        self.session.headers.update({"Authorization": f"Bearer {self.token}"})
        yield
        self.session.close()
    
    @pytest.fixture
    def test_project(self):
        """Create a test project with script and generate access logs"""
        # Create project
        project_resp = self.session.post(f"{BASE_URL}/api/projects", json={
            "name": "TEST_AnalyticsLogs_Project",
            "category_id": 1
        })
        assert project_resp.status_code == 200
        project = project_resp.json()["project"]
        project_id = project["id"]
        project_slug = project["slug"]
        
        # Create script
        script_resp = self.session.post(f"{BASE_URL}/api/projects/{project_id}/scripts", json={
            "name": "TEST_AnalyticsLogs_Script",
            "js_code": "console.log('test analytics');"
        })
        assert script_resp.status_code == 200
        script = script_resp.json()["script"]
        script_slug = script["slug"]
        
        # Generate access logs by making requests to the JS endpoint
        for i in range(3):
            referer_url = f"https://test-domain-{i}.example.com/page{i}.html"
            # Request JS with different referers (all should be denied since no whitelist)
            requests.get(
                f"{BASE_URL}/api/js/{project_slug}/{script_slug}.js",
                headers={"Referer": referer_url}
            )
        
        yield {"project_id": project_id, "project_slug": project_slug, "script": script}
        
        # Cleanup - delete project (cascades to scripts and logs)
        self.session.delete(f"{BASE_URL}/api/projects/{project_id}")
    
    def test_get_analytics_logs_endpoint_returns_200(self, test_project):
        """GET /api/projects/{id}/analytics/logs returns 200"""
        project_id = test_project["project_id"]
        response = self.session.get(f"{BASE_URL}/api/projects/{project_id}/analytics/logs")
        assert response.status_code == 200
    
    def test_analytics_logs_has_summary_stats(self, test_project):
        """Response includes summary with total, allowed, denied counts"""
        project_id = test_project["project_id"]
        response = self.session.get(f"{BASE_URL}/api/projects/{project_id}/analytics/logs")
        data = response.json()
        
        assert "summary" in data
        summary = data["summary"]
        assert "total" in summary
        assert "allowed" in summary
        assert "denied" in summary
        assert isinstance(summary["total"], int)
        assert isinstance(summary["allowed"], int)
        assert isinstance(summary["denied"], int)
    
    def test_analytics_logs_returns_individual_entries(self, test_project):
        """Response includes logs array with individual entries"""
        project_id = test_project["project_id"]
        response = self.session.get(f"{BASE_URL}/api/projects/{project_id}/analytics/logs")
        data = response.json()
        
        assert "logs" in data
        assert isinstance(data["logs"], list)
        assert len(data["logs"]) >= 1, "Expected at least 1 log entry"
    
    def test_log_entry_has_required_fields(self, test_project):
        """Each log entry has: id, referer_url, script_url, script_name, status, requests, last_access"""
        project_id = test_project["project_id"]
        response = self.session.get(f"{BASE_URL}/api/projects/{project_id}/analytics/logs")
        data = response.json()
        logs = data["logs"]
        
        assert len(logs) > 0, "Need logs to test fields"
        log = logs[0]
        
        # Required fields for Analytics table
        assert "id" in log, "Log entry must have 'id' for delete functionality"
        assert "referer_url" in log, "Log entry must have 'referer_url' (Source URL column)"
        assert "script_url" in log, "Log entry must have 'script_url' (Link Script column)"
        assert "script_name" in log, "Log entry must have 'script_name'"
        assert "status" in log, "Log entry must have 'status' (Allowed/Denied)"
        assert "requests" in log, "Log entry must have 'requests' count"
        assert "last_access" in log, "Log entry must have 'last_access'"
    
    def test_log_entry_status_values(self, test_project):
        """Status should be 'allowed' or 'denied'"""
        project_id = test_project["project_id"]
        response = self.session.get(f"{BASE_URL}/api/projects/{project_id}/analytics/logs")
        logs = response.json()["logs"]
        
        for log in logs:
            assert log["status"] in ["allowed", "denied"], f"Invalid status: {log['status']}"
    
    def test_log_entry_id_is_integer(self, test_project):
        """Log entry ID should be an integer for delete operations"""
        project_id = test_project["project_id"]
        response = self.session.get(f"{BASE_URL}/api/projects/{project_id}/analytics/logs")
        logs = response.json()["logs"]
        
        for log in logs:
            assert isinstance(log["id"], int), f"Log ID should be integer, got {type(log['id'])}"
    
    def test_delete_single_log_entry_success(self, test_project):
        """DELETE /api/projects/{id}/logs/{log_id} deletes specific log entry"""
        project_id = test_project["project_id"]
        
        # Get current logs
        response = self.session.get(f"{BASE_URL}/api/projects/{project_id}/analytics/logs")
        logs = response.json()["logs"]
        assert len(logs) > 0, "Need logs to test delete"
        
        initial_count = len(logs)
        log_id_to_delete = logs[0]["id"]
        
        # Delete the log
        delete_response = self.session.delete(f"{BASE_URL}/api/projects/{project_id}/logs/{log_id_to_delete}")
        assert delete_response.status_code == 200
        assert delete_response.json()["message"] == "Log entry deleted"
        
        # Verify log was deleted
        verify_response = self.session.get(f"{BASE_URL}/api/projects/{project_id}/analytics/logs")
        new_logs = verify_response.json()["logs"]
        assert len(new_logs) == initial_count - 1
        
        # Verify the specific ID is no longer present
        remaining_ids = [log["id"] for log in new_logs]
        assert log_id_to_delete not in remaining_ids
    
    def test_delete_non_existent_log_returns_404(self, test_project):
        """DELETE with invalid log_id returns 404"""
        project_id = test_project["project_id"]
        
        # Use a very high ID that shouldn't exist
        response = self.session.delete(f"{BASE_URL}/api/projects/{project_id}/logs/999999")
        assert response.status_code == 404
    
    def test_delete_log_from_wrong_project_returns_404(self, test_project):
        """DELETE log from another project returns 404"""
        project_id = test_project["project_id"]
        
        # Get a log ID from this project
        response = self.session.get(f"{BASE_URL}/api/projects/{project_id}/analytics/logs")
        logs = response.json()["logs"]
        if len(logs) == 0:
            pytest.skip("No logs to test")
        
        log_id = logs[0]["id"]
        
        # Try to delete from a non-existent project
        response = self.session.delete(f"{BASE_URL}/api/projects/999999/logs/{log_id}")
        assert response.status_code == 404
    
    def test_summary_updates_after_delete(self, test_project):
        """Summary counts update correctly after deleting a log"""
        project_id = test_project["project_id"]
        
        # Get initial summary
        response = self.session.get(f"{BASE_URL}/api/projects/{project_id}/analytics/logs")
        data = response.json()
        initial_total = data["summary"]["total"]
        logs = data["logs"]
        
        if len(logs) == 0:
            pytest.skip("No logs to test")
        
        log_to_delete = logs[0]
        log_id = log_to_delete["id"]
        was_allowed = log_to_delete["status"] == "allowed"
        
        # Delete the log
        self.session.delete(f"{BASE_URL}/api/projects/{project_id}/logs/{log_id}")
        
        # Verify summary updated
        response = self.session.get(f"{BASE_URL}/api/projects/{project_id}/analytics/logs")
        new_summary = response.json()["summary"]
        
        assert new_summary["total"] == initial_total - 1
    
    def test_script_url_format_is_correct(self, test_project):
        """script_url should be in format /api/js/{project_slug}/{script_slug}.js"""
        project_id = test_project["project_id"]
        project_slug = test_project["project_slug"]
        
        response = self.session.get(f"{BASE_URL}/api/projects/{project_id}/analytics/logs")
        logs = response.json()["logs"]
        
        for log in logs:
            if log["script_url"]:  # Can be null if script_id is null
                assert log["script_url"].startswith("/api/js/")
                assert log["script_url"].endswith(".js")
    
    def test_analytics_logs_limit_parameter(self, test_project):
        """?limit parameter limits number of returned logs"""
        project_id = test_project["project_id"]
        
        response = self.session.get(f"{BASE_URL}/api/projects/{project_id}/analytics/logs?limit=1")
        assert response.status_code == 200
        logs = response.json()["logs"]
        assert len(logs) <= 1


class TestAnalyticsLogsAuthentication:
    """Test authentication requirements for analytics endpoints"""
    
    def test_get_analytics_logs_requires_auth(self):
        """GET /api/projects/{id}/analytics/logs returns 401/403 without auth"""
        response = requests.get(f"{BASE_URL}/api/projects/1/analytics/logs")
        assert response.status_code in [401, 403], f"Expected 401 or 403, got {response.status_code}"
    
    def test_delete_log_requires_auth(self):
        """DELETE /api/projects/{id}/logs/{log_id} returns 401/403 without auth"""
        response = requests.delete(f"{BASE_URL}/api/projects/1/logs/1")
        assert response.status_code in [401, 403], f"Expected 401 or 403, got {response.status_code}"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
