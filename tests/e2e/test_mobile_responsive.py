"""
E2E tests for mobile viewport responsiveness (T-030).

All tests use the mobile_page fixture (375x667 — iPhone SE portrait).
Zero time.sleep() calls — uses expect(locator).to_be_visible() throughout.
"""

import pytest

from playwright.sync_api import expect


@pytest.mark.e2e
@pytest.mark.django_db(transaction=True)
class TestMobileResponsive:
    def test_homepage_no_horizontal_scroll(self, mobile_page, live_server, db):
        """
        On iPhone SE viewport, the homepage must not have horizontal scrolling.
        document.body.scrollWidth must be <= 375px.
        """
        mobile_page.goto(live_server.url + "/")
        mobile_page.wait_for_load_state("networkidle")

        scroll_width = mobile_page.evaluate("document.body.scrollWidth")
        assert (
            scroll_width <= 375
        ), f"Horizontal scroll detected: body.scrollWidth={scroll_width}px > 375px"

    def test_product_list_accessible_mobile(self, mobile_page, live_server, db):
        """
        On mobile viewport, at least one product card is visible on /products/.
        """
        from tests.factories import CategoryFactory, ProductFactory

        category = CategoryFactory()
        ProductFactory(category=category, is_active=True)

        mobile_page.goto(live_server.url + "/products/")
        mobile_page.wait_for_load_state("networkidle")

        # At least one card or product element should be visible
        card = mobile_page.locator(".card, .product-card, article").first
        expect(card).to_be_visible()

    def test_cart_accessible_mobile(self, mobile_page, live_server, db):
        """
        On mobile viewport, cart page content is visible without layout breaking.
        """
        from tests.factories import CategoryFactory, ProductFactory

        category = CategoryFactory()
        product = ProductFactory(category=category, is_active=True)

        # Add item to cart by navigating to product and submitting form
        mobile_page.goto(live_server.url + f"/products/{product.slug}/")
        mobile_page.wait_for_load_state("networkidle")
        mobile_page.locator(
            "form button[type='submit'], form input[type='submit']"
        ).first.click()
        mobile_page.wait_for_load_state("networkidle")

        # Navigate to cart
        mobile_page.goto(live_server.url + "/orders/cart/")
        mobile_page.wait_for_load_state("networkidle")

        # Main container should be visible
        main_content = mobile_page.locator("main, .container, body").first
        expect(main_content).to_be_visible()

        # No horizontal scroll
        scroll_width = mobile_page.evaluate("document.body.scrollWidth")
        assert (
            scroll_width <= 375
        ), f"Cart page has horizontal scroll: scrollWidth={scroll_width}px > 375px"
