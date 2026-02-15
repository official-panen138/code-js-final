"""
Test file for Popunder Multi-URL Features
- Multiple URLs via url_list field (newline-separated, random selection)
- floating_banner HTML field
- html_body HTML field  
- Client-side country detection via ip-api.com in JS payload
"""
import pytest
import requests
import os
import json

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


class TestMultiURLCRUD:
    """Test CRUD operations for Popunder campaigns with multiple URLs"""

    def test_create_campaign_with_multiple_urls(self, api_session, auth_headers):
        """Test creating campaign with newline-separated URLs in url_list"""
        payload = {
            "name": "TEST_Multi_URL_Create",
            "settings": {
                "url_list": "https://example1.com/offer1\nhttps://example2.com/offer2\nhttps://example3.com/offer3",
                "timer": 5,
                "interval": 12,
                "devices": ["desktop", "mobile"],
                "countries": ["US", "GB"]
            },
            "status": "active"
        }
        response = api_session.post(f"{BASE_URL}/api/popunders", headers=auth_headers, json=payload)
        assert response.status_code == 200, f"Create failed: {response.text}"
        
        data = response.json()
        assert "popunder" in data
        campaign = data["popunder"]
        
        # Verify url_list is stored correctly
        settings = campaign["settings"]
        assert "url_list" in settings
        assert "https://example1.com/offer1" in settings["url_list"]
        assert "https://example2.com/offer2" in settings["url_list"]
        assert "https://example3.com/offer3" in settings["url_list"]
        
        print(f"Created campaign with ID: {campaign['id']}, url_list has 3 URLs")
        return campaign["id"]

    def test_create_campaign_with_floating_banner(self, api_session, auth_headers):
        """Test creating campaign with floating_banner HTML"""
        banner_html = '<div style="position:fixed;bottom:0;background:#333;color:#fff;padding:10px;">Banner Test</div>'
        payload = {
            "name": "TEST_Floating_Banner",
            "settings": {
                "url_list": "https://example.com/banner-test",
                "timer": 0,
                "interval": 24,
                "devices": ["desktop"],
                "countries": [],
                "floating_banner": banner_html
            }
        }
        response = api_session.post(f"{BASE_URL}/api/popunders", headers=auth_headers, json=payload)
        assert response.status_code == 200, f"Create failed: {response.text}"
        
        campaign = response.json()["popunder"]
        assert campaign["settings"]["floating_banner"] == banner_html
        print(f"Created campaign with floating_banner: {banner_html[:50]}...")

    def test_create_campaign_with_html_body(self, api_session, auth_headers):
        """Test creating campaign with html_body injection"""
        html_body = '<div id="custom-tracking"><img src="https://pixel.example.com/track.gif" /></div>'
        payload = {
            "name": "TEST_HTML_Body",
            "settings": {
                "url_list": "https://example.com/html-body-test",
                "timer": 0,
                "interval": 24,
                "devices": ["desktop"],
                "countries": [],
                "html_body": html_body
            }
        }
        response = api_session.post(f"{BASE_URL}/api/popunders", headers=auth_headers, json=payload)
        assert response.status_code == 200, f"Create failed: {response.text}"
        
        campaign = response.json()["popunder"]
        assert campaign["settings"]["html_body"] == html_body
        print(f"Created campaign with html_body: {html_body[:50]}...")

    def test_create_campaign_with_all_new_features(self, api_session, auth_headers):
        """Test creating campaign with all new features: url_list, floating_banner, html_body"""
        payload = {
            "name": "TEST_All_Features",
            "settings": {
                "url_list": "https://url1.com\nhttps://url2.com\nhttps://url3.com",
                "timer": 10,
                "interval": 6,
                "devices": ["desktop", "mobile", "tablet"],
                "countries": ["US", "CA", "GB", "AU"],
                "floating_banner": '<div class="banner">Banner HTML</div>',
                "html_body": '<div class="custom">Custom HTML</div>'
            },
            "status": "active"
        }
        response = api_session.post(f"{BASE_URL}/api/popunders", headers=auth_headers, json=payload)
        assert response.status_code == 200
        
        campaign = response.json()["popunder"]
        settings = campaign["settings"]
        
        # Verify all fields
        assert "url_list" in settings
        assert settings["timer"] == 10
        assert settings["interval"] == 6
        assert set(settings["devices"]) == {"desktop", "mobile", "tablet"}
        assert set(settings["countries"]) == {"US", "CA", "GB", "AU"}
        assert "floating_banner" in settings
        assert "html_body" in settings
        
        print("Created campaign with all new features successfully")

    def test_update_campaign_url_list(self, api_session, auth_headers):
        """Test updating campaign to modify url_list"""
        # Create campaign first
        create_response = api_session.post(f"{BASE_URL}/api/popunders", headers=auth_headers, json={
            "name": "TEST_Update_URLs",
            "settings": {
                "url_list": "https://original.com",
                "timer": 0,
                "interval": 24,
                "devices": ["desktop"],
                "countries": []
            }
        })
        assert create_response.status_code == 200
        campaign_id = create_response.json()["popunder"]["id"]
        
        # Update url_list with multiple URLs
        update_payload = {
            "settings": {
                "url_list": "https://new1.com\nhttps://new2.com\nhttps://new3.com",
                "timer": 5,
                "interval": 12,
                "devices": ["desktop", "mobile"],
                "countries": ["US"]
            }
        }
        response = api_session.patch(f"{BASE_URL}/api/popunders/{campaign_id}", headers=auth_headers, json=update_payload)
        assert response.status_code == 200
        
        updated = response.json()["popunder"]
        assert "https://new1.com" in updated["settings"]["url_list"]
        assert "https://new2.com" in updated["settings"]["url_list"]
        assert "https://new3.com" in updated["settings"]["url_list"]
        
        # Cleanup
        api_session.delete(f"{BASE_URL}/api/popunders/{campaign_id}", headers=auth_headers)
        print(f"Successfully updated url_list for campaign {campaign_id}")

    def test_update_campaign_html_fields(self, api_session, auth_headers):
        """Test updating floating_banner and html_body fields"""
        # Create campaign first
        create_response = api_session.post(f"{BASE_URL}/api/popunders", headers=auth_headers, json={
            "name": "TEST_Update_HTML",
            "settings": {
                "url_list": "https://example.com",
                "timer": 0,
                "interval": 24,
                "devices": ["desktop"],
                "countries": [],
                "floating_banner": "",
                "html_body": ""
            }
        })
        assert create_response.status_code == 200
        campaign_id = create_response.json()["popunder"]["id"]
        
        # Update HTML fields
        update_payload = {
            "settings": {
                "url_list": "https://example.com",
                "timer": 0,
                "interval": 24,
                "devices": ["desktop"],
                "countries": [],
                "floating_banner": '<div class="updated-banner">Updated Banner</div>',
                "html_body": '<script>console.log("tracking");</script>'
            }
        }
        response = api_session.patch(f"{BASE_URL}/api/popunders/{campaign_id}", headers=auth_headers, json=update_payload)
        assert response.status_code == 200
        
        updated = response.json()["popunder"]
        assert "updated-banner" in updated["settings"]["floating_banner"]
        assert "tracking" in updated["settings"]["html_body"]
        
        # Cleanup
        api_session.delete(f"{BASE_URL}/api/popunders/{campaign_id}", headers=auth_headers)
        print(f"Successfully updated HTML fields for campaign {campaign_id}")


class TestJSDeliveryWithMultiURL:
    """Test the public JS delivery endpoint for multi-URL campaigns"""

    def test_js_contains_urls_array(self, api_session, auth_headers):
        """Test that JS delivery contains urls array from url_list"""
        # Create campaign with multiple URLs
        create_response = api_session.post(f"{BASE_URL}/api/popunders", headers=auth_headers, json={
            "name": "TEST_JS_URLs_Array",
            "settings": {
                "url_list": "https://url1.example.com\nhttps://url2.example.com\nhttps://url3.example.com",
                "timer": 3,
                "interval": 8,
                "devices": ["desktop"],
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
        
        js_content = response.text
        
        # Verify urls array is in the JS
        assert '"urls":' in js_content or "'urls':" in js_content
        assert "url1.example.com" in js_content
        assert "url2.example.com" in js_content
        assert "url3.example.com" in js_content
        
        # Verify getUrl function for random selection
        assert "getUrl" in js_content
        assert "Math.random()" in js_content
        
        # Cleanup
        api_session.delete(f"{BASE_URL}/api/popunders/{campaign_id}", headers=auth_headers)
        print(f"JS contains urls array with 3 URLs")

    def test_js_contains_banner_html(self, api_session, auth_headers):
        """Test that JS delivery includes floating banner HTML"""
        banner_html = '<div id="test-banner">Floating Banner</div>'
        create_response = api_session.post(f"{BASE_URL}/api/popunders", headers=auth_headers, json={
            "name": "TEST_JS_Banner",
            "settings": {
                "url_list": "https://example.com",
                "timer": 0,
                "interval": 24,
                "devices": ["desktop"],
                "countries": [],
                "floating_banner": banner_html
            },
            "status": "active"
        })
        assert create_response.status_code == 200
        campaign = create_response.json()["popunder"]
        campaign_id = campaign["id"]
        slug = campaign["slug"]
        
        response = requests.get(f"{BASE_URL}/api/js/popunder/{slug}.js")
        assert response.status_code == 200
        
        js_content = response.text
        
        # Verify banner is in config
        assert '"banner":' in js_content or "'banner':" in js_content
        assert "test-banner" in js_content
        
        # Verify injectBanner function
        assert "injectBanner" in js_content
        
        # Cleanup
        api_session.delete(f"{BASE_URL}/api/popunders/{campaign_id}", headers=auth_headers)
        print(f"JS contains banner HTML and injectBanner function")

    def test_js_contains_html_body(self, api_session, auth_headers):
        """Test that JS delivery includes custom html_body"""
        html_body = '<div id="custom-html">Custom Body Injection</div>'
        create_response = api_session.post(f"{BASE_URL}/api/popunders", headers=auth_headers, json={
            "name": "TEST_JS_HTML_Body",
            "settings": {
                "url_list": "https://example.com",
                "timer": 0,
                "interval": 24,
                "devices": ["desktop"],
                "countries": [],
                "html_body": html_body
            },
            "status": "active"
        })
        assert create_response.status_code == 200
        campaign = create_response.json()["popunder"]
        campaign_id = campaign["id"]
        slug = campaign["slug"]
        
        response = requests.get(f"{BASE_URL}/api/js/popunder/{slug}.js")
        assert response.status_code == 200
        
        js_content = response.text
        
        # Verify html is in config
        assert '"html":' in js_content or "'html':" in js_content
        assert "custom-html" in js_content
        
        # Verify injectHtml function
        assert "injectHtml" in js_content
        
        # Cleanup
        api_session.delete(f"{BASE_URL}/api/popunders/{campaign_id}", headers=auth_headers)
        print(f"JS contains html_body and injectHtml function")

    def test_js_contains_country_detection(self, api_session, auth_headers):
        """Test that JS delivery includes ip-api.com country detection"""
        create_response = api_session.post(f"{BASE_URL}/api/popunders", headers=auth_headers, json={
            "name": "TEST_JS_Country",
            "settings": {
                "url_list": "https://example.com",
                "timer": 0,
                "interval": 24,
                "devices": ["desktop"],
                "countries": ["US", "GB"]  # With country targeting enabled
            },
            "status": "active"
        })
        assert create_response.status_code == 200
        campaign = create_response.json()["popunder"]
        campaign_id = campaign["id"]
        slug = campaign["slug"]
        
        response = requests.get(f"{BASE_URL}/api/js/popunder/{slug}.js")
        assert response.status_code == 200
        
        js_content = response.text
        
        # Verify ip-api.com integration
        assert "ip-api.com" in js_content
        assert "checkCountry" in js_content
        assert "countryCode" in js_content
        
        # Verify countries in config
        assert '"countries":' in js_content
        
        # Cleanup
        api_session.delete(f"{BASE_URL}/api/popunders/{campaign_id}", headers=auth_headers)
        print(f"JS contains ip-api.com country detection")

    def test_js_config_structure(self, api_session, auth_headers):
        """Test complete JS config structure includes all fields"""
        create_response = api_session.post(f"{BASE_URL}/api/popunders", headers=auth_headers, json={
            "name": "TEST_JS_Full_Config",
            "settings": {
                "url_list": "https://url1.com\nhttps://url2.com",
                "timer": 5,
                "interval": 12,
                "devices": ["desktop", "mobile"],
                "countries": ["US"],
                "floating_banner": '<div>Banner</div>',
                "html_body": '<div>HTML</div>'
            },
            "status": "active"
        })
        assert create_response.status_code == 200
        campaign = create_response.json()["popunder"]
        campaign_id = campaign["id"]
        slug = campaign["slug"]
        
        response = requests.get(f"{BASE_URL}/api/js/popunder/{slug}.js")
        assert response.status_code == 200
        
        js_content = response.text
        
        # Extract config JSON from JS
        # Format: var c = {...};
        config_start = js_content.find('var c = ') + 8
        config_end = js_content.find(';\n', config_start)
        config_str = js_content[config_start:config_end]
        
        config = json.loads(config_str)
        
        # Verify all expected fields
        assert "id" in config
        assert "urls" in config
        assert isinstance(config["urls"], list)
        assert len(config["urls"]) == 2
        assert "timer" in config
        assert config["timer"] == 5
        assert "interval" in config
        assert config["interval"] == 12
        assert "devices" in config
        assert "countries" in config
        assert "banner" in config
        assert "html" in config
        
        # Cleanup
        api_session.delete(f"{BASE_URL}/api/popunders/{campaign_id}", headers=auth_headers)
        print(f"JS config structure validated: {list(config.keys())}")


class TestValidationMultiURL:
    """Test validation for new multi-URL features"""

    def test_create_without_url_list_fails(self, api_session, auth_headers):
        """Test that creating campaign without url_list fails"""
        payload = {
            "name": "TEST_No_URL_List",
            "settings": {
                "url_list": "",  # Empty url_list
                "timer": 0,
                "interval": 24,
                "devices": ["desktop"],
                "countries": []
            }
        }
        response = api_session.post(f"{BASE_URL}/api/popunders", headers=auth_headers, json=payload)
        assert response.status_code == 400
        print("Correctly rejected empty url_list")

    def test_create_with_whitespace_only_url_list_fails(self, api_session, auth_headers):
        """Test that creating campaign with whitespace-only url_list fails"""
        payload = {
            "name": "TEST_Whitespace_URLs",
            "settings": {
                "url_list": "   \n  \n  ",  # Only whitespace
                "timer": 0,
                "interval": 24,
                "devices": ["desktop"],
                "countries": []
            }
        }
        response = api_session.post(f"{BASE_URL}/api/popunders", headers=auth_headers, json=payload)
        assert response.status_code == 400
        print("Correctly rejected whitespace-only url_list")


class TestExistingMultiURLCampaign:
    """Test the existing Multi URL Campaign (id: 11)"""

    def test_get_existing_multi_url_campaign(self, api_session, auth_headers):
        """Test getting the existing Multi URL Campaign"""
        response = api_session.get(f"{BASE_URL}/api/popunders/11", headers=auth_headers)
        
        if response.status_code == 404:
            pytest.skip("Campaign id 11 not found")
        
        assert response.status_code == 200
        campaign = response.json()["popunder"]
        
        # Verify it has the new settings structure
        settings = campaign["settings"]
        assert "url_list" in settings
        
        # Parse URLs
        url_list = settings["url_list"]
        urls = [u.strip() for u in url_list.split('\n') if u.strip()]
        
        print(f"Campaign 11 has {len(urls)} URLs: {urls}")
        print(f"Settings: timer={settings.get('timer')}, interval={settings.get('interval')}")
        print(f"Devices: {settings.get('devices')}")
        print(f"Countries: {settings.get('countries')}")
        print(f"Has floating_banner: {bool(settings.get('floating_banner'))}")
        print(f"Has html_body: {bool(settings.get('html_body'))}")

    def test_existing_campaign_js_delivery(self, api_session):
        """Test JS delivery for existing Multi URL Campaign"""
        response = requests.get(f"{BASE_URL}/api/js/popunder/multi-url-campaign.js")
        
        if "noop" in response.text.lower():
            pytest.skip("Campaign multi-url-campaign not found or paused")
        
        assert response.status_code == 200
        js_content = response.text
        
        # Verify it's a valid popunder script
        assert "openPopunder" in js_content
        assert "checkCountry" in js_content
        assert "ip-api.com" in js_content
        
        print("Existing campaign JS delivery working correctly")


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
