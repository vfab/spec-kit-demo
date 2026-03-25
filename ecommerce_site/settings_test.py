"""
Test settings for ShopHub.

Inherits all production-like settings and overrides only what is needed
to make the test suite fast, isolated, and deterministic.

Usage (automatic via pytest.ini):
    DJANGO_SETTINGS_MODULE = ecommerce_site.settings_test
"""

import os

# Ensure SECRET_KEY is non-empty before settings.py is imported.
# os.environ.setdefault() would leave an existing empty-string value (e.g. an
# unset GitHub Actions secret that resolves to "") unchanged, so we check
# truthiness explicitly instead.
if not os.environ.get("SECRET_KEY"):  # noqa: S105
    os.environ["SECRET_KEY"] = "test-secret-key-for-tooling-only"  # noqa: S105

from .settings import *  # noqa: E402, F401, F403

# ---------------------------------------------------------------------------
# Database — use in-memory SQLite so tests never touch db.sqlite3 on disk.
# ---------------------------------------------------------------------------
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": ":memory:",
    }
}

# Fast password hashing in tests — do not use in production
PASSWORD_HASHERS = ["django.contrib.auth.hashers.MD5PasswordHasher"]

DEBUG = True

# ---------------------------------------------------------------------------
# Axes — disable lockout in the test suite.
# axes.backends.AxesStandaloneBackend.authenticate() requires a real HTTP
# request object; bare client.login() / authenticate() calls in tests do not
# supply one and raise AxesBackendRequestParameterRequired.
# Axes behaviour is covered explicitly in tests/test_security.py which uses
# the live login endpoint (POST /accounts/login/) so it works correctly even
# with Axes enabled at runtime.
# ---------------------------------------------------------------------------
AXES_ENABLED = False

# ---------------------------------------------------------------------------
# Cache (EPIC-11 T3) — use in-process LocMemCache so tests never need Redis.
# Per-test isolation is handled by the cache.clear() in the cache test fixtures.
# ---------------------------------------------------------------------------
CACHES = {
    "default": {
        "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
    }
}
# Use very short timeouts in tests so stale-cache scenarios can be verified
# without sleeping.
CACHE_TIMEOUT_PRODUCT_LIST = 60
CACHE_TIMEOUT_PRODUCT_DETAIL = 60
CACHE_TIMEOUT_CATEGORY_LIST = 60
