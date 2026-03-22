# ShopHub — Development Guidelines

Auto-generated from project constitution and source codebase. Last updated: 2026-03-22

## Project Overview

**ShopHub** is a production-ready Django e-commerce platform featuring a product catalog, shopping cart,
user authentication, order management, and a full automated test suite.

## Active Technologies

| Layer | Technology | Version |
|-------|------------|---------|
| Backend framework | Django | 5.2.x |
| Language | Python | 3.12+ |
| Database (dev) | SQLite | — |
| Database (prod) | PostgreSQL | via psycopg2-binary |
| Image processing | Pillow | — |
| Environment config | python-decouple | — |
| Django debug toolbar | django-debug-toolbar | — |
| Database URL parsing | dj-database-url | — |
| Brute-force protection | django-axes | — |
| Caching | django-redis + redis | — |
| Frontend | Django Templates + Bootstrap + JS/AJAX | — |
| Test runner | pytest + pytest-django + pytest-cov | — |
| Test data | factory-boy + faker | — |
| Formatter | black | 88 char line length |
| Import sorter | isort | black-compatible profile |
| Linter | flake8 | max-line=88, ignore E203/W503 |
| Type checker | mypy + django-stubs | strict_optional=True |
| SAST | bandit | — |
| CVE scanner | pip-audit | — |
| Complexity checker | radon | — |
| Pre-commit | pre-commit | — |
| CI/CD | GitHub Actions | ci.yml |

## Project Structure

```text
ecommerce_site/        Django project settings, URLs, WSGI/ASGI
accounts/              User registration, login, profile management
products/              Product catalog, categories, variants, images
orders/                Cart, checkout, orders
core/                  Shared utilities and base models
templates/             All HTML templates (per-app subdirectories)
static/                CSS, JS, images
media/                 User-uploaded files (gitignored)
tests/                 pytest test suite
  test_products.py     Product catalog models, views, forms
  test_orders.py       Cart, checkout, order models and views
  test_accounts.py     Auth, profile, registration
  test_integration.py  Full user journey flows
  test_coverage.py     Coverage enforcement tests
conftest.py            Shared pytest fixtures
TODO.md                Active issue tracker (current sprint only)
EPIC-*.md              Epic planning and progress documents (11 epics)
```

## Commands

### Development server
```bash
python manage.py runserver
```

### Database migrations
```bash
python manage.py makemigrations
python manage.py migrate
```

### Tests
```bash
# Full test suite (required: 100% pass)
python -m pytest tests/ --tb=short

# With coverage (required ≥95%)
python -m pytest tests/ --cov --cov-report=term-missing

# Single test file
python -m pytest tests/test_products.py --tb=short
```

### Pre-commit validation (all must pass before commit)
```bash
python manage.py check                                                   # Django system check
python validate_templates.py                                             # Template syntax
python -m pytest tests/ --tb=short                                      # 100% test pass
flake8 . --max-line-length=88 --extend-ignore=E203,W503 --exclude=migrations,.venv
mypy accounts orders products ecommerce_site core
bandit -r accounts core orders products ecommerce_site -ll
pip-audit -r requirements.txt
```

### Code formatting
```bash
black .
isort .
```

### Environment setup
```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.development .env
# Generate SECRET_KEY:
python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"
python manage.py migrate
```

### Docker (full stack with Postgres)
```bash
docker-compose up
```

## Code Style

- **Formatter**: black, line length 88
- **Imports**: isort with `profile = "black"`, known first-party: `accounts`, `orders`, `products`, `ecommerce_site`
- **Typing**: mypy with `strict_optional = True`; `django-stubs` plugin enabled
- **Naming**: Django conventions throughout (snake_case models/views, PascalCase classes)
- **Templates**: Django template language; validate with `python validate_templates.py` before commit
- **No direct secret commits**: all config via env vars / `.env` (gitignored); `.env.example` is the reference
- **Feature flags**: use `settings.FEATURE_FLAGS[...]` for incomplete/opt-in features

## Testing Standards

- **Minimum coverage**: 95% (CI enforced at 90% floor via `--cov-fail-under=90`)
- **Current baseline**: 97%
- **Test settings module**: `ecommerce_site.settings_test`
- **Fixtures**: defined in `conftest.py` — check there before writing new ones
- Every new **view** → happy-path + error-path test
- Every new **model method** → unit test covering edge cases
- Every new **form** → valid + invalid data tests
- Every **bug fix** → regression test that would have caught the bug

## Environment Variables

Key variables (see `.env.example` for full list):

| Variable | Dev default | Required in prod |
|----------|-------------|-----------------|
| `SECRET_KEY` | must generate | ✅ |
| `DEBUG` | `True` | set `False` |
| `DATABASE_URL` | `sqlite:///db.sqlite3` | postgres://... |
| `ALLOWED_HOSTS` | `localhost,127.0.0.1` | your domain |
| `SECURE_SSL_REDIRECT` | `False` | `True` |
| `SESSION_COOKIE_SECURE` | `False` | `True` |
| `SECURE_HSTS_SECONDS` | `0` | `31536000` |
| `FEATURE_REVIEWS` | `False` | opt-in |
| `FEATURE_WISHLIST` | `False` | opt-in |
| `FEATURE_DISCOUNT_CODES` | `False` | opt-in |

## CI/CD Pipeline (GitHub Actions)

**`ci.yml`** runs on every push and PR:

| Job | Steps |
|-----|-------|
| Lint · Type-check · Test | flake8 → mypy → pytest (--cov-fail-under=90) → upload coverage artifact |
| Security scan | bandit (SAST) → pip-audit (CVE scan) |

## Epic Status (source of truth)

| # | Epic | Status |
|---|------|--------|
| 1 | Database Models & Infrastructure | ✅ Complete |
| 2 | Product Catalog System | ✅ Complete |
| 3 | Shopping Cart Functionality | ✅ Complete |
| 4 | User Authentication & Orders | ✅ Complete |
| 5 | Frontend Templates & UI | ✅ Complete |
| 6 | Testing & Deployment (core) | ✅ Complete |
| 7 | Code Quality & Standards | ✅ Complete |
| 8 | Testing & Quality Assurance (advanced) | 🔄 In Progress |
| 9 | CI/CD & Automation | 🔄 In Progress |
| 10 | Security & Compliance | 🔄 In Progress |
| 11 | Performance & Monitoring | 📅 Planned |

<!-- MANUAL ADDITIONS START -->
<!-- MANUAL ADDITIONS END -->

## Recent Changes
- 002-product-catalog-system: Added [if applicable, e.g., PostgreSQL, CoreData, files or N/A]
