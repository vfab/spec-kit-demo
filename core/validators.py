"""Shared validators reused across multiple apps (R1: single source of truth)."""

from django.core.validators import RegexValidator

# S5: Shared phone number validator — accepts common international formats.
# Examples: +1-800-555-0199, (555) 123-4567, 555.123.4567, +44 20 7946 0958
phone_regex = RegexValidator(
    regex=r"^\+?[\d\s().\-]{7,20}$",
    message="Enter a valid phone number (7–20 digits, spaces, +, -, (, ) allowed).",
)
