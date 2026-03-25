# Research: Testing Completion, CI/CD & Production Deployment

**Feature**: `004-testing-deployment`
**Phase**: 0 — Research
**Date**: 2026-03-24

## Summary

All six unknowns from the Technical Context are resolved. No NEEDS CLARIFICATION items remain. All technology choices are consistent with the existing stack and introduce the minimum new dependencies required.

---

## R1 — E2E Framework: Playwright

**Decision**: `playwright>=1.44` + `pytest-playwright>=0.5`

**Rationale**:
- `pytest-playwright` integrates with the existing pytest runner — test discovery, markers (`@pytest.mark.e2e`), fixtures, and JUnit XML output work identically to the unit test suite.
- GitHub Actions `ubuntu-latest` runners provide Chromium via `npx playwright install chromium --with-deps` (or the Python equivalent `playwright install chromium --with-deps`); no display server (Xvfb) required — satisfies FR-005.
- Playwright's `expect(locator).to_be_visible()` and `page.wait_for_load_state("networkidle")` are the explicit-wait primitives required by FR-004. These are stronger than Selenium's `WebDriverWait` because they are assertion-based and produce clear failure messages.
- The `--base-url` CLI option and `pytest-django`'s `live_server` fixture enable FR-003 (same test suite runs against local dev server or any staging URL).
- Mobile viewport testing (FR-002 mobile acceptance scenario) is supported via `browser_context_args` fixture override, setting viewport to `{"width": 375, "height": 667}`.

**Alternatives rejected**:
- Selenium WebDriver: Requires `webdriver-manager` for binary management; more boilerplate for fixture setup; no meaningful capability advantage for this use case.
- Cypress: JavaScript-only; incompatible with the Python/pytest test infrastructure.

**Installation note**: `playwright install chromium --with-deps` must run in CI before the E2E stage. In the `ci.yml`, this is added as a step in the E2E job before `pytest`.

---

## R2 — Structured Logging: `python-json-logger`

**Decision**: `python-json-logger>=2.0` (`pythonjsonlogger.jsonlogger.JsonFormatter`)

**Rationale**:
- Drop-in replacement for the existing `verbose` formatter in `LOGGING["formatters"]` — zero changes to any `logger.info(...)` call site across the codebase.
- Emits a flat JSON object with `asctime`, `levelname`, `name`, `message`, plus any `extra={}` keyword arguments passed to the log call — satisfies FR-019 (timestamp, level, request ID, message).
- Request ID injection can be added in production via a custom `logging.Filter` that reads `threading.local()` storage populated by middleware from `HTTP_X_REQUEST_ID`.
- The existing `verbose` text formatter is preserved in `settings.py` (development) and `settings_test.py`; the JSON formatter is added only in `settings_production.py` — no test suite impact.

**Alternatives rejected**:
- `structlog`: requires `structlog.get_logger()` at every call site — invasive change across 6+ modules.
- DIY `logging.Formatter` subclass: valid but reinvents existing library. Adds maintenance burden.

---

## R3 — Error Tracking: Django Logging Only (zero-cost)

**Decision**: No external error tracking service. `python-json-logger` (already selected for R2) provides sufficient production error visibility at zero cost.

**Rationale**:
- Sentry's free tier is limited to 5,000 events/month and introduces a third-party operational dependency with pricing risk — not "zero cost" in the pure sense.
- Django's built-in logging framework automatically captures unhandled exceptions at `ERROR` level (via `django.request` logger). With `python-json-logger`'s `JsonFormatter`, these are emitted as structured JSON to stdout — satisfying FR-020 without any SDK.
- Fly.io aggregates stdout/stderr logs and makes them available via `fly logs` and the dashboard — no additional tooling required.
- No `SENTRY_DSN` env var. No `sentry-sdk` dependency. No changes to `settings_test.py`.
- If error tracking is added in future, it can be wired in via the existing `LOGGING` dict without touching any call sites.

**No new dependency**.

**Alternatives considered**:
- Sentry free tier: operational dependency with event limits and pricing risk. Rejected (zero-cost constraint).
- GlitchTip self-hosted: requires separate hosting — not zero-cost operationally. Rejected.

---

## R4 — Zero-Downtime Deployment

**Decision**: Fly.io rolling deploy with `flyctl`; `release_command` for migrations

**Rationale**:

### Fly.io (selected — zero cost)
- Fly.io free tier: 3 shared-CPU VMs, 256 MB RAM each, 3 GB persistent volume, managed Postgres cluster — all at zero cost for low-traffic apps. No credit card required for the free tier.
- `fly deploy` performs a rolling update. Fly registers the new container, waits for `GET /health/` to return 200 (configured via `[checks]` in `fly.toml`), then shifts traffic and decommissions the old instance — satisfying FR-038 and SC-004.
- `fly.toml` `[deploy] release_command = "python manage.py migrate --noinput"` runs migrations before traffic cutover — satisfying FR-037.
- Automatic rollback: if the new VM fails health checks within the window, Fly routes traffic back to the previous VM — satisfying FR-041 and SC-005.
- `flyctl` is available in GitHub Actions via `superfly/flyctl-actions/setup-flyctl@master`; authentication uses `FLY_API_TOKEN` GitHub Secret.

### fly.toml configuration (outline)
```toml
app = "shophub"
primary_region = "iad"  # Washington DC — changeable

[build]
  dockerfile = "Dockerfile"

[deploy]
  release_command = "python manage.py migrate --noinput"

[[services]]
  protocol = "tcp"
  internal_port = 8000

  [[services.ports]]
    port = 443
    handlers = ["tls", "http"]

  [[services.http_checks]]
    path = "/health/"
    interval = "10s"
    timeout = "5s"
    grace_period = "30s"
    restart_limit = 3
```

### deploy.yml approach
The `deploy.yml` GitHub Actions workflow calls `fly deploy --app shophub-staging` (staging) or `fly deploy --app shophub` (production, after manual environment approval). The workflow polls `GET /health/` every 10 seconds for up to 5 minutes to confirm success; if it fails, Fly's automatic rollback fires.

**Rejected alternatives**:
- Railway: no genuine free tier as of 2024 (Hobby plan $5/month minimum). Rejected.
- Render: free tier spins down after 15 min inactivity (~30s cold start), unsuitable for production. Rejected.

**VPS / Docker Compose alternative** (documented in runbook):
```bash
# Build new image
docker compose build web
# Start new container (alongside old one if using named services)
docker compose up -d --no-deps --build web
# Poll health check
for i in $(seq 1 30); do
  curl -sf http://localhost:8000/health/ && break
  sleep 10
done
```

---

## R5 — Static File Serving: WhiteNoise

**Decision**: `whitenoise[brotli]>=6.7`

**Rationale**:
- The existing Dockerfile already calls `python manage.py collectstatic --noinput`, writing output to `STATIC_ROOT = BASE_DIR / "staticfiles"`. WhiteNoise serves these files directly from the WSGI process — satisfies FR-031 without a separate nginx static-file proxy.
- `whitenoise[brotli]` adds brotli compression support alongside gzip, improving static asset delivery performance.
- `CompressedManifestStaticFilesStorage` appends content hashes to filenames, enabling permanent (1-year) far-future cache headers.
- WhiteNoise is inserted at position 1 in `MIDDLEWARE` (after `SecurityMiddleware`, before `SessionMiddleware`) so it short-circuits non-dynamic requests before Django processes them.
- `whitenoise.runserver_nostatic` added to `INSTALLED_APPS` (development only in `settings.py`) so `runserver` serves static files correctly during development.

**CDN compatibility**: WhiteNoise is compatible with Cloudflare CDN as a cache origin — static assets are served from the Django process on cache miss but edge-cached on subsequent requests.

---

## R6 — Backup Storage

**Decision**: Cloudflare R2 (S3-compatible API) for production; `pg_dump` + `aws s3 cp`

**Rationale**:
- Cloudflare R2 provides 10 GB free storage per month with zero egress fees and an S3-compatible API. The AWS CLI v2 communicates with R2 using `--endpoint-url https://<account_id>.r2.cloudflarestorage.com`.
- `pg_dump --format=custom` produces a compressed, parallelizable backup artifact. Typical ShopHub database size at initial production is estimated < 100 MB — well within free tier.
- The backup script (`scripts/backup_db.sh`) reads `R2_ACCOUNT_ID`, `R2_ACCESS_KEY_ID`, `R2_SECRET_ACCESS_KEY`, `R2_BUCKET`, and `DATABASE_URL` from environment variables — no credentials in the script file.
- 7-day retention is enforced by listing objects older than 7 days and deleting them in the same script run.
- The GitHub Actions scheduled workflow (`cron: "0 2 * * *"`, daily at 02:00 UTC) triggers the backup script via `fly ssh console` into the production VM or as a standalone GitHub Actions job.

**Restoration test requirement** (FR-039, SC-011): The runbook includes a quarterly procedure to restore the latest backup to a temporary database and verify row counts match — completion within 30 minutes is required.

**For staging**: backups are written to a local Docker volume (no external storage required for staging).

---

## Technology Decision Summary

| Component | Chosen Technology | New Dependency |
|-----------|------------------|----------------|
| E2E browser automation | Playwright + pytest-playwright | `playwright>=1.44`, `pytest-playwright>=0.5` |
| Load testing | Locust | `locust>=2.28` |
| Static file serving | WhiteNoise | `whitenoise[brotli]>=6.7` |
| Error tracking | Django logging only (zero-cost) | No new dependency |
| Structured logging | python-json-logger | `python-json-logger>=2.0` |
| Deployment platform | Fly.io (free tier, rolling deploy) | No new dependency (flyctl in CI) |
| Backup storage | Cloudflare R2 (AWS CLI) | No new dependency (AWS CLI in CI) |
| Security static analysis | Bandit | Already in `requirements.txt` |
| Dependency CVE scan | pip-audit | Already in `requirements.txt` |
| WSGI server | Gunicorn | Already in `requirements.txt` |
