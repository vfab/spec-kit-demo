# Implementation Plan: Database Models & Infrastructure (ShopHub Epic 1)

**Branch**: `001-database-models-infrastructure` | **Date**: 2026-03-20 | **Spec**: [spec.md](spec.md)
**Input**: Feature specification from `/specs/001-database-models-infrastructure/spec.md`

---

## Summary

Epic 1 establishes the complete data layer for ShopHub: the abstract `BaseModel` (UUID PK, timestamps),
four Django apps (`core`, `accounts`, `products`, `orders`), 12 database models, their migrations,
admin registrations, a dev seed fixture, and the full project scaffold (settings split, Docker,
pre-commit gates, test infrastructure). Every other epic depends on these stable, indexed, tested
models being in place before any view, form, or API code is written.

---

## Technical Context

**Language/Version**: Python 3.12
**Primary Dependencies**:
- Django 5.2.x
- python-decouple (env config)
- Pillow (image processing)
- psycopg2-binary (PostgreSQL adapter)
- dj-database-url (DATABASE_URL parsing)
- django-axes (brute-force protection — registered early to avoid migration issues)
- factory-boy ≥ 3.3 (test data factories)
- faker (realistic test data)
- pytest-django (Django test runner integration)
- pytest-cov (coverage measurement)
- black (formatter, 88-char line length)
- isort (import sorter, black-compatible profile)
- flake8 (linter, max-line=88, ignore E203/W503)
- mypy + django-stubs (type checking, strict_optional=True)
- bandit (SAST, -ll threshold)
- pip-audit (CVE scanning)

**Storage**: SQLite 3.35+ (dev/CI via `DATABASE_URL=sqlite:///db.sqlite3`) / PostgreSQL 15 (prod)
**Testing**: pytest + pytest-django + pytest-cov; `DJANGO_SETTINGS_MODULE=ecommerce_site.settings_test`
**Target Platform**: Linux server / Docker (Dockerfile + docker-compose.yml)
**Project Type**: web-service
**Performance Goals**: ≤200ms p95 on model queries; all FK and slug fields carry explicit DB indexes
**Constraints**: Coverage ≥ 95%; all 7 pre-commit gate commands exit 0 before any commit

---

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-checked after Phase 1 design.*

| Principle | How Epic 1 Satisfies It |
|-----------|------------------------|
| **I. Documentation-First** | `plan.md`, `data-model.md`, `quickstart.md`, and `/contracts/` are committed in the same PR as the model code; `EPIC-01.md` checkbox `[x]` is updated per task completion. |
| **II. Test-First** | Every model method, computed property, signal handler, and `save()` override has a corresponding factory-boy unit test in `tests/` before the model is considered done; 100% test pass rate is enforced by pre-commit. |
| **III. Coverage Enforcement** | `pytest-cov` gates at ≥ 95%; `.coveragerc` omits only `migrations/` and `manage.py`; pre-commit runs `pytest --cov` and fails if the threshold drops. |
| **IV. Environment-Driven Configuration** | All secrets and runtime config (SECRET_KEY, DATABASE_URL, DEBUG, ALLOWED_HOSTS) come from `python-decouple`; `.env` is gitignored; `.env.example` is the only committed env file; `python manage.py check --deploy` produces zero critical warnings in production settings. |
| **V. Incremental, Branch-Based Development** | All work is on branch `001-database-models-infrastructure`; each phase is a discrete, validated commit referencing `EPIC-1` in the message; main branch receives only fully-passing code. |

---

## Project Structure

### Documentation (this feature)

```text
specs/001-database-models-infrastructure/
├── plan.md              ← this file
├── research.md          ← Phase 0 output
├── data-model.md        ← Phase 1 output (entity fields, relationships, constraints)
├── quickstart.md        ← Phase 1 output (clone-to-running steps)
├── contracts/           ← Phase 1 output (admin interface and model API contracts)
└── tasks.md             ← Phase 2 output (/speckit.tasks — NOT created by /speckit.plan)
```

### Source Code (repository root)

```text
ecommerce_site/
├── __init__.py
├── settings.py            # Base settings (python-decouple, dj-database-url, django-axes)
├── settings_test.py       # Test overrides: SQLite in-memory, dummy cache, axes disabled
├── urls.py                # Root URL config (admin only for this epic)
├── wsgi.py
└── asgi.py

core/
├── __init__.py
├── apps.py
├── models.py              # Abstract BaseModel (UUID PK, created_at, updated_at)
└── migrations/
    └── __init__.py        # core has no concrete tables; empty migrations package

accounts/
├── __init__.py
├── apps.py
├── models.py              # UserProfile (OneToOne User), Address
├── admin.py               # UserProfileAdmin, AddressAdmin
└── migrations/
    ├── __init__.py
    └── 0001_initial.py

products/
├── __init__.py
├── apps.py
├── models.py              # Category, Product, ProductImage, ProductVariant, ProductReview
├── admin.py               # CategoryAdmin, ProductAdmin (inline images+variants), ReviewAdmin
└── migrations/
    ├── __init__.py
    └── 0001_initial.py

orders/
├── __init__.py
├── apps.py
├── models.py              # Cart, CartItem, Order, OrderItem, Payment
├── admin.py               # CartAdmin, OrderAdmin (inline items), PaymentAdmin
└── migrations/
    ├── __init__.py
    └── 0001_initial.py

tests/
├── __init__.py
├── conftest.py            # Shared pytest fixtures (django_db, factory instances)
├── factories.py           # factory-boy factories for all 12 models
├── test_accounts.py       # UserProfile, Address unit tests
├── test_products.py       # Category, Product, ProductImage, ProductVariant, ProductReview
└── test_orders.py         # Cart, CartItem, Order, OrderItem, Payment

manage.py
pyproject.toml             # black + isort config ([tool.black], [tool.isort])
pytest.ini                 # DJANGO_SETTINGS_MODULE, testpaths, addopts
mypy.ini                   # plugins = mypy_django_plugin.main, strict_optional = True
.flake8                    # max-line-length = 88, extend-ignore = E203,W503, exclude = migrations,.venv
.coveragerc                # source = accounts,products,orders,core; omit = */migrations/*
.bandit                    # [bandit] skips = B101 (assert in tests)
.pre-commit-config.yaml    # black, isort, flake8, mypy, bandit, pytest, pip-audit hooks
.gitignore                 # .env, *.pyc, __pycache__, media/, staticfiles/, db.sqlite3
.env.example               # DATABASE_URL, SECRET_KEY, DEBUG, ALLOWED_HOSTS stubs
.env.development           # Committed dev defaults (SQLite, DEBUG=True, insecure dev key)
docker-compose.yml         # web (Django) + db (postgres:15) services
Dockerfile                 # python:3.12-slim, non-root user, gunicorn entrypoint
requirements.txt           # Pinned production + dev dependencies
```

---

## Implementation Phases

### Phase 0 — Project Scaffolding

**Goal**: A runnable Django project with correct settings split, Docker, pre-commit, and env files.

Tasks:
1. `django-admin startproject ecommerce_site .` at repo root
2. Replace generated `settings.py` with the python-decouple pattern (SECRET_KEY, DEBUG, ALLOWED_HOSTS, DATABASES via dj-database-url, INSTALLED_APPS includes `axes`)
3. Create `settings_test.py`: overrides DATABASE to `sqlite:///:memory:`, disables axes (`AXES_ENABLED=False`), uses `django.core.cache.backends.dummy.DummyCache`
4. Create `pytest.ini` pointing at `ecommerce_site.settings_test`
5. Create `pyproject.toml` with `[tool.black]` (line-length=88) and `[tool.isort]` (profile=black)
6. Create `mypy.ini`, `.flake8`, `.coveragerc`, `.bandit`
7. Create `.pre-commit-config.yaml` with all 7 gates
8. Create `Dockerfile` (python:3.12-slim, WORKDIR /app, non-root user, `gunicorn ecommerce_site.wsgi`)
9. Create `docker-compose.yml` (web + db:postgres:15, mounts .env.development, depends_on db healthcheck)
10. Create `.env.example`, `.env.development` (SQLite, DEBUG=True, dev SECRET_KEY)
11. Add `.gitignore` excluding `.env`, `*.pyc`, `__pycache__`, `media/`, `staticfiles/`, `db.sqlite3`
12. Verify: `python manage.py check` exits 0

**Commit**: `feat: project scaffold — settings split, docker, pre-commit (EPIC-1, Phase 0)`

---

### Phase 1 — `core/` App: Abstract BaseModel

**Goal**: Shared abstract base that all application models inherit from.

```python
# core/models.py
import uuid
from django.db import models

class BaseModel(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True
        ordering = ["-created_at"]
```

Tasks:
1. `python manage.py startapp core` → add `"core"` to `INSTALLED_APPS`
2. Write `core/models.py` with `BaseModel` (abstract, UUID PK, timestamps, default ordering)
3. `core` has no concrete tables — `migrations/` stays as an empty package with `__init__.py`
4. Write `tests/test_core.py` (minimal: confirm BaseModel fields via a concrete subclass in tests only)

**Commit**: `feat: core app — abstract BaseModel UUID pk and timestamps (EPIC-1, Phase 1)`

---

### Phase 2 — `accounts/` App: UserProfile, Address

**Goal**: Extended user data and address records; post_save signal auto-creates UserProfile.

Models:
- **UserProfile** (inherits `BaseModel`): `OneToOneField(User)`, `phone` (RegexValidator), `date_of_birth`, `bio`, `avatar` (ImageField with upload_to)
- **Address** (inherits `BaseModel`): `ForeignKey(User)`, `address_line_1`, `address_line_2`, `city`, `state`, `country`, `postal_code`, `is_default (bool)`, `address_type` (choices: `shipping`/`billing`)

Signal:
```python
@receiver(post_save, sender=User)
def create_user_profile(sender, instance, created, **kwargs):
    if created:
        UserProfile.objects.create(user=instance)
```

Constraints:
- `Address.is_default` uniqueness per `(user, address_type)` is documented in the admin; enforced at application layer in save() (set all others to False before setting new default)

Tasks:
1. `python manage.py startapp accounts` → register in `INSTALLED_APPS`
2. Write `accounts/models.py` with UserProfile + Address + post_save signal
3. Write `accounts/admin.py` (UserProfileAdmin, AddressAdmin — `list_display`, `search_fields`, `list_filter`, `readonly_fields`)
4. Write `tests/factories.py` — `UserFactory`, `UserProfileFactory`, `AddressFactory`
5. Write `tests/test_accounts.py` — `__str__`, signal auto-creation, address type choices, phone validation
6. Run migrations: `python manage.py makemigrations accounts`

**Commit**: `feat: accounts app — UserProfile, Address, post_save signal (EPIC-1, Phase 2)`

---

### Phase 3 — `products/` App: Category, Product, Images, Variants, Reviews

**Goal**: Full product catalog data layer.

Models:
- **Category** (inherits `BaseModel`): `name`, `slug` (auto from name if blank), `description`, `is_active`, `parent` (self-FK, `null=True, blank=True, related_name='children'`)
- **Product** (inherits `BaseModel`): `name`, `slug` (auto, unique), `description`, `short_description`, `category` (FK), `price`, `sale_price`, `compare_price`, `sku` (unique), `stock_quantity`, `is_active`, `is_featured`, `weight`, `meta_title`, `meta_description`; computed: `is_in_stock`, `is_on_sale`, `discount_percentage`
- **ProductImage** (inherits `BaseModel`): FK Product, `image` (FileExtensionValidator + SizeValidator), `alt_text`, `position`, `is_primary`
- **ProductVariant** (inherits `BaseModel`): FK Product, `name`, `sku` (unique), `price_adjustment`, `stock_quantity`, `is_active`; computed: `final_price`
- **ProductReview** (inherits `BaseModel`): FK Product + FK User, `rating` (1-5 validator), `title`, `body`, `is_approved`

Slug auto-generation pattern (same for Category and Product):
```python
from django.utils.text import slugify

def save(self, *args, **kwargs):
    if not self.slug:
        self.slug = slugify(self.name)
    super().save(*args, **kwargs)
```

Tasks:
1. `python manage.py startapp products` → register in `INSTALLED_APPS`
2. Write `products/models.py` with all 5 models
3. Write `products/admin.py` — `ProductAdmin` with `ProductImageInline` and `ProductVariantInline`
4. Extend `tests/factories.py` — CategoryFactory, ProductFactory, ProductImageFactory, ProductVariantFactory, ProductReviewFactory
5. Write `tests/test_products.py` — all `__str__`, slug auto-gen, computed properties, image validators
6. `python manage.py makemigrations products`

**Commit**: `feat: products app — Category, Product, Image, Variant, Review models (EPIC-1, Phase 3)`

---

### Phase 4 — `orders/` App: Cart, Order, Payment

**Goal**: Shopping cart and order data layer with price snapshots.

Models:
- **Cart** (inherits `BaseModel`): `OneToOneField(User, null=True)`, `session_key (CharField, null=True)`; computed: `total_items`, `total_price` (prefetch-cache-aware)
- **CartItem** (inherits `BaseModel`): FK Cart, FK Product, FK ProductVariant (null), `quantity` (MinValueValidator(1)); unique constraints for cart+product+variant (including null-variant case via `UniqueConstraint` with `Q(variant__isnull=True)`); computed: `unit_price`, `line_total`/`total_price`
- **Order** (inherits `BaseModel`): `order_number` (auto-generated in `save()`, unique, editable=False), `user` FK (null), `status` (choices), `subtotal`, `tax_amount`, `shipping_cost`, `discount_amount`, `total_amount` (all DecimalField, MinValueValidator(0)), embedded billing + shipping address fields (denormalized, snapshot at purchase)
- **OrderItem** (inherits `BaseModel`): FK Order, FK Product, FK ProductVariant (null), `unit_price` (snapshot), `line_total`, product/variant name snapshots captured in `save()`
- **Payment** (inherits `BaseModel`): `OneToOneField(Order)`, `payment_method` (choices), `transaction_id` (null), `amount`, `status` (pending/paid/failed/refunded), `paid_at` (null datetime)

Order number generation (from reference implementation):
```python
def generate_order_number(self):
    now = datetime.datetime.now()
    return f"ORD-{now.strftime('%Y%m%d')}-{uuid.uuid4().hex[:8].upper()}"
```

Tasks:
1. `python manage.py startapp orders` → register in `INSTALLED_APPS`
2. Write `orders/models.py`
3. Write `orders/admin.py` — `OrderAdmin` with `OrderItemInline`, `PaymentAdmin`
4. Extend `tests/factories.py` — CartFactory, CartItemFactory, OrderFactory, OrderItemFactory, PaymentFactory
5. Write `tests/test_orders.py` — all `__str__`, order number generation, price computations, unique cart constraint, payment status
6. `python manage.py makemigrations orders`

**Commit**: `feat: orders app — Cart, CartItem, Order, OrderItem, Payment models (EPIC-1, Phase 4)`

---

### Phase 5 — Database Optimization: Indexes and Unique Constraints

**Goal**: All performance-critical fields carry explicit `Meta.indexes` and `Meta.constraints`.

Index checklist (FR-027):
| Model | Index Fields |
|-------|-------------|
| `Product` | `slug`, `sku`, `(category, -created_at)` |
| `Category` | `slug` |
| `Order` | `order_number`, `user`, `status` |
| `CartItem` | `(cart, -created_at)` |

Unique constraint checklist (FR-028):
| Model | Unique Field(s) |
|-------|----------------|
| `Product` | `slug`, `sku` |
| `Category` | `slug`, `name` |
| `Order` | `order_number` |
| `ProductVariant` | `sku` |

Tasks:
1. Add `Meta.indexes` and `Meta.constraints` to all applicable models
2. `python manage.py makemigrations --name=add_indexes_and_constraints` (one migration per app, or squash into initial)
3. Verify migration applies cleanly on both SQLite (`python manage.py migrate`) and a Postgres container (`docker-compose run db`)

**Commit**: `feat: db indexes and unique constraints on slug/sku/order_number fields (EPIC-1, Phase 5)`

---

### Phase 6 — Django Admin

**Goal**: All 12 models are admin-registered with search, filtering, and inline editing.

| Admin Class | list_display | search_fields | list_filter | Inlines |
|-------------|-------------|--------------|-------------|---------|
| `UserProfileAdmin` | username, email, phone, created_at | username, email, phone | date_joined | — |
| `AddressAdmin` | user, city, country, address_type, is_default | user__username, city | address_type, country | — |
| `CategoryAdmin` | name, slug, parent, is_active | name, slug | is_active, parent | — |
| `ProductAdmin` | name, sku, price, stock_quantity, is_active, is_featured | name, sku, description | category, is_active, is_featured | ProductImageInline, ProductVariantInline |
| `ProductImageAdmin` | product, position, is_primary | product__name | is_primary | — |
| `ProductVariantAdmin` | product, name, sku, stock_quantity, is_active | name, sku | is_active | — |
| `ProductReviewAdmin` | product, user, rating, is_approved, created_at | title, body, user__username | rating, is_approved | — |
| `CartAdmin` | user, session_key, total_items, total_price, created_at | user__username, session_key | — | CartItemInline |
| `CartItemAdmin` | cart, product, variant, quantity, line_total | product__name | — | — |
| `OrderAdmin` | order_number, user, status, total_amount, created_at | order_number, user__username | status | OrderItemInline |
| `OrderItemAdmin` | order, product_name, quantity, unit_price, line_total | product_name, product_sku | — | — |
| `PaymentAdmin` | order, payment_method, amount, status, paid_at | order__order_number, transaction_id | status, payment_method | — |

All admin classes set `readonly_fields = ("created_at", "updated_at")` at minimum.

Tasks:
1. Write `accounts/admin.py`, `products/admin.py`, `orders/admin.py` with all classes above
2. Verify admin loads without errors: `python manage.py check` + manual spot-check at `/admin/`

**Commit**: `feat: admin registrations for all 12 models with search/filter/inlines (EPIC-1, Phase 6)`

---

### Phase 7 — Migrations, Seed Fixture, Tests, Pre-commit Gate

**Goal**: All four apps have clean initial migrations; a dev seed fixture is loadable; test suite hits ≥ 95% coverage; all 7 pre-commit gates exit 0.

Migrations:
- All 4 apps have `0001_initial.py` generated
- `python manage.py migrate` succeeds on SQLite (dev) and postgres:15 (docker-compose)
- `python manage.py migrate --run-syncdb` should be clean

Dev seed fixture (`fixtures/dev_seed.json`):
- 1 superuser (`admin` / locally-set password)
- 3 Category records: Electronics, Computers (child of Electronics), Clothing
- 10 Product records with at least 1 ProductImage each
- Load command: `python manage.py loaddata dev_seed`

Test suite completeness checklist:
- `tests/conftest.py`: `@pytest.fixture` for `django_db`, `user_factory`, `product_factory`
- `tests/factories.py`: one Factory per model (12 total)
- `tests/test_accounts.py`: UserProfile auto-create signal, `__str__`, phone validator, Address.is_default logic
- `tests/test_products.py`: Category slug auto-gen, Product computed props (`is_in_stock`, `is_on_sale`, `discount_percentage`), ProductVariant `final_price`, ProductImage extension validator, ProductReview `__str__`
- `tests/test_orders.py`: Cart `total_price` prefetch path + N+1 guard, CartItem unique constraint, Order `order_number` uniqueness + format, OrderItem price snapshot, Payment status transitions

Pre-commit gate validation:
```bash
python manage.py check                                           # 0 errors
python -m pytest tests/ --tb=short                              # 100% pass
flake8 . --max-line-length=88 --extend-ignore=E203,W503 --exclude=migrations,.venv
mypy accounts orders products ecommerce_site core               # 0 errors
bandit -r accounts core orders products ecommerce_site -ll      # 0 medium/high
pip-audit -r requirements.txt                                   # 0 known CVEs
pre-commit run --all-files                                      # all hooks exit 0
```

**Commit**: `feat: migrations, dev seed fixture, full test suite, pre-commit gates pass (EPIC-1, Phase 7)`

---

## Research Notes

Key patterns from the reference implementation (`/mnt/c/src/copilot-plan-agent-build/`):

### BaseModel UUID Primary Key
The reference `core/models.py` does not exist yet in the reference repo (the `core/` app only has `validators.py`). The pattern to implement is standard Django abstract model with `uuid.uuid4` as the default — no custom manager boilerplate needed for Epic 1.

### Session-Key + User FK Dual-Mode Cart
From `orders/models.py` (reference): `Cart` uses `OneToOneField(User, null=True)` and `session_key = CharField(max_length=40, null=True)`. The `total_price` and `total_items` properties check `self._prefetched_objects_cache` before hitting the database — **this pattern must be preserved exactly** to avoid N+1 queries on cart page loads.

### Order Number Generation
From `orders/models.py` (reference): order numbers are generated in `save()` using a timestamp + short UUID hex:
```python
f"ORD-{now.strftime('%Y%m%d')}-{uuid.uuid4().hex[:8].upper()}"
# → e.g. "ORD-20260320-A3F7B2C1"
```
Collision probability is negligible for expected order volumes; the `unique=True` constraint plus application-layer retry on `IntegrityError` is the safety net.

### `settings_test.py` Pattern for Test Isolation
`settings_test.py` must:
- Set `DATABASES = {"default": {"ENGINE": "django.db.backends.sqlite3", "NAME": ":memory:"}}`
- Set `AXES_ENABLED = False` (django-axes requires this to avoid lockout during test runs)
- Use `django.core.cache.backends.dummy.DummyCache`
- Set `PASSWORD_HASHERS = ["django.contrib.auth.hashers.MD5PasswordHasher"]` for faster test runs
- Set `MEDIA_ROOT` to a temp directory

### `.env.development` / `.env.production` Split
`.env.development` is committed (safe dev values only — no real secrets):
```
DATABASE_URL=sqlite:///db.sqlite3
DEBUG=True
SECRET_KEY=dev-only-insecure-secret-key-change-in-production
ALLOWED_HOSTS=localhost,127.0.0.1
```
`.env.production` is never committed. `.env.example` documents every variable.

### OrderItem Price Snapshot
From reference `orders/models.py`: `OrderItem.save()` captures `product.name`, `product.sku`, and variant details at purchase time using existence guards (`if not self.product_name`). This ensures historical order accuracy even after product edits.

---

## Quickstart

```bash
# 1. Clone the repository
git clone <repo-url> shophub && cd shophub

# 2. Check out the feature branch
git checkout 001-database-models-infrastructure

# 3. Copy dev environment file
cp .env.development .env

# 4. Start with Docker (preferred — includes Postgres)
docker-compose up --build -d

# 5. Apply migrations
docker-compose exec web python manage.py migrate

# 6. Load seed data
docker-compose exec web python manage.py loaddata dev_seed

# 7. Verify admin is accessible
# → open http://localhost:8000/admin/ (superuser: admin / see seed fixture)

# --- OR: Local Python environment (SQLite) ---

# 3b. Create and activate a virtual environment
python3.12 -m venv .venv && source .venv/bin/activate

# 4b. Install dependencies
pip install -r requirements.txt

# 5b. Copy dev environment file
cp .env.development .env

# 6b. Apply migrations
python manage.py migrate

# 7b. Load seed data
python manage.py loaddata dev_seed

# 8. Run the full test suite
pytest tests/ -q

# Expected output:
#   NN passed in X.XXs  (coverage >= 95%)

# 9. Run pre-commit gates (all must exit 0)
pre-commit run --all-files
```

---

## Open Questions

| Question | Recommendation | Rationale |
|----------|---------------|-----------|
| **UUID vs integer PKs** | Use UUID (`uuid4`, `editable=False`) | Already established in the reference codebase; avoids sequential PK enumeration (IDOR risk); enables offline record creation; no migration complexity penalty at project start. |
| **Custom User model vs `UserProfile` OneToOne** | Use `UserProfile` OneToOne extending Django's built-in `User` | The spec explicitly states this decision must be made before `0001_initial` migrations — and it was: the assumption is documented in `spec.md`. Swapping to a custom User model after initial migrations is a destructive migration operation. `UserProfile` OneToOne adds no extra dependencies and is sufficient for all 11 epics. |
| **Self-referential `Category` vs django-mptt** | Use self-referential FK (`parent = ForeignKey('self', null=True)`) | The spec requires only two-level hierarchy for seed data and catalog browsing. django-mptt adds a dependency, migration complexity, and rebuild commands. Self-referential FK handles unlimited depth with a simple `category.children.all()` API and is sufficient for all planned epics. |

---

## Complexity Tracking

No constitution violations. All design choices are the simplest option that satisfies the requirements:
- 4 apps (not 5+): `core`, `accounts`, `products`, `orders` — no artificial splitting
- No Repository pattern: direct ORM access throughout
- No service layer: computed properties on models only
- No Celery/async: all DB operations are synchronous and fast (≤200ms p95 target is easily met with proper indexes)
