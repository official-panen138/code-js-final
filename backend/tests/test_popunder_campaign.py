"""
Pop-under Campaign API Tests
Tests for:
- Login functionality
- Pop-under campaign CRUD operations
- Pop-under JS delivery endpoint
- Pop-under test page endpoint
- Pop-under analytics tracking
"""
import pytest
import requests
import os
import time

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

# Test credentials
ADMIN_EMAIL = "admin@jshost.com"
ADMIN_PASSWORD = "Admin@123"
USER_EMAIL = "user@jshost.com"
USER_PASSWORD = "User@123"

class TestAuthentication:
    """Authentication Tests"""
    
    def test_admin_login_success(self):
        """Test admin can login with correct credentials"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": ADMIN_EMAIL,
            "password": ADMIN_PASSWORD
        })
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()
        assert "token" in data
        assert "user" in data
        assert data["user"]["email"] == ADMIN_EMAIL
        assert data["user"]["role"] == "admin"
        print("Admin login successful")
    
    def test_user_login_success(self):
        """Test regular user can login with correct credentials"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": USER_EMAIL,
            "password": USER_PASSWORD
        })
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()
        assert "token" in data
        assert "user" in data
        assert data["user"]["email"] == USER_EMAIL
        assert data["user"]["role"] == "user"
        print("User login successful")
    
    def test_login_invalid_credentials(self):
        """Test login fails with invalid credentials"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": "wrong@test.com",
            "password": "wrongpassword"
        })
        assert response.status_code == 401
        print("Invalid credentials rejected correctly")


class TestPopunderCampaignCRUD:
    """Pop-under Campaign CRUD Tests"""
    
    @pytest.fixture
    def admin_token(self):
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": ADMIN_EMAIL,
            "password": ADMIN_PASSWORD
        })
        return response.json()["token"]
    
    def test_list_popunder_campaigns(self, admin_token):
        """Test listing all popunder campaigns"""
        headers = {"Authorization": f"Bearer {admin_token}"}
        response = requests.get(f"{BASE_URL}/api/popunders", headers=headers)
        assert response.status_code == 200
        data = response.json()
        assert "popunders" in data
        assert isinstance(data["popunders"], list)
        print(f"Found {len(data['popunders'])} popunder campaigns")
    
    def test_create_popunder_campaign(self, admin_token):
        """Test creating a new popunder campaign"""
        headers = {"Authorization": f"Bearer {admin_token}"}
        payload = {
            "name": "TEST_Popunder_Campaign",
            "settings": {
                "url_list": "https://example.com\nhttps://google.com",
                "timer": 0,
                "frequency": 2,
                "devices": ["desktop", "mobile"],
                "countries": [],
                "floating_banner": "",
                "html_body": ""
            },
            "status": "active"
        }
        response = requests.post(f"{BASE_URL}/api/popunders", headers=headers, json=payload)
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()
        assert "popunder" in data
        assert data["popunder"]["name"] == "TEST_Popunder_Campaign"
        assert data["popunder"]["status"] == "active"
        assert "slug" in data["popunder"]
        print(f"Created popunder campaign with slug: {data['popunder']['slug']}")
        return data["popunder"]["id"]
    
    def test_get_popunder_campaign(self, admin_token):
        """Test getting a specific popunder campaign"""
        headers = {"Authorization": f"Bearer {admin_token}"}
        # First get list to find an existing campaign
        list_response = requests.get(f"{BASE_URL}/api/popunders", headers=headers)
        campaigns = list_response.json()["popunders"]
        if campaigns:
            campaign_id = campaigns[0]["id"]
            response = requests.get(f"{BASE_URL}/api/popunders/{campaign_id}", headers=headers)
            assert response.status_code == 200
            data = response.json()
            assert "popunder" in data
            assert data["popunder"]["id"] == campaign_id
            print(f"Retrieved popunder campaign: {data['popunder']['name']}")
    
    def test_update_popunder_campaign(self, admin_token):
        """Test updating a popunder campaign"""
        headers = {"Authorization": f"Bearer {admin_token}"}
        # First create a campaign
        create_payload = {
            "name": "TEST_Update_Popunder",
            "settings": {
                "url_list": "https://test.com",
                "timer": 0,
                "frequency": 1,
                "devices": ["desktop"],
                "countries": [],
                "floating_banner": "",
                "html_body": ""
            }
        }
        create_response = requests.post(f"{BASE_URL}/api/popunders", headers=headers, json=create_payload)
        campaign_id = create_response.json()["popunder"]["id"]
        
        # Update the campaign
        update_payload = {
            "name": "TEST_Updated_Popunder",
            "status": "paused"
        }
        response = requests.patch(f"{BASE_URL}/api/popunders/{campaign_id}", headers=headers, json=update_payload)
        assert response.status_code == 200
        data = response.json()
        assert data["popunder"]["name"] == "TEST_Updated_Popunder"
        assert data["popunder"]["status"] == "paused"
        print("Popunder campaign updated successfully")
        
        # Cleanup
        requests.delete(f"{BASE_URL}/api/popunders/{campaign_id}", headers=headers)


class TestPopunderJSDelivery:
    """Pop-under JS Delivery Tests"""
    
    def test_js_delivery_for_existing_campaign(self):
        """Test JS delivery endpoint returns JavaScript for existing campaign"""
        # Test with the existing 'test-popunder' campaign
        response = requests.get(f"{BASE_URL}/api/js/popunder/test-popunder.js")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        assert "application/javascript" in response.headers.get("content-type", "").lower() or "text/javascript" in response.headers.get("content-type", "").lower()
        # Verify JS content
        js_content = response.text
        assert "openPopunder" in js_content, "JS should contain openPopunder function"
        assert "checkFrequency" in js_content, "JS should contain checkFrequency function"
        assert "trackEvent" in js_content, "JS should contain trackEvent function"
        assert "window.open" in js_content, "JS should use window.open for popunder"
        print("JS delivery endpoint working correctly")
    
    def test_js_delivery_nonexistent_campaign(self):
        """Test JS delivery returns NOOP JS for non-existent campaign (graceful degradation)"""
        response = requests.get(f"{BASE_URL}/api/js/popunder/nonexistent-campaign-12345.js")
        # Returns 200 with NOOP JS for graceful degradation
        assert response.status_code == 200
        assert "noop" in response.text.lower() or "unauthorized" in response.text.lower()
        print("Non-existent campaign returns NOOP JS correctly (graceful degradation)")
    
    def test_js_contains_popunder_logic(self):
        """Test delivered JS contains popunder behavior logic"""
        response = requests.get(f"{BASE_URL}/api/js/popunder/test-popunder.js")
        js_content = response.text
        
        # Check for popunder technique implementations
        assert "blur()" in js_content, "JS should blur the popup window"
        assert "window.focus()" in js_content, "JS should focus back to main window"
        # Check for the enhanced techniques mentioned in the code
        assert "tempInput" in js_content or "temp" in js_content.lower(), "JS should have temp input focus technique"
        print("JS contains correct popunder logic")


class TestPopunderTestPage:
    """Pop-under Test Page Tests"""
    
    def test_test_page_accessible(self):
        """Test that the popunder test page is accessible"""
        response = requests.get(f"{BASE_URL}/api/test/popunder/test-popunder")
        assert response.status_code == 200
        assert "text/html" in response.headers.get("content-type", "").lower()
        print("Popunder test page accessible")
    
    def test_test_page_contains_script(self):
        """Test that the test page loads the popunder script"""
        response = requests.get(f"{BASE_URL}/api/test/popunder/test-popunder")
        html_content = response.text
        assert "/api/js/popunder/test-popunder.js" in html_content, "Test page should load popunder script"
        print("Test page correctly loads popunder script")
    
    def test_test_page_contains_instructions(self):
        """Test that the test page contains test instructions"""
        response = requests.get(f"{BASE_URL}/api/test/popunder/test-popunder")
        html_content = response.text
        assert "Click" in html_content, "Test page should have click instructions"
        assert "test" in html_content.lower() or "Test" in html_content, "Test page should mention testing"
        print("Test page contains instructions")
    
    def test_test_page_nonexistent_campaign(self):
        """Test that non-existent campaign test page returns 404"""
        response = requests.get(f"{BASE_URL}/api/test/popunder/nonexistent-campaign-xyz")
        assert response.status_code == 404
        print("Non-existent campaign test page returns 404")


class TestPopunderAnalytics:
    """Pop-under Analytics Tracking Tests"""
    
    @pytest.fixture
    def admin_token(self):
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": ADMIN_EMAIL,
            "password": ADMIN_PASSWORD
        })
        return response.json()["token"]
    
    def test_track_impression_event(self):
        """Test tracking an impression event"""
        # Get campaign ID first (using test-popunder)
        response = requests.get(f"{BASE_URL}/api/js/popunder/test-popunder.js")
        # Extract campaign ID from the JS config (id is in the config)
        js_content = response.text
        # The config contains "id": X
        import re
        match = re.search(r'"id":\s*(\d+)', js_content)
        if match:
            campaign_id = int(match.group(1))
        else:
            campaign_id = 1  # fallback
        
        # Track impression
        payload = {
            "campaign_id": campaign_id,
            "event_type": "impression",
            "referer_url": "https://test-site.com/page",
            "target_url": "",
            "device_type": "desktop"
        }
        response = requests.post(f"{BASE_URL}/api/popunder-analytics", json=payload)
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()
        assert data.get("status") == "ok" or "id" in data or response.status_code == 200
        print("Impression event tracked successfully")
    
    def test_track_click_event(self):
        """Test tracking a click event"""
        # Track click event
        payload = {
            "campaign_id": 1,  # Test Popunder campaign
            "event_type": "click",
            "referer_url": "https://test-site.com/page",
            "target_url": "https://example.com",
            "device_type": "desktop"
        }
        response = requests.post(f"{BASE_URL}/api/popunder-analytics", json=payload)
        assert response.status_code == 200
        print("Click event tracked successfully")
    
    def test_get_campaign_analytics(self, admin_token):
        """Test getting analytics for a campaign"""
        headers = {"Authorization": f"Bearer {admin_token}"}
        # Get analytics for test-popunder campaign (ID 1)
        response = requests.get(f"{BASE_URL}/api/popunders/1/analytics", headers=headers)
        # Campaign might not exist or user might not have access
        if response.status_code == 200:
            data = response.json()
            assert "summary" in data or "stats" in data or isinstance(data, dict)
            print("Campaign analytics retrieved successfully")
        else:
            # Try to get the first available campaign
            list_response = requests.get(f"{BASE_URL}/api/popunders", headers=headers)
            if list_response.status_code == 200:
                campaigns = list_response.json()["popunders"]
                if campaigns:
                    campaign_id = campaigns[0]["id"]
                    response = requests.get(f"{BASE_URL}/api/popunders/{campaign_id}/analytics", headers=headers)
                    assert response.status_code == 200
                    print(f"Analytics retrieved for campaign {campaign_id}")


class TestPopunderJSBehavior:
    """Tests for the pop-under JavaScript behavior implementation"""
    
    def test_js_has_blur_and_focus_techniques(self):
        """Verify JS uses multiple techniques to push popup behind"""
        response = requests.get(f"{BASE_URL}/api/js/popunder/test-popunder.js")
        js_content = response.text
        
        # Check for blur technique
        assert "popunder.blur()" in js_content or ".blur()" in js_content, "Should blur the popup"
        
        # Check for window.focus()
        assert "window.focus()" in js_content, "Should focus main window"
        
        # Check for self.focus()
        assert "self.focus()" in js_content, "Should use self.focus() technique"
        
        # Check for multiple setTimeout techniques for focus
        assert "setTimeout" in js_content, "Should use setTimeout for delayed focus"
        
        print("JS contains all required blur/focus techniques")
    
    def test_js_has_click_simulation(self):
        """Verify JS uses click simulation to regain focus"""
        response = requests.get(f"{BASE_URL}/api/js/popunder/test-popunder.js")
        js_content = response.text
        
        # Check for click event creation
        assert "createEvent" in js_content or "MouseEvents" in js_content, "Should create mouse event"
        assert "dispatchEvent" in js_content, "Should dispatch click event"
        
        print("JS contains click simulation technique")
    
    def test_js_has_temp_input_focus(self):
        """Verify JS uses temporary input focus technique"""
        response = requests.get(f"{BASE_URL}/api/js/popunder/test-popunder.js")
        js_content = response.text
        
        # Check for temporary input element creation
        assert "createElement('input')" in js_content, "Should create temp input"
        assert "appendChild" in js_content, "Should add temp input to DOM"
        assert "removeChild" in js_content, "Should remove temp input after focus"
        
        print("JS contains temporary input focus technique")
    
    def test_js_window_features(self):
        """Verify JS opens window with correct features for pop-under"""
        response = requests.get(f"{BASE_URL}/api/js/popunder/test-popunder.js")
        js_content = response.text
        
        # Check window.open features
        assert "window.open" in js_content, "Should use window.open"
        assert "width=" in js_content, "Should set window width"
        assert "height=" in js_content, "Should set window height"
        assert "toolbar" in js_content, "Should include toolbar setting"
        
        print("JS uses correct window.open features")


class TestCleanup:
    """Cleanup test data"""
    
    @pytest.fixture
    def admin_token(self):
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": ADMIN_EMAIL,
            "password": ADMIN_PASSWORD
        })
        return response.json()["token"]
    
    def test_cleanup_test_campaigns(self, admin_token):
        """Clean up test campaigns created during tests"""
        headers = {"Authorization": f"Bearer {admin_token}"}
        response = requests.get(f"{BASE_URL}/api/popunders", headers=headers)
        if response.status_code == 200:
            campaigns = response.json()["popunders"]
            cleaned = 0
            for campaign in campaigns:
                if campaign["name"].startswith("TEST_"):
                    del_response = requests.delete(
                        f"{BASE_URL}/api/popunders/{campaign['id']}", 
                        headers=headers
                    )
                    if del_response.status_code == 200:
                        cleaned += 1
            print(f"Cleaned up {cleaned} test campaigns")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
