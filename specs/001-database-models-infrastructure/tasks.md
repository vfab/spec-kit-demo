---
description: "Task list for Epic 1 — Database Models & Infrastructure (ShopHub)"
---

# Tasks: Database Models & Infrastructure (ShopHub Epic 1)

**Input**: Design documents from `/specs/001-database-models-infrastructure/`
**Prerequisites**: [spec.md](spec.md) (required), [plan.md](plan.md) (required), [data-model.md](data-model.md) (required)
**Branch**: `001-database-models-infrastructure`
**Models**: 10 concrete models across 4 apps — UserProfile · Category · Product · ProductImage · ProductVariant · ProductReview · Cart · CartItem · Order · OrderItem

> **Note on primary keys**: `data-model.md` design decisions mandate **AutoField (integer auto-increment)** PKs throughout, explicitly overriding `spec.md` FR-007's UUID recommendation. Tasks below follow `data-model.md`. Resolve with tech lead before running `makemigrations` if UUID is preferred — it must be chosen before any `0001_initial` migrations are generated.

> **Note on deferred models**: `data-model.md` defers two spec models. **`Address`** (spec FR-011/FR-012) is inlined as fields on `UserProfile` and `Order`. **`Payment`** (spec FR-026) is deferred to Epic 4; `Order.payment_status` and `Order.payment_method` replace it in Epic 1.

---

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel with other [P] tasks in the same phase (touches different files)
- **[US#]**: User story from spec.md this task satisfies
- All file paths are relative to repository root

---

## Phase 0: Project infrastructure & configuration

**Purpose**: A runnable Django 5.2.x project with python-decouple settings, SQLite/Postgres split, Docker, pre-commit gates, and all dev tooling config files. No Epic 1 model work begins until this phase is complete.

**⚠️ CRITICAL**: All Phase 1–7 tasks depend on this phase. Do not proceed until the checkpoint passes.

- [ ] T001 [US1] [US4] Create `requirements.txt` with pinned versions for all runtime and dev dependencies: Django 5.2.x, python-decouple, dj-database-url, Pillow, psycopg2-binary, django-axes, factory-boy≥3.3, faker, pytest-django, pytest-cov, black, isort, flake8, mypy, django-stubs, bandit, pip-audit, gunicorn.
  - **File**: `requirements.txt`
  - **Acceptance**: `pip install -r requirements.txt` exits 0; `python -c "import django; print(django.__version__)"` prints a 5.2.x version string.
  - **Satisfies**: FR-001

- [ ] T002 [US1] Scaffold the Django project: run `django-admin startproject ecommerce_site .` at repository root to generate `ecommerce_site/__init__.py`, `ecommerce_site/settings.py`, `ecommerce_site/urls.py`, `ecommerce_site/wsgi.py`, `ecommerce_site/asgi.py`, and `manage.py`.
  - **File**: `manage.py`, `ecommerce_site/` (directory)
  - **Depends on**: T001
  - **Acceptance**: `python manage.py check` exits 0 with the generated default settings; `ecommerce_site/` directory exists with all five files.
  - **Satisfies**: FR-001

- [ ] T003 [US4] Replace the generated `ecommerce_site/settings.py` with a python-decouple base configuration: `SECRET_KEY = config('SECRET_KEY')`, `DEBUG = config('DEBUG', cast=bool, default=True)`, `ALLOWED_HOSTS = config('ALLOWED_HOSTS', default='localhost,127.0.0.1', cast=Csv())`, `DATABASES = {'default': dj_database_url.config(default='sqlite:///db.sqlite3')}`, `INSTALLED_APPS` includes `'axes'`; keep all other standard Django apps.
  - **File**: `ecommerce_site/settings.py`
  - **Depends on**: T002
  - **Acceptance**: `SECRET_KEY` is not a string literal in any `.py` file; `python manage.py check` exits 0 with `DATABASE_URL=sqlite:///db.sqlite3` in environment; `DATABASES` switches to Postgres when `DATABASE_URL` is set to a Postgres DSN without code changes.
  - **Satisfies**: FR-002, FR-003, US4 acceptance scenarios 1–2

- [ ] T004 [P] [US4] Create `ecommerce_site/settings_test.py` with test-only overrides: `DATABASES = {"default": {"ENGINE": "django.db.backends.sqlite3", "NAME": ":memory:"}}`, `AXES_ENABLED = False`, `CACHES = {"default": {"BACKEND": "django.core.cache.backends.dummy.DummyCache"}}`, `DEBUG = True`, `PASSWORD_HASHERS = ["django.contrib.auth.hashers.MD5PasswordHasher"]`.
  - **File**: `ecommerce_site/settings_test.py`
  - **Depends on**: T003
  - **Acceptance**: `DJANGO_SETTINGS_MODULE=ecommerce_site.settings_test python manage.py check` exits 0; tests run against in-memory SQLite (no file created at `db.sqlite3`).
  - **Satisfies**: FR-006

- [ ] T005 [P] [US3] Create `pytest.ini` at repository root: `DJANGO_SETTINGS_MODULE = ecommerce_site.settings_test`, `testpaths = tests`, `addopts = --tb=short --strict-markers`, `python_files = test_*.py`.
  - **File**: `pytest.ini`
  - **Depends on**: T004
  - **Acceptance**: `python -m pytest --collect-only` discovers files in `tests/` without `ModuleNotFoundError`; exit code 0 even when `tests/` is empty.
  - **Satisfies**: FR-006

- [ ] T006 [P] [US3] Create `pyproject.toml` with `[tool.black]` (`line-length = 88`, `target-version = ["py312"]`) and `[tool.isort]` (`profile = "black"`, `known_third_party = ["django", "decouple", "factory"]`).
  - **File**: `pyproject.toml`
  - **Acceptance**: `black --check .` and `isort --check-only .` both exit 0 on the project files generated so far.
  - **Satisfies**: FR-005

- [ ] T007 [P] [US3] Create `mypy.ini` at repository root: `[mypy]` section with `plugins = mypy_django_plugin.main`, `strict_optional = True`, `ignore_missing_imports = True`, `warn_unused_ignores = True`; `[mypy.plugins.django-stubs]` section with `django_settings_module = ecommerce_site.settings_test`.
  - **File**: `mypy.ini`
  - **Acceptance**: `mypy ecommerce_site` exits 0 on the generated project skeleton; no "cannot find implementation" errors for Django imports.
  - **Satisfies**: FR-006

- [ ] T008 [P] [US3] Create `.flake8` config: `[flake8]` section with `max-line-length = 88`, `extend-ignore = E203,W503`, `exclude = migrations,.venv,__pycache__,staticfiles`.
  - **File**: `.flake8`
  - **Acceptance**: `flake8 .` exits 0 on the generated project skeleton.
  - **Satisfies**: FR-005, FR-006

- [ ] T009 [P] [US3] Create `.coveragerc`: `[run]` with `source = accounts,products,orders,core`; `[report]` with `omit = */migrations/*,manage.py`, `fail_under = 95`; `[html]` with `directory = htmlcov`.
  - **File**: `.coveragerc`
  - **Acceptance**: `pytest --cov --cov-report=term-missing` reads this config without errors; `fail_under = 95` is active in the config.
  - **Satisfies**: FR-006 (coverage config), constitution §III

- [ ] T010 [P] [US3] Create `.bandit` config: `[bandit]` section with `skips = B101` (assert in tests is acceptable).
  - **File**: `.bandit`
  - **Acceptance**: `bandit -r . -ll --ini .bandit` exits 0 on the generated skeleton with no medium/high findings.
  - **Satisfies**: FR-006

- [ ] T011 [US3] Create `.pre-commit-config.yaml` with all 7 gates as hooks: `black` (repo: psf/black), `isort` (repo: pycqa/isort), `flake8` (repo: pycqa/flake8), and four local hooks — `mypy accounts orders products ecommerce_site core`, `bandit -r accounts core orders products ecommerce_site -ll`, `pytest tests/ --cov --cov-fail-under=95 --tb=short`, `pip-audit -r requirements.txt`.
  - **File**: `.pre-commit-config.yaml`
  - **Depends on**: T006, T007, T008, T010
  - **Acceptance**: `pre-commit install` exits 0; `pre-commit run black --all-files` passes on current files; all 7 hook IDs are present in the YAML.
  - **Satisfies**: FR-005, US3 acceptance scenario 1

- [ ] T012 [P] [US1] Create `Dockerfile`: base `python:3.12-slim`, `WORKDIR /app`, copy and install `requirements.txt` (`pip install --no-cache-dir -r requirements.txt`), copy project files, create non-root user `appuser` (`adduser --disabled-password appuser`), `USER appuser`, `EXPOSE 8000`, `CMD ["gunicorn", "ecommerce_site.wsgi:application", "--bind", "0.0.0.0:8000", "--workers", "2"]`.
  - **File**: `Dockerfile`
  - **Depends on**: T001
  - **Acceptance**: `docker build -t shophub .` exits 0; `docker run --rm -e DATABASE_URL=sqlite:///tmp/db.sqlite3 -e SECRET_KEY=x shophub python manage.py check` exits 0.
  - **Satisfies**: FR-004

- [ ] T013 [US1] Create `docker-compose.yml` with services `db` (`image: postgres:15`, `POSTGRES_DB/USER/PASSWORD` from env, healthcheck on `pg_isready`) and `web` (`build: .`, `env_file: .env.development`, `depends_on: db: condition: service_healthy`, `ports: "8000:8000"`, `volumes: .:/app`).
  - **File**: `docker-compose.yml`
  - **Depends on**: T012
  - **Acceptance**: `docker-compose up --build -d` starts both containers; `docker-compose exec web python manage.py check` exits 0 (US1 acceptance scenario 1).
  - **Satisfies**: FR-004, US1 scenario 1

- [ ] T014 [P] [US4] Create environment and ignore files: (a) `.env.example` with commented stubs for `DATABASE_URL`, `SECRET_KEY`, `DEBUG`, `ALLOWED_HOSTS`; (b) `.env.development` with `DATABASE_URL=sqlite:///db.sqlite3`, `DEBUG=True`, `SECRET_KEY=dev-only-insecure-secret-key-change-in-production`, `ALLOWED_HOSTS=localhost,127.0.0.1`; (c) `.gitignore` excluding `.env`, `*.pyc`, `__pycache__/`, `media/`, `staticfiles/`, `db.sqlite3`, `.venv/`, `htmlcov/`, `.mypy_cache/`.
  - **Files**: `.env.example`, `.env.development`, `.gitignore`
  - **Acceptance**: `git status` does not show `.env` as untracked (it matches `.gitignore`); `.env.example` IS committed; running `cp .env.development .env && python manage.py check` exits 0 (US4 scenario 3).
  - **Satisfies**: FR-003, FR-005, US4 scenario 3

**Checkpoint**: `python manage.py check` exits 0 with `DATABASE_URL=sqlite:///db.sqlite3`. `docker-compose up --build` succeeds. `pre-commit install` succeeds. Phase 1 can now begin.

---

## Phase 1: Core app scaffolding (apps, settings, base model utilities)

**Purpose**: Create the `core/` app with the abstract `BaseModel` supplying shared timestamp fields inherited by all 10 application models.

- [ ] T015 [US2] Create the `core` Django app: run `python manage.py startapp core`, add `"core"` to `INSTALLED_APPS` in `ecommerce_site/settings.py`, create `core/migrations/__init__.py` (empty package — `core` has no concrete tables).
  - **Files**: `core/__init__.py`, `core/apps.py`, `core/migrations/__init__.py`; edit `ecommerce_site/settings.py`
  - **Depends on**: T003
  - **Acceptance**: `python manage.py check` exits 0; `from core.models import BaseModel` importable after T016 completes.
  - **Satisfies**: FR-007 prerequisite

- [ ] T016 [US2] Write `core/models.py` with abstract `BaseModel`: fields `created_at` (DateTimeField, auto_now_add=True) and `updated_at` (DateTimeField, auto_now=True); `class Meta: abstract = True; ordering = ["-created_at"]`. PKs for all concrete models use Django's default AutoField (integer auto-increment) per data-model.md design decisions — do NOT add a UUID `id` field here.
  - **File**: `core/models.py`
  - **Depends on**: T015
  - **Acceptance**: `BaseModel._meta.abstract is True`; a concrete test-only subclass saves to SQLite with `created_at` set automatically and `updated_at` updates on re-save; `BaseModel._meta.ordering == ["-created_at"]`.
  - **Satisfies**: FR-007, FR-008

- [ ] T017 [US2] Write `tests/test_core.py` (and create `tests/__init__.py`): define a concrete test-only subclass inside the test (`class _ConcreteModel(BaseModel): name = models.CharField(max_length=50); class Meta(BaseModel.Meta): app_label = "core"`); test: `created_at` is set on first save, `updated_at` changes after re-save, default ordering is `-created_at`, `_meta.abstract` on BaseModel is True.
  - **Files**: `tests/__init__.py`, `tests/test_core.py`
  - **Depends on**: T016
  - **Acceptance**: `pytest tests/test_core.py -v` passes all tests with `@pytest.mark.django_db`; no migration errors for the in-test concrete subclass.
  - **Satisfies**: FR-007, FR-034

**Checkpoint**: `BaseModel` is importable, abstract, and tested. All 10 application models will inherit it. Phase 2 can now begin.

---

## Phase 2: `products` app models

**Purpose**: Five product catalog models with slug auto-generation, computed properties, image validation/resizing, variant pricing, and review constraints.

- [ ] T018 [US2] Create the `products` Django app: run `python manage.py startapp products`, add `"products"` to `INSTALLED_APPS`, create `products/migrations/__init__.py`.
  - **Files**: `products/__init__.py`, `products/apps.py`, `products/migrations/__init__.py`; edit `ecommerce_site/settings.py`
  - **Depends on**: T016 (BaseModel must exist before models can inherit it)
  - **Acceptance**: `python manage.py check` exits 0; `from products import models` importable.
  - **Satisfies**: FR-013 prerequisite

- [ ] T019 [US2] Write the `Category` model in `products/models.py`: fields `id` (AutoField PK), `name` (CharField 200, unique), `slug` (SlugField 200, unique, blank=True — auto-populated from `name` in `save()` using `django.utils.text.slugify`), `description` (TextField, blank=True, null=True), `image` (ImageField upload_to='categories/', blank=True, null=True), `parent` (ForeignKey to self, CASCADE, null=True, blank=True, related_name='children'), `is_active` (BooleanField default=True), `created_at` (DateTimeField auto_now_add), `updated_at` (DateTimeField auto_now); `__str__` returns `self.name`; `Meta.ordering = ["name"]`; `Meta.indexes` with `models.Index(fields=["slug"])` and `models.Index(fields=["is_active", "name"])`.
  - **File**: `products/models.py`
  - **Depends on**: T018
  - **Acceptance**: `Category(name="Electronics").save()` sets `slug="electronics"` (US2 scenario 5, FR-013); `Category._meta.indexes` has 2 entries; `parent` FK to self with `null=True` accepts root-level categories; deleting a parent cascades children (spec edge case).
  - **Satisfies**: FR-013, FR-027, FR-028

- [ ] T020 [US2] Write the `Product` model in `products/models.py`: fields `id` (AutoField PK), `name` (CharField 200), `slug` (SlugField 200, unique, blank=True — auto in `save()`), `category` (ForeignKey → Category, CASCADE, related_name='products'), `description` (TextField), `short_description` (CharField 500, blank=True, null=True), `price` (DecimalField 10,2), `compare_price` (DecimalField 10,2, blank=True, null=True), `cost_price` (DecimalField 10,2, blank=True, null=True), `sku` (CharField 100, unique), `stock_quantity` (PositiveIntegerField default=0), `track_inventory` (BooleanField default=True), `allow_backorders` (BooleanField default=False), `weight` (DecimalField 8,2, blank=True, null=True), `dimensions_length`/`dimensions_width`/`dimensions_height` (each DecimalField 8,2, blank=True, null=True), `meta_title` (CharField 200, blank=True, null=True), `meta_description` (CharField 500, blank=True, null=True), `is_active` (BooleanField default=True), `is_featured` (BooleanField default=False), `is_digital` (BooleanField default=False), `created_at` (auto_now_add), `updated_at` (auto_now); `__str__` returns `self.name`; `Meta.ordering = ["-created_at"]`; `Meta.indexes` with indexes on `slug`, `sku`, and `(is_active, -created_at)`.
  - **File**: `products/models.py`
  - **Depends on**: T019 (Category must be defined first in the same file)
  - **Acceptance**: `Product._meta.get_field("slug").unique is True`; `Product._meta.get_field("sku").unique is True`; slug auto-generated from name; `Product._meta.indexes` has 3 entries.
  - **Satisfies**: FR-014, FR-027, FR-028

- [ ] T021 [US2] Add four computed properties to the `Product` model in `products/models.py`: `is_on_sale` (returns `True` when `compare_price` is not `None` and `compare_price > price`); `discount_percentage` (returns `int((1 - price / compare_price) * 100)` when `is_on_sale` else `0`); `is_in_stock` (returns `True` when `stock_quantity > 0 or allow_backorders`); `main_image` (returns first `ProductImage` with `is_primary=True` via `self.images` reverse manager, respecting prefetch cache).
  - **File**: `products/models.py`
  - **Depends on**: T020
  - **Acceptance**: `is_on_sale` is False when `compare_price=None`; True when `compare_price=200, price=150`; `discount_percentage` returns 25 in that case; `is_in_stock` returns True when `stock_quantity=0, allow_backorders=True`; `main_image` returns the primary image without extra queries when prefetched (US2 scenario 1).
  - **Satisfies**: FR-015

- [ ] T022 [US2] Write the `ProductImage` model in `products/models.py`: fields `id` (AutoField PK), `product` (ForeignKey → Product, CASCADE, related_name='images'), `image` (ImageField upload_to='products/', with `FileExtensionValidator(["jpg","jpeg","png","webp","gif"])` and a custom `MaxFileSizeValidator` that raises `ValidationError` for files exceeding `settings.MAX_IMAGE_UPLOAD_MB` (default 5 MB)), `alt_text` (CharField 200, blank=True, null=True), `is_primary` (BooleanField default=False), `sort_order` (PositiveIntegerField default=0), `created_at` (DateTimeField auto_now_add); `save()` enforces single-primary-per-product by calling `self.product.images.exclude(pk=self.pk).update(is_primary=False)` when `is_primary=True`, then calls `resize_image()` (Pillow: open image, thumbnail to 800×800 preserving aspect ratio, re-save preserving PNG/WebP transparency); `__str__` returns `f"Image for {self.product.name}"`. `Meta.ordering = ["sort_order", "-created_at"]`; `Meta.indexes` with `models.Index(fields=["product", "is_primary"])`.
  - **File**: `products/models.py`
  - **Depends on**: T020
  - **Acceptance**: Saving a second `ProductImage(is_primary=True)` for the same product sets the first one to `is_primary=False`; saving with extension `.bmp` raises `ValidationError`; a mock file >5MB raises `ValidationError`; `ProductImage._meta.indexes` includes the composite `(product, is_primary)` index (FR-016, FR-027).
  - **Satisfies**: FR-016, FR-027

- [ ] T023 [US2] Write the `ProductVariant` model in `products/models.py`: fields `id` (AutoField PK), `product` (ForeignKey → Product, CASCADE, related_name='variants'), `name` (CharField 100 — e.g. "Color"), `value` (CharField 100 — e.g. "Red"), `price_adjustment` (DecimalField 10,2, default=0), `sku_suffix` (CharField 50, blank=True, null=True), `stock_quantity` (PositiveIntegerField default=0), `is_active` (BooleanField default=True), `sort_order` (PositiveIntegerField default=0), `created_at` (DateTimeField auto_now_add); properties `full_sku` (returns `f"{self.product.sku}-{self.sku_suffix}"` when `sku_suffix` is set, else `self.product.sku`) and `final_price` (returns `self.product.price + self.price_adjustment`); `__str__` returns `f"{self.product.name} — {self.name}: {self.value}"`; `Meta.unique_together = [["product", "name", "value"]]`; `Meta.ordering = ["sort_order", "name", "value"]`; add `post_save` and `post_delete` signals to invalidate parent product cache.
  - **File**: `products/models.py`
  - **Depends on**: T020
  - **Acceptance**: `variant.final_price == product.price + variant.price_adjustment`; `full_sku` returns `"SKU001-L"` when `sku_suffix="L"` and `product.sku="SKU001"`; a duplicate `(product, name, value)` row raises `IntegrityError` (FR-018, FR-019).
  - **Satisfies**: FR-018, FR-019

- [ ] T024 [US2] Write the `ProductReview` model in `products/models.py`: fields `id` (AutoField PK), `product` (ForeignKey → Product, CASCADE, related_name='reviews'), `user` (ForeignKey → `settings.AUTH_USER_MODEL`, CASCADE, related_name='reviews'), `rating` (PositiveSmallIntegerField, MinValueValidator(1), MaxValueValidator(5)), `title` (CharField 200, blank=True), `body` (TextField), `is_approved` (BooleanField default=False), `created_at` (DateTimeField auto_now_add), `updated_at` (DateTimeField auto_now); `__str__` returns `f"Review by {self.user} on {self.product} ({self.rating}/5)"`; `Meta.unique_together = [["product", "user"]]`; `Meta.ordering = ["-created_at"]`.
  - **File**: `products/models.py`
  - **Depends on**: T020
  - **Acceptance**: A second `ProductReview` for the same `(product, user)` pair raises `IntegrityError`; `rating=0` raises `ValidationError`; `rating=6` raises `ValidationError`; `rating=3` saves without error (FR-017).
  - **Satisfies**: FR-017

- [ ] T025 [P] [US2] Create `tests/factories.py` with factory-boy factories for all five products models: `CategoryFactory` (DjangoModelFactory for `products.Category`, `name=factory.Faker("word")`, `is_active=True`, `parent=None`); `ProductFactory` (DjangoModelFactory for `products.Product`, `name=factory.Faker("sentence",nb_words=3)`, `category=factory.SubFactory(CategoryFactory)`, `price=Decimal("99.99")`, `sku=factory.Sequence(lambda n: f"SKU-{n:05d}")`, `stock_quantity=10`, `is_active=True`); `ProductImageFactory` (image mocked with `factory.django.ImageField()`, `product=factory.SubFactory(ProductFactory)`, `is_primary=False`); `ProductVariantFactory` (`product=factory.SubFactory(ProductFactory)`, `name="Size"`, `value="M"`, `price_adjustment=Decimal("0.00")`); `ProductReviewFactory` (`product=factory.SubFactory(ProductFactory)`, `user=factory.SubFactory("tests.factories.UserFactory")`, `rating=5`, `is_approved=False`).
  - **File**: `tests/factories.py`
  - **Depends on**: T019, T020, T022, T023, T024
  - **Acceptance**: `ProductFactory()` creates a valid Product with an auto-created Category in the test DB; `pytest --collect-only` shows no import errors; `ProductVariantFactory()` creates a variant with `final_price == Decimal("99.99")`.
  - **Satisfies**: FR-034 (test infrastructure)

- [ ] T026 [US2] Write `tests/test_products.py` with unit tests for all five products models: **(a) Category**: slug auto-gen from name, `__str__`, `is_active`, parent-child hierarchy (child.parent == parent); **(b) Product**: slug auto-gen, `is_on_sale=True` when compare_price>price, `is_on_sale=False` when compare_price is None, `discount_percentage` correct value, `is_in_stock=True` with stock>0, `is_in_stock=True` with stock=0+allow_backorders, `is_in_stock=False` with stock=0, `main_image` returns primary image; **(c) ProductImage**: single-primary enforcement (second primary demotes first), `FileExtensionValidator` rejects `.bmp`, `MaxFileSizeValidator` rejects oversized file; **(d) ProductVariant**: `final_price` computed correctly, `full_sku` with and without suffix, `unique_together` raises `IntegrityError`; **(e) ProductReview**: `__str__`, `rating` validator (0 invalid, 1 valid, 5 valid, 6 invalid), `unique_together` raises `IntegrityError`.
  - **File**: `tests/test_products.py`
  - **Depends on**: T019, T020, T021, T022, T023, T024, T025
  - **Acceptance**: `pytest tests/test_products.py -v` exits 0 with 100% pass rate; every model's `__str__` is exercised; all computed properties have at least 2 scenario branches covered (FR-034).
  - **Satisfies**: FR-034, US2 scenarios 1 and 5

**Checkpoint**: All five products models are defined, importable, and pass unit tests. Phase 3 can now begin in parallel if desired (Phase 3 has no products dependency), but Phase 4 orders tasks require products models.

---

## Phase 3: `accounts` app models

**Purpose**: `UserProfile` model extending Django's built-in `User` via OneToOne, with inlined address fields and an auto-creation `post_save` signal.

- [ ] T027 [US2] Create the `accounts` Django app: run `python manage.py startapp accounts`, add `"accounts"` to `INSTALLED_APPS`, create `accounts/migrations/__init__.py`.
  - **Files**: `accounts/__init__.py`, `accounts/apps.py`, `accounts/migrations/__init__.py`; edit `ecommerce_site/settings.py`
  - **Depends on**: T016 (BaseModel must exist)
  - **Acceptance**: `python manage.py check` exits 0; `from accounts import models` importable.
  - **Satisfies**: FR-009 prerequisite

- [ ] T028 [US2] Write the `UserProfile` model in `accounts/models.py` (inherits `BaseModel`): `user` (OneToOneField → `settings.AUTH_USER_MODEL`, CASCADE, related_name='profile'), `phone_number` (CharField 20, blank=True, null=True, RegexValidator `r'^\+?1?\d{9,15}$'`), `date_of_birth` (DateField, blank=True, null=True), `address_line_1` (CharField 255, blank=True, null=True), `address_line_2` (CharField 255, blank=True, null=True), `city` (CharField 100, blank=True, null=True), `state_province` (CharField 100, blank=True, null=True), `postal_code` (CharField 20, blank=True, null=True), `country` (CharField 100, blank=True, null=True), `newsletter_subscription` (BooleanField default=False), `email_notifications` (BooleanField default=True), `created_at` (DateTimeField auto_now_add from BaseModel), `updated_at` (DateTimeField auto_now from BaseModel); property `full_name` returning `self.user.get_full_name()`; property `full_address` returning a comma-joined string of non-blank address fields; `__str__` returning `f"Profile({self.user.username})"`. `Meta.ordering = ["-created_at"]`.
  - **File**: `accounts/models.py`
  - **Depends on**: T027
  - **Acceptance**: `UserProfile._meta.get_field("user").one_to_one is True`; `phone_number="not-a-phone"` raises `ValidationError`; `phone_number="+15555555555"` saves without error; `full_name` returns `user.get_full_name()` (FR-009).
  - **Satisfies**: FR-009

- [ ] T029 [US2] Add `post_save` signal to `accounts/models.py`: decorate `create_user_profile(sender, instance, created, **kwargs)` with `@receiver(post_save, sender=settings.AUTH_USER_MODEL)`; inside, call `UserProfile.objects.get_or_create(user=instance)` only when `created=True`; register the signal by importing `accounts.models` inside `AccountsConfig.ready()` in `accounts/apps.py`.
  - **Files**: `accounts/models.py`, `accounts/apps.py`
  - **Depends on**: T028
  - **Acceptance**: `User.objects.create_user("bob", password="pw")` automatically creates exactly one `UserProfile` for "bob"; a subsequent `user.save()` does NOT create a second profile; `UserProfile.objects.filter(user=bob).count() == 1` at all times (FR-010).
  - **Satisfies**: FR-010

- [ ] T030 [P] [US2] Extend `tests/factories.py` with accounts factories: `UserFactory` (`factory.django.DjangoModelFactory` for `django.contrib.auth.models.User`, `username=factory.Sequence(lambda n: f"user{n}")`, `email=factory.LazyAttribute(lambda o: f"{o.username}@example.com")`; use `post_generation` or `_create()` override to handle the auto-created profile without duplication); `UserProfileFactory` (`user=factory.SubFactory(UserFactory)`).
  - **File**: `tests/factories.py`
  - **Depends on**: T029
  - **Acceptance**: `UserFactory()` creates a User with exactly one associated `UserProfile` in the test DB; calling `UserFactory()` twice creates two independent users; no `IntegrityError` on second factory call.
  - **Satisfies**: FR-034

- [ ] T031 [US2] Write `tests/test_accounts.py` with unit tests for `UserProfile`: **(a)** signal auto-creation: `User.objects.create_user(...)` creates exactly one UserProfile; **(b)** double-save does NOT create a second UserProfile; **(c)** `UserProfile.__str__` returns `"Profile(username)"`; **(d)** `full_name` property returns `user.get_full_name()`; **(e)** `full_address` returns formatted string when fields are populated, empty string when all blank; **(f)** `phone_number` validator accepts `"+15555555555"` and rejects `"abc"`.
  - **File**: `tests/test_accounts.py`
  - **Depends on**: T028, T029, T030
  - **Acceptance**: `pytest tests/test_accounts.py -v` exits 0 with 100% pass rate; signal creation, double-save guard, `__str__`, and both properties are covered (FR-034).
  - **Satisfies**: FR-034, US2

**Checkpoint**: `UserProfile` is defined, the signal auto-creates profiles, and all tests pass. Phase 4 orders work can now begin.

---

## Phase 4: `orders` app models

**Purpose**: Shopping cart and order data layer — `Cart`, `CartItem`, `Order`, `OrderItem` — with prefetch-aware computed properties, null-variant unique constraints, auto-generated order numbers, and price snapshots.

- [ ] T032 [US2] Create the `orders` Django app: run `python manage.py startapp orders`, add `"orders"` to `INSTALLED_APPS`, create `orders/migrations/__init__.py`.
  - **Files**: `orders/__init__.py`, `orders/apps.py`, `orders/migrations/__init__.py`; edit `ecommerce_site/settings.py`
  - **Depends on**: T020 (Product model needed for CartItem FK)
  - **Acceptance**: `python manage.py check` exits 0; `from orders import models` importable.
  - **Satisfies**: FR-020 prerequisite

- [ ] T033 [US2] Write the `Cart` model in `orders/models.py` (inherits BaseModel): `user` (OneToOneField → `settings.AUTH_USER_MODEL`, CASCADE, null=True, blank=True, related_name='cart'), `session_key` (CharField 40, null=True, blank=True), `created_at` (auto_now_add), `updated_at` (auto_now); property `total_items` returning sum of all `CartItem.quantity` — check `self._prefetched_objects_cache` for 'items' before hitting DB; property `total_price` returning sum of all `CartItem.total_price` — same prefetch-cache check; method `clear()` calling `self.items.all().delete()`; `__str__` returning `f"Cart({'user:'+str(self.user) if self.user else 'session:'+str(self.session_key)})"`. `Meta.ordering = ["-updated_at"]`.
  - **File**: `orders/models.py`
  - **Depends on**: T032
  - **Acceptance**: `Cart.objects.create(session_key="abc123")` creates a cart with `user=None`; `cart.total_price` on a two-item cart returns the correct decimal sum; `cart.total_price` accessed twice against a prefetched queryset does not trigger additional SQL (N+1 guard), US2 scenario 2 (FR-020, FR-023).
  - **Satisfies**: FR-020, FR-023

- [ ] T034 [US2] Write the `CartItem` model in `orders/models.py` (inherits BaseModel): `cart` (ForeignKey → Cart, CASCADE, related_name='items'), `product` (ForeignKey → `products.Product`, CASCADE), `variant` (ForeignKey → `products.ProductVariant`, CASCADE, null=True, blank=True), `quantity` (PositiveIntegerField default=1, MinValueValidator(1)), `created_at` (auto_now_add), `updated_at` (auto_now); property `unit_price` returning `self.variant.final_price` if `variant` is set else `self.product.price`; property `total_price` returning `self.unit_price * self.quantity`; `__str__` returning `f"{self.quantity}x {self.product.name}"`; `Meta.unique_together = [["cart", "product", "variant"]]`; `Meta.constraints` including `UniqueConstraint(fields=["cart", "product"], condition=Q(variant__isnull=True), name="unique_cartitem_no_variant")`; `Meta.indexes` with `models.Index(fields=["cart", "-created_at"])`.
  - **File**: `orders/models.py`
  - **Depends on**: T033
  - **Acceptance**: A second `CartItem` with the same `(cart, product, variant=None)` raises `IntegrityError` (US2 scenario 4, FR-021); `unit_price` returns `product.price` when `variant=None` and `variant.final_price` when variant is set; `total_price = unit_price * quantity` (FR-022).
  - **Satisfies**: FR-021, FR-022

- [ ] T035 [US2] Write the `Order` model in `orders/models.py` (inherits BaseModel): `order_number` (CharField 50, unique, editable=False — auto-generated in `save()` as `f"ORD-{datetime.now():%Y%m%d}-{uuid.uuid4().hex[:8].upper()}"`), `user` (ForeignKey → `settings.AUTH_USER_MODEL`, CASCADE, null=True, blank=True, related_name='orders'), `email` (EmailField), `first_name` (CharField 100), `last_name` (CharField 100), `phone_number` (CharField 20, blank=True, null=True), billing address fields: `billing_address_line_1` (CharField 255), `billing_address_line_2` (CharField 255, blank=True, null=True), `billing_city` (CharField 100), `billing_state_province` (CharField 100), `billing_postal_code` (CharField 20), `billing_country` (CharField 100), `shipping_same_as_billing` (BooleanField default=True), shipping address fields: `shipping_address_line_1`/`shipping_city`/`shipping_state_province`/`shipping_postal_code`/`shipping_country` (all CharField matching billing, blank=True,null=True), `shipping_address_line_2` (blank=True,null=True), `subtotal`/`tax_amount`/`shipping_cost`/`discount_amount`/`total_amount` (all DecimalField 10,2, default=Decimal("0.00"), MinValueValidator(Decimal("0.00"))), `status` (CharField 20, choices: pending/confirmed/processing/shipped/delivered/cancelled/refunded, default='pending'), `payment_status` (CharField 20, choices: pending/paid/failed/refunded/partially_refunded, default='pending'), `payment_method` (CharField 50, default='credit_card'), `order_notes`/`internal_notes` (TextField, blank=True, null=True), `created_at` (auto_now_add), `updated_at` (auto_now), `shipped_at`/`delivered_at` (DateTimeField, null=True, blank=True); properties `full_name` (f"{first_name} {last_name}"), `billing_address` (formatted string), `shipping_address` (billing if same_as_billing else shipping fields), `can_be_cancelled` (True when status in ['pending','confirmed']), `is_completed` (True when status=='delivered'); method `recalculate_totals(tax_rate=Decimal("0.00"), save=True)` summing live OrderItems; `__str__` returning `self.order_number`. `Meta.ordering = ["-created_at"]`; `Meta.indexes` with indexes on `order_number`, `(status, -created_at)`, `(user, -created_at)`.
  - **File**: `orders/models.py`
  - **Depends on**: T032
  - **Acceptance**: `Order(...).save()` auto-generates `order_number` matching regex `ORD-\d{8}-[A-F0-9]{8}`; two distinct orders have distinct order numbers; status change to 'shipped' persists on re-fetch (US2 scenario 3); `total_amount` defaults to `Decimal("0.00")`; `Order._meta.indexes` has 3 entries (FR-024, FR-027, FR-028).
  - **Satisfies**: FR-024, FR-027, FR-028

- [ ] T036 [US2] Write the `OrderItem` model in `orders/models.py` (inherits BaseModel): `order` (ForeignKey → Order, CASCADE, related_name='items'), `product` (ForeignKey → `products.Product`, CASCADE), `variant` (ForeignKey → `products.ProductVariant`, CASCADE, null=True, blank=True), `product_name` (CharField 200), `product_sku` (CharField 100), `variant_name` (CharField 100, blank=True, null=True), `variant_value` (CharField 100, blank=True, null=True), `quantity` (PositiveIntegerField, MinValueValidator(1)), `unit_price` (DecimalField 10,2 — snapshot at purchase time), `total_price` (DecimalField 10,2 — auto-computed); `save()` snapshots `product_name`, `product_sku`, `variant_name`, `variant_value` from FK objects on first save (using `if not self.product_name:` guard), and auto-computes `total_price = self.unit_price * self.quantity`; `__str__` returning `f"{self.quantity}x {self.product_name} @ {self.unit_price}"`; `Meta.ordering = ["id"]`.
  - **File**: `orders/models.py`
  - **Depends on**: T035
  - **Acceptance**: `OrderItem.save()` sets `product_name` from `product.name` on first save; re-saving an existing `OrderItem` after changing `product.name` does NOT overwrite historical `product_name`; `total_price = unit_price * quantity` is auto-computed (FR-025).
  - **Satisfies**: FR-025

- [ ] T037 [P] [US2] Extend `tests/factories.py` with orders factories: `CartFactory` (DjangoModelFactory for `orders.Cart`, `user=None`, `session_key=factory.LazyFunction(lambda: uuid.uuid4().hex[:40])`); `CartItemFactory` (`cart=factory.SubFactory(CartFactory)`, `product=factory.SubFactory(ProductFactory)`, `variant=None`, `quantity=1`); `OrderFactory` (`user=factory.SubFactory(UserFactory)`, `email=factory.LazyAttribute(lambda o: o.user.email)`, `first_name="Test"`, `last_name="User"`, `billing_address_line_1="123 Main St"`, `billing_city="Springfield"`, `billing_state_province="IL"`, `billing_postal_code="62701"`, `billing_country="US"`, `status='pending'`); `OrderItemFactory` (`order=factory.SubFactory(OrderFactory)`, `product=factory.SubFactory(ProductFactory)`, `unit_price=Decimal("49.99")`, `quantity=1`).
  - **File**: `tests/factories.py`
  - **Depends on**: T033, T034, T035, T036
  - **Acceptance**: `OrderFactory()` creates a valid Order with auto-generated `order_number`; `CartItemFactory()` creates a CartItem linked to a Cart and Product; `pytest --collect-only` shows no import errors.
  - **Satisfies**: FR-034

- [ ] T038 [US2] Write `tests/test_orders.py` with unit tests for all four orders models: **(a) Cart**: `total_price` correct sum for two CartItems, `total_items` correct count, `total_price=Decimal("0.00")` for empty cart, `clear()` deletes all items; **(b) Cart N+1 guard**: prefetch `items` with `select_related`, access `cart.total_price` twice — assert query count does not grow on second access; **(c) CartItem**: null-variant unique constraint raises `IntegrityError`, `unit_price` falls back to `product.price` when `variant=None`, `unit_price` uses `variant.final_price` when variant is set, `total_price = unit_price * quantity`; **(d) Order**: `order_number` auto-generated matching `ORD-\d{8}-[A-F0-9]{8}`, two orders have distinct numbers, status transitions persist on refetch, `can_be_cancelled=True` for pending, `is_completed=True` for delivered; **(e) OrderItem**: `product_name` snapshot captured on first save, historical `product_name` unchanged after product rename, `total_price` auto-computed.
  - **File**: `tests/test_orders.py`
  - **Depends on**: T033, T034, T035, T036, T037
  - **Acceptance**: `pytest tests/test_orders.py -v` exits 0 with 100% pass rate; N+1 guard test uses `django.test.utils.CaptureQueriesContext` or `assertNumQueries`; constraint test explicitly catches `IntegrityError` (FR-034, US2 scenarios 2, 3, 4).
  - **Satisfies**: FR-034, US2 scenarios 2, 3, 4

**Checkpoint**: All 10 models are defined across 4 apps and pass unit tests. Phase 5 migrations can now begin.

---

## Phase 5: Migrations & database setup

**Purpose**: Generate clean initial migrations for all apps, verify on SQLite and PostgreSQL, and create the loadable dev seed fixture.

- [ ] T039 [US2] Generate initial migrations for all four apps: run `python manage.py makemigrations core accounts products orders`. Review each generated `0001_initial.py` to confirm all FR-027 indexes and FR-028 unique constraints are present explicitly (not just implied by `unique=True` field options).
  - **Files**: `core/migrations/0001_initial.py`, `accounts/migrations/0001_initial.py`, `products/migrations/0001_initial.py`, `orders/migrations/0001_initial.py`
  - **Depends on**: T028, T029, T019, T020, T021, T022, T023, T024, T033, T034, T035, T036
  - **Acceptance**: All four files exist; `python manage.py migrate --check` exits non-zero (unapplied changes exist); `python manage.py showmigrations` lists all four apps with unchecked migrations.
  - **Satisfies**: FR-032

- [ ] T040 [US2] Apply migrations on SQLite (dev): run `python manage.py migrate` with `DATABASE_URL=sqlite:///db.sqlite3`; confirm with `python manage.py showmigrations` (all marked `[X]`) and `python manage.py check` (0 errors).
  - **Depends on**: T039
  - **Acceptance**: `python manage.py migrate` exits 0; `python manage.py showmigrations` shows all migrations applied `[X]`; `python manage.py check` exits 0; all model tables exist in `db.sqlite3` (US1 acceptance scenario 2).
  - **Satisfies**: FR-032, US1 scenario 2

- [ ] T041 [US1] Verify migrations on PostgreSQL: start Postgres container with `docker-compose up -d db`, run `docker-compose exec web python manage.py migrate`, confirm `python manage.py check` exits 0 in the container.
  - **Depends on**: T040, T013 (docker-compose must exist)
  - **Acceptance**: `docker-compose exec web python manage.py migrate` exits 0; no `DataError` or `ProgrammingError` due to SQLite-specific syntax; `\dt` in psql shows all expected application tables including junction and constraint tables.
  - **Satisfies**: FR-032, US1 scenario 1

- [ ] T042 [US1] Create dev seed fixture `fixtures/dev_seed.json` (run `mkdir -p fixtures`): include exactly 1 superuser (`username: admin`, `is_superuser: true`, `is_staff: true`), 3 Category records (Electronics — root; Computers — child of Electronics; Clothing — root), 10 Product records (8 in Electronics/Computers, 2 in Clothing) each with at least 1 `ProductImage` record, and 1 `UserProfile` for the admin user. All JSON field names must match the model field names as defined in data-model.md exactly.
  - **File**: `fixtures/dev_seed.json`
  - **Depends on**: T039
  - **Acceptance**: `python manage.py loaddata dev_seed` exits 0; `Category.objects.count() >= 3`; `Product.objects.count() >= 10`; `Category.objects.get(name="Computers").parent.name == "Electronics"`; admin login at `/admin/` with seed credentials succeeds (FR-033, US1 scenario 3).
  - **Satisfies**: FR-033, US1 scenario 3

- [ ] T043 [US1] Seed end-to-end verification: run `python manage.py loaddata dev_seed` on a fresh db, start `python manage.py runserver`, navigate to `/admin/`, log in as seed admin; verify all 10 model admin list pages load (200 OK): userprofile, category, product, productimage, productvariant, productreview, cart, cartitem, order, orderitem.
  - **Depends on**: T042, T047 (Phase 6 admin registration must complete first — schedule T043 after Phase 6)
  - **Acceptance**: All 10 admin list views return HTTP 200; ProductAdmin change page shows ProductImage and ProductVariant inlines; OrderAdmin change page shows OrderItem inline; no 500 errors in server log (US1 acceptance scenario 4, FR-029, FR-030, FR-031).
  - **Satisfies**: FR-029, FR-030, FR-031, US1 scenario 4

**Checkpoint**: All migrations apply cleanly on SQLite and Postgres. Dev seed is loadable. Schedule T043 after Phase 6 completes.

---

## Phase 6: Django admin registration

**Purpose**: Register all 10 models with full `ModelAdmin` subclasses — `list_display`, `search_fields`, `list_filter`, `readonly_fields` — and inline editing for products and orders.

- [ ] T044 [P] [US1] Write `accounts/admin.py` with `UserProfileAdmin`: `list_display = ["user","phone_number","city","country","newsletter_subscription","created_at"]`, `search_fields = ["user__username","user__email","phone_number","city"]`, `list_filter = ["country","newsletter_subscription","email_notifications"]`, `readonly_fields = ["created_at","updated_at"]`; register `UserProfile`.
  - **File**: `accounts/admin.py`
  - **Depends on**: T028
  - **Acceptance**: `python manage.py check` exits 0; `/admin/accounts/userprofile/` returns HTTP 200; `created_at` and `updated_at` are listed in `readonly_fields` and render as read-only in the change form.
  - **Satisfies**: FR-029

- [ ] T045 [P] [US1] Write `products/admin.py` with five admin classes: `CategoryAdmin` (`list_display=["name","slug","parent","is_active"]`, `search_fields=["name","slug"]`, `list_filter=["is_active","parent"]`, `readonly_fields=["created_at","updated_at"]`); `ProductImageInline` (TabularInline, model=ProductImage, extra=1, `readonly_fields=["created_at"]`); `ProductVariantInline` (TabularInline, model=ProductVariant, extra=1, `readonly_fields=["created_at"]`); `ProductAdmin` (`list_display=["name","sku","price","stock_quantity","is_active","is_featured"]`, `search_fields=["name","sku","description"]`, `list_filter=["category","is_active","is_featured","is_digital"]`, `readonly_fields=["slug","created_at","updated_at"]`, `inlines=[ProductImageInline,ProductVariantInline]`); `ProductReviewAdmin` (`list_display=["product","user","rating","is_approved","created_at"]`, `search_fields=["title","body","user__username"]`, `list_filter=["rating","is_approved"]`, `readonly_fields=["created_at","updated_at"]`); register all four models.
  - **File**: `products/admin.py`
  - **Depends on**: T019, T020, T022, T023, T024
  - **Acceptance**: `python manage.py check` exits 0; `/admin/products/product/add/` renders inline sections for ProductImage and ProductVariant with at least one empty form row each (FR-030); `slug` is in `readonly_fields` so it cannot be edited manually in admin.
  - **Satisfies**: FR-029, FR-030

- [ ] T046 [P] [US1] Write `orders/admin.py` with four admin classes: `CartItemInline` (TabularInline, model=CartItem, extra=0, `readonly_fields=["unit_price","total_price","created_at"]`); `CartAdmin` (`list_display=["user","session_key","total_items","total_price","created_at"]`, `search_fields=["user__username","session_key"]`, `readonly_fields=["created_at","updated_at"]`, `inlines=[CartItemInline]`); `OrderItemInline` (TabularInline, model=OrderItem, extra=0, `readonly_fields=["product_name","product_sku","variant_name","variant_value","unit_price","total_price","created_at"]`); `OrderAdmin` (`list_display=["order_number","user","status","total_amount","created_at"]`, `search_fields=["order_number","user__username","email"]`, `list_filter=["status","payment_status","payment_method"]`, `readonly_fields=["order_number","created_at","updated_at"]`, `inlines=[OrderItemInline]`); register Cart, CartItem, Order, and OrderItem.
  - **File**: `orders/admin.py`
  - **Depends on**: T033, T034, T035, T036
  - **Acceptance**: `python manage.py check` exits 0; `/admin/orders/order/` list view displays `order_number` and `total_amount` columns; OrderItem inline renders as read-only on the Order change page (FR-031); `order_number` field in admin renders read-only.
  - **Satisfies**: FR-029, FR-031

- [ ] T047 [US1] Verify all admin registrations: run `python manage.py check` (must exit 0 with 0 errors); start dev server and manually confirm that each of the 10 model admin list URLs returns HTTP 200: `/admin/accounts/userprofile/`, `/admin/products/category/`, `/admin/products/product/`, `/admin/products/productimage/`, `/admin/products/productvariant/`, `/admin/products/productreview/`, `/admin/orders/cart/`, `/admin/orders/cartitem/`, `/admin/orders/order/`, `/admin/orders/orderitem/`.
  - **Depends on**: T044, T045, T046
  - **Acceptance**: All 10 URLs return HTTP 200 with no server-side exceptions; `ProductAdmin` add page shows both inlines; `OrderAdmin` change page shows read-only `OrderItemInline`; `CartAdmin` list shows `total_items` and `total_price` without crashing (callable properties in list_display).
  - **Satisfies**: FR-029, FR-030, FR-031

**Checkpoint**: All 10 models are admin-registered. Run T043 now to complete Phase 5 end-to-end verification.

---

## Phase 7: Tests & coverage gate

**Purpose**: Assemble shared fixture infrastructure, verify ≥ 95% coverage across all four apps, and confirm all 7 pre-commit gates pass with exit code 0.

- [ ] T048 [US2] Write `tests/conftest.py` with shared pytest fixtures used across all test modules: `@pytest.fixture` for `user` (creates via `UserFactory()`), `user_profile` (returns `user.profile` — relies on signal from T029), `category` (creates via `CategoryFactory()`), `product` (creates via `ProductFactory(category=category)`), `cart` (creates via `CartFactory(user=user)`), `order` (creates via `OrderFactory(user=user)`); mark all as `@pytest.mark.django_db` or use `@pytest.fixture(scope="function")` with Django DB access granted via `pytest.ini` `django_db` plugin.
  - **File**: `tests/conftest.py`
  - **Depends on**: T025 (products factories), T030 (accounts factories), T037 (orders factories)
  - **Acceptance**: Re-running `pytest tests/ -v` with conftest in place shows fixtures being composited correctly; no `IntegrityError` when multiple tests share factory-created objects; no `django_db` access permission errors.
  - **Satisfies**: FR-034 (shared fixtures)

- [ ] T049 [US2] [US3] Run full test suite with coverage enforcement: run `pytest tests/ --cov --cov-report=term-missing --cov-fail-under=95 -v`. Inspect per-module coverage; identify and add missing tests to reach 95% threshold if needed.
  - **Depends on**: T017, T026, T031, T038, T048
  - **Acceptance**: Exit code 0; all tests pass (100% pass rate); coverage for `accounts`, `products`, `orders`, and `core` modules combined is ≥ 95%; no single covered module falls below 85% individually; coverage report lists no uncovered lines in model `save()` overrides, computed properties, or signal handlers (FR-034, constitution §III, US2 independent test, US3 scenario 4).
  - **Satisfies**: FR-034, US2, US3 scenario 4

- [ ] T050 [P] [US3] Run flake8 gate: `flake8 . --max-line-length=88 --extend-ignore=E203,W503 --exclude=migrations,.venv,__pycache__`. Fix any violations before committing.
  - **Depends on**: T049 (all implementation code complete)
  - **Acceptance**: Exit code 0; zero violations reported across all four apps and test files (US3 scenario 1).
  - **Satisfies**: FR-005, US3 scenario 1

- [ ] T051 [P] [US3] Run mypy type-checking gate: `mypy accounts orders products ecommerce_site core`. Fix all type errors (missing return types on properties, incorrect FK type annotations, untyped function signatures) before committing.
  - **Depends on**: T049
  - **Acceptance**: Exit code 0; zero mypy errors reported; no `error: Function is missing a return type annotation` warnings in model computed properties (US3 scenario 2).
  - **Satisfies**: FR-006, US3 scenario 2

- [ ] T052 [P] [US3] Run bandit SAST gate: `bandit -r accounts core orders products ecommerce_site -ll`. Fix or document any medium/high severity findings before committing.
  - **Depends on**: T049
  - **Acceptance**: Exit code 0; zero medium/high severity findings; any B101 (assert in tests) findings are suppressed by `.bandit` config from T010 (US3 scenario 3).
  - **Satisfies**: FR-006, US3 scenario 3

- [ ] T053 [P] [US3] Run pip-audit CVE scan: `pip-audit -r requirements.txt`. Upgrade any packages with known vulnerabilities and pin updated versions in `requirements.txt`.
  - **Depends on**: T001 (requirements.txt must exist with final pinned versions)
  - **Acceptance**: Exit code 0; zero known CVEs in the full dependency tree; `requirements.txt` reflects updated, pinned versions if any upgrades were needed.
  - **Satisfies**: FR-006 (security), constitution §II

- [ ] T054 [US3] Run `pre-commit run --all-files` and confirm all 7 hooks exit 0: black (format), isort (imports), flake8 (lint), mypy (types), bandit (SAST), pytest with coverage (tests + 95% gate), pip-audit (CVEs). Fix any remaining violations.
  - **Depends on**: T050, T051, T052, T053
  - **Acceptance**: `pre-commit run --all-files` exits 0; all 7 hooks report "Passed" in output; no hook reports "Failed" or "Error"; commit message matches format `feat: migrations, dev seed fixture, full test suite, pre-commit gates pass (EPIC-1, Phase 7)` per constitution commit format (US3 scenarios 1–4, constitution §II, §III).
  - **Satisfies**: FR-005, FR-006, FR-034, US3 scenarios 1–4

**Checkpoint (Epic 1 Complete)**: All 10 models implemented, migrated on SQLite and Postgres, admin-registered, seeded with dev fixture, tested at ≥ 95% coverage. All 7 pre-commit gates pass. Branch `001-database-models-infrastructure` is ready for code review and merge to main.

---

## Dependency Graph Summary

```
T001
 └─ T002 ─ T003 ─ T004
                  T005, T006, T007, T008, T009, T010 [P after T003]
                  T011 [after T006, T007, T008, T010]
           T012 ─ T013 [docker]
           T014 [P]

T015 ─ T016 ─ T017 [tests/test_core.py]

T018 ─ T019 (Category)
     ─ T020 (Product) ─ T021 (computed props)
                      ─ T022 (ProductImage)
                      ─ T023 (ProductVariant)
                      ─ T024 (ProductReview)
     ─ T025 (factories [P after T019-T024])
     ─ T026 (tests/test_products.py [after T025])

T027 ─ T028 (UserProfile)
     ─ T029 (signal)
     ─ T030 (factories [P after T029])
     ─ T031 (tests/test_accounts.py [after T030])

T032 ─ T033 (Cart)
     ─ T034 (CartItem [after T033])
     ─ T035 (Order)
     ─ T036 (OrderItem [after T035])
     ─ T037 (factories [P after T033-T036])
     ─ T038 (tests/test_orders.py [after T037])

Phase 5 (all Phase 2-4 complete):
T039 (makemigrations) ─ T040 (SQLite verify)
                      ─ T041 (Postgres verify)
                      ─ T042 (seed fixture) ─ T043 (requires T047)

Phase 6 [T044 P, T045 P, T046 P]:
T044, T045, T046 ─ T047 (admin verify) ─ T043 (end-to-end verify)

Phase 7:
T048 (conftest) ─ T049 (coverage)
T049 ─ T050 [P], T051 [P], T052 [P]
T001 ─ T053 [P]
T050, T051, T052, T053 ─ T054 (pre-commit gate)
```
