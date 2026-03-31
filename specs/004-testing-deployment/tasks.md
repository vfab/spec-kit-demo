# Tasks: Testing Completion, CI/CD & Production Deployment

**Feature**: `004-testing-deployment`
**Input**: `specs/004-testing-deployment/plan.md`, `specs/004-testing-deployment/spec.md`
**Branch**: `004-testing-deployment`
**Generated**: 2026-03-24

---

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Parallelizable — operates on different files, no dependency on any incomplete task in the same phase
- **[US#]**: Maps to user story from spec.md (US1–US7)
- All paths are repo-root-relative

---

## Phase 1: Foundation (Shared Infrastructure)

**Purpose**: Establish the production-readiness baseline that every subsequent phase depends on — health endpoint, production settings, structured logging, WhiteNoise static files, updated dependencies, Docker HEALTHCHECK, and test markers.

**⚠️ CRITICAL**: All Phase 2–6 work requires this phase to be complete. The `/health/` endpoint in particular is consumed by the Docker HEALTHCHECK, the Fly.io rolling deploy gating, and the E2E smoke test.

**Covers**: US2 (staging parity), US3 (health endpoint + structured logging)

**Independent Test**: Run `pytest tests/test_health.py -v` and confirm both the 200-healthy and 503-DB-error cases pass. Then run `DJANGO_SETTINGS_MODULE=ecommerce_site.settings_production python manage.py check --deploy` (with dummy env vars) and confirm zero critical warnings.

- [x] T-001 Add `playwright>=1.44`, `pytest-playwright>=0.5`, `locust>=2.28`, `whitenoise[brotli]>=6.7`, `python-json-logger>=2.0` to `requirements.txt`

- [x] T-002 [P] Create `core/views.py` with `HealthCheckView` — queries `connection.ensure_connection()` inside a `try/except OperationalError`; returns `JsonResponse({"status": "ok", "database": "ok"}, status=200)` on success and `JsonResponse({"status": "error", "database": "error", "message": str(e)}, status=503)` on failure

- [x] T-003 [P] Create `core/urls.py` with `urlpatterns = [path("health/", HealthCheckView.as_view(), name="health-check")]`

- [x] T-004 Wire health URL into `ecommerce_site/urls.py` — add `path("", include("core.urls"))` **before** the `products` include (depends on T-003)

- [x] T-005 [P] Write unit tests in `tests/test_health.py` covering all four contract-required cases:
  - `test_health_check_healthy` — mock `connection.ensure_connection` to succeed → assert `response.status_code == 200` and `response.json() == {"status": "ok", "database": "ok"}`
  - `test_health_check_db_error` — mock `connection.ensure_connection` to raise `django.db.OperationalError` → assert `response.status_code == 503` and `response.json()["status"] == "error"`
  - `test_health_message_does_not_leak_internals` — mock `connection.ensure_connection` to raise `OperationalError("line1\nline2\nhostname=secret")` → assert `message` field contains no newlines and does not contain the string `hostname` (first line only, per data-model.md sanitization rule)
  - `test_health_url_requires_no_auth` — GET `/health/` as `AnonymousUser` (no session) → assert status is 200, not 302 (no redirect to login)

- [x] T-006 [P] Create `ecommerce_site/settings_production.py` that:
  - Imports `*` from `ecommerce_site.settings`
  - Reads `SECRET_KEY`, `DATABASE_URL`, `ALLOWED_HOSTS` from env via `python-decouple`
  - Sets `DEBUG = False`, `SECURE_SSL_REDIRECT = True`, `SESSION_COOKIE_SECURE = True`, `CSRF_COOKIE_SECURE = True`, `SECURE_HSTS_SECONDS = 31536000`, `SECURE_HSTS_INCLUDE_SUBDOMAINS = True`
  - Inserts `"whitenoise.middleware.WhiteNoiseMiddleware"` immediately after `"django.middleware.security.SecurityMiddleware"` in `MIDDLEWARE`
  - Sets `STATICFILES_STORAGE = "whitenoise.storage.CompressedManifestStaticFilesStorage"` and `WHITENOISE_MAX_AGE = 31536000`
  - Configures `LOGGING` formatters to use `pythonjsonlogger.jsonlogger.JsonFormatter` with fields: `timestamp`, `level`, `name`, `message`; handlers write to `stdout`

- [x] T-007 Add `HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 CMD curl -f http://localhost:8000/health/ || exit 1` to `Dockerfile`; also add `curl` to the runtime `apt-get install` line (depends on T-002, T-003, T-004)

- [x] T-008 [P] Update `pytest.ini`:
  - Register markers: `e2e: browser automation tests (Playwright)` and `load: load / performance tests (Locust)`
  - Add `--ignore=tests/e2e --ignore=tests/load` to `addopts` so the default run excludes them
  - Add `--cov-fail-under=95` to `addopts`

- [x] T-009 [P] Update `pyproject.toml` `[tool.coverage.run]` section — set `omit` to include `tests/e2e/*`, `tests/load/*`, `*/migrations/*`, `ecommerce_site/wsgi.py`, `ecommerce_site/asgi.py`

**Checkpoint**: `pytest tests/test_health.py` passes (2 tests). `python manage.py check --deploy` emits no critical warnings with production env vars set.

---

## Phase 2: E2E Tests (User Story 4)

**User Story 4**: Developer Validates Complete User Journeys via Browser Automation (Priority: P2)

**Goal**: A Playwright-backed test suite covers the five primary user flows — product browsing, cart management, user registration, login/logout, and order checkout — and can run headless in CI against both local dev server and staging.

**Independent Test**: `playwright install chromium && pytest tests/e2e/ --base-url=http://localhost:8000 -v` — all primary journey tests must pass with zero fixed `time.sleep()` calls in test code.

**Depends on**: Phase 1 complete (T-001 for package install, T-008 for marker registration)

- [x] T-010 Create `tests/e2e/__init__.py` (empty) and `tests/e2e/conftest.py` with:
  - `base_url` fixture that reads `pytest.ini`'s `--base-url` option (or falls back to `live_server.url` from `pytest-django`)
  - Browser launch options: `headless=True`, `slow_mo=0`, viewport `{"width": 1280, "height": 720}`
  - `page` fixture using `playwright.chromium.launch()` shared across tests in the module
  - Mark all tests in the directory with `@pytest.mark.e2e`

- [x] T-011 [P] [US4] Create `tests/e2e/test_product_browse.py`:
  - `test_homepage_loads` — navigate to `/`, `page.wait_for_load_state("networkidle")`, assert page title contains site name
  - `test_product_list_visible` — navigate to `/products/`, wait for product cards to be visible, assert at least one product card is present
  - `test_product_detail_accessible` — click first product card, wait for load, assert product name heading is visible and add-to-cart button is present
  - All waits use `expect(locator).to_be_visible()` or `page.wait_for_load_state()`; zero `time.sleep()` calls

- [x] T-012 [P] [US4] Create `tests/e2e/test_cart.py`:
  - `test_add_item_to_cart` — navigate to a product detail page, click "Add to cart", wait for cart count badge update, assert badge shows non-zero count
  - `test_cart_page_shows_item` — after adding an item, navigate to `/orders/cart/`, assert the product name is visible in the cart
  - `test_remove_item_from_cart` — add item, navigate to cart, click remove, wait for page update, assert cart is empty

- [x] T-013 [P] [US4] Create `tests/e2e/test_auth.py`:
  - `test_user_registration` — navigate to registration page, fill username/email/password fields, submit, `page.wait_for_url("**/")`, assert logged-in state (e.g. username visible in nav)
  - `test_user_login` — use a pre-created test user fixture, navigate to login, fill credentials, submit, assert redirect to dashboard/home
  - `test_user_logout` — login first, click logout link, assert login link reappears in nav

- [x] T-014 [US4] Create `tests/e2e/test_checkout.py` (depends on T-012 cart flow, T-013 auth flow):
  - `test_full_checkout_journey` — login as test user, add a product to cart, proceed to checkout, fill shipping address form, submit, wait for order confirmation page, assert order confirmation heading is visible and contains an order number
  - `test_checkout_requires_login` — without logging in, attempt to access checkout URL directly, assert redirect to login page

- [x] T-030 [P] [US4] Add mobile viewport coverage to `tests/e2e/conftest.py` (US4 acceptance scenario 2):
  - Add a `mobile_page` fixture that overrides `browser_context_args` with `{"viewport": {"width": 375, "height": 667}}` (iPhone SE portrait)
  - Create `tests/e2e/test_mobile_responsive.py` with:
    - `test_homepage_no_horizontal_scroll` — use `mobile_page`, navigate to `/`, assert `document.body.scrollWidth <= 375` via `page.evaluate()`
    - `test_product_list_accessible_mobile` — use `mobile_page`, navigate to `/products/`, assert at least one product card is visible
    - `test_cart_accessible_mobile` — use `mobile_page`, add a product to cart, navigate to `/orders/cart/`, assert cart content is visible without layout breaking
  - All tests use `@pytest.mark.e2e` marker
  - Zero `time.sleep()` calls; use `expect(locator).to_be_visible()` throughout

**Checkpoint**: `pytest tests/e2e/ -v --base-url=http://localhost:8000` exits 0 with all tests passing. No `time.sleep()` present in `tests/e2e/`.

---

## Phase 3: Load Tests (User Story 5)

**User Story 5**: Developer Measures Application Performance Under Load (Priority: P2)

**Goal**: A Locust load test script covers five endpoint scenarios; a production-host guard prevents accidental production targeting; a baselines document captures p50/p95/p99 targets.

**Independent Test**: `locust -f tests/load/locustfile.py --host=http://localhost:8000 --users=50 --spawn-rate=5 --run-time=60s --headless --html=tests/load/report.html` — exits 0 with an HTML report generated; p95 for homepage < 1 s; zero 5xx errors.

**Depends on**: T-001 (locust package installed)

- [x] T-015 [P] [US5] Create `tests/load/__init__.py` (empty) and `tests/load/locustfile.py` with:
  - Production guard at module level: read `TARGET_HOST` or `--host` value; if it matches a production hostname pattern (configurable via `LOCUST_ALLOWED_HOSTS` env var defaulting to `localhost,127.0.0.1,staging`), allow; otherwise `raise SystemExit("Load tests must not target production. Set LOCUST_ALLOWED_HOSTS to override.")`
  - `HomepageUser(HttpUser)` with `@task` hitting `GET /` — weight 3
  - `ProductBrowseUser(HttpUser)` with tasks: `GET /products/` (weight 2), `GET /products/<slug>/` for 3 randomized slugs read from a class-level list (weight 2)
  - `CartUser(HttpUser)` with tasks: `GET /orders/cart/` (weight 1), AJAX `POST /orders/cart/add/` with a product ID and CSRF token (weight 1)
  - `wait_time = between(1, 3)` on all user classes
  - `--users`, `--spawn-rate`, `--host` all honored via Locust CLI; no hardcoded values

- [x] T-016 [P] [US5] Create `tests/load/baselines.md` — document the performance baseline table with: columns Endpoint, p50 (ms), p95 (ms), p99 (ms), Error Rate; rows for `GET /`, `GET /products/`, `GET /products/<slug>/`, `POST /orders/cart/add/`, `GET /orders/cart/`; all values initially marked `TBD — measure on first staging run`; include target thresholds (homepage p95 < 1000 ms, error rate < 1%) per spec FR-011

**Checkpoint**: `locust -f tests/load/locustfile.py --host=http://localhost:8000 --users=10 --spawn-rate=2 --run-time=10s --headless` exits 0. Attempting `--host=https://yourproductionsite.com` (not in allowlist) exits with the guard error message.

---

## Phase 4: CI/CD Pipeline (User Stories 1 & 6)

**User Story 1**: Developer Merges Code and Gets Automated Feedback (Priority: P1)
**User Story 6**: Security Engineer Runs Vulnerability Scan and Sees No High-Severity Findings (Priority: P2)

**Goal**: A 4-stage fail-fast GitHub Actions CI workflow (lint → security → test matrix → E2E) gates every PR and branch push. A separate deploy workflow handles staging (auto) and production (manual approval).

**Independent Test (US1)**: Push a branch with a deliberate `pytest` failure; the CI `test` job turns red and the PR is blocked. Fix the failure, push again; all four stages turn green.

**Independent Test (US6)**: Add `eval(input())` to a test file, push to CI; the `security` stage fails citing Bandit rule B307. Revert, push again; security stage passes.

**Depends on**: Phase 1 complete (T-008 for marker/coverage config; T-001 for all packages); Phase 2 complete (T-010–T-014 for E2E jobs to have something to run); Phase 3 complete (T-015 for load scenarios available)

- [x] T-017 [US1] Create `.github/workflows/ci.yml` with the following jobs wired via `needs:` for fail-fast ordering:

  **`quality` job** (Python 3.12, `ubuntu-latest`):
  - Steps: checkout, setup-python, `pip install -r requirements.txt`, `black --check .`, `isort --check-only .`, `flake8 .`, `mypy accounts orders products ecommerce_site core`
  - Triggers: `push` to `**`, `pull_request` to `main`, `schedule: cron: "0 3 * * *"`

  **`security` job** (`needs: quality`, Python 3.12):
  - Steps: checkout, setup-python, pip install, `bandit -r accounts core orders products ecommerce_site -ll -f json -o bandit-report.json`, `pip-audit -r requirements.txt`
  - Upload artifact `bandit-report.json` (retention 7 days) even on failure
  - **Fails on any Bandit HIGH or MEDIUM-severity finding** (the `-ll` flag surfaces MEDIUM and above; constitution requires zero medium/high) or any pip-audit HIGH/CRITICAL CVE

  **`test` job** (`needs: security`, matrix: Python `[3.11, 3.12]`):
  - Services: `postgres:16-alpine` with `POSTGRES_DB`, `POSTGRES_USER`, `POSTGRES_PASSWORD` env vars
  - Steps: checkout, setup-python, pip install, `pytest tests/ --ignore=tests/e2e --ignore=tests/load --cov=. --cov-fail-under=95 --junit-xml=test-results.xml --cov-report=html`
  - All secrets via `${{ secrets.CI_SECRET_KEY }}`, `${{ secrets.CI_DATABASE_URL }}`; `DJANGO_SETTINGS_MODULE: ecommerce_site.settings_test`
  - Upload artifacts: `test-results.xml`, `htmlcov/` (retention 7 days)

  **`e2e` job** (`needs: test`, Python 3.12):
  - Steps: checkout, setup-python, pip install, `playwright install chromium --with-deps`, `pytest tests/e2e/ --junit-xml=e2e-results.xml -v --ds=ecommerce_site.settings_test`
  - **Django server is managed by `pytest-django`'s `live_server` fixture** (configured in T-010 conftest). Do NOT start a separate `manage.py runserver &` process — doing so causes a port conflict with the `live_server` fixture.
  - The `--base-url` is derived automatically from `live_server.url` in the conftest fixture when not supplied via CLI.
  - Upload artifacts: `e2e-results.xml`, screenshots on failure (retention 7 days)
  - Timeout: 5 minutes (`timeout-minutes: 5`)
  - `DJANGO_SETTINGS_MODULE: ecommerce_site.settings_test`

  No secrets hard-coded; all sensitive values from `${{ secrets.* }}`

- [x] T-018 [US1] [US2] Create `.github/workflows/deploy.yml` with:

  **Triggers** (match `contracts/ci-pipeline-contract.md`):
  ```yaml
  on:
    workflow_run:
      workflows: ["CI"]
      types: [completed]
      branches: [main]   # deploy only when main-branch CI completes successfully
    workflow_dispatch:   # manual trigger for production deploy
  ```

  **`deploy-staging` job** (condition: `github.event.workflow_run.conclusion == 'success'`):
  - Steps: checkout, `superfly/flyctl-actions/setup-flyctl@master`, `flyctl deploy --remote-only --app ${{ vars.FLY_STAGING_APP }}` using `FLY_API_TOKEN: ${{ secrets.FLY_API_TOKEN }}`
  - Environment: `staging` (defined in repo settings, no approval gate)

  **`deploy-production` job** (`needs: deploy-staging`):
  - Environment: `production` with `required_reviewers` set (manual approval enforced by GitHub environment protection rule — document in repo settings instructions)
  - Steps: checkout, setup-flyctl, `flyctl deploy --remote-only --app ${{ vars.FLY_PRODUCTION_APP }}`
  - Uses same `FLY_API_TOKEN` secret; app name from repo variable `FLY_PRODUCTION_APP`

**Checkpoint (US1)**: Open a PR with a failing test; CI `test` job fails and blocks merge. Fix test, push; all 4 stages pass and PR is unblocked.
**Checkpoint (US6)**: `bandit -r accounts core orders products ecommerce_site -ll` reports no HIGH findings on the clean codebase.

---

## Phase 5: Deployment Config (User Stories 2 & 3)

**User Story 2**: Developer Deploys to Staging with One Command (Priority: P1)
**User Story 3**: Site Owner Deploys to Production and Monitors Health (Priority: P1)

**Goal**: Fly.io `fly.toml` defines rolling deploy with migration release command; `.env.production.example` documents every required env var; `docker-compose.yml` adds a Postgres 16 service for local dev parity.

**Independent Test (US2)**: `flyctl deploy --remote-only` deploys to staging; smoke test script hits `/health/`, `/`, `/products/`, `/accounts/login/` and confirms all return 200.

**Independent Test (US3)**: Production deployment requires manual approval in GitHub UI before proceeding. After deploy, `GET /health/` returns `{"status":"ok"}` within 500 ms.

**Depends on**: T-002–T-004 (health endpoint live), T-006 (production settings), T-007 (HEALTHCHECK in Dockerfile), T-017 (ci.yml in place as deploy.yml dependency)

- [x] T-019 [P] [US2] [US3] Create `fly.toml` at repo root:
  - `app = "shophub-staging"` (or parameterize; note: production app name set separately via CLI)
  - `primary_region = "iad"` (changeable)
  - `[build]` section pointing to repo root `Dockerfile`
  - `[deploy] release_command = "python manage.py migrate --noinput"` (satisfies FR-037)
  - `[deploy] strategy = "rolling"` (satisfies FR-038)
  - `[[services]]` block: `internal_port = 8000`, `protocol = "tcp"`, `[[services.http_checks]]` targeting `/health/` with `interval = "30s"`, `timeout = "5s"`, `grace_period = "10s"`
  - `[env]` block: `DJANGO_SETTINGS_MODULE = "ecommerce_site.settings_production"`, `PORT = "8000"`; all secrets (`SECRET_KEY`, `DATABASE_URL`) managed via `flyctl secrets set` — not committed to `fly.toml`

- [x] T-020 [P] [US2] [US3] Create `.env.production.example` documenting every required production environment variable with description and example value:
  ```
  SECRET_KEY=           # Django secret key — generate with: python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"
  DATABASE_URL=         # PostgreSQL connection string, e.g. postgresql://user:pass@host:5432/dbname
  ALLOWED_HOSTS=        # Comma-separated hostnames, e.g. yourdomain.com,www.yourdomain.com
  DJANGO_SETTINGS_MODULE=ecommerce_site.settings_production
  PORT=8000
  ```
  Include all vars consumed by `settings_production.py` (R2/R2 bucket vars for backup, etc.)

- [x] T-021 [P] [US2] Update `docker-compose.yml` to add:
  - `db` service: `image: postgres:16-alpine`, env vars `POSTGRES_DB`, `POSTGRES_USER`, `POSTGRES_PASSWORD`, named volume `db_data:/var/lib/postgresql/data`
  - `web.depends_on: [db]`
  - `web.environment.DATABASE_URL: postgresql://postgres:postgres@db:5432/shophub`
  - `volumes:` block at top level with `db_data:` entry
  - Comment: `# This docker-compose.yml is for LOCAL DEVELOPMENT ONLY — not for production (FR-036)`

- [x] T-029 [P] [US3] Configure UptimeRobot uptime monitoring (FR-018, SC-007):
  - Create a free UptimeRobot account at https://uptimerobot.com
  - Add an HTTP(S) monitor targeting `https://<production-host>/health/`
  - Set check interval to **5 minutes** (maximum for free tier)
  - Configure alert contact to the operator's email address
  - Document the monitor URL and alert contact in `docs/runbooks/deployment.md` under a **Monitoring** section
  - Add a line to `go-live-checklist.md` (T-033) confirming the monitor is active and has sent at least one successful ping
  - Note: UptimeRobot does NOT require authentication; the `/health/` endpoint is intentionally public (per contract). No secrets needed.

**Checkpoint (US2)**: `docker compose up -d` starts both `web` and `db`; `docker compose exec web python manage.py migrate` succeeds; `curl http://localhost:8000/health/` returns `{"status":"ok","database":"ok"}`.
**Checkpoint (US3)**: `fly.toml` passes `flyctl config validate`; health check endpoint is reachable on staging within 30 s of `flyctl deploy` completing.

---

## Phase 6: Backup & Runbooks (User Story 7 + Cross-Cutting)

**User Story 7**: Operator Performs Database Backup and Restore (Priority: P3)

**Goal**: Shell scripts for pg_dump → Cloudflare R2 backup with 7-day retention and interactive restore; runbooks document deployment, rollback, and backup/restore procedures.

**Independent Test**: `./scripts/backup_db.sh` creates a `.dump` file and uploads it to the configured R2 bucket. `./scripts/restore_db.sh <backup-key>` downloads and restores it; `psql -c "SELECT COUNT(*) FROM products_product"` on the restored DB matches the original.

**Depends on**: T-019 (fly.toml defines deployment model referenced in runbooks), T-017/T-018 (CI/CD pipeline described in deployment runbook)

- [x] T-022 [P] [US7] Create `scripts/backup_db.sh` (executable, `chmod +x`):
  - Reads `DATABASE_URL`, `R2_BUCKET`, `R2_ENDPOINT_URL`, `AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY` from environment; exits with non-zero status and error message if any are missing
  - Generates filename: `backup_$(date +%Y%m%dT%H%M%S).dump`
  - Runs `pg_dump --format=custom "$DATABASE_URL" -f "/tmp/$FILENAME"`
  - Uploads with `aws s3 cp "/tmp/$FILENAME" "s3://$R2_BUCKET/backups/$FILENAME" --endpoint-url "$R2_ENDPOINT_URL"`
  - Deletes S3 objects older than 7 days: list objects, filter by `LastModified < now-7days`, delete each
  - Prints `Backup complete: $FILENAME` on success; exits 1 on any error (satisfies FR-039 alert-on-failure)

- [x] T-023 [P] [US7] Create `scripts/restore_db.sh` (executable):
  - Accepts one argument: backup key (e.g. `backup_20260324T020000.dump`); prints usage and exits 1 if not provided
  - Downloads from R2 to `/tmp/<key>` via `aws s3 cp`
  - Prompts `"WARNING: This will overwrite $DATABASE_URL. Type YES to continue:"` — aborts unless user types exact string `YES`
  - Runs `pg_restore --clean --no-owner -d "$DATABASE_URL" "/tmp/<key>"`
  - Prints row counts for key tables post-restore as verification

- [x] T-024 [P] Create `docs/runbooks/deployment.md` with sections:
  - **Trigger a staging deploy**: `git push origin main` → CI runs → `deploy-staging` job triggers automatically
  - **Trigger a production deploy**: Navigate to GitHub Actions → `deploy.yml` → approve the `deploy-production` environment gate
  - **Monitor deploy progress**: `flyctl logs --app shophub-production -f`
  - **Rollback procedure**: `flyctl releases list --app shophub-production`, then `flyctl deploy --image <previous-image>` or `flyctl releases rollback <version>`
  - **Run migrations manually** (emergency): `flyctl ssh console --app shophub-production -C "python manage.py migrate --noinput"`
  - **Known irreversible migrations**: table listing migration name, date, and reason; instructions to update before authoring a squash migration
  - **Zero-downtime guarantee**: explanation of Fly.io rolling deploy + health-check gating

- [x] T-025 [P] Create `docs/runbooks/backup_restore.md` with sections:
  - **Trigger a manual backup**: `DATABASE_URL=... R2_BUCKET=... ./scripts/backup_db.sh`
  - **Verify backup was created**: `aws s3 ls s3://$R2_BUCKET/backups/ --endpoint-url $R2_ENDPOINT_URL`
  - **Restore procedure**: `./scripts/restore_db.sh <backup-key>` with full walkthrough
  - **Verify restore**: expected row counts for `products_product`, `accounts_user`, `orders_order`
  - **Automated daily backup**: description of the GitHub Actions scheduled workflow (`backup.yml` at `cron: "0 2 * * *"`) that calls `backup_db.sh`
  - **What to do if backup storage is full/unavailable**: escalation checklist

- [x] T-031 [P] [US7] Create `.github/workflows/backup.yml` — automated daily backup workflow (FR-039):
  - Trigger: `schedule: cron: "0 2 * * *"` (daily at 02:00 UTC) + `workflow_dispatch` (manual trigger)
  - Job: `backup` running on `ubuntu-latest`
  - Steps:
    1. `superfly/flyctl-actions/setup-flyctl@master`
    2. `flyctl ssh console --app ${{ vars.FLY_PRODUCTION_APP }} -C "./scripts/backup_db.sh"` to run the backup inside the production VM
    3. On failure: the job exit code is non-zero and GitHub Actions notifies the configured email (satisfies FR-039 alert-on-failure requirement)
  - Secrets required: `FLY_API_TOKEN`, `R2_ACCESS_KEY_ID`, `R2_SECRET_ACCESS_KEY`
  - Vars required: `FLY_PRODUCTION_APP`, `R2_BUCKET`, `R2_ENDPOINT_URL`
  - All secrets passed as env vars into the `flyctl ssh console` command; never logged
  - Add `backup.yml` reference to `docs/runbooks/backup_restore.md` (T-025)

**Checkpoint (US7)**: `scripts/backup_db.sh` runs against a local Postgres container and produces a `.dump` file. `scripts/restore_db.sh` with a valid key restores that dump. Both scripts exit cleanly and provide meaningful error messages on missing env vars.

---

## Phase 7: Polish & Cross-Cutting Concerns

**Purpose**: Tie together loose ends — security test coverage, coverage exclusion validation, documentation gaps, and any config discovered during integration.

- [x] T-026 [P] Add security regression tests to `tests/test_security.py` (extend existing file):
  - `test_security_headers_present` — assert `X-Content-Type-Options`, `X-Frame-Options`, `Content-Security-Policy` headers are present in responses from the home page
  - `test_csrf_required_on_add_to_cart` — POST to `/orders/cart/add/` without CSRF token → assert 403
  - `test_checkout_requires_authentication` — unauthenticated GET to checkout → assert redirect to login
  - `test_no_stack_trace_in_500_response` — trigger a 500 with `DEBUG=False` and assert response body does not contain `Traceback`

- [x] T-027 [P] Validate coverage omit configuration — run `pytest tests/ --ignore=tests/e2e --ignore=tests/load --cov=. --cov-report=term-missing` locally and confirm `tests/e2e/`, `tests/load/`, and `*/migrations/*` files are absent from the coverage report. Update `pyproject.toml` `omit` list if any still appear.

- [x] T-028 Update `README.md` (or create if absent) with a **Quick Start** section referencing `specs/004-testing-deployment/quickstart.md` commands for: running the full local test suite, running E2E tests, running load tests, and starting Docker with Postgres.

- [x] T-032 [P] [US6] Extend `tests/test_security.py` or create `tests/test_mocks.py` with mock/patch coverage for FR-016:
  - `test_email_backend_is_locmem_in_tests` — assert `settings.EMAIL_BACKEND == 'django.core.mail.backends.locmem.EmailBackend'` when `settings_test.py` is active; trigger a view that sends email and assert `len(mail.outbox) == 1` (no real SMTP call)
  - `test_payment_processing_is_mocked` — if a payment integration exists, mock the payment gateway client and assert the mock is called rather than the real endpoint; if no payment integration exists yet, add a `@pytest.mark.skip(reason="payment gateway not yet integrated")` placeholder
  - `test_file_upload_does_not_write_to_disk` — use `override_settings(MEDIA_ROOT=tmp_path)` (pytest `tmp_path` fixture) when uploading a product image via form; assert the file is written to the temporary path, not the production `media/` directory
  - All tests MUST pass with the existing `settings_test.py` configuration

- [x] T-033 [P] Create `docs/go-live-checklist.md` covering FR-043, FR-044, FR-045:
  - **Pre-launch security audit checklist**:
    - [ ] `bandit -r accounts core orders products ecommerce_site -ll` → 0 findings
    - [ ] `pip-audit -r requirements.txt` → 0 HIGH/CRITICAL CVEs
    - [ ] `python manage.py check --deploy` (with production env vars) → 0 critical warnings
    - [ ] OWASP Top 10 self-assessment (linked to project security tests in `tests/test_security.py`)
  - **Final staging load test**:
    - [ ] Run `locust -f tests/load/locustfile.py --host=<staging-url> --users=50 --spawn-rate=5 --run-time=60s --headless --html=docs/load-test-report.html`
    - [ ] Confirm homepage p95 < 1000 ms and error rate < 1% (SC-009)
    - [ ] Commit `tests/load/baselines.md` with measured values from this run
  - **Infrastructure readiness**:
    - [ ] UptimeRobot monitor is active and has sent at least one successful ping (T-029)
    - [ ] Automated backup workflow (`backup.yml`) has run successfully at least once
    - [ ] Rollback procedure tested: `flyctl releases rollback` executed in staging
    - [ ] SSL certificate valid for production domain
    - [ ] All GitHub Secrets (`FLY_API_TOKEN`, `CI_SECRET_KEY`, etc.) populated in repo settings
    - [ ] GitHub branch protection rule on `main` requires all 5 CI status checks (per ci-pipeline-contract.md)
  - **Smoke test sign-off**:
    - [ ] `pytest tests/e2e/ --base-url=<production-url> -m smoke` exits 0
    - [ ] Manual walkthrough: browse → add to cart → checkout → order confirmation
  - Sign-off line: `Approved by: ___________ Date: ___________`

**Checkpoint**: `pytest tests/ --ignore=tests/e2e --ignore=tests/load --cov=. --cov-fail-under=95` passes with ≥ 95% coverage. No migration or E2E files appear in coverage output.

---

## Dependencies

```
Phase 1 (Foundation)
  └── Phase 2 (E2E Tests)        [T-001 packages, T-008 markers]
  └── Phase 3 (Load Tests)       [T-001 packages]
  └── Phase 4 (CI/CD Pipeline)   [T-008 coverage config, T-001 packages]
      Phase 2 ─────────────────► Phase 4 (E2E job needs E2E tests to exist)
      Phase 3 ─────────────────► Phase 4 (load test files present, excluded by markers)
  └── Phase 5 (Deploy Config)    [T-002–T-007 health endpoint + Docker HEALTHCHECK]
      Phase 4 ─────────────────► Phase 5 (ci.yml must exist before deploy.yml is meaningful)
  └── Phase 6 (Backup/Runbooks)  [T-019 fly.toml, T-017/T-018 pipeline docs]
  └── Phase 7 (Polish)           [all prior phases]
```
New task placement:
- T-029 (UptimeRobot) → Phase 5 (depends on T-002–T-004 health endpoint; requires production URL from T-019)
- T-030 (mobile viewport) → Phase 2 (depends on T-010 conftest, T-001 packages)
- T-031 (backup.yml workflow) → Phase 6 (depends on T-022 backup script)
- T-032 (mock/patch tests) → Phase 7 (can run independently; no new dependencies)
- T-033 (go-live checklist) → Phase 7 (depends on all prior phases complete)
**User Story completion order** (by priority and dependency):
1. US2 + US3 (P1 deploy stories) — unblocked after Phase 1 + Phase 5
2. US1 (P1 CI story) — unblocked after Phase 4
3. US4 (P2 E2E) — unblocked after Phase 2
4. US5 (P2 load) — unblocked after Phase 3
5. US6 (P2 security scan) — unblocked after Phase 4 (`bandit`/`pip-audit` in ci.yml)
6. US7 (P3 backup) — unblocked after Phase 6

---

## Parallel Execution Examples

### Phase 1 — can run in parallel:
```
T-001 (requirements.txt)    ║  T-002 (core/views.py)     ║  T-003 (core/urls.py)
T-005 (test_health.py)      ║  T-006 (settings_prod.py)  ║  T-008 (pytest.ini)
T-009 (pyproject coverage)  ║
```
T-004 (urls.py wiring) depends on T-003; T-007 (Dockerfile) depends on T-002.

### Phase 2 — can run in parallel after T-010:
```
T-011 (test_product_browse)  ║  T-012 (test_cart)  ║  T-013 (test_auth)
```
T-014 (test_checkout) depends on T-012 and T-013 patterns being established.

### Phase 5 — can all run in parallel:
```
T-019 (fly.toml)  ║  T-020 (.env.production.example)  ║  T-021 (docker-compose)  ║  T-029 (UptimeRobot)
```

### Phase 6 — can all run in parallel:
```
T-022 (backup_db.sh)  ║  T-023 (restore_db.sh)  ║  T-024 (deployment.md)  ║  T-025 (backup_restore.md)  ║  T-031 (backup.yml)
```

### Phase 7 — can all run in parallel:
```
T-026 (security tests)  ║  T-027 (coverage validation)  ║  T-028 (README)  ║  T-030 (mobile E2E)  ║  T-032 (mock tests)  ║  T-033 (go-live checklist)
```

---

## Implementation Strategy

**MVP Scope (deliver first)**: Phase 1 + Phase 4 + Phase 5
- Gets CI gating live on every PR immediately (US1 — highest leverage)
- Gets staging deploy automated (US2)
- All subsequent phases build on a green CI baseline

**Phase 2 Increment**: E2E tests (US4) added to CI once CI is stable
**Phase 3 Increment**: Load tests (US5) added as a separate optional step
**Phase 6 Increment**: Backup automation (US7) added last — lower urgency, no user-facing impact

---

## Summary

| Phase | Tasks | User Stories | Parallelizable |
|-------|-------|--------------|----------------|
| 1 — Foundation | T-001–T-009 (9 tasks) | US2, US3 (partial) | 7 of 9 |
| 2 — E2E Tests | T-010–T-014 (5 tasks) | US4 | 3 of 5 |
| 3 — Load Tests | T-015–T-016 (2 tasks) | US5 | 2 of 2 |
| 4 — CI/CD Pipeline | T-017–T-018 (2 tasks) | US1, US6 | 0 of 2 |
| 5 — Deployment Config | T-019–T-021 (3 tasks) | US2, US3 | 3 of 3 |
| 6 — Backup & Runbooks | T-022–T-025 (4 tasks) | US7 | 4 of 4 |
| 7 — Polish | T-026–T-028 (3 tasks) | Cross-cutting | 2 of 3 |
| **Total** | **28 tasks** | **7 user stories** | **21 parallelizable** |

**Coverage**: All 7 user stories (US1–US7) fully covered. All 41 functional requirements (FR-001–FR-040) addressed. All 6 edge cases from spec.md mitigated (production load test guard in T-015, explicit waits mandate in T-011–T-014, health check timeout in T-002, irreversible migration flag in T-024, false-positive suppression policy in T-017 bandit config, backup failure alerting in T-022).
