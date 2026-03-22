"""
Factory Boy factories for all ShopHub application models (T025, T030, T037).

Usage:
    from tests.factories import UserFactory, ProductFactory, OrderFactory
    user = UserFactory()
    product = ProductFactory()
    order = OrderFactory(user=user)
"""

import uuid
from decimal import Decimal

import factory
import factory.django

from django.contrib.auth.models import User

from accounts.models import UserProfile
from orders.models import Cart, CartItem, Order, OrderItem
from products.models import Category, Product, ProductImage, ProductReview, ProductVariant


# ---------------------------------------------------------------------------
# Accounts factories
# ---------------------------------------------------------------------------


class UserFactory(factory.django.DjangoModelFactory):
    """
    Creates a Django User.  The post_save signal on User auto-creates a
    UserProfile, so no explicit profile creation is needed here.
    """

    class Meta:
        model = User
        django_get_or_create = ("username",)

    username = factory.Sequence(lambda n: f"user{n}")
    email = factory.LazyAttribute(lambda o: f"{o.username}@example.com")
    first_name = factory.Faker("first_name")
    last_name = factory.Faker("last_name")

    @classmethod
    def _create(cls, model_class, *args, **kwargs):
        """Use create_user so the password is properly hashed."""
        manager = cls._get_manager(model_class)
        return manager.create_user(*args, **kwargs)


class UserProfileFactory(factory.django.DjangoModelFactory):
    """
    Returns (or creates) the UserProfile for a User.

    Because the signal auto-creates a profile on User creation,
    we use django_get_or_create to avoid IntegrityError when used
    alongside UserFactory().
    """

    class Meta:
        model = UserProfile
        django_get_or_create = ("user",)

    user = factory.SubFactory(UserFactory)


# ---------------------------------------------------------------------------
# Products factories
# ---------------------------------------------------------------------------


class CategoryFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Category

    name = factory.Sequence(lambda n: f"Category {n}")
    is_active = True
    parent = None


class ProductFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Product

    name = factory.Sequence(lambda n: f"Product {n}")
    category = factory.SubFactory(CategoryFactory)
    description = factory.Faker("paragraph")
    price = Decimal("99.99")
    sku = factory.Sequence(lambda n: f"SKU-{n:05d}")
    stock_quantity = 10
    is_active = True


class ProductImageFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = ProductImage

    product = factory.SubFactory(ProductFactory)
    image = factory.django.ImageField(color="blue")
    alt_text = factory.Faker("sentence", nb_words=4)
    is_primary = False
    sort_order = 0


class ProductVariantFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = ProductVariant

    product = factory.SubFactory(ProductFactory)
    name = "Size"
    value = "M"
    price_adjustment = Decimal("0.00")


class ProductReviewFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = ProductReview

    product = factory.SubFactory(ProductFactory)
    user = factory.SubFactory(UserFactory)
    rating = 5
    title = factory.Faker("sentence", nb_words=5)
    body = factory.Faker("paragraph")
    is_approved = False


# ---------------------------------------------------------------------------
# Orders factories
# ---------------------------------------------------------------------------


class CartFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Cart

    user = None
    session_key = factory.LazyFunction(lambda: uuid.uuid4().hex[:40])


class CartItemFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = CartItem

    cart = factory.SubFactory(CartFactory)
    product = factory.SubFactory(ProductFactory)
    variant = None
    quantity = 1


class OrderFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Order

    user = factory.SubFactory(UserFactory)
    email = factory.LazyAttribute(lambda o: o.user.email)
    first_name = "Test"
    last_name = "User"
    billing_address_line_1 = "123 Main St"
    billing_city = "Springfield"
    billing_state_province = "IL"
    billing_postal_code = "62701"
    billing_country = "US"
    status = "pending"


class OrderItemFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = OrderItem

    order = factory.SubFactory(OrderFactory)
    product = factory.SubFactory(ProductFactory)
    unit_price = Decimal("49.99")
    quantity = 1
