# Tasks: Shopping Cart Functionality

## Phase 1: Cart Architecture

- [X] **Task 3.1:** Session-based cart for anonymous users
  - `Cart` model with `session_key` field (orders/models.py)
  - `get_or_create_cart(request)` utility function (orders/views.py)
  - Cart persistence via Django session middleware

- [X] **Task 3.2:** Database cart for authenticated users + cart migration
  - `Cart` model with `user` FK (orders/models.py)
  - `CartItem` model with quantity, product, variant (orders/models.py)
  - Cart migration on login via `user_logged_in` signal (orders/signals.py)
  - Signal registered in `orders/apps.py` → `ready()`

- [X] **Task 3.3:** Cart context processor and settings
  - `ecommerce_site/context_processors/__init__.py` — `global_context()`
  - Injects `cart_items_count` and `current_cart` into all templates
  - Registered under `TEMPLATES[0]["OPTIONS"]["context_processors"]`

## Phase 2: Cart Operations

- [X] **Task 3.4:** Add to cart functionality
  - `AddToCartView` (POST /cart/add/<product_id>/) — AJAX + non-AJAX
  - Variant support via `variant_id` POST param
  - Inventory stock check before adding
  - JSON response for AJAX: `{success, message, cart_count}`

- [X] **Task 3.5:** Cart item management
  - `UpdateCartView` (POST /cart/update/<item_id>/) — update quantity or delete
  - `RemoveFromCartView` (POST /cart/remove/<item_id>/) — delete item
  - Ownership validation on both views

- [X] **Task 3.6:** Cart total calculation
  - `Cart.total_price` property — sum of CartItem subtotals
  - `Cart.total_items` property — sum of quantities
  - `CartItem.subtotal` property — price × quantity

## Phase 3: Cart Display and UI

- [X] **Task 3.7:** Cart summary in navbar
  - `cart_items_count` badge in base.html via context processor
  - `updateCartCount()` in main.js updates badge after AJAX operations

- [X] **Task 3.8:** Full cart page (templates/orders/cart.html)
  - Item list with product images, names, quantities
  - Inline update/remove forms
  - Cart total display

- [X] **Task 3.9:** Cart navigation
  - "Continue shopping" link back to product list
  - "Proceed to checkout" button → /checkout/

## Phase 4: Advanced Cart Features

- [X] **Task 3.10:** Cart persistence and recovery
  - Anonymous cart persists across browser sessions (session middleware)
  - Authenticated cart persists in database indefinitely

- [X] **Task 3.11:** Inventory management integration
  - `_check_stock()` in `AddToCartView` validates available stock
  - Respects `track_inventory`, `allow_backorders`, `stock_quantity`
  - Returns 400 JSON for AJAX, redirect + message for non-AJAX

- [X] **Task 3.12:** Checkout integration
  - `CheckoutView` (LoginRequired) — display cart + checkout form
  - `CheckoutForm` with billing/shipping fields
  - Order creation with OrderItem records and stock decrement

## Phase 5: Integration and Testing

- [X] **Task 3.13:** Comprehensive cart tests (tests/test_orders.py)
  - `TestCartModel` — creation, totals, item count
  - `TestCartItemModel` — subtotals, variants, quantity validation
  - `TestCartViews` — authenticated and anonymous cart views
  - `TestCheckoutViews` — checkout flow, empty cart, form validation
  - `TestOrderIntegration` — complete add→checkout→order flow
  - `TestGetOrCreateCartAnonymous` — session key handling
  - `TestRemoveFromCartAnonymousOwnership` — session ownership check
  - `TestAddToCartOverstockAjax` — AJAX 400 on overstock
  - `TestCheckoutViewPostBranches` — POST edge cases
  - `TestCheckoutFormClean` — shipping address validation
