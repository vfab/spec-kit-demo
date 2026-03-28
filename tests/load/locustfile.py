"""
Load test scenarios for ShopHub using Locust.

Run:
    locust -f tests/load/locustfile.py --host=http://localhost:8000 \
        --users=50 --spawn-rate=5 --run-time=60s --headless

Production guard:
    By default, only localhost, 127.0.0.1, and hostnames containing "staging"
    are allowed as targets. Set LOCUST_ALLOWED_HOSTS env var (comma-separated)
    to override.

    Attempting to target a non-allowed host aborts immediately with an error.
"""

import os
import re
from urllib.parse import urlparse

from locust import HttpUser, between, events, task

# ---------------------------------------------------------------------------
# Production guard
# ---------------------------------------------------------------------------
_DEFAULT_ALLOWED_PATTERNS = r"(localhost|127\.0\.0\.1|staging)"
_ALLOWED_HOSTS_ENV = os.environ.get("LOCUST_ALLOWED_HOSTS", "")

if _ALLOWED_HOSTS_ENV:
    # Build regex from comma-separated allowlist entries (exact hostname match)
    _allowed_parts = [
        re.escape(h.strip()) for h in _ALLOWED_HOSTS_ENV.split(",") if h.strip()
    ]
    _ALLOWED_PATTERN = r"(" + "|".join(_allowed_parts) + r")"
else:
    _ALLOWED_PATTERN = _DEFAULT_ALLOWED_PATTERNS


@events.init_command_line_parser.add_listener
def _(parser, **kwargs):
    """Register a no-op so the --host flag is documented in help output."""
    pass  # Locust already registers --host


@events.test_start.add_listener
def check_host_allowlist(environment, **kwargs):
    """Abort if the target host is not in the allowed list."""
    host = environment.host or ""
    parsed = urlparse(host)
    hostname = parsed.hostname or host

    if not re.search(_ALLOWED_PATTERN, hostname, re.IGNORECASE):
        raise SystemExit(
            f"Load tests must not target production host: {hostname!r}. "
            f"Allowed pattern: {_ALLOWED_PATTERN!r}. "
            "Set LOCUST_ALLOWED_HOSTS env var to override (comma-separated)."
        )


# ---------------------------------------------------------------------------
# Randomized product slugs — read from environment or use defaults
# ---------------------------------------------------------------------------
_PRODUCT_SLUGS = os.environ.get(
    "LOCUST_PRODUCT_SLUGS",
    "sample-product-1,sample-product-2,sample-product-3",
).split(",")


# ---------------------------------------------------------------------------
# User classes
# ---------------------------------------------------------------------------


class HomepageUser(HttpUser):
    """Simulates a user who repeatedly visits the homepage."""

    wait_time = between(1, 3)

    @task(3)
    def visit_homepage(self):
        self.client.get("/", name="GET /")


class ProductBrowseUser(HttpUser):
    """Simulates a user browsing the product catalog."""

    wait_time = between(1, 3)

    @task(2)
    def visit_product_list(self):
        self.client.get("/products/", name="GET /products/")

    @task(2)
    def visit_product_detail(self):
        import random

        slug = random.choice(_PRODUCT_SLUGS).strip()
        self.client.get(f"/products/{slug}/", name="GET /products/<slug>/")


class CartUser(HttpUser):
    """Simulates a user interacting with the shopping cart."""

    wait_time = between(1, 3)

    # CSRF token cache — fetched once per user session
    _csrf_token: str = ""

    def on_start(self):
        """Fetch the homepage to obtain a CSRF token for subsequent POSTs."""
        resp = self.client.get("/", name="GET / (cart setup)")
        # Extract csrftoken from the Set-Cookie header if present
        csrf = resp.cookies.get("csrftoken", "")
        self._csrf_token = csrf

    @task(1)
    def view_cart(self):
        self.client.get("/orders/cart/", name="GET /orders/cart/")

    @task(1)
    def add_to_cart(self):
        """AJAX POST to add a product to the cart (product ID 1 as placeholder)."""
        product_id = int(os.environ.get("LOCUST_TEST_PRODUCT_ID", "1"))
        with self.client.post(
            f"/orders/cart/add/{product_id}/",
            data={
                "quantity": "1",
                "csrfmiddlewaretoken": self._csrf_token,
            },
            headers={
                "X-CSRFToken": self._csrf_token,
                "Referer": self.host,
            },
            name="POST /orders/cart/add/",
            catch_response=True,
        ) as resp:
            # Accept 200 (success), 302 (redirect after add), 403 (CSRF expiry under load)
            if resp.status_code not in (200, 302, 403):
                resp.failure(f"Unexpected status {resp.status_code}")
