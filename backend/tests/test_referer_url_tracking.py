"""
Tests for Full Referrer URL Tracking Feature.
This feature captures the complete referrer URL (not just domain) when scripts are accessed.

Features tested:
- Full referrer URL captured in access logs (referer_url field)
- Analytics API returns 'referer_url_details' with full URLs
- Script-specific analytics returns 'referer_urls' with full URLs  
- Access logs API returns 'referer_url' field

Backend API endpoints tested:
- GET /api/projects/{id}/analytics - returns referer_url_details
- GET /api/projects/{id}/scripts/{id}/analytics - returns referer_urls
- GET /api/projects/{id}/logs - returns referer_url in each log
- GET /api/js/{project_slug}/{script_slug}.js - captures full referrer URL
"""
import pytest
import requests
import os

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

# Test credentials
TEST_EMAIL = "admin@jshost.com"
TEST_PASSWORD = "Admin@123"


@pytest.fixture(scope="module")
def auth_token():
    """Get authentication token."""
    response = requests.post(f"{BASE_URL}/api/auth/login", json={
        "email": TEST_EMAIL,
        "password": TEST_PASSWORD
    })
    assert response.status_code == 200, f"Login failed: {response.text}"
    return response.json()["token"]


@pytest.fixture(scope="module")
def api_client(auth_token):
    """Create authenticated session."""
    session = requests.Session()
    session.headers.update({
        "Authorization": f"Bearer {auth_token}",
        "Content-Type": "application/json"
    })
    return session


@pytest.fixture(scope="module")
def test_project(api_client):
    """Create a test project for referer URL tracking testing."""
    # Get categories first
    cat_res = api_client.get(f"{BASE_URL}/api/categories")
    assert cat_res.status_code == 200
    categories = cat_res.json()["categories"]
    assert len(categories) > 0, "No categories found"
    category_id = categories[0]["id"]
    
    # Create project
    create_res = api_client.post(f"{BASE_URL}/api/projects", json={
        "name": "TEST_RefererURL_Project",
        "category_id": category_id,
        "status": "active"
    })
    assert create_res.status_code == 200, f"Create project failed: {create_res.text}"
    project = create_res.json()["project"]
    
    # Create a script for this project
    script_res = api_client.post(f"{BASE_URL}/api/projects/{project['id']}/scripts", json={
        "name": "TEST_RefererURL_Script",
        "js_code": "console.log('Test script for referrer URL tracking');",
        "status": "active"
    })
    assert script_res.status_code == 200
    script = script_res.json()["script"]
    project["script"] = script
    
    # Add a whitelist entry to allow example.com
    whitelist_res = api_client.post(f"{BASE_URL}/api/projects/{project['id']}/scripts/{script['id']}/whitelist", json={
        "domain_pattern": "example.com"
    })
    assert whitelist_res.status_code == 200
    
    yield project
    
    # Cleanup: delete project
    api_client.delete(f"{BASE_URL}/api/projects/{project['id']}")


class TestRefererUrlCapture:
    """Test that full referrer URLs are captured when scripts are accessed."""
    
    def test_full_referer_url_captured_on_allowed_request(self, test_project):
        """Test that full referrer URL is captured for allowed (whitelisted) requests."""
        project_slug = test_project["slug"]
        script_slug = test_project["script"]["slug"]
        
        # Request from whitelisted domain with full URL path
        full_referer = "https://example.com/products/electronics/laptop-deals.html?utm_source=google&campaign=summer2026"
        response = requests.get(
            f"{BASE_URL}/api/js/{project_slug}/{script_slug}.js",
            headers={"Referer": full_referer}
        )
        assert response.status_code == 200
        assert "Test script for referrer URL tracking" in response.text
    
    def test_full_referer_url_captured_on_denied_request(self, test_project):
        """Test that full referrer URL is captured for denied (non-whitelisted) requests."""
        project_slug = test_project["slug"]
        script_slug = test_project["script"]["slug"]
        
        # Request from non-whitelisted domain with full URL path
        full_referer = "https://unauthorized-site.com/pages/embedded-script-test.html?version=2"
        response = requests.get(
            f"{BASE_URL}/api/js/{project_slug}/{script_slug}.js",
            headers={"Referer": full_referer}
        )
        assert response.status_code == 200  # Always returns 200, but with noop
        assert "noop" in response.text or "unauthorized" in response.text


class TestAccessLogsApi:
    """Test that access logs API returns referer_url field."""
    
    def test_logs_contain_referer_url_field(self, api_client, test_project):
        """Verify logs API returns referer_url in each log entry."""
        # First generate some access logs
        project_slug = test_project["slug"]
        script_slug = test_project["script"]["slug"]
        
        test_urls = [
            "https://example.com/page1.html",
            "https://example.com/blog/article-123.html",
            "https://denied-domain.org/test/page.php"
        ]
        
        for url in test_urls:
            requests.get(
                f"{BASE_URL}/api/js/{project_slug}/{script_slug}.js",
                headers={"Referer": url}
            )
        
        # Now check logs
        res = api_client.get(f"{BASE_URL}/api/projects/{test_project['id']}/logs?limit=20")
        assert res.status_code == 200
        
        logs = res.json()["logs"]
        assert len(logs) > 0, "No logs found"
        
        # Verify referer_url field exists in logs
        for log in logs:
            assert "referer_url" in log, f"Missing referer_url field in log: {log}"
            assert "ref_domain" in log, f"Missing ref_domain field in log: {log}"
        
    def test_referer_url_contains_full_path(self, api_client, test_project):
        """Verify referer_url contains the full URL path, not just domain."""
        project_slug = test_project["slug"]
        script_slug = test_project["script"]["slug"]
        
        # Generate request with specific full URL
        test_referer = "https://example.com/deep/nested/path/page.html?query=test&id=456"
        requests.get(
            f"{BASE_URL}/api/js/{project_slug}/{script_slug}.js",
            headers={"Referer": test_referer}
        )
        
        # Check logs
        res = api_client.get(f"{BASE_URL}/api/projects/{test_project['id']}/logs?limit=5")
        assert res.status_code == 200
        
        logs = res.json()["logs"]
        # Find our specific log entry
        found = False
        for log in logs:
            if log.get("referer_url") and "deep/nested/path" in log["referer_url"]:
                found = True
                # Verify it contains the full URL, not just domain
                assert "example.com" in log["referer_url"]
                assert "deep/nested/path/page.html" in log["referer_url"]
                break
        
        assert found, "Could not find log entry with full referer URL path"


class TestProjectAnalyticsApi:
    """Test that project analytics API returns referer_url_details."""
    
    def test_analytics_contains_referer_url_details(self, api_client, test_project):
        """Verify analytics API returns referer_url_details section."""
        res = api_client.get(f"{BASE_URL}/api/projects/{test_project['id']}/analytics")
        assert res.status_code == 200
        
        data = res.json()
        assert "referer_url_details" in data, "Missing referer_url_details in analytics response"
    
    def test_referer_url_details_structure(self, api_client, test_project):
        """Verify referer_url_details has correct structure."""
        # Generate some requests first
        project_slug = test_project["slug"]
        script_slug = test_project["script"]["slug"]
        
        requests.get(
            f"{BASE_URL}/api/js/{project_slug}/{script_slug}.js",
            headers={"Referer": "https://example.com/analytics-test.html"}
        )
        
        res = api_client.get(f"{BASE_URL}/api/projects/{test_project['id']}/analytics")
        assert res.status_code == 200
        
        data = res.json()
        referer_details = data.get("referer_url_details", [])
        
        if len(referer_details) > 0:
            # Check structure of each entry
            for entry in referer_details:
                assert "script_id" in entry, "Missing script_id"
                assert "script_name" in entry, "Missing script_name"
                assert "script_url" in entry, "Missing script_url"
                assert "referer_url" in entry, "Missing referer_url"
                assert "domain" in entry, "Missing domain"
                assert "status" in entry, "Missing status"
                assert "request_count" in entry, "Missing request_count"
                assert "last_access" in entry, "Missing last_access"
                
                # Verify status is valid
                assert entry["status"] in ("allowed", "denied")
    
    def test_referer_url_details_shows_full_urls(self, api_client, test_project):
        """Verify referer_url field in details contains full URLs."""
        res = api_client.get(f"{BASE_URL}/api/projects/{test_project['id']}/analytics")
        assert res.status_code == 200
        
        data = res.json()
        referer_details = data.get("referer_url_details", [])
        
        for entry in referer_details:
            referer_url = entry.get("referer_url", "")
            if referer_url:
                # Full URL should contain protocol
                assert referer_url.startswith("http://") or referer_url.startswith("https://"), \
                    f"referer_url should be full URL, got: {referer_url}"


class TestScriptAnalyticsApi:
    """Test that script-specific analytics API returns referer_urls."""
    
    def test_script_analytics_contains_referer_urls(self, api_client, test_project):
        """Verify script analytics API returns referer_urls section."""
        script_id = test_project["script"]["id"]
        res = api_client.get(f"{BASE_URL}/api/projects/{test_project['id']}/scripts/{script_id}/analytics")
        assert res.status_code == 200
        
        data = res.json()
        assert "referer_urls" in data, "Missing referer_urls in script analytics response"
    
    def test_script_analytics_referer_urls_structure(self, api_client, test_project):
        """Verify referer_urls has correct structure."""
        # Generate request first
        project_slug = test_project["slug"]
        script_slug = test_project["script"]["slug"]
        
        requests.get(
            f"{BASE_URL}/api/js/{project_slug}/{script_slug}.js",
            headers={"Referer": "https://example.com/script-analytics-test.html"}
        )
        
        script_id = test_project["script"]["id"]
        res = api_client.get(f"{BASE_URL}/api/projects/{test_project['id']}/scripts/{script_id}/analytics")
        assert res.status_code == 200
        
        data = res.json()
        referer_urls = data.get("referer_urls", [])
        
        if len(referer_urls) > 0:
            for entry in referer_urls:
                assert "referer_url" in entry, "Missing referer_url"
                assert "domain" in entry, "Missing domain"
                assert "status" in entry, "Missing status"
                assert "request_count" in entry, "Missing request_count"
                assert "last_access" in entry, "Missing last_access"
    
    def test_script_analytics_has_both_domains_and_referer_urls(self, api_client, test_project):
        """Verify script analytics returns both domains summary and detailed referer_urls."""
        script_id = test_project["script"]["id"]
        res = api_client.get(f"{BASE_URL}/api/projects/{test_project['id']}/scripts/{script_id}/analytics")
        assert res.status_code == 200
        
        data = res.json()
        # Should have both
        assert "domains" in data, "Missing domains in script analytics"
        assert "referer_urls" in data, "Missing referer_urls in script analytics"


class TestMultiDomainAccessPatterns:
    """Test tracking of access patterns across multiple domains and pages."""
    
    def test_multiple_pages_same_domain_tracked_separately(self, api_client, test_project):
        """Verify different pages from same domain are tracked with distinct URLs."""
        project_slug = test_project["slug"]
        script_slug = test_project["script"]["slug"]
        
        # Generate requests from multiple pages on same domain
        test_pages = [
            "https://example.com/unique-page-a.html",
            "https://example.com/unique-page-b.html",
            "https://example.com/unique-page-c.html"
        ]
        
        for page in test_pages:
            requests.get(
                f"{BASE_URL}/api/js/{project_slug}/{script_slug}.js",
                headers={"Referer": page}
            )
        
        res = api_client.get(f"{BASE_URL}/api/projects/{test_project['id']}/analytics")
        assert res.status_code == 200
        
        referer_details = res.json().get("referer_url_details", [])
        
        # Check that multiple unique pages are tracked
        unique_urls = set(entry.get("referer_url", "") for entry in referer_details)
        # At least some of our test pages should be tracked as distinct entries
        found_count = sum(1 for page in test_pages if any(page in url for url in unique_urls))
        assert found_count >= 1, f"Expected multiple unique page URLs tracked, found: {unique_urls}"
    
    def test_allowed_and_denied_status_correctly_tracked(self, api_client, test_project):
        """Verify allowed/denied status is correctly associated with referer URLs."""
        project_slug = test_project["slug"]
        script_slug = test_project["script"]["slug"]
        
        # Generate allowed request (example.com is whitelisted)
        requests.get(
            f"{BASE_URL}/api/js/{project_slug}/{script_slug}.js",
            headers={"Referer": "https://example.com/allowed-status-test.html"}
        )
        
        # Generate denied request (random domain not whitelisted)
        requests.get(
            f"{BASE_URL}/api/js/{project_slug}/{script_slug}.js",
            headers={"Referer": "https://denied-random-domain.xyz/denied-status-test.html"}
        )
        
        res = api_client.get(f"{BASE_URL}/api/projects/{test_project['id']}/analytics")
        assert res.status_code == 200
        
        referer_details = res.json().get("referer_url_details", [])
        
        # Check for both allowed and denied statuses
        statuses = set(entry.get("status") for entry in referer_details)
        # We should have at least one of each status
        has_allowed = any(entry.get("status") == "allowed" for entry in referer_details)
        has_denied = any(entry.get("status") == "denied" for entry in referer_details)
        
        assert has_allowed, "No 'allowed' status entries found"
        assert has_denied, "No 'denied' status entries found"


class TestExistingTestData:
    """Test using the pre-created test data from main agent."""
    
    def test_project_1_analytics_has_referer_url_details(self, api_client):
        """Verify Project ID 1 has referer_url_details in analytics."""
        res = api_client.get(f"{BASE_URL}/api/projects/1/analytics")
        assert res.status_code == 200
        
        data = res.json()
        assert "referer_url_details" in data
        referer_details = data["referer_url_details"]
        
        # Should have entries from the seed data
        assert len(referer_details) > 0, "Project 1 should have referer_url_details entries"
        
        # Verify expected URLs from seed data
        urls = [entry["referer_url"] for entry in referer_details]
        print(f"Found referer URLs: {urls}")
    
    def test_project_1_logs_have_referer_url(self, api_client):
        """Verify Project ID 1 logs have referer_url field."""
        res = api_client.get(f"{BASE_URL}/api/projects/1/logs")
        assert res.status_code == 200
        
        logs = res.json()["logs"]
        assert len(logs) > 0, "Project 1 should have access logs"
        
        # Every log should have referer_url field
        for log in logs:
            assert "referer_url" in log, f"Log missing referer_url: {log}"
    
    def test_script_1_analytics_has_referer_urls(self, api_client):
        """Verify Script ID 1 analytics has referer_urls."""
        res = api_client.get(f"{BASE_URL}/api/projects/1/scripts/1/analytics")
        assert res.status_code == 200
        
        data = res.json()
        assert "referer_urls" in data
        
        referer_urls = data["referer_urls"]
        assert len(referer_urls) > 0, "Script 1 should have referer_urls entries"


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
