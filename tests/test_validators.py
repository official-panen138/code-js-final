"""Unit tests for domain validators and matching logic."""
import sys
sys.path.insert(0, '/app/backend')

import pytest
from validators import validate_domain_pattern, normalize_domain, is_domain_allowed


class TestValidateDomainPattern:
    """Tests for validate_domain_pattern()"""

    # ── Valid patterns ──
    def test_valid_exact_domain(self):
        valid, msg = validate_domain_pattern("example.com")
        assert valid is True

    def test_valid_subdomain(self):
        valid, msg = validate_domain_pattern("sub.example.com")
        assert valid is True

    def test_valid_deep_subdomain(self):
        valid, msg = validate_domain_pattern("a.b.c.example.com")
        assert valid is True

    def test_valid_wildcard(self):
        valid, msg = validate_domain_pattern("*.example.com")
        assert valid is True

    def test_valid_wildcard_deep(self):
        valid, msg = validate_domain_pattern("*.sub.example.com")
        assert valid is True

    def test_valid_hyphenated_domain(self):
        valid, msg = validate_domain_pattern("my-site.example.com")
        assert valid is True

    def test_valid_numeric_domain(self):
        valid, msg = validate_domain_pattern("123.456.com")
        assert valid is True

    def test_normalizes_to_lowercase(self):
        valid, msg = validate_domain_pattern("Example.COM")
        assert valid is True

    # ── Invalid patterns ──
    def test_reject_empty(self):
        valid, msg = validate_domain_pattern("")
        assert valid is False

    def test_reject_url_with_https(self):
        valid, msg = validate_domain_pattern("https://example.com")
        assert valid is False
        assert "protocol" in msg.lower() or "path" in msg.lower()

    def test_reject_url_with_http(self):
        valid, msg = validate_domain_pattern("http://example.com")
        assert valid is False

    def test_reject_url_with_path(self):
        valid, msg = validate_domain_pattern("example.com/path")
        assert valid is False

    def test_reject_bare_wildcard(self):
        valid, msg = validate_domain_pattern("*")
        assert valid is False

    def test_reject_middle_wildcard(self):
        valid, msg = validate_domain_pattern("a.*.com")
        assert valid is False

    def test_reject_no_dot_localhost(self):
        valid, msg = validate_domain_pattern("localhost")
        assert valid is False

    def test_reject_port(self):
        valid, msg = validate_domain_pattern("example.com:8080")
        assert valid is False

    def test_reject_too_long(self):
        valid, msg = validate_domain_pattern("a" * 256 + ".com")
        assert valid is False

    def test_reject_double_wildcard(self):
        valid, msg = validate_domain_pattern("*.*.example.com")
        assert valid is False

    def test_reject_wildcard_without_dot(self):
        valid, msg = validate_domain_pattern("*example.com")
        assert valid is False


class TestNormalizeDomain:
    """Tests for normalize_domain()"""

    def test_strips_https(self):
        assert normalize_domain("https://example.com") == "example.com"

    def test_strips_http(self):
        assert normalize_domain("http://example.com") == "example.com"

    def test_strips_port(self):
        assert normalize_domain("example.com:8080") == "example.com"

    def test_strips_path(self):
        assert normalize_domain("example.com/path/to/page") == "example.com"

    def test_strips_all(self):
        assert normalize_domain("https://example.com:443/path") == "example.com"

    def test_lowercase(self):
        assert normalize_domain("EXAMPLE.COM") == "example.com"

    def test_empty_string(self):
        assert normalize_domain("") == ""

    def test_none_returns_empty(self):
        assert normalize_domain(None) == ""

    def test_already_clean(self):
        assert normalize_domain("example.com") == "example.com"

    def test_with_referer_url(self):
        assert normalize_domain("https://sub.example.com:3000/page?q=1") == "sub.example.com"


class TestIsDomainAllowed:
    """Tests for is_domain_allowed() - safe matching without regex ReDoS."""

    # ── Exact matches ──
    def test_exact_match(self):
        assert is_domain_allowed("example.com", ["example.com"]) is True

    def test_exact_no_match(self):
        assert is_domain_allowed("evil.com", ["example.com"]) is False

    def test_exact_match_multiple_patterns(self):
        assert is_domain_allowed("b.com", ["a.com", "b.com", "c.com"]) is True

    # ── Wildcard matches ──
    def test_wildcard_matches_subdomain(self):
        assert is_domain_allowed("sub.example.com", ["*.example.com"]) is True

    def test_wildcard_matches_deep_subdomain(self):
        assert is_domain_allowed("a.b.example.com", ["*.example.com"]) is True

    def test_wildcard_does_not_match_base(self):
        """*.example.com should NOT match example.com itself."""
        assert is_domain_allowed("example.com", ["*.example.com"]) is False

    def test_wildcard_does_not_match_unrelated(self):
        assert is_domain_allowed("other.com", ["*.example.com"]) is False

    # ── Empty / edge cases ──
    def test_empty_patterns_deny(self):
        assert is_domain_allowed("example.com", []) is False

    def test_empty_domain_deny(self):
        assert is_domain_allowed("", ["example.com"]) is False

    def test_none_domain_deny(self):
        assert is_domain_allowed(None, ["example.com"]) is False

    # ── Mixed exact + wildcard ──
    def test_mixed_exact_wins(self):
        assert is_domain_allowed("example.com", ["example.com", "*.example.com"]) is True

    def test_mixed_wildcard_wins(self):
        assert is_domain_allowed("sub.example.com", ["other.com", "*.example.com"]) is True

    # ── Domain normalization in matching ──
    def test_strips_origin_protocol(self):
        assert is_domain_allowed("https://example.com", ["example.com"]) is True

    def test_strips_referer_full_url(self):
        assert is_domain_allowed("https://sub.example.com/page", ["*.example.com"]) is True

    # ── Delivery logic scenarios ──
    def test_delivery_project_paused_scenario(self):
        """Even with valid domain and patterns, delivery logic checks project status first."""
        # This tests the function itself - the delivery endpoint checks status separately
        assert is_domain_allowed("example.com", ["example.com"]) is True

    def test_delivery_empty_whitelist_deny(self):
        """Empty whitelist = DENY by default."""
        assert is_domain_allowed("example.com", []) is False


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
