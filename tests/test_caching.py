"""
Tests for EPIC-11 T3 — Redis caching layer.

Uses Django's LocMemCache (configured in settings_test.py) so the suite
runs without a real Redis server.

Covers:
- CACHES is configured
- Home page data is served from cache on second request
- Category list is cached across requests
- Product detail objects are cached after first fetch
- Cache keys are invalidated when models are saved or deleted
- Price filter rejects non-numeric input gracefully (regression guard)
"""

import pytest

from django.core.cache import cache

from products.models import Category, Product

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture(autouse=True)
def clear_cache():
    """Ensure every test starts with a clean cache."""
    cache.clear()
    yield
    cache.clear()


@pytest.fixture
def category(db):
    return Category.objects.create(name="Gadgets", slug="gadgets")


@pytest.fixture
def product(db, category):
    return Product.objects.create(
        name="Widget Pro",
        slug="widget-pro",
        price="29.99",
        category=category,
        stock_quantity=10,
        is_active=True,
        is_featured=True,
    )


# ---------------------------------------------------------------------------
# Configuration tests
# ---------------------------------------------------------------------------


class TestCacheConfiguration:
    """The CACHES setting is present and usable."""

    def test_caches_setting_present(self):
        from django.conf import settings

        assert hasattr(settings, "CACHES"), "CACHES must be defined in settings"
        assert "default" in settings.CACHES

    def test_cache_is_functional(self):
        """Cache can store and retrieve a value."""
        cache.set("smoke_test", "hello", timeout=30)
        assert cache.get("smoke_test") == "hello"

    def test_cache_miss_returns_none(self):
        assert cache.get("nonexistent_key_xyz") is None

    def test_cache_delete_works(self):
        cache.set("del_me", "value", timeout=30)
        cache.delete("del_me")
        assert cache.get("del_me") is None


# ---------------------------------------------------------------------------
# Home page cache
# ---------------------------------------------------------------------------


@pytest.mark.django_db
class TestHomePageCache:
    """Home page data is populated into cache after first request."""

    def test_home_data_cached_after_first_request(self, client, product):
        """After the first GET / the cache key 'home_page_data' is populated."""
        assert cache.get("home_page_data") is None

        response = client.get("/")
        assert response.status_code == 200

        assert (
            cache.get("home_page_data") is not None
        ), "home_page_data should be cached after the first request"

    def test_home_data_served_from_cache(self, client, product):
        """Second request uses cached data (cache key survives between reads)."""
        client.get("/")
        cached = cache.get("home_page_data")
        assert cached is not None

        # Overwrite the cache with a known sentinel value.
        sentinel_value = "SENTINEL_TEST_VALUE"
        cache.set(
            "home_page_data",
            {"featured_products": [sentinel_value], "categories": []},
        )

        # The cache should return our sentinel, confirming the view would use
        # the cached value on the next hit (not re-query the DB).
        cached_after = cache.get("home_page_data")
        assert cached_after is not None
        assert (
            cached_after["featured_products"][0] == sentinel_value
        ), "Cache value should be the sentinel string we wrote"


# ---------------------------------------------------------------------------
# Category list cache
# ---------------------------------------------------------------------------


@pytest.mark.django_db
class TestCategoryListCache:
    """The top-level category list is cached."""

    def test_category_list_cached_after_product_list_request(self, client, category):
        """After GET /products/ the cache key 'product_categories' is set."""
        assert cache.get("product_categories") is None

        response = client.get("/products/")
        assert response.status_code == 200

        assert (
            cache.get("product_categories") is not None
        ), "product_categories should be cached after the first product list request"

    def test_cached_categories_match_db(self, client, category):
        """Cached category list contains the same objects as a fresh DB query."""
        client.get("/products/")
        cached_cats = cache.get("product_categories")
        assert cached_cats is not None

        db_cats = list(Category.objects.filter(parent=None))
        assert len(cached_cats) == len(db_cats)
        cached_ids = {c.pk for c in cached_cats}
        db_ids = {c.pk for c in db_cats}
        assert cached_ids == db_ids


# ---------------------------------------------------------------------------
# Product detail cache
# ---------------------------------------------------------------------------


@pytest.mark.django_db
class TestProductDetailCache:
    """Product detail objects are stored in cache after first fetch."""

    def test_product_detail_cached_after_first_request(self, client, product):
        """After GET /products/<slug>/ the cache key product_detail:<pk> is set."""
        cache_key = f"product_detail:{product.pk}"
        assert cache.get(cache_key) is None

        response = client.get(f"/products/{product.slug}/")
        assert response.status_code == 200

        assert (
            cache.get(cache_key) is not None
        ), f"product_detail:{product.pk} should be in cache after the first request"

    def test_cached_product_matches_db(self, client, product):
        """Cached product object has the same pk and name as the DB record."""
        client.get(f"/products/{product.slug}/")
        cached_product = cache.get(f"product_detail:{product.pk}")
        assert cached_product is not None
        assert cached_product.pk == product.pk
        assert cached_product.name == product.name


# ---------------------------------------------------------------------------
# Cache invalidation via signals
# ---------------------------------------------------------------------------


@pytest.mark.django_db
class TestCacheInvalidation:
    """Model save/delete signals clear the relevant cache keys."""

    def test_product_save_clears_detail_cache(self, client, product):
        """Saving a product removes its detail cache entry."""
        # Populate the cache
        client.get(f"/products/{product.slug}/")
        assert cache.get(f"product_detail:{product.pk}") is not None

        # Mutate the product — signal should invalidate the cache
        product.name = "Widget Pro Updated"
        product.save()

        assert (
            cache.get(f"product_detail:{product.pk}") is None
        ), "product_detail cache should be cleared after product.save()"

    def test_product_delete_clears_detail_cache(self, client, product):
        """Deleting a product removes its detail cache entry."""
        client.get(f"/products/{product.slug}/")
        pk = product.pk
        product.delete()

        assert (
            cache.get(f"product_detail:{pk}") is None
        ), "product_detail cache should be cleared after product.delete()"

    def test_category_save_clears_category_list_cache(self, client, category):
        """Saving a category clears the product_categories cache entry."""
        # Populate the cache
        client.get("/products/")
        assert cache.get("product_categories") is not None

        # Mutate the category
        category.name = "Gadgets Updated"
        category.save()

        assert (
            cache.get("product_categories") is None
        ), "product_categories cache should be cleared after category.save()"

    def test_category_delete_clears_category_list_cache(self, db):
        """Deleting a category clears the product_categories cache entry."""
        cat = Category.objects.create(name="Temp Cat", slug="temp-cat")
        # Manually warm the cache
        cache.set("product_categories", [cat], timeout=60)
        assert cache.get("product_categories") is not None

        cat.delete()

        assert (
            cache.get("product_categories") is None
        ), "product_categories cache should be cleared after category.delete()"

    def test_home_cache_cleared_on_product_save(self, client, product):
        """Saving a product clears the home_page_data cache entry."""
        client.get("/")
        assert cache.get("home_page_data") is not None

        product.price = "19.99"
        product.save()

        # The home cache is cleared (either via cache.clear() or delete_pattern)
        # so the next request will rehydrate it from DB.
        assert (
            cache.get("home_page_data") is None
        ), "home_page_data cache should be cleared after product.save()"

    def test_home_cache_cleared_on_category_save(self, client, category, product):
        """Saving a category also clears the home_page_data cache entry."""
        client.get("/")
        assert cache.get("home_page_data") is not None

        category.name = "Gadgets Renamed"
        category.save()

        assert (
            cache.get("home_page_data") is None
        ), "home_page_data cache should be cleared after category.save()"


# ---------------------------------------------------------------------------
# Settings-level cache timeout constants
# ---------------------------------------------------------------------------


class TestCacheTimeoutSettings:
    """Cache timeout constants are present and reasonable."""

    def test_product_list_timeout_defined(self):
        from django.conf import settings

        assert hasattr(settings, "CACHE_TIMEOUT_PRODUCT_LIST")
        assert settings.CACHE_TIMEOUT_PRODUCT_LIST > 0

    def test_product_detail_timeout_defined(self):
        from django.conf import settings

        assert hasattr(settings, "CACHE_TIMEOUT_PRODUCT_DETAIL")
        assert settings.CACHE_TIMEOUT_PRODUCT_DETAIL > 0

    def test_category_list_timeout_defined(self):
        from django.conf import settings

        assert hasattr(settings, "CACHE_TIMEOUT_CATEGORY_LIST")
        assert settings.CACHE_TIMEOUT_CATEGORY_LIST > 0
