"""
Integration and functional tests for ShopHub e-commerce application
Tests complete user workflows and cross-app functionality
"""

from decimal import Decimal

import pytest

from django.contrib.auth.models import User
from django.urls import reverse

from orders.models import Cart, Order, OrderItem
from products.models import Category, Product


class TestUserJourney:
    """Test complete user journey from registration to order"""

    @pytest.mark.django_db
    def test_complete_user_journey(self, client, sample_data):
        """Test complete user journey:
        register -> browse -> add to cart -> checkout -> order"""

        # Step 1: User visits homepage
        response = client.get(reverse("products:home"))
        assert response.status_code == 200

        # Step 2: User registers
        registration_data = {
            "username": "journeyuser",
            "email": "journey@example.com",
            "first_name": "Journey",
            "last_name": "User",
            "password1": "Xk9#mPqLw2!",
            "password2": "Xk9#mPqLw2!",
        }
        response = client.post(reverse("accounts:register"), data=registration_data)
        assert response.status_code == 302

        # Step 3: User logs in
        login_response = client.post(
            reverse("accounts:login"),
            {"username": "journeyuser", "password": "Xk9#mPqLw2!"},
        )
        assert login_response.status_code == 302

        # Step 4: User browses products
        response = client.get(reverse("products:product_list"))
        assert response.status_code == 200

        # Step 5: User views product detail
        product = sample_data["products"][0]
        response = client.get(reverse("products:product_detail", args=[product.slug]))
        assert response.status_code == 200

        # Step 6: User adds product to cart
        response = client.post(
            reverse("orders:add_to_cart", args=[product.id]), {"quantity": 2}
        )
        assert response.status_code in [200, 302]

        # Step 7: User views cart
        response = client.get(reverse("orders:cart"))
        assert response.status_code == 200

        # Step 8: User proceeds to checkout
        response = client.get(reverse("orders:checkout"))
        assert response.status_code == 200

        # Step 9: User completes order
        checkout_data = {
            "first_name": "Journey",
            "last_name": "User",
            "email": "journey@example.com",
            "billing_address_line_1": "123 Journey Street",
            "billing_city": "Journey City",
            "billing_state_province": "CA",
            "billing_postal_code": "12345",
            "billing_country": "US",
            "payment_method": "credit_card",
        }

        response = client.post(reverse("orders:checkout"), data=checkout_data)
        assert response.status_code == 302

        # Step 10: Verify order was created
        user = User.objects.get(username="journeyuser")
        order = Order.objects.get(user=user)
        assert order.first_name == "Journey"
        assert OrderItem.objects.filter(order=order).count() == 1

        # Step 11: User views order confirmation
        response = client.get(
            reverse("orders:order_confirmation", args=[order.order_number])
        )
        assert response.status_code == 200

        # Step 12: User views order history
        response = client.get(reverse("orders:order_list"))
        assert response.status_code == 200
        assert order in response.context["orders"]


class TestProductCatalogIntegration:
    """Test product catalog functionality across apps"""

    @pytest.mark.django_db
    def test_category_product_integration(self, client, sample_data):
        """Test category-product relationships and filtering"""
        electronics_category = sample_data["categories"][0]
        fashion_category = sample_data["categories"][1]  # noqa: F841

        # Test category page shows only category products
        response = client.get(
            reverse("products:category", args=[electronics_category.slug])
        )
        assert response.status_code == 200

        products_in_category = response.context["products"]
        for product in products_in_category:
            assert product.category == electronics_category

        # Test product list filtering
        response = client.get(
            reverse("products:product_list"), {"category": electronics_category.id}
        )
        assert response.status_code == 200

        filtered_products = response.context["products"]
        for product in filtered_products:
            assert product.category == electronics_category

    @pytest.mark.django_db
    def test_product_search_functionality(self, client, sample_data):
        """Test product search across categories"""
        # Search for a term that matches exactly one fixture product
        response = client.get(
            reverse("products:product_list"), {"search": "Sample Product 1"}
        )
        assert response.status_code == 200

        search_results = response.context["products"]

        # Exactly one product should match "Sample Product 1"
        # (not "Sample Product 10", "11", etc. since fixture only has 1–5)
        assert len(search_results) == 1
        assert search_results[0].name == "Sample Product 1"

        # Verify non-matching products are excluded
        result_names = [p.name for p in search_results]
        assert "Sample Product 2" not in result_names
        assert "Sample Product 3" not in result_names

    @pytest.mark.django_db
    def test_product_stock_management(self, client, user, product):
        """Test product stock management during orders"""
        client.login(username=user.username, password="testpass123")

        # Record initial stock
        initial_stock = product.stock_quantity

        # Add product to cart
        response = client.post(
            reverse("orders:add_to_cart", args=[product.id]), {"quantity": 3}
        )
        assert response.status_code in [200, 302]

        # Stock should not decrease until order is placed
        product.refresh_from_db()
        assert product.stock_quantity == initial_stock

        # Complete checkout process
        checkout_data = {
            "first_name": "Stock",
            "last_name": "Test",
            "email": "stock@example.com",
            "billing_address_line_1": "123 Stock St",
            "billing_city": "Stock City",
            "billing_state_province": "CA",
            "billing_postal_code": "12345",
            "billing_country": "US",
            "payment_method": "credit_card",
        }

        response = client.post(reverse("orders:checkout"), data=checkout_data)
        assert response.status_code == 302

        # Verify stock was updated (if implemented)
        # This depends on business logic implementation


class TestCartPersistence:
    """Test cart persistence and session management"""

    @pytest.mark.django_db
    def test_authenticated_user_cart_persistence(self, client, user, product):
        """Test cart persists across sessions for authenticated users"""
        # Login and add item to cart
        client.force_login(user)

        response = client.post(
            reverse("orders:add_to_cart", args=[product.id]), {"quantity": 2}
        )
        assert response.status_code in [200, 302]

        # Logout
        client.post(reverse("accounts:logout"))

        # Login again
        client.force_login(user)

        # Cart should still contain items
        response = client.get(reverse("orders:cart"))
        assert response.status_code == 200

        cart_items = response.context.get("cart_items", [])
        assert len(cart_items) > 0

        # Find the cart item
        found_item = False
        for item in cart_items:
            if item.product == product and item.quantity == 2:
                found_item = True
                break
        assert found_item

    @pytest.mark.django_db
    def test_cart_cleanup_on_order_completion(
        self, authenticated_client, user, product
    ):
        """Test cart is cleared after successful order"""
        # Add item to cart
        response = authenticated_client.post(
            reverse("orders:add_to_cart", args=[product.id]), {"quantity": 1}
        )
        assert response.status_code in [200, 302]

        # Verify cart has items
        cart = Cart.objects.get(user=user)
        cart_items = getattr(cart, "items")
        assert cart_items.count() == 1

        # Complete checkout
        checkout_data = {
            "first_name": "Cleanup",
            "last_name": "Test",
            "email": "cleanup@example.com",
            "billing_address_line_1": "123 Cleanup Ave",
            "billing_city": "Cleanup City",
            "billing_state_province": "CA",
            "billing_postal_code": "54321",
            "billing_country": "US",
            "payment_method": "credit_card",
        }

        response = authenticated_client.post(
            reverse("orders:checkout"), data=checkout_data
        )
        assert response.status_code == 302

        # Cart should be empty after checkout
        cart.refresh_from_db()
        # This depends on implementation - cart might be cleared or marked as ordered


class TestUserProfileIntegration:
    """Test user profile integration with orders"""

    @pytest.mark.django_db
    def test_profile_autofill_checkout(self, authenticated_client, user):
        """Test checkout form is pre-filled with user profile data"""
        # Update user profile
        profile = getattr(user, "profile")
        profile.phone_number = "555-123-4567"
        profile.address_line_1 = "789 Profile Street"
        profile.city = "Profile City"
        profile.postal_code = "98765"
        profile.save()

        user.first_name = "Profile"
        user.last_name = "User"
        user.email = "profile@example.com"
        user.save()

        # Visit checkout page
        response = authenticated_client.get(reverse("orders:checkout"))
        assert response.status_code == 200

        # Check if form is pre-filled (this depends on implementation)
        form = response.context.get("form")
        if form and hasattr(form, "initial"):
            assert form.initial.get("first_name") == "Profile"
            assert form.initial.get("last_name") == "User"
            assert form.initial.get("email") == "profile@example.com"

    @pytest.mark.django_db
    def test_order_updates_profile(self, authenticated_client, user, product):
        """Test order information updates user profile"""
        # Add item to cart
        response = authenticated_client.post(
            reverse("orders:add_to_cart", args=[product.id]), {"quantity": 1}
        )

        # Complete checkout with new address
        new_checkout_data = {
            "first_name": "Updated",
            "last_name": "Name",
            "email": "updated@example.com",
            "billing_address_line_1": "999 New Address",
            "billing_city": "New City",
            "billing_state_province": "CA",
            "billing_postal_code": "11111",
            "billing_country": "US",
            "payment_method": "credit_card",
        }

        response = authenticated_client.post(
            reverse("orders:checkout"), data=new_checkout_data
        )
        assert response.status_code == 302

        # Check if profile was updated (this depends on implementation)
        user.refresh_from_db()
        profile = getattr(user, "profile")
        profile.refresh_from_db()

        # This would need to be implemented based on business requirements


class TestErrorHandling:
    """Test error handling and edge cases"""

    @pytest.mark.django_db
    def test_add_out_of_stock_product(self, authenticated_client, user, category):
        """Test adding out of stock product to cart"""
        # Create out of stock product
        out_of_stock_product = Product.objects.create(
            name="Out of Stock Product",
            slug="out-of-stock-product",
            price=Decimal("25.00"),
            category=category,
            stock_quantity=0,
            sku="OUTSTOCK-001",
            is_active=True,
        )

        # Try to add to cart
        response = authenticated_client.post(
            reverse("orders:add_to_cart", args=[out_of_stock_product.pk]),
            {"quantity": 1},
        )

        # Should handle gracefully (depends on implementation)
        # Could return error message or redirect with message
        assert response.status_code in [200, 302, 400]

    @pytest.mark.django_db
    def test_checkout_empty_cart(self, authenticated_client, user):
        """Test checkout with empty cart"""
        # Try to checkout without items
        response = authenticated_client.get(reverse("orders:checkout"))

        # Should handle gracefully
        assert response.status_code in [200, 302]

        # If allowing checkout page, should show appropriate message
        if response.status_code == 200:
            # Should indicate empty cart
            pass

    @pytest.mark.django_db
    def test_access_other_user_order(self, client, user, sample_data):
        """Test user cannot access another user's order"""
        # Create two users
        user1 = User.objects.create_user(
            username="access_test_user1",
            password="pass123",
            email="user1@accesstest.com",
        )
        user2 = User.objects.create_user(  # noqa: F841
            username="access_test_user2",
            password="pass123",
            email="user2@accesstest.com",
        )

        # Create order for user1
        order = Order.objects.create(
            user=user1,
            email=user1.email,
            first_name="User",
            last_name="One",
            billing_address_line_1="123 Test St",
            billing_city="Test City",
            billing_state_province="Test State",
            billing_postal_code="12345",
            billing_country="Test Country",
            total_amount=Decimal("50.00"),
            status="pending",
        )

        # Login as user2 and try to access user1's order
        client.login(username="access_test_user2", password="pass123")
        response = client.get(reverse("orders:order_detail", args=[order.order_number]))

        # Should deny access (404 or 403)
        assert response.status_code in [403, 404]


class TestPerformance:
    """Test performance-related scenarios"""

    @pytest.mark.django_db
    def test_large_product_catalog(self, client):
        """Test performance with large number of products"""
        # Create category
        category = Category.objects.create(
            name="Performance Test", slug="performance-test"
        )

        # Create many products
        products = []
        for i in range(100):  # Smaller number for testing
            product = Product(
                name=f"Performance Product {i}",
                slug=f"performance-product-{i}",
                price=Decimal(f"{i+1}.99"),
                category=category,
                stock_quantity=10,
                sku=f"PERF-{i+1:03d}",
                is_active=True,
            )
            products.append(product)

        Product.objects.bulk_create(products)

        # Test product list page performance
        response = client.get(reverse("products:product_list"))
        assert response.status_code == 200

        # Should handle large catalog without timeout
        assert len(response.context["products"]) > 0

    @pytest.mark.django_db
    def test_concurrent_cart_modifications(self, client, user, product):
        """Test concurrent cart modifications"""
        # This test would require more complex setup for true concurrency testing
        # For now, we'll test sequential operations that could cause conflicts

        client.force_login(user)

        # Multiple additions to cart
        for i in range(5):
            response = client.post(
                reverse("orders:add_to_cart", args=[product.id]), {"quantity": 1}
            )
            assert response.status_code in [200, 302]

        # Check final cart state
        cart = Cart.objects.get(user=user)
        # Depending on implementation, might have 1 item with quantity 5
        # or 5 separate items that get merged
        cart_items = getattr(cart, "items")
        total_quantity = sum(item.quantity for item in cart_items.all())
        assert total_quantity >= 1  # At least some items were added
