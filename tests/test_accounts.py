"""
Unit tests for accounts app - user authentication, profiles, and user management
"""

import pytest

from django.contrib.auth import authenticate
from django.contrib.auth.models import User
from django.urls import reverse

from accounts.forms import UserProfileForm, UserRegistrationForm
from accounts.models import UserProfile


class TestUserModel:
    """Test Django User model extensions and functionality"""

    @pytest.mark.django_db
    def test_user_creation(self):
        """Test creating a user"""
        user = User.objects.create_user(
            username="testuser",
            email="test@example.com",
            password="testpass123",
            first_name="Test",
            last_name="User",
        )
        assert user.username == "testuser"
        assert user.email == "test@example.com"
        assert user.check_password("testpass123")
        assert str(user) == "testuser"

    @pytest.mark.django_db
    def test_user_authentication(self):
        """Test user authentication"""
        user = User.objects.create_user(username="authuser", password="authpass123")

        # Test successful authentication
        authenticated_user = authenticate(username="authuser", password="authpass123")
        assert authenticated_user is not None
        assert authenticated_user == user

        # Test failed authentication
        failed_auth = authenticate(username="authuser", password="wrongpass")
        assert failed_auth is None

    @pytest.mark.django_db
    def test_superuser_creation(self):
        """Test creating a superuser"""
        admin = User.objects.create_superuser(
            username="admin", email="admin@example.com", password="adminpass123"
        )
        assert admin.is_staff is True
        assert admin.is_superuser is True


class TestUserProfileModel:
    """Test UserProfile model functionality"""

    @pytest.mark.django_db
    def test_profile_creation(self, user):
        """Test creating a user profile"""
        # Profile should be auto-created by signal, just update it
        profile = getattr(user, "profile")
        profile.phone_number = "123-456-7890"
        profile.address_line_1 = "123 Test Street"
        profile.city = "Test City"
        profile.postal_code = "12345"
        profile.save()

        assert profile.user == user
        assert profile.phone_number == "123-456-7890"
        assert str(profile) == f"{user.username}'s Profile"

    @pytest.mark.django_db
    def test_profile_auto_creation_signal(self):
        """Test that profile is auto-created when user is created"""
        user = User.objects.create_user(
            username="signaluser", email="signal@example.com", password="testpass123"
        )
        # Profile should be auto-created by signal
        assert hasattr(user, "profile")
        try:
            profile = getattr(user, "profile")
            assert isinstance(profile, UserProfile)
        except UserProfile.DoesNotExist:
            pytest.fail("UserProfile was not created by signal")

    @pytest.mark.django_db
    def test_profile_optional_fields(self, user):
        """Test profile with minimal required fields"""
        # Profile already exists from signal, just test it
        profile = getattr(user, "profile")
        assert profile.phone_number in [None, ""]
        assert profile.address_line_1 in [None, ""]
        assert profile.city in [None, ""]
        assert profile.postal_code in [None, ""]


class TestUserRegistrationForm:
    """Test user registration form"""

    @pytest.mark.django_db
    def test_valid_registration_form(self):
        """Test valid registration form data"""
        form_data = {
            "username": "newuser",
            "email": "newuser@example.com",
            "first_name": "New",
            "last_name": "User",
            "password1": "StrongPass1!@",
            "password2": "StrongPass1!@",
        }
        form = UserRegistrationForm(data=form_data)
        assert form.is_valid()

    @pytest.mark.django_db
    def test_password_mismatch(self):
        """Test registration form with mismatched passwords"""
        form_data = {
            "username": "newuser",
            "email": "newuser@example.com",
            "first_name": "New",
            "last_name": "User",
            "password1": "StrongPass1!@",
            "password2": "DifferentP1!@",
        }
        form = UserRegistrationForm(data=form_data)
        assert not form.is_valid()
        assert "password2" in form.errors

    @pytest.mark.django_db
    def test_duplicate_username(self, user):
        """Test registration with duplicate username"""
        form_data = {
            "username": user.username,  # Already exists
            "email": "different@example.com",
            "password1": "StrongPass1!@",
            "password2": "StrongPass1!@",
        }
        form = UserRegistrationForm(data=form_data)
        assert not form.is_valid()
        assert "username" in form.errors

    @pytest.mark.django_db
    def test_invalid_email(self):
        """Test registration with invalid email"""
        form_data = {
            "username": "newuser",
            "email": "invalid-email",
            "password1": "StrongPass1!@",
            "password2": "StrongPass1!@",
        }
        form = UserRegistrationForm(data=form_data)
        assert not form.is_valid()
        assert "email" in form.errors


class TestUserProfileForm:
    """Test user profile form"""

    def test_valid_profile_form(self):
        """Test valid profile form data"""
        form_data = {
            "first_name": "Updated",
            "last_name": "Name",
            "email": "updated@example.com",
            "phone_number": "555-123-4567",
            "address_line_1": "456 Updated Street",
            "city": "Updated City",
            "postal_code": "54321",
        }
        form = UserProfileForm(data=form_data)
        assert form.is_valid()

    def test_partial_profile_form(self):
        """Test profile form with partial data"""
        form_data = {
            "first_name": "Partial",
            "last_name": "Update",
            "email": "partial@example.com",
        }
        form = UserProfileForm(data=form_data)
        assert form.is_valid()


class TestAccountViews:
    """Test account views functionality"""

    @pytest.mark.django_db
    def test_register_view_get(self, client):
        """Test registration page GET request"""
        response = client.get(reverse("accounts:register"))
        assert response.status_code == 200
        assert "form" in response.context
        assert isinstance(response.context["form"], UserRegistrationForm)

    @pytest.mark.django_db
    def test_register_view_post_valid(self, client):
        """Test registration with valid data"""
        form_data = {
            "username": "newuser",
            "email": "newuser@example.com",
            "first_name": "New",
            "last_name": "User",
            "password1": "StrongPass1!@",
            "password2": "StrongPass1!@",
        }
        response = client.post(reverse("accounts:register"), data=form_data)

        # Should redirect after successful registration
        assert response.status_code == 302

        # User should be created
        user = User.objects.get(username="newuser")
        assert user.email == "newuser@example.com"
        assert user.first_name == "New"
        assert user.last_name == "User"

    @pytest.mark.django_db
    def test_register_view_post_invalid(self, client):
        """Test registration with invalid data"""
        form_data = {
            "username": "newuser",
            "email": "invalid-email",
            "password1": "pass",
            "password2": "different",
        }
        response = client.post(reverse("accounts:register"), data=form_data)

        # Should not redirect, stay on form
        assert response.status_code == 200
        assert "form" in response.context
        assert response.context["form"].errors

    @pytest.mark.django_db
    def test_login_view_get(self, client):
        """Test login page GET request"""
        response = client.get(reverse("accounts:login"))
        assert response.status_code == 200

    @pytest.mark.django_db
    def test_login_view_post_valid(self, client):
        """Test login with valid credentials"""
        User.objects.create_user(username="testuser", password="testpass123")
        response = client.post(
            reverse("accounts:login"),
            {"username": "testuser", "password": "testpass123"},
        )
        # Should redirect after successful login
        assert response.status_code == 302

        # Check if user is logged in
        response = client.get(reverse("accounts:profile"))
        assert response.status_code == 200  # Should access profile without redirect

    @pytest.mark.django_db
    def test_login_view_post_invalid(self, client, user):
        """Test login with invalid credentials"""
        response = client.post(
            reverse("accounts:login"),
            {"username": "testuser", "password": "wrongpassword"},
        )
        # Should stay on login page
        assert response.status_code == 200

    @pytest.mark.django_db
    def test_profile_view_authenticated(self, authenticated_client, user):
        """Test profile view for authenticated user"""
        response = authenticated_client.get(reverse("accounts:profile"))
        assert response.status_code == 200
        assert response.context["user"] == user
        assert "profile" in response.context

    @pytest.mark.django_db
    def test_profile_view_anonymous(self, client):
        """Test profile view for anonymous user"""
        response = client.get(reverse("accounts:profile"))
        # Should redirect to login
        assert response.status_code == 302
        assert "/accounts/login/" in response.url

    @pytest.mark.django_db
    def test_profile_edit_view_get(self, authenticated_client, user):
        """Test profile edit page GET request"""
        response = authenticated_client.get(reverse("accounts:profile_edit"))
        assert response.status_code == 200
        assert "form" in response.context
        assert isinstance(response.context["form"], UserProfileForm)

    @pytest.mark.django_db
    def test_profile_edit_view_post_valid(self, authenticated_client, user):
        """Test profile edit with valid data"""
        form_data = {
            "first_name": "Updated",
            "last_name": "Name",
            "email": "updated@example.com",
            "phone_number": "555-999-8888",
            "address_line_1": "789 New Address",
            "city": "New City",
            "postal_code": "98765",
        }
        response = authenticated_client.post(
            reverse("accounts:profile_edit"), data=form_data
        )

        # Should redirect after successful update
        assert response.status_code == 302

        # Check that user was updated
        user.refresh_from_db()
        assert user.first_name == "Updated"
        assert user.last_name == "Name"
        assert user.email == "updated@example.com"

        # Check that profile was updated
        profile = getattr(user, "profile")
        profile.refresh_from_db()
        assert profile.phone_number == "555-999-8888"
        assert profile.address_line_1 == "789 New Address"

    @pytest.mark.django_db
    def test_logout_view(self, authenticated_client):
        """Test logout functionality"""
        response = authenticated_client.post(reverse("accounts:logout"))
        # Should redirect after logout
        assert response.status_code == 302

        # Check that user is logged out
        response = authenticated_client.get(reverse("accounts:profile"))
        assert response.status_code == 302  # Should redirect to login


class TestAccountIntegration:
    """Integration tests for account functionality"""

    @pytest.mark.django_db
    def test_complete_user_registration_flow(self, client):
        """Test complete user registration and login flow"""
        # Step 1: Register new user
        registration_data = {
            "username": "flowuser",
            "email": "flow@example.com",
            "first_name": "Flow",
            "last_name": "User",
            "password1": "FlowPass1!@",
            "password2": "FlowPass1!@",
        }
        response = client.post(reverse("accounts:register"), data=registration_data)
        assert response.status_code == 302

        # Step 2: Verify user was created with profile
        user = User.objects.get(username="flowuser")
        assert user.email == "flow@example.com"
        assert hasattr(user, "profile")

        # Step 3: Login with new user
        login_response = client.post(
            reverse("accounts:login"),
            {"username": "flowuser", "password": "FlowPass1!@"},
        )
        assert login_response.status_code == 302

        # Step 4: Access profile
        profile_response = client.get(reverse("accounts:profile"))
        assert profile_response.status_code == 200
        assert profile_response.context["user"] == user

    @pytest.mark.django_db
    def test_user_profile_update_flow(self, authenticated_client, user):
        """Test complete profile update flow"""
        # Step 1: Get profile edit page
        response = authenticated_client.get(reverse("accounts:profile_edit"))
        assert response.status_code == 200

        # Step 2: Update profile
        update_data = {
            "first_name": "Updated",
            "last_name": "Profile",
            "email": "updated.profile@example.com",
            "phone_number": "555-111-2222",
            "address_line_1": "999 Updated Lane",
            "city": "Updated City",
            "postal_code": "11111",
        }
        response = authenticated_client.post(
            reverse("accounts:profile_edit"), data=update_data
        )
        assert response.status_code == 302

        # Step 3: Verify updates in profile view
        response = authenticated_client.get(reverse("accounts:profile"))
        user.refresh_from_db()
        profile = getattr(user, "profile")
        profile.refresh_from_db()

        assert response.context["user"].first_name == "Updated"
        response_profile = getattr(response.context["user"], "profile")
        assert response_profile.phone_number == "555-111-2222"
