"""
Test Ownership Visibility Rules:
- Regular user (ID=2) created project ID=1 and campaign ID=1
- Admin (ID=1) created project ID=2 and campaign ID=2
- Regular user should NOT see project/campaign ID=2 in lists and should get 404 when accessing directly
- Admin should see ALL projects/campaigns in lists and access any of them
"""

import pytest
import requests
import os

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

# Test credentials
ADMIN_CREDS = {"email": "admin@jshost.com", "password": "Admin@123"}
USER_CREDS = {"email": "user@jshost.com", "password": "User@123"}


@pytest.fixture(scope="module")
def admin_token():
    """Get admin auth token."""
    response = requests.post(f"{BASE_URL}/api/auth/login", json=ADMIN_CREDS)
    assert response.status_code == 200, f"Admin login failed: {response.text}"
    data = response.json()
    assert data["user"]["role"] == "admin", "Expected admin role"
    assert data["user"]["id"] == 1, "Expected admin ID=1"
    return data["token"]


@pytest.fixture(scope="module")
def user_token():
    """Get regular user auth token."""
    response = requests.post(f"{BASE_URL}/api/auth/login", json=USER_CREDS)
    assert response.status_code == 200, f"User login failed: {response.text}"
    data = response.json()
    assert data["user"]["role"] == "user", "Expected user role"
    assert data["user"]["id"] == 2, "Expected user ID=2"
    return data["token"]


@pytest.fixture
def admin_headers(admin_token):
    return {"Authorization": f"Bearer {admin_token}", "Content-Type": "application/json"}


@pytest.fixture
def user_headers(user_token):
    return {"Authorization": f"Bearer {user_token}", "Content-Type": "application/json"}


# ================== PROJECT LISTING VISIBILITY ==================

class TestProjectListingVisibility:
    """Test that regular user sees only their projects, admin sees all."""
    
    def test_admin_sees_all_projects(self, admin_headers):
        """Admin should see ALL projects regardless of owner."""
        response = requests.get(f"{BASE_URL}/api/projects", headers=admin_headers)
        assert response.status_code == 200
        data = response.json()
        projects = data["projects"]
        
        # Admin should see projects from both user_id=1 (admin) and user_id=2 (user)
        user_ids = {p["user_id"] for p in projects}
        assert 1 in user_ids, "Admin should see admin's projects (user_id=1)"
        assert 2 in user_ids, "Admin should see user's projects (user_id=2)"
        
        # Verify project ID=1 (user's) and ID=2 (admin's) are visible
        project_ids = {p["id"] for p in projects}
        assert 1 in project_ids, "Admin should see project ID=1 (User Project)"
        assert 2 in project_ids, "Admin should see project ID=2 (Admin Project)"
        print(f"PASS: Admin sees {len(projects)} projects from multiple owners")
    
    def test_user_sees_only_own_projects(self, user_headers):
        """Regular user should see ONLY their own projects."""
        response = requests.get(f"{BASE_URL}/api/projects", headers=user_headers)
        assert response.status_code == 200
        data = response.json()
        projects = data["projects"]
        
        # User should only see their own projects (user_id=2)
        for project in projects:
            assert project["user_id"] == 2, f"User should only see own projects, got user_id={project['user_id']}"
        
        # Verify project ID=2 (admin's project) is NOT visible
        project_ids = {p["id"] for p in projects}
        assert 2 not in project_ids, "User should NOT see admin's project ID=2"
        print(f"PASS: User sees only {len(projects)} own project(s)")


# ================== PROJECT DIRECT ACCESS ==================

class TestProjectDirectAccess:
    """Test that regular user cannot access other user's project via direct ID."""
    
    def test_user_can_access_own_project(self, user_headers):
        """User should be able to access their own project (ID=1)."""
        response = requests.get(f"{BASE_URL}/api/projects/1", headers=user_headers)
        assert response.status_code == 200, f"User should access own project: {response.text}"
        data = response.json()
        assert data["project"]["user_id"] == 2, "Project should belong to user"
        print("PASS: User can access own project ID=1")
    
    def test_user_cannot_access_admin_project(self, user_headers):
        """User should get 404 when trying to access admin's project (ID=2)."""
        response = requests.get(f"{BASE_URL}/api/projects/2", headers=user_headers)
        assert response.status_code == 404, f"User should get 404 for admin's project, got {response.status_code}"
        print("PASS: User gets 404 for admin's project ID=2")
    
    def test_admin_can_access_user_project(self, admin_headers):
        """Admin should be able to access any project including user's (ID=1)."""
        response = requests.get(f"{BASE_URL}/api/projects/1", headers=admin_headers)
        assert response.status_code == 200, f"Admin should access any project: {response.text}"
        data = response.json()
        assert data["project"]["user_id"] == 2, "Project ID=1 belongs to user"
        print("PASS: Admin can access user's project ID=1")
    
    def test_admin_can_access_own_project(self, admin_headers):
        """Admin should be able to access their own project (ID=2)."""
        response = requests.get(f"{BASE_URL}/api/projects/2", headers=admin_headers)
        assert response.status_code == 200, f"Admin should access own project: {response.text}"
        data = response.json()
        assert data["project"]["user_id"] == 1, "Project ID=2 belongs to admin"
        print("PASS: Admin can access own project ID=2")


# ================== PROJECT UPDATE ACCESS ==================

class TestProjectUpdateAccess:
    """Test that regular user cannot update other user's project."""
    
    def test_user_cannot_update_admin_project(self, user_headers):
        """User should get 404 when trying to update admin's project."""
        response = requests.patch(
            f"{BASE_URL}/api/projects/2",
            headers=user_headers,
            json={"name": "Hacked Project Name"}
        )
        assert response.status_code == 404, f"User should get 404 when updating admin's project, got {response.status_code}"
        print("PASS: User cannot update admin's project ID=2")
    
    def test_admin_can_update_user_project(self, admin_headers):
        """Admin should be able to update any project."""
        # Get current name first
        response = requests.get(f"{BASE_URL}/api/projects/1", headers=admin_headers)
        original_name = response.json()["project"]["name"]
        
        # Update project
        response = requests.patch(
            f"{BASE_URL}/api/projects/1",
            headers=admin_headers,
            json={"name": "Admin Updated Name"}
        )
        assert response.status_code == 200, f"Admin should update any project: {response.text}"
        
        # Restore original name
        response = requests.patch(
            f"{BASE_URL}/api/projects/1",
            headers=admin_headers,
            json={"name": original_name}
        )
        assert response.status_code == 200
        print("PASS: Admin can update user's project ID=1")


# ================== PROJECT DELETE ACCESS ==================

class TestProjectDeleteAccess:
    """Test that regular user cannot delete other user's project."""
    
    def test_user_cannot_delete_admin_project(self, user_headers):
        """User should get 404 when trying to delete admin's project."""
        response = requests.delete(f"{BASE_URL}/api/projects/2", headers=user_headers)
        assert response.status_code == 404, f"User should get 404 when deleting admin's project, got {response.status_code}"
        print("PASS: User cannot delete admin's project ID=2")


# ================== POPUNDER CAMPAIGN LISTING VISIBILITY ==================

class TestPopunderListingVisibility:
    """Test that regular user sees only their campaigns, admin sees all."""
    
    def test_admin_sees_all_campaigns(self, admin_headers):
        """Admin should see ALL popunder campaigns regardless of owner."""
        response = requests.get(f"{BASE_URL}/api/popunders", headers=admin_headers)
        assert response.status_code == 200
        data = response.json()
        campaigns = data["popunders"]
        
        # Admin should see campaigns from both user_id=1 (admin) and user_id=2 (user)
        user_ids = {c["user_id"] for c in campaigns}
        assert 1 in user_ids, "Admin should see admin's campaigns (user_id=1)"
        assert 2 in user_ids, "Admin should see user's campaigns (user_id=2)"
        
        # Verify campaign ID=1 (user's) and ID=2 (admin's) are visible
        campaign_ids = {c["id"] for c in campaigns}
        assert 1 in campaign_ids, "Admin should see campaign ID=1 (User Campaign)"
        assert 2 in campaign_ids, "Admin should see campaign ID=2 (Admin Campaign)"
        print(f"PASS: Admin sees {len(campaigns)} campaigns from multiple owners")
    
    def test_user_sees_only_own_campaigns(self, user_headers):
        """Regular user should see ONLY their own popunder campaigns."""
        response = requests.get(f"{BASE_URL}/api/popunders", headers=user_headers)
        assert response.status_code == 200
        data = response.json()
        campaigns = data["popunders"]
        
        # User should only see their own campaigns (user_id=2)
        for campaign in campaigns:
            assert campaign["user_id"] == 2, f"User should only see own campaigns, got user_id={campaign['user_id']}"
        
        # Verify campaign ID=2 (admin's campaign) is NOT visible
        campaign_ids = {c["id"] for c in campaigns}
        assert 2 not in campaign_ids, "User should NOT see admin's campaign ID=2"
        print(f"PASS: User sees only {len(campaigns)} own campaign(s)")


# ================== POPUNDER CAMPAIGN DIRECT ACCESS ==================

class TestPopunderDirectAccess:
    """Test that regular user cannot access other user's campaign via direct ID."""
    
    def test_user_can_access_own_campaign(self, user_headers):
        """User should be able to access their own campaign (ID=1)."""
        response = requests.get(f"{BASE_URL}/api/popunders/1", headers=user_headers)
        assert response.status_code == 200, f"User should access own campaign: {response.text}"
        data = response.json()
        assert data["popunder"]["user_id"] == 2, "Campaign should belong to user"
        print("PASS: User can access own campaign ID=1")
    
    def test_user_cannot_access_admin_campaign(self, user_headers):
        """User should get 404 when trying to access admin's campaign (ID=2)."""
        response = requests.get(f"{BASE_URL}/api/popunders/2", headers=user_headers)
        assert response.status_code == 404, f"User should get 404 for admin's campaign, got {response.status_code}"
        print("PASS: User gets 404 for admin's campaign ID=2")
    
    def test_admin_can_access_user_campaign(self, admin_headers):
        """Admin should be able to access any campaign including user's (ID=1)."""
        response = requests.get(f"{BASE_URL}/api/popunders/1", headers=admin_headers)
        assert response.status_code == 200, f"Admin should access any campaign: {response.text}"
        data = response.json()
        assert data["popunder"]["user_id"] == 2, "Campaign ID=1 belongs to user"
        print("PASS: Admin can access user's campaign ID=1")
    
    def test_admin_can_access_own_campaign(self, admin_headers):
        """Admin should be able to access their own campaign (ID=2)."""
        response = requests.get(f"{BASE_URL}/api/popunders/2", headers=admin_headers)
        assert response.status_code == 200, f"Admin should access own campaign: {response.text}"
        data = response.json()
        assert data["popunder"]["user_id"] == 1, "Campaign ID=2 belongs to admin"
        print("PASS: Admin can access own campaign ID=2")


# ================== POPUNDER CAMPAIGN UPDATE ACCESS ==================

class TestPopunderUpdateAccess:
    """Test that regular user cannot update other user's campaign."""
    
    def test_user_cannot_update_admin_campaign(self, user_headers):
        """User should get 404 when trying to update admin's campaign."""
        response = requests.patch(
            f"{BASE_URL}/api/popunders/2",
            headers=user_headers,
            json={"name": "Hacked Campaign Name"}
        )
        assert response.status_code == 404, f"User should get 404 when updating admin's campaign, got {response.status_code}"
        print("PASS: User cannot update admin's campaign ID=2")
    
    def test_admin_can_update_user_campaign(self, admin_headers):
        """Admin should be able to update any campaign."""
        # Get current name first
        response = requests.get(f"{BASE_URL}/api/popunders/1", headers=admin_headers)
        original_name = response.json()["popunder"]["name"]
        
        # Update campaign
        response = requests.patch(
            f"{BASE_URL}/api/popunders/1",
            headers=admin_headers,
            json={"name": "Admin Updated Campaign"}
        )
        assert response.status_code == 200, f"Admin should update any campaign: {response.text}"
        
        # Restore original name
        response = requests.patch(
            f"{BASE_URL}/api/popunders/1",
            headers=admin_headers,
            json={"name": original_name}
        )
        assert response.status_code == 200
        print("PASS: Admin can update user's campaign ID=1")


# ================== POPUNDER CAMPAIGN DELETE ACCESS ==================

class TestPopunderDeleteAccess:
    """Test that regular user cannot delete other user's campaign."""
    
    def test_user_cannot_delete_admin_campaign(self, user_headers):
        """User should get 404 when trying to delete admin's campaign."""
        response = requests.delete(f"{BASE_URL}/api/popunders/2", headers=user_headers)
        assert response.status_code == 404, f"User should get 404 when deleting admin's campaign, got {response.status_code}"
        print("PASS: User cannot delete admin's campaign ID=2")


# ================== VERIFY DATA INTEGRITY ==================

class TestDataIntegrity:
    """Verify the test data setup matches expected ownership."""
    
    def test_project_1_owned_by_user(self, admin_headers):
        """Project ID=1 should be owned by user (ID=2)."""
        response = requests.get(f"{BASE_URL}/api/projects/1", headers=admin_headers)
        assert response.status_code == 200
        data = response.json()
        assert data["project"]["user_id"] == 2, "Project ID=1 should be owned by user_id=2"
        print("PASS: Project ID=1 owned by user_id=2")
    
    def test_project_2_owned_by_admin(self, admin_headers):
        """Project ID=2 should be owned by admin (ID=1)."""
        response = requests.get(f"{BASE_URL}/api/projects/2", headers=admin_headers)
        assert response.status_code == 200
        data = response.json()
        assert data["project"]["user_id"] == 1, "Project ID=2 should be owned by admin_id=1"
        print("PASS: Project ID=2 owned by admin_id=1")
    
    def test_campaign_1_owned_by_user(self, admin_headers):
        """Campaign ID=1 should be owned by user (ID=2)."""
        response = requests.get(f"{BASE_URL}/api/popunders/1", headers=admin_headers)
        assert response.status_code == 200
        data = response.json()
        assert data["popunder"]["user_id"] == 2, "Campaign ID=1 should be owned by user_id=2"
        print("PASS: Campaign ID=1 owned by user_id=2")
    
    def test_campaign_2_owned_by_admin(self, admin_headers):
        """Campaign ID=2 should be owned by admin (ID=1)."""
        response = requests.get(f"{BASE_URL}/api/popunders/2", headers=admin_headers)
        assert response.status_code == 200
        data = response.json()
        assert data["popunder"]["user_id"] == 1, "Campaign ID=2 should be owned by admin_id=1"
        print("PASS: Campaign ID=2 owned by admin_id=1")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
