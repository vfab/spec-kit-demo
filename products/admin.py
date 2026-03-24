"""Django admin configuration for the products app."""

from django.conf import settings
from django.contrib import admin
from django.db.models import Q

from .models import Category, Product, ProductImage, ProductReview, ProductVariant


class StockStatusFilter(admin.SimpleListFilter):
    """Filter products by their computed stock_status property."""

    title = "stock status"
    parameter_name = "stock_status"

    def lookups(self, request, model_admin):
        return [
            ("in_stock", "In Stock"),
            ("low_stock", "Low Stock"),
            ("out_of_stock", "Out of Stock"),
        ]

    def queryset(self, request, queryset):
        threshold = getattr(settings, "LOW_STOCK_THRESHOLD", 5)
        if self.value() == "out_of_stock":
            return queryset.filter(
                track_inventory=True,
                stock_quantity__lte=0,
                allow_backorders=False,
            )
        if self.value() == "low_stock":
            return queryset.filter(
                track_inventory=True,
                allow_backorders=False,
                stock_quantity__gt=0,
                stock_quantity__lte=threshold,
            )
        if self.value() == "in_stock":
            return queryset.filter(
                Q(track_inventory=False)
                | Q(allow_backorders=True)
                | Q(
                    track_inventory=True,
                    allow_backorders=False,
                    stock_quantity__gt=threshold,
                )
            )
        return queryset


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ("name", "parent", "is_active", "created_at")
    list_filter = ("is_active", "parent", "created_at")
    search_fields = ("name", "description")
    prepopulated_fields = {"slug": ("name",)}
    readonly_fields = ("created_at", "updated_at")

    fieldsets = (
        (None, {"fields": ("name", "slug", "description", "parent")}),
        ("Media", {"fields": ("image",)}),
        ("Settings", {"fields": ("is_active",)}),
        (
            "Timestamps",
            {"fields": ("created_at", "updated_at"), "classes": ("collapse",)},
        ),
    )


class ProductImageInline(admin.TabularInline):
    model = ProductImage
    extra = 1
    fields = ("image", "alt_text", "is_primary", "sort_order")
    readonly_fields = ("created_at",)


class ProductVariantInline(admin.TabularInline):
    model = ProductVariant
    extra = 0
    fields = (
        "name",
        "value",
        "price_adjustment",
        "sku_suffix",
        "stock_quantity",
        "is_active",
        "sort_order",
    )
    readonly_fields = ("created_at",)


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = (
        "name",
        "category",
        "price",
        "stock_quantity",
        "stock_status",
        "is_active",
        "is_featured",
        "created_at",
    )
    list_filter = (
        "is_active",
        "is_featured",
        "is_digital",
        "category",
        StockStatusFilter,
        "created_at",
    )
    search_fields = ("name", "sku", "description")
    prepopulated_fields = {"slug": ("name",)}
    readonly_fields = ("created_at", "updated_at")
    inlines = [ProductImageInline, ProductVariantInline]

    fieldsets = (
        ("Basic Information", {"fields": ("name", "slug", "category", "sku")}),
        ("Description", {"fields": ("short_description", "description")}),
        ("Pricing", {"fields": (("price", "compare_price", "cost_price"),)}),
        (
            "Inventory",
            {"fields": (("stock_quantity", "track_inventory"), ("allow_backorders",))},
        ),
        (
            "Physical Properties",
            {
                "fields": (
                    ("weight",),
                    ("dimensions_length", "dimensions_width", "dimensions_height"),
                ),
                "classes": ("collapse",),
            },
        ),
        (
            "SEO",
            {"fields": ("meta_title", "meta_description"), "classes": ("collapse",)},
        ),
        ("Status", {"fields": ("is_active", "is_featured", "is_digital")}),
        (
            "Timestamps",
            {"fields": ("created_at", "updated_at"), "classes": ("collapse",)},
        ),
    )

    def get_queryset(self, request):
        return super().get_queryset(request).select_related("category")


@admin.register(ProductImage)
class ProductImageAdmin(admin.ModelAdmin):
    list_display = ("product", "alt_text", "is_primary", "sort_order", "created_at")
    list_filter = ("is_primary", "created_at")
    search_fields = ("product__name", "alt_text")
    readonly_fields = ("created_at",)

    def get_queryset(self, request):
        return super().get_queryset(request).select_related("product")


@admin.register(ProductVariant)
class ProductVariantAdmin(admin.ModelAdmin):
    list_display = (
        "product",
        "name",
        "value",
        "price_adjustment",
        "stock_quantity",
        "is_active",
    )
    list_filter = ("name", "is_active", "created_at")
    search_fields = ("product__name", "name", "value")
    readonly_fields = ("created_at",)

    def get_queryset(self, request):
        return super().get_queryset(request).select_related("product")


@admin.register(ProductReview)
class ProductReviewAdmin(admin.ModelAdmin):
    list_display = ("product", "user", "rating", "is_approved", "created_at")
    list_filter = ("is_approved", "rating", "created_at")
    search_fields = ("title", "body", "user__username", "product__name")
    readonly_fields = ("created_at", "updated_at")
    actions = ["bulk_approve"]

    def get_queryset(self, request):
        return super().get_queryset(request).select_related("product", "user")

    @admin.action(description="Approve selected reviews")
    def bulk_approve(self, request, queryset):
        updated = queryset.update(is_approved=True)
        self.message_user(request, f"{updated} review(s) approved.")
