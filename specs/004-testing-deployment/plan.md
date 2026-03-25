# Implementation Plan: Testing Completion, CI/CD & Production Deployment

**Branch**: `004-testing-deployment` | **Date**: 2026-03-24 | **Spec**: [spec.md](spec.md)
**Input**: Feature specification from `/specs/004-testing-deployment/spec.md`

## Summary

Extend the existing 153-test, 97%-coverage pytest suite with browser E2E tests (Playwright), load testing (Locust), CI/CD GitHub Actions pipelines, and a production-ready deployment stack. The implementation adds a `/health/` endpoint, production Django settings (`settings_production.py`), structured JSON logging, database backup scripts, and a hardened multi-stage Docker image. GitHub Actions orchestrates the full quality pipeline: lint → security scan → unit+integration tests (3.11 & 3.12 matrix) → E2E tests → deploy to staging (auto on `main`) → deploy to production (manual approval).

## Technical Context

**Language/Version**: Python 3.12 (primary), Python 3.11 (CI matrix)
**Primary Dependencies**: Django 5.2.12, pytest 9.0.2, gunicorn 23.0.0, Playwright (new), Locust (new), whitenoise (new), python-json-logger (new)
**Storage**: SQLite (dev/test), PostgreSQL via `DATABASE_URL` (staging/production); Redis for cache
**Testing**: pytest + pytest-django + pytest-cov (existing); playwright-pytest (new E2E); Locust CLI (load)
**Target Platform**: Docker container on Fly.io (free tier — 3 shared VMs, no sleep); GitHub Actions for CI
**Project Type**: Django web application (e-commerce)
**Performance Goals**: Homepage p95 < 1 s under 50 concurrent VUs; health check response < 500 ms
**Constraints**: CI completes within 10 min; deployment to staging within 15 min of merge; zero-downtime deploys; coverage ≥ 95% (constitution floor, stricter than spec's 90%)
**Scale/Scope**: Initial production load ~50 concurrent users; 153 existing tests must continue passing

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Gate | Status | Notes |
|------|--------|-------|
| **Test-First (II)**: All new views/endpoints require happy-path + error-path tests | PASS | `/health/` endpoint gets unit tests covering 200 (healthy) and 503 (DB down) paths |
| **Coverage Enforcement (III)**: ≥ 95% coverage floor | PASS — with caveat | Spec FR-025 says "90% minimum"; the constitution's 95% floor is stricter and governs. CI enforces 95%. |
| **Environment-Driven Config (IV)**: No secrets committed; production settings from env vars | PASS | `settings_production.py` reads all sensitive values via `python-decouple`; DB creds, secret key, Fly.io deploy token all from env vars / GitHub Secrets |
| **Incremental Development (V)**: Feature branch, passing before merge | PASS | All work on `004-testing-deployment`; CI gate blocks merge on failure |
| **Documentation-First (I)**: Runbooks and docs land in same commit as code | FLAG | Runbooks (`docs/runbooks/`) must be included in the same PR as the deployment pipeline files |

**Violations requiring justification**: None. The constitution's 95% coverage threshold supersedes the spec's 90% mention — both are satisfied when 95% is enforced.

**Post-design re-check**: After Phase 1, verify that `tests/e2e/` and `tests/load/` directories are excluded from the coverage measurement (they are integration/external tests, not unit-testable by definition). The `.coveragerc` / `pyproject.toml` omit list must be updated to exclude these paths.

## Project Structure

### Documentation (this feature)

```text
specs/004-testing-deployment/
├── plan.md              ← this file
├── research.md          ← Phase 0 output
├── data-model.md        ← Phase 1 output
├── quickstart.md        ← Phase 1 output
├── contracts/
│   ├── health-endpoint.md
│   └── ci-pipeline-contract.md
└── tasks.md             ← Phase 2 output (/speckit.tasks command)
```

### Source Code changes (repository root)

```text
# New files
.github/
└── workflows/
    ├── ci.yml                          # PR/push pipeline: lint → scan → test → E2E
    └── deploy.yml                      # Staging (auto) + production (manual approval)

core/
├── views.py                            # NEW: health check view
└── urls.py                             # NEW: /health/ URL

ecommerce_site/
├── settings_production.py              # NEW: production settings (extends settings.py)
└── settings_test.py                    # No change required (no external error service)

tests/
├── e2e/                                # NEW: Playwright-based browser tests
│   ├── conftest.py                     # base_url fixture, browser configuration
│   ├── test_product_browse.py          # FR-002: product browsing journey
│   ├── test_cart.py                    # FR-002: cart add/remove journey
│   ├── test_auth.py                    # FR-002: register + login/logout journey
│   └── test_checkout.py               # FR-002: order placement journey
├── load/                               # NEW: Locust load test scenarios
│   ├── locustfile.py                   # FR-007: homepage, product list, cart scenarios
│   └── baselines.md                    # FR-011: documented p50/p95/p99 baselines
└── test_health.py                      # NEW: unit tests for /health/ endpoint

scripts/
├── backup_db.sh                        # FR-039: pg_dump backup with retention
└── restore_db.sh                       # FR-039: pg_restore from named artifact

docs/
└── runbooks/
    ├── deployment.md                   # FR-040: deploy, rollback, migration procedures
    └── backup_restore.md               # FR-040: backup trigger and restore procedure

# Modified files
requirements.txt                        # Add: playwright, locust, whitenoise, python-json-logger
Dockerfile                              # Add: HEALTHCHECK instruction; add curl to runtime deps
docker-compose.yml                      # Add: PostgreSQL service for local dev
ecommerce_site/urls.py                  # Add: path("health/", ...) route
pytest.ini                              # Add: e2e and load markers; exclude e2e/load from default run
pyproject.toml                          # Add: coverage omit entries for e2e/load/migrations
.env.production.example                 # NEW: document every required production variable
```

**Structure Decision**: Single-project layout (existing Django project). New capability directories (`tests/e2e/`, `tests/load/`) are parallelised under the existing `tests/` root — they use distinct markers (`e2e`, `load`) to allow selective execution. GitHub Actions workflow files live at `.github/workflows/`. Runbooks live in `docs/runbooks/` (new directory tree). All new Django code (`/health/` view) goes into the existing `core` app since it provides project-wide infrastructure.

## Complexity Tracking

No constitution violations requiring justification. The coverage threshold discrepancy (spec 90% vs. constitution 95%) is resolved by enforcing the stricter value.

---

## Phase 0: Research

### Unknowns from Technical Context

| # | Unknown | Research Task |
|---|---------|--------------|
| R1 | E2E framework choice: Playwright vs Selenium | Compare async-native Playwright vs mature Selenium; assess headless CI support, Django LiveServer compatibility, and pytest plugin quality |
| R2 | Structured logging library | Evaluate `python-json-logger` vs Django's built-in formatter for JSON output; assess request-ID injection |
| R3 | Error tracking strategy | Confirm zero-cost approach: Django structured logging (python-json-logger) covers error visibility without an external service |
| R4 | Zero-downtime deployment mechanism | Assess Fly.io rolling deploys with health-check-gated traffic cutover |
| R5 | Static file serving without nginx | Evaluate `whitenoise` serving compressed static files from Django's WSGI layer |
| R6 | Backup storage for pg_dump artifacts | Assess platform-native volume vs S3-compatible bucket vs GitHub Actions artifact storage |

---

### Research Findings

#### R1 — E2E Framework: Playwright

**Decision**: Playwright via `pytest-playwright` plugin.

**Rationale**:
- `pytest-playwright` integrates directly with pytest, uses the same test-discovery and marker system as the existing suite, and produces JUnit XML via `--junit-xml` — satisfying FR-006 with zero additional tooling.
- GitHub Actions runners (`ubuntu-latest`) have Chromium available via `playwright install chromium --with-deps`; no display server (Xvfb) is required because Playwright runs natively headless — satisfying FR-005.
- Playwright's `expect(locator).to_be_visible()` and `page.wait_for_load_state("networkidle")` are the explicit-wait primitives mandated by FR-004; Selenium's `WebDriverWait` is functionally equivalent but more verbose.
- `pytest-django`'s `live_server` fixture provides the `base_url` that Playwright tests connect to, enabling FR-003 (configurable target URL via `--base-url` CLI option).

**Alternatives considered**:
- Selenium WebDriver: mature but requires separate WebDriver binary management (`webdriver-manager`); Playwright is more ergonomic with fewer setup steps. Rejected.
- Cypress: JavaScript-only; incompatible with the Python test runner. Rejected outright.

**New dependencies**: `playwright>=1.44`, `pytest-playwright>=0.5`

---

#### R2 — Structured Logging: `python-json-logger`

**Decision**: `python-json-logger` (`pythonjsonlogger` package) with a custom `JsonFormatter` in `settings_production.py`.

**Rationale**:
- Provides a drop-in `JsonFormatter` that replaces the existing `verbose` formatter in `LOGGING["formatters"]` — zero changes to any call-site (`logger.info(...)` invocations).
- Emits `timestamp`, `level`, `name`, `message`, and any extras passed to the log call as a flat JSON object, satisfying FR-019.
- In development and test settings, the existing `verbose` text formatter is preserved; the JSON formatter is activated only in `settings_production.py`.

**Alternatives considered**:
- `structlog`: requires annotating every logger call with `structlog.get_logger()` — invasive change across the codebase. Rejected.
- DIY Django `Formatter` subclass: valid but reinvents what `python-json-logger` provides. Rejected.

**New dependency**: `python-json-logger>=2.0`

---

#### R3 — Error Tracking: Django Logging Only

**Decision**: No external error tracking service. `python-json-logger` structured logging to stdout is sufficient for zero-cost production visibility.

**Rationale**:
- Sentry free tier is limited to 5,000 events/month and requires account creation — it is not "zero cost" in the strictest sense (operational dependency on a third-party service with pricing risk).
- `python-json-logger` is already included for structured logging (FR-019). JSON-formatted logs emitted to stdout are captured by the Fly.io log aggregator and can be piped to any sink (e.g., Fly Log Ship, self-hosted Loki) without code changes.
- Django's built-in `logging` integration in `settings_production.py` captures unhandled exceptions at `WARNING` level automatically — satisfying FR-020 without an SDK.
- No new dependency. No `SENTRY_DSN` env var. No `settings_test.py` change required.

**No new dependency**.

---

#### R4 — Zero-Downtime Deployment

**Decision**: Fly.io rolling deploy with health-check-gated traffic cutover.

**Rationale**:
- Fly.io free tier provides 3 shared-CPU VMs (`fly-1`), persistent volumes, and a managed Postgres instance — all at zero cost for low-traffic apps.
- `fly deploy` performs a rolling update: the new container must return 200 on `GET /health/` before Fly routes traffic to it — satisfying FR-038 and SC-004.
- `[deploy] release_command = "python manage.py migrate --noinput"` in `fly.toml` runs migrations before traffic cutover — satisfying FR-037.
- Automatic rollback (FR-041, SC-005): Fly detects a failed health check and rolls back to the previous version automatically within the 5-minute window.
- `flyctl` is available as a GitHub Actions action (`superfly/flyctl-actions/setup-flyctl@master`); the `FLY_API_TOKEN` secret is the only credential required.

**No-cost confirmation**: Fly.io's free allowances (as of 2026) include 3 shared VMs, 3 GB persistent storage, and a Postgres cluster — no credit card required for the free tier.

---

#### R5 — Static Files: WhiteNoise

**Decision**: `whitenoise[brotli]` middleware inserted directly after `SecurityMiddleware`.

**Rationale**:
- Serves compressed (gzip + brotli) static files directly from the Django WSGI process — satisfying FR-031 without a separate nginx tier.
- The existing `STATIC_ROOT = BASE_DIR / "staticfiles"` and `collectstatic` call in `Dockerfile` are already correct; WhiteNoise only needs `MIDDLEWARE` insertion and `STATICFILES_STORAGE` set to `CompressedManifestStaticFilesStorage`.
- `WHITENOISE_MAX_AGE = 31536000` (1 year) enables far-future cache headers with content-hash filenames.

**New dependency**: `whitenoise[brotli]>=6.7`

---

#### R6 — Backup Storage

**Decision**: Cloudflare R2 (S3-compatible) for production backups; `pg_dump` → `aws s3 cp` via AWS CLI v2.

**Rationale**:
- Cloudflare R2 provides 10 GB free storage with S3-compatible API — zero cost for initial production backup needs.
- `pg_dump` to a mounted volume is sufficient for staging but creates a single point of failure in production.
- GitHub Actions scheduled workflow (`cron: "0 2 * * *"`) triggers the backup script, satisfying FR-039.
- 7-day retention enforced by the script deleting files older than 7 days from the bucket.

**Alternative considered**: GitHub Actions artifact storage — free but 90-day maximum retention and not independently accessible. Rejected.

---

## Phase 1: Design

### Data Model (`data-model.md`)

No new database tables are introduced. The artifacts are:

#### Health Check Response Schema

```json
// 200 OK — all systems healthy
{"status": "ok", "database": "ok"}

// 503 Service Unavailable — database unreachable
{"status": "error", "database": "error", "message": "connection timeout"}
```

- `GET /health/` → **200** when all components healthy
- `GET /health/` → **503** when any component reports error
- Response time must be < 500 ms (SC-006); the view enforces a DB query with a configurable timeout guard

#### Load Test Baselines (to be measured on first staging run)

| Endpoint | p50 (ms) | p95 (ms) | p99 (ms) | Error Rate |
|----------|----------|----------|----------|------------|
| `GET /` (homepage) | TBD | < 1000 | TBD | < 1% |
| `GET /products/` (list) | TBD | TBD | TBD | < 1% |
| `GET /products/<slug>/` (detail) | TBD | TBD | TBD | < 1% |
| `POST /orders/cart/add/` (AJAX) | TBD | TBD | TBD | < 1% |
| `GET /orders/cart/` (cart page) | TBD | TBD | TBD | < 1% |

*Baselines are measured on the first full staging run and committed to `tests/load/baselines.md`.*

#### CI Artifact Schema

| Artifact | File | Format | Retention |
|----------|------|--------|-----------|
| Coverage HTML report | `htmlcov/` directory | HTML | 7 days (GitHub Actions) |
| Test results | `test-results.xml` | JUnit XML | 7 days |
| E2E test results | `e2e-results.xml` | JUnit XML | 7 days |
| Security scan results | `bandit-report.json` | JSON | 7 days |

---

### Contracts

#### `/health/` Endpoint Contract

```
GET /health/
```

| Scenario | HTTP Status | Body |
|----------|-------------|------|
| All systems healthy | 200 OK | `{"status": "ok", "database": "ok"}` |
| Database unreachable | 503 Service Unavailable | `{"status": "error", "database": "error", "message": "connection timeout"}` |

**Response time SLA**: < 500 ms (if exceeded, treat as failure → 503)
**Authentication**: None required (public endpoint)
**Rate limiting**: Not applied (monitoring services poll every 5 minutes)
**Content-Type**: `application/json`

**Liveness tests required**:
1. Unit test → DB mock healthy → expect 200 + `{"status": "ok"}`
2. Unit test → DB mock raises `OperationalError` → expect 503 + `{"status": "error"}`

#### CI Pipeline Contract

```
Trigger: push to any branch  OR  pull_request to main
```

| Stage | Tool | Gate | Artifact |
|-------|------|------|----------|
| 1. Code Quality | `black --check`, `isort --check`, `flake8`, `mypy` | fail on any violation | — |
| 2. Security Scan | `bandit -r ... -ll`, `pip-audit -r requirements.txt` | fail on high-severity finding or high/critical CVE | `bandit-report.json` |
| 3. Unit + Integration Tests | `pytest tests/ --ignore=tests/e2e --ignore=tests/load --cov --cov-fail-under=95 --junit-xml=test-results.xml` | fail if coverage < 95% or any test fails | `test-results.xml`, `htmlcov/` |
| 4. E2E Tests | `pytest tests/e2e/ --junit-xml=e2e-results.xml` | fail if any E2E test fails | `e2e-results.xml` |

**Fail-fast**: each stage depends on the previous; a failed stage stops all subsequent stages.
**Matrix**: Python 3.11 and 3.12 for Stage 3. Stages 1, 2, 4 run on Python 3.12 only.

---

### Quickstart (`quickstart.md`)

#### Running the full local test suite

```bash
# Unit + integration (existing workflow — unchanged)
pytest tests/ --ignore=tests/e2e --ignore=tests/load

# E2E tests (requires running Django dev server on port 8000)
playwright install chromium
pytest tests/e2e/ --base-url=http://localhost:8000 -v

# E2E tests against staging
pytest tests/e2e/ --base-url=https://staging.yourdomain.com -v

# Load tests (against local server — NEVER against production)
locust -f tests/load/locustfile.py --host=http://localhost:8000 \
       --users=50 --spawn-rate=5 --run-time=60s --headless \
       --html=tests/load/report.html

# Security scan (same as CI)
bandit -r accounts core orders products ecommerce_site -ll -f json -o bandit-report.json
pip-audit -r requirements.txt

# Production settings check
DJANGO_SETTINGS_MODULE=ecommerce_site.settings_production \
  DATABASE_URL=postgresql://user:pass@localhost/shophub \
  SECRET_KEY=dummy python manage.py check --deploy
```

#### Starting the local Docker environment with PostgreSQL

```bash
# First-time setup
docker compose up -d
docker compose exec web python manage.py migrate
docker compose exec web python manage.py createsuperuser

# View logs
docker compose logs -f web
```

---

## Implementation File Inventory

### New Files to Create

| File | Purpose | Key Content |
|------|---------|-------------|
| `core/views.py` | Health check view | `HealthCheckView` — queries `connection.ensure_connection()`; returns 200/503 JSON |
| `core/urls.py` | Health URL routing | `path("health/", HealthCheckView.as_view(), name="health-check")` |
| `ecommerce_site/settings_production.py` | Production Django settings | Extends `settings.py`; `DEBUG=False`, HTTPS flags, JSON logging via `python-json-logger`, WhiteNoise (no Sentry — logging-only approach per R3) |
| `.env.production.example` | Production env var documentation | All required variables with description and example values |
| `tests/test_health.py` | Unit tests for `/health/` | 4 tests: healthy DB → 200; `OperationalError` → 503; message sanitization; no-auth access |
| `tests/e2e/conftest.py` | Playwright E2E fixtures | `base_url` from `--base-url` CLI option; browser launch settings (headless, Chromium) |
| `tests/e2e/test_product_browse.py` | Product browsing E2E journey | Browse homepage, product list, product detail; explicit `wait_for_load_state` waits |
| `tests/e2e/test_cart.py` | Cart E2E journey | Add item to cart, update quantity, remove item |
| `tests/e2e/test_auth.py` | Auth E2E journey | Register new user, login, logout |
| `tests/e2e/test_checkout.py` | Checkout E2E journey | Full cart → checkout → order confirmation |
| `tests/load/locustfile.py` | Locust load test scenarios | `HomepageUser`, `ProductBrowseUser`, `CartUser` task sets; production host guard |
| `tests/load/baselines.md` | Performance baselines | Table of measured p50/p95/p99 per endpoint (filled after first staging run) |
| `.github/workflows/ci.yml` | CI pipeline | 4-stage pipeline; fail-fast; Python 3.11/3.12 matrix; artifact upload |
| `.github/workflows/deploy.yml` | Deploy pipeline | Staging (auto on `main`); production (manual approval via GitHub environment) |
| `scripts/backup_db.sh` | Database backup script | `pg_dump` compressed → S3/R2 bucket; prune snapshots older than 7 days |
| `scripts/restore_db.sh` | Database restore script | Interactive restore from named backup artifact; prompts for confirmation |
| `docs/runbooks/deployment.md` | Deployment runbook | Trigger deploy, rollback, run migrations manually, VPS blue-green alternative |
| `docs/runbooks/backup_restore.md` | Backup/restore runbook | Trigger backup, verify record counts, restore procedure |

### Files to Modify

| File | Change |
|------|--------|
| `requirements.txt` | Add `playwright>=1.44`, `pytest-playwright>=0.5`, `locust>=2.28`, `whitenoise[brotli]>=6.7`, `python-json-logger>=2.0` |
| `Dockerfile` | Add `curl` to runtime `apt-get` packages; add `HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 CMD curl -f http://localhost:8000/health/ \|\| exit 1` |
| `docker-compose.yml` | Add `db` service (PostgreSQL 16-alpine); update `web.depends_on: [db]`; set `DATABASE_URL` env var pointing to `db`; add `db_data` named volume |
| `ecommerce_site/urls.py` | Add `path("health/", include("core.urls"))` before the `products` include |
| `ecommerce_site/settings_test.py` | No changes required |
| `pytest.ini` | Add `e2e` and `load` markers; add `--ignore=tests/e2e` and `--ignore=tests/load` to default `addopts`; add `--cov-fail-under=95` |
| `pyproject.toml` | Add `[tool.coverage.run]` with `omit = ["tests/e2e/*", "tests/load/*", "*/migrations/*"]` |

---

## CI/CD Pipeline Architecture

```
push / pull_request to main
          │
          ▼
┌─────────────────────┐
│  Stage 1: Quality   │  black, isort, flake8, mypy
│  (Python 3.12)      │  → fail: stop all subsequent stages
└────────┬────────────┘
         │ success
         ▼
┌─────────────────────┐
│  Stage 2: Security  │  bandit, pip-audit
│  (Python 3.12)      │  → fail: stop; upload bandit-report.json
└────────┬────────────┘
         │ success
         ▼
┌──────────────────────────────────────────┐
│  Stage 3: Unit + Integration Tests        │  pytest tests/ (excl. e2e, load)
│  (matrix: Python 3.11, 3.12)             │  --cov-fail-under=95 --junit-xml
│                                           │  → upload: htmlcov/, test-results.xml
└────────┬─────────────────────────────────┘
         │ success (both matrix legs must pass)
         ▼
┌─────────────────────┐
│  Stage 4: E2E Tests │  playwright install + pytest tests/e2e/
│  (Python 3.12)      │  --junit-xml=e2e-results.xml
│                     │  → upload: e2e-results.xml
└────────┬────────────┘
         │ success (only on workflow_run for main branch)
         ▼
┌──────────────────────┐   deploy.yml (separate workflow)
│  Deploy to Staging   │── triggered by: workflow_run ci.yml success on main
│  (automatic)         │── runs: fly deploy --app shophub-staging
└────────┬─────────────┘
         │
         ▼ (manual trigger via GitHub environment approval)
┌──────────────────────┐
│  Deploy to           │── requires: "production" environment approval
│  Production          │── runs: fly deploy --app shophub + health-check poll
│  (manual approval)   │── on health-check failure: Fly.io automatic rollback
└──────────────────────┘
```

---

## Production Settings Design

`ecommerce_site/settings_production.py` inherits from `settings.py` and overrides:

```python
from .settings import *  # noqa: F401, F403

DEBUG = False

# All HTTPS/security flags enabled in production
SECURE_SSL_REDIRECT = True
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
SECURE_HSTS_SECONDS = 31536000
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_HSTS_PRELOAD = True
SECURE_CONTENT_TYPE_NOSNIFF = True
X_FRAME_OPTIONS = "DENY"

# WhiteNoise for static files (FR-031)
MIDDLEWARE.insert(1, "whitenoise.middleware.WhiteNoiseMiddleware")
STATICFILES_STORAGE = "whitenoise.storage.CompressedManifestStaticFilesStorage"
WHITENOISE_MAX_AGE = 31536000

# Structured JSON logging (FR-019)
LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "json": {
            "()": "pythonjsonlogger.jsonlogger.JsonFormatter",
            "format": "%(asctime)s %(levelname)s %(name)s %(message)s",
        },
    },
    "handlers": {
        "console": {"class": "logging.StreamHandler", "formatter": "json"},
    },
    "root": {"handlers": ["console"], "level": "WARNING"},
    "loggers": {
        "django": {"handlers": ["console"], "level": "WARNING", "propagate": False},
        "ecommerce_site": {"handlers": ["console"], "level": "INFO", "propagate": False},
    },
}

# No external error tracking — unhandled exceptions are logged as ERROR to stdout
# by Django's built-in AdminEmailHandler equivalent via the JSON logger (FR-020)
# python-json-logger captures exc_info automatically when logging.exception() is called
```

---

## Security Considerations

| Concern | Mitigation |
|---------|-----------|
| Secrets in CI | All sensitive values via GitHub Secrets (`DATABASE_URL`, `SECRET_KEY`, `FLY_API_TOKEN`); no plaintext in workflow YAML (FR-026, FR-033) |
| Health endpoint information disclosure | `/health/` returns only `"ok"/"error"` status — no version, hostname, or stack trace in the response body |
| Log PII | JSON logs omit email/passwords; user ID logged as integer (not email) |
| Bandit false positives | Suppressed with `# nosec BXXX` inline comment and documented justification; undocumented suppressions are a CI violation |
| Load test targeting production | `locustfile.py` reads `LOCUST_HOST` env var and raises `SystemExit` if value matches the production domain (FR-009) |
| Backup credentials | AWS/R2 access key and secret stored in GitHub Secrets; `scripts/backup_db.sh` reads them from environment — never hardcoded |
