"""Custom template context processors for the ecommerce_site project."""

from orders.models import Cart
from products.models import Category


def global_context(request):
    """Global context processor for common template variables"""
    context = {
        "categories": Category.objects.filter(parent=None, is_active=True)[:6],
    }

    # Normalise the comparison session dict so the compare widget always has
    # an 'items' list.  Sessions created before the items key was added would
    # otherwise cause the template to iterate dict.items() (the method) and
    # produce broken output.  We fix them in place once here so the template
    # always receives a well-formed structure.
    comparison = request.session.get("comparison")
    if isinstance(comparison, dict) and "items" not in comparison:
        comparison["items"] = []
        request.session.modified = True
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
