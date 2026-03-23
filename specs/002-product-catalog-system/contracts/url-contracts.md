# URL Contracts: Product Catalog System (Epic 2)

**Branch**: `002-product-catalog-system`
**Date**: 2026-03-22
**Type**: Django URL routes (public customer-facing + AJAX endpoints)

All routes are under `app_name = "products"` (namespaced as `products:*`).

---

## Public Read Routes (No Auth Required)

### 1. Product List

```
GET /products/
```

**Query Parameters**:
| Param | Type | Default | Description |
|-------|------|---------|-------------|
| `q` or `search` | str | — | Search term (name/description) |
| `category` | str/int | — | Category slug or pk |
| `min_price` | float | — | Minimum price filter |
| `max_price` | float | — | Maximum price filter |
| `sort` | str | `-created_at` | One of: `price`, `-price`, `name`, `-name`, `created_at`, `-created_at` |
| `page` | int | 1 | Page number |
| `format` | str | — | If `partial`: returns `_product_grid.html` fragment only (AJAX) |

**Success Response**: `200 OK` — renders `products/product_list.html`
**AJAX Response** (`format=partial`): `200 OK` — renders `products/_product_grid.html` fragment

---

### 2. Product Detail

```
GET /products/<slug:slug>/
```

**Success Response**: `200 OK` — renders `products/product_detail.html`
**Not Found**: `404` — when product does not exist or `is_active=False`

---

### 3. Category Listing

```
GET /category/<slug:slug>/
```

**Success Response**: `200 OK` — renders `products/category.html`
**Not Found**: `404` — when category does not exist

---

### 4. Product Search

```
GET /search/?q=<query>
```

**Query Parameters**: same sort/filter params as Product List
**Success Response**: `200 OK` — renders `products/search_results.html`
**Empty Query**: returns `products/search_results.html` with empty queryset and no query context

---

### 5. Search Autocomplete *(NEW)*

```
GET /products/autocomplete/?q=<query>
```

**Minimum characters**: 2 (empty or 1-character queries return empty results to avoid expensive scans)

**Success Response**: `200 OK` — JSON
```json
{
  "results": [
    {
      "name": "Blue Widget",
      "url": "/products/blue-widget/"
    }
  ]
}
```
**Max results**: 10
**Requires auth**: No
**Error (q missing/too short)**:
```json
{"results": []}
```

---

## Write Routes (Auth Required)

### 6. Submit Product Review *(NEW)*

```
POST /products/<slug:slug>/review/
```

**Authentication**: Required — `LoginRequiredMixin` redirects to login page if not authenticated
**CSRF**: Required (Django default)

**Request body (form-encoded)**:
| Field | Type | Required | Constraints |
|-------|------|----------|-------------|
| `rating` | int | Yes | 1–5 inclusive |
| `title` | str | No | max 200 chars |
| `body` | str | No | optional text |

**Success Response**: `302 Redirect` → `products:product_detail` with `?review=submitted` query param (for success message display)

**Already Reviewed**: `302 Redirect` → `products:product_detail` (no second review stored)

**Validation Error**: `200 OK` — re-renders product detail page with form errors inline

**Unauthenticated**: `302 Redirect` → `/accounts/login/?next=/products/<slug>/review/`

---

## Comparison Routes (NEW)

### 7. Add to Comparison

```
POST /products/compare/add/
```

**Authentication**: Not required (session-based)
**CSRF**: Required

**Request body (form-encoded)**:
| Field | Type | Required | Notes |
|-------|------|----------|-------|
| `product_id` | int | Yes | Must be a valid active product pk |

**Success Response**: `302 Redirect` → HTTP_REFERER (safe) or `products:product_list`
**Category Mismatch**: `302 Redirect` → referrer with `?compare_error=category` message
**Limit Exceeded (3 products)**: `302 Redirect` → referrer with `?compare_error=limit` message
**Invalid product_id**: `302 Redirect` → referrer with `?compare_error=invalid` message
**Product not found / inactive**: `404 Not Found`

---

### 8. Remove from Comparison

```
POST /products/compare/remove/
```

**Authentication**: Not required
**CSRF**: Required

**Request body (form-encoded)**:
| Field | Type | Required | Notes |
|-------|------|----------|-------|
| `product_id` | int | Yes | Removes from session comparison list |

**Success Response**: `302 Redirect` → HTTP_REFERER or `products:compare`
**Not in comparison**: no-op, `302 Redirect` → referrer

---

### 9. View Comparison Table

```
GET /products/compare/
```

**Authentication**: Not required
**Success Response**: `200 OK` — renders `products/compare.html`
**Empty comparison**: renders `products/compare.html` with empty state message

---

## URL Routing Summary

```python
# products/urls.py — additions for Epic 2
urlpatterns = [
    # ... existing routes ...
    path("products/autocomplete/", views.AutocompleteView.as_view(), name="autocomplete"),
    path("products/<slug:slug>/review/", views.ReviewSubmitView.as_view(), name="submit_review"),
    path("products/compare/", views.ComparisonView.as_view(), name="compare"),
    path("products/compare/add/", views.ComparisonAddView.as_view(), name="compare_add"),
    path("products/compare/remove/", views.ComparisonRemoveView.as_view(), name="compare_remove"),
]
```

**Note**: `compare/*` and `autocomplete` routes must be declared **before** the `products/<slug:slug>/` route to avoid slug-matching conflicts.

---

## Template Contracts (Rendered HTML)

### Context variables guaranteed by each view:

| Template | View | Required Context Keys |
|----------|------|-----------------------|
| `product_list.html` | `ProductListView` | `products` (Page), `categories`, `price_range`, `search`, `sort_by` |
| `product_detail.html` | `ProductDetailView` | `product`, `images`, `variants`, `related_products`, `reviews`, `review_form`, `recently_viewed`, `user_existing_review` |
| `category.html` | `CategoryView` | `products` (Page), `category` |
| `search_results.html` | `ProductSearchView` | `products` (Page), `query`, `result_count` |
| `compare.html` | `ComparisonView` | `comparison_products` (list[Product]), `attributes` (dict) |
| `_product_grid.html` | `ProductListView` (partial) | `products` (Page) |
