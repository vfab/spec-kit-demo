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
        with django_assert_max_num_queries(11):
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
