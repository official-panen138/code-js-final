import re


def validate_domain_pattern(pattern: str) -> tuple:
    """Validate a domain pattern for whitelist. Returns (is_valid, message)."""
    if not pattern:
        return False, "Domain pattern cannot be empty"

    pattern = pattern.lower().strip()

    if len(pattern) > 255:
        return False, "Domain pattern too long (max 255)"

    # Reject URLs with protocol or path
    if '://' in pattern or '/' in pattern:
        return False, "Domain pattern must not contain protocol or path"

    # Reject patterns with port
    if ':' in pattern:
        return False, "Domain pattern must not contain port"

    # Reject bare wildcard
    if pattern == '*':
        return False, "Bare wildcard (*) is not allowed"

    if '*' in pattern:
        # Only allow leading *.
        if not pattern.startswith('*.'):
            return False, "Wildcard only allowed as leading *."

        rest = pattern[2:]

        if '*' in rest:
            return False, "Only one wildcard allowed"

        if '.' not in rest:
            return False, "Wildcard domain must have at least one dot"

        if not re.match(r'^[a-z0-9][a-z0-9.-]*[a-z0-9]$', rest):
            return False, "Invalid domain format after wildcard"
    else:
        if '.' not in pattern:
            return False, "Domain must contain at least one dot (no localhost)"

        if not re.match(r'^[a-z0-9][a-z0-9.-]*[a-z0-9]$', pattern):
            return False, "Domain contains invalid characters (only a-z, 0-9, ., - allowed)"

    return True, "Valid"


def normalize_domain(raw: str) -> str:
    """Extract and normalize domain from Origin/Referer header."""
    if not raw:
        return ""

    domain = raw.lower().strip()

    # Strip protocol
    if '://' in domain:
        domain = domain.split('://')[1]

    # Strip port
    if ':' in domain:
        domain = domain.split(':')[0]

    # Strip path
    if '/' in domain:
        domain = domain.split('/')[0]

    return domain


def is_domain_allowed(domain: str, patterns: list) -> bool:
    """Check if domain matches any whitelist patterns. Safe, no regex ReDoS."""
    if not domain or not patterns:
        return False

    domain = normalize_domain(domain)

    exact_patterns = set()
    wildcard_patterns = []

    for p in patterns:
        p = p.lower().strip()
        if p.startswith('*.'):
            wildcard_patterns.append(p)
        else:
            exact_patterns.add(p)

    # Exact match
    if domain in exact_patterns:
        return True

    # Wildcard match
    for p in wildcard_patterns:
        suffix = p[2:]  # Remove *.
        if domain.endswith('.' + suffix) and domain != suffix:
            return True

    return False
