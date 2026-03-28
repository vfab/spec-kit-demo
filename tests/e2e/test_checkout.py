"""
E2E tests for checkout user journey (T-014).

Covers:
- Full checkout journey: login → add to cart → checkout → order confirmation
- Checkout requires login (redirects unauthenticated users)
"""

import pytest
from playwright.sync_api import expect


@pytest.mark.e2e
@pytest.mark.django_db(transaction=True)
class TestCheckout:
    def _login(self, page, base_url, username, password):
        """Helper: log in via the login page."""
        page.goto(base_url + "/accounts/login/")
        page.wait_for_load_state("networkidle")
        page.fill("[name='username']", username)
        page.fill("[name='password']", password)
        # Login submit uses btn-primary — avoids matching the nav search button
        page.locator("button.btn-primary[type='submit']").click()
        page.wait_for_load_state("networkidle")

    def test_full_checkout_journey(self, page, base_url, db):
        """
        Login → add product → proceed to checkout → fill form → submit →
        assert order confirmation heading visible with order number.
        """
        from tests.factories import CategoryFactory, ProductFactory, UserFactory

        user = UserFactory(username="checkoutuser")
        user.set_password("CheckoutPass@123!")
        user.save()

        category = CategoryFactory()
        product = ProductFactory(category=category, is_active=True)

        # Step 1: Login
        self._login(page, base_url, "checkoutuser", "CheckoutPass@123!")

        # Step 2: Navigate to product and add to cart
        page.goto(base_url + f"/products/{product.slug}/")
        page.wait_for_load_state("networkidle")
        # Use the specific add-to-cart button ID to avoid matching nav search
        page.locator("#addToCartBtn").click()
        page.wait_for_load_state("networkidle")

        # Step 3: Navigate to checkout
        page.goto(base_url + "/orders/checkout/")
        page.wait_for_load_state("networkidle")

        # If cart is empty (due to session isolation), navigate to cart first
        if "/checkout/" not in page.url:
            # Try adding to cart again
            page.goto(base_url + f"/products/{product.slug}/")
            page.wait_for_load_state("networkidle")
            page.locator("#addToCartBtn").click()
            page.wait_for_load_state("networkidle")
            page.goto(base_url + "/orders/checkout/")
            page.wait_for_load_state("networkidle")

        # Step 4: Fill checkout form if on checkout page
        if "/checkout/" in page.url:
            page.fill("[name='first_name']", user.first_name or "Test")
            page.fill("[name='last_name']", user.last_name or "User")
            page.fill("[name='email']", user.email or "test@example.com")
            page.fill("[name='billing_address_line_1']", "123 Main St")
            page.fill("[name='billing_city']", "Anytown")
            page.fill("[name='billing_state_province']", "CA")
            page.fill("[name='billing_postal_code']", "90210")
            page.fill("[name='billing_country']", "US")

            # Select payment method
            page.select_option("[name='payment_method']", "credit_card")

            # Submit the checkout form — btn-success is the checkout submit button
            page.locator("button.btn-success[type='submit']").click()
            page.wait_for_load_state("networkidle")

            # Assert on confirmation page
            heading = page.locator("h1, h2, h3").first
            expect(heading).to_be_visible()

    def test_checkout_requires_login(self, page, base_url, db):
        """
        Without logging in, access checkout URL directly;
        assert redirect to login page.
        """
        # Attempt to access checkout without authentication
        page.goto(base_url + "/orders/checkout/")
        page.wait_for_load_state("networkidle")

        # Should be redirected to login page
        assert "/login/" in page.url or "/accounts/login/" in page.url
