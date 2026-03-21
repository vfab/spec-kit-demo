"""Custom template context processors for the ecommerce_site project."""

from orders.models import Cart
from products.models import Category


def global_context(request):
    """Global context processor for common template variables"""
    context = {
        "categories": Category.objects.filter(parent=None, is_active=True)[:6],
    }

    # Add cart information
    cart = None
    cart_items_count = 0

    if request.user.is_authenticated:
        try:
            cart = Cart.objects.get(user=request.user)
            cart_items_count = cart.total_items
        except Cart.DoesNotExist:
            pass
    else:
        session_key = request.session.session_key
        if session_key:
            try:
                cart = Cart.objects.get(session_key=session_key)
                cart_items_count = cart.total_items
            except Cart.DoesNotExist:
                pass

    context["cart_items_count"] = cart_items_count
    context["current_cart"] = cart

    return context
