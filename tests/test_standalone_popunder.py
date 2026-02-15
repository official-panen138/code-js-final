"""
Tests for Standalone Popunder Campaign Module (New Independent Structure).
Tests cover:
- CRUD operations for standalone popunder campaigns (/api/popunders)
- Campaign-specific whitelist management (/api/popunders/{id}/whitelist)
- Public JS delivery endpoint with campaign's own whitelist (/api/js/popunder/{campaignSlug}.js)
- Domain tester for campaign whitelist

Note: Popunder campaigns are now completely independent from Projects with their own whitelist table.
"""
import pytest
import httpx
import os

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', 'https://js-hosting-hub.preview.emergentagent.com')
API_URL = f"{BASE_URL}/api"

# Test credentials
ADMIN_CREDS = {"email": "admin@jshost.com", "password": "Admin@123"}


class TestStandalonePopunderCRUD:
    """Test CRUD operations for standalone popunder campaigns."""
    
    @pytest.fixture(scope="class")
    def admin_token(self):
        """Get admin token for authenticated requests."""
        with httpx.Client(base_url=API_URL, timeout=30) as client:
            response = client.post("/auth/login", json=ADMIN_CREDS)
            assert response.status_code == 200, f"Login failed: {response.text}"
            return response.json()["token"]
    
    def test_list_popunder_campaigns(self, admin_token):
        """Test listing all popunder campaigns."""
        with httpx.Client(base_url=API_URL, timeout=30) as client:
            headers = {"Authorization": f"Bearer {admin_token}"}
            response = client.get("/popunders", headers=headers)
            assert response.status_code == 200
            data = response.json()
            assert "popunders" in data
            print(f"Found {len(data['popunders'])} popunder campaigns")
    
    def test_create_popunder_campaign(self, admin_token):
        """Test creating a standalone popunder campaign."""
        with httpx.Client(base_url=API_URL, timeout=30) as client:
            headers = {"Authorization": f"Bearer {admin_token}"}
            
            campaign_data = {
                "name": "TEST_Standalone Campaign",
                "settings": {
                    "target_url": "https://test-target.com/landing",
                    "frequency": 2,
                    "frequency_unit": "hour",
                    "delay": 1000,
                    "width": 1024,
                    "height": 768
                }
            }
            
            response = client.post("/popunders", json=campaign_data, headers=headers)
            assert response.status_code == 200, f"Failed to create: {response.text}"
            
            data = response.json()
            assert "popunder" in data
            campaign = data["popunder"]
            assert campaign["name"] == "TEST_Standalone Campaign"
            assert "slug" in campaign and campaign["slug"]
            assert campaign["status"] == "active"
            assert campaign["settings"]["target_url"] == "https://test-target.com/landing"
            
            # Cleanup
            client.delete(f"/popunders/{campaign['id']}", headers=headers)
    
    def test_create_campaign_without_target_url_fails(self, admin_token):
        """Test that creating campaign without target_url fails."""
        with httpx.Client(base_url=API_URL, timeout=30) as client:
            headers = {"Authorization": f"Bearer {admin_token}"}
            
            campaign_data = {
                "name": "Invalid Campaign",
                "settings": {
                    "frequency": 1
                }
            }
            
            response = client.post("/popunders", json=campaign_data, headers=headers)
            assert response.status_code in [400, 422], f"Should fail: {response.text}"
    
    def test_get_single_campaign(self, admin_token):
        """Test getting a single popunder campaign with its whitelist."""
        with httpx.Client(base_url=API_URL, timeout=30) as client:
            headers = {"Authorization": f"Bearer {admin_token}"}
            
            # Create campaign
            campaign_data = {
                "name": "TEST_Get Single Campaign",
                "settings": {"target_url": "https://example.com"}
            }
            create_resp = client.post("/popunders", json=campaign_data, headers=headers)
            campaign_id = create_resp.json()["popunder"]["id"]
            
            # Get campaign
            response = client.get(f"/popunders/{campaign_id}", headers=headers)
            assert response.status_code == 200
            data = response.json()
            assert "popunder" in data
            assert "whitelists" in data
            assert data["popunder"]["name"] == "TEST_Get Single Campaign"
            
            # Cleanup
            client.delete(f"/popunders/{campaign_id}", headers=headers)
    
    def test_update_campaign(self, admin_token):
        """Test updating a popunder campaign."""
        with httpx.Client(base_url=API_URL, timeout=30) as client:
            headers = {"Authorization": f"Bearer {admin_token}"}
            
            # Create campaign
            campaign_data = {
                "name": "TEST_Update Campaign",
                "settings": {"target_url": "https://original.com"}
            }
            create_resp = client.post("/popunders", json=campaign_data, headers=headers)
            campaign_id = create_resp.json()["popunder"]["id"]
            
            # Update campaign
            update_data = {
                "name": "TEST_Updated Campaign Name",
                "status": "paused",
                "settings": {"target_url": "https://updated.com", "delay": 2000}
            }
            response = client.patch(f"/popunders/{campaign_id}", json=update_data, headers=headers)
            assert response.status_code == 200
            
            updated = response.json()["popunder"]
            assert updated["name"] == "TEST_Updated Campaign Name"
            assert updated["status"] == "paused"
            assert updated["settings"]["target_url"] == "https://updated.com"
            
            # Verify with GET
            get_resp = client.get(f"/popunders/{campaign_id}", headers=headers)
            assert get_resp.json()["popunder"]["status"] == "paused"
            
            # Cleanup
            client.delete(f"/popunders/{campaign_id}", headers=headers)
    
    def test_delete_campaign(self, admin_token):
        """Test deleting a popunder campaign."""
        with httpx.Client(base_url=API_URL, timeout=30) as client:
            headers = {"Authorization": f"Bearer {admin_token}"}
            
            # Create campaign
            campaign_data = {
                "name": "TEST_Delete Campaign",
                "settings": {"target_url": "https://example.com"}
            }
            create_resp = client.post("/popunders", json=campaign_data, headers=headers)
            campaign_id = create_resp.json()["popunder"]["id"]
            
            # Delete campaign
            response = client.delete(f"/popunders/{campaign_id}", headers=headers)
            assert response.status_code == 200
            
            # Verify deletion
            get_resp = client.get(f"/popunders/{campaign_id}", headers=headers)
            assert get_resp.status_code == 404


class TestPopunderCampaignWhitelist:
    """Test whitelist management for popunder campaigns."""
    
    @pytest.fixture(scope="class")
    def admin_token(self):
        """Get admin token."""
        with httpx.Client(base_url=API_URL, timeout=30) as client:
            response = client.post("/auth/login", json=ADMIN_CREDS)
            return response.json()["token"]
    
    @pytest.fixture
    def test_campaign(self, admin_token):
        """Create a test campaign for whitelist tests."""
        with httpx.Client(base_url=API_URL, timeout=30) as client:
            headers = {"Authorization": f"Bearer {admin_token}"}
            
            campaign_data = {
                "name": "TEST_Whitelist Campaign",
                "settings": {"target_url": "https://test-whitelist.com"}
            }
            response = client.post("/popunders", json=campaign_data, headers=headers)
            campaign = response.json()["popunder"]
            
            yield campaign
            
            # Cleanup
            client.delete(f"/popunders/{campaign['id']}", headers=headers)
    
    def test_add_whitelist_domain(self, admin_token, test_campaign):
        """Test adding a domain to campaign whitelist."""
        with httpx.Client(base_url=API_URL, timeout=30) as client:
            headers = {"Authorization": f"Bearer {admin_token}"}
            
            response = client.post(
                f"/popunders/{test_campaign['id']}/whitelist",
                json={"domain_pattern": "example.com"},
                headers=headers
            )
            assert response.status_code == 200
            
            whitelist = response.json()["whitelist"]
            assert whitelist["domain_pattern"] == "example.com"
            assert whitelist["is_active"] == True
    
    def test_add_wildcard_domain(self, admin_token, test_campaign):
        """Test adding a wildcard domain pattern."""
        with httpx.Client(base_url=API_URL, timeout=30) as client:
            headers = {"Authorization": f"Bearer {admin_token}"}
            
            response = client.post(
                f"/popunders/{test_campaign['id']}/whitelist",
                json={"domain_pattern": "*.wildcard.com"},
                headers=headers
            )
            assert response.status_code == 200
            assert response.json()["whitelist"]["domain_pattern"] == "*.wildcard.com"
    
    def test_list_whitelist(self, admin_token, test_campaign):
        """Test listing whitelist entries."""
        with httpx.Client(base_url=API_URL, timeout=30) as client:
            headers = {"Authorization": f"Bearer {admin_token}"}
            
            # Add a domain first
            client.post(
                f"/popunders/{test_campaign['id']}/whitelist",
                json={"domain_pattern": "listtest.com"},
                headers=headers
            )
            
            response = client.get(f"/popunders/{test_campaign['id']}/whitelist", headers=headers)
            assert response.status_code == 200
            assert "whitelists" in response.json()
    
    def test_toggle_whitelist_status(self, admin_token, test_campaign):
        """Test toggling whitelist entry active status."""
        with httpx.Client(base_url=API_URL, timeout=30) as client:
            headers = {"Authorization": f"Bearer {admin_token}"}
            
            # Add domain
            create_resp = client.post(
                f"/popunders/{test_campaign['id']}/whitelist",
                json={"domain_pattern": "toggle.com"},
                headers=headers
            )
            whitelist_id = create_resp.json()["whitelist"]["id"]
            
            # Toggle off
            response = client.patch(
                f"/popunders/{test_campaign['id']}/whitelist/{whitelist_id}",
                json={"is_active": False},
                headers=headers
            )
            assert response.status_code == 200
            assert response.json()["whitelist"]["is_active"] == False
    
    def test_delete_whitelist_entry(self, admin_token, test_campaign):
        """Test deleting a whitelist entry."""
        with httpx.Client(base_url=API_URL, timeout=30) as client:
            headers = {"Authorization": f"Bearer {admin_token}"}
            
            # Add domain
            create_resp = client.post(
                f"/popunders/{test_campaign['id']}/whitelist",
                json={"domain_pattern": "delete.com"},
                headers=headers
            )
            whitelist_id = create_resp.json()["whitelist"]["id"]
            
            # Delete
            response = client.delete(
                f"/popunders/{test_campaign['id']}/whitelist/{whitelist_id}",
                headers=headers
            )
            assert response.status_code == 200


class TestPopunderDomainTester:
    """Test domain tester for popunder campaigns."""
    
    @pytest.fixture(scope="class")
    def admin_token(self):
        """Get admin token."""
        with httpx.Client(base_url=API_URL, timeout=30) as client:
            response = client.post("/auth/login", json=ADMIN_CREDS)
            return response.json()["token"]
    
    @pytest.fixture
    def campaign_with_whitelist(self, admin_token):
        """Create campaign with whitelist entries."""
        with httpx.Client(base_url=API_URL, timeout=30) as client:
            headers = {"Authorization": f"Bearer {admin_token}"}
            
            # Create campaign
            campaign_data = {
                "name": "TEST_Domain Tester Campaign",
                "settings": {"target_url": "https://tester.com"}
            }
            response = client.post("/popunders", json=campaign_data, headers=headers)
            campaign = response.json()["popunder"]
            
            # Add whitelist entries
            client.post(f"/popunders/{campaign['id']}/whitelist", json={"domain_pattern": "allowed.com"}, headers=headers)
            client.post(f"/popunders/{campaign['id']}/whitelist", json={"domain_pattern": "*.wildcard.com"}, headers=headers)
            
            yield campaign
            
            # Cleanup
            client.delete(f"/popunders/{campaign['id']}", headers=headers)
    
    def test_domain_allowed(self, admin_token, campaign_with_whitelist):
        """Test domain tester for allowed domain."""
        with httpx.Client(base_url=API_URL, timeout=30) as client:
            headers = {"Authorization": f"Bearer {admin_token}"}
            
            response = client.post(
                f"/popunders/{campaign_with_whitelist['id']}/test-domain",
                json={"domain": "https://allowed.com"},
                headers=headers
            )
            assert response.status_code == 200
            data = response.json()
            assert data["allowed"] == True
            assert "allowed.com" in data["matched_patterns"]
    
    def test_domain_allowed_wildcard(self, admin_token, campaign_with_whitelist):
        """Test domain tester for wildcard match."""
        with httpx.Client(base_url=API_URL, timeout=30) as client:
            headers = {"Authorization": f"Bearer {admin_token}"}
            
            response = client.post(
                f"/popunders/{campaign_with_whitelist['id']}/test-domain",
                json={"domain": "https://sub.wildcard.com"},
                headers=headers
            )
            assert response.status_code == 200
            data = response.json()
            assert data["allowed"] == True
    
    def test_domain_denied(self, admin_token, campaign_with_whitelist):
        """Test domain tester for denied domain."""
        with httpx.Client(base_url=API_URL, timeout=30) as client:
            headers = {"Authorization": f"Bearer {admin_token}"}
            
            response = client.post(
                f"/popunders/{campaign_with_whitelist['id']}/test-domain",
                json={"domain": "https://unauthorized.com"},
                headers=headers
            )
            assert response.status_code == 200
            data = response.json()
            assert data["allowed"] == False


class TestPopunderJSDelivery:
    """Test public JS delivery endpoint with campaign's own whitelist."""
    
    @pytest.fixture(scope="class")
    def admin_token(self):
        """Get admin token."""
        with httpx.Client(base_url=API_URL, timeout=30) as client:
            response = client.post("/auth/login", json=ADMIN_CREDS)
            return response.json()["token"]
    
    @pytest.fixture
    def active_campaign_with_whitelist(self, admin_token):
        """Create an active campaign with whitelist."""
        with httpx.Client(base_url=API_URL, timeout=30) as client:
            headers = {"Authorization": f"Bearer {admin_token}"}
            
            campaign_data = {
                "name": "TEST_JS Delivery Campaign",
                "status": "active",
                "settings": {
                    "target_url": "https://delivery-target.com",
                    "frequency": 1,
                    "delay": 500
                }
            }
            response = client.post("/popunders", json=campaign_data, headers=headers)
            campaign = response.json()["popunder"]
            
            # Add whitelist
            client.post(f"/popunders/{campaign['id']}/whitelist", json={"domain_pattern": "deliverytest.com"}, headers=headers)
            client.post(f"/popunders/{campaign['id']}/whitelist", json={"domain_pattern": "*.deliverytest.com"}, headers=headers)
            
            yield campaign
            
            # Cleanup
            client.delete(f"/popunders/{campaign['id']}", headers=headers)
    
    def test_delivery_success_with_allowed_domain(self, active_campaign_with_whitelist):
        """Test successful JS delivery for allowed domain (using campaign's own whitelist)."""
        campaign_slug = active_campaign_with_whitelist["slug"]
        
        with httpx.Client(base_url=BASE_URL, timeout=30) as client:
            headers = {"Origin": "https://deliverytest.com"}
            response = client.get(f"/api/js/popunder/{campaign_slug}.js", headers=headers)
            
            assert response.status_code == 200
            assert "application/javascript" in response.headers["content-type"]
            assert "delivery-target.com" in response.text
            assert "noop" not in response.text
    
    def test_delivery_success_with_wildcard_subdomain(self, active_campaign_with_whitelist):
        """Test successful JS delivery for wildcard subdomain."""
        campaign_slug = active_campaign_with_whitelist["slug"]
        
        with httpx.Client(base_url=BASE_URL, timeout=30) as client:
            headers = {"Origin": "https://sub.deliverytest.com"}
            response = client.get(f"/api/js/popunder/{campaign_slug}.js", headers=headers)
            
            assert response.status_code == 200
            assert "delivery-target.com" in response.text
    
    def test_delivery_denied_for_unlisted_domain(self, active_campaign_with_whitelist):
        """Test noop JS for domain not in campaign's whitelist."""
        campaign_slug = active_campaign_with_whitelist["slug"]
        
        with httpx.Client(base_url=BASE_URL, timeout=30) as client:
            headers = {"Origin": "https://unauthorized.com"}
            response = client.get(f"/api/js/popunder/{campaign_slug}.js", headers=headers)
            
            assert response.status_code == 200  # Always 200
            assert "noop" in response.text or "unauthorized" in response.text
            assert "delivery-target.com" not in response.text
    
    def test_delivery_denied_for_paused_campaign(self, admin_token, active_campaign_with_whitelist):
        """Test noop JS when campaign is paused."""
        campaign_id = active_campaign_with_whitelist["id"]
        campaign_slug = active_campaign_with_whitelist["slug"]
        
        with httpx.Client(base_url=API_URL, timeout=30) as client:
            headers = {"Authorization": f"Bearer {admin_token}"}
            # Pause the campaign
            client.patch(f"/popunders/{campaign_id}", json={"status": "paused"}, headers=headers)
        
        with httpx.Client(base_url=BASE_URL, timeout=30) as client:
            req_headers = {"Origin": "https://deliverytest.com"}
            response = client.get(f"/api/js/popunder/{campaign_slug}.js", headers=req_headers)
            
            assert response.status_code == 200
            assert "noop" in response.text or "unauthorized" in response.text
        
        # Restore active status
        with httpx.Client(base_url=API_URL, timeout=30) as client:
            headers = {"Authorization": f"Bearer {admin_token}"}
            client.patch(f"/popunders/{campaign_id}", json={"status": "active"}, headers=headers)
    
    def test_delivery_denied_for_nonexistent_campaign(self):
        """Test noop JS for nonexistent campaign slug."""
        with httpx.Client(base_url=BASE_URL, timeout=30) as client:
            headers = {"Origin": "https://any.com"}
            response = client.get("/api/js/popunder/nonexistent-campaign-xyz.js", headers=headers)
            
            assert response.status_code == 200
            assert "noop" in response.text or "unauthorized" in response.text
    
    def test_delivery_denied_without_js_extension(self, active_campaign_with_whitelist):
        """Test noop JS when file doesn't end with .js."""
        campaign_slug = active_campaign_with_whitelist["slug"]
        
        with httpx.Client(base_url=BASE_URL, timeout=30) as client:
            headers = {"Origin": "https://deliverytest.com"}
            response = client.get(f"/api/js/popunder/{campaign_slug}.txt", headers=headers)
            
            assert response.status_code == 200
            assert "noop" in response.text or "unauthorized" in response.text
    
    def test_delivery_denied_for_empty_whitelist(self, admin_token):
        """Test noop JS when campaign has no whitelist entries."""
        with httpx.Client(base_url=API_URL, timeout=30) as client:
            headers = {"Authorization": f"Bearer {admin_token}"}
            
            # Create campaign without whitelist
            campaign_data = {
                "name": "TEST_No Whitelist Campaign",
                "settings": {"target_url": "https://test.com"}
            }
            response = client.post("/popunders", json=campaign_data, headers=headers)
            campaign = response.json()["popunder"]
            
            # Test delivery
            with httpx.Client(base_url=BASE_URL, timeout=30) as delivery_client:
                req_headers = {"Origin": "https://any-domain.com"}
                resp = delivery_client.get(f"/api/js/popunder/{campaign['slug']}.js", headers=req_headers)
                
                assert resp.status_code == 200
                assert "noop" in resp.text or "unauthorized" in resp.text
            
            # Cleanup
            client.delete(f"/popunders/{campaign['id']}", headers=headers)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
