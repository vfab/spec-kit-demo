"""Django admin configuration for the orders app."""

from django.contrib import admin

from .models import Cart, CartItem, Order, OrderItem


class CartItemInline(admin.TabularInline):
    model = CartItem
    extra = 0
    fields = ("product", "variant", "quantity", "unit_price", "total_price")
    readonly_fields = ("unit_price", "total_price", "created_at")


@admin.register(Cart)
class CartAdmin(admin.ModelAdmin):
    list_display = ("__str__", "user", "total_items", "total_price", "updated_at")
    list_filter = ("created_at", "updated_at")
    search_fields = ("user__username", "user__email", "session_key")
    readonly_fields = ("created_at", "updated_at", "total_items", "total_price")
    inlines = [CartItemInline]

    def get_queryset(self, request):
        return (
            super()
            .get_queryset(request)
            .select_related("user")
            .prefetch_related("items")
        )


@admin.register(CartItem)
class CartItemAdmin(admin.ModelAdmin):
    list_display = (
        "cart",
        "product",
        "variant",
        "quantity",
        "unit_price",
        "total_price",
        "created_at",
    )
    list_filter = ("created_at", "updated_at")
    search_fields = ("cart__user__username", "product__name")
    readonly_fields = ("unit_price", "total_price", "created_at", "updated_at")

    def get_queryset(self, request):
        return (
            super()
            .get_queryset(request)
            .select_related("cart__user", "product", "variant")
        )


class OrderItemInline(admin.TabularInline):
    model = OrderItem
    extra = 0
    fields = (
        "product_name",
        "variant_name",
        "variant_value",
        "quantity",
        "unit_price",
        "total_price",
    )
    readonly_fields = (
        "product_name",
        "variant_name",
        "variant_value",
        "unit_price",
        "total_price",
        "created_at",
    )


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = (
        "order_number",
        "full_name",
        "email",
        "status",
        "payment_status",
        "total_amount",
        "created_at",
    )
    list_filter = ("status", "payment_status", "created_at", "updated_at")
    search_fields = (
        "order_number",
        "email",
        "first_name",
        "last_name",
        "user__username",
    )
    readonly_fields = (
        "order_number",
        "created_at",
        "updated_at",
        "full_name",
        "billing_address",
        "shipping_address",
    )
    inlines = [OrderItemInline]
    date_hierarchy = "created_at"

    fieldsets = (
        (
            "Order Information",
            {"fields": ("order_number", "user", "status", "payment_status")},
        ),
        (
            "Customer Information",
            {"fields": (("first_name", "last_name"), ("email", "phone_number"))},
        ),
        (
            "Billing Address",
            {
                "fields": (
                    ("billing_address_line_1", "billing_address_line_2"),
                    ("billing_city", "billing_state_province"),
                    ("billing_postal_code", "billing_country"),
                )
            },
        ),
        (
            "Shipping Address",
            {
                "fields": (
                    "shipping_same_as_billing",
                    ("shipping_address_line_1", "shipping_address_line_2"),
                    ("shipping_city", "shipping_state_province"),
                    ("shipping_postal_code", "shipping_country"),
                )
            },
        ),
        (
            "Order Totals",
            {
                "fields": (
                    ("subtotal", "tax_amount"),
                    ("shipping_cost", "discount_amount"),
                    ("total_amount",),
                )
            },
        ),
        (
            "Notes",
            {"fields": ("order_notes", "internal_notes"), "classes": ("collapse",)},
        ),
        (
            "Important Dates",
            {
                "fields": ("created_at", "updated_at", "shipped_at", "delivered_at"),
                "classes": ("collapse",),
            },
        ),
    )

    def get_queryset(self, request):
        return super().get_queryset(request).select_related("user")

    @admin.display(description="Customer Name")
    def full_name(self, obj):
        return obj.full_name

    def save_model(self, request, obj, form, change):
        # Auto-set shipped_at when status changes to shipped
        if change and "status" in form.changed_data:
            if obj.status == "shipped" and not obj.shipped_at:
                from django.utils import timezone

                obj.shipped_at = timezone.now()
            elif obj.status == "delivered" and not obj.delivered_at:
                from django.utils import timezone

                obj.delivered_at = timezone.now()
        super().save_model(request, obj, form, change)


@admin.register(OrderItem)
class OrderItemAdmin(admin.ModelAdmin):
    list_display = (
        "order",
        "product_name",
        "variant_info",
        "quantity",
        "unit_price",
        "total_price",
    )
    list_filter = ("created_at",)
    search_fields = ("order__order_number", "product_name", "product__name")
    readonly_fields = ("total_price", "created_at")

    @admin.display(description="Variant")
    def variant_info(self, obj):
        if obj.variant_name and obj.variant_value:
            return f"{obj.variant_name}: {obj.variant_value}"
        return "-"

    def get_queryset(self, request):
        return super().get_queryset(request).select_related("order", "product")
