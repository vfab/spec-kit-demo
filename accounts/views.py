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

# Lazy imports from `orders` live inside methods/functions below to avoid the
# accounts ↔ orders circular import (orders.models imports auth.User).


def _merge_anonymous_cart(request, user, old_session_key):
    """Move items from an anonymous session cart into the user's persistent cart.

    Called after login/registration once the session key has been rotated.
    `old_session_key` must be captured *before* Django's login() calls
    cycle_key() — the caller is responsible for this.
    """
    if not old_session_key:
        return

    # Lazy import to avoid accounts ↔ orders circular dependency.
    from django.db import transaction  # noqa: PLC0415

    from orders.models import Cart, CartItem  # noqa: PLC0415

    try:
        session_cart = Cart.objects.get(session_key=old_session_key, user=None)
    except Cart.DoesNotExist:
        return

    session_items = list(session_cart.items.select_related("product", "variant"))
    if not session_items:
        session_cart.delete()
        return

    try:
        with transaction.atomic():
            user_cart, _ = Cart.objects.get_or_create(user=user)
            for item in session_items:
                existing = CartItem.objects.filter(
                    cart=user_cart,
                    product=item.product,
                    variant=item.variant,
                ).first()
                if existing:
                    existing.quantity += item.quantity
                    existing.save(update_fields=["quantity"])
                else:
                    item.cart = user_cart
                    item.save(update_fields=["cart"])
            session_cart.delete()
    except Exception:
        import logging  # noqa: PLC0415

        logging.getLogger(__name__).exception(
            "Failed to merge session cart %s into user cart for user %s",
            old_session_key,
            user.pk,
        )


class RegisterView(CreateView):
    """User registration view"""

    model = User
    form_class = UserRegistrationForm
    template_name = "accounts/register.html"
    success_url = reverse_lazy("products:home")

    def form_valid(self, form):
        response = super().form_valid(form)
        # Capture the session key BEFORE login() rotates it via cycle_key().
        old_session_key = self.request.session.session_key
        # Log in the user after successful registration.
        # Specify the backend explicitly because multiple AUTHENTICATION_BACKENDS
        # are configured (AxesStandaloneBackend + ModelBackend); Django cannot
        # infer the backend when the user object has no .backend attribute.
        login(
            self.request,
            self.object,
            backend="django.contrib.auth.backends.ModelBackend",
        )
        _merge_anonymous_cart(self.request, self.object, old_session_key)
        messages.success(self.request, "Registration successful! Welcome to our store.")
        return response


class CustomLoginView(LoginView):
    """Custom login view"""

    template_name = "accounts/login.html"
    redirect_authenticated_user = True

    def get_success_url(self):
        return reverse_lazy("products:home")

    def form_valid(self, form):
        # Capture old session key BEFORE super().form_valid() calls login() →
        # cycle_key(), which rotates the session key.
        old_session_key = self.request.session.session_key
        messages.success(self.request, f"Welcome back, {form.get_user().username}!")
        response = super().form_valid(form)
        _merge_anonymous_cart(self.request, form.get_user(), old_session_key)
        return response


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
