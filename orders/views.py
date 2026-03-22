"""Views for the orders app — cart, checkout, and order history."""

import logging

from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db import transaction
from django.db.models import Count, Prefetch
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect
from django.utils.http import url_has_allowed_host_and_scheme
from django.views.generic import DetailView, ListView, TemplateView, View

from accounts.models import UserProfile
from products.models import Product, ProductVariant

from .forms import CheckoutForm
from .models import Cart, CartItem, Order, OrderItem

logger = logging.getLogger(__name__)


def get_or_create_cart(request):
    """Return (or lazily create) the cart for the current request (L3).

    Authenticated users: cart is keyed by user.
    Anonymous users: cart is keyed by session.
    """
    if request.user.is_authenticated:
        cart, _ = Cart.objects.get_or_create(user=request.user)
    else:
        session_key = request.session.session_key
        if not session_key:
            request.session.create()
            session_key = request.session.session_key
        cart, _ = Cart.objects.get_or_create(session_key=session_key)
    return cart


class CartView(TemplateView):
    """Shopping cart view"""

    template_name = "orders/cart.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        cart = self.get_or_create_cart()
        context["cart"] = cart
        context["cart_items"] = (
            cart.items.select_related("product", "variant") if cart else []
        )
        return context

    def get_or_create_cart(self):
        return get_or_create_cart(self.request)


class AddToCartView(View):
    """Add product to cart"""

    def _check_stock(self, request, cart, product, variant, quantity):
        """Return an error response if stock is insufficient, else None."""
        if not (product.track_inventory and not product.allow_backorders):
            return None
        stock_source = variant if variant else product
        existing_qty = (
            CartItem.objects.filter(cart=cart, product=product, variant=variant)
            .values_list("quantity", flat=True)
            .first()
            or 0
        )
        if existing_qty + quantity <= stock_source.stock_quantity:
            return None
        available = stock_source.stock_quantity - existing_qty
        error_msg = (
            f"Sorry, only {available} more unit(s) of"
            f" {product.name} can be added "
            f"(you already have {existing_qty} in your cart)."
        )
        if request.headers.get("X-Requested-With") == "XMLHttpRequest":
            return JsonResponse({"success": False, "message": error_msg}, status=400)
        messages.error(request, error_msg)
        # Use the Referer only if it is a same-host URL to prevent open redirects
        # (CWE-601). url_has_allowed_host_and_scheme is Django's canonical helper.
        referer = request.META.get("HTTP_REFERER", "")
        if referer and url_has_allowed_host_and_scheme(
            referer, allowed_hosts={request.get_host()}, require_https=request.is_secure()
        ):
            return redirect(referer)
        return redirect("products:product_list")

    def post(self, request, product_id):
        product = get_object_or_404(Product, id=product_id, is_active=True)
        try:
            quantity = max(1, int(request.POST.get("quantity", 1)))
        except (TypeError, ValueError):
            quantity = 1
        variant_id = request.POST.get("variant_id")

        # Get variant if specified
        variant = None
        if variant_id:
            variant = get_object_or_404(ProductVariant, id=variant_id, product=product)

        # Get or create cart first so we can check existing quantity
        cart = get_or_create_cart(request)

        stock_error = self._check_stock(request, cart, product, variant, quantity)
        if stock_error is not None:
            return stock_error

        # Add or update cart item
        cart_item, created = CartItem.objects.get_or_create(
            cart=cart, product=product, variant=variant, defaults={"quantity": quantity}
        )
        if not created:
            cart_item.quantity += quantity
            cart_item.save()

        messages.success(request, f"{product.name} added to cart!")

        # Return JSON response for AJAX requests
        if request.headers.get("X-Requested-With") == "XMLHttpRequest":
            return JsonResponse(
                {
                    "success": True,
                    "message": f"{product.name} added to cart!",
                    "cart_count": cart.total_items,
                }
            )

        return redirect("orders:cart")


class RemoveFromCartView(View):
    """Remove item from cart (works for both authenticated and anonymous users)"""

    def post(self, request, item_id):
        cart_item = get_object_or_404(CartItem, id=item_id)

        # Verify ownership — authenticated users must own the cart;
        # anonymous users must match via session key.
        if request.user.is_authenticated:
            if cart_item.cart.user != request.user:
                messages.error(request, "Unauthorized action.")
                return redirect("orders:cart")
        else:
            if cart_item.cart.session_key != request.session.session_key:
                messages.error(request, "Unauthorized action.")
                return redirect("orders:cart")

        product_name = cart_item.product.name
        cart_item.delete()
        messages.success(request, f"{product_name} removed from cart.")

        return redirect("orders:cart")


class UpdateCartView(View):
    """Update cart item quantity"""

    def post(self, request, item_id):
        cart_item = get_object_or_404(CartItem, id=item_id)
        try:
            quantity = int(request.POST.get("quantity", 1))
        except (TypeError, ValueError):
            messages.error(request, "Invalid quantity.")
            return redirect("orders:cart")

        # Verify ownership
        if (request.user.is_authenticated and cart_item.cart.user != request.user) or (
            not request.user.is_authenticated
            and cart_item.cart.session_key != request.session.session_key
        ):
            messages.error(request, "Unauthorized action.")
            return redirect("orders:cart")

        if quantity > 0:
            cart_item.quantity = quantity
            cart_item.save()
            messages.success(request, "Cart updated successfully.")
        else:
            # Capture the name before deletion to avoid use-after-delete.
            product_name = cart_item.product.name
            cart_item.delete()
            messages.success(request, f"{product_name} removed from cart.")

        return redirect("orders:cart")


class CheckoutView(LoginRequiredMixin, TemplateView):
    """Checkout process view"""

    template_name = "orders/checkout.html"

    def _get_or_create_cart(self):
        return get_or_create_cart(self.request)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        cart = self._get_or_create_cart()
        context["cart"] = cart
        context["cart_items"] = cart.items.select_related("product", "variant")
        # Provide a form-like dict pre-populated with profile data for the template
        form_initial = {}
        try:
            profile = UserProfile.objects.get(user=self.request.user)
            context["profile"] = profile
            form_initial = {
                "first_name": self.request.user.first_name,
                "last_name": self.request.user.last_name,
                "email": self.request.user.email,
                "billing_address_line_1": getattr(profile, "address_line_1", ""),
                "billing_city": getattr(profile, "city", ""),
                "billing_state_province": getattr(profile, "state_province", ""),
                "billing_postal_code": getattr(profile, "postal_code", ""),
                "billing_country": getattr(profile, "country", ""),
            }
        except UserProfile.DoesNotExist:
            context["profile"] = None
        context["form"] = CheckoutForm(initial=form_initial)
        return context

    def post(self, request, *args, **kwargs):
        """Validate checkout form then create order."""
        cart = self._get_or_create_cart()

        if not cart.items.exists():
            messages.error(request, "Your cart is empty.")
            return redirect("orders:cart")

        form = CheckoutForm(request.POST)
        if not form.is_valid():
            context = self.get_context_data(**kwargs)
            context["form"] = form
            messages.error(request, "Please correct the errors below.")
            return self.render_to_response(context)

        d = form.cleaned_data
        try:
            with transaction.atomic():
                order = Order.objects.create(
                    user=request.user,
                    first_name=d["first_name"],
                    last_name=d["last_name"],
                    email=d["email"],
                    phone_number=d.get("phone_number", ""),
                    billing_address_line_1=d["billing_address_line_1"],
                    billing_address_line_2=d.get("billing_address_line_2", ""),
                    billing_city=d["billing_city"],
                    billing_state_province=d["billing_state_province"],
                    billing_postal_code=d["billing_postal_code"],
                    billing_country=d["billing_country"],
                    shipping_same_as_billing=d.get("shipping_same_as_billing", True),
                    payment_method=d["payment_method"],
                    order_notes=d.get("order_notes", ""),
                )

                if not order.shipping_same_as_billing:
                    order.shipping_address_line_1 = d.get("shipping_address_line_1", "")
                    order.shipping_address_line_2 = d.get("shipping_address_line_2", "")
                    order.shipping_city = d.get("shipping_city", "")
                    order.shipping_state_province = d.get("shipping_state_province", "")
                    order.shipping_postal_code = d.get("shipping_postal_code", "")
                    order.shipping_country = d.get("shipping_country", "")
                    order.save()

                for cart_item in cart.items.select_related("product", "variant").all():
                    OrderItem.objects.create(
                        order=order,
                        product=cart_item.product,
                        quantity=cart_item.quantity,
                        unit_price=cart_item.unit_price,
                        variant=cart_item.variant,
                    )
                    # H2: Decrement stock now that the order is committed.
                    if cart_item.product.track_inventory:
                        if cart_item.variant:
                            cart_item.variant.stock_quantity = max(
                                0, cart_item.variant.stock_quantity - cart_item.quantity
                            )
                            cart_item.variant.save(update_fields=["stock_quantity"])
                        else:
                            cart_item.product.stock_quantity = max(
                                0, cart_item.product.stock_quantity - cart_item.quantity
                            )
                            cart_item.product.save(update_fields=["stock_quantity"])

                # Use the centralised method to compute totals
                # from actual OrderItems (M1)
                order.recalculate_totals()

                cart.items.all().delete()

                messages.success(
                    request, f"Order {order.order_number} placed successfully!"
                )
                return redirect(
                    "orders:order_confirmation", order_number=order.order_number
                )

        except Exception as exc:
            logger.exception("Checkout failed for user %s: %s", request.user, exc)
            messages.error(
                request, "There was an error processing your order. Please try again."
            )
            return self.get(request, *args, **kwargs)


class OrderListView(LoginRequiredMixin, ListView):
    """User's order history"""

    model = Order
    template_name = "orders/order_list.html"
    context_object_name = "orders"
    paginate_by = 10

    def get_queryset(self):
        # Annotate item count (single aggregation query) and prefetch items
        # for the preview rows — avoids N+1 on both count and iteration in
        # the template.
        return (
            Order.objects.filter(user=self.request.user)
            .annotate(items_count=Count("items"))
            .prefetch_related(
                Prefetch(
                    "items",
                    queryset=OrderItem.objects.select_related("product", "variant"),
                )
            )
            .order_by("-created_at")
        )


class OrderDetailView(LoginRequiredMixin, DetailView):
    """Order detail view"""

    model = Order
    template_name = "orders/order_detail.html"
    context_object_name = "order"
    slug_field = "order_number"
    slug_url_kwarg = "order_number"

    def get_queryset(self):
        return Order.objects.filter(user=self.request.user)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["order_items"] = self.object.items.select_related("product", "variant")
        return context


class OrderConfirmationView(LoginRequiredMixin, TemplateView):
    """Order confirmation page"""

    template_name = "orders/order_confirmation.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        order_number = kwargs.get("order_number")
        order = get_object_or_404(
            Order, order_number=order_number, user=self.request.user
        )
        context["order"] = order
        context["order_items"] = order.items.select_related("product", "variant")
        return context
