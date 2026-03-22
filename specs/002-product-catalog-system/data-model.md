# Data Model: Product Catalog System (Epic 2)

**Branch**: `002-product-catalog-system`
**Date**: 2026-03-22
**Status**: Complete — all entities already exist in Django ORM from Epic 1

---

## Overview

All entities required by Epic 2 are defined in `products/models.py`. This document
captures each entity's fields, relationships, validation rules, and state transitions
to serve as the authoritative reference during implementation.

Epic 2 adds **one new model property** (`stock_status`) and makes no schema changes
— no new migrations are required.

---

## Entity 1: Category

**File**: `products/models.py:Category`

| Field | Type | Nullable | Unique | Notes |
|-------|------|----------|--------|-------|
| `id` | Auto PK | — | ✅ | |
| `name` | CharField(200) | No | ✅ | |
| `slug` | SlugField(200) | No | ✅ | Auto-generated from name if blank |
| `description` | TextField | Yes | No | |
| `image` | ImageField | Yes | No | upload_to="categories/" |
| `parent` | FK(self) | Yes | No | Enables category hierarchy; null = root |
| `is_active` | BooleanField | No | No | Default: True |
| `created_at` | DateTimeField | No | No | auto_now_add |
| `updated_at` | DateTimeField | No | No | auto_now |

**Relationships**:
- `parent` → `Category` (self-referential, nullable FK, on_delete=CASCADE)
- `children` (reverse manager via `parent`)
- `products` (reverse manager from `Product.category`)

**Validation Rules**:
- `name` must be globally unique
- `slug` must be globally unique; auto-slugified from name if not provided

**Business Rules**:
- Category browsing (`CategoryView`) includes all products from the category AND its direct children (one level of nesting supported in current query)
- Deleting a category cascades to products in that category (they become orphaned per edge-case spec)

**Indexes**: `(slug)`, `(is_active, name)`

---

## Entity 2: Product

**File**: `products/models.py:Product`

| Field | Type | Nullable | Unique | Notes |
|-------|------|----------|--------|-------|
| `id` | Auto PK | — | ✅ | |
| `name` | CharField(200) | No | No | |
| `slug` | SlugField(200) | No | ✅ | Auto-generated from name if blank |
| `category` | FK(Category) | No | No | on_delete=CASCADE |
| `description` | TextField | No | No | Full marketing copy |
| `short_description` | CharField(500) | Yes | No | Used in listing cards |
| `price` | DecimalField(10,2) | No | No | Current selling price |
| `compare_price` | DecimalField(10,2) | Yes | No | Original price (for "was/now") |
| `cost_price` | DecimalField(10,2) | Yes | No | Internal cost (admin only) |
| `sku` | CharField(100) | No | ✅ | |
| `stock_quantity` | PositiveIntegerField | No | No | Default: 0 |
| `track_inventory` | BooleanField | No | No | Default: True |
| `allow_backorders` | BooleanField | No | No | Default: False |
| `weight` | DecimalField(8,2) | Yes | No | |
| `dimensions_*` | DecimalField(8,2) | Yes | No | 3 fields: l/w/h |
| `meta_title` | CharField(200) | Yes | No | SEO |
| `meta_description` | CharField(500) | Yes | No | SEO |
| `is_active` | BooleanField | No | No | Default: True; controls visibility |
| `is_featured` | BooleanField | No | No | Default: False |
| `is_digital` | BooleanField | No | No | Default: False |
| `created_at` | DateTimeField | No | No | auto_now_add |
| `updated_at` | DateTimeField | No | No | auto_now |

**Computed Properties** (no DB column):
- `is_on_sale` → bool: `compare_price is not None and compare_price > price`
- `discount_percentage` → int: percentage off compare_price
- `is_in_stock` → bool: `stock_quantity > 0 or allow_backorders` (when track_inventory=True)
- `main_image` → ProductImage|None: primary image, prefetch-aware
- `stock_status` (**NEW in Epic 2**) → str: `"in_stock"` / `"low_stock"` / `"out_of_stock"` based on `settings.LOW_STOCK_THRESHOLD` (default 5)

**Relationships**:
- `category` → Category
- `images` (reverse manager: `ProductImage.product`)
- `variants` (reverse manager: `ProductVariant.product`)
- `reviews` (reverse manager: `ProductReview.product`)

**State Transitions** (`is_active`):
```
DRAFT (is_active=False) ──[admin activates]──▶ ACTIVE (is_active=True)
ACTIVE ──[admin deactivates / bulk deactivate]──▶ DRAFT
```
- ACTIVE: visible on all customer-facing pages, searchable
- DRAFT: hidden from all customer pages; accessible only in Django admin

**Validation Rules**:
- `slug` → unique globally; auto-slugified from name
- `sku` → unique globally
- `price` → must be positive Decimal

**Indexes**: `(slug)`, `(sku)`, `(is_active, -created_at)`

---

## Entity 3: ProductImage

**File**: `products/models.py:ProductImage`

| Field | Type | Nullable | Unique | Notes |
|-------|------|----------|--------|-------|
| `id` | Auto PK | — | ✅ | |
| `product` | FK(Product) | No | No | on_delete=CASCADE |
| `image` | ImageField | No | No | upload_to="products/"; validated extension + size |
| `alt_text` | CharField(200) | Yes | No | |
| `is_primary` | BooleanField | No | No | Default: False |
| `sort_order` | PositiveIntegerField | No | No | Default: 0 |
| `created_at` | DateTimeField | No | No | auto_now_add |

**Validation Rules**:
- File extensions: jpg, jpeg, png, webp, gif (FileExtensionValidator)
- File size: max `settings.MAX_IMAGE_UPLOAD_MB` (default 5 MB)
- Only one `is_primary=True` per product (enforced in `save()`)

**Auto-Behaviour** (`save()`):
- When `is_primary=True`, all other images for the same product are flipped to `is_primary=False`
- When image file is new/changed, calls `resize_image()` → resizes to max 800×800px, compresses JPEG to quality=85

**Indexes**: `(product, is_primary)` — supports `main_image` lookup

---

## Entity 4: ProductVariant

**File**: `products/models.py:ProductVariant`

| Field | Type | Nullable | Unique | Notes |
|-------|------|----------|--------|-------|
| `id` | Auto PK | — | ✅ | |
| `product` | FK(Product) | No | No | on_delete=CASCADE |
| `name` | CharField(100) | No | No | Attribute type, e.g., "Size" |
| `value` | CharField(100) | No | No | Attribute value, e.g., "Large" |
| `price_adjustment` | DecimalField(10,2) | No | No | Default: 0 |
| `sku_suffix` | CharField(50) | Yes | No | |
| `stock_quantity` | PositiveIntegerField | No | No | Default: 0 |
| `is_active` | BooleanField | No | No | Default: True |
| `sort_order` | PositiveIntegerField | No | No | Default: 0 |
| `created_at` | DateTimeField | No | No | auto_now_add |

**Constraints**: `unique_together = [("product", "name", "value")]`

**Computed Properties** (**NEW in Epic 2**):
- `stock_status` → str: same logic as Product.stock_status, using variant's own `stock_quantity`

---

## Entity 5: ProductReview

**File**: `products/models.py:ProductReview`

| Field | Type | Nullable | Unique | Notes |
|-------|------|----------|--------|-------|
| `id` | Auto PK | — | ✅ | |
| `product` | FK(Product) | No | No | on_delete=CASCADE |
| `user` | FK(auth.User) | No | No | on_delete=CASCADE |
| `rating` | PositiveSmallIntegerField | No | No | 1–5; MinValueValidator + MaxValueValidator |
| `title` | CharField(200) | No | No | blank=True allowed |
| `body` | TextField | No | No | Required in practice |
| `is_approved` | BooleanField | No | No | Default: False; controls public visibility |
| `created_at` | DateTimeField | No | No | auto_now_add |
| `updated_at` | DateTimeField | No | No | auto_now |

**Constraints**: `unique_together = [("product", "user")]` → one review per user per product

**State Transitions** (`is_approved`):
```
PENDING (is_approved=False) ──[admin approves]──▶ APPROVED (is_approved=True)
APPROVED ──[admin rejects]──▶ PENDING
```
- PENDING: visible only in Django admin moderation queue
- APPROVED: visible on product detail page; included in aggregate rating calculation

**Validation Rules**:
- `rating` must be between 1 and 5 inclusive
- A user cannot submit a second review for the same product

---

## New Properties (Epic 2 Additions — No Migration Required)

### `Product.stock_status` property

```python
@property
def stock_status(self) -> str:
    """Return stock status label based on configurable threshold."""
    from django.conf import settings
    threshold = getattr(settings, "LOW_STOCK_THRESHOLD", 5)
    if not self.track_inventory:
        return "in_stock"
    if self.stock_quantity == 0 and not self.allow_backorders:
        return "out_of_stock"
    if self.stock_quantity <= threshold:
        return "low_stock"
    return "in_stock"
```

### `ProductVariant.stock_status` property

```python
@property
def stock_status(self) -> str:
    """Return stock status label for this variant."""
    from django.conf import settings
    threshold = getattr(settings, "LOW_STOCK_THRESHOLD", 5)
    if self.stock_quantity == 0:
        return "out_of_stock"
    if self.stock_quantity <= threshold:
        return "low_stock"
    return "in_stock"
```

---

## Session Data (No DB Model)

### `recently_viewed` (session key)

```python
# Type: list[int]  — list of product PKs in reverse-chronological order
# Max length: 8
# Managed in: ProductDetailView.get_context_data()
# Example: [42, 17, 3, 99]
```

### `comparison` (session key)

```python
# Type: dict — {"pks": list[int], "category_id": int|None}
# pks: up to 3 product PKs
# category_id: enforces same-category constraint
# Managed in: ComparisonAddView, ComparisonRemoveView
# Example: {"pks": [42, 17, 3], "category_id": 5}
```

---

## Entity Relationship Diagram

```
auth.User
    │
    │ 1..*
    ▼
ProductReview ──────────────────────────────────┐
    │                                           │
    │ *.1                                       │
    ▼                                           │
Product ─────────────── Category               │
    │                      │                   │
    │ has many              │ has many          │
    ▼                       ▼                  │
ProductImage         sub-categories            │
ProductVariant                                 │
    │                                          │
    └──────────────────────────────────────────┘
       (FK: product)   (FK: user)
```
