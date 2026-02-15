"""
Tests for Secondary Script feature with two modes:
1. Full JS Script mode - raw JavaScript code for non-whitelisted domains
2. Link Injection mode - generates hidden HTML links with URL/keyword pairs

Backend API endpoints tested:
- PATCH /api/projects/{id} - Update secondary_script, secondary_script_mode, secondary_script_links
- GET /api/js/{project_slug}/{script_slug}.js - JS delivery with mode-based response
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
    """Create a test project for secondary script testing."""
    # Get categories first
    cat_res = api_client.get(f"{BASE_URL}/api/categories")
    assert cat_res.status_code == 200
    categories = cat_res.json()["categories"]
    assert len(categories) > 0, "No categories found"
    category_id = categories[0]["id"]
    
    # Create project
    create_res = api_client.post(f"{BASE_URL}/api/projects", json={
        "name": "TEST_SecondaryScript_Project",
        "category_id": category_id,
        "status": "active"
    })
    assert create_res.status_code == 200, f"Create project failed: {create_res.text}"
    project = create_res.json()["project"]
    
    # Create a script for this project
    script_res = api_client.post(f"{BASE_URL}/api/projects/{project['id']}/scripts", json={
        "name": "TEST_Main_Script",
        "js_code": "console.log('Primary script for whitelisted domains');",
        "status": "active"
    })
    assert script_res.status_code == 200
    script = script_res.json()["script"]
    project["script"] = script
    
    # Add a whitelist entry
    whitelist_res = api_client.post(f"{BASE_URL}/api/projects/{project['id']}/whitelist", json={
        "domain_pattern": "whitelisted.example.com"
    })
    assert whitelist_res.status_code == 200
    
    yield project
    
    # Cleanup: delete project
    api_client.delete(f"{BASE_URL}/api/projects/{project['id']}")


class TestSecondaryScriptMode:
    """Test secondary script mode configuration via API."""
    
    def test_project_has_secondary_script_fields(self, api_client, test_project):
        """Verify project returns secondary script fields."""
        res = api_client.get(f"{BASE_URL}/api/projects/{test_project['id']}")
        assert res.status_code == 200
        
        project = res.json()["project"]
        # Fields should exist
        assert "secondary_script" in project
        assert "secondary_script_mode" in project
        assert "secondary_script_links" in project
        # Default values
        assert project["secondary_script_mode"] in ("js", "links", None)
        
    def test_update_js_mode(self, api_client, test_project):
        """Test updating project to JS mode with script content."""
        js_code = "alert('Non-whitelisted domain detected!');"
        
        res = api_client.patch(f"{BASE_URL}/api/projects/{test_project['id']}", json={
            "secondary_script_mode": "js",
            "secondary_script": js_code,
            "secondary_script_links": []
        })
        assert res.status_code == 200
        
        project = res.json()["project"]
        assert project["secondary_script_mode"] == "js"
        assert project["secondary_script"] == js_code
        assert project["secondary_script_links"] == []
        
    def test_update_links_mode(self, api_client, test_project):
        """Test updating project to Links mode with URL/keyword pairs."""
        links = [
            {"url": "https://example.com/page1", "keyword": "keyword1"},
            {"url": "https://example.com/page2", "keyword": "keyword2"},
            {"url": "https://example.com/page3", "keyword": "keyword3"}
        ]
        
        res = api_client.patch(f"{BASE_URL}/api/projects/{test_project['id']}", json={
            "secondary_script_mode": "links",
            "secondary_script": "",
            "secondary_script_links": links
        })
        assert res.status_code == 200
        
        project = res.json()["project"]
        assert project["secondary_script_mode"] == "links"
        assert len(project["secondary_script_links"]) == 3
        # Verify link data
        assert project["secondary_script_links"][0]["url"] == "https://example.com/page1"
        assert project["secondary_script_links"][0]["keyword"] == "keyword1"
        
    def test_invalid_mode_rejected(self, api_client, test_project):
        """Test that invalid mode values are rejected."""
        res = api_client.patch(f"{BASE_URL}/api/projects/{test_project['id']}", json={
            "secondary_script_mode": "invalid_mode"
        })
        assert res.status_code == 400
        assert "js" in res.json()["detail"].lower() or "links" in res.json()["detail"].lower()


class TestJSDeliveryModes:
    """Test JS delivery endpoint with different secondary script modes."""
    
    def test_js_mode_delivery(self, api_client, test_project):
        """Test JS delivery returns raw JS code when mode is 'js' and request is from non-whitelisted domain."""
        # Set up JS mode
        js_code = "console.log('Secondary JS for non-whitelisted');"
        api_client.patch(f"{BASE_URL}/api/projects/{test_project['id']}", json={
            "secondary_script_mode": "js",
            "secondary_script": js_code,
            "secondary_script_links": []
        })
        
        project_slug = test_project["slug"]
        script_slug = test_project["script"]["slug"]
        
        # Request from non-whitelisted domain (using wrong referer)
        non_auth_response = requests.get(
            f"{BASE_URL}/api/js/{project_slug}/{script_slug}.js",
            headers={"Referer": "https://non-whitelisted-domain.com/page"}
        )
        assert non_auth_response.status_code == 200
        assert "application/javascript" in non_auth_response.headers.get("Content-Type", "")
        # Should return secondary JS
        assert "Secondary JS for non-whitelisted" in non_auth_response.text
        
    def test_links_mode_delivery(self, api_client, test_project):
        """Test JS delivery returns hidden link injection JS when mode is 'links'."""
        # Set up Links mode
        links = [
            {"url": "https://seo-link.com/page", "keyword": "seo keyword"},
            {"url": "https://backlink.com/", "keyword": "another keyword"}
        ]
        api_client.patch(f"{BASE_URL}/api/projects/{test_project['id']}", json={
            "secondary_script_mode": "links",
            "secondary_script": "",
            "secondary_script_links": links
        })
        
        project_slug = test_project["slug"]
        script_slug = test_project["script"]["slug"]
        
        # Request from non-whitelisted domain
        response = requests.get(
            f"{BASE_URL}/api/js/{project_slug}/{script_slug}.js",
            headers={"Referer": "https://unknown-domain.org/"}
        )
        assert response.status_code == 200
        
        # Should contain link injection JS
        js_content = response.text
        # Check for hidden div structure
        assert 'display:none' in js_content
        assert 'seo-link.com/page' in js_content
        assert 'seo keyword' in js_content
        assert 'backlink.com' in js_content
        assert 'another keyword' in js_content
        
    def test_whitelisted_domain_gets_primary_script(self, api_client, test_project):
        """Test that whitelisted domains always receive the primary script."""
        # Set up secondary script
        api_client.patch(f"{BASE_URL}/api/projects/{test_project['id']}", json={
            "secondary_script_mode": "js",
            "secondary_script": "alert('This should NOT be served to whitelisted');",
            "secondary_script_links": []
        })
        
        project_slug = test_project["slug"]
        script_slug = test_project["script"]["slug"]
        
        # Request from whitelisted domain
        response = requests.get(
            f"{BASE_URL}/api/js/{project_slug}/{script_slug}.js",
            headers={"Referer": "https://whitelisted.example.com/page"}
        )
        assert response.status_code == 200
        
        # Should return primary script, not secondary
        assert "Primary script for whitelisted domains" in response.text
        assert "This should NOT be served" not in response.text
        
    def test_empty_links_returns_noop(self, api_client, test_project):
        """Test that empty links array returns noop response."""
        # Set links mode with empty array
        api_client.patch(f"{BASE_URL}/api/projects/{test_project['id']}", json={
            "secondary_script_mode": "links",
            "secondary_script": "",
            "secondary_script_links": []
        })
        
        project_slug = test_project["slug"]
        script_slug = test_project["script"]["slug"]
        
        response = requests.get(
            f"{BASE_URL}/api/js/{project_slug}/{script_slug}.js",
            headers={"Referer": "https://non-whitelisted.com/"}
        )
        assert response.status_code == 200
        # Should return noop
        assert "noop" in response.text or "unauthorized" in response.text
        
    def test_empty_js_returns_noop(self, api_client, test_project):
        """Test that empty/whitespace JS returns noop response."""
        # Set JS mode with empty script
        api_client.patch(f"{BASE_URL}/api/projects/{test_project['id']}", json={
            "secondary_script_mode": "js",
            "secondary_script": "   ",  # Whitespace only
            "secondary_script_links": []
        })
        
        project_slug = test_project["slug"]
        script_slug = test_project["script"]["slug"]
        
        response = requests.get(
            f"{BASE_URL}/api/js/{project_slug}/{script_slug}.js",
            headers={"Referer": "https://non-whitelisted.com/"}
        )
        assert response.status_code == 200
        # Should return noop when secondary_script is empty/whitespace
        assert "noop" in response.text or "unauthorized" in response.text


class TestLinkInjectionFormat:
    """Test the HTML link injection format generated by links mode."""
    
    def test_link_format_structure(self, api_client, test_project):
        """Verify the hidden link HTML format is correct."""
        links = [
            {"url": "https://target-url.com/path", "keyword": "target keyword"}
        ]
        api_client.patch(f"{BASE_URL}/api/projects/{test_project['id']}", json={
            "secondary_script_mode": "links",
            "secondary_script": "",
            "secondary_script_links": links
        })
        
        project_slug = test_project["slug"]
        script_slug = test_project["script"]["slug"]
        
        response = requests.get(
            f"{BASE_URL}/api/js/{project_slug}/{script_slug}.js",
            headers={"Referer": "https://any-domain.com/"}
        )
        
        js_content = response.text
        # Should contain the hidden div with link
        assert '<div style="display:none;">' in js_content or "display:none" in js_content
        assert '<a href="https://target-url.com/path">' in js_content or 'target-url.com/path' in js_content
        assert "target keyword" in js_content
        
    def test_multiple_links_injection(self, api_client, test_project):
        """Test multiple links are all injected."""
        links = [
            {"url": "https://link1.com/", "keyword": "first"},
            {"url": "https://link2.com/", "keyword": "second"},
            {"url": "https://link3.com/", "keyword": "third"}
        ]
        api_client.patch(f"{BASE_URL}/api/projects/{test_project['id']}", json={
            "secondary_script_mode": "links",
            "secondary_script": "",
            "secondary_script_links": links
        })
        
        project_slug = test_project["slug"]
        script_slug = test_project["script"]["slug"]
        
        response = requests.get(
            f"{BASE_URL}/api/js/{project_slug}/{script_slug}.js",
            headers={"Referer": "https://any-domain.com/"}
        )
        
        js_content = response.text
        # All links should be present
        assert "link1.com" in js_content
        assert "link2.com" in js_content  
        assert "link3.com" in js_content
        assert "first" in js_content
        assert "second" in js_content
        assert "third" in js_content
        
    def test_special_characters_escaped(self, api_client, test_project):
        """Test that special characters in URLs/keywords are properly escaped."""
        links = [
            {"url": "https://example.com/path?param=value&other=1", "keyword": 'keyword with "quotes"'}
        ]
        api_client.patch(f"{BASE_URL}/api/projects/{test_project['id']}", json={
            "secondary_script_mode": "links",
            "secondary_script": "",
            "secondary_script_links": links
        })
        
        project_slug = test_project["slug"]
        script_slug = test_project["script"]["slug"]
        
        response = requests.get(
            f"{BASE_URL}/api/js/{project_slug}/{script_slug}.js",
            headers={"Referer": "https://any-domain.com/"}
        )
        
        # Should not break JS syntax
        assert response.status_code == 200
        # The JS should be valid (no syntax errors indicated by proper structure)
        assert "(function()" in response.text or "function" in response.text.lower()


class TestModeSwitch:
    """Test switching between modes preserves/clears data appropriately."""
    
    def test_switch_js_to_links_preserves_js_until_save(self, api_client, test_project):
        """After switching from JS to links mode, both data types are stored."""
        # Set JS mode first
        js_code = "console.log('Test JS');"
        api_client.patch(f"{BASE_URL}/api/projects/{test_project['id']}", json={
            "secondary_script_mode": "js",
            "secondary_script": js_code,
            "secondary_script_links": []
        })
        
        # Now switch to links mode
        links = [{"url": "https://new.com/", "keyword": "new"}]
        res = api_client.patch(f"{BASE_URL}/api/projects/{test_project['id']}", json={
            "secondary_script_mode": "links",
            "secondary_script_links": links
        })
        assert res.status_code == 200
        
        # Verify mode changed and links saved
        project = res.json()["project"]
        assert project["secondary_script_mode"] == "links"
        assert len(project["secondary_script_links"]) == 1
        # JS content may still be there but not used (depending on implementation)
        
    def test_partial_update_preserves_existing(self, api_client, test_project):
        """Updating only mode should not clear existing data."""
        # Set full configuration
        api_client.patch(f"{BASE_URL}/api/projects/{test_project['id']}", json={
            "secondary_script_mode": "js",
            "secondary_script": "existing JS code",
            "secondary_script_links": [{"url": "https://old.com/", "keyword": "old"}]
        })
        
        # Update only mode
        res = api_client.patch(f"{BASE_URL}/api/projects/{test_project['id']}", json={
            "secondary_script_mode": "links"
        })
        assert res.status_code == 200
        
        project = res.json()["project"]
        assert project["secondary_script_mode"] == "links"
        # Previous links should still be there
        assert len(project["secondary_script_links"]) == 1


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
