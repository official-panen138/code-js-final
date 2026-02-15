"""
Unit and Integration tests for Popunder Campaign Module.
Tests cover:
- CRUD operations for popunder campaigns
- Public JS delivery endpoint with strict validation
- Whitelist enforcement
- Campaign/Project status checks
"""
import pytest
import httpx
import os

BASE_URL = os.environ.get('BASE_URL', 'http://localhost:8001')
API_URL = f"{BASE_URL}/api"

# Test credentials
ADMIN_CREDS = {"email": "admin@jshost.com", "password": "Admin@123"}
USER_CREDS = {"email": "user@jshost.com", "password": "User@123"}


class TestPopunderCampaignCRUD:
    """Test CRUD operations for popunder campaigns."""
    
    @pytest.fixture
    def admin_token(self):
        """Get admin token for authenticated requests."""
        with httpx.Client(base_url=API_URL) as client:
            response = client.post("/auth/login", json=ADMIN_CREDS)
            if response.status_code == 200:
                return response.json()["token"]
            # Register if login fails
            response = client.post("/auth/register", json=ADMIN_CREDS)
            return response.json()["token"]
    
    @pytest.fixture
    def test_project(self, admin_token):
        """Create a test project for popunder tests."""
        with httpx.Client(base_url=API_URL) as client:
            headers = {"Authorization": f"Bearer {admin_token}"}
            # Get first category
            cat_resp = client.get("/categories", headers=headers)
            category_id = cat_resp.json()["categories"][0]["id"] if cat_resp.json()["categories"] else 1
            
            # Create project
            project_data = {"name": "Popunder Test Project", "category_id": category_id}
            response = client.post("/projects", json=project_data, headers=headers)
            project = response.json()["project"]
            
            # Add whitelist entry
            client.post(f"/projects/{project['id']}/whitelist", json={"domain_pattern": "example.com"}, headers=headers)
            client.post(f"/projects/{project['id']}/whitelist", json={"domain_pattern": "*.test.com"}, headers=headers)
            
            yield project
            
            # Cleanup
            client.delete(f"/projects/{project['id']}", headers=headers)
    
    def test_create_popunder_campaign(self, admin_token, test_project):
        """Test creating a popunder campaign."""
        with httpx.Client(base_url=API_URL) as client:
            headers = {"Authorization": f"Bearer {admin_token}"}
            
            campaign_data = {
                "name": "Test Campaign",
                "settings": {
                    "target_url": "https://example.com/landing",
                    "frequency": 2,
                    "frequency_unit": "hour",
                    "delay": 1000,
                    "width": 1024,
                    "height": 768
                }
            }
            
            response = client.post(f"/projects/{test_project['id']}/popunders", json=campaign_data, headers=headers)
            assert response.status_code == 200, f"Failed: {response.text}"
            
            data = response.json()
            assert "popunder" in data
            campaign = data["popunder"]
            assert campaign["name"] == "Test Campaign"
            assert campaign["slug"] == "test-campaign"
            assert campaign["status"] == "active"
            assert campaign["settings"]["target_url"] == "https://example.com/landing"
    
    def test_create_popunder_without_target_url(self, admin_token, test_project):
        """Test that creating campaign without target_url fails."""
        with httpx.Client(base_url=API_URL) as client:
            headers = {"Authorization": f"Bearer {admin_token}"}
            
            campaign_data = {
                "name": "Invalid Campaign",
                "settings": {
                    "frequency": 1
                }
            }
            
            response = client.post(f"/projects/{test_project['id']}/popunders", json=campaign_data, headers=headers)
            assert response.status_code == 422 or response.status_code == 400
    
    def test_list_popunder_campaigns(self, admin_token, test_project):
        """Test listing popunder campaigns."""
        with httpx.Client(base_url=API_URL) as client:
            headers = {"Authorization": f"Bearer {admin_token}"}
            
            # Create a campaign first
            campaign_data = {
                "name": "List Test Campaign",
                "settings": {"target_url": "https://example.com"}
            }
            client.post(f"/projects/{test_project['id']}/popunders", json=campaign_data, headers=headers)
            
            # List campaigns
            response = client.get(f"/projects/{test_project['id']}/popunders", headers=headers)
            assert response.status_code == 200
            
            data = response.json()
            assert "popunders" in data
            assert len(data["popunders"]) >= 1
    
    def test_get_single_popunder_campaign(self, admin_token, test_project):
        """Test getting a single popunder campaign."""
        with httpx.Client(base_url=API_URL) as client:
            headers = {"Authorization": f"Bearer {admin_token}"}
            
            # Create a campaign
            campaign_data = {
                "name": "Get Test Campaign",
                "settings": {"target_url": "https://example.com"}
            }
            create_resp = client.post(f"/projects/{test_project['id']}/popunders", json=campaign_data, headers=headers)
            campaign_id = create_resp.json()["popunder"]["id"]
            
            # Get campaign
            response = client.get(f"/projects/{test_project['id']}/popunders/{campaign_id}", headers=headers)
            assert response.status_code == 200
            assert response.json()["popunder"]["name"] == "Get Test Campaign"
    
    def test_update_popunder_campaign(self, admin_token, test_project):
        """Test updating a popunder campaign."""
        with httpx.Client(base_url=API_URL) as client:
            headers = {"Authorization": f"Bearer {admin_token}"}
            
            # Create a campaign
            campaign_data = {
                "name": "Update Test Campaign",
                "settings": {"target_url": "https://example.com"}
            }
            create_resp = client.post(f"/projects/{test_project['id']}/popunders", json=campaign_data, headers=headers)
            campaign_id = create_resp.json()["popunder"]["id"]
            
            # Update campaign
            update_data = {
                "name": "Updated Campaign Name",
                "status": "paused",
                "settings": {"target_url": "https://updated.com", "delay": 2000}
            }
            response = client.patch(f"/projects/{test_project['id']}/popunders/{campaign_id}", json=update_data, headers=headers)
            assert response.status_code == 200
            
            updated = response.json()["popunder"]
            assert updated["name"] == "Updated Campaign Name"
            assert updated["status"] == "paused"
            assert updated["settings"]["target_url"] == "https://updated.com"
    
    def test_delete_popunder_campaign(self, admin_token, test_project):
        """Test deleting a popunder campaign."""
        with httpx.Client(base_url=API_URL) as client:
            headers = {"Authorization": f"Bearer {admin_token}"}
            
            # Create a campaign
            campaign_data = {
                "name": "Delete Test Campaign",
                "settings": {"target_url": "https://example.com"}
            }
            create_resp = client.post(f"/projects/{test_project['id']}/popunders", json=campaign_data, headers=headers)
            campaign_id = create_resp.json()["popunder"]["id"]
            
            # Delete campaign
            response = client.delete(f"/projects/{test_project['id']}/popunders/{campaign_id}", headers=headers)
            assert response.status_code == 200
            assert response.json()["message"] == "Popunder campaign deleted"
            
            # Verify deletion
            get_resp = client.get(f"/projects/{test_project['id']}/popunders/{campaign_id}", headers=headers)
            assert get_resp.status_code == 404


class TestPopunderJSDelivery:
    """Test public JS delivery endpoint with strict validation."""
    
    @pytest.fixture
    def admin_token(self):
        """Get admin token."""
        with httpx.Client(base_url=API_URL) as client:
            response = client.post("/auth/login", json=ADMIN_CREDS)
            if response.status_code == 200:
                return response.json()["token"]
            response = client.post("/auth/register", json=ADMIN_CREDS)
            return response.json()["token"]
    
    @pytest.fixture
    def active_project_with_campaign(self, admin_token):
        """Create an active project with whitelist and campaign."""
        with httpx.Client(base_url=API_URL) as client:
            headers = {"Authorization": f"Bearer {admin_token}"}
            
            # Get category
            cat_resp = client.get("/categories", headers=headers)
            category_id = cat_resp.json()["categories"][0]["id"] if cat_resp.json()["categories"] else 1
            
            # Create active project
            project_data = {"name": "JS Delivery Test Project", "category_id": category_id, "status": "active"}
            project_resp = client.post("/projects", json=project_data, headers=headers)
            project = project_resp.json()["project"]
            
            # Add whitelist
            client.post(f"/projects/{project['id']}/whitelist", json={"domain_pattern": "allowed.com"}, headers=headers)
            client.post(f"/projects/{project['id']}/whitelist", json={"domain_pattern": "*.allowed.com"}, headers=headers)
            
            # Create campaign
            campaign_data = {
                "name": "Delivery Test Campaign",
                "status": "active",
                "settings": {
                    "target_url": "https://target.com",
                    "frequency": 1,
                    "delay": 500
                }
            }
            campaign_resp = client.post(f"/projects/{project['id']}/popunders", json=campaign_data, headers=headers)
            campaign = campaign_resp.json()["popunder"]
            
            yield {"project": project, "campaign": campaign}
            
            # Cleanup
            client.delete(f"/projects/{project['id']}", headers=headers)
    
    def test_delivery_success_with_allowed_domain(self, active_project_with_campaign):
        """Test successful JS delivery for allowed domain."""
        project = active_project_with_campaign["project"]
        campaign = active_project_with_campaign["campaign"]
        
        with httpx.Client(base_url=BASE_URL) as client:
            headers = {"Origin": "https://allowed.com"}
            response = client.get(f"/api/js/popunder/{project['slug']}/{campaign['slug']}.js", headers=headers)
            
            assert response.status_code == 200
            assert "application/javascript" in response.headers["content-type"]
            assert "target.com" in response.text
            assert "popunder" in response.text.lower()
    
    def test_delivery_success_with_wildcard_subdomain(self, active_project_with_campaign):
        """Test successful JS delivery for wildcard subdomain."""
        project = active_project_with_campaign["project"]
        campaign = active_project_with_campaign["campaign"]
        
        with httpx.Client(base_url=BASE_URL) as client:
            headers = {"Origin": "https://sub.allowed.com"}
            response = client.get(f"/api/js/popunder/{project['slug']}/{campaign['slug']}.js", headers=headers)
            
            assert response.status_code == 200
            assert "target.com" in response.text
    
    def test_delivery_denied_for_unlisted_domain(self, active_project_with_campaign):
        """Test noop JS for domain not in whitelist."""
        project = active_project_with_campaign["project"]
        campaign = active_project_with_campaign["campaign"]
        
        with httpx.Client(base_url=BASE_URL) as client:
            headers = {"Origin": "https://unauthorized.com"}
            response = client.get(f"/api/js/popunder/{project['slug']}/{campaign['slug']}.js", headers=headers)
            
            assert response.status_code == 200  # Always 200
            assert "noop" in response.text or "unauthorized" in response.text
            assert "target.com" not in response.text
    
    def test_delivery_denied_for_paused_project(self, admin_token, active_project_with_campaign):
        """Test noop JS when project is paused."""
        project = active_project_with_campaign["project"]
        campaign = active_project_with_campaign["campaign"]
        
        with httpx.Client(base_url=API_URL) as client:
            headers = {"Authorization": f"Bearer {admin_token}"}
            # Pause the project
            client.patch(f"/projects/{project['id']}", json={"status": "paused"}, headers=headers)
        
        with httpx.Client(base_url=BASE_URL) as client:
            req_headers = {"Origin": "https://allowed.com"}
            response = client.get(f"/api/js/popunder/{project['slug']}/{campaign['slug']}.js", headers=req_headers)
            
            assert response.status_code == 200
            assert "noop" in response.text or "unauthorized" in response.text
    
    def test_delivery_denied_for_paused_campaign(self, admin_token, active_project_with_campaign):
        """Test noop JS when campaign is paused."""
        project = active_project_with_campaign["project"]
        campaign = active_project_with_campaign["campaign"]
        
        with httpx.Client(base_url=API_URL) as client:
            headers = {"Authorization": f"Bearer {admin_token}"}
            # Pause the campaign
            client.patch(f"/projects/{project['id']}/popunders/{campaign['id']}", json={"status": "paused"}, headers=headers)
        
        with httpx.Client(base_url=BASE_URL) as client:
            req_headers = {"Origin": "https://allowed.com"}
            response = client.get(f"/api/js/popunder/{project['slug']}/{campaign['slug']}.js", headers=req_headers)
            
            assert response.status_code == 200
            assert "noop" in response.text or "unauthorized" in response.text
    
    def test_delivery_denied_for_nonexistent_project(self):
        """Test noop JS for nonexistent project."""
        with httpx.Client(base_url=BASE_URL) as client:
            headers = {"Origin": "https://allowed.com"}
            response = client.get("/api/js/popunder/nonexistent-project/some-campaign.js", headers=headers)
            
            assert response.status_code == 200
            assert "noop" in response.text or "unauthorized" in response.text
    
    def test_delivery_denied_for_nonexistent_campaign(self, active_project_with_campaign):
        """Test noop JS for nonexistent campaign."""
        project = active_project_with_campaign["project"]
        
        with httpx.Client(base_url=BASE_URL) as client:
            headers = {"Origin": "https://allowed.com"}
            response = client.get(f"/api/js/popunder/{project['slug']}/nonexistent-campaign.js", headers=headers)
            
            assert response.status_code == 200
            assert "noop" in response.text or "unauthorized" in response.text
    
    def test_delivery_denied_without_js_extension(self, active_project_with_campaign):
        """Test noop JS when file doesn't end with .js."""
        project = active_project_with_campaign["project"]
        campaign = active_project_with_campaign["campaign"]
        
        with httpx.Client(base_url=BASE_URL) as client:
            headers = {"Origin": "https://allowed.com"}
            response = client.get(f"/api/js/popunder/{project['slug']}/{campaign['slug']}.txt", headers=headers)
            
            assert response.status_code == 200
            assert "noop" in response.text or "unauthorized" in response.text
    
    def test_delivery_denied_for_empty_whitelist(self, admin_token):
        """Test noop JS when project has no whitelist entries."""
        with httpx.Client(base_url=API_URL) as client:
            headers = {"Authorization": f"Bearer {admin_token}"}
            
            # Get category
            cat_resp = client.get("/categories", headers=headers)
            category_id = cat_resp.json()["categories"][0]["id"] if cat_resp.json()["categories"] else 1
            
            # Create project without whitelist
            project_data = {"name": "No Whitelist Project", "category_id": category_id}
            project_resp = client.post("/projects", json=project_data, headers=headers)
            project = project_resp.json()["project"]
            
            # Create campaign
            campaign_data = {
                "name": "Empty Whitelist Test",
                "settings": {"target_url": "https://test.com"}
            }
            campaign_resp = client.post(f"/projects/{project['id']}/popunders", json=campaign_data, headers=headers)
            campaign = campaign_resp.json()["popunder"]
            
            # Test delivery
            with httpx.Client(base_url=BASE_URL) as delivery_client:
                req_headers = {"Origin": "https://any-domain.com"}
                response = delivery_client.get(f"/api/js/popunder/{project['slug']}/{campaign['slug']}.js", headers=req_headers)
                
                assert response.status_code == 200
                assert "noop" in response.text or "unauthorized" in response.text
            
            # Cleanup
            client.delete(f"/projects/{project['id']}", headers=headers)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
