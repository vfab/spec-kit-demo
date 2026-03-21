"""
Additional tests to reach 100% coverage on core app logic and 75%+ on customizations.
Targets:
  - accounts/forms.py         65% → 100%
  - accounts/models.py        92% → 100%
  - orders/models.py          92% → 100%
  - orders/views.py           87% → 100%
  - products/models.py        80% → 100%
  - products/views.py         88% → 100%
  - orders/admin.py           76% → 75%+ (already at 76%, improve)
  - management commands        0% → 75%+
  - context_processors        91% → 100%
"""

import io
from decimal import Decimal
from unittest.mock import MagicMock, patch

import pytest

from django.contrib.admin.sites import AdminSite
from django.contrib.auth.models import User
from django.core.management.base import OutputWrapper
from django.test import RequestFactory
from django.urls import reverse

from accounts.forms import UserProfileForm
from accounts.models import UserProfile
from ecommerce_site.context_processors import global_context
from orders.admin import CartAdmin, CartItemAdmin, OrderAdmin, OrderItemAdmin
from orders.models import Cart, CartItem, Order, OrderItem
from products.models import Category, Product, ProductImage, ProductVariant

# ---------------------------------------------------------------------------
# accounts/forms.py — UserProfileForm.__init__ and save()
# ---------------------------------------------------------------------------


class TestUserProfileFormInit:
    """Cover UserProfileForm.__init__ with user kwarg (lines 139-149)"""

    @pytest.mark.django_db
    def test_form_init_without_user(self):
        """Form works with no user kwarg"""
        form = UserProfileForm()
        assert form.user is None

    @pytest.mark.django_db
    def test_form_init_with_user_no_profile(self):
        """__init__ pre-populates User fields"""
        user = User.objects.create_user(
            username="inituser",
            password="pass123",
            first_name="Init",
            last_name="User",
            email="init@example.com",
        )
        # Delete auto-created profile so hasattr check is False
        UserProfile.objects.filter(user=user).delete()
        form = UserProfileForm(user=user)
        assert form.fields["first_name"].initial == "Init"
        assert form.fields["last_name"].initial == "User"
        assert form.fields["email"].initial == "init@example.com"

    @pytest.mark.django_db
    def test_form_init_with_user_with_profile(self):
        """__init__ pre-populates profile fields when profile exists"""
        user = User.objects.create_user(
            username="profileinituser",
            password="pass123",
            first_name="Profile",
            last_name="Init",
            email="pi@example.com",
        )
        profile = UserProfile.objects.get_or_create(user=user)[0]
        profile.phone_number = "555-0001"
        profile.address_line_1 = "1 Main St"
        profile.city = "Testville"
        profile.postal_code = "10001"
        profile.save()

        # Re-fetch user to clear the cached profile accessor
        user = User.objects.get(pk=user.pk)
        form = UserProfileForm(user=user)
        assert form.fields["phone_number"].initial == "555-0001"
        assert form.fields["address_line_1"].initial == "1 Main St"
        assert form.fields["city"].initial == "Testville"
        assert form.fields["postal_code"].initial == "10001"


class TestUserProfileFormSave:
    """Cover UserProfileForm.save() (lines 152-171)"""

    @pytest.mark.django_db
    def test_save_without_user_raises(self):
        """save() without user raises ValueError"""
        form = UserProfileForm(
            data={"first_name": "A", "last_name": "B", "email": "a@b.com"}
        )
        with pytest.raises(ValueError, match="User must be provided"):
            form.save()

    @pytest.mark.django_db
    def test_save_updates_user_and_profile(self):
        """save() updates User and UserProfile fields"""
        user = User.objects.create_user(
            username="saveuser",
            password="pass123",
            first_name="Old",
            last_name="Name",
            email="old@example.com",
        )
        form = UserProfileForm(
            user=user,
            data={
                "first_name": "New",
                "last_name": "Name",
                "email": "new@example.com",
                "phone_number": "555-9999",
                "address_line_1": "42 New St",
                "city": "New City",
                "postal_code": "99999",
            },
        )
        assert form.is_valid(), form.errors
        saved_user = form.save()

        saved_user.refresh_from_db()
        assert saved_user.first_name == "New"
        assert saved_user.email == "new@example.com"

        profile = UserProfile.objects.get(user=user)
        assert profile.phone_number == "555-9999"
        assert profile.address_line_1 == "42 New St"
        assert profile.city == "New City"
        assert profile.postal_code == "99999"


# ---------------------------------------------------------------------------
# accounts/models.py — full_name, full_address properties
# ---------------------------------------------------------------------------


class TestUserProfileProperties:
    """Cover accounts/models.py lines 41 and 46-54"""

    @pytest.mark.django_db
    def test_full_name(self):
        user = User.objects.create_user(
            username="fullnameuser", password="pass", first_name="Jane", last_name="Doe"
        )
        profile = UserProfile.objects.get_or_create(user=user)[0]
        assert profile.full_name == "Jane Doe"

    @pytest.mark.django_db
    def test_full_name_strips_whitespace(self):
        user = User.objects.create_user(username="noname", password="pass")
        profile = UserProfile.objects.get_or_create(user=user)[0]
        assert profile.full_name == ""  # no first/last set

    @pytest.mark.django_db
    def test_full_address_all_parts(self):
        user = User.objects.create_user(username="addruser", password="pass")
        profile = UserProfile.objects.get_or_create(user=user)[0]
        profile.address_line_1 = "10 Elm St"
        profile.address_line_2 = "Apt 2"
        profile.city = "Springfield"
        profile.state_province = "IL"
        profile.postal_code = "62701"
        profile.country = "US"
        profile.save()
        addr = profile.full_address
        assert "10 Elm St" in addr
        assert "Apt 2" in addr
        assert "Springfield" in addr
        assert "US" in addr

    @pytest.mark.django_db
    def test_full_address_partial(self):
        """Blank fields are excluded from full_address"""
        user = User.objects.create_user(username="partialaddruser", password="pass")
        profile = UserProfile.objects.get_or_create(user=user)[0]
        profile.address_line_1 = "5 Oak Ave"
        profile.city = "Oaktown"
        profile.save()
        addr = profile.full_address
        assert "5 Oak Ave" in addr
        assert "Oaktown" in addr
        # Empty fields not joined
        assert addr.count(",") < 5


# ---------------------------------------------------------------------------
# orders/models.py — Cart.clear(), anonymous __str__, CartItem variant __str__,
#                    Order properties, OrderItem variant save path
# ---------------------------------------------------------------------------


class TestCartModelExtra:
    """Cover orders/models.py: Cart.clear() (line 37), anon __str__ (line 26)"""

    @pytest.mark.django_db
    def test_anonymous_cart_str(self):
        cart = Cart.objects.create(session_key="testsession123")
        assert "Anonymous Cart" in str(cart)
        assert "testsession123" in str(cart)

    @pytest.mark.django_db
    def test_cart_clear(self, user, product):
        cart = Cart.objects.create(user=user)
        CartItem.objects.create(cart=cart, product=product, quantity=1)
        assert CartItem.objects.filter(cart=cart).count() == 1
        cart.clear()
        assert CartItem.objects.filter(cart=cart).count() == 0


class TestCartItemVariantStr:
    """Cover CartItem __str__ with variant (line 65)"""

    @pytest.mark.django_db
    def test_cart_item_str_with_variant(self, cart, product):
        variant = ProductVariant.objects.create(
            product=product,
            name="Color",
            value="Red",
            price_adjustment=Decimal("5.00"),
            stock_quantity=10,
        )
        item = CartItem.objects.create(
            cart=cart, product=product, variant=variant, quantity=1
        )
        assert "Color" in str(item)
        assert "Red" in str(item)


class TestOrderProperties:
    """Cover Order properties: full_name, billing_address, shipping_address,
    can_be_cancelled, is_completed (lines 174-205)"""

    @pytest.fixture
    def base_order(self, user):
        return Order.objects.create(
            user=user,
            email="test@example.com",
            first_name="Alice",
            last_name="Smith",
            billing_address_line_1="1 Billing Rd",
            billing_address_line_2="Suite 100",
            billing_city="Billtown",
            billing_state_province="CA",
            billing_postal_code="90001",
            billing_country="US",
            total_amount=Decimal("100.00"),
        )

    @pytest.mark.django_db
    def test_full_name(self, base_order):
        assert base_order.full_name == "Alice Smith"

    @pytest.mark.django_db
    def test_billing_address(self, base_order):
        addr = base_order.billing_address
        assert "1 Billing Rd" in addr
        assert "Suite 100" in addr
        assert "Billtown" in addr
        assert "US" in addr

    @pytest.mark.django_db
    def test_shipping_address_same_as_billing(self, base_order):
        base_order.shipping_same_as_billing = True
        base_order.save()
        assert base_order.shipping_address == base_order.billing_address

    @pytest.mark.django_db
    def test_shipping_address_different(self, base_order):
        base_order.shipping_same_as_billing = False
        base_order.shipping_address_line_1 = "99 Ship St"
        base_order.shipping_city = "Shipville"
        base_order.shipping_state_province = "NY"
        base_order.shipping_postal_code = "10001"
        base_order.shipping_country = "US"
        base_order.save()
        addr = base_order.shipping_address
        assert "99 Ship St" in addr
        assert "Shipville" in addr

    @pytest.mark.django_db
    def test_can_be_cancelled_pending(self, base_order):
        base_order.status = "pending"
        assert base_order.can_be_cancelled is True

    @pytest.mark.django_db
    def test_can_be_cancelled_confirmed(self, base_order):
        base_order.status = "confirmed"
        assert base_order.can_be_cancelled is True

    @pytest.mark.django_db
    def test_cannot_be_cancelled_shipped(self, base_order):
        base_order.status = "shipped"
        assert base_order.can_be_cancelled is False

    @pytest.mark.django_db
    def test_is_completed_delivered(self, base_order):
        base_order.status = "delivered"
        assert base_order.is_completed is True

    @pytest.mark.django_db
    def test_is_completed_cancelled(self, base_order):
        base_order.status = "cancelled"
        assert base_order.is_completed is True

    @pytest.mark.django_db
    def test_is_not_completed_pending(self, base_order):
        base_order.status = "pending"
        assert base_order.is_completed is False


class TestOrderItemVariantSave:
    """Cover OrderItem.save() variant branch (lines 240-241)"""

    @pytest.mark.django_db
    def test_order_item_save_with_variant(self, order, product):
        variant = ProductVariant.objects.create(
            product=product,
            name="Size",
            value="XL",
            price_adjustment=Decimal("2.00"),
            stock_quantity=5,
        )
        item = OrderItem.objects.create(
            order=order,
            product=product,
            variant=variant,
            quantity=1,
            unit_price=product.price,
        )
        assert item.variant_name == "Size"
        assert item.variant_value == "XL"


# ---------------------------------------------------------------------------
# orders/views.py — uncovered branches
# ---------------------------------------------------------------------------


class TestAddToCartViewExtra:
    """Cover AddToCart: anonymous session, variant, AJAX (lines 51,57-61,79)"""

    @pytest.mark.django_db
    def test_add_to_cart_anonymous_creates_session_cart(self, client, product):
        """Anonymous user cart is created via session key"""
        response = client.post(
            reverse("orders:add_to_cart", args=[product.id]), {"quantity": 1}
        )
        assert response.status_code == 302
        # Cart should exist with session key
        assert Cart.objects.filter(session_key__isnull=False).exists()

    @pytest.mark.django_db
    def test_add_to_cart_with_variant(self, authenticated_client, user, product):
        """Add to cart with a variant_id"""
        variant = ProductVariant.objects.create(
            product=product,
            name="Color",
            value="Blue",
            price_adjustment=Decimal("0.00"),
            stock_quantity=10,
        )
        response = authenticated_client.post(
            reverse("orders:add_to_cart", args=[product.id]),
            {"quantity": 1, "variant_id": variant.pk},
        )
        assert response.status_code == 302
        cart = Cart.objects.get(user=user)
        assert CartItem.objects.filter(cart=cart, variant=variant).exists()

    @pytest.mark.django_db
    def test_add_to_cart_ajax_returns_json(self, authenticated_client, product):
        """AJAX request returns JsonResponse"""
        response = authenticated_client.post(
            reverse("orders:add_to_cart", args=[product.id]),
            {"quantity": 1},
            HTTP_X_REQUESTED_WITH="XMLHttpRequest",
        )
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "cart_count" in data


class TestRemoveFromCartViewExtra:
    """Cover RemoveFromCartView unauthorized branch (lines 96-97)"""

    @pytest.mark.django_db
    def test_remove_unauthorized_user(self, client, product):
        """Cannot remove another user's cart item"""
        owner = User.objects.create_user(
            username="cartowner", password="pass", email="owner@example.com"
        )
        UserProfile.objects.get_or_create(user=owner)
        other = User.objects.create_user(
            username="other", password="pass", email="other@example.com"
        )
        UserProfile.objects.get_or_create(user=other)
        cart = Cart.objects.create(user=owner)
        item = CartItem.objects.create(cart=cart, product=product, quantity=1)

        client.login(username="other", password="pass")
        response = client.post(reverse("orders:remove_from_cart", args=[item.pk]))
        assert response.status_code == 302
        # Item should NOT have been deleted
        assert CartItem.objects.filter(pk=item.pk).exists()


class TestUpdateCartViewExtra:
    """Cover UpdateCartView: unauthorized and quantity=0 delete
    (lines 116-117,124-125)"""

    @pytest.mark.django_db
    def test_update_unauthorized_user(self, client, product):
        """Cannot update another user's cart item"""
        owner = User.objects.create_user(
            username="updateowner", password="pass", email="uo@example.com"
        )
        UserProfile.objects.get_or_create(user=owner)
        other = User.objects.create_user(
            username="updateother", password="pass", email="uother@example.com"
        )
        UserProfile.objects.get_or_create(user=other)
        cart = Cart.objects.create(user=owner)
        item = CartItem.objects.create(cart=cart, product=product, quantity=2)

        client.login(username="updateother", password="pass")
        response = client.post(
            reverse("orders:update_cart", args=[item.pk]), {"quantity": 5}
        )
        assert response.status_code == 302
        item.refresh_from_db()
        assert item.quantity == 2  # unchanged

    @pytest.mark.django_db
    def test_update_quantity_zero_deletes_item(self, authenticated_client, cart_item):
        """Quantity=0 should delete the cart item"""
        item_id = cart_item.id
        response = authenticated_client.post(
            reverse("orders:update_cart", args=[item_id]), {"quantity": 0}
        )
        assert response.status_code == 302
        assert not CartItem.objects.filter(id=item_id).exists()


class TestCheckoutViewErrorPath:
    """Cover CheckoutView POST exception handler (lines 221-223)"""

    @pytest.mark.django_db
    def test_checkout_exception_returns_200(self, authenticated_client, user, product):
        """When Order.objects.create raises, view re-renders checkout (200)"""
        cart = Cart.objects.create(user=user)
        CartItem.objects.create(cart=cart, product=product, quantity=1)

        with patch(
            "orders.views.Order.objects.create", side_effect=Exception("DB error")
        ):
            response = authenticated_client.post(
                reverse("orders:checkout"),
                data={
                    "first_name": "Test",
                    "last_name": "User",
                    "email": "test@example.com",
                    "billing_address_line_1": "1 St",
                    "billing_city": "City",
                    "billing_state_province": "CA",
                    "billing_postal_code": "12345",
                    "billing_country": "US",
                    "payment_method": "credit_card",
                },
            )
        assert response.status_code == 200


class TestOrderConfirmationGuestPath:
    """Cover OrderConfirmationView — unauthenticated users are redirected to login"""

    @pytest.mark.django_db
    def test_unauthenticated_redirected_to_login(self, client, user):
        """Anonymous users cannot view order confirmation — redirected to login"""
        order = Order.objects.create(
            user=user,
            email="test@example.com",
            first_name="Test",
            last_name="User",
            billing_address_line_1="1 Test Rd",
            billing_city="Testville",
            billing_state_province="CA",
            billing_postal_code="90210",
            billing_country="US",
            total_amount=Decimal("25.00"),
        )
        response = client.get(
            reverse("orders:order_confirmation", args=[order.order_number])
        )
        assert response.status_code == 302
        assert "/accounts/login/" in response["Location"]


# ---------------------------------------------------------------------------
# products/models.py — uncovered properties and methods
# ---------------------------------------------------------------------------


class TestCategoryAbsoluteUrl:
    """Cover Category.get_absolute_url (line 29)"""

    @pytest.mark.django_db
    def test_get_absolute_url(self):
        cat = Category.objects.create(name="Gadgets", slug="gadgets")
        url = cat.get_absolute_url()
        assert "/gadgets/" in url


class TestProductModelExtra:
    """Cover Product.get_absolute_url, is_on_sale, discount_percentage, is_in_stock"""

    @pytest.mark.django_db
    def test_get_absolute_url(self, product):
        url = product.get_absolute_url()
        assert product.slug in url

    @pytest.mark.django_db
    def test_is_on_sale_true(self, product):
        product.compare_price = Decimal("99.99")
        product.price = Decimal("49.99")
        product.save()
        assert product.is_on_sale is True

    @pytest.mark.django_db
    def test_is_on_sale_false_no_compare(self, product):
        product.compare_price = None
        product.save()
        assert not product.is_on_sale

    @pytest.mark.django_db
    def test_discount_percentage(self, product):
        product.compare_price = Decimal("100.00")
        product.price = Decimal("75.00")
        product.save()
        assert product.discount_percentage == 25

    @pytest.mark.django_db
    def test_discount_percentage_not_on_sale(self, product):
        product.compare_price = None
        product.save()
        assert product.discount_percentage == 0

    @pytest.mark.django_db
    def test_is_in_stock_track_inventory_false(self, product):
        product.track_inventory = False
        product.stock_quantity = 0
        product.save()
        assert product.is_in_stock is True

    @pytest.mark.django_db
    def test_is_in_stock_allow_backorders(self, product):
        product.track_inventory = True
        product.stock_quantity = 0
        product.allow_backorders = True
        product.save()
        assert product.is_in_stock is True

    @pytest.mark.django_db
    def test_is_in_stock_zero_no_backorders(self, product):
        product.track_inventory = True
        product.stock_quantity = 0
        product.allow_backorders = False
        product.save()
        assert product.is_in_stock is False

    @pytest.mark.django_db
    def test_main_image_returns_none_when_no_images(self, product):
        assert product.main_image is None


class TestProductImageSave:
    """Cover ProductImage.save() primary-uniqueness logic (lines 140-143)"""

    @pytest.mark.django_db
    def test_primary_image_uniqueness(self, product):
        """Setting is_primary=True on a new image clears existing primary"""
        # Patch both resize_image AND the image field's save to avoid real file I/O
        with (
            patch.object(ProductImage, "resize_image", return_value=None),
            patch("django.db.models.fields.files.FieldFile.save", return_value=None),
            patch(
                "django.db.models.fields.files.FieldFile.__bool__", return_value=False
            ),
        ):
            img1 = ProductImage.objects.create(  # noqa: F841
                product=product, alt_text="first", is_primary=True
            )
            img2 = ProductImage.objects.create(
                product=product, alt_text="second", is_primary=True
            )

        # Only img2 should be primary
        assert (
            ProductImage.objects.filter(product=product, is_primary=True).count() == 1
        )
        assert ProductImage.objects.get(product=product, is_primary=True).pk == img2.pk


class TestProductVariantProperties:
    """Cover ProductVariant.full_sku and final_price (lines 198-201)"""

    @pytest.mark.django_db
    def test_full_sku_with_suffix(self, product):
        variant = ProductVariant.objects.create(
            product=product, name="Size", value="L", sku_suffix="L", stock_quantity=5
        )
        assert variant.full_sku == f"{product.sku}-L"

    @pytest.mark.django_db
    def test_full_sku_no_suffix(self, product):
        variant = ProductVariant.objects.create(
            product=product, name="Size", value="M", stock_quantity=5
        )
        assert variant.full_sku == product.sku

    @pytest.mark.django_db
    def test_final_price(self, product):
        variant = ProductVariant.objects.create(
            product=product,
            name="Size",
            value="XL",
            price_adjustment=Decimal("5.00"),
            stock_quantity=5,
        )
        expected = product.price + Decimal("5.00")
        assert variant.final_price == expected


# ---------------------------------------------------------------------------
# products/views.py — uncovered branches
# ---------------------------------------------------------------------------


class TestProductListViewExtra:
    """Cover price filter and slug-based category (lines 46,56,58)"""

    @pytest.mark.django_db
    def test_price_filter_min(self, client, category):
        Product.objects.create(
            name="Cheap",
            slug="cheap",
            description="d",
            price=Decimal("5.00"),
            category=category,
            stock_quantity=10,
            sku="CHEAP-001",
            is_active=True,
        )
        Product.objects.create(
            name="Expensive",
            slug="expensive",
            description="d",
            price=Decimal("200.00"),
            category=category,
            stock_quantity=10,
            sku="EXP-001",
            is_active=True,
        )
        response = client.get(reverse("products:product_list"), {"min_price": "100"})
        assert response.status_code == 200
        names = [p.name for p in response.context["products"]]
        assert "Expensive" in names
        assert "Cheap" not in names

    @pytest.mark.django_db
    def test_price_filter_max(self, client, category):
        Product.objects.create(
            name="Cheap2",
            slug="cheap2",
            description="d",
            price=Decimal("5.00"),
            category=category,
            stock_quantity=10,
            sku="CHEAP-002",
            is_active=True,
        )
        Product.objects.create(
            name="Expensive2",
            slug="expensive2",
            description="d",
            price=Decimal("200.00"),
            category=category,
            stock_quantity=10,
            sku="EXP-002",
            is_active=True,
        )
        response = client.get(reverse("products:product_list"), {"max_price": "50"})
        assert response.status_code == 200
        names = [p.name for p in response.context["products"]]
        assert "Cheap2" in names
        assert "Expensive2" not in names

    @pytest.mark.django_db
    def test_sort_by_price(self, client, category):
        """sort= GET parameter is applied"""
        response = client.get(reverse("products:product_list"), {"sort": "price"})
        assert response.status_code == 200


class TestProductSearchView:
    """Cover ProductSearchView (lines 135-148)"""

    @pytest.mark.django_db
    def test_search_with_query(self, client, category):
        Product.objects.create(
            name="Widget Pro",
            slug="widget-pro",
            description="A widget",
            price=Decimal("29.99"),
            category=category,
            stock_quantity=5,
            sku="WGT-001",
            is_active=True,
        )
        response = client.get(reverse("products:search"), {"q": "widget"})
        assert response.status_code == 200
        assert response.context["query"] == "widget"
        names = [p.name for p in response.context["products"]]
        assert "Widget Pro" in names

    @pytest.mark.django_db
    def test_search_empty_query(self, client):
        """Empty search returns empty queryset"""
        response = client.get(reverse("products:search"), {"q": ""})
        assert response.status_code == 200
        assert len(response.context["products"]) == 0

    @pytest.mark.django_db
    def test_search_no_query_param(self, client):
        """Missing q param returns empty queryset"""
        response = client.get(reverse("products:search"))
        assert response.status_code == 200
        assert len(response.context["products"]) == 0


# ---------------------------------------------------------------------------
# orders/admin.py — admin methods (lines 22,33,101,104,109-116,127-129,133)
# ---------------------------------------------------------------------------


class TestOrderAdminMethods:
    """Cover OrderAdmin custom methods"""

    @pytest.fixture
    def admin_site(self):
        return AdminSite()

    @pytest.fixture
    def order_admin(self, admin_site):
        return OrderAdmin(Order, admin_site)

    @pytest.fixture
    def cart_admin(self, admin_site):
        return CartAdmin(Cart, admin_site)

    @pytest.fixture
    def cart_item_admin(self, admin_site):
        return CartItemAdmin(CartItem, admin_site)

    @pytest.fixture
    def order_item_admin(self, admin_site):
        return OrderItemAdmin(OrderItem, admin_site)

    @pytest.mark.django_db
    def test_cart_admin_get_queryset(self, cart_admin, rf, admin_user):
        request = rf.get("/")
        request.user = admin_user
        qs = cart_admin.get_queryset(request)
        assert qs is not None

    @pytest.mark.django_db
    def test_cart_item_admin_get_queryset(self, cart_item_admin, rf, admin_user):
        request = rf.get("/")
        request.user = admin_user
        qs = cart_item_admin.get_queryset(request)
        assert qs is not None

    @pytest.mark.django_db
    def test_order_admin_get_queryset(self, order_admin, rf, admin_user):
        request = rf.get("/")
        request.user = admin_user
        qs = order_admin.get_queryset(request)
        assert qs is not None

    @pytest.mark.django_db
    def test_order_admin_full_name(self, order_admin, order):
        result = order_admin.full_name(order)
        assert result == order.full_name

    @pytest.mark.django_db
    def test_order_admin_save_model_shipped(self, order_admin, order, rf, admin_user):
        """save_model sets shipped_at when status transitions to 'shipped'"""
        request = rf.post("/")
        request.user = admin_user
        order.status = "shipped"
        form = MagicMock()
        form.changed_data = ["status"]
        order_admin.save_model(request, order, form, change=True)
        order.refresh_from_db()
        assert order.shipped_at is not None

    @pytest.mark.django_db
    def test_order_admin_save_model_delivered(self, order_admin, order, rf, admin_user):
        """save_model sets delivered_at when status transitions to 'delivered'"""
        request = rf.post("/")
        request.user = admin_user
        order.status = "delivered"
        form = MagicMock()
        form.changed_data = ["status"]
        order_admin.save_model(request, order, form, change=True)
        order.refresh_from_db()
        assert order.delivered_at is not None

    @pytest.mark.django_db
    def test_order_admin_save_model_no_status_change(
        self, order_admin, order, rf, admin_user
    ):
        """save_model with no status change doesn't set timestamps"""
        request = rf.post("/")
        request.user = admin_user
        form = MagicMock()
        form.changed_data = ["email"]  # status not changed
        order_admin.save_model(request, order, form, change=True)
        order.refresh_from_db()
        assert order.shipped_at is None
        assert order.delivered_at is None

    @pytest.mark.django_db
    def test_order_item_admin_variant_info_with_values(
        self, order_item_admin, order, product
    ):
        item = OrderItem.objects.create(
            order=order,
            product=product,
            quantity=1,
            unit_price=product.price,
        )
        item.variant_name = "Size"
        item.variant_value = "L"
        result = order_item_admin.variant_info(item)
        assert result == "Size: L"

    @pytest.mark.django_db
    def test_order_item_admin_variant_info_empty(
        self, order_item_admin, order, product
    ):
        item = OrderItem.objects.create(
            order=order,
            product=product,
            quantity=1,
            unit_price=product.price,
        )
        result = order_item_admin.variant_info(item)
        assert result == "-"

    @pytest.mark.django_db
    def test_order_item_admin_get_queryset(self, order_item_admin, rf, admin_user):
        request = rf.get("/")
        request.user = admin_user
        qs = order_item_admin.get_queryset(request)
        assert qs is not None


# ---------------------------------------------------------------------------
# context_processors — anonymous session cart (lines 27-28)
# ---------------------------------------------------------------------------


class TestGlobalContextProcessor:
    """Cover context_processors/__init__.py anonymous cart path (lines 27-28)"""

    @pytest.mark.django_db
    def test_anonymous_user_with_session_cart(self, rf, product):
        """Anonymous user with a session cart gets cart_items_count > 0"""
        request = rf.get("/")
        # Simulate an anonymous user
        from django.contrib.auth.models import AnonymousUser

        request.user = AnonymousUser()

        # Create session and anonymous cart
        session_key = "anon_test_session_xyz"
        cart = Cart.objects.create(session_key=session_key)
        CartItem.objects.create(cart=cart, product=product, quantity=3)

        # Attach session_key to request session mock
        request.session = MagicMock()
        request.session.session_key = session_key

        ctx = global_context(request)
        assert ctx["cart_items_count"] == 3
        assert ctx["current_cart"] == cart

    @pytest.mark.django_db
    def test_anonymous_user_no_session(self, rf):
        """Anonymous user with no session key gets count=0"""
        request = rf.get("/")
        from django.contrib.auth.models import AnonymousUser

        request.user = AnonymousUser()
        request.session = MagicMock()
        request.session.session_key = None

        ctx = global_context(request)
        assert ctx["cart_items_count"] == 0
        assert ctx["current_cart"] is None

    @pytest.mark.django_db
    def test_anonymous_user_session_no_cart(self, rf):
        """Anonymous user with session key but no cart gets count=0"""
        request = rf.get("/")
        from django.contrib.auth.models import AnonymousUser

        request.user = AnonymousUser()
        request.session = MagicMock()
        request.session.session_key = "nonexistent_session_key_abc"

        ctx = global_context(request)
        assert ctx["cart_items_count"] == 0
        assert ctx["current_cart"] is None


# ---------------------------------------------------------------------------
# Management commands — to 75%+ coverage
# ---------------------------------------------------------------------------


class TestManagementCommands:
    """Cover products/management/commands/ to 75%+"""

    @pytest.mark.django_db
    def test_add_sample_carts_no_users(self, capsys):
        """Command handles case where no non-superuser users exist"""
        from products.management.commands.add_sample_carts import Command

        cmd = Command()
        out = io.StringIO()
        cmd.stdout = OutputWrapper(out)
        cmd.stderr = OutputWrapper(io.StringIO())
        cmd.style = MagicMock()
        cmd.style.ERROR = lambda x: x
        # Ensure no non-superuser users
        User.objects.filter(is_superuser=False).delete()
        cmd.handle()
        output = out.getvalue()
        assert "Creating sample cart items" in output

    @pytest.mark.django_db
    def test_add_sample_carts_with_users(self, product, category):
        """Command creates cart items for non-superuser users"""
        from products.management.commands.add_sample_carts import Command

        user = User.objects.create_user(
            username="cartcmd_user", password="pass", email="cartcmd@example.com"
        )
        UserProfile.objects.get_or_create(user=user)
        cmd = Command()
        cmd.stdout = OutputWrapper(io.StringIO())
        cmd.stderr = OutputWrapper(io.StringIO())
        cmd.style = MagicMock()
        cmd.style.ERROR = lambda x: x
        cmd.style.SUCCESS = lambda x: x  # must return a string
        cmd.handle()
        assert Cart.objects.filter(user=user).exists()

    @pytest.mark.django_db
    def test_create_sample_data_command(self):
        """create_sample_data Command runs without error"""
        from products.management.commands.create_sample_data import Command

        cmd = Command()
        cmd.stdout = OutputWrapper(io.StringIO())
        cmd.stderr = OutputWrapper(io.StringIO())
        cmd.style = MagicMock()
        cmd.style.SUCCESS = lambda x: x
        cmd.style.ERROR = lambda x: x
        cmd.handle(clear=False)
        # Should have created categories and products
        assert Category.objects.exists()
        assert Product.objects.exists()


# ---------------------------------------------------------------------------
# Fixtures reused from conftest (rf fixture for RequestFactory)
# ---------------------------------------------------------------------------


@pytest.fixture
def rf():
    return RequestFactory()


@pytest.fixture
def admin_user():
    return User.objects.create_superuser(
        username="admin_cov", email="admin_cov@example.com", password="adminpass"
    )
