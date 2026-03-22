"""App configuration for the core app."""

from django.apps import AppConfig


class CoreConfig(AppConfig):
    name = "core"
    default_auto_field = "django.db.models.AutoField"
    verbose_name = "Core"
