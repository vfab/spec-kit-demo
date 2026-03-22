# Research: Product Catalog System (Epic 2)

**Branch**: `002-product-catalog-system`
**Date**: 2026-03-22
**Status**: Complete — all unknowns resolved from codebase analysis + Django best practices

---

## 1. Existing Codebase State (Delta Analysis)

### Already Complete from Epic 1

| Component | File | Status |
|-----------|------|--------|
| Category model | `products/models.py` | ✅ Complete |
| Product model | `products/models.py` | ✅ Complete |
| ProductImage model | `products/models.py` | ✅ Complete |
| ProductVariant model | `products/models.py` | ✅ Complete |
| ProductReview model | `products/models.py` | ✅ Complete (with `is_approved`, `unique_together`) |
| All migrations | `products/migrations/0001–0004` | ✅ Complete |
| HomeView | `products/views.py` | ✅ Complete with cache |
| ProductListView | `products/views.py` | ✅ Complete with search, filter, sort, pagination |
| ProductDetailView | `products/views.py` | ✅ Complete with dual-key cache, related products |
| CategoryView | `products/views.py` | ✅ Complete |
| ProductSearchView | `products/views.py` | ✅ Complete |
| URL routing | `products/urls.py` | ✅ All 5 routes defined |
| CategoryAdmin | `products/admin.py` | ✅ Complete |
| ProductAdmin | `products/admin.py` | ✅ Complete with ImageInline, VariantInline |
| Cache invalidation signals | `products/models.py` | ✅ Complete |
| home.html | `templates/products/` | ✅ Template exists |
| product_detail.html | `templates/products/` | ✅ Template exists |
| product_list.html | `templates/products/` | ✅ Template exists |

### Missing — Must Be Built in Epic 2

| Component | File | Spec FRs |
|-----------|------|----------|
| category.html template | `templates/products/category.html` | FR-003, FR-004 |
| search_results.html template | `templates/products/search_results.html` | FR-013–FR-017 |
| Search autocomplete view | `products/views.py` + new URL | FR-018 |
| Review submission view + form | `products/views.py`, `products/forms.py` | FR-024–FR-029 |
| ProductReviewAdmin | `products/admin.py` | FR-035 |
| `stock_status` property | `products/models.py` | FR-036–FR-038 |
| Recently viewed tracking | `products/views.py` session logic + template | FR-040 |
| Product comparison | new views + URLs + session + template | FR-042–FR-045 |
| AJAX filter JS | `static/js/filters.js` | FR-022 |
| Autocomplete JS | `static/js/autocomplete.js` | FR-018 |
| Comparison widget JS | `static/js/comparison.js` | FR-042–FR-045 |
| Test coverage for all above | `tests/test_products.py` | Constitution §II |

---

## 2. Technical Decisions

### Decision 1: Review Submission View Approach
- **Decision**: Class-based `LoginRequiredMixin` + `FormView` at `POST /products/<slug>/review/`
- **Rationale**: Consistent with existing CBV patterns in the codebase. `LoginRequiredMixin` redirects unauthenticated users cleanly (satisfies FR-029). Single POST endpoint prevents duplicate submission via `get_or_create` guard.
- **Alternatives considered**: Function-based view — rejected to maintain CBV consistency across the codebase.

### Decision 2: Search Autocomplete
- **Decision**: Django JSON view at `/products/autocomplete/?q=` returning `{"results": [{"name": ..., "url": ...}]}`, called client-side after 2+ characters.
- **Rationale**: Aligns with FR-018 (2-character threshold). Pure Django JSON — no additional package needed.
- **Alternatives considered**: django-autocomplete-light — rejected, adds a dependency for trivial functionality.

### Decision 3: AJAX Filter Updates
- **Decision**: Fetch API calls to the existing `ProductListView` with `?format=partial` query param. The view returns a minimal HTML fragment (`products/_product_grid.html`) when `format=partial` is detected.
- **Rationale**: Avoids a separate API endpoint; reuses the ORM filter chain already in `ProductListView.get_queryset()`. The partial template approach keeps the server rendering cycle intact and avoids CSP complexity with `innerHTML`.
- **Alternatives considered**: DRF API endpoint for products — over-engineered for this phase. htmx — not currently in the stack.

### Decision 4: Recently Viewed Tracking
- **Decision**: Store a list of product PKs in `request.session["recently_viewed"]` (max 8), updated in `ProductDetailView.get_context_data()`.
- **Rationale**: Stateless, requires no DB writes, privacy-safe (session cleared on browser close by default). Consistent with spec assumption: "session-scoped, not persisted to account".
- **Alternatives considered**: DB model `RecentlyViewed` — over-engineered; spec explicitly states session scope only.

### Decision 5: Product Comparison
- **Decision**: Store compared product PKs in `request.session["comparison"]` (max 3). Three new views: `ComparisonAddView`, `ComparisonRemoveView`, `ComparisonView`. Category enforcement: validate category FK on add.
- **Rationale**: Sessions are already used for cart state (from Epic 1); same pattern. Enforcing same-category at add time (not display time) gives immediate user feedback per FR-044.
- **Alternatives considered**: Cookie-based storage — session is already the correct abstraction here; cookies add complexity.

### Decision 6: Stock Status Property
- **Decision**: Add `stock_status` property to `Product` and `ProductVariant` returning `"in_stock"`, `"low_stock"`, or `"out_of_stock"`. Threshold from `settings.LOW_STOCK_THRESHOLD` (default: 5).
- **Rationale**: Centralises threshold logic in one place; templates can use `{{ product.stock_status }}` without conditional logic. Setting is configurable without a code change (FR-037).
- **Alternatives considered**: Inline template logic — poor separation of concerns and violates DRY.

### Decision 7: Review Moderation Admin
- **Decision**: Register `ProductReviewAdmin` in `products/admin.py` with `list_display`, `list_filter`, and a `bulk_approve` admin action.
- **Rationale**: Leverages Django's built-in admin action system; no custom view needed. Satisfies FR-035 (approve/reject) within existing admin interface.
- **Alternatives considered**: Custom moderation UI — out of scope for Epic 2; Django admin is sufficient.

---

## 3. Performance Decisions

### Decision 8: Autocomplete Query Optimisation
- **Decision**: `Product.objects.filter(name__icontains=q, is_active=True).only("name", "slug")[:10]`
- **Rationale**: `only()` avoids fetching the full product record (description, images etc.) for a 10-item list. Response target: <100ms.

### Decision 9: Recently Viewed Batch Fetch
- **Decision**: `Product.objects.filter(pk__in=recently_viewed_pks).only("name", "slug", "price")` — prefetch images separately.
- **Rationale**: A single queryset for all 8 recently viewed products. Using `only()` keeps the result set lightweight.

---

## 4. Testing Strategy

All new views require:
- Happy-path test (authenticated + unauthenticated where relevant)
- Edge-case tests: empty state, duplicate review, out-of-stock, invalid input
- Security tests: CSRF on POST views, login redirect for authenticated-only views

Constitution §II mandates 100% pass rate, §III mandates ≥95% coverage.
All tests go in `tests/test_products.py` per constitution project structure.

---

## 5. File Inventory — What Will Change

```
products/
  models.py          ADD: stock_status property (Product + ProductVariant)
  views.py           ADD: ReviewSubmitView, AutocompleteView, ComparisonAddView,
                         ComparisonRemoveView, ComparisonView
                     MODIFY: ProductDetailView.get_context_data (recently viewed)
  forms.py           NEW: ReviewSubmissionForm
  admin.py           ADD: ProductReviewAdmin with bulk_approve action
  urls.py            ADD: review, autocomplete, compare/* routes

templates/products/
  product_list.html  EXTEND: AJAX filter JS, active filter pills, recently viewed
  product_detail.html EXTEND: review form, review list, recently viewed shelf
  category.html      NEW: category header + product grid (reuse product_list logic)
  search_results.html NEW: query display, result count, product grid
  _product_card.html NEW: extracted partial (shared across listing, search, category)
  _product_grid.html NEW: partial for AJAX filter response
  compare.html       NEW: comparison table with attribute matrix
  _compare_widget.html NEW: floating comparison bar widget

static/
  js/filters.js      NEW: Fetch-based AJAX filter + sort without page reload
  js/autocomplete.js NEW: input event listener, dropdown render, keyboard nav
  js/comparison.js   NEW: add/remove comparison, widget update, session sync

tests/
  test_products.py   EXTEND: tests for all new views, forms, model properties
```
