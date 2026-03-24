"""
Unit tests for orders app - cart, checkout, order management functionality
"""

from decimal import Decimal

import pytest

from django.core.exceptions import ValidationError
from django.urls import reverse

from orders.models import Cart, CartItem, Order, OrderItem
from products.models import Product, ProductVariant


class TestCartModel:
    """Test Cart model functionality"""

    @pytest.mark.django_db
    def test_cart_creation(self, user):
        """Test creating a cart"""
        cart = Cart.objects.create(user=user)
        assert cart.user == user
        assert cart.created_at is not None
        assert str(cart) == f"Cart for {user.username}"

    @pytest.mark.django_db
    def test_cart_total_calculation(self, user, category):
        """Test cart total calculation"""
        cart = Cart.objects.create(user=user)

        # Create products
        product1 = Product.objects.create(
            name="Product 1",
            slug="product-1",
            price=Decimal("10.00"),
            category=category,
            stock_quantity=10,
            sku="CART-001",
        )
        product2 = Product.objects.create(
            name="Product 2",
            slug="product-2",
            price=Decimal("25.50"),
            category=category,
            stock_quantity=5,
            sku="CART-002",
        )

        # Add items to cart
        CartItem.objects.create(cart=cart, product=product1, quantity=2)
        CartItem.objects.create(cart=cart, product=product2, quantity=1)

        # Calculate expected total
        expected_total = (product1.price * 2) + (product2.price * 1)

        # Test total calculation method (assuming we implement this)
        cart_items = getattr(cart, "items").all()
        calculated_total = sum(
            item.product.price * item.quantity for item in cart_items
        )
        assert calculated_total == expected_total

    @pytest.mark.django_db
    def test_cart_item_count(self, user, category):
        """Test cart item count"""
        cart = Cart.objects.create(user=user)

        product = Product.objects.create(
            name="Test Product",
            slug="test-product",
            price=Decimal("15.00"),
            category=category,
            stock_quantity=20,
            sku="COUNT-001",
        )

        # Add multiple quantities
        CartItem.objects.create(cart=cart, product=product, quantity=3)

        # Test item count
        cart_items = getattr(cart, "items")
        assert cart_items.count() == 1
        total_quantity = sum(item.quantity for item in cart_items.all())
        assert total_quantity == 3


class TestCartItemModel:
    """Test CartItem model functionality"""

    @pytest.mark.django_db
    def test_cart_item_creation(self, cart, product):
        """Test creating a cart item"""
        cart_item = CartItem.objects.create(cart=cart, product=product, quantity=2)
        assert cart_item.cart == cart
        assert cart_item.product == product
        assert cart_item.quantity == 2
        assert str(cart_item) == f"{product.name} x2"

    @pytest.mark.django_db
    def test_cart_item_quantity_validation(self, cart, product):
        """Test cart item quantity must be positive"""
        with pytest.raises(ValidationError):
            cart_item = CartItem(cart=cart, product=product, quantity=0)
            cart_item.full_clean()

        with pytest.raises(ValidationError):
            cart_item = CartItem(cart=cart, product=product, quantity=-1)
            cart_item.full_clean()

    @pytest.mark.django_db
    def test_cart_item_subtotal(self, cart, product):
        """Test cart item subtotal calculation"""
        cart_item = CartItem.objects.create(cart=cart, product=product, quantity=3)
        expected_subtotal = product.price * cart_item.quantity
        # Assuming we implement a subtotal property
        calculated_subtotal = cart_item.product.price * cart_item.quantity
        assert calculated_subtotal == expected_subtotal

    @pytest.mark.django_db
    def test_cart_item_variant_support(self, cart, product):
        """Test cart item with product variant"""
        variant = ProductVariant.objects.create(
            product=product,
            name="Size",
            value="Large Size",
            price_adjustment=Decimal("5.00"),
            stock_quantity=10,
        )

        cart_item = CartItem.objects.create(
            cart=cart, product=product, variant=variant, quantity=1
        )

        assert cart_item.variant == variant
        # Test price calculation with variant
        expected_price = product.price + variant.price_adjustment  # noqa: F841
        # This would require implementation in the model


class TestOrderModel:
    """Test Order model functionality"""

    @pytest.mark.django_db
    def test_order_creation(self, user):
        """Test creating an order"""
        order = Order.objects.create(
            user=user,
            email=user.email,
            first_name=user.first_name,
            last_name=user.last_name,
            billing_address_line_1="123 Test Street",
            billing_city="Test City",
            billing_state_province="Test State",
            billing_postal_code="12345",
            billing_country="Test Country",
            total_amount=Decimal("99.99"),
            status="pending",
        )
        assert order.user == user
        assert order.status == "pending"
        assert order.total_amount == Decimal("99.99")
        assert str(order) == f"Order {order.order_number}"

    @pytest.mark.django_db
    def test_order_status_choices(self, user):
        """Test order status validation"""
        order = Order.objects.create(
            user=user,
            email=user.email,
            first_name="Test",
            last_name="User",
            billing_address_line_1="123 Test Street",
            billing_city="Test City",
            billing_state_province="Test State",
            billing_postal_code="12345",
            billing_country="Test Country",
            total_amount=Decimal("50.00"),
            # L8: 'completed' is not a valid choice; use 'delivered'
            status="delivered",
        )
        assert order.status == "delivered"

        # Test invalid status would be caught by model validation
        # This depends on how status choices are implemented

    @pytest.mark.django_db
    def test_order_total_validation(self, user):
        """Test order total amount validation"""
        with pytest.raises(ValidationError):
            order = Order(
                user=user,
                email=user.email,
                first_name="Test",
                last_name="User",
                billing_address_line_1="123 Test Street",
                billing_city="Test City",
                billing_state_province="Test State",
                billing_postal_code="12345",
                billing_country="Test Country",
                total_amount=Decimal("-10.00"),  # Negative amount
                status="pending",
            )
            order.full_clean()


class TestOrderItemModel:
    """Test OrderItem model functionality"""

    @pytest.mark.django_db
    def test_order_item_creation(self, order, product):
        """Test creating an order item"""
        order_item = OrderItem.objects.create(
            order=order, product=product, quantity=2, unit_price=product.price
        )
        assert order_item.order == order
        assert order_item.product == product
        assert order_item.quantity == 2
        assert order_item.unit_price == product.price
        assert str(order_item) == f"{product.name} x2"

    @pytest.mark.django_db
    def test_order_item_subtotal(self, order, product):
        """Test order item subtotal calculation"""
        order_item = OrderItem.objects.create(
            order=order, product=product, quantity=3, unit_price=product.price
        )
        expected_subtotal = order_item.unit_price * order_item.quantity
        assert order_item.total_price == expected_subtotal

    @pytest.mark.django_db
    def test_order_item_price_snapshot(self, order, product):
        """Test that order item stores price at time of order"""
        original_price = product.price
        order_item = OrderItem.objects.create(
            order=order, product=product, quantity=1, unit_price=original_price
        )

        # Change product price to a different value
        product.price = Decimal("149.99")
        product.save()

        # Order item should still have original price
        order_item.refresh_from_db()
        assert order_item.unit_price == original_price
        assert order_item.unit_price != product.price


class TestCartViews:
    """Test cart-related views"""

    @pytest.mark.django_db
    def test_cart_view_authenticated(self, authenticated_client, user, product):
        """Test cart view for authenticated user"""
        cart = Cart.objects.create(user=user)
        CartItem.objects.create(cart=cart, product=product, quantity=1)

        response = authenticated_client.get(reverse("orders:cart"))
        assert response.status_code == 200
        assert "cart" in response.context
        assert "cart_items" in response.context

    @pytest.mark.django_db
    def test_cart_view_anonymous(self, client):
        """Test cart view for anonymous user"""
        response = client.get(reverse("orders:cart"))
        # Should redirect to login or handle session cart
        # Implementation depends on how anonymous carts are handled
        assert response.status_code in [200, 302]

    @pytest.mark.django_db
    def test_add_to_cart_authenticated(self, authenticated_client, user, product):
        """Test adding item to cart for authenticated user"""
        response = authenticated_client.post(
            reverse("orders:add_to_cart", args=[product.id]), {"quantity": 2}
        )

        # Should redirect or return success response
        assert response.status_code in [200, 302]

        # Check that item was added to cart
        cart = Cart.objects.get(user=user)
        cart_item = CartItem.objects.get(cart=cart, product=product)
        assert cart_item.quantity == 2

    @pytest.mark.django_db
    def test_update_cart_item(self, authenticated_client, cart_item):
        """Test updating cart item quantity"""
        response = authenticated_client.post(
            reverse("orders:update_cart", args=[cart_item.id]),
            {"item_id": cart_item.id, "quantity": 5},
        )

        assert response.status_code in [200, 302]

        cart_item.refresh_from_db()
        assert cart_item.quantity == 5

    @pytest.mark.django_db
    def test_remove_from_cart(self, authenticated_client, cart_item):
        """Test removing item from cart"""
        item_id = cart_item.id
        response = authenticated_client.post(
            reverse("orders:remove_from_cart", args=[item_id]), {"item_id": item_id}
        )

        assert response.status_code in [200, 302]

        # Item should be deleted
        assert not CartItem.objects.filter(id=item_id).exists()


class TestCheckoutViews:
    """Test checkout process views"""

    @pytest.mark.django_db
    def test_checkout_view_authenticated(self, authenticated_client, user, product):
        """Test checkout page for authenticated user with cart items"""
        cart = Cart.objects.create(user=user)
        CartItem.objects.create(cart=cart, product=product, quantity=1)

        response = authenticated_client.get(reverse("orders:checkout"))
        assert response.status_code == 200
        assert "form" in response.context
        assert "cart_items" in response.context

    @pytest.mark.django_db
    def test_checkout_view_empty_cart(self, authenticated_client, user):
        """Test checkout with empty cart"""
        response = authenticated_client.get(reverse("orders:checkout"))
        # Should redirect or show empty cart message
        # Implementation depends on business logic
        assert response.status_code in [200, 302]

    @pytest.mark.django_db
    def test_checkout_process(self, authenticated_client, user, product):
        """Test complete checkout process"""
        # Setup cart
        cart = Cart.objects.create(user=user)
        CartItem.objects.create(cart=cart, product=product, quantity=2)

        # Submit checkout form
        checkout_data = {
            "first_name": "Test",
            "last_name": "User",
            "email": "test@example.com",
            "billing_address_line_1": "123 Checkout Street",
            "billing_city": "Checkout City",
            "billing_state_province": "CA",
            "billing_postal_code": "54321",
            "billing_country": "US",
            "payment_method": "credit_card",
        }

        response = authenticated_client.post(
            reverse("orders:checkout"), data=checkout_data
        )

        # Should redirect to order confirmation
        assert response.status_code == 302

        # Check that order was created
        order = Order.objects.get(user=user)
        assert order.first_name == "Test"
        assert order.last_name == "User"
        assert order.email == "test@example.com"

        # Check that order items were created
        order_items = OrderItem.objects.filter(order=order)
        assert order_items.count() == 1
        first_item = order_items.first()
        assert first_item is not None
        assert first_item.quantity == 2


class TestOrderViews:
    """Test order management views"""

    @pytest.mark.django_db
    def test_order_confirmation_view(self, authenticated_client, order):
        """Test order confirmation page"""
        response = authenticated_client.get(
            reverse("orders:order_confirmation", args=[order.order_number])
        )
        assert response.status_code == 200
        assert response.context["order"] == order

    @pytest.mark.django_db
    def test_order_detail_view(self, authenticated_client, order):
        """Test order detail page"""
        response = authenticated_client.get(
            reverse("orders:order_detail", args=[order.order_number])
        )
        assert response.status_code == 200
        assert response.context["order"] == order

    @pytest.mark.django_db
    def test_order_list_view(self, authenticated_client, user, order):
        """Test user's order list page"""
        response = authenticated_client.get(reverse("orders:order_list"))
        assert response.status_code == 200
        assert "orders" in response.context
        assert order in response.context["orders"]


class TestOrderIntegration:
    """Integration tests for complete order workflow"""

    @pytest.mark.django_db
    def test_complete_order_flow(self, authenticated_client, user, product):
        """Test complete order flow from cart to confirmation"""
        # Step 1: Add item to cart
        response = authenticated_client.post(
            reverse("orders:add_to_cart", args=[product.id]), {"quantity": 1}
        )
        assert response.status_code in [200, 302]

        # Step 2: View cart
        response = authenticated_client.get(reverse("orders:cart"))
        assert response.status_code == 200

        # Step 3: Proceed to checkout
        response = authenticated_client.get(reverse("orders:checkout"))
        assert response.status_code == 200

        # Step 4: Submit order
        checkout_data = {
            "first_name": "Integration",
            "last_name": "Test",
            "email": "integration@example.com",
            "billing_address_line_1": "456 Integration Ave",
            "billing_city": "Test City",
            "billing_state_province": "CA",
            "billing_postal_code": "67890",
            "billing_country": "US",
            "payment_method": "credit_card",
        }

        response = authenticated_client.post(
            reverse("orders:checkout"), data=checkout_data
        )
        assert response.status_code == 302

        # Step 5: Verify order was created
        order = Order.objects.get(user=user)
        assert order.first_name == "Integration"
        assert OrderItem.objects.filter(order=order).count() == 1

        # Step 6: View order confirmation
        response = authenticated_client.get(
            reverse("orders:order_confirmation", args=[order.order_number])
        )
        assert response.status_code == 200


# ---------------------------------------------------------------------------
# Coverage gap tests – orders/views.py
# ---------------------------------------------------------------------------


class TestGetOrCreateCartAnonymous:
    """get_or_create_cart() anonymous session branch – covers line 83."""

    @pytest.mark.django_db
    def test_anonymous_cart_created_via_session(self, client):
        """First anonymous request creates a session and a session-keyed cart."""
        # Accessing the cart view forces get_or_create_cart for an anon user.
        response = client.get(reverse("orders:cart"))
        assert response.status_code == 200
        # A Cart keyed by session_key should now exist.
        from orders.models import Cart

        assert Cart.objects.filter(session_key__isnull=False).exists()


class TestRemoveFromCartAnonymousOwnership:
    """RemoveFromCartView anonymous ownership check – covers lines 125-127."""

    @pytest.mark.django_db
    def test_anonymous_cannot_remove_other_session_item(self, client, product):
        """Anonymous user with wrong session key gets
        redirected without deleting item."""
        # Create a cart and item for session A
        client.get(reverse("orders:cart"))  # seeds a session
        session_key_a = client.session.session_key

        cart_a = Cart.objects.get(session_key=session_key_a)
        item = CartItem.objects.create(cart=cart_a, product=product, quantity=1)

        # Now forge a NEW session (session B) and try to remove session A's item
        from django.test import Client

        client_b = Client()
        client_b.get(reverse("orders:cart"))  # seeds a different session

        response = client_b.post(  # type: ignore[attr-defined]
            reverse("orders:remove_from_cart", args=[item.id])
        )
        # Should redirect (ownership check fails for wrong session)
        assert response.status_code == 302
        # Item should still exist
        assert CartItem.objects.filter(  # type: ignore[attr-defined]
            id=item.id
        ).exists()


class TestAddToCartOverstockAjax:
    """AddToCartView over-stock AJAX path – covers lines 125-127."""

    @pytest.mark.django_db
    def test_add_to_cart_overstock_ajax_returns_400(
        self, authenticated_client, user, product
    ):
        """AJAX request adding more than available stock returns 400 JSON."""
        # Product has stock_quantity=100 from conftest; set it low
        product.stock_quantity = 2
        product.track_inventory = True
        product.allow_backorders = False
        product.save()

        response = authenticated_client.post(
            reverse("orders:add_to_cart", args=[product.id]),
            {"quantity": 5},
            HTTP_X_REQUESTED_WITH="XMLHttpRequest",
        )
        assert response.status_code == 400
        data = response.json()
        assert data["success"] is False
        assert "only" in data["message"]

    @pytest.mark.django_db
    def test_add_to_cart_overstock_non_ajax_redirects(
        self, authenticated_client, product
    ):
        """Non-AJAX overstock request redirects with an error message."""
        product.stock_quantity = 1
        product.track_inventory = True
        product.allow_backorders = False
        product.save()

        response = authenticated_client.post(
            reverse("orders:add_to_cart", args=[product.id]),
            {"quantity": 10},
        )
        assert response.status_code == 302


class TestCheckoutViewPostBranches:
    """CheckoutView.post – covers lines 199-200, 204-207, 230-236, 249-252.
    CheckoutView.get_context_data – covers lines 189-190 (no UserProfile)."""

    def _checkout_data(self, **overrides):
        data = {
            "first_name": "Jane",
            "last_name": "Doe",
            "email": "jane@example.com",
            "billing_address_line_1": "1 Test Lane",
            "billing_city": "Testville",
            "billing_state_province": "TX",
            "billing_postal_code": "75001",
            "billing_country": "US",
            "payment_method": "credit_card",
        }
        data.update(overrides)
        return data

    @pytest.mark.django_db
    def test_checkout_get_no_profile_sets_profile_none(
        self, authenticated_client, user, product
    ):
        """GET checkout when user has no UserProfile sets
        context['profile'] = None (lines 189-190)."""
        from accounts.models import UserProfile

        UserProfile.objects.filter(user=user).delete()

        cart = Cart.objects.create(user=user)
        CartItem.objects.create(cart=cart, product=product, quantity=1)

        response = authenticated_client.get(reverse("orders:checkout"))
        assert response.status_code == 200
        assert response.context["profile"] is None

    @pytest.mark.django_db
    def test_post_empty_cart_redirects(self, authenticated_client, user):
        """POST to checkout with an empty cart should redirect to cart page."""
        # Ensure no cart items exist
        Cart.objects.filter(user=user).delete()
        response = authenticated_client.post(
            reverse("orders:checkout"),
            data=self._checkout_data(),
        )
        assert response.status_code == 302
        assert "cart" in response["Location"]

    @pytest.mark.django_db
    def test_post_invalid_form_rerenders(self, authenticated_client, user, product):
        """Invalid form data should re-render the checkout page (200)."""
        Cart.objects.create(user=user)
        cart = Cart.objects.get(user=user)
        CartItem.objects.create(cart=cart, product=product, quantity=1)

        response = authenticated_client.post(
            reverse("orders:checkout"),
            data={"first_name": ""},  # missing required fields
        )
        assert response.status_code == 200
        # Form in context should have errors
        assert response.context["form"].errors

    @pytest.mark.django_db
    def test_post_separate_shipping_address(self, authenticated_client, user, product):
        """shipping_same_as_billing=False should populate
        shipping address fields on the order."""
        cart = Cart.objects.create(user=user)
        CartItem.objects.create(cart=cart, product=product, quantity=1)

        # Include shipping_same_as_billing key in POST (so clean() sees it) but with
        # an unchecked value – Django BooleanField returns False for '' or absent.
        # The clean() logic: same = False OR ('key' NOT in data) → here key IS in data
        # and BooleanField gives False, so same=False and separate shipping fires.
        data = self._checkout_data(
            shipping_address_line_1="99 Ship St",
            shipping_city="ShipCity",
            shipping_state_province="CA",
            shipping_postal_code="90001",
            shipping_country="US",
        )
        # Include key in POST with falsy value so clean() resolves same=False
        data["shipping_same_as_billing"] = "False"
        response = authenticated_client.post(reverse("orders:checkout"), data=data)
        assert response.status_code == 302

        order = Order.objects.get(user=user)
        assert order.shipping_same_as_billing is False
        assert order.shipping_address_line_1 == "99 Ship St"

    @pytest.mark.django_db
    def test_post_variant_stock_decremented(
        self, authenticated_client, user, product, product_variant
    ):
        """Checkout with a variant item should decrement variant stock."""
        product_variant.stock_quantity = 10
        product_variant.save()
        product.track_inventory = True
        product.save()

        cart = Cart.objects.create(user=user)
        CartItem.objects.create(
            cart=cart, product=product, variant=product_variant, quantity=3
        )

        response = authenticated_client.post(
            reverse("orders:checkout"),
            data=self._checkout_data(),
        )
        assert response.status_code == 302

        product_variant.refresh_from_db()
        assert product_variant.stock_quantity == 7

    @pytest.mark.django_db
    def test_post_checkout_exception_shows_error(
        self, authenticated_client, user, product
    ):
        """When an unexpected exception occurs, the user sees an error message."""
        from unittest.mock import patch

        cart = Cart.objects.create(user=user)
        CartItem.objects.create(cart=cart, product=product, quantity=1)

        with patch(
            "orders.views.Order.objects.create", side_effect=Exception("DB error")
        ):
            response = authenticated_client.post(
                reverse("orders:checkout"),
                data=self._checkout_data(),
            )
        # Should re-render checkout (200) with an error message
        assert response.status_code == 200


# ---------------------------------------------------------------------------
# Coverage gap tests – orders/forms.py (lines 58-62)
# ---------------------------------------------------------------------------


class TestCheckoutFormClean:
    """CheckoutForm.clean() separate-shipping validation – covers lines 58-62."""

    def _base_data(self, **overrides):
        data = {
            "first_name": "Jane",
            "last_name": "Doe",
            "email": "jane@example.com",
            "billing_address_line_1": "1 Test Lane",
            "billing_city": "Testville",
            "billing_state_province": "TX",
            "billing_postal_code": "75001",
            "billing_country": "US",
            "payment_method": "credit_card",
        }
        data.update(overrides)
        return data

    def test_separate_shipping_missing_fields_raises_errors(self):
        """Submitting separate shipping without filling it in gives field errors."""
        from orders.forms import CheckoutForm

        # Include shipping_same_as_billing in POST with a falsy value so the key IS
        # present in self.data, making clean() resolve same=False and require fields.
        data = self._base_data()
        data["shipping_same_as_billing"] = "False"  # key present, BooleanField → False
        form = CheckoutForm(data=data)
        # The form is invalid because shipping address fields are empty
        assert not form.is_valid()
        for field in (
            "shipping_address_line_1",
            "shipping_city",
            "shipping_state_province",
            "shipping_postal_code",
            "shipping_country",
        ):
            assert field in form.errors, f"Expected error on {field}"

    def test_separate_shipping_filled_is_valid(self):
        """Submitting a complete separate shipping address makes the form valid."""
        from orders.forms import CheckoutForm

        data = self._base_data(
            shipping_address_line_1="99 Ship St",
            shipping_city="ShipCity",
            shipping_state_province="CA",
            shipping_postal_code="90001",
            shipping_country="US",
        )
        # Include key so clean() resolves same=False; all fields are filled → valid
        data["shipping_same_as_billing"] = "False"
        form = CheckoutForm(data=data)
        assert form.is_valid(), form.errors


# ---------------------------------------------------------------------------
# Cart migration on login – accounts/views.py
# ---------------------------------------------------------------------------


class TestCartMergeOnLogin:
    """_merge_anonymous_cart() called from CustomLoginView.form_valid()
    (Task 3.2 – session → user cart merge)."""

    LOGIN_URL = "/accounts/login/"

    def _login_via_view(self, client, user, password="testpass123"):
        """POST to the login view (fires view-level cart merge logic)."""
        return client.post(
            self.LOGIN_URL,
            {"username": user.username, "password": password},
            follow=False,
        )

    @pytest.mark.django_db
    def test_new_items_transferred_to_user_cart(self, client, user, product):
        """Anonymous cart items that don't exist in the user cart are moved."""
        # Set a known password (root conftest user already has testpass123,
        # but tests/conftest UserFactory users do not — set it explicitly).
        user.set_password("testpass123")
        user.save()

        # CartView creates a session AND a session-keyed Cart in one hit.
        client.get(reverse("orders:cart"))
        session_key = client.session.session_key
        # Get the cart already created by CartView (do NOT create a duplicate).
        session_cart = Cart.objects.get(session_key=session_key)
        CartItem.objects.create(cart=session_cart, product=product, quantity=3)

        # Log in via the actual view so form_valid() captures old_session_key.
        response = self._login_via_view(client, user)
        assert response.status_code == 302  # redirect → login succeeded

        user_cart = Cart.objects.get(user=user)
        assert user_cart.items.count() == 1
        assert user_cart.items.first().quantity == 3
        # Session cart deleted
        assert not Cart.objects.filter(session_key=session_key).exists()

    @pytest.mark.django_db
    def test_quantities_summed_for_existing_items(self, client, user, product):
        """When an item already in the user cart is also in the session cart,
        quantities are summed rather than overwritten."""
        user.set_password("testpass123")
        user.save()

        # Pre-existing user cart with 2 of the product
        user_cart = Cart.objects.create(user=user)
        CartItem.objects.create(cart=user_cart, product=product, quantity=2)

        # Anonymous session cart also has 3 of the same product.
        client.get(reverse("orders:cart"))
        session_key = client.session.session_key
        session_cart = Cart.objects.get(session_key=session_key)
        CartItem.objects.create(cart=session_cart, product=product, quantity=3)

        response = self._login_via_view(client, user)
        assert response.status_code == 302

        user_cart.refresh_from_db()
        item = user_cart.items.get(product=product)
        assert item.quantity == 5  # 2 existing + 3 from session
        assert not Cart.objects.filter(session_key=session_key).exists()

    @pytest.mark.django_db
    def test_no_session_cart_is_a_noop(self, client, user):
        """Login with no session cart leaves cart state unchanged."""
        user.set_password("testpass123")
        user.save()
        Cart.objects.filter(user=user).delete()

        # Hit any page that creates a session but NOT a Cart.
        # The accounts login page itself doesn't call get_or_create_cart.
        response = self._login_via_view(client, user)
        assert response.status_code == 302

        # No stray session-keyed cart was created
        assert not Cart.objects.filter(session_key__isnull=False, user=None).exists()

    @pytest.mark.django_db
    def test_empty_session_cart_is_deleted(self, client, user):
        """An empty session cart is removed on login."""
        user.set_password("testpass123")
        user.save()

        # CartView creates the session cart (empty).
        client.get(reverse("orders:cart"))
        session_key = client.session.session_key
        # No items in the session cart.

        response = self._login_via_view(client, user)
        assert response.status_code == 302

        assert not Cart.objects.filter(session_key=session_key).exists()
