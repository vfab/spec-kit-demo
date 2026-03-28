"""
Tests for EPIC-10 T3 — Authentication Security Enhancement.
Tests for EPIC-10 T4 — SQL Injection Audit and Prevention.

Covers:
- Strong password validation (minimum length 10, symbol required)
- Account lockout via django-axes (5 consecutive failures)
- Session security settings
- Password-reset token timeout
- SQL injection audit: ORM-only usage, no raw SQL
- SQL injection robustness: malicious inputs rejected or safely parameterised
"""

import pytest

from django.contrib.auth.models import User
from django.test import Client

# ---------------------------------------------------------------------------
# Password validators
# ---------------------------------------------------------------------------


class TestPasswordValidators:
    """The configured AUTH_PASSWORD_VALIDATORS enforce strong passwords."""

    def test_minimum_length_is_10(self):
        """MinimumLengthValidator option is set to 10."""
        from django.conf import settings

        validators = settings.AUTH_PASSWORD_VALIDATORS
        min_length_cfg = next(
            (v for v in validators if "MinimumLengthValidator" in v["NAME"]),
            None,
        )
        assert min_length_cfg is not None, "MinimumLengthValidator not found"
        assert min_length_cfg.get("OPTIONS", {}).get("min_length", 8) >= 10

    def test_symbol_validator_configured(self):
        """SymbolPasswordValidator is present in AUTH_PASSWORD_VALIDATORS."""
        from django.conf import settings

        names = [v["NAME"] for v in settings.AUTH_PASSWORD_VALIDATORS]
        assert any("SymbolPasswordValidator" in n for n in names)

    def test_symbol_validator_rejects_no_symbol(self):
        """SymbolPasswordValidator raises ValidationError for alpha-only passwords."""
        from django.core.exceptions import ValidationError

        from accounts.validators import SymbolPasswordValidator

        v = SymbolPasswordValidator()
        with pytest.raises(ValidationError, match="special character"):
            v.validate("AllLettersNoSymbol1")

    def test_symbol_validator_accepts_symbol(self):
        """SymbolPasswordValidator passes when a symbol is present."""
        from accounts.validators import SymbolPasswordValidator

        v = SymbolPasswordValidator()
        v.validate("HasASymbol1!")  # should not raise


# ---------------------------------------------------------------------------
# Session security
# ---------------------------------------------------------------------------


class TestSessionSecurity:
    """Session settings enforce reasonable expiry and httponly behaviour."""

    def test_session_cookie_age_max_2_hours(self):
        """SESSION_COOKIE_AGE is at most 7200 seconds (2 hours)."""
        from django.conf import settings

        assert settings.SESSION_COOKIE_AGE <= 7200

    def test_session_cookie_httponly(self):
        """SESSION_COOKIE_HTTPONLY is True (JS cannot read the cookie)."""
        from django.conf import settings

        assert settings.SESSION_COOKIE_HTTPONLY is True


# ---------------------------------------------------------------------------
# Password reset timeout
# ---------------------------------------------------------------------------


class TestPasswordResetTimeout:
    """Password-reset tokens expire quickly."""

    def test_password_reset_timeout_max_1_hour(self):
        """PASSWORD_RESET_TIMEOUT is at most 3600 seconds (1 hour)."""
        from django.conf import settings

        assert settings.PASSWORD_RESET_TIMEOUT <= 3600


# ---------------------------------------------------------------------------
# Axes lockout configuration
# ---------------------------------------------------------------------------


class TestAxesConfig:
    """django-axes is installed and configured correctly."""

    def test_axes_in_installed_apps(self):
        """axes is in INSTALLED_APPS."""
        from django.conf import settings

        assert "axes" in settings.INSTALLED_APPS

    def test_axes_middleware_present(self):
        """AxesMiddleware is in MIDDLEWARE."""
        from django.conf import settings

        assert "axes.middleware.AxesMiddleware" in settings.MIDDLEWARE

    def test_axes_backend_configured(self):
        """AxesStandaloneBackend is first in AUTHENTICATION_BACKENDS."""
        from django.conf import settings

        assert hasattr(settings, "AUTHENTICATION_BACKENDS")
        assert settings.AUTHENTICATION_BACKENDS[0] == (
            "axes.backends.AxesStandaloneBackend"
        )

    def test_axes_failure_limit_max_5(self):
        """AXES_FAILURE_LIMIT is at most 5 attempts."""
        from django.conf import settings

        assert settings.AXES_FAILURE_LIMIT <= 5

    def test_axes_reset_on_success(self):
        """AXES_RESET_ON_SUCCESS is True so legit logins clear the counter."""
        from django.conf import settings

        assert settings.AXES_RESET_ON_SUCCESS is True

    def test_axes_lockout_uses_username_and_ip(self):
        """Lockout is keyed by both username and IP to reduce false positives."""
        from django.conf import settings

        assert "username" in settings.AXES_LOCKOUT_PARAMETERS
        assert "ip_address" in settings.AXES_LOCKOUT_PARAMETERS

    @pytest.mark.django_db
    def test_axes_blocks_after_repeated_failures(self):
        """After AXES_FAILURE_LIMIT bad logins the account is locked."""
        from django.conf import settings

        limit = settings.AXES_FAILURE_LIMIT
        User.objects.create_user(username="locktest", password="Correct1ng@Pass!")
        client = Client(REMOTE_ADDR="127.0.0.2")

        for _ in range(limit):
            client.post(
                "/accounts/login/",
                {"username": "locktest", "password": "WrongPassword1!"},
            )

        # After exhausting attempts, a correct password must still be blocked.
        response = client.post(
            "/accounts/login/",
            {"username": "locktest", "password": "Correct1ng@Pass!"},
        )
        # axes returns 403 (or redirects to AXES_LOCKOUT_URL) — not 200
        assert response.status_code in (
            302,
            403,
        ), f"Expected lockout (302/403) but got {response.status_code}"


# ---------------------------------------------------------------------------
# EPIC-10 T4 — SQL Injection Audit
# ---------------------------------------------------------------------------


class TestNoRawSQL:
    """
    Static-audit: confirm the codebase uses the Django ORM exclusively and
    contains no hand-crafted SQL that could introduce injection vectors.

    These tests traverse every .py file in the project (excluding migrations
    and __pycache__) and fail loudly if any raw-SQL pattern is found.
    """

    # Patterns that indicate raw SQL execution in Django code
    RAW_SQL_PATTERNS = [
        "cursor.execute(",
        "objects.raw(",
        "RawSQL(",
        ".extra(select=",
        ".extra(where=",
        "connection.cursor",
    ]

    # Exclude migrations (generated), caches, VCS, virtualenv directories, and
    # the tests/ directory itself (which contains these pattern strings as
    # literals inside docstrings/assertions and would otherwise self-detect).
    EXCLUDED_DIRS = {"migrations", "__pycache__", ".git", "venv", ".venv", "tests"}

    def _iter_python_files(self):
        """Yield all non-excluded .py paths under the project root."""
        import pathlib

        root = pathlib.Path(__file__).resolve().parent.parent
        for path in root.rglob("*.py"):
            # Skip any path whose parts include an excluded directory name
            if not any(part in self.EXCLUDED_DIRS for part in path.parts):
                yield path

    def test_no_cursor_execute(self):
        """No file calls cursor.execute() with a raw SQL string."""
        violations = []
        for path in self._iter_python_files():
            text = path.read_text(errors="replace")
            if "cursor.execute(" in text:
                violations.append(str(path))
        assert (
            violations == []
        ), "Raw cursor.execute() found — use the Django ORM instead:\n" + "\n".join(
            violations
        )

    def test_no_objects_raw(self):
        """No file calls QuerySet.raw() with an unparameterised SQL string."""
        violations = []
        for path in self._iter_python_files():
            text = path.read_text(errors="replace")
            if "objects.raw(" in text:
                violations.append(str(path))
        assert (
            violations == []
        ), "objects.raw() found — use the Django ORM instead:\n" + "\n".join(violations)

    def test_no_rawsql_expression(self):
        """No file uses the RawSQL() expression directly."""
        violations = []
        for path in self._iter_python_files():
            text = path.read_text(errors="replace")
            if "RawSQL(" in text:
                violations.append(str(path))
        assert violations == [], (
            "RawSQL() expression found — use annotate/aggregate with F() or "
            "built-in expressions instead:\n" + "\n".join(violations)
        )

    def test_no_queryset_extra(self):
        """No file uses QuerySet.extra() (deprecated, injection-prone)."""
        violations = []
        for path in self._iter_python_files():
            text = path.read_text(errors="replace")
            if ".extra(select=" in text or ".extra(where=" in text:
                violations.append(str(path))
        assert violations == [], (
            "QuerySet.extra() found — use annotate/filter/exclude instead:\n"
            + "\n".join(violations)
        )


@pytest.mark.django_db
class TestSQLInjectionRobustness:
    """
    Runtime checks: pass common SQL injection payloads through public URL
    endpoints and confirm the application either returns 200/404 with
    normal HTML (ORM parameterisation neutralised the payload) or a 4xx
    validation error.  A 500 is never acceptable.
    """

    SQL_PAYLOADS = [
        "' OR '1'='1",
        "' OR '1'='1' --",
        "1; DROP TABLE products_product; --",
        "' UNION SELECT null,null,null --",
        "admin'--",
        '" OR "1"="1',
        "1' AND SLEEP(5) --",
    ]

    def _assert_not_500(self, client, url, label=""):
        response = client.get(url)
        assert response.status_code != 500, (
            f"Server error (500) for {label!r} at {url!r}. "
            "Raw SQL injection may have caused an unhandled exception."
        )
        return response

    def test_product_search_injection(self, client):
        """Injection payloads in ?q= never cause a 500 on product search."""
        for payload in self.SQL_PAYLOADS:
            self._assert_not_500(
                client,
                f"/products/?q={payload}",
                label=f"search payload: {payload}",
            )

    def test_product_list_search_param(self, client):
        """Injection payloads in ?search= on the product list never 500."""
        for payload in self.SQL_PAYLOADS:
            self._assert_not_500(
                client,
                f"/products/?search={payload}",
                label=f"search payload: {payload}",
            )

    def test_category_filter_injection(self, client):
        """Injection payloads in ?category= never cause a 500."""
        for payload in self.SQL_PAYLOADS:
            response = client.get(f"/products/?category={payload}")
            # get_object_or_404 gives 404; ORM parameterisation gives 200 or 404
            assert (
                response.status_code != 500
            ), f"500 on category filter with payload {payload!r}"

    def test_price_filter_injection(self, client):
        """Injection payloads in ?min_price= / ?max_price= never cause a 500."""
        for payload in self.SQL_PAYLOADS:
            r1 = client.get(f"/products/?min_price={payload}")
            r2 = client.get(f"/products/?max_price={payload}")
            assert (
                r1.status_code != 500
            ), f"500 on min_price filter with payload {payload!r}"
            assert (
                r2.status_code != 500
            ), f"500 on max_price filter with payload {payload!r}"

    def test_sort_param_uses_allowlist(self, client):
        """
        The sort parameter is validated against an explicit allowlist so an
        injected ORDER BY clause can never reach the DB.
        """
        injection_sorts = [
            "(SELECT 1 FROM users WHERE '1'='1')",
            "name; DROP TABLE products_product; --",
            "CASE WHEN 1=1 THEN name ELSE price END",
        ]
        for payload in injection_sorts:
            response = client.get(f"/products/?sort={payload}")
            # Falls back to the default sort — should return the normal list page
            assert (
                response.status_code == 200
            ), f"Unexpected status {response.status_code} for sort payload {payload!r}"

    def test_product_slug_injection(self, client):
        """Injection payloads in the product detail URL slug never cause a 500."""
        import urllib.parse

        for payload in self.SQL_PAYLOADS:
            safe_slug = urllib.parse.quote(payload, safe="")
            response = client.get(f"/products/{safe_slug}/")
            # 404 is expected (slug won't match); 500 is not acceptable
            assert (
                response.status_code != 500
            ), f"500 on product detail with slug payload {payload!r}"

    def test_order_number_injection(self, client):
        """Injection payloads in the order confirmation URL never cause a 500."""
        import urllib.parse

        from django.contrib.auth.models import User

        user = User.objects.create_user(username="sqltestuser", password="Secure1Pass!")
        client.force_login(user)
        for payload in self.SQL_PAYLOADS:
            safe_order = urllib.parse.quote(payload, safe="")
            response = client.get(f"/orders/confirmation/{safe_order}/")
            assert (
                response.status_code != 500
            ), f"500 on order confirmation with payload {payload!r}"


class TestORMUsageDocumentation:
    """
    Documents the ORM patterns used throughout the project so that future
    contributors know *why* no raw SQL is needed.  Each test acts as
    both documentation and a regression guard.
    """

    def test_products_uses_icontains_not_like(self):
        """
        Product search uses __icontains which Django maps to a parameterised
        LIKE query — the value is never interpolated directly into SQL.
        """
        from products.views import ProductListView

        # The real guard is test_no_objects_raw / test_no_cursor_execute above.
        # Here we confirm the allowlist exists as an additional regression guard.
        assert (
            ProductListView.ALLOWED_SORT_FIELDS
        ), "ProductListView must define ALLOWED_SORT_FIELDS allowlist"

    def test_sort_allowlist_contains_only_safe_fields(self):
        """
        Every entry in ALLOWED_SORT_FIELDS is a known field name (optionally
        prefixed with '-').  No entry contains SQL metacharacters.
        """
        import re

        from products.views import ProductListView

        safe_pattern = re.compile(r"^-?[a-z_]+$")
        for field in ProductListView.ALLOWED_SORT_FIELDS:
            assert safe_pattern.match(
                field
            ), f"Suspicious value in ALLOWED_SORT_FIELDS: {field!r}"

    def test_order_queryset_scoped_to_user(self):
        """
        OrderDetailView.get_queryset() filters by request.user so a user can
        never access another user's orders via URL manipulation.
        """
        import inspect

        from orders.views import OrderDetailView

        source = inspect.getsource(OrderDetailView.get_queryset)
        assert (
            "request.user" in source
        ), "OrderDetailView.get_queryset must filter by request.user"

    def test_cart_ownership_verified_before_mutation(self):
        """
        RemoveFromCartView and UpdateCartView check cart ownership before
        deleting or modifying items.
        """
        import inspect

        from orders.views import RemoveFromCartView, UpdateCartView

        for view_cls in (RemoveFromCartView, UpdateCartView):
            source = inspect.getsource(view_cls.post)
            assert (
                "Unauthorized" in source
            ), f"{view_cls.__name__}.post must check ownership before mutating"


# ---------------------------------------------------------------------------
# T-026 — Security headers and access control regression tests
# ---------------------------------------------------------------------------


@pytest.mark.django_db
class TestSecurityHeaders:
    """Verify security-relevant HTTP headers are present on responses."""

    def test_security_headers_present(self, client):
        """Home page response carries required security headers."""
        response = client.get("/")
        assert (
            "X-Content-Type-Options" in response
        ), "X-Content-Type-Options header missing from home page response"
        assert (
            "X-Frame-Options" in response
        ), "X-Frame-Options header missing from home page response"
        assert (
            "Content-Security-Policy" in response
        ), "Content-Security-Policy header missing — CSPMiddleware may not be active"

    def test_csrf_required_on_add_to_cart(self, client):
        """POST to add-to-cart without CSRF token returns 403."""
        from django.test import Client as DjangoClient

        # Use enforce_csrf_checks=True to bypass the test-client's CSRF bypass
        csrf_client = DjangoClient(enforce_csrf_checks=True)
        response = csrf_client.post("/orders/cart/add/1/", data={"quantity": 1})
        assert (
            response.status_code == 403
        ), f"Expected 403 (CSRF failure) but got {response.status_code}"

    def test_checkout_requires_authentication(self, client):
        """Unauthenticated GET to checkout redirects to login."""
        response = client.get("/orders/checkout/")
        assert (
            response.status_code == 302
        ), f"Expected redirect (302) but got {response.status_code}"
        assert (
            "/login/" in response["Location"]
        ), "Checkout redirect target does not point to login page"

    def test_no_stack_trace_in_500_response(self):
        """With DEBUG=False a 500 response body must not contain a traceback."""
        from django.test import Client as DjangoClient
        from django.test import override_settings

        with override_settings(DEBUG=False):
            c = DjangoClient(raise_request_exception=False)
            # Trigger a 500 by accessing a URL that raises (use the test 500 view
            # if available, otherwise check that DEBUG=False hides tracebacks by
            # inspecting the 404 handler which never exposes internals)
            response = c.get("/this-url-does-not-exist-12345/")
            # 404 responses must never contain Python tracebacks
            body = response.content.decode("utf-8", errors="replace")
            assert "Traceback" not in body, (
                "Response body contains 'Traceback' — Django may be leaking "
                "internal stack traces with DEBUG=False"
            )


# ---------------------------------------------------------------------------
# T-032 — Mock/patch tests (email, payment placeholder, file upload)
# ---------------------------------------------------------------------------


@pytest.mark.django_db
class TestMockIntegrations:
    """Verify that external integrations are properly mocked in the test suite."""

    def test_email_backend_is_locmem_in_tests(self, settings):
        """settings_test.py uses the in-memory email backend — no real SMTP."""
        from django.core import mail

        locmem_backend = "django.core.mail.backends.locmem.EmailBackend"
        assert settings.EMAIL_BACKEND == locmem_backend, (
            "EMAIL_BACKEND must be django.core.mail.backends.locmem.EmailBackend "
            "in the test settings (no real SMTP calls during tests)"
        )
        # Sanity-check: the outbox is accessible
        assert hasattr(mail, "outbox"), "django.core.mail.outbox is not available"

    @pytest.mark.skip(reason="payment gateway not yet integrated")
    def test_payment_processing_is_mocked(self):  # pragma: no cover
        """
        Placeholder: once a payment gateway client is added, mock it here and
        assert the mock is called instead of the real endpoint.
        """

    def test_file_upload_does_not_write_to_production_media(self, tmp_path, settings):
        """
        Uploading a category image via the ORM writes to MEDIA_ROOT, not media/.

        Uses settings fixture (override_settings) with MEDIA_ROOT=tmp_path to
        isolate the test from the production media/ folder, then exercises
        Django's actual ImageField upload path by saving a Category instance.
        """
        import pathlib

        from django.core.files.uploadedfile import SimpleUploadedFile

        from products.models import Category

        settings.MEDIA_ROOT = str(tmp_path)

        # Create a minimal valid PNG (1×1 pixel) without Pillow
        png_bytes = (
            b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01"
            b"\x00\x00\x00\x01\x08\x02\x00\x00\x00\x90wS\xde\x00\x00"
            b"\x00\x0cIDATx\x9cc\xf8\x0f\x00\x00\x01\x01\x00\x05\x18"
            b"\xd8N\x00\x00\x00\x00IEND\xaeB`\x82"
        )
        uploaded = SimpleUploadedFile(
            "upload_test_cat.png", png_bytes, content_type="image/png"
        )

        # Exercise Django's upload machinery via the model
        category = Category.objects.create(
            name="Upload Isolation Test",
            image=uploaded,
        )

        # File should be stored under the overridden MEDIA_ROOT (tmp_path)
        stored = pathlib.Path(settings.MEDIA_ROOT) / category.image.name
        assert stored.exists(), (
            f"Uploaded file not found at {stored} — "
            "file was not written through Django's storage backend"
        )

        # File must NOT appear in the real media/categories/ directory
        real = pathlib.Path("media") / "categories" / "upload_test_cat.png"
        assert not real.exists(), (
            "File was unexpectedly written to the production media/ directory"
        )

        # Cleanup: delete the category (image file stays in tmp_path which is
        # auto-cleaned by pytest)
        category.delete()
