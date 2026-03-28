# Contract: CI/CD Pipeline

**Feature**: `004-testing-deployment`
**Workflows**: `.github/workflows/ci.yml`, `.github/workflows/deploy.yml`
**Date**: 2026-03-24

## CI Workflow (`ci.yml`)

### Triggers

```yaml
on:
  push:
    branches: ["**"]      # every branch push
  pull_request:
    branches: [main]      # PRs targeting main
  schedule:
    - cron: "0 3 * * *"  # nightly at 03:00 UTC (FR-022, scenario 5)
```

### Jobs and Stages

#### Stage 1: Code Quality

| Property | Value |
|----------|-------|
| Job name | `quality` |
| Python version | 3.12 only |
| Runs on | `ubuntu-latest` |
| Tools | `black --check .`, `isort --check-only .`, `flake8 .`, `mypy accounts orders products ecommerce_site core` |
| Failure behaviour | All subsequent stages are skipped (fail-fast via `needs:`) |
| Artifacts uploaded | None |

#### Stage 2: Security Scan

| Property | Value |
|----------|-------|
| Job name | `security` |
| Python version | 3.12 only |
| Depends on | `quality` |
| Tools | `bandit -r accounts core orders products ecommerce_site -ll -f json -o bandit-report.json`, `pip-audit -r requirements.txt` |
| Failure behaviour | Fails on any Bandit HIGH severity finding or any pip-audit HIGH/CRITICAL CVE |
| Artifacts uploaded | `bandit-report.json` (7-day retention) |

#### Stage 3: Unit + Integration Tests

| Property | Value |
|----------|-------|
| Job name | `test` |
| Python versions | **Matrix: 3.11, 3.12** |
| Depends on | `security` |
| Services | PostgreSQL 16 (test suite uses SQLite :memory: via `settings_test.py`, but Postgres service ensures psycopg2 can connect in integration scenarios) |
| Command | `pytest tests/ --ignore=tests/e2e --ignore=tests/load --cov=. --cov-fail-under=95 --junit-xml=test-results.xml --cov-report=html` |
| Coverage threshold | **95%** (constitution floor; stricter than spec FR-025 90%) |
| Failure behaviour | Fails if any test fails OR if coverage < 95% |
| Artifacts uploaded | `test-results.xml`, `htmlcov/` directory (7-day retention) |

#### Stage 4: E2E Tests

| Property | Value |
|----------|-------|
| Job name | `e2e` |
| Python version | 3.12 only |
| Depends on | `test` (all matrix legs must pass) |
| Pre-step | `playwright install chromium --with-deps` |
| Django server | Started via `pytest-django`'s `--live-server-url` / `live_server` fixture; `DJANGO_SETTINGS_MODULE=ecommerce_site.settings_test` |
| Command | `pytest tests/e2e/ --junit-xml=e2e-results.xml -v` |
| Timeout | 5 minutes (SC-008) |
| Failure behaviour | Fails if any E2E test fails; flaky tests must be quarantined before blocking CI |
| Artifacts uploaded | `e2e-results.xml`, screenshots on failure (7-day retention) |

### Environment Variables in CI

All sensitive values are loaded from GitHub Secrets:

```yaml
env:
  SECRET_KEY: ${{ secrets.CI_SECRET_KEY }}
  DATABASE_URL: ${{ secrets.CI_DATABASE_URL }}   # or use SQLite default
  DJANGO_SETTINGS_MODULE: ecommerce_site.settings_test
  AXES_ENABLED: "false"
```

**Rule**: No secrets, API keys, or passwords appear as plaintext in `ci.yml` (FR-026).

---

## Deploy Workflow (`deploy.yml`)

### Triggers

```yaml
on:
  workflow_run:
    workflows: ["CI"]
    types: [completed]
    branches: [main]   # only deploy when main branch CI completes
  workflow_dispatch:   # manual trigger for production deploy + approval
```

### Jobs

#### Deploy to Staging (automatic)

| Property | Value |
|----------|-------|
| Job name | `deploy-staging` |
| Condition | `github.event.workflow_run.conclusion == 'success'` |
| Steps | 1. Checkout; 2. `flyctl deploy --remote-only --app ${{ vars.FLY_STAGING_APP }}`; 3. Poll `/health/` every 10s for up to 5 min |
| Success condition | `/health/` returns 200 at least once within the polling window |
| Failure condition | `/health/` never returns 200 within 5 min (Fly.io rolls back automatically) |
| Secrets required | `FLY_API_TOKEN` |
| Vars required | `FLY_STAGING_APP` (repo variable — app name) |
| Target | `https://<FLY_STAGING_APP>.fly.dev` |

#### Deploy to Production (manual approval)

| Property | Value |
|----------|-------|
| Job name | `deploy-production` |
| Depends on | `deploy-staging` |
| Environment | `production` (GitHub environment with required reviewers — FR-027, FR-042) |
| Steps | 1. Checkout; 2. Require approval (gate via GitHub environment); 3. `flyctl deploy --remote-only --app ${{ vars.FLY_PRODUCTION_APP }}`; 4. Poll `/health/`; 5. Run smoke tests |
| Smoke tests | `pytest tests/e2e/ --base-url=https://${{ vars.FLY_PRODUCTION_APP }}.fly.dev -m smoke -v` |
| Secrets required | `FLY_API_TOKEN` |
| Vars required | `FLY_PRODUCTION_APP` (repo variable) |
| Rollback trigger | Automatic (Fly.io detects failed health check); workflow marks deploy as failed |

### Deployment Sequence (per environment)

```
1. Trigger deploy (CLI/API call)
2. Platform runs: python manage.py migrate --noinput  (release command)
3. Platform starts new container
4. Platform polls GET /health/ → waits for 200
5. Platform shifts traffic to new container
6. Old container decommissioned
7. deploy.yml confirms 200 on app URL
8. Smoke test suite runs (production only)
```

**Invariant**: Step 2 (migrations) completes before step 5 (traffic shift). Partial migration state never serves user requests (edge case from spec).

---

## Artifact Retention Policy

| Artifact | Retention | Notes |
|----------|-----------|-------|
| `bandit-report.json` | 7 days | Security scan output |
| `test-results.xml` | 7 days | JUnit XML for all unit/integration tests |
| `htmlcov/` | 7 days | HTML coverage report |
| `e2e-results.xml` | 7 days | JUnit XML for E2E tests |
| E2E failure screenshots | 7 days | Auto-captured by playwright-pytest on failure |

## PR Status Checks Required

The following checks must be required in the GitHub branch protection rule for `main`:

1. `quality` (Code Quality)
2. `security` (Security Scan)
3. `test (3.11)` (Unit tests on Python 3.11)
4. `test (3.12)` (Unit tests on Python 3.12)
5. `e2e` (Browser E2E tests)

Merging to `main` is blocked if any of these checks fail or are not present (FR-022, FR-023, SC-001, SC-002).
