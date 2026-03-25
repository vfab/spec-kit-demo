# Go-Live Checklist

Complete every item before promoting to production.

---

## Pre-Launch Security Audit

- [ ] `bandit -r accounts core orders products ecommerce_site -ll` → **0 findings** (zero HIGH or MEDIUM severity)
- [ ] `pip-audit -r requirements.txt` → **0 HIGH/CRITICAL CVEs**
- [ ] `DJANGO_SETTINGS_MODULE=ecommerce_site.settings_production python manage.py check --deploy` (with production env vars) → **0 critical warnings**
- [ ] OWASP Top 10 self-assessment passed — see `tests/test_security.py` for automated coverage:
  - Broken access control: `TestSecurityHeaders.test_checkout_requires_authentication`
  - CSRF: `TestSecurityHeaders.test_csrf_required_on_add_to_cart`
  - SQL injection: `TestNoRawSQL`, `TestSQLInjectionRobustness`
  - Security misconfiguration: `pytest tests/ --ignore=tests/e2e --ignore=tests/load` passes at ≥ 95% coverage

---

## Final Staging Load Test

- [ ] Run load test against staging:
  ```bash
  locust -f tests/load/locustfile.py \
    --host=https://shophub-staging.fly.dev \
    --users=50 --spawn-rate=5 --run-time=60s \
    --headless --html=docs/load-test-report.html
  ```
- [ ] Homepage p95 < **1000 ms** (FR-011, SC-009)
- [ ] Error rate < **1%** (SC-009)
- [ ] `tests/load/baselines.md` updated with measured p50/p95/p99 values from this run
- [ ] `docs/load-test-report.html` committed (or attached to this PR)

---

## Infrastructure Readiness

- [ ] **UptimeRobot monitor** is active and has sent at least one successful ping (T-029):
  - Monitor target: `https://shophub.fly.dev/health/`
  - Check interval: 5 minutes
  - Alert contact: operator email confirmed
- [ ] **Automated backup workflow** (`backup.yml`) has run successfully at least once:
  - Navigate to GitHub → Actions → Automated Database Backup
  - Confirm last run status is green
- [ ] **Rollback procedure tested** on staging:
  - `flyctl releases list --app shophub-staging` shows ≥ 2 releases
  - `flyctl releases rollback <previous-version> --app shophub-staging` executed successfully
  - Health check confirmed green after rollback
  - Re-deployed current version after test
- [ ] **SSL certificate** valid for production domain (verify via browser padlock or `curl -Iv https://shophub.fly.dev`)
- [ ] **All GitHub Secrets populated** in repo settings:
  - [ ] `FLY_API_TOKEN`
  - [ ] `CI_SECRET_KEY`
  - [ ] `CI_DATABASE_URL`
  - [ ] `R2_ACCESS_KEY_ID`
  - [ ] `R2_SECRET_ACCESS_KEY`
- [ ] **All GitHub Variables populated** in repo settings:
  - [ ] `FLY_STAGING_APP` = `shophub-staging`
  - [ ] `FLY_PRODUCTION_APP` = `shophub`
  - [ ] `R2_BUCKET`
  - [ ] `R2_ENDPOINT_URL`
- [ ] **GitHub branch protection** on `main` requires all 5 CI status checks:
  - `Code Quality`
  - `Security Scan`
  - `Test (Python 3.11)`
  - `Test (Python 3.12)`
  - `E2E Browser Tests`

---

## Smoke Test Sign-Off

- [ ] E2E smoke tests pass against production:
  ```bash
  pytest tests/e2e/ --base-url=https://shophub.fly.dev -v
  ```
- [ ] Manual walkthrough completed:
  - [ ] Browse product catalog → product detail
  - [ ] Add item to cart → view cart → update quantity → remove item
  - [ ] Register new account
  - [ ] Log in → checkout → order confirmation page
  - [ ] Log out

---

## Sign-Off

```
Approved by: ___________________________   Date: _______________
```
