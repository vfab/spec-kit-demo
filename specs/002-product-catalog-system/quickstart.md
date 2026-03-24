# Quickstart: Product Catalog System (Epic 2)

**Branch**: `002-product-catalog-system`
**Date**: 2026-03-22
**Audience**: Developers implementing Epic 2 tasks

---

## Prerequisites

Epic 1 must be complete and merged:
- All product models exist and are migrated (`products/migrations/0001–0004`)
- Test suite at ≥95% coverage with 100% pass rate
- All pre-commit gates passing

---

## Integration Scenarios

### Scenario 1: Browse Products with Filtering

**Entry point**: `GET /products/`

The `ProductListView` already handles search (`q`), category, price range, and sort. To verify the AJAX filter path, you need two additional pieces:

1. The `format=partial` parameter check in `get_template_names()` or the view's `render_to_response()` — returns `_product_grid.html` instead of the full page.
2. The `static/js/filters.js` script on the listing page — intercepts form submit events and fires `fetch('/products/?format=partial&...')`, then replaces the product grid DOM node with the response.

**Test Path**:
```python
# In tests/test_products.py
response = client.get("/products/?min_price=10&max_price=50&format=partial")
assert response.status_code == 200
assert "product_grid" in response.content.decode()  # partial template marker
```

---

### Scenario 2: View Product Detail with Reviews

**Entry point**: `GET /products/<slug>/`

The `ProductDetailView.get_context_data()` must be extended to include:

1. `reviews` — approved reviews for the product: `product.reviews.filter(is_approved=True)`
2. `review_form` — an empty `ReviewSubmissionForm` instance (or the user's pre-filled form on validation error)
3. `user_existing_review` — `ProductReview.objects.filter(product=product, user=request.user).first()` or `None` for anonymous users
4. `recently_viewed` — list of `Product` objects from `request.session.get("recently_viewed", [])`

The session update logic (add current product to recently_viewed list, rotate to max 8) also runs in `get_context_data()`.

**Test Path**:
```python
# Authenticated user with approved review exists
user = UserFactory()
product = ProductFactory(is_active=True)
review = ProductReview.objects.create(product=product, user=user, rating=5, is_approved=True)
client.force_login(user)
response = client.get(f"/products/{product.slug}/")
assert response.status_code == 200
assert b"5" in response.content  # rating visible
assert b"Submit Review" not in response.content  # form hidden for user who reviewed
```

---

### Scenario 3: Submit a Review

**Entry point**: `POST /products/<slug>/review/`

1. User must be authenticated (`LoginRequiredMixin`)
2. `ReviewSubmitView.post()` calls `form.save(commit=False)`, sets `review.product` and `review.user`, then `review.save()` (with `is_approved=False` default)
3. On success: `HttpResponseRedirect(reverse("products:product_detail", kwargs={"slug": slug}) + "?review=submitted")`
4. On duplicate: query `ProductReview.objects.filter(product=product, user=request.user).exists()` before saving; if True, silently redirect with `?review=exists`

**Test Path**:
```python
user = UserFactory()
product = ProductFactory(is_active=True)
client.force_login(user)
response = client.post(f"/products/{product.slug}/review/", {"rating": 4, "body": "Great!"})
assert response.status_code == 302
assert ProductReview.objects.filter(product=product, user=user, is_approved=False).exists()
```

---

### Scenario 4: Search Autocomplete

**Entry point**: `GET /products/autocomplete/?q=blu`

Returns JSON. Called by `static/js/autocomplete.js` on `input` events with `q.length >= 2`.

**Test Path**:
```python
ProductFactory(name="Blue Widget", is_active=True)
ProductFactory(name="Red Gadget", is_active=True)
response = client.get("/products/autocomplete/?q=blue")
data = response.json()
assert len(data["results"]) == 1
assert data["results"][0]["name"] == "Blue Widget"
```

---

### Scenario 5: Product Comparison Flow

**Entry point**: `POST /products/compare/add/` → `GET /products/compare/`

**Add flow**:
1. Session key `comparison` initialised to `{"pks": [], "category_id": None}` on first add
2. On add: validate product exists and is active, check category matches session `category_id` (or set it on first add), check `len(pks) < 3`
3. Add product pk to `comparison["pks"]`

**View flow** (`GET /products/compare/`):
1. Fetch `Product.objects.filter(pk__in=session["comparison"]["pks"])` — in a single query
2. Build attribute matrix: `{attr_name: {product_pk: value}}` from variant names/values
3. Pass to `compare.html` template

**Test Path**:
```python
product_a = ProductFactory(is_active=True, category=cat)
product_b = ProductFactory(is_active=True, category=cat)
# Add first product
response = client.post("/products/compare/add/", {"product_id": product_a.pk})
assert response.status_code == 302
# Add second product
response = client.post("/products/compare/add/", {"product_id": product_b.pk})
assert response.status_code == 302
# View comparison
response = client.get("/products/compare/")
assert response.status_code == 200
assert product_a.name.encode() in response.content
assert product_b.name.encode() in response.content
```

---

### Scenario 6: Recently Viewed Products

**Flow**: Every `ProductDetailView` request:
1. Read `recently_viewed = request.session.get("recently_viewed", [])`
2. Insert current `product.pk` at index 0
3. Remove duplicates (if product was previously viewed), keep insert-order
4. Trim to max 8
5. Write back: `request.session["recently_viewed"] = recently_viewed`
6. Query: `Product.objects.filter(pk__in=recently_viewed).only("name", "slug", "price")` — displayed as shelf on page

**Test Path**:
```python
products = ProductFactory.create_batch(3, is_active=True)
session = client.session
session["recently_viewed"] = [products[0].pk, products[1].pk]
session.save()
response = client.get(f"/products/{products[2].slug}/")
assert response.status_code == 200
# products[2] should now be at the front of recently_viewed in session
assert client.session["recently_viewed"][0] == products[2].pk
```

---

## Development Sequence (Recommended)

1. **Add model properties** — `stock_status` on Product and ProductVariant (no migration; pure Python)
2. **Add ProductReviewAdmin** — get moderation working in admin first
3. **Add `products/forms.py`** — `ReviewSubmissionForm`
4. **Add `ReviewSubmitView`** — with `LoginRequiredMixin`, duplicate guard, redirect on success
5. **Extend `ProductDetailView.get_context_data()`** — add reviews, review_form, recently_viewed
6. **Add `AutocompleteView`** — returns JSON
7. **Add comparison views** — `ComparisonAddView`, `ComparisonRemoveView`, `ComparisonView`
8. **Update `products/urls.py`** — register all new routes (before slug route)
9. **Write/extend templates** — category.html, search_results.html, extend product_detail.html
10. **Add JS files** — filters.js, autocomplete.js, comparison.js
11. **Extend test suite** — cover all new views and properties

---

## Key Settings

```python
# ecommerce_site/settings.py additions for Epic 2

# Inventory thresholds
LOW_STOCK_THRESHOLD = 5  # units; products at or below this show "Low Stock"
```

---

## Common Pitfalls

1. **URL ordering**: `compare/*` and `autocomplete` routes MUST appear before `products/<slug>/` in `urlpatterns` — otherwise Django's slug pattern will try to match "compare" and "autocomplete" as product slugs.

2. **Session modification detection**: Django sessions are saved only when `SESSION_SAVE_EVERY_REQUEST = True` or when `request.session.modified = True` is set. After mutating the recently_viewed list, explicitly set `request.session.modified = True`.

3. **Duplicate review guard**: Always check before `form.save()`, not in the form itself — the `unique_together` DB constraint will raise `IntegrityError` without the guard, which would result in a 500 error.

4. **Partial template detection**: `request.GET.get("format") == "partial"` must be checked in the view (override `render_to_response` or `get_template_names`), not in the template.

5. **Autocomplete security**: The query param is passed to `filter(name__icontains=q)` — Django ORM parameterises this so there is no SQL injection risk, but do enforce max query length (100 chars) and minimum length (2 chars) to prevent DoS.
