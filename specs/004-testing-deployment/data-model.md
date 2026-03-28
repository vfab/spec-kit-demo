# Data Model: Testing Completion, CI/CD & Production Deployment

**Feature**: `004-testing-deployment`
**Phase**: 1 — Design
**Date**: 2026-03-24

## Overview

This feature introduces **no new database tables**. All data entities are either:
- Stateless HTTP response schemas (health check endpoint)
- File-based artifacts (CI reports, backup files)
- Configuration-only changes (environment variables, settings)

---

## 1. Health Check Response Schema

The `/health/` endpoint returns a JSON object. This is a runtime response schema — not a database model.

### Healthy Response (HTTP 200)

```json
{
  "status": "ok",
  "database": "ok"
}
```

### Unhealthy Response (HTTP 503)

```json
{
  "status": "error",
  "database": "error",
  "message": "could not connect to server: Connection refused"
}
```

### Field Definitions

| Field | Type | Values | Required |
|-------|------|--------|----------|
| `status` | string | `"ok"` \| `"error"` | Always |
| `database` | string | `"ok"` \| `"error"` | Always |
| `message` | string | Error detail (sanitized) | Only when `status == "error"` |

**Sanitization rule**: The `message` field MUST NOT include internal hostnames, port numbers, credentials, or raw exception stack traces. It contains only the high-level failure description (e.g., `"connection timeout"`, `"host unreachable"`).

### Django View Design

```python
# core/views.py
from django.db import connection, OperationalError
from django.http import JsonResponse
from django.views import View

class HealthCheckView(View):
    """
    GET /health/ — liveness and readiness endpoint.

    Returns 200 {"status": "ok"} when the application and database are
    reachable. Returns 503 {"status": "error"} on any failure.
    Used by: UptimeRobot, deployment health-check polling, Dockerfile HEALTHCHECK.
    """

    def get(self, request):
        try:
            connection.ensure_connection()
            return JsonResponse({"status": "ok", "database": "ok"}, status=200)
        except OperationalError as exc:
            return JsonResponse(
                {
                    "status": "error",
                    "database": "error",
                    "message": str(exc).split("\n")[0],  # first line only — no traces
                },
                status=503,
            )
```

---

## 2. Load Test Baselines Schema

Stored in `tests/load/baselines.md` as a Markdown table. Updated after each staging load test run and committed to the repository. Not a database model.

### Baseline Table Format

```markdown
| Endpoint | Method | VUs | p50 (ms) | p95 (ms) | p99 (ms) | Throughput (req/s) | Error Rate | Measured Date |
|----------|--------|-----|----------|----------|----------|--------------------|------------|---------------|
| /        | GET    | 50  | NNN      | NNN      | NNN      | NNN                | N.NN%      | YYYY-MM-DD    |
| /products/ | GET  | 50  | NNN      | NNN      | NNN      | NNN                | N.NN%      | YYYY-MM-DD    |
| /products/<slug>/ | GET | 50 | NNN | NNN | NNN | NNN | N.NN% | YYYY-MM-DD |
| /orders/cart/add/ | POST | 50 | NNN | NNN | NNN | NNN | N.NN% | YYYY-MM-DD |
| /orders/cart/ | GET | 50 | NNN | NNN | NNN | NNN | N.NN% | YYYY-MM-DD |
```

### Performance Targets (from SC-009, FR-007)

| Endpoint | p95 Target | Error Rate Target |
|----------|-----------|------------------|
| `GET /` (homepage) | < 1000 ms | < 1% |
| All other endpoints | < 2000 ms | < 1% |

---

## 3. CI Artifact Schema

File-based artifacts uploaded to GitHub Actions for each CI run.

### 3.1 JUnit XML Test Results

Produced by: `pytest --junit-xml=test-results.xml`

Standard JUnit XML format consumed by GitHub Actions `junit-reporter` and most CI dashboards.

```xml
<testsuites>
  <testsuite name="pytest" tests="153" errors="0" failures="0" ...>
    <testcase classname="tests.test_products.TestProductModel"
              name="test_active_products_queryset" time="0.012" />
    ...
  </testsuite>
</testsuites>
```

### 3.2 Coverage HTML Report

Produced by: `pytest --cov=. --cov-report=html`

Output directory: `htmlcov/` — uploaded as a GitHub Actions artifact, accessible via the Actions UI for 7 days per run.

### 3.3 Bandit Security Report

Produced by: `bandit -r ... -f json -o bandit-report.json`

```json
{
  "results": [],
  "metrics": {
    "_totals": {
      "CONFIDENCE.HIGH": 0,
      "SEVERITY.HIGH": 0,
      "SEVERITY.MEDIUM": 0
    }
  }
}
```

An empty `results` array and zero counts in `SEVERITY.HIGH` is the required passing state (FR-012).

---

## 4. Environment Variable Schema

All production configuration passed via environment variables. No defaults for secrets.

### Required Variables (`settings_production.py`)

| Variable | Type | Example | Description |
|----------|------|---------|-------------|
| `SECRET_KEY` | string | `django-insecure-...` | Django secret key — no default; fails loudly if absent |
| `DATABASE_URL` | URL | `postgresql://user:pass@host:5432/db` | PostgreSQL connection string |
| `ALLOWED_HOSTS` | CSV | `myapp.fly.dev,myapp.com` | Django `ALLOWED_HOSTS` list |
| `REDIS_URL` | URL | `redis://localhost:6379/1` | Redis cache URL; absent uses LocMemCache |
| `DJANGO_SETTINGS_MODULE` | module | `ecommerce_site.settings_production` | Activates production settings |

### Optional Variables (with defaults)

| Variable | Default | Description |
|----------|---------|-------------|
| `DEBUG` | `False` | Must remain `False` in production |
| `SECURE_SSL_REDIRECT` | `True` | Enforced in production settings |
| `DB_CONN_MAX_AGE` | `60` | DB connection pool max age (seconds) |
| `GUNICORN_WORKERS` | `3` | Gunicorn worker count |
| `TAX_RATE` | `0.08` | Checkout tax rate |
| `MAX_IMAGE_UPLOAD_MB` | `5` | Maximum image upload size |
| `LOW_STOCK_THRESHOLD` | `5` | "Low stock" badge threshold |

### Backup / CI Variables (GitHub Secrets)

| Variable | Used In | Description |
|----------|---------|-------------|
| `R2_ACCOUNT_ID` | `scripts/backup_db.sh` | Cloudflare R2 account ID |
| `R2_ACCESS_KEY_ID` | `scripts/backup_db.sh` | R2 access key |
| `R2_SECRET_ACCESS_KEY` | `scripts/backup_db.sh` | R2 secret key |
| `R2_BUCKET` | `scripts/backup_db.sh` | R2 bucket name |
| `FLY_API_TOKEN` | `.github/workflows/deploy.yml`, `backup.yml` | Fly.io deploy token |
| `PRODUCTION_DATABASE_URL` | `.github/workflows/deploy.yml` | Production DB URL (for migration step) |

---

## 5. State Transitions: Deployment Lifecycle

```
Branch push
    │
    ▼
CI Running ─── fail ──► CI Failed (PR blocked)
    │
   pass
    │
    ▼
Merge to main
    │
    ▼
Staging Deploy Running ─── fail ──► Staging Deploy Failed (platform auto-rollback)
    │
   pass (health check green)
    │
    ▼
Staging Live
    │
   (manual approval trigger)
    │
    ▼
Production Deploy Running ─── fail ──► Production Rolled Back (auto, < 5 min)
    │
   pass (health check green)
    │
    ▼
Production Live
```

**Invariant**: Production is never updated without a prior passing staging deployment. The `deploy.yml` workflow enforces this ordering via `needs: [deploy-staging]` in the production job.
