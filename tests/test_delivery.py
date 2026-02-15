"""Integration tests for JS delivery endpoint and API flows."""
import sys
sys.path.insert(0, '/app/backend')

import pytest
import requests
import os

API_URL = os.environ.get('REACT_APP_BACKEND_URL', 'https://campaign-preview-3.preview.emergentagent.com')
API = f"{API_URL}/api"

# ── Test fixtures ──
TEST_EMAIL = "delivery_test@example.com"
TEST_PASSWORD = "testpass123"


def get_auth_token():
    """Register or login a test user and return JWT token."""
    # Try login first
    res = requests.post(f"{API}/auth/login", json={"email": TEST_EMAIL, "password": TEST_PASSWORD})
    if res.status_code == 200:
        return res.json()["token"]
    # Register if login fails
    res = requests.post(f"{API}/auth/register", json={"email": TEST_EMAIL, "password": TEST_PASSWORD})
    assert res.status_code == 200, f"Registration failed: {res.text}"
    return res.json()["token"]


def auth_headers(token):
    return {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}


class TestDeliveryEndpoint:
    """Tests for GET /api/js/{projectSlug}/{scriptSlug}.js"""

    @classmethod
    def setup_class(cls):
        """Set up test project with script and whitelist."""
        cls.token = get_auth_token()
        headers = auth_headers(cls.token)

        # Create test project
        res = requests.post(f"{API}/projects", json={"name": "Delivery Test Project", "category_id": 1}, headers=headers)
        assert res.status_code == 200
        cls.project = res.json()["project"]
        cls.project_slug = cls.project["slug"]

        # Create test script
        res = requests.post(
            f"{API}/projects/{cls.project['id']}/scripts",
            json={"name": "Test Script", "js_code": 'console.log("delivery test");'},
            headers=headers
        )
        assert res.status_code == 200
        cls.script = res.json()["script"]
        cls.script_slug = cls.script["slug"]

        # Add whitelist entries
        requests.post(f"{API}/projects/{cls.project['id']}/whitelist", json={"domain_pattern": "allowed.com"}, headers=headers)
        requests.post(f"{API}/projects/{cls.project['id']}/whitelist", json={"domain_pattern": "*.trusted.com"}, headers=headers)

    @classmethod
    def teardown_class(cls):
        """Clean up test project."""
        headers = auth_headers(cls.token)
        requests.delete(f"{API}/projects/{cls.project['id']}", headers=headers)

    def _js_url(self):
        return f"{API_URL}/api/js/{self.project_slug}/{self.script_slug}.js"

    def test_allowed_exact_domain(self):
        """Exact domain match serves real JS."""
        res = requests.get(self._js_url(), headers={"Origin": "https://allowed.com"})
        assert res.status_code == 200
        assert 'console.log("delivery test")' in res.text
        assert "noop" not in res.text

    def test_allowed_wildcard_domain(self):
        """Wildcard domain match serves real JS."""
        res = requests.get(self._js_url(), headers={"Origin": "https://sub.trusted.com"})
        assert res.status_code == 200
        assert 'console.log("delivery test")' in res.text

    def test_denied_unknown_domain(self):
        """Unknown domain gets noop JS with 200 status."""
        res = requests.get(self._js_url(), headers={"Origin": "https://evil.com"})
        assert res.status_code == 200
        assert "noop" in res.text
        assert 'console.log("delivery test")' not in res.text

    def test_denied_no_referer(self):
        """No Origin/Referer gets noop JS."""
        res = requests.get(self._js_url())
        assert res.status_code == 200
        assert "noop" in res.text

    def test_denied_referer_fallback(self):
        """Referer header is used when Origin is absent."""
        res = requests.get(self._js_url(), headers={"Referer": "https://allowed.com/page"})
        assert res.status_code == 200
        assert 'console.log("delivery test")' in res.text

    def test_nonexistent_project_noop(self):
        """Non-existent project slug returns noop."""
        res = requests.get(f"{API_URL}/api/js/nonexistent-project-xyz/{self.script_slug}.js")
        assert res.status_code == 200
        assert "noop" in res.text

    def test_nonexistent_script_noop(self):
        """Non-existent script slug returns noop."""
        res = requests.get(f"{API_URL}/api/js/{self.project_slug}/nonexistent-script.js")
        assert res.status_code == 200
        assert "noop" in res.text

    def test_no_js_extension_noop(self):
        """Request without .js extension returns noop."""
        res = requests.get(f"{API_URL}/api/js/{self.project_slug}/{self.script_slug}.txt")
        assert res.status_code == 200
        assert "noop" in res.text

    def test_content_type_javascript(self):
        """Response Content-Type must be application/javascript."""
        res = requests.get(self._js_url(), headers={"Origin": "https://allowed.com"})
        assert "application/javascript" in res.headers.get("content-type", "")

    def test_vary_header(self):
        """Response must include Vary: Origin, Referer."""
        res = requests.get(self._js_url(), headers={"Origin": "https://allowed.com"})
        vary = res.headers.get("vary", "")
        assert "Origin" in vary
        assert "Referer" in vary

    def test_paused_project_noop(self):
        """Paused project returns noop JS."""
        headers = auth_headers(self.token)
        # Pause project
        requests.patch(f"{API}/projects/{self.project['id']}", json={"status": "paused"}, headers=headers)
        res = requests.get(self._js_url(), headers={"Origin": "https://allowed.com"})
        assert res.status_code == 200
        assert "noop" in res.text
        # Restore active
        requests.patch(f"{API}/projects/{self.project['id']}", json={"status": "active"}, headers=headers)

    def test_disabled_script_noop(self):
        """Disabled script returns noop JS."""
        headers = auth_headers(self.token)
        # Disable script
        requests.patch(f"{API}/projects/{self.project['id']}/scripts/{self.script['id']}", json={"status": "disabled"}, headers=headers)
        res = requests.get(self._js_url(), headers={"Origin": "https://allowed.com"})
        assert res.status_code == 200
        assert "noop" in res.text
        # Restore active
        requests.patch(f"{API}/projects/{self.project['id']}/scripts/{self.script['id']}", json={"status": "active"}, headers=headers)


class TestDomainValidationAPI:
    """Tests for domain validation via the whitelist API."""

    @classmethod
    def setup_class(cls):
        cls.token = get_auth_token()
        cls.headers = auth_headers(cls.token)
        # Get a project ID
        res = requests.get(f"{API}/projects", headers=cls.headers)
        projects = res.json()["projects"]
        if projects:
            cls.project_id = projects[0]["id"]
        else:
            res = requests.post(f"{API}/projects", json={"name": "Validation Test", "category_id": 1}, headers=cls.headers)
            cls.project_id = res.json()["project"]["id"]

    def test_reject_https_prefix(self):
        res = requests.post(f"{API}/projects/{self.project_id}/whitelist", json={"domain_pattern": "https://bad.com"}, headers=self.headers)
        assert res.status_code == 400

    def test_reject_bare_wildcard(self):
        res = requests.post(f"{API}/projects/{self.project_id}/whitelist", json={"domain_pattern": "*"}, headers=self.headers)
        assert res.status_code == 400

    def test_reject_localhost(self):
        res = requests.post(f"{API}/projects/{self.project_id}/whitelist", json={"domain_pattern": "localhost"}, headers=self.headers)
        assert res.status_code == 400

    def test_reject_middle_wildcard(self):
        res = requests.post(f"{API}/projects/{self.project_id}/whitelist", json={"domain_pattern": "a.*.com"}, headers=self.headers)
        assert res.status_code == 400

    def test_accept_valid_domain(self):
        res = requests.post(f"{API}/projects/{self.project_id}/whitelist", json={"domain_pattern": "valid-test-domain.com"}, headers=self.headers)
        assert res.status_code == 200
        # Cleanup
        wl_id = res.json()["whitelist"]["id"]
        requests.delete(f"{API}/projects/{self.project_id}/whitelist/{wl_id}", headers=self.headers)

    def test_accept_valid_wildcard(self):
        res = requests.post(f"{API}/projects/{self.project_id}/whitelist", json={"domain_pattern": "*.valid-wildcard.com"}, headers=self.headers)
        assert res.status_code == 200
        wl_id = res.json()["whitelist"]["id"]
        requests.delete(f"{API}/projects/{self.project_id}/whitelist/{wl_id}", headers=self.headers)


class TestDomainTestEndpoint:
    """Tests for POST /api/projects/{id}/test-domain"""

    @classmethod
    def setup_class(cls):
        cls.token = get_auth_token()
        cls.headers = auth_headers(cls.token)
        # Create a project with whitelist
        res = requests.post(f"{API}/projects", json={"name": "Domain Tester Project", "category_id": 1}, headers=cls.headers)
        cls.project = res.json()["project"]
        # Add whitelist
        requests.post(f"{API}/projects/{cls.project['id']}/whitelist", json={"domain_pattern": "allowed-test.com"}, headers=cls.headers)
        requests.post(f"{API}/projects/{cls.project['id']}/whitelist", json={"domain_pattern": "*.wildcard-test.com"}, headers=cls.headers)

    @classmethod
    def teardown_class(cls):
        requests.delete(f"{API}/projects/{cls.project['id']}", headers=cls.headers)

    def test_allowed_domain(self):
        res = requests.post(f"{API}/projects/{self.project['id']}/test-domain", json={"domain": "allowed-test.com"}, headers=self.headers)
        assert res.status_code == 200
        data = res.json()
        assert data["allowed"] is True

    def test_denied_domain(self):
        res = requests.post(f"{API}/projects/{self.project['id']}/test-domain", json={"domain": "denied.com"}, headers=self.headers)
        assert res.status_code == 200
        data = res.json()
        assert data["allowed"] is False

    def test_wildcard_match(self):
        res = requests.post(f"{API}/projects/{self.project['id']}/test-domain", json={"domain": "sub.wildcard-test.com"}, headers=self.headers)
        assert res.status_code == 200
        data = res.json()
        assert data["allowed"] is True

    def test_normalizes_input(self):
        res = requests.post(f"{API}/projects/{self.project['id']}/test-domain", json={"domain": "https://allowed-test.com/page"}, headers=self.headers)
        assert res.status_code == 200
        data = res.json()
        assert data["allowed"] is True
        assert data["normalized_domain"] == "allowed-test.com"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
