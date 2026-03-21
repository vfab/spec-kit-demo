"""
Django forms for user authentication and profile management
"""

from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User

from .models import UserProfile, phone_regex


class UserRegistrationForm(UserCreationForm):
    """
    Extended user registration form with additional fields
    """

    email = forms.EmailField(
        required=True,
        widget=forms.EmailInput(
            attrs={"class": "form-control", "placeholder": "Enter your email"}
        ),
    )
    first_name = forms.CharField(
        max_length=30,
        required=True,
        widget=forms.TextInput(
            attrs={"class": "form-control", "placeholder": "First Name"}
        ),
    )
    last_name = forms.CharField(
        max_length=30,
        required=True,
        widget=forms.TextInput(
            attrs={"class": "form-control", "placeholder": "Last Name"}
        ),
    )

    class Meta:
        model = User
        fields = (
            "username",
            "first_name",
            "last_name",
            "email",
            "password1",
            "password2",
        )
        widgets = {
            "username": forms.TextInput(
                attrs={"class": "form-control", "placeholder": "Choose a username"}
            ),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["password1"].widget.attrs.update(
            {"class": "form-control", "placeholder": "Create a password"}
        )
        self.fields["password2"].widget.attrs.update(
            {"class": "form-control", "placeholder": "Confirm password"}
        )

    def save(self, commit=True):
        user = super().save(commit=False)
        user.email = self.cleaned_data["email"]
        user.first_name = self.cleaned_data["first_name"]
        user.last_name = self.cleaned_data["last_name"]

        if commit:
            user.save()
            # Profile is created by the post-save signal (create_user_profile).

        return user


class UserProfileForm(forms.Form):
    """
    Form for updating user profile information
    """

    first_name = forms.CharField(
        max_length=30,
        required=True,
        widget=forms.TextInput(
            attrs={"class": "form-control", "placeholder": "First Name"}
        ),
    )
    last_name = forms.CharField(
        max_length=30,
        required=True,
        widget=forms.TextInput(
            attrs={"class": "form-control", "placeholder": "Last Name"}
        ),
    )
    email = forms.EmailField(
        required=True,
        widget=forms.EmailInput(
            attrs={"class": "form-control", "placeholder": "Email Address"}
        ),
    )
    phone_number = forms.CharField(
        max_length=20,
        required=False,
        validators=[phone_regex],
        widget=forms.TextInput(
            attrs={"class": "form-control", "placeholder": "Phone Number"}
        ),
    )
    address_line_1 = forms.CharField(
        max_length=200,
        required=False,
        widget=forms.TextInput(
            attrs={"class": "form-control", "placeholder": "Street Address"}
        ),
    )
    city = forms.CharField(
        max_length=100,
        required=False,
        widget=forms.TextInput(attrs={"class": "form-control", "placeholder": "City"}),
    )
    postal_code = forms.CharField(
        max_length=20,
        required=False,
        widget=forms.TextInput(
            attrs={"class": "form-control", "placeholder": "Postal Code"}
        ),
    )
    address_line_2 = forms.CharField(
        max_length=200,
        required=False,
        widget=forms.TextInput(
            attrs={"class": "form-control", "placeholder": "Apartment, suite, etc."}
        ),
    )
    state_province = forms.CharField(
        max_length=100,
        required=False,
        widget=forms.TextInput(
            attrs={"class": "form-control", "placeholder": "State / Province"}
        ),
    )
    country = forms.CharField(
        max_length=100,
        required=False,
        widget=forms.TextInput(
            attrs={"class": "form-control", "placeholder": "Country"}
        ),
    )
    date_of_birth = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={"class": "form-control", "type": "date"}),
    )
    newsletter_subscription = forms.BooleanField(
        required=False, widget=forms.CheckboxInput(attrs={"class": "form-check-input"})
    )
    email_notifications = forms.BooleanField(
        required=False, widget=forms.CheckboxInput(attrs={"class": "form-check-input"})
    )

    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop("user", None)
        super().__init__(*args, **kwargs)

        if self.user:
            # Pre-populate form with current user data
            self.fields["first_name"].initial = self.user.first_name
            self.fields["last_name"].initial = self.user.last_name
            self.fields["email"].initial = self.user.email

            # Pre-populate profile data if exists
            if hasattr(self.user, "profile"):
                profile = self.user.profile
                self.fields["phone_number"].initial = profile.phone_number
                self.fields["address_line_1"].initial = profile.address_line_1
                self.fields["address_line_2"].initial = profile.address_line_2
                self.fields["city"].initial = profile.city
                self.fields["state_province"].initial = profile.state_province
                self.fields["postal_code"].initial = profile.postal_code
                self.fields["country"].initial = profile.country
                self.fields["date_of_birth"].initial = profile.date_of_birth
                self.fields["newsletter_subscription"].initial = (
                    profile.newsletter_subscription
                )
                self.fields["email_notifications"].initial = profile.email_notifications

    def save(self, commit=True):
        if not self.user:
            raise ValueError("User must be provided to save profile")

        # Update user fields
        self.user.first_name = self.cleaned_data["first_name"]
        self.user.last_name = self.cleaned_data["last_name"]
        self.user.email = self.cleaned_data["email"]

        if commit:
            self.user.save()

            # Update or create profile
            profile, created = UserProfile.objects.get_or_create(user=self.user)
            profile.phone_number = self.cleaned_data.get("phone_number", "")
            profile.address_line_1 = self.cleaned_data.get("address_line_1", "")
            profile.address_line_2 = self.cleaned_data.get("address_line_2", "")
            profile.city = self.cleaned_data.get("city", "")
            profile.state_province = self.cleaned_data.get("state_province", "")
            profile.postal_code = self.cleaned_data.get("postal_code", "")
            profile.country = self.cleaned_data.get("country", "")
            profile.date_of_birth = self.cleaned_data.get("date_of_birth")
            profile.newsletter_subscription = self.cleaned_data.get(
                "newsletter_subscription", False
            )
            profile.email_notifications = self.cleaned_data.get(
                "email_notifications", False
            )
            profile.save()

        return self.user
