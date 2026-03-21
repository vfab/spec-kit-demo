"""Data models for the accounts app (UserProfile)."""

from django.contrib.auth.models import User
from django.db import models
from django.db.models.signals import post_save
from django.dispatch import receiver

from core.validators import phone_regex


class UserProfile(models.Model):
    """
    Extended user profile with additional information
    """

    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="profile")
    phone_number = models.CharField(
        max_length=20, blank=True, null=True, validators=[phone_regex]
    )
    date_of_birth = models.DateField(blank=True, null=True)

    # Address information
    address_line_1 = models.CharField(max_length=255, blank=True, null=True)
    address_line_2 = models.CharField(max_length=255, blank=True, null=True)
    city = models.CharField(max_length=100, blank=True, null=True)
    state_province = models.CharField(max_length=100, blank=True, null=True)
    postal_code = models.CharField(max_length=20, blank=True, null=True)
    country = models.CharField(max_length=100, blank=True, null=True)

    # Profile settings
    newsletter_subscription = models.BooleanField(default=False)
    email_notifications = models.BooleanField(default=True)

    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "User Profile"
        verbose_name_plural = "User Profiles"
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.user.username}'s Profile"

    @property
    def full_name(self):
        return f"{self.user.first_name} {self.user.last_name}".strip()

    @property
    def full_address(self):
        """Return formatted full address"""
        parts = [
            self.address_line_1,
            self.address_line_2,
            self.city,
            self.state_province,
            self.postal_code,
            self.country,
        ]
        return ", ".join([part for part in parts if part])


@receiver(post_save, sender=User)
def create_user_profile(sender, instance, created, **kwargs):
    """
    Automatically create a UserProfile when a User is created
    """
    if created:
        UserProfile.objects.create(user=instance)


@receiver(post_save, sender=User)
def save_user_profile(sender, instance, created, **kwargs):
    """
    Save the UserProfile when the User is saved.
    Guard: only runs for updates (not creates, which are handled by create_user_profile)
    and only when the profile already exists, preventing a redundant UPDATE on every
    User.save() call (M4).
    """
    if not created and hasattr(instance, "profile"):
        instance.profile.save()
