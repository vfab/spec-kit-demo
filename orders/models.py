"""Data models for the orders app (Cart, CartItem, Order, OrderItem)."""

import datetime
import uuid
from decimal import Decimal

from django.contrib.auth.models import User
from django.core.validators import MinValueValidator
from django.db import models
from django.db.models import Q

from core.validators import phone_regex


class Cart(models.Model):
    """
    Shopping cart model
    """

    user = models.OneToOneField(
        User, on_delete=models.CASCADE, related_name="cart", null=True, blank=True
    )
    session_key = models.CharField(
        max_length=40, null=True, blank=True
    )  # For anonymous users

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Shopping Cart"
        verbose_name_plural = "Shopping Carts"
        ordering = ["-updated_at"]

    def __str__(self):
        if self.user:
            return f"Cart for {self.user.username}"
        return f"Anonymous Cart ({self.session_key})"

    @property
    def total_items(self):
        # Use the prefetch cache when available (R2: avoids redundant DB hits
        # when the caller already called .prefetch_related('items')).
        cache = getattr(self, "_prefetched_objects_cache", {})
        if "items" in cache:
            return sum(item.quantity for item in cache["items"])
        return sum(item.quantity for item in self.items.all())

    @property
    def total_price(self):
        cache = getattr(self, "_prefetched_objects_cache", {})
        if "items" in cache:
            return sum(item.total_price for item in cache["items"])
        return sum(item.total_price for item in self.items.all())

    def clear(self):
        self.items.all().delete()


class CartItem(models.Model):
    """
    Items in shopping cart
    """

    cart = models.ForeignKey(Cart, on_delete=models.CASCADE, related_name="items")
    product = models.ForeignKey("products.Product", on_delete=models.CASCADE)
    variant = models.ForeignKey(
        "products.ProductVariant", on_delete=models.CASCADE, null=True, blank=True
    )
    quantity = models.PositiveIntegerField(default=1, validators=[MinValueValidator(1)])

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Cart Item"
        verbose_name_plural = "Cart Items"
        unique_together = ["cart", "product", "variant"]
        constraints = [
            # L1: Enforce uniqueness when no variant is selected (NULL != NULL in SQL,
            # so unique_together alone doesn't prevent duplicate base-product rows).
            models.UniqueConstraint(
                fields=["cart", "product"],
                condition=Q(variant__isnull=True),
                name="unique_cart_product_no_variant",
            ),
        ]
        ordering = ["-created_at"]
        indexes = [
            # Fast cart contents lookup (used on every cart page load)
            models.Index(fields=["cart", "-created_at"]),
        ]

    def __str__(self):
        variant_info = (
            f" ({self.variant.name}: {self.variant.value})" if self.variant else ""
        )
        return f"{self.product.name}{variant_info} x{self.quantity}"

    @property
    def unit_price(self):
        if self.variant:
            return self.variant.final_price
        return self.product.price

    @property
    def total_price(self):
        return self.unit_price * self.quantity


class Order(models.Model):
    """
    Order model
    """

    ORDER_STATUS_CHOICES = [
        ("pending", "Pending"),
        ("confirmed", "Confirmed"),
        ("processing", "Processing"),
        ("shipped", "Shipped"),
        ("delivered", "Delivered"),
        ("cancelled", "Cancelled"),
        ("refunded", "Refunded"),
    ]

    PAYMENT_STATUS_CHOICES = [
        ("pending", "Pending"),
        ("paid", "Paid"),
        ("failed", "Failed"),
        ("refunded", "Refunded"),
        ("partial_refund", "Partially Refunded"),
    ]

    # Order identification
    order_number = models.CharField(max_length=50, unique=True, editable=False)
    user = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name="orders", null=True, blank=True
    )

    # Customer information
    email = models.EmailField()
    first_name = models.CharField(max_length=100)
    last_name = models.CharField(max_length=100)
    phone_number = models.CharField(
        max_length=20, blank=True, null=True, validators=[phone_regex]
    )

    # Billing address
    billing_address_line_1 = models.CharField(max_length=255)
    billing_address_line_2 = models.CharField(max_length=255, blank=True, null=True)
    billing_city = models.CharField(max_length=100)
    billing_state_province = models.CharField(max_length=100)
    billing_postal_code = models.CharField(max_length=20)
    billing_country = models.CharField(max_length=100)

    # Shipping address
    shipping_same_as_billing = models.BooleanField(default=True)
    shipping_address_line_1 = models.CharField(max_length=255, blank=True, null=True)
    shipping_address_line_2 = models.CharField(max_length=255, blank=True, null=True)
    shipping_city = models.CharField(max_length=100, blank=True, null=True)
    shipping_state_province = models.CharField(max_length=100, blank=True, null=True)
    shipping_postal_code = models.CharField(max_length=20, blank=True, null=True)
    shipping_country = models.CharField(max_length=100, blank=True, null=True)

    # Order totals
    subtotal = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=Decimal("0.00"),
        validators=[MinValueValidator(Decimal("0.00"))],
    )
    tax_amount = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=Decimal("0.00"),
        validators=[MinValueValidator(Decimal("0.00"))],
    )
    shipping_cost = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=Decimal("0.00"),
        validators=[MinValueValidator(Decimal("0.00"))],
    )
    discount_amount = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=Decimal("0.00"),
        validators=[MinValueValidator(Decimal("0.00"))],
    )
    total_amount = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=Decimal("0.00"),
        validators=[MinValueValidator(Decimal("0.00"))],
    )

    # Status
    status = models.CharField(
        max_length=20, choices=ORDER_STATUS_CHOICES, default="pending"
    )
    payment_status = models.CharField(
        max_length=20, choices=PAYMENT_STATUS_CHOICES, default="pending"
    )
    payment_method = models.CharField(max_length=50, default="credit_card")

    # Notes
    order_notes = models.TextField(blank=True, null=True)
    internal_notes = models.TextField(blank=True, null=True)  # Staff only

    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    shipped_at = models.DateTimeField(null=True, blank=True)
    delivered_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        verbose_name = "Order"
        verbose_name_plural = "Orders"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["order_number"]),
            models.Index(fields=["status", "-created_at"]),
            models.Index(fields=["user", "-created_at"]),
        ]

    def save(self, *args, **kwargs):
        if not self.order_number:
            self.order_number = self.generate_order_number()
        super().save(*args, **kwargs)

    def generate_order_number(self):
        """Generate unique order number"""
        now = datetime.datetime.now()
        return f"ORD-{now.strftime('%Y%m%d')}-{str(uuid.uuid4().hex[:8]).upper()}"

    def __str__(self):
        return f"Order {self.order_number}"

    @property
    def full_name(self):
        return f"{self.first_name} {self.last_name}"

    @property
    def billing_address(self):
        parts = [
            self.billing_address_line_1,
            self.billing_address_line_2,
            self.billing_city,
            self.billing_state_province,
            self.billing_postal_code,
            self.billing_country,
        ]
        return ", ".join([part for part in parts if part])

    @property
    def shipping_address(self):
        if self.shipping_same_as_billing:
            return self.billing_address

        parts = [
            self.shipping_address_line_1,
            self.shipping_address_line_2,
            self.shipping_city,
            self.shipping_state_province,
            self.shipping_postal_code,
            self.shipping_country,
        ]
        return ", ".join([part for part in parts if part])

    @property
    def can_be_cancelled(self):
        return self.status in ["pending", "confirmed"]

    @property
    def is_completed(self):
        return self.status in ["delivered", "cancelled", "refunded"]

    def recalculate_totals(self, tax_rate=None, save=True):
        """
        Recompute subtotal, tax_amount, and total_amount from current OrderItems.
        Call this after adding or modifying items (M6).
        tax_rate defaults to settings.TAX_RATE if not supplied.
        """
        from django.conf import settings as django_settings

        if tax_rate is None:
            tax_rate = Decimal(str(getattr(django_settings, "TAX_RATE", "0.08")))
        self.subtotal = sum(item.total_price for item in self.items.all())
        self.tax_amount = self.subtotal * tax_rate
        self.total_amount = (
            self.subtotal + self.tax_amount + self.shipping_cost - self.discount_amount
        )
        if save:
            self.save(update_fields=["subtotal", "tax_amount", "total_amount"])


class OrderItem(models.Model):
    """
    Items in an order
    """

    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name="items")
    product = models.ForeignKey("products.Product", on_delete=models.CASCADE)
    variant = models.ForeignKey(
        "products.ProductVariant", on_delete=models.CASCADE, null=True, blank=True
    )

    # Product details at time of purchase (for historical accuracy)
    product_name = models.CharField(max_length=200)
    product_sku = models.CharField(max_length=100)
    variant_name = models.CharField(max_length=100, blank=True, null=True)
    variant_value = models.CharField(max_length=100, blank=True, null=True)

    quantity = models.PositiveIntegerField(validators=[MinValueValidator(1)])
    unit_price = models.DecimalField(max_digits=10, decimal_places=2)
    total_price = models.DecimalField(max_digits=10, decimal_places=2)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Order Item"
        verbose_name_plural = "Order Items"
        ordering = ["id"]

    def save(self, *args, **kwargs):
        # R5: Snapshot product/variant details at the time of purchase for
        # historical accuracy. The guards (if not self.product_name) are
        # intentional: on resaves (e.g. status updates) we preserve the
        # original values even if the live Product has since changed.
        if not self.product_name:
            self.product_name = self.product.name
        if not self.product_sku:
            self.product_sku = self.product.sku
        if self.variant and not self.variant_name:
            self.variant_name = self.variant.name
            self.variant_value = self.variant.value

        # Calculate total price
        self.total_price = self.unit_price * self.quantity
        super().save(*args, **kwargs)

    def __str__(self):
        variant_info = (
            f" ({self.variant_name}: {self.variant_value})" if self.variant_name else ""
        )
        return f"{self.product_name}{variant_info} x{self.quantity}"
