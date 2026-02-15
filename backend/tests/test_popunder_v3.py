"""
Test file for Popunder V3 Refactor
- Removed whitelist functionality
- New settings: direct_link, timer, interval, devices, countries
- Self-contained JS payload at /api/js/popunder/{slug}.js
"""
import pytest
import requests
import os

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

# Test credentials
ADMIN_EMAIL = "admin@jshost.com"
ADMIN_PASSWORD = "Admin@123"

@pytest.fixture(scope="session")
def api_session():
    """Create requests session"""
    session = requests.Session()
    session.headers.update({"Content-Type": "application/json"})
    return session

@pytest.fixture(scope="session")
def auth_token(api_session):
    """Get admin authentication token"""
    response = api_session.post(f"{BASE_URL}/api/auth/login", json={
        "email": ADMIN_EMAIL,
        "password": ADMIN_PASSWORD
    })
    assert response.status_code == 200, f"Login failed: {response.text}"
    token = response.json().get("token")
    assert token, "No token returned"
    return token

@pytest.fixture(scope="session")
def auth_headers(auth_token):
    """Get headers with auth token"""
    return {"Authorization": f"Bearer {auth_token}", "Content-Type": "application/json"}


class TestPopunderV3CRUD:
    """Test CRUD operations for Popunder campaigns with new V3 settings"""

    def test_list_popunders(self, api_session, auth_headers):
        """Test listing popunder campaigns"""
        response = api_session.get(f"{BASE_URL}/api/popunders", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert "popunders" in data
        print(f"Found {len(data['popunders'])} popunder campaigns")

    def test_create_popunder_with_new_settings(self, api_session, auth_headers):
        """Test creating popunder campaign with new V3 settings schema"""
        payload = {
            "name": "TEST_V3_Campaign",
            "settings": {
                "direct_link": "https://example.com/v3-test-landing",
                "timer": 5,
                "interval": 12,
                "devices": ["desktop", "mobile"],
                "countries": ["US", "GB", "CA"]
            },
            "status": "active"
        }
        response = api_session.post(f"{BASE_URL}/api/popunders", headers=auth_headers, json=payload)
        assert response.status_code == 200, f"Create failed: {response.text}"
        
        data = response.json()
        assert "popunder" in data
        campaign = data["popunder"]
        
        # Verify campaign structure
        assert campaign["name"] == "TEST_V3_Campaign"
        assert campaign["status"] == "active"
        assert "slug" in campaign
        assert "id" in campaign
        
        # Verify settings structure
        settings = campaign["settings"]
        assert settings["direct_link"] == "https://example.com/v3-test-landing"
        assert settings["timer"] == 5
        assert settings["interval"] == 12
        assert "desktop" in settings["devices"]
        assert "mobile" in settings["devices"]
        assert "US" in settings["countries"]
        
        print(f"Created campaign with ID: {campaign['id']}, slug: {campaign['slug']}")
        return campaign["id"]

    def test_get_popunder_with_settings(self, api_session, auth_headers):
        """Test getting a specific popunder campaign shows new settings"""
        # First list to get a campaign ID
        response = api_session.get(f"{BASE_URL}/api/popunders", headers=auth_headers)
        campaigns = response.json()["popunders"]
        
        if not campaigns:
            pytest.skip("No campaigns to test")
        
        campaign_id = campaigns[0]["id"]
        response = api_session.get(f"{BASE_URL}/api/popunders/{campaign_id}", headers=auth_headers)
        assert response.status_code == 200
        
        data = response.json()
        campaign = data["popunder"]
        
        # Verify settings exist
        assert "settings" in campaign
        settings = campaign["settings"]
        
        # Check expected fields exist (may have old or new format)
        print(f"Campaign {campaign_id} settings: {settings}")

    def test_update_popunder_settings(self, api_session, auth_headers):
        """Test updating popunder campaign settings"""
        # Create a test campaign first
        create_payload = {
            "name": "TEST_V3_Update_Campaign",
            "settings": {
                "direct_link": "https://example.com/original",
                "timer": 0,
                "interval": 24,
                "devices": ["desktop"],
                "countries": []
            }
        }
        create_response = api_session.post(f"{BASE_URL}/api/popunders", headers=auth_headers, json=create_payload)
        assert create_response.status_code == 200
        campaign_id = create_response.json()["popunder"]["id"]
        
        # Update settings
        update_payload = {
            "settings": {
                "direct_link": "https://example.com/updated",
                "timer": 10,
                "interval": 48,
                "devices": ["desktop", "mobile", "tablet"],
                "countries": ["US", "DE"]
            }
        }
        response = api_session.patch(f"{BASE_URL}/api/popunders/{campaign_id}", headers=auth_headers, json=update_payload)
        assert response.status_code == 200
        
        updated = response.json()["popunder"]
        settings = updated["settings"]
        
        assert settings["direct_link"] == "https://example.com/updated"
        assert settings["timer"] == 10
        assert settings["interval"] == 48
        assert set(settings["devices"]) == {"desktop", "mobile", "tablet"}
        assert "US" in settings["countries"]
        assert "DE" in settings["countries"]
        
        # Cleanup
        api_session.delete(f"{BASE_URL}/api/popunders/{campaign_id}", headers=auth_headers)
        print(f"Successfully updated and cleaned up campaign {campaign_id}")

    def test_toggle_campaign_status(self, api_session, auth_headers):
        """Test toggling campaign status between active and paused"""
        # Create campaign
        create_response = api_session.post(f"{BASE_URL}/api/popunders", headers=auth_headers, json={
            "name": "TEST_Status_Toggle",
            "settings": {
                "direct_link": "https://example.com/status-test",
                "timer": 0,
                "interval": 24,
                "devices": ["desktop"],
                "countries": []
            },
            "status": "active"
        })
        assert create_response.status_code == 200
        campaign_id = create_response.json()["popunder"]["id"]
        
        # Toggle to paused
        response = api_session.patch(f"{BASE_URL}/api/popunders/{campaign_id}", headers=auth_headers, json={
            "status": "paused"
        })
        assert response.status_code == 200
        assert response.json()["popunder"]["status"] == "paused"
        
        # Toggle back to active
        response = api_session.patch(f"{BASE_URL}/api/popunders/{campaign_id}", headers=auth_headers, json={
            "status": "active"
        })
        assert response.status_code == 200
        assert response.json()["popunder"]["status"] == "active"
        
        # Cleanup
        api_session.delete(f"{BASE_URL}/api/popunders/{campaign_id}", headers=auth_headers)
        print(f"Status toggle test passed for campaign {campaign_id}")

    def test_delete_campaign(self, api_session, auth_headers):
        """Test deleting a popunder campaign"""
        # Create campaign to delete
        create_response = api_session.post(f"{BASE_URL}/api/popunders", headers=auth_headers, json={
            "name": "TEST_To_Delete",
            "settings": {
                "direct_link": "https://example.com/delete-test",
                "timer": 0,
                "interval": 24,
                "devices": ["desktop"],
                "countries": []
            }
        })
        assert create_response.status_code == 200
        campaign_id = create_response.json()["popunder"]["id"]
        
        # Delete
        response = api_session.delete(f"{BASE_URL}/api/popunders/{campaign_id}", headers=auth_headers)
        assert response.status_code == 200
        
        # Verify deleted - should get 404
        get_response = api_session.get(f"{BASE_URL}/api/popunders/{campaign_id}", headers=auth_headers)
        assert get_response.status_code == 404
        print(f"Successfully deleted campaign {campaign_id}")


class TestJSDeliveryEndpoint:
    """Test the public JS delivery endpoint with self-contained payload"""

    def test_js_delivery_returns_javascript(self, api_session, auth_headers):
        """Test that JS delivery endpoint returns valid JavaScript"""
        # Create a campaign
        create_response = api_session.post(f"{BASE_URL}/api/popunders", headers=auth_headers, json={
            "name": "TEST_JS_Delivery",
            "settings": {
                "direct_link": "https://example.com/js-test",
                "timer": 3,
                "interval": 12,
                "devices": ["desktop", "mobile"],
                "countries": []
            },
            "status": "active"
        })
        assert create_response.status_code == 200
        campaign = create_response.json()["popunder"]
        campaign_id = campaign["id"]
        slug = campaign["slug"]
        
        # Get JS (no auth needed - public endpoint)
        response = requests.get(f"{BASE_URL}/api/js/popunder/{slug}.js")
        assert response.status_code == 200
        
        content_type = response.headers.get("content-type", "")
        assert "javascript" in content_type, f"Expected JavaScript content type, got: {content_type}"
        
        js_content = response.text
        
        # Verify it contains campaign config
        assert "url" in js_content or "direct_link" in js_content or "example.com/js-test" in js_content
        assert "timer" in js_content or '"timer":3' in js_content.replace(" ", "")
        assert "interval" in js_content
        assert "devices" in js_content
        
        # Verify it's self-contained (contains the popunder logic)
        assert "function" in js_content.lower()
        assert "openPopunder" in js_content or "popunder" in js_content.lower()
        
        print(f"JS content preview (first 500 chars):\n{js_content[:500]}")
        
        # Cleanup
        api_session.delete(f"{BASE_URL}/api/popunders/{campaign_id}", headers=auth_headers)

    def test_js_delivery_for_paused_campaign(self, api_session, auth_headers):
        """Test that paused campaigns return noop JS"""
        # Create a paused campaign
        create_response = api_session.post(f"{BASE_URL}/api/popunders", headers=auth_headers, json={
            "name": "TEST_Paused_JS",
            "settings": {
                "direct_link": "https://example.com/paused-test",
                "timer": 0,
                "interval": 24,
                "devices": ["desktop"],
                "countries": []
            },
            "status": "paused"
        })
        assert create_response.status_code == 200
        campaign = create_response.json()["popunder"]
        campaign_id = campaign["id"]
        slug = campaign["slug"]
        
        # Get JS
        response = requests.get(f"{BASE_URL}/api/js/popunder/{slug}.js")
        assert response.status_code == 200
        
        js_content = response.text
        
        # Should be noop for paused campaign
        assert "noop" in js_content.lower() or "unauthorized" in js_content.lower()
        
        # Cleanup
        api_session.delete(f"{BASE_URL}/api/popunders/{campaign_id}", headers=auth_headers)
        print("Paused campaign correctly returns noop JS")

    def test_js_delivery_nonexistent_campaign(self, api_session):
        """Test that nonexistent campaigns return noop JS"""
        response = requests.get(f"{BASE_URL}/api/js/popunder/nonexistent-slug-12345.js")
        assert response.status_code == 200
        
        js_content = response.text
        assert "noop" in js_content.lower() or "unauthorized" in js_content.lower()
        print("Nonexistent campaign correctly returns noop JS")


class TestValidation:
    """Test input validation for V3 settings"""

    def test_create_without_direct_link_fails(self, api_session, auth_headers):
        """Test that creating campaign without direct_link fails"""
        payload = {
            "name": "TEST_No_Direct_Link",
            "settings": {
                "direct_link": "",  # Empty direct link
                "timer": 0,
                "interval": 24,
                "devices": ["desktop"],
                "countries": []
            }
        }
        response = api_session.post(f"{BASE_URL}/api/popunders", headers=auth_headers, json=payload)
        assert response.status_code == 400
        print("Correctly rejected empty direct_link")

    def test_create_without_name_fails(self, api_session, auth_headers):
        """Test that creating campaign without name fails"""
        payload = {
            "name": "",
            "settings": {
                "direct_link": "https://example.com",
                "timer": 0,
                "interval": 24,
                "devices": ["desktop"],
                "countries": []
            }
        }
        response = api_session.post(f"{BASE_URL}/api/popunders", headers=auth_headers, json=payload)
        assert response.status_code == 400
        print("Correctly rejected empty name")

    def test_invalid_status_fails(self, api_session, auth_headers):
        """Test that invalid status is rejected"""
        # Create valid campaign first
        create_response = api_session.post(f"{BASE_URL}/api/popunders", headers=auth_headers, json={
            "name": "TEST_Invalid_Status",
            "settings": {
                "direct_link": "https://example.com",
                "timer": 0,
                "interval": 24,
                "devices": ["desktop"],
                "countries": []
            }
        })
        assert create_response.status_code == 200
        campaign_id = create_response.json()["popunder"]["id"]
        
        # Try invalid status
        response = api_session.patch(f"{BASE_URL}/api/popunders/{campaign_id}", headers=auth_headers, json={
            "status": "invalid_status"
        })
        assert response.status_code == 400
        
        # Cleanup
        api_session.delete(f"{BASE_URL}/api/popunders/{campaign_id}", headers=auth_headers)
        print("Correctly rejected invalid status")


class TestCleanup:
    """Clean up test data"""

    def test_cleanup_test_campaigns(self, api_session, auth_headers):
        """Remove all TEST_ prefixed campaigns"""
        response = api_session.get(f"{BASE_URL}/api/popunders", headers=auth_headers)
        campaigns = response.json().get("popunders", [])
        
        deleted_count = 0
        for campaign in campaigns:
            if campaign["name"].startswith("TEST_"):
                del_response = api_session.delete(f"{BASE_URL}/api/popunders/{campaign['id']}", headers=auth_headers)
                if del_response.status_code == 200:
                    deleted_count += 1
        
        print(f"Cleaned up {deleted_count} test campaigns")
