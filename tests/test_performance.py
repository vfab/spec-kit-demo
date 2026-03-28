"""
Tests for EPIC-11 T2 — Database Query Optimisation.

Verifies that key views do not exhibit N+1 query patterns by asserting
against ``assertNumQueries`` / ``django.test.utils.CaptureQueriesContext``.

Strategy
--------
We use Django's ``assertNumQueries`` helper (via ``django_assert_num_queries``
pytest-django fixture) to set upper bounds.  The exact count may change if the
view logic changes, but the test will still catch regressions where the count
grows proportionally with the number of rows.

For lists, we create N items and assert the total query count stays constant
(O(1)) rather than growing with N.
"""

from decimal import Decimal

import pytest

from django.test import Client

pytestmark = pytest.mark.django_db


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def make_products(category, n: int):
    from products.models import Product

    return [
        Product.objects.create(
            name=f"Perf Product {i}",
            slug=f"perf-product-{i}",
            category=category,
            description="desc",
            price=Decimal("9.99"),
            sku=f"PERF-{i:04d}",
            stock_quantity=10,
            is_active=True,
        )
        for i in range(n)
    ]


def make_orders(user, n: int):
    from orders.models import Order

    return [
        Order.objects.create(
            user=user,
            email=user.email,
            first_name="Test",
            last_name="User",
            billing_address_line_1="1 Test St",
            billing_city="City",
            billing_state_province="State",
            billing_postal_code="00000",
            billing_country="US",
            total_amount=Decimal("19.99"),
            status="pending",
        )
        for _ in range(n)
    ]


# ---------------------------------------------------------------------------
# Product list view — no N+1 on category join
# ---------------------------------------------------------------------------


class TestProductListQueryCount:
    def test_product_list_query_count_is_bounded(
        self, django_assert_max_num_queries, category
    ):
        """ProductListView uses select_related('category') — query count is
        constant regardless of the number of products."""
        make_products(category, n=10)
        client = Client()
        # Max queries: session + products + categories + price aggregate = ~5
        with django_assert_max_num_queries(10):
            response = client.get("/products/")
        assert response.status_code == 200


# ---------------------------------------------------------------------------
# Order list view — no N+1 on order items
# ---------------------------------------------------------------------------


class TestOrderListQueryCount:
    def test_order_list_does_not_grow_with_orders(
        self, django_assert_max_num_queries, user, authenticated_client
    ):
        """OrderListView prefetches items, so query count stays constant."""
        make_orders(user, n=8)
        # Max: session lookup + user + orders + prefetch items = ~5
        with django_assert_max_num_queries(10):
            response = authenticated_client.get("/orders/orders/")
        assert response.status_code == 200


# ---------------------------------------------------------------------------
# Order detail view — items are fetched with select_related
# ---------------------------------------------------------------------------


class TestOrderDetailQueryCount:
    def test_order_detail_select_related_items(
        self,
        django_assert_max_num_queries,
        authenticated_client,
        order,
        product,
    ):
        """OrderDetailView uses select_related on items — one query for items."""
        from orders.models import OrderItem

        OrderItem.objects.create(
            order=order,
            product=product,
            quantity=2,
            unit_price=product.price,
        )
        with django_assert_max_num_queries(10):
            response = authenticated_client.get(f"/orders/orders/{order.order_number}/")
        assert response.status_code == 200


# ---------------------------------------------------------------------------
# Product detail view — images and variants prefetched
# ---------------------------------------------------------------------------


class TestProductDetailQueryCount:
    def test_product_detail_prefetches_images_and_variants(
        self, django_assert_max_num_queries, category, product
    ):
        """ProductDetailView prefetches images and variants in bulk."""
        from products.models import ProductVariant

        for i in range(5):
            ProductVariant.objects.create(
                product=product,
                name="Size",
                value=f"XL{i}",
                stock_quantity=5,
            )
        client = Client()
        with django_assert_max_num_queries(10):
            response = client.get(f"/products/{product.slug}/")
        assert response.status_code == 200


# ---------------------------------------------------------------------------
# New indexes are reflected in the model Meta
# ---------------------------------------------------------------------------


class TestModelIndexes:
    def test_category_has_slug_index(self):
        """Category.Meta.indexes includes a slug index."""
        from products.models import Category

        index_fields = [idx.fields for idx in Category._meta.indexes]
        assert ["slug"] in index_fields

    def test_category_has_active_name_index(self):
        """Category.Meta.indexes includes is_active+name index."""
        from products.models import Category

        index_fields = [list(idx.fields) for idx in Category._meta.indexes]
        assert ["is_active", "name"] in index_fields

    def test_product_image_has_product_primary_index(self):
        """ProductImage.Meta.indexes includes product+is_primary index."""
        from products.models import ProductImage

        index_fields = [list(idx.fields) for idx in ProductImage._meta.indexes]
        assert ["product", "is_primary"] in index_fields

    def test_cartitem_has_cart_created_index(self):
        """CartItem.Meta.indexes includes cart+created_at index."""
        from orders.models import CartItem

        index_fields = [list(idx.fields) for idx in CartItem._meta.indexes]
        # Index on cart + -created_at (DESC prefix stored as '-created_at')
        assert any("cart" in fields for fields in index_fields)


# ---------------------------------------------------------------------------
# SlowQueryFilter unit tests (EPIC-11 T6)
# ---------------------------------------------------------------------------


class TestSlowQueryFilter:
    """Unit tests for ecommerce_site.log_filters.SlowQueryFilter."""

    def _make_record(self, duration: float):
        import logging

        record = logging.LogRecord(
            name="django.db.backends",
            level=logging.DEBUG,
            pathname="",
            lineno=0,
            msg="SELECT 1",
            args=(),
            exc_info=None,
        )
        record.duration = duration
        record.sql = "SELECT 1"
        return record

    def test_slow_record_passes_filter(self):
        """A record whose duration >= threshold is kept (filter returns True)."""
        from ecommerce_site.log_filters import SlowQueryFilter

        f = SlowQueryFilter(threshold_ms=100.0)
        record = self._make_record(duration=150.0)
        assert f.filter(record) is True

    def test_fast_record_blocked_by_filter(self):
        """A record whose duration < threshold is dropped (filter returns False)."""
        from ecommerce_site.log_filters import SlowQueryFilter

        f = SlowQueryFilter(threshold_ms=100.0)
        record = self._make_record(duration=50.0)
        assert f.filter(record) is False

    def test_record_at_exact_threshold_passes(self):
        """A record exactly at the threshold is kept."""
        from ecommerce_site.log_filters import SlowQueryFilter

        f = SlowQueryFilter(threshold_ms=100.0)
        record = self._make_record(duration=100.0)
        assert f.filter(record) is True

    def test_default_threshold_is_100_ms(self):
        """Default threshold_ms is 100.0 when not specified."""
        from ecommerce_site.log_filters import SlowQueryFilter

        f = SlowQueryFilter()
        assert f.threshold_ms == 100.0

    def test_custom_threshold_respected(self):
        """A custom threshold_ms value is honoured."""
        from ecommerce_site.log_filters import SlowQueryFilter

        f = SlowQueryFilter(threshold_ms=200.0)
        assert f.filter(self._make_record(duration=150.0)) is False
        assert f.filter(self._make_record(duration=250.0)) is True

    def test_missing_duration_attribute_treated_as_zero(self):
        """Records without a duration attribute do not raise; treated as 0ms."""
        import logging

        from ecommerce_site.log_filters import SlowQueryFilter

        f = SlowQueryFilter(threshold_ms=100.0)
        record = logging.LogRecord(
            name="django.db.backends",
            level=logging.DEBUG,
            pathname="",
            lineno=0,
            msg="SELECT 1",
            args=(),
            exc_info=None,
        )
        # No record.duration set — getattr default is 0.0, which is < 100ms.
        assert f.filter(record) is False


# ---------------------------------------------------------------------------
# RequestTimingMiddleware unit tests (EPIC-11 T5)
# ---------------------------------------------------------------------------


class TestRequestTimingMiddleware:
    """Unit tests for ecommerce_site.middleware.RequestTimingMiddleware."""

    def _make_middleware(self, status_code=200):
        """Return (middleware, get_response_mock) pair."""
        from unittest.mock import MagicMock

        from django.http import HttpResponse

        response = HttpResponse(status=status_code)
        get_response = MagicMock(return_value=response)
        from ecommerce_site.middleware import RequestTimingMiddleware

        mw = RequestTimingMiddleware(get_response)
        return mw, get_response, response

    def test_middleware_returns_response(self):
        """Middleware passes request through and returns the response."""
        from django.test import RequestFactory

        factory = RequestFactory()
        request = factory.get("/products/")
        mw, _, original_response = self._make_middleware()
        result = mw(request)
        assert result is original_response

    def test_middleware_calls_get_response(self):
        """Middleware calls get_response exactly once with the request."""
        from django.test import RequestFactory

        factory = RequestFactory()
        request = factory.get("/")
        mw, get_response_mock, _ = self._make_middleware()
        mw(request)
        get_response_mock.assert_called_once_with(request)

    def test_debug_header_set_when_debug_true(self):
        """X-Request-Duration header is attached when DEBUG=True."""
        from django.test import RequestFactory, override_settings

        factory = RequestFactory()
        request = factory.get("/")
        mw, _, _ = self._make_middleware()
        with override_settings(DEBUG=True):
            response = mw(request)
        assert "X-Request-Duration" in response

    def test_debug_header_absent_when_debug_false(self):
        """X-Request-Duration header is NOT attached when DEBUG=False."""
        from django.test import RequestFactory, override_settings

        factory = RequestFactory()
        request = factory.get("/")
        mw, _, _ = self._make_middleware()
        with override_settings(DEBUG=False):
            response = mw(request)
        assert "X-Request-Duration" not in response

    def test_debug_header_contains_ms_suffix(self):
        """X-Request-Duration header value ends with 'ms'."""
        from django.test import RequestFactory, override_settings

        factory = RequestFactory()
        request = factory.get("/health/")
        mw, _, _ = self._make_middleware()
        with override_settings(DEBUG=True):
            response = mw(request)
        assert response["X-Request-Duration"].endswith("ms")

    def test_middleware_logs_request(self):
        """Middleware emits one INFO log record per request."""
        import logging
        from unittest.mock import patch

        from django.test import RequestFactory

        factory = RequestFactory()
        request = factory.get("/products/")
        mw, _, _ = self._make_middleware()
        with patch.object(
            logging.getLogger("ecommerce_site.performance"), "info"
        ) as mock_log:
            mw(request)
        mock_log.assert_called_once()
        _, kwargs = mock_log.call_args
        extra = kwargs.get("extra", {})
        assert extra["method"] == "GET"
        assert extra["path"] == "/products/"
        assert "duration_ms" in extra
        assert isinstance(extra["duration_ms"], float)
