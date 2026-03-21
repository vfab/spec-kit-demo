"""
Pytest configuration and fixtures for ShopHub e-commerce testing
"""

import os

import pytest

import django

# Configure Django for testing before any Django imports below.
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "ecommerce_site.settings_test")
django.setup()

from decimal import Decimal  # noqa: E402

from django.contrib.auth.models import User  # noqa: E402
from django.test import Client  # noqa: E402

from accounts.models import UserProfile  # noqa: E402
from orders.models import Cart, CartItem, Order, OrderItem  # noqa: E402
from products.models import Category, Product, ProductVariant  # noqa: E402


@pytest.fixture
def client():
    """Django test client"""
    return Client()


@pytest.fixture
def user():
    """Create a test user"""
    user = User.objects.create_user(
        username="testuser",
        email="test@example.com",
        password="testpass123",
        first_name="Test",
        last_name="User",
    )
    # Ensure profile is created
    UserProfile.objects.get_or_create(user=user)
    return user


@pytest.fixture
def admin_user():
    """Create an admin user"""
    return User.objects.create_superuser(
        username="admin", email="admin@example.com", password="adminpass123"
    )


@pytest.fixture
def authenticated_client(client, user):
    """Client with authenticated user"""
    # Use force_login to bypass axes backend (which requires a request object
    # during authenticate() — not available in the fixture context).
    client.force_login(user)
    return client


@pytest.fixture
def category():
    """Create a test category"""
    return Category.objects.create(
        name="Test Category", slug="test-category", description="A test category"
    )


@pytest.fixture
def product(category):
    """Create a test product"""
    return Product.objects.create(
        name="Test Product",
        slug="test-product",
        description="A test product",
        price=Decimal("49.99"),
        category=category,
        stock_quantity=100,
        sku="TEST-001",
        is_active=True,
    )


@pytest.fixture
def product_variant(product):
    """Create a test product variant"""
    return ProductVariant.objects.create(
        product=product,
        name="Size",
        value="Test Variant",
        price_adjustment=Decimal("10.00"),
        stock_quantity=50,
    )


@pytest.fixture
def cart(user):
    """Create a test cart"""
    return Cart.objects.create(user=user)


@pytest.fixture
def cart_item(cart, product):
    """Create a test cart item"""
    return CartItem.objects.create(cart=cart, product=product, quantity=2)


@pytest.fixture
def order(user):
    """Create a test order"""
    return Order.objects.create(
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


@pytest.fixture
def order_item(order, product):
    """Create a test order item"""
    return OrderItem.objects.create(
        order=order, product=product, quantity=1, unit_price=product.price
    )


@pytest.fixture
def sample_data(db):
    """Create comprehensive sample data for testing"""
    # Create users
    user1 = User.objects.create_user(
        username="user1", email="user1@example.com", password="testpass123"
    )
    user2 = User.objects.create_user(
        username="user2", email="user2@example.com", password="testpass123"
    )

    # Create categories
    electronics = Category.objects.create(
        name="Sample Electronics",
        slug="sample-electronics",
        description="Electronic devices",
    )
    fashion = Category.objects.create(
        name="Sample Fashion",
        slug="sample-fashion",
        description="Clothing and accessories",
    )

    # Create products
    products = []
    for i in range(5):
        product = Product.objects.create(
            name=f"Sample Product {i+1}",
            slug=f"sample-product-{i+1}",
            description=f"Description for sample product {i+1}",
            price=Decimal(f"{(i+1)*10}.99"),
            category=electronics if i % 2 == 0 else fashion,
            stock_quantity=50,
            sku=f"SAMPLE-{i+1:03d}",
            is_active=True,
        )
        products.append(product)

    return {
        "users": [user1, user2],
        "categories": [electronics, fashion],
        "products": products,
    }
