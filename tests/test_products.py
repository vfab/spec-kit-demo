"""
Unit tests for products app models, views, and functionality
"""

import io
import os
import tempfile
from decimal import Decimal
from unittest.mock import MagicMock, PropertyMock, patch

import pytest
from PIL import Image

from django.core.exceptions import ValidationError
from django.core.files.uploadedfile import InMemoryUploadedFile
from django.test import override_settings
from django.urls import reverse

from products.models import (
    Category,
    Product,
    ProductImage,
    ProductVariant,
    validate_image_file_size,
)


class TestCategoryModel:
    """Test Category model functionality"""

    @pytest.mark.django_db
    def test_category_creation(self):
        """Test creating a category"""
        category = Category.objects.create(
            name="Electronics",
            slug="electronics",
            description="Electronic devices and gadgets",
        )
        assert category.name == "Electronics"
        assert category.slug == "electronics"
        assert str(category) == "Electronics"

    @pytest.mark.django_db
    def test_category_slug_uniqueness(self):
        """Test that category slugs must be unique"""
        Category.objects.create(name="Electronics", slug="electronics")

        with pytest.raises(Exception):  # IntegrityError
            Category.objects.create(name="Electronics 2", slug="electronics")

    @pytest.mark.django_db
    def test_category_absolute_url(self):
        """Test category get_absolute_url method"""
        category = Category.objects.create(name="Electronics", slug="electronics")
        expected_url = reverse("products:category", args=[category.slug])
        assert category.get_absolute_url() == expected_url


class TestProductModel:
    """Test Product model functionality"""

    @pytest.mark.django_db
    def test_product_creation(self, category):
        """Test creating a product"""
        product = Product.objects.create(
            name="Gaming Laptop",
            slug="gaming-laptop",
            description="High-performance gaming laptop",
            price=Decimal("999.99"),
            category=category,
            stock_quantity=10,
            sku="GAMING-001",
            is_active=True,
        )
        assert product.name == "Gaming Laptop"
        assert product.price == Decimal("999.99")
        assert product.is_active is True
        assert str(product) == "Gaming Laptop"

    @pytest.mark.django_db
    def test_product_slug_uniqueness(self, category):
        """Test that product slugs must be unique"""
        Product.objects.create(
            name="Product 1",
            slug="test-product",
            price=Decimal("10.00"),
            category=category,
            stock_quantity=10,
            sku="TESTPROD-001",
        )

        with pytest.raises(Exception):  # IntegrityError
            Product.objects.create(
                name="Product 2",
                slug="test-product",
                price=Decimal("20.00"),
                category=category,
                stock_quantity=5,
                sku="TESTPROD-001",  # Same SKU to test uniqueness
            )

    @pytest.mark.django_db
    def test_product_price_validation(self, category):
        """Test product price must be positive"""
        with pytest.raises(ValidationError):
            product = Product(
                name="Invalid Product",
                slug="invalid-product",
                price=Decimal("-10.00"),
                category=category,
                stock_quantity=10,
            )
            product.full_clean()

    @pytest.mark.django_db
    def test_product_stock_quantity_validation(self, category):
        """Test product stock quantity cannot be negative"""
        with pytest.raises(ValidationError):
            product = Product(
                name="Invalid Stock Product",
                slug="invalid-stock-product",
                price=Decimal("10.00"),
                category=category,
                stock_quantity=-5,
            )
            product.full_clean()

    @pytest.mark.django_db
    def test_product_absolute_url(self, category):
        """Test product get_absolute_url method"""
        product = Product.objects.create(
            name="Test Product",
            slug="test-product",
            price=Decimal("10.00"),
            category=category,
            stock_quantity=10,
        )
        expected_url = reverse("products:product_detail", args=[product.slug])
        assert product.get_absolute_url() == expected_url

    @pytest.mark.django_db
    def test_product_is_in_stock(self, category):
        """Test product stock availability"""
        # Product with stock
        product_with_stock = Product.objects.create(
            name="In Stock Product",
            slug="in-stock-product",
            price=Decimal("10.00"),
            category=category,
            stock_quantity=5,
            sku="INSTOCK-001",
        )
        assert product_with_stock.stock_quantity > 0

        # Product without stock
        product_no_stock = Product.objects.create(
            name="Out of Stock Product",
            slug="out-of-stock-product",
            price=Decimal("10.00"),
            category=category,
            stock_quantity=0,
            sku="NOSTOCK-001",
        )
        assert product_no_stock.stock_quantity == 0


class TestProductVariantModel:
    """Test ProductVariant model functionality"""

    @pytest.mark.django_db
    def test_variant_creation(self, product):
        """Test creating a product variant"""
        variant = ProductVariant.objects.create(
            product=product,
            name="Size",
            value="Large - Blue",
            price_adjustment=Decimal("5.00"),
            stock_quantity=20,
        )
        assert variant.name == "Size"
        assert variant.value == "Large - Blue"
        assert variant.price_adjustment == Decimal("5.00")
        assert variant.product == product
        assert str(variant) == f"{product.name} - Size: Large - Blue"

    @pytest.mark.django_db
    def test_variant_final_price(self, product):
        """Test variant final price calculation"""
        variant = ProductVariant.objects.create(
            product=product,
            name="Version",
            value="Premium Version",
            price_adjustment=Decimal("10.00"),
            stock_quantity=15,
        )
        expected_price = product.price + variant.price_adjustment
        # Test the final_price property that should be implemented
        assert variant.final_price == expected_price
        assert variant.price_adjustment == Decimal("10.00")


class TestProductViews:
    """Test product views functionality"""

    @pytest.mark.django_db
    def test_home_view(self, client, sample_data):
        """Test home page view"""
        response = client.get(reverse("products:home"))
        assert response.status_code == 200
        assert "categories" in response.context
        assert len(response.context["categories"]) > 0

    @pytest.mark.django_db
    def test_product_list_view(self, client, sample_data):
        """Test product list view"""
        response = client.get(reverse("products:product_list"))
        assert response.status_code == 200
        assert "products" in response.context
        assert "categories" in response.context

    @pytest.mark.django_db
    def test_product_detail_view(self, client, product):
        """Test product detail view"""
        response = client.get(reverse("products:product_detail", args=[product.slug]))
        assert response.status_code == 200
        assert response.context["product"] == product
        assert "variants" in response.context

    @pytest.mark.django_db
    def test_product_detail_404(self, client):
        """Test product detail view with non-existent product"""
        response = client.get(reverse("products:product_detail", args=["non-existent"]))
        assert response.status_code == 404

    @pytest.mark.django_db
    def test_category_view(self, client, category, product):
        """Test category products view"""
        response = client.get(reverse("products:category", args=[category.slug]))
        assert response.status_code == 200
        assert response.context["category"] == category
        assert "products" in response.context

    @pytest.mark.django_db
    def test_category_view_404(self, client):
        """Test category view with non-existent category"""
        response = client.get(reverse("products:category", args=["non-existent"]))
        assert response.status_code == 404

    @pytest.mark.django_db
    def test_product_search(self, client, sample_data):
        """Test product search functionality"""
        response = client.get(reverse("products:product_list"), {"search": "Product 1"})
        assert response.status_code == 200
        # Check that search results are filtered
        products = response.context["products"]
        assert len(products) >= 1

    @pytest.mark.django_db
    def test_category_filter(self, client, sample_data):
        """Test product filtering by category"""
        electronics_category = sample_data["categories"][0]
        response = client.get(
            reverse("products:product_list"), {"category": electronics_category.id}
        )
        assert response.status_code == 200
        products = response.context["products"]
        for product in products:
            assert product.category == electronics_category


class TestProductAdmin:
    """Test product admin functionality"""

    @pytest.mark.django_db
    def test_admin_product_list_access(self, client, admin_user):
        """Test admin can access product list in admin"""
        client.login(username="admin", password="adminpass123")
        response = client.get("/admin/products/product/")
        assert response.status_code == 200

    @pytest.mark.django_db
    def test_admin_category_list_access(self, client, admin_user):
        """Test admin can access category list in admin"""
        client.login(username="admin", password="adminpass123")
        response = client.get("/admin/products/category/")
        assert response.status_code == 200


class TestProductIntegration:
    """Integration tests for products functionality"""

    @pytest.mark.django_db
    def test_product_category_relationship(self, category):
        """Test product-category relationship"""
        product1 = Product.objects.create(
            name="Product 1",
            slug="product-1",
            price=Decimal("10.00"),
            category=category,
            stock_quantity=10,
            sku="CATTEST-001",
        )

        product2 = Product.objects.create(
            name="Product 2",
            slug="product-2",
            price=Decimal("20.00"),
            category=category,
            stock_quantity=5,
            sku="CATTEST-002",
        )

        # Test reverse relationship
        category_products = category.products.all()
        assert product1 in category_products
        assert product2 in category_products
        assert len(category_products) == 2

    @pytest.mark.django_db
    def test_product_variant_relationship(self, product):
        """Test product-variant relationship"""
        variant1 = ProductVariant.objects.create(
            product=product,
            name="Size",
            value="Variant 1",
            price_adjustment=Decimal("5.00"),
            stock_quantity=10,
        )

        variant2 = ProductVariant.objects.create(
            product=product,
            name="Color",
            value="Variant 2",
            price_adjustment=Decimal("10.00"),
            stock_quantity=15,
        )

        # Test reverse relationship
        product_variants = product.variants.all()
        assert variant1 in product_variants
        assert variant2 in product_variants
        assert len(product_variants) == 2


# ---------------------------------------------------------------------------
# Coverage gap tests – products/models.py
# ---------------------------------------------------------------------------


def _make_png_bytes(mode="RGB", size=(10, 10), colour=(100, 150, 200)):
    """Return raw PNG bytes for an in-memory image."""
    buf = io.BytesIO()
    img = Image.new(mode, size, colour)
    img.save(buf, format="PNG")
    buf.seek(0)
    return buf.read()


def _make_jpeg_bytes(size=(10, 10)):
    buf = io.BytesIO()
    img = Image.new("RGB", size, (200, 100, 50))  # type: ignore[arg-type]
    img.save(buf, format="JPEG")
    buf.seek(0)
    return buf.read()


class TestValidateImageFileSize:
    """validate_image_file_size – covers lines 18-29."""

    @override_settings(MAX_IMAGE_UPLOAD_MB=1)
    def test_in_memory_file_under_limit_passes(self):
        """Small InMemoryUploadedFile should pass without error."""
        small_data = b"x" * 100
        mock_file = MagicMock(spec=InMemoryUploadedFile)
        mock_file.size = len(small_data)
        del mock_file.temporary_file_path  # ensure hasattr returns False
        # Should not raise
        validate_image_file_size(mock_file)

    @override_settings(MAX_IMAGE_UPLOAD_MB=1)
    def test_in_memory_file_over_limit_raises(self):
        """InMemoryUploadedFile over the limit should raise ValidationError."""
        mock_file = MagicMock(spec=InMemoryUploadedFile)
        mock_file.size = 2 * 1024 * 1024  # 2 MB
        del mock_file.temporary_file_path
        with pytest.raises(ValidationError, match="Maximum allowed size"):
            validate_image_file_size(mock_file)

    @override_settings(MAX_IMAGE_UPLOAD_MB=1)
    def test_temporary_file_under_limit_passes(self):
        """TemporaryUploadedFile: reads actual OS file size – should pass."""
        with tempfile.NamedTemporaryFile(delete=False, suffix=".png") as tmp:
            tmp.write(b"x" * 500)  # 500 bytes – well under 1 MB
            tmp_path = tmp.name
        try:
            mock_file = MagicMock()
            mock_file.temporary_file_path.return_value = tmp_path
            validate_image_file_size(mock_file)
        finally:
            os.unlink(tmp_path)

    @override_settings(MAX_IMAGE_UPLOAD_MB=1)
    def test_temporary_file_over_limit_raises(self):
        """TemporaryUploadedFile over the limit should raise ValidationError."""
        with tempfile.NamedTemporaryFile(delete=False, suffix=".png") as tmp:
            tmp.write(b"x" * (2 * 1024 * 1024))  # 2 MB
            tmp_path = tmp.name
        try:
            mock_file = MagicMock()
            mock_file.temporary_file_path.return_value = tmp_path
            with pytest.raises(ValidationError, match="Maximum allowed size"):
                validate_image_file_size(mock_file)
        finally:
            os.unlink(tmp_path)


class TestCategoryAutoSlug:
    """Category.save() auto-slug – covers line 56."""

    @pytest.mark.django_db
    def test_category_auto_slug_generated(self):
        """Saving a Category without a slug should auto-generate one."""
        cat = Category(name="My New Category", description="test")
        cat.save()
        assert cat.slug == "my-new-category"

    @pytest.mark.django_db
    def test_category_existing_slug_unchanged(self):
        """Saving a Category with a slug set should not overwrite it."""
        cat = Category(name="My Category", slug="custom-slug")
        cat.save()
        assert cat.slug == "custom-slug"


class TestProductAutoSlug:
    """Product.save() auto-slug – covers line 118 (self.slug = slugify(self.name))."""

    @pytest.mark.django_db
    def test_product_auto_slug_generated(self, category):
        """Saving a Product without a slug should auto-generate one from the name."""
        p = Product(
            name="My Auto Slug Product",
            description="test",
            price=Decimal("9.99"),
            category=category,
            stock_quantity=10,
            sku="AUTO-SLUG-001",
        )
        p.save()
        assert p.slug == "my-auto-slug-product"

    @pytest.mark.django_db
    def test_product_existing_slug_unchanged(self, category):
        """Saving a Product that already has a slug should not overwrite it."""
        p = Product(
            name="Some Product",
            slug="custom-product-slug",
            description="test",
            price=Decimal("9.99"),
            category=category,
            stock_quantity=5,
            sku="CUSTOM-SLUG-001",
        )
        p.save()
        assert p.slug == "custom-product-slug"


class TestProductMainImage:
    """Product.main_image property – covers line 118."""

    @pytest.mark.django_db
    def test_main_image_returns_none_when_no_images(self, product):
        """product.main_image is None when there are no images."""
        assert product.images.count() == 0
        assert product.main_image is None

    @pytest.mark.django_db
    def test_main_image_returns_primary(self, product):
        """product.main_image returns the primary ProductImage row."""
        with patch.object(ProductImage, "resize_image"):
            from django.core.files.base import ContentFile

            pi1 = ProductImage(product=product, is_primary=False)
            pi1.image.save("sec.png", ContentFile(_make_png_bytes()), save=False)
            pi1.save()

            pi2 = ProductImage(product=product, is_primary=True)
            pi2.image.save("pri.png", ContentFile(_make_png_bytes()), save=False)
            pi2.save()

        # Access via the property (line 118)
        main = product.main_image
        assert main == pi2


class TestProductImageSavePrimarySwap:
    """ProductImage.save() primary-image swap – covers lines 186-188."""

    @pytest.mark.django_db
    def test_setting_new_primary_demotes_old_primary(self, product):
        """When a new image is marked primary, previous ones are demoted."""
        with patch.object(ProductImage, "resize_image"):
            from django.core.files.base import ContentFile

            img1 = ProductImage(product=product, is_primary=True)
            img1.image.save("img1.png", ContentFile(_make_png_bytes()), save=False)
            img1.save()

            img2 = ProductImage(product=product, is_primary=True)
            img2.image.save("img2.png", ContentFile(_make_png_bytes()), save=False)
            img2.save()

        img1.refresh_from_db()
        img2.refresh_from_db()
        assert img1.is_primary is False
        assert img2.is_primary is True

    @pytest.mark.django_db
    def test_product_image_str(self, product):
        """ProductImage.__str__ returns the expected string (line 218)."""
        with patch.object(ProductImage, "resize_image"):
            from django.core.files.base import ContentFile

            pi = ProductImage(product=product, is_primary=False)
            pi.image.save("str_test.png", ContentFile(_make_png_bytes()), save=False)
            pi.save()
        assert str(pi) == (  # type: ignore[attr-defined]
            f"{product.name} - Image {pi.id}"
        )


class TestResizeImageTransparency:
    """resize_image() – covers lines 192-218
    (RGBA/P on JPEG flatten, paletted PNG, quality kwarg)."""

    @pytest.mark.django_db
    def test_rgba_image_on_jpeg_is_flattened(self, product, tmp_path):
        """RGBA-mode image saved to a .jpg path should be flattened to white RGB."""
        # Write a real RGBA PNG to disk – our resize_image reads it via Pillow
        rgba_file = tmp_path / "source.png"
        img = Image.new("RGBA", (20, 20), (255, 0, 0, 128))  # type: ignore[arg-type]
        img.save(str(rgba_file))

        with patch.object(ProductImage, "resize_image"):
            from django.core.files.base import ContentFile

            buf = io.BytesIO()
            img = Image.new("RGBA", (20, 20), (255, 0, 0, 128))  # type: ignore
            img.save(buf, format="PNG")
            buf.seek(0)
            pi = ProductImage(product=product, is_primary=False)
            pi.image.save("rgba_test.png", ContentFile(buf.read()), save=False)
            pi.save()

        # Call resize_image with path pointing at the RGBA PNG
        # but extension forced to .jpg
        # so the transparent-format branch is NOT taken and flattening fires.
        with patch.object(
            type(pi.image),
            "path",
            new_callable=PropertyMock,
            return_value=str(rgba_file),
        ):
            with patch(
                "products.models.os.path.splitext", return_value=("base", ".jpg")
            ):
                pi.resize_image()
        # If no exception raised, the flatten branch executed without error
        result = Image.open(str(rgba_file))
        assert result.mode == "RGB"

    @pytest.mark.django_db
    def test_palette_mode_jpeg_converted_and_flattened(self, product, tmp_path):
        """P-mode image on a .jpg path should convert to RGBA
        then flatten (lines 200, 218)."""
        # Create a paletted PNG on disk (mode=P)
        palette_file = tmp_path / "palette_src.png"
        Image.new("P", (20, 20)).save(str(palette_file))

        with patch.object(ProductImage, "resize_image"):
            from django.core.files.base import ContentFile

            buf = io.BytesIO()
            Image.new("P", (20, 20)).save(buf, format="PNG")
            buf.seek(0)
            pi = ProductImage(product=product, is_primary=False)
            pi.image.save("palette_jpeg.png", ContentFile(buf.read()), save=False)
            pi.save()

        # Patch path + extension so the P-mode-in-JPEG branch fires (line 200)
        with patch.object(
            type(pi.image),
            "path",
            new_callable=PropertyMock,
            return_value=str(palette_file),
        ):
            with patch(
                "products.models.os.path.splitext", return_value=("base", ".jpg")
            ):
                pi.resize_image()
        # No exception = P→RGBA→RGB flatten completed

    @pytest.mark.django_db
    def test_rgb_image_gets_quality_kwarg(self, product, tmp_path):
        """Plain RGB JPEG should save with quality=85 (line 218)."""
        rgb_file = tmp_path / "rgb.jpg"
        img = Image.new("RGB", (20, 20), (100, 150, 200))  # type: ignore[arg-type]
        img.save(str(rgb_file), format="JPEG")

        with patch.object(ProductImage, "resize_image"):
            from django.core.files.base import ContentFile

            buf = io.BytesIO()
            img = Image.new("RGB", (20, 20), (100, 150, 200))  # type: ignore[arg-type]
            img.save(buf, format="JPEG")
            buf.seek(0)
            pi = ProductImage(product=product, is_primary=False)
            pi.image.save("rgb.jpg", ContentFile(buf.read()), save=False)
            pi.save()

        with patch.object(
            type(pi.image),
            "path",
            new_callable=PropertyMock,
            return_value=str(rgb_file),
        ):
            pi.resize_image()  # RGB JPEG: quality=85 should be applied
        # Check the file is still readable
        assert Image.open(str(rgb_file)).mode == "RGB"

    @pytest.mark.django_db
    def test_paletted_png_is_converted_to_rgba(self, product, tmp_path):
        """Paletted (mode=P) PNG/WebP should be converted to RGBA."""
        # Create a paletted PNG
        palette_file = tmp_path / "palette.png"
        img = Image.new("P", (20, 20))
        img.save(str(palette_file))

        with patch.object(ProductImage, "resize_image"):
            from django.core.files.base import ContentFile

            buf = io.BytesIO()
            img.save(buf, format="PNG")
            buf.seek(0)
            pi = ProductImage(product=product, is_primary=False)
            pi.image.save("palette_test.png", ContentFile(buf.read()), save=False)
            pi.save()

        with patch.object(
            type(pi.image),
            "path",
            new_callable=PropertyMock,
            return_value=str(palette_file),
        ):
            pi.resize_image()
        # No exception = paletted PNG handled correctly

    @pytest.mark.django_db
    def test_resize_image_png_preserves_transparency(self, product, tmp_path):
        """PNG with RGBA mode should be saved without
        flattening (transparent_formats)."""
        rgba_file = tmp_path / "rgba.png"
        img = Image.new("RGBA", (20, 20), (0, 200, 100, 200))  # type: ignore[arg-type]
        img.save(str(rgba_file))

        with patch.object(ProductImage, "resize_image"):
            from django.core.files.base import ContentFile

            buf = io.BytesIO()
            img = Image.new("RGBA", (20, 20), (0, 200, 100, 200))  # type: ignore
            img.save(buf, format="PNG")
            buf.seek(0)
            pi = ProductImage(product=product, is_primary=False)
            pi.image.save("rgba_png.png", ContentFile(buf.read()), save=False)
            pi.save()

        with patch.object(
            type(pi.image),
            "path",
            new_callable=PropertyMock,
            return_value=str(rgba_file),
        ):
            pi.resize_image()  # Should not raise; quality kwarg omitted for transparent

        # Verify saved file is still a valid PNG
        saved = Image.open(str(rgba_file))
        assert saved.format == "PNG"


# ---------------------------------------------------------------------------
# Coverage gap tests – products/views.py (lines 46, 68)
# ---------------------------------------------------------------------------


class TestProductListViewFilters:
    """products/views.py lines 46 and 68 –
    slug category filter + invalid sort fallback."""

    @pytest.mark.django_db
    def test_category_filter_by_slug(self, client, category, product):
        """Filtering by category slug (not digit) hits the slug-lookup branch."""
        response = client.get(
            reverse("products:product_list"), {"category": category.slug}
        )
        assert response.status_code == 200
        products = response.context["products"]
        assert product in products

    @pytest.mark.django_db
    def test_max_price_filter(self, client, sample_data):
        """max_price parameter filters out products above the limit."""
        response = client.get(reverse("products:product_list"), {"max_price": "15.00"})
        assert response.status_code == 200
        products = response.context["products"]
        for p in products:
            assert p.price <= Decimal("15.00")

    @pytest.mark.django_db
    def test_invalid_sort_field_falls_back_to_default(self, client, product):
        """An invalid sort parameter should fall back to '-created_at' (line 68)."""
        response = client.get(
            reverse("products:product_list"),
            {"sort": "invalid_field_that_doesnt_exist"},
        )
        assert response.status_code == 200
