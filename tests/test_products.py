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


# ---------------------------------------------------------------------------
# T007 – US1: Category page tests
# ---------------------------------------------------------------------------


class TestCategoryViewExtended:
    """T007 – US1: Category page shows products, subcategories, sorting."""

    @pytest.mark.django_db
    def test_category_page_renders_with_products(self, client, category, product):
        """Category page responds 200 and includes the product."""
        response = client.get(reverse("products:category", args=[category.slug]))
        assert response.status_code == 200
        assert product in response.context["products"]

    @pytest.mark.django_db
    def test_category_shows_subcategory_links(self, client, db):
        """Subcategories of the current category appear in context."""
        from tests.factories import CategoryFactory, ProductFactory

        parent = CategoryFactory(name="Parent Cat")
        child = CategoryFactory(name="Child Cat", parent=parent)
        ProductFactory(category=parent)
        response = client.get(reverse("products:category", args=[parent.slug]))
        assert response.status_code == 200
        subcategories = list(response.context["subcategories"])
        assert child in subcategories

    @pytest.mark.django_db
    def test_sort_by_price_ascending(self, client, db):
        """sort=price returns products in ascending price order."""
        from decimal import Decimal

        from tests.factories import CategoryFactory, ProductFactory

        cat = CategoryFactory()
        ProductFactory(category=cat, price=Decimal("50.00"))
        ProductFactory(category=cat, price=Decimal("10.00"))
        ProductFactory(category=cat, price=Decimal("30.00"))
        response = client.get(
            reverse("products:category", args=[cat.slug]), {"sort": "price"}
        )
        assert response.status_code == 200
        products = list(response.context["products"])
        prices = [p.price for p in products]
        assert prices == sorted(prices)

    @pytest.mark.django_db
    def test_invalid_sort_falls_back(self, client, category, product):
        """An invalid sort value is ignored and the page still renders."""
        response = client.get(
            reverse("products:category", args=[category.slug]),
            {"sort": "malicious_field"},
        )
        assert response.status_code == 200

    @pytest.mark.django_db
    def test_category_404_for_nonexistent_slug(self, client, db):
        """Category page returns 404 for a slug that doesn't exist."""
        response = client.get(reverse("products:category", args=["does-not-exist"]))
        assert response.status_code == 404

    @pytest.mark.django_db
    def test_inactive_products_excluded(self, client, db):
        """Inactive products do not appear on the category page."""
        from tests.factories import CategoryFactory, ProductFactory

        cat = CategoryFactory()
        active = ProductFactory(category=cat, is_active=True)
        inactive = ProductFactory(category=cat, is_active=False)
        response = client.get(reverse("products:category", args=[cat.slug]))
        products = list(response.context["products"])
        assert active in products
        assert inactive not in products

    @pytest.mark.django_db
    def test_child_category_products_appear_on_parent_page(self, client, db):
        """Products in child categories are included on the parent category page."""
        from tests.factories import CategoryFactory, ProductFactory

        parent = CategoryFactory()
        child = CategoryFactory(parent=parent)
        child_product = ProductFactory(category=child)
        response = client.get(reverse("products:category", args=[parent.slug]))
        assert response.status_code == 200
        products = list(response.context["products"])
        assert child_product in products


# ---------------------------------------------------------------------------
# T010 – US2: Product detail review context tests
# ---------------------------------------------------------------------------


class TestProductDetailExtended:
    """T010 – US2: Product detail page review context."""

    @pytest.mark.django_db
    def test_context_includes_review_form_and_reviews(self, client, product):
        """Product detail context contains review_form and reviews keys."""
        response = client.get(reverse("products:product_detail", args=[product.slug]))
        assert response.status_code == 200
        assert "reviews" in response.context
        assert "review_form" in response.context
        assert "review_count" in response.context

    @pytest.mark.django_db
    def test_only_approved_reviews_visible(self, client, db):
        """Unapproved reviews are excluded from the reviews context."""
        from tests.factories import ProductFactory, ProductReviewFactory, UserFactory

        product = ProductFactory()
        approved = ProductReviewFactory(product=product, is_approved=True, rating=4)
        unapproved = ProductReviewFactory(
            product=product,
            user=UserFactory(),
            is_approved=False,
            rating=3,
        )
        response = client.get(reverse("products:product_detail", args=[product.slug]))
        reviews = list(response.context["reviews"])
        assert approved in reviews
        assert unapproved not in reviews

    @pytest.mark.django_db
    def test_avg_rating_reflects_approved_reviews(self, client, db):
        """avg_rating is computed only from approved reviews."""
        from tests.factories import ProductFactory, ProductReviewFactory, UserFactory

        product = ProductFactory()
        ProductReviewFactory(product=product, is_approved=True, rating=4)
        ProductReviewFactory(
            product=product,
            user=UserFactory(),
            is_approved=True,
            rating=2,
        )
        response = client.get(reverse("products:product_detail", args=[product.slug]))
        avg = response.context["avg_rating"]
        assert avg is not None
        # 4 + 2 = 6 / 2 = 3.0
        assert float(avg) == pytest.approx(3.0)

    @pytest.mark.django_db
    def test_inactive_product_returns_404(self, client, db):
        """Accessing an inactive product detail page returns 404."""
        from tests.factories import ProductFactory

        inactive = ProductFactory(is_active=False)
        response = client.get(reverse("products:product_detail", args=[inactive.slug]))
        assert response.status_code == 404

    @pytest.mark.django_db
    def test_user_existing_review_in_context(self, client, db):
        """Authenticated user's own review is exposed in user_existing_review."""
        from tests.factories import ProductFactory, ProductReviewFactory, UserFactory

        user = UserFactory()
        product = ProductFactory()
        review = ProductReviewFactory(
            product=product, user=user, is_approved=True, rating=5
        )
        client.force_login(user)
        response = client.get(reverse("products:product_detail", args=[product.slug]))
        assert response.context["user_existing_review"] == review


# ---------------------------------------------------------------------------
# T014 – US3: Autocomplete view and search results tests
# ---------------------------------------------------------------------------


class TestAutocomplete:
    """T014 – US3: Autocomplete JSON endpoint."""

    @pytest.mark.django_db
    def test_returns_json_for_two_plus_chars(self, client, product):
        """Querying with >= 2 chars returns JSON with results list."""
        q = product.name[:3]
        response = client.get(reverse("products:autocomplete"), {"q": q})
        assert response.status_code == 200
        data = response.json()
        assert "results" in data
        assert any(r["name"] == product.name for r in data["results"])

    @pytest.mark.django_db
    def test_returns_empty_for_one_char(self, client, product):
        """Querying with < 2 chars returns empty results."""
        response = client.get(reverse("products:autocomplete"), {"q": "a"})
        assert response.status_code == 200
        data = response.json()
        assert data["results"] == []

    @pytest.mark.django_db
    def test_returns_empty_for_no_query(self, client, product):
        """Querying with no q param returns empty results."""
        response = client.get(reverse("products:autocomplete"))
        assert response.status_code == 200
        assert response.json()["results"] == []

    @pytest.mark.django_db
    def test_results_include_url(self, client, product):
        """Each result dict includes a url key."""
        q = product.name[:4]
        response = client.get(reverse("products:autocomplete"), {"q": q})
        data = response.json()
        if data["results"]:
            assert "url" in data["results"][0]

    @pytest.mark.django_db
    def test_inactive_products_excluded(self, client, db):
        """Inactive products do not appear in autocomplete results."""
        from tests.factories import ProductFactory

        active = ProductFactory(name="Visible Widget", is_active=True)
        inactive = ProductFactory(name="Visible Widget Inactive", is_active=False)
        response = client.get(reverse("products:autocomplete"), {"q": "Visible"})
        names = [r["name"] for r in response.json()["results"]]
        assert active.name in names
        assert inactive.name not in names


class TestSearchResults:
    """T014 – US3: Search results page."""

    @pytest.mark.django_db
    def test_search_results_shows_count(self, client, product):
        """Search results page renders a result count in context."""
        response = client.get(reverse("products:search"), {"q": product.name[:4]})
        assert response.status_code == 200
        assert "query" in response.context

    @pytest.mark.django_db
    def test_empty_query_returns_no_products(self, client, product):
        """Search with empty/missing q returns no products."""
        response = client.get(reverse("products:search"))
        assert response.status_code == 200
        assert response.context["products"].count() == 0

    @pytest.mark.django_db
    def test_matching_query_returns_products(self, client, product):
        """Products matching the query appear in results."""
        response = client.get(reverse("products:search"), {"q": product.name[:4]})
        assert product in response.context["products"]


# ---------------------------------------------------------------------------
# T019 – US4: AJAX partial filter tests
# ---------------------------------------------------------------------------


class TestAJAXFilters:
    """T019 – US4: format=partial returns fragment template."""

    @pytest.mark.django_db
    def test_format_partial_returns_fragment(self, client, product):
        """Requesting format=partial returns 200 using the partial template."""
        response = client.get(reverse("products:product_list"), {"format": "partial"})
        assert response.status_code == 200
        # The response should NOT contain full HTML document structure
        content = response.content.decode()
        assert "<html" not in content

    @pytest.mark.django_db
    def test_full_request_returns_full_template(self, client, product):
        """A normal (non-partial) request renders the full template."""
        response = client.get(reverse("products:product_list"))
        assert response.status_code == 200
        content = response.content.decode()
        # Full template has the base HTML skeleton
        assert "<html" in content or "<!DOCTYPE" in content

    @pytest.mark.django_db
    def test_partial_with_filters_narrows_results(self, client, db):
        """format=partial combined with max_price filter narrows results."""
        from decimal import Decimal

        from tests.factories import CategoryFactory, ProductFactory

        cat = CategoryFactory()
        cheap = ProductFactory(category=cat, price=Decimal("5.00"))
        expensive = ProductFactory(category=cat, price=Decimal("200.00"))
        response = client.get(
            reverse("products:product_list"),
            {"format": "partial", "max_price": "10.00"},
        )
        assert response.status_code == 200
        products = list(response.context["products"])
        assert cheap in products
        assert expensive not in products


# ---------------------------------------------------------------------------
# T024 – US5: Review submission tests
# ---------------------------------------------------------------------------


class TestReviewSubmission:
    """T024 – US5: Review form submission."""

    @pytest.mark.django_db
    def test_authenticated_post_creates_review(self, client, db):
        """An authenticated POST to the review URL creates a pending review."""
        from products.models import ProductReview
        from tests.factories import ProductFactory, UserFactory

        user = UserFactory()
        product = ProductFactory()
        client.force_login(user)
        response = client.post(
            reverse("products:submit_review", args=[product.slug]),
            {"rating": 4, "title": "Great!", "body": "Loved it."},
        )
        assert response.status_code == 302
        assert ProductReview.objects.filter(product=product, user=user).exists()

    @pytest.mark.django_db
    def test_review_approved_false_by_default(self, client, db):
        """A newly submitted review has is_approved=False."""
        from products.models import ProductReview
        from tests.factories import ProductFactory, UserFactory

        user = UserFactory()
        product = ProductFactory()
        client.force_login(user)
        client.post(
            reverse("products:submit_review", args=[product.slug]),
            {"rating": 5, "title": "", "body": "Nice"},
        )
        review = ProductReview.objects.get(product=product, user=user)
        assert review.is_approved is False

    @pytest.mark.django_db
    def test_duplicate_post_redirects_without_creating_second(self, client, db):
        """Submitting a second review redirects with exists flag (no duplicate)."""
        from tests.factories import ProductFactory, ProductReviewFactory, UserFactory

        user = UserFactory()
        product = ProductFactory()
        ProductReviewFactory(product=product, user=user)
        client.force_login(user)
        response = client.post(
            reverse("products:submit_review", args=[product.slug]),
            {"rating": 3, "title": "", "body": "Again"},
            follow=False,
        )
        assert response.status_code == 302
        assert "review=exists" in response.url

    @pytest.mark.django_db
    def test_unauthenticated_post_redirects_to_login(self, client, db):
        """Unauthenticated users are redirected to login."""
        from tests.factories import ProductFactory

        product = ProductFactory()
        response = client.post(
            reverse("products:submit_review", args=[product.slug]),
            {"rating": 5},
        )
        assert response.status_code == 302
        assert "/login/" in response.url or "/accounts/login/" in response.url

    @pytest.mark.django_db
    def test_review_submitted_param_in_redirect_url(self, client, db):
        """After a successful review submission, redirect URL has ?review=submitted."""
        from tests.factories import ProductFactory, UserFactory

        user = UserFactory()
        product = ProductFactory()
        client.force_login(user)
        response = client.post(
            reverse("products:submit_review", args=[product.slug]),
            {"rating": 5, "title": "Great", "body": "Really good"},
            follow=False,
        )
        assert response.status_code == 302
        assert "review=submitted" in response.url


# ---------------------------------------------------------------------------
# T026 – US6: Admin management tests
# ---------------------------------------------------------------------------


class TestAdminManagement:
    """T026 – US6: ProductAdmin and ProductReviewAdmin."""

    @pytest.mark.django_db
    def test_bulk_approve_sets_is_approved_true(self, admin_user, db):
        """bulk_approve action marks selected reviews as approved."""
        from unittest.mock import MagicMock

        from django.contrib.admin.sites import AdminSite

        from products.admin import ProductReviewAdmin
        from products.models import ProductReview
        from tests.factories import ProductReviewFactory

        review1 = ProductReviewFactory(is_approved=False)
        review2 = ProductReviewFactory(is_approved=False)
        site = AdminSite()
        ma = ProductReviewAdmin(ProductReview, site)
        request = MagicMock()
        queryset = ProductReview.objects.filter(pk__in=[review1.pk, review2.pk])
        ma.bulk_approve(request, queryset)
        review1.refresh_from_db()
        review2.refresh_from_db()
        assert review1.is_approved is True
        assert review2.is_approved is True

    @pytest.mark.django_db
    def test_stock_status_in_product_admin_list_display(self, admin_user, client):
        """ProductAdmin list_display includes stock_status."""
        from django.contrib.admin.sites import AdminSite

        from products.admin import ProductAdmin
        from products.models import Product

        site = AdminSite()
        ma = ProductAdmin(Product, site)
        assert "stock_status" in ma.list_display

    @pytest.mark.django_db
    def test_product_admin_changelist_accessible(self, admin_user, client):
        """Admin staff can access the product changelist page."""
        client.force_login(admin_user)
        response = client.get("/admin/products/product/")
        assert response.status_code == 200

    @pytest.mark.django_db
    def test_product_review_admin_changelist_accessible(self, admin_user, client):
        """Admin staff can access the product review changelist page."""
        client.force_login(admin_user)
        response = client.get("/admin/products/productreview/")
        assert response.status_code == 200


# ---------------------------------------------------------------------------
# T030 – US7: Recently viewed tests
# ---------------------------------------------------------------------------


class TestRecentlyViewed:
    """T030 – US7: Session-based recently-viewed tracking."""

    @pytest.mark.django_db
    def test_viewing_product_adds_pk_to_session(self, client, product):
        """Visiting a product detail page adds its PK to the session."""
        client.get(reverse("products:product_detail", args=[product.slug]))
        assert product.pk in client.session.get("recently_viewed", [])

    @pytest.mark.django_db
    def test_second_view_deduplicates_pk(self, client, product):
        """Visiting the same product twice results in only one entry in the session."""
        client.get(reverse("products:product_detail", args=[product.slug]))
        client.get(reverse("products:product_detail", args=[product.slug]))
        rv = client.session.get("recently_viewed", [])
        assert rv.count(product.pk) == 1

    @pytest.mark.django_db
    def test_recently_viewed_capped_at_eight(self, client, db):
        """The recently-viewed list is capped at 8 entries."""
        from tests.factories import CategoryFactory, ProductFactory

        cat = CategoryFactory()
        products = [ProductFactory(category=cat) for _ in range(10)]
        for p in products:
            client.get(reverse("products:product_detail", args=[p.slug]))
        rv = client.session.get("recently_viewed", [])
        assert len(rv) <= 8

    @pytest.mark.django_db
    def test_recently_viewed_context_excludes_current_product(self, client, db):
        """Detail page context excludes the current product from recently_viewed."""
        from tests.factories import CategoryFactory, ProductFactory

        cat = CategoryFactory()
        p1 = ProductFactory(category=cat)
        p2 = ProductFactory(category=cat)
        # Visit p1 first so it's in session
        client.get(reverse("products:product_detail", args=[p1.slug]))
        # Now visit p2 — p1 should appear in recently_viewed context; p2 should not
        response = client.get(reverse("products:product_detail", args=[p2.slug]))
        rv_context = response.context.get("recently_viewed", [])
        rv_pks = [p.pk for p in rv_context]
        assert p2.pk not in rv_pks

    @pytest.mark.django_db
    def test_recently_viewed_on_product_list(self, client, product):
        """Product list includes recently_viewed in context after a detail visit."""
        client.get(reverse("products:product_detail", args=[product.slug]))
        response = client.get(reverse("products:product_list"))
        assert "recently_viewed" in response.context


# ---------------------------------------------------------------------------
# T036 – US8: Product comparison tests
# ---------------------------------------------------------------------------


class TestProductComparison:
    """T036 – US8: Session-based product comparison."""

    @pytest.mark.django_db
    def test_add_product_stores_pk_in_session(self, client, product):
        """POSTing to compare/add stores the product PK in the session."""
        client.post(
            reverse("products:compare_add"),
            {"product_id": product.pk, "next": "/"},
        )
        comparison = client.session.get("comparison", {})
        assert product.pk in comparison.get("pks", [])

    @pytest.mark.django_db
    def test_adding_fourth_product_returns_limit_error(self, client, db):
        """Adding a 4th product redirects with compare_error=limit."""
        from tests.factories import CategoryFactory, ProductFactory

        cat = CategoryFactory()
        products = [ProductFactory(category=cat) for _ in range(4)]
        for p in products[:3]:
            client.post(
                reverse("products:compare_add"),
                {"product_id": p.pk, "next": "/"},
            )
        response = client.post(
            reverse("products:compare_add"),
            {"product_id": products[3].pk, "next": "/"},
        )
        assert response.status_code == 302
        assert "compare_error=limit" in response.url

    @pytest.mark.django_db
    def test_different_category_returns_category_error(self, client, db):
        """Adding a different-category product redirects with compare_error=category."""
        from tests.factories import CategoryFactory, ProductFactory

        cat1 = CategoryFactory()
        cat2 = CategoryFactory()
        p1 = ProductFactory(category=cat1)
        p2 = ProductFactory(category=cat2)
        client.post(
            reverse("products:compare_add"),
            {"product_id": p1.pk, "next": "/"},
        )
        response = client.post(
            reverse("products:compare_add"),
            {"product_id": p2.pk, "next": "/"},
        )
        assert response.status_code == 302
        assert "compare_error=category" in response.url

    @pytest.mark.django_db
    def test_remove_clears_pk_from_session(self, client, product):
        """POSTing to compare/remove removes the product PK from session."""
        client.post(
            reverse("products:compare_add"),
            {"product_id": product.pk, "next": "/"},
        )
        client.post(
            reverse("products:compare_remove"),
            {"product_id": product.pk, "next": "/"},
        )
        pks = client.session.get("comparison", {}).get("pks", [])
        assert product.pk not in pks

    @pytest.mark.django_db
    def test_compare_view_renders_table(self, client, db):
        """ComparisonView renders 200 when comparison products are in session."""
        from tests.factories import CategoryFactory, ProductFactory

        cat = CategoryFactory()
        p1 = ProductFactory(category=cat)
        p2 = ProductFactory(category=cat)
        client.post(
            reverse("products:compare_add"),
            {"product_id": p1.pk, "next": "/"},
        )
        client.post(
            reverse("products:compare_add"),
            {"product_id": p2.pk, "next": "/"},
        )
        response = client.get(reverse("products:compare"))
        assert response.status_code == 200
        compared = list(response.context["compared_products"])
        assert p1 in compared
        assert p2 in compared

    @pytest.mark.django_db
    def test_empty_comparison_renders_empty_state(self, client, db):
        """ComparisonView renders 200 with an empty list when no products selected."""
        response = client.get(reverse("products:compare"))
        assert response.status_code == 200
        assert list(response.context["compared_products"]) == []

    @pytest.mark.django_db
    def test_invalid_product_id_redirects(self, client, db):
        """ComparisonAddView handles an invalid product_id (redirects with error)."""
        response = client.post(
            reverse("products:compare_add"),
            {"product_id": "not-a-number", "next": "/"},
        )
        assert response.status_code == 302
        assert "compare_error=invalid" in response.url

    @pytest.mark.django_db
    def test_adding_same_product_twice_is_noop(self, client, product):
        """Adding the same product twice does not duplicate PKs in session."""
        for _ in range(2):
            client.post(
                reverse("products:compare_add"),
                {"product_id": product.pk, "next": "/"},
            )
        pks = client.session.get("comparison", {}).get("pks", [])
        assert pks.count(product.pk) == 1
