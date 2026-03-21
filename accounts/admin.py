"""Django admin configuration for the accounts app."""

from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.contrib.auth.models import User

from .models import UserProfile


class UserProfileInline(admin.StackedInline):
    model = UserProfile
    can_delete = False
    verbose_name_plural = "Profile"
    fields = (
        ("phone_number", "date_of_birth"),
        ("address_line_1", "address_line_2"),
        ("city", "state_province"),
        ("postal_code", "country"),
        ("newsletter_subscription", "email_notifications"),
    )


class UserAdmin(BaseUserAdmin):
    inlines = (UserProfileInline,)
    list_display = (
        "username",
        "email",
        "first_name",
        "last_name",
        "is_staff",
        "date_joined",
        "get_phone_number",
    )
    list_filter = (
        "is_staff",
        "is_superuser",
        "is_active",
        "date_joined",
        "profile__newsletter_subscription",
    )
    search_fields = (
        "username",
        "first_name",
        "last_name",
        "email",
        "profile__phone_number",
    )

    @admin.display(description="Phone Number", ordering="profile__phone_number")
    def get_phone_number(self, obj):
        return obj.profile.phone_number if hasattr(obj, "profile") else "-"


@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    list_display = (
        "user",
        "phone_number",
        "city",
        "country",
        "newsletter_subscription",
        "created_at",
    )
    list_filter = (
        "newsletter_subscription",
        "email_notifications",
        "country",
        "created_at",
    )
    search_fields = ("user__username", "user__email", "phone_number", "city")
    readonly_fields = ("created_at", "updated_at")

    fieldsets = (
        ("User Information", {"fields": ("user",)}),
        ("Contact Information", {"fields": ("phone_number", "date_of_birth")}),
        (
            "Address",
            {
                "fields": (
                    ("address_line_1", "address_line_2"),
                    ("city", "state_province"),
                    ("postal_code", "country"),
                )
            },
        ),
        ("Preferences", {"fields": ("newsletter_subscription", "email_notifications")}),
        (
            "Timestamps",
            {"fields": ("created_at", "updated_at"), "classes": ("collapse",)},
        ),
    )


# Re-register UserAdmin
admin.site.unregister(User)
admin.site.register(User, UserAdmin)
