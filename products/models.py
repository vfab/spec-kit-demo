"""Data models for the products app: Category, Product, ProductImage."""

import os

from PIL import Image

from django.conf import settings
from django.core.cache import cache
from django.core.exceptions import ValidationError
from django.core.validators import (
    FileExtensionValidator,
    MaxValueValidator,
    MinValueValidator,
)
from django.db import models
from django.db.models.signals import post_delete, post_save
from django.dispatch import receiver
from django.urls import reverse
from django.utils.text import slugify


def validate_image_file_size(image):
    """Reject uploads larger than settings.MAX_IMAGE_UPLOAD_MB (M2).

    Reads actual bytes rather than trusting the client-supplied Content-Length
    header (S1).  Works for both InMemoryUploadedFile and TemporaryUploadedFile.
    """
    max_mb = getattr(settings, "MAX_IMAGE_UPLOAD_MB", 5)
    max_bytes = max_mb * 1024 * 1024

    # Prefer OS-level file size (not spoofable) when the upload is on disk.
    if hasattr(image, "temporary_file_path"):
        actual_size = os.stat(image.temporary_file_path()).st_size
    else:
        # InMemoryUploadedFile: read the buffer length directly.
        actual_size = image.size  # already the buffer length, not Content-Length

    if actual_size > max_bytes:
        raise ValidationError(
            f"Image file too large. Maximum allowed size is {max_mb} MB "
            f"(uploaded file is {actual_size / 1024 / 1024:.1f} MB)."
        )


class Category(models.Model):
    """
    Product category model
    """

    name = models.CharField(max_length=200, unique=True)
    slug = models.SlugField(max_length=200, unique=True, blank=True)
    description = models.TextField(blank=True, null=True)
    image = models.ImageField(upload_to="categories/", blank=True, null=True)
    parent = models.ForeignKey(
        "self", on_delete=models.CASCADE, null=True, blank=True, related_name="children"
    )
    is_active = models.BooleanField(default=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Category"
        verbose_name_plural = "Categories"
        ordering = ["name"]
        indexes = [
            models.Index(fields=["slug"]),
            models.Index(fields=["is_active", "name"]),
        ]

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)

    def __str__(self):
        return self.name

    def get_absolute_url(self):
        return reverse("products:category", kwargs={"slug": self.slug})


class Product(models.Model):
    """
    Main product model
    """

    name = models.CharField(max_length=200)
    slug = models.SlugField(max_length=200, unique=True, blank=True)
    category = models.ForeignKey(
        Category, on_delete=models.CASCADE, related_name="products"
    )
    description = models.TextField()
    short_description = models.CharField(max_length=500, blank=True, null=True)

    # Pricing
    price = models.DecimalField(max_digits=10, decimal_places=2)
    compare_price = models.DecimalField(
        max_digits=10, decimal_places=2, blank=True, null=True
    )
    cost_price = models.DecimalField(
        max_digits=10, decimal_places=2, blank=True, null=True
    )

    # Inventory
    sku = models.CharField(max_length=100, unique=True)
    stock_quantity = models.PositiveIntegerField(default=0)
    track_inventory = models.BooleanField(default=True)
    allow_backorders = models.BooleanField(default=False)

    # Product attributes
    weight = models.DecimalField(max_digits=8, decimal_places=2, blank=True, null=True)
    dimensions_length = models.DecimalField(
        max_digits=8, decimal_places=2, blank=True, null=True
    )
    dimensions_width = models.DecimalField(
        max_digits=8, decimal_places=2, blank=True, null=True
    )
    dimensions_height = models.DecimalField(
        max_digits=8, decimal_places=2, blank=True, null=True
    )

    # SEO
    meta_title = models.CharField(max_length=200, blank=True, null=True)
    meta_description = models.CharField(max_length=500, blank=True, null=True)

    # Status
    is_active = models.BooleanField(default=True)
    is_featured = models.BooleanField(default=False)
    is_digital = models.BooleanField(default=False)

    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Product"
        verbose_name_plural = "Products"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["slug"]),
            models.Index(fields=["sku"]),
            models.Index(fields=["is_active", "-created_at"]),
        ]

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)

    def __str__(self):
        return self.name

    def get_absolute_url(self):
        return reverse("products:product_detail", kwargs={"slug": self.slug})

    @property
    def is_on_sale(self):
        return self.compare_price and self.compare_price > self.price

    @property
    def discount_percentage(self):
        if self.is_on_sale:
            return int(((self.compare_price - self.price) / self.compare_price) * 100)
        return 0

    @property
    def is_in_stock(self):
        if not self.track_inventory:
            return True
        return self.stock_quantity > 0 or self.allow_backorders

    @property
    def main_image(self):
        # Use the prefetch cache when images are prefetched (avoids N+1 on
        # list views that call prefetch_related('images')).
        cache = getattr(self, "_prefetched_objects_cache", {})
        if "images" in cache:
            for img in cache["images"]:
                if img.is_primary:
                    return img
            # No primary set — fall back to first image in the prefetch.
            images = cache["images"]
            return images[0] if images else None
        return self.images.filter(is_primary=True).first()


class ProductImage(models.Model):
    """
    Product images model
    """

    product = models.ForeignKey(
        Product, on_delete=models.CASCADE, related_name="images"
    )
    image = models.ImageField(
        upload_to="products/",
        validators=[
            FileExtensionValidator(
                allowed_extensions=["jpg", "jpeg", "png", "webp", "gif"]
            ),
            validate_image_file_size,
        ],
    )
    alt_text = models.CharField(max_length=200, blank=True, null=True)
    is_primary = models.BooleanField(default=False)
    sort_order = models.PositiveIntegerField(default=0)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Product Image"
        verbose_name_plural = "Product Images"
        ordering = ["sort_order", "-created_at"]
        indexes = [
            # Speeds up Product.main_image (filter product + is_primary)
            models.Index(fields=["product", "is_primary"]),
        ]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # L2: Track the image name at load time so save() can detect whether the
        # image file itself changed and skip the expensive resize when it hasn't.
        self._original_image_name = self.image.name if self.image else None

    def save(self, *args, **kwargs):
        # Ensure only one primary image per product
        if self.is_primary:
            ProductImage.objects.filter(product=self.product, is_primary=True).update(
                is_primary=False
            )
        super().save(*args, **kwargs)

        # L2: Only re-compress when the image file is new or has been replaced.
        image_changed = self.image and self.image.name != self._original_image_name
        if image_changed:
            self.resize_image()
            # Update the baseline so subsequent metadata saves don't re-trigger.
            self._original_image_name = self.image.name

    def resize_image(self):
        """Resize image to optimise for web,
        preserving transparency for PNG/WebP (M3)."""
        img = Image.open(self.image.path)
        ext = os.path.splitext(self.image.path)[1].lower()
        # Formats that support an alpha channel — preserve their mode.
        transparent_formats = {".png", ".webp"}
        if ext not in transparent_formats and img.mode in ("RGBA", "P"):
            # JPEG and GIF don't support transparency; flatten onto white.
            background = Image.new("RGB", img.size, (255, 255, 255))
            if img.mode == "P":
                img = img.convert("RGBA")
            background.paste(img, mask=img.split()[3])  # use alpha channel as mask
            img = background
        elif img.mode == "P":
            # Paletted PNG/WebP — convert to RGBA so Pillow can handle it cleanly.
            img = img.convert("RGBA")

        # Resize if too large
        max_size = (800, 800)
        img.thumbnail(max_size, Image.Resampling.LANCZOS)

        # Save optimised image; format is inferred from the file extension.
        save_kwargs = {"optimize": True}
        if img.mode not in ("RGBA", "P") or ext not in transparent_formats:
            save_kwargs["quality"] = 85
        img.save(self.image.path, **save_kwargs)

    def __str__(self):
        return f"{self.product.name} - Image {self.id}"


class ProductVariant(models.Model):
    """
    Product variants (size, color, etc.)
    """

    product = models.ForeignKey(
        Product, on_delete=models.CASCADE, related_name="variants"
    )
    name = models.CharField(max_length=100)  # e.g., "Size", "Color"
    value = models.CharField(max_length=100)  # e.g., "Large", "Red"

    # Pricing override
    price_adjustment = models.DecimalField(max_digits=10, decimal_places=2, default=0)

    # Inventory override
    sku_suffix = models.CharField(max_length=50, blank=True, null=True)
    stock_quantity = models.PositiveIntegerField(default=0)

    is_active = models.BooleanField(default=True)
    sort_order = models.PositiveIntegerField(default=0)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Product Variant"
        verbose_name_plural = "Product Variants"
        ordering = ["sort_order", "name", "value"]
        unique_together = ["product", "name", "value"]

    def __str__(self):
        return f"{self.product.name} - {self.name}: {self.value}"

    @property
    def full_sku(self):
        base_sku = self.product.sku
        if self.sku_suffix:
            return f"{base_sku}-{self.sku_suffix}"
        return base_sku

    @property
    def final_price(self):
        return self.product.price + self.price_adjustment


class ProductReview(models.Model):
    """
    Customer reviews for products (FR-017).
    """

    product = models.ForeignKey(
        Product, on_delete=models.CASCADE, related_name="reviews"
    )
    user = models.ForeignKey(
        "auth.User", on_delete=models.CASCADE, related_name="reviews"
    )
    rating = models.PositiveSmallIntegerField(
        validators=[
            MinValueValidator(1),
            MaxValueValidator(5),
        ]
    )
    title = models.CharField(max_length=200, blank=True)
    body = models.TextField()
    is_approved = models.BooleanField(default=False)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Product Review"
        verbose_name_plural = "Product Reviews"
        unique_together = [["product", "user"]]
        ordering = ["-created_at"]

    def __str__(self):
        return f"Review by {self.user} on {self.product} ({self.rating}/5)"


# ---------------------------------------------------------------------------
# Cache invalidation signals (EPIC-11 T3)
#
# Whenever a Category or Product is saved or deleted we purge the relevant
# cache keys so the next request fetches fresh data from the database.
# ---------------------------------------------------------------------------


def _invalidate_category_cache(sender, instance, **kwargs):  # noqa: ARG001
    """Clear cached category lists when any category changes."""
    cache.delete("product_categories")
    cache.delete("home_page_data")
    # Redis supports pattern deletion for list page variants; on LocMemCache
    # we only delete the keys we know about to avoid wiping unrelated entries.
    if hasattr(cache, "delete_pattern"):
        cache.delete_pattern("product_list:*")


def _invalidate_product_cache(sender, instance, **kwargs):  # noqa: ARG001
    """Clear cached product data when any product changes."""
    # Specific product detail (pk-based and slug-based alias keys)
    cache.delete(f"product_detail:{instance.pk}")
    cache.delete(f"product_detail_slug:{instance.slug}")
    # Home page embeds featured products
    cache.delete("home_page_data")
    # Redis supports pattern deletion for list page variants; on LocMemCache
    # we only delete the keys we know about to avoid wiping unrelated entries.
    if hasattr(cache, "delete_pattern"):
        cache.delete_pattern("product_list:*")


@receiver(post_save, sender=Category)
@receiver(post_delete, sender=Category)
def on_category_change(sender, instance, **kwargs):
    """Invalidate category and product list caches on any category mutation."""
    _invalidate_category_cache(sender, instance, **kwargs)


@receiver(post_save, sender=Product)
@receiver(post_delete, sender=Product)
def on_product_change(sender, instance, **kwargs):
    """Invalidate product caches on any product mutation."""
    _invalidate_product_cache(sender, instance, **kwargs)


@receiver(post_save, sender="products.ProductVariant")
@receiver(post_delete, sender="products.ProductVariant")
def on_variant_change(sender, instance, **kwargs):
    """Invalidate the parent product's cache when a variant changes.

    Variant mutations (stock quantity, price adjustment) affect the product
    detail page, so the cached product object must be evicted.
    """
    cache.delete(f"product_detail:{instance.product_id}")
    cache.delete(f"product_detail_slug:{instance.product.slug}")
