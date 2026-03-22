"""Forms for the products app."""

from django import forms
from django.core.validators import MaxValueValidator, MinValueValidator

from .models import ProductReview


class ReviewSubmissionForm(forms.ModelForm):
    """Form for submitting a product review."""

    rating = forms.IntegerField(
        min_value=1,
        max_value=5,
        validators=[MinValueValidator(1), MaxValueValidator(5)],
        widget=forms.NumberInput(attrs={"class": "form-control", "min": 1, "max": 5}),
        help_text="Rate between 1 (worst) and 5 (best).",
    )
    title = forms.CharField(
        max_length=200,
        required=False,
        widget=forms.TextInput(
            attrs={"class": "form-control", "placeholder": "Review title (optional)"}
        ),
    )
    body = forms.CharField(
        required=False,
        widget=forms.Textarea(
            attrs={
                "class": "form-control",
                "rows": 4,
                "placeholder": "Share your thoughts\u2026",
            }
        ),
    )

    class Meta:
        model = ProductReview
        fields = ["rating", "title", "body"]
