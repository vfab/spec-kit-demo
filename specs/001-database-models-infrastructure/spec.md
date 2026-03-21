# Feature Specification: Database Models & Infrastructure (ShopHub Epic 1)

**Feature Branch**: `001-database-models-infrastructure`  
**Created**: 2026-03-20  
**Status**: Draft  
**Epic**: 1 of 11 — foundational prerequisite for all other epics

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Developer Bootstraps Local Environment (Priority: P1)

A developer clones the ShopHub repository, runs a single `docker-compose up` command, and has a fully operational local development environment with a Postgres database, all migrations applied, and seed data loaded. They can immediately start building features without manual setup steps.

**Why this priority**: Without a working local dev environment, no other development work can begin. This unblocks the entire team.

**Independent Test**: Clone repository, run `docker-compose up --build`, run `python manage.py migrate && python manage.py loaddata dev_seed`, and confirm Django admin is accessible with sample categories, products, and a test user.

**Acceptance Scenarios**:

1. **Given** a fresh clone of the repository, **When** a developer runs `docker-compose up --build`, **Then** the Django app and Postgres container start without errors and the app serves requests on `localhost:8000`.
2. **Given** the containers are running, **When** the developer runs `python manage.py migrate`, **Then** all migrations apply cleanly with zero errors and all tables exist in the database.
3. **Given** migrations are applied, **When** the developer runs `python manage.py loaddata dev_seed`, **Then** the database contains at least 3 product categories, 10 products, and 1 test user.
4. **Given** the seed data is loaded, **When** the developer navigates to `/admin/` and logs in with the seed superuser, **Then** all models (Category, Product, ProductImage, ProductReview, ProductVariant, UserProfile, Address, Cart, CartItem, Order, OrderItem, Payment) are visible in the admin interface.

---

### User Story 2 - Developer Works with the Data Model (Priority: P1)

A developer writing a feature that touches products, orders, or accounts can query the database through clean model APIs with proper relationships, indexes in place, and confidence that model constraints prevent data corruption.

**Why this priority**: Every other epic depends on these models being stable, correct, and performant from day one.

**Independent Test**: Run the full model test suite (`pytest tests/test_products.py tests/test_orders.py tests/test_accounts.py`) and confirm 100% of tests pass with >= 95% coverage.

**Acceptance Scenarios**:

1. **Given** a `Product` record with a `Category` and two `ProductImage` records, **When** a developer fetches the product and accesses `product.images.filter(is_primary=True).first()`, **Then** the primary image is returned without additional queries (via prefetch cache).
2. **Given** an authenticated user adds two items to their cart, **When** `cart.total_price` is accessed, **Then** the correct sum of `(unit_price x quantity)` for all items is returned.
3. **Given** an `Order` is created with status `pending`, **When** the status is changed to `shipped`, **Then** the change is persisted, and querying `Order.objects.filter(status='shipped')` returns that order.
4. **Given** two `CartItem` records for the same `Cart` and `Product` with no variant, **When** a third insert for the same cart+product is attempted, **Then** a database integrity error is raised (unique constraint prevents duplicates).
5. **Given** a `Category` slug field is left blank on save, **When** the record is saved, **Then** the slug is auto-populated from the category name.

---

### User Story 3 - Developer Runs Pre-commit and CI Checks (Priority: P2)

A developer commits code and all 7 pre-commit gates (black, isort, flake8, mypy, bandit, pytest, coverage check) pass. The codebase ships with zero known style, type, or security violations from the start.

**Why this priority**: Establishing quality gates at project inception prevents accumulating technical debt across all 11 epics.

**Independent Test**: Run `pre-commit run --all-files` on the full codebase and confirm all hooks pass with exit code 0.

**Acceptance Scenarios**:

1. **Given** the project codebase, **When** `pre-commit run --all-files` is executed, **Then** black, isort, and flake8 all pass with no violations.
2. **Given** the project codebase, **When** `mypy .` is executed, **Then** no type errors are reported.
3. **Given** the project codebase, **When** `bandit -r .` is executed with the `.bandit` config, **Then** no high-severity findings are reported.
4. **Given** the full model test suite, **When** `pytest --cov` is run, **Then** coverage is at or above 95% and all tests pass.

---

### User Story 4 - Platform Supports Production Deployment (Priority: P2)

A DevOps engineer can configure the application with environment variables for PostgreSQL, secret key, and allowed hosts without modifying source code. Settings split cleanly between dev and production.

**Why this priority**: Production-readiness must be designed in; retrofitting it across 10+ epics is costly.

**Independent Test**: Copy `.env.example` to `.env.production`, set `DATABASE_URL` to a Postgres DSN, `DEBUG=False`, and `SECRET_KEY` to a strong value, then run `python manage.py check --deploy` with no critical warnings.

**Acceptance Scenarios**:

1. **Given** a `.env` file with `DATABASE_URL` set to a Postgres connection string, **When** Django loads settings, **Then** the database backend is PostgreSQL without any code changes.
2. **Given** `DEBUG=False` in the environment, **When** `python manage.py check --deploy` is run, **Then** no critical security warnings are emitted.
3. **Given** the project, **When** the `.env` file is absent from the repository, **Then** no secrets are committed to version control (`.gitignore` excludes `.env`).

---

### Edge Cases

- What happens when a `Category` is deleted that has child categories? (CASCADE deletes children — documented in admin.)
- What happens when a `Product` with active `CartItem` or `OrderItem` references is deleted? (CASCADE from OrderItem; logic to prevent deletion of products with active orders is a future epic concern.)
- How does the system handle an anonymous cart session when a user logs in? (Session merging is deferred to the Cart epic; the model supports `session_key` for this transition.)
- What happens if `stock_quantity` drops to zero for a `Product` or `ProductVariant`? (Model records the value; enforcement of purchase restrictions is deferred to the checkout epic.)
- What happens when `Order.order_number` generation collides? (Auto-generation uses UUID-based or timestamp-prefixed logic with a unique constraint; retries on collision are handled at the application layer.)
- What happens if an image upload exceeds the maximum file size? (A model-level validator raises `ValidationError` before the file is persisted.)

## Requirements *(mandatory)*

### Functional Requirements

#### Project Setup

- **FR-001**: The project MUST be a Django 5.2.x application named `ecommerce_site` with a `manage.py` at the repository root.
- **FR-002**: Settings MUST be split into a base configuration plus environment-specific overrides: `settings/dev.py` (SQLite, `DEBUG=True`) and `settings/production.py` (PostgreSQL, `DEBUG=False`).
- **FR-003**: All environment-specific values (database URL, secret key, allowed hosts, email credentials) MUST be sourced from environment variables via `python-decouple`, with a committed `.env.example` and an uncommitted `.env`.
- **FR-004**: The project MUST include a `Dockerfile` and `docker-compose.yml` that starts the Django application and a Postgres 15 container for local development.
- **FR-005**: The repository MUST include `.gitignore` (excluding `.env`, `*.pyc`, `__pycache__`, `media/`, `staticfiles/`), `pyproject.toml`, and `.pre-commit-config.yaml` configured with black, isort, and flake8.
- **FR-006**: The project MUST include `pytest.ini`, `mypy.ini`, `.flake8`, `.coveragerc`, and `.bandit` configuration files with settings appropriate for a Django project.

#### Base Infrastructure

- **FR-007**: An abstract `BaseModel` MUST define `id` (UUID, primary key, default=uuid4), `created_at` (auto-set on creation), and `updated_at` (auto-updated on every save). All application models MUST inherit from `BaseModel` unless they have a documented reason not to.
- **FR-008**: The `BaseModel` MUST expose a default custom manager and queryset that can be extended per-model without boilerplate.

#### Accounts App

- **FR-009**: A `UserProfile` model MUST extend Django's built-in `User` via a `OneToOneField` and include: `phone` (optional, validated format), `date_of_birth` (optional date), `bio` (optional text), and `avatar` (optional image upload).
- **FR-010**: A `post_save` signal on `User` MUST automatically create a `UserProfile` record when a new `User` is created.
- **FR-011**: An `Address` model MUST belong to a `User` via `ForeignKey` and include: `address_line_1`, `address_line_2` (optional), `city`, `state`, `country`, `postal_code`, `is_default` (boolean), and `address_type` (choice: `shipping` or `billing`).
- **FR-012**: At most one `Address` per user per address type MUST be designated as default (`is_default=True`); the model MUST enforce or document this constraint.

#### Products App

- **FR-013**: A `Category` model MUST support self-referential hierarchy via an optional `parent` `ForeignKey` to `self` (with `null=True, blank=True, related_name='children'`). It MUST include `name`, `slug` (auto-generated from name if blank), `description` (SEO), and `is_active`.
- **FR-014**: A `Product` model MUST include: `name`, `slug` (auto-generated, unique), `description`, `short_description` (optional), `category` FK, `price`, `sale_price` / `compare_price` (optional), `sku` (unique), `stock_quantity`, `is_active`, `is_featured`, `weight` (optional), `meta_title` (optional), `meta_description` (optional).
- **FR-015**: The `Product` model MUST expose computed properties: `is_in_stock` (true when stock_quantity > 0 or backorders allowed), `is_on_sale` (true when `compare_price` > `price`), and `discount_percentage` (integer percentage).
- **FR-016**: A `ProductImage` model MUST link to `Product` and include: `image` (file upload with extension validator for jpg/jpeg/png/webp/gif and a size validator), `alt_text`, `position` (integer for ordering), and `is_primary` (boolean).
- **FR-017**: A `ProductReview` model MUST link to `Product` and `User` and include: `rating` (integer 1-5), `title`, `body`, `is_approved` (boolean, default False), and timestamp fields.
- **FR-018**: A `ProductVariant` model MUST link to `Product` and include: `name` (e.g., "Size M / Blue"), `sku` (unique), `price_adjustment` (decimal, can be negative), `stock_quantity`, and `is_active`.
- **FR-019**: The `ProductVariant` MUST expose a `final_price` computed property returning `product.price + price_adjustment`.

#### Orders App

- **FR-020**: A `Cart` model MUST support both authenticated users (via nullable `OneToOneField` to `User`) and anonymous visitors (via `session_key` CharField). Exactly one of `user` or `session_key` SHOULD be populated at any time.
- **FR-021**: A `CartItem` model MUST link to `Cart`, `Product`, and optionally `ProductVariant`, with a `quantity` field (minimum 1). A unique constraint MUST prevent duplicate entries for the same cart + product + variant combination, including the null-variant case.
- **FR-022**: `CartItem` MUST expose `unit_price` (returns variant `final_price` if variant is set, else `product.price`) and `line_total` / `total_price` (unit_price x quantity) as computed properties.
- **FR-023**: `Cart` MUST expose `total_items` (sum of all item quantities) and `total_price` (sum of all `CartItem.total_price`) as computed properties, using prefetch caches when available to avoid N+1 queries.
- **FR-024**: An `Order` model MUST include: `order_number` (auto-generated, unique, non-editable), `user` FK (nullable for guest checkout), `status` (choices: pending, confirmed, processing, shipped, delivered, cancelled, refunded), `subtotal`, `tax_amount`, `shipping_cost`, `discount_amount`, `total_amount` (all decimals with minimum 0 validators), and embedded billing and shipping address fields.
- **FR-025**: An `OrderItem` model MUST link to `Order`, `Product`, and optionally `ProductVariant`, and include: `quantity`, `unit_price` (snapshot at time of purchase), and `line_total` (quantity x unit_price).
- **FR-026**: A `Payment` model MUST link to `Order` via `OneToOneField` and include: `payment_method` (choice field), `transaction_id` (optional), `amount`, `status` (pending/paid/failed/refunded), and `paid_at` (nullable datetime).

#### Database Optimization

- **FR-027**: Database indexes MUST be defined (via `Meta.indexes`) on: `Product.slug`, `Product.sku`, `Product.category + created_at`, `Category.slug`, `Order.order_number`, `Order.user`, `Order.status`, and `CartItem.cart + created_at`.
- **FR-028**: Unique constraints MUST be enforced at the database level for: `Product.slug`, `Product.sku`, `Category.slug`, `Category.name`, `Order.order_number`, and `ProductVariant.sku`.

#### Admin Interface

- **FR-029**: All models MUST be registered with `ModelAdmin` subclasses. Each admin class MUST configure `list_display`, `search_fields`, `list_filter`, and `readonly_fields` (at minimum `created_at`, `updated_at`).
- **FR-030**: `ProductAdmin` MUST support inline editing of `ProductImage` and `ProductVariant` records from the product change page.
- **FR-031**: `OrderAdmin` MUST support inline viewing of `OrderItem` records and display order totals in `list_display`.

#### Migrations & Fixtures

- **FR-032**: Initial migrations MUST be generated for all four apps (`core`, `accounts`, `products`, `orders`) and MUST apply cleanly on both SQLite (dev) and PostgreSQL (production) with `python manage.py migrate`.
- **FR-033**: A dev seed fixture MUST be loadable via `python manage.py loaddata dev_seed` and MUST create: at least 3 `Category` records (including one nested child category), at least 10 `Product` records with images, and at least 1 superuser.

#### Testing

- **FR-034**: Unit tests MUST cover every model's `__str__` representation, all computed properties, all custom `save()` logic (e.g., slug auto-generation), and all signal handlers.
- **FR-035**: Tests MUST be organized in `tests/test_products.py`, `tests/test_orders.py`, and `tests/test_accounts.py`.
- **FR-036**: All test data MUST be created using `factory-boy` factories (one factory per model, defined in `tests/factories.py`).
- **FR-037**: Overall test coverage MUST be >= 95% as measured by `pytest-cov` against the four application modules.

### Key Entities

- **UserProfile**: Extended data for a registered user (contact info, avatar, bio). One-to-one with Django's `User`.
- **Address**: A physical address record (shipping or billing) associated with a user. A user may have multiple addresses.
- **Category**: Product taxonomy node. Hierarchical (parent/child). Identified by slug.
- **Product**: The primary sellable item. Has pricing, inventory, SEO metadata, and variants. Central entity referenced by cart and order items.
- **ProductImage**: One of potentially many images for a product; one is designated primary.
- **ProductVariant**: A purchasable variation of a product (size, color, etc.) with its own SKU and price modifier.
- **ProductReview**: A moderated customer review (1-5 stars) for a product.
- **Cart**: A temporary container for items a user intends to purchase. Can be anonymous (session) or authenticated.
- **CartItem**: A single line in a cart: product (+ optional variant) at a quantity.
- **Order**: A completed or in-progress purchase. Immutably records the customer's address data and totals at the time of purchase.
- **OrderItem**: A snapshot of a purchased product line (price is captured at purchase time, not live).
- **Payment**: The payment record associated one-to-one with an order.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: A developer can go from `git clone` to a running local environment with seed data in under 5 minutes using only documented commands.
- **SC-002**: The full model test suite runs to completion in under 60 seconds on a standard developer laptop.
- **SC-003**: Test coverage across all four application modules is >= 95% with no untested model methods or properties.
- **SC-004**: All 7 pre-commit gates pass on the initial codebase without any manually allowed violations.
- **SC-005**: All database migrations apply cleanly (zero errors) on both SQLite and PostgreSQL from a fresh database.
- **SC-006**: The Django admin interface is accessible for all 12 models with search, filtering, and inline editing configured — verified by a developer in under 10 minutes of review.
- **SC-007**: No secrets (secret key, database credentials, API tokens) are present in any committed file; `git log --all -p | grep SECRET_KEY` returns no results.
- **SC-008**: `python manage.py check --deploy` produces zero critical warnings when run with production settings.

## Assumptions

- Django's built-in `User` model is used (not a swapped custom user model), and `UserProfile` provides extension via OneToOne. This must be decided before generating `0001_initial` migrations as it cannot be changed after that.
- Image storage uses the local filesystem (`MEDIA_ROOT`) in development. Cloud storage integration is deferred to a later infrastructure epic.
- Tax calculation logic is deferred. The `tax_amount` field stores a pre-computed value; calculation rules are out of scope for this epic.
- Shipping carrier integration is deferred. `shipping_cost` stores the final amount; carrier selection is out of scope.
- Guest checkout is supported at the model level (nullable `user` FK on `Order`), but the checkout flow is implemented in a later epic.
- The `Order` model uses embedded (denormalized) address fields rather than a FK to `accounts.Address` so that order history is immutable even if the user later changes their address.
- `python-decouple` is used for environment configuration (not `django-environ`).
- PostgreSQL 15 is the target production database; SQLite 3.35+ is used for development and CI.
- Factory Boy version >= 3.3 is used for test data; model factories live in `tests/factories.py`.

## Out of Scope

- Authentication views, login/logout/registration endpoints (Epic 2)
- Product listing and detail views (Epic 3)
- Shopping cart views and session merging logic (Epic 4)
- Checkout flow and order creation views (Epic 5)
- Payment gateway integration (Epic 6)
- Email notifications (Epic 7)
- Search functionality (Epic 8)
- Celery / async task queue setup (Epic 9)
- Deployment infrastructure, CI/CD pipelines, cloud provisioning (Epic 10)
- Front-end templates or static asset pipeline (Epic 11)
