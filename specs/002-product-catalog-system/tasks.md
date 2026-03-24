# Tasks: Product Catalog System (ShopHub Epic 2)

**Input**: Design documents from `specs/002-product-catalog-system/`
**Branch**: `002-product-catalog-system`
**Date**: 2026-03-22
**Prerequisites**: plan.md ✅, spec.md ✅, research.md ✅, data-model.md ✅, contracts/url-contracts.md ✅, quickstart.md ✅

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies on incomplete tasks in this phase)
- **[Story]**: Which user story this task belongs to (US1–US8)
- Exact file paths included in all descriptions

---

## Phase 1: Setup

**Purpose**: Configuration additions required before any model or view work can begin

- [X] T001 Add `LOW_STOCK_THRESHOLD = 5` to `ecommerce_site/settings.py` (required by all stock_status logic)

**Checkpoint**: Configuration ready — Phase 2 can begin

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Shared components that MUST be complete before any user story phase begins

**⚠️ CRITICAL**: All user story phases depend on this phase being complete

- [X] T002 [P] Add `stock_status` property to `Product` model in `products/models.py` (returns `"in_stock"` / `"low_stock"` / `"out_of_stock"` using `getattr(settings, "LOW_STOCK_THRESHOLD", 5)`)
- [X] T003 [P] Add `stock_status` property to `ProductVariant` model in `products/models.py` (same logic as T002 using variant's own `stock_quantity`)
- [X] T004 [P] Add `ProductReviewAdmin` to `products/admin.py` with `list_display = ["product", "user", "rating", "is_approved", "created_at"]`, `list_filter = ["is_approved", "rating"]`, and `bulk_approve` admin action
- [X] T005 Create `templates/products/_product_card.html` partial (product name, primary image, price, sale price when `is_on_sale`, aggregate rating, stock status badge, compare button)

**Checkpoint**: Shared components ready — all user story phases can begin

---

## Phase 3: User Story 1 — Customer Browses and Discovers Products (Priority: P1) 🎯 MVP

**Goal**: Enable customers to browse paginated product listings, navigate by category, sort results, and see empty-state messages when no products match.

**Independent Test**: Navigate to `/products/` without logging in, browse multiple pages, select a category via `/category/<slug>/`, change the sort order, verify correct products are displayed and pagination controls work.

### Implementation for User Story 1

- [X] T006 [US1] Create `templates/products/category.html` (category name, description, subcategory links, product grid using `_product_card.html`, empty-state message, pagination)

### Tests for User Story 1

- [X] T007 [P] [US1] Write US1 tests in `tests/test_products.py`: category page renders with products and subcategory links; sort by price/name returns correct order; empty category shows empty-state message; pagination returns correct page

**Checkpoint**: User Story 1 complete — customers can browse and discover products independently

---

## Phase 4: User Story 2 — Customer Views a Product Detail Page (Priority: P1)

**Goal**: Product detail page shows complete product information including image gallery, variants with stock status, sale price, breadcrumb nav, and approved customer reviews with aggregate rating.

**Independent Test**: Navigate directly to `/products/<slug>/` without login; verify all product info is displayed, breadcrumb links are navigable, and approved reviews appear with aggregate star rating.

### Implementation for User Story 2

- [X] T008 [US2] Extend `ProductDetailView.get_context_data()` in `products/views.py` to add: `reviews` (approved only), `review_form` (empty `ReviewSubmissionForm` instance), `user_existing_review` (`None` for anonymous users)
- [X] T009 [US2] Update `templates/products/product_detail.html` with: reviews section showing aggregate rating + review count, individual approved review cards (reviewer name, date, rating, body), guest prompt to log in, and placeholder for review form (form rendered but submission via US5)

### Tests for User Story 2

- [X] T010 [P] [US2] Write US2 tests in `tests/test_products.py`: detail page context includes `reviews` and `review_form`; approved reviews visible, unapproved hidden; aggregate rating computed correctly; inactive product returns 404; breadcrumb context available

**Checkpoint**: User Story 2 complete — customers can view full product details and existing reviews independently

---

## Phase 5: User Story 3 — Customer Searches for Products (Priority: P1)

**Goal**: Search results page shows matching products with count, supports the same sort/filter as the listing, shows empty-state for no results, and the search input provides autocomplete suggestions.

**Independent Test**: Type a product name fragment into the search bar; verify results page shows count (e.g., "14 results for 'jacket'"); type a non-existent term and verify empty-state message; type ≥2 characters and verify autocomplete dropdown appears.

### Implementation for User Story 3

- [X] T011 [US3] Create `templates/products/search_results.html` (query display, result count, sort dropdown, product grid using `_product_card.html`, empty-state message with search term, "suggestions to broaden" copy)
- [X] T012 [US3] Add `AutocompleteView` to `products/views.py` (returns `{"results": [{"name": ..., "url": ...}]}`, uses `.only("name", "slug")[:10]`, returns `{"results": []}` for `q` shorter than 2 characters) and add URL `products/autocomplete/` to `products/urls.py` **before** the `<slug:slug>` route
- [X] T013 [P] [US3] Create `static/js/autocomplete.js` (listens to `input` event on search field, fires `fetch("/products/autocomplete/?q=")` after ≥2 chars, renders dropdown, handles keyboard navigation and selection)

### Tests for User Story 3

- [X] T014 [P] [US3] Write US3 tests in `tests/test_products.py`: search results page shows correct count and products; empty query shows empty results; autocomplete returns JSON for ≥2 chars; autocomplete returns `{"results": []}` for 1-char query; URL resolves correctly before slug route

**Checkpoint**: User Story 3 complete — customers can search and get autocomplete suggestions independently

---

## Phase 6: User Story 4 — Customer Filters Products by Multiple Criteria (Priority: P2)

**Goal**: Product listings support multiple simultaneous filters (price range, category), active filters are shown as removable pills, filters update the product grid via AJAX without a full page reload, and "Clear all filters" resets the view.

**Independent Test**: Apply a price range filter then add a category filter; verify the product count updates after each; remove one filter without reloading; clear all filters and confirm the full list returns.

### Implementation for User Story 4

- [X] T015 [US4] Override `render_to_response()` in `ProductListView` in `products/views.py` to detect `request.GET.get("format") == "partial"` and return `templates/products/_product_grid.html` fragment only
- [X] T016 [P] [US4] Create `templates/products/_product_grid.html` AJAX fragment partial (product grid of `_product_card.html` cards + pagination, no surrounding layout — used for partial responses and as include target)
- [X] T017 [US4] Update `templates/products/product_list.html` with: active filter pills (each with remove control), "Clear all filters" link, subcategory navigation links, and `id="product-grid"` anchor for JS DOM swap
- [X] T018 [P] [US4] Create `static/js/filters.js` (intercepts filter/sort form submit, builds URL with `format=partial`, fires `fetch()`, replaces `#product-grid` DOM node with response, updates browser URL via `history.pushState`)

### Tests for User Story 4

- [X] T019 [P] [US4] Write US4 tests in `tests/test_products.py`: `GET /products/?min_price=10&max_price=50&format=partial` returns `_product_grid.html` fragment (not full page); full request without `format=partial` returns full template; combined filters narrow results correctly; `format=partial` with no results returns empty-state fragment

**Checkpoint**: User Story 4 complete — customers can apply multiple filters and see AJAX-updated results independently

---

## Phase 7: User Story 5 — Customer Submits a Product Review (Priority: P2)

**Goal**: Authenticated customers can submit a star rating and optional review text; the review is held for moderation; duplicate submissions are prevented; guests see a login prompt.

**Independent Test**: Log in, navigate to a product without a prior review, submit a rating and review text, verify confirmation; attempt a second submission and verify it is blocked; log out and verify the review form is replaced by a login prompt.

### Implementation for User Story 5

- [X] T020 [US5] Create `products/forms.py` with `ReviewSubmissionForm` (fields: `rating` IntegerField 1–5 with `MinValueValidator`/`MaxValueValidator`, `title` CharField max 200 optional, `body` CharField optional)
- [X] T021 [US5] Add `ReviewSubmitView` to `products/views.py` (`LoginRequiredMixin`, `FormView`, `form_class = ReviewSubmissionForm`; `post()` checks `ProductReview.objects.filter(product=product, user=request.user).exists()` before saving; sets `review.product`, `review.user`, `review.is_approved = False`; redirects to `products:product_detail` with `?review=submitted` on success or `?review=exists` on duplicate)
- [X] T022 [US5] Add review URL to `products/urls.py` before the `<slug:slug>` route: `path("products/<slug:slug>/review/", views.ReviewSubmitView.as_view(), name="submit_review")`
- [X] T023 [US5] Update `templates/products/product_detail.html` with: review submission form (for authenticated users without existing review), current user's existing review display, guest login prompt, `?review=submitted` success message, `?review=exists` info message

### Tests for User Story 5

- [X] T024 [P] [US5] Write US5 tests in `tests/test_products.py`: authenticated POST creates review with `is_approved=False`; duplicate POST returns redirect without creating second review; unauthenticated POST redirects to login; form validation error returns 200 with inline errors; `?review=submitted` message visible in response

**Checkpoint**: User Story 5 complete — authenticated review submission with moderation flow works independently

---

## Phase 8: User Story 6 — Administrator Manages Products (Priority: P2)

**Goal**: Administrators can see stock status directly in the product list admin, and can approve/reject reviews via the `ProductReviewAdmin` interface created in Phase 2.

**Independent Test**: Log in as admin; apply "bulk deactivate" to selected products and verify they disappear from public listing; navigate to Reviews admin and use "bulk approve" to approve a review; verify it appears on the product detail page.

### Implementation for User Story 6

- [X] T025 [US6] Add `stock_status` to `ProductAdmin.list_display` and `list_filter` in `products/admin.py` so admin can filter by stock status and see it in the product list

### Tests for User Story 6

- [X] T026 [P] [US6] Write US6 tests in `tests/test_products.py`: admin bulk_approve sets `is_approved=True` on selected reviews; bulk deactivate hides products from public listing; inactive product URL returns 404; stock_status appears in admin list display

**Checkpoint**: User Story 6 complete — admin can manage products and moderate reviews independently

---

## Phase 9: User Story 7 — Customer Views Product Recommendations (Priority: P3)

**Goal**: Product detail pages show a "Recently Viewed" shelf (up to 8 session-tracked products) and a "Related Products" section (up to 4 same-category products, already populated by Epic 1).

**Independent Test**: Browse 3 products, return to any product page, verify "Recently Viewed" shows those products in reverse chronological order.

### Implementation for User Story 7

- [X] T027 [US7] Add recently-viewed session tracking to `ProductDetailView.get_context_data()` in `products/views.py`: prepend current product PK to `request.session["recently_viewed"]` list (max 8, deduplicated, set `request.session.modified = True`); batch-fetch `Product.objects.filter(pk__in=pks).only("name", "slug", "price")` excluding current product; add `recently_viewed` to context
- [X] T028 [US7] Add recently-viewed shelf to `templates/products/product_detail.html` (horizontal scroll, uses `_product_card.html`, hidden when `recently_viewed` is empty)
- [X] T029 [P] [US7] Add recently-viewed shelf to `templates/products/product_list.html` (same pattern as T028, shown at bottom of listing page)

### Tests for User Story 7

- [X] T030 [P] [US7] Write US7 tests in `tests/test_products.py`: viewing a product adds its PK to session; second view deduplicates PK; list truncates at 8; `recently_viewed` context excludes current product; related products context excludes current product

**Checkpoint**: User Story 7 complete — recently viewed and related products work independently

---

## Phase 10: User Story 8 — Customer Compares Products (Priority: P3)

**Goal**: Customers can add up to 3 same-category products to a comparison selection; a persistent floating widget shows the selection; the comparison view shows a side-by-side attribute table; the selection persists for the full session.

**Independent Test**: Add 2 products from the same category to the comparison widget, open `/products/compare/`, verify a table with attributes side by side; remove one product and verify the table updates; try adding a product from a different category and verify a rejection message.

### Implementation for User Story 8

- [X] T031 [US8] Add `ComparisonAddView`, `ComparisonRemoveView`, and `ComparisonView` to `products/views.py`:
  - `ComparisonAddView.post()`: validate `product_id` (int, active product exists); initialise `request.session["comparison"] = {"pks": [], "category_id": None}` on first add; enforce same-category constraint (redirect with `?compare_error=category` on mismatch); enforce 3-product limit (redirect with `?compare_error=limit`); set `request.session.modified = True`; use `url_has_allowed_host_and_scheme()` for redirect back to referrer
  - `ComparisonRemoveView.post()`: remove PK from session list, reset `category_id` if list empty
  - `ComparisonView.get()`: batch-fetch compared products; build attribute matrix from variant names/values; render `compare.html`
- [X] T032 [US8] Add comparison URLs to `products/urls.py` **before** the `<slug:slug>` route: `compare/`, `compare/add/`, `compare/remove/`
- [X] T033 [P] [US8] Create `templates/products/compare.html` (side-by-side table: name, primary image, price, aggregate rating, key attributes from variants; empty-state message; "Remove" button per product; "Clear All" link)
- [X] T034 [P] [US8] Create `templates/products/_compare_widget.html` (floating bar showing 0–3 selected products; "Compare" CTA linking to `/products/compare/`; "×" remove button per slot; hidden when comparison list is empty; include in `base.html` or listing templates)
- [X] T035 [P] [US8] Create `static/js/comparison.js` (intercepts "Add to Compare" button clicks, posts to `compare/add/` via `fetch()`, updates widget count badge, shows error toast on category mismatch or limit exceeded)

### Tests for User Story 8

- [X] T036 [P] [US8] Write US8 tests in `tests/test_products.py`: add product stores PK in session; adding 4th product returns limit error; adding product from different category returns category error; remove clears PK from session; `GET /products/compare/` renders products table; empty comparison renders empty state; invalid `product_id` triggers redirect with `?compare_error=invalid`

**Checkpoint**: User Story 8 complete — product comparison with session persistence works independently

---

## Final Phase: Polish & Cross-Cutting Concerns

**Purpose**: Validate the full implementation, meet coverage requirements, and commit

- [X] T037 Run full test suite and fix any coverage gaps: `pytest tests/ --cov=. --cov-report=term-missing` (target: ≥95% coverage, 0 failures)
- [X] T038 [P] Run all 7 pre-commit quality gates: `flake8`, `mypy`, `bandit`, `pip-audit`, `pre-commit run --all-files` — fix all reported issues
- [X] T039 Commit all changes: `git add -A && git commit -m "feat: implement product catalog system (EPIC-2, Tasks T001-T038)"`

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies — start immediately
- **Foundational (Phase 2)**: Depends on Phase 1 — **BLOCKS all user story phases**
- **Phase 3 (US1)**: Depends on Phase 2 completion only
- **Phase 4 (US2)**: Depends on Phase 2 completion only (and T020 `ReviewSubmissionForm` for the form instance in context — but form can be instantiated as `None` temporarily; full wiring in Phase 7)
- **Phase 5 (US3)**: Depends on Phase 2 completion only
- **Phase 6 (US4)**: Depends on Phase 3 (US1) — reuses `_product_card.html` (T005) and product listing page
- **Phase 7 (US5)**: Depends on Phase 4 (US2) — adds form to the product detail template updated in T009/T023
- **Phase 8 (US6)**: Depends on Phase 2 (T004 ProductReviewAdmin already complete)
- **Phase 9 (US7)**: Depends on Phase 4 (US2) — extends the same `ProductDetailView.get_context_data()` modified in T008
- **Phase 10 (US8)**: Depends on Phase 2 completion only (session pattern, product model)
- **Final Phase**: Depends on all desired user story phases being complete

### Key Sequential Dependencies Within Phases

| Task | Depends On | Reason |
|------|-----------|--------|
| T006 (category.html) | T005 (_product_card.html) | Template includes the partial |
| T009 (product_detail.html reviews) | T008 (extend context) | Template uses context vars |
| T012 (AutocompleteView + URL) | T001 (settings) | View imports settings |
| T015 (AJAX partial in view) | T016 (create _product_grid.html) | View renders the template |
| T017 (product_list.html filter pills) | T015, T016 | Template references grid partial |
| T021 (ReviewSubmitView) | T020 (ReviewSubmissionForm) | View imports the form |
| T022 (review URL) | T021 (ReviewSubmitView) | URL references the view |
| T023 (product_detail.html form) | T022, T009 | Template updated after URL wired up |
| T027 (recently_viewed in view) | T008 (get_context_data already extended) | Extends the same method |
| T028 (recently_viewed in template) | T027 (context var added) | Template uses `recently_viewed` |
| T032 (comparison URLs) | T031 (comparison views exist) | URL references views |
| T033, T034 (compare templates) | T031 (views set context vars) | Templates use context |

### Parallel Opportunities Per Story

- **Phase 2**: T002, T003, T004 can all run in parallel (different model classes/files)
- **Phase 3**: T007 tests can run while T006 category.html is being created (different files)
- **Phase 5**: T013 autocomplete.js can be written while T011/T012 server-side work is done
- **Phase 6**: T016 (_product_grid.html) and T018 (filters.js) in parallel after T015
- **Phase 7**: T024 tests can be written while T020–T023 implementation proceeds
- **Phase 10**: T033, T034, T035 can run in parallel after T031 is complete

---

## Parallel Example: User Story 8

```bash
# After T031 (comparison views) and T032 (URLs) are complete, launch in parallel:
Task T033: "Create templates/products/compare.html"
Task T034: "Create templates/products/_compare_widget.html"
Task T035: "Create static/js/comparison.js"
Task T036: "Write US8 tests in tests/test_products.py"
```

## Parallel Example: User Story 3

```bash
# After T011 (search_results.html) and T012 (AutocompleteView + URL) are complete:
Task T013: "Create static/js/autocomplete.js"   # frontend, no server deps
Task T014: "Write US3 tests"                      # can be written independently
```

---

## Implementation Strategy

### MVP First (P1 Stories Only)

1. Complete Phase 1 Setup
2. Complete Phase 2 Foundational (CRITICAL — blocks everything)
3. Complete Phase 3 US1 — product browsing and category pages
4. Complete Phase 4 US2 — product detail with reviews display
5. Complete Phase 5 US3 — search results and autocomplete
6. **STOP and VALIDATE**: All three P1 stories independently testable
7. Run tests and quality gates before proceeding to P2

### Incremental Delivery

1. Setup + Foundational → Shared components ready
2. US1 (P1) → Customers can browse → MVP browsing experience
3. US2 (P1) → Customers can see product details → Full detail view
4. US3 (P1) → Customers can search → Core discovery complete (**P1 MVP done**)
5. US4 (P2) → AJAX filtering → Filtering UX upgrade
6. US5 (P2) → Review submission → Engagement feature
7. US6 (P2) → Admin management → Operations complete
8. US7 (P3) → Recently viewed → Recommendation layer
9. US8 (P3) → Product comparison → Advanced discovery
10. Polish → Quality gates, commit

### Story Count by Priority

| Priority | Stories | Tasks |
|----------|---------|-------|
| Setup/Foundation | — | T001–T005 (5 tasks) |
| P1 | US1, US2, US3 | T006–T014 (9 tasks) |
| P2 | US4, US5, US6 | T015–T026 (12 tasks) |
| P3 | US7, US8 | T027–T036 (10 tasks) |
| Polish | — | T037–T039 (3 tasks) |
| **Total** | **8 stories** | **39 tasks** |

---

## Notes

- `[P]` tasks target different files with no incomplete dependencies in the same phase
- `[US?]` label traces each task to its user story for independent validation
- `compare/*` and `autocomplete` URLs **must** be declared before `products/<slug:slug>/` in `products/urls.py`
- Always call `request.session.modified = True` after mutating `recently_viewed` or `comparison` session dicts
- Open redirect guard: use `url_has_allowed_host_and_scheme()` from `django.utils.http` in all comparison redirect logic (same pattern as `orders/views.py`)
- No new migrations required — all schema changes were completed in Epic 1
