# Quickstart: Testing Completion, CI/CD & Production Deployment

**Feature**: `004-testing-deployment`
**Date**: 2026-03-24

## Prerequisites

```bash
# Ensure virtual environment is active
source .venv/bin/activate   # or: conda activate shophub

# Install all dependencies (including new ones for this feature)
pip install -r requirements.txt

# Install Playwright browsers (one-time setup per machine/CI runner)
playwright install chromium --with-deps
```

---

## Running Tests

### Unit + Integration Tests (existing workflow — unchanged)

```bash
# Full suite with coverage
pytest tests/ --ignore=tests/e2e --ignore=tests/load

# Fast iteration (no coverage, short traceback)
pytest tests/ --ignore=tests/e2e --ignore=tests/load -x --tb=short -q

# Specific module
pytest tests/test_products.py -v

# Coverage report only
pytest tests/ --ignore=tests/e2e --ignore=tests/load --cov=. --cov-report=html
# Open htmlcov/index.html in browser
```

### Health Check Unit Tests (new)

```bash
pytest tests/test_health.py -v
```

### Browser E2E Tests (new)

E2E tests require a running Django server. They can target local dev or any deployed URL.

```bash
# Against local development server (run server first: python manage.py runserver)
pytest tests/e2e/ --base-url=http://localhost:8000 -v

# Against local server via pytest-django live_server fixture (server auto-starts)
pytest tests/e2e/ -v
# (pytest-django starts the server automatically if no --base-url is given
#  and the live_server fixture is used in conftest.py)

# Against staging environment
pytest tests/e2e/ --base-url=https://staging.yourdomain.example.com -v

# Run only smoke tests (for post-deploy validation)
pytest tests/e2e/ -m smoke -v

# Run with headed browser (visible browser window — useful for debugging)
pytest tests/e2e/ --headed -v

# Run with slow motion for visual debugging
pytest tests/e2e/ --headed --slowmo=500 -v

# Mobile viewport (375x667)
pytest tests/e2e/ --browser-channel=chrome --viewport='{"width":375,"height":667}' -v
```

### Load Tests (new)

**WARNING**: Load tests MUST NOT target the production environment. The `locustfile.py` enforces this with a host guard, but always verify `--host`.

```bash
# Headless run (as in CI) — 50 VUs, 60 seconds
locust -f tests/load/locustfile.py \
       --host=http://localhost:8000 \
       --users=50 \
       --spawn-rate=5 \
       --run-time=60s \
       --headless \
       --html=tests/load/report.html

# Open report
open tests/load/report.html  # macOS
xdg-open tests/load/report.html  # Linux

# Interactive web UI (Locust dashboard at http://localhost:8089)
locust -f tests/load/locustfile.py --host=http://localhost:8000
```

---

## Security Scanning

```bash
# Static analysis (Bandit) — same flags as CI
bandit -r accounts core orders products ecommerce_site -ll

# JSON output (for CI artifact)
bandit -r accounts core orders products ecommerce_site -ll -f json -o bandit-report.json
cat bandit-report.json | python -m json.tool

# Dependency CVE scan (pip-audit) — same as CI
pip-audit -r requirements.txt

# Both in one shot (mirrors CI Stage 2)
bandit -r accounts core orders products ecommerce_site -ll && pip-audit -r requirements.txt
```

---

## Running with PostgreSQL (Docker Compose)

```bash
# Start Django + PostgreSQL
docker compose up -d

# First-time: apply migrations and create superuser
docker compose exec web python manage.py migrate
docker compose exec web python manage.py createsuperuser

# Run tests against the Docker environment
docker compose exec web pytest tests/ --ignore=tests/e2e --ignore=tests/load

# View application logs
docker compose logs -f web

# Stop everything
docker compose down

# Stop and remove volumes (wipes the database)
docker compose down -v
```

---

## Production Settings Validation

```bash
# Validate production settings locally (requires PostgreSQL)
DJANGO_SETTINGS_MODULE=ecommerce_site.settings_production \
  DATABASE_URL=postgresql://user:pass@localhost/shophub_test \
  SECRET_KEY=test-only-not-real \
  ALLOWED_HOSTS=localhost \
  python manage.py check --deploy

# The output must show: "System check identified no issues (0 silenced)."
# Critical warnings must be zero (SC-012).
```

---

## Triggering a Backup (Production)

```bash
# Manual backup (requires R2 credentials in environment)
export R2_ACCOUNT_ID=<your-account-id>
export R2_ACCESS_KEY_ID=<your-key-id>
export R2_SECRET_ACCESS_KEY=<your-secret>
export R2_BUCKET=shophub-backups
export DATABASE_URL=postgresql://user:pass@host:5432/shophub

bash scripts/backup_db.sh

# Verify the backup was created
aws s3 ls s3://$R2_BUCKET/ \
  --endpoint-url "https://${R2_ACCOUNT_ID}.r2.cloudflarestorage.com"
```

---

## Triggering a Deployment

### Staging (automatic)

Staging deploys automatically when CI passes on the `main` branch. No manual action required.

To verify: check the GitHub Actions **deploy.yml** workflow run after a merge to `main`.

### Production (manual approval)

1. Go to **GitHub → Actions → Deploy** workflow in the repository.
2. Click **Run workflow** → select branch `main`.
3. The workflow will pause at the `deploy-production` job and request approval.
4. An authorized team member approves via the GitHub environment approval UI.
5. Monitor the deployment progress in the Actions log.
6. Confirm `GET /health/` returns 200 on the production URL.

---

## Checking the Health Endpoint

```bash
# Local
curl -s http://localhost:8000/health/ | python -m json.tool

# Staging
curl -s https://staging.yourdomain.example.com/health/ | python -m json.tool

# Expected output (healthy):
# {
#     "status": "ok",
#     "database": "ok"
# }
```

---

## Common Issues

### E2E tests fail with "Connection refused"

The Django server is not running. Either:
- Use the `live_server` fixture (auto-starts server): ensure `conftest.py` in `tests/e2e/` uses it.
- Or start the server manually: `python manage.py runserver` then pass `--base-url=http://localhost:8000`.

### Playwright not found

Run `playwright install chromium --with-deps` to install the browser binary.

### Bandit reports false positive

Add `# nosec BXXX` inline comment with a documented justification comment on the preceding line:
```python
# Safe: this eval() call only processes trusted internal config, never user input
result = eval(config_expr)  # nosec B307
```

### Load test blocked from targeting production

The `locustfile.py` host guard raises `SystemExit` if `LOCUST_HOST` or `--host` matches the production domain. To run load tests, use the staging or local URL explicitly.
