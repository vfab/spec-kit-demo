"""
Shared pytest fixtures for ShopHub test suite (T048).

These fixtures provide common objects used across test modules,
built on top of the factory-boy factories in tests/factories.py.
"""

import pytest

from tests.factories import (
    CartFactory,
    CategoryFactory,
    OrderFactory,
    ProductFactory,
    UserFactory,
)


@pytest.fixture()
def user(db):
    """A regular test user with auto-created UserProfile (via signal)."""
    return UserFactory()


@pytest.fixture()
def user_profile(user):
    """The UserProfile auto-created by the post_save signal on ``user``."""
    return user.profile


@pytest.fixture()
def category(db):
    """A single active Category."""
    return CategoryFactory()


@pytest.fixture()
def product(category):
    """A single active Product in ``category``."""
    return ProductFactory(category=category)


@pytest.fixture()
def cart(user):
    """An authenticated Cart belonging to ``user``."""
    return CartFactory(user=user, session_key=None)


@pytest.fixture()
def order(user):
    """A pending Order belonging to ``user``."""
    return OrderFactory(user=user)
