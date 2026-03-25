# ShopHub

A Django e-commerce application with a full product catalog, shopping cart, and order management system.

## Quick Start

For full local setup instructions see [specs/004-testing-deployment/quickstart.md](specs/004-testing-deployment/quickstart.md).

### Run the full test suite

```bash
pytest tests/ --ignore=tests/e2e --ignore=tests/load --cov=. --cov-fail-under=95
```

### Run E2E browser tests (Playwright)

```bash
# Install Playwright browser (first time only)
playwright install chromium

# Run all E2E tests against the local dev server
pytest tests/e2e/ -v
```

### Run load tests (Locust)

```bash
locust -f tests/load/locustfile.py \
    --host=http://localhost:8000 \
    --users=50 --spawn-rate=5 --run-time=60s \
    --headless --html=tests/load/report.html
```

### Start Docker with Postgres

```bash
docker compose up -d
# Health check
curl http://localhost:8000/health/
```

## Deployment

- **Staging**: automatically deployed on every merge to `main` via GitHub Actions + Fly.io
- **Production**: requires manual approval in the `production` environment gate

See [docs/runbooks/deployment.md](docs/runbooks/deployment.md) for full procedures.

## Documentation

- [specs/004-testing-deployment/quickstart.md](specs/004-testing-deployment/quickstart.md) — local setup guide
- [docs/runbooks/deployment.md](docs/runbooks/deployment.md) — deploy, rollback, and monitoring
- [docs/runbooks/backup_restore.md](docs/runbooks/backup_restore.md) — database backup and restore
- [docs/go-live-checklist.md](docs/go-live-checklist.md) — pre-launch readiness checklist
