"""
Forms for the orders app.
"""

from django import forms

from core.validators import phone_regex

PAYMENT_METHOD_CHOICES = [
    ("credit_card", "Credit Card"),
    ("debit_card", "Debit Card"),
    ("paypal", "PayPal"),
    ("bank_transfer", "Bank Transfer"),
]


class CheckoutForm(forms.Form):
    """Validates checkout POST data before creating an Order."""

    # Contact
    first_name = forms.CharField(max_length=100)
    last_name = forms.CharField(max_length=100)
    email = forms.EmailField()
    phone_number = forms.CharField(
        max_length=20, required=False, validators=[phone_regex]
    )

    # Billing address (all required by the Order model)
    billing_address_line_1 = forms.CharField(max_length=255)
    billing_address_line_2 = forms.CharField(max_length=255, required=False)
    billing_city = forms.CharField(max_length=100)
    billing_state_province = forms.CharField(max_length=100)
    billing_postal_code = forms.CharField(max_length=20)
    billing_country = forms.CharField(max_length=100)

    # Shipping
    shipping_same_as_billing = forms.BooleanField(required=False)
    shipping_address_line_1 = forms.CharField(max_length=255, required=False)
    shipping_address_line_2 = forms.CharField(max_length=255, required=False)
    shipping_city = forms.CharField(max_length=100, required=False)
    shipping_state_province = forms.CharField(max_length=100, required=False)
    shipping_postal_code = forms.CharField(max_length=20, required=False)
    shipping_country = forms.CharField(max_length=100, required=False)

    # Payment
    payment_method = forms.ChoiceField(choices=PAYMENT_METHOD_CHOICES)
    order_notes = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={"rows": 3}),
    )

    def clean(self):
        cleaned = super().clean()
        # Treat an absent or unchecked checkbox as "same as billing" (True)
        # unless the user explicitly submitted shipping_same_as_billing=False
        # AND also provided a separate shipping address.
        same = (
            cleaned.get("shipping_same_as_billing")
            or "shipping_same_as_billing" not in self.data
        )
        # Write back so downstream code sees the resolved value, not raw False.
        cleaned["shipping_same_as_billing"] = same
        if not same:
            # Shipping address fields are required when not copying billing
            for field in (
                "shipping_address_line_1",
                "shipping_city",
                "shipping_state_province",
                "shipping_postal_code",
                "shipping_country",
            ):
                if not cleaned.get(field):
                    self.add_error(
                        field,
                        "This field is required when shipping"
                        " address differs from billing.",
                    )
        return cleaned
