"""Views for the accounts app — registration, login, logout, and profile."""

from django.contrib import messages
from django.contrib.auth import login
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.models import User
from django.contrib.auth.views import LoginView, LogoutView
from django.shortcuts import redirect
from django.urls import reverse_lazy
from django.views.generic import CreateView, DetailView, UpdateView

from .forms import UserProfileForm, UserRegistrationForm
from .models import UserProfile

# Imported here (not at module top) to avoid a circular import:
# accounts -> orders would create a cycle since orders already imports accounts.
# The lazy import is moved here as a module-level comment to make it explicit.


class RegisterView(CreateView):
    """User registration view"""

    model = User
    form_class = UserRegistrationForm
    template_name = "accounts/register.html"
    success_url = reverse_lazy("products:home")

    def form_valid(self, form):
        response = super().form_valid(form)
        # Log in the user after successful registration.
        # Specify the backend explicitly because multiple AUTHENTICATION_BACKENDS
        # are configured (AxesStandaloneBackend + ModelBackend); Django cannot
        # infer the backend when the user object has no .backend attribute.
        login(
            self.request,
            self.object,
            backend="django.contrib.auth.backends.ModelBackend",
        )
        messages.success(self.request, "Registration successful! Welcome to our store.")
        return response


class CustomLoginView(LoginView):
    """Custom login view"""

    template_name = "accounts/login.html"
    redirect_authenticated_user = True

    def get_success_url(self):
        return reverse_lazy("products:home")

    def form_valid(self, form):
        messages.success(self.request, f"Welcome back, {form.get_user().username}!")
        return super().form_valid(form)


class CustomLogoutView(LogoutView):
    """Custom logout view"""

    next_page = reverse_lazy("products:home")

    def dispatch(self, request, *args, **kwargs):
        messages.info(request, "You have been logged out successfully.")
        return super().dispatch(request, *args, **kwargs)


class ProfileView(LoginRequiredMixin, DetailView):
    """User profile view"""

    model = UserProfile
    template_name = "accounts/profile.html"
    context_object_name = "profile"

    def get_object(self):
        profile, created = UserProfile.objects.get_or_create(user=self.request.user)
        return profile

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # Add user's recent orders
        # (orders.models imported here to avoid accounts <-> orders circular import)
        from orders.models import Order  # noqa: PLC0415

        context["recent_orders"] = (
            Order.objects.filter(user=self.request.user)
            .prefetch_related("items")
            .order_by("-created_at")[:5]
        )
        return context


class ProfileEditView(LoginRequiredMixin, UpdateView):
    """Edit user profile view"""

    model = UserProfile
    form_class = UserProfileForm
    template_name = "accounts/profile_edit.html"
    success_url = reverse_lazy("accounts:profile")

    def get_object(self):
        # R8: Cache the profile on the view instance. This is safe because
        # Django CBVs create a fresh instance per request, so there is no
        # cross-request bleed. It avoids a second DB hit if get_object is
        # called more than once during the request lifecycle.
        if not hasattr(self, "_profile"):
            self._profile, _ = UserProfile.objects.get_or_create(user=self.request.user)
        return self._profile

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        # UserProfileForm is a plain Form (not ModelForm), remove 'instance'
        kwargs.pop("instance", None)
        # Pass user= so the form handles its own pre-population (M4)
        kwargs["user"] = self.request.user
        return kwargs

    def form_valid(self, form):
        form.save()
        messages.success(self.request, "Profile updated successfully!")
        return redirect(self.success_url)
