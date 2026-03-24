# Plan: Shopping Cart Functionality

## Tech Stack
- **Framework:** Django 5.0.2
- **Language:** Python 3.12
- **Database:** SQLite (dev) / PostgreSQL (prod)
- **Frontend:** Bootstrap 5, vanilla JS (AJAX with Fetch API)

## Architecture

### Cart Storage
- **Anonymous users:** `Cart` model keyed by `session_key` (Django session)
- **Authenticated users:** `Cart` model keyed by `user` FK
- **Migration:** On login, anonymous session cart items merge into user cart
  (handled via Django `user_logged_in` signal in `orders/signals.py`)

### File Structure

```
orders/
  models.py          — Cart, CartItem, Order, OrderItem
  views.py           — CartView, AddToCartView, RemoveFromCartView,
                       UpdateCartView, CheckoutView, order views
  signals.py         — merge_cart_on_login (user_logged_in receiver)
  forms.py           — CheckoutForm
  urls.py            — cart/*, checkout/*, orders/* routes
  apps.py            — registers signals in ready()

ecommerce_site/
  context_processors/
    __init__.py      — global_context: injects cart_items_count + current_cart

static/js/
  main.js            — updateCartCount() for navbar badge

templates/orders/
  cart.html          — full cart management page
  checkout.html      — checkout form
  order_confirmation.html
  order_detail.html
  order_list.html

tests/
  test_orders.py     — cart model, cart views, checkout, order flow tests
```

## Key Design Decisions

1. **Signal-based cart migration** avoids circular imports between `accounts` and
   `orders` apps. The `user_logged_in` signal fires after login; the receiver in
   `orders/signals.py` merges session cart items into the user cart.

2. **Ownership validation** on all cart mutation views (remove/update) checks
   `cart.user == request.user` for authenticated users or
   `cart.session_key == request.session.session_key` for anonymous users.

3. **Open-redirect protection** in `AddToCartView._check_stock()` uses
   `url_has_allowed_host_and_scheme` to validate the Referer header before
   redirecting back (CWE-601).

4. **AJAX support** — all cart mutation endpoints return JSON when
   `X-Requested-With: XMLHttpRequest` is present in the request headers.

## Data Model
See `../001-database-models-infrastructure/data-model.md` for Cart and CartItem
field definitions.
