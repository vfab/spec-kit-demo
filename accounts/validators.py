"""Custom password validators for the accounts app (EPIC-10 T3)."""

import re

from django.core.exceptions import ValidationError
from django.utils.translation import gettext as _eager
from django.utils.translation import gettext_lazy as _


class SymbolPasswordValidator:
    """Require at least one non-alphanumeric character.

    This validator supplements Django's built-in validators (minimum length,
    common-password check, numeric-only check) by ensuring the password
    contains at least one symbol such as ``!@#$%^&*()``.
    """

    SYMBOL_RE = re.compile(r"[^A-Za-z0-9]")

    def validate(self, password: str, user=None) -> None:  # type: ignore[override]
        if not self.SYMBOL_RE.search(password):
            raise ValidationError(
                _(
                    "Your password must contain at least one special character "
                    "(e.g. !@#$%%^&*()-_=+)."
                ),
                code="password_no_symbol",
            )

    def get_help_text(self) -> str:
        return _eager(
            "Your password must contain at least one special character "
            "(e.g. !@#$%^&*()-_=+)."
        )
