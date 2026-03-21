# Data Model: ShopHub — Epic 1 (Database Models & Infrastructure)

**Branch**: `001-database-models-infrastructure` | **Date**: 2026-03-20  
**Source**: Reverse-engineered from `copilot-plan-agent-build` with improvements noted.

---

## Design Decisions

| Decision | Choice | Rationale |
|----------|--------|-----------|
| Primary keys | Django default (integer auto-increment) | Reference impl uses this; matches Django convention; UUID adds overhead with no clear benefit at this scale |
| User extension | `UserProfile` OneToOne (not custom User) | Avoids swapping `AUTH_USER_MODEL` mid-project and the complex migrations that follow |
| Category hierarchy | Self-referential `parent` FK | No extra library (MPTT/treebeard); adequate for typical category depth ≤ 5 |
| Address storage | Inlined on `UserProfile` and `Order` | Reference impl does this; avoids join for the most common read path; separate Address model deferred to Epic 4 enhancement |
| Cart identity | UserProfile OneToOne + session_key for anon | Reference pattern: promoted on login |
| Order number | `ORD-YYYYMMDD-<8hex>` generated on first save | UUID-derived suffix; collision-resistant enough for typical throughput |
| Price snapshot | `OrderItem` copies product_name, product_sku, unit_price at save | Ensures historical accuracy when products change post-purchase |
| Image resize | `ProductImage.save()` calls Pillow resize (800×800 max) | Prevents large uploads bloating media storage |
| Cache invalidation | `post_save`/`post_delete` signals on Category, Product, ProductVariant | Keeps Redis/LocMemCache consistent without manual cache busting in views |

---

## Entity Relationship Overview

```
User (Django built-in)
 └── UserProfile (OneToOne)

Category ──self-ref parent──> Category
Product ──FK──> Category
Product ──rev──> ProductImage (many)
Product ──rev──> ProductVariant (many)
Product ──rev──> ProductReview (many) [FK: User]

Cart ──OneToOne──> User (nullable)
Cart ──rev──> CartItem (many)
CartItem ──FK──> Product
CartItem ──FK──> ProductVariant (nullable)

Order ──FK──> User (nullable)
Order ──rev──> OrderItem (many)
OrderItem ──FK──> Product
OrderItem ──FK──> ProductVariant (nullable)
```

---

## Models

### 1. `accounts.UserProfile`

Extends Django's built-in `User` via OneToOne.  
Auto-created by `post_save` signal on `User`.

| Field | Type | Constraints | Index |
|-------|------|-------------|-------|
| `id` | AutoField (PK) | — | PK |
| `user` | OneToOneField → `auth.User` | CASCADE, related_name=`profile` | implicit |
| `phone_number` | CharField(20) | blank/null, `phone_regex` validator | — |
| `date_of_birth` | DateField | blank/null | — |
| `address_line_1` | CharField(255) | blank/null | — |
| `address_line_2` | CharField(255) | blank/null | — |
| `city` | CharField(100) | blank/null | — |
| `state_province` | CharField(100) | blank/null | — |
| `postal_code` | CharField(20) | blank/null | — |
| `country` | CharField(100) | blank/null | — |
| `newsletter_subscription` | BooleanField | default=False | — |
| `email_notifications` | BooleanField | default=True | — |
| `created_at` | DateTimeField | auto_now_add | — |
| `updated_at` | DateTimeField | auto_now | — |

**Properties**: `full_name`, `full_address`  
**Meta**: `ordering=["-created_at"]`

---

### 2. `products.Category`

Self-referential hierarchy (depth ≤ 5 recommended).

| Field | Type | Constraints | Index |
|-------|------|-------------|-------|
| `id` | AutoField (PK) | — | PK |
| `name` | CharField(200) | unique | — |
| `slug` | SlugField(200) | unique, blank (auto from name) | ✓ |
| `description` | TextField | blank/null | — |
| `image` | ImageField(`categories/`) | blank/null | — |
| `parent` | ForeignKey → self | CASCADE, null/blank, related_name=`children` | — |
| `is_active` | BooleanField | default=True | ✓ (composite with `name`) |
| `created_at` | DateTimeField | auto_now_add | — |
| `updated_at` | DateTimeField | auto_now | — |

**Methods**: `save()` auto-slugifies `name`; `get_absolute_url()`  
**Meta**: `ordering=["name"]`; indexes on `slug`, `(is_active, name)`

---

### 3. `products.Product`

Core product entity.

| Field | Type | Constraints | Index |
|-------|------|-------------|-------|
| `id` | AutoField (PK) | — | PK |
| `name` | CharField(200) | — | — |
| `slug` | SlugField(200) | unique, blank (auto) | ✓ |
| `category` | ForeignKey → Category | CASCADE, related_name=`products` | implicit FK |
| `description` | TextField | — | — |
| `short_description` | CharField(500) | blank/null | — |
| `price` | DecimalField(10,2) | — | — |
| `compare_price` | DecimalField(10,2) | blank/null | — |
| `cost_price` | DecimalField(10,2) | blank/null | — |
| `sku` | CharField(100) | unique | ✓ |
| `stock_quantity` | PositiveIntegerField | default=0 | — |
| `track_inventory` | BooleanField | default=True | — |
| `allow_backorders` | BooleanField | default=False | — |
| `weight` | DecimalField(8,2) | blank/null | — |
| `dimensions_length` | DecimalField(8,2) | blank/null | — |
| `dimensions_width` | DecimalField(8,2) | blank/null | — |
| `dimensions_height` | DecimalField(8,2) | blank/null | — |
| `meta_title` | CharField(200) | blank/null | — |
| `meta_description` | CharField(500) | blank/null | — |
| `is_active` | BooleanField | default=True | ✓ (composite with `-created_at`) |
| `is_featured` | BooleanField | default=False | — |
| `is_digital` | BooleanField | default=False | — |
| `created_at` | DateTimeField | auto_now_add | — |
| `updated_at` | DateTimeField | auto_now | — |

**Properties**: `is_on_sale`, `discount_percentage`, `is_in_stock`, `main_image`  
**Methods**: `save()` auto-slugifies; `get_absolute_url()`  
**Meta**: `ordering=["-created_at"]`; indexes on `slug`, `sku`, `(is_active, -created_at)`  
**Signals**: `post_save`/`post_delete` → cache invalidation

---

### 4. `products.ProductImage`

Multiple images per product; one marked primary.

| Field | Type | Constraints | Index |
|-------|------|-------------|-------|
| `id` | AutoField (PK) | — | PK |
| `product` | ForeignKey → Product | CASCADE, related_name=`images` | ✓ (composite with `is_primary`) |
| `image` | ImageField(`products/`) | file-ext validator + size validator (≤ MAX_IMAGE_UPLOAD_MB, default 5MB) | — |
| `alt_text` | CharField(200) | blank/null | — |
| `is_primary` | BooleanField | default=False | ✓ (composite with `product`) |
| `sort_order` | PositiveIntegerField | default=0 | — |
| `created_at` | DateTimeField | auto_now_add | — |

**Methods**: `save()` enforces single primary per product, triggers `resize_image()`; `resize_image()` uses Pillow 800×800 max, preserves PNG/WebP transparency  
**Meta**: `ordering=["sort_order", "-created_at"]`; index on `(product, is_primary)`

---

### 5. `products.ProductVariant`

Attribute-value pairs per product (e.g. "Size / Large").

| Field | Type | Constraints | Index |
|-------|------|-------------|-------|
| `id` | AutoField (PK) | — | PK |
| `product` | ForeignKey → Product | CASCADE, related_name=`variants` | implicit FK |
| `name` | CharField(100) | — (e.g. "Color") | — |
| `value` | CharField(100) | — (e.g. "Red") | — |
| `price_adjustment` | DecimalField(10,2) | default=0 | — |
| `sku_suffix` | CharField(50) | blank/null | — |
| `stock_quantity` | PositiveIntegerField | default=0 | — |
| `is_active` | BooleanField | default=True | — |
| `sort_order` | PositiveIntegerField | default=0 | — |
| `created_at` | DateTimeField | auto_now_add | — |

**Properties**: `full_sku` (product.sku + sku_suffix), `final_price` (product.price + price_adjustment)  
**Meta**: `ordering=["sort_order", "name", "value"]`; `unique_together=["product", "name", "value"]`  
**Signals**: `post_save`/`post_delete` → parent product cache invalidation

---

### 6. `products.ProductReview`

Customer ratings and reviews. Added here (not in reference; part of spec FR-019).

| Field | Type | Constraints | Index |
|-------|------|-------------|-------|
| `id` | AutoField (PK) | — | PK |
| `product` | ForeignKey → Product | CASCADE, related_name=`reviews` | implicit FK |
| `user` | ForeignKey → `auth.User` | CASCADE, related_name=`reviews` | implicit FK |
| `rating` | PositiveSmallIntegerField | MinValueValidator(1), MaxValueValidator(5) | — |
| `title` | CharField(200) | blank | — |
| `body` | TextField | — | — |
| `is_approved` | BooleanField | default=False | — |
| `created_at` | DateTimeField | auto_now_add | — |
| `updated_at` | DateTimeField | auto_now | — |

**Meta**: `ordering=["-created_at"]`; `unique_together=["product", "user"]` (one review per user per product)

---

### 7. `orders.Cart`

Session-based for anonymous users; user-linked for authenticated users.

| Field | Type | Constraints | Index |
|-------|------|-------------|-------|
| `id` | AutoField (PK) | — | PK |
| `user` | OneToOneField → `auth.User` | CASCADE, null/blank, related_name=`cart` | implicit |
| `session_key` | CharField(40) | null/blank | — |
| `created_at` | DateTimeField | auto_now_add | — |
| `updated_at` | DateTimeField | auto_now | — |

**Properties**: `total_items`, `total_price` (both prefetch-cache-aware)  
**Methods**: `clear()`  
**Meta**: `ordering=["-updated_at"]`

---

### 8. `orders.CartItem`

Line items within a cart.

| Field | Type | Constraints | Index |
|-------|------|-------------|-------|
| `id` | AutoField (PK) | — | PK |
| `cart` | ForeignKey → Cart | CASCADE, related_name=`items` | ✓ (composite with `-created_at`) |
| `product` | ForeignKey → `products.Product` | CASCADE | — |
| `variant` | ForeignKey → `products.ProductVariant` | CASCADE, null/blank | — |
| `quantity` | PositiveIntegerField | default=1, MinValueValidator(1) | — |
| `created_at` | DateTimeField | auto_now_add | — |
| `updated_at` | DateTimeField | auto_now | — |

**Properties**: `unit_price` (variant.final_price or product.price), `total_price`  
**Meta**: `unique_together=["cart", "product", "variant"]`; additional `UniqueConstraint` for null-variant case (prevents duplicate base-product rows); index on `(cart, -created_at)`

---

### 9. `orders.Order`

Customer order with embedded billing/shipping address snapshot.

| Field | Type | Constraints | Index |
|-------|------|-------------|-------|
| `id` | AutoField (PK) | — | PK |
| `order_number` | CharField(50) | unique, editable=False | ✓ |
| `user` | ForeignKey → `auth.User` | CASCADE, null/blank, related_name=`orders` | ✓ (composite with `-created_at`) |
| `email` | EmailField | — | — |
| `first_name` | CharField(100) | — | — |
| `last_name` | CharField(100) | — | — |
| `phone_number` | CharField(20) | blank/null, phone_regex | — |
| `billing_address_line_1` | CharField(255) | — | — |
| `billing_address_line_2` | CharField(255) | blank/null | — |
| `billing_city` | CharField(100) | — | — |
| `billing_state_province` | CharField(100) | — | — |
| `billing_postal_code` | CharField(20) | — | — |
| `billing_country` | CharField(100) | — | — |
| `shipping_same_as_billing` | BooleanField | default=True | — |
| `shipping_address_line_1` | CharField(255) | blank/null | — |
| `shipping_address_line_2` | CharField(255) | blank/null | — |
| `shipping_city` | CharField(100) | blank/null | — |
| `shipping_state_province` | CharField(100) | blank/null | — |
| `shipping_postal_code` | CharField(20) | blank/null | — |
| `shipping_country` | CharField(100) | blank/null | — |
| `subtotal` | DecimalField(10,2) | default=0, MinValueValidator(0) | — |
| `tax_amount` | DecimalField(10,2) | default=0, MinValueValidator(0) | — |
| `shipping_cost` | DecimalField(10,2) | default=0, MinValueValidator(0) | — |
| `discount_amount` | DecimalField(10,2) | default=0, MinValueValidator(0) | — |
| `total_amount` | DecimalField(10,2) | default=0, MinValueValidator(0) | — |
| `status` | CharField(20) | choices (7 values), default=`pending` | ✓ (composite with `-created_at`) |
| `payment_status` | CharField(20) | choices (5 values), default=`pending` | — |
| `payment_method` | CharField(50) | default=`credit_card` | — |
| `order_notes` | TextField | blank/null | — |
| `internal_notes` | TextField | blank/null | — |
| `created_at` | DateTimeField | auto_now_add | — |
| `updated_at` | DateTimeField | auto_now | — |
| `shipped_at` | DateTimeField | null/blank | — |
| `delivered_at` | DateTimeField | null/blank | — |

**Methods**: `save()` calls `generate_order_number()` on first save; `recalculate_totals(tax_rate, save)` recomputes subtotal/tax/total from live OrderItems  
**Properties**: `full_name`, `billing_address`, `shipping_address`, `can_be_cancelled`, `is_completed`  
**Meta**: `ordering=["-created_at"]`; indexes on `order_number`, `(status, -created_at)`, `(user, -created_at)`

---

### 10. `orders.OrderItem`

Immutable line item snapshot within an order.

| Field | Type | Constraints | Index |
|-------|------|-------------|-------|
| `id` | AutoField (PK) | — | PK |
| `order` | ForeignKey → Order | CASCADE, related_name=`items` | implicit FK |
| `product` | ForeignKey → `products.Product` | CASCADE | — |
| `variant` | ForeignKey → `products.ProductVariant` | CASCADE, null/blank | — |
| `product_name` | CharField(200) | snapshot on first save | — |
| `product_sku` | CharField(100) | snapshot on first save | — |
| `variant_name` | CharField(100) | blank/null, snapshot on first save | — |
| `variant_value` | CharField(100) | blank/null, snapshot on first save | — |
| `quantity` | PositiveIntegerField | MinValueValidator(1) | — |
| `unit_price` | DecimalField(10,2) | price at time of purchase | — |
| `total_price` | DecimalField(10,2) | auto-computed = unit_price × quantity | — |
| `created_at` | DateTimeField | auto_now_add | — |

**Methods**: `save()` snapshots product/variant details on first write; computes `total_price`  
**Meta**: `ordering=["id"]`

---

## Model Count Summary

| App | Models |
|-----|--------|
| `accounts` | UserProfile |
| `products` | Category, Product, ProductImage, ProductVariant, ProductReview |
| `orders` | Cart, CartItem, Order, OrderItem |
| **Total** | **10 models** (+ Django auth.User, auth.Group built-ins) |

> **Note**: The original spec listed `Payment` as a separate model. The reference implementation does not include a standalone Payment model — payment state is tracked via `Order.payment_status` and `Order.payment_method`. A dedicated `Payment` model is deferred to Epic 4 (User Authentication & Orders) if needed.

---

## Key Constraints Summary

| Constraint | Enforced By |
|-----------|-------------|
| One UserProfile per User | OneToOneField |
| Unique product slug & SKU | `unique=True` on field |
| Unique category slug & name | `unique=True` on field |
| One primary image per product | `ProductImage.save()` logic |
| No duplicate (name, value) variant per product | `unique_together` |
| No duplicate base-product cart item (null variant) | `UniqueConstraint` with `Q(variant__isnull=True)` |
| No duplicate (product, user) review | `unique_together` |
| Unique order number | `unique=True` on field |
| All decimal amounts ≥ 0 | `MinValueValidator(Decimal("0.00"))` |
| CartItem quantity ≥ 1 | `MinValueValidator(1)` |
