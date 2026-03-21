# ShopHub Constitution

## Core Principles

### I. Documentation-First
Every code change is accompanied by documentation updates in the **same commit** — never deferred. The source of truth for project progress is the checked `[x]` items in the EPIC files, not commit messages or memory. `TODO.md`, relevant `EPIC-*.md` files, and `README.md` must reflect reality at all times. Stale docs erode trust and cause duplicate work.

### II. Test-First (NON-NEGOTIABLE)
A **100% test pass rate is required** before any commit. New views require at minimum one happy-path and one error-path test. New model methods require unit tests covering edge cases. New forms require valid and invalid data tests. Every bug fix requires a regression test that would have caught the bug. No exceptions.

### III. Coverage Enforcement
Minimum code coverage threshold is **95%**. No commit may drop coverage below this floor. New code must not reduce coverage. Coverage is verified with `pytest --cov --cov-report=term-missing` before every commit.

### IV. Environment-Driven Configuration
All runtime configuration is read from environment variables (or a `.env` file via python-decouple). Secrets are **never committed**. The `.env` file is gitignored. Incomplete or environment-specific features are gated by `FEATURE_FLAGS` in `settings.py`. Production settings enforce HTTPS, secure cookies, and HSTS.

### V. Incremental, Branch-Based Development
All work happens on a feature branch (`fix/`, `feat/`, `chore/`, `test/`). Changes are implemented incrementally, validated fully, and committed with descriptive messages referencing EPIC numbers and TODO items. The main branch only receives fully validated, passing code.

## Technical Standards

### Technology Stack
| Layer | Technology |
|-------|------------|
| Backend | Django 5.0.2, Python 3.12+ |
| Database | SQLite (development), PostgreSQL (production) |
| Image Processing | Pillow |
| Environment Config | python-decouple |
| Frontend | Django Templates, Bootstrap, JavaScript/AJAX |
| Testing | pytest, pytest-django, pytest-cov |
| CI/CD | GitHub Actions |

### Pre-Commit Validation Gates (all must pass)
| Gate | Command | Required Result |
|------|---------|----------------|
| Django system check | `python manage.py check` | 0 errors |
| Template syntax | `python validate_templates.py` | clean |
| Tests | `python -m pytest tests/ --tb=short` | 100% pass |
| Lint | `flake8 . --max-line-length=88 --extend-ignore=E203,W503 --exclude=migrations,.venv` | 0 violations |
| Types | `mypy accounts orders products ecommerce_site core` | 0 errors |
| SAST | `bandit -r accounts core orders products ecommerce_site -ll` | 0 medium/high |
| CVEs | `pip-audit -r requirements.txt` | 0 known vulnerabilities |

### Commit Message Format
```
type: short description (scope)
```
- **type**: `fix` | `feat` | `chore` | `test` | `refactor` | `docs`
- **scope**: reference the EPIC number, TODO item, or both
- Examples:
  - `fix: address code review findings (H1-H3, M1-M4, L1-L5, S1)`
  - `feat: add order recalculate_totals method (EPIC-1, Task 1.9)`
  - `test: cover H2 stock-check AJAX path (EPIC-8)`

### Branch Naming
- `fix/short-description` — bug fixes
- `feat/short-description` — new features
- `chore/short-description` — maintenance, docs, refactor
- `test/short-description` — test additions only

### Project Structure
```
ecommerce_site/   Django project settings, URLs, WSGI/ASGI
accounts/         User registration, login, profile management
products/         Product catalog, categories, variants, images
orders/           Cart, checkout, orders
templates/        All HTML templates (per-app subdirectories)
static/           CSS, JS, images
tests/            Test suite (pytest)
conftest.py       Shared pytest fixtures
TODO.md           Active issue tracker (current sprint only)
EPIC-*.md         Epic planning and progress documents
```

### Test File Locations
```
tests/
  test_products.py    Product catalog models, views, forms
  test_orders.py      Cart, checkout, order models and views
  test_accounts.py    Auth, profile, registration
  test_integration.py Full user journey flows
  test_coverage.py    Coverage enforcement tests
conftest.py           Shared fixtures (all tests share these)
```

## Governance

### Source of Truth
The **EPIC files** (`EPIC-*.md`) are the authoritative record of what is done. Commit messages and memory are insufficient. Verified completion means the task checkbox `[x]` and acceptance criteria are checked in the EPIC file.

### Documentation Rules
- `TODO.md` is the current-sprint issue tracker only; items use severity prefixes (`H1`, `M2`, `L3`, `S1`). Before starting a new review cycle, delete all `[x]` items and start fresh.
- EPIC files retain completed tasks as project history (never delete `[x]` tasks).
- README status table is updated whenever an epic changes state or coverage/test count changes significantly.
- Documentation is always updated in the same commit as the code it describes.

### Quality Gate Enforcement
No code may be accepted (kept or merged) until all pre-commit validation gates pass and the agent has explicitly signaled **"✅ Safe to Keep"**. Do not click "Keep All Edits" during active debugging, failing tests, or mid-cycle template fixes.

### Amendment Process
Changes to this constitution require: (1) a documented rationale, (2) a migration plan for any affected practices or tooling, and (3) an update to the version and amendment date below.

### Constitution Supremacy
This constitution supersedes all other practices. When conflicts arise between convenience and these principles, the constitution governs.

**Version**: 1.0.0 | **Ratified**: 2026-03-20 | **Last Amended**: 2026-03-20
