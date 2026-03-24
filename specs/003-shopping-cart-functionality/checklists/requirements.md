# Checklist: Shopping Cart Requirements

## Functional Requirements

- [x] Anonymous users can add products to cart without logging in
- [x] Authenticated users' carts persist in the database
- [x] Cart items display with product name, price, quantity, subtotal
- [x] Users can update item quantities in the cart
- [x] Users can remove items from the cart
- [x] Cart displays order total (sum of all item subtotals)
- [x] Cart count badge in navbar shows number of cart items
- [x] Stock validation prevents adding out-of-stock items
- [x] Stock validation returns helpful error messages
- [x] Anonymous cart merges into user cart on login
- [x] Checkout requires authentication (redirects to login)
- [x] Checkout creates an Order with correct OrderItems
- [x] Stock is decremented when order is placed

## Security Requirements

- [x] Cart item ownership validated before update/remove (no IDOR)
- [x] Open-redirect protection on stock error referer redirect
- [x] Checkout requires login (LoginRequiredMixin)
- [x] CSRF protection on all cart mutation endpoints

## Technical Requirements

- [x] AJAX support (X-Requested-With: XMLHttpRequest) for add-to-cart
- [x] Session cart keyed by session_key for anonymous users
- [x] Database cart keyed by user FK for authenticated users
- [x] Cart context processor registered in TEMPLATES settings 
- [x] Signals registered in orders/apps.py ready()
- [x] All tests pass (test_orders.py)
