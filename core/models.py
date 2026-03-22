"""Abstract base model providing shared timestamp fields for all application models."""

from django.db import models


class BaseModel(models.Model):
    """
    Abstract base model supplying created_at and updated_at to all concrete models.

    All 10 application models (UserProfile, Category, Product, ProductImage,
    ProductVariant, ProductReview, Cart, CartItem, Order, OrderItem) inherit
    from this class so timestamp behaviour is defined once.

    Design decision (data-model.md): PKs use Django's default AutoField
    (integer auto-increment).  Do NOT add a UUID id field here.
    """

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True
        ordering = ["-created_at"]
